# Investigation Protocol v1 — Freeze Readiness Report

狀態：pilot-gold-v1 快照已建立；Investigation Protocol v1 仍是 freeze candidate，等待作者核准。沒有實作 B1–B4、沒有 LLM/API call、沒有研究結果。
方法：**single-reviewer gold，reviewer R1**。不聲稱 independent dual annotation、adjudication 或 inter-annotator agreement。四份已簽核標註逐 byte 未改。

## 1. Pilot gold manifest 與 hashes

[Pilot gold manifest](/Users/potinglu/Documents/ICIT2027/annotations/gold/pilot-v1/manifest.json)；[SHA256 seal](/Users/potinglu/Documents/ICIT2027/annotations/gold/pilot-v1/manifest.sha256)。
Manifest SHA256：`660ca033cd1c6a5bb9de98bb75c6a7ece5f28980716b9181152187e72c557d4a`。

| Event | 正向 / guardrail / questions | Reviewer / 簽核時間 | annotation SHA256 |
|---|---|---|---|
| ev_0961f1c2da8a257e3ebc | 11 / 6 / 7 | R1 / 2026-09-25T01:03:59+08:00 | `1e96e43b8dc48e076fa7e05db0d11e90bc52e321e4fa90c458991a763030a312` |
| ev_21f18503563e6a677ae5 | 5 / 6 / 7 | R1 / 2026-09-23T03:51:24+08:00 | `94b6a2d124ced29ac5c21bc39fc689361f370c6f930b4b40f0b7951ae8146af2` |
| ev_812f8057d7c974d9cf36 | 8 / 6 / 7 | R1 / 2026-09-24T02:37:06+08:00 | `d23ededc01e91a7ee7258478f8ff8fedb063ab930c25220af008be68a87b7024` |
| ev_ab03f537915a04bff66c | 6 / 6 / 7 | R1 / 2026-09-25T00:20:57+08:00 | `ea8339ced9ffcbbf90878aaa3af6ec9b39379afd58a2a526ba5453a04af772a4` |

共 30 正向、24 guardrails、28 reviewed questions、0 pending。98 個來源／政策／schema 檔案已 byte-copy 為唯讀 snapshot。Manifest 逐項包含來源 evidence hashes、reviewer/time、annotation schema、claim/export version 與 policy snapshot version。
快照同時記錄 annotation-time 政策與 prospective candidate 政策，明確區別：保存候選 hash 不等於已核准容差或追認新的人工判斷。改動須另建版本，不回寫此快照。

## 2. 非數值 matching 定案候選

Evidence ID／role、asset ID、channel ID、claim type、ASDU type／COT、boolean、unit 與 temporal order/scope 全部 exact；同一 event/view/version/bundle 內檢查完整支持，null 不是 wildcard。Fact key 用於 identity／去重，不能掩蓋錯值、錯型別或較強敘述。自然語言相似度不作主要 correctness 指標。
[完整 matching 規則](/Users/potinglu/Documents/ICIT2027/docs/investigation_matching.v1.candidate.md)；[機器可讀候選](/Users/potinglu/Documents/ICIT2027/configs/investigation_matching.v1.candidate.json)。

**待處理的 representation 差異**：8 筆人審 numerical facts 使用 electrical_change，既有 B0 使用 reported_change。Literal exact type 下不相等。人工 gold 未改；作者需接受 strict literal 行為，或另核准版本化的共同呈現 adapter。去重仍不可把同一 pair/quantity 算兩筆。

## 3. Empirical numeric precision

只讀四個 development pilot 的完整允許 E/N universe、canonical evidence 與兩個 Basic PCAP headers；未讀 32 個 evaluation events 來選 tolerance。11,849 筆有效 numeric E 都由 type13 float32 解碼，轉 Python binary64／JSON 可逐值精確 round-trip；另有 3 筆 type1 boolean。

| Unit | Numeric observations | Nonzero float32 ULP 範圍 | 六位小數 rendering 最大誤差（binary64 比較） |
|---|---:|---:|---:|
| AMPERE | 1618 | 1.16415322e-10–3.05175781e-05 | 4.99267578391e-07 |
| PER_UNIT | 2331 | 5.96046448e-08–1.1920929e-07 | 4.99511718655e-07 |
| VAR | 3950 | 4.4408921e-16–1 | 5.00003807247e-07 |
| WATT | 3950 | 1.11022302e-16–2 | 5.00003807247e-07 |

