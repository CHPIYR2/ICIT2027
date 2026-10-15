# Technical Design & Implementation: Evidence-Stratified Incident Synthesis

- **Status**: Implemented in `src/mirage_ot/etgi/reconstruction/synthesis.py` (base `2083eb7`)
- **Baseline Commit**: `2083eb76484f21a2db3b2d0c91c7a573fa077421`
- **Target Module**: `src/mirage_ot/etgi/reconstruction/synthesis.py`
- **Outputs**: `runs/etgi/synthesis-20261015/reconstruction/<episode_id>/incident_synthesis.json` & Section `2B` in `investigation_report.md`

---

## 1. Problem Statement & Motivation

After the Behavioral Reconstruction Refinement (Tasks 1–4), MIRAGE-OT produces verified local building blocks for no-command windows:
- **Verified Multi-Source Behavioral Storylines** (`behavioral_chain_with_supported_relations`): e.g. in `ev_564bebaa`, 5 transmission lines (`line.0`, `line.1`, `line.3`, `line.4`, `line.12`) whose `from` and `to` ends are reported by independent RTUs with matching measurement quantities, compatible change types/directions, decoded good quality (`IV=NT=SB=BL=OV=0`), clear test bits (`T=0`), and sustained post-change persistence (`>= 80%` across `>= 2` subsequent samples).
- **Verified Single-Anchor Storylines** (`behavioral_single_anchor`): e.g. bus de-energizations (`bus.5`, `bus.6`, `bus.4`), load drops (`load.3`, `load.4`, `load.2`), generator/storage drops (`sgen.1`, `sgen.2`, `sgen.3`, `sgen.9`, `storage.0`), open-terminal charging shift on `line.2` (`A011` and `A023`), and TCP/ARP link disruptions (`ev_812f80`, `ev_cbe1e5`).
- **Sequential Same-Entity Observations** (`same_entity_sequential_observation`): same-device anchor pairs in separate ASDUs that fail the behavioral consistency gate (e.g. `line.2` `A011 -> A023` due to `change_type_mismatch`; `sgen.0` `A001 -> A002` in `ev_4e913b` due to `no_prior_state_value_in_window`).
- **Unverified Observations** (`behavioral_unverified_observation`): observations retained for auditability but quarantined from supported spines due to missing pre-state baseline (`switch.13`, `switch.14`, `sgen.0:is_connected`) or transient post-sample oscillation (`A026`–`A032` in `ev_564bebaa`, `A003`–`A004` in `ev_4e913b`, `A005`–`A007` in `ev_cbe1e5`).

However, an operator reading 27 separate local storylines and 129 pairwise `cross_device_temporal_candidate` branches still faces an fragmented view. The goal of **Incident Synthesis** is to assemble local storylines into a higher-level **Incident Scenario** while strictly enforcing four invariants:
1. **No Causal or Topological Promotion from Co-occurrence**: Temporal proximity across distinct grid elements (`cross_device_temporal_candidate`) is never upgraded to `supported`, `observed_fact`, or `supported_inference`.
2. **Explicit Source-Dependency Accounting**: Observations carried in the same IEC-104 ASDU (`same_iec104_asdu`) or derived from IPAL (`temporal_correspondence`) are never double-counted as independent confirmations.
3. **Quarantine of Unverified Observations**: Anchors with `verification_status == "unverified_observation"` cannot anchor a confirmed scenario phase or bridge two verified storylines.
4. **Mandatory Competing / Alternative Explanations**: Every synthesized scenario must output explicit alternative explanations that remain consistent with the observed evidence.

---

## 2. Four-Layer Epistemic Architecture for Incident Synthesis

Incident Synthesis organizes a window's reconstruction outputs into four distinct layers:

