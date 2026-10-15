# Evidence-Grounded Incident Reconstruction Report

- **Report Status**: `quality_consistent`
- **Quality & Behavioral Consistency (`quality_consistency.json`)**: `consistent`
- **Evidence Lineage Audit (`lineage_consistency.json`)**: `consistent`

- **Incident Window**: `1742933403.2674494` to `1742933529.526473`
- **Reconstructed IEC-104 Transactions**: `0`
- **Reconstructed Event Storylines**: `6`
- **Verified Same-Device Transitions (Consistency Gate Passed)**: `0`
- **Unverified Protocol State Reports (Value Undecoded or No Pre-Baseline)**: `0`
- **LLM Claim Verifier Output (Separate from Graph Gate)**: `0` verified, `0` withheld

## 1. Incident Sequence & Protocol Transactions
- No IEC-104 control transactions were observed in this window.

## 2A. Behavioral Incident Reconstruction (No Control Command)
- Method: `evidence_anchor_discovery`. Inputs not used: `['official event labels', 'attack type', 'malicious flags', 'physical.zip']`. Control objects in window: `0`.
- `2` event anchors (`2` verified, `0` unverified), `2` behavioral storylines (`0` with corroborated multi-ASDU transitions, `2` verified single-anchor, `0` unverified observations), `0` sequential same-entity observations (gate failed), `1` unresolved cross-device branches.

### 2A.1 Event Anchors (by time)
- **A001** (rank `1`, `communication_change`, `verified_observation`, +`0.0`s, RTU `172.16.3.22`): IEC-104 link 172.16.1.2 <-> 172.16.3.22: clock_synchronisation_cot6 x1, clock_synchronisation_cot7 x1, connection_attempt_unanswered x34, connection_established x1, general_interrogation_cot10 x1, general_interrogation_cot6 x1, general_interrogation_cot7 x1, tcp_fin x4, telemetry_gap x1; first at 1742933403.267 (verification=verified_observation).
- **A002** (rank `2`, `communication_change`, `verified_observation`, +`14.96`s, RTU `172.16.3.23`): IEC-104 link 172.16.1.2 <-> 172.16.3.23: clock_synchronisation_cot6 x1, clock_synchronisation_cot7 x1, connection_attempt_unanswered x36, connection_established x1, general_interrogation_cot10 x1, general_interrogation_cot6 x1, general_interrogation_cot7 x1; first at 1742933418.228 (verification=verified_observation).

### 2A.2 Behavioral Storylines
#### SL001 — anchors `['A001']` (+`0.0`s, status=`behavioral_single_anchor`)
- **Reconstructed**: [A001] IEC-104 link 172.16.1.2 <-> 172.16.3.22: clock_synchronisation_cot6 x1, clock_synchronisation_cot7 x1, connection_attempt_unanswered x34, connection_established x1, general_interrogation_cot10 x1, general_interrogation_cot6 x1, general_interrogation_cot7 x1, tcp_fin x4, telemetry_gap x1; first at 1742933403.267 (verification=verified_observation).
- **Evidence-supported relations**: none (single anchor)
- **Candidate relations (unresolved, time proximity only; 1)**: R0029: -> 172.16.1.2<->172.16.3.23:2404/IEC104 (@+14.96s)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL002 — anchors `['A002']` (+`14.96`s, status=`behavioral_single_anchor`)
- **Reconstructed**: [A002] IEC-104 link 172.16.1.2 <-> 172.16.3.23: clock_synchronisation_cot6 x1, clock_synchronisation_cot7 x1, connection_attempt_unanswered x36, connection_established x1, general_interrogation_cot10 x1, general_interrogation_cot6 x1, general_interrogation_cot7 x1; first at 1742933418.228 (verification=verified_observation).
- **Evidence-supported relations**: none (single anchor)
- **Candidate relations (unresolved, time proximity only; 1)**: R0029: 172.16.1.2<->172.16.3.22:2404/IEC104 (@+0.0s) ->
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.

