# FrontierOps

FrontierOps 是一個 agent-agnostic 的研究前沿簡報 Harness。它不自行實作一套 Agent，而是提供可配置、可追蹤、可重現的研究資料處理流程，讓 Codex、Claude Code 或其他 Agent 能透過穩定介面執行工作。

## 目前做到哪裡

規劃中的完整 Pipeline 是：

```text
Build -> Sync -> Rank -> Brief -> Review -> Render
```

目前已實作到 **Review** 階段，功能包括：

- 驗證 `frontier.yaml`，未知欄位會直接失敗。
- 將有效設定解析成標準化的 resolved config。
- 建立唯一且可重現檢查的 Run 目錄。
- 保存環境資訊、設定雜湊、Stage Result 與 Run Manifest。
- 提供 Unit tests、Integration tests 與可執行的 `frontier` CLI。
- 由使用者執行 `frontier sync` 才比較上次成功狀態；不啟動背景排程。
- 保存 immutable raw cache，並以 stable external ID 與內容雜湊避免重複訊號。

Sync 支援凍結 fixture、arXiv／Semantic Scholar live provider、OpenReview 與本地 PDF／文字庫。Rank 會依 YAML Gate 與可解釋分數挑選新研究，Brief 產生可調時間的 `BriefingSpec`，Review 則在發布前阻擋缺少 Evidence、引用失效、數字無依據、重複研究與超時內容。Render 已能產生可切換論文問題與查核證據的互動 HTML、OpenSlide v2 投影片專案，以及含 HeyGen 旁白與 word-level 字幕的 HyperFrames preview project。最終 MP4 必須在人工預覽核准後才編碼，因此 preview 不會被誤記為已完成的 `video`。

