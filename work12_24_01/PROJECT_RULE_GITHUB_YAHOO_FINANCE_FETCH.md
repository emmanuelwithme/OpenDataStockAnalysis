# 🏞️ 活水 AI 理財教練｜Yahoo Finance 真實資料擷取固定執行規則

使用者原文（2026/10/08；保留原句，不改字）：

> 記住，照抄，記在專案，以後抓資料要寫程式放在 GitHub 實際連線 Yahoo Finance 下載的資料。記住記住記住

## 執行要求
- 之後凡需 Yahoo Finance 股票／ETF 歷史資料，先編寫 Python / yfinance 擷取程式，提交至 GitHub，由 GitHub Actions 實際連線、實際執行下載。
- 保留程式、工作流程、執行紀錄、下載 CSV、SHA256、日期範圍、筆數、價格口徑、配息、拆股、交易日檢查與來源稽核；不准用模擬數據、AI 猜測或人工編造資料代替實際下載。
- Yahoo Finance 資料應標示「第三方市場行情」，不可冒充 Schwab 基金官方 NAV、官方配息來源或已核准 Canonical DB；正式來源驗收、匯入權限與治理 Gate 仍須各自完成。
- 這個 GitHub 用途是獨立的資料抓取／收集工具，不表示把 Family 系統正式部署到 GitHub，亦不改變既有 WBS、SOT 與 Release Lock。

## 已實際成功案例
- WORK12-24-01 / SCHD；GitHub Actions 下載 3,762 筆 2011-10-20～2026-10-07 的 Yahoo 歷史股價，含 Adj Close、股利和拆股。
- 公開原始抓取紀錄：https://github.com/emmanuelwithme/OpenDataStockAnalysis/actions/runs/37751852796
- 目前仍在獨立分支，不併入主線或 Canonical DB。

此檔是專案執行偏好紀錄，並非 Family 正式 WBS／母規則的治理變更。
