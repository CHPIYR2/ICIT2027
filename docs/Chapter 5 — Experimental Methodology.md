# 5. Experimental Methodology

We evaluate whether heterogeneous electrical/process and network evidence can support useful OT incident reconstruction while keeping generated conclusions traceable to observable evidence and mechanically checkable against predefined support requirements.

The evaluation is organized around three research questions:

**RQ1 — Cross-Source Investigation Value.**\
Does combining electrical/process and network evidence improve the completeness of OT incident reconstruction compared with either source alone?

**RQ2 — Evidence-Grounded LLM Investigation.**\
How reliably can an LLM generate structured OT incident explanations when substantive claims are required to cite observable evidence?

**RQ3 — Deterministic Verification.**\
Can deterministic evidence-consistency and support verification reduce unsupported security conclusions while preserving useful investigation coverage?

The experimental design separates two factors that would otherwise be confounded: the **evidence view** available to the investigator and the **investigation/verification method** applied to that evidence. The primary comparisons therefore change only one intended factor at a time.

Development runs used for implementation validation, output-capacity selection, schema testing, and execution debugging are excluded from the final research results.

---

## 5.1 Dataset and Evidence Source

We evaluate the proposed investigation pipeline using the Sherlock v3 OT security dataset, which contains power-grid co-simulation recordings with both network communication and electrical/process observations.

The dataset provides a suitable setting for studying incident investigation because individual events may contain complementary evidence about:

- OT network communication;
- protocol messages and command-type requests;
- communication timing and gaps;
- electrical/process measurements;
- reported value changes; and
- relationships between protocol control points, process channels, and simulated assets.

The study includes both cyber-related and benign operational events. However, the malicious/benign event label is not provided to the investigation model. Such labels remain evaluator-only information.

### Shared Evidence Lineage

Electrical/process and network evidence in this study should not be interpreted as independent sensor systems. Some observations may ultimately be derived from the same packet or simulation lineage.

We therefore interpret (E) and (N) as **complementary investigative representations** rather than statistically independent sensors.

Consequently, RQ1 does not test whether two independent physical sensors outperform one another. Instead, it asks whether exposing complementary electrical/process and network representations improves incident reconstruction under a fixed investigation budget.

---

## 5.2 Event Set and Experimental Separation

The protocol separates events into a **development set** and a **final evaluation set** before final evaluation execution.

The development set is used only for:

- evidence/export validation;
- schema validation;
- prompt and runner conformance;
- output-capacity validation;
- evidence-view isolation tests;
- deterministic-verifier testing; and
- execution and rate-limit validation.

Development outputs are not treated as research performance results.

The final evaluation set contains **32 preselected events**. The development set contains **16 events**. Event identifiers and scenario strata are fixed before final evaluation.

The final evaluation is executed only after:

1. experimental conditions are frozen;
2. prompts and schemas are frozen;
3. metric definitions and denominators are frozen;
4. evidence retrieval settings are frozen;
5. model configuration is frozen;
6. evaluation gold is committed; and
7. evaluation data access is separated from development execution.

The event, rather than the claim, packet, or LLM repetition, is the primary statistical unit.

---

## 5.3 Human Gold Annotation

Final evaluation uses human-reviewed investigation annotations rather than attack labels alone.

For each annotated event, the gold representation distinguishes:

- observable facts;
- acceptable supporting evidence;
- asset mappings;
- supported temporal relationships;
- permitted security-relevant interpretations;
- conclusions that are explicitly unsupported; and
- conclusions that should remain unresolved.

The annotation policy preserves the semantic boundaries defined in Section 3.4. In particular:

- command observation does not imply command execution;
- activation acknowledgement does not imply physical completion;
- a process change does not identify its network cause;
- temporal ordering does not establish causation;
- event labels do not make attacker intent observable.

### Single-Reviewer Annotation

Gold annotations are produced and reviewed under a predefined annotation and claim-support policy by a **single reviewer**.

