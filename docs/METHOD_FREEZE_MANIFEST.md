# MIRAGE-OT Method Freeze Manifest & Sherlock v3 Cross-Scenario Experiment Plan

- **Freeze Status**: `FROZEN_FOR_CROSS_SCENARIO_EVALUATION` (v1.0.0)
- **Machine-Readable Manifest**: `configs/etgi/method_freeze.v1.json`
- **Git Branch**: `mirage-ot`
- **Frozen Engine Commit (`git_commit`)**: `2981fb062b127218a34f23f2ff0292e4ca8cfea7`
- **Reconstruction Code Hash (`code_sha256`)**: `d43d9867ce847df169e13345e4c3461cd99fd5167292a85cedaaa553d93e5bb3`
- **Evidence Layer Code Hash (`evidence_code_sha256`)**: `032c6977ac0507e9c442b37e4e78455d0ab6d1a21b1efe751a0ccf37242a3b85`
- **Working-Tree Dirty Diff Hash (`git_dirty_diff_sha256`)**: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (empty diff)

---

## 1. Pre-Freeze Reliability Hardening & Re-Run Verification

Before freezing the reconstruction and synthesis pipeline, two final reliability checks were added and verified against both synthesis milestones (`runs/etgi/synthesis-method-freeze-20261015/reconstruction/` and `review_artifacts/synthesis-method-freeze-20261015/`):

### 1.1 Per-Target First ARP Timestamp Precedence (`anchors.py`, `synthesis.py`)
- **Rule**: `_arp_anchors()` records `target_first_seen[dst_ip]` and `target_first_evidence_ids[dst_ip]` for each destination IP addressed by an ARP burst, and includes every target's first ARP packet in `evidence_ids`. `_arp_link_precedence()` evaluates each `(arp_anchor, communication_anchor)` pair using the **target RTU's first ARP packet timestamp** (`timestamp_basis = "per_target_first_arp_packet"`), requiring:
  1. `rtu_ip in arp_anchor["targets"]` (target IP overlap),
  2. `target_first_arp_time <= link_change_time` (per-target temporal precedence), and
  3. `0.0 <= link_change_time - target_first_arp_time <= 15.0 s` (bounded horizon).
- **Fallback When Per-Target Timestamps Are Absent**: If `target_first_seen` is unavailable on an ARP anchor, `_arp_link_precedence()` sets `eligible = False` and emits only the weaker window-level co-occurrence hypothesis `arp_and_iec104_link_temporal_cooccurrence_without_per_target_timestamp` (`eligibility_gate = "degraded_missing_per_target_arp_timestamp"`).
- **Observed Change on `ev_cbe1e5bef23346604396` (No Artificial Retention)**:
  - `A001 -> A002` (RTU `172.16.3.10`): first ARP `EV-0e9f6fb66f6907e4` at `1742953786.677999` (+1.410 s) precedes link change at `1742953792.79` (+7.522 s), `dt = +6.112 s` $\to$ **Eligible**.
  - `A001 -> A004` (RTU `172.16.3.9`): first ARP `EV-fd36a37175d5af9d` at `1742953786.648633` (+1.381 s) precedes link change at `1742953800.09818` (+14.830 s), `dt = +13.450 s` $\to$ **Eligible**.
  - `A001 -> A003` (RTU `172.16.3.20`): first ARP `EV-dd59c3d758762e69` at `1742953831.077105` (+45.809 s) occurred **37.707 s after** the link change at `1742953793.37` (+8.102 s) $\to$ **Rejected (`ineligible_arp_link_pairs`)**.
  - Consequently, `EXP-001` (`arp_address_interference_preceding_iec104_session_loss_hypothesis`) narrows its precedence claim to `overlapping_target_rtu_ips = ['172.16.3.10', '172.16.3.9']` (`scope = ['A001', 'A002', 'A004']`), while `A003` (`172.16.3.20`) is explicitly listed in `ineligible_arp_link_pairs` and covered by `EXP-002` (`concurrent_l2_link_disturbance_and_arp_re_resolution_hypothesis`).
- **Observed Result on `ev_564bebaa45f0686cf98d`**:
  - No ARP anchors exist in `ev_564bebaa45f0686cf98d`; all 12 RTU ASDU bundles and all 5 cross-RTU verified element bridges (`BRG-001`..`BRG-005`) are byte-for-byte unchanged (`incident_synthesis.json` SHA256 `34974448c2cdca8181c27c6cb39594f4d9c477cb849dac8b0f3cf5b3a8108bad`).

