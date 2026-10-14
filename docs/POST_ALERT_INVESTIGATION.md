# Evidence-grounded post-alert investigation

The investigation starts from a supplied time window. It selects observations, builds one timeline with full lineage, records candidate relations, asks Qwen for structured claims, and publishes a claim only after the indexed rows agree. The earlier agent, memory, and subgoal runs stay in their original directories.

## T2 review fixes (2026-10-15)

The T2 audit (`ETGI_T2_REVIEW.zip`) identified two P0 verifier gaps and five P1 reporting/comparability issues in `runs/etgi/postalert-t2-paired-20261014` (kept untouched):

1. **P0 — Claim-level upgrade of observed record links (`verify.py`, `pipeline.py`)**:
   - Previously, `_check_relation()` accepted `claim_level="supported_inference"` when `edge.claim_level == "observed_fact"`, and `_report()` set `no_confirmed_inferred_relation=False` by reading the model's claimed level rather than the canonical edge origin.
   - Now, upgrading an `observed_fact` record link (`communication`, `same_device`, `shared_source`, `same_frame`) to `supported_inference` is rejected with `observed_link_cannot_be_upgraded_to_inference`. `confirmed_inferred_relations` and `no_confirmed_inferred_relation` in `report.json` are computed strictly from verified claims whose canonical edge has `canonical_origin == "inferred"` and `canonical_claim_level == "supported_inference"`.
2. **P0 — Strict canonical `fact_id` / `edge_id` primary-key binding (`verify.py`)**:
   - When `fact_id` (`timeline_id`) is supplied, any explicitly provided `entity`, `time`/`start_time`/`end_time`, `claim_level`, or `evidence_ids` must match that canonical timeline event and its full `lineage.json` set (`fact_id_entity_mismatch`, `fact_id_time_mismatch`, `fact_id_evidence_mismatch`, `fact_claim_level_mismatch`).
   - When `edge_id` is supplied, any explicitly provided `relation_type`, `source_entity`/`target_entity`, or `evidence_ids` must match that canonical edge and its endpoint provenance (`edge_relation_type_mismatch`, `edge_endpoint_mismatch`, `edge_evidence_not_in_edge_provenance`).
3. **P1 — Baseline report labeling, unique citation counts, absence bounds, and relation exposure (`pipeline.py`, `explain.py`, `evaluate.py`, `verify.py`)**:
   - `B0`–`B3` do not run the verifier for publication: their `published_claims` is empty, their raw claims are stored in `unverified_model_claims`, and `report.md` renders them under `Unverified raw model claims (baseline output, not checked by verifier):`. Offline audit numbers are reported as `offline_audit_verified_claims` / `offline_audit_rejected_claims`.
   - `coverage.json` separates `cited_unique_evidence_by_modality`, `cited_unique_facts_by_modality`, and `cited_mentions_by_modality`.
   - `absence_claim` requires the queried `[start_time, end_time]` to lie inside the indexed `[incident_start, incident_end]` window and requires the window to contain indexed observations (`absence_range_outside_indexed_incident_window`).
   - `expose_relations()` prioritizes candidate relations where **both** endpoint entities appear in the exposed Fact Cards (`both_endpoints`).
   - `gold_facts()` in `evaluate.py` is explicitly documented and prefixed (`sanity_*`) as a pipeline sanity probe, not an independent event-importance or edge-precision gold.

## Frozen-code paired comparison (`code_sha256 = 521a3958...`)

Saved under `runs/etgi/postalert-t2-frozen-20261015/comparison.json`, with all referenced database rows and parent packets exported to `runs/etgi/postalert-t2-frozen-20261015/evidence_audit_bundle.json` for external verification without the full SQLite file. Every run in this directory shares the exact same `code_sha256` (`521a395860ab969a11090c8c0313e1ab2c38f497e64ba7dac87b12167684a908`), model (`qwen3.5:9b-q4_K_M`), temperature (`0`), seed (`1`), and `num_ctx` (`8192`). `free_form` is tested at both `num_predict=512` and `num_predict=1536`.

