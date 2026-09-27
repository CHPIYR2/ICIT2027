# Verifiable OT Incident Investigation — A–J 審閱提案

日期：2026-09-22。狀態：**方向依作者指示轉換；以下實驗設計仍待作者核准，未凍結、未執行 LLM。**

Working title: **Verifiable OT Incident Investigation with Electrical and Network Evidence**
中文：**整合電氣與網路證據之可驗證 OT 資安事件調查**。

本輪需求來源是作者貼上的 Research Direction Lock。原文副本見 research_direction_lock.md。
第 28–29 節要求先交付 A–J，再停止，等待 claim vocabulary、support policy、問題、事件集、
annotation、baseline 與 metrics 核准。本提案不改原分類／observability 程式、設定或結果。
舊鎖定檔已重新查核通過；Git 既有 tracked files 無修改。docs/ 仍依作者要求留在 gitignore。

研究問題照作者指定固定為：RQ1 跨來源調查完整性、RQ2 有引用的結構化調查可靠性、
RQ3 決定性支援驗證與不足時保留判斷的效益。任務是已知事件範圍的調查；不做未知起點偵測、
自動修復、攻擊者歸因或物理因果證明。原 N-FULL RF/GB 的 N=EN=1.000 及新 transport 條件
E-only 優於 EN 的結果都保留，僅作研究轉向的動機，不代表真實 OT 攻擊容易偵測。

## A. 可重用元件與實際界線

| 需求 | 現有程式 | 可重用部分／限制 |
|---|---|---|
| EvidenceRecord / Episode | src/evidence/schema.py | 來源、opaque IDs、時間、quality、父子圖、固定 −60/+60 秒驗證；並非 claim verifier |
| lineage | src/evidence/lineage.py | remove_sources 刪 root 與所有後代；真的移除來源時重算，不可保留 E 後代 |
| E/N views | src/evidence/views.py | records_for_view 只做 record 篩選；不是安全 retrieval 介面，E 父節點仍屬 N，不能直接將 canonical episode 交給 LLM |
| 可見性 | src/evidence/observability_v2.py | Transport projection、不可恢復隱藏尾段、public E 去除 parent headers；屬 transport-only 特例，需另建 investigation export adapter，不能拿它冒充 N-FULL |
| asset mapping | src/sherlock/build_v2.py 的 sanitize_mapping | quality-audited MEASUREMENT channel→opaque asset/unit/attribute；沒有可用的 command→asset linkage |
| episode 建構 | src/sherlock/build_v2.py、capture_v2.py、parser_v2.py | 已建立 119 個 canonical episodes、APDU 去重與 capture timestamp；只支援經稽核 layout，不代表接收端接受／執行 |
| 輸入 allowlist | src/sherlock/sanitizer.py | 嚴格 record/channel schema，隔離 G、raw filename、process payload 與 N；仍需給新 aggregate/M receipts 另定 schema |
| 數值計算 | src/features/extract.py | quality-valid 前後觀測、單位與 family 識別可參考；既有 max/mean/floor 特徵不能當作個別資產原始事實或百分比 |
| 統計 | experiments/paired_bootstrap.py | event 配對概念可重用；metric_vector 只支援分類，不能直接拿來算 investigation metrics |
| retrieval/verifier | 尚無完整元件 | 現有 schema/visibility 檢查是基礎，不是既有 investigation 系統 |

程式稽核發現的三個核心限制：

1. packet/message 的 asset_id 均設為 None；decoder 只對 monitoring type 1/13 保留 measurement objects。
   command 的 CA/IOA、setpoint、select/execute、request-response correlation key 不在現有 canonical N 中。
   第一版只能說「看到命令型 request」，不能說「命令控制 asset X」。本提案不擴 decoder；有需要須另提版本。
2. decoder 對 COT 做 `& 0x3f`，未保留 test / positive-negative bits。COT=7 只能表示該類 response 被觀察，
   不能聲稱 positive acknowledgement、accepted、execution success；TCP ACK、S frame、activation confirmation 分開。
3. 119/119 事件都沒有 reported_state 的有效 pre/post channel pair。仍有 Basic 20/35、Semiurban 24/48、
   Rural 14/36 事件在 post 看見至少一個 state channel。可報 observed state，不能據缺失推斷 state unchanged；
   是否有同一 post channel 的有效兩筆轉移，必須由實際原始 records 查核，既有摘要尚未回答。

reported_time 一律 None，因此所有排序只談 capture/observation time，不能當成實際設備作用時間。

