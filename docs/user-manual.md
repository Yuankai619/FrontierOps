# FrontierOps 使用手冊

FrontierOps 是供既有 Coding Agent 使用的研究簡報 Harness。研究人員**主動執行 Sync**，系統才比較上次成功同步後的新訊號；其首要成果是幫人理解「這篇論文解決什麼問題、怎麼做、證據支持到哪裡」，而非僅列論文清單。HTML、OpenSlide 投影片與影片預覽共用通過 Review 的 `BriefingSpec`。

## Quick Start：研究人員只需四個 Agent Skill

需求：先安裝 `uv >= 0.12.20, < 0.14`；slides/video 另需 Node.js／npm。先在 Claude Code、Codex CLI 或 GitHub Copilot CLI 裝 FrontierOps plugin（遠端 repository 必須包含已合併的 plugin 版本）：

```bash
claude plugin marketplace add Yuankai619/FrontierOps
claude plugin install frontierops@frontierops

codex plugin marketplace add Yuankai619/FrontierOps
codex plugin add frontierops@frontierops

copilot plugin install Yuankai619/FrontierOps:plugins/frontierops
```

安裝 plugin 只有 Skill，還沒有 Python Harness。進入研究專案後，請 Agent 使用 [`frontier-setup`](../plugins/frontierops/skills/frontier-setup/SKILL.md)：「幫我在這裡 setup FrontierOps。」明確呼叫語法分別為 Claude Code `/frontierops:frontier-setup`、Codex `$frontier-setup`、Copilot CLI `/frontierops/frontier-setup`；要跑其他 Skill 時只換最後名稱。Setup 會用 uv 安裝 Harness、檢查可用工具、執行 `frontier setup`，並回報 `frontier.yaml` 與 `frontier_output/` 的實際路徑。已存在的 YAML 不會被覆蓋；新 YAML 的來源預設關閉，需要下一步設定。

1. 使用 [`frontier-config`](../plugins/frontierops/skills/frontier-config/SKILL.md)：「我研究多模態論文理解，追蹤某位學者與 CVPR，給我 8 分鐘互動 HTML 與 slides。」如果主題或來源不清楚，Agent 先詢問；學者／會議 ID 無法確認時不會臆造。產生的候選 YAML 先驗證、顯示差異，再套用到 active `frontier.yaml`。
2. 使用 [`frontier-discover`](../plugins/frontierops/skills/frontier-discover/SKILL.md)：「現在檢查新論文，說明篩選理由。」這才會主動 Sync；Rank 的 HTML 公開於 `frontier_output/discoveries/<run-id>.html`，能搜尋、切換合格／排除，展開 Gate 與權重貢獻。
3. 使用 [`frontier-briefing`](../plugins/frontierops/skills/frontier-briefing/SKILL.md)：「用剛才的 Run 解釋選中的論文，產生 HTML 和投影片。」Agent 會核對 Evidence，跑 Brief、Review、Render，成果在 `frontier_output/briefings/<run-id>/`。影片需明確啟用與核准；旁白預覽不等於已匯出的 MP4。

`frontier.yaml.example` 是**不需 API key 的離線 fixture 示例**，適合開發者測試，並非使用者的 active 設定。Agent 使用的是 `frontier.yaml`。每次 Run 的原始資料與中間 Artifact 在 `.frontier/runs/<run-id>/`；公開成果才放 `frontier_output/`。Briefing Skill 會在生成的 OpenSlide 專案內同步其原生 Skill；若啟用影片則使用 HyperFrames 原生 Skill。FrontierOps 不複製或重造這些框架的技能。

## 開發者／除錯用指令

