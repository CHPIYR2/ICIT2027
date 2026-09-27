# 人工審查包 v2 — DRAFT_UNREVIEWED

Event: `ev_812f8057d7c974d9cf36`。不是 gold；請人工審查與簽核。

complete_allowed_evidence.json.gz 是完整 [-60,+60) E/N/M；allowed_lineage.json.gz 是包內 p→m→e、m→a 關係。
B0_E/N/EN 與 retrieved/receipt 是固定預算結果；完整證據與 top-k 必須分別檢查。
command_address_observation 只含命令地址的 opaque 靜態映射，原始地址與控制值不在本包。
amendment_claims 提供通過有限一致性檢查的 m+a+M 與同資產 capture-time 候選；amendment_insufficiency 保留不足原因。
命令地址與同資產 E 的時間關聯不能證明執行、物理效果、因果、惡意或歸因。
reported_state_change 為選配，單筆 state 只算 reported_value，不影響最低問題充分性。
請審查 meaningful facts、aliases、support sets、較強但不被支援的敘述、unknowns 與機械驗證可行性。
