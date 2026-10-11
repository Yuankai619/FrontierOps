# AutoSci：四個 Skill 的實跑對話

論文：[AutoSci](https://arxiv.org/abs/2605.31468)（[PDF](https://arxiv.org/pdf/2605.31468)）。以下是研究者會說的話，不是交給 Agent 的驗收指令。這次在全新的 `ADSL/FrontierOps_test/autosci-revised-example/` 執行，只產生 HTML 與 OpenSlide，不測影片。

## Setup

在新的研究資料夾開啟 Coding Agent，輸入：

> setup

Agent 應檢查 uv、Git、Node/npm，安裝或使用 FrontierOps Harness，建立 `frontier.yaml` 和 `frontier_output/`。若目前目錄不明確，才問「要使用哪個資料夾？」。本次用本機 FrontierOps checkout 的 `uv run --locked frontier`；它從 repo 的虛擬環境執行，**不會把原始碼複製到研究資料夾**。遠端 plugin 安裝及 `uv tool install` 尚未在此範例實測。

實跑輸出：`created_config: true`，新設定通過驗證，來源尚未啟用。下一步只需指定論文。

## Config

> config https://arxiv.org/pdf/2605.31468

這個 URL 已指定一篇論文，Agent 不應要求你再寫長篇 prompt。它應取得 PDF，核對首頁書目，存進 `data/library/`，旁邊放同名 `.pdf.json`（作者、機構、日期、arXiv ID、預印本狀態等），再建立候選設定、驗證、比較差異，最後套用到 active `frontier.yaml`。若是單獨輸入 `config`，Agent 先讀現有設定，問「想新增或修改什麼？」。

本次設定啟用本地 PDF 庫，研究興趣為 automated scientific research、scientific agents、research memory；無引用數 Gate，停用 citation 排序特徵，沿用五分鐘與 HTML/slides 預設。沒有啟用網路來源、影片或背景排程。候選設定在 `.frontier/config-drafts/autosci.yaml`，只是待核對提案；**Sync 只讀 `frontier.yaml`**。兩份檔案不是並列生效。

## Discover

> discover

Agent 以 active YAML 執行使用者觸發的 Sync、Rank，然後開啟 Discover 頁。首次 Run `run_20261011T211534942740Z_5ecc5ccc`：新增 1、合格 1、來源錯誤 0。頁面列新增數、排名理由與歷次 Run；我在頁面勾選 AutoSci、按「儲存選取」，產生同一 Run 的 `02-rank/briefing-selection.json`。之後只需說 `briefing`，不必重複貼 candidate ID。

再次輸入 `discover` 得到另一個 Run `run_20261011T212004265500Z_5ecc5ccc`：新增 0、重複 1；時間表列前次新增 1、本次未變 1，並可展開先前收錄。此時不應再宣稱 AutoSci 是新論文，也不應對空的新候選清單直接 Briefing。Rank 的分數是設定下的排序，不是研究品質。

## Briefing

> briefing

Agent 使用**第一次 Run**的選取檔。`frontier brief` 產出的 deterministic 草稿誤把附錄的 `debate` 表格句子當研究問題，也把 GPU wiki 示例當研究意義；這是可重現的品質缺陷，不能直接發佈。Agent 對照 PDF 第 1、3、7、8、9、12、13 頁，修正問題、四個模組、實驗、限制與來源 ID，再執行 Review、Render。論文報告的 6.3/10 與 5.8/10 是 **PaperReview.ai 在 ICLR 目標設定下的自動評分**，不是人類審稿或 FrontierOps 分數。

本次 Review：`approved`、7/7 claims 有來源 ID、0 issues。請注意這只表示格式、來源 ID、數字等規則通過；Review **不會判斷語意是否真的被引文支持**。這一步仍依賴 Agent 回到原論文檢查。產出以每篇論文為單位：

- 互動 HTML：`frontier_output/briefings/run_20261011T211534942740Z_5ecc5ccc-3/papers/paper-1/html/index.html`。有書目、Executive summary、原文 Figure 1、問題／方法／實驗／限制分頁，以及可展開的來源證據。
- OpenSlide 原始專案：同目錄的 `papers/paper-1/slides/`。可執行 `npm install`、`npm run sync:skills`、`npm run build`。此版把原圖與機制解釋拆頁，並由 Agent 依 OpenSlide Skill 再加入原文 Table 4 的裁圖來解說實驗；這是範例的逐篇編輯，不是通用 Render 自動辨識 Table 4。

重做 Render 會建立 `-2`、`-3` 等目錄，不覆寫舊成果；最新 Render 的 `public_output_dir` 指向 `-3`。每次 Run 的 Delta、候選、選取、核准內容保留在 `.frontier/runs/<run-id>/`。這是流程 Demo，不是長期品質實驗；Claude/Copilot 遠端 plugin 安裝、影片、真正的同行審查均未驗證。
