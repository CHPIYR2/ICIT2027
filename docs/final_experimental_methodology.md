# 5. Experimental Methodology

We evaluate whether heterogeneous electrical/process and network evidence can support useful OT incident investigation while keeping generated conclusions traceable to observable evidence and mechanically checkable against predefined support requirements.

The evaluation is organized around three research questions:

**RQ1 — Cross-Source Investigation Value.**\
Does combining electrical/process and network evidence improve the completeness of OT incident reconstruction compared with either source alone?

**RQ2 — Evidence-Grounded LLM Investigation.**\
How reliably can an LLM generate structured OT incident explanations when substantive claims are required to cite observable evidence?

**RQ3 — Deterministic Verification.**\
Can deterministic evidence-consistency and support verification reduce unsupported security conclusions while preserving useful investigation coverage?

The design separates two factors that would otherwise be confounded: the **evidence view** available to the investigator and the **generation/verification method** applied to that evidence. Primary comparisons therefore change only one intended factor at a time. Development runs used for implementation validation, schema testing, output-capacity selection, and execution debugging are excluded from final research results.

## 5.1 Dataset and Evidence Source

We evaluate the investigation pipeline using Sherlock v3, a power-grid co-simulation dataset containing network communication and electrical/process observations. Sherlock is generated using the Wattson co-simulator and includes IEC 60870-5-104 communication, device and control-center information, process data, event annotations, and physical ground-truth material.

The study uses observable evidence including OT network activity, protocol messages and command-type requests, communication timing and gaps, electrical/process measurements, reported value or state changes, and approved relationships between protocol or process identifiers and simulated assets.

Cyber/benign labels, scenario descriptions, hidden simulator truth, and other evaluator-only information are not provided to the investigation model.

### Shared Evidence Lineage

Electrical/process evidence and network evidence are not interpreted as statistically independent sensor systems. Some representations may ultimately share packet or simulation lineage. We therefore evaluate E and N as **complementary investigative representations**.

RQ1 consequently does not estimate the benefit of independent sensor fusion. It asks whether different representations of the event support different levels of investigation performance under a fixed evidence budget.

## 5.2 Event Set and Experimental Separation

The protocol separates development events from the final evaluation set before final research execution.

The development set contains 16 events and is used for evidence/export validation, prompt and schema conformance, evidence-view isolation tests, output-capacity testing, verifier testing, and execution validation. Development outputs are not used as research performance results.

The final evaluation contains **32 preselected events**. Event identifiers and scenario strata are fixed before final generation.

Before final execution, the following are frozen:

1. experimental conditions;
2. prompts and structured-output schemas;
3. metric definitions and denominators;
4. retrieval configuration and evidence budgets;
5. model configuration;
6. human gold and claim-support policy; and
7. statistical treatment.

The event is the primary statistical unit. Claims, evidence records, packets, and repeated LLM generations are not treated as independent experimental samples.

## 5.3 Human Gold and Review Policy

The final evaluation uses human-reviewed investigation annotations rather than event labels alone.

For each event, the annotation distinguishes observable positive facts from conclusions that should remain unresolved or withheld. Positive facts include reviewed observations, supporting evidence, asset relationships, temporal relationships, and bounded security-relevant interpretations when such an interpretation is supportable.

Let (G_e) denote the set of unique positive investigation facts for event (e). These facts form the denominator for Evidence Completeness.

The annotation separately records guardrails and withholding opportunities for stronger conclusions not justified by the observable evidence, including command execution, physical completion, cyber-physical causation, malicious intent, successful compromise, and attacker attribution. Guardrails do not enter the positive-fact recall denominator.

### Semantic Annotation Boundaries

The annotation policy preserves the claim semantics defined in Section 3.4:

- command observation does not imply command execution;
- activation acknowledgement does not imply physical completion;
- electrical/process change does not identify a network cause;
- temporal ordering does not establish causation; and
- scenario labels do not make malicious intent or attribution observable.

### Single-Reviewer Design

Gold construction and final subjective evaluation use a **single reviewer (R1)** under a frozen annotation and review contract. We therefore make no claim of dual annotation, adjudication, or inter-annotator agreement.

Subjective R1 review is limited to the research cells. D0 is a deterministic descriptive reference and is excluded from subjective human-scored comparisons.

The corrected R1 universe contains **477 valid research outputs**: 96 G0, 93 valid G1-E, 96 G1-N, 96 G1-EN, and 96 V1-EN outputs. Three provider-incomplete G1-E repetitions contain no valid substantive output and therefore do not enter the subjective R1 assertion review; they remain part of the planned experiment and are handled as repetition-level NA in final scoring.

