# MIRAGE-OT: Automated Evidence-Grounded Incident Reconstruction and Explanation Engine

- **R1 Run directory (preserved)**: `runs/etgi/reconstruction-20261015/` (`code_sha256 = c884c2d4...`, commit `b0bbe66`)
- **R2 Reliability-Hardened Run directory (preserved)**: `runs/etgi/reconstruction-r2-20261015/`
- **R2 Frozen code SHA-256 (`postalert/*.py` + `reconstruction/*.py`)**: `f8a168270b3cc85e95aa0c3662fd11d4cffbba57406e5751049334c1ff6a8ee0` (Git commit `7203e32`)
- **R3 Run directory**: `runs/etgi/reconstruction-r3-20261015/`
- **R3 code SHA-256 (`postalert/*.py` + `reconstruction/*.py`)**: `ba06d033607dea894bd1fff18f9e19e13fc5eceee8bb77beaf2b81a1493d7ff3`
- **Offline test suite after R3**: **77 passed** (`13` in `tests/test_reconstruction.py`, `36` in `tests/test_postalert.py`, `28` in `tests/test_etgi.py`)

The compact R3 review is `docs/R3_RECONSTRUCTION_REVIEW.md`. Full `transactions.json`, `event_graph.json`, `storylines.json`, `run_manifest.json`, and `evidence_audit_bundle.json` stay in the run directory and are not committed.

---

## 1. Summary of P0 & P1 Reliability Fixes (`commit 7203e32`)

Following the independent code & evidence audit (`docs/MIRAGE_OT_RECONSTRUCTION_AUDIT_20261015.md`), four P0 and three P1 fixes were implemented without redesigning the architecture or relaxing any verification criteria:

1. **P0-1 — IEC-104 Device State Verification & Boolean Decoder Support (`iec104.py`, `index.py`, `transactions.py`)**:
   - Extended `iec104.py` (`_FIELDS` & `_parse_value`) to decode `tshark` boolean strings (`"True"` / `"False"`) for `iec60870_asdu.siq.spi`, `iec60870_asdu.sco.on`, `iec60870_asdu.nega` (P/N bit), `iec60870_asdu.test`, `iec60870_asdu.sq`, `iec60870_asdu.sco.se` / `qos.se` (Select/Execute), `siq.iv` / `qds.iv` (quality invalid), and `iec60870_104.tx` / `rx`.
   - In `_finalize_transaction()`, mere presence of a `COT=3` (`M_SP_NA_1`) message or an IPAL `new` row **never** sets `state_change_observed`. When the state report value is undecoded (`value_present=False`), status is downgraded to `state_report_observed_value_unknown`; when decoded but lacking a pre-command IEC-104 baseline proving $v_{\text{pre}} \neq v_{\text{post}}$, status is `state_report_observed_no_pre_baseline`.
2. **P0-2 — Independent Consistency Gate for `supported_inference` (`transactions.py`, `event_graph.py`)**:
   - Implemented `evaluate_command_effect_inference()`, invoked directly inside `build_temporal_event_graph()` on the actual pre-command, command, and post-command values/flags.
   - An edge is upgraded to `claim_level="supported_inference"` (`graph_consistency_gate_status="passed_noncausal_inference_gate"`) **only** when: (a) same RTU/CA and device stem, (b) command not rejected by NACK or missing `COT=7`, (c) valid pre-command baseline exists, (d) valid post-command value exists with valid quality, (e) `shifted_from_pre_baseline` holds ($|\Delta| > \max(1\%, 10^{-3})$), (f) shift direction approaches target, and (g) post value matches commanded target within tolerance.
   - When any condition fails (including the audit counterexamples: `post_command_value = 39999.0`, wrong shift direction, missing pre-baseline, or undecoded switch values), the edge is downgraded to `claim_level="unresolved"`, `verification_status="unresolved"`, `relation_type="command_to_device_state_candidate"` (`graph_consistency_gate_status="failed_gate_kept_unresolved"`).