ULP 隨量級改變：例如大值 WATT 可到 2 W、VAR 可到 1 VAR，而小非零值非常細。這是儲存格式／觀察間距，不是儀器解析度、校正精度或物理誤差。
996 個有效 numeric pairs；91 個 zero-baseline pairs 無 percent。WATT／VAR 近零分母可產生極大百分比，不自動截斷或據此判安全相關。Binary64 subtraction 最大誤差約 1.68e-11（WATT），percentage 最大絕對算術誤差約 1.28e-4 percentage points（極大比值）；比較參考值仍依凍結公式重算。
兩個 PCAP header 均為 microsecond format（1e-6 s）；epoch timestamp 的 binary64 ULP 約 2.384185791e-7 s。Capture order 使用儲存值精確比較，不能把 display tolerance 當時序容差。
[完整精度數據](/Users/potinglu/Documents/ICIT2027/results/investigation-freeze-v1/numeric_precision.pilots.json)；[Derived rendering 檢查](/Users/potinglu/Documents/ICIT2027/results/investigation-freeze-v1/derived_rendering_check.json)。

## 4. 數值容差提案，需作者核准

`abs(pred-reference) <= max(atol, rtol*abs(reference))`，先通過所有 exact identity/type/unit/scope gates。參考值來自 cited evidence／凍結公式，不是人工 prose 的 rounded number。

| Profile | 絕對容差 | 相對容差 | 意義 |
|---|---:|---:|---|
| A（建議）typed numeric fidelity | 0 | 5e-8 | 至少 8 significant digits／round-trip JSON，zero 精確；保留微小非零值 |
| B（替代）six-decimal compatibility | 5e-7，依輸出單位 | 5e-8 | 六位小數半單位；對近零值較寬鬆，仍須 zero/sign gate |
| Duration rendering（獨立提案） | 5e-7 SECOND | 0 | 只容許 Δt 呈現四捨五入，order/equality 仍 exact |

A/B 適用已分析的 AMPERE、PER_UNIT、WATT、VAR，以及 derived PERCENT（percentage points）。其他數值單位 pending，boolean 一律 exact。5e-8 源自八位有效數字的半 decimal unit 誤差界，pilot values/differences/percent 的實際 rendering 均通過這個界；不是任意採用 1% 之類物理容差。
A 的 atol=0 是刻意的保守選擇，避免六位小數把小 WATT/VAR 訊號視為零。B 的 5e-7 源自六位小數；報表略高於半單位的 binary64 比較尾差應以精確 decimal/rational 比較處理，不暗中放寬。所有 active tolerance 欄位仍為 null，尚未套用評分。

## 5. Q5 語意

Q5 量測 N 與 E/process 的可支持 capture-time 關係，可為 episode_only 或 same_observed_asset。前者不宣稱相同資產；後者必須 m+a+control M 與 E+channel M 兩邊映射到同一 opaque asset。共享封包祖先的 same_capture_time 不是獨立佐證。時序不證明 execution、causation、intent、compromise 或 attribution。

## 6. Q6 語意

Q6 詢問哪些具體觀測／組合值得進一步安全調查，以及可支持的解釋界限。明確分開：observed evidence → supported relationship → human-judged investigation relevance → unsupported stronger interpretation。Command/RST/gap/大數值差／同資產時間關聯不自動成立 review_required，更不自動判 malicious 或 benign。四個 pilot 的 Q6 全部不足決定保持不變，不捏造正例。
[Q1–Q7 完整定義與最低支持](/Users/potinglu/Documents/ICIT2027/docs/investigation_questions.v1.candidate.md)；[Question definitions JSON](/Users/potinglu/Documents/ICIT2027/configs/investigation_questions.v1.candidate.json)。

## 7. Metrics

完整規格逐項列出 numerator、denominator、aliases、guardrails、qualified/withheld、micro/macro/event-level 聚合與 failures：
- Gold Fact Recall：recover 的唯一正向 gold / 固定 EN-positive gold；另報 view-conditional 與 modality ceiling。
- Supported Claim Precision：有完整 accessible support 的 atomic substantive assertions / 所有此類 assertions。
- Unsupported Claim Rate：未充分支持的 assertions / 相同 assertion denominator；另報所有位置的 stronger-security subset。
- Question Coverage：符合最低支持的 Q1–Q6 實質回答 / 6；Sufficiency：full-view diagnosis 與 retrieval-conditioned action 兩組分數及 joint / 7。Q7 不增加 substantive coverage。
- Citation Validity：正確 event/view/role/support 的 citation pairs / 全部 cited pairs；另報 citation coverage 與 cited complete-support，避免不引用而得滿分。
- Verifier disposition accuracy：對 B3 原始輸入 claim 作出正確 disposition、保留內容及 reason / 全部 verifier input claims；oracle 不來自 verifier 自己。另報 fixed positive+guardrail opportunity action accuracy。