### 1.2 Bridge RTU IP Exact Alignment Check (`consistency.py`)
- `check_quality_consistency()` now verifies not only `from_rtu_ip != to_rtu_ip`, but also that:
  - `bridge["from_rtu_ip"] == src_node["protocol_meta"]["rtu_ip"] == from_bundle["rtu_ip"]`, and
  - `bridge["to_rtu_ip"] == dst_node["protocol_meta"]["rtu_ip"] == to_bundle["rtu_ip"]`.
- Any discrepancy raises `synthesis_bridge_rtu_ip_mismatch` and downgrades the final report to `diagnostic_only_quality_inconsistent`.

---

## 2. Frozen Algorithm Architecture & Parameter Lock

No algorithm, threshold, or consistency gate rule may be modified during the cross-scenario evaluation across `01-Basic`, `02-Semiurban`, and `03-Rural`.

### 2.1 Frozen Module Hashes

| Layer / Module | Relative Path | Frozen SHA256 |
| --- | --- | --- |
| Evidence Indexer | `evidence/index.py` | `11a8bb73f72c0b71d69f398c701a5626b51a9e3fce5c060ee17819ef79aaa016` |
| IEC-104 Dissector | `evidence/iec104.py` | `1ffaf03f3f1ed49026411b5abb581f57696358ec11c1cbe47448d4eef9b7de86` |
| Raw APDU Decoder | `evidence/iec104_raw.py` | `0e06d7813de4565400ba4031c0ae196032ddb824528b8957f5dc6cd647104a34` |
| Field Audit | `evidence/field_audit.py` | `2712fa9a87cd9ab1d33d10d618024b9439935c686d69648763b7929e926fe37d` |
| Evidence Store | `evidence/store.py` | `a85ae489b228dbf4dc06968449c4b53798a1ab12c7308fd1dbe00ca3029650f3` |
| Evidence Queries | `evidence/queries.py` | `9d2fb070bb5a59a48205f6b114676583680da13a8b7c5815576c2639cca4583e` |
| Phase 1 Transactions | `reconstruction/transactions.py` | `d77dcd6bddfeb7c805229392dd83acf88879f1a7143b789c938cda1c8be8e850` |
| Event Anchor Discovery | `reconstruction/anchors.py` | `65c12ee679e986d829005f6bc28292958ab941c4059923eec45d64600357139f` |
| Behavioral Relations | `reconstruction/behavior.py` | `db98618f2db4017a11fa6909e993ebe9fe5bb2fcc0253fafb31f87963461e459` |
| Phase 2 Event Graph | `reconstruction/event_graph.py` | `d4a570aa0b4924bbdc0b108114a9af07082bafdb6a5efe821d296e52433ff883` |
| Phase 3 Storylines | `reconstruction/storyline.py` | `c01b1a9be706d224a1faabac88ed6d1e96dc9450068ea0a52aca4064a944bd70` |
| Phase 4 Synthesis | `reconstruction/synthesis.py` | `d040a767322d820b41e1b36df87630d0b87974ff0f6ce98d7d9af968e9660392` |
| Consistency Gates | `reconstruction/consistency.py` | `f9addfb77cc6adb8fcfcc5da9c0658e335453de92ed089bb8c3c7dca5f5aa2c1` |
| Investigation Report | `reconstruction/report.py` | `4285ec7239f5c6cacceb119a022a40372c59f0e61b70d0c6d8db58a8802166f4` |
| Reconstruction Engine | `reconstruction/engine.py` | `a0e99d95e7faa6c483313628fa225ee032a5d6e5bd968f6cadbc1dedb5a2af37` |

### 2.2 Frozen Hyperparameters & Gate Thresholds

