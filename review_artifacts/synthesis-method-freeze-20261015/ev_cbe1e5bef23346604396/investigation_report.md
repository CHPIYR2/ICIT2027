# Evidence-Grounded Incident Reconstruction Report

- **Report Status**: `quality_consistent`
- **Quality & Behavioral Consistency (`quality_consistency.json`)**: `consistent`
- **Evidence Lineage Audit (`lineage_consistency.json`)**: `consistent`

- **Incident Window**: `1742953785.268002` to `1742953913.4897654`
- **Reconstructed IEC-104 Transactions**: `0`
- **Reconstructed Event Storylines**: `7`
- **Verified Same-Device Transitions (Consistency Gate Passed)**: `0`
- **Unverified Protocol State Reports (Value Undecoded or No Pre-Baseline)**: `0`
- **LLM Claim Verifier Output (Separate from Graph Gate)**: `0` verified, `0` withheld

## 1. Incident Sequence & Protocol Transactions
- No IEC-104 control transactions were observed in this window.

## 2A. Behavioral Incident Reconstruction (No Control Command)
- Method: `evidence_anchor_discovery`. Inputs not used: `['official event labels', 'attack type', 'malicious flags', 'physical.zip']`. Control objects in window: `0`.
- `7` event anchors (`4` verified, `3` unverified), `7` behavioral storylines (`0` with corroborated multi-ASDU transitions, `4` verified single-anchor, `3` unverified observations), `0` sequential same-entity observations (gate failed), `7` unresolved cross-device branches.

### 2A.1 Event Anchors (by time)
- **A001** (rank `4`, `arp_activity_increase`, `verified_observation`, +`1.381`s, RTU `None`): ARP from 172.16.3.28: 127 packets in window (2 requests, 125 replies) to ['172.16.3.10', '172.16.3.20', '172.16.3.9']; 0 in background (verification=verified_observation).
- **A002** (rank `1`, `communication_change`, `verified_observation`, +`7.522`s, RTU `172.16.3.10`): IEC-104 link 172.16.1.2 <-> 172.16.3.10: clock_synchronisation_cot6 x1, clock_synchronisation_cot7 x1, connection_attempt_unanswered x35, connection_established x2, general_interrogation_cot10 x1, general_interrogation_cot6 x1, general_interrogation_cot7 x1, tcp_fin x5, tcp_reset x1, telemetry_gap x1; first at 1742953792.79 (verification=verified_observation).
- **A003** (rank `3`, `communication_change`, `verified_observation`, +`8.102`s, RTU `172.16.3.20`): IEC-104 link 172.16.1.2 <-> 172.16.3.20: clock_synchronisation_cot6 x1, clock_synchronisation_cot7 x1, connection_attempt_unanswered x8, connection_established x1, general_interrogation_cot10 x1, general_interrogation_cot6 x1, general_interrogation_cot7 x1, telemetry_gap x1; first at 1742953793.37 (verification=verified_observation).
- **A004** (rank `2`, `communication_change`, `verified_observation`, +`14.83`s, RTU `172.16.3.9`): IEC-104 link 172.16.1.2 <-> 172.16.3.9: clock_synchronisation_cot6 x1, clock_synchronisation_cot7 x1, connection_attempt_unanswered x35, connection_established x2, general_interrogation_cot10 x1, general_interrogation_cot6 x1, general_interrogation_cot7 x1, tcp_fin x5, tcp_reset x1; first at 1742953800.098 (verification=verified_observation).
- **A005** (rank `5`, `measurement_step`, `unverified_observation`, +`29.737`s, RTU `172.16.3.11`): line.11: 1 measurement(s) in one ASDU from RTU 172.16.3.11 changed current_from 0.194438234 -> -0.379789442 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A006** (rank `6`, `measurement_step`, `unverified_observation`, +`75.372`s, RTU `172.16.3.12`): line.11: 1 measurement(s) in one ASDU from RTU 172.16.3.12 changed current_to 0.0171663631 -> 0.228123486 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A007** (rank `7`, `measurement_step`, `unverified_observation`, +`124.465`s, RTU `172.16.3.9`): line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from 0.36232686 -> 0.143206537 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['pre_sample_gap_exceeded', 'insufficient_post_samples']).