在 FrontierOps 原始碼 checkout 中，使用 `uv sync --locked`。完整離線驗收請依 [README 的 fixture 流程](../README.md#離線端到端驗收) 執行：`sync --config frontier.yaml.example` 後依序 rank、brief、review、render，使用同一個 stdout 印出的**絕對 Run 路徑**；測試為 `uv run --locked python -m unittest discover -s tests -v`。研究人員不必自行逐步執行。

## 指令參考

在原始碼 checkout 中，`frontier ...` 前面加 `uv run --locked`；透過 Setup Skill 安裝為獨立工具後直接用 `frontier ...`。未列出的選項不是隱藏功能；用 `frontier --help` 查看目前 CLI。

| 指令 | 輸入與效果 |
|---|---|
| `setup --workspace PATH --name NAME` | 建立 active YAML 與公開輸出目錄，保留既有設定；Python 安裝由 Setup Skill 管理。 |
| `schema config --format json` | 印出嚴格的 config JSON Schema，可查看所有預設值與型別。 |
| `config inspect --config PATH` | 讀取並展開預設值，不修改檔案。 |
| `config validate --config PATH` | 驗證 YAML；未知欄位或無效值會失敗。 |
| `config draft --config PATH --output PATH` | 產生候選設定檔；供 Agent 編輯，不改 active config。 |
| `config diff --old PATH --new PATH` | 顯示欄位路徑、修改前後值，供人工審核。 |
| `config apply --candidate PATH --config PATH` | 完整驗證後原子取代目標設定；只在確認後用。 |
| `scholar resolve --name NAME --provider semantic_scholar` | 查詢學者 stable ID 候選；同名者須人工消歧。目前 resolver 是離線 fixture。 |
| `venue resolve --name NAME --year YEAR --provider openreview` | 查詢會議 stable venue ID 候選；目前 resolver 是離線 fixture。 |
| `build --config PATH` | 驗證設定並建立新 Run、manifest、resolved config；不取回來源。 |
| `sync --config PATH` | 使用者觸發 Build 與 delta sync；比較上次成功 Sync，不在背景定時執行。 |
| `rank --run PATH` | 套用 Gate、權重與深度解釋；輸出候選、Evidence、排序報告與可開啟的 Discovery HTML。 |
| `brief --run PATH` | 按內容與時間預算建立 renderer-neutral draft。 |
| `review --run PATH` | 查 Evidence、來源、數字、重複與時間，通過後建立 approved spec。 |
| `render --run PATH` | 只讀 approved spec，發布互動 HTML、OpenSlide source，及在已啟用時的影片 preview。 |

## `frontier.yaml` 設定參考

由 Setup Skill 建立 `frontier.yaml`，再由 Config Skill 按研究目的修改；[`frontier.yaml.example`](../frontier.yaml.example) 僅示範離線 fixture。所有路徑相對於 YAML 所在目錄解析。模型拒絕未知欄位。API key、OpenReview 密碼只填**環境變數名稱**，不可放 secret value。括號中的數字是未指定時的程式預設。

| 路徑 | 意義 |
|---|---|
| `schema_version` | 設定契約版本，目前只能是 `"0.1"`。 |
| `project.id / name` | 穩定專案 ID／顯示名稱，均必填。 |
| `project.timezone / language / workspace_dir / output_dir` | 時區（`UTC`）、內容語言（`en`）、Run 工作目錄（`.frontier`）與公開成果目錄（`frontier_output`）。 |
| `profile.topics[]` | 每個研究主題的 `id`、`description`、非負 `weight`（1）；用於相關度。 |
| `profile.keywords.include / exclude` | 偏好的／排除的關鍵詞陣列；不要把它當全文理解的唯一依據。 |
| `tracking.scholars[]` | `id` 是本地 tracker ID、`name` 是顯示名稱；`aliases` 處理別名，`identities` 保存 provider stable ID，`providers` 指來源；`backfill_days`（365）與 `always_include_new_publications`（true）控制追蹤視窗與新作優先。 |
| `tracking.venues[]` | `provider: openreview`、`venue_id` stable ID 與可選的 `decisions` 過濾。 |
| `sources.semantic_scholar / arxiv` | 同型來源設定，欄位見下表。 |
| `sources.local_library` | 本地 PDF、Markdown、文字庫設定，欄位見下表。 |
| `sources.openreview` | OpenReview 專用設定，欄位見下表。 |
| `sync.trigger_mode / baseline` | 目前固定為 `manual`／`last_successful_sync`；未經使用者 Sync 不更新。 |
| `sync.default_lookback_days` | 初次或缺少 cursor 時回看天數（14）。 |
| `sync.on_provider_error` | `fail` 中止或 `partial` 保留部分結果；部分失敗不是「無新論文」。 |
| `sync.preserve_raw_responses` | 是否保留來源原始回應（true），方便溯源。 |
| `ranking.gates[]` | 候選資格規則；欄位見 Gate 小節。 |
| `ranking.features.*.enabled / weight` | 開關與非負權重：`lexical_relevance`（0.55）、`citation`（0.15）、`freshness`（0.15）、`reliability`（0.15）。合格後才按分數排序。 |
| `ranking.citation_scale / freshness_half_life_days` | 引用分數尺度（100）／新鮮度半衰期天數（180）。 |
| `ranking.source_reliability` | provider 名稱到可信度分數的映射，可在 YAML 調整。 |
| `ranking.deep_enrich_top_k / max_fulltext_pages` | 深度產生 Paper Explanation 的候選上限（5）／讀取全文頁數上限（20）。 |
| `brief.target_duration_seconds` | 目標長度（300 秒），可自訂；不是固定五分鐘。 |
| `brief.maximum_developments / maximum_seconds_per_development` | 最多研究項目（5）／每項時間上限（75 秒）。 |
| `brief.narration_words_per_minute / outputs` | 旁白估計語速（140）／目標格式陣列 `html`、`slides`、`video`。 |
| `review.required / auto_fix` | Review 開關（true）／只允許 `none` 或 `safe_only`；即使設定可選，產品流程仍建議保持 Review。 |
| `review.fail_on_*` | `missing_evidence`、`broken_source`、`unsupported_number`、`duration_over_budget`、`duplicate_development` 是否阻擋核准（皆預設 true）。 |
| `rendering.video` | 影片 preview 與外部 HeyGen TTS adapter 設定，欄位見下表。 |

### 來源設定細項

| 路徑／欄位 | 意義 |
|---|---|
| `semantic_scholar`／`arxiv`: `enabled / mode / fixture_path` | 是否讀取來源（false）；`fixture` 或 `live`（預設 fixture）；凍結測資路徑。Live Semantic Scholar 需要已追蹤的 stable author ID；Live arXiv 需要查詢目標。 |
| 同上：`overlap_days / page_size / max_results` | 回看重疊天數（3）、每頁筆數（100）、本次最大結果數（100）。 |
| 同上：`api_key_env / base_url / user_agent` | API key 的環境變數名、端點覆蓋、User-Agent（`FrontierOps/0.1`）。 |
| 同上：`request_timeout_seconds / request_delay_seconds` | 連線逾時（30 秒）與請求間隔（3 秒）。 |
| 同上：`paper_ids / queries / categories` | arXiv 的指定 ID、搜尋字串或分類；live mode 至少提供一項。 |
| `local_library.enabled / roots / recursive` | 是否啟用（false）、資料夾清單、是否遞迴（true）。建議使用 `data/library/`。 |
| `local_library.allowed_extensions / allow_outside_project_root` | 允許 `.pdf`、`.md`、`.txt`；預設不允許路徑或 symlink 逃出專案根目錄。 |
| `openreview.enabled / mode / fixture_path / base_url` | 啟用（false）、fixture/live、測資路徑、API v2 端點。 |
| `openreview.username_env / password_env / token_env` | 認證環境變數名稱；不將實際密碼或 token 寫入 YAML。 |
| `openreview.include_replies` | 是否包含討論 reply（true），連同 forum／decision provenance 保存。 |

`tracking.scholar.providers` 允許 `google_scholar` 這個追蹤值，但**目前沒有 Google Scholar live adapter**；不應宣稱已能從 Google Scholar 自動抓文。Semantic Scholar live、arXiv live、OpenReview live 與本地庫可用，但網路、憑證、rate limit 與原站資料品質仍會影響結果。

### Gate 是什麼？

Gate 是**資格檢查**，不是排序權重。每條 rule 有 `id`、`type`（`publication_year`／`citation`／`relevance`）、`enabled`（true）與 `on_fail`（`exclude` 或 `warn`）。各 type 的門檻分別是 `min_year`、`minimum_count`、`minimum`（0–1）。Citation 可設 `exempt_if_age_days_lte`（0），讓剛發表、來不及累積引用的新論文豁免。輸出會保留 `pass`、`exclude`、`warn`、`exempt` trace，便於解釋「為何進／沒進」。例：

```yaml
ranking:
  gates:
    - id: recent
      type: publication_year
      min_year: 2024
      on_fail: exclude
    - id: citations
      type: citation
      minimum_count: 3
      exempt_if_age_days_lte: 90
      on_fail: warn
```

### 影片設定細項

| `rendering.video` 欄位 | 意義 |
|---|---|
| `enabled` | 預設 false；true 時必須有 `heygen_tts_script`。 |
| `provider / tts_provider` | 目前固定 `hyperframes`／`heygen`。 |
| `heygen_tts_script` | HeyGen TTS 外部工具的本地路徑；不由 FrontierOps 重造 TTS client。 |
| `voice_id / language` | 選用的 HeyGen 聲音與語言覆蓋。 |
| `width / height / fps` | 預覽畫布 1920×1080、30 fps；fps 可選 24／30／60。 |
| `quality` | `draft`／`looks`（預設）／`delivery` 的預覽品質。 |

影片輸出是 `05-render/hyperframes/` 中可檢查的 composition、WAV 和 word-level 字幕，不是已核准 MP4。先跑 `npx hyperframes check` 和 `npx hyperframes preview --background`，看過原圖、場景、旁白與字幕，再由使用者核准後另行編碼。離線預覽需自行提供固定版動畫依賴。

## 產物、保存與設計邏輯

```text
.frontier/
  runs/<run-id>/
    00-build/  01-sync/  02-rank/  03-brief/  04-review/  05-render/
    run-manifest.json
  state/             # 上次成功同步的 cursor、身分與研究發展索引
  cache/raw/         # 不可變來源快照
```

每次執行建立新的 Run，過往 Run 不覆蓋。JSON／JSONL 是可查核的資料本體，SQLite 是可重建索引。失敗的 Run 仍留作除錯，但不能推進上次成功同步 cursor。`ResearchSignal` 記錄新事件，`Evidence` 帶頁碼／文字定位，`BriefingCandidate` 保留分數與 Gate trace，`ResearchDevelopment` 跨 Run 合併同一研究，`BriefingSpec` 固定核准內容與時間，`RunManifest` 串起每一階段。這使三種媒體能回到同一組已核准 claim，而不是各自自由生成。

視覺設計遵循 CS 論文報告的論證順序：問題 → 核心方法 → 實驗支持 → 限制。優先使用可回到原 PDF 頁碼的 Figure／關鍵段落；一頁一個可驗證主訊息。HTML 提供問題分頁、Evidence 展開、原圖放大與 PDF 回查；OpenSlide 項目保留可編輯 source；影片先做可審閱 preview。禁止把裝飾圖、無來源數字、重複卡片格當作學術解釋，也不使用標題上方小標、裝飾性全大寫英文或 pill／圓點堆砌。

若要接入自己的論文庫，把 PDF 放在 `data/library/`，開啟 `sources.local_library.enabled` 並設定 `roots`。PDF 由 PyMuPDF adapter 抽取頁碼與 bbox，文字檔保留行號；Agent 可再用既有 PDF 工具檢查公式、圖與段落，不應將 parser 的猜測當成原文事實。完整架構契約見 [`system-spec.md`](system-spec.md)。
