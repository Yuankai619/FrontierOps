# FrontierOps

FrontierOps 是給 Claude Code、Codex、GitHub Copilot CLI 等 Coding Agent 使用的研究簡報 Harness。研究人員用自然語言要求「設定研究範圍」、「看看新論文」或「解釋這篇論文」；Agent Skill 操作可追溯的 Python Harness。沒有背景排程：只有研究人員要求 Discover 時才執行 Sync，與上次成功同步比較。

首要成果是幫人理解論文的研究問題、方法、實驗支持與限制。可產生可互動 HTML、OpenSlide 原始投影片專案，以及在啟用影音相依與授權後的 HyperFrames 旁白預覽；預覽不等於已匯出的 MP4。

請從[網頁版使用說明](docs/index.html)、[完整手冊](docs/user-manual.md)、[AutoSci 四個 Skill 實測範例](docs/examples/autosci.md)或[系統規格](docs/system-spec.md)開始。

## Quick Start：先安裝 Agent Skill plugin

選擇你使用的 Agent 安裝一次；以下安裝命令須待包含 plugin 的 PR 合併到預設分支後才能從遠端 repository 使用。本機開發可將 marketplace 來源改為這個 checkout 的絕對路徑。Copilot 指 GitHub **Copilot CLI**，不保證其他 Copilot 產品表面有相同命令。

```bash
# Claude Code
claude plugin marketplace add Yuankai619/FrontierOps
claude plugin install frontierops@frontierops

# Codex CLI
codex plugin marketplace add Yuankai619/FrontierOps
codex plugin add frontierops@frontierops

# GitHub Copilot CLI
copilot plugin install Yuankai619/FrontierOps:plugins/frontierops
```

安裝 plugin 只讓 Agent 讀到工作流程；尚未安裝 Python Harness。開啟你的研究專案，對 Agent 說：「使用 `frontier-setup`，在這個 workspace 設定 FrontierOps。」若要明確呼叫 Skill：Claude Code 輸入 `/frontierops:frontier-setup`、Codex 輸入 `$frontier-setup`、Copilot CLI 輸入 `/frontierops/frontier-setup`；其餘三個 Skill 只需替換末尾名稱。Setup 會檢查環境，用 `uv` 安裝 Harness，執行 `frontier setup`，建立**實際可編輯的** `frontier.yaml` 和 `frontier_output/`；不覆蓋已有設定。`uv` 是必備前置工具，slides/video 另需 Node.js／npm。

接著可依序對 Agent 說：

1. 「用 `frontier-config` 追蹤我研究的主題／學者／會議，預設五分鐘、輸出 HTML 和 slides。」資訊不夠時 Agent 會詢問，不猜測學者 ID 或 Gate。設定先經驗證與差異檢查，才寫入 active YAML。
2. 「用 `frontier-discover` 看看自上次以來有哪些新研究。」Agent 手動執行 Sync＋Rank，交付 `frontier_output/discoveries/<run-id>.html`；可搜尋、篩合格／排除、展開 Gate 與分數理由。沒有新論文或來源失敗也會明說。
3. 「用 `frontier-briefing` 解釋這篇論文，做互動 HTML 與投影片。」Agent 對同一 Run 執行 Brief＋Review＋Render，交付 `frontier_output/briefings/<run-id>/`。影片需在設定中啟用，且旁白／MP4 額外受外部服務與核准限制。

`frontier.yaml.example` 只是版本控管的**離線示例／測試資料**，不是 active config；日常操作讀寫的是 `frontier.yaml`。新建設定預設關閉 live 來源，Config 後才開始抓論文。所有 Gate、權重、追蹤名單、時間與輸出格式都在 YAML，不寫死在程式裡。

## Agent 如何操作 Harness

研究人員只需四個 Skill；內部仍保持可重現的 `Build → Sync → Rank → Brief → Review → Render`，每一步輸出標準 Artifacts 與 Run Manifest，方便除錯。Review 是發布閘門：檢查 Evidence 引用、數字、重複與時間；通過才渲染。原文 Figure／關鍵段落優先於裝飾圖，找不到可靠圖時明示缺漏。

每次 Run 保存在 `.frontier/runs/<run-id>/`，同步狀態在 `.frontier/state/`，原始來源快照在 `.frontier/cache/raw/`；公開成果在 `frontier_output/`。舊 Run 不因下一次 Sync 被覆蓋。系統採 Hexagonal Architecture：`domain/` 定義契約，`application/` 編排用例與 ports，`adapters/` 對接來源、儲存及 renderers。

### 離線端到端驗收

開發者要在 clone 的 repo 中跑**無 API key 的離線端到端驗收**，才使用 `frontier.yaml.example`。它引用版控內的 fixture，不會修改研究人員的 active `frontier.yaml`。`sync` 印出的絕對 Run 路徑須帶入後面每一步：

```bash
uv sync --locked
uv run --locked frontier sync --config frontier.yaml.example
uv run --locked frontier rank --run <run-path>
uv run --locked frontier brief --run <run-path>
uv run --locked frontier review --run <run-path>
uv run --locked frontier render --run <run-path>
uv run --locked python -m unittest discover -s tests -v
```

驗收時開啟 `frontier_output/discoveries/<run-id>.html` 與 `frontier_output/briefings/<run-id>/index.html`；在公開成果的 `slides/` 中用 `npm install`、`npm run sync:skills`、`npm run build` 驗收 OpenSlide。預設 fixture 未設 HeyGen 授權，不應期待最終 MP4。完整命令與 YAML 欄位見[使用手冊](docs/user-manual.md)；變更規範見[AGENTS.md](AGENTS.md)。所有程式變動須以英文摘要式標題、繁體中文描述的 Pull Request 提交，每 PR 不超過 600 行 source／test／docs 變動。
