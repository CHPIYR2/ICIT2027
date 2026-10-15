# Stage 3 Baseline & Ablation Experimental Results — Paper-Readiness Audit Edition (All 103 Sherlock v3 Test Windows)

- **Frozen Engine Commit (`git_commit`)**: `2981fb062b127218a34f23f2ff0292e4ca8cfea7`
- **Reconstruction Code Hash (`code_sha256`)**: `d43d9867ce847df169e13345e4c3461cd99fd5167292a85cedaaa553d93e5bb3`
- **Evidence Layer Code Hash (`evidence_code_sha256`)**: `032c6977ac0507e9c442b37e4e78455d0ab6d1a21b1efe751a0ccf37242a3b85`
- **Audit-Response Output Directory**: `runs/etgi/stage3-audit-response-20261015/` (prior `runs/etgi/stage3-baseline-ablation-20261015/` preserved untouched)
- **Public Review Artifacts**: `review_artifacts/stage3-audit-response-20261015/`

---

## 1. Summary of Paper-Readiness Audit Corrections (Tasks 1–6)

1. **Task 1 — Separation of Unsubstantiated Candidates vs. Explicit Constraint Conflicts in `B1_temporal_only`**:
   - Rather than grouping all `84,836` non-corroborated temporal links together or treating `not same_device` as a proven false relation, `B1` candidate temporal relations (`107,666` total) are strictly partitioned into:
     - **`unsubstantiated_temporal_candidates`**: **`18,130` (`16.84%`)** — temporally proximate pairs (`0 <= dt <= 15s`) lacking direct protocol/topology link evidence (e.g. `not same_device` with valid endpoints, or `no_prior_state_value_in_window`), **not proven false**, held `unresolved` by MIRAGE-OT.
     - **`explicit_evidence_constraint_conflicts`**: **`66,706` (`61.96%`)** — pairs that directly violate checkable telemetry properties (quality/test-bit/vantage conflicts `8,489`, transient non-sustained oscillations `66,042`, same-device change-type/side conflicts `3,707`, same-ASDU co-reports chained as temporal steps `2,628`, and same-device direction/ratio conflicts `35`).
     - **`corroborated_same_device_candidates`**: **`22,830` (`21.20%`)**.
   - B1 relations are strictly referred to as **candidate temporal associations**, never "false causal inferences".
2. **Task 2 — Five-Way Packet-Identity Provenance Decomposition in `A2_without_provenance_dedup`**:
   - Using actual `evidence.sqlite` packet fields (`vantage`, 4-tuple, `timestamp`, `fingerprint`, `apci_tx`, `asdu_index`, `ca_ioa`, `object_index`, `tcp_seq`, `tcp_flags`, `op`) across the `9,836` raw observations (`4,493` distinct source containers, `5,343` excess rows), the `5,343` excess rows are decomposed into:
     - **`true_cross_vantage_mirror_duplicate_count`**: **`1,845`** (revised from the naive `2,509` estimate).
     - **`same_asdu_different_ioa_point_count`**: **`572`**.
     - **`distinct_messages_in_same_tcp_session_count`**: **`268`**.
     - **`distinct_time_network_events_in_anchor_count`**: **`396`** (distinct-time SYN/FIN/ARP events inside `communication_change` and `arp_activity_increase` anchors, e.g. `ev_cbe1e5bef23346604396` where `true_mirror = 0`, `same_session_msgs = 20`, `diff_time_events = 19`).
     - **`ipal_derived_observation_count`**: **`2,262`**.
     - **`unknown_provenance_relation_count`**: **`0`**.
   - Thus, **`4,679` rows** (`1,845 + 572 + 2,262`, revised from `5,343`) represent true duplicate/multi-IOA/IPAL source inflation (mean inflation factor **`2.44x`**, median **`2.22x`**), while **`664` rows** (`268 + 396`) represent multi-event aggregation inside link/ARP anchors.
3. **Task 3 — Sensitivity Analysis for `A1_without_behavioral_consistency_gate` Excluding Max Outlier `ev_52f5eee28f8b95e702fd`**:
   - Across all 103 windows, counterfactual A1 produces **`2,171` unsupported promotions** (`409` potential cross-RTU bridges), of which `1,966` (`360` bridges) originate from the severe cross-vantage MITM conflict window `ev_52f5eee28f8b95e702fd`.
   - **Excluding `ev_52f5eee28f8b95e702fd` (`N=102` windows)**: counterfactual A1 still produces **`205` unsupported promotions** (`126` behavioral + `79` transaction command-effect) and **`49` spurious cross-RTU bridge promotions** across **51 of the 102 windows** (mean `2.01`, descriptive bootstrap 95% CI `[1.15, 2.92]`).
4. **Task 4 — Four-Level E3 Traceability Definition**:
   - Level 1 (`1_evidence_citation_presence`): **`103 / 103` (`100.0%`)**
   - Level 2 (`2_evidence_id_resolution` in `evidence.sqlite`): **`103 / 103` (`100.0%`, `0` missing IDs)**
   - Level 3 (`3_evidence_to_fact_anchor_consistency`): **`102 / 103` (`99.03%`)** (`ev_5dd0102bf58bf2ce9487` fails on `A007` `EV-6e9e7ece8bf456f0` `time_outside_cited_sample`)
   - Level 4 (`4_full_lineage_consistency`): **`102 / 103` (`99.03%`)**.

---

## 2. Quantitative Tables Across All 103 Windows (`Total (Mean / Med / P95 / Max)`)

### 2.1 RQ1 — `B1_temporal_only` vs. Full MIRAGE-OT (Audit-Corrected)

| Metric (`Total (Mean / Med / P95 / Max)`) | `01-Basic` (`N=28`) | `02-Semiurban` (`N=39`) | `03-Rural` (`N=36`) | All 103 Windows (`N=103`) |
| --- | --- | --- | --- | --- |
| **B1 Unbounded 15s Temporal Pairs** | `43,880` (`1567.143` / `23.5` / `10116.0` / `21575`) | `244,745` (`6275.513` / `2594.0` / `19752.0` / `37537`) | `110,707` (`3075.194` / `2254.5` / `10745.0` / `11920`) | **`399,332` (`3877.01` / `381.0` / `17631.0` / `37537`)** |
| **B1 Bounded Candidate Temporal Relations** | `22,632` (`808.286` / `22.5` / `5273.0` / `6930`) | `50,750` (`1301.282` / `580.0` / `4632.0` / `8091`) | `34,284` (`952.333` / `572.5` / `2823.0` / `3796`) | **`107,666` (`1045.301` / `192.0` / `3796.0` / `8091`)** |
| — Topology: Cross-Device Candidates | `10,630` (`379.643` / `18.5` / `2150.0` / `3998`) | `44,253` (`1134.692` / `575.0` / `3707.0` / `6456`) | `23,355` (`648.75` / `440.0` / `2420.0` / `2698`) | `78,238` (`759.592` / `129.0` / `3401.0` / `6456`) |
| — Topology: Same-Device Separate-ASDU Candidates | `10,437` (`372.75` / `2.0` / `2469.0` / `3123`) | `5,770` (`147.949` / `1.0` / `1606.0` / `2487`) | `10,593` (`294.25` / `1.0` / `2469.0` / `3280`) | `26,800` (`260.194` / `1.0` / `2365.0` / `3280`) |
| — Topology: Same-ASDU Co-Report Candidates | `1,565` (`55.893` / `0.0` / `364.0` / `966`) | `727` (`18.641` / `7.0` / `84.0` / `123`) | `336` (`9.333` / `2.5` / `63.0` / `95`) | `2,628` (`25.515` / `3.0` / `84.0` / `966`) |
| **1. Unsubstantiated Temporal Candidates (No Direct Link, Not Proven False)** | `3,319` (`118.536` / `6.0` / `494.0` / `2150`) | `9,285` (`238.077` / `158.0` / `697.0` / `1343`) | `5,526` (`153.5` / `74.5` / `570.0` / `603`) | **`18,130` (`176.019` / `53.0` / `580.0` / `2150`)** |
| **2. Explicit Evidence Constraint Conflicts (`Total`)** | `12,003` (`428.679` / `4.5` / `2352.0` / `6928`) | `36,425` (`933.974` / `161.0` / `3761.0` / `5179`) | `18,278` (`507.722` / `153.5` / `2136.0` / `2416`) | **`66,706` (`647.631` / `59.0` / `3213.0` / `6928`)** |
| — Endpoint Transient / Not Sustained Conflict | `11,928` (`426.0` / `3.5` / `2342.0` / `6928`) | `36,103` (`925.718` / `160.0` / `3754.0` / `5176`) | `18,011` (`500.306` / `153.0` / `2136.0` / `2415`) | `66,042` (`641.184` / `54.0` / `3210.0` / `6928`) |
| — Endpoint Quality / Test-Bit / Vantage Conflict | `7,085` (`253.036` / `0.0` / `1396.0` / `4530`) | `1,404` (`36.0` / `0.0` / `201.0` / `1198`) | `0` (`0.0` / `0.0` / `0.0` / `0`) | `8,489` (`82.417` / `0.0` / `5.0` / `4530`) |
| — Same-Device Change-Type or Side Conflict | `2,920` (`104.286` / `0.0` / `575.0` / `1786`) | `692` (`17.744` / `0.0` / `37.0` / `547`) | `95` (`2.639` / `0.0` / `26.0` / `26`) | `3,707` (`35.99` / `0.0` / `26.0` / `1786`) |
| — Same-ASDU Co-Report Temporal Ordering Conflict | `1,565` (`55.893` / `0.0` / `364.0` / `966`) | `727` (`18.641` / `7.0` / `84.0` / `123`) | `336` (`9.333` / `2.5` / `63.0` / `95`) | `2,628` (`25.515` / `3.0` / `84.0` / `966`) |
| — Same-Device Direction or Ratio Conflict | `14` (`0.5` / `0.0` / `4.0` / `4`) | `7` (`0.179` / `0.0` / `1.0` / `2`) | `14` (`0.389` / `0.0` / `2.0` / `2`) | `35` (`0.34` / `0.0` / `2.0` / `4`) |
| **3. Corroborated Same-Device Candidates** | `7,310` (`261.071` / `1.0` / `2469.0` / `3123`) | `5,040` (`129.231` / `0.0` / `1569.0` / `2471`) | `10,480` (`291.111` / `0.0` / `2469.0` / `3280`) | **`22,830` (`221.65` / `1.0` / `2353.0` / `3280`)** |

