"""Evidence-led, interactive paper reading interface."""

from html import escape
import json

from frontierops.application.render import claim_fingerprint, claim_fingerprints
from frontierops.domain.models import BriefingSpec, Evidence


LABELS_ZH = ["研究問題", "核心想法", "方法", "新穎性", "實驗結果", "限制", "研究意義"]
LABELS_EN = ["Problem", "Core idea", "Method", "Novelty", "Results", "Limitations", "Why it matters"]


class StaticHtmlRenderer:
    target = "html"

    def __init__(self, visuals: dict[str, dict] | None = None) -> None:
        self.visuals = visuals or {}

    def render(self, briefing: BriefingSpec, evidence: list[Evidence]) -> str:
        by_id = {item.artifact_id: item for item in evidence}
        zh = briefing.language.lower().startswith("zh")
        labels = LABELS_ZH if zh else LABELS_EN
        navigation = "".join(
            f'<a href="#{escape(section.id, quote=True)}">{escape(section.headline)}</a>'
            for section in briefing.sections
        )
        sections = "".join(
            _section(section, by_id, labels, self.visuals.get(section.id), zh)
            for section in briefing.sections
        )
        metadata = json.dumps({
            "briefing_id": briefing.artifact_id,
            "claim_fingerprints": claim_fingerprints(briefing),
        }, ensure_ascii=False).replace("</", "<\\/")
        intro = "選一個問題，先看結論，再回到論文查證。" if zh else "Choose a question, read the answer, then inspect its source."
        return f"""<!doctype html>
<html lang="{escape(briefing.language, quote=True)}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(briefing.title)}</title>
<style>
:root{{--paper:#fbfaf7;--ink:#222723;--muted:#606963;--rule:#cdd3cc;--accent:#216b59;--focus:#e7f1ec}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--paper);color:var(--ink);font:18px/1.5 system-ui,sans-serif}}
a{{color:var(--accent);text-underline-offset:3px}}button{{font:inherit;cursor:pointer}}.shell{{max-width:1540px;margin:auto;padding:0 42px}}
.masthead{{padding:56px 0 30px;border-bottom:2px solid var(--ink)}}h1{{max-width:1100px;margin:0;font:600 clamp(38px,5vw,72px)/1.08 Georgia,serif}}
.intro{{color:var(--muted);margin:18px 0 0}}.paper-nav{{display:flex;gap:28px;overflow-x:auto;padding:18px 0;border-bottom:1px solid var(--rule)}}
.paper{{padding:56px 0 90px;border-bottom:1px solid var(--rule)}}.paper h2{{font:600 clamp(32px,3.5vw,52px)/1.15 Georgia,serif;margin:0 0 32px}}
.reader{{display:grid;grid-template-columns:235px minmax(0,1fr);column-gap:42px;row-gap:28px;align-items:start}}
.outline{{grid-row:1/span 2;position:sticky;top:24px;border-top:2px solid var(--ink)}}.step{{display:block;width:100%;text-align:left;border:0;border-bottom:1px solid var(--rule);background:transparent;padding:16px 12px;color:var(--muted)}}
.step[aria-selected="true"]{{background:var(--focus);color:var(--ink);font-weight:700;border-left:4px solid var(--accent);padding-left:8px}}
.explanation{{grid-column:2;grid-row:2;min-height:280px}}.answer{{display:none}}.answer.active{{display:block}}.answer h3{{margin:0 0 18px;font-size:17px;color:var(--accent)}}
.answer p{{margin:0 0 34px;font:400 clamp(23px,2vw,32px)/1.38 Georgia,serif}}.evidence-list{{border-top:1px solid var(--rule);padding-top:16px}}
details{{border-bottom:1px solid var(--rule);padding:10px 0}}summary{{cursor:pointer;color:var(--accent)}}blockquote{{margin:14px 0;padding-left:16px;border-left:3px solid var(--rule);font-size:15px;color:var(--muted);white-space:pre-wrap}}
.visual{{grid-column:2;grid-row:1;margin:0}}.visual img{{display:block;width:100%;height:auto;max-height:520px;object-fit:contain;background:white;border:1px solid var(--rule);cursor:zoom-in}}
figcaption{{margin-top:12px;font-size:14px;color:var(--muted)}}.source-empty{{padding:22px;border-top:1px solid var(--rule);font-size:16px;color:var(--muted)}}
dialog{{max-width:min(94vw,1500px);max-height:94vh;border:0;padding:20px;box-shadow:0 20px 80px #0005}}dialog::backdrop{{background:#111b}}
dialog img{{display:block;max-width:100%;max-height:80vh}}dialog button{{float:right;border:0;background:white;padding:10px}}
@media(max-width:680px){{.shell{{padding:0 20px}}.reader{{display:block}}.outline{{display:grid;position:static;grid-template-columns:repeat(2,1fr);margin-bottom:28px}}.visual{{margin-bottom:28px}}}}
</style></head><body>
<div class="shell"><header class="masthead"><h1>{escape(briefing.title)}</h1><p class="intro">{intro}</p></header>
<nav class="paper-nav" aria-label="Papers">{navigation}</nav><main>{sections}</main></div>
<dialog id="figure-dialog"><button type="button" id="close-figure" aria-label="Close">✕</button><img alt=""></dialog>
<script id="frontierops-claims" type="application/json">{metadata}</script>
<script>
document.querySelectorAll('.paper').forEach(paper=>{{
  const steps=[...paper.querySelectorAll('.step')], answers=[...paper.querySelectorAll('.answer')];
  const choose=i=>{{steps.forEach((step,n)=>{{step.setAttribute('aria-selected',String(n===i));step.tabIndex=n===i?0:-1}});
    answers.forEach((answer,n)=>answer.classList.toggle('active',n===i));}};
  steps.forEach((step,i)=>{{step.addEventListener('click',()=>choose(i));step.addEventListener('keydown',e=>{{
    if(e.key==='ArrowDown'||e.key==='ArrowRight'){{e.preventDefault();const n=(i+1)%steps.length;choose(n);steps[n].focus()}}
    if(e.key==='ArrowUp'||e.key==='ArrowLeft'){{e.preventDefault();const n=(i+steps.length-1)%steps.length;choose(n);steps[n].focus()}}
  }})}});if(steps.length)choose(0);
}});
const dialog=document.getElementById('figure-dialog');
document.querySelectorAll('.visual img').forEach(img=>img.addEventListener('click',()=>{{dialog.querySelector('img').src=img.src;dialog.querySelector('img').alt=img.alt;dialog.showModal()}}));
document.getElementById('close-figure').addEventListener('click',()=>dialog.close());
</script></body></html>"""


