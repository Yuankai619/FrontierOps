"""Self-contained, accessible HTML briefing renderer."""

from html import escape
import json

from frontierops.application.render import claim_fingerprints
from frontierops.domain.models import BriefingSpec, Evidence, EvidenceClaim


class StaticHtmlRenderer:
    target = "html"

    def render(self, briefing: BriefingSpec, evidence: list[Evidence]) -> str:
        evidence_by_id = {item.artifact_id: item for item in evidence}
        navigation = "".join(
            f'<a href="#{escape(section.id)}">{escape(section.headline)}</a>'
            for section in briefing.sections
        )
        sections = "".join(
            _section(section, evidence_by_id, briefing.language) for section in briefing.sections
        )
        zh = briefing.language.lower().startswith("zh")
        lede = "具證據連結的研究簡報" if zh else "Evidence-linked research briefing"
        metadata = json.dumps({
            "briefing_id": briefing.artifact_id,
            "claim_fingerprints": claim_fingerprints(briefing),
        }, ensure_ascii=False).replace("</", "<\\/")
        return f"""<!doctype html>
<html lang="{escape(briefing.language)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(briefing.title)}</title>
<style>
:root{{--ink:#17211b;--muted:#657168;--paper:#f4f1e8;--accent:#9f3d2d;--line:#d8d2c4}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--paper);color:var(--ink);font:18px/1.65 system-ui,sans-serif}}
header,main{{width:min(1080px,calc(100% - 40px));margin:auto}} header{{padding:72px 0 36px;border-bottom:1px solid var(--line)}}
h1{{font:700 clamp(42px,7vw,76px)/1.05 Georgia,serif;margin:0 0 20px}} .lede{{color:var(--muted)}}
nav{{display:flex;gap:18px;overflow:auto;padding:20px 0}} a{{color:var(--accent)}} article{{padding:64px 0;border-bottom:1px solid var(--line)}}
h2{{font:700 clamp(30px,4vw,48px)/1.15 Georgia,serif;margin:0 0 8px}} .duration{{color:var(--muted)}}
dl{{display:grid;grid-template-columns:150px 1fr;gap:18px 34px;margin-top:36px}} dt{{font-weight:700;color:var(--accent)}} dd{{margin:0}}
.evidence{{font-size:15px;margin-left:8px;white-space:nowrap}} @media(max-width:700px){{dl{{grid-template-columns:1fr;gap:6px}}dd{{margin-bottom:20px}}}}
</style>
</head>
<body>
<header><h1>{escape(briefing.title)}</h1><p class="lede">{briefing.target_duration_seconds} seconds · {lede}</p><nav>{navigation}</nav></header>
<main>{sections}</main>
<script id="frontierops-claims" type="application/json">{metadata}</script>
</body></html>
"""


def _section(section, evidence: dict[str, Evidence], language: str) -> str:
    labels = (["研究問題", "核心想法", "方法", "新穎性", "實驗",
               "限制", "研究意義"] if language.lower().startswith("zh") else
              ["Problem", "Core idea", "Method", "Novelty", "Experiments",
               "Limitations", "Why it matters"])
    rows = "".join(
        f"<dt>{labels[index] if index < len(labels) else 'Claim'}</dt>"
        f"<dd>{_claim(claim, evidence)}</dd>"
        for index, claim in enumerate(section.claims)
    )
    return (
        f'<article id="{escape(section.id)}"><h2>{escape(section.headline)}</h2>'
        f'<p class="duration">{section.duration_seconds} seconds</p><dl>{rows}</dl></article>'
    )


def _claim(claim: EvidenceClaim, evidence: dict[str, Evidence]) -> str:
    links = []
    for evidence_id in claim.evidence_ids:
        item = evidence[evidence_id]
        locator = item.locator
        place = f"page {locator.get('page')}" if locator.get("page") else locator.get("type", "source")
        links.append(
            f'<a class="evidence" href="{escape(item.source_uri, quote=True)}">[{escape(str(place))}]</a>'
        )
    qualifier = " <em>(interpretation)</em>" if claim.kind == "interpretation" else ""
    return escape(claim.text) + qualifier + "".join(links)