---

### 2.2 RQ3 — Counterfactual Ablation `A1` (`All 103 Windows` vs. `102 Windows Excluding ev_52f5ee`)

| Counterfactual Metric (`Total (Mean / Med / P95 / Max)`) | All 103 Windows (`N=103`) | Excluding Max Outlier `ev_52f5ee` (`N=102`) | Contribution of `ev_52f5ee` Alone |
| --- | --- | --- | ---: |
| **Originally Supported Relations (Gate Passed)** | `61` (`0.592` / `0.0` / `4.0` / `11`) | `61` (`0.598` / `0.0` / `4.0` / `11`) | `0` |
| **Counterfactual Unsupported Promotions (`Total`)** | **`2,171` (`21.078` / `1.0` / `18.0` / `1966`)** | **`205` (`2.01` / `0.5` / `6.0` / `26`)** | `1,966` (`90.56%`) |
| — Behavioral Same-Device Promotions | `2,092` (`20.311` / `0.0` / `6.0` / `1966`) | `126` (`1.235` / `0.0` / `5.0` / `26`) | `1,966` |
| — Transaction Command-to-Effect Promotions | `79` (`0.767` / `0.0` / `3.0` / `20`) | `79` (`0.775` / `0.0` / `3.0` / `20`) | `0` |
| **Potential Spurious Cross-RTU Bridge Promotions** | **`409` (`3.971` / `0.0` / `2.0` / `360`)** | **`49` (`0.48` / `0.0` / `2.0` / `15`)** | `360` (`88.02%`) |
| — Violation: Persistence Insufficient | `2,035` (`19.757` / `0.0` / `5.0` / `1966`) | `69` (`0.676` / `0.0` / `3.0` / `15`) | `1,966` |
| — Violation: Non-Complementary / Disjoint Interval | `1,930` (`18.738` / `0.0` / `4.0` / `1843`) | `87` (`0.853` / `0.0` / `4.0` / `26`) | `1,843` |
| — Violation: Quality / Test-Bit / Vantage Conflict | `1,357` (`13.175` / `0.0` / `3.0` / `1318`) | `39` (`0.382` / `0.0` / `2.0` / `4`) | `1,318` |
| — Violation: Change-Type Mismatch | `190` (`1.845` / `0.0` / `1.0` / `180`) | `10` (`0.098` / `0.0` / `1.0` / `3`) | `180` |
| — Violation: Prior State Baseline Missing | `83` (`0.806` / `0.0` / `3.0` / `20`) | `83` (`0.814` / `0.0` / `3.0` / `20`) | `0` |
| — Violation: Magnitude / Direction Conflict | `55` (`0.534` / `0.0` / `1.0` / `20`) | `55` (`0.539` / `0.0` / `1.0` / `20`) | `0` |
| **Windows with $>0$ Unsupported Promotions** | `52 / 103` (`50.49%`, 95% CI `[1.42, 59.87]`) | **`51 / 102` (`50.00%`, 95% CI `[1.15, 2.92]`)** | `1` window |

---

### 2.3 RQ4 — Counterfactual Ablation `A2` (`Five-Way Packet-Identity Provenance Decomposition`)

| Metric (`Total (Mean / Med / P95 / Max)`) | `01-Basic` (`N=28`) | `02-Semiurban` (`N=39`) | `03-Rural` (`N=36`) | All 103 Windows (`N=103`) |
| --- | --- | --- | --- | --- |
| **Raw Observations Cited (`Network + IPAL`)** | `1,342` (`47.929` / `12.5` / `232.0` / `372`) | `3,756` (`96.308` / `56.0` / `354.0` / `448`) | `4,738` (`131.611` / `104.5` / `590.0` / `740`) | **`9,836` (`95.495` / `36.0` / `354.0` / `740`)** |
| **Deduplicated Message / Event Containers (`MIRAGE-OT`)** | `986` (`35.214` / `4.0` / `214.0` / `366`) | `1,670` (`42.821` / `12.0` / `178.0` / `354`) | `1,837` (`51.028` / `31.0` / `178.0` / `370`) | **`4,493` (`43.621` / `9.0` / `178.0` / `370`)** |
| **Scenario-Wide Unique RTU IPs (`Sum Across Windows`)** | `25` unique (`186` window-sum) | `69` unique (`696` window-sum) | `57` unique (`679` window-sum) | `25` / `69` / `57` (`1,561` window-sum) |
| **1. True Cross-Vantage Mirror Duplicates (Same Packet)** | `83` (`2.964` / `0.0` / `18.0` / `19`) | `465` (`11.923` / `1.0` / `86.0` / `88`) | `1,297` (`36.028` / `7.5` / `172.0` / `370`) | **`1,845` (`17.913` / `3.0` / `88.0` / `370`)** |
| **2. Same-ASDU Different IOA Points (Same Packet)** | `62` (`2.214` / `0.0` / `13.0` / `41`) | `228` (`5.846` / `0.0` / `48.0` / `85`) | `282` (`7.833` / `0.0` / `96.0` / `167`) | **`572` (`5.553` / `0.0` / `31.0` / `167`)** |
| **3. IPAL-Derived State Records (No Packet Lineage)** | `109` (`3.893` / `1.0` / `18.0` / `53`) | `1,138` (`29.179` / `4.0` / `128.0` / `179`) | `1,015` (`28.194` / `3.5` / `182.0` / `235`) | **`2,262` (`21.961` / `2.0` / `72.0` / `235`)** |
| **Subtotal: True Duplicate / Multi-IOA / IPAL Inflation (`1+2+3`)** | `254` (`9.071` / `3.5` / `31.0` / `97`) | `1,831` (`46.949` / `5.0` / `264.0` / `350`) | `2,594` (`72.056` / `12.5` / `412.0` / `522`) | **`4,679` (`45.427` / `5.0` / `173.0` / `522`)** |
| **4. Distinct Messages in Same TCP Session (Link/Tx)** | `33` (`1.179` / `0.0` / `13.0` / `20`) | `117` (`3.0` / `0.0` / `26.0` / `35`) | `118` (`3.278` / `0.0` / `26.0` / `27`) | **`268` (`2.602` / `0.0` / `20.0` / `35`)** |
| **5. Distinct-Time Network Events in Link/ARP Anchor** | `69` (`2.464` / `0.0` / `18.0` / `19`) | `138` (`3.538` / `0.0` / `23.0` / `25`) | `189` (`5.25` / `0.0` / `19.0` / `24`) | **`396` (`3.845` / `0.0` / `19.0` / `25`)** |
| **Subtotal: Multi-Event Anchor Aggregation (`4+5`)** | `102` (`3.643` / `0.0` / `22.0` / `39`) | `255` (`6.538` / `0.0` / `49.0` / `55`) | `307` (`8.528` / `0.0` / `44.0` / `44`) | **`664` (`6.447` / `0.0` / `38.0` / `55`)** |
| **6. Unknown Provenance Relation Count** | `0` | `0` | `0` | **`0`** |
| **Strict Duplicate & Derived Inflation Factor** | `66.1994` (`2.364` / `1.432` / `9.0` / `9.083`) | `96.5623` (`2.476` / `2.167` / `8.889` / `14.0`) | `88.7035` (`2.464` / `2.536` / `5.791` / `8.677`) | **`251.4652` (`2.441` / `2.217` / `7.2` / `14.0`)** |

---

### 2.4 RQ5 & Task 4 — Four-Level `E3` Traceability Verification Across All 103 Windows

