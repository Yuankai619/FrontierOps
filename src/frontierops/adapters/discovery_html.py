"""Discovery timeline and selectable, escaped paper report."""

from html import escape
import json

from frontierops.domain.models import BriefingCandidate


def render_discovery(candidates: list[BriefingCandidate], weights: dict, *, run_id: str = "",
                     history: list[dict] | None = None, previous: list[dict] | None = None,
                     config_changed: bool = False, topic_delta: dict | None = None) -> str:
    enabled = {key: val["weight"] for key, val in weights.items() if val["enabled"]}
    denominator = sum(enabled.values()) or 1.0
    eligible = sum(not _excluded(item) for item in candidates)
    delta_labels = {entry["subject_id"]: _STATUS[entry["status"]]
                    for topic in (topic_delta or {}).get("topics", [])
                    for entry in topic["entries"] if entry["current_rank"] is not None}
    cards = "\n".join(_candidate(item, enabled, denominator,
                                 delta_labels.get(item.subject_id)) for item in candidates)
    if not cards:
        cards = '<p>這次沒有新增或更新的論文。下方保留先前 Run 的紀錄。</p>'
    timeline = "".join(
        f'<tr><td>{escape(str(row["run_id"]))}</td><td>{row["new"]}</td>'
        f'<td>{row["updated"]}</td><td>{row["unchanged"]}</td></tr>'
        for row in (history or [])
    )
    prior = "".join(f'<li>{escape(str(item["title"]))}</li>' for item in (previous or []))
    topic_view = _topic_delta_html(topic_delta or {})
    scope = ("主題檢索會重評本次回傳的候選；查詢範圍改變時，新命中不等於新發表。"
             if (topic_delta or {}).get("topics") else
             "設定已變動；舊清單是歷史收錄，不代表新設定下的完整庫存。" if config_changed
             else "本次只排名新增或更新項目；舊清單不會重複排名。")
    return f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>FrontierOps｜研究更新</title>