```
+-----------------------------------------------------------------------------------+
| Layer 4: Scenario-Level Competing Explanations & Source-Dependency Ledger         |
|   - Explicit alternative hypotheses (H1, H2, H3...) + what evidence is missing    |
|   - Deduplicated container ledger: distinct RTUs, ASDUs, vantages, IPAL rows      |
+-----------------------------------------------------------------------------------+
                                         ^
                                         |
+-----------------------------------------------------------------------------------+
| Layer 3: Candidate Scenario Phases / Temporal Wavefronts (Unresolved Grouping)    |
|   - Groups non-bridged RTU bundles & single-anchor chains by temporal epoch       |
|   - Preserves `cross_device_temporal_candidate` and structural context            |
|     (shared RTU, shared master, ARP target overlap) as `unresolved`               |
+-----------------------------------------------------------------------------------+
                                         ^
                                         |
+-----------------------------------------------------------------------------------+
| Layer 2: Shared-Container RTU Bundles & Two-End Element Bridges                   |
|   - Groups anchors sharing one `SRC-ASDU-...` container (`same_iec104_asdu`)      |
|   - Bridges two RTU bundles ONLY when linked by a Layer-1 corroborated            |
|     same-device transition (`corroborated_same_device_behavioral_transition`)     |
+-----------------------------------------------------------------------------------+
                                         ^
                                         |
+-----------------------------------------------------------------------------------+
| Layer 1: Verified Local Behavioral Chains & Quarantined Unverified Observations   |
|   - 1A: Corroborated multi-ASDU chains (`behavioral_chain_with_supported_...`)    |
|   - 1B: Verified single-anchor chains (`behavioral_single_anchor`)                |
|   - 1C: Sequential same-entity observations (`same_entity_sequential_...`)        |
|   - 1D: Quarantined unverified observations (`behavioral_unverified_observation`) |
+-----------------------------------------------------------------------------------+
```

### 2.1 Layer 1: Local Storyline Partition
Input storylines are partitioned deterministically by `completeness_status`:
- **Partition 1A (`corroborated_chains`)**: `completeness_status in ("complete_with_verified_transition", "partial_missing_cot10_but_verified_measurement_transition", "behavioral_chain_with_supported_relations")`.
- **Partition 1B (`verified_single_anchors`)**: `completeness_status == "behavioral_single_anchor"`.
- **Partition 1C (`sequential_same_device_links`)**: `same_entity_sequential_observation` edges. These are attached as annotated non-supported links (`status="unverified"`, `failed_conditions=[...]`) between their endpoint storylines.
- **Partition 1D (`quarantined_unverified`)**: `completeness_status == "behavioral_unverified_observation"`. Stored in `scenario["quarantined_unverified_observations"]` and excluded from Layer 2 bridging and Layer 3 core wavefronts (except that `spontaneous_state_report` anchors with `no_prior_state_value_in_window` are listed in an explicit `unverified_precursor_reports` slot with their missing-baseline caveat).

### 2.2 Layer 2: Shared-Container RTU Bundles & Verified Element Bridges
In IEC-104 polling, one RTU often reports multiple grid elements in a single multi-object ASDU (`same_iec104_asdu`). Layer 2 constructs **RTU ASDU Bundles**:
- **Definition (`RTUBundle`)**:
  - `bundle_id`: `BND-001`, `BND-002`, ...
  - `asdu_container_id`: `SRC-ASDU-<src_ip>|<src_port>|<dst_ip>|<dst_port>|<apci_tx>|<asdu_index>`
  - `rtu_ip`: RTU IP address
  - `time`: ASDU timestamp
  - `member_anchor_ids`: all verified anchors carried in that ASDU
  - `member_entities`: e.g. `["bus.5:...", "line.3:...", "line.4:...", "load.3:..."]`
  - `independent_source_count`: `1` (regardless of how many elements are inside the ASDU or how many mirror ports captured it)
