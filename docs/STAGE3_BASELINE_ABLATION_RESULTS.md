# Stage 3 Baseline & Ablation Experimental Results (All 103 Sherlock v3 Test Windows)

- **Frozen Engine Commit (`git_commit`)**: `2981fb062b127218a34f23f2ff0292e4ca8cfea7`
- **Reconstruction Code Hash (`code_sha256`)**: `d43d9867ce847df169e13345e4c3461cd99fd5167292a85cedaaa553d93e5bb3`
- **Evidence Layer Code Hash (`evidence_code_sha256`)**: `032c6977ac0507e9c442b37e4e78455d0ab6d1a21b1efe751a0ccf37242a3b85`
- **Windows Evaluated**: `103 / 103` (`28` `01-Basic`, `39` `02-Semiurban`, `36` `03-Rural`)
- **Stage 3A Pilot Summary**: `runs/etgi/stage3-baseline-ablation-20261015/stage3a_pilot_summary.json` (12 stratified windows)
- **Stage 3B Full Summary**: `runs/etgi/stage3-baseline-ablation-20261015/stage3b_full_summary.json` (103 windows)

---

## 1. Quantitative Answers to the Five Stage 3 Research Questions (103 Windows)

All cell values below are formatted as **`Total` (`Mean` / `Median` / `P95` / `Max`)** across windows.

### 1.1 RQ1 — Baseline B1 (`Temporal-Only Reconstruction`) vs. Full MIRAGE-OT

| Metric (`Total (Mean / Med / P95 / Max)`) | `01-Basic` (`N=28`) | `02-Semiurban` (`N=39`) | `03-Rural` (`N=36`) | All 103 Windows (`N=103`) |
| --- | --- | --- | --- | --- |
| **B1 Unbounded 15s Temporal Pairs** | `43,880` (`1567.143` / `23.5` / `10116.0` / `21575`) | `244,745` (`6275.513` / `2594.0` / `19752.0` / `37537`) | `110,707` (`3075.194` / `2254.5` / `10745.0` / `11920`) | **`399,332` (`3877.01` / `381.0` / `17631.0` / `37537`)** |
| **B1 Bounded Candidate Temporal Relations** | `22,632` (`808.286` / `22.5` / `5273.0` / `6930`) | `50,750` (`1301.282` / `580.0` / `4632.0` / `8091`) | `34,284` (`952.333` / `572.5` / `2823.0` / `3796`) | **`107,666` (`1045.301` / `192.0` / `3796.0` / `8091`)** |
| **B1 Conflicting / Unsupported Candidates (Any Violation)** | `15,322` (`547.214` / `22.0` / `2395.0` / `6930`) | `45,710` (`1172.051` / `580.0` / `4072.0` / `6522`) | `23,804` (`661.222` / `462.5` / `2436.0` / `2711`) | **`84,836` (`823.65` / `152.0` / `3587.0` / `6930`)** |
| — Lacking Device / Session Support (Cross-Device) | `12,188` (`435.286` / `20.5` / `2150.0` / `4964`) | `44,921` (`1151.821` / `580.0` / `3716.0` / `6485`) | `23,672` (`657.556` / `453.5` / `2436.0` / `2710`) | `80,781` (`784.282` / `145.0` / `3524.0` / `6485`) |
| — Transient / Not Sustained in Later Samples | `11,957` (`427.036` / `4.5` / `2342.0` / `6929`) | `36,138` (`926.615` / `160.0` / `3754.0` / `5176`) | `18,030` (`500.833` / `153.0` / `2136.0` / `2418`) | `66,125` (`641.99` / `54.0` / `3210.0` / `6929`) |
| — Endpoint Quality / Test-Bit / Vantage Conflict | `7,085` (`253.036` / `0.0` / `1396.0` / `4530`) | `1,404` (`36.0` / `0.0` / `201.0` / `1198`) | `0` (`0.0` / `0.0` / `0.0` / `0`) | `8,489` (`82.417` / `0.0` / `5.0` / `4530`) |
| — Same-Device Direction or Change-Type Conflict | `2,934` (`104.786` / `0.5` / `575.0` / `1786`) | `698` (`17.897` / `1.0` / `37.0` / `547`) | `108` (`3.0` / `0.0` / `26.0` / `28`) | `3,740` (`36.311` / `1.0` / `28.0` / `1786`) |
| — Same-ASDU Co-Report Chained as Sequence | `1,565` (`55.893` / `0.0` / `364.0` / `966`) | `727` (`18.641` / `7.0` / `84.0` / `123`) | `336` (`9.333` / `2.5` / `63.0` / `95`) | `2,628` (`25.515` / `3.0` / `84.0` / `966`) |
| **MIRAGE-OT Supported Storyline Steps** | `521` (`18.607` / `7.0` / `89.0` / `183`) | `450` (`11.538` / `0.0` / `89.0` / `177`) | `598` (`16.611` / `0.0` / `89.0` / `185`) | **`1,569` (`15.233` / `2.0` / `89.0` / `185`)** |
| **MIRAGE-OT Cross-RTU Verified Element Bridges** | `6` (`0.214` / `0.0` / `1.0` / `5`) | `6` (`0.154` / `0.0` / `1.0` / `5`) | `11` (`0.306` / `0.0` / `4.0` / `7`) | **`23` (`0.223` / `0.0` / `1.0` / `7`)** |

- **Window-Paired Difference (`B1 Conflicting Candidates - MIRAGE-OT Unsupported Promotions`)**: Mean difference **`823.65` per window** (Bootstrap 95% CI **`[588.63, 1,081.04]`**, Median `152.0`, `94 / 103` windows with B1 > MIRAGE-OT, `9` tied at 0, `0` with MIRAGE-OT > B1).

---

### 1.2 RQ2 — Baseline B2 (`Protocol-Only Reconstruction`) vs. Full MIRAGE-OT

| Metric | `01-Basic` (`N=28`) | `02-Semiurban` (`N=39`) | `03-Rural` (`N=36`) | All 103 Windows (`N=103`) |
| --- | --- | --- | --- | --- |
| **Control-Command Windows (`Applicable`)** | `16` (`57.1%`) | `16` (`41.0%`) | `14` (`38.9%`) | **`46` (`44.66%`)** |
| **No-Command Windows (`Not Applicable`)** | `12` (`42.9%`) | `23` (`59.0%`) | `22` (`61.1%`) | **`57` (`55.34%`)** |
| **B2 Info Retained in No-Command Windows** | `0` across all 12 | `0` across all 23 | `0` across all 22 | **`0` across all 57** |
| **B2 Verified Command Transitions** | `9` (`0.321` / `0.0` / `2.0` / `3`) | `3` (`0.077` / `0.0` / `1.0` / `1`) | `3` (`0.083` / `0.0` / `1.0` / `1`) | **`15` (`0.146` / `0.0` / `1.0` / `3`)** |
| **Omitted Verified Non-Command Anchors** | `153` (`5.464` / `3.5` / `18.0` / `23`) | `1,557` (`39.923` / `30.0` / `119.0` / `122`) | `1,066` (`29.611` / `16.5` / `114.0` / `117`) | **`2,776` (`26.951` / `11.0` / `94.0` / `122`)** |
| **Omitted Supported Behavioral Chains** | `6` (`0.214` / `0.0` / `1.0` / `5`) | `12` (`0.308` / `0.0` / `2.0` / `9`) | `8` (`0.222` / `0.0` / `4.0` / `4`) | **`26` (`0.252` / `0.0` / `1.0` / `9`)** |
| **Omitted Cross-RTU Verified Bridges** | `6` (`0.214` / `0.0` / `1.0` / `5`) | `6` (`0.154` / `0.0` / `1.0` / `5`) | `11` (`0.306` / `0.0` / `4.0` / `7`) | **`23` (`0.223` / `0.0` / `1.0` / `7`)** |
| **Unexpressible Network Anomalies (ARP / Link)** | `37` (`1.321` / `0.0` / `7.0` / `7`) | `44` (`1.128` / `0.0` / `5.0` / `7`) | `53` (`1.472` / `1.0` / `5.0` / `6`) | **`134` (`1.301` / `0.0` / `5.0` / `7`)** |

---

### 1.3 RQ3 — Ablation A1 (`Without Behavioral Consistency Gate`) vs. Full MIRAGE-OT