We therefore do not report inter-annotator agreement, dual annotation, or adjudication.

Annotation subjectivity is treated as a limitation of the study.

### Positive Facts and Guardrails

The annotation contains two conceptually different components.

Let

[\
G_e\
]

denote the set of unique positive investigation facts for event (e).

These positive facts form the denominator for Evidence Completeness.

Separately, the annotation records unsupported or prohibited conclusions, including causal, malicious-intent, successful-compromise, or attribution claims that are not justified by observable evidence.

These guardrails are used to evaluate unsupported conclusions and withholding behavior, but they do not enter the positive-fact recall denominator.

---

## 5.4 Evidence Views and Retrieval Budget

We evaluate three evidence views:

[\
V_E,\
\quad\
V_N,\
\quad\
V\_{EN}.\
]

### Electrical/Process View

[\
V_E = E + M_E\
]

contains electrical/process records and the minimum approved metadata necessary to interpret those records.

It does not expose network messages or hidden network support.

### Network View

[\
V_N = N + M_N\
]

contains network records and approved network-related metadata.

It does not expose electrical/process values.

### Combined View

[\
V\_{EN} = E + N + M\_{EN}.\
]

The combined view contains both evidence domains and permits cross-source relationships only when the required evidence and mappings are simultaneously visible.

### Fixed Retrieval Budget

Evidence-view comparisons are performed under a predeclared fixed total retrieval budget.

The retrieval allocation is:

| Evidence view | Maximum evidence allocation |
| ------------- | --------------------------: |
| (V_E)         |                64 E records |
| (V_N)         |                64 N records |
| (V\_{EN})     |         32 E + 32 N records |

The serialized evidence bundle is additionally constrained by the frozen byte and evidence-input safety limits defined in the implementation protocol.

This design is important for interpreting RQ1.

The comparison does **not** estimate the effect of adding electrical evidence while keeping every network record unchanged.

Instead, RQ1 estimates:

> investigation performance under the same total evidence budget using different predeclared evidence-view allocations.

Retrieval ranking and quotas are frozen before evaluation and are not modified according to final model performance.

---

## 5.5 Experimental Conditions

Table 2 defines the final experimental conditions.

### Table 2. Experimental conditions

| Cell      | Evidence view | Generation method                  | Citation policy   | Deterministic verifier | Role                  |
| --------- | ------------- | ---------------------------------- | ----------------- | ---------------------- | --------------------- |
| **D0**    | EN            | Deterministic structured reference | Evidence-linked   | Reference checks only  | Descriptive reference |
| **G0**    | EN            | LLM investigation                  | Citation optional | No                     | RQ2 comparison        |
| **G1-E**  | E             | LLM investigation                  | Citation required | No                     | RQ1                   |
| **G1-N**  | N             | LLM investigation                  | Citation required | No                     | RQ1                   |
| **G1-EN** | EN            | LLM investigation                  | Citation required | No                     | RQ1, RQ2, RQ3         |
| **V1-EN** | EN            | Exact replay of G1-EN              | Preserved         | Yes                    | RQ3                   |

D0 is a deterministic structured reference and is not interpreted as an equivalent generative competitor to the LLM cells.

### G0 — Citation-Optional EN Investigation

G0 receives the combined evidence view but does not require every substantive assertion to contain complete supporting citations.

G0 is therefore described as **citation optional**, not citation free or ungrounded.

It provides the primary comparison for studying the effect of imposing the required-citation generation policy.

### G1-E, G1-N, and G1-EN

The three G1 conditions use the same citation-required investigation method and differ only in the visible evidence view.

They use the same:

- model snapshot;
- temperature;
- investigation questions;
- claim vocabulary;
- structured-output schema;
- output policy;
- metric definitions; and
- number of repetitions.

This makes the G1 family the primary RQ1 experiment.

### V1-EN

