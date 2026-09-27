# Investigation Protocol v1 — integrated development candidate r3

Status: **DEVELOPMENT IMPLEMENTED; PROTOCOL NOT FROZEN**. The current author approval
integrates semantic-resolution r2. The exact model, evidence-token cap, prompts and
remaining compatibility/custody decisions still require final approval. This work
ran local development/synthetic conformance tests only: zero model calls, zero
evaluation event runs, no evaluation gold creation/inspection and no research scores.

Entry point: `configs/investigation_protocol.v1.development_candidate.json`.
Authorization: `results/investigation-development-v1/approval/author_approval.txt`.
All r1/r2 candidates and the sealed pilot-gold snapshot remain historical records.

## 1. Integrated semantic-resolution test results

Resolution B is now approved: electrical_change strictly specializes reported_change.
The implementation validates raw support before constructing a canonical evaluation
identity. Asset/channel, ordered E pair, source/result units, family, exact capture
timestamps, finite values, arithmetic and interpretation gates remain mandatory.
Raw types, values, text, source positions and hashes are preserved. There are no new
gold aliases; a same-key invalid assertion is not repaired or merged into a valid one.

Eight sealed pilot electrical pairs pass manufactured conformance cases under both
raw numeric types; these are not B0 or model recovery results. The four reviewed
annotation files and gold manifest remain byte-identical. Gold is still **single-reviewer
gold**, with 30 positive facts, 24 guardrails and 28 reviewed question judgments.
Single-reviewer judgment is an explicit methodological limitation: no dual independent
annotation, adjudication or inter-annotator agreement is claimed.

Numeric matching uses exact rational comparisons against the approved binary source
values: absolute tolerance 0, relative tolerance 5e-8. Parsed prediction decimal
representations are compared without adding an epsilon. Exact zero and tiny nonzero
values remain distinct. Displayed durations use 5e-7 seconds absolute tolerance and
zero relative tolerance; timestamp ordering/equality remains exact. Raw output bytes
are retained for any later decimal-token audit.

Implementation: `src/investigation_dev/claims.py`, `adapter.py`, and `gold_contract.py`.
Approved settings: `configs/investigation-dev-v1/matching.json`, `numeric_projection.json`.

## 2. Selected-model capability report

Proposed single model: OpenAI `gpt-4.1-2025-04-14`, Responses API, temperature 0.
The provider lists a dated snapshot, 1,047,576-token context and 32,768-token maximum
output. The selected endpoint has no seed parameter. A snapshot pin is not a guarantee
of immutable or deterministic execution. Account access was not tested.
See `docs/investigation_model.capabilities.v1.md` for official sources, controls,
token-counting method and reproducibility metadata. No leaderboard was implemented.

## 3. Development-only evidence token-budget audit

The audit reads only the existing 16 development events × N/EN retrieved bundles
and receipts. It uses the exact approved compact sorted-JSON serialization and
`tiktoken==0.12.0/o200k_base`. It neither regenerates retrieval nor reads model answers.
All source-file and serialized-bundle hashes are recorded.

| Evidence view | Events | Minimum | Median | p90 | p95 | Maximum |
|---|---:|---:|---:|---:|---:|---:|
| N | 16 | 8,239 | 8,376.5 | 8,665.5 | 8,702.25 | 8,727 |
| EN | 16 | 10,610 | 10,733.5 | 11,081.5 | 11,126.75 | 11,162 |

Quantiles use linear interpolation at `(n−1)q`.

| Candidate evidence cap | N exceedances | EN exceedances |
|---|---:|---:|
| 8,192 | 16 | 16 |
| 11,162 | 0 | 0 |
| 16,384 | 0 | 0 |
| 32,768 | 0 | 0 |

Prompt text counts are B1=4,514, B2=4,514, B3=4,520. With the proposed 32,768 output
reserve, no development input exceeds the 65,536, 131,072 or published 1,047,576
context candidates under this local text-count diagnostic. This is not an exact
provider-framing count. The worst local evidence+prompt+output total is 48,450.

Data: `results/investigation-development-v1/token_budget_audit.json`.

## 4. Proposed fixed evidence budget

**11,162 evidence tokens**, the maximum across both production views of all 16
development events. This is the minimal integer cap covering the measured inputs,
not a guessed headroom multiplier. Proposed local input-text cap is 15,682 tokens;
the model output cap is 32,768, its documented maximum. Author approval is pending.

