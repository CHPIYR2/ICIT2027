# Stage 2 Frozen Cross-Scenario Experiment Results (`01-Basic`, `02-Semiurban`, `03-Rural`)

- **Frozen Engine Commit (`git_commit`)**: `2981fb062b127218a34f23f2ff0292e4ca8cfea7`
- **Reconstruction Code Hash (`code_sha256`)**: `d43d9867ce847df169e13345e4c3461cd99fd5167292a85cedaaa553d93e5bb3`
- **Evidence Layer Code Hash (`evidence_code_sha256`)**: `032c6977ac0507e9c442b37e4e78455d0ab6d1a21b1efe751a0ccf37242a3b85`
- **Method Freeze Manifest**: `configs/etgi/method_freeze.v1.json` (zero parameter or rule changes across all 103 windows)
- **Batch Runner**: `scripts/run_stage2_cross_scenario_experiment.py`
- **Full Stage 2 Output Directory**: `runs/etgi/stage2-cross-scenario-frozen-20261015/`
- **Public Review Artifacts**: `review_artifacts/stage2-cross-scenario-frozen-20261015/`

---

## 1. Epistemic Distinction: Internal Consistency vs. Evidence Coverage vs. External Ground-Truth Accuracy

In accordance with the MIRAGE-OT evaluation protocol, all metrics reported in this document are strictly stratified into three distinct epistemic categories and **must never be conflated**:

1. **Internal Consistency (`Quality Consistency` & `Lineage Consistency`)**:
   - Measures whether the deterministic reconstruction phases (Transactions, Anchors, Temporal Graph, Storylines, Incident Synthesis, and Report) obey the frozen consistency gates and whether every cited `evidence_id` resolves to a valid database row matching the claimed entity, point (`ca_ioa`), host, and sample timestamp window.
   - A `100%` consistency pass rate proves **internal algorithmic and evidentiary self-consistency**, **NOT** external reconstruction accuracy.
2. **Evidence Coverage & Multi-Source Corroboration (`Verified Transactions`, `Verified Anchors`, `Supported Storylines`, `Cross-RTU Bridges`)**:
   - Measures how many protocol transactions or behavioral transitions in the raw telemetry satisfy the frozen pre/post baseline, quality descriptor (`IV/NT/SB/BL/OV=0`), test bit (`T=0`), post-sample persistence ($\ge 80\%$ across $\ge 2$ samples), and cross-RTU complementarity criteria.
   - Higher counts of anchors or storylines in long or high-traffic windows reflect telemetry volume or quarantined attack oscillations, **never** higher reconstruction accuracy.
3. **External Ground-Truth Reconstruction Accuracy (Not Claimed from Unlabeled Telemetry)**:
   - Because official Sherlock event labels (`events.json`), attack names, `malicious` flags, and `physical.zip` are strictly excluded from the pipeline and no external physical bus-branch topology model is provided, cross-device causal accuracy is not claimed; all cross-device links without direct protocol or same-element evidence remain `unresolved` (`causal_status = "not_established"`).

---

## 2. Unified Cross-Scenario Comparison (`01-Basic` vs. `02-Semiurban` vs. `03-Rural`)

### 2.1 Primary Cross-Scenario Summary Table (All 103 Test Windows)

| Metric | `01-Basic` (`test`) | `02-Semiurban` (`test`) | `03-Rural` (`test`) | Total / Combined (103 Windows) |
| --- | --- | --- | --- | --- |
| **Window Count** | `28` | `39` | `36` | **`103`** |
| **Mapped Data Points (`data-point-map.json`)** | `500` (`4` mirror PCAPs) | `3,640` (`6` mirror PCAPs) | `1,908` (`8` mirror PCAPs) | `500`–`3,640` |
| **Verified Transactions (`Tot` / `Acc` / `Ver`)** | `9` verified (`419` tot / `419` acc across `6` windows) | `3` verified (`370` tot / `370` acc across `3` windows) | `3` verified (`534` tot / `534` acc across `3` windows) | **`15` verified** (`1,323` tot / `1,323` acc across `12` windows) |
| **Verified Anchors (`Ver` / `Tot`, `Unv` quarantined)** | `160` / `1,447` (`1,287` unv) | `1,564` / `7,413` (`5,849` unv) | `1,069` / `4,167` (`3,098` unv) | **`2,793` / `13,027`** (`10,234` unv) |
| **Supported Multi-Node Storylines (`Sup` / `Tot`)** | `15` / `1,270` (`40` ver single) | `15` / `5,518` (`961` ver single) | `11` / `4,262` (`832` ver single) | **`41` / `11,050`** (`1,833` ver single) |
| **Cross-RTU Verified Element Bridges (`Bridges` / `Bundles`)** | **`6` bridges** (`36` bundles, `3` components in `2` windows) | **`6` bridges** (`910` bundles, `2` components in `2` windows) | **`11` bridges** (`754` bundles, `6` components in `2` windows) | **`23` bridges** (`1,700` bundles, `11` components in `6` windows) |
| **Unresolved Cross-Device Branches (`unresolved`)** | `4,186` | `27,768` | `19,643` | **`51,597`** |
| **Sequential Same-Device Observations (Gate Failed)** | `1,976` | `71` | `45` | **`2,092`** |
| **Quality Consistency Pass Rate** | **`28 / 28` (`100.0%`)** | **`39 / 39` (`100.0%`)** | **`36 / 36` (`100.0%`)** | **`103 / 103` (`100.0%`)** |
| **Lineage Consistency Pass Rate** | **`28 / 28` (`100.0%`)** | **`38 / 39` (`97.44%`)** (1 window auto-downgraded to `diagnostic_only`) | **`36 / 36` (`100.0%`)** | **`102 / 103` (`99.03%`)** |
| **Honest Abstention Breakdown** | `2` full abstention (`0` ver anc/tx); `10` unverified-cmd-only; `8` single-source; `8` multi-source | `1` full abstention (`ev_8e3ee4`); `12` unverified-cmd-only; `21` single-source; `5` multi-source | `0` full abstention; `11` unverified-cmd-only; `20` single-source; `5` multi-source | `3` full abstention; `33` unverified-cmd-only; `49` single-source; `18` multi-source |
| **Execution Failures (Software / Crash / Hash Mismatch)** | **`0 / 28`** | **`0 / 39`** | **`0 / 36`** | **`0 / 103` (`0.0%`)** |
| **Mean / Median Window Runtime (`Idx + Rec`)** | Mean `6.57s` / Med `7.88s` (Rec: Mean `0.91s` / Med `0.66s`) | Mean `124.14s` / Med `136.23s` (Rec: Mean `21.24s` / Med `14.04s`) | Mean `77.26s` / Med `80.28s` (Rec: Mean `11.61s` / Med `7.74s`) | Stage 2 Process End-to-End Wall Clock: `1,237.35s` (`20.62 min`, 6 workers) |
| **Storage Usage (`SQLite + Artifacts`)** | **`770.36 MiB`** (`547.44` + `222.92 MiB`) | **`8,459.98 MiB`** (`7,736.66` + `723.33 MiB`) | **`4,997.40 MiB`** (`4,450.57` + `546.84 MiB`) | **`14,227.74 MiB` (`13.89 GiB`)** |

