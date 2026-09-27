# Research Direction Lock

## Working Title

**Verifiable OT Incident Investigation with Electrical and Network Evidence**

Chinese:

**整合電氣與網路證據之可驗證 OT 資安事件調查**

This research supersedes the previous attempt to make evidence fusion improve Cyber/Benign classification accuracy.

The existing Layer-1 classification and network-observability experiments must remain preserved as prior findings and motivation.

Do not continue optimizing the Cyber/Benign classifier unless explicitly requested.

---

# 1. Core Research Problem

The paper is no longer primarily asking:

> Can Electrical + Network features classify OT cyber events better than Network-only?

Instead, it asks:

> **Given an OT event requiring investigation, can heterogeneous electrical/process and network evidence be used to produce a structured, evidence-grounded incident explanation, and can deterministic verification reduce unsupported security conclusions?**

The security problem is incident investigation, not generic LLM question answering.

The LLM is an investigation assistant, not the research subject by itself.

---

# 2. Motivation from Existing Results

Preserve the following existing finding:

Under the original full protocol-aware Sherlock condition, Random Forest and Gradient Boosting achieved perfect event-level classification using Network-only evidence, and E+N did not alter their binary predictions.

This means classification performance alone is not a sufficient research target.

A classifier output such as:

```text id="80o96v"
CYBER_RELATED
```

does not answer:

```text id="cr0h4j"
What happened?

Which network activities were observed?

Which electrical/process changes were observed?

Which assets were involved?

What was the temporal sequence?

Which conclusions are directly observed?

Which conclusions are interpretations?

Which claims are unsupported?

What remains unknown?
```

The new research focuses on these investigation questions.

---

# 3. Scope

The system is:

**event-conditioned OT incident investigation**

It is NOT:

```text id="ib4m24"
continuous intrusion detection
unknown-onset attack detection
autonomous root-cause proof
automatic attribution of attacker intent
causal cyber-physical inference
```

The event scope/time window may be supplied by the existing experimental protocol.

This must be clearly stated in the paper.

---

# 4. Existing Evidence Contract Must Be Reused

Reuse the existing packet-derived evidence model and leakage controls.

Electrical/process evidence may include permitted observations such as:

```text id="7cbpnm"
voltage
current
active power
reactive power
reported state
observation freshness / missingness
```

Network evidence may include permitted observations such as:

```text id="x6euf8"
network activity
protocol messages
commands
activation responses
communication timing
communication gaps
endpoints
```

Do not expose evaluator-only ground truth to the investigation model.

The following remain forbidden as LLM/retrieval evidence:

```text id="tr7j3j"
malicious label
gold event description
attack family label
attack_point
physical simulator truth
hidden state
future observations
scenario playbook
```

Ground truth may only be used by isolated annotation/evaluation code.

---

# 5. Preserve Evidence Lineage

Continue using or extending the existing evidence structure:

```text id="43q7k4"
EvidenceRecord(
    evidence_id,
    asset_id,
    observation_time,
    reported_time,
    value,
    unit,
    source_type,
    source_file,
    vantage_point,
    protocol,
    parent_ids,
    quality_flags,
    transformation
)
```

Every claim shown to the LLM or returned by the system must be traceable to evidence IDs.

Derived evidence must preserve parent lineage.

Do not create independent-looking evidence records from the same underlying packet lineage.

Electrical and network evidence from the same PCAP are complementary representations, not independent sensors.

---

# 6. Main Research Questions

Freeze the research questions as follows unless a correctness problem is found.

## RQ1 — Cross-Source Investigation Value

> **Does combining electrical/process and network evidence improve the completeness of OT incident reconstruction compared with either evidence source alone?**

This is NOT a classification-accuracy question.

Compare:

```text id="5taccz"
N-only investigation
E-only investigation
E+N investigation
```

Evaluate what facts and relationships each condition can correctly recover.

---

## RQ2 — Evidence-Grounded LLM Investigation

> **How reliably can an LLM generate structured OT incident explanations when every substantive claim must cite observable evidence?**

Measure whether the system correctly identifies:

```text id="d6zpxg"
observed network activity
observed commands
observed acknowledgements
electrical/process changes
asset relationships
temporal relationships
uncertainty
unsupported interpretations
```

---

## RQ3 — Deterministic Verification

> **Can deterministic evidence verification reduce unsupported security conclusions while preserving useful investigation coverage?**

Compare at minimum:

```text id="xvhaj3"
LLM + retrieved evidence

LLM + retrieved evidence + citations

LLM + retrieved evidence + citations + deterministic verifier

LLM + retrieved evidence + citations + verifier + sufficiency/withholding policy
```