- **Verified Cross-RTU Element Bridges (`VerifiedElementBridge`)**:
  - Two RTU bundles $B_1$ (from RTU $r_1$) and $B_2$ (from RTU $r_2$, $r_1 \neq r_2$) are connected by a **Verified Element Bridge** if and only if a verified anchor $a_1 \in B_1$ and a verified anchor $a_2 \in B_2$ are linked by a Layer-1 `corroborated_same_device_behavioral_transition` edge on element $d$.
  - **What a Bridge Claims vs. Does Not Claim**:
    - *Claims (Supported)*: Element $d$ (e.g. `line.3`) is reported by both RTU $r_1$ (`.18`) and RTU $r_2$ (`.16`) as undergoing the same verified transition (`to_zero`).
    - *Does Not Claim (Kept Unresolved)*: It does **not** prove that `bus.5` or `load.3` (co-reported in $B_1$) caused `bus.4` or `load.2` (co-reported in $B_2$) to drop. Co-reported bundle members remain `shared_asdu_container_co_report`.

**Concrete Trace on `ev_564bebaa`**:
- **Component C1 (Multi-RTU De-energization Cluster bridged by Verified Line Transitions)**:
  - `BND-001` (+5.645s, RTU `.18`, 1 ASDU): `bus.5`, `line.3_to`, `line.4_from`, `load.3` (all `to_zero`).
  - `BND-002` (+7.772s, RTU `.22`, 1 ASDU): `bus.6`, `line.12_from`, `line.4_to`, `load.4` (all `to_zero`).
  - `BND-003` (+7.844s, RTU `.24`, 1 ASDU): `line.12_to` (`to_zero`).
  - `BND-004` (+10.695s, RTU `.16`, 1 ASDU): `bus.4`, `line.2_to`, `line.3_from`, `load.2` (`to_zero`).
  - **Verified Bridges**:
    - `BND-001 <--[line.4 corroborated to_zero]--> BND-002`
    - `BND-002 <--[line.12 corroborated to_zero]--> BND-003`
    - `BND-001 <--[line.3 corroborated to_zero]--> BND-004`
  - **Sequential (Non-Bridging) Link**:
    - `A011` (+6.784s, RTU `.14`, `line.2_from` `level_shift`) `--[same_entity_sequential_observation: change_type_mismatch]--> BND-004 (A023, line.2_to to_zero)`.
- **Component C2 (Multi-RTU Power Flow Increase Cluster)**:
  - `SL002` (`line.0`: RTU `.2.3` `active_power_from` and RTU `.3.13` `active_power_to` both +217% `level_shift`).
  - `SL008` (`line.1`: RTU `.3.13` `active_power_from` and RTU `.3.14` `active_power_to` both +214% `level_shift`).
  - Note: `A008` (`line.0_to`) and `A009` (`line.1_from`) are in the same ASDU from RTU `.3.13` (+6.551s, `same_iec104_asdu`), and `A010` (`line.1_to`) and `A011` (`line.2_from`) are in the same ASDU from RTU `.3.14` (+6.784s, `same_iec104_asdu`).

### 2.3 Layer 3: Candidate Scenario Phases & Structural Context
Verified bundles and single-anchor storylines that are not joined by a Layer-1 supported edge are organized into chronological **Candidate Scenario Phases** based on bounded time windows and structural context:
- **Context Types Allowed on Candidate Links (Never Upgraded to Supported)**:
  1. `shared_rtu_context`: Two observations originate from the same RTU IP in different ASDUs.
  2. `shared_master_context`: Multiple IEC-104 link disruptions share the same master IP (`172.16.1.2`, as in `ev_812f80` and `ev_cbe1e5`).
  3. `arp_target_address_overlap_context`: An `arp_activity_increase` anchor from host $H$ targets the exact RTU IPs whose IEC-104 links subsequently fail (`ev_cbe1e5`: ARP from `172.16.3.28` sends 63, 2, and 62 replies to `.10`, `.20`, and `.9` within 15s before their IEC-104 sessions drop).
  4. `temporal_wavefront_cooccurrence`: Distinct RTUs report `to_zero` or `level_shift` steps within the same 15s horizon (e.g. `sgen.1`, `sgen.3`, `storage.0`, `sgen.2`, `sgen.9` dropping `to_zero` between `+7.66s` and `+9.75s` in `ev_564bebaa`).