The same evidence cap applies to B1, B2 and B3; B4 reuses B3. Preserve the existing
N=64 N entries and EN=32 E+32 N entries, and common 48,000-byte cap. There is no new
trimming, evidence reordering, quota reallocation or retrieval. A future overflow
is a recorded preflight failure with no model call; changing a cap requires a new
approved version. Actual N and EN token consumption differs: fairness is a common
budget ceiling and controlled retrieval contract, not equal realized token counts.
The existing B1/B2 contrast is not “identical N evidence plus added E”.

Proposal: `configs/investigation-dev-v1/token_budget.candidate.json`.

## 5. Prompt files and hashes

All prompts share identical questions, ontology/schema, numerical rules, Q5/Q6
boundaries, output instructions and finite wording templates. B1/B2 differ only
in N versus EN view. B2/B3 differ only in citation mode and the required-citation
instruction. B4 has no generation prompt. No gold descriptions, scenario labels,
attack-family hints, attack points, simulator truth or evaluator data are injected.

| Prompt file | SHA256 |
|---|---|
| prompts/investigation-v1/B1.v1.txt | 679abefd3f89293a4bcd3a7fd044f5ef2f311d2fe9ad30e6d27e0a658eab992c |
| prompts/investigation-v1/B2.v1.txt | 32d3cd94b00286a462bde0c5aee95c208aaeec60ce29709153839aa1d3cd5856 |
| prompts/investigation-v1/B3.v1.txt | 7064007b145198503a73d93c0f847d92ab4b688ffc575dfb8832fa53e7922da6 |

`prompts/investigation-v1/manifest.v1.json` binds those files, common text, wording
templates, question definitions and the unchanged v2 claim schema. These are prompt
candidates, not evaluation-optimized or frozen prompts.

## 6. Retry and repetition configuration

Temperature=0; three independent requests per event/generation baseline, repetitions
1–3 retained and scored. No best repetition selection. B4 has one exact replay of
each B3 repetition; B0 is the existing deterministic EN artifact referenced by three
aligned slots, not three independent generations. The development plan has 240
aligned slots: 144 proposed generation requests, 48 B3 replays, and 48 references to
16 existing deterministic B0 artifacts. No such model requests were executed.

At most three transport attempts per repetition (initial+two retries), fixed delays
1 and 2 seconds, timeout 120 seconds. Retry only connection/timeout failures, HTTP
408/429/5xx, malformed provider envelope, or a completed response without a recoverable
JSON experiment envelope. The exact boundary is documented: a JSON object with
claims and questions lists is retained, even when its claims/citations/schema,
question links or event context are wrong. Those are experiment outcomes, not retry
opportunities. Missing citations, low correctness, missing evidence and verifier
rejection never trigger generation. Refusals, output-limit truncation, other 4xx
errors and unsupported controls are terminal. No hidden SDK retries are used.

Every request/attempt/raw response, available partial output, provider metadata and
failure is retained with hashes. Retries use the same body; attempt request IDs differ.
A transport timeout may leave provider completion/billing uncertain; no unseen answer
is claimed recovered. The configuration remains reviewable before live use.

Configuration: `configs/investigation-dev-v1/generation.json`.

## 7. Statistical-analysis configuration

Event is the statistical unit. Keep three repetition ratios for stability, reporting
within-event mean, range, population standard deviation and defined/NA counts.
Primary analysis averages within event, then equally across events. Pooled micro is
complementary. B0 shared slots do not triple its micro denominators.

Use 2,000 event-level bootstrap resamples, seed 20270922, percentile 95% intervals.
Preserve each predeclared scenario stratum’s event count; all repetitions travel with
the sampled event. Paired B1→B2, B2→B3 and B3→B4 contrasts resample common events
together. Missing strata fail rather than being guessed. Singleton strata are retained
and their lack of within-stratum resampling variation is disclosed. Conditional metrics
use paired defined events, reporting omitted events and NA coverage.

Do not treat claims, packets, records or repetitions as independent observations.
Intervals are conditional on the evaluated Sherlock events/scenarios, not uncertainty
over real-world OT deployments. The final event-to-scenario map remains a custodian
decision before result inspection. No confidence intervals or research scores were
computed here; only synthetic conformance checks exercise the implementation.

Configuration: `configs/investigation-dev-v1/statistics.json`.

## 8. Evaluation custody/isolation manifest

`configs/investigation-dev-v1/evaluation_custody.json` records all 32 evaluation IDs,
the frozen split hash, proposed private gold location, reviewer/custodian/developer/
generation roles, excluded paths, hash/version process, and access-log procedure.
No evaluation gold directory or files were created or inspected.

