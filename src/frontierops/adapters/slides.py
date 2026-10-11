"""Generate a native OpenSlide v2 source deck from an approved briefing."""

import json
import textwrap

from frontierops.application.render import claim_fingerprint, claim_fingerprints
from frontierops.domain.models import BriefingSpec, Evidence, EvidenceClaim


def _js(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _short(value: str, limit: int = 145) -> str:
    return textwrap.shorten(value.replace("\n", " "), width=limit, placeholder="…")


class OpenSlideRenderer:
    target = "slides"

    def __init__(self, visuals: dict[str, dict] | None = None) -> None:
        self.visuals = visuals or {}

    def render(self, briefing: BriefingSpec, evidence: list[Evidence]) -> str:
        by_id = {item.artifact_id: item for item in evidence}
        imports = ["import type { Page, SlideMeta } from '@open-slide/core';"]
        pages = [
            "const Cover: Page = () => <div className=\"fo-slide cover\"><style>{css}</style>"
            f"<h1>{'{' + _js(briefing.title) + '}'}</h1>"
            f"<p>{'{' + _js(_cover_message(briefing)) + '}'}</p>"
            f"<footer>{'{' + _js(_cover_source(briefing)) + '}'}</footer></div>;"
        ]
        names = ["Cover"]
        notes = [f"Introduce the paper and its publication status: {briefing.title}."]
        for number, section in enumerate(briefing.sections, 1):
            figure = self.visuals.get(section.id)
            figure_name = f"figure{number}"
            if figure:
                imports.append(f"import {figure_name} from '../../assets/{figure['uri'].split('/')[-1]}';")
            section_pages, section_names = _paper_pages(number, section, by_id, figure, figure_name)
            pages.extend(section_pages)
            names.extend(section_names)
            notes.extend(_paper_notes(section, bool(figure or section.source_excerpts)))
        metadata = json.dumps({
            "briefing_id": briefing.artifact_id,
            "claim_fingerprints": claim_fingerprints(briefing),
        }, ensure_ascii=False)
        return "\n".join([
            *imports, "", f"export const frontieropsClaims = {metadata};", _CSS,
            *pages, "", ("export const meta: SlideMeta = { "
                         f"title: {_js(briefing.title)}, "
                         f"createdAt: {_js(briefing.created_at.isoformat().replace('+00:00', 'Z'))} }};"),
            f"export const notes = {json.dumps(notes, ensure_ascii=False)};",
            f"export default [{', '.join(names)}] satisfies Page[];", "",
        ])

    @staticmethod
    def project_files() -> dict[str, str]:
        return {
            "package.json": json.dumps({
                "name": "frontierops-briefing", "private": True, "version": "0.0.0",
                "type": "module", "scripts": {"dev": "open-slide dev", "build": "open-slide build",
                                                 "preview": "open-slide preview",
                                                 "sync:skills": "open-slide sync:skills"},
                "dependencies": {"@open-slide/core": "2.0.0", "react": "19.2.8", "react-dom": "19.2.8"},
                "devDependencies": {"@types/react": "19.2.18", "@types/react-dom": "19.2.5"},
            }, indent=2) + "\n",
            "open-slide.config.ts": "import type { OpenSlideConfig } from '@open-slide/core';\n"
                                    "const config: OpenSlideConfig = { build: { showSlideBrowser: false } };\n"
                                    "export default config;\n",
            "tsconfig.json": json.dumps({"compilerOptions": {
                "target": "ES2022", "lib": ["ES2022", "DOM", "DOM.Iterable"], "module": "ESNext",
                "moduleResolution": "bundler", "jsx": "react-jsx", "resolveJsonModule": True,
                "isolatedModules": True, "moduleDetection": "force", "noEmit": True,
                "strict": True, "skipLibCheck": True, "types": ["@open-slide/core/env"],
            }, "include": ["slides/**/*", "open-slide.config.ts"]}, indent=2) + "\n",
        }


def _cover_message(briefing: BriefingSpec) -> str:
    if not briefing.sections:
        return ""
    meta = briefing.sections[0].paper_metadata
    authors = ", ".join(meta.authors[:4]) + (" et al." if len(meta.authors) > 4 else "")
    return "\n".join(value for value in (authors, ", ".join(meta.affiliations),
                                          meta.published_at or "", _publication(meta)) if value)


def _cover_source(briefing: BriefingSpec) -> str:
    if not briefing.sections:
        return ""
    meta = briefing.sections[0].paper_metadata
    return (f"arXiv:{meta.arxiv_id}" if meta.arxiv_id else
            meta.publication_venue or _publication(meta))


def _publication(meta) -> str:
    return {"preprint": "arXiv preprint", "conference": "Conference paper",
            "journal": "Journal article"}.get(meta.publication_status, "Publication status unverified")


def _paper_pages(number, section, evidence, figure, figure_name) -> tuple[list[str], list[str]]:
    claims = section.claims
    if not claims:
        return [], []
    problem = claims[0]
    idea = claims[1] if len(claims) > 1 else None
    method = claims[2] if len(claims) > 2 else None
    novelty = claims[3] if len(claims) > 3 else None
    results = claims[4] if len(claims) > 4 else None
    limits = claims[5] if len(claims) > 5 else None
    significance = claims[6] if len(claims) > 6 else None
    prefix = f"Paper{number}"
    overview = (f"const {prefix}Overview: Page = () => <div className=\"fo-slide overview\"><style>{{css}}</style>"
                f"<h2>Executive summary</h2><div className=\"overview-body\">"
                f"<div><h3>Contribution</h3>{_statement(idea, 'summary-line') if idea else ''}</div>"
                f"<div><h3>Why it matters</h3>{_statement(significance, 'summary-line') if significance else ''}</div></div>"
                f"<footer>{'{' + _js(_source_line(idea, evidence)) + '}'}</footer></div>;")
    context = (f"const {prefix}Context: Page = () => <div className=\"fo-slide context\"><style>{{css}}</style>"
               f"<h2>Research problem</h2>{_statement(problem, 'main')}"
               f"<footer>{'{' + _js(_source_line(problem, evidence)) + '}'}</footer></div>;")
    figure_markup = (
        f'<figure><img src={{{figure_name}}} alt={{{_js(str(figure["label"]) + " from paper")}}} />'
        f'<figcaption>{{{_js(str(figure["label"]) + " · p. " + str(figure["page"]))}}}</figcaption></figure>'
        if figure else _excerpt_markup(section, evidence)
    )
    has_visual = bool(figure or section.source_excerpts)
    method_page = (f"const {prefix}Method: Page = () => <div className=\"fo-slide method\"><style>{{css}}</style>"
                   f"<h2>Proposed system</h2>{figure_markup if has_visual else ''}"
                   f"{_statement(method, 'method-text' if has_visual else 'main') if method and not novelty else ''}"
                   f"<footer>{'{' + _js(_figure_source(figure, section.headline)) + '}'}</footer></div>;")
    mechanism_page = (f"const {prefix}Mechanism: Page = () => <div className=\"fo-slide mechanism\"><style>{{css}}</style>"
                      f"<h2>How the harness works</h2>{_statement(method, 'main') if method else ''}"
                      f"{_statement(novelty, 'main') if novelty else ''}"
                      f"<footer>{'{' + _js(_source_line(novelty, evidence)) + '}'}</footer></div>;")
    result_page = (f"const {prefix}Results: Page = () => <div className=\"fo-slide results\"><style>{{css}}</style>"
                   f"<h2>Evaluation</h2>"
                   f"<div className=\"result-body\">{_statement(results, 'finding') if results else ''}</div>"
                   f"<footer>{'{' + _js(_source_line(results, evidence) if results else section.headline) + '}'}</footer></div>;")
    limits_page = (f"const {prefix}Limits: Page = () => <div className=\"fo-slide limits\"><style>{{css}}</style>"
                   f"<h2>Limits and open questions</h2>{_statement(limits, 'main') if limits else ''}"
                   f"<footer>{'{' + _js(_source_line(limits, evidence) if limits else section.headline) + '}'}</footer></div>;")
    pages = [overview, context]
    names = [prefix + name for name in ("Overview", "Context")]
    if has_visual or not novelty:
        pages.append(method_page)
        names.append(prefix + "Method")
    if novelty:
        pages.append(mechanism_page)
        names.append(prefix + "Mechanism")
    return (pages + [result_page, limits_page], names + [prefix + "Results", prefix + "Limits"])


def _paper_notes(section, has_visual: bool) -> list[str]:
    claims = section.claims
    note = lambda index: claims[index].text if index < len(claims) else ""
    notes = [f"Summarize the contribution and why it matters. {note(1)} {note(6)}",
             f"Explain the gap in earlier work. {note(0)}"]
    if has_visual or len(claims) <= 3:
        notes.append(f"Walk through the source figure or method. {note(2)}")
    if len(claims) > 3:
        notes.append(f"Explain the execution contract and handoffs. {note(3)}")
    return notes + [f"State what was measured and what was not. {note(4)}",
                    f"Separate study limitations from open questions. {note(5)}"]


def _excerpt_markup(section, evidence: dict[str, Evidence]) -> str:
    for excerpt in section.source_excerpts:
        item = evidence.get(excerpt.evidence_id)
        if item:
            page = item.locator.get("page")
            return (f'<blockquote className="source-quote"><mark>{{{_js(_short(excerpt.quote, 500))}}}</mark>'
                    f'<cite>{{{_js("Paper p. " + str(page))}}}</cite></blockquote>')
    return '<p className="no-figure">No verified paper figure or excerpt supplied.</p>'


def _statement(claim: EvidenceClaim | None, class_name: str, display: str | None = None) -> str:
    if claim is None:
        return ""
    return (f'<p className="{class_name}" data-claim-fingerprint="{claim_fingerprint(claim)}">'
            f'{{{_js(_short(display or claim.text, 260))}}}</p>')


def _source_line(claim: EvidenceClaim | None, evidence: dict[str, Evidence]) -> str:
    if claim is None:
        return ""
    pages = [f"p. {evidence[ref].locator['page']}" for ref in claim.evidence_ids
             if ref in evidence and evidence[ref].locator.get("page")]
    return "Source paper " + ", ".join(dict.fromkeys(pages)) if pages else "Source: see briefing evidence"


def _figure_source(figure: dict | None, paper: str) -> str:
    return f"{paper} · {figure['label']} · p. {figure['page']}" if figure else paper


_CSS = """const css = `
.fo-slide{width:100%;height:100%;box-sizing:border-box;padding:90px 118px 80px;background:#fff;color:#111;font-family:Arial,sans-serif;position:relative;overflow:hidden}
.fo-slide h1{font:700 98px/1.07 Georgia,serif;max-width:1600px;margin:0 0 44px}.fo-slide h2{font:700 66px/1.1 Georgia,serif;margin:0 0 48px;max-width:1640px}
.fo-slide p{margin:0}.fo-slide footer{position:absolute;bottom:45px;left:118px;right:118px;border-top:1px solid #aaa;padding-top:12px;font-size:20px;color:#555}
.cover{display:flex;flex-direction:column;justify-content:center}.cover p{font-size:31px;white-space:pre-line;line-height:1.45;max-width:1450px}
.overview-body{display:grid;grid-template-columns:1fr 1fr;gap:70px;margin-top:90px}.overview h3{font-size:27px;margin:0 0 15px;border-top:2px solid #111;padding-top:17px}.summary-line{font:36px/1.38 Georgia,serif}
.context .main,.method .main,.limits .main{font:47px/1.35 Georgia,serif;max-width:1450px;margin-top:100px}.method{padding-top:65px}.method h2{margin-bottom:20px}.method figure{margin:0;max-width:1670px}.method img{display:block;width:100%;max-height:760px;object-fit:contain}.method figcaption{font-size:20px;color:#555;margin-top:7px}.method-text{font:27px/1.3 Arial,sans-serif;margin-top:18px}
.mechanism .main{font:40px/1.35 Georgia,serif;max-width:1480px;margin-top:52px}.source-quote{font:36px/1.4 Georgia,serif;margin:50px 0;max-width:1500px}.source-quote mark{background:#ffed9c}.source-quote cite{display:block;font:21px Arial,sans-serif;margin-top:20px}
.no-figure{font-size:30px;color:#555}.result-body{font:48px/1.35 Georgia,serif;max-width:1470px;margin-top:90px}
`;"""