---

### 2.2 Per-Window Distribution Statistics (`Sum`, `Mean`, `Median`, `P95`, `Max`)

Because a few long-duration or high-oscillation attack windows can dominate totals, the table below reports the per-window `Mean`, `Median`, `P95`, and `Max` across all three scenarios:

| Metric | `01-Basic` (`N=28`) | `02-Semiurban` (`N=39`) | `03-Rural` (`N=36`) |
| --- | --- | --- | --- |
| **Transactions Total** | Sum `419` (Mean `14.964`, Med `1.0`, P95 `89.0`, Max `180`) | Sum `370` (Mean `9.487`, Med `0.0`, P95 `89.0`, Max `177`) | Sum `534` (Mean `14.833`, Med `0.0`, P95 `89.0`, Max `185`) |
| **Verified Transitions (Tx)** | Sum `9` (Mean `0.321`, Med `0.0`, P95 `2.0`, Max `3`) | Sum `3` (Mean `0.077`, Med `0.0`, P95 `1.0`, Max `1`) | Sum `3` (Mean `0.083`, Med `0.0`, P95 `1.0`, Max `1`) |
| **Anchors Total** | Sum `1,447` (Mean `51.679`, Med `11.5`, P95 `254.0`, Max `675`) | Sum `7,413` (Mean `190.077`, Med `106.0`, P95 `672.0`, Max `752`) | Sum `4,167` (Mean `115.75`, Med `47.5`, P95 `438.0`, Max `487`) |
| **Verified Anchors** | Sum `160` (Mean `5.714`, Med `4.0`, P95 `18.0`, Max `23`) | Sum `1,564` (Mean `40.103`, Med `30.0`, P95 `119.0`, Max `123`) | Sum `1,069` (Mean `29.694`, Med `17.0`, P95 `114.0`, Max `117`) |
| **Quarantined Unverified Anchors** | Sum `1,287` (Mean `45.964`, Med `5.0`, P95 `243.0`, Max `671`) | Sum `5,849` (Mean `149.974`, Med `26.0`, P95 `618.0`, Max `682`) | Sum `3,098` (Mean `86.056`, Med `20.5`, P95 `384.0`, Max `431`) |
| **Storylines Total** | Sum `1,270` (Mean `45.357`, Med `6.0`, P95 `180.0`, Max `675`) | Sum `5,518` (Mean `141.487`, Med `23.0`, P95 `648.0`, Max `672`) | Sum `4,262` (Mean `118.389`, Med `58.0`, P95 `438.0`, Max `487`) |
| **Supported Multi-Node Storylines** | Sum `15` (Mean `0.536`, Med `0.0`, P95 `3.0`, Max `5`) | Sum `15` (Mean `0.385`, Med `0.0`, P95 `2.0`, Max `9`) | Sum `11` (Mean `0.306`, Med `0.0`, P95 `4.0`, Max `4`) |
| **RTU ASDU Bundles** | Sum `36` (Mean `1.286`, Med `0.0`, P95 `5.0`, Max `12`) | Sum `910` (Mean `23.333`, Med `4.0`, P95 `80.0`, Max `95`) | Sum `754` (Mean `20.944`, Med `3.0`, P95 `68.0`, Max `86`) |
| **Cross-RTU Bridges** | Sum `6` (Mean `0.214`, Med `0.0`, P95 `1.0`, Max `5`) | Sum `6` (Mean `0.154`, Med `0.0`, P95 `1.0`, Max `5`) | Sum `11` (Mean `0.306`, Med `0.0`, P95 `4.0`, Max `7`) |
| **Unresolved Cross-Device Branches** | Sum `4,186` (Mean `149.5`, Med `0.0`, P95 `129.0`, Max `3998`) | Sum `27,768` (Mean `712.0`, Med `12.0`, P95 `3622.0`, Max `3707`) | Sum `19,643` (Mean `545.639`, Med `8.5`, P95 `2420.0`, Max `2698`) |
| **Indexing Time (`s`)** | Sum `158.584` (Mean `5.664`, Med `6.758`, P95 `10.106`, Max `10.457`) | Sum `4,013.058` (Mean `102.899`, Med `111.58`, P95 `169.193`, Max `180.589`) | Sum `2,363.544` (Mean `65.654`, Med `64.672`, P95 `102.407`, Max `105.658`) |
| **Reconstruction + Synthesis Time (`s`)** | Sum `25.346` (Mean `0.905`, Med `0.657`, P95 `2.443`, Max `2.563`) | Sum `828.309` (Mean `21.239`, Med `14.036`, P95 `58.515`, Max `79.007`) | Sum `417.813` (Mean `11.606`, Med `7.736`, P95 `28.632`, Max `38.102`) |
| **Total Window Time (`s`)** | Sum `183.93` (Mean `6.569`, Med `7.875`, P95 `12.199`, Max `12.549`) | Sum `4,841.367` (Mean `124.138`, Med `136.228`, P95 `196.984`, Max `239.104`) | Sum `2,781.357` (Mean `77.26`, Med `80.278`, P95 `123.863`, Max `131.039`) |
| **SQLite Size (`MiB`)** | Sum `547.443` (Mean `19.552`, Med `15.945`, P95 `45.223`, Max `46.668`) | Sum `7,736.653` (Mean `198.376`, Med `138.746`, P95 `459.262`, Max `638.191`) | Sum `4,450.565` (Mean `123.627`, Med `85.867`, P95 `273.328`, Max `348.531`) |
| **Artifacts Size (`MiB`)** | Sum `222.926` (Mean `7.962`, Med `2.067`, P95 `7.797`, Max `154.273`) | Sum `723.328` (Mean `18.547`, Med `6.818`, P95 `77.871`, Max `88.202`) | Sum `546.84` (Mean `15.19`, Med `7.564`, P95 `53.139`, Max `58.536`) |
| **Worker Peak RSS (`MiB`)** | N/A (single-process Stage 1) | Sum `65,888.55` (Mean `1689.45`, Med `1866.78`, P95 `2429.25`, Max `3269.61`) | Sum `71,490.65` (Mean `1985.851`, Med `2043.47`, P95 `2429.25`, Max `2429.25`) |