| Traceability Verification Level | `01-Basic` (`N=28`) | `02-Semiurban` (`N=39`) | `03-Rural` (`N=36`) | All 103 Windows (`N=103`) |
| --- | ---: | ---: | ---: | ---: |
| **Level 1: Evidence Citation Presence** (non-empty `evidence_ids` fields) | `28 / 28` (`100.0%`) | `39 / 39` (`100.0%`) | `36 / 36` (`100.0%`) | **`103 / 103` (`100.0%`)** |
| **Level 2: Evidence ID Resolution** (all cited IDs exist in `evidence.sqlite`) | `28 / 28` (`100.0%`) | `39 / 39` (`100.0%`) | `36 / 36` (`100.0%`) | **`103 / 103` (`100.0%`)** |
| **Level 3: Evidence-to-Fact/Anchor Consistency** (entity, `ca_ioa`, host, time bounds) | `28 / 28` (`100.0%`) | **`38 / 39` (`97.44%`)** | `36 / 36` (`100.0%`) | **`102 / 103` (`99.03%`)** |
| **Level 4: Full Lineage Consistency** (`lineage_consistency.json` `consistent=True`) | `28 / 28` (`100.0%`) | **`38 / 39` (`97.44%`)** | `36 / 36` (`100.0%`) | **`102 / 103` (`99.03%`)** |

---

## 3. Task 6 — Air-Gapped Post-Freeze Physical State Snapshot Comparison (`01-Basic` `test/physical.zip`)

Executed strictly offline and read-only after all reconstruction outputs were frozen (`40,319` 1-second pandapower physical snapshots in `01-Basic/raw/test/physical.zip`):

1. **Verified Control-Command Transitions (`9 / 9 = 100.0%` Physical State/Measurement Value Agreement)**:
   - All `9` transactions across the `6` `01-Basic` verified-command windows (`ev_e76705884b8fec84592a` `sgen.1`, `ev_1a2c7b07458620ddeb67` `switch.29` & `switch.30`, `ev_12dcd56b2f5e78144cfb` `sgen.10`, `ev_54569eab2d55482f6496` `switch.0`, `ev_343cc5effb0b1b22931b` `sgen.12`, `storage.1`, `sgen.6`, and `ev_0961f1c2da8a257e3ebc` `sgen.6`) match the simulator's physical pre-event and post-event state/measurement values.
2. **Cross-RTU Verified Element Bridges (`6 / 6 = 100.0%` Physical Endpoint State Agreement across `32` Endpoint Attributes)**:
   - All `5` Cross-RTU Bridges in `ev_564bebaa45f0686cf98d` (`line.0`, `line.1`, `line.3`, `line.4`, `line.12`) and `1` Cross-RTU Bridge in `ev_b15ac1c8e04d148f09cb` (`line.2`) match the simulator's physical endpoint changes (noting that pandapower outputs `0.0` for de-energized active/reactive power and `NaN` for de-energized island voltage/current, which the RTU encodes as `0.0` in IEC-104 `M_ME_NC_1`).
3. **MITM Cross-Vantage Conflict Quarantine (`ev_52f5eee28f8b95e702fd`)**:
   - In the physical simulator, `switch.21` opened once (`True -> False`) and `sgen.12` active power dropped to `0.0 W` and remained `0.0 W`. The `671` rapid oscillation anchors in network telemetry were artifacts of conflicting packets across mirror vantages (`n302` vs `n318`), which MIRAGE-OT's `_merge_iec_vantages()` flagged and quarantined out of supported spines.

---

## 4. Seven Categories / 11 Real Sherlock Case Studies (Task 5)

### Instance 01 (`C1_command_passed_consistency_gate`) — `01-Basic` / `ev_0961f1c2da8a257e3ebc`
- **Category**: IEC-104 control command passing pre/post transition consistency gate
- **Selection Rule**: Select `01-Basic` window `ev_0961f1c2da8a257e3ebc` (setpoint command on `sgen.6`) and `02-Semiurban` window `ev_229f54b33cd3bfeb8f67` (binary command on `switch.335:closed`), where `COT=6 -> COT=7 (P/N=0)` is followed by a decoded pre-to-post shift matching the target.
- **1. Raw Observable Facts**:
  - Control transactions: `4` (unpaired control replies: `0`); Verified anchors: `14`; Quarantined unverified anchors: `4`
- **2. Baseline Relations**:
  - `B1_temporal_only`: `125` candidate temporal links (`100` unsubstantiated candidates + `15` explicit constraint conflicts `{'endpoint_quality_or_test_bit_conflict': 0, 'endpoint_transient_not_sustained_conflict': 10, 'same_device_direction_or_ratio_conflict': 1, 'same_device_change_type_or_side_conflict': 3, 'same_asdu_co_report_temporal_ordering_conflict': 3}`; topology `{'cross_device_candidate_count': 108, 'same_device_separate_asdu_candidate_count': 14, 'same_asdu_co_report_candidate_count': 3}`).
  - `B2_protocol_only`: `APPLICABLE_CONTROL_COMMAND_WINDOW`, `4` protocol storylines, `1` verified transitions; omits `13` verified behavioral anchors and `0` cross-RTU bridges.
- **3. Full MIRAGE-OT Relations**:
  - `report_status`: `quality_consistent` (`quality_consistency=True`, `lineage_consistency=True`)
  - `E3 Traceability (4 Levels)`: `{'1_evidence_citation_presence': True, '2_evidence_id_resolution': True, '3_evidence_to_fact_anchor_consistency': True, '4_full_lineage_consistency': True, 'synthesis_cited_evidence_id_count': 8, 'sqlite_unresolved_ids': [], 'timeline_row_check_failure_count': 0, 'behavioral_anchor_row_check_failure_count': 0}`
  - RTU ASDU Bundles: `0`; Cross-RTU Verified Element Bridges: `[]`
- **4. Methodological Differences**:
  - vs `B1`: B1 emits 125 candidate temporal links (100 unsubstantiated cross-device/unverified candidates and 15 explicit quality/persistence/direction/same-ASDU conflicts); MIRAGE-OT keeps cross-device links unresolved and restricts supported bridges to 0.
  - vs `B2`: B2 is `APPLICABLE_CONTROL_COMMAND_WINDOW` and omits 13 verified behavioral anchors and 0 cross-RTU bridges.
  - vs `A1`: Counterfactual A1 promotes 3 unsupported relations ({'quality_or_test_bit_violation': 3, 'persistence_insufficient_violation': 0, 'prior_state_baseline_missing_violation': 3, 'change_type_mismatch_violation': 0, 'magnitude_or_direction_conflict_violation': 0, 'non_complementary_or_disjoint_interval_violation': 0}).
  - vs `A2`: Counterfactual A2 counts 31 raw observations vs 13 message/event containers: true_mirror=13, same_asdu_ioa=0, same_tcp_session_msgs=0, diff_time_anchor_events=0, ipal=5.
  - vs `A3`: Without Incident Synthesis, A3 outputs 6 local storylines without consolidating 0 ASDU bundles, 0 cross-RTU bridges, or 1 competing explanations.
- **5. Cited Evidence IDs**: `['EV-494a34e6da358c21', 'EV-918472877d43879f', 'EV-43ead8119c854618', 'EV-76020d689440e581', 'EV-ba4f905fff7eaca9', 'EV-78d55af4a2046fad', 'EV-961567f8b54229f1', 'EV-d5420c7d73dd15c7', 'EV-accf99760a168d29', 'EV-8cda44d8746c998a', 'EV-15246b352cf4b896', 'EV-b8bc847b6ab955d9', 'EV-fe8bd9d68c56080f', 'EV-94f5611fd32eefad', 'EV-96c4cfdc8a90f8d4', 'EV-8b19c9ecd899e660']`
- **6. Remaining Unconfirmed Items**: `['Physical causation across distinct grid elements (no bus-branch topology model in telemetry)', 'Initiating actor or host process behind observed network frames']`

### Instance 02 (`C1_command_passed_consistency_gate`) — `02-Semiurban` / `ev_229f54b33cd3bfeb8f67`
- **Category**: IEC-104 control command passing pre/post transition consistency gate
- **Selection Rule**: Select `01-Basic` window `ev_0961f1c2da8a257e3ebc` (setpoint command on `sgen.6`) and `02-Semiurban` window `ev_229f54b33cd3bfeb8f67` (binary command on `switch.335:closed`), where `COT=6 -> COT=7 (P/N=0)` is followed by a decoded pre-to-post shift matching the target.
- **1. Raw Observable Facts**:
  - Control transactions: `1` (unpaired control replies: `0`); Verified anchors: `67`; Quarantined unverified anchors: `510`
- **2. Baseline Relations**:
  - `B1_temporal_only`: `4073` candidate temporal links (`311` unsubstantiated candidates + `3761` explicit constraint conflicts `{'endpoint_quality_or_test_bit_conflict': 1198, 'endpoint_transient_not_sustained_conflict': 3754, 'same_device_direction_or_ratio_conflict': 0, 'same_device_change_type_or_side_conflict': 547, 'same_asdu_co_report_temporal_ordering_conflict': 123}`; topology `{'cross_device_candidate_count': 3401, 'same_device_separate_asdu_candidate_count': 549, 'same_asdu_co_report_candidate_count': 123}`).
  - `B2_protocol_only`: `APPLICABLE_CONTROL_COMMAND_WINDOW`, `1` protocol storylines, `1` verified transitions; omits `66` verified behavioral anchors and `0` cross-RTU bridges.
