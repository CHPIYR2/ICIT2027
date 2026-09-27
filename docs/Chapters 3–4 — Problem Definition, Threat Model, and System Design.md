# 3. Problem Definition and Threat Model

Operational technology (OT) incident investigation differs fundamentally from event classification. A detector may identify an event as suspicious or cyber-related, but an investigator must determine what was actually observed, which assets were involved, how network and physical-process observations relate in time, and which conclusions are justified by the available evidence. The central problem considered in this work is therefore not whether an event belongs to a particular attack class, but whether a useful incident reconstruction can be produced without exceeding what the observable evidence supports.

We formulate this problem as **event-conditioned, evidence-grounded OT incident investigation**. For each event, the investigator receives an externally defined investigation scope together with a set of electrical/process observations, network observations, and sanitized static metadata. The system produces a structured set of claims describing the observable event. Each substantive claim is linked to explicit evidence records and is subsequently checked against deterministic, claim-specific support rules.

This formulation deliberately separates three concepts that are frequently conflated in automated security analysis: *observation*, *interpretation*, and *causation*. For example, observing a control command on the network is not equivalent to proving that the physical operation was executed. Likewise, observing an electrical change after a command does not establish that the command caused that change. The proposed system is designed to preserve these distinctions throughout evidence retrieval, language-model generation, and deterministic verification.

## 3.1 Event-Conditioned Investigation

We assume that an upstream mechanism has already identified an event that requires investigation. Such a mechanism may be an intrusion-detection system, an operational alert, an anomaly detector, or a human analyst. The mechanism that produces the event scope is outside the scope of this work.

Let an investigation event be denoted by (e), with an externally supplied temporal scope (W_e). The system operates only on evidence observable within the permitted investigation scope. Its task is not to determine when an incident begins in a continuous stream and not to perform continuous attack detection. Instead, it answers the narrower but operationally important question:

> Given an event that has already been selected for investigation, what can be reconstructed from the available OT evidence, and which conclusions are sufficiently supported?

This distinction is important because event-conditioned investigation is materially easier than continuous unknown-onset detection. The investigation process is given an event boundary rather than being required to discover one. Consequently, results in this work must not be interpreted as measurements of continuous IDS performance or unknown-onset detection capability.

For an event (e), the investigation system receives a visible evidence bundle

[\
B_e^v = E_e^v \cup N_e^v \cup M_e^v ,\
]

where (v) denotes the permitted evidence view. Depending on the experimental condition, (v) may contain electrical/process evidence only, network evidence only, or both. Static sanitized metadata may be provided when required to interpret an otherwise opaque observation, for example to map a protocol control point or process channel to an opaque asset identifier.

The event scope and the permitted evidence view form a hard visibility boundary. Information outside that boundary cannot be used to support a generated claim. In particular, evaluator-only labels, attack descriptions, hidden simulator state, and other ground-truth information are excluded from both retrieval and language-model generation.

The threat model of this paper therefore focuses on **unsupported investigative conclusions** rather than only on missed attack detections. We consider several failure modes relevant to LLM-assisted investigation:

- generation of facts that do not appear in the visible evidence;
- citation of evidence that exists but does not support the associated assertion;
- incorrect numerical calculations or unit interpretation;
- incorrect asset or timestamp relationships;
- promotion of temporal correlation into causal attribution;
- interpretation of an observed command as proof of physical execution;
- attribution of malicious intent, successful compromise, or attacker identity without sufficient evidence; and
- failure to state that a requested conclusion is unresolved when the available evidence is insufficient.

The system is designed to detect a finite subset of these failures mechanically. It does not claim to establish the complete truth of an incident or to replace analyst judgment.

## 3.2 Evidence Views

We distinguish four information domains:

[\
E = \text{electrical/process evidence},\
]

[\
N = \text{network evidence},\
]

[\
M = \text{static sanitized metadata},\
]

and

[\
G = \text{evaluator-only ground truth}.\
]

### Electrical/Process Evidence (E)