每事件／baseline／run 都保存 n/d。Micro=sum(n)/sum(d)；先平均 event 內有效 runs，再等權 macro over events。零分母 NA，fixed-denominator failure 不剔除。以 event 配對比較三個 primary contrasts；facts/packets/runs 不是獨立樣本。尚未計任何研究結果。
[完整 metric definitions](/Users/potinglu/Documents/ICIT2027/docs/investigation_metrics.v1.candidate.md)。

## 8. Final controlled matrix candidate

| B | Primary input | LLM | Citation | Verifier |
|---|---|---|---|---|
| B0 | EN | 無，既有 structured deterministic baseline | 既有 evidence links | 既有 B0 checks |
| B1 | N | 同一待選模型 | optional | 無 |
| B2 | EN | 同一待選模型 | optional | 無 |
| B3 | EN | 同一待選模型 | required | 無 |
| B4 | EN | 重放同一模型生成的 B3 output | 同 B3 | deterministic verifier |

Primary contrasts：B1→B2 跨來源價值；B2→B3 citation/grounding；B3→B4 verification/publication。B4 不重抽 LLM 輸出，避免 generation noise。沒有 model-comparison primary arm。32×5=160 primary event-baseline cells 是計畫數，不是結果。
N 最多64筆；EN最多32+32筆，既有兩者48,000 bytes。B1→B2包含固定總預算下 N 配額與 EN retrieval 的差異，不能聲稱只改了 E 而 N 完全不變。B2/B3/B4 共用同一 EN bundle。
[完整 controls](/Users/potinglu/Documents/ICIT2027/docs/investigation_baselines.v1.candidate.md)；[Model / token / prompt pending fields](/Users/potinglu/Documents/ICIT2027/configs/investigation_model.v1.pending.json)。

## 9. Remaining author decisions

1. Choose numeric profile A or B (or explicitly justified alternative), duration-rendering tolerance and output precision.
2. Confirm literal exact claim-type matching versus an explicitly versioned common representation adapter; existing B0 reported_change differs from reviewed electrical_change. No facts changed.
3. Approve final matching, Q5/Q6, metric and controlled-baseline candidate as one protocol version.
4. Select provider/exact model snapshot, temperature/seed policy, input/output/evidence token budgets, prompt versions/hashes, repetitions, retry and cost budget.
5. Finalize evaluation gold/version, custodian/access controls and scoring-reviewer role under single-reviewer methodology; no second reviewer or IAA claimed.
6. Fix event-level uncertainty procedure and diagnostic reporting before evaluation inspection.
7. Authorize later baseline implementation and validate/hash final B0–B4 serialization, prompts and verifier code before protocol freeze.

Evaluation 隔離保持：development/pilot 可完善 protocol；看過 finalized evaluation gold/results 後不可在同一 frozen version 調 prompt/verifier/tolerance/metrics/retrieval。任何此類改動需要 new exploratory protocol version。不能宣稱此資料是 untouched test。

## 10. 精確 freeze 檔案清單與 readiness

目前精確列出 176 個既有檔案的路徑與 SHA256；其中 pilot snapshot 已封存，其餘仍是 candidate。
[逐檔 inventory](/Users/potinglu/Documents/ICIT2027/configs/investigation_protocol.v1.freeze_inventory.json)；[Protocol freeze candidate](/Users/potinglu/Documents/ICIT2027/configs/investigation_protocol.v1.freeze_candidate.json)。
未實作的 model-specific prompt、B1–B3 generation／共同 report serialization、B4 verifier，以及 evaluation-gold manifest／access controls 尚無定案路徑或 hash，已明列 pending，沒有假稱這些檔案已存在。實際 protocol freeze 前，必須補齊 exact paths/hashes 並重新驗證 inventory。
Pilot snapshot 的 version/hash/唯讀檔案防止無意覆寫，修改須另建版本；這不宣稱是外部不可竄改儲存服務。
驗證：121/121 tests，含7項新測試；4份 reviewed annotations byte-identical；98份snapshot seals通過；既有v2的1,089檔hash不變；numeric audit只用4pilots。
[驗證紀錄](/Users/potinglu/Documents/ICIT2027/results/investigation-freeze-v1/verification.json)。

**STOP：等待作者核准。Protocol 尚未凍結；沒有實作 B1–B4、沒有任何 LLM/API call、沒有研究結果。**