- **3. Full MIRAGE-OT Relations**:
  - `report_status`: `quality_consistent` (`quality_consistency=True`, `lineage_consistency=True`)
  - `E3 Traceability (4 Levels)`: `{'1_evidence_citation_presence': True, '2_evidence_id_resolution': True, '3_evidence_to_fact_anchor_consistency': True, '4_full_lineage_consistency': True, 'synthesis_cited_evidence_id_count': 13, 'sqlite_unresolved_ids': [], 'timeline_row_check_failure_count': 0, 'behavioral_anchor_row_check_failure_count': 0}`
  - RTU ASDU Bundles: `0`; Cross-RTU Verified Element Bridges: `[]`
- **4. Methodological Differences**:
  - vs `B1`: B1 emits 4073 candidate temporal links (311 unsubstantiated cross-device/unverified candidates and 3761 explicit quality/persistence/direction/same-ASDU conflicts); MIRAGE-OT keeps cross-device links unresolved and restricts supported bridges to 0.
  - vs `B2`: B2 is `APPLICABLE_CONTROL_COMMAND_WINDOW` and omits 66 verified behavioral anchors and 0 cross-RTU bridges.
  - vs `A1`: Counterfactual A1 promotes 0 unsupported relations ({'quality_or_test_bit_violation': 0, 'persistence_insufficient_violation': 0, 'prior_state_baseline_missing_violation': 0, 'change_type_mismatch_violation': 0, 'magnitude_or_direction_conflict_violation': 0, 'non_complementary_or_disjoint_interval_violation': 0}).
  - vs `A2`: Counterfactual A2 counts 6 raw observations vs 4 message/event containers: true_mirror=1, same_asdu_ioa=0, same_tcp_session_msgs=0, diff_time_anchor_events=0, ipal=1.
  - vs `A3`: Without Incident Synthesis, A3 outputs 5 local storylines without consolidating 0 ASDU bundles, 0 cross-RTU bridges, or 3 competing explanations.
- **5. Cited Evidence IDs**: `['EV-00a00cd3fa83e497', 'EV-7c67612c711ec8cd', 'EV-3334e4f733bfeddb', 'EV-5b22fe895f2c795d', 'EV-65ebf26ca8e9e5e4', 'EV-de0e6d51086a4384', 'EV-bcd4a8979aabf22e', 'EV-781966975711b2a5', 'EV-d08935622b887dbd', 'EV-94a7e098b756773e']`
- **6. Remaining Unconfirmed Items**: `['Physical causation across distinct grid elements (no bus-branch topology model in telemetry)', 'Initiating actor or host process behind observed network frames']`

### Instance 03 (`C2_command_without_pre_post_measurement_evidence`) — `01-Basic` / `ev_3e4d36008b29595ef246`
- **Category**: IEC-104 control command without sufficient pre/post state or measurement evidence
- **Selection Rule**: Select `01-Basic` window `ev_3e4d36008b29595ef246`, which contains 3 accepted switch commands (`TX001` `switch.23`, `TX002` `switch.24`, `TX003` `switch.30`) where `TX001`/`TX002` lack a prior IEC-104 state baseline in `[start-15s, cmd_time)` and `TX003` has no post-command state report.
- **1. Raw Observable Facts**:
  - Control transactions: `3` (unpaired control replies: `0`); Verified anchors: `18`; Quarantined unverified anchors: `15`
- **2. Baseline Relations**:
  - `B1_temporal_only`: `234` candidate temporal links (`74` unsubstantiated candidates + `151` explicit constraint conflicts `{'endpoint_quality_or_test_bit_conflict': 0, 'endpoint_transient_not_sustained_conflict': 142, 'same_device_direction_or_ratio_conflict': 4, 'same_device_change_type_or_side_conflict': 7, 'same_asdu_co_report_temporal_ordering_conflict': 21}`; topology `{'cross_device_candidate_count': 189, 'same_device_separate_asdu_candidate_count': 24, 'same_asdu_co_report_candidate_count': 21}`).
  - `B2_protocol_only`: `APPLICABLE_CONTROL_COMMAND_WINDOW`, `3` protocol storylines, `0` verified transitions; omits `18` verified behavioral anchors and `0` cross-RTU bridges.
- **3. Full MIRAGE-OT Relations**:
  - `report_status`: `quality_consistent` (`quality_consistency=True`, `lineage_consistency=True`)
  - `E3 Traceability (4 Levels)`: `{'1_evidence_citation_presence': True, '2_evidence_id_resolution': True, '3_evidence_to_fact_anchor_consistency': True, '4_full_lineage_consistency': True, 'synthesis_cited_evidence_id_count': 8, 'sqlite_unresolved_ids': [], 'timeline_row_check_failure_count': 0, 'behavioral_anchor_row_check_failure_count': 0}`
  - RTU ASDU Bundles: `0`; Cross-RTU Verified Element Bridges: `[]`
- **4. Methodological Differences**:
  - vs `B1`: B1 emits 234 candidate temporal links (74 unsubstantiated cross-device/unverified candidates and 151 explicit quality/persistence/direction/same-ASDU conflicts); MIRAGE-OT keeps cross-device links unresolved and restricts supported bridges to 0.
  - vs `B2`: B2 is `APPLICABLE_CONTROL_COMMAND_WINDOW` and omits 18 verified behavioral anchors and 0 cross-RTU bridges.
  - vs `A1`: Counterfactual A1 promotes 2 unsupported relations ({'quality_or_test_bit_violation': 2, 'persistence_insufficient_violation': 0, 'prior_state_baseline_missing_violation': 2, 'change_type_mismatch_violation': 0, 'magnitude_or_direction_conflict_violation': 0, 'non_complementary_or_disjoint_interval_violation': 0}).
  - vs `A2`: Counterfactual A2 counts 10 raw observations vs 8 message/event containers: true_mirror=0, same_asdu_ioa=0, same_tcp_session_msgs=0, diff_time_anchor_events=0, ipal=2.
  - vs `A3`: Without Incident Synthesis, A3 outputs 6 local storylines without consolidating 0 ASDU bundles, 0 cross-RTU bridges, or 1 competing explanations.
- **5. Cited Evidence IDs**: `['EV-791de060d8603144', 'EV-e7746bd283b0f24f', 'EV-2a9f286e93fcbdac', 'EV-1584efea78937735', 'EV-eeeef33791631632', 'EV-9ea7e1f8c572ba8f', 'EV-2b03558caa5c80ba', 'EV-01204992f7cb6854', 'EV-889bf81070aa2ebf', 'EV-358c43a69870cbc2', 'EV-4a9c9a05ab9eb4f1', 'EV-b55b9638092be4fa', 'EV-96f93dc194661bb4', 'EV-45db89473e47780a', 'EV-18d92f1b33278446', 'EV-31818c33b6e8aeea']`
- **6. Remaining Unconfirmed Items**: `['Physical causation across distinct grid elements (no bus-branch topology model in telemetry)', 'Initiating actor or host process behind observed network frames']`

### Instance 04 (`C3_no_command_cross_rtu_verified_bridge`) — `01-Basic` / `ev_564bebaa45f0686cf98d`
- **Category**: No control command, corroborated Cross-RTU Verified Element Bridges
- **Selection Rule**: Select one no-command `S2` window from each scenario (`01-Basic` `ev_564bebaa45f0686cf98d`, `02-Semiurban` `ev_d3c46672f9814dcdc40c`, `03-Rural` `ev_0d966f97d1922adb09bb`) where `verified_element_bridges > 0`.
- **1. Raw Observable Facts**:
  - Control transactions: `0` (unpaired control replies: `0`); Verified anchors: `23`; Quarantined unverified anchors: `9`
- **2. Baseline Relations**:
  - `B1_temporal_only`: `157` candidate temporal links (`123` unsubstantiated candidates + `29` explicit constraint conflicts `{'endpoint_quality_or_test_bit_conflict': 0, 'endpoint_transient_not_sustained_conflict': 8, 'same_device_direction_or_ratio_conflict': 2, 'same_device_change_type_or_side_conflict': 1, 'same_asdu_co_report_temporal_ordering_conflict': 20}`; topology `{'cross_device_candidate_count': 129, 'same_device_separate_asdu_candidate_count': 8, 'same_asdu_co_report_candidate_count': 20}`).
  - `B2_protocol_only`: `NOT_APPLICABLE_NO_CONTROL_COMMANDS`, `0` protocol storylines, `0` verified transitions; omits `23` verified behavioral anchors and `5` cross-RTU bridges.