## B. 缺少的元件

尚缺調查 claim schema、固定問題與 prompts、E/N/M field-scoped export、可重現 retrieval receipt、
B0 timeline、LLM runner、八類逐 claim checks、canonical qualified rendering、question-level sufficiency、
人工審查 gold、獨立評分與 coverage–reliability 報告。沒有預設已有這些功能。

最小新增只對應 RQ1–RQ3；不加向量資料庫、agent framework、deep IDS、fine-tuning、第二資料集或分類 tuning。

## C. 精確結構化 schema 提案

完整 JSON Schema Draft 2020-12：investigation_claim_schema.proposed.json。
verifier 結果 envelope：investigation_verification_schema.proposed.json。
兩者只是文件附件，尚未接入 src 或 runtime。

report 固定有 schema_version、event_id、evidence_view、citation_mode、claims、7 個 questions。
每個 claim 有 claim_id、question_ids、claim_type、claim_text、support_assertion、evidence_ids、
asset_ids、channel_ids、endpoint_ids、依 claim_type 選擇的 typed payload。禁止未列欄位。
共 13 個 claim types：作者原列 12 種，加上明確提案的 asset_relationship，用來回答 Q3 的
同資產／endpoint 關係；不默默加入任意類型。

範例形狀（示意，不是 gold 或模型輸出）：

```json
{
  "claim_id": "c_1", "question_ids": ["Q2"], "claim_type": "reported_change",
  "claim_text": "同一通道的兩筆回報電壓由 1.00 pu 變成 0.98 pu。",
  "support_assertion": "asserted", "evidence_ids": ["e_111111111111111111111111", "e_222222222222222222222222"],
  "asset_ids": ["asset_1111111111111111"], "channel_ids": ["ch_1111111111111111"], "endpoint_ids": [],
  "payload": {"before_id": "e_111111111111111111111111", "after_id": "e_222222222222222222222222",
    "before_value": 1.0, "after_value": 0.98, "operation": "difference", "result": -0.02,
    "unit": "PER_UNIT", "before_time": -2.0, "after_time": 3.0}
}
```

Schema 之外仍必須實作跨欄位 constraints：claim IDs 唯一、Q1–Q7 各一次、question 引用存在、
payload 所用 records 都在 evidence_ids、scope/view 與 runner 一致。B1 的 citation_mode 由 runner
固定 optional_baseline；B2 固定 required，模型不能自選來逃過 citation 規則。無引用且無不足標記
只允許出現在 B1 這個刻意不強制引用的對照，不能成為 production 的合格輸出。

unknown 亦須有可核對的 scope/coverage ID 或缺少條件說明；unknown 不等於 BENIGN。
JSON 語法驗證不代表 statement 受證據支持；故 schema 允許 security_interpretation 表達較強
結論，以觀察 baseline 是否過度推論，再由 policy 拒絕。verifier 不把 LLM 自稱 supported 當真。

自由 claim_text 不能被有限規則證明語意正確。B3/B4 只輸出由已檢查 typed payload 產生的固定語句；
原始文字保留供人類評分。若原文多出因果／意圖等語意，不因數字或引用通過就標整句 SUPPORTED。
無法機械確認的文字只允許較弱 canonical projection，標 QUALIFIED 或 INSUFFICIENT。

## D. Claim-support policy

逐類必要證據、允許／禁止推論與機械檢查見 claim_support_policy.md。
關鍵界線：命令≠執行、response≠物理完成、回報變化≠真實物理因果、先後≠因果。

## E. 人工 gold 計畫

見 investigation_annotation_policy.md。先開發 pilot，建立人工核准的固定機會集合與可接受證據組；
gold 不從 LLM 輸出或 verifier PASS 自動產生。先看 sanitized observable bundle、後看 evaluator G。
每條明列 E/N/EN 可回答性。最終 gold 必須具名 reviewer、版本與 adjudication 紀錄；未完成人工審查
就停止正式評估，不能用自動草稿代替。建議兩位獨立 reviewer；若只有一位則明示並取消 IAA 宣稱。

## F. 候選事件集

見 investigation_event_selection.md 和 investigation_event_candidates.proposed.json：
16 Basic 開發 + 32 Semiurban/Rural 評估；三場景、五份 recording，明列 IDs、選取規則及限制。
這是等待作者選定的清單，尚未凍結。並非新的 untouched Sherlock test。

## G. 精確 baseline matrix