| Stage | Parameter | Frozen Value | Role |
| --- | --- | --- | --- |
| Indexing | `context_seconds` | `15.0 s` | Pre/post window slice `[start - 15s, end + 15s)` |
| Transactions | `confirm_window_sec` / `termination_window_sec` | `5.0 s` / `10.0 s` | `COT=7` / `COT=10` protocol pairing horizon |
| Transactions | `post_feedback_sec` / `retransmit_window_sec` | `15.0 s` / `0.5 s` | Post-command feedback horizon / same-`tcp_seq` retransmission window |
| Anchors | `STEP_RELATIVE` / `PERSIST_RELATIVE` | `0.5` / `0.1` | Minimum relative step ($\ge 50\%$) and post-sample consistency tolerance ($\le 10\%$) |
| Anchors | `MAGNITUDE_FLOOR` / `NEAR_ZERO_RELATIVE` | `1e-3` / `1e-6` | Numerical noise floor and `to_zero` / `from_zero` relative threshold |
| Anchors | `MIN_PERSIST_SAMPLES` / `MIN_PERSIST_RATIO` | `2` / `0.8` | Minimum post-change samples and consistent sample ratio for `verified_observation` |
| Anchors | `MAX_PRE_SAMPLE_GAP_SECONDS` | `30.0 s` | Maximum pre-step polling gap before flagging `pre_sample_gap_exceeded` |
| Anchors | `VANTAGE_MERGE_SECONDS` | `0.5 s` | Maximum cross-vantage mirror transit gap for identical payloads |
| Anchors | `ARP_MIN_COUNT` / `ARP_RATE_FACTOR` | `10` / `5.0` | Minimum ARP packets in window and rate multiplier vs background |
| Anchors | `GAP_MIN_SECONDS` / `GAP_CADENCE_FACTOR` | `25.0 s` / `3.0` | Telemetry silence threshold per master–RTU link |
| Behavior | `HORIZON_SECONDS` / `MAX_CANDIDATES_PER_ANCHOR` | `15.0 s` / `6` | Maximum horizon for same-device transitions and unresolved cross-device candidates |
| Behavior | `MIN_LEVEL_SHIFT_RATIO_AGREEMENT` | `0.5` | Minimum ratio agreement between `from` and `to` `level_shift` steps |
| Storyline | `beam_width` / `max_depth` / `selection_limit` | `4` / `6` / `24` | Bounded beam search parameters and timeline selection cap |
| Synthesis | `phase_gap_seconds` / `ipal_independent_source_weight` | `15.0 s` / `0` | Candidate phase grouping gap and zero weight for IPAL correspondences |

---

## 3. Complete Sherlock v3 Cross-Scenario Experiment Plan

### 3.1 Strict Input Isolation & Air-Gapped Evaluation Protocol
1. **Window Boundary Input (`windows_times_only.json`)**:
   - The indexing and reconstruction pipeline receives **only** `(episode_id, scenario, recording, start, end)`.
   - `events.json`, `events.jsonl`, official event descriptions, attack family names, `malicious` flags, and `physical.zip` are never opened by `index_window()` or `reconstruct_incident()`.
2. **Air-Gapped Offline Evaluation (Post-Reconstruction Only)**:
   - Reconstruction runs to completion and writes immutable per-window artifacts (`run_manifest.json`, `transactions.json`, `event_anchors.json`, `event_graph.json`, `storylines.json`, `incident_synthesis.json`, `quality_consistency.json`, `lineage_consistency.json`, `investigation_report.json/.md`).
   - Any offline comparison against reference window descriptions is executed in a separate read-only analysis script **after** all reconstruction outputs and SHA256 manifests are frozen, and may never feed back into parameter tuning or rule changes.

### 3.2 Scenario Coverage & Stratum Design

| Scenario (`recording`) | Windows | Total Window Duration | PCAP Mirror Vantages | Mapped Data Points (`data-point-map.json`) | Role in Paper |
| --- | ---: | ---: | --- | ---: | --- |
| **`01-Basic` (`test`)** | `28` | `6,180.6 s` (`30.0`–`594.6 s`) | `4` (`n302`, `n303`, `n318`, `n321`) | `500` | Full characterization across all 4 observation strata: (S1) `16` control-command windows, (S2) `5` spontaneous state + measurement drop windows, (S3) `2` ARP / IEC-104 link disruption windows, (S4) `5` periodic-measurement-only low-information windows. |
| **`02-Semiurban` (`test`)** | `39` | `10,720.7 s` (`30.1`–`940.7 s`) | `6` (`n406`, `n407`, `n495`, `n502`, `n523`, `n532`) | `3,640` | Cross-scenario scalability & transfer test (7.3$\times$ more mapped points, 6 switch mirror vantages) with **zero parameter changes**. |
| **`03-Rural` (`test`)** | `36` | `10,362.0 s` (`30.1`–`970.5 s`) | `8` (`n402`, `n403`, `n468`, `n472`, `n477`, `n484`, `n493`, `n502`) | `1,908` | Cross-scenario transfer test on a radial/rural topology with 8 switch mirror vantages and **zero parameter changes**. |
| **Total (`test` splits)** | **`103`** | **`27,263.3 s` (`7.57 hours`)** | `4`–`8` per scenario | `500`–`3,640` | Complete evaluation across all three Sherlock v3 distribution/transmission grids. |

