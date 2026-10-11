# FrontierOps

FrontierOps 是研究前沿簡報 Harness，讓 Codex、Claude Code 等既有 Coding Agent 以可設定、可追溯的流程，協助研究人員快速理解新論文。它不是另一個 Agent framework，也不會在背景定時監控；**使用者執行 `sync` 才比較上次成功同步後的變化**。

先看可直接開啟的 [HTML 介紹頁](docs/index.html)。完整操作方式、所有 CLI 指令與 YAML 欄位請見[使用手冊](docs/user-manual.md)；[系統規格](docs/system-spec.md)說明契約與架構。可讀取的 Agent Skill 有[自然語言設定](skills/frontier-config/SKILL.md)和[論文簡報](skills/frontier-briefing/SKILL.md)。

## 目前可展示什麼

```text
Build → Sync → Rank → Brief → Review → Render
```

- Sync：離線 fixture，或接入 arXiv、Semantic Scholar、OpenReview、本地 PDF／文字庫；保存 delta、原始來源及 Run 歷史。
- Rank／Brief：由 YAML Gate 與權重篩選，對候選論文建立有 Evidence 的問題、核心想法、方法、實驗與限制解釋；簡報時間預設 300 秒但可更改。
- Review：阻擋缺乏 Evidence、來源失效、無依據數字、重複或超時內容；Render 只讀核准版本。
- HTML：可切換論文問題、展開 Evidence、放大原文 Figure、返回 PDF 頁碼。
- Slides：產生真正的 OpenSlide v2 source project；需再用 `npm run build` 建置展示站或從工具列匯出 PDF。
- Video：可選的 HeyGen 旁白與 HyperFrames scene preview；**未經預覽核准，不產生或宣稱已有 MP4**。

三種格式共用一份 `BriefingSpec` 和已查核來源，重點是解釋論文的論證，而不是把摘要放進重複卡片。若原圖不可驗證，系統會明示素材缺漏，不畫假的論文 Figure。

## Quick start

需求：Python 3.12、`uv >= 0.12.20, < 0.13`。以下使用不需 API key 的 fixture 設定；各步驟的 `<run-path>` 必須替換成 `sync` 印出的**同一個**絕對路徑。

```bash
uv sync --locked
uv run --locked frontier config validate --config frontier.yaml.example
uv run --locked frontier sync --config frontier.yaml.example
uv run --locked frontier rank --run <run-path>
uv run --locked frontier brief --run <run-path>
uv run --locked frontier review --run <run-path>
uv run --locked frontier render --run <run-path>
```

打開 `<run-path>/05-render/briefing.html` 閱讀互動論文解釋。要驗收 OpenSlide（另需 Node.js／npm）：

```bash
cd <run-path>/05-render/open-slide
npm install
npm run build
npm run preview
```

在瀏覽器開啟 `/s/frontier-briefing`。`npm` 僅用於 OpenSlide 的 JS 相依；Python 操作均使用 `uv`。若另行啟用影片 adapter，先在 `05-render/hyperframes/` 執行 `npx hyperframes check` 與 `npx hyperframes preview --background`，供人工核准後才編碼最終影片。

## 程式結構

專案遵循 Hexagonal Architecture：`domain/` 定義嚴格的設定與 Artifact 契約；`application/` 編排 Build、Sync、Rank、Brief、Review、Render Use Case 與 outbound ports；`adapters/` 封裝 CLI、YAML／持久化、來源與 renderer；`src/frontierops/` 頂層模組負責 composition。依賴朝 Domain 流動，不把外部 API 或 UI 細節放進研究政策。

每個 Run 位於 `.frontier/runs/<run-id>/`，分階段保存 `00-build` 至 `05-render` 及 `run-manifest.json`；`.frontier/state/` 保存上次成功 Sync 的 cursor 與索引，`.frontier/cache/raw/` 保存來源快照。舊 Run 不會因下一次 Sync 被覆蓋。

## 驗證與貢獻

```bash
uv run --locked python -m unittest discover -s tests -v
```

所有變更都必須透過 Pull Request；英文摘要式標題、繁體中文描述、每個 PR 不超過 600 行 counted source／test／docs 變動。完整規則見 [`AGENTS.md`](AGENTS.md)。