Electrical/process evidence describes observable values or reported states associated with the monitored physical process. Depending on the available channel, such records may include voltage, current, active power, reactive power, reported states, observation freshness, and related process measurements.

Electrical/process evidence can support statements such as:

> A reported voltage value was observed for asset (x) at time (t).

or

> The reported value on channel (c) changed from (v_1) to (v_2) between (t_1) and (t_2).

It cannot, by itself, establish which network operation produced the change or whether the change resulted from malicious activity.

### Network Evidence (N)

Network evidence describes observable communication behavior. It may include communication activity, endpoints, protocol messages, command-type activation requests, activation responses, message timing, and communication gaps.

Network evidence can therefore support statements such as:

> A command-type activation request was observed at time (t).

When the command contains an address that can be resolved through approved static metadata, the evidence may further support:

> A command-type activation request addressed to a control point mapped to asset (x) was observed.

This wording is intentionally narrower than statements such as “asset (x) executed the command.” A command observed on the network establishes communication behavior, not completion of the corresponding physical operation.

### Static Sanitized Metadata (M)

Static metadata provides relationships necessary to interpret observations without revealing evaluator-only scenario knowledge. Examples include mappings between process channels and opaque asset identifiers or between protocol control points and corresponding assets.

Metadata is used only as a relationship source. It does not encode whether an event is malicious, which attack family is present, whether an attack succeeded, or what the correct incident explanation should be.

For example, a protocol address may be mapped as

[\
\text{control point} \rightarrow \text{asset } x.\
]

This mapping permits the investigator to state that a network message was *addressed to a control point mapped to asset (x)*. It does not establish that the mapped asset changed state as a consequence.

### Evaluator-Only Ground Truth (G)

Ground truth contains information used exclusively for annotation and evaluation. It may contain reviewed event facts, permitted interpretations, unsupported conclusions, or other evaluator information.

A strict separation is enforced:

[\
G \not\subseteq B_e^v.\
]

Ground truth is never made available to evidence retrieval or to the LLM. In particular, malicious labels, attack-family information, gold incident descriptions, hidden simulator truth, scenario playbooks, and future observations cannot be used to generate an investigation.

This separation prevents an explanation from appearing evidence-grounded while actually reproducing evaluator knowledge.

### Evidence Views

The study considers three investigation views:

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

where (M_v) contains only the sanitized metadata permitted for the corresponding view.

These views should not be interpreted as three independent sensor systems. In the studied setting, some electrical/process and network representations may ultimately share packet lineage. Their value is therefore evaluated as **complementary investigative representations**, not as statistically independent sensors.

## 3.3 Investigation Objective

For each event, the system aims to reconstruct five categories of investigative information:

1. observable event facts;
2. an evidence-grounded timeline;
3. asset and cross-source relationships;
4. security-relevant interpretations that remain within the evidence boundary; and
5. unresolved questions that cannot be supported by the available evidence.

Let

[\
C_e = {c_1,c_2,\ldots,c_k}\
]

denote the set of generated claims for event (e). Each substantive claim (c_i) contains at least a claim type, a natural-language representation, and one or more evidence references. The investigation objective is not simply to maximize the number of claims. Instead, the desired output should simultaneously provide useful coverage and evidentiary traceability.

Conceptually, the system seeks an investigation (I_e) satisfying

[\
I_e =\
(O_e, T_e, R_e, S_e, U_e),\
]

where:

- (O_e) is the set of supported observations;
- (T_e) contains temporal relationships;
- (R_e) contains supported asset or cross-source relationships;
- (S_e) contains bounded security-relevant interpretations; and
- (U_e) records unresolved conclusions.

A useful investigation should provide enough information to answer questions such as:

- What network activity was observed?
- What electrical/process changes were observed?
- Which assets can be associated with the observations?
- What sequence of observable events can be reconstructed?
- Which cross-source temporal relationships are supported?
- What security-relevant conclusions are justified?
- What cannot be concluded from the available evidence?

