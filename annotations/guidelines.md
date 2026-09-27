# Phase-1 人工標註指南

所有 packets 與自動候選均為 **DRAFT_UNREVIEWED**，目前沒有任何人工簽核 gold。
每個 reviewer 只拿 annotations/events/<opaque event ID>/ 的單一完整包；不要開 evaluator catalog、
results/investigation-v1/audit/pilot_selection.private.json、分類結果或外部事件敘事。

1. 先看 review.md；它只是閱讀入口。complete_allowed_evidence.json.gz 是完整允許的 E/N/M，
   allowed_lineage.json.gz 保存其完整 p→m→e 關係。production retrieved_*.json 只是預算對照，不能限制 gold。
2. 可用 scripts/inspect_investigation_packet.py 查指定 ID/channel/time；預設只顯示前 20 筆，
   matching_records 顯示完整查詢分母；提高 --limit 或直接讀 gzip JSON 可看全部。
3. 在 annotation.DRAFT.json facts 中逐條新增 atomic fact、claim type、Q 編號、acceptable support sets、
   asset/channel/unit、capture times、可接受表述、禁止 overclaim、E/N/EN 各自可回答性與理由。
4. 原始觀測、數值衍生、時間關聯、安全解釋、因果主張與不足分開。reported_change/electrical_change
   對同 pair 是 alias，只計一個 fact。同一 p 的 N/E 表示不能當作兩個獨立 sensor。
5. 對 scope 前後都有值的 pair 與只有 pre／只有 post 的 pair 分開；pre-only 差值不能描述為事件後的變化。
   無有效 post 數值不等於 0；單筆 state 不代表 transition；沒有 state pair 不代表 unchanged。
6. 命令 target amendment 尚未核准，review packets 沒有 CA/IOA/control point。不得自己使用 gold attack_point
   補 asset。COT7、TCP ACK、S frame 不能混同或推論物理成功；時間關聯不能推論因果。
7. 完成各 claim type supportability_review：人工確認的支持／不足 examples、歧義、alias、能否機械檢查，
   註明 supportability candidate counts 與不足 probes 的不同分母，不相除作 accuracy。
8. 目前自動安全候選值 0 表示 B0 不自動核准安全語意，不代表沒有安全相關 observations；
   primitive_security_observations 另列 command、RST、numeric pair。請審查 review_required 是否具有足夠資訊量。
9. 建議兩位 reviewer 先各自標註，保留兩版並 adjudicate。只有一位時明示 single-reviewer，勿聲稱 IAA。
10. 填 reviewer、reviewed_at、signoff 後才有資格另存 annotations/gold/；正式評估前還需核准及 freeze。
    不得把本次作者核准 Phase 1 視為已簽核任何 event gold。

每條 gold 需保留三項獨立量：supportable_from_eligible_universe、complete_support_retrieved、
correctly_recovered_by_system。現在第三項一律未評分，不以 retrieval 成功代替事實恢復成功。

問題 Q1–Q7 固定在 configs/investigation.phase1.json。主 benchmark 建議最多 12 個 salient facts/event，
另列固定不足／過度推論機會；人工定案前不發布 completeness 或 unsupported rate。