---

## 3. Key Cross-Scenario Findings

1. **Zero-Modification Generalization of Cross-RTU Verified Element Bridges**:
   - Without changing a single parameter or rule from `configs/etgi/method_freeze.v1.json`, the frozen Behavioral Consistency Gate (`evaluate_behavioral_relation_consistency`) and Layer 2 Synthesis (`_build_verified_element_bridges`) discovered corroborated two-end transmission line transitions across distinct RTUs in both new scenarios:
     - **`02-Semiurban` (`6` Cross-RTU Bridges in `2` windows)**:
       - `#11 ev_c77d85a14214995d2a2e`: `BRG-001` on `line.44` across RTUs `172.16.8.9` and `172.16.8.6`.
       - `#31 ev_d3c46672f9814dcdc40c`: `BRG-001`..`BRG-004` on `line.6` across RTUs `172.16.7.7` and `172.16.7.1`, and `BRG-005` on `line.7` across RTUs `172.16.7.7` and `172.16.7.12`.
     - **`03-Rural` (`11` Cross-RTU Bridges in `2` windows)**:
       - `#02 ev_bdac022dece4728f5d4e`: `BRG-001` on `line.37` (`172.16.8.1 <-> 172.16.7.1`), `BRG-002` on `line.43` (`172.16.3.10 <-> 172.16.3.9`), `BRG-003` on `line.41` (`172.16.3.7 <-> 172.16.3.8`), and `BRG-004` on `line.42` (`172.16.3.8 <-> 172.16.3.9`).
       - `#33 ev_0d966f97d1922adb09bb`: `7` Cross-RTU Bridges across `line.57` (`172.16.9.8 <-> 172.16.9.7`), `line.100` (`172.16.11.3 <-> 172.16.11.1`), `line.98` (`172.16.11.2 <-> 172.16.10.1`), and `line.56` (`172.16.9.6 <-> 172.16.9.7`).
2. **Zero-Modification Generalization of Protocol Transaction Verification**:
   - In **`02-Semiurban`**, `3` control-command windows passed all pre/post state, quality, test-bit, and `COT=7` `P/N=0` checks: `#02 ev_229f54b33cd3bfeb8f67` (`switch.335:closed`), `#03 ev_a50c6019708978b4f2a5` (`switch.150:closed`), and `#36 ev_08003d46b7fce7995131` (`load.73:connected`).
   - In **`03-Rural`**, `3` control-command windows passed all checks: `#18 ev_33a53478089ef5a96639` (`sgen.34:connected`), `#27 ev_7e55a0045a505982b278` (`switch.193:closed`), and `#31 ev_02f636fa1aedfa7539fe` (`switch.34:connected`).
3. **Real-World Validation of the Dual Quality + Lineage Consistency Gate (`ev_5dd0102bf58bf2ce9487`)**:
   - In `02-Semiurban` `#25 ev_5dd0102bf58bf2ce9487`, `quality_consistency` passed (`True`), but `audit_anchor_lineage()` flagged `1` row check failure on unverified anchor `A007` (`switch.48:is_closed`, `evidence_id = EV-6e9e7ece8bf456f0`, `reason = "time_outside_cited_sample"`) because a mirror packet on switch `n495` arrived slightly after the `COT=3` timestamp on `n406`.
   - As designed, `apply_quality_consistency()` refused to mark the report verified and automatically downgraded `ev_5dd0102bf58bf2ce9487` to `report_status = "diagnostic_only_lineage_inconsistent"` (`scenario_status = "diagnostic_only_withheld"`), demonstrating that the lineage gate catches cross-switch timestamp skew in larger 6-switch networks without silent pass-through.