B0–B4 全部比較 E/N/EN，15 cells；所有條件同 event IDs、同 Q1–Q7、同 scope。
B0 決定性 timeline；B1 結構化 LLM、citation 選填；B2 同模型加強制 citation；
B3 對**同一份 B2 輸出**做 verifier；B4 在同一 B3 結果增加 question-level sufficiency。
不重新呼叫 LLM 產生 B3/B4，避免將生成差異混入驗證效益。細節見 investigation_protocol.md。

## H. 精確 metrics

見 investigation_protocol.md：citation support precision、共同 EN-gold completeness、view-conditional
completeness、unsupported security-claim rate、數值／asset／時間一致性、withholding/qualification
適切率、Q1–Q6 實質 coverage、schema compliance、retrieval recall。
分母為零記 NA 並報 eligible count；不能把沒說安全主張當成 100% 正確。
三次生成先在 event 內平均，事件才是配對分析單位。人類 gold 為評分標準，不讓 verifier 自評。

## I. 最小實作順序

1. 作者審閱本 A–J，核准七項內容；選定候選 IDs，先凍結事件集以防依 LLM 表現挑事件。
2. 只建新 export/retrieval、claim schema 與 B0；用 Basic 開發集，不先開正式 eval 輸出。
3. 選 4 個開發 pilot 做人工標註：兩個 cyber（不同家族）與兩個 benign（不同操作），覆蓋
   缺測與有狀態回報；從已核准開發清單按公開規則選，不看模型結果。完善 guidelines，再人工審完全組 gold。
4. 建 deterministic checks 與合成邊界測試，先驗 reference/visibility/lineage，再驗 units/numeric/time/asset，
   最後有限 policy／sufficiency。這些 tests 是工程測試，不充作真實事件研究結果。
5. 接一個固定模型的 B1/B2；僅在 Basic pilot 檢查 schema／token budget／prompts。記錄 provider、
   snapshot、sampling、context limit、輸出上限與價格估算；未決參數必須在正式 freeze 前補齊。
6. 全部 prompt、retrieval、gold、policy、metrics、模型設定與 codehash 最終凍結；評估 32 件。
   B3/B4 從同 B2 輸出重放，報完整 15 cells 和配對 coverage–reliability。
7. 核心穩定後另表評估小型合成失敗；新資料或其他模型不在本輪自動擴張。

目前不做第 2–7 步。第一個可交付的實作里程碑應是「人工可審的 evidence bundle + B0 + 4 件 pilot
annotation」，不是先接 LLM API。

## J. 研究風險與控制

| 風險 | 控制與仍存在的限制 |
|---|---|
| Ground-truth leakage | selection/annotation/evaluator 程序隔離；runtime 只允許 opaque scope+E/N/M；不讀 catalog、family、playbook 或 physical truth |
| Shared lineage | E/N 共 PCAP，不能計為獨立感測佐證；同事實去重，root provenance 保留 |
| Annotation 主觀性 | 先 observable 後 G，獨立 review/adjudication；沒有第二人就不能宣稱 inter-annotator agreement |
| LLM hallucination | 原始輸出完整留存；schema 合法不等於正確；不靠另一個 LLM 當 gold 或主 verifier |
| 因果過度推論 | 限定捕獲先後、同資產與 observation；意圖、歸因、physical execution 無支援即 withheld |
| Citation without support | 除存在性外檢查 role、內容、完整 support set；人類評分整句，不只數 citation IDs |
| Retrieval failure | eligible 與 retrieved 分開；固定預算、report retrieval recall；top-k 沒找到不表示事件沒有 |
| 記錄數少 | 五份 recording，事件不是獨立 simulation；配對 CI 僅條件式描述，不宣稱新場景泛化 |
| Sherlock 已稽核 | 新任務且 outputs 未產生，但資料／家族已知；仍明示探索性，不稱 independent confirmation |
| E+N token / gold 優勢 | 固定總 evidence budget，報 token 數；同 EN-gold 主分母、view-conditioned 次分母一起列 |
| Verifier 自我循環 | final gold 由人審；評分規則獨立於驗證器 status；保留 verifier 錯拒與錯放 |
| 過度拒答 | unsupported rate 與 coverage 同報；all-withhold control 的實質 coverage 為 0 |
| 實測 vs 物理真值 | E 僅 reported observations；單位與時序不證明物理準確、接收或因果 |

**待核准清單：13 種 vocabulary、支援規則、Q1–Q7、16+32 事件提案、人工 annotation、15-cell matrix、metrics。**
本文依作者附件第 29 節停在此 gate；未開始完整 LLM 系統、沒有新實驗分數。