V1-EN receives the **exact raw G1-EN output** and applies deterministic evidence-consistency and support verification.

No language-model generation occurs in V1-EN.

For each repetition,

\text{raw output}(G1\text{-}EN)\
]

is verified by exact byte/hash identity.

Thus, the RQ3 comparison changes the verification/publishing layer while holding the original LLM output and evidence bundle fixed.

---

## 5.6 Research-Question Comparisons

### RQ1 — Evidence View

RQ1 compares:

[\
G1\text{-}EN\
\quad \text{vs.} \quad\
G1\text{-}E\
]

and

[\
G1\text{-}EN\
\quad \text{vs.} \quad\
G1\text{-}N.\
]

The independent variable is the evidence view.

The following variables remain fixed:

- event;
- LLM;
- prompt family;
- citation requirement;
- structured schema;
- question set;
- total evidence budget;
- repetitions;
- evaluation policy; and
- statistical treatment.

Both pairwise contrasts are reported.

An improvement relative to only one single-source view is not described as outperforming both single-source conditions.

### RQ2 — Evidence-Grounded Generation

RQ2 first characterizes the reliability of G1-EN itself and then compares:

[\
G1\text{-}EN\
\quad \text{vs.} \quad\
G0.\
]

The evidence view is held fixed at EN.

The principal difference is the requirement that substantive claims be accompanied by evidence citations under the citation-required structured generation policy.

Because G0 may still emit evidence identifiers, this comparison is described as:

> citation-optional versus citation-required generation,

rather than:

> citations versus no citations.

### RQ3 — Deterministic Verification

RQ3 compares:

[\
V1\text{-}EN\
\quad \text{vs.} \quad\
G1\text{-}EN\
]

for the same generated output.

The primary goal is to measure whether deterministic verification changes unsupported-claim behavior while retaining useful investigative information.

The verifier is not evaluated as a truth oracle and does not regenerate the incident narrative.

---

## 5.7 Investigation Questions

Each generated investigation addresses the same fixed question set.

**Q1.** What network activities were observed?

**Q2.** What electrical/process observations or changes were observed?

**Q3.** Which assets can be associated with the observed evidence?

**Q4.** What observable timeline can be reconstructed?

**Q5.** What temporal or cross-source associations are supported?

**Q6.** What security-relevant interpretation is supported by the available evidence?

**Q7.** What conclusions cannot be established from the available evidence?

Q1–Q6 measure substantive investigation coverage.

Q7 records uncertainty and unsupported conclusions and is evaluated separately through withholding/insufficiency metrics.

It is therefore not counted as an additional substantive-coverage opportunity.

---

## 5.8 Evaluation Metrics

No single metric is sufficient to evaluate incident investigation.

A system could obtain a low unsupported-claim rate simply by withholding every conclusion, whereas a system that produces high coverage could do so by inventing unsupported facts.

We therefore evaluate both **investigative usefulness** and **evidentiary reliability**.

### 5.8.1 Evidence Completeness

Evidence Completeness, also referred to as Gold Fact Recall, measures how much of the human-reviewed investigation can be correctly reconstructed.

For event (e),

[\
EC_e =\
\frac{\
|\hat{G}\_e \cap G_e|\
}{\
|G_e|\
},\
]

where (\hat{G}\_e) contains unique correctly recovered facts that are supported by evidence actually visible to the evaluated system.

The denominator (G_e) is identical across E, N, and EN conditions.

This common denominator is the **primary RQ1 completeness metric**, because it allows the three evidence views to be compared against the same desired investigation.

A fact that happens to exist somewhere in the full dataset does not count as recovered if its required evidence was not visible to the system.

---

### 5.8.2 View-Conditional Completeness

Some gold facts are inherently unavailable from a particular evidence view.

Let

[\
G\_{ev} \subseteq G_e\
]

denote the subset of gold facts that can be supported from the complete evidence view (v).

View-Conditional Completeness is