| Metric (`Total (Mean / Med / P95 / Max)`) | `01-Basic` (`N=28`) | `02-Semiurban` (`N=39`) | `03-Rural` (`N=36`) | All 103 Windows (`N=103`) |
| --- | --- | --- | --- | --- |
| **Originally Supported Relations (Gate Passed)** | `21` (`0.75` / `0.0` / `5.0` / `6`) | `23` (`0.59` / `0.0` / `5.0` / `11`) | `17` (`0.472` / `0.0` / `4.0` / `7`) | **`61` (`0.592` / `0.0` / `4.0` / `11`)** |
| **Unsupported Promotions Blocked by Gate (`Total`)** | `2,032` (`72.571` / `1.0` / `20.0` / `1966`) | `85` (`2.179` / `1.0` / `19.0` / `25`) | `54` (`1.5` / `0.0` / `6.0` / `26`) | **`2,171` (`21.078` / `1.0` / `18.0` / `1966`)** |
| — Behavioral Same-Device Promotions Blocked | `1,976` (`70.571` / `0.0` / `3.0` / `1966`) | `71` (`1.821` / `0.0` / `19.0` / `25`) | `45` (`1.25` / `0.0` / `6.0` / `26`) | `2,092` (`20.311` / `0.0` / `6.0` / `1966`) |
| — Command-to-Effect Promotions Blocked | `56` (`2.0` / `0.0` / `18.0` / `20`) | `14` (`0.359` / `0.0` / `3.0` / `4`) | `9` (`0.25` / `0.0` / `2.0` / `3`) | `79` (`0.767` / `0.0` / `3.0` / `20`) |
| **Spurious Cross-RTU Bridges Blocked by Gate** | `368` (`13.143` / `0.0` / `3.0` / `360`) | `31` (`0.795` / `0.0` / `10.0` / `15`) | `10` (`0.278` / `0.0` / `2.0` / `2`) | **`409` (`3.971` / `0.0` / `2.0` / `360`)** |
| **Violation: Persistence Insufficient** | `1,973` (`70.464` / `0.0` / `2.0` / `1966`) | `49` (`1.256` / `0.0` / `13.0` / `15`) | `13` (`0.361` / `0.0` / `2.0` / `5`) | `2,035` (`19.757` / `0.0` / `5.0` / `1966`) |
| **Violation: Non-Complementary / Disjoint Interval** | `1,845` (`65.893` / `0.0` / `2.0` / `1843`) | `49` (`1.256` / `0.0` / `12.0` / `16`) | `36` (`1.0` / `0.0` / `4.0` / `26`) | `1,930` (`18.738` / `0.0` / `4.0` / `1843`) |
| **Violation: Quality / Test-Bit / Vantage Conflict** | `1,333` (`47.607` / `0.0` / `3.0` / `1318`) | `15` (`0.385` / `0.0` / `3.0` / `4`) | `9` (`0.25` / `0.0` / `2.0` / `3`) | `1,357` (`13.175` / `0.0` / `3.0` / `1318`) |
| **Violation: Change-Type Mismatch** | `184` (`6.571` / `0.0` / `1.0` / `180`) | `3` (`0.077` / `0.0` / `0.0` / `3`) | `3` (`0.083` / `0.0` / `1.0` / `2`) | `190` (`1.845` / `0.0` / `1.0` / `180`) |
| **Violation: Prior State Baseline Missing** | `58` (`2.071` / `0.5` / `18.0` / `20`) | `15` (`0.385` / `0.0` / `3.0` / `4`) | `10` (`0.278` / `0.0` / `2.0` / `3`) | `83` (`0.806` / `0.0` / `3.0` / `20`) |
| **Violation: Magnitude / Direction Conflict** | `42` (`1.5` / `0.0` / `18.0` / `20`) | `6` (`0.154` / `0.0` / `1.0` / `1`) | `7` (`0.194` / `0.0` / `1.0` / `2`) | `55` (`0.534` / `0.0` / `1.0` / `20`) |

---

### 1.4 RQ4 — Ablation A2 (`Without Provenance Deduplication`) vs. Full MIRAGE-OT

| Metric (`Total (Mean / Med / P95 / Max)`) | `01-Basic` (`N=28`) | `02-Semiurban` (`N=39`) | `03-Rural` (`N=36`) | All 103 Windows (`N=103`) |
| --- | --- | --- | --- | --- |
| **Raw Observation Count (Undeduplicated)** | `1,342` (`47.929` / `12.5` / `232.0` / `372`) | `3,756` (`96.308` / `56.0` / `354.0` / `448`) | `4,738` (`131.611` / `104.5` / `590.0` / `740`) | **`9,836` (`95.495` / `36.0` / `354.0` / `740`)** |
| **True Distinct Source Container Count (MIRAGE-OT)** | `986` (`35.214` / `4.0` / `214.0` / `366`) | `1,670` (`42.821` / `12.0` / `178.0` / `354`) | `1,837` (`51.028` / `31.0` / `178.0` / `370`) | **`4,493` (`43.621` / `9.0` / `178.0` / `370`)** |
| **Distinct RTU Count** | `54` (`1.929` / `1.0` / `5.0` / `12`) | `828` (`21.231` / `2.0` / `64.0` / `64`) | `679` (`18.861` / `3.0` / `53.0` / `55`) | `1,561` (`15.155` / `2.0` / `62.0` / `64`) |
| **Falsely Counted Independent Sources (`Total`)** | `356` (`12.714` / `4.5` / `39.0` / `97`) | `2,086` (`53.487` / `25.0` / `264.0` / `353`) | `2,901` (`80.583` / `40.5` / `412.0` / `522`) | **`5,343` (`51.874` / `13.0` / `173.0` / `522`)** |
| — Mirror Vantage Duplicates (`n302`/`n318`/`n406`...) | `185` (`6.607` / `3.0` / `22.0` / `39`) | `720` (`18.462` / `5.0` / `88.0` / `89`) | `1,604` (`44.556` / `34.5` / `172.0` / `370`) | `2,509` (`24.359` / `6.0` / `89.0` / `370`) |
| — IPAL-Derived State Observations (Weight 0) | `109` (`3.893` / `1.0` / `18.0` / `53`) | `1,138` (`29.179` / `4.0` / `128.0` / `179`) | `1,015` (`28.194` / `3.5` / `182.0` / `235`) | `2,262` (`21.961` / `2.0` / `72.0` / `235`) |
| — Same-ASDU Multi-IOA Point Expansion | `62` (`2.214` / `0.0` / `13.0` / `41`) | `228` (`5.846` / `0.0` / `48.0` / `85`) | `282` (`7.833` / `0.0` / `96.0` / `167`) | `572` (`5.553` / `0.0` / `31.0` / `167`) |
| **Source Inflation Factor (`Raw / True Containers`)** | `103.1994` (`3.686` / `1.938` / `10.75` / `12.0`) | `132.7669` (`3.404` / `2.5` / `12.0` / `14.0`) | `121.9315` (`3.387` / `2.821` / `8.4` / `8.677`) | **`357.8978` (`3.475` / `2.547` / `9.083` / `14.0`)** |
| **Spurious Multi-Source Storylines Without Dedup** | `794` (`28.357` / `1.0` / `22.0` / `673`) | `5,093` (`130.59` / `20.0` / `648.0` / `672`) | `3,691` (`102.528` / `10.5` / `438.0` / `485`) | **`9,578` (`92.99` / `7.0` / `508.0` / `673`)** |

---

### 1.5 RQ5 — Ablation A3 (`Without Incident Synthesis`) vs. Full MIRAGE-OT

| Metric (`Total (Mean / Med / P95 / Max)`) | Without Synthesis (`A3`) | With Four-Layer Incident Synthesis (`Full MIRAGE-OT`) | Added Value & Traceability |
| --- | --- | --- | --- |
| **Local Storylines (103 Windows)** | `11,050` (`107.282` / `19.0` / `508.0` / `675`) | `11,050` (`107.282` / `19.0` / `508.0` / `675`) (Partitioned in Layer 1) | Separates supported chains, verified single anchors, sequential observations, and quarantined unverified anchors |
| **Deduplicated Source Containers** | Not computed (`0`) | **`4,493` (`43.621` / `9.0` / `178.0` / `370`)** | Explicit container family accounting (`iec104_asdu`, `tcp_link`, `arp`, `composite_event`) |
| **RTU ASDU Bundles (`Layer 2`)** | `0` | **`1,700` (`16.505` / `1.0` / `66.0` / `95`)** (`186` co-reported points collapsed) | Collapses multi-IOA ASDUs into single-source RTU bundles (`independent_source_count=1`) |
| **Cross-RTU Verified Element Bridges (`Layer 2`)** | `0` | **`23` (`0.223` / `0.0` / `1.0` / `7`)** across **`11` Bridged Components** | Connects distinct RTU bundles only when linked by corroborated two-end element transitions |
| **Candidate Scenario Phases (`Layer 3`)** | `0` | **`143` (`1.388` / `1.0` / `3.0` / `4`)** | Groups co-occurring bundles and links by time horizon and host/ARP context while keeping cross-device links `unresolved` |
| **Competing Explanations (`Layer 4`)** | `0` | **`161` (`1.563` / `2.0` / `3.0` / `4`)** | Generates evidence-anchored alternative hypotheses and explicit `missing_disambiguating_evidence` lists |
| **100% `evidence_id` Traceability Verified** | Local spine only | **`True` (`103 / 103` windows)** | Every bundle, bridge, and competing explanation cites verifiable `evidence_id`s |

