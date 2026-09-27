# Investigation Protocol v1 — question semantics

Version: questions-v1-candidate-20260925. Final candidate text under the author's
direction; formal protocol freeze still awaits approval. The existing 28 pilot
question judgments and 54 reviewed entries are not modified or relabeled.

Q1: What network activities, command requests and responses were observed?
Minimum: one valid observed N fact with the claimed protocol semantics; a command
is not mandatory when other network activity is supported. ACK/COT7 is not proof
of physical execution or completion of a particular request without correlation.

Q2: What process/electrical values and changes were reported?
Minimum: one quality-valid E observation. A claimed change additionally needs two
valid same-channel compatible observations in strict capture order and the stated
operation. State change is optional and never an event/question coverage quota.

Q3: Which observed assets/channels/endpoints are involved and what is unknown?
Minimum: an actual observation plus its approved mapping or an actual packet with
its directional endpoint pair. A static inventory entry alone is not involvement.

Q4: What capture-time ordering is supported?
Minimum: at least two distinct observations supporting the stated precedes or
same_capture_time relation. For precedes the stored timestamps must differ in the
stated direction. No message interaction or device-action chronology is inferred.

## Q5 — cross-source temporal relationships

Q5 asks which supported temporal relationships connect observed network activity
and electrical/process observations within the supplied event window.

Minimum support: one valid N observation (p/m, or a supported command-address child
with its m parent) and one quality-valid E observation, both actually accessible
in the report's input, with exact capture-time ordering/equality. E-only or N-only
cannot substantiate Q5; a correct explicit insufficient answer remains valuable
for sufficiency accuracy, but earns no substantive Q5 coverage.

Two distinct scopes are permitted:

- **episode_only**: actual N/E records and exact time relation. No asset identity
  is implied; shared packet ancestry may yield capture-time equality and must not
  be described as independent corroboration.
- **same_observed_asset**: command m+a+control M, valid E+channel M, exactly matching
  opaque asset on both mapping edges, and the actual stored time relation. A
  target string or an uncited asset inventory is not a substitute for both edges.

A single valid relationship can satisfy Q5; no minimum number of state changes or
multiple command targets is required. Gold salience/alias choices remain those of
the reviewed annotation. If only episode scope is supported, qualify an attempted
same-asset statement to that scope or withhold its stronger part.

This is asset-linked temporal evidence when both mappings exist. Neither scope
supports command execution, physical causation, malicious intent, successful
compromise or attribution. Do not use later reported values as execution receipts.

## Q6 — conservative security-investigation relevance

Q6 asks which concrete observations or evidence combinations warrant further
security investigation and what interpretation boundary is supported. It does
not classify the event as malicious or benign.

Keep four separately reviewable layers:

1. **Observed evidence**: specific captured command, ACK, RST, gap, quality flag,
   or reported value/change, with exact accessible evidence references.
2. **Supported relationship**: only an established mapping, compatible numerical
   comparison, or capture-time relation, with its actual scope and support set.
3. **Investigation relevance**: an explicit, evidence-grounded rationale for a
   concrete unresolved security question and a useful next check. A single reviewer
   must judge its relevance under this fixed rubric; mechanical presence of a
   primitive or relationship does not automatically justify review_required.
4. **Unsupported stronger interpretation**: explicitly exclude execution, physical
   causation, intent, compromise, attribution and benign/safe-from-absence unless a
   future separately approved evidence policy establishes them.

A supported positive Q6 answer requires layers 1 and 3, layer 2 whenever invoked,
and the boundary in layer 4. The rationale cannot depend on G, malicious labels,
unavailable topology, an assumed normal baseline, invented thresholds, or hidden
observations. Commands, large changes, gaps and same-asset timing alone are not a
sufficient relevance rule. A generic 'worth investigating' sentence is insufficient.

If evidence establishes only reconstruction facts, retain those under Q1–Q5 and
state Q6 insufficient for a positive security-relevance conclusion. If only a
weaker concrete rationale is supportable, qualify to that explicit rationale;
do not assert unsupported incident classification. The current four reviewed
pilots have Q6 insufficient in all views. Preserve those decisions: positive Q6
recall cannot be estimated from this pilot set, and safe/benign does not follow.

No new positive Q6 annotations or numerical alert threshold is generated here.
Final scoring of relevance and stronger text follows the single-reviewer rubric
independently of verifier output; runtime generation/verifier implementation remains
unimplemented. Any future deterministic relevance rules require author approval
before evaluation-gold/results exposure and must not silently manufacture relevance.

Q7: What cannot be concluded and what support is missing?
Minimum: explicit limitations, relevant missing support and appropriate withhold/
qualify actions. Supported Q7 means limitations can be explained, not that the
prohibited propositions are true. Guardrails do not become positive facts or add
substantive Q1–Q6 coverage.
