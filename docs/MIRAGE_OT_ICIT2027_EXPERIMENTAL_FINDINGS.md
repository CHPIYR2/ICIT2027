# MIRAGE-OT: Experimental Findings & Evidence Package for IEEE ICIT 2027 (Paper-Readiness Audit Edition)

- **Target Venue**: IEEE International Conference on Industrial Technology (ICIT 2027)
- **Paper Positioning**: An Evidence-Grounded Post-Alert Incident Reconstruction and Four-Layer Scenario Synthesis Framework for Operational Technology (OT) Networks
- **Frozen Engine Commit**: `2981fb062b127218a34f23f2ff0292e4ca8cfea7` (`code_sha256 = d43d9867ce84...`, `evidence_code_sha256 = 032c6977ac05...`)
- **Dataset Evaluated**: Sherlock v3 Complete Test Suite (`103` windows: `28` `01-Basic`, `39` `02-Semiurban`, `36` `03-Rural`; `27,263.3 s` / `7.57 hours` of multi-switch PCAPs and IPAL telemetry)

---

## 1. Core Paper Claims (Strictly Scoped per Paper-Readiness Audit)

1. **Cross-Scenario Generalization Without Parameter Tuning**:
   - Frozen on `01-Basic` (`500` mapped points, `4` switch mirror vantages) and transferred with **zero parameter or rule modifications** to `02-Semiurban` (`3,640` points, `6` mirror vantages) and `03-Rural` (`1,908` points, `8` mirror vantages), MIRAGE-OT completed **`103 / 103` windows (`0` execution failures)** with **`100.0%` (`103 / 103`) Quality Consistency**, **`100.0%` (`103 / 103`) Evidence Citation Presence & SQLite ID Resolution**, and **`99.03%` (`102 / 103`) Full Lineage Consistency** (catching and automatically downgrading the single cross-switch clock-skew anomaly in `02-Semiurban` `ev_5dd0102bf58bf2ce9487` to `diagnostic_only_lineage_inconsistent`).
2. **Separation of Unsubstantiated Temporal Candidates vs. Explicit Constraint Conflicts (`B1` & Counterfactual `A1`)**:
   - Temporal-Only Reconstruction (`B1`) emits **`107,666` candidate temporal associations** (`78,238` cross-device, `26,800` same-device separate-ASDU, `2,628` same-ASDU co-reports). Rather than treating `not same_device` as a proven false causal relation, our evaluation separates:
     - **`18,130` (`16.84%`) `unsubstantiated_temporal_candidates`** (temporally proximate pairs lacking direct protocol/topology link evidence, **not proven false**, held `unresolved` by MIRAGE-OT), and
     - **`66,706` (`61.96%`) `explicit_evidence_constraint_conflicts`** (pairs directly conflicting with checkable telemetry properties: `66,042` transient non-sustained oscillations, `8,489` quality/test-bit/vantage conflicts, `3,707` same-device change-type/side conflicts, `2,628` same-ASDU co-reports chained as sequences, and `35` same-device direction/ratio conflicts).
   - In **counterfactual ablation `A1`** (removing the Behavioral & Command Consistency Gates), **`2,171` counterfactual unsupported promotions** (`409` potential cross-RTU bridges) occur across `52` windows. Even after **excluding the maximum cross-vantage conflict outlier `ev_52f5eee28f8b95e702fd` (`N=102` windows)**, **`205` counterfactual unsupported promotions** (`126` behavioral + `79` command-effect) and **`49` spurious cross-RTU bridges** remain across **`51 / 102` (`50.0%`) windows**.
3. **Scope Expansion Beyond Protocol Control Transactions (`B2`)**:
   - Pure IEC-104 Transaction Reconstruction (`B2`) is applicable to **`46 / 103` (`44.66%`)** windows containing control objects (`45` `S1` windows with reconstructed `COT=6` transactions plus `1` window `ev_5dd0102bf58bf2ce9487` containing `62` unpaired `COT=7` replies without a matching `COT=6` command) and is `NOT_APPLICABLE` to the remaining **`57 / 103` (`55.34%`)** no-command windows, omitting **`2,776` verified behavioral anchors**, **`23` Cross-RTU Verified Element Bridges**, and **`134` verified ARP / IEC-104 link disruption anomalies**.