---

## 2. Representative Real Sherlock Case Studies (Task 5, Categories C1–C7)

### `C1_command_passed_consistency_gate` — `01-Basic` / `ev_0961f1c2da8a257e3ebc`
- **Category**: IEC-104 control command passing pre/post transition consistency gate
- **Selection Rule**: Select `01-Basic` window `ev_0961f1c2da8a257e3ebc` (setpoint command on `sgen.6`) and `02-Semiurban` window `ev_229f54b33cd3bfeb8f67` (binary command on `switch.335:closed`), where `COT=6 -> COT=7 (P/N=0)` is followed by a decoded pre-to-post shift matching the target.
- **1. Raw Observable Facts**:
  - Control transactions: `4` (`['switch.23:closed:state_report_observed_no_pre_baseline', 'switch.24:closed:state_report_observed_no_pre_baseline', 'switch.25:closed:state_report_observed_no_pre_baseline', 'sgen.6:target_active_power:verified_measurement_transition']`)
  - Verified anchors: `14`; Quarantined unverified anchors: `4`
  - Sample verified anchors: `[('A004', 'measurement_step', 'line.7:reactive_power_from', '172.16.3.1'), ('A005', 'measurement_step', 'line.13:active_power_from,reactive_power_from', '172.16.3.9'), ('A006', 'measurement_step', 'line.4:reactive_power_from', '172.16.3.18'), ('A007', 'measurement_step', 'line.12:reactive_power_to', '172.16.3.24'), ('A008', 'measurement_step', 'line.5:reactive_power_from', '172.16.3.24'), ('A009', 'measurement_step', 'line.13:active_power_to,reactive_power_to', '172.16.3.16')]`
- **2. Baseline Relations**:
  - `B1_temporal_only`: `125` candidate temporal links (`115` violating constraints: `111` cross-device unlinked, `0` quality/conflict, `10` transient non-sustained, `4` direction/type conflict).
  - `B2_protocol_only`: `APPLICABLE_CONTROL_COMMAND_WINDOW`, `4` protocol storylines, `1` verified command transitions; omits `13` verified behavioral anchors and `0` cross-RTU bridges.
- **3. Full MIRAGE-OT Relations**:
  - `report_status`: `quality_consistent` (`quality_consistency=True`, `lineage_consistency=True`, issues=`[]`)
  - RTU ASDU Bundles: `0`; Cross-RTU Verified Element Bridges: `[]`
  - Same-device sequential observations rejected by gate: `[]`
  - Unresolved cross-device branches preserved: `0`
- **4. Methodological Differences**:
  - vs `B1`: B1 emits 125 candidate temporal links (115 violating device/quality/persistence/direction constraints); MIRAGE-OT restricts supported steps to 0 cross-RTU bridges and 1 verified command transitions.
  - vs `B2`: B2 is `APPLICABLE_CONTROL_COMMAND_WINDOW` and omits 13 verified behavioral anchors and 0 cross-RTU bridges.
  - vs `A1`: Without the consistency gate, A1 promotes 3 unsupported relations ({'quality_or_test_bit_violation': 3, 'persistence_insufficient_violation': 0, 'prior_state_baseline_missing_violation': 3, 'change_type_mismatch_violation': 0, 'magnitude_or_direction_conflict_violation': 0, 'non_complementary_or_disjoint_interval_violation': 0}).
  - vs `A2`: Without provenance deduplication, A2 inflates 13 true source containers to 31 raw observations (inflation factor 2.3846x).
  - vs `A3`: Without Incident Synthesis, A3 leaves 6 fragmented local storylines without consolidating 0 ASDU bundles, 0 cross-RTU bridges, or 1 competing explanations.
- **5. Cited Evidence IDs**: `['EV-494a34e6da358c21', 'EV-918472877d43879f', 'EV-43ead8119c854618', 'EV-76020d689440e581', 'EV-ba4f905fff7eaca9', 'EV-78d55af4a2046fad', 'EV-961567f8b54229f1', 'EV-d5420c7d73dd15c7', 'EV-accf99760a168d29', 'EV-8cda44d8746c998a', 'EV-15246b352cf4b896', 'EV-b8bc847b6ab955d9', 'EV-fe8bd9d68c56080f', 'EV-94f5611fd32eefad', 'EV-96c4cfdc8a90f8d4', 'EV-8b19c9ecd899e660']`
- **6. Remaining Unconfirmed Items**: `['Physical causation across distinct grid elements (no bus-branch topology model in telemetry)', 'Initiating actor or host process behind observed network frames']`

### `C1_command_passed_consistency_gate` — `02-Semiurban` / `ev_229f54b33cd3bfeb8f67`
- **Category**: IEC-104 control command passing pre/post transition consistency gate
- **Selection Rule**: Select `01-Basic` window `ev_0961f1c2da8a257e3ebc` (setpoint command on `sgen.6`) and `02-Semiurban` window `ev_229f54b33cd3bfeb8f67` (binary command on `switch.335:closed`), where `COT=6 -> COT=7 (P/N=0)` is followed by a decoded pre-to-post shift matching the target.
- **1. Raw Observable Facts**:
  - Control transactions: `1` (`['switch.335:closed:verified_state_transition']`)
  - Verified anchors: `67`; Quarantined unverified anchors: `510`
  - Sample verified anchors: `[('A001', 'arp_activity_increase', '172.16.14.8/ARP', '172.16.14.8'), ('A002', 'arp_activity_increase', '172.16.14.7/ARP', '172.16.14.7'), ('A012', 'measurement_step', 'sgen.71:cos_phi', '172.16.14.7'), ('A074', 'communication_change', '172.16.14.11<->172.16.14.7:2404/IEC104', '172.16.14.7'), ('A075', 'spontaneous_state_report', 'switch.335:is_closed', '172.16.14.7'), ('A457', 'measurement_step', 'sgen.46:cos_phi', '172.16.7.18')]`
- **2. Baseline Relations**:
  - `B1_temporal_only`: `4073` candidate temporal links (`4072` violating constraints: `3524` cross-device unlinked, `1198` quality/conflict, `3754` transient non-sustained, `547` direction/type conflict).
  - `B2_protocol_only`: `APPLICABLE_CONTROL_COMMAND_WINDOW`, `1` protocol storylines, `1` verified command transitions; omits `66` verified behavioral anchors and `0` cross-RTU bridges.
- **3. Full MIRAGE-OT Relations**:
  - `report_status`: `quality_consistent` (`quality_consistency=True`, `lineage_consistency=True`, issues=`[]`)
  - RTU ASDU Bundles: `0`; Cross-RTU Verified Element Bridges: `[]`
  - Same-device sequential observations rejected by gate: `[]`
  - Unresolved cross-device branches preserved: `0`
- **4. Methodological Differences**:
  - vs `B1`: B1 emits 4073 candidate temporal links (4072 violating device/quality/persistence/direction constraints); MIRAGE-OT restricts supported steps to 0 cross-RTU bridges and 1 verified command transitions.
  - vs `B2`: B2 is `APPLICABLE_CONTROL_COMMAND_WINDOW` and omits 66 verified behavioral anchors and 0 cross-RTU bridges.
  - vs `A1`: Without the consistency gate, A1 promotes 0 unsupported relations ({'quality_or_test_bit_violation': 0, 'persistence_insufficient_violation': 0, 'prior_state_baseline_missing_violation': 0, 'change_type_mismatch_violation': 0, 'magnitude_or_direction_conflict_violation': 0, 'non_complementary_or_disjoint_interval_violation': 0}).
  - vs `A2`: Without provenance deduplication, A2 inflates 4 true source containers to 6 raw observations (inflation factor 1.5x).
  - vs `A3`: Without Incident Synthesis, A3 leaves 5 fragmented local storylines without consolidating 0 ASDU bundles, 0 cross-RTU bridges, or 3 competing explanations.
