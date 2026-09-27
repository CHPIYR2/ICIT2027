# Investigation Protocol v1 — exact metric definitions

Version: metrics-v1-candidate-20260925. Specification only; no research results
computed. These definitions supersede the earlier exploratory metric table for
the proposed primary B0–B4 matrix, subject to final author protocol approval.

## Units and common rules

For event e and view v, G_e is the frozen set of unique salient positive EN-gold
facts, H_e is its separate guardrail set, and G_ev is the subset of G_e supported
by the full approved view. The pilot has 30 G and 24 H across four events; the 32
evaluation events need their own isolated final gold. These are annotation counts,
not system results. Each reviewed Q1–Q7 judgment is a separate fixed opportunity.

For each event, baseline and predeclared run, split every generated output into
atomic substantive assertions. A retained qualified assertion counts at its actual
weaker strength; an explicit limitation/withhold alone is not a positive assertion.
Any asserted stronger guardrail proposition counts as a substantive assertion even
when labeled unknown or buried in text. Preserve raw output and final published
output separately. For B4 score both the B3 raw input and B4 published output; the
primary B4 precision/recall use published output, with raw exposure disclosed.

Semantically identical duplicate assertions with identical content/support roles
are one precision unit; record duplication separately. Do not collapse correct
and incorrect variants merely because they share a fact key. An atomic assertion
matches at most one gold fact; a gold fact earns at most one recall credit. A
reviewed alias group has one canonical gold denominator member. Numerical
reported_change/electrical_change duplicates never create extra gold units; exact
claim-type matching is still enforced as specified in the matching candidate.

Support means evidence accessible in the actual input bundle establishes the
entire typed proposition and stated interpretation, under exact gates and the
approved numeric tolerances. Being true in full-universe gold alone is not enough
to claim input support. Human judgments of content/text are independent of the
verifier status. Pending human judgments remain pending: do not silently score
them as success, failure or NA. Tolerances must be approved before any scoring.

## 1. Gold Fact Recall

Numerator: number of distinct g in G_e correctly recovered with matching type,
identity/content/scope and complete accessible support. Denominator: |G_e|,
identical for B1 N and B2–B4 EN to measure reconstruction against a common target.
Companion view-conditional recall uses recovered g in G_ev / |G_ev| and reports
the modality ceiling |G_ev|/|G_e|. The common-denominator metric is primary.

Aliases count once. Guardrails H_e are excluded. A correct withhold, silence,
unsupported guess or overstrong version does not recover a positive fact. A
qualified statement counts only if its retained proposition matches a gold fact
at that approved strength. Optional-citation B1/B2 may earn content recall after
human verification against the bundle, but do not receive invented citation credit.

## 2. Supported Claim Precision

Numerator: unique substantive atomic assertions fully supported by the input
bundle and approved interpretation policy. Denominator: all unique substantive
atomic assertions emitted/published at the measured layer, including assertions
outside G_e and asserted prohibited guardrail propositions. A correct additional
fact may count in this numerator without expanding G_e or recall.

Duplicate true aliases count once; conflicting/incorrect variants remain separate.
Guardrail limitations and pure withholds are excluded, but a prohibited proposition
asserted as fact is included and unsupported. Qualified retained content is judged
at its actual strength. No assertions gives NA, not 1 or 0; always show assertion
count, recall and question coverage to expose all-withhold behavior.

## 3. Unsupported Claim Rate

Numerator: denominator assertions not fully supported, including contradictory,
missing-support, inaccessible-reference and overstrong assertions. Denominator:
the exact same assertion set as Supported Claim Precision. With completed binary
human support judgments, this is its complement; unassessed claims block the result.

Alias, guardrail and qualified/withheld rules are identical to precision. Report
an additional security-interpretation subset using all assertions about security,
causation, intent, success, attribution or safety anywhere in the text, regardless
of declared claim_type. A denominator of zero is NA; no security assertions is
not evidence of successful security investigation. Raw and published rates for B4
must be reported together to distinguish generation risk from publication filtering.

## 4. Question Coverage / Sufficiency

**Substantive coverage** numerator: number of Q1–Q6 answers containing at least one
correct, nonempty, accessible-supported assertion that meets that question's frozen
minimum at the stated scope. Denominator: 6 per event/run, fixed across baselines.
At most one credit per question, regardless of fact aliases or number of claims.
Q7 and guardrail-only answers are excluded. Withhold/insufficient answers earn no
coverage even if appropriate. An accepted partial/qualified answer earns coverage
only when its retained supported content satisfies the question's approved partial
answer requirement; a vacuous disclaimer never earns credit. Report each question
separately and the gold-view answerability ceiling; do not punish correct Q6
withholding by mislabeling it as an incorrect sufficiency decision.

