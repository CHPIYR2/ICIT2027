# 人工審查證據包 — DRAFT_UNREVIEWED

Event: `ev_0961f1c2da8a257e3ebc`。本包不是 gold，待人工簽核。

complete_allowed_evidence.json.gz 包含完整 [-60,+60) 允許 E/N/M；不是 production top-k。
allowed_lineage.json.gz 提供同一包內的 p→m→e 父子關係。reported_time 未知；時序僅為 capture time。

完整來源數：{'packet': 1576, 'message': 782, 'process': 2991}。數值候選：249。

B0_E/N/EN 與 retrieved_E/N/EN 是固定預算對照；annotation.DRAFT.json 留待人工審查填寫。
不得將 evaluator metadata、攻擊描述或 classifier 輸出拿來補可觀測事實。
命令目標映射尚未核准，B0 不包含；命令≠執行、回報變化≠因果、missing≠benign。

請對照每個 claim type 的 DRAFT counts，記錄可支援／不足例子、歧義、alias 與可機械檢查性。
查看方法：Python gzip.open(..., "rt") + json.load；完整事件亦可用 scripts/inspect_investigation_packet.py 依 ID/channel/time 查詢。