3. **P0-3 — Explicit `COT=7` P/N Bit (Positive vs. Negative Confirmation) Semantics (`transactions.py`)**:
   - `cot_negative is False` $\to$ `command_acceptance_status = "accepted_by_rtu"`
   - `cot_negative is True` $\to$ `command_acceptance_status = "rejected_negative_confirmation"` (blocks downstream inference)
   - `cot_negative is None` (when evaluating pre-existing DBs that did not index `nega`) $\to$ `command_acceptance_status = "confirmation_observed_acceptance_unknown"` (never claims `accepted_by_rtu` when the P/N bit is absent).
4. **P0-4 — Contiguous Directed Path Invariant on Storyline Spines (`storyline.py`)**:
   - Every storyline spine now enforces `_assert_contiguous_spine_path()`: `len(spine_fact_ids) == len(confirmed_and_supported_steps) + 1` and `step[i].source_fact_id == spine_fact_ids[i]`, `step[i].target_fact_id == spine_fact_ids[i+1]`.
   - Pre-command baseline nodes (`EF015` on `sgen.6`, `EF003` on `sgen.10`) and their `pre_to_post_measurement_transition` edges (`R0014`, `R0002`) are stored separately in `context_observations` and `supporting_evidence_edges`.
5. **P1-5 — Cross-Vantage Payload Conflict Detection & Strict TCP Retransmission Rules (`transactions.py`)**:
   - If two mirror vantages (`n302`, `n318`) share `(5-tuple, tcp_seq, entity, ca_ioa, type_id, cot)` but differ in decoded value or flags, they are **never** merged; both are preserved and logged in `cross_vantage_conflicts` (`cross_vantage_payload_conflict`).
   - An unconfirmed `COT=6` is attached as `tcp_retransmission` **only** when `tcp_seq` (and `apci_tx` if present) matches the open command; a distinct `tcp_seq` starts a new transaction.
6. **P1-6 & P1-7 — Vantage-Invariant `canonical_source_id`, Stratified N-P Stream Types, and Endpoint Evidence Citations (`event_graph.py`, `storyline.py`, `report.py`)**:
   - `independent_source_container_count` now counts unique canonical sources (`3` on a 4-node `COT=6 -> COT=7 -> COT=3/POST -> IPAL` spine) rather than multiplying by mirror ports (`vantage_capture_count` is reported separately).
   - Every edge and report line explicitly prints `src_ev=[...]` and `dst_ev=[...]`.

---

## 2. All Downgraded or Corrected Transactions, Edges, and Storylines (R1 $\to$ R2)