Implemented development access guard: verify the split hash; reject non-development
IDs before event access; allow only fixed N/EN production bundle/receipt paths; reject
symlink escapes; verify audited source hashes; log reads and denials with a hash chain.
Generation has no gold-path argument or evaluation execution switch. Scoring can read
the four sealed pilot contracts and refuses to invent gold for other development events.

This is an application-level guard, not a claim that arbitrary shell access is blocked.
A named custodian/reviewer, private directory/account ACLs, separately anchored OS/access
logs, scenario manifest and private gold commitment must be provisioned and verified
before freeze. No post-freeze evaluation observation may tune prompts, retrieval,
serialization, verifier, matching, metrics, tolerances or ontology. Such changes require
a new exploratory protocol version.

## 9. Development implementation and test results

**102 tests pass: 68 new development/integration tests plus 34 historical regression
tests. Zero failures or errors.** Results: `results/investigation-development-v1/conformance-final/`.
Tests use synthetic provider responses and development evidence only.

Implemented modules cover raw-support-first numeric projection, typed/native B0 matching
sidecars, finite verifier and approved episode-scope qualification, exact B3 replay,
generation delivery/retry/logging, create-once run manifests, fixed-gold denominator
binding, all six required metric families and companions, event aggregation/bootstrap,
token audit and development access controls.

Metric computation requires completed hash-bound human review ledgers for the entire
output. Support, free-text overclaims, relevance, question minimums, citation roles
and disposition-oracle judgments are not supplied by B4 itself. Pending judgments
block scoring. Aliases count once; conflicting variants cannot collapse; all-withhold
precision/citation rates are NA; fixed positive/Q denominators remain fixed. Verifier
accuracy includes retained content/reason, confusion counts, class denominators and
supported-claim false-withhold rate. Raw B3 exposure and B4 publication require separate
reviewed layers. No human system-review judgments were fabricated in this task.

The deterministic verifier supports finite canonical observable statements and limited
explicit policy insufficiencies. It does not certify arbitrary natural language or
invent positive Q6 relevance rules. Non-checkable text/Q6 claims are withheld for lack
of deterministic support; independent human review can reveal false withholds and
coverage loss. This is an explicit coverage limitation, not a claim of semantic truth.

Development CLI: `scripts/run_investigation_development.py` supports planning, a named
generation cell, stored B3 replay, reviewed scoring and stratified aggregation. The
model/budget approval gate prevents live calls in this candidate. Test entry point:
`scripts/test_investigation_development.py --report-dir <new directory>`.

## 10. Exact remaining decisions before freeze

1. Approve the exact model, account access and cost authorization. Approve the common
   evidence-token cap, output/input-text limits, prompt versions and exact retry policy.
2. Resolve an existing **representation compatibility gap**, not the now-approved
   reported/electrical specialization: four signed pilot facts use the already-defined
   observation_channel_maps_to_asset relation with a single E observation. B0/fact-key
   policy can represent it; v2 typed asset schema cannot. B0 sidecars preserve it.
   Do not change gold, silently add a relation enum, alias it to reported_value, or
   compensate recall. The concrete proposed schema-role constraints and exact files
   needing a versioned repair are in `configs/investigation-dev-v1/mapping_representation.pending.json`.
   Recommend authorizing representation of that existing relation, then versioning
   claim/verification schemas, validator and affected prompts and rerunning conformance.
3. Designate evaluation reviewer/custodian and provision private storage, permissions,
   logs, scenario-stratum mapping and gold version/commitment without developer tuning
   access. No claim that these operational controls already exist.
4. Review finite-verifier coverage and the completed development implementation.
   After the preceding approvals/compatibility work, validate live provider delivery
   on development only if authorized, retain all repetitions, and bind final artifacts.
5. Give explicit protocol freeze approval. Semantic/numeric/Q5/Q6/methodology/baseline
   decisions already approved by the present instruction are not reopened.

## 11. Updated freeze inventory and hashes

`configs/investigation_protocol.v1.freeze_inventory.r3.json` enumerates exact existing
paths/hashes, preserves historical gold/r1/r2 bindings and adds the current candidate,
prompts, implementation, dependency pins, configuration and verification artifacts.
`results/investigation-development-v1/delivery_manifest.json` binds the delivered
package; its sidecar seals its hash. Pending private gold, scenario and compatibility
artifacts are explicitly absent, not falsely described as immutable.

The pilot-gold manifest remains
`660ca033cd1c6a5bb9de98bb75c6a7ece5f28980716b9181152187e72c557d4a`.
Neither the inventory nor delivery manifest freezes Investigation Protocol v1.
