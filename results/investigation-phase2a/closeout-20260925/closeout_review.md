# Phase 2A 四份 pilot 收尾檢查（待第一份簽核）

現有彙整腳本已通過：54 筆已審內容、0 筆待審、0 筆自動合併；其中 30 筆正向事實、24 條 guardrails。28 個問題判斷均已完成人審；3 件已簽核，ev_0961f1c2da8a257e3ebc 待事件簽核。

## 本次欄位整理

- 補齊 24 個 guardrail fact_key，以已審核的 event_id + gold_claim_id 建立穩定列識別鍵；沒有依文字相似度合併、沒有建立新的機械證據鍵規則。三個機械提案欄位維持 null，覆寫理由已附註。
- 55 個有完整正向支援集合的 fact/view 欄位已填入 production bundle 集合可得性。這是支援 ID 集合核對，不是系統回答正確性；沒有計算研究效能指標。
- 無正向支援集合的欄位維持 null，包含所有 guardrails；空集合不當成已取回。
- recovered_by_system 全部維持 null。
- 0961 的負電流差值文字由 absolute difference 修正為 signed difference；另一處補上空格。數值、引用、視角與人工判斷均未改變。
- 保留三件原始簽核時間，以 field_completion_audit.json 另記簽核後欄位整理。未代簽第一件。

## 0961 簽核範圍

11 筆正向事實：4 筆映射命令觀測、4 筆電氣差值、2 筆同映射資產時間關係、1 筆 E-side 通道資產映射。另有 6 條獨立 guardrails。18 項原始證據／時間線核對通過。觀測到零值不代表設備狀態；命令與时间關係不證明執行或因果；Q6 三視角不足不代表安全。

| 問題 | E | N | EN |
|---|---|---|---|
| Q1 | insufficient | supported | supported |
| Q2 | supported | insufficient | supported |
| Q3 | supported | supported | supported |
| Q4 | supported | supported | supported |
| Q5 | insufficient | insufficient | supported |
| Q6 | insufficient | insufficient | insufficient |
| Q7 | supported | supported | supported |

## 後續待定

本次是 development pilot 欄位收尾，尚未發布正式 gold 或凍結 protocol。第二位 reviewer／裁決政策、gold 版本及發布、數值／時間容差、模型設定與授權、evaluation gold 管理及隔離仍須逐項決定。四個事件的個別判斷不能自動當成全部 protocol 政策已核准。annotations/gold/README.md 的「尚無簽核」描述已落後於 pilot 進度，但 gold 發布本身仍未完成。

未呼叫外部 LLM、未使用 evaluator labels、未檢查 evaluation gold。