For V1-EN, R1 evaluates only claims appearing in the verifier's published report. Raw claims assigned `INSUFFICIENT` and not published are not treated as substantive V1 assertions. Verification dispositions themselves are not substituted for human claim judgments.

## 5.4 Evidence Views and Retrieval Budget

We evaluate three evidence views:

[\
V_E = E + M_E,\
]

[\
V_N = N + M_N,\
]

and

[\
V\_{EN} = E + N + M\_{EN},\
]

where (M_v) contains only the sanitized static metadata permitted for the corresponding view.

### Electrical/Process View

(V_E) contains electrical/process observations and the approved metadata needed to interpret them. Network messages and hidden network support are excluded.

### Network View

(V_N) contains network observations and approved network-related metadata. Electrical/process measurements are excluded.

### Combined View

(V\_{EN}) exposes both evidence domains. Cross-source relationships are supportable only when the required observations and mappings are simultaneously visible.

### Fixed Evidence Budget

All RQ1 conditions use a predeclared maximum of 64 evidence records:

| Evidence view |  Maximum allocation |
| ------------- | ------------------: |
| (V_E)         |        64 E records |
| (V_N)         |        64 N records |
| (V\_{EN})     | 32 E + 32 N records |

The serialized bundle is also subject to frozen evidence-input and byte limits.

The RQ1 comparison therefore does not estimate the marginal effect of adding electrical evidence while retaining every network observation. It estimates performance under the same total evidence budget with different predefined allocations. Retrieval ranking and quotas are not tuned using final model performance.

## 5.5 Experimental Conditions

Table 2 defines the final experimental conditions.

### Table 2. Experimental conditions

| Cell      | Evidence view | Generation method                  | Citation policy   | Deterministic verifier | Role                  |
| --------- | ------------- | ---------------------------------- | ----------------- | ---------------------- | --------------------- |
| **D0**    | EN            | Deterministic structured reference | Evidence-linked   | Reference checks only  | Descriptive reference |
| **G0**    | EN            | LLM investigation                  | Citation optional | No                     | RQ2                   |
| **G1-E**  | E             | LLM investigation                  | Citation required | No                     | RQ1                   |
| **G1-N**  | N             | LLM investigation                  | Citation required | No                     | RQ1                   |
| **G1-EN** | EN            | LLM investigation                  | Citation required | No                     | RQ1, RQ2, RQ3         |
| **V1-EN** | EN            | Exact replay of G1-EN              | Preserved         | Yes                    | RQ3                   |

D0 is retained as a deterministic descriptive reference for reproducibility and diagnostic checks. It is not treated as an equivalent generative competitor and is excluded from the primary RQ1–RQ3 tables and human-scored research-cell aggregates.

### G0 — Citation-Optional EN Generation

G0 receives the combined evidence view but does not require every substantive assertion to include complete evidence citations. Because G0 may still emit evidence identifiers, it is described as **citation optional**, not citation free or ungrounded.

### G1 Family

G1-E, G1-N, and G1-EN use the same citation-required generation method. They differ only in the visible evidence view.

The conditions use the same model snapshot, prompt family, structured-output contract, investigation questions, claim vocabulary, decoding configuration, output policy, repetition count, and scoring rules.

### V1-EN — Exact Verification Replay

V1-EN applies the deterministic verifier to the exact raw G1-EN output. No additional LLM generation occurs.

Source G1-EN outputs are matched by their frozen hashes before replay. V1 therefore changes only the verification/publishing layer while holding the evidence bundle and original model output fixed.

## 5.6 Research-Question Contrasts

### RQ1 — Evidence View

RQ1 compares

[\
G1\text{-}EN - G1\text{-}E\
]

and

[\
G1\text{-}EN - G1\text{-}N.\
]

The evidence view is the independent variable. Event, model, prompt family, citation requirement, schema, question set, total evidence budget, repetition count, and statistical analysis remain fixed.

Both pairwise contrasts are reported. Improvement relative to one single-source condition is not described as superiority to both.

### RQ2 — Citation-Required Grounding

RQ2 compares

[\
G1\text{-}EN - G0.\
]

Both use the EN evidence view. The principal manipulation is whether substantive claims are required to provide evidence citations under the structured generation policy.

The comparison is therefore **citation-required versus citation-optional generation**.

### RQ3 — Deterministic Verification

RQ3 compares

[\
V1\text{-}EN - G1\text{-}EN.\
]

The same generated output is used on both sides. The comparison measures the effect of deterministic evidence-consistency/support verification and publication, not a change in original LLM reasoning.