\frac{\
|\hat{G}*{ev} \cap G*{ev}|\
}{\
|G\_{ev}|\
}.\
]

This metric distinguishes two failure modes:

1. the information is unavailable from the view itself; and
2. the information is available but the system fails to retrieve or reconstruct it.

We also report

[\
\frac{|G\_{ev}|}{|G_e|}\
]

or the corresponding counts to show how much of the full investigation is theoretically answerable from each evidence view.

View-Conditional Completeness is supplementary to, not a replacement for, common-denominator Evidence Completeness.

---

### 5.8.3 Retrieval Recall

Retrieval Recall measures whether the retrieval layer supplies the evidence required for facts that are supportable under a given view.

\frac{\
\text{supportable gold facts whose complete support set was retrieved}\
}{\
|G\_{ev}|\
}.\
]

This metric separates:

- evidence unavailable in the selected view;
- evidence available but omitted by retrieval; and
- evidence retrieved but not correctly used by the generator.

---

### 5.8.4 Citation Precision

Citation Precision evaluates individual claim-evidence citation relationships.

[\
CP =\
\frac{\
\text{supporting visible claim–evidence citation pairs}\
}{\
\text{all cited claim–evidence pairs}\
}.\
]

A citation is counted as correct only when:

1. the evidence ID exists;
2. the evidence was visible to the generator; and
3. the cited evidence supports the role assigned to it in the assertion.

Citation Precision therefore measures more than evidence-ID validity.

---

### 5.8.5 Complete-Support Rate

Citation Precision can remain high even if a claim cites one relevant record while omitting another record required to support the full assertion.

Complete-Support Rate is therefore evaluated at the assertion level:

[\
CSR =\
\frac{\
\text{substantive assertions whose cited set fully supports the assertion}\
}{\
\text{all substantive assertions}\
}.\
]

Evaluator-added evidence is not used to repair an incomplete generated citation set.

---

### 5.8.6 Unsupported Security-Claim Rate

Unsupported Security-Claim Rate measures unsupported security-sensitive conclusions.

The evaluation includes substantive assertions involving:

- malicious intent;
- causal cyber-physical effects;
- successful compromise;
- command execution;
- attacker identity;
- attack success; and
- other security interpretations that exceed observable support.

For an event/run,

[\
USCR =\
\frac{\
\text{unsupported security-sensitive assertions}\
}{\
\text{all security-sensitive assertions}\
}.\
]

Evaluation is performed over the actual generated text and structured claims rather than relying only on the model-provided `claim_type`.

This prevents a causal or intent assertion from escaping review merely because it was assigned an innocuous claim type.

If a response contains no security-sensitive assertions, USCR is reported as **NA**, not zero.

---

### 5.8.7 Numerical Consistency

Numerical Consistency evaluates claims containing reported values, differences, percentages, or other deterministic numeric relationships.

A numeric assertion is correct only when:

- source observations are correctly identified;
- values match the cited evidence under the predefined tolerance policy;
- the claimed transformation is correct;
- units are compatible; and
- the claim scope is correct.

[\
NC =\
\frac{\
\text{correct numerical assertions}\
}{\
\text{all numerical assertions}\
}.\
]

A zero denominator is reported as NA.

---

### 5.8.8 Asset Consistency

Asset Consistency evaluates whether asset-bearing claims agree with the cited observations and approved metadata mappings.

[\
AC =\
\frac{\
\text{asset assertions with correct evidence-supported asset relationships}\
}{\
\text{all asset assertions}\
}.\
]

A timestamp match alone cannot substitute for an asset mapping.

---

### 5.8.9 Temporal Consistency

Temporal Consistency measures whether temporal assertions are consistent with the cited timestamps and required mappings.

[\
TC =\
\frac{\
\text{supported temporal assertions with correct ordering/scope}\
}{\
\text{all temporal assertions}\
}.\
]

Correct temporal ordering does not imply causal validity.

---