---

## 4. Complete 39-Window Master Table for `02-Semiurban` (`test`)

| # | Episode ID | Stratum | Dur (s) | Tx `Tot (Ver/Unv/NoChg)` | Anchors `Tot (Ver/Unv)` | Storylines `Tot (Sup/VSgl/PUnv/BUnv)` | Bundles / Bridges (`Comp`) | Unres / Seq | QC / LC | Abstention / Component Status | Idx / Rec (s) | Size / RSS (MiB) |
| --- | --- | --- | ---: | --- | --- | --- | --- | ---: | --- | --- | ---: | ---: |
| 01 | `ev_54ead6013ea77949d028` | `S3` | `136.4` | `0 (0/0/0)` | `132 (66/66)` | `132 (0/66/0/66)` | `63 / 0 (0)` | `725 / 1` | `Pass / Pass` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `23.1 / 6.72` | `112.3` / `532` |
| 02 | `ev_229f54b33cd3bfeb8f67` | `S1` | `358.4` | `1 (1/0/0)` | `577 (67/510)` | `5 (1/0/4/0)` | `0 / 0 (0)` | `0 / 0` | `Pass / Pass` | `MULTI_SOURCE_CORROBORATED` | `34.7 / 27.00` | `239.4` / `1266` |
| 03 | `ev_a50c6019708978b4f2a5` | `S1` | `181.6` | `30 (1/0/29)` | `244 (123/121)` | `30 (1/0/29/0)` | `0 / 0 (0)` | `0 / 0` | `Pass / Pass` | `MULTI_SOURCE_CORROBORATED` | `30.3 / 11.70` | `132.3` / `712` |
| 04 | `ev_f17d7aaa4b87b7bebbc8` | `S1` | `390.5` | `4 (0/4/0)` | `26 (10/16)` | `6 (0/0/6/0)` | `0 / 0 (0)` | `0 / 0` | `Pass / Pass` | `PARTIAL:COMMANDS_OBSERVED_NO_VERIFIED_TRANSITION` | `42.9 / 22.89` | `260.7` / `1376` |
| 05 | `ev_b147bd0bb6df32a938c3` | `S3` | `153.4` | `0 (0/0/0)` | `12 (5/7)` | `12 (0/5/0/7)` | `5 / 0 (0)` | `16 / 0` | `Pass / Pass` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `33.8 / 8.56` | `110.6` / `601` |
| 06 | `ev_48d9fc078aff4e136a46` | `S1` | `64.0` | `3 (0/2/1)` | `17 (7/10)` | `6 (0/0/6/0)` | `0 / 0 (0)` | `0 / 0` | `Pass / Pass` | `PARTIAL:COMMANDS_OBSERVED_NO_VERIFIED_TRANSITION` | `34.6 / 4.42` | `61.2` / `350` |
| 07 | `ev_bbfa5beb48621263dda4` | `S4` | `485.8` | `0 (0/0/0)` | `392 (67/325)` | `392 (0/67/0/325)` | `66 / 0 (0)` | `2192 / 0` | `Pass / Pass` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `57.0 / 35.51` | `370.2` / `1699` |
| 08 | `ev_f7bce2b07965f3d54423` | `S1` | `678.9` | `177 (0/0/177)` | `752 (70/682)` | `177 (0/0/177/0)` | `0 / 0 (0)` | `0 / 0` | `Pass / Pass` | `PARTIAL:COMMANDS_OBSERVED_NO_VERIFIED_TRANSITION` | `75.4 / 79.01` | `476.0` / `2429` |
| 09 | `ev_221c449c4efc18c42997` | `S3` | `495.1` | `0 (0/0/0)` | `508 (62/446)` | `508 (0/62/0/446)` | `58 / 0 (0)` | `2830 / 0` | `Pass / Pass` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `68.0 / 40.97` | `394.7` / `1759` |
| 10 | `ev_4ef53124e3e1f5eea2ac` | `S1` | `30.1` | `1 (0/1/0)` | `5 (4/1)` | `5 (0/0/5/0)` | `0 / 0 (0)` | `0 / 0` | `Pass / Pass` | `PARTIAL:COMMANDS_OBSERVED_NO_VERIFIED_TRANSITION` | `51.3 / 2.79` | `42.1` / `601` |
| 11 | `ev_c77d85a14214995d2a2e` | `S2` | `170.9` | `0 (0/0/0)` | `22 (15/7)` | `21 (1/13/0/7)` | `9 / 1 (1)` | `75 / 4` | `Pass / Pass` | `MULTI_SOURCE_CORROBORATED` | `62.1 / 11.38` | `136.6` / `1266` |
| 12 | `ev_2f4098e1cd5c479e3b6d` | `S3` | `124.2` | `0 (0/0/0)` | `106 (68/38)` | `106 (0/68/0/38)` | `65 / 0 (0)` | `575 / 0` | `Pass / Pass` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `63.6 / 8.51` | `114.7` / `1376` |
| 13 | `ev_f9c57c15a205a5e8c49a` | `S4` | `595.6` | `0 (0/0/0)` | `630 (67/563)` | `630 (0/67/0/563)` | `64 / 0 (0)` | `3559 / 1` | `Pass / Pass` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `88.8 / 52.49` | `481.7` / `2137` |
| 14 | `ev_50b143b3c49e56cb4c57` | `S1` | `30.1` | `1 (0/0/1)` | `10 (0/10)` | `6 (0/0/6/0)` | `0 / 0 (0)` | `0 / 0` | `Pass / Pass` | `PARTIAL:COMMANDS_OBSERVED_NO_VERIFIED_TRANSITION` | `65.5 / 2.82` | `42.4` / `601` |
| 15 | `ev_52e918c1a93310b4c12a` | `S4` | `556.6` | `0 (0/0/0)` | `263 (30/233)` | `263 (0/30/0/233)` | `28 / 0 (0)` | `1367 / 1` | `Pass / Pass` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `96.6 / 45.64` | `422.2` / `2050` |
| 16 | `ev_0c08ce74d40931b74df0` | `S2` | `326.3` | `0 (0/0/0)` | `23 (9/14)` | `23 (0/9/0/14)` | `4 / 0 (0)` | `34 / 1` | `Pass / Pass` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `85.7 / 22.46` | `242.3` / `1376` |
| 17 | `ev_8e3ee44aec0a0f81c99a` | `S4` | `496.4` | `0 (0/0/0)` | `20 (0/20)` | `20 (0/0/0/20)` | `0 / 0 (0)` | `12 / 1` | `Pass / Pass` | `ABSTAIN:NO_VERIFIED_ANCHOR_OR_COMMAND` | `101.1 / 35.13` | `351.6` / `1867` |
| 18 | `ev_0e94985baec0b6585ae1` | `S3` | `122.1` | `0 (0/0/0)` | `7 (4/3)` | `7 (0/4/0/3)` | `4 / 0 (0)` | `8 / 0` | `Pass / Pass` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `84.3 / 8.71` | `102.4` / `601` |
| 19 | `ev_c25a5999cc26b9797acc` | `S2` | `558.9` | `0 (0/0/0)` | `566 (66/500)` | `566 (0/66/0/500)` | `65 / 0 (0)` | `3144 / 5` | `Pass / Pass` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `113.5 / 50.58` | `449.0` / `2429` |
| 20 | `ev_8fd579d965e1e1604416` | `S3` | `595.4` | `0 (0/0/0)` | `648 (30/618)` | `648 (0/30/0/618)` | `30 / 0 (0)` | `3622 / 6` | `Pass / Pass` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `120.5 / 39.80` | `491.9` / `2128` |
| 21 | `ev_d2eff99482b1195f73f5` | `S1` | `31.5` | `3 (0/3/0)` | `20 (12/8)` | `6 (0/0/6/0)` | `0 / 0 (0)` | `0 / 0` | `Pass / Pass` | `PARTIAL:COMMANDS_OBSERVED_NO_VERIFIED_TRANSITION` | `99.3 / 3.17` | `44.8` / `2137` |
| 22 | `ev_5fbea088e70b34749755` | `S4` | `547.5` | `0 (0/0/0)` | `21 (1/20)` | `21 (0/1/0/20)` | `1 / 0 (0)` | `7 / 0` | `Pass / Pass` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `129.3 / 39.29` | `393.4` / `2037` |
| 23 | `ev_9dfa79bb5bae1913a995` | `S3` | `132.6` | `0 (0/0/0)` | `8 (3/5)` | `8 (0/3/0/5)` | `3 / 0 (0)` | `5 / 0` | `Pass / Pass` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `111.6 / 9.39` | `111.2` / `603` |
| 24 | `ev_eda32c84a9cf2952b292` | `S3` | `105.1` | `0 (0/0/0)` | `40 (15/25)` | `40 (0/15/0/25)` | `15 / 0 (0)` | `189 / 0` | `Pass / Pass` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `112.5 / 8.24` | `97.5` / `2050` |
| 25 | `ev_5dd0102bf58bf2ce9487` | `S3` | `186.8` | `0 (0/0/0)` | `240 (119/121)` | `231 (9/101/0/121)` | `95 / 0 (0)` | `1354 / 19` | `Pass / Fail` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `121.0 / 15.22` | `177.3` / `1867` |
| 26 | `ev_4b50c491e75756bdb5bd` | `S2` | `181.9` | `0 (0/0/0)` | `176 (76/100)` | `176 (0/76/0/100)` | `71 / 0 (0)` | `974 / 3` | `Pass / Pass` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `122.5 / 13.79` | `161.6` / `2137` |
| 27 | `ev_5ce1ef963d55b4d4f117` | `S1` | `46.1` | `2 (0/2/0)` | `9 (4/5)` | `6 (0/0/6/0)` | `0 / 0 (0)` | `0 / 0` | `Pass / Pass` | `PARTIAL:COMMANDS_OBSERVED_NO_VERIFIED_TRANSITION` | `118.9 / 4.21` | `54.1` / `2429` |
| 28 | `ev_a32eb40b8189d88ad8d3` | `S3` | `489.5` | `0 (0/0/0)` | `23 (5/18)` | `23 (0/5/0/18)` | `5 / 0 (0)` | `19 / 1` | `Pass / Pass` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `146.4 / 34.86` | `350.6` / `1797` |
| 29 | `ev_ce4748a6aff3395edf43` | `S1` | `30.1` | `1 (0/1/0)` | `18 (11/7)` | `6 (0/0/6/0)` | `0 / 0 (0)` | `0 / 0` | `Pass / Pass` | `PARTIAL:COMMANDS_OBSERVED_NO_VERIFIED_TRANSITION` | `128.6 / 3.12` | `43.1` / `2050` |
| 30 | `ev_6c0f0f93854fcaf4ca4e` | `S1` | `178.7` | `89 (0/0/89)` | `254 (78/176)` | `89 (0/0/89/0)` | `0 / 0 (0)` | `0 / 0` | `Pass / Pass` | `PARTIAL:COMMANDS_OBSERVED_NO_VERIFIED_TRANSITION` | `141.1 / 16.93` | `146.0` / `2037` |
| 31 | `ev_d3c46672f9814dcdc40c` | `S2` | `173.3` | `0 (0/0/0)` | `219 (94/125)` | `216 (2/89/0/125)` | `80 / 5 (1)` | `1220 / 25` | `Pass / Pass` | `MULTI_SOURCE_CORROBORATED` | `143.9 / 13.78` | `163.7` / `1867` |
| 32 | `ev_fa8e045e341a6397db03` | `S2` | `178.9` | `0 (0/0/0)` | `202 (67/135)` | `202 (0/67/0/135)` | `66 / 0 (0)` | `1149 / 0` | `Pass / Pass` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `146.2 / 14.04` | `163.2` / `2137` |
| 33 | `ev_6fdcfece5fea8e89e47d` | `S3` | `441.9` | `0 (0/0/0)` | `12 (2/10)` | `12 (0/2/0/10)` | `2 / 0 (0)` | `5 / 0` | `Pass / Pass` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `164.6 / 32.39` | `320.1` / `2429` |
| 34 | `ev_f2346d953482ad8cc899` | `S1` | `30.1` | `1 (0/1/0)` | `108 (100/8)` | `6 (0/0/6/0)` | `0 / 0 (0)` | `0 / 0` | `Pass / Pass` | `PARTIAL:COMMANDS_OBSERVED_NO_VERIFIED_TRANSITION` | `145.4 / 3.29` | `43.2` / `2050` |
| 35 | `ev_6182d95c34d95866f8b1` | `S3` | `940.7` | `0 (0/0/0)` | `672 (58/614)` | `672 (0/58/0/614)` | `56 / 0 (0)` | `3707 / 3` | `Pass / Pass` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `180.6 / 58.52` | `726.4` / `3270` |
| 36 | `ev_08003d46b7fce7995131` | `S1` | `220.5` | `55 (1/0/54)` | `201 (62/139)` | `55 (1/0/54/0)` | `0 / 0 (0)` | `0 / 0` | `Pass / Pass` | `MULTI_SOURCE_CORROBORATED` | `167.4 / 18.73` | `172.2` / `1797` |
| 37 | `ev_93d8f2c53c21004efb91` | `S2` | `194.5` | `0 (0/0/0)` | `174 (57/117)` | `174 (0/57/0/117)` | `55 / 0 (0)` | `980 / 0` | `Pass / Pass` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `169.2 / 15.73` | `171.5` / `2037` |
| 38 | `ev_a7b10ddd06141f5ac6a8` | `S1` | `30.1` | `1 (0/0/1)` | `56 (30/26)` | `6 (0/0/6/0)` | `0 / 0 (0)` | `0 / 0` | `Pass / Pass` | `PARTIAL:COMMANDS_OBSERVED_NO_VERIFIED_TRANSITION` | `163.7 / 3.22` | `43.0` / `1867` |
| 39 | `ev_0431e34c3ed30056a8f0` | `S1` | `30.1` | `1 (0/0/1)` | `0 (0/0)` | `6 (0/0/6/0)` | `0 / 0 (0)` | `0 / 0` | `Pass / Pass` | `PARTIAL:COMMANDS_OBSERVED_NO_VERIFIED_TRANSITION` | `167.9 / 3.31` | `42.8` / `2137` |