## 5.7 Investigation Questions

Every generated investigation addresses the same seven questions:

**Q1.** What network activities were observed?\
**Q2.** What electrical/process observations or changes were observed?\
**Q3.** Which assets can be associated with the observed evidence?\
**Q4.** What observable timeline can be reconstructed?\
**Q5.** What temporal or cross-source associations are supported?\
**Q6.** What security-relevant interpretation is supported by the available evidence?\
**Q7.** What conclusions cannot be established from the available evidence?

Q1–Q6 form the substantive investigation-coverage denominator.

Q7 is treated separately as uncertainty/withholding behavior. An always-withhold response therefore cannot obtain positive Q1–Q6 Coverage simply by refusing conclusions.

## 5.8 Evaluation Metrics

No single metric is sufficient to characterize incident investigation. A system can reduce unsupported claims by suppressing useful content, while a high-coverage system may achieve coverage by generating poorly supported statements. We therefore measure reconstruction, retrieval, support quality, consistency, coverage, and withholding separately.

### 5.8.1 Evidence Completeness

Evidence Completeness (Gold Fact Recall) measures exact reconstruction of the human-reviewed positive fact set:

[\
EC_e =\
\frac{|\hat{G}\_e \cap G_e|}\
{|G_e|}.\
]

The denominator (G_e) is common across E, N, and EN. This is the primary RQ1 reconstruction metric.

A fact does not count as recovered if the required support was not visible to the evaluated system.

### 5.8.2 View-Conditional Completeness

Let (G\_{ev}\subseteq G_e) be the subset of gold facts supportable from complete view (v).

[\
VCC\_{ev} =\
\frac{|\hat{G}*{ev}\cap G*{ev}|}\
{|G\_{ev}|}.\
]

VCC distinguishes limitations caused by evidence unavailability from failures to use evidence that the view could, in principle, support.

The corresponding supportable-fact counts are reported alongside the RQ1 funnel.

### 5.8.3 Retrieval Recall

Retrieval Recall measures the fraction of view-supportable gold facts for which a complete required support set was retrieved:

[\
RR\_{ev} =\
\frac{\text{supportable gold facts with complete support retrieved}}\
{|G\_{ev}|}.\
]

This separates view availability, retrieval failure, and reconstruction failure.

### 5.8.4 Citation Precision

Citation Precision is evaluated over claim-evidence citation relationships:

[\
CP =\
\frac{\text{visible citations that support their assigned role}}\
{\text{all claim-evidence citation pairs}}.\
]

A correct citation must reference an existing visible evidence item and support the role assigned to that evidence within the assertion.

### 5.8.5 Complete-Support Rate

Citation Precision does not ensure that all evidence needed for an assertion is present. Complete-Support Rate therefore measures assertion-level support completeness:

[\
CSR =\
\frac{\text{substantive assertions completely supported by their cited set}}\
{\text{all substantive assertions}}.\
]

Evaluator-added evidence cannot repair a generated citation set.

### 5.8.6 Unsupported Security-Claim Rate

USCR measures unsupported security-sensitive substantive assertions:

[\
USCR =\
\frac{\text{unsupported security-sensitive assertions}}\
{\text{all security-sensitive substantive assertions}}.\
]

Security-sensitive assertions include claims of malicious intent, command execution, physical or cyber-physical causation, successful compromise, attack success, attribution, and other security interpretations beyond direct observation.

Human review evaluates the actual claim text rather than relying only on the model-assigned `claim_type`.

If no security-sensitive substantive assertion exists, USCR is **NA**, not zero.

### 5.8.7 Numerical Consistency

Numerical Consistency evaluates whether numerical assertions use the correct source observations, values, transformation, unit, channel/asset scope, and frozen tolerance policy:

[\
NC =\
\frac{\text{correct numerical assertions}}\
{\text{all numerical assertions}}.\
]

A zero denominator is NA.

### 5.8.8 Asset Consistency

Asset Consistency evaluates whether asset-bearing assertions agree with observation identity and approved metadata relationships:

[\
AC =\
\frac{\text{correct evidence-supported asset assertions}}\
{\text{all asset assertions}}.\
]

Temporal proximity alone cannot establish an asset relationship.

### 5.8.9 Temporal Consistency

Temporal Consistency measures the correctness of stated ordering, interval, and required scope:

[\
TC =\
\frac{\text{correct temporal assertions}}\
{\text{all temporal assertions}}.\
]

Correct ordering is not interpreted as causal validity.

### 5.8.10 Q1–Q6 Coverage

Coverage measures whether each substantive investigation question has at least one substantive, supported answer:

[\
Coverage =\
\frac{\text{adequately answered questions among Q1--Q6}}{6}.\
]

Unsupported claims, generic disclaimers, and empty answers do not count.

Q7 is excluded from this denominator.

### 5.8.11 Required Withholding Recall

The gold annotation defines explicit opportunities where a stronger conclusion should be qualified or withheld.

[\
RWR =\
\frac{\text{required opportunities correctly qualified or withheld}}\
{\text{all required withholding opportunities}}.\
]

A withholding action is credited only when its action, scope, and reason are correct.

### 5.8.12 Withholding Precision

[\
WP =\
\frac{\text{correct explicit qualification/withholding actions}}\
{\text{all explicit qualification/withholding actions}}.\
]

A zero action denominator is NA.

WP is reported together with RWR and substantive coverage so that aggressive suppression is not treated as success by itself.

### 5.8.13 Schema Compliance

Schema Compliance is a diagnostic execution metric recording whether a delivered response satisfies the frozen structured-output and local validation contract. It is not interpreted as factual correctness.

## 5.9 Metric Roles by Research Question

### Table 3. Metric roles

| Metric                          |        RQ1        |     RQ2    |        RQ3        | Role                               |
| ------------------------------- | :---------------: | :--------: | :---------------: | ---------------------------------- |
| Evidence Completeness           |      Primary      |  Secondary |     Secondary     | Exact positive-fact reconstruction |
| View-Conditional Completeness   |     Secondary     |      —     |         —         | View-specific reconstruction       |
| Retrieval Recall                |     Secondary     |  Secondary |         —         | Retrieval-stage performance        |
| Citation Precision              |     Secondary     |   Primary  |     Secondary     | Claim-evidence link quality        |
| Complete-Support Rate           |     Secondary     |   Primary  |     Secondary     | Full assertion support             |
| Unsupported Security-Claim Rate |     Secondary     |   Primary  |      Primary      | Unsupported stronger conclusions   |
| Numerical Consistency           |     Secondary     |  Secondary |     Secondary     | Numerical correctness              |
| Asset Consistency               |     Secondary     |  Secondary |     Secondary     | Asset correctness                  |
| Temporal Consistency            |     Secondary     |  Secondary |     Secondary     | Timeline correctness               |
| Q1–Q6 Coverage                  | Primary companion |  Secondary | Primary companion | Investigation usefulness           |
| Required Withholding Recall     |         —         |  Secondary |      Primary      | Required epistemic restraint       |
| Withholding Precision           |         —         |  Secondary |      Primary      | Correctness of explicit restraint  |
| Schema Compliance               |     Diagnostic    | Diagnostic |     Diagnostic    | Execution conformance              |

RQ3 is never interpreted from USCR alone. Verification is evaluated jointly with retained coverage and other support metrics.

## 5.10 Human Review of Generated Assertions

Mechanical verification and human scoring have different roles.

Reference existence and visibility, many numerical relationships, units, timestamps, lineage relationships, and deterministic mappings can be evaluated mechanically. Higher-level judgments, including whether actual text is security-sensitive, whether a security interpretation is substantively supported, and whether an explicit withholding action correctly addresses a gold opportunity, are reviewed by R1 under the frozen policy.

Each reviewable whole-claim assertion is judged from the actual generated or V1-published text. Structural strings and schema labels are not treated as separate propositions.

For a substantive assertion judged supported, the review records at least one valid support set contained within the visible evidence. Complete cited support is credited only when one valid support set is fully represented in the claim's own citations and the cited roles are correct.

A gold match and evidentiary support are evaluated separately. A claim can be supported by visible evidence without reconstructing one of the frozen gold facts.

## 5.11 Model Generation Protocol

All generative cells use the fixed model snapshot:

`gpt-4.1-2025-04-14`

through the Responses API.

The final decoding and request configuration is:

- temperature = 0;
- max output tokens = 24,576;
- no seed supplied;
- truncation disabled;
- tools disabled; and
- provider-side storage disabled.

Each event-condition pair is planned for **three repetitions**. The study does not select a best repetition.

Retries are permitted only under predefined transport, availability, or delivery-recovery rules. They are never triggered by answer quality, missing citations, factual correctness, verifier disposition, or metric score.

### Provider-Incomplete Responses

A response terminated by the provider because the frozen output-token limit is reached is an incomplete delivery rather than a valid structured investigation.

Incomplete outputs are preserved for provenance and receive repetition-level NA rather than being repaired with evaluator information or regenerated because of poor content.

Three G1-E final repetitions are provider-incomplete under this rule; their remaining event repetitions keep the corresponding event-level metrics defined.