4. **Packet-Identity Provenance Accounting (`A2` Counterfactual Analysis)**:
   - Across the 103 windows, **`4,493` distinct protocol message / event containers** (spanning `25` unique RTUs in Basic, `69` in Semiurban, and `57` in Rural; `1,561` when summed per window across the 103 windows) are cited by `9,836` raw observations (`5,343` excess rows). Note that **message/event containers represent deduplicated network telemetry containers, NOT independent physical process sensors**.
   - Packet-identity decomposition against `evidence.sqlite` shows that the `5,343` excess rows consist of:
     - **`1,845` true cross-vantage mirror duplicates** (same packet captured at multiple switch mirror ports),
     - **`572` same-ASDU different IOA points** (multiple objects carried in one ASDU),
     - **`2,262` IPAL-derived state records** (subtotal **`4,679` true duplicate/multi-IOA/IPAL source inflations**, mean inflation factor **`2.44x`**, median **`2.22x`**), and
     - **`664` multi-event anchor aggregations** (`268` distinct messages in the same TCP session + `396` distinct-time network events inside `communication_change` and `arp_activity_increase` anchors, e.g. `ev_cbe1e5bef23346604396` where `true_mirror = 0`), plus **`0` unknown** rows.
5. **Addition of Traceable Structural Information via Four-Layer Synthesis (`A3`)**:
   - Compared to `11,050` ungrouped local storylines in `A3`, Four-Layer Incident Synthesis adds structured, evidence-traceable organization (`1,700` RTU ASDU Bundles, `23` Cross-RTU Verified Element Bridges in `11` Bridged Components, `143` Candidate Scenario Phases, and `161` competing explanations with explicit `missing_disambiguating_evidence`). We claim **structural organization and traceability only**, not empirically measured human investigation time savings.
6. **Air-Gapped Post-Freeze Physical State Value Agreement (`Task 6`, `01-Basic` `test/physical.zip`)**:
   - In a strictly offline, read-only check executed after all reconstruction outputs were frozen against `40,319` 1-second simulator snapshots in `01-Basic/raw/test/physical.zip`, **`9 / 9` (`100.0%`)** verified control-command transitions and **`6 / 6` (`100.0%`, `32 / 32` endpoint attributes)** Cross-RTU Verified Element Bridges match the simulator's pre- and post-event physical state/measurement values (with pandapower's `NaN` on de-energized islands encoded as `0.0` by RTU telemetry). This confirms **state/measurement value agreement**, not physical causal graph verification.

---

## 2. Paper-Ready Master Tables

### Table I — Cross-Scenario Evaluation Across All 103 Sherlock v3 Test Windows

| Metric | `01-Basic` (`N=28`) | `02-Semiurban` (`N=39`) | `03-Rural` (`N=36`) | All Scenarios (`N=103`) |
| --- | ---: | ---: | ---: | ---: |
| Mapped Points / Switch Mirror Vantages | `500` / `4` | `3,640` / `6` | `1,908` / `8` | `500–3,640` / `4–8` |
| Unique RTUs Cited in Scenario (`Per-Window Sum`) | `25` (`186`) | `69` (`696`) | `57` (`679`) | `25 / 69 / 57` (`1,561`) |
| Reconstructed Command Windows (`S1`) / B2 Applicable | `16` / `16` | `15` / `16`* | `14` / `14` | `45` / `46`* |
| No-Command Behavioral Windows (`S2` / `S3` / `S4`) | `4` / `6` / `2` | `7` / `12` / `5` | `4` / `15` / `3` | `15` / `33` / `10` |
| Reconstructed Transactions (`Total` / `Verified`) | `419` / `9` | `370` / `3` | `534` / `3` | `1,323` / `15` |
| Discovered Anchors (`Total` / `Verified` / `Quarantined`) | `1,447` / `160` / `1,287` | `7,413` / `1,564` / `5,849` | `4,167` / `1,069` / `3,098` | `13,027` / `2,793` / `10,234` |
| RTU Source Bundles / Cross-RTU Bridges (`Components`) | `36` / `6` (`3`) | `910` / `6` (`2`) | `754` / `11` (`6`) | `1,700` / `23` (`11`) |
| E3 Level 1 & 2: Citation Presence & SQLite ID Resolution | `28/28` (`100%`) | `39/39` (`100%`) | `36/36` (`100%`) | `103/103` (`100.0%`) |
| E3 Level 3 & 4: Fact/Anchor & Full Lineage Consistency | `28/28` (`100%`) | `38/39` (`97.44%`) | `36/36` (`100%`) | `102/103` (`99.03%`) |
| Quality Consistency Pass Rate / Execution Failures | `28/28` / `0` | `39/39` / `0` | `36/36` / `0` | `103/103` (`100%`) / `0` |
| Full Pipeline Reconstruction + Synthesis Time (Med / Mean) | `0.66 s` / `0.91 s` | `14.04 s` / `21.24 s` | `7.74 s` / `11.61 s` | `7.41 s` / `12.34 s` |