- **3. Full MIRAGE-OT Relations**:
  - `report_status`: `quality_consistent` (`quality_consistency=True`, `lineage_consistency=True`)
  - `E3 Traceability (4 Levels)`: `{'1_evidence_citation_presence': True, '2_evidence_id_resolution': True, '3_evidence_to_fact_anchor_consistency': True, '4_full_lineage_consistency': True, 'synthesis_cited_evidence_id_count': 57, 'sqlite_unresolved_ids': [], 'timeline_row_check_failure_count': 0, 'behavioral_anchor_row_check_failure_count': 0}`
  - RTU ASDU Bundles: `12`; Cross-RTU Verified Element Bridges: `[('BRG-001', 'line.0', '172.16.2.3->172.16.3.13'), ('BRG-002', 'line.3', '172.16.3.18->172.16.3.16'), ('BRG-003', 'line.4', '172.16.3.18->172.16.3.22'), ('BRG-004', 'line.1', '172.16.3.13->172.16.3.14'), ('BRG-005', 'line.12', '172.16.3.22->172.16.3.24')]`
- **4. Methodological Differences**:
  - vs `B1`: B1 emits 157 candidate temporal links (123 unsubstantiated cross-device/unverified candidates and 29 explicit quality/persistence/direction/same-ASDU conflicts); MIRAGE-OT keeps cross-device links unresolved and restricts supported bridges to 5.
  - vs `B2`: B2 is `NOT_APPLICABLE_NO_CONTROL_COMMANDS` and omits 23 verified behavioral anchors and 5 cross-RTU bridges.
  - vs `A1`: Counterfactual A1 promotes 3 unsupported relations ({'quality_or_test_bit_violation': 0, 'persistence_insufficient_violation': 2, 'prior_state_baseline_missing_violation': 0, 'change_type_mismatch_violation': 1, 'magnitude_or_direction_conflict_violation': 2, 'non_complementary_or_disjoint_interval_violation': 0}).
  - vs `A2`: Counterfactual A2 counts 109 raw observations vs 12 message/event containers: true_mirror=3, same_asdu_ioa=41, same_tcp_session_msgs=0, diff_time_anchor_events=0, ipal=53.
  - vs `A3`: Without Incident Synthesis, A3 outputs 27 local storylines without consolidating 12 ASDU bundles, 5 cross-RTU bridges, or 2 competing explanations.
- **5. Cited Evidence IDs**: `['EV-3c3cbb46e50d7d28', 'EV-dea3772f106a463b', 'EV-84daa0e68ef06102', 'EV-8157ecd56e21ff99', 'EV-d0ebc674e5e5f30c', 'EV-7d6b819e7f3d4f63', 'EV-d852dab86b4e7efb', 'EV-99ceaa9a519bf6c0', 'EV-f969c5f8a10a6e07', 'EV-5ece22ffa46d5ca3', 'EV-09ca5573406fa16b', 'EV-bfef5819e801be66', 'EV-6a99c02e933fe11b', 'EV-5b1890a70bf8109b', 'EV-9419dfe4ce1fb46e', 'EV-4baf725f280851a4']`
- **6. Remaining Unconfirmed Items**: `['Physical causation across distinct grid elements (no bus-branch topology model in telemetry)', 'Initiating actor or host process behind observed network frames']`

### Instance 05 (`C3_no_command_cross_rtu_verified_bridge`) — `02-Semiurban` / `ev_d3c46672f9814dcdc40c`
- **Category**: No control command, corroborated Cross-RTU Verified Element Bridges
- **Selection Rule**: Select one no-command `S2` window from each scenario (`01-Basic` `ev_564bebaa45f0686cf98d`, `02-Semiurban` `ev_d3c46672f9814dcdc40c`, `03-Rural` `ev_0d966f97d1922adb09bb`) where `verified_element_bridges > 0`.
- **1. Raw Observable Facts**:
  - Control transactions: `0` (unpaired control replies: `0`); Verified anchors: `94`; Quarantined unverified anchors: `125`
- **2. Baseline Relations**:
  - `B1_temporal_only`: `1310` candidate temporal links (`421` unsubstantiated candidates + `884` explicit constraint conflicts `{'endpoint_quality_or_test_bit_conflict': 0, 'endpoint_transient_not_sustained_conflict': 849, 'same_device_direction_or_ratio_conflict': 1, 'same_device_change_type_or_side_conflict': 16, 'same_asdu_co_report_temporal_ordering_conflict': 60}`; topology `{'cross_device_candidate_count': 1220, 'same_device_separate_asdu_candidate_count': 30, 'same_asdu_co_report_candidate_count': 60}`).
  - `B2_protocol_only`: `NOT_APPLICABLE_NO_CONTROL_COMMANDS`, `0` protocol storylines, `0` verified transitions; omits `94` verified behavioral anchors and `5` cross-RTU bridges.
- **3. Full MIRAGE-OT Relations**:
  - `report_status`: `quality_consistent` (`quality_consistency=True`, `lineage_consistency=True`)
  - `E3 Traceability (4 Levels)`: `{'1_evidence_citation_presence': True, '2_evidence_id_resolution': True, '3_evidence_to_fact_anchor_consistency': True, '4_full_lineage_consistency': True, 'synthesis_cited_evidence_id_count': 216, 'sqlite_unresolved_ids': [], 'timeline_row_check_failure_count': 0, 'behavioral_anchor_row_check_failure_count': 0}`
  - RTU ASDU Bundles: `80`; Cross-RTU Verified Element Bridges: `[('BRG-001', 'line.6', '172.16.7.7->172.16.7.1'), ('BRG-002', 'line.6', '172.16.7.7->172.16.7.1'), ('BRG-003', 'line.6', '172.16.7.1->172.16.7.7'), ('BRG-004', 'line.6', '172.16.7.1->172.16.7.7'), ('BRG-005', 'line.7', '172.16.7.7->172.16.7.12')]`
- **4. Methodological Differences**:
  - vs `B1`: B1 emits 1310 candidate temporal links (421 unsubstantiated cross-device/unverified candidates and 884 explicit quality/persistence/direction/same-ASDU conflicts); MIRAGE-OT keeps cross-device links unresolved and restricts supported bridges to 5.
  - vs `B2`: B2 is `NOT_APPLICABLE_NO_CONTROL_COMMANDS` and omits 94 verified behavioral anchors and 5 cross-RTU bridges.
  - vs `A1`: Counterfactual A1 promotes 25 unsupported relations ({'quality_or_test_bit_violation': 0, 'persistence_insufficient_violation': 13, 'prior_state_baseline_missing_violation': 0, 'change_type_mismatch_violation': 0, 'magnitude_or_direction_conflict_violation': 1, 'non_complementary_or_disjoint_interval_violation': 16}).
  - vs `A2`: Counterfactual A2 counts 344 raw observations vs 80 message/event containers: true_mirror=88, same_asdu_ioa=48, same_tcp_session_msgs=0, diff_time_anchor_events=0, ipal=128.
  - vs `A3`: Without Incident Synthesis, A3 outputs 216 local storylines without consolidating 80 ASDU bundles, 5 cross-RTU bridges, or 2 competing explanations.
- **5. Cited Evidence IDs**: `['EV-ca799306460047c5', 'EV-e2d519ce2f80c961', 'EV-96d101e95030427a', 'EV-d1bc9993aa5440f8', 'EV-2a7275c96212c5aa', 'EV-f240fe3395866802', 'EV-295aec80459a8036', 'EV-c9091214d4155501', 'EV-548ecb99ee9805ba', 'EV-9fabac9dde67aede', 'EV-3de66be3f916d3ef', 'EV-bccb807762548915', 'EV-602ef0f51c63d3d1', 'EV-2e32a79e963c2f15', 'EV-1937578581fc6b5e', 'EV-0042a3e4dbabdd08']`
- **6. Remaining Unconfirmed Items**: `['Physical causation across distinct grid elements (no bus-branch topology model in telemetry)', 'Initiating actor or host process behind observed network frames']`

### Instance 06 (`C3_no_command_cross_rtu_verified_bridge`) — `03-Rural` / `ev_0d966f97d1922adb09bb`
- **Category**: No control command, corroborated Cross-RTU Verified Element Bridges
- **Selection Rule**: Select one no-command `S2` window from each scenario (`01-Basic` `ev_564bebaa45f0686cf98d`, `02-Semiurban` `ev_d3c46672f9814dcdc40c`, `03-Rural` `ev_0d966f97d1922adb09bb`) where `verified_element_bridges > 0`.
- **1. Raw Observable Facts**:
  - Control transactions: `0` (unpaired control replies: `0`); Verified anchors: `114`; Quarantined unverified anchors: `73`
- **2. Baseline Relations**:
  - `B1_temporal_only`: `1131` candidate temporal links (`603` unsubstantiated candidates + `521` explicit constraint conflicts `{'endpoint_quality_or_test_bit_conflict': 0, 'endpoint_transient_not_sustained_conflict': 442, 'same_device_direction_or_ratio_conflict': 0, 'same_device_change_type_or_side_conflict': 26, 'same_asdu_co_report_temporal_ordering_conflict': 63}`; topology `{'cross_device_candidate_count': 1035, 'same_device_separate_asdu_candidate_count': 33, 'same_asdu_co_report_candidate_count': 63}`).
  - `B2_protocol_only`: `NOT_APPLICABLE_NO_CONTROL_COMMANDS`, `0` protocol storylines, `0` verified transitions; omits `114` verified behavioral anchors and `7` cross-RTU bridges.