Importantly, an investigation is not considered better merely because it produces more definitive language. A system that refuses every conclusion may minimize unsupported claims but provide little investigative value. Conversely, a system that provides a complete narrative by filling evidentiary gaps with plausible assumptions may be useful-sounding but unreliable. Our formulation therefore treats **coverage and evidentiary reliability as separate dimensions**.

## 3.4 Claim Semantics

The system uses an explicit claim semantics to prevent observations from being silently promoted into stronger conclusions. We distinguish six conceptual levels.

### Observed Facts

An observed fact reports information directly represented in an evidence record.

Examples include:

> Network activity was observed between two endpoints.

> A command-type activation request was observed.

> A reported process value of (x) was observed at time (t).

Observed facts do not imply intent, execution, causality, or attack success.

### Derived Facts

A derived fact is computed deterministically from one or more observations while preserving their provenance. Examples include a numerical difference between two reported measurements or a derived ordering between timestamps.

For two compatible observations (o_1) and (o_2),

[\
\Delta v = v_2-v_1\
]

may be represented as a derived reported change if the values, units, channel identity, timestamps, and parent evidence satisfy the applicable support policy.

The derived value does not become independent evidence: its lineage continues to point to its source observations.

### Asset Relationships

An asset relationship links an observation or control point to an opaque asset through approved metadata. Examples include a process channel mapped to an asset or a network command address mapped to the same asset.

Such a relationship establishes an interpretation of identifiers, not an operational consequence.

### Temporal Associations

A temporal association states an ordering or timing relationship between otherwise supported observations.

For example, if a network command is observed at (t_c) and an electrical observation associated with the same mapped asset is observed at (t_e), with

[\
t_c < t_e,\
]

the system may report that the command observation preceded the electrical/process observation.

The central semantic constraint is:

> **Temporal association does not imply causation.**

Even if the two records refer to the same mapped asset and occur within a short interval, the evidence supports an ordering relation, not the statement that the command caused the later change.

### Security Interpretations

A security interpretation goes beyond direct observation but may still be useful to an investigator when sufficiently supported. Such interpretations must remain explicitly bounded by the available evidence and by the support policy.

A security-relevant pattern may justify language such as:

> The observed activity is security-relevant because it combines an OT command observation with a subsequent process observation on the same mapped asset.

It does not automatically justify:

> An attacker successfully manipulated the asset.

Security interpretations therefore require stricter support than ordinary observations.

### Causal Claims

A causal claim asserts that one observed event produced another, for example that a network command caused a voltage change.

The evidence available to this study generally supports temporal and asset relationships rather than experimental causal identification. Consequently, the presence of a command followed by a process change is insufficient to establish causation.

Unless a claim-specific policy contains evidence sufficient for a causal conclusion, such a statement must not be elevated to a supported result.

### Unknown or Insufficient Conclusions

When a requested conclusion cannot be supported, the system records the limitation explicitly rather than filling it with an assumption.

Examples include:

> The available evidence does not establish whether the observed command was physically executed.

> The available evidence does not establish that the later electrical change was caused by the command.

> Attacker intent cannot be determined from the visible evidence.

Unknown is therefore a first-class investigative result, not a system failure.

The operational claim vocabulary further refines these semantics into finite claim types including `network_activity`, `command_observed`, `acknowledgement_observed`, `communication_gap`, `reported_value`, `reported_change`, `reported_state_change`, `electrical_change`, `asset_relationship`, `temporal_association`, `security_indicator`, `security_interpretation`, and `unknown`.

This finite vocabulary enables deterministic claim-specific verification. It also prevents the verifier from having to infer arbitrary semantic categories from unrestricted prose.

---

# 4. System Design

Figure 1 presents the proposed investigation pipeline. The system transforms heterogeneous OT observations into structured evidence, retrieves an event-specific evidence bundle, uses an LLM to synthesize an investigation, and then subjects the generated claims to deterministic evidence-consistency and support verification.

**Figure 1: Verifiable OT incident-investigation pipeline.**

