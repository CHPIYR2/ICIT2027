# r6 24,576 Development Validation — Author Review

**PASS_DEVELOPMENT_CAP_ONLY_NOT_FREEZE**. Scope: development capacity, conformance, isolation, binding and exact replay only. No final research performance scores; protocol NOT FROZEN.

## A. Preflight integrity

PASS. Approved r6 inventory cc0b0f9a03578aa1cecaf45f742bd29284a0cceccb510a4bd73b21d53e86f84e verified; all 64 exact requests and 8192→24576 equivalence records verified. Model gpt-4.1-2025-04-14, Responses, temperature 0, no seed, original repetitions and scientific files unchanged. Evidence input ceiling 16,384 remains separate from output cap 24,576. Development IDs/bundles are guarded; no evaluation path or custody provisioning. Execution adapter was separately tested and bound before calls.

## B. Request-size/rate preflight

Local prompt+evidence+compiled-schema estimates over 64 positions: {'n': 64, 'minimum': 24251, 'median': 26789.0, 'p90': 28740.0, 'p95': 28779.0, 'maximum': 28876}. No estimate exceeded 30,000. Applicable rate-demand interpretation is max(configured maximum output allowance, estimated request demand), not their sum. Provider framing/estimator is not claimed exact. Historical token limit 30,000 was the author-approved starting feasibility evidence; live headers control subsequent waits/blockers. Model capability, TPM, monthly/account quota and actual billable usage remain distinct.

## C. Executed logical positions and attempts

64/64 positions attempted; 67 transport attempts. Execution status: ALL_64_POSITIONS_FINISHED. No r5 output reused as r6. Unfinished/checkpoint-review records: [].

## D. Per-cell delivery and capacity

| Cell | Planned | Attempted | Completed provider deliveries | Cap truncations | Other incomplete | Strict schema passes | Strict schema failures | View/reference violations | Context mismatches |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| G0 | 19 | 19 | 19 | 0 | 0 | 19 | 0 | 0 | 0 |
| G1-E | 12 | 12 | 12 | 0 | 0 | 12 | 0 | 0 | 0 |
| G1-N | 12 | 12 | 12 | 0 | 0 | 12 | 0 | 0 | 0 |
| G1-EN | 21 | 21 | 21 | 0 | 0 | 21 | 0 | 0 | 0 |

Completed provider deliveries count provider responses, including retries if any; schema checks count finalized recoverable structured outputs. Incomplete/unrecoverable outputs are not automatically schema passes or schema failures; separate schema_not_assessed and transport categories remain in JSON.

| Cell | Attempts | Transport/rate failure attempts | Transport-exhausted positions | Retries | Not attempted |
|---|---:|---:|---:|---:|---:|
| G0 | 19 | 0 | 0 | 0 | 0 |
| G1-E | 12 | 0 | 0 | 0 | 0 |
| G1-N | 15 | 3 | 0 | 3 | 0 |
| G1-EN | 21 | 0 | 0 | 0 | 0 |

Retry reasons by cell: {'G1-E': {}, 'G1-EN': {}, 'G1-N': {'ConnectionResetError': 1, 'TimeoutError': 2}, 'G0': {}}.

Output-token statistics for delivered completed/incomplete provider responses with usage; linear interpolation index=(n−1)q, not research performance:

| Cell | n | Min | Median | p90 | p95 | Max |
|---|---:|---:|---:|---:|---:|---:|
| G0 | 19 | 2314 | 4626 | 6324.6 | 6439.099999999999 | 6764 |
| G1-E | 12 | 2205 | 3077.0 | 3363.2 | 3713.2499999999995 | 4123 |
| G1-N | 12 | 2356 | 3071.5 | 5699.700000000001 | 5975.0 | 6019 |
| G1-EN | 21 | 2042 | 5533 | 8217.0 | 8256.0 | 8332 |

## E. 24,576 acceptance

PASS_DEVELOPMENT_CAP_ONLY_NOT_FREEZE. Truncated positions: []. Conformance-invalid positions: []. Missing/no-delivery positions remain explicit in validation_report.json. A first cap truncation stops new positions without retry or limit increase. A rate-feasibility/implementation blocker is not mislabeled as output-cap failure. No automatic freeze or guarantee of zero final-evaluation truncation.