- **3. Full MIRAGE-OT Relations**:
  - `report_status`: `quality_consistent` (`quality_consistency=True`, `lineage_consistency=True`)
  - `E3 Traceability (4 Levels)`: `{'1_evidence_citation_presence': True, '2_evidence_id_resolution': True, '3_evidence_to_fact_anchor_consistency': True, '4_full_lineage_consistency': True, 'synthesis_cited_evidence_id_count': 316, 'sqlite_unresolved_ids': [], 'timeline_row_check_failure_count': 0, 'behavioral_anchor_row_check_failure_count': 0}`
  - RTU ASDU Bundles: `86`; Cross-RTU Verified Element Bridges: `[('BRG-001', 'line.57', '172.16.9.8->172.16.9.7'), ('BRG-002', 'line.57', '172.16.9.8->172.16.9.7'), ('BRG-003', 'line.57', '172.16.9.8->172.16.9.7'), ('BRG-004', 'line.100', '172.16.11.3->172.16.11.1'), ('BRG-005', 'line.98', '172.16.11.2->172.16.10.1'), ('BRG-006', 'line.56', '172.16.9.6->172.16.9.7'), ('BRG-007', 'line.56', '172.16.9.6->172.16.9.7')]`
- **4. Methodological Differences**:
  - vs `B1`: B1 emits 1131 candidate temporal links (603 unsubstantiated cross-device/unverified candidates and 521 explicit quality/persistence/direction/same-ASDU conflicts); MIRAGE-OT keeps cross-device links unresolved and restricts supported bridges to 7.
  - vs `B2`: B2 is `NOT_APPLICABLE_NO_CONTROL_COMMANDS` and omits 114 verified behavioral anchors and 7 cross-RTU bridges.
  - vs `A1`: Counterfactual A1 promotes 26 unsupported relations ({'quality_or_test_bit_violation': 0, 'persistence_insufficient_violation': 1, 'prior_state_baseline_missing_violation': 0, 'change_type_mismatch_violation': 0, 'magnitude_or_direction_conflict_violation': 0, 'non_complementary_or_disjoint_interval_violation': 26}).
  - vs `A2`: Counterfactual A2 counts 498 raw observations vs 86 message/event containers: true_mirror=134, same_asdu_ioa=96, same_tcp_session_msgs=0, diff_time_anchor_events=0, ipal=182.
  - vs `A3`: Without Incident Synthesis, A3 outputs 183 local storylines without consolidating 86 ASDU bundles, 7 cross-RTU bridges, or 2 competing explanations.
- **5. Cited Evidence IDs**: `['EV-83de42bd94e2a7ca', 'EV-e0bb812cbbd92c5a', 'EV-49e6cd8b18ebc8b7', 'EV-38a2d0b85cd4f125', 'EV-da5bd99c5a6fa7c8', 'EV-6afc3a562208d1b1', 'EV-1a23285701b08127', 'EV-34f8a65dc2d6481d', 'EV-89c1731670ffafd4', 'EV-f667390311e9f926', 'EV-fca909efbf50b967', 'EV-84f063a1f9bd8ee9', 'EV-64088f30d933a8d5', 'EV-9dc44b64daec1e6b', 'EV-5c8b44acf41cb48a', 'EV-c23466acb2a086e7']`
- **6. Remaining Unconfirmed Items**: `['Physical causation across distinct grid elements (no bus-branch topology model in telemetry)', 'Initiating actor or host process behind observed network frames']`

### Instance 07 (`C4_arp_and_iec104_link_disruption_uncertain_causality`) — `01-Basic` / `ev_cbe1e5bef23346604396`
- **Category**: ARP burst and IEC-104 link disruptions with per-target precedence filtering, multi-event provenance separation, and uncertain causality
- **Selection Rule**: Select `01-Basic` window `ev_cbe1e5bef23346604396`, where ARP traffic from `172.16.3.28` precedes link loss on RTUs `172.16.3.10` and `172.16.3.9` within 15s (while first ARP to `172.16.3.20` occurs 37.7s after its link change), and where `communication_change` anchors aggregate distinct-time SYN/FIN events (`true_cross_vantage_mirror_duplicate_count = 0`).
- **1. Raw Observable Facts**:
  - Control transactions: `0` (unpaired control replies: `0`); Verified anchors: `4`; Quarantined unverified anchors: `3`
- **2. Baseline Relations**:
  - `B1_temporal_only`: `7` candidate temporal links (`6` unsubstantiated candidates + `1` explicit constraint conflicts `{'endpoint_quality_or_test_bit_conflict': 0, 'endpoint_transient_not_sustained_conflict': 1, 'same_device_direction_or_ratio_conflict': 0, 'same_device_change_type_or_side_conflict': 0, 'same_asdu_co_report_temporal_ordering_conflict': 0}`; topology `{'cross_device_candidate_count': 7, 'same_device_separate_asdu_candidate_count': 0, 'same_asdu_co_report_candidate_count': 0}`).
  - `B2_protocol_only`: `NOT_APPLICABLE_NO_CONTROL_COMMANDS`, `0` protocol storylines, `0` verified transitions; omits `4` verified behavioral anchors and `0` cross-RTU bridges.
- **3. Full MIRAGE-OT Relations**:
  - `report_status`: `quality_consistent` (`quality_consistency=True`, `lineage_consistency=True`)
  - `E3 Traceability (4 Levels)`: `{'1_evidence_citation_presence': True, '2_evidence_id_resolution': True, '3_evidence_to_fact_anchor_consistency': True, '4_full_lineage_consistency': True, 'synthesis_cited_evidence_id_count': 43, 'sqlite_unresolved_ids': [], 'timeline_row_check_failure_count': 0, 'behavioral_anchor_row_check_failure_count': 0}`
  - RTU ASDU Bundles: `4`; Cross-RTU Verified Element Bridges: `[]`
- **4. Methodological Differences**:
  - vs `B1`: B1 emits 7 candidate temporal links (6 unsubstantiated cross-device/unverified candidates and 1 explicit quality/persistence/direction/same-ASDU conflicts); MIRAGE-OT keeps cross-device links unresolved and restricts supported bridges to 0.
  - vs `B2`: B2 is `NOT_APPLICABLE_NO_CONTROL_COMMANDS` and omits 4 verified behavioral anchors and 0 cross-RTU bridges.
  - vs `A1`: Counterfactual A1 promotes 0 unsupported relations ({'quality_or_test_bit_violation': 0, 'persistence_insufficient_violation': 0, 'prior_state_baseline_missing_violation': 0, 'change_type_mismatch_violation': 0, 'magnitude_or_direction_conflict_violation': 0, 'non_complementary_or_disjoint_interval_violation': 0}).
  - vs `A2`: Counterfactual A2 counts 43 raw observations vs 4 message/event containers: true_mirror=0, same_asdu_ioa=0, same_tcp_session_msgs=20, diff_time_anchor_events=19, ipal=0.
  - vs `A3`: Without Incident Synthesis, A3 outputs 7 local storylines without consolidating 4 ASDU bundles, 0 cross-RTU bridges, or 2 competing explanations.
- **5. Cited Evidence IDs**: `['EV-0e9f6fb66f6907e4', 'EV-dd59c3d758762e69', 'EV-06a22bddc2cd3bee', 'EV-79fef36709e79d8b', 'EV-43c669e3989a2cb9', 'EV-4f94ff12f644b2ff', 'EV-f0d746d67fdd2fa4', 'EV-a19b67117ff1dbe7']`
- **6. Remaining Unconfirmed Items**: `['Physical causation across distinct grid elements (no bus-branch topology model in telemetry)', 'Initiating actor or host process behind observed network frames']`

### Instance 08 (`C5_multi_vantage_payload_conflict`) — `01-Basic` / `ev_52f5eee28f8b95e702fd`
- **Category**: Multi-vantage mirror payload conflicts quarantined from supported spines
- **Selection Rule**: Select `01-Basic` window `ev_52f5eee28f8b95e702fd`, which exhibits 240 `post_cross_vantage_payload_conflict` and 236 `pre_cross_vantage_payload_conflict` anchor issues across mirror vantages.
- **1. Raw Observable Facts**:
  - Control transactions: `0` (unpaired control replies: `0`); Verified anchors: `4`; Quarantined unverified anchors: `671`
- **2. Baseline Relations**:
  - `B1_temporal_only`: `6930` candidate temporal links (`2` unsubstantiated candidates + `6928` explicit constraint conflicts `{'endpoint_quality_or_test_bit_conflict': 4530, 'endpoint_transient_not_sustained_conflict': 6928, 'same_device_direction_or_ratio_conflict': 0, 'same_device_change_type_or_side_conflict': 1786, 'same_asdu_co_report_temporal_ordering_conflict': 966}`; topology `{'cross_device_candidate_count': 3998, 'same_device_separate_asdu_candidate_count': 1966, 'same_asdu_co_report_candidate_count': 966}`).
  - `B2_protocol_only`: `NOT_APPLICABLE_NO_CONTROL_COMMANDS`, `0` protocol storylines, `0` verified transitions; omits `4` verified behavioral anchors and `0` cross-RTU bridges.