## 2B. Incident Scenario Synthesis (Four-Layer Epistemic Integration)
- **Scenario Status**: `synthesized_consistent`
- **Layer 1 Partition**: `0` supported multi-node chains, `2` verified single-anchor chains, `0` sequential same-entity observations (gate failed), `0` quarantined unverified observations (`0` unverified COT=3 precursor reports).
- **Layer 2 Bundles & Bridges**: `2` source bundles (each counted as `1` container), `0` cross-RTU verified element bridges, `0` same-RTU supported relations (not cross-RTU support), `0` multi-bundle bridged components.
- **Layer 3 Candidate Phases**: `1` candidate scenario phases (all cross-device links kept `unresolved`).
- **Layer 4 Source Dependency Ledger**: `0` IEC-104 ASDU, `2` TCP link, `0` ARP, `0` composite containers across `2` RTU(s) (`['172.16.3.22', '172.16.3.23']`), `0` co-reported same-ASDU points collapsed, mirror vantages `[]`, `0` IPAL rows excluded (`weight=0`).

### 2B.1 Layer 2 — RTU ASDU Bundles & Verified Element Bridges
- **BND-001** (`+0.0s`, RTU `172.16.3.22`, container=`SRC-COMMUNICATION_CHANGE-172.16.1.2<->172.16.3.22:2404/IEC104`, independent_sources=`1`): anchors `['A001']` -> `['172.16.1.2<->172.16.3.22:2404/IEC104']`.
- **BND-002** (`+14.96s`, RTU `172.16.3.23`, container=`SRC-COMMUNICATION_CHANGE-172.16.1.2<->172.16.3.23:2404/IEC104`, independent_sources=`1`): anchors `['A002']` -> `['172.16.1.2<->172.16.3.23:2404/IEC104']`.
- **Cross-RTU Verified Element Bridges**: `none`.

### 2B.2 Layer 3 — Candidate Scenario Phases (Cross-Device Links Unresolved)
- **PHS-001** (`+0.0s`..`+124.618s`, profile=`multi_rtu_iec104_link_disruptions`): bundles=`['BND-001', 'BND-002']`, verified_bridges=`[]`, sequential_same_device=`[]`, unverified_precursors=`[]`, RTUs=`['172.16.3.22', '172.16.3.23']`, ARP=`[]`, unresolved_candidates=`1`.

### 2B.3 Layer 4 — Evidence-Anchored Competing Explanations & Missing Evidence
- **EXP-001** (`shared_master_or_path_iec104_session_interruption_hypothesis`, status=`unresolved_competing_hypothesis`, causal_status=`not_established`): IEC-104 sessions to RTUs ['172.16.3.22', '172.16.3.23'] (['A001', 'A002']) sharing master ['172.16.1.2'] experienced telemetry gaps, TCP FIN teardown, repeated unanswered SYN attempts, and subsequent re-establishment with General Interrogation (COT=6/7/10/20) and Clock Synchronisation (COT=6/7).
  - **Anchored by**: `{'communication_anchor_ids': ['A001', 'A002'], 'affected_rtu_ips': ['172.16.3.22', '172.16.3.23'], 'shared_master_ips': ['172.16.1.2'], 'evidence_ids': ['EV-35b6b6baef5a1648', 'EV-3e777acdeb712c42', 'EV-ad1210245bcd4ebd', 'EV-0e9d37abdca9c3c3', 'EV-c960837f9a6fe62b', 'EV-4217cddd505acc34']}`
  - **Unverified/candidate links required**: `['R0029']`
  - **Alternative comparison**: Competes with independent RTU-side daemon/interface restarts on ['172.16.3.22', '172.16.3.23'] occurring within the same 15s window (candidate link ['R0029'] remains unresolved).
  - **Missing disambiguating evidence**: `['Switch port drop/ACL counters between master 172.16.1.2 and RTU subnet', "Host/RTU daemon logs on 172.16.1.2 and ['172.16.3.22', '172.16.3.23']"]`
- **EXP-002** (`independent_rtu_endpoint_unavailability_cooccurrence_hypothesis`, status=`unresolved_competing_hypothesis`, causal_status=`not_established`): Each RTU link in ['A001', 'A002'] (['172.16.3.22', '172.16.3.23']) independently refused master TCP SYN attempts before recovering and completing General Interrogation and Clock Synchronisation, without requiring a shared network-fabric fault.
  - **Anchored by**: `{'communication_anchor_ids': ['A001', 'A002'], 'affected_rtu_ips': ['172.16.3.22', '172.16.3.23'], 'evidence_ids': ['EV-35b6b6baef5a1648', 'EV-3e777acdeb712c42', 'EV-ad1210245bcd4ebd', 'EV-0e9d37abdca9c3c3', 'EV-c960837f9a6fe62b', 'EV-4217cddd505acc34']}`
  - **Alternative comparison**: Does not assume a common upstream cause across the two RTUs; keeps the cross-link temporal candidate ['R0029'] unresolved.
  - **Missing disambiguating evidence**: `["Local RTU OS/service restart logs on ['172.16.3.22', '172.16.3.23']", 'Per-port L2 link-down counters on the RTU access switch']`

