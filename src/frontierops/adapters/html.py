"""Academic paper reader built from an approved, evidence-linked briefing."""

from html import escape
import json

from frontierops.application.render import claim_fingerprint, claim_fingerprints
from frontierops.domain.models import BriefingSpec, Evidence, PaperMetadata


LABELS_ZH = ["問題", "主要貢獻", "方法", "與既有工作的差異", "實驗", "限制", "研究意義"]
LABELS_EN = ["Problem", "Contribution", "Method", "Difference", "Evaluation", "Limitations", "Implications"]
SUMMARY_ZH = ["問題", "做法", "證據", "待確認"]
SUMMARY_EN = ["Problem", "Approach", "Evidence", "Open question"]


class StaticHtmlRenderer:
    target = "html"

    def __init__(self, visuals: dict[str, dict] | None = None) -> None:
        self.visuals = visuals or {}

    def render(self, briefing: BriefingSpec, evidence: list[Evidence]) -> str:
        by_id = {item.artifact_id: item for item in evidence}
        zh = briefing.language.lower().startswith("zh")
        labels = LABELS_ZH if zh else LABELS_EN
        sections = "".join(_section(item, by_id, labels, self.visuals.get(item.id), zh)
                           for item in briefing.sections)
        metadata = json.dumps({"briefing_id": briefing.artifact_id,
                               "claim_fingerprints": claim_fingerprints(briefing)},
                              ensure_ascii=False).replace("</", "<\\/")
        return f'''<!doctype html><html lang="{escape(briefing.language, quote=True)}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(briefing.title)}</title>
<style>:root{{--ink:#161616;--muted:#555;--rule:#c6c6c6;--paper:#fff}}*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--paper);color:var(--ink);font:17px/1.6 system-ui,sans-serif}}
.shell{{max-width:1370px;margin:auto;padding:0 48px}}a{{color:inherit;text-underline-offset:3px}}button{{font:inherit;cursor:pointer}}h1,h2{{font-family:Georgia,serif;line-height:1.14}}
.masthead{{padding:56px 0 35px;border-bottom:2px solid var(--ink)}}.masthead h1{{font-size:clamp(40px,5vw,67px);max-width:1120px;margin:0}}.masthead p{{margin:14px 0 0;color:var(--muted)}}
.paper{{padding:45px 0 95px;border-bottom:1px solid var(--rule)}}.paper-title{{font-size:36px;margin:0 0 18px}}.bib{{border-top:1px solid var(--rule);padding-top:14px;color:var(--muted);font-size:15px}}
.bib span{{margin-right:16px}}.bib a{{color:var(--ink)}}.authors{{margin:9px 0 0}}.authors summary{{cursor:pointer}}.summary{{margin:45px 0 55px;border-top:2px solid var(--ink)}}.summary h3{{font:700 30px Georgia,serif;margin:20px 0}}
.summary dl{{margin:0;display:grid;grid-template-columns:1fr 1fr;gap:0 42px}}.summary dl div{{padding:17px 0;border-top:1px solid var(--rule)}}.summary dt{{font-weight:700;font-size:14px}}.summary dd{{margin:5px 0 0;max-width:600px}}
.reader{{display:grid;grid-template-columns:220px minmax(0,1fr);gap:35px}}.outline{{position:sticky;top:16px;align-self:start;border-top:2px solid var(--ink)}}.step{{display:block;width:100%;text-align:left;border:0;border-bottom:1px solid var(--rule);background:#fff;padding:12px 8px}}
.step[aria-selected=true]{{font-weight:700;border-left:4px solid var(--ink);padding-left:4px;background:#f2f2f2}}.content{{min-width:0}}.visual{{margin:0 0 36px}}.visual img{{display:block;width:100%;max-height:590px;object-fit:contain;background:#fff;cursor:zoom-in}}
figcaption{{font-size:14px;color:var(--muted);margin-top:7px}}.excerpt{{margin:0 0 35px;border-left:3px solid var(--ink);padding:12px 20px;background:#f4f4f4}}.excerpt mark{{background:#ffed9c;box-decoration-break:clone}}
.answer{{display:none;max-width:800px}}.answer.active{{display:block}}.answer h3{{font:700 29px Georgia,serif;margin:0 0 17px}}.answer p{{font-size:22px;line-height:1.45;margin:0 0 25px}}
.evidence-list{{border-top:1px solid var(--rule)}}details.source{{padding:13px 0;border-bottom:1px solid var(--rule)}}details.source summary{{font-size:15px;cursor:pointer}}
blockquote{{margin:14px 0;padding-left:16px;border-left:2px solid #888;font:15px/1.5 system-ui;white-space:pre-wrap;color:var(--muted)}}.evidence-list a{{font-size:14px}}.empty{{color:var(--muted)}}
dialog{{max-width:min(95vw,1500px);max-height:94vh;border:1px solid var(--ink);padding:15px}}dialog::backdrop{{background:#000b}}dialog img{{max-width:100%;max-height:80vh;display:block}}dialog button{{float:right;border:0;background:#fff;padding:8px}}
@media(max-width:730px){{.shell{{padding:0 20px}}.summary dl{{grid-template-columns:1fr}}.reader{{display:block}}.outline{{display:grid;grid-template-columns:repeat(2,1fr);position:static;margin-bottom:28px}}}}
</style></head><body><div class="shell"><header class="masthead"><h1>{escape(briefing.title)}</h1><p>{"逐項看主張，再回到論文核對" if zh else "Read the claims, then check the paper"}</p></header><main>{sections}</main></div>
<dialog id="figure-dialog"><button type="button" id="close-figure" aria-label="Close">✕</button><img alt=""></dialog>
<script id="frontierops-claims" type="application/json">{metadata}</script><script>
document.querySelectorAll('.paper').forEach(paper=>{{const steps=[...paper.querySelectorAll('.step')],answers=[...paper.querySelectorAll('.answer')];
const choose=i=>{{steps.forEach((s,n)=>{{s.setAttribute('aria-selected',String(n===i));s.tabIndex=n===i?0:-1}});answers.forEach((a,n)=>a.classList.toggle('active',n===i))}};
steps.forEach((s,i)=>{{s.addEventListener('click',()=>choose(i));s.addEventListener('keydown',e=>{{if(['ArrowDown','ArrowRight','ArrowUp','ArrowLeft'].includes(e.key)){{e.preventDefault();const n=(i+(e.key==='ArrowDown'||e.key==='ArrowRight'?1:steps.length-1))%steps.length;choose(n);steps[n].focus()}}}})}});if(steps.length)choose(0)}});
const dialog=document.getElementById('figure-dialog');document.querySelectorAll('.visual img').forEach(img=>img.addEventListener('click',()=>{{dialog.querySelector('img').src=img.src;dialog.querySelector('img').alt=img.alt;dialog.showModal()}}));document.getElementById('close-figure').addEventListener('click',()=>dialog.close());
</script></body></html>'''


