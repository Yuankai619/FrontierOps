"""Safe local-library scanning with routed document parsers."""

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Protocol

import pymupdf

from frontierops.domain.models import LocalLibraryConfig, PaperMetadata, SourceBatch, SourceRecord


class DocumentParser(Protocol):
    name: str

    def parse(self, path: Path) -> list[dict[str, Any]]: ...


class PyMuPDFParser:
    name = "pymupdf"

    def parse(self, path: Path) -> list[dict[str, Any]]:
        pages = []
        with pymupdf.open(path) as document:
            for index, page in enumerate(document):
                pages.append({
                    "text": page.get_text("text").strip(),
                    "locator": {
                        "type": "pdf_page",
                        "page": index + 1,
                        "bbox": [0.0, 0.0, page.rect.width, page.rect.height],
                    },
                })
        return pages


class PlainTextParser:
    name = "plain_text"

    def parse(self, path: Path) -> list[dict[str, Any]]:
        text = path.read_text(encoding="utf-8")
        return [{
            "text": text,
            "locator": {"type": "line_range", "start": 1, "end": len(text.splitlines())},
        }]


class ParserRouter:
    def __init__(self) -> None:
        self.parsers: dict[str, DocumentParser] = {
            ".pdf": PyMuPDFParser(),
            ".md": PlainTextParser(),
            ".txt": PlainTextParser(),
        }

    def parse(self, path: Path) -> tuple[str, list[dict[str, Any]]]:
        parser = self.parsers[path.suffix.lower()]
        return parser.name, parser.parse(path)


class LocalLibraryProvider:
    name = "local_library"

    def __init__(
        self, settings: LocalLibraryConfig, project_root: Path, router: ParserRouter
    ) -> None:
        self.settings = settings
        self.project_root = project_root.resolve()
        self.router = router

    def fetch(self, cursor: Mapping[str, object]) -> SourceBatch:
        del cursor
        records = [self._record(path) for path in self._files()]
        return SourceBatch(
            records=records,
            next_cursor={"content_hashes": {
                record.external_id: record.payload["sha256"] for record in records
            }},
        )

    def _files(self) -> list[Path]:
        files: list[Path] = []
        for configured in self.settings.roots:
            root = configured if configured.is_absolute() else self.project_root / configured
            root = root.resolve()
            if not self.settings.allow_outside_project_root and not root.is_relative_to(self.project_root):
                raise ValueError(f"local library root escapes project: {configured}")
            if not root.is_dir():
                raise ValueError(f"local library root is not a directory: {configured}")
            candidates = root.rglob("*") if self.settings.recursive else root.glob("*")
            for candidate in candidates:
                resolved = candidate.resolve()
                if candidate.is_file() and candidate.suffix.lower() in self.settings.allowed_extensions:
                    if not self.settings.allow_outside_project_root and not resolved.is_relative_to(root):
                        raise ValueError(f"local library file escapes root: {candidate}")
                    files.append(resolved)
        return sorted(set(files))

    def _record(self, path: Path) -> SourceRecord:
        content = path.read_bytes()
        digest = sha256(content).hexdigest()
        sidecar = path.with_name(path.name + ".json")
        metadata = PaperMetadata.model_validate(
            json.loads(sidecar.read_text(encoding="utf-8")) if sidecar.is_file() else {}
        )
        version = sha256((digest + metadata.model_dump_json()).encode()).hexdigest()
        parser, sections = self.router.parse(path)
        try:
            external_id = path.relative_to(self.project_root).as_posix()
        except ValueError:
            external_id = path.as_posix()
        return SourceRecord(
            provider=self.name,
            external_id=external_id,
            version=version,
            updated_at=datetime.fromtimestamp(path.stat().st_mtime, timezone.utc),
            payload={
                "title": metadata.title or path.stem,
                "path": external_id,
                "extension": path.suffix.lower(),
                "sha256": digest,
                "parser": parser,
                "sections": sections,
                "metadata": metadata.model_dump(mode="json"),
                "arxiv_id": metadata.arxiv_id,
            },
        )