### 5.8.10 Q1–Q6 Substantive Coverage

Substantive Coverage measures whether the investigation provides useful supported content for the six substantive investigation questions.

[\
Coverage =\
\frac{\
\text{Q1--Q6 with at least one adequately supported substantive answer}\
}{\
6\
}.\
]

Empty responses, generic disclaimers, or unsupported content do not count as coverage.

Q7 is excluded because uncertainty itself should not allow a system to inflate substantive investigation coverage.

An always-withhold system therefore has:

[\
Coverage = 0.\
]

---

### 5.8.11 Required Withholding Recall

The annotation identifies opportunities where a stronger conclusion should be qualified or withheld.

Required Withholding Recall is:

[\
RWR =\
\frac{\
\text{required opportunities correctly qualified/withheld}\
}{\
\text{all required qualification/withholding opportunities}\
}.\
]

A decision is correct only when its action, scope, and reason match the predefined support policy.

---

### 5.8.12 Withholding Precision

Withholding Precision evaluates whether the system withholds only when withholding is justified.

[\
WP =\
\frac{\
\text{correct explicit qualify/withhold decisions}\
}{\
\text{all explicit qualify/withhold decisions}\
}.\
]

This metric is necessary because excessive withholding can reduce useful investigation coverage.

---

### 5.8.13 Schema Compliance

For delivered model responses, Schema Compliance records whether the response satisfies the frozen structured-output contract and local semantic validation requirements.

Provider-side schema acceptance alone is not interpreted as factual correctness.

---

## 5.9 Metric Summary by Research Question

### Table 3. Metrics used for each research question

| Metric                          |          RQ1          |     RQ2     |          RQ3          | Role                             |
| ------------------------------- | :-------------------: | :---------: | :-------------------: | -------------------------------- |
| Evidence Completeness           |      **Primary**      |  Secondary  |       Secondary       | Full investigation recovery      |
| View-Conditional Completeness   |       Secondary       |      —      |           —           | View-specific answerability      |
| Retrieval Recall                |       Secondary       |  Secondary  |           —           | Retrieval failure separation     |
| Citation Precision              |       Secondary       | **Primary** |       Secondary       | Evidence-link quality            |
| Complete-Support Rate           |       Secondary       | **Primary** |       Secondary       | Full assertion support           |
| Unsupported Security-Claim Rate |       Secondary       | **Primary** |      **Primary**      | Unsupported security conclusions |
| Numerical Consistency           |       Secondary       |  Secondary  |       Secondary       | Numeric correctness              |
| Asset Consistency               |       Secondary       |  Secondary  |       Secondary       | Asset correctness                |
| Temporal Consistency            |       Secondary       |  Secondary  |       Secondary       | Timeline correctness             |
| Q1–Q6 Coverage                  | **Primary companion** |  Secondary  | **Primary companion** | Investigation usefulness         |
| Required Withholding Recall     |           —           |  Secondary  |      **Primary**      | Required restraint               |
| Withholding Precision           |           —           |  Secondary  |      **Primary**      | Avoid excessive withholding      |
| Schema Compliance               |       Diagnostic      |  Diagnostic |       Diagnostic      | Execution/conformance            |

RQ3 does not define success using Unsupported Security-Claim Rate alone.

The result is interpreted jointly with Evidence Completeness and Q1–Q6 Coverage so that a system cannot appear safer merely by suppressing useful content.

No arbitrary maximum acceptable coverage-loss threshold is selected after observing results.

---

## 5.10 Human Review of Higher-Level Claims

Not every evidentiary judgment can be reduced to deterministic rules.

Reference validity, numeric relationships, timestamps, units, lineage, and many asset relationships can be checked mechanically.

Higher-level security relevance may require human evaluation.

In particular, positive Q6 interpretations and security/causal/intent statements are reviewed against the annotation policy rather than being automatically accepted merely because their constituent evidence references are valid.