| Event | Scope | R1 (`c884c2d4...`) | R2 (`f8a16827...`) | Reason for Downgrade / Correction |
| --- | --- | --- | --- | --- |
| `ev_0961` | `TX001` (`switch.23`), `TX002` (`switch.24`), `TX003` (`switch.25`) acceptance | `accepted_by_rtu` | **`confirmation_observed_acceptance_unknown`** | Existing DB rows lacked decoded `cot_negative` (P/N bit); cannot claim positive acceptance without P/N bit. |
| `ev_0961` | `TX001`, `TX002`, `TX003` device state status | `state_change_observed` | **`state_report_observed_value_unknown`** | `COT=3` (`switch.23/24/25:is_closed`) had `value=None` (`unparsed_value`) and no pre-command IEC-104 baseline. |
| `ev_0961` | Graph edges `EF001->EF003`, `EF005->EF007`, `EF009->EF011` (3 switch inference edges) | `command_to_device_state_transition` (`supported_inference` / `supported`) | **`command_to_device_state_candidate` (`unresolved` / `unresolved`)** | Failed consistency gate (`command_value_unknown, missing_pre_command_baseline, post_state_or_measurement_value_unknown`). Total `supported_inference` edges in `ev_0961` dropped from **4 $\to$ 1** (only `TX004` `sgen.6` remains `supported_inference`). |
| `ev_0961` | `SL004` (`sgen.6`) spine topology | Non-contiguous 5-node list `['EF015','EF013','EF014','EF016','EF018']` | **Contiguous 4-node spine `['EF013','EF014','EF016','EF018']` + `context_observations=['EF015']` + `supporting_evidence_edges=['R0014']`** | Enforced contiguous directed path invariant `edge[i].target == edge[i+1].source`. |
| `ev_0961` | `SL001`–`SL004` `independent_source_container_count` | `10` (inflated by dual mirror vantages + point keys) | **`3` on spine (`4` including supporting `EF015` on `SL004`), `vantage_captures=7` reported separately** | Canonical source IDs deduplicate mirror captures across `n302` and `n318`. |
| `ev_3e4d` | `TX001` (`switch.31`), `TX002` (`switch.30`), `TX003` (`switch.27`) acceptance | `accepted_by_rtu` | **`confirmation_observed_acceptance_unknown`** | Missing `cot_negative` P/N bit in pre-existing DB. |
| `ev_3e4d` | `TX001` (`switch.31`), `TX003` (`switch.27`) device state status | `state_change_observed` | **`state_report_observed_value_unknown`** | `COT=3` (`switch.31/27:is_closed`) had `value=None` and no pre-command baseline. |
| `ev_3e4d` | Graph edges `EF001->EF003`, `EF007->EF009` (2 switch inference edges) | `command_to_device_state_transition` (`supported_inference` / `supported`) | **`command_to_device_state_candidate` (`unresolved` / `unresolved`)** | Failed consistency gate. Total `supported_inference` edges in `ev_3e4d` dropped from **2 $\to$ 0**. |
| `ev_12dcd56b` | `TX001` (`sgen.10`) acceptance | `accepted_by_rtu` | **`confirmation_observed_acceptance_unknown`** | Missing `cot_negative` P/N bit in pre-existing DB (`device_state_change_status` remains `verified_measurement_transition` because `309980.938 -> 269971.625` matches target `270000.0`). |
| `ev_12dcd56b` | `SL001` (`sgen.10`) spine topology | Non-contiguous 5-node list `['EF003','EF001','EF002','EF004','EF006']` | **Contiguous 4-node spine `['EF001','EF002','EF004','EF006']` + `context_observations=['EF003']` + `supporting_evidence_edges=['R0002']`** | Enforced contiguous directed path invariant; `independent_source_container_count` corrected from `7` $\to$ `3` (`4` with `EF003`). |

---

## 3. R3 reliability fixes

R3 does not redesign the engine. It closes two review findings and three protocol gaps.

1. **P0-1 — One consistency gate.** `evaluate_command_effect_inference()` now requires decoded quality on both the pre-command and post-command measurements. `quality_invalid is True` fails as `pre_value_quality_invalid` or `post_value_quality_invalid`. `quality_invalid is None` fails as `pre_quality_unknown` or `post_quality_unknown` and is listed under `quality_uncertainty`. The event graph passes those same fields and, if the transaction gate already failed, cannot upgrade the edge.
2. **P0-2 — IPAL source binding.** An IPAL row shares an IEC-104 `canonical_source_id` only when `parent_evidence_id` hits that message's evidence or parent ids. Otherwise the row keeps `SRC-IPAL-...` with `source_binding=unconfirmed_temporal_correspondence` and `counts_as_independent_source=false`. Same point and nearby time produce `temporally_aligned_same_point_stream` only. `same_network_data_stream_ipal_derivation` is no longer taken from the last fact created.
3. **P1-1 — Select versus Execute.** A COT=7 reply or a retransmission is attached only when `select_execute` agrees. Same CA/IOA and the same control value with different Select/Execute stay two transactions.
4. **P1-2 — Multi-object ASDU.** Shared type id, COT, and CA are copied onto each IOA. Empty aggregator slots stay in place, so a missing middle value is not shifted onto the next IOA. A single value is not copied onto every IOA.
5. **P1-3 — No control command.** Existing beam search can spine same-device supported couplings. Cross-entity time proximity stays unresolved and is not promoted. A dedicated no-command algorithm is deferred (`no_control_command_policy`).

## 4. R2 to R3 on the three Basic windows

The indexed databases still have no decoded `quality_invalid`. R3 therefore does not keep the two R2 `supported_inference` edges. Lineage export is complete on all three windows (`missing_ids=[]`). Every storyline spine remains a contiguous directed path. IPAL rows are `unconfirmed_temporal_correspondence` and are not counted as independent sources. There is no `same_network_data_stream_ipal_derivation` edge, because these indexes do not store an IPAL parent id.