| Case | Run ID | `num_predict` | Done reason | `partial_output` | Model claims | Verified (B4) / Offline-audited (B0–B3) | Rejected | Published verified | Confirmed inferred | Tokens |
| --- | --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| supplied ev_0961 | `B4_free_form_512` | 512 | length | True | 0 | 0 | 0 | 0 | 0 | 512 |
| supplied ev_0961 | `B4_free_form_1536` | 1536 | length | True | 0 | 0 | 0 | 0 | 0 | 1536 |
| supplied ev_0961 | `B0_typed_refs` | 512 | stop | False | 0 (abstain) | 0 | 0 | 0 | 0 | 17 |
| supplied ev_0961 | `B1_typed_refs` | 512 | stop | False | 4 (unverified) | 4 | 0 | 0 | 0 | 178 |
| supplied ev_0961 | `B2_typed_refs` | 512 | stop | False | 0 (abstain) | 0 | 0 | 0 | 0 | 27 |
| supplied ev_0961 | `B3_typed_refs` | 512 | stop | False | 2 (unverified) | 1 | 1 | 0 | 0 | 101 |
| supplied ev_0961 | `B4_typed_refs` | 512 | stop | False | 2 | **1** | **1** | **1** | **0** | 101 |
| preceding 15 s | `B4_free_form_512` | 512 | length | True | 0 | 0 | 0 | 0 | 0 | 512 |
| preceding 15 s | `B4_free_form_1536` | 1536 | length | True | 0 | 0 | 0 | 0 | 0 | 1536 |
| preceding 15 s | `B0_typed_refs` | 512 | stop | False | 0 (abstain) | 0 | 0 | 0 | 0 | 17 |
| preceding 15 s | `B1_typed_refs` | 512 | stop | False | 4 (unverified) | 4 | 0 | 0 | 0 | 178 |
| preceding 15 s | `B2_typed_refs` | 512 | stop | False | 0 (abstain) | 0 | 0 | 0 | 0 | 27 |
| preceding 15 s | `B3_typed_refs` | 512 | stop | False | 2 (unverified) | 1 | 1 | 0 | 0 | 101 |
| preceding 15 s | `B4_typed_refs` | 512 | stop | False | 2 | **1** | **1** | **1** | **0** | 101 |
| supplied ev_12dcd56b | `B4_free_form_512` | 512 | length | True | 0 | 0 | 0 | 0 | 0 | 512 |
| supplied ev_12dcd56b | `B4_free_form_1536` | 1536 | length | True | 0 | 0 | 0 | 0 | 0 | 1536 |
| supplied ev_12dcd56b | `B0_typed_refs` | 512 | stop | False | 0 (abstain) | 0 | 0 | 0 | 0 | 17 |
| supplied ev_12dcd56b | `B1_typed_refs` | 512 | stop | False | 4 (unverified) | 4 | 0 | 0 | 0 | 178 |
| supplied ev_12dcd56b | `B2_typed_refs` | 512 | stop | False | 0 (abstain) | 0 | 0 | 0 | 0 | 27 |
| supplied ev_12dcd56b | `B3_typed_refs` | 512 | stop | False | 2 (unverified) | 1 | 1 | 0 | 0 | 101 |
| supplied ev_12dcd56b | `B4_typed_refs` | 512 | stop | False | 2 | **1** | **1** | **1** | **0** | 101 |

### Findings from the frozen comparison

1. **Raising `num_predict` to 1536 does not rescue `free_form`**: In all three windows, `B4_free_form_1536` still hits `done_reason=length` at 1536 tokens (`partial_output=True`), whereas `typed_refs` finishes in 17–178 tokens with `done_reason=stop`.
2. **Claim-level calibration catches LLM over-claiming on record links**: In `B3_typed_refs` and `B4_typed_refs`, Qwen selects one valid observation fact (`TL001` or `TL016`, `observed_fact`), which passes verification and is published (`1` verified claim per window), and one valid record-link edge (`R0002`, `R0001`, or `R0005`) but labels its `claim_level` as `supported_inference`. In `B3`, that unverified upgrade remains in the raw baseline output; in `B4`, the verifier rejects the upgrade with `observed_link_cannot_be_upgraded_to_inference`, logs it to `rejected_claims.json`, and keeps `confirmed_inferred_relations = 0` (`no_confirmed_inferred_relation = True`).

## Regression tests

`PYTHONPATH=src python -m pytest -q tests/test_postalert.py tests/test_etgi.py` passes **49** offline tests (`21` in `tests/test_postalert.py` and `28` in `tests/test_etgi.py`), including the 4 new counterexample and semantic tests (`test_observed_edge_upgraded_to_supported_inference_is_rejected`, `test_canonical_fact_and_edge_binding_rejects_mismatched_fields`, `test_baseline_reports_do_not_label_raw_claims_as_verified`, and `test_absence_claim_rejects_range_outside_indexed_window`).
