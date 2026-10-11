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

研究人員入口收斂為 `Setup -> Config -> Discover -> Briefing`；前者建立真正的 `frontier.yaml` 與公開成果目錄，Config 使用自然語言與必要追問，Discover 內含手動 Sync＋Rank，Briefing 內含 Brief＋Review＋Render。六個原階段仍是可重現、可除錯的內部契約，不要求研究人員逐一操作。

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
- `project.output_dir` 預設 `frontier_output/`，保存可供研究人員直接開啟的成果；內部 Run 與公開成果分離。Setup 不覆蓋既有 `frontier.yaml`，新設定的來源預設關閉，產出先選 HTML／slides；影片須確認 TTS 與授權後啟用。
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
- `plugins/frontierops/skills/` 提供 portable Setup／Config／Discover／Briefing Skill；自然語言設定、使用者觸發的 Sync、Review 發布邊界及輸出查核由既有 Coding Agent 操作，不內嵌 LLM client 或 agent framework。OpenSlide source/build 與影片 preview/MP4 核准仍須明確區分；不得繞過主系統 artifacts。
- 安全順序是 `schema/inspect -> draft -> resolve -> validate -> diff -> apply`；preview-only 或未消歧請求必須停在 apply 前。

## Render 與影片核准邊界

- Render 只讀取 `04-review/briefing.approved.json`，所有格式保存相同 claim fingerprints。
- Render 會把可閱讀的 HTML、OpenSlide 專案與可用的 HyperFrames 預覽發布到 `project.output_dir/briefings/<run-id>/`，另附 `index.html` 與 `manifest.json`；公開目錄不含 Sync raw cache。重跑同一 Run 會建立帶序號的新目錄，不覆蓋既有成果。最終 MP4 與 preview 明確區分。
- HTML adapter 是逐篇論文的互動閱讀介面：研究問題分頁、Evidence 展開、原文頁碼連結、可放大的論文圖。使用者應能先理解論文，再查核原文；不能只列靜態摘要卡。
- Render 從已引用的本地 PDF 擷取附有 caption 與頁碼的原圖，記入 `assets-manifest.json.visuals`。向上裁切範圍須涵蓋 caption 前的整張向量／影像圖，而非固定高度的圖尾；找不到可驗證圖片時明示缺少素材，不生成貌似原圖的裝飾圖；圖像抽取失敗不得影響文字簡報。
- Slides adapter 從同一份 `BriefingSpec` 與原圖素材產生 OpenSlide v2 的 React `Page[]` 專案，位於 `05-render/open-slide/`。頁面以論文問題、方法原圖、結果與限制組織；每頁只有一個主訊息，原圖必須標明 Figure 與頁碼。輸出 `index.tsx` 是可編輯 deck source；執行專案內 `npm run build` 才得到 `dist/` 靜態展示站，PDF 由 OpenSlide 工具列匯出。
- Video preview adapter 透過外部 HeyGen TTS tool 取得 WAV 與原生 word timestamps；FrontierOps 不重作 TTS client，也不保存憑證。
- HyperFrames project 使用三段論文導向的 scene sub-compositions（問題／方法原圖／結果）、有頁碼的原圖、受控的進度與內容動態、獨立音軌與 timed captions；禁止重複卡片格、標題上方小標、全大寫裝飾字與無關的 pill。找不到原圖時需明示，不能生成貌似論文證據的假圖。同一 Run 重跑會重用既有旁白。
- `video_preview` 只代表可審核 composition。未經 preview 核准前，`missing_targets` 必須保留 `video`，Run 不得宣告完整成功。
- `rendering.video` 的 provider、voice、language、畫布、fps 與 quality 都由 YAML 控制，不得 hardcode 成隱藏政策。

## Runtime 與驗收

- Python 3.12 與 `uv >= 0.12.20, < 0.14` 是必要條件；CI 同時驗證 uv 0.12 與 0.13，`uv.lock` 與 `uv sync --locked` 保證可重現安裝。
- Build 需建立標準 stage output、`RunManifest`、state files 與可重建 SQLite index，且不得覆蓋舊 Run。
- Unit／integration tests 必須透過 `uv run --locked` 執行；未知設定欄位需明確失敗。
- Sync 只能由使用者觸發，保存 raw snapshots，並以 stable source ID 與內容雜湊做 delta comparison。
- Live arXiv 保存 base ID 與 version；Semantic Scholar 使用 stable author ID 與分頁 author-paper response。
- Local library root 預設限制在 project 內；PDF Evidence 保存 page／bbox，文字 Evidence 保存 line locator。
- OpenReview 使用官方 API v2 client，保存 forum、invitation、reply 與 decision provenance；認證只存在環境。
- Rank 輸出 Evidence、合格／排除候選與可重現 ranking report；factual explanation 必須引用 abstract 或 page-level Evidence。
- Discover 入口把 Sync＋Rank 結果呈現在 `project.output_dir/discoveries/<run-id>.html`，顯示本次新增／更新與先前 Run 的時間序列、合格／排除、每條 Gate 與排序特徵；舊論文只作歷史清單，不以新設定重算分數。若設定雜湊改變，頁面須提示比較範圍不同。不可把 heuristic 抽句或排序分數當成已查證的論文品質。
- `frontier discovery serve --run PATH` 僅綁定 loopback，提供暫時互動頁。研究者在頁面勾選後，伺服器驗證 Run ID 與合格 candidate ID，寫入 `02-rank/briefing-selection.json`；Brief 只採用此檔指定的候選。純靜態 HTML 只能下載同格式 JSON，無法直接改寫自己的檔案。選取檔是可追溯的 Run artifact，不需要資料庫；沒有選取檔時維持既有預設。
- 使用者操作面是可安裝的 Agent plugin（Claude、Codex、Copilot）及 Setup／Config／Discover／Briefing 四個 Skill。六個 CLI 階段仍保留可測試的 Artifacts，但不要求研究人員逐段下指令；plugin 只提供工作流程，Python Harness 由 Setup 透過 uv 安裝。
- Brief 將跨來源候選聚合成 persistent developments，抑制 unchanged items，並產生可調時間的 renderer-neutral spec。
- Review 是發布邊界；schema、duration、duplicate、Evidence reference 與 numeric-support 錯誤都必須阻擋核准。
- Video preview 驗收至少包含 HyperFrames lint、browser runtime、layout、caption safe zone、contrast 與人工 snapshot 檢查。