*\*Note: `02-Semiurban` `ev_5dd0102bf58bf2ce9487` contains `62` unpaired `COT=7` confirmation objects (`iec104_control_objects_in_window = 62`) with `0` matching `COT=6` commands (`transaction_count = 0`), accounting for the `45` `S1` transaction windows vs. `46` `B2` applicable windows.*

---

### Table II — Audit-Corrected Baseline and Counterfactual Ablation Summary (`N=103` Windows)

| Variant | Nature of Comparison | Key Quantitative Finding Across 103 Windows |
| --- | --- | --- |
| **`B1_temporal_only`** | Baseline (`dt <= 15s`) | Emits `107,666` candidate temporal associations: **`18,130` unsubstantiated candidates** (held `unresolved` by MIRAGE-OT), **`66,706` explicit constraint conflicts** (eliminated by MIRAGE-OT), and `22,830` corroborated same-device pairs. |
| **`B2_protocol_only`** | Baseline (`COT=6/7/10`) | Applicable to `46 / 103` windows (`15` verified transitions); `NOT_APPLICABLE` to `57 / 103` no-command windows, omitting **`2,776` verified behavioral anchors**, **`23` Cross-RTU Bridges**, and **`134` network anomalies**. |
| **`A1_no_behavioral_gate`** | Counterfactual Ablation | All 103 windows: **`2,171` unsupported promotions** (`409` spurious bridges). **Sensitivity excluding `ev_52f5ee` (`N=102`)**: **`205` unsupported promotions** (`126` behavioral + `79` command-effect) and **`49` spurious bridges** across `51 / 102` windows. |
| **`A2_no_provenance_dedup`** | Counterfactual Ablation | `9,836` raw observations vs. `4,493` message/event containers: **`1,845` true cross-vantage mirror duplicates**, **`572` same-ASDU different IOA points**, **`2,262` IPAL records** (`4,679` true duplicate/derived inflations, `2.44x` mean factor), plus **`664` multi-event link/ARP anchor aggregations** (`268` same-session + `396` diff-time) and `0` unknown. |
| **`A3_no_incident_synthesis`** | Structural Ablation | Stops at `11,050` local storylines; omits `1,700` ASDU bundles, `23` Cross-RTU Bridges (`11` components), `143` candidate phases, and `161` competing explanations (`103/103` SQLite ID resolution, `102/103` full lineage consistency). |
| **`MIRAGE-OT (Full)`** | Complete Framework | `15` verified command transitions (`9/9` physical agreement in Basic), `23` Cross-RTU Bridges (`6/6` physical agreement in Basic), `51,597` unresolved branches preserved, `0` unsupported promotions, `1` lineage anomaly auto-withheld (`diagnostic_only_lineage_inconsistent`). |

---

## 3. Threats to Validity (Explicitly Addressed for Reviewers)

1. **Non-Equivalence of Internal Consistency, Evidence Coverage, and External Causal Accuracy**:
   - `Quality Consistency` (`100.0%`) and `Full Lineage Consistency` (`99.03%`) verify internal algorithmic and evidentiary self-consistency. `Cross-RTU Bridges` (`23`) and `Verified Transactions` (`15`) measure multi-source evidence coverage. Neither metric claims external causal-graph accuracy across distinct devices.
2. **Message Containers vs. Physical Sensors (`A2`)**:
   - Deduplicated source containers (`SRC-ASDU-...`, `SRC-MSG-...`) represent distinct network protocol messages or link/ARP event containers, **not** independent out-of-band physical sensors.
3. **Outlier Sensitivity & Window Dependence in Bootstrap Intervals (`A1`, `B1`)**:
   - Because consecutive windows sliced from the same Sherlock recording may share background grid state and violate i.i.d. assumptions, bootstrap 95% confidence intervals are reported strictly as **descriptive summaries of sample variability**, alongside median, P95, max, and the `N=102` outlier-excluded sensitivity analysis (`ev_52f5ee` excluded).
4. **Runtime Accounting Separation (`E4`)**:
   - Full pipeline runtime consists of shared evidence indexing (`Median 6.76s` Basic, `111.58s` Semiurban, `64.67s` Rural) and reconstruction + synthesis (`Median 0.66s` Basic, `14.04s` Semiurban, `7.74s` Rural; total `1,271.47s` across 103 windows). The `5.12s` (`2.66s` prior) runtime of `run_stage3.py` is **Stage 3 Cached Artifact Evaluation Time**, never conflated with end-to-end reconstruction runtime.