The deterministic verifier is therefore evaluated as an **evidence-consistency and support mechanism**, not as an automated judge of incident truth.

---

## 5.11 Model Generation Protocol

All generative cells use the same fixed model snapshot and decoding configuration.

Each event-condition pair is executed for **three repetitions**.

The model snapshot, temperature, structured-output schema, prompt bytes, retrieval policy, and provider request configuration are frozen before evaluation.

The study does not select the best repetition.

All valid repetitions are retained.

Retries are permitted only for predefined transport or delivery failures and never because of:

- answer quality;
- metric score;
- missing citations;
- unsupported claims;
- verifier disposition; or
- factual correctness.

### Incomplete Provider Responses

A provider response terminated because it reaches the configured output-token limit is treated as an **incomplete delivery**, not as a valid structured investigation.

The response is preserved for provenance but is not repaired, regenerated based on quality, or completed using evaluator information.

Output-capacity configuration is selected using development-only validation and is frozen before final evaluation.

---

## 5.12 Repetitions and Statistical Unit

Metrics are first computed separately for each repetition.

For metric (m), event (e), condition (c), and repetition (r),

[\
m\_{ecr}\
]

is computed according to the fixed metric definition.

The three repetitions are then averaged within the event:

\frac{1}{3}\
\sum\_{r=1}^{3}\
m\_{ecr},\
]

subject to the predefined NA rules for claim-conditioned metrics.

The primary aggregate is the macro-average over evaluation events:

\frac{1}{|E|}\
\sum\_{e \in E}\
\bar{m}\_{ec}.\
]

The event is therefore the primary independent experimental unit.

Repetitions, claims, packets, and evidence records are not treated as independent samples.

Pooled claim-level or citation-level micro results may be reported as supplementary descriptive statistics.

---

## 5.13 Paired Contrasts and Confidence Intervals

RQ comparisons are computed as paired event-level differences.

For example, for RQ1,

## \bar{m}\_{e,G1-EN}

\bar{m}\_{e,G1-E},\
]

and

## \bar{m}\_{e,G1-EN}

\bar{m}\_{e,G1-N}.\
]

RQ2 uses:

## \bar{m}\_{e,G1-EN}

\bar{m}\_{e,G0}.\
]

RQ3 uses:

## \bar{m}\_{e,V1-EN}

\bar{m}\_{e,G1-EN}.\
]

Uncertainty is estimated using **2,000 scenario-stratified bootstrap resamples** with fixed seed:

[\
20270922.\
]

Entire events, together with all of their repetitions and paired condition outputs, are resampled as a unit.

We report 95% percentile bootstrap confidence intervals.

These intervals characterize uncertainty conditional on the evaluated event/scenario population and should not be interpreted as population guarantees for arbitrary real-world OT systems.

---

## 5.14 Missing Data and Zero-Denominator Rules

Metric denominators are defined before observing final evaluation results.

When a claim-conditioned denominator is zero, the corresponding metric is reported as:

[\
NA\
]

rather than as 0 or 1.

Examples include:

- no security assertions → Unsupported Security-Claim Rate = NA;
- no numerical assertions → Numerical Consistency = NA;
- no explicit withholding decisions → Withholding Precision = NA.

Counts are reported together with proportions so that NA-heavy conditions remain interpretable.

For fixed-denominator investigation metrics such as Evidence Completeness and Q1–Q6 Coverage, absence of a valid substantive answer does not remove the opportunity from the denominator.

Thus, a system that produces no useful investigation receives zero coverage rather than an artificially favorable missing value.

---

# 5.15 Planned Results Presentation

The final results are organized by research question rather than by implementation component.

No development-run numbers are inserted into the main quantitative tables.

## 5.15.1 RQ1 — Evidence-View Comparison

RQ1 reports E-only, N-only, and EN under the same citation-required generation method.

### Table 4. RQ1 — Evidence-view investigation results