- **5. Cited Evidence IDs**: `['EV-00a00cd3fa83e497', 'EV-7c67612c711ec8cd', 'EV-3334e4f733bfeddb', 'EV-5b22fe895f2c795d', 'EV-65ebf26ca8e9e5e4', 'EV-de0e6d51086a4384', 'EV-bcd4a8979aabf22e', 'EV-781966975711b2a5', 'EV-d08935622b887dbd', 'EV-94a7e098b756773e']`
- **6. Remaining Unconfirmed Items**: `['Physical causation across distinct grid elements (no bus-branch topology model in telemetry)', 'Initiating actor or host process behind observed network frames']`

### `C2_command_without_pre_post_measurement_evidence` — `01-Basic` / `ev_3e4d36008b29595ef246`
- **Category**: IEC-104 control command without sufficient pre/post state or measurement evidence
- **Selection Rule**: Select `01-Basic` window `ev_3e4d36008b29595ef246`, which contains 3 accepted switch commands (`TX001` `switch.23`, `TX002` `switch.24`, `TX003` `switch.30`) where `TX001`/`TX002` lack a prior IEC-104 state baseline in `[start-15s, cmd_time)` and `TX003` has no post-command state report.
- **1. Raw Observable Facts**:
  - Control transactions: `3` (`['switch.31:closed:state_report_observed_no_pre_baseline', 'switch.30:closed:no_state_change_observed', 'switch.27:closed:state_report_observed_no_pre_baseline']`)
  - Verified anchors: `18`; Quarantined unverified anchors: `15`
  - Sample verified anchors: `[('A003', 'measurement_step', 'line.0:reactive_power_to', '172.16.3.13'), ('A005', 'measurement_step', 'line.1:reactive_power_from', '172.16.3.13'), ('A007', 'measurement_step', 'line.0:reactive_power_from', '172.16.2.3'), ('A008', 'measurement_step', 'line.10:active_power_from,current_from,reactive_power_from', '172.16.2.4'), ('A010', 'measurement_step', 'line.11:active_power_to,current_to,reactive_power_to', '172.16.3.12'), ('A011', 'measurement_step', 'line.14:active_power_from,current_from,reactive_power_from', '172.16.3.12')]`
- **2. Baseline Relations**:
  - `B1_temporal_only`: `234` candidate temporal links (`225` violating constraints: `205` cross-device unlinked, `0` quality/conflict, `142` transient non-sustained, `10` direction/type conflict).
  - `B2_protocol_only`: `APPLICABLE_CONTROL_COMMAND_WINDOW`, `3` protocol storylines, `0` verified command transitions; omits `18` verified behavioral anchors and `0` cross-RTU bridges.
- **3. Full MIRAGE-OT Relations**:
  - `report_status`: `quality_consistent` (`quality_consistency=True`, `lineage_consistency=True`, issues=`[]`)
  - RTU ASDU Bundles: `0`; Cross-RTU Verified Element Bridges: `[]`
  - Same-device sequential observations rejected by gate: `[]`
  - Unresolved cross-device branches preserved: `0`
- **4. Methodological Differences**:
  - vs `B1`: B1 emits 234 candidate temporal links (225 violating device/quality/persistence/direction constraints); MIRAGE-OT restricts supported steps to 0 cross-RTU bridges and 0 verified command transitions.
  - vs `B2`: B2 is `APPLICABLE_CONTROL_COMMAND_WINDOW` and omits 18 verified behavioral anchors and 0 cross-RTU bridges.
  - vs `A1`: Without the consistency gate, A1 promotes 2 unsupported relations ({'quality_or_test_bit_violation': 2, 'persistence_insufficient_violation': 0, 'prior_state_baseline_missing_violation': 2, 'change_type_mismatch_violation': 0, 'magnitude_or_direction_conflict_violation': 0, 'non_complementary_or_disjoint_interval_violation': 0}).
  - vs `A2`: Without provenance deduplication, A2 inflates 8 true source containers to 10 raw observations (inflation factor 1.25x).
  - vs `A3`: Without Incident Synthesis, A3 leaves 6 fragmented local storylines without consolidating 0 ASDU bundles, 0 cross-RTU bridges, or 1 competing explanations.
- **5. Cited Evidence IDs**: `['EV-791de060d8603144', 'EV-e7746bd283b0f24f', 'EV-2a9f286e93fcbdac', 'EV-1584efea78937735', 'EV-eeeef33791631632', 'EV-9ea7e1f8c572ba8f', 'EV-2b03558caa5c80ba', 'EV-01204992f7cb6854', 'EV-889bf81070aa2ebf', 'EV-358c43a69870cbc2', 'EV-4a9c9a05ab9eb4f1', 'EV-b55b9638092be4fa', 'EV-96f93dc194661bb4', 'EV-45db89473e47780a', 'EV-18d92f1b33278446', 'EV-31818c33b6e8aeea']`
- **6. Remaining Unconfirmed Items**: `['Physical causation across distinct grid elements (no bus-branch topology model in telemetry)', 'Initiating actor or host process behind observed network frames']`

### `C3_no_command_cross_rtu_verified_bridge` — `01-Basic` / `ev_564bebaa45f0686cf98d`
- **Category**: No control command, corroborated Cross-RTU Verified Element Bridges
- **Selection Rule**: Select one no-command `S2` window from each scenario (`01-Basic` `ev_564bebaa45f0686cf98d`, `02-Semiurban` `ev_d3c46672f9814dcdc40c`, `03-Rural` `ev_0d966f97d1922adb09bb`) where `verified_element_bridges > 0`.
- **1. Raw Observable Facts**:
  - Control transactions: `0` (`[]`)
  - Verified anchors: `23`; Quarantined unverified anchors: `9`
  - Sample verified anchors: `[('A002', 'measurement_step', 'line.0:active_power_from', '172.16.2.3'), ('A003', 'measurement_step', 'bus.5:active_power,reactive_power,voltage,voltage_angle', '172.16.3.18'), ('A004', 'measurement_step', 'line.3:active_power_to,current_to,reactive_power_to,voltage_to', '172.16.3.18'), ('A005', 'measurement_step', 'line.4:active_power_from,current_from,reactive_power_from,voltage_from', '172.16.3.18'), ('A006', 'measurement_step', 'load.3:active_power,reactive_power', '172.16.3.18'), ('A008', 'measurement_step', 'line.0:active_power_to', '172.16.3.13')]`
- **2. Baseline Relations**:
  - `B1_temporal_only`: `157` candidate temporal links (`152` violating constraints: `149` cross-device unlinked, `0` quality/conflict, `25` transient non-sustained, `3` direction/type conflict).
  - `B2_protocol_only`: `NOT_APPLICABLE_NO_CONTROL_COMMANDS`, `0` protocol storylines, `0` verified command transitions; omits `23` verified behavioral anchors and `5` cross-RTU bridges.
- **3. Full MIRAGE-OT Relations**:
  - `report_status`: `quality_consistent` (`quality_consistency=True`, `lineage_consistency=True`, issues=`[]`)
  - RTU ASDU Bundles: `12`; Cross-RTU Verified Element Bridges: `[('BRG-001', 'line.0', '172.16.2.3->172.16.3.13'), ('BRG-002', 'line.3', '172.16.3.18->172.16.3.16'), ('BRG-003', 'line.4', '172.16.3.18->172.16.3.22'), ('BRG-004', 'line.1', '172.16.3.13->172.16.3.14'), ('BRG-005', 'line.12', '172.16.3.22->172.16.3.24')]`
  - Same-device sequential observations rejected by gate: `[('R0134', 'line.2', ['change_type_mismatch']), ('R0211', 'line.2', ['left_not_sustained', 'right_not_sustained', 'left_anchor_unverified', 'right_anchor_unverified', 'magnitude_ratio_mismatch:current']), ('R0212', 'line.14', ['left_not_sustained', 'right_not_sustained', 'left_anchor_unverified', 'right_anchor_unverified', 'magnitude_direction_mismatch:current'])]`
  - Unresolved cross-device branches preserved: `129`
- **4. Methodological Differences**:
  - vs `B1`: B1 emits 157 candidate temporal links (152 violating device/quality/persistence/direction constraints); MIRAGE-OT restricts supported steps to 5 cross-RTU bridges and 0 verified command transitions.
  - vs `B2`: B2 is `NOT_APPLICABLE_NO_CONTROL_COMMANDS` and omits 23 verified behavioral anchors and 5 cross-RTU bridges.
  - vs `A1`: Without the consistency gate, A1 promotes 3 unsupported relations ({'quality_or_test_bit_violation': 0, 'persistence_insufficient_violation': 2, 'prior_state_baseline_missing_violation': 0, 'change_type_mismatch_violation': 1, 'magnitude_or_direction_conflict_violation': 2, 'non_complementary_or_disjoint_interval_violation': 0}).
  - vs `A2`: Without provenance deduplication, A2 inflates 12 true source containers to 109 raw observations (inflation factor 9.0833x).
  - vs `A3`: Without Incident Synthesis, A3 leaves 27 fragmented local storylines without consolidating 12 ASDU bundles, 5 cross-RTU bridges, or 2 competing explanations.
