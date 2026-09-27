# Verifiable OT Incident Investigation with Electrical and Network Evidence

## Abstract

只回答四件事：

1. OT incident investigation 面臨什麼問題。
2. 為什麼單純 detection / LLM explanation 不夠。
3. 我們提出什麼 evidence-grounded + verification 方法。
4. 實驗回答哪三個 RQ。

不要在 abstract 花篇幅介紹 Random Forest classification。

最終結果尚未完成前，不填任何虛構數字。

---

# 1. Introduction

## 1.1 Problem

OT security monitoring不只需要指出事件可能與資安相關，也需要協助 analyst 回答：

```text id="g49dyy"
What happened?
Which assets were involved?
What network activity was observed?
What electrical/process effects were observed?
Which conclusions are actually supported?
```

---

## 1.2 Limitation of Detection Alone

利用既有實驗作 motivation：

在 Sherlock 的完整 protocol-aware 條件下，Network evidence 甚至可以讓部分傳統 classifier 完全區分目前事件。

但：

```text id="whfyup"
correct classification
≠
complete incident investigation
```

Classifier 不會自然回答：

```text id="0djffn"
why
what evidence
what changed physically
what remains unknown
```

---

## 1.3 LLM Opportunity and Risk

LLM 適合：

```text id="2mgvwr"
heterogeneous evidence synthesis
timeline summarization
natural-language investigation
```

但也可能：

```text id="ndusk0"
hallucinate facts
misread numbers
cite irrelevant evidence
confuse correlation with causation
overstate malicious intent
```

因此需要 evidence grounding + deterministic verification。

---

## 1.4 Proposed Approach

一句話：

> We propose a verifiable OT incident-investigation pipeline that grounds LLM-generated claims in electrical/process and network evidence and mechanically checks evidence references, assets, timing, numerical statements, and claim-specific support requirements.

---

## 1.5 Contributions

限制成三項。

### C1 — Cross-domain OT evidence model

建立 electrical/process + network evidence 的可追溯事件表示與 lineage。

### C2 — Evidence-grounded investigation

讓每個 substantive claim 綁定 evidence IDs，並區分 observed fact、temporal association、security interpretation 與 unresolved claim。

### C3 — Deterministic verification

以 claim-specific rules 驗證 evidence reference、asset、time、unit、numerical consistency 與 support sufficiency，評估能否降低 unsupported security claims。

不要把「使用 LLM」本身列為 contribution。

---

# 2. Background and Related Work

限制在三個 subsection。

## 2.1 OT / ICS Intrusion Detection and Process-Aware Security

介紹：

```text id="nl3m93"
network-based ICS IDS
process-aware IDS
cyber-physical evidence
```

目的：

說明 detection 很重要，但本研究不是提出另一個 IDS。

---

## 2.2 Security Incident Investigation and Explainable IDS

介紹：

```text id="pxptgc"
SOC investigation
alert explanation
incident reconstruction
forensic evidence
explainable NIDS
```

指出：

> explanation != verified investigation.

---

## 2.3 LLMs for Cybersecurity Investigation

介紹：

```text id="gu3z8x"
LLM incident summarization
security QA
LLM cybersecurity reasoning
hallucination / factuality
```

Research gap 最後收斂成：

> Existing work motivates LLM-assisted security investigation, but OT investigation requires cross-domain evidence and stronger guarantees that generated claims remain traceable to observable cyber-physical evidence.

---

# 3. Problem Definition and Threat Model

這節非常重要。

## 3.1 Event-Conditioned Investigation

明確定義：

輸入是一個已經需要調查的事件 scope。

不是 continuous attack detection。

---

## 3.2 Evidence Views

定義：

```text id="chzc3p"
E = electrical/process evidence
N = network evidence
M = static sanitized metadata
G = evaluator-only ground truth
```

G 永遠不能進 LLM/retrieval。

---

## 3.3 Investigation Objective

輸出：

```text id="4s3380"
observations
timeline
cross-source relationships
security interpretations
unresolved questions
```

---

## 3.4 Claim Semantics

區分：

```text id="exxq96"
observed fact
derived fact
temporal association
security interpretation
causal claim
unknown
```

這裡第一次明確寫：

> temporal association does not imply causation.

---

# 4. System Design

這是 paper 核心方法節。

建議放 Figure 1。

```text id="7ft3mr"
Electrical / Process Evidence ─┐
                              │
                              ├→ Evidence Retrieval
Network Evidence ─────────────┘
                                      ↓
                              LLM Investigation
                                      ↓
                              Structured Claims
                              + Evidence IDs
                                      ↓
                         Deterministic Verification
                                      ↓
                 Supported / Qualified / Withheld
                                      ↓
                       Verifiable Incident Report
```

---

## 4.1 Evidence Construction

介紹 EvidenceRecord、asset、timestamp、unit、lineage。

不要重複太多 Sherlock parser implementation。

---

## 4.2 Investigation Retrieval

如何依：

```text id="z4yxx5"
event
asset
time
network activity
electrical/process change
```

選 evidence。

---

## 4.3 Structured LLM Investigation

介紹 JSON schema。

每個 claim 必須有：

```text id="pa7ijb"
claim text
claim type
evidence IDs
```

---

## 4.4 Deterministic Verification

分成：