- **3. Full MIRAGE-OT Relations**:
  - `report_status`: `quality_consistent` (`quality_consistency=True`, `lineage_consistency=True`)
  - `E3 Traceability (4 Levels)`: `{'1_evidence_citation_presence': True, '2_evidence_id_resolution': True, '3_evidence_to_fact_anchor_consistency': True, '4_full_lineage_consistency': True, 'synthesis_cited_evidence_id_count': 30, 'sqlite_unresolved_ids': [], 'timeline_row_check_failure_count': 0, 'behavioral_anchor_row_check_failure_count': 0}`
  - RTU ASDU Bundles: `4`; Cross-RTU Verified Element Bridges: `[]`
- **4. Methodological Differences**:
  - vs `B1`: B1 emits 6930 candidate temporal links (2 unsubstantiated cross-device/unverified candidates and 6928 explicit quality/persistence/direction/same-ASDU conflicts); MIRAGE-OT keeps cross-device links unresolved and restricts supported bridges to 0.
  - vs `B2`: B2 is `NOT_APPLICABLE_NO_CONTROL_COMMANDS` and omits 4 verified behavioral anchors and 0 cross-RTU bridges.
  - vs `A1`: Counterfactual A1 promotes 1966 unsupported relations ({'quality_or_test_bit_violation': 1318, 'persistence_insufficient_violation': 1966, 'prior_state_baseline_missing_violation': 0, 'change_type_mismatch_violation': 180, 'magnitude_or_direction_conflict_violation': 0, 'non_complementary_or_disjoint_interval_violation': 1843}).
  - vs `A2`: Counterfactual A2 counts 31 raw observations vs 4 message/event containers: true_mirror=3, same_asdu_ioa=2, same_tcp_session_msgs=0, diff_time_anchor_events=18, ipal=4.
  - vs `A3`: Without Incident Synthesis, A3 outputs 675 local storylines without consolidating 4 ASDU bundles, 0 cross-RTU bridges, or 2 competing explanations.
- **5. Cited Evidence IDs**: `['EV-6f3a914c20272ca8', 'EV-61547e835af4a3ca', 'EV-6922926db75760aa', 'EV-ef47051ed970f5b7', 'EV-dc141233bb171ebd', 'EV-c243276e252c1fe3', 'EV-3a8ee6bdd2843d26', 'EV-ee92af90f15168a1', 'EV-820989a947a979bc', 'EV-30c2665e86953e3f']`
- **6. Remaining Unconfirmed Items**: `['Physical causation across distinct grid elements (no bus-branch topology model in telemetry)', 'Initiating actor or host process behind observed network frames']`

### Instance 09 (`C6_lineage_consistency_failure_diagnostic_downgrade`) — `02-Semiurban` / `ev_5dd0102bf58bf2ce9487`
- **Category**: Lineage consistency failure automatically downgrading final report to Diagnostic Only (also the 46th window with unpaired COT=7 objects)
- **Selection Rule**: Select `02-Semiurban` window `ev_5dd0102bf58bf2ce9487`, the single window in the 103-window suite where `lineage_consistency.json` flags `time_outside_cited_sample` on `A007` (`EV-6e9e7ece8bf456f0`), and which also contains 62 unpaired `COT=7` replies without a matching `COT=6` command.
- **1. Raw Observable Facts**:
  - Control transactions: `0` (unpaired control replies: `62`); Verified anchors: `119`; Quarantined unverified anchors: `121`
- **2. Baseline Relations**:
  - `B1_temporal_only`: `1468` candidate temporal links (`550` unsubstantiated candidates + `907` explicit constraint conflicts `{'endpoint_quality_or_test_bit_conflict': 0, 'endpoint_transient_not_sustained_conflict': 879, 'same_device_direction_or_ratio_conflict': 2, 'same_device_change_type_or_side_conflict': 14, 'same_asdu_co_report_temporal_ordering_conflict': 84}`; topology `{'cross_device_candidate_count': 1354, 'same_device_separate_asdu_candidate_count': 30, 'same_asdu_co_report_candidate_count': 84}`).
  - `B2_protocol_only`: `APPLICABLE_CONTROL_COMMAND_WINDOW`, `0` protocol storylines, `0` verified transitions; omits `119` verified behavioral anchors and `0` cross-RTU bridges.
- **3. Full MIRAGE-OT Relations**:
  - `report_status`: `diagnostic_only_lineage_inconsistent` (`quality_consistency=True`, `lineage_consistency=False`)
  - `E3 Traceability (4 Levels)`: `{'1_evidence_citation_presence': True, '2_evidence_id_resolution': True, '3_evidence_to_fact_anchor_consistency': False, '4_full_lineage_consistency': False, 'synthesis_cited_evidence_id_count': 273, 'sqlite_unresolved_ids': [], 'timeline_row_check_failure_count': 0, 'behavioral_anchor_row_check_failure_count': 1}`
  - RTU ASDU Bundles: `95`; Cross-RTU Verified Element Bridges: `[]`
- **4. Methodological Differences**:
  - vs `B1`: B1 emits 1468 candidate temporal links (550 unsubstantiated cross-device/unverified candidates and 907 explicit quality/persistence/direction/same-ASDU conflicts); MIRAGE-OT keeps cross-device links unresolved and restricts supported bridges to 0.
  - vs `B2`: B2 is `APPLICABLE_CONTROL_COMMAND_WINDOW` and omits 119 verified behavioral anchors and 0 cross-RTU bridges.
  - vs `A1`: Counterfactual A1 promotes 19 unsupported relations ({'quality_or_test_bit_violation': 0, 'persistence_insufficient_violation': 15, 'prior_state_baseline_missing_violation': 0, 'change_type_mismatch_violation': 3, 'magnitude_or_direction_conflict_violation': 1, 'non_complementary_or_disjoint_interval_violation': 12}).
  - vs `A2`: Counterfactual A2 counts 448 raw observations vs 95 message/event containers: true_mirror=86, same_asdu_ioa=85, same_tcp_session_msgs=3, diff_time_anchor_events=0, ipal=179.
  - vs `A3`: Without Incident Synthesis, A3 outputs 231 local storylines without consolidating 95 ASDU bundles, 0 cross-RTU bridges, or 4 competing explanations.
- **5. Cited Evidence IDs**: `['EV-242533da5141d071', 'EV-fb8fbf3a69024939', 'EV-815682f7635b2589', 'EV-6e9e7ece8bf456f0', 'EV-88f73588781b6263', 'EV-c3b7fa57049aced8', 'EV-ebc43dcb2fdacb91', 'EV-be2907a10928b50b', 'EV-ba723003a68b8c08', 'EV-82dac0a8871bbc86', 'EV-02497bc7a91653d5', 'EV-77d0a290d587c609', 'EV-434cd4e06b8d0d97', 'EV-ff04deff30cd68df', 'EV-2465843b09957f98']`
- **6. Remaining Unconfirmed Items**: `['Physical causation across distinct grid elements (no bus-branch topology model in telemetry)', 'Initiating actor or host process behind observed network frames']`

### Instance 10 (`C7_low_information_honest_abstention`) — `01-Basic` / `ev_d58f418ff4f085ccc0a7`
- **Category**: Honest abstention in low-information periodic-measurement-only windows
- **Selection Rule**: Select `01-Basic` window `ev_d58f418ff4f085ccc0a7` and `02-Semiurban` window `ev_8e3ee44aec0a0f81c99a`, where only periodic `M_ME_NC_1 (COT=1)` telemetry and transient oscillations occur.
- **1. Raw Observable Facts**:
  - Control transactions: `0` (unpaired control replies: `0`); Verified anchors: `0`; Quarantined unverified anchors: `14`
- **2. Baseline Relations**:
  - `B1_temporal_only`: `4` candidate temporal links (`0` unsubstantiated candidates + `4` explicit constraint conflicts `{'endpoint_quality_or_test_bit_conflict': 0, 'endpoint_transient_not_sustained_conflict': 4, 'same_device_direction_or_ratio_conflict': 1, 'same_device_change_type_or_side_conflict': 0, 'same_asdu_co_report_temporal_ordering_conflict': 0}`; topology `{'cross_device_candidate_count': 2, 'same_device_separate_asdu_candidate_count': 2, 'same_asdu_co_report_candidate_count': 0}`).
  - `B2_protocol_only`: `NOT_APPLICABLE_NO_CONTROL_COMMANDS`, `0` protocol storylines, `0` verified transitions; omits `0` verified behavioral anchors and `0` cross-RTU bridges.
- **3. Full MIRAGE-OT Relations**:
  - `report_status`: `quality_consistent` (`quality_consistency=True`, `lineage_consistency=True`)
  - `E3 Traceability (4 Levels)`: `{'1_evidence_citation_presence': True, '2_evidence_id_resolution': True, '3_evidence_to_fact_anchor_consistency': True, '4_full_lineage_consistency': True, 'synthesis_cited_evidence_id_count': 4, 'sqlite_unresolved_ids': [], 'timeline_row_check_failure_count': 0, 'behavioral_anchor_row_check_failure_count': 0}`
  - RTU ASDU Bundles: `0`; Cross-RTU Verified Element Bridges: `[]`