## 5.12 Repetitions and Statistical Unit

Metrics are first computed for each repetition (r):

[\
m\_{ecr}.\
]

Valid repetitions are then averaged within event (e) and condition (c). For metrics with NA denominators, averaging uses the defined repetitions. If all three repetitions are NA, the event-condition metric is NA.

The event-level value is therefore

[\
\bar{m}*{ec} =*\
*\operatorname{mean}{m*{ecr}\:m\_{ecr}\ \text{defined}}.\
]

For fixed-denominator metrics such as Evidence Completeness and Q1–Q6 Coverage, failure to produce useful valid content contributes zero unless the provider delivery itself is invalid.

The primary aggregate is the event-level macro mean:

[\
\bar{m}*c =*\
*\frac{1}{|E_c|}*\
*\sum*{e\in E_c}\bar{m}\_{ec},\
]

over events for which the metric is defined.

Pooled citation- or assertion-level counts are supplementary descriptive statistics rather than independent inferential samples.

## 5.13 Paired Contrasts and Confidence Intervals

Research-question contrasts are computed as paired event-level differences.

RQ1 uses

[\
\bar{m}*{e,G1-EN}-\bar{m}*{e,G1-E}\
]

and

[\
\bar{m}*{e,G1-EN}-\bar{m}*{e,G1-N}.\
]

RQ2 uses

[\
\bar{m}*{e,G1-EN}-\bar{m}*{e,G0}.\
]

RQ3 uses

[\
\bar{m}*{e,V1-EN}-\bar{m}*{e,G1-EN}.\
]

Only events with both sides defined enter a claim-conditioned paired contrast.

Uncertainty is estimated using **2,000 scenario-stratified bootstrap resamples** with fixed seed **20270922**. Entire events, together with their repetitions and paired conditions, are resampled as units.

We report 95% percentile bootstrap confidence intervals. A contrast is described as detected only when its interval excludes zero; we do not introduce post-hoc significance thresholds.

## 5.14 Missing Data and Zero-Denominator Rules

Metric denominators are frozen before final scoring.

A zero claim-conditioned denominator produces **NA**, not zero or one. Examples include:

- no security-sensitive substantive assertions → USCR = NA;
- no numerical assertions → Numerical Consistency = NA;
- no explicit qualification/withholding action → Withholding Precision = NA.

Opportunity and NA counts are reported with primary results to prevent sparse conditions from appearing artificially favorable.

For fixed-denominator metrics such as Evidence Completeness and Q1–Q6 Coverage, absence of a useful answer remains part of the denominator.

Q7 withholding content cannot create positive Q1–Q6 Coverage.

## 5.15 Evaluation Integrity and Exact Replay

The final evaluation is executed under a sealed-input workflow.

The committed evaluation package binds the final gold annotation, support/matching policy, generation outputs, V1 replay source mapping, retrieval/evidence configuration, review scope, and statistical configuration.

The final generative outputs consist of G0, G1-E, G1-N, and G1-EN research cells. V1-EN performs zero additional model calls and replays the exact G1-EN source outputs.

The deterministic D0 reference is generated separately and retained for descriptive reproducibility checks only.

Before final scoring, the completed R1 review universe is validated against the corrected review-scope contract. Final scoring proceeds only after all 477 required review items are complete and validation reports no errors.

The scoring implementation preserves the distinction between:

- generated claims;
- V1-published claims;
- evaluator-only gold facts;
- human support judgments; and
- verifier dispositions.

The verifier does not create its own evaluation ground truth.

## 5.16 Interpretation Rules

Final results are interpreted under predeclared semantic restrictions.

For **RQ1**, differences concern investigation behavior under the frozen evidence views and total retrieval budget. They do not demonstrate independent-sensor fusion, continuous detection performance, or causal value of either modality.

For **RQ2**, higher Citation Precision or Complete-Support Rate supports a conclusion about evidence-grounding quality. It does not imply universal factual truth or improved reconstruction unless those metrics also improve.

For **RQ3**, verifier effects are interpreted jointly with Q1–Q6 Coverage. Removing or withholding every claim is not treated as successful verification. A reduction or disappearance of security-sensitive published claims is also not automatically interpreted as an improved USCR when the post-verification denominator is zero.

Across all RQs:

- command observed does not imply execution;
- acknowledgement observed does not imply physical completion;
- electrical/process change does not imply network causation;
- temporal association does not imply causation; and
- deterministic support verification does not establish attacker intent, successful compromise, attribution, or real-world physical truth.

These restrictions define the boundary between mechanically verifiable evidence support and broader incident interpretation.