```text id="58lt1n"
reference
asset
time
numerical
unit
lineage
support policy
```

---

## 4.5 Evidence Sufficiency

輸出：

```text id="xwzemd"
SUPPORTED
QUALIFIED
INSUFFICIENT
```

不要允許：

> evidence 不足 → 自動改成 benign。

本 paper 是 investigation，不是 classifier。

---

# 5. Experimental Methodology

## 5.1 Dataset

Sherlock v3。

說明：

```text id="kw25d4"
power-grid co-simulation
network + process/electrical observations
cyber and benign OT events
```

同時揭露：

> E/N 可能共享 packet lineage，不是 independent sensors。

---

## 5.2 Investigation Event Set

說明：

```text id="vx6kct"
event families
scenario distribution
selection policy
annotation process
```

不要只寫總 sample 數。

---

## 5.3 Gold Annotation

說明人工 annotation：

```text id="7qvmzg"
observable facts
valid evidence
temporal relations
unsupported claims
```

最好報 inter-annotator agreement，如果最後有第二位 annotator。

若沒有，不可虛構。

---

## 5.4 Baselines

至少：

```text id="2zw85z"
B0 Deterministic timeline

B1 LLM + retrieval

B2 LLM + retrieval + evidence citations

B3 B2 + deterministic verifier

B4 B3 + insufficiency / withholding
```

另外做：

```text id="k67a4x"
E-only
N-only
E+N
```

來回答 RQ1。

---

## 5.5 Metrics

主要：

```text id="2ed3lb"
citation precision
evidence completeness
unsupported security-claim rate
numerical accuracy
asset consistency
temporal consistency
qualification/withholding accuracy
coverage
```

分類 accuracy 不再是主指標。

---

# 6. Results

現在先保留結果骨架，不填數字。

## 6.1 RQ1 — Value of Cross-Source Evidence

回答：

> E-only / N-only / E+N 在 investigation completeness 上有什麼差異？

期待分析：

```text id="a0fqrg"
N gives cyber/network context

E gives process/electrical consequence

E+N may provide a more complete timeline
```

但必須由結果支持。

---

## 6.2 RQ2 — Evidence-Grounded Investigation

比較：

```text id="euhflu"
plain/retrieved LLM
vs
citation-constrained LLM
```

關注：

```text id="myvtgl"
evidence completeness
citation precision
unsupported claims
```

---

## 6.3 RQ3 — Verification

比較 verifier 前後：

```text id="jjr1ow"
unsupported claims ↓
numerical errors ↓
asset/time inconsistencies ↓
```

同時報：

```text id="5enolw"
coverage
```

避免「全部拒答」看起來最好。

---

## 6.4 Case Studies

只選 2–3 個。

最好包含：

```text id="kxnd0p"
一個 verifier 成功攔下因果過度推論
一個 E+N 比單來源提供更完整 investigation
一個 evidence insufficient 的案例
```

不要拿 case study 代替 aggregate result。

---

# 7. Discussion

## 7.1 Detection vs Investigation

這裡可以重新提到之前 classifier 100% 的發現：

> 高 classification performance 不代表 investigation solved。

---

## 7.2 What Verification Can and Cannot Guarantee

可以：

```text id="izx32u"
check evidence existence
check numerical consistency
check timestamp relationships
enforce finite support policies
```

不能：

```text id="y6erqp"
prove attacker intent
prove physical causality
guarantee real-world truth
```

---

## 7.3 Deployment Implications

討論：

```text id="geoxft"
SOC / OT analyst assistance
auditability
cross-domain investigation
evidence traceability
```

不要聲稱已降低 analyst workload，除非做人因研究。

---

## 7.4 Limitations

必須主動列：

```text id="gagsil"
Sherlock is simulated power-grid data
event-conditioned investigation
limited number of recordings
shared E/N packet lineage
annotation subjectivity
LLM/model dependence
no semiconductor-fab validation
no causal ground truth
```

---

# 8. Conclusion

結論只回三件事：

1. OT incident investigation 需要的不只是 event classification。
2. Electrical/process + network evidence 能否增加 investigation completeness。
3. deterministic verification 是否降低 unsupported security conclusions。

不要在 Conclusion 擴張成 autonomous SOC / real-world deployment claims。

---

# Figures and Tables to Reserve Now

## Figure 1

**System architecture**

一定要有。

---

## Table 1

**Claim types and evidence-support rules**

例如：

| Claim | Required evidence | Allowed conclusion | Prohibited overclaim |
|---|---|---|---|
| command observed | network record | command observed | command executed |
| voltage changed | E observations | reported change | attack caused change |
| temporal association | time-aligned N+E | event A preceded B | A caused B |

這張表會是 paper 很有辨識度的核心。

---

## Table 2

**Experimental baselines**

B0–B4 × E/N/EN。

---

## Table 3

**Main quantitative results**

不要現在填數字。

---

## Figure 2

**Coverage vs unsupported-claim rate**

如果實驗成功，這可能比單純 bar chart 更有價值。

---

# One-Sentence Paper Test

任何時候研究開始發散，就回到這一句：

> **This paper investigates whether OT incident explanations generated from heterogeneous electrical and network evidence can remain useful while being traceable to observable evidence and mechanically verifiable against unsupported security claims.**

如果新增內容不能幫助回答這句話，先不要做。