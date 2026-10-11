"""Best-effort, source-linked figure crops from local PDF evidence."""

from pathlib import Path
import re

import pymupdf

from frontierops.domain.models import BriefingSpec, Evidence


def extract_paper_visuals(
    briefing: BriefingSpec, evidence: list[Evidence], render_dir: Path,
    max_pages: int = 20,
) -> dict[str, dict[str, str | int]]:
    """Map a section to a verifiable figure; never invent a visual on failure."""
    by_id = {item.artifact_id: item for item in evidence}
    visuals: dict[str, dict[str, str | int]] = {}
    for section in briefing.sections:
        sources = dict.fromkeys(
            by_id[ref].source_uri
            for claim in section.claims for ref in claim.evidence_ids
            if ref in by_id and by_id[ref].source_uri.startswith("assets/")
        )
        for source_uri in sources:
            source = (render_dir / source_uri).resolve()
            if (not source.is_relative_to(render_dir.resolve())
                    or source.suffix.lower() != ".pdf" or not source.is_file()):
                continue
            try:
                visual = _first_figure(source, source_uri, render_dir, max_pages)
            except (pymupdf.FileDataError, ValueError, RuntimeError):
                continue
            if visual:
                visuals[section.id] = visual
                break
    return visuals


def _first_figure(
    source: Path, source_uri: str, render_dir: Path, max_pages: int
) -> dict[str, str | int] | None:
    with pymupdf.open(source) as document:
        for number in range(min(len(document), max_pages)):
            page = document[number]
            caption_line = None
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    content = "".join(span["text"] for span in line["spans"]).strip()
                    match = re.match(r"(?:Figure|Fig\.)\s+([1-9]\d*)\s*[:.]\s*(.*)", content)
                    if match:
                        caption_line = (match, pymupdf.Rect(line["bbox"]))
                        break
                if caption_line:
                    break
            if not caption_line:
                continue
            match, caption = caption_line
            crop = pymupdf.Rect(
                page.rect.x0 + 60, _figure_top(page, caption.y0),
                page.rect.x1 - 60, caption.y0 - 3,
            )
            if crop.height < 35 or crop.width < 100:
                continue
            target = render_dir / "visuals" / f"{source.stem}-p{number + 1}-fig-{match.group(1)}.png"
            target.parent.mkdir(parents=True, exist_ok=True)
            page.get_pixmap(matrix=pymupdf.Matrix(2, 2), clip=crop, alpha=False).save(target)
            return {
                "uri": target.relative_to(render_dir).as_posix(),
                "source_uri": source_uri, "page": number + 1,
                "label": f"Figure {match.group(1)}", "caption": match.group(2)[:220],
            }
    return None


def _figure_top(page: pymupdf.Page, caption_y: float) -> float:
    """Include the whole vector/image figure above a caption, not just its last 112 pt."""
    lower_bound = page.rect.y0 + 55  # Ignore running headers and their ornaments.
    boxes = [item["rect"] for item in page.get_drawings()]
    boxes.extend(
        pymupdf.Rect(block["bbox"])
        for block in page.get_text("dict")["blocks"] if block.get("type") == 1
    )
    tops = [box.y0 for box in boxes
            if lower_bound <= box.y0 < caption_y and box.y1 <= caption_y]
    if tops:
        return max(lower_bound, min(tops) - 12)
    return max(page.rect.y0 + 35, caption_y - 112)