| Metric                        | G1-E | G1-N | G1-EN | Δ EN−E [95% CI] | Δ EN−N [95% CI] |
| ----------------------------- | ---: | ---: | ----: | --------------: | --------------: |
| Evidence Completeness         |  TBD |  TBD |   TBD |             TBD |             TBD |
| View-Conditional Completeness |  TBD |  TBD |   TBD |             TBD |             TBD |
| Retrieval Recall              |  TBD |  TBD |   TBD |             TBD |             TBD |
| Q1–Q6 Coverage                |  TBD |  TBD |   TBD |             TBD |             TBD |
| Citation Precision            |  TBD |  TBD |   TBD |             TBD |             TBD |
| Complete-Support Rate         |  TBD |  TBD |   TBD |             TBD |             TBD |

The main text should interpret Evidence Completeness first.

View-Conditional Completeness and Retrieval Recall are then used to explain whether differences originate from evidence availability, retrieval, or generation.

The paper must not claim that EN is superior to both single-source views unless both predeclared contrasts support that conclusion.

---

## 5.15.2 RQ2 — Citation-Required Investigation

RQ2 compares citation-optional and citation-required EN investigations.

### Table 5. RQ2 — Effect of citation-required generation

| Metric                          | G0 Citation-Optional | G1-EN Citation-Required | Paired Δ [95% CI] |
| ------------------------------- | -------------------: | ----------------------: | ----------------: |
| Citation Precision              |                  TBD |                     TBD |               TBD |
| Complete-Support Rate           |                  TBD |                     TBD |               TBD |
| Unsupported Security-Claim Rate |                  TBD |                     TBD |               TBD |
| Evidence Completeness           |                  TBD |                     TBD |               TBD |
| Q1–Q6 Coverage                  |                  TBD |                     TBD |               TBD |
| Numerical Consistency           |                  TBD |                     TBD |               TBD |
| Asset Consistency               |                  TBD |                     TBD |               TBD |
| Temporal Consistency            |                  TBD |                     TBD |               TBD |

RQ2 should be interpreted as a reliability/coverage trade-off.

For example, if citation requirements improve Complete-Support Rate but reduce Evidence Completeness, both effects should be reported.

---

## 5.15.3 RQ3 — Deterministic Verification

RQ3 compares the same G1-EN output before and after deterministic verification.

### Table 6. RQ3 — Verification safety/coverage trade-off

| Metric                          | Raw G1-EN | Verified V1-EN | Paired Δ [95% CI] |
| ------------------------------- | --------: | -------------: | ----------------: |
| Unsupported Security-Claim Rate |       TBD |            TBD |               TBD |
| Evidence Completeness           |       TBD |            TBD |               TBD |
| Q1–Q6 Coverage                  |       TBD |            TBD |               TBD |
| Citation Precision              |       TBD |            TBD |               TBD |
| Complete-Support Rate           |       TBD |            TBD |               TBD |
| Numerical Consistency           |       TBD |            TBD |               TBD |
| Asset Consistency               |       TBD |            TBD |               TBD |
| Temporal Consistency            |       TBD |            TBD |               TBD |
| Required Withholding Recall     |         — |            TBD |                 — |
| Withholding Precision           |         — |            TBD |                 — |

The primary RQ3 interpretation must consider Unsupported Security-Claim Rate jointly with retained coverage.

A verifier that removes all content is not considered useful merely because unsupported claims disappear.

---

## 5.15.4 Denominator and Opportunity Counts

Because several metrics may have NA denominators, the paper should include counts in either the main tables or a supplementary table.

### Table 7. Evaluation opportunity counts

