# Investigation Protocol v1 — semantic resolution candidate r2

Status: AUTHOR REVIEW REQUIRED; NOT FROZEN. Specification only. No matcher,
B1–B4 implementation, model call, or research scoring is introduced. The author’s
numeric, time, Q5/Q6, single-reviewer, isolation and baseline decisions are accepted
in principle in this revision; the semantic projection below awaits approval.

## 1. reported_change versus electrical_change

Let a and b denote the approved before/after E observations, M their sanitized
channel metadata, and F = {voltage, current, active_power, reactive_power}.

| Field | reported_change | electrical_change |
|---|---|---|
| Definition | Difference or percentage change between two valid reported numeric observations. | The same reported numeric fact, restricted to an electrical family in F. It is not an independently established physical change. |
| Required evidence | Two valid e IDs, same channel/asset/source unit, approved channel M, valid lineage, event and accessible view/bundle. A derived d record does not replace its parents. | All reported_change requirements plus consistent family membership in F established by both E records and M. |
| Fact key | Existing phase2a key: event + normalized reported_change kind + ordered before/after e IDs + quantity + unit. | The existing key proposal already normalizes its kind to reported_change. A shared key only identifies a candidate fact; it does not validate family, values, scope or truth. |
| Asset identity | Both E asset IDs must agree with channel M; compare the exact opaque asset. Null is not a wildcard or evidence of a known asset. | Same; no extra command-target identity may be inferred. |
| Channel identity | Exact same E channel ID and approved metadata lookup. | Same, including consistent electrical family. |
| Before evidence/value | before_id is an e ID, never p/m/a; before_value is the finite numeric value from that E, not a Boolean/configuration/setpoint. | Same. |
| After evidence/value | after_id is a distinct e ID; after_value is the finite numeric value from that E. | Same. |
| Timestamps | Exact stored capture times in the approved window; before_time < after_time. File order cannot break ties. | Same; no physical action or exact transition time follows. |
| Unit | Both source units agree exactly. Difference uses that source unit; percent_change result uses PERCENT. No conversions. Schema’s broad unit enum does not itself authorize every unit. | Same, with current family/unit mapping voltage→PER_UNIT, current→AMPERE, active_power→WATT, reactive_power→VAR. |
| Delta | Signed b.value − a.value, not absolute magnitude; zero difference is permitted. | Same. |
| Relative delta | 100 × (b.value − a.value) / abs(a.value), expressed in percentage points; a.value=0 makes this operation insufficient, not zero. No denominator floor. | Same. This is supported by the base table’s “same as reported_change”, its shared checks, the shared delta schema, and the quantity-aware fact-key policy. |
| Quality requirements | Both observations present, numeric/non-Boolean, finite and quality-valid; approved metadata/provenance; derived result finite. | Same plus the family gate. |
| Allowed interpretation | These two records report these values and their computed difference/percentage at these capture times. | The same assertion explicitly concerning an electrical measurement family. |
| Prohibited stronger interpretation | Continuous trend, exact transition time, device action, causation, dangerous threshold, malicious intent, successful compromise, attribution or safety without support. | Same; “electrical” does not establish physical truth, attack-caused change, severity, shutdown or de-energization. |
| Verifier checks | Reference roles, visibility, provenance, E/M agreement, exact identities/time/unit, numeric validity and arithmetic, operation, interpretation boundary. | All common checks plus E-before/E-after/M family agreement and F membership. A schema PASS or key match alone cannot establish this. |
| Q1 relevance | No network/command fact follows. | Same. |
| Q2 relevance | Direct process/value-change evidence. | Direct electrical/value-change evidence. |
| Q3 relevance | Channel/asset context only with its approved M mapping; do not silently create a separate relationship fact. | Same. |
| Q4 relevance | Supports the capture ordering of its own pair, not the trajectory or actual transition time. | Same. |
| Q5 relevance | May supply the process side; requires separate network evidence and temporal claim. Same-asset scope requires approved mapping on both sides. | May supply the electrical side under the same requirements. |
| Q6 relevance | May be an observed input to a separately justified investigation-relevance statement; not automatically a security indicator or malicious/benign classification. | Same; electrical magnitude alone does not establish security relevance. |
| Q7 relevance | Supports explaining these interpretation limits; a limitation does not assert its prohibited stronger proposition. | Same. |