**Sufficiency decision accuracy** numerator: correctly handled Q1–Q7 slots matching
the independent human full-view answerability and required scope, with appropriate
assert/qualify/withhold or explanation of retrieval insufficiency. Denominator: 7
per event/run. Disclose two components: (a) correct diagnosis of what the full view
can support; (b) correct operational action given retrieved support. They are
separate: an answerable full view may still require operational withhold because
retrieval omitted support. Never label retrieval failure as evidence absence.
Full-view diagnosis is scored only if the system output explicitly makes that
diagnosis; missing diagnosis is incorrect for that component, not filled by the
evaluator. Operational action can be scored from the explicit answer and reason.
The joint sufficiency numerator counts a slot only when BOTH components are correct;
report the two component numerators separately, each over the same seven slots.

For supported slots require a substantive adequately supported answer, or explicit
correct retrieval-shortfall diagnosis with withhold for the operational component.
For partially supported slots require the approved weaker scope plus limitation;
for insufficient slots require explicit correct insufficiency and reason. Q7 is
supported by accurately explaining limitations; that does not assert H_e. Silence,
generic refusal, missing/invalid question answer or wrong reason is incorrect.
No answerability/action is inferred just from number of facts. Minimum partial
support sets for evaluation must be authored in its gold before scoring.

## 5. Citation Validity

Numerator: valid (atomic assertion, distinct cited evidence ID) pairs. A pair is
valid only if the exact ID exists in the correct event/version, is accessible in
the actual bundle (including approved static/query records), has the claimed role,
and supports the attributed part without contradictory scope. Denominator: all
such cited pairs, including fabricated, hidden, wrong-event and irrelevant IDs.
Duplicate IDs within one assertion count once; duplicate equivalent assertion
units use the same dedup rule. Different assertions citing one ID remain separate.

Qualified retained assertions and explicitly cited guardrail/limitation explanations
are included, with their own scope-specific support roles. Uncited withholds add
no pairs. If no citations, validity is NA, never perfect. Report cited substantive
assertion coverage = number with at least one citation / all substantive assertions.
Also report cited complete-support rate = substantive assertions whose entire
support requirement is jointly met by their citations / all substantive assertions.
Missing citations therefore cannot game the primary grounding comparison B2→B3.
Mere individual citation validity does not imply joint complete support.

## 6. Verifier disposition accuracy (B4)

For every atomic B3 input claim presented to the B4 verifier, a human oracle whose
judgment is independent of the verifier's decision records the correct disposition
under the actual bundle and frozen policy (this does not imply a second reviewer):
SUPPORTED (publish unchanged), QUALIFIED (a specified supported weaker canonical
proposition may be published with the correct reason), or INSUFFICIENT (withhold
with the correct reason). A gold fact's full-universe status is not this oracle.

Numerator: input claims with exactly correct disposition AND required retained
content/reason; denominator: all input claim units handled by B4. Incorrect
qualification, publishing a stronger remnant, wrong-reason withholding, missing
output or verifier failure are incorrect. Fully duplicate input units may be
deduplicated only using the common assertion rule; conflicting variants remain.
Guardrail propositions asserted in B3 are included, normally requiring INSUFFICIENT;
explicit truthful limitations are judged as limitations. Do not use B4's own labels
as the oracle. Report confusion counts, class denominators and supported-claim
false-withhold rate. No B3 input claims gives NA, not perfect verification.

To expose unaddressed obligations separately, report **fixed-opportunity action
accuracy** over each unique positive gold + guardrail slot in G_e ∪ H_e: numerator
is slots with an explicit correct action, retained scope and reason given the
retrieved support; denominator is |G_e|+|H_e|. Absence is NOT_ADDRESSED, not successful
withholding. Guardrails count once each; aliases do not multiply opportunities.
Positive and guardrail strata must be shown separately. This companion does not
replace claim-input verifier accuracy and requires no new model-comparison arm.

## Aggregation, failures and reporting

Every metric above records integer numerator/denominator for each event/baseline/run
and each stated component. Micro = sum of numerators / sum of denominators.
Compute the ratio per run first; event score = mean of defined run ratios. Macro =
unweighted mean of defined event scores, so claim-rich events do not dominate.
For zero-denominator cases use NA and report numbers of defined runs/events; never
silently drop a failure with a nonzero fixed denominator. With one run, event score
is simply its ratio. Run count/seed are pending model configuration decisions.

Research contrasts are paired at the event level: B1→B2, B2→B3, B3→B4. Average runs
within each event first, then compare common defined event sets for conditional
metrics, reporting n and coverage/NA differences. Events, not facts/packets/runs,
are the statistical units. Evaluation sample is 32 events, not the 54 pilot entries.
Uncertainty procedure must be fixed before final evaluation inspection; no claim
of independent recording-level generalization or inter-annotator agreement.

Transport failures, invalid schema and truncation remain recorded attempts.
For fixed-denominator recall/coverage/sufficiency/action metrics they score zero
where no valid result exists. For assertion-based metrics, independently review
recoverable raw assertions for overclaims; if none can be assessed, report NA plus
the failure, not a perfect score. Schema compliance/failure counts are mandatory
diagnostics. No retries to select the nicest answer; transport retry parameters
must be predeclared. No model-comparison experiments in the primary matrix.
