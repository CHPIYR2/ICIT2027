# Sherlock 獨立操作來源稽核

日期：2026-10-13。機器可讀摘要：`results/ebrl-provenance-audit/summary.json`。  
稽核只讀既有 manifest、內容稽核與 `data/evaluator/event_catalog.json`。沒有打開模型可見證據，也沒有重新下載約 8.95 GB 封存。

## 目錄實際計數

Evaluator catalog 有 **119** 筆事件，與 2026-09-20 內容稽核一致：

| 場景 | 事件數 | 其中 |
|---|---:|---|
| 01-Basic | 35 | train 良性 7；test 良性 10、cyber 18 |
| 02-Semiurban | 48 | train 良性 9；test 良性 10、cyber 29 |
| 03-Rural | 36 | test 良性 8、cyber 28 |

論文舊稿的「Basic 16 筆開發、評估 32 筆」沒有對應的凍結挑選規則。此切分標為 **NOT_CONFIRMED**。Catalog 上的 cyber/benign 是 evaluator-only，不得進入 proposer、檢索或 verifier。

## 有沒有 command → execution → effect 的連接鍵

**未確認。** 因此自然 Sherlock 配對的 \(g_c=0\)，R3/R4 的事實正確率標 **NA**。這不是「已經證明資料集裡完全沒有這種欄位」。原始封存不在這台機器上，不能逐筆重讀。

保存下來的樣本只支持下列判斷：

- `physical.zip` 樣本的頂層鍵是 `timestamp` 與 `values`（匯流排電壓、功率等）。這是時間序列快照，不是帶命令 ID 的動作效果紀錄。稽核標記為隔離，不可進模型。
- `control-center.zip` 樣本是 `CONNECTION_CHANGE`，鍵為 `type`、`data`、`timestamp`。已保存的預覽沒有命令到遙測的連接鍵。通知檔很大，其他型別沒有在這次稽核裡逐類列舉。
- `events.jsonl` 在內容稽核裡只有雜湊，沒有保存紀錄內文。既有稽核已對過 procedure start 與 IPAL 事件起點；那是情境程序，不是單筆 IEC-104 命令的執行回執。
- 裝置 log 的保存首行是 `Instantiating VccDeployment`，屬於啟動紀錄。
- 主 PCAP 的 ASDU 統計含 type 45 命令與 type 13 量測。命令出現不能當成執行，量測出現不能當成物理真值。
- 設定與量測可能共用 `tap_position` 這類名稱但 CA/IOA 不同。實作把 context 不一致視為 `U`，不視為物理狀態已改變。

## 可以主張與不可以主張

可以主張：在模型可見的時間、映射與語意下，一筆候選最高寫到哪個用詞（R0–R2），以及何時必須棄答或提出有反證的非關聯。

不可以主張：Sherlock 上的操作關聯 precision/recall、命令已被執行、物理完成、因果、入侵、意圖或歸屬。R3/R4 的程式路徑只在呼叫端另行提供可見的獨立證據紀錄時啟用；合成測試使用了這種紀錄，不代表 Sherlock 有同樣的欄位。