| Event | Scope | R2 | R3 | Reason |
| --- | --- | --- | --- | --- |
| `ev_0961` | `TX004` `sgen.6` | `verified_measurement_transition`, 1 `supported_inference` | `measurement_observed_transition_unverified`, 0 `supported_inference` | Pre/post values still move 40004.5312 → 20000.6875 toward 20000.0, but quality is not decoded (`pre_quality_unknown`, `post_quality_unknown`). |
| `ev_0961` | `SL004` | 4-node verified spine | 3-node spine: command, confirmation, IPAL setpoint update. `independent_source_container_count=2` | The unverified measurement edge is off the spine. The IPAL row is not an independent source. |
| `ev_0961` | `SL001`–`SL003` | 4 nodes, IPAL sharing the last protocol source | 3 nodes: command, confirmation, COT=3 report. `independent_source_container_count=3` | IPAL no longer inherits `facts[-1]`. |
| `ev_3e4d` | transactions | 0 `supported_inference`; switch.30 `no_state_change_observed` | unchanged claim levels | Quality was already not supporting an inference. IPAL derivation edges 2 → 0. |
| `ev_12dcd56b` | `TX001` `sgen.10` | `verified_measurement_transition`, 1 `supported_inference` | `measurement_observed_transition_unverified`, 0 `supported_inference` | 309980.938 → 269971.625 toward 270000.0 remains visible, but quality is unknown. |
| `ev_12dcd56b` | `SL001` | verified 4-node protocol spine, 3 independent sources | command, confirmation, two IPAL updates. `independent_source_container_count=2` | Unverified measurement edge leaves the spine. Both IPAL rows are non-independent. |

## 5. R4 IEC-104 evidence reindexing

R4 fixes the evidence layer, not the engine. Details and the field audit are in `docs/R4_EVIDENCE_REINDEX_REVIEW.md`.

1. **ASDU versus object fields.** `split_fields()` reads type id, COT (cause, P/N, T), SQ, NumIx, OA and CA once per ASDU. Value, SIQ/DIQ/QDS bits and S/E are read per information object. A count mismatch leaves the field unknown for that frame; it is not shifted or broadcast.
2. **Gate inputs.** `evaluate_command_effect_inference()` also requires NT/SB/BL/OV decoded and clear, T decoded and clear on command, confirmation, pre and post, and a decoded P/N. Transaction and event graph build these inputs with the same helpers (`measurement_gate_inputs`, `feedback_gate_inputs`).
3. **Consistency file.** Each run writes `quality_consistency.json`, comparing the transaction gate with the graph edge, graph node quality, storyline status and report summary. The report lists each transaction's gate inputs and failed conditions. The manifest adds `evidence_code_sha256`.
4. **Audit.** `etgi field-audit` traces each raw object through tshark, the parser and the database, and checks IPAL records for a packet reference.

## 6. R3 to R4 on two reindexed Basic windows

The old indexes lacked quality, T, P/N and S/E because parser `6a0c162` never requested those tshark fields. The raw packets contain them. In the two reindexed windows all values are clear (IV/NT/SB/BL/OV/T/P-N all 0; Execute only). IPAL state records hold no packet reference, so IPAL stays temporal correspondence.

| Event | Scope | R3 | R4 | Reason |
| --- | --- | --- | --- | --- |
| `ev_0961` | `TX004` `sgen.6` | `measurement_observed_transition_unverified` | `verified_measurement_transition`, 1 `supported_inference` | 40004.5312 → 20000.6875 toward 20000.0 with decoded good quality, T=0, P/N=0. |
| `ev_0961` | `TX001`–`TX003` switches | acceptance unknown, value unknown | accepted, values decoded, `state_report_observed_no_pre_baseline` | No IEC-104 value before the command. Still unresolved. |
| `ev_12dcd56b` | `TX001` `sgen.10` | `measurement_observed_transition_unverified` | `verified_measurement_transition`, 1 `supported_inference` | 309980.938 → 269971.625 toward 270000.0 with decoded good quality, T=0, P/N=0. |

## 7. Behavioral reconstruction round

Details: `docs/BEHAVIORAL_RECONSTRUCTION.md`.