The two types share `$defs/delta` in `schemas/investigation_claim.v2.json` and the
same common identity/citation fields. The payload does not carry family. The
runtime structural validator therefore cannot replace evidence-dependent semantic
checks. Existing B0 emits `reported_change`, carrying a numeric_difference record
with both difference and percent_change fields; the raw shape is not the typed
delta schema. No existing B4/general numeric verifier is claimed to be complete.

Audit scope: four sealed development-pilot annotations and their sealed approved
EN evidence only; B0 representation was inspected in source code. All eight raw
electrical_change gold entries use quantity=difference. Their E-before/E-after/M
family, channel, asset, unit, quality and ordering agree. Each signed annotation
explicitly explains that the reported_change form is not an additional fact.
This is evidence-contract validation, not a B0 recovery or performance result.

## 2. Recommended semantic resolution and justification

**B: electrical_change is a strict semantic specialization of reported_change.**
The original `docs/claim_support_policy.md` explicitly adds F membership and says
the same content counts once. The sealed phase2a fact-key policy and all eight
signed gold rationales independently preserve this same-fact distinction. A is
unsupported for the same ordered pair/quantity; C would incorrectly erase the
family restriction. The current export happens to allow only these four numeric
families plus Boolean state, so the presently reachable numeric domains coincide;
this does not make the ontology definitions globally identical or authorize new
non-electrical evidence families.

There is a real candidate-layer inconsistency to repair: r1 matching enforces
literal raw types even for the already documented same-content specialization.
There is also a provenance gap: the pilot-v1 manifest binds the v2 command-target
amendment but not the original base support table. That table is titled a proposal;
it is evidence of existing candidate semantics, not retrospectively certified
frozen policy. Therefore B is justified as a pre-freeze resolution proposal, not
an already activated scoring exception. D is not necessary as the final ontology
choice: the family relation is explicit, but author approval is needed to resolve
the matching inconsistency and bind the complete policy chain prospectively.

The base policy is copied byte-for-byte into the r2 audit package and hashed.
Its historical 1e-6 numeric and 1 microsecond duration tolerances are NOT reinstated.
For the new candidate the author-selected numeric/time policy supersedes them;
the accepted Q5/Q6 definitions supersede older, broader security-template wording.
The v2 amendment continues to govern command/address roles. Original snapshots,
annotations, schemas and raw claim types remain unchanged.

Proposed canonical **evaluation** representation, version `numeric-fact-projection-v1`:

- Preserve source file/output hash, source claim/field location, raw_claim_type,
  original fact_key (if present), raw payload and text. Never rewrite source gold.
- The match identity is `(version, event_id, evidence_export_version,
  canonical_kind=reported_numeric_change, before_e_id, after_e_id, asset_id,
  channel_id, family, source_unit, operation, result_unit)`. Each component is
  exact. Approved alternate support sets remain governed by reviewed gold; this
  proposal introduces no cross-pair alias. Run/view/bundle hashes are support
  provenance, not additions that would make the same event fact baseline-specific.
- Carry before/after values and exact timestamps, computed reference result,
  metadata ID and actual support IDs as checked content/provenance. Numeric values
  do not belong in a rounded/hash-based identity key; compare them separately.
- For the two raw types, allow cross-type matching only after both propositions
  pass all common gates and the E/M evidence proves the same family in F. The
  projection's family comes from approved evidence, never from an asserted label.
- An electrical_change claim with missing/conflicting/out-of-domain family fails
  the specialization check. Do not relabel it reported_change to hide the failure.
  An unsupported causal/severity assertion is not equivalent to a numeric fact.
