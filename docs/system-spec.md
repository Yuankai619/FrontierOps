# FrontierOps 動態系統規格

## 產品目標

使用者主動執行 Sync 後，FrontierOps 應協助研究人員快速理解新研究。Briefing 預設為 300 秒但可由設定調整；HTML、slides 與旁白影片都必須由同一份已核准 `BriefingSpec` 產生。

## Hexagonal Architecture

- **Domain** 擁有純粹的設定與 artifact 契約，不依賴外層模組。
- **Application** 擁有 use cases，並定義基礎設施必須實作的 ports。
- **Adapters** 實作 YAML、檔案系統、時間、資料來源、renderer 與使用者介面。
- `frontierops.build` 等頂層模組是 composition root；CLI 只是 driving adapter，不放業務規則。
- 依賴只朝核心流動：`adapters -> application -> domain`。

## Pipeline

`Build -> Sync -> Rank -> Brief -> Review -> Render`

- **Build：** 驗證設定並建立可重現的 Run。
- **Sync：** 與上一次成功狀態比較資料來源；系統不內建排程器。
- **Rank：** 套用 YAML 定義的 eligibility gates 與可拆解分數。
- **Brief：** 解釋問題、方法、新穎性、實驗、限制與研究意義。
- **Review：** 阻擋無證據 claim、失效來源、重複內容與超時 briefing。
- **Render：** 只從已核准 spec 產生各種格式；影片先產生可審核 preview，核准後才編碼 MP4。

## 核心 Artifacts

| Artifact | 職責 |
|---|---|
| `ResearchSignal` | 新增或改變的論文、決策、release、benchmark 或本地文件 |
| `Evidence` | 具有穩定 locator、可回到來源查證的證據片段 |
| `BriefingCandidate` | 已正規化、評分且保留 eligibility trace 的候選研究 |
| `ResearchDevelopment` | 跨來源、跨 Run 聚合的一項研究發展 |
| `BriefingSpec` | 與 renderer 無關、含時間與 Evidence link 的 briefing 內容 |
| `RunManifest` | 一次 Run 的輸入、輸出、版本、stage、警告與失敗狀態 |

## 保存與政策

- `.frontier/runs/` 採 append-only；`.frontier/state/` 保存 cursors；`.frontier/cache/raw/` 保存 immutable source snapshots。
- JSON／JSONL artifacts 是可直接檢查的 source of truth；SQLite 只是可重建的查詢索引。
- 失敗的 Sync Run 仍保留供除錯，但不得推進 last-successful cursor。
- `frontier.yaml` 擁有 domain policy；未知欄位必須失敗，secret 只保存環境變數名稱。
- Gate 對候選項做 pass、exclude、warn 或 exempt；score 只負責排列合格候選。

## 設定生命週期

- `schema` 與 `inspect` 公開 machine-readable 契約與 materialized defaults。
- `validate` 必須在外部操作前拒絕未知欄位。
- `diff` 以穩定欄位路徑比較設定，而不是比較 YAML 排版。
- `draft` 產生暫存 candidate；`apply` 驗證成功後才 atomic replace。
- Coding-agent Skills 必須透過這些命令修改設定，不可直接盲改 active config。
- Scholar／venue resolver 回傳 stable ID 與消歧資訊；多個候選必須由使用者明確確認。
- Offline fixtures 定義 adapter contract；live provider 可替換 adapter 而不改 use case。
- `skills/frontier-config/SKILL.md` 是自然語言設定流程的 portable Skill，不內嵌 LLM client 或 agent framework。
- 安全順序是 `schema/inspect -> draft -> resolve -> validate -> diff -> apply`；preview-only 或未消歧請求必須停在 apply 前。

## Render 與影片核准邊界

- Render 只讀取 `04-review/briefing.approved.json`，所有格式保存相同 claim fingerprints。
- HTML adapter 是逐篇論文的互動閱讀介面：研究問題分頁、Evidence 展開、原文頁碼連結、可放大的論文圖。使用者應能先理解論文，再查核原文；不能只列靜態摘要卡。
- Render 從已引用的本地 PDF 擷取附有 caption 與頁碼的原圖，記入 `assets-manifest.json.visuals`。找不到可驗證圖片時明示缺少素材，不生成貌似原圖的裝飾圖；圖像抽取失敗不得影響文字簡報。
- Slides 的目標 adapter 是 OpenSlide v2 project，並從同一份 `BriefingSpec` 與原圖素材產生。現有 HTML deck 為待替換的過渡版本，不是產品規格。
- Video preview adapter 透過外部 HeyGen TTS tool 取得 WAV 與原生 word timestamps；FrontierOps 不重作 TTS client，也不保存憑證。
- HyperFrames project 使用 scene sub-compositions、獨立音軌與 timed captions；同一 Run 重跑會重用既有旁白。
- `video_preview` 只代表可審核 composition。未經 preview 核准前，`missing_targets` 必須保留 `video`，Run 不得宣告完整成功。
- `rendering.video` 的 provider、voice、language、畫布、fps 與 quality 都由 YAML 控制，不得 hardcode 成隱藏政策。

## Runtime 與驗收

- Python 3.12 與 `uv` 是必要條件；`uv.lock` 與 `uv sync --locked` 保證可重現安裝。
- Build 需建立標準 stage output、`RunManifest`、state files 與可重建 SQLite index，且不得覆蓋舊 Run。
- Unit／integration tests 必須透過 `uv run --locked` 執行；未知設定欄位需明確失敗。
- Sync 只能由使用者觸發，保存 raw snapshots，並以 stable source ID 與內容雜湊做 delta comparison。
- Live arXiv 保存 base ID 與 version；Semantic Scholar 使用 stable author ID 與分頁 author-paper response。
- Local library root 預設限制在 project 內；PDF Evidence 保存 page／bbox，文字 Evidence 保存 line locator。
- OpenReview 使用官方 API v2 client，保存 forum、invitation、reply 與 decision provenance；認證只存在環境。
- Rank 輸出 Evidence、合格／排除候選與可重現 ranking report；factual explanation 必須引用 abstract 或 page-level Evidence。
- Brief 將跨來源候選聚合成 persistent developments，抑制 unchanged items，並產生可調時間的 renderer-neutral spec。
- Review 是發布邊界；schema、duration、duplicate、Evidence reference 與 numeric-support 錯誤都必須阻擋核准。
- Video preview 驗收至少包含 HyperFrames lint、browser runtime、layout、caption safe zone、contrast 與人工 snapshot 檢查。