### 2.4 Layer 4: Source-Dependency Ledger & Deterministic Competing Explanations
Every synthesized scenario must include:
1. **`source_dependency_ledger`**:
   - `independent_network_containers`: list and count of unique `SRC-ASDU-...` / `SRC-...` containers across verified anchors.
   - `distinct_rtu_ips`: list and count of unique RTU IPs contributing verified anchors.
   - `vantage_captures_total`: raw mirror packet capture count (`n302` + `n318`).
   - `co_reported_elements_collapsed`: count of anchor facts that share an ASDU container with another anchor fact (preventing multi-IOA fan-out from inflating confidence).
   - `ipal_correspondences_excluded`: count of IPAL `temporal_correspondence` rows (explicitly weighted `0` in source counting).
2. **`competing_scenario_explanations`**:
   - Rather than picking a single narrative or attack label, the synthesizer outputs a structured table of candidate interpretations, listing for each:
     - `explanation_id` (`EXP-1`, `EXP-2`, ...)
     - `consistent_with_verified_evidence`: which Layer-1/2 facts it accounts for
     - `unverified_links_required`: which unresolved branches or missing baselines would have to hold
     - `missing_disambiguating_evidence`: what external evidence (e.g. grid topology map, relay trip records, switch pre-event state, L2 switch CAM/port logs) would be required to confirm or refute it.

---

## 3. Planned Output Schema (`incident_synthesis.json`)

```json
{
  "synthesis_version": "1.0-design",
  "window": {"start": 1742922604.1942136, "end": 1742922784.4018285},
  "epistemic_guarantees": {
    "promotes_cooccurrence_to_supported": false,
    "counts_same_asdu_as_independent": false,
    "counts_ipal_as_independent": false,
    "allows_unverified_anchors_in_supported_bridges": false
  },
  "source_dependency_ledger": {
    "verified_anchor_count": 23,
    "quarantined_unverified_anchor_count": 9,
    "independent_asdu_container_count": 12,
    "distinct_rtu_count": 12,
    "co_reported_fact_reduction": 11,
    "ipal_correspondence_count_excluded": 33
  },
  "rtu_asdu_bundles": [...],
  "verified_element_bridges": [...],
  "sequential_same_device_links": [...],
  "candidate_scenario_phases": [...],
  "unverified_precursor_reports": [...],
  "quarantined_unverified_observations": [...],
  "competing_scenario_explanations": [...]
}
```

---

## 4. Planned Consistency & Verification Checks for Incident Synthesis

When Incident Synthesis is implemented in the next round, `check_quality_consistency()` will verify four synthesis invariants:
1. **No Fabricated Support (`synthesis_no_new_supported_edges`)**: Every `VerifiedElementBridge` in `incident_synthesis.json` must reference an existing `corroborated_same_device_behavioral_transition` edge in `event_graph.json` that passed `evaluate_behavioral_relation_consistency()`.
2. **Quarantine Preservation (`synthesis_unverified_quarantine_intact`)**: No anchor with `verification_status == "unverified_observation"` may appear in `rtu_asdu_bundles` or `verified_element_bridges`.
3. **Container Accounting Exactness (`synthesis_source_ledger_exact`)**: `independent_asdu_container_count` must equal the exact cardinality of unique `SRC-ASDU-...` / `SRC-...` containers across verified anchors, never the number of anchors or vantages.
4. **Candidate Non-Promotion (`synthesis_candidate_links_unresolved`)**: Every cross-device link in `candidate_scenario_phases` must retain `verification_status == "unresolved"` and `causal_status == "not_established"`.

---

## 5. Pre-Implementation Reliability Hardening & Real Window Synthesis Results

