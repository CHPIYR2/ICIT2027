# Phase 2A 人工標註入口

Phase 1 v2 已接受。本次只建立人工標註準備資料，尚無人工 gold、LLM 或研究效能評估。

請先讀 [Reviewer instructions](REVIEWER_INSTRUCTIONS.md)。以下四份工作表的 facts 都是空陣列，
blank_fact_template 的判斷欄位均未填。請另存 reviewer_annotation.json 後開始人工填寫。

| Pilot | 空白工作表 | 獨立候選數 | 數值 alias 建議群組 |
|---|---|---:|---:|
| ev_0961f1c2da8a257e3ebc | [開啟模板](pilots/ev_0961f1c2da8a257e3ebc/reviewer_annotation.BLANK.json) | 3758 | 249 |
| ev_21f18503563e6a677ae5 | [開啟模板](pilots/ev_21f18503563e6a677ae5/reviewer_annotation.BLANK.json) | 3721 | 249 |
| ev_812f8057d7c974d9cf36 | [開啟模板](pilots/ev_812f8057d7c974d9cf36/reviewer_annotation.BLANK.json) | 3648 | 249 |
| ev_ab03f537915a04bff66c | [開啟模板](pilots/ev_ab03f537915a04bff66c/reviewer_annotation.BLANK.json) | 3740 | 249 |

候選數包含 reported_change / electrical_change 的重複提案、同一 request 的弱／映射強度
版本及其他共享證據候選，不能當成獨立事實總量；實際自動合併數 = 0。每個目錄的
observation_candidates.DRAFT.json 與 deduplication_proposals.DRAFT.json 均保持 DRAFT_UNREVIEWED。
目前 state-change 候選 = 0，且永遠不列為最低充分性必要條件。

原始完整允許證據的路徑與 hash 已寫入模板。新的查詢工具
scripts/inspect_pilot_evidence_phase2a.py 預設查完整 universe，只有 --production 才切換為
64-entry 預算的檢索結果。工具支援 a_ 與 meta_，不會因命令地址沒有 fields 而查詢失敗。

填妥四份後，執行：

```sh
.venv/bin/python scripts/summarize_human_annotations.py --filename reviewer_annotation.json
```

它只統計 HUMAN_REVIEWED 的唯一事實、人工 alias 合併、三 view 的 answerability/actions、
checkability、Q1–Q7 人工判斷及暫無正例的類型；不計研究 performance。未簽核的摘要仍是暫定。
空白模板的 smoke check 已保存於 results/investigation-phase2a/blank_annotation_summary.json，
狀態 ANNOTATION_PENDING；這不是人審結果。

搭配文件：

- docs/investigation_fact_keys.phase2a.proposed.md：typed identity 與人工覆寫／合併規則。
- docs/investigation_matching.phase2a.proposed.md：未來 system-vs-gold matching 提案，數值容差待核准。
- docs/investigation_gold_isolation.phase2a.md：pilot 使用與 finalized evaluation gold 隔離規則。
- configs/investigation_protocol.v1.proposed.json：既有檔案 current hash + pending freeze hash，未定模型等欄位明確 null/pending。

尚待作者決定：reviewer/adjudication、salient facts 與 aliases、Q5/Q6 充分性、安全相關性語意、
數值／時間容差、最終 metric 分母、未來模型／prompt/token/成本，以及 evaluation gold 保管與存取規則。
reported_state_change optional 與 ASDU 45/47/50 範圍是既有決定，不需要重新定案。