Do not claim verification guarantees truth.

---

# 7. Investigation Output Schema

The LLM must NOT return unconstrained free-form prose as the primary experimental output.

Define a structured schema.

Suggested form:

```text id="nqnfls"
{
  "event_id": "...",
  "observations": [
    {
      "claim": "...",
      "claim_type": "...",
      "evidence_ids": ["..."]
    }
  ],
  "temporal_relations": [],
  "security_interpretation": [],
  "unresolved": []
}
```

Every substantive claim must contain one or more evidence IDs or explicitly state that support is insufficient.

---

# 8. Initial Claim Vocabulary

Start with a finite claim vocabulary.

At minimum consider:

```text id="cx9htw"
network_activity
command_observed
acknowledgement_observed
communication_gap

reported_value
reported_change
reported_state_change
electrical_change

temporal_association

security_indicator
security_interpretation

unknown
```

Do not silently allow arbitrary new high-level claim types.

If a new claim type is required, document it before evaluation.

---

# 9. Critical Semantic Boundaries

These distinctions must be enforced.

## Command observed

May support:

> A command was observed on the monitored network.

Does NOT automatically support:

> The command was successfully executed.

---

## Activation acknowledgement observed

May support:

> A protocol response was observed.

Does NOT automatically support:

> The physical action completed successfully.

---

## Electrical/process change observed

May support:

> A reported electrical/process value changed.

Does NOT automatically support:

> The change was caused by the observed network command.

---

## Command followed by electrical change

May support:

> A temporal association was observed.

Does NOT automatically support:

```text id="wnkff0"
causation
malicious intent
attacker identity
successful compromise
```

These boundaries are central to the paper.

---

# 10. Deterministic Verifier

Implement the verifier primarily as deterministic code/rules.

Do NOT use a second unrestricted LLM as the main verifier.

For each claim, perform applicable checks.

## Reference check

Do cited evidence IDs exist?

---

## Visibility check

Was the evidence allowed under the experimental condition?

---

## Asset check

Do evidence records refer to the claimed asset or a valid mapped relationship?

---

## Time check

Does the claimed temporal ordering match observation timestamps?

---

## Numerical check

If the LLM states:

```text id="4fw9br"
voltage increased by X
current decreased by Y%
```

recompute it deterministically.

---

## Unit check

Verify compatible units.

Do not infer conversions that are not defined by the evidence contract.

---

## Lineage check

Ensure derived evidence has visible and valid parents.

---

## Claim-policy check

Map each claim type to the evidence required to support it.

The verifier may output:

```text id="c8x6zg"
SUPPORTED
QUALIFIED
INSUFFICIENT
```

Use `QUALIFIED` when part of the statement is supported but stronger interpretation is not.

---

# 11. Do Not Build a General Semantic Truth Oracle

The verifier cannot determine arbitrary real-world truth.

For example:

```text id="m89mjo"
"the attacker intentionally caused the voltage change"
```

cannot generally be verified from packet-derived evidence.

The correct result should usually be:

```text id="z0ys5f"
INSUFFICIENT
```

or a weaker qualified statement.

The paper must describe the verifier as:

> deterministic evidence-consistency and support verification

not:

> automatic truth verification.

---

# 12. Evidence Retrieval

Do not dump entire raw PCAP-derived evidence into the LLM.

Implement investigation-oriented retrieval.

Candidate retrieval keys:

```text id="psap96"
event scope
asset
time
protocol activity
command activity
electrical/process change
important observation intervals
```

Retrieve original structured evidence records, not only ML feature vectors.

ML feature importance may be used as a retrieval hint only if justified.

It must not be treated as causal evidence.

---

# 13. Experimental Evidence Conditions

For RQ1, use matched investigation conditions:

```text id="6nhdyg"
E-only
N-only
E+N
```

The same event IDs and investigation questions must be used.

Do NOT compare different event subsets.

The objective is to measure investigation completeness and support quality, not Cyber/Benign accuracy.

---

# 14. Investigation Questions

Create a fixed investigation-question template.

Candidate questions:

```text id="hm5jga"
1. What network activities were observed during the event?

2. What electrical/process changes were observed?

3. Which assets were involved?

4. What is the observable event timeline?

5. Are there temporal associations between network activity and electrical/process changes?

6. What security-relevant interpretation is supported by the available evidence?

7. What cannot be concluded from the available evidence?
```

Questions must not expose the gold event description or attack label.

