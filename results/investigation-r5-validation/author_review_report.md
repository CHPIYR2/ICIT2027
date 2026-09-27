# r5 8192 Development Validation — Author Review

**FAIL_OUTPUT_CAP_STOP_AUTHOR_REVIEW**. Protocol NOT FROZEN; no final evaluation or custody provisioning.

## A. Preflight

All r5 inventory, manifest and protected r4/gold bindings passed. 64 exact requests verified; 40 stress requests differ from r4 only at output cap. Fixed model gpt-4.1-2025-04-14, temperature 0, no seed assumption, output 8192, input evidence safety ceiling 16384. Scientific candidate files unchanged; separate execution adapter bound before calls.

## B–C. Execution

Logical positions executed: 18/64; transport attempts: 18. Status: FAILED_8192_OUTPUT_CAP_STOP_AUTHOR_REVIEW.

| Cell | Planned | Executed | Delivered | Complete outputs | Schema valid | Cap truncations | Schema/context/visibility failures | Other non-complete failures | Not executed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| G1-E | 12 | 6 | 6 | 6 | 6 | 0 | 0 | 0 | 6 |
| G1-EN | 21 | 3 | 3 | 2 | 2 | 1 | 0 | 0 | 18 |
| G1-N | 12 | 6 | 6 | 6 | 6 | 0 | 0 | 0 | 6 |
| G0 | 19 | 3 | 3 | 3 | 3 | 0 | 0 | 0 | 16 |

Complete schema-valid delivery does not imply factual correctness. Full attempt status/headers/IDs/raw bytes retained in the run folders and JSON report.

## D. Capacity decision

FAIL_OUTPUT_CAP_STOP_AUTHOR_REVIEW. A cap truncation overrides completing the matrix. No limit increase, retry of truncated output, prompt shortening or evidence reduction is authorized. No-delivery remains separate/inconclusive. A development pass would not guarantee zero evaluation truncation and never automatically freezes 8192.

- `ev_363ad64e92cfa74fd5f6/G1-EN/rep-1`: provider `status=incomplete`, reason `max_output_tokens`; exact response and output preserved; no retry.

Run stopped at 2026-09-26T16:55:47.715385+00:00; 46 remaining positions were not scheduled.

## E. Smoke conformance

G1-E/G1-N delivered output schema/context/reference checks appear separately in the JSON report. All scheduled inputs were validated against exact view, necessary metadata, existing entry quotas/48,000-byte policy and 16,384 evidence safety ceiling. Unexecuted positions are not successes or failures. No factual scores were used to tune the protocol.

| Cell | Planned | Executed | Schema valid | Visible references, complete outputs | All output conformance checks | Input view/budget checks |
|---|---:|---:|---:|---:|---:|---:|---:|
| G1-E | 12 | 6 | 6 | 6 | 6 | 6 |
| G1-N | 12 | 6 | 6 | 6 | 6 | 6 |

## F. V1-EN replay

2 replayed; 1 unavailable; 18 not reached. Eligible replay input hashes matched exact corresponding stored G1-EN bytes; zero verifier model calls. Raw and published outputs retained separately.

## G. Transport

HTTP counts: {'200': 18}. Retry reasons: {}. Unknown-delivery attempts: 0. Minimum recorded request-start spacing: 60.00008699996397 seconds. Single in-flight request; Retry-After and later reset headers respected. [Official header reference](https://developers.openai.com/api/docs/guides/rate-limits#rate-limits-in-headers).

## H. API usage/cost

Known input: 377,686; cached input (subset): 184,704; output: 70,434; total: 448,120 tokens. Known calculable list-price subtotal **USD 1.041788**, using the approved documented pricing formula. 0 attempts without provider usage remain unknown, never assumed zero. This is not necessarily the provider invoice. Exact meters and pricing in usage_and_cost.json.

Provider input usage includes the full request; the separate 16,384-token safety ceiling applies to the serialized input evidence, not total provider-billed input. Cached input is already included in input tokens.

## I–J. Tests and preservation

Pre-execution tests: 259 PASS. Post-execution tests: 259 PASS. r5 candidate, protected r4/legacy and sealed gold hashes verified again after the run. Every preflight protected binding unchanged. No gold facts, aliases, guardrails or human decisions changed. No evaluation evidence/gold/results accessed.

## K. Artifacts

New result namespace: results/investigation-r5-validation/. post_validation_manifest.json and its SHA-256 sidecar bind all new run records, reports, tests and execution adapter files. Original r5 candidate/manifest are not overwritten.

## L. Deviations

[]. Early capacity stop, when triggered, is compliance with author instruction and not missing-data selection. All completed and unavailable records remain preserved.

## M. Remaining blockers

Capacity acceptance and any unresolved smoke conformance require author review. Custody ACL/account logging and gold commitments remain unprovisioned; no evaluation authorization. Final protocol freeze always needs explicit approval.

## N. Next author action

Review this validation outcome and its exact failure/conformance records. If the hard output-cap stop fired, decide a separately versioned development plan; do not resume unscheduled positions or increase limits automatically. If passed, review the evidence and remaining custody/freeze steps under separate authorization. STOP for author review.

Recommended action for this run: Do not accept or freeze the 8192 candidate. Review the preserved truncation and authorize a separately versioned offline development proposal before any further generation. The 46 unscheduled positions remain unexecuted; no automatic resume or token-limit increase.