Slides 由 OpenSlide v2 真正產生 React `Page[]` deck，來源位於 `05-render/open-slide/`，並引用有頁碼的論文原圖。進入該目錄後執行 `npm install`、`npm run build`，即可得到 `dist/`；用 `npm run preview` 開啟 `/s/frontier-briefing`。PDF 可從 OpenSlide 工具列匯出，PPTX 目前只支援圖片式匯出，不能假稱為可編輯的原生 PPTX。參考 [OpenSlide export 文件](https://open-slide.dev/docs/core-feature/export)。

Live arXiv 依 `paper_ids`、`queries` 或 `categories` 查詢並保留 base ID 與 version。Semantic Scholar 依 tracker 中已解析的 stable author ID 分頁取得論文；`SEMANTIC_SCHOLAR_API_KEY` 是選用項，未設定時使用公開無金鑰額度。Live smoke test 不放入 deterministic CI。

Local Library 由 `sources.local_library.roots` 注入。相對路徑以 `frontier.yaml` 所在目錄為基準，預設禁止 root 或 symlink 逃出 project；PDF 交由 PyMuPDF adapter 解析並保留 1-based page 與 bbox locator，Markdown／文字檔則保留 line-range locator。

OpenReview 使用官方 `openreview-py` v2 client，保留 submission forum、note、invitation、reply 與 decision provenance。Offline fixture 是 deterministic demo 路徑；live mode 只從設定指定的 token 或 username/password 環境變數讀取認證，不會保存 secret value。

Rank 會對前 `deep_enrich_top_k` 個合格候選產生結構化 Paper Explanation。若 local PDF title 可對應候選，會加入 page-level full-text Evidence；所有 factual explanation 欄位都必須引用 Evidence，找不到明示限制時則清楚標成 interpretation。

## 架構概覽

專案採用 Hexagonal Architecture，依賴只允許朝核心方向流動：

```text
CLI (driving adapter)
        |
        v
Composition Root -> Application Use Case -> Domain
                         |
                         v
                    Outbound Ports
                         ^
                         |
          YAML / Filesystem / Clock adapters
```

- **Domain** 不知道 CLI、YAML、檔案系統或其他外部服務。
- **Application** 編排 Use Case，並定義自己需要的 Ports。
- **Adapters** 負責與外界互動，但不放業務規則。
- **Composition Root** 是唯一組裝具體 Adapter 與 Use Case 的地方。

完整設計規則請參考 [`docs/system-spec.md`](docs/system-spec.md) 與 [`AGENTS.md`](AGENTS.md)。

## `src/` 目錄導覽

```text
src/frontierops/
├── __init__.py
├── build.py
├── config.py
├── identity.py
├── domain/
│   └── models.py
├── application/
│   ├── build.py
│   ├── config.py
│   ├── identity.py
│   └── ports.py
└── adapters/
    ├── build.py
    ├── cli.py
    ├── config.py
    ├── identity.py
    └── storage.py
```

### `domain/models.py`

系統核心資料契約，不依賴外層模組：

- `FrontierConfig`：整份 YAML 設定，包含 project、manual sync 與 briefing 輸出設定。
- `ResearchSignal`：論文、Benchmark、Code Release 等新發現或變更事件。
- `Evidence`：具有來源 URI 與 locator 的可引用證據片段。
- `BriefingCandidate`：通過 Gate 後可供排序與簡報使用的候選項目。
- `ResearchDevelopment`：跨來源、跨 Run 聚合出的研究發展。
- `BriefingSpec`：與 Renderer 無關、含時間與 Evidence link 的簡報規格。
- `RunManifest`／`StageResult`：記錄設定雜湊、Stage、輸出、警告與執行狀態。

所有 Pydantic models 預設拒絕未知欄位，避免拼錯設定卻被靜默忽略。

### `application/ports.py`

由 Application Core 定義的 outbound interfaces：

- `ConfigReader`：讀取原始設定。
- `RunRepository`：保存一個 Run 的 artifacts。
- `EnvironmentReader`：取得執行環境資訊。
- `Clock`：提供時間，使 Use Case 不必直接依賴系統時鐘。

未來接入資料庫、雲端 Storage 或不同 Config 格式時，應新增 Adapter，而不是修改 Domain。

`application/config.py` 實作 validated inspect／diff／draft／apply；`adapters/config.py` 提供 YAML 與 atomic write；根目錄的 `config.py` 是其 Composition Root。

`application/identity.py` 定義 scholar／venue resolution Use Case；目前由 `adapters/identity.py` 的離線 fixture 實作。Resolver 回傳 stable ID、affiliation、paper count 與 profile URL，同名候選不會被自動消歧。

### `application/build.py`

`BuildUseCase` 是目前唯一完成的 Application Use Case，負責：

1. 透過 `ConfigReader` 取得設定並交由 Domain model 驗證。
2. 計算 resolved config 的 SHA-256。
3. 產生唯一 `run_id` 並解析 workspace 路徑。
4. 建立 `StageResult` 與 `RunManifest`。
5. 將待保存的 artifacts 交給 `RunRepository`。

這一層不直接讀 YAML、不呼叫 `mkdir`，也不直接取得系統環境。

### `adapters/build.py`

目前的 driven adapters：

- `YamlConfigReader`：使用 PyYAML 讀取設定。
- `FileRunRepository`：將 JSON／YAML artifacts 原子化寫入本地檔案系統。
- `SystemEnvironment`：取得 FrontierOps、Python 與平台版本。
- `SystemClock`：提供 UTC 時間。

### `adapters/cli.py`

Driving adapter。解析 `frontier build --config ...`，呼叫 Build 流程，成功時印出 Run 路徑；設定或 I/O 錯誤時印到 stderr 並回傳 exit code `2`。

### `adapters/storage.py`

- `FileArtifactStore` 原子化讀寫 JSON／JSONL，並阻止路徑逃出 Store root。
- `SQLiteStateIndex` 建立可重建的 Run／Artifact 查詢索引。
- JSON／JSONL 是可直接檢查的 source of truth；SQLite 只負責加速查詢。
- 重複 Build 不會清空既有 cursor、identity 或 development state。

### `build.py`

Composition Root。它只負責把具體 Adapters 注入 `BuildUseCase`，並保留 `run_build()` 這個簡單的 Python 呼叫介面。

## Build 的資料流

```text
frontier.yaml
  -> YamlConfigReader
  -> FrontierConfig validation
  -> BuildUseCase
  -> FileRunRepository
  -> .frontier/runs/<run-id>/
```

每次成功 Build 會產生：

```text
.frontier/runs/<run-id>/
├── run-manifest.json
└── 00-build/
    ├── resolved-config.yaml
    ├── config-resolution.json
    ├── environment-report.json
    └── stage-result.json
```

並初始化長期保存的狀態基礎：

```text
.frontier/state/
├── source-cursors.json
├── identity-map.jsonl
├── development-index.jsonl
└── index.sqlite3
```

## 安裝與快速執行

需求：Git 與 `uv >= 0.12.20, < 0.13`。Python 版本由 `.python-version` 固定為 3.12。

```bash
uv sync --locked
uv run --locked frontier build --config frontier.yaml.example
uv run --locked frontier sync --config frontier.yaml.example
uv run --locked frontier rank --run <sync-run-path>
uv run --locked frontier brief --run <ranked-run-path>
uv run --locked frontier review --run <briefed-run-path>
uv run --locked frontier render --run <approved-run-path>
```

第二個指令成功後會印出本次 Run 的完整路徑。

如需 narrated video preview，於 YAML 額外啟用外部工具 adapter；路徑可使用絕對路徑，或相對於 `frontier.yaml`：

```yaml
rendering:
  video:
    enabled: true
    provider: hyperframes
    tts_provider: heygen
    heygen_tts_script: /path/to/media-use/audio/scripts/heygen-tts.mjs
    width: 1920
    height: 1080
    fps: 30
    quality: looks
```

`frontier render` 會在 `05-render/hyperframes/` 產生 `index.html`、scene sub-compositions、`narration.wav` 與 `narration.words.json`。同一 Run 重跑時會重用既有旁白，避免重複呼叫 HeyGen。憑證由 HeyGen CLI 的 credential store 或環境變數提供，不會寫進 config 或 Run artifacts。

影片畫面以論文的問題、方法原圖、結果與限制為主，不使用重複的卡片模板。先在 `05-render/hyperframes/` 執行 `npx hyperframes check`，再執行 `npx hyperframes preview --background` 人工檢查場景與字幕；未經核准不輸出最終 MP4。場景動態使用固定版 GSAP CDN；如在隔離／離線環境中預覽，需先提供該依賴。

## Config lifecycle

以下介面供使用者及 [`frontier-config` Skill](skills/frontier-config/SKILL.md) 建立安全的設定變更；要讓既有 Coding Agent 執行並檢查完整論文簡報，使用 [`frontier-briefing` Skill](skills/frontier-briefing/SKILL.md)。

```bash
uv run --locked frontier schema config --format json
uv run --locked frontier config inspect --config frontier.yaml
uv run --locked frontier config validate --config frontier.yaml
uv run --locked frontier config draft --config frontier.yaml --output /tmp/frontier-candidate.yaml
uv run --locked frontier config diff --old frontier.yaml --new /tmp/frontier-candidate.yaml
uv run --locked frontier config apply --candidate /tmp/frontier-candidate.yaml --config frontier.yaml
uv run --locked frontier scholar resolve --name "Alex Kim" --provider semantic_scholar
uv run --locked frontier venue resolve --name ICLR --year 2026 --provider openreview
```

- `inspect` 與 `draft` 會 materialize 所有預設值。
- `diff` 會輸出穩定的 JSON path、before 與 after，方便 Agent 與人類檢查。
- `apply` 會先驗證完整 candidate，再以 atomic replace 寫入；驗證失敗不修改目標檔案。
- 設定只保存 secret 的環境變數名稱，不應放入 API key value。
- Resolver fixture 只用於離線驗收；多個同名候選必須由使用者確認後才能寫入 tracker。

### 用自然語言建立設定變更

`skills/frontier-config/SKILL.md` 是可由 Codex、Claude Code 等既有 Coding Agent 讀取的 portable Skill。它不包模型或 Agent framework，而是把自然語言設定工作約束成可稽核流程：

```text
schema / inspect -> draft -> resolve identities -> validate -> diff -> apply
```

例如可對已載入 Skill 的 Agent 說：

> 請把研究簡報改成 10 分鐘、最多收錄 7 項，並先讓我確認變更，不要直接套用。

Agent 應先建立暫存 candidate，回報 validation 與 semantic diff；使用者只要求預覽時不得執行 `apply`。新增學者或會議若有多個 resolver candidates，也必須停在套用前要求使用者選擇。

## E2E 驗收步驟

### 1. 驗證安裝與全部測試

```bash
uv sync --locked
uv run --locked python -m unittest discover -s tests -v
```

預期結果：42 個測試全部顯示 `ok`，最後輸出 `OK`。

### 2. 執行真實 CLI 流程

```bash
uv run --locked frontier build --config frontier.yaml.example
```

預期結果：exit code 為 `0`，stdout 印出類似以下路徑：

```text
.../.frontier/runs/run_YYYYMMDDTHHMMSSffffffZ_<config-hash>
```

### 3. 檢查輸出 artifacts

將 `<run-id>` 替換為上一步印出的目錄名稱：

```bash
find .frontier/runs/<run-id> -type f | sort
uv run --locked python -m json.tool .frontier/runs/<run-id>/run-manifest.json
uv run --locked python -m json.tool .frontier/runs/<run-id>/00-build/stage-result.json
```

驗收條件：

- 五個 artifacts 全部存在。
- `run-manifest.json` 的 `status` 是 `success`。
- `stage-result.json` 的 `stage` 是 `build`。
- `stage-result.json` 的 `next_stage_allowed` 是 `true`。
- `resolved-config.yaml` 保留 `target_duration_seconds: 300` 與三種輸出格式。
- `.frontier/state/` 的三個狀態檔與 SQLite index 全部存在。

### 4. 驗證 Run 可重複且彼此獨立

再次執行 Build：

```bash
uv run --locked frontier build --config frontier.yaml.example
find .frontier/runs -mindepth 1 -maxdepth 1 -type d | sort
```

驗收條件：第二次輸出的 `run_id` 不同，第一次的目錄及內容仍然存在。

### 5. 驗證錯誤設定會被拒絕

複製 `frontier.yaml.example`，在最外層加入未定義欄位，例如：

```yaml
unexpected_option: true
```

再執行：

```bash
uv run --locked frontier build --config <invalid-config-path>
```

驗收條件：exit code 為 `2`、stderr 顯示 `build failed` 與 validation error，而且不會建立成功的 Run。

## Contribution rules

所有變更都必須透過 Pull Request。PR title 使用英文 Conventional Commit 格式，description 使用繁體中文；每個 PR 最多 600 個 counted lines，詳細規則見 [`AGENTS.md`](AGENTS.md)。