1. **Quality inconsistency.** When `quality_consistency.json` reports `consistent=false`, the report status is
   `diagnostic_only_quality_inconsistent`, verified transitions are moved to `withheld_verified_device_transitions`,
   and the Markdown is titled "DIAGNOSTIC ONLY, NOT VERIFIED". Diagnostic artifacts are still written.
2. **IPAL correspondence.** Same point and time without lineage is `temporal_correspondence /
   temporally_aligned_same_point_stream` (`common_source_unconfirmed`), not `shared_source`. It is listed per
   storyline under `temporal_correspondences` and never forms a step. The P0 test's `sgen.6` spine is now 3 nodes
   and 2 steps instead of 4 and 3.
3. **No-command windows.** `discover_event_anchors()` finds state reports, measurement steps, link activity and ARP
   increases. Without a transaction they enter the graph and root behavioral storylines; cross-device links stay
   `cross_device_temporal_candidate` (unresolved). New artifacts: `event_anchors.json`,
   `behavioral_storylines.json`, `unresolved_branches.json`.

## 8. Behavioral reconstruction refinement & Incident Synthesis design

Details: `docs/BEHAVIORAL_RECONSTRUCTION.md` (Section 10) and `docs/INCIDENT_SYNTHESIS_DESIGN.md`.

1. **Supported transition vs. sequential observation (`behavior.py`).** `evaluate_behavioral_relation_consistency()`
   checks device stem, separate ASDUs, `0 <= dt <= 15 s`, overlapping `[pre_time, post_time]` transition intervals,
   endpoint verification (`verified_observation`), complementary endpoints (`from` vs `to` on a shared quantity or
   verified `COT=3` state transition paired with `to_zero`/`from_zero`), and matching change type, magnitude direction,
   and power flow sign. Pairs that pass become `corroborated_same_device_behavioral_transition` (`supported`);
   same-device pairs that fail become `same_entity_sequential_observation` (`unverified`, off-spine).
2. **Anchor reliability (`anchors.py`).** Pre/post quality descriptors, COT test bits, pre-sample cadence gap
   (`<= 30 s`), and post-sample persistence (`>= 2` post samples, `>= 80 %` consistent) classify each anchor as
   `verified_observation` or `unverified_observation`. Unverified observations are retained as
   `behavioral_unverified_observation` and excluded from supported spines.
3. **Separate quality and lineage consistency (`consistency.py`).** `quality_consistency.json` checks transaction and
   behavioral transition consistency; `lineage_consistency.json` records timeline and anchor evidence lineage checks
   separately.
4. **Refined Basic results (`runs/etgi/behavioral-r5-20261015/`).** In `ev_564bebaa`, 5 of the 8 chains remain
   supported (`line.0`, `line.1`, `line.3`, `line.4`, `line.12`) and 3 are downgraded to
   `same_entity_sequential_observation` (`line.2` early `A011 -> A023` due to `change_type_mismatch`; `line.2` late
   `A028 -> A029` and `line.14` late `A030 -> A031` due to failed persistence and direction/ratio mismatch). In
   `ev_4e913b`, `sgen.0` `A001 -> A002` is downgraded to `same_entity_sequential_observation` because `A001` lacks a
   prior state value in the window.

## 9. Incident Synthesis implementation (`synthesis.py`)

Details: `docs/INCIDENT_SYNTHESIS_DESIGN.md` (Section 5).

1. **Pre-synthesis hardening.** `_merge_iec_vantages()` refuses to merge same-vantage packets or conflicting cross-vantage
   payloads; `_obs_quality_fields()` requires all SIQ/DIQ/QDS quality bits to be present and boolean before setting
   `quality_good=True`; `apply_quality_consistency()` requires both `quality_consistency` and `lineage_consistency` to pass.
2. **Four-layer synthesis (`synthesis.py`).** `synthesize_incident_scenario()` builds Layer 1 (`local_storyline_partition`),
   Layer 2 (`rtu_asdu_bundles`, `verified_element_bridges`, `bridged_bundle_components`), Layer 3
   (`candidate_scenario_phases`), and Layer 4 (`source_dependency_ledger`, `competing_explanations`), exported to
   `incident_synthesis.json` and rendered in Section `2B` of `investigation_report.md`.
