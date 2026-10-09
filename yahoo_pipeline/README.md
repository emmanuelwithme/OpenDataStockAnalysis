最後修改日期時間：2026/10/10 02:50（台灣時間）

# Yahoo Finance + ChatGPT 雙路線（個人研究版）

路線 A：ChatGPT 網路搜尋查詢最新行情及新聞；明確標示報價資料日、盤前盤後與資料延遲。這不是 Yahoo 官方即時 API。

路線 B：GitHub Actions 實際連線 Yahoo Finance，yfinance 下載全歷史日 OHLCV、Adj Close、配息與拆股，計算：

- 1、5、10、20年歷史 CAGR（日資料周年價）
- 3、15年 CAGR（相同月報酬序列複利）
- 歷史最大回撤、峰/谷/回復日期
- 高TD9、低TD9、KD、MACD、MA、EMV、RSI、ATR、量比

輸出：outputs/latest_snapshot.json、outputs/technical_summary.json、outputs/performance_summary.csv、outputs/data_status.json。

本資料夾執行：
~~~sh
pip install -r requirements-dev.txt
PYTHONPATH=. pytest -q tests
python -m yf_pipeline.cli --project-dir . --symbols VOO QQQ
python -m yf_pipeline.cli --project-dir .
~~~

GitHub Actions：台灣時間週二至週六 07:20（美股收盤後）；週一至週五 16:20（台股收盤後）。PR 執行離線測試加 VOO 真實連線測試；只有合併到預設分支後才啟用自動排程。資料只存在 Actions artifact 7 天，不公開提交原始行情。因目前此 repo 是公開的，尚未把行情輸出公開發送供 ChatGPT 連接器直接讀取。若要長期直讀請使用合適的私人儲存庫並確認資料授權。

Close 用於價格與技術分析；Adj Close 僅供稅前含息報酬近似。TD9 是簡化 setup，非券商官方 TD9。研究工具不下單。

資料授權：yfinance 非 Yahoo 官方授權行情供應商。文件限定個人研究及教育用途；商業化活水AI必須使用合法授權行情源。