## 2. Key Findings & Reconstructed Storylines (Contiguous Directed Spines)
### SL003 — Anchor `line.14:current_from` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`26`)
- Step 1 [R0015 | P-P | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL013 (line.14:current_from @ 1742933407.8582) -> TL018 (line.14:current_to @ 1742933408.8582) [src_ev=EV-cea3ed522cc75923, EV-184ffecba308e365; dst_ev=EV-3206942a14240dda, EV-0e0bb6ca703d4225]
### SL004 — Anchor `line.14:current_from` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`52`)
- Step 1 [R0014 | N-N | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL009 (line.14:current_from @ 1742933407.673) -> TL021 (line.14:current_to @ 1742933408.6221) [src_ev=EV-e561b52da21ceda4, EV-218efa89d142c524; dst_ev=EV-31ba455fe90e42c1, EV-d86918c33ec2e33d]
- Time-aligned IPAL row [R0007 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL013 (line.14:current_from=0.007824240252375603 @ 1742933407.8582) aligned with TL009; not an independent source
- Time-aligned IPAL row [R0011 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL018 (line.14:current_to=-0.11318999528884888 @ 1742933408.8582) aligned with TL021; not an independent source
### SL005 — Anchor `line.9:active_power_from` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`26`)
- Step 1 [R0018 | P-P | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL016 (line.9:active_power_from @ 1742933408.8582) -> TL017 (line.9:active_power_to @ 1742933408.8582) [src_ev=EV-d4e2a7f3eeda201d, EV-61fcb628e4c48154; dst_ev=EV-892c43fbd67330ac, EV-66a37ec431e4c23f]
### SL006 — Anchor `line.9:active_power_from` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`52`)
- Step 1 [R0017 | N-N | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL022 (line.9:active_power_from @ 1742933408.0725) -> TL012 (line.9:active_power_to @ 1742933408.5566) [src_ev=EV-ba033b86f608b976, EV-60efb92307837731; dst_ev=EV-2f8bf0ee2fc6c1c1, EV-255ab60223c226c9]
- Time-aligned IPAL row [R0009 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL016 (line.9:active_power_from=-106657.78125 @ 1742933408.8582) aligned with TL022; not an independent source
- Time-aligned IPAL row [R0010 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL017 (line.9:active_power_to=110909.96875 @ 1742933408.8582) aligned with TL012; not an independent source

## 3. Observed Network & Electrical Impact (Epistemically Stratified)
### 3.1 Verified Same-Device Measurement/State Transitions (Consistency Gate Passed)
- No post-command device transition passed all pre/post and target consistency checks.

### 3.2 Protocol State Reports Observed Without Verified Transition (Value Undecoded or No Pre-Baseline)
- None.

### 3.3 Candidate Cross-Entity Co-occurring Changes (Unresolved Hypotheses, Not Causal Proof)
- [SL001 / R0029 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): 172.16.1.2<->172.16.3.23:2404/IEC104 (BA002) at 1742933418.2277 after BA001 (0 <= dt (14.96s) <= 15.0s) [src_ev=EV-35b6b6baef5a1648, EV-3e777acdeb712c42; dst_ev=EV-0e9d37abdca9c3c3, EV-c960837f9a6fe62b].
- [SL003 / R0022 | cross_entity_temporal_cooccurrence] (level=temporal_cooccurrence, status=unresolved, gate=unresolved_cooccurrence, causal_status=not_established): line.13:current_from (TL019) at 1742933407.8582 after TL013 (0 <= dt (0.0s) <= 2.0s) [src_ev=EV-cea3ed522cc75923, EV-184ffecba308e365; dst_ev=EV-a356bf771e22ab6c, EV-2bfc83d16239a0b7].
- [SL003 / R0023 | cross_entity_temporal_cooccurrence] (level=temporal_cooccurrence, status=unresolved, gate=unresolved_cooccurrence, causal_status=not_established): bus.9:active_power (TL020) at 1742933407.8582 after TL013 (0 <= dt (0.0s) <= 2.0s) [src_ev=EV-cea3ed522cc75923, EV-184ffecba308e365; dst_ev=EV-0aad070da2cd8dfa, EV-2d917696f7068b3a].
- [SL003 / R0024 | cross_entity_temporal_cooccurrence] (level=temporal_cooccurrence, status=unresolved, gate=unresolved_cooccurrence, causal_status=not_established): line.9:active_power_from (TL016) at 1742933408.8582 after TL013 (0 <= dt (1.0s) <= 2.0s) [src_ev=EV-cea3ed522cc75923, EV-184ffecba308e365; dst_ev=EV-d4e2a7f3eeda201d, EV-61fcb628e4c48154].
- [SL003 / R0025 | cross_entity_temporal_cooccurrence] (level=temporal_cooccurrence, status=unresolved, gate=unresolved_cooccurrence, causal_status=not_established): line.9:active_power_to (TL017) at 1742933408.8582 after TL013 (0 <= dt (1.0s) <= 2.0s) [src_ev=EV-cea3ed522cc75923, EV-184ffecba308e365; dst_ev=EV-892c43fbd67330ac, EV-66a37ec431e4c23f].

## 4. Alternative Explanations & Competing Hypotheses
- **[SL003 | competing_cross_entity_cooccurrences | status=`unresolved`]**: Multiple distinct grid measurements (line.13:current_from, bus.9:active_power, line.9:active_power_from, line.9:active_power_to) changed within the time horizon after line.14:current_from. Without an independent physical topology/power-flow model in the loop, these remain competing unresolved temporal co-occurrences rather than confirmed causal effects.

## 5. Unresolved Questions, Evidence Gaps & Unattached Observations
- **Unattached Observations (`16` nodes not on a storyline spine)**:
  - `TL001` (`1742933403.3615`, `network`, `communication`): `172.16.3.11:2404->172.16.1.2:39462/TCP` (`not_on_confirmed_storyline_spine`) [`EV-279846de97602ae1, EV-d6b2485b62227ad2`]
  - `TL002` (`1742933403.3876`, `network`, `communication`): `172.16.1.2:39462->172.16.3.11:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-9e792c4ae987b451, EV-60c6459fdeb0df9d`]
  - `TL008` (`1742933403.4858`, `network`, `communication`): `172.16.3.10:2404->172.16.1.2:56094/TCP` (`not_on_confirmed_storyline_spine`) [`EV-f141cde667636e03, EV-8ff4c3eca671d279`]
  - `TL025` (`1742933403.5260`, `network`, `communication`): `172.16.1.2:56094->172.16.3.10:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-9870a834bb77d719, EV-d953f00c63354e54`]
  - `TL010` (`1742933405.5464`, `network`, `electrical_report`): `bus.0:voltage_angle` (`not_on_confirmed_storyline_spine`) [`EV-7ef166dce4e5e570, EV-41d1389f5c80b756`]
  - `TL014` (`1742933405.8582`, `electrical`, `electrical_change`): `bus.0:voltage_angle` (`not_on_confirmed_storyline_spine`) [`EV-05fc2312b91dcd24, EV-4208e550799677dd`]
  - `TL023` (`1742933407.1332`, `network`, `electrical_report`): `line.13:current_from` (`not_on_confirmed_storyline_spine`) [`EV-2b7cac122365197c, EV-a62e6c17e69df4de`]
  - `TL024` (`1742933407.7281`, `network`, `electrical_report`): `bus.9:active_power` (`not_on_confirmed_storyline_spine`) [`EV-c38f3bdc5342edc8, EV-9ed2d34131dabd1a`]
  - `TL019` (`1742933407.8582`, `electrical`, `electrical_change`): `line.13:current_from` (`not_on_confirmed_storyline_spine`) [`EV-a356bf771e22ab6c, EV-2bfc83d16239a0b7`]
  - `TL020` (`1742933407.8582`, `electrical`, `electrical_change`): `bus.9:active_power` (`not_on_confirmed_storyline_spine`) [`EV-0aad070da2cd8dfa, EV-2d917696f7068b3a`]