Freeze the question set before final evaluation.

---

# 15. Gold Annotation

A human-reviewed investigation gold set is required.

Do not generate the final gold purely using an LLM.

Create:

```text id="3opwia"
annotations/guidelines.md
annotations/events/
annotations/gold/
```

For every selected event, annotate:

```text id="j9k8nc"
observable facts
acceptable evidence IDs
asset mappings
temporal relations
permitted security interpretation
unsupported conclusions
information that must remain unresolved
```

Each gold claim should be classified by claim type.

---

# 16. Annotation Policy

The annotation guide must explicitly distinguish:

```text id="cm71z9"
Observed fact
Derived numerical fact
Temporal association
Security interpretation
Causal claim
Unknown / insufficient evidence
```

Ground-truth attack labels may help evaluators understand an event but MUST NOT automatically make a claim observable.

For example:

The evaluator may know an event is malicious.

That does not allow the LLM to claim malicious intent unless visible evidence supports the claim under the investigation condition.

---

# 17. Event Selection

Do not automatically annotate all 119 events first.

Audit event-family diversity and evidence availability.

Propose a representative evaluation set across:

```text id="dht9tv"
cyber families
benign operational families
scenarios
different evidence availability
different electrical effects
different network patterns
```

Before final selection, produce:

```text id="0t73zm"
docs/investigation_event_selection.md
```

with rationale.

Do not select only easy events.

Do not select events based on LLM performance.

Freeze selected IDs before final prompt/verifier tuning.

---

# 18. Baselines

At minimum design the following investigation baselines.

## B0 — Deterministic timeline

No LLM.

Produce a structured chronological listing of retrieved evidence.

Purpose:

Establish how much value comes from simple evidence presentation.

---

## B1 — LLM without deterministic verification

LLM receives retrieved evidence and generates structured investigation claims.

---

## B2 — Evidence-cited LLM

Every substantive claim requires evidence IDs.

---

## B3 — Evidence-cited LLM + deterministic verifier

Unsupported or inconsistent claims are detected and qualified/withheld.

---

## B4 — Verified LLM + evidence sufficiency

If available evidence cannot support an investigation conclusion, the system explicitly withholds it.

---

# 19. Optional Evidence-Source Ablation

For selected baselines compare:

```text id="0mj5yo"
N-only
E-only
E+N
```

The expected value of E+N is not necessarily better classification.

Investigate whether:

```text id="1hd68u"
N-only:
better network context,
limited physical/process consequence

E-only:
better physical/process observation,
limited network intent/context

E+N:
more complete cross-domain event reconstruction
```

This hypothesis must be measured rather than assumed.

---

# 20. Primary Metrics

Do NOT use classification accuracy as the main metric.

Define investigation metrics.

At minimum:

## Citation Precision

Among cited evidence references, how many actually support the associated claim?

---

## Evidence Completeness

How many gold-supported investigation facts are recovered?

---

## Unsupported Security-Claim Rate

```text id="hflkpt"
unsupported substantive security claims
/
all substantive security claims
```

This should be one of the main paper metrics.

---

## Numerical Accuracy

Are reported values/deltas/reductions correctly computed?

---

## Asset Consistency

Do claims refer to the correct asset/evidence mapping?

---

## Temporal Consistency

Does the claimed event order match observable timestamps?

---

## Qualification / Withholding Accuracy

When evidence is insufficient, does the system correctly qualify or withhold?

---

# 21. Coverage vs Reliability

A system that says:

> insufficient evidence

for every question is useless but technically safe.

Therefore report both:

```text id="dqlckl"
coverage
and
error / unsupported-claim rate
```

Define investigation coverage as the fraction of investigation questions or claim opportunities where the system provides a substantive supported/qualified answer.

Report the coverage–reliability tradeoff.

---

# 22. Repeated LLM Runs

If the LLM is stochastic, perform repeated runs only to estimate output stability.

Do not count repeated runs as independent events.

The event remains the primary statistical unit.

Use event-level paired analysis.

---

# 23. Adversarial / Failure Tests

After the core system is stable, evaluate a small number of controlled evidence failures.

Possible cases:

```text id="v8cvdc"
missing electrical evidence
missing network evidence
retrieval failure
stale electrical observation
incorrect cited evidence ID
synthetic conflicting evidence
```

Clearly distinguish synthetic contradiction tests from real Sherlock events.

Do not claim synthetic contradictions represent real attacks.

---

# 24. Relationship to Previous Classification Work

Preserve existing classification/observability results.