### 3.3 Standardized Per-Window Recording Schema & Failure/Abstention Taxonomy

For every evaluated window across `01-Basic`, `02-Semiurban`, and `03-Rural`, the batch runner will record a standardized summary row containing:
1. **Observation & Anchor Counts**: `anchor_count_total`, `anchor_count_verified`, `anchor_count_unverified`, breakdown by `spontaneous_state_report`, `measurement_step`, `communication_change`, and `arp_activity_increase`.
2. **Protocol Transactions**: `transaction_count_total`, `accepted_count` (`COT=7` `P/N=0`), `rejected_negative_ack_count`, `verified_state_or_measurement_transition_count`, `state_report_observed_unverified_count`, `no_state_change_count`, `cross_vantage_conflict_count`.
3. **Storylines & Behavioral Gates**: `storyline_count_total`, `supported_multi_node_storyline_count`, `verified_single_anchor_storyline_count`, `unverified_behavioral_observation_count`, `sequential_same_device_observation_count` (with exact `failed_conditions` distribution).
4. **Incident Synthesis (Layers 2–4)**: `rtu_asdu_bundle_count`, `cross_rtu_verified_element_bridge_count`, `same_rtu_supported_relation_count`, `bridged_bundle_component_count`, `candidate_scenario_phase_count`, `competing_explanation_count` & `competing_explanation_classes`, `unresolved_cross_device_branch_count`, and `source_dependency_ledger` counts by container family (`iec104_asdu`, `tcp_link`, `arp`, `composite_event`, `ipal_correspondence_row_count`).
5. **Consistency & Audit Status**: `quality_consistency_passed`, `lineage_consistency_passed`, `final_report_status`.
6. **Explicit Reconstruction Failure / Honest Abstention Reasons**:
   - `LOW_INFORMATION_PERIODIC_ONLY`: Window contains only periodic cyclic `M_ME_NC_1 (COT=1)` telemetry with no control commands, no `COT=3` state reports, no link disruptions, and no sustained measurement steps (`>= 50%`).
   - `COMMAND_WITHOUT_PRE_BASELINE`: Control command and `COT=3` feedback observed, but no pre-command IEC-104 state baseline exists in `[start - 15s, cmd_time)` (`state_report_observed_no_pre_baseline`).
   - `COMMAND_CONFIRMATION_WITHOUT_STATE_CHANGE`: `COT=6` and `COT=7` observed, but no subsequent state or measurement shift occurred (`no_state_change_observed`).
   - `UNVERIFIED_ANCHOR_QUARANTINED`: Anchor detected but quarantined due to `no_prior_state_value_in_window`, `not_sustained_in_later_samples`, `insufficient_post_samples`, `pre_sample_gap_exceeded`, or quality/test-bit issues.
   - `SAME_DEVICE_GATE_REJECTED_SEQUENTIAL`: Same-device multi-ASDU observations present but rejected by `evaluate_behavioral_relation_consistency()` (`change_type_mismatch`, `magnitude_direction_mismatch`, `magnitude_ratio_mismatch`, `endpoints_not_complementary`).
   - `CROSS_DEVICE_NO_TOPOLOGY_UNRESOLVED`: Multiple devices changed within `15 s`, but kept as `cross_device_temporal_candidate` (`unresolved`) because no topological or protocol link evidence exists in telemetry.

---

## 4. Data Integrity Audit & Resource Requirements Assessment

### 4.1 Raw Dataset Integrity Audit (`data/raw/sherlock/v3/`)

All three Sherlock v3 archives are present, intact, and verified against the project handoff MD5 checksums:

| Archive | Exact Compressed Bytes (`GiB` $2^{30}$ / `GB` $10^9$) | Exact Uncompressed Bytes (`GiB` $2^{30}$ / `GB` $10^9$) | MD5 Checksum | `discover_members()` Verification |
| --- | ---: | ---: | --- | --- |
| `01-Basic.zip` | `703,191,516 B` (`0.6549 GiB` / `0.7032 GB`) | `899,785,684 B` (`0.8380 GiB` / `0.8998 GB`) | `c482e0dc7e56b063b357d8b03be5cce6` (Match) | `test` (4 PCAPs, 1 state.gz, 1 map) & `train` (4 PCAPs, 1 state.gz, 1 map) OK |
| `02-Semiurban.zip` | `6,375,875,182 B` (`5.9380 GiB` / `6.3759 GB`) | `7,812,778,716 B` (`7.2762 GiB` / `7.8128 GB`) | `0f7d3eb61e478d05f4b431ae99d45564` (Match) | `test` (6 PCAPs, 1 state.gz, 1 map) & `train` (6 PCAPs, 1 state.gz, 1 map) OK |
| `03-Rural.zip` | `1,866,012,065 B` (`1.7379 GiB` / `1.8660 GB`) | `2,508,796,032 B` (`2.3365 GiB` / `2.5088 GB`) | `0cc7807bd5a76ea5bc85a1da6fd6c061` (Match) | `test` (8 PCAPs, 1 state.gz, 1 map) OK |