- **5. Cited Evidence IDs**: `['EV-3c3cbb46e50d7d28', 'EV-dea3772f106a463b', 'EV-84daa0e68ef06102', 'EV-8157ecd56e21ff99', 'EV-d0ebc674e5e5f30c', 'EV-7d6b819e7f3d4f63', 'EV-d852dab86b4e7efb', 'EV-99ceaa9a519bf6c0', 'EV-f969c5f8a10a6e07', 'EV-5ece22ffa46d5ca3', 'EV-09ca5573406fa16b', 'EV-bfef5819e801be66', 'EV-6a99c02e933fe11b', 'EV-5b1890a70bf8109b', 'EV-9419dfe4ce1fb46e', 'EV-4baf725f280851a4']`
- **6. Remaining Unconfirmed Items**: `['Physical causation across distinct grid elements (no bus-branch topology model in telemetry)', 'Initiating actor or host process behind observed network frames']`

### `C3_no_command_cross_rtu_verified_bridge` — `02-Semiurban` / `ev_d3c46672f9814dcdc40c`
- **Category**: No control command, corroborated Cross-RTU Verified Element Bridges
- **Selection Rule**: Select one no-command `S2` window from each scenario (`01-Basic` `ev_564bebaa45f0686cf98d`, `02-Semiurban` `ev_d3c46672f9814dcdc40c`, `03-Rural` `ev_0d966f97d1922adb09bb`) where `verified_element_bridges > 0`.
- **1. Raw Observable Facts**:
  - Control transactions: `0` (`[]`)
  - Verified anchors: `94`; Quarantined unverified anchors: `125`
  - Sample verified anchors: `[('A009', 'measurement_step', 'line.17:current_to', '172.16.7.17'), ('A018', 'measurement_step', 'line.16:current_from', '172.16.7.16'), ('A021', 'measurement_step', 'bus.9:voltage', '172.16.7.1'), ('A022', 'measurement_step', 'bus.9:active_power,voltage_angle', '172.16.7.1'), ('A026', 'measurement_step', 'line.13:current_to', '172.16.7.15'), ('A028', 'measurement_step', 'line.14:current_from', '172.16.7.15')]`
- **2. Baseline Relations**:
  - `B1_temporal_only`: `1310` candidate temporal links (`1305` violating constraints: `1269` cross-device unlinked, `0` quality/conflict, `850` transient non-sustained, `17` direction/type conflict).
  - `B2_protocol_only`: `NOT_APPLICABLE_NO_CONTROL_COMMANDS`, `0` protocol storylines, `0` verified command transitions; omits `94` verified behavioral anchors and `5` cross-RTU bridges.
- **3. Full MIRAGE-OT Relations**:
  - `report_status`: `quality_consistent` (`quality_consistency=True`, `lineage_consistency=True`, issues=`[]`)
  - RTU ASDU Bundles: `80`; Cross-RTU Verified Element Bridges: `[('BRG-001', 'line.6', '172.16.7.7->172.16.7.1'), ('BRG-002', 'line.6', '172.16.7.7->172.16.7.1'), ('BRG-003', 'line.6', '172.16.7.1->172.16.7.7'), ('BRG-004', 'line.6', '172.16.7.1->172.16.7.7'), ('BRG-005', 'line.7', '172.16.7.7->172.16.7.12')]`
  - Same-device sequential observations rejected by gate: `[('R0245', 'line.94', ['left_not_sustained', 'right_not_sustained', 'left_anchor_unverified', 'right_anchor_unverified', 'endpoints_not_complementary']), ('R0252', 'line.94', ['left_not_sustained', 'right_not_sustained', 'left_anchor_unverified', 'right_anchor_unverified']), ('R0259', 'line.94', ['left_not_sustained', 'right_not_sustained', 'left_anchor_unverified', 'right_anchor_unverified']), ('R0266', 'line.89', ['left_not_sustained', 'right_not_sustained', 'left_anchor_unverified', 'right_anchor_unverified']), ('R0267', 'line.95', ['left_not_sustained', 'right_not_sustained', 'left_anchor_unverified', 'right_anchor_unverified', 'endpoints_not_complementary']), ('R0274', 'line.95', ['left_not_sustained', 'right_not_sustained', 'left_anchor_unverified', 'right_anchor_unverified'])]`
  - Unresolved cross-device branches preserved: `1220`
- **4. Methodological Differences**:
  - vs `B1`: B1 emits 1310 candidate temporal links (1305 violating device/quality/persistence/direction constraints); MIRAGE-OT restricts supported steps to 5 cross-RTU bridges and 0 verified command transitions.
  - vs `B2`: B2 is `NOT_APPLICABLE_NO_CONTROL_COMMANDS` and omits 94 verified behavioral anchors and 5 cross-RTU bridges.
  - vs `A1`: Without the consistency gate, A1 promotes 25 unsupported relations ({'quality_or_test_bit_violation': 0, 'persistence_insufficient_violation': 13, 'prior_state_baseline_missing_violation': 0, 'change_type_mismatch_violation': 0, 'magnitude_or_direction_conflict_violation': 1, 'non_complementary_or_disjoint_interval_violation': 16}).
  - vs `A2`: Without provenance deduplication, A2 inflates 80 true source containers to 344 raw observations (inflation factor 4.3x).
  - vs `A3`: Without Incident Synthesis, A3 leaves 216 fragmented local storylines without consolidating 80 ASDU bundles, 5 cross-RTU bridges, or 2 competing explanations.
- **5. Cited Evidence IDs**: `['EV-ca799306460047c5', 'EV-e2d519ce2f80c961', 'EV-96d101e95030427a', 'EV-d1bc9993aa5440f8', 'EV-2a7275c96212c5aa', 'EV-f240fe3395866802', 'EV-295aec80459a8036', 'EV-c9091214d4155501', 'EV-548ecb99ee9805ba', 'EV-9fabac9dde67aede', 'EV-3de66be3f916d3ef', 'EV-bccb807762548915', 'EV-602ef0f51c63d3d1', 'EV-2e32a79e963c2f15', 'EV-1937578581fc6b5e', 'EV-0042a3e4dbabdd08']`
- **6. Remaining Unconfirmed Items**: `['Physical causation across distinct grid elements (no bus-branch topology model in telemetry)', 'Initiating actor or host process behind observed network frames']`

### `C3_no_command_cross_rtu_verified_bridge` — `03-Rural` / `ev_0d966f97d1922adb09bb`
- **Category**: No control command, corroborated Cross-RTU Verified Element Bridges
- **Selection Rule**: Select one no-command `S2` window from each scenario (`01-Basic` `ev_564bebaa45f0686cf98d`, `02-Semiurban` `ev_d3c46672f9814dcdc40c`, `03-Rural` `ev_0d966f97d1922adb09bb`) where `verified_element_bridges > 0`.
- **1. Raw Observable Facts**:
  - Control transactions: `0` (`[]`)
  - Verified anchors: `114`; Quarantined unverified anchors: `73`
  - Sample verified anchors: `[('A002', 'measurement_step', 'sgen.58:active_power', '172.16.10.1'), ('A003', 'measurement_step', 'storage.23:active_power', '172.16.10.1'), ('A004', 'measurement_step', 'storage.24:active_power', '172.16.11.2'), ('A005', 'measurement_step', 'sgen.60:active_power', '172.16.11.1'), ('A006', 'measurement_step', 'line.53:active_power_to,reactive_power_to', '172.16.9.5'), ('A008', 'measurement_step', 'line.54:active_power_from,reactive_power_from', '172.16.9.5')]`
- **2. Baseline Relations**:
  - `B1_temporal_only`: `1131` candidate temporal links (`1124` violating constraints: `1094` cross-device unlinked, `0` quality/conflict, `447` transient non-sustained, `26` direction/type conflict).
  - `B2_protocol_only`: `NOT_APPLICABLE_NO_CONTROL_COMMANDS`, `0` protocol storylines, `0` verified command transitions; omits `114` verified behavioral anchors and `7` cross-RTU bridges.