```text
 Electrical / Process Evidence ──┐
                                 │
                                 ├──> Evidence Retrieval
 Network Evidence ───────────────┘          │
                                            ▼
                                   LLM Investigation
                                            │
                                            ▼
                                   Structured Claims
                                    + Evidence IDs
                                            │
                                            ▼
                              Deterministic Verification
                                            │
                         ┌──────────────────┼─────────────────┐
                         ▼                  ▼                 ▼
                    SUPPORTED          QUALIFIED        INSUFFICIENT
                         └──────────────────┬─────────────────┘
                                            ▼
                                  Verifiable Incident Report
```

The design follows two principles. First, evidence must remain traceable across parsing, transformation, retrieval, generation, and verification. Second, the system must distinguish *whether a statement is plausible* from *whether the available evidence supports that statement*. The LLM is used for evidence synthesis, not as the final authority on evidentiary validity.

## 4.1 Evidence Construction

Raw OT observations are converted into normalized evidence records before they are presented to the investigation system. Each evidence record contains sufficient information to identify the observation, its asset context, time, source, units, and provenance.

Conceptually, an evidence record is represented as

[\
r =\
(id, a, t_o, t_r, v, u, s, f, p, P, q, \tau),\
]

where:

- (id) is a stable evidence identifier;
- (a) is an opaque asset identifier when known;
- (t_o) is the observation time;
- (t_r) is the reported time when separately available;
- (v) is the observed or derived value;
- (u) is its unit;
- (s) identifies the evidence source type;
- (f) identifies the source file or source record;
- (p) records protocol or vantage-point information where applicable;
- (P) contains parent evidence identifiers;
- (q) contains quality or validity flags; and
- (\tau) describes any transformation used to derive the record.

In implementation terms, the corresponding fields include information such as `evidence_id`, `asset_id`, `observation_time`, `reported_time`, `value`, `unit`, `source_type`, `source_file`, `vantage_point`, `protocol`, `parent_ids`, `quality_flags`, and `transformation`.

### Stable Evidence Identifiers

Every evidence item exposed to the investigation stage receives a stable identifier. The identifier is the bridge between natural-language claims and the underlying observation.

For a claim (c_i), let

[\
R(c_i)={id_1,\ldots,id_m}\
]

be its cited evidence set. Verification operates on these references rather than relying on the prose generated by the LLM alone.

This design has two benefits. First, an analyst can inspect the evidence supporting an assertion. Second, the verifier can mechanically determine whether the cited evidence was actually visible to the model and whether it possesses the fields required by the claim type.

### Evidence Lineage

Derived records preserve their source lineage. If a reported change is calculated from two original measurements (r_1) and (r_2), the derived evidence record retains

[\
P(r\_\Delta)={id(r_1),id(r_2)}.\
]

A derived observation is therefore not treated as an independent measurement.

Lineage also prevents a generated conclusion from citing only a convenient derived value while losing the observations from which it originated.

### Network-to-Asset Mapping

Protocol messages may contain identifiers that are meaningful to the control system but not directly equivalent to an investigation asset identifier. Sanitized static metadata is therefore used to resolve approved address relationships.

For example:

[\
\text{protocol control point}\
\xrightarrow{M}\
\text{opaque asset }x.\
]

A command-address observation may retain the command message as a parent, the mapped target asset, and the metadata record responsible for the mapping.

When this mapping is exact, the system can safely state:

> A command-type activation request addressed to a control point mapped to asset (x) was observed.

The mapping still does not establish execution or causality.

### Process-to-Asset Mapping

Electrical/process observations similarly preserve the relationship between a measurement channel and an opaque asset. A channel-to-asset mapping allows multiple observations to be associated with the same investigation asset without exposing scenario-specific ground truth.

Cross-source reasoning is allowed only when the necessary mappings exist on both sides. A network command and an electrical observation cannot be described as involving the same asset merely because they occur close together in time.

## 4.2 Investigation Retrieval

Presenting all available event data to the LLM would increase context size while weakening control over what information is actually used. The system therefore performs investigation-oriented evidence retrieval before generation.

Retrieval is conditioned on the supplied event scope and evidence view. Its purpose is to select records likely to answer the investigation questions while preserving the visibility boundary of the experiment.

Relevant dimensions include:

- event membership;
- observation time;
- asset identity;
- protocol and network activity;
- command or acknowledgement observations;
- communication gaps;
- electrical/process values;
- reported changes; and
- evidence needed to connect observations through approved metadata.

The retrieval stage operates on structured evidence rather than on attack labels or model explanations. It does not have access to evaluator-only ground truth.

For an event (e) and view (v), retrieval produces

[\
R_e^v \subseteq B_e^v.\
]

The downstream generator is constrained to (R_e^v). Evidence outside the retrieved bundle cannot subsequently be used by the evaluator to retroactively justify a generated claim.

This distinction is important. Suppose a correct electrical observation exists somewhere in the full event record but was not included in the model's evidence bundle. If the LLM generates the value anyway, the statement is not considered grounded merely because an evaluator can find the value elsewhere. Grounding is evaluated against the information that was actually visible at generation time.

### View-Aware Retrieval

For an electrical/process-only condition, the retriever exposes (E) and the minimum approved metadata required to interpret (E). Network records are excluded.

For a network-only condition, the retriever exposes (N) and its permitted metadata while excluding electrical/process observations.

For a combined condition, both sources may be retrieved. Cross-source relationships are considered only when the corresponding records and mappings are simultaneously visible.

This design supports an evidence-view comparison without changing the basic investigation task.

### Retrieval Is Not Causal Selection

Retrieval prioritizes observations that may be useful for investigation, but retrieval priority itself is not evidence of importance or causality. Likewise, feature importance from a classifier is not treated as causal evidence and is not substituted for original observations.

The retriever therefore returns structured evidence records rather than only machine-learning feature vectors or ranked explanations.

## 4.3 Structured LLM Investigation

The LLM receives the retrieved evidence together with the investigation instructions and produces a structured report. The generator is responsible for heterogeneous evidence synthesis, timeline construction, and natural-language formulation. It is not trusted to determine evidentiary validity by itself.

Each substantive claim contains at least:

```json
{
  "claim_id": "...",
  "claim_type": "...",
  "claim_text": "...",
  "evidence_ids": ["..."]
}
```

Additional typed fields encode the structured content required by specific claim types, such as assets, timestamps, channels, values, units, or the participating records in a temporal relationship.

At the report level, claims are organized so that they can support the investigation questions while remaining independently verifiable. A simplified representation is:

```json
{
  "event_id": "...",
  "evidence_view": "...",
  "claims": [
    {
      "claim_id": "...",
      "claim_type": "command_observed",
      "claim_text": "...",
      "evidence_ids": ["..."]
    }
  ],
  "questions": [
    {
      "question_id": "Q1",
      "claim_ids": ["..."]
    }
  ]
}
```

The schema constrains syntax and claim typing, but schema validity is not equivalent to evidentiary correctness. A structurally valid claim may still cite an irrelevant record, contain the wrong number, connect incompatible assets, or overstate what its evidence proves.

### Evidence-Cited Generation

In the evidence-grounded configuration, substantive assertions must explicitly reference evidence IDs. Citation is required at the claim level rather than being added to the final report after generation.

This matters because post-hoc citation retrieval could create the appearance of grounding without demonstrating that the cited evidence actually supported the generated statement.

Nevertheless,

[\
\text{citation presence}\
\neq\
\text{claim support}.\
]

A citation is useful only if its referenced record is visible and semantically supports the assertion.

### Conservative Language Boundary

Generation instructions explicitly preserve the claim semantics introduced in Section 3.4.

For example, the following statement is permitted when supported:

> A command-type activation request addressed to a control point mapped to asset (x) was observed at (t_1). A process observation associated with the same mapped asset was observed later at (t_2).

The following stronger transformation is not justified solely by those observations:

> The attacker executed the command and caused the process change.

The difference is not stylistic. It represents a different evidentiary claim.

### LLM Role

The role of the LLM is therefore deliberately bounded. It provides capabilities that are difficult to encode efficiently with fixed templates, including:

- synthesis of heterogeneous evidence;
- selection of human-readable event facts;
- organization of observations into an investigative narrative;
- identification of potentially relevant temporal relationships; and
- explicit articulation of unresolved questions.

The subsequent verifier, rather than the LLM, determines whether supported claim types meet their deterministic evidence requirements.

## 4.4 Deterministic Verification

Generated claims are processed by a deterministic evidence-consistency and support verifier. The verifier is **not a truth oracle**. Instead, it checks whether a claim is internally consistent with the visible evidence and whether it satisfies a finite support policy defined for its claim type.

Let

[\
V(c_i,R_e^v)\
]

denote verification of claim (c_i) against the retrieved bundle (R_e^v).

The verifier applies several classes of checks.

### Reference Verification

Every cited evidence ID must exist and must belong to the evidence bundle visible to the generator.

For every

[\
id \in R(c_i),\
]

the verifier requires

[\
id \in R_e^v.\
]

A claim cannot be supported by an evidence record that was never visible to the model.

### Asset Verification

If a claim asserts an asset relationship, the cited records must contain the required asset identity or the approved metadata lineage establishing that relationship.

For cross-source same-asset relationships, both sides must independently resolve to the same asset. Time proximity alone cannot substitute for asset mapping.

### Temporal Verification

Claims containing timestamps or ordering relationships are checked against evidence timestamps.

A temporal claim

[\
A \prec B\
]

requires observable timestamps satisfying the declared ordering. Verification of the ordering does not verify a causal relationship.

### Numerical Verification

Claims involving reported values or changes are recalculated from cited evidence.

If a claim states

[\
\Delta v = v_2-v_1,\
]

the verifier checks the source values, their compatibility, and the resulting arithmetic under the predefined numerical comparison policy.

This check is performed on the typed numeric representation rather than by attempting to interpret arbitrary prose.

### Unit Verification

Values participating in a numeric claim must use compatible units. A numerically correct subtraction does not make a claim valid if the operands correspond to incompatible quantities or units.

### Lineage Verification

Derived evidence must retain the required parent observations. The verifier checks that the claimed transformation can be traced to its referenced source records.

This prevents an untraceable derived value from becoming the apparent sole basis of a conclusion.

### Claim-Specific Support Policy

The final layer checks whether the cited evidence types are sufficient for the semantic strength of the claim.

Examples include:

- `command_observed` requires an observable network command record;
- an asset-targeted command statement additionally requires the corresponding approved address-to-asset mapping;
- `reported_value` requires the matching electrical/process observation;
- `reported_change` requires compatible before/after observations and the corresponding numerical relationship;
- `asset_relationship` requires the applicable mapping record;
- a same-asset `temporal_association` requires evidence and mapping on both participating sides, plus valid time ordering.

A causal conclusion is not accepted merely because its underlying temporal observations pass these checks.

Similarly:

[\
\text{activation acknowledgement observed}\
\not\Rightarrow\
\text{physical operation completed}.\
]

The acknowledgement is itself an observable network fact. Its interpretation remains bounded by the semantics of the protocol evidence available to the investigator.

### Verification Scope

Some conclusions cannot be mechanically validated using finite evidence rules. In particular, the verifier does not independently infer attacker intent, establish causal cyber-physical effects, identify an attacker, or prove successful compromise.

Such statements must either satisfy a separately defined and supported interpretation policy or be qualified or withheld.

Table 1 summarizes representative claim-support boundaries.

**Table 1. Representative claim types and evidence-support rules**