- Other raw types retain literal exact matching. Booleans/state transitions,
  generic reported_value, different pairs, channels, operations or scopes never
  become this fact through this rule. No natural-language similarity matching.
- A key/projection identifies a potential match, not support. Missing production
  evidence still prevents recovery. No gold evidence may be injected into B0/B1–B4.

For a numeric difference, channel M is the approved bundle's validation context;
the reviewed minimal support sets containing the two E IDs are not rewritten to
add a new citation obligation. Those E records must still agree with accessible M.
A separate asserted mapping relationship retains its existing explicit M-citation
requirement. Context validation never earns a citation that the system did not emit.

This applies uniformly to all B0–B4 outputs, before results are seen. It is a
declared specialization-aware representation rule, not a new human alias decision.
The companion JSON specifies the rule but activates no evaluator.

## 3. Exact protocol files that change through an additive revision

Old r1 paths remain historical, byte-identical files. r2 becomes the candidate
entry point; the following explicit overrides take effect only upon approval.

| Existing file / role | r2 candidate change |
|---|---|
| configs/investigation_protocol.v1.freeze_candidate.json | configs/investigation_protocol.v1.semantic_resolution.r2.json selects in-principle decisions, binds this addendum and both support-policy sources, and retains pending freeze status. |
| configs/investigation_matching.v1.candidate.json | configs/investigation_matching.v1.semantic_resolution.r2.json selects numeric A/time values and specifies the pending, gated raw-type exception. |
| docs/investigation_matching.v1.candidate.md | Sections 1–2 and 4 of this addendum replace the literal-type prohibition for this one gated case and obsolete numeric/time approval alternatives. All other gates remain. |
| docs/investigation_fact_keys.phase2a.proposed.md | Sections 1–2 and 4 clarify that existing key normalization requires support/family checks for matching; original fact keys and alias decisions are preserved. No new adjudication occurred. |
| docs/claim_support_policy.md + docs/claim_support_policy_v2.md | Complete source chain is explicitly bound; section 2 states precedence. The base table’s numeric semantics are adopted prospectively subject to approval; old tolerance values are superseded. |
| docs/investigation_metrics.v1.candidate.md | Section 4 replaces raw-type equality with gated canonical equality for the two types only. All metric units, formulas, aggregation, guardrails and NA rules otherwise remain. |
| docs/investigation_verification_policy.v1.candidate.md | Sections 1–2 and 4 add explicit family validation, no label-based repair, and identical B3 replay/provenance. |
| docs/investigation_baselines.v1.candidate.md | Section 4 resolves the pending B0 label issue prospectively; generation and B0–B4 controlled contrasts remain unchanged. |
| configs/investigation_protocol.v1.freeze_inventory.json | configs/investigation_protocol.v1.freeze_inventory.r2.json retains historical bindings and adds exact r2 file hashes. This is an inventory candidate, not a freeze lock. |

New standalone artifacts: this addendum;
`configs/investigation_numeric_fact_projection.v1.candidate.json`;
`results/investigation-semantic-r2/pilot_semantic_audit.json`;
`results/investigation-semantic-r2/base_claim_support_policy.snapshot.md`;
`results/investigation-semantic-r2/verification.json`; and
`results/investigation-semantic-r2/delivery_manifest.json`.
No source annotations, sealed manifests, claim/export schemas, retrieval code,
B0 generation code, matching implementation or verifier implementation are changed.

## 4. Matching and metric consequences

**Numeric/time decisions recorded:** Option A: absolute tolerance 0 and relative
tolerance 5e-8 for AMPERE/PER_UNIT/WATT/VAR and PERCENT, with
`abs(pred-reference) <= max(atol, rtol*abs(reference))` after exact gates. Zero
reference requires zero; small nonzero values and sign are preserved. The reference
uses approved evidence, not rounded annotation prose. At least eight significant
digits or round-trip serialization is required. No inference of physical accuracy.
Capture timestamps/order remain exact; only displayed Δt uses 5e-7 SECOND absolute
tolerance and zero relative tolerance. It cannot change direction or equality.