def _section(section, evidence: dict[str, Evidence], labels: list[str], visual: dict | None, zh: bool) -> str:
    claims = section.claims
    headings = SUMMARY_ZH if zh else SUMMARY_EN
    summary_claims = [claims[i].text if i < len(claims) else "" for i in (0, 1, 4, 5)]
    summary = "".join(f'<div><dt>{escape(label)}</dt><dd>{escape(text)}</dd></div>'
                      for label, text in zip(headings, summary_claims) if text)
    tabs = "".join(f'<button class="step" role="tab" type="button" aria-controls="{escape(section.id)}-answer-{i}">{escape(labels[i] if i < len(labels) else "Claim")}</button>'
                   for i in range(len(claims)))
    answers = "".join(_answer(section.id, i, claim, evidence, labels, zh)
                      for i, claim in enumerate(claims))
    figure = _visual(section, evidence, visual, zh)
    return (f'<section class="paper" id="{escape(section.id, quote=True)}">'
            f'<h2 class="paper-title">{escape(section.headline)}</h2>{_bibliography(section.paper_metadata, zh)}'
            f'<div class="summary"><h3>{"重點摘要" if zh else "Executive summary"}</h3><dl>{summary}</dl></div>'
            f'<div class="reader"><nav class="outline" role="tablist" aria-label="Paper questions">{tabs}</nav>'
            f'<div class="content">{figure}<div class="explanation">{answers}</div></div></div></section>')