- **3. Full MIRAGE-OT Relations**:
  - `report_status`: `quality_consistent` (`quality_consistency=True`, `lineage_consistency=True`, issues=`[]`)
  - RTU ASDU Bundles: `86`; Cross-RTU Verified Element Bridges: `[('BRG-001', 'line.57', '172.16.9.8->172.16.9.7'), ('BRG-002', 'line.57', '172.16.9.8->172.16.9.7'), ('BRG-003', 'line.57', '172.16.9.8->172.16.9.7'), ('BRG-004', 'line.100', '172.16.11.3->172.16.11.1'), ('BRG-005', 'line.98', '172.16.11.2->172.16.10.1'), ('BRG-006', 'line.56', '172.16.9.6->172.16.9.7'), ('BRG-007', 'line.56', '172.16.9.6->172.16.9.7')]`
  - Same-device sequential observations rejected by gate: `[('R0322', 'bus.98', ['endpoints_not_complementary']), ('R0360', 'bus.68', ['endpoints_not_complementary']), ('R0366', 'bus.68', ['endpoints_not_complementary']), ('R0373', 'bus.68', ['endpoints_not_complementary']), ('R0376', 'bus.63', ['endpoints_not_complementary']), ('R0382', 'bus.63', ['endpoints_not_complementary'])]`
  - Unresolved cross-device branches preserved: `1035`
- **4. Methodological Differences**:
  - vs `B1`: B1 emits 1131 candidate temporal links (1124 violating device/quality/persistence/direction constraints); MIRAGE-OT restricts supported steps to 7 cross-RTU bridges and 0 verified command transitions.
  - vs `B2`: B2 is `NOT_APPLICABLE_NO_CONTROL_COMMANDS` and omits 114 verified behavioral anchors and 7 cross-RTU bridges.
  - vs `A1`: Without the consistency gate, A1 promotes 26 unsupported relations ({'quality_or_test_bit_violation': 0, 'persistence_insufficient_violation': 1, 'prior_state_baseline_missing_violation': 0, 'change_type_mismatch_violation': 0, 'magnitude_or_direction_conflict_violation': 0, 'non_complementary_or_disjoint_interval_violation': 26}).
  - vs `A2`: Without provenance deduplication, A2 inflates 86 true source containers to 498 raw observations (inflation factor 5.7907x).
  - vs `A3`: Without Incident Synthesis, A3 leaves 183 fragmented local storylines without consolidating 86 ASDU bundles, 7 cross-RTU bridges, or 2 competing explanations.
- **5. Cited Evidence IDs**: `['EV-83de42bd94e2a7ca', 'EV-e0bb812cbbd92c5a', 'EV-49e6cd8b18ebc8b7', 'EV-38a2d0b85cd4f125', 'EV-da5bd99c5a6fa7c8', 'EV-6afc3a562208d1b1', 'EV-1a23285701b08127', 'EV-34f8a65dc2d6481d', 'EV-89c1731670ffafd4', 'EV-f667390311e9f926', 'EV-fca909efbf50b967', 'EV-84f063a1f9bd8ee9', 'EV-64088f30d933a8d5', 'EV-9dc44b64daec1e6b', 'EV-5c8b44acf41cb48a', 'EV-c23466acb2a086e7']`
- **6. Remaining Unconfirmed Items**: `['Physical causation across distinct grid elements (no bus-branch topology model in telemetry)', 'Initiating actor or host process behind observed network frames']`

### `C4_arp_and_iec104_link_disruption_uncertain_causality` — `01-Basic` / `ev_cbe1e5bef23346604396`
- **Category**: ARP burst and IEC-104 link disruptions with per-target precedence filtering and uncertain causality
- **Selection Rule**: Select `01-Basic` window `ev_cbe1e5bef23346604396`, where ARP traffic from `172.16.3.28` precedes link loss on RTUs `172.16.3.10` and `172.16.3.9` within 15s, while first ARP to `172.16.3.20` occurs 37.7s after its link change.
- **1. Raw Observable Facts**:
  - Control transactions: `0` (`[]`)
  - Verified anchors: `4`; Quarantined unverified anchors: `3`
  - Sample verified anchors: `[('A001', 'arp_activity_increase', '172.16.3.28/ARP', '172.16.3.28'), ('A002', 'communication_change', '172.16.1.2<->172.16.3.10:2404/IEC104', '172.16.3.10'), ('A003', 'communication_change', '172.16.1.2<->172.16.3.20:2404/IEC104', '172.16.3.20'), ('A004', 'communication_change', '172.16.1.2<->172.16.3.9:2404/IEC104', '172.16.3.9')]`
- **2. Baseline Relations**:
  - `B1_temporal_only`: `7` candidate temporal links (`7` violating constraints: `7` cross-device unlinked, `0` quality/conflict, `1` transient non-sustained, `0` direction/type conflict).
  - `B2_protocol_only`: `NOT_APPLICABLE_NO_CONTROL_COMMANDS`, `0` protocol storylines, `0` verified command transitions; omits `4` verified behavioral anchors and `0` cross-RTU bridges.
- **3. Full MIRAGE-OT Relations**:
  - `report_status`: `quality_consistent` (`quality_consistency=True`, `lineage_consistency=True`, issues=`[]`)
  - RTU ASDU Bundles: `4`; Cross-RTU Verified Element Bridges: `[]`
  - Same-device sequential observations rejected by gate: `[]`
  - Unresolved cross-device branches preserved: `7`
- **4. Methodological Differences**:
  - vs `B1`: B1 emits 7 candidate temporal links (7 violating device/quality/persistence/direction constraints); MIRAGE-OT restricts supported steps to 0 cross-RTU bridges and 0 verified command transitions.
  - vs `B2`: B2 is `NOT_APPLICABLE_NO_CONTROL_COMMANDS` and omits 4 verified behavioral anchors and 0 cross-RTU bridges.
  - vs `A1`: Without the consistency gate, A1 promotes 0 unsupported relations ({'quality_or_test_bit_violation': 0, 'persistence_insufficient_violation': 0, 'prior_state_baseline_missing_violation': 0, 'change_type_mismatch_violation': 0, 'magnitude_or_direction_conflict_violation': 0, 'non_complementary_or_disjoint_interval_violation': 0}).
  - vs `A2`: Without provenance deduplication, A2 inflates 4 true source containers to 43 raw observations (inflation factor 10.75x).
  - vs `A3`: Without Incident Synthesis, A3 leaves 7 fragmented local storylines without consolidating 4 ASDU bundles, 0 cross-RTU bridges, or 2 competing explanations.
- **5. Cited Evidence IDs**: `['EV-0e9f6fb66f6907e4', 'EV-dd59c3d758762e69', 'EV-06a22bddc2cd3bee', 'EV-79fef36709e79d8b', 'EV-43c669e3989a2cb9', 'EV-4f94ff12f644b2ff', 'EV-f0d746d67fdd2fa4', 'EV-a19b67117ff1dbe7']`
- **6. Remaining Unconfirmed Items**: `['Physical causation across distinct grid elements (no bus-branch topology model in telemetry)', 'Initiating actor or host process behind observed network frames']`

### `C5_multi_vantage_payload_conflict` — `01-Basic` / `ev_52f5eee28f8b95e702fd`
- **Category**: Multi-vantage mirror payload conflicts quarantined from supported spines
- **Selection Rule**: Select `01-Basic` window `ev_52f5eee28f8b95e702fd`, which exhibits 240 `post_cross_vantage_payload_conflict` and 236 `pre_cross_vantage_payload_conflict` anchor issues across mirror vantages.
- **1. Raw Observable Facts**:
  - Control transactions: `0` (`[]`)
  - Verified anchors: `4`; Quarantined unverified anchors: `671`
  - Sample verified anchors: `[('A001', 'arp_activity_increase', '172.16.3.24/ARP', '172.16.3.24'), ('A002', 'arp_activity_increase', '172.16.3.28/ARP', '172.16.3.28'), ('A018', 'measurement_step', 'line.9:current_from,reactive_power_from', '172.16.3.14'), ('A029', 'measurement_step', 'line.13:current_to,voltage_to', '172.16.3.16')]`
- **2. Baseline Relations**:
  - `B1_temporal_only`: `6930` candidate temporal links (`6930` violating constraints: `4964` cross-device unlinked, `4530` quality/conflict, `6929` transient non-sustained, `1786` direction/type conflict).
  - `B2_protocol_only`: `NOT_APPLICABLE_NO_CONTROL_COMMANDS`, `0` protocol storylines, `0` verified command transitions; omits `4` verified behavioral anchors and `0` cross-RTU bridges.