**B0:** Its raw reported_change row remains untouched. A future versioned format
adapter may map before_id/after_id/values/times plus channel_id/asset_id to the
common representation. The difference field yields operation=difference and
result_unit=the source unit. A non-null percent_change field is a separate
arithmetic assertion with operation=percent_change and result_unit=PERCENT;
retain the row's original source unit separately, never interpret a percentage
as WATT/AMPERE/etc. Null percent with zero_baseline asserts no numeric percentage.
Before/after values are checked components, not automatically extra reported_value
facts. Independently emitted reported_value claims remain distinct assertions.
Do not generate missing values or citations in this adapter. Distinguish implicit
approved M context from IDs explicitly cited by the raw output. A raw B0 label
can cease to be a mismatch; wrong pairs, missing retrieval, arithmetic errors,
incorrect citations or stronger interpretations still fail. No score or recovery
count is calculated here.

**Gold Fact Recall:** Per event/run numerator is unique positive gold facts
recovered by a supported matching proposition; denominator is the same fixed
unique EN-positive G_e for every baseline. Replace only type matching with the
gated rule above. View-conditional recall still uses G_ev. No raw-label double
credit: all eight electrical facts remain eight, the pilot total remains 30;
24 guardrails are excluded. A percent alone does not recover a difference fact
without an explicitly reviewed alternative; secondary percent prose creates no
new gold row. Withheld/insufficient, unsupported guesses and missing retrieval
earn no positive recall. Qualified output counts only at its retained strength.

**Supported Claim Precision:** Numerator is unique substantive assertions fully
supported by the actual input; denominator is all substantive assertions at the
scored raw/published layer, including non-gold assertions and asserted guardrail
propositions. Conditional cross-type duplicates with the SAME asserted content,
quantity, strength and support roles count once. Wrong/right variants sharing an
identity remain separate; numeric closeness alone is not a transitive duplicate
equivalence. A missing family or false electrical label remains an unsupported
assertion and may not disappear in dedup. Pure withholds/limitations are excluded;
qualified retained claims are judged at their actual scope. No assertions is NA.
Recall and precision are different: supported unselected facts can earn precision
without changing gold or recall. Difference and percent are separate assertions,
not automatically duplicate precision units. Existing reviewed alias rules apply.

**Alias accounting and denominators:** Preserve every human alias_of, alias_decision,
alias_rationale, fact_key and raw type. Log raw units, original gold IDs, canonical
identity, proposed cross-type equivalence, checks, duplicate membership and failed
gates separately. This proposal adds no gold aliases. A gold alias group still has
one denominator member; conflicting/incorrect generated variants are retained.
The 30-positive/24-guardrail/28-question pilot inventory is unchanged. Projection
does not manufacture extra Q coverage, support sets or independent corroboration.

**Other metrics:** Unsupported Claim Rate retains precision's denominator and
unsupported numerator. Citation Validity retains exact assertion–cited-ID pairs;
canonicalization never fabricates M/e citations. Missing citations still affect
cited coverage/complete-support companions. Coverage remains six Q1–Q6 slots;
sufficiency remains seven Q1–Q7 slots with separate full-view and retrieved-action
components. Q5 needs a distinct supported N/E temporal relationship; Q6 keeps all
four interpretation layers and the signed pilot judgments unchanged. Each metric
retains r1 per-event/run integer numerators/denominators, micro=sum(n)/sum(d),
run-averaged event scores and equal-event macro, with zero-denominator NA disclosed.
No evaluation denominator is inferred from the pilot counts.

