# Sherlock v3 內容稽核

**Phase 1 已完成下述範圍的內容稽核；證據契約與研究 split 為待確認方案，尚未凍結，尚未訓練模型。**

機器可讀結果：`data/manifests/content_audit/summary.json`、各場景 JSON 與
`followup.json`。版本與壓縮檔雜湊在 `data/manifests/sherlock_manifest.json`。
所有事件數由本地資料計算，不以網站或論文事件數代替。

## 版本與稽核範圍

固定版本：[Sherlock v3 / Zenodo 18467070](https://zenodo.org/records/18467070)，
DOI `10.5281/zenodo.18467070`。三個 ZIP 共 **8,945,078,763 bytes**，均符合官方
MD5，已另外計算 SHA256。版本依 record 頁面及 changelog 確認，API 的
`metadata.version` 未提供字串。來源 metadata 已保存；授權為 CC BY 4.0。

| 範圍 | 本輪檢查 |
|---|---|
| 28 份 PCAP | 全量 25,167,133 個封包紀錄的檔案框架、時間、長度及基本協定檢查 |
| 5 份 process state | 全量 216,028 筆 JSON 的 schema、欄位集合、時間、null／非有限值與初始化檢查 |
| 5 份 IPAL event 標註 | 全部 119 事件逐一對照 raw procedure 的相同起點與 malicious 值 |
| 5 組 mapping、initial state、scenario config；3 份 rules | 全檔解析與轉換規則核對；未執行資料集程式 |
| Raw event logs、裝置 logs | 全檔讀取；事件 log 結構化解析，裝置 log 行數／格式盤點 |
| 5 份 physical.zip、5 份 control-center.zip | 完整內部成員清單，首個有效資料檔 schema 取樣；整批隔離 |
| 網路／電網圖 | SVG 全檔 XML 解析；PDF 僅檔案清單與雜湊，未渲染 |

PCAP 的 application probe 檢查單一 TCP segment 中完整的 APDU；本輪觀察到的
TCP/2404 payload 無未解析尾段。這不是已驗證的 production TCP reassembly，
APDU 數也未去除 retransmission，不可直接當成正式特徵。
Quarantined physical/control-center 的巨量內容未逐筆語意驗證；來源辨識、清單
與 schema 已完成，第一版排除它們作為模型輸入。

## 本地事件數

| 場景／官方 recording | Cyber | Benign | 合計 | PCAP 數 | State rows |
|---|---:|---:|---:|---:|---:|
| Basic train | 0 | 7 | 7 | 4 | 43,204 |
| Basic test | 18 | 10 | 28 | 4 | 43,204 |
| Semiurban train | 0 | 9 | 9 | 6 | 43,207 |
| Semiurban test | 29 | 10 | 39 | 6 | 43,207 |
| Rural test | 28 | 8 | 36 | 8 | 43,206 |
| **合計** | **75** | **44** | **119** | **28** | **216,028** |

119 個 IPAL event 的 start 均唯一對上 raw log 中一個 procedure start，原始
malicious 布林值與 IPAL ID 的 benign 標記全部一致，沒有未解決或不一致列。
Cyber 家族為 Industroyer、Drift-off、Control-and-freeze、ARP spoofing DoS；
benign 包含維護、發電控制、開關／拓樸變更等。每份 recording 的精確家族計數
在對應 audit JSON，未把 raw notifications 合併為新的研究事件。

原始 event log 的 28／6,712／48／16,730／10,609 列是 notifications，不能當成
獨立安全事件。Ground-truth catalog 在 `data/evaluator/event_catalog.json`，
只能供隔離的 trainer target y、評分、annotation 與 error analysis 使用。

## 影響實驗正確性的發現

### 1. malicious 不是乾淨的二元欄位

每筆 state 均有 malicious，型別包含 bool 和 event ID 字串。Benign ID 也是
非空字串；直接做 `bool(row['malicious'])` 會把這些良性事件判成 true。
禁止它進入 X／retrieval／LLM，標籤由已核對的 evaluator catalog 取得。
原始 ID、描述、檔名與 recording 名稱同樣不能成為模型特徵。

### 2. 初始化與未觀測通道

Basic 與 Rural 首筆 state 完全等於 initial_state；Semiurban train 首筆
3,565 欄中 3,548 欄仍等於初始值，test 為 3,549 欄。部分差異符合已接收
float32 觀測的精度，但未逐項重建官方 state 的生成過程。

第一版 E 候選 mapping 中，Basic train 的 314 個通道只有 256 個在主觀測點
整份 recording 的 application probe 中出現，Basic test 為 287/314。
欄位存在不能代替實際觀測；未收到值的通道應為 missing，不能使用 initial_value。

### 3. 缺失值與 stale state

五份 state 全量掃描均沒有 JSON null 或 NaN/Infinity，不能據此宣稱觀測無缺失。
三份 rules 各有 472／3,623／1,896 個 NaN→0 轉換；state 以 1 秒間距持續輸出，
也有完全相同的相鄰列，缺少逐欄最近量測時間。
本輪可解析的 type-13 物件未發現非有限 float 或高位 quality flag；這不是
所有 missing／通訊中斷／來源缺失的證明。Packet-derived evidence 必須保存
None、quality、last_observation_time 與 missingness。

目前 [IPAL timeslice](https://github.com/ipal-ids/ipal_transcriber/blob/master/state_extractors/timeslice.py)
及 [state extractor](https://github.com/ipal-ids/ipal_transcriber/blob/master/state_extractors/state_extractor.py)
與初始化、沿用舊值、固定時間切片的行為一致。唯讀副本與 SHA256 已保存於
`docs/sources/`、`followup.json`。它們僅為佐證；本地資料未附當時的 transcriber
commit，不能宣稱這就是生成 v3 的完全相同版本。

### 4. Semiurban state.test 屬於 N

Semiurban test 第 1,420 筆開始新增 state.test=1，時間為 1743599823.367243。
這個欄不在 mapping 或 named rules。本地主 PCAP packet **75,736** 於
1743599822.509228 含 APDU `680443000000`，附近還有同類 TESTFR 訊息。
[官方 IEC-104 transcriber](https://github.com/ipal-ids/ipal_transcriber/blob/master/transcribers/iec104.py)
把 U-format test 訊息表示為 `{'test': 1}`。

所以不能把整個 state dict 直接視為 E-only。這個欄應排除於 E，N 若使用測試
活動，需由原始協定訊息重建。欄位名稱含 test 不等於它是 ground-truth 標籤。

### 5. 設定／量測別名碰撞

Rules 把不同 IOA 的 tap_position 合併成相同 asset:attribute 名稱：Basic 有
2 個、Semiurban 58 個、Rural 2 個此類重複名稱。例：Semiurban 101.10010 是
CONFIGURATION tap_position，101.10020 是 MEASUREMENT tap_position。
Evidence identity 必須保留 CA/IOA、context、asset 與 parent packet；首版 E
候選暫不納入 tap_position。不能把設定命令當成物理狀態已改變的證據。

### 6. 觀測點重複，不是獨立感測器

Basic train 前 2,000 個 TCP/2404 identity 取樣中，n302 與 n318／n303／n321
分別有 376／314／62 個相同 flow/sequence/payload identity。比對排除路由途中
會變化的 TTL／checksum／MAC。例子與 packet index 在 followup.json；這是
重複觀測的證據，不是全資料去重率。

E 和 N 取自同一 PCAP 時是互補表示。候選主觀測點固定為 Basic n302、Semiurban
n406、Rural n402，已核對 SVG/config 的 control-center 角色。主觀測點沒有直接
看到 ARP frame；ARP spoofing DoS 的可見線索可能是通訊影響，不能把 simulator
記載的攻擊機制當成主觀測點已見證據。

## 時間與未來資訊

五份 config 的 recording duration 為 43,200 秒，wattson_speed 為 14。
Simulation-start 同時保存 wall_time 與 sim_time，兩者是不同時鐘。
IPAL event 起點與 raw notification timestamp 相同，全部落在主 PCAP 範圍內。
State 起點與主 PCAP 首封包相差 0–0.0135 秒，末筆 state 可比末封包晚約
0.4–0.53 秒。第一版採 **PCAP capture time／Unix 秒**，不乘除 14；simulator
時間只留在 evaluator。

本地 IPAL benign event 的 end 均比 raw procedure end 多 **30 秒**；cyber 的
end 與 raw procedure end 相同。不能用按標籤產生的長度裁模型視窗。
119 個事件到 recovery/end 的區間沒有互相重疊，但不等於事件統計獨立。

候選觀測窗 `[start−60s, start+60s)`，在 start+60s 決策。起點由 evaluator 提供，
必須明示 event-conditioned triage。固定窗在所有 recording 都沒有互相重疊。
60 秒是待確認的觀測延遲設定，未根據 held-out 成績選擇；不使用 gold end、
recovery 或 attack_point 來改變裁切與資產選擇。

## Layer 1 可行性與下一階段

**可以支持受限的事件條件式 E／N／E+N 研究，但不能直接把現成 state 當成乾淨 E。**

本地 PCAP 包含帶映射的量測／狀態物件、命令、APCI、COT、端點與時間資訊。
下一階段仍須實作 packet-derived evidence builder、sanitizer、lineage 與
matched feature tests；本輪沒有宣稱已完成這些程式或效能實驗。

建議 development 使用 Basic train+test，共 35 事件（18 cyber／17 benign）；
Semiurban train+test 與 Rural test 共 84 事件（57 cyber／27 benign）保留評估。
Official train/test 是原資料集命名，研究 split 另列，三視圖共用 event IDs／folds。

Basic 只有兩個 recording，且 cyber 只在其中一個。按事件做五折不等於按獨立
simulation run 驗證；多個視窗、封包或 LLM 重跑不能增加事件數。35 個開發事件
不支持大量特徵搜尋或深度模型，首個候選仍為 regularized Logistic Regression。
需按 scenario、recording、事件家族分列，保留 benign-only recording 的誤報率。
Event-cluster bootstrap CI 只反映已觀察模擬條件下的事件重抽樣，不代表真實世界外推。

完成：版本／hashes、核心資料全量掃描、事件交叉核對、時鐘、單位、觀測點、
欄位可見性與 lineage 風險盤點。未知的歷史 transcriber commit、現成 state 的
逐項 parent lineage、新鮮度都已列為資料限制，沒有補造。
接續審閱 evidence_contract.md 與 experiment_protocol.md；定案後再發佈 frozen
版本並實作最小 RQ1。LLM、Layer 3、sufficiency annotation 仍屬後續階段。