def _bibliography(meta: PaperMetadata, zh: bool) -> str:
    status = {"preprint": "arXiv 預印本" if zh else "arXiv preprint",
              "conference": "會議論文" if zh else "Conference paper",
              "journal": "期刊論文" if zh else "Journal article"}.get(meta.publication_status, "發表狀態未確認" if zh else "Status unverified")
    parts = [status]
    if meta.publication_venue:
        parts.append(meta.publication_venue)
    if meta.published_at:
        parts.append(meta.published_at[:10])
    if meta.affiliations:
        parts.append(", ".join(meta.affiliations))
    if meta.arxiv_id:
        parts.append(f"arXiv:{meta.arxiv_id}")
    source = f'<a href="{escape(meta.source_url, quote=True)}" target="_blank" rel="noopener">{"原始頁面" if zh else "Source page"}</a>' if meta.source_url else ""
    authors = ", ".join(meta.authors[:5]) + (f" +{len(meta.authors)-5}" if len(meta.authors) > 5 else "")
    all_authors = f'<details class="authors"><summary>{escape(authors)}</summary>{escape(", ".join(meta.authors))}</details>' if len(meta.authors) > 5 else f'<p class="authors">{escape(authors)}</p>' if authors else ""
    return f'<div class="bib">{" · ".join(escape(part) for part in parts)} {source}{all_authors}</div>'


def _visual(section, evidence: dict[str, Evidence], visual: dict | None, zh: bool) -> str:
    if visual:
        source = f'{escape(str(visual["source_uri"]), quote=True)}#page={visual["page"]}'
        return (f'<figure class="visual"><img src="{escape(str(visual["uri"]), quote=True)}" alt="{escape(str(visual["label"]), quote=True)} from source paper">'
                f'<figcaption>{escape(str(visual["label"]))} · p. {visual["page"]} {escape(str(visual["caption"]))} '
                f'<a href="{source}" target="_blank" rel="noopener">{"查看論文原頁" if zh else "Open source page"}</a></figcaption></figure>')
    excerpts = []
    for excerpt in section.source_excerpts:
        item = evidence.get(excerpt.evidence_id)
        if item:
            page = item.locator.get("page")
            uri = item.source_uri + (f"#page={page}" if page and item.source_uri.lower().endswith(".pdf") else "")
            excerpts.append(f'<blockquote class="excerpt"><mark>{escape(excerpt.quote)}</mark><figcaption>{escape(excerpt.caption or "")}'
                            f' <a href="{escape(uri, quote=True)}" target="_blank" rel="noopener">p. {escape(str(page or "source"))}</a></figcaption></blockquote>')
    return "".join(excerpts) if excerpts else '<p class="empty">' + ("此文沒有已核對的原圖或重點引文。" if zh else "No verified figure or highlighted passage was supplied.") + '</p>'


def _answer(section_id: str, index: int, claim, evidence: dict[str, Evidence], labels: list[str], zh: bool) -> str:
    citations = "".join(_citation(evidence[ref], zh) for ref in claim.evidence_ids if ref in evidence)
    if not citations:
        citations = '<p class="empty">' + ("詮釋，未附直接引文。" if zh else "Interpretation; no direct source supplied.") + '</p>'
    qualifier = "（詮釋）" if zh and claim.kind == "interpretation" else " (interpretation)" if claim.kind == "interpretation" else ""
    return (f'<article class="answer" id="{escape(section_id, quote=True)}-answer-{index}" role="tabpanel" data-claim-fingerprint="{claim_fingerprint(claim)}">'
            f'<h3>{escape(labels[index] if index < len(labels) else "Claim")}{qualifier}</h3><p>{escape(claim.text)}</p><div class="evidence-list">{citations}</div></article>')


def _citation(item: Evidence, zh: bool) -> str:
    page = item.locator.get("page")
    uri = item.source_uri + (f"#page={page}" if page and item.source_uri.lower().endswith(".pdf") else "")
    place = f"p. {page}" if page else item.locator.get("type", "source")
    excerpt = item.content[:650] + ("…" if len(item.content) > 650 else "")
    return (f'<details class="source"><summary>{"查核證據" if zh else "Inspect evidence"} · {escape(str(place))}</summary>'
            f'<blockquote>{escape(excerpt)}</blockquote><a href="{escape(uri, quote=True)}" target="_blank" rel="noopener">'
            f'{"開啟原始資料" if zh else "Open original source"}</a></details>')
