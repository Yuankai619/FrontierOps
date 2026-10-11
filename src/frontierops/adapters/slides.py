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
            "<footer>FrontierOps · source-grounded briefing</footer></div>;"
        ]
        names = ["Cover"]
        notes = [briefing.title]
        for number, section in enumerate(briefing.sections, 1):
            figure = self.visuals.get(section.id)
            figure_name = f"figure{number}"
            if figure:
                imports.append(f"import {figure_name} from '../../assets/{figure['uri'].split('/')[-1]}';")
            section_pages, section_names = _paper_pages(number, section, by_id, figure, figure_name)
            pages.extend(section_pages)
            names.extend(section_names)
            notes.extend([section.narration_script] * len(section_pages))
        metadata = json.dumps({
            "briefing_id": briefing.artifact_id,
            "claim_fingerprints": claim_fingerprints(briefing),
        }, ensure_ascii=False)
        return "\n".join([
            *imports, "", f"export const frontieropsClaims = {metadata};", _CSS,
            *pages, "", f"export const meta: SlideMeta = {{ title: {_js(briefing.title)} }};",
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
    if briefing.sections and len(briefing.sections[0].claims) > 1:
        return _short(briefing.sections[0].claims[1].text, 210)
    return "An evidence-grounded explanation of new research"


def _paper_pages(number, section, evidence, figure, figure_name) -> tuple[list[str], list[str]]:
    claims = section.claims
    if not claims:
        return [], []
    problem = claims[0]
    significance = claims[6] if len(claims) > 6 else None
    method = claims[2] if len(claims) > 2 else None
    idea = claims[1] if len(claims) > 1 else None
    novelty = claims[3] if len(claims) > 3 else None
    results = claims[4] if len(claims) > 4 else None
    limits = claims[5] if len(claims) > 5 else None
    prefix = f"Paper{number}"
    source = _source_line(problem, evidence)
    problem_title = _short(problem.text.split(":", 1)[0], 125)
    problem_detail = problem.text.split(":", 1)[1].strip() if ":" in problem.text else problem.text
    context = (f"const {prefix}Context: Page = () => <div className=\"fo-slide context\"><style>{{css}}</style>"
               f"<h2>{'{' + _js(problem_title) + '}'}</h2>"
               f"{_statement(problem, 'question', problem_detail)}"
               f"{_statement(significance, 'meaning') if significance else ''}"
               f"<footer>{'{' + _js(source) + '}'}</footer></div>;")
    figure_markup = (
        f'<figure><img src={{{figure_name}}} alt={{{_js(str(figure["label"]) + " from paper")}}} />'
        f'<figcaption>{{{_js(str(figure["label"]) + " · p. " + str(figure["page"]))}}}</figcaption></figure>'
        if figure else '<p className="no-figure">No source figure available; inspect the cited paper.</p>'
    )
    method_title = _short(idea.text if idea else method.text if method else section.headline)
    method_page = (f"const {prefix}Method: Page = () => <div className=\"fo-slide method\"><style>{{css}}</style>"
                   f"<h2{(' data-claim-fingerprint=\"' + claim_fingerprint(idea) + '\"') if idea else ''}>{'{' + _js(method_title) + '}'}</h2>{figure_markup}"
                   f"<div className=\"method-points\">"
                   f"{_statement(method, 'method-text') if method else ''}"
                   f"{_statement(novelty, 'novelty') if novelty else ''}</div>"
                   f"<footer>{'{' + _js(_figure_source(figure, section.headline)) + '}'}</footer></div>;")
    result_title = _short(results.text if results else section.headline)
    result_page = (f"const {prefix}Results: Page = () => <div className=\"fo-slide results\"><style>{{css}}</style>"
                   f"<h2>{'{' + _js(result_title) + '}'}</h2>"
                   f"<div className=\"result-body\">{_statement(results, 'finding') if results else ''}"
                   f"{_statement(limits, 'limit') if limits else ''}</div>"
                   f"<footer>{'{' + _js(_source_line(results, evidence) if results else section.headline) + '}'}</footer></div>;")
    return [context, method_page, result_page], [prefix + "Context", prefix + "Method", prefix + "Results"]


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
.fo-slide{width:100%;height:100%;box-sizing:border-box;padding:86px 112px 74px;background:#f9f8f4;color:#202722;font-family:Arial,sans-serif;position:relative;overflow:hidden}
.fo-slide h1{font:700 104px/1.08 Georgia,serif;max-width:1540px;margin:80px 0 36px}.fo-slide h2{font:700 62px/1.12 Georgia,serif;margin:0 0 32px;max-width:1670px}
.fo-slide p{margin:0}.fo-slide footer{position:absolute;bottom:48px;left:112px;font-size:20px;color:#5c655d}
.cover{display:flex;flex-direction:column;justify-content:center}.cover p{font-size:38px;line-height:1.3;max-width:1260px;border-top:3px solid #276b59;padding-top:28px}
.context .question{font:40px/1.42 Georgia,serif;max-width:1450px;margin:45px 0 65px}.context .meaning{font-size:32px;color:#276b59;max-width:1300px;border-left:5px solid #276b59;padding-left:26px}
.method figure{margin:0;max-width:1690px}.method img{display:block;width:100%;max-height:470px;object-fit:contain;background:#fff}.method figcaption{font-size:21px;color:#5c655d;margin-top:8px}
.method-points{display:grid;grid-template-columns:1fr 1fr;column-gap:55px;row-gap:12px;margin-top:27px;font-size:27px;line-height:1.25}.method-points .novelty{grid-column:1/-1;color:#276b59}
.no-figure{font-size:32px;padding:80px;border:2px solid #b6beb6}.result-body{display:grid;grid-template-columns:1.3fr 1fr;gap:75px;margin-top:65px;font:37px/1.42 Georgia,serif}
.result-body .finding{border-top:5px solid #276b59;padding-top:25px}.result-body .limit{border-top:2px solid #77877e;padding-top:28px;color:#4e5b52}
`;"""