---

## 5. Complete 36-Window Master Table for `03-Rural` (`test`)

| # | Episode ID | Stratum | Dur (s) | Tx `Tot (Ver/Unv/NoChg)` | Anchors `Tot (Ver/Unv)` | Storylines `Tot (Sup/VSgl/PUnv/BUnv)` | Bundles / Bridges (`Comp`) | Unres / Seq | QC / LC | Abstention / Component Status | Idx / Rec (s) | Size / RSS (MiB) |
| --- | --- | --- | ---: | --- | --- | --- | --- | ---: | --- | --- | ---: | ---: |
| 01 | `ev_d547da0be440532c580e` | `S1` | `30.1` | `1 (0/0/1)` | `1 (0/1)` | `3 (0/0/3/0)` | `0 / 0 (0)` | `0 / 0` | `Pass / Pass` | `PARTIAL:COMMANDS_OBSERVED_NO_VERIFIED_TRANSITION` | `15.8 / 1.01` | `21.7` / `154` |
| 02 | `ev_bdac022dece4728f5d4e` | `S2` | `172.7` | `0 (0/0/0)` | `183 (117/66)` | `179 (4/109/0/66)` | `68 / 4 (2)` | `1021 / 6` | `Pass / Pass` | `MULTI_SOURCE_CORROBORATED` | `26.1 / 6.40` | `92.3` / `2429` |
| 03 | `ev_f684bbfff5711a74db7d` | `S3` | `108.2` | `0 (0/0/0)` | `103 (13/90)` | `103 (0/13/0/90)` | `13 / 0 (0)` | `555 / 0` | `Pass / Pass` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `26.8 / 4.10` | `59.0` / `2050` |
| 04 | `ev_94386ab3184c46c62ce3` | `S4` | `970.5` | `0 (0/0/0)` | `124 (56/68)` | `124 (0/56/0/68)` | `55 / 0 (0)` | `450 / 2` | `Pass / Pass` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `65.3 / 26.18` | `368.3` / `1782` |
| 05 | `ev_a0511b88a60de51f8897` | `S1` | `30.2` | `1 (0/1/0)` | `8 (6/2)` | `6 (0/0/6/0)` | `0 / 0 (0)` | `0 / 0` | `Pass / Pass` | `PARTIAL:COMMANDS_OBSERVED_NO_VERIFIED_TRANSITION` | `29.4 / 1.57` | `23.1` / `2429` |
| 06 | `ev_906c24cffc08c5783c45` | `S1` | `697.8` | `185 (0/0/185)` | `47 (12/35)` | `185 (0/0/185/0)` | `0 / 0 (0)` | `0 / 0` | `Pass / Pass` | `PARTIAL:COMMANDS_OBSERVED_NO_VERIFIED_TRANSITION` | `52.9 / 38.10` | `289.4` / `2050` |
| 07 | `ev_daad548a60ebf4e219bc` | `S4` | `577.9` | `0 (0/0/0)` | `438 (54/384)` | `438 (0/54/0/384)` | `52 / 0 (0)` | `2420 / 0` | `Pass / Pass` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `53.8 / 26.98` | `272.9` / `2429` |
| 08 | `ev_23f7515ecdcec934ecdb` | `S3` | `450.9` | `0 (0/0/0)` | `375 (29/346)` | `375 (0/29/0/346)` | `27 / 0 (0)` | `2064 / 0` | `Pass / Pass` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `51.8 / 20.64` | `223.6` / `1867` |
| 09 | `ev_54f129e565141b49466d` | `S3` | `122.1` | `0 (0/0/0)` | `10 (7/3)` | `10 (0/7/0/3)` | `7 / 0 (0)` | `21 / 0` | `Pass / Pass` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `43.3 / 5.00` | `61.1` / `1797` |
| 10 | `ev_26f6b1b85d08903c561b` | `S2` | `535.1` | `0 (0/0/0)` | `15 (1/14)` | `15 (0/1/0/14)` | `1 / 0 (0)` | `8 / 0` | `Pass / Pass` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `59.3 / 20.51` | `221.6` / `2037` |
| 11 | `ev_0a8313d6fdba7a8267af` | `S3` | `578.1` | `0 (0/0/0)` | `354 (47/307)` | `354 (0/47/0/307)` | `45 / 0 (0)` | `1846 / 5` | `Pass / Pass` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `62.5 / 26.31` | `275.4` / `1797` |
| 12 | `ev_87eb044f38bd34bc8e99` | `S1` | `30.2` | `1 (0/0/1)` | `0 (0/0)` | `5 (0/0/5/0)` | `0 / 0 (0)` | `0 / 0` | `Pass / Pass` | `PARTIAL:COMMANDS_OBSERVED_NO_VERIFIED_TRANSITION` | `46.6 / 1.63` | `25.1` / `2050` |
| 13 | `ev_dde1f49547c99a8a79f2` | `S4` | `477.8` | `0 (0/0/0)` | `387 (54/333)` | `387 (0/54/0/333)` | `52 / 0 (0)` | `2155 / 1` | `Pass / Pass` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `63.5 / 22.42` | `245.0` / `2137` |
| 14 | `ev_0fcf5733c917a90df27c` | `S3` | `117.5` | `0 (0/0/0)` | `48 (23/25)` | `48 (0/23/0/25)` | `23 / 0 (0)` | `227 / 0` | `Pass / Pass` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `53.2 / 4.70` | `62.7` / `1867` |
| 15 | `ev_0de1984956bcba353145` | `S3` | `138.2` | `0 (0/0/0)` | `11 (5/6)` | `11 (0/5/0/6)` | `5 / 0 (0)` | `12 / 1` | `Pass / Pass` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `56.3 / 5.61` | `67.6` / `2429` |
| 16 | `ev_06ea9a17a9417b83c52b` | `S3` | `325.4` | `0 (0/0/0)` | `10 (2/8)` | `10 (0/2/0/8)` | `2 / 0 (0)` | `1 / 0` | `Pass / Pass` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `64.1 / 12.19` | `143.9` / `2037` |
| 17 | `ev_e30a4fd4382a52400f75` | `S2` | `179.0` | `0 (0/0/0)` | `146 (60/86)` | `146 (0/60/0/86)` | `55 / 0 (0)` | `808 / 3` | `Pass / Pass` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `61.1 / 7.21` | `100.8` / `2050` |
| 18 | `ev_33a53478089ef5a96639` | `S1` | `219.6` | `55 (1/0/54)` | `175 (50/125)` | `55 (1/0/54/0)` | `0 / 0 (0)` | `0 / 0` | `Pass / Pass` | `MULTI_SOURCE_CORROBORATED` | `63.7 / 9.04` | `103.9` / `1867` |
| 19 | `ev_424b7c55b138714f4e57` | `S3` | `555.1` | `0 (0/0/0)` | `487 (56/431)` | `487 (0/56/0/431)` | `55 / 0 (0)` | `2698 / 1` | `Pass / Pass` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `70.8 / 19.13` | `287.4` / `1148` |
| 20 | `ev_6545a8576a07a2c06b5c` | `S1` | `30.5` | `3 (0/3/0)` | `13 (9/4)` | `6 (0/0/6/0)` | `0 / 0 (0)` | `0 / 0` | `Pass / Pass` | `PARTIAL:COMMANDS_OBSERVED_NO_VERIFIED_TRANSITION` | `61.9 / 1.75` | `26.3` / `2429` |
| 21 | `ev_17a23404248cd549e2d8` | `S3` | `533.2` | `0 (0/0/0)` | `6 (1/5)` | `6 (0/1/0/5)` | `1 / 0 (0)` | `0 / 0` | `Pass / Pass` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `81.7 / 20.41` | `233.5` / `1797` |
| 22 | `ev_7cafdb049b6397dab355` | `S1` | `63.2` | `3 (0/2/1)` | `29 (13/16)` | `6 (0/0/6/0)` | `0 / 0 (0)` | `0 / 0` | `Pass / Pass` | `PARTIAL:COMMANDS_OBSERVED_NO_VERIFIED_TRANSITION` | `67.0 / 2.81` | `39.8` / `2137` |
| 23 | `ev_0b718baa9850dc39693e` | `S3` | `135.4` | `0 (0/0/0)` | `107 (35/72)` | `107 (0/35/0/72)` | `35 / 0 (0)` | `582 / 0` | `Pass / Pass` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `70.9 / 5.56` | `78.7` / `2037` |
| 24 | `ev_a9fae32d1b8c5ad5da48` | `S3` | `132.4` | `0 (0/0/0)` | `108 (50/58)` | `108 (0/50/0/58)` | `49 / 0 (0)` | `588 / 0` | `Pass / Pass` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `72.9 / 5.31` | `77.6` / `2050` |
| 25 | `ev_5e80443dc92f14ac1b03` | `S1` | `181.8` | `46 (0/0/46)` | `9 (3/6)` | `46 (0/0/46/0)` | `0 / 0 (0)` | `0 / 0` | `Pass / Pass` | `PARTIAL:COMMANDS_OBSERVED_NO_VERIFIED_TRANSITION` | `76.4 / 7.60` | `92.4` / `2429` |
| 26 | `ev_7218e5e493c665c9ed93` | `S1` | `177.8` | `89 (0/0/89)` | `2 (1/1)` | `89 (0/0/89/0)` | `0 / 0 (0)` | `0 / 0` | `Pass / Pass` | `PARTIAL:COMMANDS_OBSERVED_NO_VERIFIED_TRANSITION` | `77.5 / 8.41` | `91.3` / `1867` |
| 27 | `ev_7e55a0045a505982b278` | `S1` | `185.7` | `61 (1/0/60)` | `49 (24/25)` | `61 (1/0/60/0)` | `0 / 0 (0)` | `0 / 0` | `Pass / Pass` | `MULTI_SOURCE_CORROBORATED` | `79.9 / 8.08` | `93.5` / `2137` |
| 28 | `ev_83372cb93af73e03771f` | `S3` | `460.7` | `0 (0/0/0)` | `151 (61/90)` | `151 (0/61/0/90)` | `60 / 0 (0)` | `730 / 0` | `Pass / Pass` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `91.7 / 19.22` | `219.7` / `2037` |
| 29 | `ev_555b785446049d6b5667` | `S1` | `46.1` | `2 (0/2/0)` | `87 (82/5)` | `6 (0/0/6/0)` | `0 / 0 (0)` | `0 / 0` | `Pass / Pass` | `PARTIAL:COMMANDS_OBSERVED_NO_VERIFIED_TRANSITION` | `81.9 / 2.42` | `33.7` / `1797` |
| 30 | `ev_affcf9589116c90a0824` | `S3` | `580.4` | `0 (0/0/0)` | `436 (57/379)` | `436 (0/57/0/379)` | `57 / 0 (0)` | `2412 / 0` | `Pass / Pass` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `102.4 / 28.63` | `303.5` / `2050` |
| 31 | `ev_02f636fa1aedfa7539fe` | `S1` | `170.8` | `85 (1/0/84)` | `36 (21/15)` | `85 (1/0/84/0)` | `0 / 0 (0)` | `0 / 0` | `Pass / Pass` | `MULTI_SOURCE_CORROBORATED` | `91.8 / 7.87` | `90.6` / `2429` |
| 32 | `ev_bd163f5a88c87c1fca09` | `S3` | `507.0` | `0 (0/0/0)` | `14 (4/10)` | `14 (0/4/0/10)` | `4 / 0 (0)` | `9 / 0` | `Pass / Pass` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `105.7 / 18.20` | `232.3` / `1867` |
| 33 | `ev_0d966f97d1922adb09bb` | `S2` | `180.5` | `0 (0/0/0)` | `187 (114/73)` | `183 (4/106/0/73)` | `86 / 7 (4)` | `1035 / 26` | `Pass / Pass` | `MULTI_SOURCE_CORROBORATED` | `94.3 / 7.41` | `112.9` / `2137` |
| 34 | `ev_56f6a02bdb6cd6262ef2` | `S1` | `30.1` | `1 (0/1/0)` | `3 (0/3)` | `4 (0/0/4/0)` | `0 / 0 (0)` | `0 / 0` | `Pass / Pass` | `PARTIAL:COMMANDS_OBSERVED_NO_VERIFIED_TRANSITION` | `88.1 / 1.25` | `26.6` / `1797` |
| 35 | `ev_0ed0845aa71a77f06ba3` | `S1` | `30.2` | `1 (0/0/1)` | `0 (0/0)` | `5 (0/0/5/0)` | `0 / 0 (0)` | `0 / 0` | `Pass / Pass` | `PARTIAL:COMMANDS_OBSERVED_NO_VERIFIED_TRANSITION` | `77.6 / 1.01` | `27.0` / `2037` |
| 36 | `ev_3855d8c61d1bd55fa074` | `S3` | `599.4` | `0 (0/0/0)` | `8 (2/6)` | `8 (0/2/0/6)` | `2 / 0 (0)` | `1 / 0` | `Pass / Pass` | `PARTIAL:SINGLE_SOURCE_VERIFIED_NO_BRIDGE` | `75.6 / 13.13` | `273.3` / `2050` |