- **3. Full MIRAGE-OT Relations**:
  - `report_status`: `quality_consistent` (`quality_consistency=True`, `lineage_consistency=True`, issues=`[]`)
  - RTU ASDU Bundles: `4`; Cross-RTU Verified Element Bridges: `[]`
  - Same-device sequential observations rejected by gate: `[('R0704', 'sgen.12', ['left_quality_or_test_bit_not_good', 'right_quality_or_test_bit_not_good', 'left_not_sustained', 'right_not_sustained', 'left_anchor_unverified', 'right_anchor_unverified', 'endpoints_not_complementary']), ('R0711', 'sgen.12', ['left_quality_or_test_bit_not_good', 'right_quality_or_test_bit_not_good', 'left_not_sustained', 'right_not_sustained', 'left_anchor_unverified', 'right_anchor_unverified', 'endpoints_not_complementary']), ('R0712', 'sgen.12', ['left_quality_or_test_bit_not_good', 'right_quality_or_test_bit_not_good', 'left_not_sustained', 'right_not_sustained', 'left_anchor_unverified', 'right_anchor_unverified', 'transition_intervals_disjoint', 'endpoints_not_complementary']), ('R0719', 'sgen.12', ['left_quality_or_test_bit_not_good', 'right_quality_or_test_bit_not_good', 'left_not_sustained', 'right_not_sustained', 'left_anchor_unverified', 'right_anchor_unverified', 'endpoints_not_complementary']), ('R0720', 'sgen.12', ['left_quality_or_test_bit_not_good', 'right_quality_or_test_bit_not_good', 'left_not_sustained', 'right_not_sustained', 'left_anchor_unverified', 'right_anchor_unverified', 'transition_intervals_disjoint', 'endpoints_not_complementary']), ('R0727', 'sgen.6', ['left_quality_or_test_bit_not_good', 'right_quality_or_test_bit_not_good', 'left_not_sustained', 'right_not_sustained', 'left_anchor_unverified', 'right_anchor_unverified', 'endpoints_not_complementary'])]`
  - Unresolved cross-device branches preserved: `3998`
- **4. Methodological Differences**:
  - vs `B1`: B1 emits 6930 candidate temporal links (6930 violating device/quality/persistence/direction constraints); MIRAGE-OT restricts supported steps to 0 cross-RTU bridges and 0 verified command transitions.
  - vs `B2`: B2 is `NOT_APPLICABLE_NO_CONTROL_COMMANDS` and omits 4 verified behavioral anchors and 0 cross-RTU bridges.
  - vs `A1`: Without the consistency gate, A1 promotes 1966 unsupported relations ({'quality_or_test_bit_violation': 1318, 'persistence_insufficient_violation': 1966, 'prior_state_baseline_missing_violation': 0, 'change_type_mismatch_violation': 180, 'magnitude_or_direction_conflict_violation': 0, 'non_complementary_or_disjoint_interval_violation': 1843}).
  - vs `A2`: Without provenance deduplication, A2 inflates 4 true source containers to 31 raw observations (inflation factor 7.75x).
  - vs `A3`: Without Incident Synthesis, A3 leaves 675 fragmented local storylines without consolidating 4 ASDU bundles, 0 cross-RTU bridges, or 2 competing explanations.
- **5. Cited Evidence IDs**: `['EV-6f3a914c20272ca8', 'EV-61547e835af4a3ca', 'EV-6922926db75760aa', 'EV-ef47051ed970f5b7', 'EV-dc141233bb171ebd', 'EV-c243276e252c1fe3', 'EV-3a8ee6bdd2843d26', 'EV-ee92af90f15168a1', 'EV-820989a947a979bc', 'EV-30c2665e86953e3f']`
- **6. Remaining Unconfirmed Items**: `['Physical causation across distinct grid elements (no bus-branch topology model in telemetry)', 'Initiating actor or host process behind observed network frames']`

### `C6_lineage_consistency_failure_diagnostic_downgrade` — `02-Semiurban` / `ev_5dd0102bf58bf2ce9487`
- **Category**: Lineage consistency failure automatically downgrading final report to Diagnostic Only
- **Selection Rule**: Select `02-Semiurban` window `ev_5dd0102bf58bf2ce9487`, the single window in the 103-window suite where `lineage_consistency.json` flags `time_outside_cited_sample` on `A007` (`EV-6e9e7ece8bf456f0`).
- **1. Raw Observable Facts**:
  - Control transactions: `0` (`[]`)
  - Verified anchors: `119`; Quarantined unverified anchors: `121`
  - Sample verified anchors: `[('A004', 'communication_change', '172.16.11.1<->172.16.12.1:2404/IEC104', '172.16.12.1'), ('A005', 'spontaneous_state_report', 'switch.48:is_closed', '172.16.12.1'), ('A008', 'measurement_step', 'line.1:active_power_to,current_to', '172.16.7.23'), ('A010', 'measurement_step', 'line.2:active_power_from,current_from', '172.16.7.23'), ('A013', 'measurement_step', 'line.11:active_power_to,current_to', '172.16.7.14'), ('A015', 'measurement_step', 'line.12:active_power_from,current_from', '172.16.7.14')]`
- **2. Baseline Relations**:
  - `B1_temporal_only`: `1468` candidate temporal links (`1457` violating constraints: `1412` cross-device unlinked, `0` quality/conflict, `883` transient non-sustained, `15` direction/type conflict).
  - `B2_protocol_only`: `APPLICABLE_CONTROL_COMMAND_WINDOW`, `0` protocol storylines, `0` verified command transitions; omits `119` verified behavioral anchors and `0` cross-RTU bridges.
- **3. Full MIRAGE-OT Relations**:
  - `report_status`: `diagnostic_only_lineage_inconsistent` (`quality_consistency=True`, `lineage_consistency=False`, issues=`[{'scope': 'behavioral_anchor_lineage', 'issue': 'row_check_failures', 'failures': [{'anchor_id': 'A007', 'evidence_id': 'EV-6e9e7ece8bf456f0', 'reason': 'time_outside_cited_sample'}]}]`)
  - RTU ASDU Bundles: `95`; Cross-RTU Verified Element Bridges: `[]`
  - Same-device sequential observations rejected by gate: `[('R0290', 'switch.48', ['right_not_sustained', 'right_anchor_unverified', 'unsupported_anchor_type_pair']), ('R0449', 'line.94', ['endpoints_not_complementary']), ('R0450', 'line.94', ['right_not_sustained', 'right_anchor_unverified', 'endpoints_not_complementary']), ('R0455', 'line.94', ['right_not_sustained', 'right_anchor_unverified', 'no_shared_measurement_quantity']), ('R0464', 'line.88', ['change_type_mismatch']), ('R0473', 'line.89', ['right_not_sustained', 'right_anchor_unverified', 'no_shared_measurement_quantity'])]`
  - Unresolved cross-device branches preserved: `1354`
- **4. Methodological Differences**:
  - vs `B1`: B1 emits 1468 candidate temporal links (1457 violating device/quality/persistence/direction constraints); MIRAGE-OT restricts supported steps to 0 cross-RTU bridges and 0 verified command transitions.
  - vs `B2`: B2 is `APPLICABLE_CONTROL_COMMAND_WINDOW` and omits 119 verified behavioral anchors and 0 cross-RTU bridges.
  - vs `A1`: Without the consistency gate, A1 promotes 19 unsupported relations ({'quality_or_test_bit_violation': 0, 'persistence_insufficient_violation': 15, 'prior_state_baseline_missing_violation': 0, 'change_type_mismatch_violation': 3, 'magnitude_or_direction_conflict_violation': 1, 'non_complementary_or_disjoint_interval_violation': 12}).
  - vs `A2`: Without provenance deduplication, A2 inflates 95 true source containers to 448 raw observations (inflation factor 4.7158x).
  - vs `A3`: Without Incident Synthesis, A3 leaves 231 fragmented local storylines without consolidating 95 ASDU bundles, 0 cross-RTU bridges, or 4 competing explanations.
- **5. Cited Evidence IDs**: `['EV-242533da5141d071', 'EV-fb8fbf3a69024939', 'EV-815682f7635b2589', 'EV-6e9e7ece8bf456f0', 'EV-88f73588781b6263', 'EV-c3b7fa57049aced8', 'EV-ebc43dcb2fdacb91', 'EV-be2907a10928b50b', 'EV-ba723003a68b8c08', 'EV-82dac0a8871bbc86', 'EV-02497bc7a91653d5', 'EV-77d0a290d587c609', 'EV-434cd4e06b8d0d97', 'EV-ff04deff30cd68df', 'EV-2465843b09957f98']`
- **6. Remaining Unconfirmed Items**: `['Physical causation across distinct grid elements (no bus-branch topology model in telemetry)', 'Initiating actor or host process behind observed network frames']`

### `C7_low_information_honest_abstention` — `01-Basic` / `ev_d58f418ff4f085ccc0a7`
- **Category**: Honest abstention in low-information periodic-measurement-only windows
- **Selection Rule**: Select `01-Basic` window `ev_d58f418ff4f085ccc0a7` and `02-Semiurban` window `ev_8e3ee44aec0a0f81c99a`, where only periodic `M_ME_NC_1 (COT=1)` telemetry and transient oscillations occur.
- **1. Raw Observable Facts**:
  - Control transactions: `0` (`[]`)
  - Verified anchors: `0`; Quarantined unverified anchors: `14`
  - Sample verified anchors: `[]`