They should be used in the paper primarily to motivate why classification alone does not solve incident investigation.

Do not spend the new research cycle trying to beat the existing classification scores.

The paper may state that:

> Under the evaluated full protocol-aware Sherlock condition, network evidence already provided highly discriminative event-level classification, motivating a shift from merely predicting event class toward evidence-grounded incident investigation.

Do not claim real-world OT attacks are easy to detect.

---

# 25. Repository Structure

Add, without overwriting previous results:

```text id="8i0cyh"
docs/
├── investigation_problem.md
├── investigation_event_selection.md
├── investigation_annotation_policy.md
├── investigation_protocol.md
├── claim_support_policy.md
└── paper_outline_incident_investigation.md

annotations/
├── guidelines.md
├── development/
└── gold/

src/
├── retrieval/
│   ├── investigation_retriever.py
│   └── evidence_formatter.py
│
├── investigation/
│   ├── schema.py
│   ├── prompts.py
│   ├── runner.py
│   └── timeline.py
│
├── verification/
│   ├── reference.py
│   ├── asset.py
│   ├── temporal.py
│   ├── numerical.py
│   ├── units.py
│   ├── lineage.py
│   └── claim_policy.py
│
└── evaluation/
    ├── citation_metrics.py
    ├── claim_metrics.py
    ├── coverage_metrics.py
    └── investigation_reports.py

configs/
├── investigation.v1.json
├── retrieval.v1.json
├── verification.v1.json
└── investigation_eval.v1.json

experiments/
├── run_timeline_baseline.py
├── run_llm_investigation.py
├── run_cited_investigation.py
├── run_verified_investigation.py
└── run_evidence_ablation.py

results/
└── investigation-v1/
```

Do not overwrite classification-v1/v2 artifacts.

---

# 26. Paper-First Constraint

All implementation decisions must correspond to one of:

```text id="ij9j88"
RQ1
RQ2
RQ3
a required baseline
a required metric
a documented threat to validity
```

Before adding a feature, model, prompt technique, agent framework, vector database, or extra dataset, answer:

> Which research question does this change help answer?

If there is no clear answer, do not add it.

---

# 27. Explicit Non-Goals

For this paper, do NOT expand into:

```text id="c6nz9d"
new deep-learning IDS architecture
continuous attack detection
attack attribution
malware classification
automatic remediation
agentic SOC automation
causal inference
adaptive E/N classification fusion
large multi-agent system
fine-tuning a foundation model
```

These may be future work.

---

# 28. Required First Codex Response

Do NOT start major implementation immediately.

First inspect the repository and return:

## A. Reusable Existing Components

Identify which current modules can be reused for:

```text id="14xks4"
EvidenceRecord
lineage
E/N views
asset mapping
episode construction
visibility checks
numerical calculation
existing retrieval/verifier code if any
```

---

## B. Missing Components

Identify what does not yet exist for the investigation paper.

---

## C. Proposed Claim Schema

Give the exact structured JSON schema.

---

## D. Proposed Claim-Support Policy

For each initial claim type specify:

```text id="7oekwj"
required evidence
allowed interpretation
prohibited stronger interpretation
mechanical checks
```

---

## E. Gold Annotation Plan

Propose how investigation gold will be manually reviewed.

---

## F. Candidate Event Set

Propose representative event families and selection criteria.

Do not select events based on LLM output quality.

---

## G. Exact Baseline Matrix

Specify:

```text id="qwh735"
evidence condition
LLM condition
citation requirement
verification
sufficiency
```

---

## H. Exact Evaluation Metrics

Give definitions and denominators.

---

## I. Minimal Implementation Order

Recommend the smallest sequence needed to obtain the first scientifically meaningful experiment.

---

## J. Research Risks

At minimum discuss:

```text id="bydwan"
ground-truth leakage
shared packet lineage
annotation subjectivity
LLM hallucination
causal overclaiming
citation without support
retrieval failure
small number of simulation recordings
reuse of already-inspected Sherlock data
```

---

# 29. Approval Gate

After returning A–J:

STOP.

Do not implement the full LLM system yet.

The author must approve:

```text id="5quut9"
claim vocabulary
support policy
investigation questions
event selection
annotation protocol
baseline matrix
metrics
```

before the experiment is frozen.

---

# 30. Research Principle

The paper should demonstrate:

> **An OT incident investigation system should not merely generate plausible explanations; each substantive security conclusion should be traceable to observable electrical/network evidence, mechanically checked where possible, and explicitly withheld when the available evidence is insufficient.**

Keep this principle as the main constraint for every design decision.