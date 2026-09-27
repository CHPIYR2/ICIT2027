# Evidence contract v1 — 已核准凍結

內容稽核已完成，以下是第一版資料使用契約。Machine-readable 正式設定在
`configs/evidence_contract.v1.json`，逐欄清單在
`data/manifests/field_catalog.proposed.json`（涵蓋五份 mapping 的 10,188 個項目）。
每項列出 source member、parent PCAP、CA/IOA、asset、context、attribute、unit、
scale、E 候選資格、主觀測點是否曾看到、N payload 禁用及 leakage 風險。

三項設定已核准，雜湊見 `configs/protocol.v1.lock.json`。
目前已實作並測試 allowlist、來源、時限、洩漏與 lineage removal；
完整範圍與限制見 `docs/feature_spec.md`。

## E：可見的電氣／製程量測

來源固定為主觀測點 raw PCAP 中的 IEC-104 monitoring observations；不直接使用
發布的整個 state dict。需要同時符合：mapping context=MEASUREMENT、單位匹配、
訊息語意為量測／回報、在目前視窗可見、能追溯到 parent packet。
設定命令的 payload 不能當作已回報量測。

| 候選 family | 原始 attribute allowlist | 原始單位 | 視圖與權限 |
|---|---|---|---|
| voltage | voltage、voltage_from/to/hv/lv | PER_UNIT | E；可進 ML／LLM，須有當前可見 parent |
| current | current_from/to/hv/lv | AMPERE | E；同上 |
| active_power | active_power、active_power_from/to/hv/lv | WATT | E；同上；不是 energy |
| reactive_power | reactive_power、reactive_power_from/to/hv/lv | VAR | E；同上 |
| reported_state | is_closed、is_connected | NONE | E；只表示回報狀態，不證明獨立物理真值 |

排除 CONFIGURATION、tap_position 別名碰撞、初始值、state.test、malicious、
其他尚未列出的欄位。電壓 pu 不得直接改稱 V；原始 attribute 的完整展開名稱
已寫入 machine-readable contract。

Missing rule：沒有可見觀測即為 None + missing flag，不能補成 0。保留 quality、
actual observation time、last observation time。若沿用舊值，必須標記 stale，
不可用其不變來證明物理穩定；未來 observations 不得回填過去。
後續 estimator 所需 imputation／normalization 只能在每個 training fold 擬合，
不能把統計補值偽裝成 evidence record。

## N：網路與協定活動

來源與 E 相同的 raw PCAP，避免增加觀測點而破壞 matched comparison。

| 欄位 | 來源／parent | 允許用途 | 禁止事項 |
|---|---|---|---|
| observation_time | PCAP record capture timestamp | N timing、scope、LLM timeline | 不用絕對日期／recording 身分作 predictor |
| source/destination endpoint | IP/TCP header | N endpoint counts、核對通訊 | 不讓 raw IP 成為記住場景的分類欄 |
| ip_protocol、source/destination port | IP/TCP header | N 協定活動 | 不推斷未見攻擊意圖 |
| tcp_flags、packet_length | TCP header／record | N 連線行為、封包量 | TCP ACK 不等於控制命令被執行 |
| apci_format | IEC APCI | I/S/U 活動、TESTFR | 不把 state.test 放入 E |
| asdu_type、cause_of_transmission | IEC ASDU header | 命令／量測類型、activation confirmation | 不包含電氣 payload 或 setpoint 數值 |

所有 N 欄位都來自 raw bytes 的解析，不是 ground-truth labels。N-only 排除
電壓、電流、功率、開關值與設定值的 payload；CA/IOA 靜態對照屬 M。
Feature counts、rates、gaps 是 derived values，需要保存全部 parent 或可重算查詢。
TCP ACK、IEC activation confirmation、實際 process report 三者必須分開。

## M：三視圖共享的 metadata

