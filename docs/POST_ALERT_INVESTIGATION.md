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

3. **The completion token counts repeat across windows because the outputs are templated.** For example, B1 always emits four `observation_claim` objects with four-character fact ids, so it is 178 tokens each time. The prompts differ by window, as the prompt token counts show. The model tends to pick the first ids it sees (`TL001`, `TL002`, `TL003`).

## T3 audit fixes and atomic rerun (2026-10-15)

The frozen-run audit found that an IEC-104 frame carrying several information objects was grouped as one measurement (`TL013`/`TL015` on ev12 mixed different CA/IOA values). The T2 frozen directory is kept untouched. Every result in it that involves IEC-104 values is superseded by the rerun below.

Code changes (commit `a314a26`):

1. **IEC-104 atomicity (`select.py`, `timeline.py`, `relations.py`).** IEC-104 rows are grouped per `(class, entity, CA/IOA)`. The parent frame stays in lineage as a shared container. Samples are counted once per frame (`sample_basis = distinct_source_frames`). `_merge_same_frame` only merges the same point seen at several vantages. Points from one frame get an observed `same_frame` record link and are excluded from `temporal_cooccurrence` and `supported_inference`.
2. **Complete lineage export (`pipeline.export_lineage_bundle`).** `db.get` caps at 100 ids, which is why the T2 bundle had 100 rows for 257/144/130 lineage ids. Export now fetches in chunks, follows parents, and records `requested_count`, `expected_with_parents`, `exported_count`, `missing_ids`, and per-row checks (entity, CA/IOA, and time inside the fact span).
3. **Scores (`select.py`).** The score is `min(log1p(z), 10)`, comparable only within one role. `z` is the robust z-score (1.4826·MAD) against the background. A flat background, a sparse background, and a missing background each use 1% of the level as the scale and are labeled (`background_flat_relative_1pct`, `background_sparse_relative_1pct`, `within_window_range_relative_1pct`). The `1e-3` MAD fallback and the ×2 control weight are gone. TCP rates use distinct frames. `background_status` and the observed background span are recorded.
4. **Flow counts (`timeline.py`).** `packet_count` (sum over vantages), `packet_count_by_vantage`, and `distinct_frame_count` are separate. TCP flows no longer pass through `_merge_same_frame`, which had been dropping the second vantage's count.
5. **Edge provenance (`relations.py`, `verify.py`).** Every edge carries `source_fact_id` and `target_fact_id`. `_edge_allowed_ids` allows only the edge's own ids and the lineage of those two facts, not every fact on the same entity. `expose_relations` checks both endpoints by fact id.
6. **Time and attribution (`verify.py`).** Each claim record has `time_tolerance_seconds = 1.0` and `time_match` (`inherited_from_anchor`, `exact_anchor`, `tolerance_aligned`, `outside_tolerance`, `row_tolerance_only`, `no_time_supplied`). `model_selected_fact_ids`, `model_selected_edge_ids`, and `model_supplied_evidence_ids` are kept apart from `system_resolved_evidence_ids`.
7. **Five-stage coverage (`pipeline.stage_coverage`).** `coverage.json → stages` reports available, selected, exposed, chosen by model, and published, by modality and role, with edges by level.
8. **Background in the CLI (`evidence/index.py`).** `open_indexed` did not return `context_seconds` or `indexed_start`, so the `postalert` CLI path ran with a zero-length background. The T2 frozen runs were not affected (their script set the background directly). The fields are now returned.
9. **Runner (`runner.py`, `postalert-protocol` CLI).** Runs a protocol file into a new directory and refuses an existing one. Protocol: `configs/etgi/postalert_t3_atomic_protocol.json`.

### Rerun: `runs/etgi/postalert-t3-atomic-20261015`

One `code_sha256` for all 21 runs: `6044c9704773e786b05749504c3317fe21d9f32f678066c2c11c6b8c05a69484`, git commit `a314a26`, clean diff for `postalert/`. Model `qwen3.5:9b-q4_K_M`, temperature 0, seed 1, `num_ctx` 8192, no salvage.

Lineage export per window (`<case>/evidence_audit_bundle.json`):

| Window | Background | Requested ids | Exported (with parents) | `missing_ids` | Row check failures |
| --- | --- | ---: | ---: | ---: | ---: |
| supplied ev_0961 | observed, 14.66 s | 305 | 305 | 0 | 0 |
| preceding 15 s ev_0961 | clipped to 0 s by index start | 78 | 78 | 0 | 0 |
| supplied ev_12dcd56b | observed, 14.75 s | 144 | 144 | 0 | 0 |

Typed references, `num_predict = 512`:

| Window | Run | Claims | B4 verified / B0–B3 offline audit (pass/fail) | Published | Confirmed inferred | Reject reason | Model-chosen facts / edges |
| --- | --- | ---: | --- | ---: | ---: | --- | --- |
| supplied ev_0961 | B0 | 0 (abstain) | – | 0 | 0 | – | – |
| supplied ev_0961 | B1 | 2 | 1 / 1 | 0 | 0 | `missing_evidence_ids` (invented edge id `R_TL001-TL003`) | TL009 / – |
| supplied ev_0961 | B2 | 0 (abstain) | – | 0 | 0 | – | – |
| supplied ev_0961 | B3 | 2 | 1 / 1 | 0 | 0 | `observed_link_cannot_be_upgraded_to_inference` | TL009 / R0002 |
| supplied ev_0961 | B4 | 2 | **1 / 1** | **1** | **0** | `observed_link_cannot_be_upgraded_to_inference` | TL009 / R0002 |
| preceding ev_0961 | B0 | 0 (abstain) | – | 0 | 0 | – | – |
| preceding ev_0961 | B1 | 3 | 3 / 0 | 0 | 0 | – | TL001, TL002, TL003 / – |
| preceding ev_0961 | B2 | 3 | 3 / 0 | 0 | 0 | – | TL001, TL002, TL016 / – |
| preceding ev_0961 | B3 | 2 | 1 / 1 | 0 | 0 | `observed_link_cannot_be_upgraded_to_inference` | TL001 / R0001 |
| preceding ev_0961 | B4 | 2 | **1 / 1** | **1** | **0** | `observed_link_cannot_be_upgraded_to_inference` | TL001 / R0001 |
| supplied ev_12dcd56b | B0 | 0 (abstain) | – | 0 | 0 | – | – |
| supplied ev_12dcd56b | B1 | 3 | 3 / 0 | 0 | 0 | – | TL001, TL002, TL009 / – |
| supplied ev_12dcd56b | B2 | 0 (abstain) | – | 0 | 0 | – | – |
| supplied ev_12dcd56b | B3 | 2 | 1 / 1 | 0 | 0 | `observed_link_cannot_be_upgraded_to_inference` | TL001 / R0001 |
| supplied ev_12dcd56b | B4 | 2 | **1 / 1** | **1** | **0** | `observed_link_cannot_be_upgraded_to_inference` | TL001 / R0001 |

`free_form` at 512 and 1536 tokens ends with `done_reason = length` and no parsable claim in all three windows, as in T2.

Five-stage coverage for B4 typed references:

| Window | Available rows (net / elec) | Selected facts (net / elec) | Exposed facts (net / elec) | Chosen facts (net / elec) | Published facts (net / elec) |
| --- | --- | --- | --- | --- | --- |
| supplied ev_0961 | 4642 / 1759 | 12 / 8 | 6 / 4 | 3 / 0 | 1 / 0 |
| preceding ev_0961 | 799 / 335 | 16 / 8 | 6 / 4 | 2 / 0 | 1 / 0 |
| supplied ev_12dcd56b | 1805 / 720 | 16 / 8 | 6 / 4 | 2 / 0 | 1 / 0 |

"Chosen facts" counts the model's own fact ids plus the two endpoint facts of the edge it named. IEC-104 rows count as network, because they are network-reported.

### Findings from the atomic rerun

1. **B3 and B4 receive the same prompt and return the same raw output in every window.** Their difference is verification and publication only. This is a verification ablation, not a comparison of reasoning strategies.
2. **The only edge Qwen names is a recorded TCP `communication` link, always relabeled `supported_inference`.** The verifier rejects it in all three windows. No window has a confirmed inferred relation. Recorded links are not counted as inferred-edge hits.
3. **The model never chooses an electrical fact.** Four electrical facts are exposed per window, and the chosen and published sets are network-only. On ev_0961 the published fact is now the IEC-104 control command on `switch.23:closed` (TL009); after atomicity, that command is its own fact instead of being grouped with other objects from its frame.
4. **The preceding window has no usable background.** The index starts exactly at its start, so the 15 s background is clipped to zero and all of its scores use the within-window or no-background basis. This is recorded in `window_policy.json`.
5. **Known labeling gap.** An invented edge id (`R_TL001-TL003` in B1 on ev_0961) is rejected as `missing_evidence_ids` because the evidence check runs before the edge lookup. The claim is correctly rejected but the reason should read `unknown_edge_id`. This only affects the offline audit of an unverified baseline. It is left unchanged so the rerun matches its recorded code hash, and will be fixed in the next code round.
6. **IEC-104 control commands have no numeric value, so their score is 0.** They reach the timeline only through the fixed control quota. The score is not an importance gold, and the T3 study compares it against random and model choices on an independent gold (`docs/T3_GOLD_AND_STUDY_DESIGN.md`).

Three windows from two development events are too few to claim any method is better. These are development diagnostics.

## Regression tests

`.venv/bin/python -m pytest -q tests/test_postalert.py tests/test_etgi.py` passes **57** offline tests (`29` in `tests/test_postalert.py`, `28` in `tests/test_etgi.py`). The eight added in T3:

- `test_iec104_points_in_one_frame_are_separate_facts_with_shared_lineage`: two CA/IOA with different units in each of two frames at two vantages stay separate facts, values are not mixed, samples count once per frame, lineage is shared, and the pair gets only a `same_frame` record link.
- `test_measurement_from_a_sibling_point_in_the_same_frame_is_rejected`
- `test_same_flow_at_two_vantages_reports_distinct_frames`
- `test_lineage_bundle_exports_every_id_beyond_the_query_cap` (130 ids, `missing_ids == []`)
- `test_lineage_bundle_includes_parents_and_passes_row_checks`
- `test_edge_provenance_excludes_same_entity_at_another_time`
- `test_flat_or_missing_background_gives_bounded_labeled_scores`
- `test_claim_records_model_choices_separately_from_system_resolution`