**Verifier:** Future B4 consumes the byte-identical stored B3 output and its exact
bundle/receipt; record their hashes and B3 run ID. No regeneration, extra retrieval,
gold lookup or model call. Validate raw semantics/family before canonical matching;
absence of a supporting family forbids SUPPORTED for electrical_change. This
proposal defines no automatic generic downgrade: a failed numeric specialization
is withheld with its explicit reason unless a separately approved weaker projection
applies. QUALIFIED may publish only that checked weaker proposition, never the
unsupported stronger remnant. The disposition oracle remains human and independent
of verifier status, not an independent second annotator. Verifier accuracy numerator
is correctly disposed input units including required retained content/reason, over
all B3 input claim units under the existing duplicate rule; guardrail assertions
stay included. Missing output is incorrect, no-input is NA. The fixed gold+guardrail
action companion remains unchanged. Family checks are specified, not implemented.

## 5. Remaining unresolved author decisions

1. Approve B and the conditional canonical evaluation representation, complete
   policy-chain binding, precedence and metric consequences in this r2 addendum.
   This is not permission to silently change raw types or human annotation.
2. Approve the integrated final matching/metric/verification specification and,
   separately, authorize later implementation and conformance validation. Existing
   v2 structural schemas can stay unchanged; family support is evidence-dependent.
3. Set the pending model/prompt/run configuration below; fix event-level uncertainty
   procedure and reporting, transport retry policy and failure handling before
   evaluation exposure. No model comparison is added to the primary matrix.
4. Finalize evaluation-gold collection/custodian/access controls and evaluation
   reviewer responsibilities without granting protocol developers tuning access.
   A sealed manifest/commitment and role-separated gold workflow are needed; the
   32 events/gold/results may not tune prompts, retrieval, verifier, tolerances,
   claim semantics or metrics after freeze. Any exposure-informed later change
   requires a new exploratory version, never a silent revision to v1.
5. Explicitly approve the final named artifact inventory and the actual protocol
   freeze only after the checklist below is complete.

Numeric Option A, time ordering/display tolerance, Q5/Q6, single-reviewer wording,
the fixed B0–B4 matrix and identical B3 replay are recorded as accepted in principle;
they are not presented as unanswered A/B choices again.

## 6. Model, prompt and token fields still pending

The unchanged `configs/investigation_model.v1.pending.json` retains null provider,
exact model snapshot/version, temperature, seed and seed-supported policy,
max input tokens, max output tokens, final evidence token budget, tokenizer/version,
model-fit verification, prompt version/hash/files, run repetitions, transport retry
policy and cost budget. B1–B4 share the same LLM model component; B4 makes no new
generation call. Existing retrieval caps (N:64 N; EN:32 E+32 N; 48,000 compact JSON
bytes) are fixed evidence constraints, not a selected model token budget. Exact
prompt artifacts and hashes for each generation condition are still required.

## 7. Final pre-freeze checklist

- [x] Four single-reviewer files remain byte-identical to the sealed pilot-v1
  manifest; 30 positive facts, 24 guardrails and 28 reviewed question judgments.
- [x] Audit all eight electrical pairs against sealed pilot evidence and M; retain
  raw types and alias rationales; record hashes and the base-policy provenance gap.
- [x] Record accepted-in-principle A/time, Q5/Q6, isolation and B0–B4/B3-replay rules.
- [ ] Author approves the semantic specialization/projection and policy precedence.
- [ ] Author resolves model/prompt/token/run, uncertainty, reviewer/custodian and
  evaluation-gold access decisions without using held-out outcomes for tuning.
- [ ] After separate authorization, finish and validate the common output adapter,
  B1–B4/prompt artifacts and deterministic verifier against development/synthetic
  cases. Include wrong family, missing M, conflicting metadata, inaccessible E,
  Boolean confusion, zero/tiny baseline, reversed/equal timestamps, wrong quantity/
  unit, false causal text, contradictory duplicate and B3-replay integrity cases.
  This checklist item authorizes no implementation in the current task.
- [ ] Produce complete exact final artifact hashes: support/schema/matching/metrics,
  adapter/verifier/code, prompts/model/retrieval settings, isolation/gold commitment
  and inventory; independently verify conformance without evaluation tuning.
- [ ] Obtain explicit author freeze approval, then seal a separately versioned v1
  lock. Until then protocol_frozen=false; this task stops for author approval.