### 2A.2 Behavioral Storylines
#### SL001 — anchors `['A001']` (+`1.381`s, status=`behavioral_single_anchor`)
- **Reconstructed**: [A001] ARP from 172.16.3.28: 127 packets in window (2 requests, 125 replies) to ['172.16.3.10', '172.16.3.20', '172.16.3.9']; 0 in background (verification=verified_observation).
- **Evidence-supported relations**: none (single anchor)
- **Candidate relations (unresolved, time proximity only; 3)**: R0027: -> 172.16.1.2<->172.16.3.10:2404/IEC104 (@+7.522s); R0028: -> 172.16.1.2<->172.16.3.20:2404/IEC104 (@+8.102s); R0029: -> 172.16.1.2<->172.16.3.9:2404/IEC104 (@+14.83s)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL002 — anchors `['A002']` (+`7.522`s, status=`behavioral_single_anchor`)
- **Reconstructed**: [A002] IEC-104 link 172.16.1.2 <-> 172.16.3.10: clock_synchronisation_cot6 x1, clock_synchronisation_cot7 x1, connection_attempt_unanswered x35, connection_established x2, general_interrogation_cot10 x1, general_interrogation_cot6 x1, general_interrogation_cot7 x1, tcp_fin x5, tcp_reset x1, telemetry_gap x1; first at 1742953792.79 (verification=verified_observation).
- **Evidence-supported relations**: none (single anchor)
- **Candidate relations (unresolved, time proximity only; 3)**: R0030: -> 172.16.1.2<->172.16.3.20:2404/IEC104 (@+8.102s); R0031: -> 172.16.1.2<->172.16.3.9:2404/IEC104 (@+14.83s); R0027: 172.16.3.28/ARP (@+1.381s) ->
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL003 — anchors `['A003']` (+`8.102`s, status=`behavioral_single_anchor`)
- **Reconstructed**: [A003] IEC-104 link 172.16.1.2 <-> 172.16.3.20: clock_synchronisation_cot6 x1, clock_synchronisation_cot7 x1, connection_attempt_unanswered x8, connection_established x1, general_interrogation_cot10 x1, general_interrogation_cot6 x1, general_interrogation_cot7 x1, telemetry_gap x1; first at 1742953793.37 (verification=verified_observation).
- **Evidence-supported relations**: none (single anchor)
- **Candidate relations (unresolved, time proximity only; 3)**: R0032: -> 172.16.1.2<->172.16.3.9:2404/IEC104 (@+14.83s); R0028: 172.16.3.28/ARP (@+1.381s) ->; R0030: 172.16.1.2<->172.16.3.10:2404/IEC104 (@+7.522s) ->
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL004 — anchors `['A004']` (+`14.83`s, status=`behavioral_single_anchor`)
- **Reconstructed**: [A004] IEC-104 link 172.16.1.2 <-> 172.16.3.9: clock_synchronisation_cot6 x1, clock_synchronisation_cot7 x1, connection_attempt_unanswered x35, connection_established x2, general_interrogation_cot10 x1, general_interrogation_cot6 x1, general_interrogation_cot7 x1, tcp_fin x5, tcp_reset x1; first at 1742953800.098 (verification=verified_observation).
- **Evidence-supported relations**: none (single anchor)
- **Candidate relations (unresolved, time proximity only; 4)**: R0033: -> line.11:current_from (@+29.737s); R0029: 172.16.3.28/ARP (@+1.381s) ->; R0031: 172.16.1.2<->172.16.3.10:2404/IEC104 (@+7.522s) ->; R0032: 172.16.1.2<->172.16.3.20:2404/IEC104 (@+8.102s) ->
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL005 — anchors `['A005']` (+`29.737`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A005] line.11: 1 measurement(s) in one ASDU from RTU 172.16.3.11 changed current_from 0.194438234 -> -0.379789442 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A005': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Candidate relations (unresolved, time proximity only; 1)**: R0033: 172.16.1.2<->172.16.3.9:2404/IEC104 (@+14.83s) ->
- **IPAL time-aligned rows (not independent)**: line.11:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL006 — anchors `['A006']` (+`75.372`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A006] line.11: 1 measurement(s) in one ASDU from RTU 172.16.3.12 changed current_to 0.0171663631 -> 0.228123486 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A006': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.11:current_to (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL007 — anchors `['A007']` (+`124.465`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A007] line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from 0.36232686 -> 0.143206537 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['pre_sample_gap_exceeded', 'insufficient_post_samples']).
- **Unverified observation issues**: `{'A007': ['pre_sample_gap_exceeded', 'insufficient_post_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.13:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.

## 2B. Incident Scenario Synthesis (Four-Layer Epistemic Integration)
- **Scenario Status**: `synthesized_consistent`
- **Layer 1 Partition**: `0` supported multi-node chains, `4` verified single-anchor chains, `0` sequential same-entity observations (gate failed), `3` quarantined unverified observations (`0` unverified COT=3 precursor reports).
- **Layer 2 Bundles & Bridges**: `4` source bundles (each counted as `1` container), `0` cross-RTU verified element bridges, `0` same-RTU supported relations (not cross-RTU support), `0` multi-bundle bridged components.
- **Layer 3 Candidate Phases**: `1` candidate scenario phases (all cross-device links kept `unresolved`).
- **Layer 4 Source Dependency Ledger**: `0` IEC-104 ASDU, `3` TCP link, `1` ARP, `0` composite containers across `3` RTU(s) (`['172.16.3.10', '172.16.3.20', '172.16.3.9']`), `0` co-reported same-ASDU points collapsed, mirror vantages `[]`, `3` IPAL rows excluded (`weight=0`).

### 2B.1 Layer 2 — RTU ASDU Bundles & Verified Element Bridges
- **BND-001** (`+1.381s`, RTU `None`, container=`SRC-ARP_ACTIVITY_INCREASE-172.16.3.28/ARP`, independent_sources=`1`): anchors `['A001']` -> `['172.16.3.28/ARP']`.
- **BND-002** (`+7.522s`, RTU `172.16.3.10`, container=`SRC-COMMUNICATION_CHANGE-172.16.1.2<->172.16.3.10:2404/IEC104`, independent_sources=`1`): anchors `['A002']` -> `['172.16.1.2<->172.16.3.10:2404/IEC104']`.
- **BND-003** (`+8.102s`, RTU `172.16.3.20`, container=`SRC-COMMUNICATION_CHANGE-172.16.1.2<->172.16.3.20:2404/IEC104`, independent_sources=`1`): anchors `['A003']` -> `['172.16.1.2<->172.16.3.20:2404/IEC104']`.
- **BND-004** (`+14.83s`, RTU `172.16.3.9`, container=`SRC-COMMUNICATION_CHANGE-172.16.1.2<->172.16.3.9:2404/IEC104`, independent_sources=`1`): anchors `['A004']` -> `['172.16.1.2<->172.16.3.9:2404/IEC104']`.
- **Cross-RTU Verified Element Bridges**: `none`.

### 2B.2 Layer 3 — Candidate Scenario Phases (Cross-Device Links Unresolved)
- **PHS-001** (`+1.381s`..`+128.208s`, profile=`arp_burst_and_multi_rtu_iec104_link_disruptions`): bundles=`['BND-001', 'BND-002', 'BND-003', 'BND-004']`, verified_bridges=`[]`, sequential_same_device=`[]`, unverified_precursors=`[]`, RTUs=`['172.16.3.10', '172.16.3.20', '172.16.3.9']`, ARP=`[{'anchor_id': 'A001', 'host_ip': '172.16.3.28', 'packet_count': 127, 'targets': {'172.16.3.9': 62, '172.16.3.10': 63, '172.16.3.20': 2}, 'target_first_seen': {'172.16.3.9': 1742953786.648633, '172.16.3.10': 1742953786.677999, '172.16.3.20': 1742953831.077105}, 'arp_target_overlap_rtu_ips': ['172.16.3.10', '172.16.3.20', '172.16.3.9']}]`, unresolved_candidates=`7`.

### 2B.3 Layer 4 — Evidence-Anchored Competing Explanations & Missing Evidence
- **EXP-001** (`arp_address_interference_preceding_iec104_session_loss_hypothesis`, status=`unresolved_competing_hypothesis`, causal_status=`not_established`): Host(s) ['172.16.3.28'] sent ARP traffic (['A001']) whose per-target first packet to RTU IP(s) ['172.16.3.10', '172.16.3.9'] occurred before those IEC-104 links changed and within 15s (`eligible_arp_link_pairs`). Other link(s) ['172.16.3.20'] did not satisfy per-target precedence and are excluded from this precedence claim.
  - **Anchored by**: `{'arp_anchor_ids': ['A001'], 'communication_anchor_ids': ['A002', 'A004'], 'arp_source_hosts': ['172.16.3.28'], 'overlapping_target_rtu_ips': ['172.16.3.10', '172.16.3.9'], 'per_target_first_arp_evidence_ids': ['EV-0e9f6fb66f6907e4', 'EV-fd36a37175d5af9d'], 'evidence_ids': ['EV-0e9f6fb66f6907e4', 'EV-dd59c3d758762e69', 'EV-fd36a37175d5af9d', 'EV-06a22bddc2cd3bee', 'EV-79fef36709e79d8b', 'EV-449dd0e2c716cc8e', 'EV-43c669e3989a2cb9', 'EV-4f94ff12f644b2ff', 'EV-6c3c28ec9cf1ce5a', 'EV-f0d746d67fdd2fa4']}`
  - **Unverified/candidate links required**: `['R0027', 'R0028', 'R0029', 'R0030', 'R0031', 'R0032', 'R0033']`
  - **Alternative comparison**: Per-target ARP precedence holds for ['172.16.3.10', '172.16.3.9'], but candidate edges ['R0027', 'R0028', 'R0029', 'R0030', 'R0031', 'R0032', 'R0033'] remain unresolved. ARP counts do not prove MAC spoofing.
  - **Missing disambiguating evidence**: `["ARP payload sender-MAC to sender-IP binding audit for ['172.16.3.28'] vs legitimate MACs of ['172.16.3.10', '172.16.3.9'] and master", 'Managed switch CAM/ARP table logs and port-security counters at n302/n318', "TCP stack reset/timeout logs on master 172.16.1.2 and RTUs ['172.16.3.10', '172.16.3.9']"]`
- **EXP-002** (`concurrent_l2_link_disturbance_and_arp_re_resolution_hypothesis`, status=`unresolved_competing_hypothesis`, causal_status=`not_established`): IEC-104 links ['A002', 'A003', 'A004'] (sharing master 172.16.1.2) experienced session loss and re-establishment in the same window as ARP burst ['A001'], without requiring ['172.16.3.28'] to have caused the TCP session drops (e.g. switch path reset or interface flap accompanied by neighbor re-resolution).
  - **Anchored by**: `{'arp_anchor_ids': ['A001'], 'communication_anchor_ids': ['A002', 'A003', 'A004'], 'evidence_ids': ['EV-0e9f6fb66f6907e4', 'EV-dd59c3d758762e69', 'EV-fd36a37175d5af9d', 'EV-06a22bddc2cd3bee', 'EV-79fef36709e79d8b', 'EV-449dd0e2c716cc8e', 'EV-43c669e3989a2cb9', 'EV-4f94ff12f644b2ff', 'EV-6c3c28ec9cf1ce5a', 'EV-f0d746d67fdd2fa4']}`
  - **Alternative comparison**: Treats the ARP burst and the TCP session drops as co-occurring L2/L3 network events rather than assuming causal ARP interference.
  - **Missing disambiguating evidence**: `['Switch interface link-state / spanning-tree logs during the telemetry gap', "Host ['172.16.3.28'] network service and ARP table logs"]`

## 2. Key Findings & Reconstructed Storylines (Contiguous Directed Spines)

## 3. Observed Network & Electrical Impact (Epistemically Stratified)
### 3.1 Verified Same-Device Measurement/State Transitions (Consistency Gate Passed)
- No post-command device transition passed all pre/post and target consistency checks.

### 3.2 Protocol State Reports Observed Without Verified Transition (Value Undecoded or No Pre-Baseline)
- None.

### 3.3 Candidate Cross-Entity Co-occurring Changes (Unresolved Hypotheses, Not Causal Proof)
- [SL001 / R0027 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): 172.16.1.2<->172.16.3.10:2404/IEC104 (BA002) at 1742953792.79 after BA001 (0 <= dt (6.141s) <= 15.0s) [src_ev=EV-0e9f6fb66f6907e4, EV-dd59c3d758762e69; dst_ev=EV-06a22bddc2cd3bee, EV-79fef36709e79d8b].
- [SL001 / R0028 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): 172.16.1.2<->172.16.3.20:2404/IEC104 (BA003) at 1742953793.37 after BA001 (0 <= dt (6.721s) <= 15.0s) [src_ev=EV-0e9f6fb66f6907e4, EV-dd59c3d758762e69; dst_ev=EV-43c669e3989a2cb9, EV-4f94ff12f644b2ff].
- [SL001 / R0029 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): 172.16.1.2<->172.16.3.9:2404/IEC104 (BA004) at 1742953800.0982 after BA001 (0 <= dt (13.45s) <= 15.0s) [src_ev=EV-0e9f6fb66f6907e4, EV-dd59c3d758762e69; dst_ev=EV-f0d746d67fdd2fa4, EV-a19b67117ff1dbe7].
- [SL002 / R0030 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): 172.16.1.2<->172.16.3.20:2404/IEC104 (BA003) at 1742953793.37 after BA002 (0 <= dt (0.58s) <= 15.0s) [src_ev=EV-06a22bddc2cd3bee, EV-79fef36709e79d8b; dst_ev=EV-43c669e3989a2cb9, EV-4f94ff12f644b2ff].
- [SL002 / R0031 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): 172.16.1.2<->172.16.3.9:2404/IEC104 (BA004) at 1742953800.0982 after BA002 (0 <= dt (7.308s) <= 15.0s) [src_ev=EV-06a22bddc2cd3bee, EV-79fef36709e79d8b; dst_ev=EV-f0d746d67fdd2fa4, EV-a19b67117ff1dbe7].
- [SL003 / R0032 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): 172.16.1.2<->172.16.3.9:2404/IEC104 (BA004) at 1742953800.0982 after BA003 (0 <= dt (6.728s) <= 15.0s) [src_ev=EV-43c669e3989a2cb9, EV-4f94ff12f644b2ff; dst_ev=EV-f0d746d67fdd2fa4, EV-a19b67117ff1dbe7].
- [SL004 / R0033 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): line.11:current_from (BA005) at 1742953815.0051 after BA004 (0 <= dt (14.907s) <= 15.0s) [src_ev=EV-f0d746d67fdd2fa4, EV-a19b67117ff1dbe7; dst_ev=EV-fc84bf76fcef2626, EV-6cac6fb06df4e222].

## 4. Alternative Explanations & Competing Hypotheses
- **[SL001 | competing_cross_entity_cooccurrences | status=`unresolved`]**: Multiple distinct grid measurements (172.16.1.2<->172.16.3.10:2404/IEC104, 172.16.1.2<->172.16.3.20:2404/IEC104, 172.16.1.2<->172.16.3.9:2404/IEC104) changed within the time horizon after 172.16.3.28/ARP. Without an independent physical topology/power-flow model in the loop, these remain competing unresolved temporal co-occurrences rather than confirmed causal effects.
- **[SL002 | competing_cross_entity_cooccurrences | status=`unresolved`]**: Multiple distinct grid measurements (172.16.1.2<->172.16.3.20:2404/IEC104, 172.16.1.2<->172.16.3.9:2404/IEC104) changed within the time horizon after 172.16.1.2<->172.16.3.10:2404/IEC104. Without an independent physical topology/power-flow model in the loop, these remain competing unresolved temporal co-occurrences rather than confirmed causal effects.

## 5. Unresolved Questions, Evidence Gaps & Unattached Observations
- **Unattached Observations (`27` nodes not on a storyline spine)**:
  - `TL008` (`1742953785.5268`, `network`, `communication`): `172.16.3.22:2404->172.16.1.2:34946/TCP` (`not_on_confirmed_storyline_spine`) [`EV-36e75836de364de8, EV-50f10e5b665065c8`]
  - `TL025` (`1742953785.5308`, `network`, `communication`): `172.16.1.2:34946->172.16.3.22:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-c91b77185d64509f, EV-b0903cd89af01468`]
  - `TL014` (`1742953785.8582`, `electrical`, `electrical_change`): `line.11:current_from` (`not_on_confirmed_storyline_spine`) [`EV-e9d217b62e01ef12, EV-8e7e97a5cb4a5480`]
  - `TL018` (`1742953785.8582`, `electrical`, `electrical_change`): `line.6:active_power_to` (`not_on_confirmed_storyline_spine`) [`EV-b6d969196ed270cd, EV-02cb8aa7e0a06edc`]
  - `TL023` (`1742953788.5860`, `network`, `electrical_report`): `bus.0:voltage_angle` (`not_on_confirmed_storyline_spine`) [`EV-e5bf50771d815002, EV-05315487505d9a2f`]
  - `TL019` (`1742953788.8582`, `electrical`, `electrical_change`): `bus.0:voltage_angle` (`not_on_confirmed_storyline_spine`) [`EV-c0b3eb3294418e61, EV-4895c3f6d6e75d51`]
  - `TL020` (`1742953788.8582`, `electrical`, `electrical_change`): `line.0:active_power_from` (`not_on_confirmed_storyline_spine`) [`EV-5f3e17a7b786a7af, EV-6b2c311f9d0e3c99`]
  - `TL012` (`1742953789.5607`, `network`, `electrical_report`): `line.10:current_from` (`not_on_confirmed_storyline_spine`) [`EV-3cfc0041bfff893c, EV-dac7d65f1b12a11f`]
  - `TL016` (`1742953789.8582`, `electrical`, `electrical_change`): `line.10:current_from` (`not_on_confirmed_storyline_spine`) [`EV-cbbdbe10392fd1a5, EV-626f43e238fe9543`]
  - `TL009` (`1742953790.6156`, `network`, `electrical_report`): `line.11:current_to` (`not_on_confirmed_storyline_spine`) [`EV-87a18bdec5b7b860, EV-efb2fe43eac1d4c5`]