def _section(section, evidence: dict[str, Evidence], labels: list[str], visual: dict | None, zh: bool) -> str:
    steps = "".join(
        f'<button class="step" role="tab" aria-controls="{escape(section.id)}-answer-{i}" type="button">{escape(labels[i] if i < len(labels) else "Claim")}</button>'
        for i in range(len(section.claims))
    )
    answers = "".join(
        _answer(section.id, i, claim, evidence, labels, zh) for i, claim in enumerate(section.claims)
    )
    if visual:
        source = f'{escape(str(visual["source_uri"]), quote=True)}#page={visual["page"]}'
        figure = (f'<figure class="visual"><img src="{escape(str(visual["uri"]), quote=True)}" '
                  f'alt="{escape(str(visual["label"]), quote=True)} from source paper">'
                  f'<figcaption>{escape(str(visual["label"]))} · p. {visual["page"]} '
                  f'{escape(str(visual["caption"]))}</figcaption>'
                  f'<a href="{source}" target="_blank" rel="noopener">{"查看論文原頁" if zh else "Open source page"}</a></figure>')
    else:
        figure = '<div class="source-empty">' + ("此論文尚無可驗證的原圖；請從左側引用回到原文。" if zh else "No verified figure available. Use the citations to inspect the source.") + '</div>'
    return (f'<section class="paper" id="{escape(section.id, quote=True)}"><h2>{escape(section.headline)}</h2>'
            f'<div class="reader"><nav class="outline" role="tablist" aria-label="Paper questions">{steps}</nav>'
            f'{figure}<div class="explanation">{answers}</div></div></section>')


def _answer(section_id: str, index: int, claim, evidence: dict[str, Evidence], labels: list[str], zh: bool) -> str:
    citations = "".join(_citation(evidence[ref], zh) for ref in claim.evidence_ids if ref in evidence)
    if not citations:
        citations = '<p>' + ("這是作者的詮釋，尚無直接來源。" if zh else "Interpretation; no direct source supplied.") + '</p>'
    qualifier = ' <small>（詮釋）</small>' if zh and claim.kind == "interpretation" else (' <small>(interpretation)</small>' if claim.kind == "interpretation" else "")
    return (f'<article class="answer" id="{escape(section_id, quote=True)}-answer-{index}" role="tabpanel" '
            f'data-claim-fingerprint="{claim_fingerprint(claim)}"><h3>{escape(labels[index] if index < len(labels) else "Claim")}{qualifier}</h3>'
            f'<p>{escape(claim.text)}</p><div class="evidence-list">{citations}</div></article>')


def _citation(item: Evidence, zh: bool) -> str:
    page = item.locator.get("page")
    uri = item.source_uri + (f"#page={page}" if page and item.source_uri.lower().endswith(".pdf") else "")
    place = f"p. {page}" if page else item.locator.get("type", "source")
    excerpt = item.content[:650] + ("…" if len(item.content) > 650 else "")
    return (f'<details><summary>{"查核證據" if zh else "Inspect evidence"} · {escape(str(place))}</summary>'
            f'<blockquote>{escape(excerpt)}</blockquote><a href="{escape(uri, quote=True)}" target="_blank" rel="noopener">'
            f'{"開啟原始資料" if zh else "Open original source"}</a></details>')