| Claim                    | Required evidence                              | Supported conclusion                                  | Unsupported promotion                                        |
| ------------------------ | ---------------------------------------------- | ----------------------------------------------------- | ------------------------------------------------------------ |
| Network activity         | Network observation                            | Communication activity was observed                   | Activity was malicious                                       |
| Command observed         | Command-type network record                    | A command-type request was observed                   | Command was executed                                         |
| Command mapped to asset  | Command record + approved address mapping      | Request addressed a control point mapped to asset (x) | Asset (x) physically acted                                   |
| Acknowledgement observed | Corresponding network response                 | Activation response was observed                      | Requested operation completed physically                     |
| Reported value           | Electrical/process observation                 | Reported value (v) observed                           | Value represents hidden physical truth                       |
| Reported change          | Compatible observations + arithmetic support   | Reported value changed between observations           | Network activity caused the change                           |
| Asset relationship       | Observation + approved metadata                | Observation/control point maps to asset (x)           | Asset was compromised                                        |
| Temporal association     | Supported observations + mappings + time order | Observation (A) preceded (B)                          | (A) caused (B)                                               |
| Security interpretation  | Claim-specific supporting evidence             | Bounded security-relevant interpretation              | Attacker intent, identity, or attack success without support |
| Unknown                  | Missing support requirement identified         | Conclusion cannot be established                      | Unsupported conclusion filled by assumption                  |

This table encodes a central design principle: the system verifies **support boundaries**, not merely evidence-ID existence.

## 4.5 Evidence Sufficiency

After verification, each claim is assigned an evidence-sufficiency disposition:

[\
D(c_i) \in\
{\
\texttt{SUPPORTED},\
\texttt{QUALIFIED},\
\texttt{INSUFFICIENT}\
}.\
]

These dispositions control how the final report presents the generated conclusion.

### SUPPORTED

A claim is `SUPPORTED` when its references are visible and the claim satisfies all deterministic requirements applicable to its type.

For example, a reported numerical change may be supported when the cited before/after observations refer to the required channel or asset, use compatible units, satisfy the expected time relationship, and reproduce the claimed arithmetic.

`SUPPORTED` means that the assertion is supported under the finite evidence policy. It does not mean that the verifier has established universal real-world truth.

### QUALIFIED

A claim is `QUALIFIED` when part of the generated statement is supportable but its original wording exceeds what the evidence establishes.

For example, suppose the evidence shows:

1. a network command-type request mapped to asset (x);
2. a later electrical observation associated with asset (x); and
3. valid timestamp ordering.

The evidence may support the qualified statement:

> The command observation preceded the electrical/process observation associated with the same mapped asset.

It does not necessarily support:

> The command caused the electrical change.

The qualification mechanism preserves the useful observation while removing the unsupported causal interpretation.

### INSUFFICIENT

A claim is `INSUFFICIENT` when the evidence requirements for the claimed conclusion are not met.

Reasons may include:

- nonexistent evidence references;
- references outside the visible evidence bundle;
- missing asset mapping;
- incompatible assets;
- incorrect timestamp ordering;
- incorrect numerical values;
- unit mismatch;
- broken lineage; or
- absence of the evidence type required for the semantic strength of the claim.

`INSUFFICIENT` does not imply that the event is benign. It means only that the specified conclusion cannot be established from the available evidence.

Formally,

[\
\text{insufficient evidence}\
\not\Rightarrow\
\text{benign event}.\
]

This distinction is essential because the proposed system is an investigation framework rather than a classifier.

### Report Construction

The final incident report preserves both the supported findings and the epistemic boundary of the investigation. It therefore communicates not only *what was observed*, but also *what remains unresolved*.

A report may, for example, state:

> A command-type activation request mapped to asset (x) was observed at (t_1). A subsequent electrical/process observation associated with the same mapped asset was observed at (t_2). The available evidence supports the temporal ordering but is insufficient to establish that the command caused the later observation.

Such output is intentionally more conservative than a plausible causal narrative. Its purpose is to provide an analyst with a reconstruction that remains auditable against the underlying evidence.

This design also creates an explicit trade-off that is evaluated later in the paper. A verifier could trivially avoid unsupported conclusions by withholding everything, but such a system would provide no useful investigation coverage. The experimental methodology therefore evaluates both unsupported-claim behavior and retained investigative coverage rather than treating withholding alone as success.

Taken together, the pipeline transforms LLM-generated incident explanations into claims with explicit evidentiary provenance and finite support boundaries. The resulting report is not guaranteed to be a complete or causal reconstruction of the underlying physical event. Instead, it provides a structured account of what the available electrical/process and network observations support, what can only be stated with qualification, and what remains unknown.
