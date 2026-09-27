# Investigation gold annotation — 人工審查提案

狀態：待核准，尚無 human-reviewed gold。預定實作位置為 annotations/guidelines.md、
annotations/development/、annotations/events/（供審查的 evidence packets）、annotations/gold/。
所有 annotations 為 evaluator/reviewer-only，禁止 runtime retrieval/LLM 存取。

## E. 流程

1. 核准事件 ID 後，先從 16 件 Basic 開發清單挑 4 個 pilot：不同的兩個 cyber 家族及兩個 benign 家族，
   以既有 coverage 確保至少有一件 numeric missing 與一件 post-state observation；不看任何 LLM 成績。
2. 用原始允許 E/N/M 建人工查閱包，提供 timeline/channel query、capture quality 與 provenance；
   不先給 gold family、malicious、attack_point 或敘事。可瀏覽完整可見 event universe，
   不只看 production top-k bundle，避免讓 retriever 限制 gold。
3. 第一位標註者建立 observable facts 與 unknown。第二位独立檢查／標註同 evidence，均先看不到 LLM 輸出。
   第二位尚未確定，不能把建議流程寫成已完成或虛構 reviewer。
4. 再開隔離 evaluator metadata，只做家族 coverage 與檢查，不以真值敘事補出原來不可觀測的事實。
   若 G 讓 reviewer 新增 fact，必須獨立找到允許原始 evidence，且記錄此變更。
5. 討論分歧、保留原始兩份標註、adjudication 理由與最終版；在正式模型評估前凍結。
   若只有單一 reviewer，至少完整逐 claim 人審並承認缺少 IAA；不可把自動 draft/LLM text 當 final gold。
6. 先完成 pilot guidelines，再依相同規則審查選定開發／評估事件。開發 gold 可用於調流程；
   32 件 evaluation gold 由隔離 evaluator 保管，prompt/verifier 不按其錯誤改動。

自動工具最多產生 observation candidates、算術、ID/hash 對照，狀態固定 DRAFT_UNREVIEWED。
人工 sign-off 前不進 gold/，也不發布研究分數。所有人審結果需要 reviewer ID、時間、來源 hash、
schema/policy version、resolved disagreements；作者核准設計不等於代替逐事件人工 review。

## 標註單位與數量

每個 event 的主 benchmark 設定最多 12 個不重複 salient observable facts：最多 4 N、4 E、
2 asset relations、2 temporal relations。各 domain 先依 Q1–Q5 的信息價值、evidence quality 與時間覆蓋選，
不能只挑最大變化。實際無支援則留空，不能為達配額捏造。保留 reviewer rationale 與所有排除候選。
這是可管理的調查事實 benchmark，不宣稱列完事件的每一 packet fact。

同時為 Q1–Q7 各標 answerability 與 acceptable minimal support sets；另預定四個安全推論 guardrails：
command execution、physical causation、malicious intent/identity、由缺少警訊推論 benign/safe。
這些不是四個「真實攻擊事實」，而是固定的可回答性檢查機會。不可讓 gold 只含模型主動聲稱的事實。

## 每條 gold 的欄位

- gold_claim_id、event_id、question_ids、claim_type、atomic statement、typed payload。
- epistemic category：observed / derived_numerical / temporal_association / security_interpretation /
  causal_claim / unknown。causal_claim 在本契約通常應是 insufficient，不變成新的 runtime claim type。
- 一組或多組最小支援 evidence IDs、每個 ID 的 role、channel/asset/unit、capture time、canonical ancestry hash。
- 可接受同義表述／數值容忍、不可接受的 stronger interpretation；重複或 alias claim 的同一 fact key。
- E / N / EN 各自的 supported / partially_supported / insufficient，以及各自原因與最小證據组。
- eligible universe 的可回答性、指定 retrieved bundle 的可回答性分開：沒有 retrieval 不等於不存在證據。
- acceptable action：assert / qualify / withhold；unknown 的缺少前提與 scope。
- 標註／審查身分、版本、爭議及 adjudication。G 僅存 evaluator 區，不混到 public evidence packet。

## 概念邊界

Observed fact：在監測點出現特定 packet/message 或品質有效 reported value。
Derived fact：從指定相容 records 機械算出的差、duration、count，需保留完整支援。
Temporal association：capture 先後／同 timestamp，不證明真正設備作用次序或 causal chain。
Security interpretation：基於有限 observation 的調查提示；不得把 attack family 或 label 當 observable。
Unknown：可能是 view 不允許、retrieval 遺漏、無有效 pair、mapping 缺漏或 policy 不允許因果推論；要區分。

M 表中存在資產不表示事件涉及該資產；N command target 未保留則不能由 golden attack_point 補上。
只見一次 state 不能說「由開变關」；未見 state 不能說不變。acknowledgement 不能說 physical action 成功。

## 評分獨立性與一致性報告

最終模型輸出以隱去 baseline 名稱的方式交 reviewer；原始與發佈層分開標 claim support、完整性、overclaim。
可用固定 gold exact-match 支援 deterministic slots，但語意更強的 claim_text 仍需人工檢查；
自動 verifier 不是評分裁判。必要時補 gold 正確但未收錄的等價 support set，必須盲化、記錄版本、
一致重評所有 baselines，不能只為某模型加分；新的 benchmark fact 不能看結果後任意加入主分母。

若有兩位 reviewer，報 matching rule 固定後的 fact-set agreement，以及固定 question/guardrail slots 的
action agreement／Cohen's kappa、support-role agreement，附分母和 NA。不要把自由 claim set 未對齐就算 kappa。
若只有一位，報 single-reviewer gold 與抽查限制，不估不存在的 inter-annotator reliability。
