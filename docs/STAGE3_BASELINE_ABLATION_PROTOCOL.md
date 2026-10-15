# Stage 3 Baseline & Ablation Experimental Protocol (`STAGE3_BASELINE_ABLATION_PROTOCOL.md`)

- **Frozen Engine Commit (`git_commit`)**: `2981fb062b127218a34f23f2ff0292e4ca8cfea7`
- **Reconstruction Code Hash (`code_sha256`)**: `d43d9867ce847df169e13345e4c3461cd99fd5167292a85cedaaa553d93e5bb3`
- **Evidence Layer Code Hash (`evidence_code_sha256`)**: `032c6977ac0507e9c442b37e4e78455d0ab6d1a21b1efe751a0ccf37242a3b85`
- **Stage 3 Implementation Package**: `experiments/stage3/` (strictly isolated from `src/mirage_ot/etgi/`)

---

## 1. Research Questions & Experimental Scope

Stage 3 evaluates MIRAGE-OT across all **103 Sherlock v3 `test` windows** (`28` `01-Basic`, `39` `02-Semiurban`, `36` `03-Rural`) to answer five specific methodological questions:
1. **RQ1 (Temporal Proximity vs. Evidentiary Gating)**: Why is temporal proximity alone (`B1_temporal_only`) insufficient to establish incident relations in OT telemetry?
2. **RQ2 (Protocol Transactions vs. Behavioral Reconstruction)**: Why is pure IEC-104 control transaction reconstruction (`B2_protocol_only`) insufficient for complete post-alert OT incident investigation?
3. **RQ3 (Behavioral Consistency Gate Impact)**: Which specific `unsupported_promotion` edges and `evidence_constraint_violation` categories are blocked by the Behavioral Consistency Gate (`A1_without_behavioral_consistency_gate`)?
4. **RQ4 (Provenance Deduplication Impact)**: How does Provenance Deduplication (`A2_without_provenance_deduplication`) affect independent source container counts and prevent multi-vantage mirror, multi-IOA ASDU, and IPAL transcription inflation?
5. **RQ5 (Incident Synthesis Contribution)**: What traceable incident organization information (RTU ASDU bundles, cross-RTU element bridges, candidate scenario phases, and competing explanations with missing disambiguators) does Four-Layer Incident Synthesis (`A3_without_incident_synthesis`) add beyond local storylines?

---

## 2. Fairness & Non-Degradation Principles for Baselines and Ablations

1. **Identical Evidence & Window Boundaries**: Every baseline and ablation operates on the exact same indexed SQLite evidence (`evidence.sqlite`), `evidence_id`s, and window bounds `[start, end)` as full MIRAGE-OT.
2. **No Straw-Man Baselines**:
   - **Baseline B1 (`B1_temporal_only`)** is given the **exact same vantage-deduplicated event anchors and protocol events**, chronological ordering, `15.0 s` time horizon (`HORIZON_SECONDS = 15.0`), and per-event outgoing link cap (`MAX_LINKS_PER_EVENT = 6`) as MIRAGE-OT. Its relations are labeled `candidate_temporal_relation` (never falsely accused of claiming physical causation).
   - **Baseline B2 (`B2_protocol_only`)** retains the **full reliability-hardened Phase 1 transaction engine** (`COT=6/7/10`, `P/N` bit check, TCP sequence retransmission deduplication, and pre/post command consistency gate). When a window contains `0` IEC-104 control commands, B2 is recorded as `NOT_APPLICABLE_NO_CONTROL_COMMANDS` rather than penalized as a software error or false negative.
