# FrontierOps

FrontierOps 是一個 agent-agnostic 的研究前沿簡報 Harness。它不自行實作一套 Agent，而是提供可配置、可追蹤、可重現的研究資料處理流程，讓 Codex、Claude Code 或其他 Agent 能透過穩定介面執行工作。

## 目前做到哪裡

規劃中的完整 Pipeline 是：

```text
Build -> Sync -> Rank -> Brief -> Review -> Render
```

目前只實作第一個 **Build** 階段，功能包括：

- 驗證 `frontier.yaml`，未知欄位會直接失敗。
- 將有效設定解析成標準化的 resolved config。
- 建立唯一且可重現檢查的 Run 目錄。
- 保存環境資訊、設定雜湊、Stage Result 與 Run Manifest。
- 提供 Unit tests、Integration tests 與可執行的 `frontier` CLI。

目前尚未實作真正的論文同步、排序、內容解釋、Review，以及 HTML／Slides／Video 產生。因此現階段的 E2E 驗收，是驗證「設定檔進入 Harness，產生完整 Build artifacts」的流程。

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
├── domain/
│   └── models.py
├── application/
│   ├── build.py
│   └── ports.py
└── adapters/
    ├── build.py
    └── cli.py
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

## 安裝與快速執行

需求：Git 與 `uv >= 0.12.20, < 0.13`。Python 版本由 `.python-version` 固定為 3.12。

```bash
uv sync --locked
uv run --locked frontier build --config frontier.yaml.example
```

第二個指令成功後會印出本次 Run 的完整路徑。

## E2E 驗收步驟

### 1. 驗證安裝與全部測試

```bash
uv sync --locked
uv run --locked python -m unittest discover -s tests -v
```

預期結果：4 個測試全部顯示 `ok`，最後輸出 `OK`。

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