| Condition | Security assertions | Citation pairs | Numerical assertions | Asset assertions | Temporal assertions | Withholding opportunities |
| --------- | ------------------: | -------------: | -------------------: | ---------------: | ------------------: | ------------------------: |
| G0        |                 TBD |            TBD |                  TBD |              TBD |                 TBD |                       TBD |
| G1-E      |                 TBD |            TBD |                  TBD |              TBD |                 TBD |                       TBD |
| G1-N      |                 TBD |            TBD |                  TBD |              TBD |                 TBD |                       TBD |
| G1-EN     |                 TBD |            TBD |                  TBD |              TBD |                 TBD |                       TBD |
| V1-EN     |                 TBD |            TBD |                  TBD |              TBD |                 TBD |                       TBD |

These counts prevent a condition with very few opportunities from appearing artificially strong.

---

## 5.15.5 Coverage–Reliability Visualization

In addition to tables, we report the joint relationship between useful investigation coverage and unsupported conclusions.

**Figure 2 — Coverage versus Unsupported Security-Claim Rate**

Recommended axes:

[\
x = \text{Q1--Q6 Substantive Coverage}\
]

[\
y = \text{Unsupported Security-Claim Rate}.\
]

The preferred region is therefore the **lower-right** portion of the figure:

- higher substantive coverage;
- lower unsupported-claim rate.

Each experimental condition should be displayed with event-level uncertainty rather than only a pooled claim count.

This visualization is especially important for RQ3 because verification may improve safety at the cost of useful content.

---

## 5.15.6 Evidence-Completeness Decomposition

To interpret RQ1, an additional decomposition figure or supplementary table should distinguish:

1. facts unavailable in the evidence view;
2. facts available but not retrieved;
3. facts retrieved but not reconstructed correctly.

A useful presentation is a three-stage funnel:

```text
Full Gold Facts
      ↓
Supportable in View
      ↓
Retrieved
      ↓
Correctly Reconstructed
```

This prevents a low E-only or N-only result from being incorrectly attributed entirely to LLM reasoning when the missing information is structurally unavailable from that source.

---

## 5.15.7 Case Studies

Aggregate results are supplemented with a small number of qualitative case studies.

Case studies should illustrate predefined methodological phenomena rather than replace aggregate evaluation.

The planned categories are:

1. a case where deterministic verification blocks or qualifies an unsupported causal/security conclusion;
2. a case where combined E+N evidence provides information not recoverable from one single-source view; and
3. a case where the correct investigative result is explicit insufficiency.

Each case study should present:

- visible evidence;
- generated claim;
- cited evidence IDs;
- verifier decision;
- final published claim; and
- the conclusion that remains unsupported.

Case studies must not be used to infer aggregate effectiveness.

---

## 5.16 Interpretation Rules

To avoid overclaiming, final results are interpreted under the following rules.

### RQ1

A higher EN Evidence Completeness supports a claim about **investigation completeness under the frozen evidence budget and retrieval policy**.

It does not demonstrate:

- independent-sensor fusion;
- causal value of electrical evidence;
- continuous attack detection performance; or
- classification accuracy improvement.

### RQ2

Higher Citation Precision or Complete-Support Rate supports a conclusion about evidence-grounding reliability.

It does not demonstrate that every natural-language statement is true.

### RQ3

A reduction in Unsupported Security-Claim Rate supports a conclusion about the effect of the deterministic verification/publishing layer only when considered together with retained coverage and completeness.

It does not demonstrate:

- truth verification;
- causal inference;
- attacker attribution;
- improved original LLM reasoning; or
- guaranteed correctness.

---

## 5.17 Reproducibility and Evaluation Integrity

The final evaluation package records hashes for:

- model configuration;
- prompts;
- schemas;
- retrieval configuration;
- evidence bundles;
- claim-support policy;
- metrics;
- annotation policy;
- event split;
- statistical configuration; and
- evaluation outputs.

Development, evaluation generation, and scoring access are separated so that evaluator-only ground truth is not exposed to the generation pipeline.

The human gold remains independent of verifier output.

The verifier is evaluated against the annotation policy rather than being used to create its own reference answers.

This separation is essential because a system cannot be considered verified merely by agreeing with rules that generated its evaluation labels.