3. **Non-Circular Evaluation of Unsupported Promotions (`E2`)**:
   - Candidate relations in B1 and ungated promotions in A1 are audited against **five fixed, public telemetry criteria** computed directly from the raw observations:
     1. `cross_device_without_protocol_or_session_link`: endpoints have distinct `device_stem`s and no shared control session.
     2. `same_asdu_co_report_chained_as_sequence`: endpoints share the exact same `asdu_key` (simultaneous multi-IOA payload packing, not a sequential transition).
     3. `endpoint_quality_or_test_bit_conflict`: at least one endpoint has `quality_invalid=True`, non-clear `quality_flags` (`ov, bl, sb, nt`), unknown quality bits, `cot_test=True`, or `cross_vantage_payload_conflict`.
     4. `endpoint_transient_not_sustained`: at least one endpoint fails post-sample persistence ($< 2$ post samples or $< 80\%$ consistent samples).
     5. `same_device_direction_or_change_type_conflict`: same-device endpoints in separate ASDUs have non-complementary sides (`from` vs `from`), mismatched `step_kinds` (`to_zero` vs `level_shift`), or opposing magnitude change directions.

---

## 3. Four-Category Evaluation Framework (E1–E4)

| Category | Metrics Recorded (`Total, Mean, Median, P95, Max` + Paired Bootstrap 95% CI) | Epistemic Interpretation |
| --- | --- | --- |
| **E1 — Evidence Coverage** | Retained control transactions, verified transitions, verified anchors (by type), quarantined unverified anchors, supported multi-node storylines, verified single-anchor storylines, cross-RTU bridges. | Measures observable telemetry coverage and corroborated local relations (not external accuracy). |
| **E2 — Unsupported Relation Promotion** | B1 conflicting/unsupported temporal candidates; A1 `unsupported_promotion` counts broken down by quality/test-bit, persistence, missing prior baseline, change-type mismatch, and magnitude/direction conflict; A2 `falsely_counted_independent_source_count` and `source_inflation_factor`. | Quantifies constraint violations prevented by MIRAGE-OT's gates and provenance deduplication. |
| **E3 — Incident Structure & Traceability** | Deduplicated source containers (`iec104_asdu`, `tcp_link`, `arp`, `composite_event`), RTU ASDU bundles, cross-RTU bridges, multi-bundle bridged components, candidate phases, competing explanations, and 100% `evidence_id` citation verification. | Distinguishes structural traceability from external ground-truth correctness. |
| **E4 — Computational Cost** | Shared indexing time (`indexing_s`) and SQLite size (`sqlite_mib`) reported separately from reconstruction/synthesis runtime (`full_pipeline_reconstruction_and_synthesis_s`), standalone synthesis time, and per-method evaluation time. | Evaluates practical post-alert runtime and storage overhead. |

---

## 4. Two-Stage Execution Plan (`Stage 3A` Pilot $\to$ `Stage 3B` Full 103 Windows)

- **Stage 3A (`--mode stage3a`)**: Deterministic 12-window stratified pilot selecting the first window of each observation stratum (`S1_control_command`, `S2_spontaneous_state_and_measurement_drop`, `S3_arp_or_iec104_link_disruption`, `S4_periodic_measurement_only`) in each of the three scenarios (`4 Basic + 4 Semiurban + 4 Rural = 12 windows`), plus 3 synthetic known-answer counterexamples (`S-KA1`, `S-KA2`, `S-KA3`).
  - *Stage 3A Pilot Design Refinement Recorded Prior to Stage 3B*: During Stage 3A pilot testing on `02-Semiurban` `ev_c77d85a14214995d2a2e`, we observed that applying `MAX_LINKS_PER_EVENT = 6` across all subsequent events in `B1_temporal_only` caused same-ASDU co-reported neighbors (`A009..A015`) to consume all 6 slots before reaching the true same-device counterpart (`A016` on `line.44`). To ensure B1 is not artificially disadvantaged relative to MIRAGE-OT's `add_behavioral_edges()`, B1 applies `MAX_LINKS_PER_EVENT = 6` only to cross-device candidates while preserving all same-device and same-ASDU pairs within the `15.0 s` horizon (and also reports the unbounded 15s pair counts).
- **Stage 3B (`--mode stage3b`)**: Full execution across all **103 Sherlock v3 `test` windows** (`28 Basic + 39 Semiurban + 36 Rural`) after Stage 3A passes all unit and protocol checks.
