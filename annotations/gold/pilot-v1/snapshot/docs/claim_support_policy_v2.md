# Approved command-target amendment — evidence/export v2

授權：results/investigation-v2/approval/author_approval.txt。舊分類契約及 Phase-1 v1 產物保留。
僅實作觀測、靜態映射、retrieval、B0 與人工 packet；不做 B1–B4 或 LLM API call。

## ID role audit

新增 a_[0-9a-f]{24} 只適用 address records、一般 claim citation、command address_evidence_id、
command-address asset relationships、temporal observation endpoints，以及相關 retrieval/visibility IDs。
command message ID 仍只准 m_；數值與 state 的前後／reported_value 只准 e_；gap 邊界只准 p_；
mapping 只准 meta_；scope/coverage 只准 d_。network/ack observation 不接受 a_；security basis 不盲目放寬。
command_address_maps_to_asset 必須同時引用 m+a+M；same_observed_asset 必須包含 a/e 與兩條 M 邊。
active schemas 在 schemas/*v2.json；舊 docs/*.proposed.json 保留歷史，不再作新版 runtime 規範。

## Command 與關係支援

無 exact_static_match：只說命令型 activation request 被觀察，不可說 target asset。
有 exact_static_match：m message、a child、static M 三者內容與 ancestry 必須相符，才可说
「captured request addressed to a control point mapped to asset X」。
資產關係只表示地址的靜態對應，不表示執行或控制結果。
same_observed_asset 的時間關聯另需 quality-valid E observation、channel→asset M，
兩邊 asset 完全一致；capture ordering 不升級為 execution、causation、malicious intent、成功入侵或 attribution。
新 B0 只發佈由已檢查欄位產生的固定語句，不機械宣稱驗證任意自然語言。

## 保留不足

missing、ambiguous、非允許 context/attribute、invalid address layout 均保留 child 或失敗記錄，
mapped control point / asset / M ID 一律 null，reason 明列。不以 gold 或猜測補 mapping。
實際 audited 類型只有 45/47/50；不擴 46/48/49/51。
raw CA/IOA、raw element、初始值、setpoint、select/execute 不進 public evidence。

## Optional state

reported_state_change 留在 ontology，但不作 event coverage 或 question sufficiency 必要條件。
只可從兩筆有效、同 channel、嚴格 ordered、不同 bool value 的觀測建立；單筆只算 reported_value。
零值、missing、initial_value 不得補出前後狀態。
