# AutoSci：四個 Agent Skill 的端到端範例

論文：[AutoSci: A Memory-Centric Agentic System for the Full Scientific Research Lifecycle](https://arxiv.org/abs/2605.31468)（[PDF](https://arxiv.org/pdf/2605.31468)）。目標是在 `ADSL/FrontierOps_test/autosci-example/` 用本地 PDF 產生互動 HTML 與 OpenSlide；不執行影片、不需 API key，也不啟用背景排程。

以下 prompt 是給已安裝 FrontierOps plugin 的 **Coding Agent**，不是請研究人員手動串接六個 CLI stage。把 `<ADSL>` 換成自己的絕對路徑。先把論文 PDF 放到 `<ADSL>/FrontierOps_test/autosci-example/data/library/`；建議檔名為 `AutoSci - A Memory-Centric Agentic System for the Full Scientific Research Lifecycle.pdf`，因為目前本地來源以檔名作論文標題。原有 `<ADSL>/FrontierOps_test/frontier.yaml` 不必修改；使用獨立子資料夾。

## 1. Setup

對 Agent 說：

> 使用 `frontier-setup` Skill，在 `<ADSL>/FrontierOps_test/autosci-example` 建立名為「AutoSci」的研究 workspace。依 Skill 檢查 uv、Git、Node/npm，在 FrontierOps 原始碼 checkout 用 `uv sync --locked` 與 `uv run --locked frontier`；建立真正的 `frontier.yaml` 和 `frontier_output/`。不要覆寫其他 workspace 的設定，也不要宣稱已同步論文。回報各工具版本、設定路徑與是否新建。

| 本步輸入 | 本步實際輸出 | 交給下一步 |
|---|---|---|
| workspace 絕對路徑、專案名稱、FrontierOps checkout | `frontier.yaml`、`frontier_output/`、`created_config`、前置工具檢查 | active `frontier.yaml` 路徑，以及研究範圍的自然語言描述 |

本次 `created_config: true`；新 YAML 通過 `frontier config validate`，來源預設全部關閉。這裡使用**本機開發 checkout**，未驗證三種宿主的遠端 plugin 安裝命令。

## 2. Config

對 Agent 說：

> 使用 `frontier-config` Skill。只追蹤這份 AutoSci 本地 PDF，研究主題為 automated scientific research、persistent research memory 與 agent harness。請啟用 `sources.local_library`，`roots` 指向 workspace 內的 `data/library`；其他網路來源先關閉。HTML 與 slides，影片關閉；保留五分鐘目標，單篇上限也調為 300 秒。不要設定 citation Gate，並停用 citation 排序權重，因本地 PDF 沒有可靠引用數。先讀 schema/inspect，建立候選 YAML，validate、diff 後再 apply；回報實際改動，不要自動 Sync。

| 本步輸入 | 本步實際輸出 | 交給下一步 |
|---|---|---|
| active YAML、上述需求、`data/library/` 中的 PDF | `frontier.candidate.yaml`、驗證結果、設定差異、已套用的 `frontier.yaml` | active YAML 路徑與「現在檢查新研究」的明確要求 |

關鍵設定如下；其他欄位保留 Setup 預設值：

```yaml
sources:
  local_library:
    enabled: true
    roots: [data/library]
profile:
  topics:
    - id: auto-research
      description: Automated scientific research systems, persistent research memory, agent harnesses, and research workflows
      weight: 1.0
  keywords:
    include: [AutoSci, SciMem, SciFlow, SciDAG, SciEvolve]
ranking:
  gates: []
  features:
    citation: {enabled: false, weight: 0.0}
  max_fulltext_pages: 22
brief:
  target_duration_seconds: 300
  maximum_seconds_per_development: 300
  outputs: [html, slides]
rendering:
  video: {enabled: false}
```

這是**設定節錄**，不能直接取代完整 YAML；Schema 中 `rendering.video` 等區塊有其他預設欄位。`target_duration_seconds` 是內容時間預算，不會憑空把簡短內容補成五分鐘旁白。

## 3. Discover

對 Agent 說：

> 使用 `frontier-discover` Skill，對 `<ADSL>/FrontierOps_test/autosci-example/frontier.yaml` 執行一次使用者觸發的 Sync 與 Rank。檢查 Sync 的新增數／來源錯誤、Rank 的 Gate 和分數理由；開啟 Discovery HTML。請回報**完整 Run 路徑**，並只把這個 Run 交給後續 Briefing。不要把排序分數解釋成論文品質。

| 本步輸入 | 本步實際輸出 | 交給下一步 |
|---|---|---|
| active YAML；使用者明確要求同步 | `.frontier/runs/<run-id>/`、`01-sync/`、`02-rank/`、`frontier_output/discoveries/<run-id>.html` | **同一個** Run 絕對路徑、選中的 AutoSci candidate、期望的解說格式 |

首次實跑：抓到 1 筆、產生 1 筆、Rank 合格 1 筆，無 provider error。再由使用者要求第二次 Sync 時：抓到 1 筆、產生 0 筆、略過重複 1 筆；不應再假稱有新論文。這份本地 PDF 沒有引用數／可靠發布日期，所以分數不是品質判斷。

**品質檢查發現：**目前 deterministic Rank explanation 會按關鍵字從全文挑句；本例把 appendix 的「debate」當研究問題，且把 GPU wiki 附錄當作「研究意義」。Discovery HTML 與候選清單可供初篩，但自動解說不可直接發布。Agent 必須回到原文修正 Briefing draft；這是已觀察到的限制，不應寫成通過品質驗證。

## 4. Briefing

對 Agent 說：

> 使用 `frontier-briefing` Skill，對剛才 Discover 回報的**同一個 Run**解說 AutoSci，只輸出互動 HTML 和 OpenSlide，不做影片。先核對 PDF 第 1–3、7、13 頁，說清楚研究問題、SciMem／SciFlow／SciDAG／SciEvolve、兩個 case study 的證據與評估限制。若 `03-brief/briefing.draft.json` 有錯誤抽句，請只依有頁碼的 Evidence 修正 claims、paper explanation、旁白文字，保留 schema／Evidence ID；再跑 Review，通過才 Render。檢查 HTML 分頁、展開證據、PDF 原頁連結和 Figure 1；在輸出的 slides 專案執行 `npm install`、`npm run sync:skills`、`npm run build`，並視覺檢查每頁。回報實際輸出路徑及還需人工改稿之處。

| 本步輸入 | 本步實際輸出 | 驗收重點 |
|---|---|---|
| 同一 Run 絕對路徑、選中的 AutoSci 論文、PDF Evidence、HTML/slides 格式 | `03-brief/briefing.draft.json`、`04-review/briefing.approved.json`、`05-render/render-result.json`、公開 briefing 目錄 | 核准的 claims 均有可回原文的證據；HTML 可互動；OpenSlide 可 build、圖與字不裁切 |

本次 Agent 核對後，把「問題／四個模組／兩個案例／限制」改為 7 條來源連結的 claims。案例分數 **6.3/10 與 5.8/10 是論文所報的自動 review 分數**，不是人類審稿結果或 FrontierOps 對品質的評分。Review 結果為 `approved`、7/7 claims 通過、0 issues；HTML 的 Results 分頁切換、證據展開與第 13 頁 PDF 連結已在瀏覽器實測。OpenSlide 的 `npm run build` 通過，Figure 1 完整顯示。`npm install` 當時提示 8 項 high-severity audit warnings；本例未任意升級框架相依，需另案查核。

成功的公開成果位於 `frontier_output/briefings/<run-id>/html/index.html` 與同目錄的 `slides/`；`slides/dist/` 是執行 build 後的展示站，OpenSlide 路由為 `/s/frontier-briefing`。同一 Run 重做 Render 會產生 `-2`、`-3` 等新公開目錄；以 `05-render/render-result.json.public_output_dir` 為準，勿猜路徑。這次因修正裁圖而重 Render，最新成果在 `run_20261011T194631748787Z_865dbc82-3/`。原有的 `FrontierOps_test/frontier.yaml` 未動。

## 實測結論與邊界

- 四個 Skill 的指令順序、資料交接、Delta Sync、Review、HTML 互動及 OpenSlide build 都走通；此次是在 Codex 中依四份 `SKILL.md` 指令操作本機 checkout，**未宣稱已在 Claude／Copilot 測過 plugin 安裝**。
- Review 目前檢查 schema、Evidence ID、數字、重複與時間；**不會語意判斷引用段落是否真能支持 claim**。原文核對是 Briefing Skill 的必要人工／Agent 工作，不可省略。
- 原始自動草稿的抽句不合格；修正過的核准成果可示範流程，但此例不構成「全自動、高品質研究解說」的證明。投影片可建置且有來源圖，正式展示前仍建議依 OpenSlide `slide-authoring` Skill 精簡長標題與文字密度。
- `frontier_output/` 與 `.frontier/` 是測試 workspace 的產物，不納入 git；影片完全未測。