- **4. Methodological Differences**:
  - vs `B1`: B1 emits 4 candidate temporal links (0 unsubstantiated cross-device/unverified candidates and 4 explicit quality/persistence/direction/same-ASDU conflicts); MIRAGE-OT keeps cross-device links unresolved and restricts supported bridges to 0.
  - vs `B2`: B2 is `NOT_APPLICABLE_NO_CONTROL_COMMANDS` and omits 0 verified behavioral anchors and 0 cross-RTU bridges.
  - vs `A1`: Counterfactual A1 promotes 2 unsupported relations ({'quality_or_test_bit_violation': 0, 'persistence_insufficient_violation': 2, 'prior_state_baseline_missing_violation': 0, 'change_type_mismatch_violation': 0, 'magnitude_or_direction_conflict_violation': 1, 'non_complementary_or_disjoint_interval_violation': 2}).
  - vs `A2`: Counterfactual A2 counts 0 raw observations vs 0 message/event containers: true_mirror=0, same_asdu_ioa=0, same_tcp_session_msgs=0, diff_time_anchor_events=0, ipal=0.
  - vs `A3`: Without Incident Synthesis, A3 outputs 14 local storylines without consolidating 0 ASDU bundles, 0 cross-RTU bridges, or 2 competing explanations.
- **5. Cited Evidence IDs**: `['EV-42943a48737cbcab', 'EV-12d0e000a2c6bd1a', 'EV-c5a1d0edc1f56808', 'EV-ce3ffd677fa3c9cc', 'EV-37b12ca1ac085502']`
- **6. Remaining Unconfirmed Items**: `['Physical causation across distinct grid elements (no bus-branch topology model in telemetry)', 'Initiating actor or host process behind observed network frames']`

### Instance 11 (`C7_low_information_honest_abstention`) — `02-Semiurban` / `ev_8e3ee44aec0a0f81c99a`
- **Category**: Honest abstention in low-information periodic-measurement-only windows
- **Selection Rule**: Select `01-Basic` window `ev_d58f418ff4f085ccc0a7` and `02-Semiurban` window `ev_8e3ee44aec0a0f81c99a`, where only periodic `M_ME_NC_1 (COT=1)` telemetry and transient oscillations occur.
- **1. Raw Observable Facts**:
  - Control transactions: `0` (unpaired control replies: `0`); Verified anchors: `0`; Quarantined unverified anchors: `20`
- **2. Baseline Relations**:
  - `B1_temporal_only`: `13` candidate temporal links (`0` unsubstantiated candidates + `13` explicit constraint conflicts `{'endpoint_quality_or_test_bit_conflict': 0, 'endpoint_transient_not_sustained_conflict': 13, 'same_device_direction_or_ratio_conflict': 1, 'same_device_change_type_or_side_conflict': 0, 'same_asdu_co_report_temporal_ordering_conflict': 0}`; topology `{'cross_device_candidate_count': 12, 'same_device_separate_asdu_candidate_count': 1, 'same_asdu_co_report_candidate_count': 0}`).
  - `B2_protocol_only`: `NOT_APPLICABLE_NO_CONTROL_COMMANDS`, `0` protocol storylines, `0` verified transitions; omits `0` verified behavioral anchors and `0` cross-RTU bridges.
- **3. Full MIRAGE-OT Relations**:
  - `report_status`: `quality_consistent` (`quality_consistency=True`, `lineage_consistency=True`)
  - `E3 Traceability (4 Levels)`: `{'1_evidence_citation_presence': True, '2_evidence_id_resolution': True, '3_evidence_to_fact_anchor_consistency': True, '4_full_lineage_consistency': True, 'synthesis_cited_evidence_id_count': 4, 'sqlite_unresolved_ids': [], 'timeline_row_check_failure_count': 0, 'behavioral_anchor_row_check_failure_count': 0}`
  - RTU ASDU Bundles: `0`; Cross-RTU Verified Element Bridges: `[]`
- **4. Methodological Differences**:
  - vs `B1`: B1 emits 13 candidate temporal links (0 unsubstantiated cross-device/unverified candidates and 13 explicit quality/persistence/direction/same-ASDU conflicts); MIRAGE-OT keeps cross-device links unresolved and restricts supported bridges to 0.
  - vs `B2`: B2 is `NOT_APPLICABLE_NO_CONTROL_COMMANDS` and omits 0 verified behavioral anchors and 0 cross-RTU bridges.
  - vs `A1`: Counterfactual A1 promotes 1 unsupported relations ({'quality_or_test_bit_violation': 0, 'persistence_insufficient_violation': 1, 'prior_state_baseline_missing_violation': 0, 'change_type_mismatch_violation': 0, 'magnitude_or_direction_conflict_violation': 1, 'non_complementary_or_disjoint_interval_violation': 0}).
  - vs `A2`: Counterfactual A2 counts 0 raw observations vs 0 message/event containers: true_mirror=0, same_asdu_ioa=0, same_tcp_session_msgs=0, diff_time_anchor_events=0, ipal=0.
  - vs `A3`: Without Incident Synthesis, A3 outputs 20 local storylines without consolidating 0 ASDU bundles, 0 cross-RTU bridges, or 2 competing explanations.
- **5. Cited Evidence IDs**: `['EV-23a0be9000ba4c8e', 'EV-5567a8cd1fa3e806', 'EV-d31e1798d784fe7f', 'EV-6c70c4696b372a69', 'EV-b22fde6d085aa45f', 'EV-986f1fc1f38e2249']`
- **6. Remaining Unconfirmed Items**: `['Physical causation across distinct grid elements (no bus-branch topology model in telemetry)', 'Initiating actor or host process behind observed network frames']`

---

## 5. Four Synthetic Known-Answer Counterexamples (Reported Separately from Sherlock)

- **`S_KA1_test_bit_and_opposing_direction`** (`passed_known_answer = True`): `line.1:active_power_from` (RTU .11) increases 100->300, whereas `line.1:active_power_to` (RTU .12) decreases in magnitude |-100|->|-40| and has COT test bit `T=1` at the step sample. Must be flagged as `explicit_evidence_constraint_conflict` in B1 and rejected from bridges in MIRAGE-OT. Details: `{'B1_temporal_only_candidates': 1, 'B1_explicit_constraint_conflicts': 1, 'A1_ungated_unsupported_promotions': 1, 'MIRAGE_OT_supported_bridges': 0, 'MIRAGE_OT_sequential_rejected': 1, 'passed_known_answer': True}`.
- **`S_KA2_mirror_and_same_asdu_and_ipal_duplication`** (`passed_known_answer = True`): One ASDU (`apci_tx=31`) from RTU `172.16.3.18` carries two objects (`bus.5` and `load.3`), is mirrored at two vantages (`n302` and `n318`, 4 packet objects: 1 primary + 1 same-ASDU diff IOA + 2 true cross-vantage mirrors), and produces 2 IPAL rows (6 raw observations total). True container count is 1. Details: `{'A2_naive_raw_observation_count': 6, 'A2_true_cross_vantage_mirror_duplicate_count': 2, 'A2_same_asdu_different_ioa_point_count': 1, 'A2_ipal_derived_count': 2, 'MIRAGE_OT_distinct_source_container_count': 1, 'passed_known_answer': True}`.
- **`S_KA3_unverified_switch_vs_verified_cross_rtu_line_bridge`** (`passed_known_answer = True`): Unverified `switch.99:is_closed=0` (no prior baseline) occurs 4s before `line.4` drops to zero at both `to` (RTU .18) and `from` (RTU .22) ends. The 2 cross-device links from `switch.99` are `unsubstantiated_temporal_candidates` (not proven false conflicts), while `line.4` (`to` <-> `from`) is 1 `corroborated_same_device_candidate` forming 1 Cross-RTU Bridge. Details: `{'B1_temporal_only_candidates': 3, 'B1_unsubstantiated_candidates': 2, 'B1_explicit_constraint_conflicts': 0, 'B1_corroborated_same_device_candidates': 1, 'MIRAGE_OT_verified_bridges': ['line.4'], 'MIRAGE_OT_unresolved_branches': 2, 'passed_known_answer': True}`.
- **`S_KA4_communication_anchor_multi_event_not_mirror_duplicate`** (`passed_known_answer = True`): A `communication_change` anchor on `n302` cites 4 TCP packets at different times across 3 ephemeral sessions (`56094` FIN, `56736` two SYN retries, `56752` SYN). Because all 4 packets are on `n302` at different times, `true_cross_vantage_mirror_duplicate_count` must be 0, with 1 `distinct_messages_in_same_tcp_session_count` and 2 `distinct_time_network_events_in_anchor_count`. Details: `{'A2_true_cross_vantage_mirror_duplicate_count': 0, 'A2_distinct_messages_in_same_tcp_session_count': 1, 'A2_distinct_time_network_events_in_anchor_count': 2, 'passed_known_answer': True}`.