## F. G1-E / G1-N isolation

| Cell | Attempted inputs passing unchanged isolation/budget/binding checks | All output schema/context/reference checks passed |
|---|---:|---:|
| G1-E | 12 | 12 |
| G1-N | 12 | 12 |

Only exact view and necessary metadata were provided; references/entities checked against each actual bundle. No hidden N in E or hidden E/process values in N. These are existing structural conformance gates, not a human factual/security oracle or new semantic tuning.

## G. G1-EN / V1-EN replay

Eligible completed G1-EN: 21; replayed: 21; unavailable: 0; not reached: 0. Exact identity passes/failures: 21/0. Verifier model calls: 0. Raw G1-EN and published/verifier artifacts are preserved separately. No V1-E/V1-N. No verifier accuracy claim.

## H. Rate-limit and transport events

HTTP status counts: {'200': 64, 'None': 3}. Rate failure classes: {}. Retries: 3; UNKNOWN-delivery attempts: 3. Minimum request-start spacing: 60.00003900000593 seconds. Global single flight, no batching. Recorded Retry-After/reset deadlines audited against subsequent starts. Full headers, IDs, statuses and timestamps retained per attempt. Temporary rate exhaustion is distinct from a single request exceeding the rate allowance and from billing/quota failure.

The inherited pure policy's live_authorized=false field does not itself grant execution authority; this run's authority is the separately preserved author_approval.txt and successful preflight. Scientific candidate flags remain unchanged.

## I. Actual usage and calculable cost

- Known input tokens: 1,339,618
- Known cached input tokens (included in input): 652,928
- Known uncached input tokens: 686,690
- Known output tokens: 275,461
- Known total tokens: 1,615,079
- Attempts without provider usage: 3; partially missing usage responses: 0.
- Calculable subtotal: **USD 3.903532** across 64 priced responses.

Actual usage, documented GPT-4.1 rates/service tier and the approved formula are retained in usage_and_cost.json. Configured 24,576 is not billed output. Unknown usage/cost stays unknown; subtotal is not necessarily the final provider invoice. No fixed total bill was assumed.

## J. Pre/post local tests

Pre-execution: 305 PASS. Post-execution: 305 PASS. Network disabled during tests; synthetic fixtures only; historical result roots redirected to temporary directories. No output-driven scientific/test tuning during execution.

## K. r4/r5/r6/gold preservation

{'status': 'PASS', 'r6_inventory_files': 3307, 'historical_protected_files': 3216, 'all64_request_identities': True, 'model_calls': 0}. All preflight-bound files and sealed pilot-gold snapshots remained byte-identical. Historical 4096/8192 runs and forensic inputs preserved. No aliases, facts, guardrails, reviewer decisions, prompts, schemas, retrieval, verifier, matching, metrics or tolerance changes. No evaluation evidence/gold/truth/ledgers/results accessed.

## L. Post-validation manifest/hash

New namespace: results/investigation-r6-validation/. post_validation_manifest.json and .sha256 bind all new execution/response/replay/accounting/report/test artifacts and adapter code; the r6 pre-run candidate inventory is not overwritten. Hash is provided in the sidecar and final author response.

## M. Deviations

[]. Any unfinished records listed above remain subject to author/checkpoint review, not automatic rerun. Early stopping under a hard-stop rule is compliance, not result selection.

## N. Remaining freeze blockers

Author review of this capacity/conformance outcome, any failed/pending position or execution blocker, separate custody/gold commitment arrangements and explicit final protocol freeze remain required. A successful development outcome alone authorizes neither evaluation nor freeze. Current protocol remains NOT FROZEN.

## O. Exact recommended next author action

Review the acceptance status and the per-position preserved failure/conformance records. If capacity or rate/implementation feasibility failed, decide a separately authorized next development action; no automatic cap increase or resumption. If all development gates passed, explicitly accept this development configuration, then address remaining custody and final freeze decisions under separate authorization. STOP for author review. No evaluation or custody action has been started.