> **Document Revision Note (Size Reconciliation)**: `configs/etgi/method_freeze.v1.json` (`a0a4b86`) recorded the exact `stat().st_size` byte counts (`703,191,516`, `6,375,875,182`, and `1,866,012,065`), whereas the Markdown table in the initial draft of `docs/METHOD_FREEZE_MANIFEST.md` (`a0a4b86`) listed back-multiplied 2-decimal GiB approximations (`0.65 * 2^30 = 698,668,450`, `5.94 * 2^30 = 6,374,977,927`, `1.74 * 2^30 = 1,871,218,378`). The table above reconciles the Markdown text to the exact `stat().st_size` and `ZipInfo.file_size` sums and explicitly reports both binary `GiB` ($2^{30}$) and decimal `GB` ($10^9$). The underlying raw Sherlock v3 ZIP files were never modified and their MD5 digests are unchanged.

### 4.2 Compute Time & Disk Space Estimation

- **Available Local Disk Space**: **`72.25 GB` free** (on `/Users/potinglu/Documents/ICIT2027-mirage` volume, total `460.43 GB`).
- **Already Indexed Windows (Reusable Without Re-Indexing)**:
  - `01-Basic`: `8` windows already indexed (`ev_0961`, `ev_12dcd56b`, `ev_3e4d`, `ev_564bebaa`, `ev_4e913b`, `ev_812f80`, `ev_b15ac1`, `ev_cbe1e5`), averaging `10.8 MB` per `evidence.sqlite`.
  - `02-Semiurban`: `1` window already indexed (`ev_0431e34c3ed30056a8f0`, `27.43 MB` `evidence.sqlite`).
- **Resource Cost per Phase**:
  1. **Reconstruction + Synthesis (`reconstruct_incident --no-llm`)**:
     - CPU time: **`0.7 s`–`1.5 s` per window** once indexed (`~2 minutes` total for all 103 windows).
     - Artifact size: **`1.0 MB`–`4.0 MB` per window** (`~250 MB` total across 103 windows).
  2. **Window Indexing (`index_window` from ZIP stream + `tshark`)**:
     - `01-Basic` (remaining `20` of `28` test windows, `0.65 GB` ZIP): ~`15`–`25 s` per window $\to$ **`~6–8 minutes`**, ~`220 MB` SQLite storage.
     - `03-Rural` (`36` test windows, `1.74 GB` ZIP, 8 PCAPs): ~`35`–`55 s` per window (or ~`8 minutes` total if PCAPs are pre-sliced in a single pass) $\to$ ~`700 MB`–`1.1 GB` SQLite storage.
     - `02-Semiurban` (`39` test windows, `5.94 GB` ZIP, 6 PCAPs): streaming the `5.94 GB` ZIP repeatedly per window would be I/O-bound (~`90`–`150 s` per window), whereas a single-pass multi-window PCAP/state slice pass followed by per-window `tshark` indexing reduces total runtime to **`~15–20 minutes`** and ~`1.2`–`1.8 GB` SQLite storage (well within the `72.25 GB` free disk budget).

### 4.3 Staged Execution Plan (For Next Rounds)
- **Stage 1 (`01-Basic` Complete 28-Window Suite)**: Index the remaining 20 `01-Basic` test windows and run the frozen `reconstruct_incident --no-llm` across all 28 windows, producing the complete Basic stratum table (control commands, spontaneous state + measurement drops, ARP/link disruptions, and periodic-only windows).
- **Stage 2 (`02-Semiurban` & `03-Rural` Cross-Scenario Transfer Suite)**: Execute the frozen pipeline with zero parameter changes across the representative/full `02-Semiurban` and `03-Rural` test windows, quantifying cross-scenario generalization, consistency gate pass rates, and honest abstention rates.