- **2. Baseline Relations**:
  - `B1_temporal_only`: `4` candidate temporal links (`4` violating constraints: `2` cross-device unlinked, `0` quality/conflict, `4` transient non-sustained, `1` direction/type conflict).
  - `B2_protocol_only`: `NOT_APPLICABLE_NO_CONTROL_COMMANDS`, `0` protocol storylines, `0` verified command transitions; omits `0` verified behavioral anchors and `0` cross-RTU bridges.
- **3. Full MIRAGE-OT Relations**:
  - `report_status`: `quality_consistent` (`quality_consistency=True`, `lineage_consistency=True`, issues=`[]`)
  - RTU ASDU Bundles: `0`; Cross-RTU Verified Element Bridges: `[]`
  - Same-device sequential observations rejected by gate: `[('R0037', 'line.13', ['left_not_sustained', 'right_not_sustained', 'left_anchor_unverified', 'right_anchor_unverified', 'transition_intervals_disjoint', 'magnitude_direction_mismatch:current']), ('R0040', 'line.13', ['left_not_sustained', 'right_not_sustained', 'left_anchor_unverified', 'right_anchor_unverified', 'transition_intervals_disjoint'])]`
  - Unresolved cross-device branches preserved: `2`
- **4. Methodological Differences**:
  - vs `B1`: B1 emits 4 candidate temporal links (4 violating device/quality/persistence/direction constraints); MIRAGE-OT restricts supported steps to 0 cross-RTU bridges and 0 verified command transitions.
  - vs `B2`: B2 is `NOT_APPLICABLE_NO_CONTROL_COMMANDS` and omits 0 verified behavioral anchors and 0 cross-RTU bridges.
  - vs `A1`: Without the consistency gate, A1 promotes 2 unsupported relations ({'quality_or_test_bit_violation': 0, 'persistence_insufficient_violation': 2, 'prior_state_baseline_missing_violation': 0, 'change_type_mismatch_violation': 0, 'magnitude_or_direction_conflict_violation': 1, 'non_complementary_or_disjoint_interval_violation': 2}).
  - vs `A2`: Without provenance deduplication, A2 inflates 0 true source containers to 0 raw observations (inflation factor 1.0x).
  - vs `A3`: Without Incident Synthesis, A3 leaves 14 fragmented local storylines without consolidating 0 ASDU bundles, 0 cross-RTU bridges, or 2 competing explanations.
- **5. Cited Evidence IDs**: `['EV-42943a48737cbcab', 'EV-12d0e000a2c6bd1a', 'EV-c5a1d0edc1f56808', 'EV-ce3ffd677fa3c9cc', 'EV-37b12ca1ac085502']`
- **6. Remaining Unconfirmed Items**: `['Physical causation across distinct grid elements (no bus-branch topology model in telemetry)', 'Initiating actor or host process behind observed network frames']`

### `C7_low_information_honest_abstention` — `02-Semiurban` / `ev_8e3ee44aec0a0f81c99a`
- **Category**: Honest abstention in low-information periodic-measurement-only windows
- **Selection Rule**: Select `01-Basic` window `ev_d58f418ff4f085ccc0a7` and `02-Semiurban` window `ev_8e3ee44aec0a0f81c99a`, where only periodic `M_ME_NC_1 (COT=1)` telemetry and transient oscillations occur.
- **1. Raw Observable Facts**:
  - Control transactions: `0` (`[]`)
  - Verified anchors: `0`; Quarantined unverified anchors: `20`
  - Sample verified anchors: `[]`
- **2. Baseline Relations**:
  - `B1_temporal_only`: `13` candidate temporal links (`13` violating constraints: `12` cross-device unlinked, `0` quality/conflict, `13` transient non-sustained, `1` direction/type conflict).
  - `B2_protocol_only`: `NOT_APPLICABLE_NO_CONTROL_COMMANDS`, `0` protocol storylines, `0` verified command transitions; omits `0` verified behavioral anchors and `0` cross-RTU bridges.
- **3. Full MIRAGE-OT Relations**:
  - `report_status`: `quality_consistent` (`quality_consistency=True`, `lineage_consistency=True`, issues=`[]`)
  - RTU ASDU Bundles: `0`; Cross-RTU Verified Element Bridges: `[]`
  - Same-device sequential observations rejected by gate: `[('R0047', 'line.53', ['left_not_sustained', 'right_not_sustained', 'left_anchor_unverified', 'right_anchor_unverified', 'magnitude_direction_mismatch:current'])]`
  - Unresolved cross-device branches preserved: `12`
- **4. Methodological Differences**:
  - vs `B1`: B1 emits 13 candidate temporal links (13 violating device/quality/persistence/direction constraints); MIRAGE-OT restricts supported steps to 0 cross-RTU bridges and 0 verified command transitions.
  - vs `B2`: B2 is `NOT_APPLICABLE_NO_CONTROL_COMMANDS` and omits 0 verified behavioral anchors and 0 cross-RTU bridges.
  - vs `A1`: Without the consistency gate, A1 promotes 1 unsupported relations ({'quality_or_test_bit_violation': 0, 'persistence_insufficient_violation': 1, 'prior_state_baseline_missing_violation': 0, 'change_type_mismatch_violation': 0, 'magnitude_or_direction_conflict_violation': 1, 'non_complementary_or_disjoint_interval_violation': 0}).
  - vs `A2`: Without provenance deduplication, A2 inflates 0 true source containers to 0 raw observations (inflation factor 1.0x).
  - vs `A3`: Without Incident Synthesis, A3 leaves 20 fragmented local storylines without consolidating 0 ASDU bundles, 0 cross-RTU bridges, or 2 competing explanations.
- **5. Cited Evidence IDs**: `['EV-23a0be9000ba4c8e', 'EV-5567a8cd1fa3e806', 'EV-d31e1798d784fe7f', 'EV-6c70c4696b372a69', 'EV-b22fde6d085aa45f', 'EV-986f1fc1f38e2249']`
- **6. Remaining Unconfirmed Items**: `['Physical causation across distinct grid elements (no bus-branch topology model in telemetry)', 'Initiating actor or host process behind observed network frames']`

---

## 3. Synthetic Known-Answer Counterexamples (Reported Strictly Separately from Sherlock)

The following three synthetic counterexamples were executed in isolated temporary SQLite databases to verify deterministic rejection of known quality, provenance, and topological violations:

- **`S_KA1_test_bit_and_opposing_direction`** (`passed_known_answer = True`): `line.1:active_power_from` (RTU .11) increases 100->300, whereas `line.1:active_power_to` (RTU .12) decreases in magnitude |-100|->|-40| and has COT test bit `T=1` at the step sample. Must NOT form a supported transition or cross-RTU bridge. Details: `{'B1_temporal_only_candidates': 1, 'A1_ungated_unsupported_promotions': 1, 'MIRAGE_OT_supported_bridges': 0, 'MIRAGE_OT_sequential_rejected': 1, 'passed_known_answer': True}`.
- **`S_KA2_mirror_and_same_asdu_and_ipal_duplication`** (`passed_known_answer = True`): One ASDU (`apci_tx=31`) from RTU `172.16.3.18` carries two objects (`bus.5` and `load.3`), is mirrored at two vantages (`n302` and `n318`, 4 packet objects), and produces 2 IPAL rows (6 raw observations total). True independent source container count is exactly 1. Details: `{'A2_naive_raw_observation_count': 6, 'A2_mirror_duplicate_count': 2, 'A2_same_asdu_expansion_count': 1, 'A2_ipal_derived_count': 2, 'MIRAGE_OT_distinct_source_container_count': 1, 'passed_known_answer': True}`.
- **`S_KA3_unverified_switch_vs_verified_cross_rtu_line_bridge`** (`passed_known_answer = True`): Unverified `switch.99:is_closed=0` (no prior baseline) occurs 4s before `line.4` drops to zero at both `to` (RTU .18) and `from` (RTU .22) ends. Only `line.4` (`to` <-> `from`) is a corroborated cross-RTU bridge; `switch.99 -> line.4` must remain an unresolved candidate branch. Details: `{'B1_temporal_only_candidates': 3, 'B1_cross_device_unsupported_candidates': 2, 'MIRAGE_OT_verified_bridges': ['line.4'], 'MIRAGE_OT_unresolved_branches': 2, 'passed_known_answer': True}`.
