"""An inspectable, escaped HTML view of Rank decisions."""

from html import escape

from frontierops.domain.models import BriefingCandidate


def render_discovery(candidates: list[BriefingCandidate], weights: dict) -> str:
    enabled = {name: item["weight"] for name, item in weights.items() if item["enabled"]}
    denominator = sum(enabled.values()) or 1.0
    included = sum(not _excluded(item) for item in candidates)
    cards = "\n".join(_candidate(item, enabled, denominator) for item in candidates)
    if not cards:
        cards = '<p class="empty">這次 Sync 沒有可排序的新訊號；請檢查來源狀態與設定。</p>'
    return f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FrontierOps｜新研究篩選</title><style>
:root{{--ink:#182723;--muted:#54635d;--line:#cbd2cb;--paper:#f8f7f2;--green:#1d5b50}}
*{{box-sizing:border-box}}body{{max-width:1020px;margin:0 auto;padding:38px 24px 80px;background:var(--paper);color:var(--ink);font:16px/1.65 system-ui,sans-serif}}
h1,h2{{font-family:Georgia,serif;line-height:1.25}}h1{{font-size:clamp(36px,5vw,60px);margin:30px 0 12px}}h2{{font-size:27px;margin:0 0 10px}}
header{{border-bottom:2px solid var(--ink);padding-bottom:25px}}.meta,.note{{color:var(--muted)}}.controls{{display:flex;gap:16px;align-items:center;flex-wrap:wrap;margin:28px 0}}
button,input{{font:inherit;padding:8px 10px;border:1px solid var(--line);background:white;color:var(--ink)}}button{{cursor:pointer}}button[aria-pressed="true"]{{border-color:var(--green);color:var(--green);font-weight:700}}input{{min-width:260px;flex:1}}
article{{border-top:1px solid var(--line);padding:25px 0}}article:last-child{{border-bottom:1px solid var(--line)}}.status{{font-size:14px;color:var(--green);font-weight:700}}.excluded .status{{color:#914a36}}
.score{{font:700 24px Georgia,serif;margin:0 0 13px}}.reason{{margin:0 0 14px;color:var(--muted)}}details{{margin-top:15px}}summary{{cursor:pointer;font-weight:700}}table{{border-collapse:collapse;width:100%;margin-top:15px}}td,th{{padding:9px 8px;text-align:left;border-bottom:1px solid var(--line)}}td:last-child{{text-align:right}}.bar{{height:5px;background:#dfe6dd}}.bar span{{display:block;height:100%;background:var(--green)}}
.explanation{{border-left:3px solid var(--green);padding-left:16px;margin:17px 0}}.empty{{padding:40px 0}}[hidden]{{display:none!important}}
@media(max-width:580px){{body{{padding:20px 16px 50px}}.controls{{gap:8px}}input{{min-width:100%}}h2{{font-size:23px}}}}
</style></head><body><header><h1>本次發現的新研究</h1>
<p class="meta">共 {len(candidates)} 項候選，{included} 項通過資格檢查。分數是依 YAML 權重計算的相對排序，並非論文品質或真偽的機率。</p>
</header><div class="controls" aria-label="篩選研究"><button type="button" data-filter="all" aria-pressed="true">全部</button>
<button type="button" data-filter="included" aria-pressed="false">合格</button><button type="button" data-filter="excluded" aria-pressed="false">排除</button>
<input id="search" type="search" placeholder="搜尋論文標題" aria-label="搜尋論文標題"></div><main id="results">{cards}</main>
<p class="note">資格檢查（Gate）決定能否入選；通過後才依特徵分數排序。展開任一項可查看每條規則與各特徵的貢獻。</p>
<script>
const cards=[...document.querySelectorAll('article[data-state]')];let filter='all';
function update(){{const query=document.querySelector('#search').value.trim().toLowerCase();for(const card of cards)card.hidden=(filter!=='all'&&card.dataset.state!==filter)||!card.dataset.title.toLowerCase().includes(query)}}
document.querySelectorAll('[data-filter]').forEach(button=>button.addEventListener('click',()=>{{filter=button.dataset.filter;document.querySelectorAll('[data-filter]').forEach(other=>other.setAttribute('aria-pressed',String(other===button)));update()}}));
document.querySelector('#search').addEventListener('input',update);
</script></body></html>'''


def _excluded(item: BriefingCandidate) -> bool:
    return any(gate.result == "exclude" for gate in item.gate_trace)


def _candidate(item: BriefingCandidate, weights: dict[str, float], denominator: float) -> str:
    excluded = _excluded(item)
    state = "excluded" if excluded else "included"
    label = "已排除" if excluded else "合格候選"
    gates = "".join(
        f"<tr><td>{escape(gate.gate)}</td><td>{escape(gate.result)}</td>"
        f"<td>{escape(gate.reason or '')}</td></tr>" for gate in item.gate_trace
    ) or '<tr><td colspan="3">未設定 Gate</td></tr>'
    features = "".join(
        f"<tr><td>{escape(name)}</td><td>{item.features.get(name, 0):.3f} × {weight:.2f}</td>"
        f"<td>{(item.features.get(name, 0) * weight / denominator * 100):.1f}</td></tr>"
        for name, weight in weights.items()
    )
    explanation = item.paper_explanation
    insight = (f'<div class="explanation"><strong>研究問題</strong><p>{escape(explanation.problem.text)}</p>'
               f'<strong>核心想法</strong><p>{escape(explanation.core_idea.text)}</p></div>') if explanation else ""
    reasons = "; ".join(f"{gate.gate}: {gate.result}" for gate in item.gate_trace)
    return (f'<article class="{state}" data-state="{state}" data-title="{escape(item.title, quote=True)}">'
            f'<span class="status">{label}</span><h2>{escape(item.title)}</h2>'
            f'<p class="score">{item.total_score * 100:.1f} / 100</p>'
            f'<p class="reason">{escape(reasons or "未設定 Gate")}</p>{insight}'
            f'<details><summary>查看資格與分數依據</summary>'
            f'<h3>Gate</h3><table><thead><tr><th>規則</th><th>結果</th><th>原因</th></tr></thead><tbody>{gates}</tbody></table>'
            f'<h3>排序特徵</h3><table><thead><tr><th>特徵</th><th>值 × 權重</th><th>貢獻／100</th></tr></thead><tbody>{features}</tbody></table>'
            '</details></article>')
