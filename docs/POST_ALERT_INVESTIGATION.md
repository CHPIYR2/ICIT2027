# Evidence-grounded post-alert investigation

The investigation starts from a supplied time window. It selects observations, builds one timeline with full lineage, records candidate relations, asks Qwen for structured claims, and publishes a claim only after the indexed rows agree. The earlier agent, memory, and subgoal runs stay in their original directories.

## Review fixes (2026-10-14)

The post-alert review identified five issues in `runs/etgi/postalert-bounded-20261014` (kept untouched):

1. **False negatives from an untyped `value` field**: `verify.py` now separates `observation_claim`, `measurement_claim`, `relation_claim`, and `absence_claim`. Packet existence (`observation_claim`) does not require a numeric measurement, accepts `{start, end}` interval times, and does not require a two-node graph edge.
2. **False positives from unverified free prose and set-intersection relation checks**: Free prose in `statement` is no longer published as a verified fact; published text (`rendered_text`) is rendered from the bound database rows. `measurement_claim` requires `entity`, `timestamp`, and numeric `value` (rejecting booleans where `float(True) == 1.0`) to match the **same** atomic row. `relation_claim` requires both endpoints to have matching evidence rows, checks the relation type, and rejects same-source IEC-104/IPAL pairs claimed as independent evidence.
3. **Multimodal exposure**: `expose_timeline()` stratifies the 10 exposed Fact Cards across available roles (`command`, `electrical_change`, `electrical_report`, `communication`, `response`) rather than slicing `timeline[:8]` by timestamp. Each run writes `coverage.json` with `available`, `selected`, `exposed`, and `cited` counts by modality and role.
4. **Timeline precision and artifact manifests**: TCP packet byte lengths are stored as `packet_bytes_min`/`packet_bytes_max` with `value=None` so frame sizes are not mistaken for electrical measurements. Multi-sample electrical groups record `value_first`, `value_last`, `value_min`, `value_max`, and `sample_count`. Flow scoring normalizes packet counts by window duration (`packets_per_second`) while keeping raw counts. Full evidence ID lists are written to `lineage.json` and match `evidence_id_count`. Each run writes `run_manifest.json` with `git_commit`, `code_sha256`, module hashes, config hash, and database fingerprint. Rejected claims are logged to `rejected_claims.json` and omitted from public `report.md`.
5. **Truncated outputs**: When `done_reason == "length"`, `partial_output=True` is recorded. Unless salvage is explicitly enabled for an offline diagnostic replay, truncated JSON is not treated as a completed structured response.

## T0 — Offline verifier replay on saved partial outputs (no Ollama call)

Saved under `runs/etgi/postalert-t0-replay-20261014/t0_replay.json`. Replaying the salvaged claims from `postalert-bounded-20261014` against the repaired verifier separates format false negatives from genuine model errors:

| Case | Saved salvaged claims | Old verifier | Repaired verifier | Reason |
| --- | ---: | ---: | ---: | --- |
| supplied ev_0961 | 2 | 0 verified | **2 verified** | Both TCP existence claims cited valid IDs on the flow; `value: true` is no longer treated as an electrical measurement mismatch. |
| preceding 15 s | 1 | 0 verified | 0 verified | Model prefixed `network:tcp_packet` onto the entity name (`entity_does_not_match_cited_rows`). |
| supplied ev_12dcd56b | 2 | 0 verified | 0 verified | Model claimed `storage.1:state_of_charge=100.0` while citing only TCP packet IDs (`entity_does_not_match_cited_rows`). |

## T1 — Multimodal Fact Card exposure

Across the three Basic windows, stratified Fact Card selection exposes both network and electrical observations whenever they exist in the window:

| Window | Available (`network` / `electrical`) | Selected (`network` / `electrical`) | Exposed Fact Cards (`network` / `electrical`) | Exposed roles |
| --- | --- | --- | --- | --- |
| supplied ev_0961 | 4642 / 1759 | 12 / 8 | 6 / 4 | 2 command, 4 electrical_change, 2 electrical_report, 2 communication |
| preceding 15 s | 799 / 335 | 16 / 8 | 6 / 4 | 4 electrical_change, 2 electrical_report, 4 communication |
| supplied ev_12dcd56b | 1805 / 720 | 14 / 9 | 6 / 4 | 1 command, 4 electrical_change, 2 electrical_report, 3 communication |

## T2 — Paired `free_form` vs `typed_refs` comparison (`allow_salvage=False`)