<style>:root{{--ink:#111;--line:#bbb;--muted:#555}}*{{box-sizing:border-box}}body{{max-width:1050px;margin:auto;padding:34px 24px 80px;color:var(--ink);font:16px/1.6 system-ui;background:#fff}}
h1,h2{{font-family:Georgia,serif;line-height:1.2}}h1{{font-size:clamp(36px,5vw,58px);margin:20px 0}}h2{{font-size:27px;margin:0 0 10px}}header{{border-bottom:2px solid #111;padding-bottom:18px}}
.muted{{color:var(--muted)}}.summary{{display:flex;gap:38px;flex-wrap:wrap;margin:25px 0}}.summary strong{{display:block;font:38px Georgia,serif}}
.history{{background:#f4f4f4;padding:20px 25px;margin:26px 0}}.history h2{{font-size:22px}}.history ul{{max-height:160px;overflow:auto}}
table{{border-collapse:collapse;width:100%;margin:12px 0}}td,th{{padding:8px;text-align:left;border-bottom:1px solid var(--line)}}.controls{{display:flex;gap:12px;flex-wrap:wrap;margin:25px 0}}
button,input{{font:inherit;padding:8px;border:1px solid #888;background:#fff}}button{{cursor:pointer}}button[aria-pressed="true"]{{background:#111;color:#fff}}input[type=search]{{min-width:250px;flex:1}}
article{{border-top:1px solid var(--line);padding:25px 0}}article:last-child{{border-bottom:1px solid var(--line)}}.score{{font:22px Georgia,serif}}.select{{display:flex;align-items:center;gap:8px;margin:12px 0}}
.select input{{width:20px;height:20px}}details{{margin-top:12px}}summary{{cursor:pointer}}.actions{{border-top:2px solid #111;margin-top:34px;padding-top:20px}}#save-status{{min-height:25px}}[hidden]{{display:none!important}}
@media(max-width:600px){{body{{padding:18px}}input[type=search]{{min-width:100%}}}}</style></head><body>
<header><h1>研究更新</h1><p class="muted">Run：{escape(run_id)}。分數只是目前 frontier.yaml 下的排序，不代表論文品質。</p></header>
<div class="summary"><div><strong>{len(candidates)}</strong>{'本次檢索候選' if (topic_delta or {}).get('topics') else '本次新增或更新'}</div><div><strong>{eligible}</strong>符合設定</div><div><strong>{len(previous or [])}</strong>先前收錄</div></div>
{topic_view}
<section class="history"><h2>同步紀錄</h2><p>{escape(scope)}</p><table><thead><tr><th>Run</th><th>新增</th><th>更新</th><th>未變</th></tr></thead><tbody>{timeline}</tbody></table>
<details><summary>查看先前收錄</summary><ul>{prior or '<li>尚無先前論文</li>'}</ul></details></section>
<div class="controls" aria-label="篩選論文"><button data-filter="all" aria-pressed="true">全部</button><button data-filter="included" aria-pressed="false">合格</button>
<button data-filter="excluded" aria-pressed="false">排除</button><input id="search" type="search" placeholder="搜尋論文標題" aria-label="搜尋論文標題"></div><main>{cards}</main>
<section class="actions"><h2>選擇要解說的論文</h2><p>勾選並儲存，再對 Agent 說「briefing」。選取屬於此 Run；每篇論文分別輸出。</p>
<button id="save-selection">儲存選取</button><p id="save-status" role="status"></p><p class="muted">Agent 開啟的本機頁面可直接儲存。開啟靜態 HTML 時，按鈕會下載 JSON；交給 Agent 放入同一 Run 的 <code>02-rank/briefing-selection.json</code>。</p></section>
<script>const runId={json.dumps(run_id).replace('<', '\\u003c')},cards=[...document.querySelectorAll('article[data-state]')];let filter='all';
function update(){{const q=document.querySelector('#search').value.trim().toLowerCase();for(const card of cards)card.hidden=(filter!=='all'&&card.dataset.state!==filter)||!card.dataset.title.toLowerCase().includes(q)}}
document.querySelectorAll('[data-filter]').forEach(b=>b.addEventListener('click',()=>{{filter=b.dataset.filter;document.querySelectorAll('[data-filter]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));update()}}));document.querySelector('#search').addEventListener('input',update);
document.querySelector('#save-selection').addEventListener('click',async()=>{{const ids=[...document.querySelectorAll('input[data-candidate-id]:checked')].map(x=>x.dataset.candidateId),status=document.querySelector('#save-status');
if(!ids.length){{status.textContent='請至少選一篇合格論文。';return}}const payload={{schema_version:'0.1',run_id:runId,selected_candidate_ids:ids}},session=new URL(location.href).searchParams.get('session');
if(session){{try{{const response=await fetch('/selection?session='+encodeURIComponent(session),{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(payload)}});if(!response.ok)throw Error(await response.text());status.textContent='已儲存。現在可以對 Agent 說「briefing」。';return}}catch(error){{status.textContent='儲存失敗：'+error.message;return}}}}
const blob=new Blob([JSON.stringify(payload,null,2)],{{type:'application/json'}}),url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download='briefing-selection.json';link.click();URL.revokeObjectURL(url);status.textContent='已下載選取檔，請交給 Agent。';}});</script></body></html>'''


def _excluded(item: BriefingCandidate) -> bool:
    return any(gate.result == "exclude" for gate in item.gate_trace)


_STATUS = {
    "baseline": "首次建立基準", "new_in_scope": "新納入查詢範圍",
    "published_since_last_run": "上次執行後發表", "newly_observed": "本次才查得",
    "newly_eligible": "新符合 Gate", "newly_excluded": "新被 Gate 排除",
    "ranking_changed": "排名或 Gate 變動", "unchanged": "未變",
    "not_returned": "本次未回傳（不代表撤稿）",
}


def _topic_delta_html(report: dict) -> str:
    sections = []
    for topic in report.get("topics", []):
        if topic["previous_run"] is None:
            note = "首次建立基準；這些論文不是全部在今天新發表。"
        elif topic["scope_changed"]:
            note = "查詢條件或日期範圍已改變；新命中是新納入範圍，不代表上次執行後才發表。"
        else:
            note = "與上一次相同主題查詢比較；來源晚收錄的舊論文會標為「本次才查得」。"
        if topic["policy_changed"]:
            note += " Gate 已變動；分數與資格依各自 Run 的設定計算。"
        if any(scope.get("truncated") or scope.get("coverage") == "top_k_only"
               for scope in topic["coverage"] + topic.get("previous_coverage", [])):
            note += " 本次或上次來源結果有上限，本表不是全量論文差異。"
        rows = []
        for entry in topic["entries"]:
            old_rank = entry["previous_rank"] or "—"
            new_rank = entry["current_rank"] or "—"
            old_score = "—" if entry["previous_score"] is None else f'{entry["previous_score"]*100:.1f}'
            new_score = "—" if entry["current_score"] is None else f'{entry["current_score"]*100:.1f}'
            gates = ", ".join(f"{key}: {value}" for key, value in (entry["current_gates"] or {}).items()) or "—"
            rows.append(f'<tr><td>{escape(entry["title"])}</td><td>{escape(_STATUS[entry["status"]])}</td>'
                        f'<td>{old_rank} → {new_rank}</td><td>{old_score} → {new_score}</td>'
                        f'<td>{escape(gates)}</td></tr>')
        counts = " · ".join(f'{_STATUS[key]} {count}' for key, count in topic["counts"].items())
        detail_open = " open" if len(rows) <= 25 else ""
        sections.append(f'<section class="history"><h2>{escape(topic["topic_id"])}</h2><p>{escape(note)}</p>'
                        f'<p>{escape(counts)}</p><p class="muted">比較基準：{escape(topic["previous_run"] or "無")}</p>'
                        f'<details{detail_open}><summary>查看 {len(rows)} 篇論文的前後差異</summary>'
                        '<table><thead><tr><th>論文</th><th>變化</th><th>排名</th><th>分數</th><th>目前 Gate</th>'
                        f'</tr></thead><tbody>{"".join(rows)}</tbody></table></details></section>')
    return "\n".join(sections)


def _candidate(item: BriefingCandidate, weights: dict[str, float], denominator: float,
               delta_label: str | None = None) -> str:
    excluded = _excluded(item)
    gates = "".join(f"<tr><td>{escape(g.gate)}</td><td>{escape(g.result)}</td><td>{escape(g.reason or '')}</td></tr>" for g in item.gate_trace) or '<tr><td colspan="3">未設定 Gate</td></tr>'
    features = "".join(f"<tr><td>{escape(k)}</td><td>{item.features.get(k, 0):.3f} × {v:.2f}</td><td>{item.features.get(k, 0)*v/denominator*100:.1f}</td></tr>" for k, v in weights.items())
    select = "" if excluded or item.paper_explanation is None else f'<label class="select"><input type="checkbox" data-candidate-id="{escape(item.artifact_id, quote=True)}" checked>列入 Briefing</label>'
    return (f'<article data-state="{"excluded" if excluded else "included"}" data-title="{escape(item.title, quote=True)}">'
            f'<strong>{"已排除" if excluded else "合格候選"}</strong>'
            f'{" · " + escape(delta_label) if delta_label else ""}<h2>{escape(item.title)}</h2>'
            f'<p class="score">排序 {item.total_score*100:.1f} / 100</p>{select}'
            f'<details><summary>資格與分數依據</summary><h3>Gate</h3><table>{gates}</table><h3>排序特徵</h3><table>{features}</table></details></article>')