### 5.1 Three Pre-Synthesis Reliability Fixes
1. **`_merge_iec_vantages()` (`anchors.py`)**: Merges two IEC-104 object rows only when they arrive on **strictly distinct vantages** (`vantage not in inst["vantage_times"]`) within `0.5 s` and pass `_vantage_payload_consistent()` across value, quality descriptors, and COT flags. Same-vantage independent packets or cross-vantage conflicting payloads are never merged and receive distinct disambiguated `asdu_key`s (`#pkt2`, ...); cross-vantage payload conflicts set `cross_vantage_conflict=True` (`post_cross_vantage_payload_conflict`).
2. **`_obs_quality_fields()` (`anchors.py`)**: Checks `_REQUIRED_QUALITY_BITS` (`("iv", "nt", "sb", "bl")` for state types and `("iv", "nt", "sb", "bl", "ov")` for measurement types). Whenever any required bit is missing or `None`, `quality_flags_unknown=True` and `quality_good=None`, even if `quality_invalid=False` or `quality_good=True` was supplied in the payload.
3. **Dual Quality + Lineage Gate on Final Report (`report.py`)**: `apply_quality_consistency(report, quality_consistency, lineage_consistency)` requires both `quality_consistency["consistent"]` and `lineage_consistency["consistent"]`. Failure of either downgrades `report_status` to `diagnostic_only_quality_inconsistent`, `diagnostic_only_lineage_inconsistent`, or `diagnostic_only_quality_and_lineage_inconsistent`, withholding verified transitions, supported chains, and `verified_element_bridges`.

### 5.2 Real Window Synthesis Results (`runs/etgi/synthesis-20261015/reconstruction/`)

| Window | Layer 1 Partition | Layer 2 Bundles & Verified Bridges | Layer 3 Candidate Phases | Layer 4 Source Ledger & Competing Explanations |
| --- | --- | --- | --- | --- |
| `ev_564bebaa` | `5` supported multi-node, `13` verified single-anchor, `3` sequential (`R0134`, `R0211`, `R0212`), `9` quarantined unverified (`2` COT=3 precursors `A001`, `A007`) | `12` RTU ASDU bundles (`independent_source_count=1` each), `5` verified element bridges (`BRG-001`..`BRG-005` on `line.0`, `line.3`, `line.4`, `line.1`, `line.12`), `2` bridged components (`CMP-001`, `CMP-002`) | `PHS-001` (`+0.896s`..`+10.695s`, `multi_rtu_corroborated_measurement_transitions`, `129` unresolved candidates) | `12` independent ASDU containers across `12` RTUs (`11` same-ASDU co-reported points collapsed), `62` IPAL rows (`weight=0`); `EXP-001` (physical switching/protection cascade) vs `EXP-002` (uncommanded/altered multi-RTU telemetry) |
| `ev_cbe1e5` | `0` supported multi-node, `4` verified single-anchor (`A001` ARP + `A002`..`A004` links), `0` sequential, `3` quarantined unverified (`A005`..`A007`) | `4` bundles, **`0` verified element bridges**, `0` bridged components | `PHS-001` (`+1.381s`..`+128.208s`, `arp_burst_and_multi_rtu_iec104_link_disruptions`, ARP target overlap `['172.16.3.10', '172.16.3.20', '172.16.3.9']`, `7` unresolved candidates) | `4` independent containers across `3` RTUs + ARP host `172.16.3.28`, `3` IPAL rows (`weight=0`); `EXP-001` (ARP cache interference preceding session loss) vs `EXP-002` (concurrent L2 link disturbance with ARP re-resolution) |
| `ev_4e913b` | `0` supported multi-node, `1` verified single-anchor (`A002`), `1` sequential (`R0035`), `3` quarantined (`1` COT=3 precursor `A001`) | `1` bundle (`BND-001` on `sgen.0:active_power`), `0` bridges | `PHS-001` (`+1.187s`..`+10.839s`, `localized_measurement_or_state_observations`, `0` unresolved candidates) | `1` ASDU container on RTU `172.16.3.15`, `4` IPAL rows (`weight=0`); `EXP-001` vs `EXP-002` |
| `ev_812f80` | `0` supported multi-node, `2` verified single-anchor (`A001`, `A002` links), `0` quarantined | `2` bundles (RTUs `.22`, `.23`), `0` bridges | `PHS-001` (`+0.0s`..`+124.618s`, `multi_rtu_iec104_link_disruptions`, `1` unresolved candidate `R0029`) | `2` containers across `2` RTUs sharing master `172.16.1.2`; `EXP-001` vs `EXP-002` |