Saved under `runs/etgi/postalert-t2-paired-20261014/comparison.json`. Model `qwen3.5:9b-q4_K_M`, temperature 0, seed 1, `num_predict` 512, `num_ctx` 8192. In `typed_refs`, the schema is a `oneOf` union requiring `fact_id` (`TL...`) for observation/measurement claims or `edge_id` (`R...`) for relation claims; the verifier binds the database rows and renders the text.

| Case | Mode / Level | Done reason | `partial_output` | Model claims | Verified claims | Rejected claims | Published claims | Completion tokens |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| supplied ev_0961 | B4 `free_form` | length | True | 0 (2 salvaged, withheld) | 0 | 0 | 0 (minimum report) | 512 |
| supplied ev_0961 | B0 `typed_refs` | stop | False | 0 (abstain) | 0 | 0 | 0 | 27 |
| supplied ev_0961 | B1 `typed_refs` | stop | False | 4 | 4 | 0 | 4 | 178 |
| supplied ev_0961 | B2 `typed_refs` | stop | False | 0 (abstain) | 0 | 0 | 0 | 17 |
| supplied ev_0961 | B3 `typed_refs` | stop | False | 2 | 2 | 0 | 2 | 101 |
| supplied ev_0961 | B4 `typed_refs` | stop | False | 2 | **2** | 0 | **2** | 101 |
| preceding 15 s | B4 `free_form` | length | True | 0 (2 salvaged, withheld) | 0 | 0 | 0 (minimum report) | 512 |
| preceding 15 s | B0 `typed_refs` | stop | False | 0 (abstain) | 0 | 0 | 0 | 27 |
| preceding 15 s | B1 `typed_refs` | stop | False | 4 | 4 | 0 | 4 | 178 |
| preceding 15 s | B2 `typed_refs` | stop | False | 0 (abstain) | 0 | 0 | 0 | 27 |
| preceding 15 s | B3 `typed_refs` | stop | False | 2 | 2 | 0 | 2 | 108 |
| preceding 15 s | B4 `typed_refs` | stop | False | 2 | **2** | 0 | **2** | 108 |
| supplied ev_12dcd56b | B4 `free_form` | length | True | 0 (2 salvaged, withheld) | 0 | 0 | 0 (minimum report) | 512 |
| supplied ev_12dcd56b | B0 `typed_refs` | stop | False | 0 (abstain) | 0 | 0 | 0 | 27 |
| supplied ev_12dcd56b | B1 `typed_refs` | stop | False | 3 | 3 | 0 | 3 | 139 |
| supplied ev_12dcd56b | B2 `typed_refs` | stop | False | 0 (abstain) | 0 | 0 | 0 | 27 |
| supplied ev_12dcd56b | B3 `typed_refs` | stop | False | 2 | 2 | 0 | 2 | 101 |
| supplied ev_12dcd56b | B4 `typed_refs` | stop | False | 2 | **2** | 0 | **2** | 101 |

In all three windows, `free_form` B4 hits the 512-token cap while rewriting entity strings, timestamps, and prose (`partial_output=True`). With `typed_refs`, B4 finishes in 101–108 tokens with `done_reason=stop`, and all 6 proposed claims across the three windows pass verification (for example, `TL016` electrical update on `external_grid.0:active_power` and `R0005` `same_device` relation between `bus.0:active_power` and `bus.0:reactive_power` on `ev_12dcd56b`, plus bidirectional TCP `communication` relation `R0002` on `ev_0961`). None of the three windows produces a cross-modal `supported_inference` claim beyond record links, and causal status remains `not_established`.

## Regression tests

`tests/test_postalert.py` and `tests/test_etgi.py` pass 45 offline tests, including the 12 regression tests from the review (`test_packet_existence_does_not_require_numeric_measurement`, `test_true_is_not_equal_to_numeric_one`, `test_observed_single_packet_without_edge_can_pass`, `test_unsupported_statement_cannot_pass_with_only_valid_id`, `test_relation_requires_both_endpoint_refs_and_type`, `test_entity_timestamp_and_value_match_same_fact`, `test_time_interval_supported_with_typed_range`, `test_multimodal_input_exposes_available_electrical_changes`, `test_derived_iec104_and_ipal_not_independent_sources`, `test_partial_json_is_not_complete_response`, `test_code_version_and_run_artifact_consistency`, and `test_public_report_does_not_include_rejected_claim_text`).
