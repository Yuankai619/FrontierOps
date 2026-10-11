"""Zero-dependency 1920x1080 HTML slide deck adapter."""

from html import escape
import json

from frontierops.application.render import claim_fingerprint, claim_fingerprints
from frontierops.domain.models import BriefingSpec, Evidence


class StaticSlideRenderer:
    target = "slides"

    def render(self, briefing: BriefingSpec, evidence: list[Evidence]) -> str:
        evidence_by_id = {item.artifact_id: item for item in evidence}
        zh = briefing.language.lower().startswith("zh")
        pages = [_cover(briefing, zh)]
        for section in briefing.sections:
            pages.extend(_paper_pages(section, evidence_by_id, zh))
        metadata = json.dumps({
            "briefing_id": briefing.artifact_id,
            "claim_fingerprints": claim_fingerprints(briefing),
        }, ensure_ascii=False).replace("</", "<\\/")
        numbered = "".join(
            page.replace("</section>", f'<footer>{index} / {len(pages)}</footer></section>')
            for index, page in enumerate(pages, 1)
        )
        return f"""<!doctype html>
<html lang="{escape(briefing.language)}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(briefing.title)} slides</title>
<style>
:root{{--ink:#f4f1e8;--muted:#a6aea8;--accent:#e36f55;--paper:#17211b}}
*{{box-sizing:border-box}} body{{margin:0;background:#090d0b;color:var(--ink);font-family:Arial,sans-serif}}
.slide{{position:relative;width:min(100vw,177.78vh);aspect-ratio:16/9;margin:0 auto 4vh;padding:6% 7%;overflow:hidden;background:var(--paper);break-after:page}}
.cover{{display:flex;flex-direction:column;justify-content:center}} .kicker{{color:var(--accent);font-size:28px;font-weight:700;letter-spacing:.08em;text-transform:uppercase}}
h1{{max-width:1500px;margin:24px 0;font:700 120px/1.02 Georgia,serif}} h2{{margin:0 0 54px;font:700 76px/1.08 Georgia,serif}}
.headline{{color:var(--muted);font-size:28px;margin-bottom:42px}} .grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:54px 72px}}
.claim.wide{{grid-column:1/-1}} h3{{margin:0 0 12px;color:var(--accent);font-size:25px;text-transform:uppercase;letter-spacing:.06em}}
.claim p{{margin:0;font-size:31px;line-height:1.3}} .source{{display:inline-block;margin:14px 12px 0 0;color:var(--muted);font-size:17px}}
.interpretation{{color:var(--muted);font-style:italic}} footer{{position:absolute;right:7%;bottom:4%;color:var(--muted);font-size:18px}}
@media print{{@page{{size:16in 9in;margin:0}}body{{background:none}}.slide{{width:16in;height:9in;margin:0}}}}
</style></head><body>{numbered}
<script id="frontierops-claims" type="application/json">{metadata}</script>
<script>let p=0;const s=[...document.querySelectorAll('.slide')];addEventListener('keydown',e=>{{if(e.key==='ArrowRight'||e.key===' ')p=Math.min(p+1,s.length-1);if(e.key==='ArrowLeft')p=Math.max(p-1,0);s[p].scrollIntoView({{behavior:'smooth'}})}});</script>
</body></html>
"""


def _cover(briefing: BriefingSpec, zh: bool) -> str:
    kicker = "研究前沿簡報" if zh else "Research frontier briefing"
    subtitle = "核准內容與證據可追溯" if zh else "Approved content with traceable evidence"
    return (f'<section class="slide cover"><p class="kicker">{kicker}</p>'
            f'<h1>{escape(briefing.title)}</h1><p class="headline">'
            f'{briefing.target_duration_seconds} seconds · {subtitle}</p></section>')


def _paper_pages(section, evidence: dict[str, Evidence], zh: bool) -> list[str]:
    labels = (["研究問題", "核心想法", "方法", "新穎性", "實驗", "限制", "研究意義"]
              if zh else ["Problem", "Core idea", "Method", "Novelty", "Experiments",
                          "Limitations", "Why it matters"])
    groups = [(0, 1, 6), (2, 3), tuple([4, 5, *range(7, len(section.claims))])]
    page_titles = (["研究概覽", "方法與貢獻", "結果與限制"] if zh else
                   ["Research overview", "Method and contribution", "Results and limitations"])
    pages = []
    for title, indices in zip(page_titles, groups):
        claims = [(index, section.claims[index]) for index in indices
                  if index < len(section.claims)]
        if not claims:
            continue
        blocks = "".join(_claim(labels[index] if index < len(labels) else "Claim",
                                claim, evidence, len(claims) == 1)
                         for index, claim in claims)
        pages.append(f'<section class="slide"><p class="headline">{escape(section.headline)}</p>'
                     f'<h2>{title}</h2><div class="grid">{blocks}</div></section>')
    return pages


def _claim(label: str, claim, evidence: dict[str, Evidence], wide: bool) -> str:
    links = "".join(
        f'<a class="source" href="{escape(evidence[item].source_uri, quote=True)}">'
        f'[{escape(_locator(evidence[item]))}]</a>' for item in claim.evidence_ids
    )
    qualifier = '<span class="interpretation">interpretation</span>' if claim.kind == "interpretation" else ""
    return (f'<div class="claim{" wide" if wide else ""}" data-claim-fingerprint="{claim_fingerprint(claim)}">'
            f'<h3>{label}</h3><p>{escape(claim.text)}</p>{qualifier}{links}</div>')


def _locator(evidence: Evidence) -> str:
    return f"p. {evidence.locator['page']}" if evidence.locator.get("page") else "source"
