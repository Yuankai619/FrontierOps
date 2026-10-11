"""Materialize local Evidence sources beside portable render outputs."""

from hashlib import sha256
from pathlib import Path
import shutil
from urllib.parse import urlparse

from frontierops.domain.models import Evidence


def materialize_local_evidence(
    evidence: list[Evidence], config_dir: Path, render_dir: Path
) -> tuple[list[Evidence], list[dict[str, object]]]:
    resolved: list[Evidence] = []
    assets_by_uri: dict[str, dict[str, object]] = {}
    for item in evidence:
        parsed = urlparse(item.source_uri)
        if parsed.scheme in {"http", "https"}:
            resolved.append(item)
            continue
        if item.producer != "rank:fulltext":
            resolved.append(item)
            continue
        source = Path(parsed.path) if parsed.scheme == "file" else Path(item.source_uri)
        source = source if source.is_absolute() else config_dir / source
        source = source.resolve()
        if not source.is_file():
            resolved.append(item)
            continue
        digest = sha256(source.read_bytes()).hexdigest()
        name = f"{digest[:12]}-{source.name}"
        target = render_dir / "assets" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        uri = f"assets/{name}"
        resolved.append(item.model_copy(update={"source_uri": uri}))
        asset = assets_by_uri.setdefault(uri, {
            "evidence_ids": [], "source": str(source), "uri": uri, "sha256": digest,
        })
        evidence_ids = asset["evidence_ids"]
        assert isinstance(evidence_ids, list)
        evidence_ids.append(item.artifact_id)
    return resolved, list(assets_by_uri.values())