| 欄位 | 來源 | ML／LLM 使用方式 | 風險與處理 |
|---|---|---|---|
| CA/IOA、element、context、attribute | data-point-map.json | sanitized 靜態對照 | 不合併 CONFIGURATION／MEASUREMENT |
| unit、scale | 同上 | 單位檢查／轉換 | 不猜測未驗證單位；不跨單位直接平均 |
| fixed vantage／asset scope | 已稽核的 static topology／PCAP mapping | 三視圖保持相同 | 不加入隱藏攻擊資產 |
| opaque event/evidence/source IDs | 由資料管線建立 | 只作索引／引用，不作 X | 私下 resolver 才能看到含場景／標籤的路徑 |

initial_value 雖在 mapping 檔內，仍不是靜態 M；description 自由文字與完整
scenario config 不直接傳入模型。metadata 與檔案位置只能用於資料管線及驗證，
不能透過 source_file 字串把 train/test、scenario 或 benign event 洩漏給模型。

## G：隔離的 ground truth 與模擬器資訊

| 欄位／來源 | 分類 | ML X／LLM／retrieval | evaluator／trainer |
|---|---|---|---|
| malicious | G | 禁止 | raw procedure 值用來核對事件標籤；state bool/str 不作布林轉型 |
| 原始 event id、description、attack_point | G | 禁止 | 事件家族、annotation／error analysis |
| event start/end/recovery | G | 不直接作 feature／prompt | start 僅依已明示的事件條件協議設定 scope；end/recovery 不決定裁窗 |
| events.json、events.jsonl | G | 禁止 | 事件 catalog 與評分 |
| physical.zip、initial_state、initial_value | G／quarantine | 禁止 | 物理真值與初始化稽核 |
| scenario config／playbooks | G／quarantine | 禁止整檔存取 | 僅稽核者建立已審查的 static M |
| control-center.zip、裝置 logs | quarantine | 首版禁止 | 後續若要使用，須另行稽核可見性與新版本契約 |

監督式訓練需要 y，所以隔離 trainer 可以讀 event_truth 作為 target；這不是
允許 G 進入 X。訓練／評分流程與 runtime evidence reader 必須分開。
本輪 evaluator catalog 含真值，不能整份放進檢索索引或 LLM。

## Lineage、遮蔽與時間

根 ID：archive SHA256 + member + packet index。子證據另有 APDU/object offset、
parent_ids 與 transformation version。公開 source_file 欄使用 opaque source handle；
原始路徑僅存在 verifier／loader 的 private resolver。

保留 observation_time=PCAP capture time。若協定確有 reported_time，分開保存；
沒有來源就設 None，不用 simulator time 補造。對本輪觀察到的無附帶時間 type-13
物件，不假設另有真實量測時間。超過決策截止時間的資料不得用於 features／retrieval。

移除原始封包時，所有衍生證據要 lineage-closed removal，aggregate 重新計算。
隱藏 E 表示或 N 表示，與移除整個物理來源是不同消融；前者也不能讓被隱藏的
payload 透過另一表示滲入。E+N 是互補表示，不是獨立多感測器佐證。

## 凍結紀錄

三項研究設定已由使用者於 2026-09-21 明確核准，正式版本是
`configs/evidence_contract.v1.json` 與 `configs/split.v1.json`；雜湊保存於
`configs/protocol.v1.lock.json`。原 proposed 保留為歷史。未來變更另立版本與理由。

目前 decoder、sanitizer、episode lineage、來源移除及 E/N feature extraction
已有實作與測試。封包內不同數值是不同「觀測回報」，不是接收端實際採用值或
物理真值；exact TCP retransmission 去重，同序號衝突另列 private audit。
只按 IEC quality flags 排除不合格量測，不預先依內容判定哪份回報可信。
`docs/feature_spec.md` 記錄完整公式與限制。分類、LLM/verifier 的不同里程碑
分別記錄，不把契約凍結等同於整個研究系統完成。
