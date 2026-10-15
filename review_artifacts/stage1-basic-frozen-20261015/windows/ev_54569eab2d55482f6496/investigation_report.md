# Evidence-Grounded Incident Reconstruction Report

- **Report Status**: `quality_consistent`
- **Quality & Behavioral Consistency (`quality_consistency.json`)**: `consistent`
- **Evidence Lineage Audit (`lineage_consistency.json`)**: `consistent`

- **Incident Window**: `1742949924.2669797` to `1742950255.657609`
- **Reconstructed IEC-104 Transactions**: `2`
- **Reconstructed Event Storylines**: `6`
- **Verified Same-Device Transitions (Consistency Gate Passed)**: `1`
- **Unverified Protocol State Reports (Value Undecoded or No Pre-Baseline)**: `0`
- **LLM Claim Verifier Output (Separate from Graph Gate)**: `0` verified, `0` withheld

## 1. Incident Sequence & Protocol Transactions
- **TX001** (`1742949983.0829`–`1742949983.1121`): `C_SC_NA_1 (Single command)` on `switch.17:closed` (`CA/IOA=127.10150`, value=`0.0`) over `172.16.3.33:37542 -> 172.16.3.22:2404` at vantages `['n318']`. **Command Acceptance (`COT=7` P/N)**: `accepted_by_rtu`; **Device State Verification**: `no_state_change_observed` (reason=`no_post_command_feedback_observed`); **Completeness**: `confirmation_observed_only_no_state_report`; **Missing/Unverified Stages**: `['activation_termination_cot10', 'post_command_state_or_measurement_change']` (`EV-1ce1899f6eebeff2, EV-3cccc3750ec52e13, EV-1847dbaeb32a1e72, EV-4cdb321ac3919dcd`).
- **TX002** (`1742949986.0844`–`1742949986.3542`): `C_SC_NA_1 (Single command)` on `switch.0:closed` (`CA/IOA=127.10130`, value=`0.0`) over `172.16.3.33:37542 -> 172.16.3.22:2404` at vantages `['n318']`. **Command Acceptance (`COT=7` P/N)**: `accepted_by_rtu`; **Device State Verification**: `verified_state_transition` (reason=`decoded_spontaneous_state_shift_verified`); **Completeness**: `partial_no_cot10_but_verified_measurement_transition`; **Missing/Unverified Stages**: `['activation_termination_cot10']` (`EV-52cb37ee29c71e25, EV-226873e1895281f8, EV-8943cd03f7e42744, EV-6aa6324f0b33d7c6`).
  - Inference gate (`state_report`): passed=`True`; pre IV=`False` other flags=`[]`; post IV=`False` other flags=`[]`; COT test bits=`{'command': False, 'confirmation': False, 'pre': False, 'post': False}`; failed=`[]`.

## 2A. Behavioral Incident Reconstruction (No Control Command)
- `232` event anchors found; a control transaction is present, so anchors are listed in `event_anchors.json` and do not root storylines.

## 2B. Incident Scenario Synthesis (Four-Layer Epistemic Integration)
- **Scenario Status**: `synthesized_consistent`
- **Layer 1 Partition**: `1` supported multi-node chains, `0` verified single-anchor chains, `0` sequential same-entity observations (gate failed), `0` quarantined unverified observations (`0` unverified COT=3 precursor reports).
- **Layer 2 Bundles & Bridges**: `0` source bundles (each counted as `1` container), `0` cross-RTU verified element bridges, `0` same-RTU supported relations (not cross-RTU support), `0` multi-bundle bridged components.
- **Layer 3 Candidate Phases**: `1` candidate scenario phases (all cross-device links kept `unresolved`).
- **Layer 4 Source Dependency Ledger**: `0` IEC-104 ASDU, `0` TCP link, `0` ARP, `7` composite containers across `1` RTU(s) (`['172.16.3.22']`), `0` co-reported same-ASDU points collapsed, mirror vantages `['n318']`, `434` IPAL rows excluded (`weight=0`).

### 2B.2 Layer 3 — Candidate Scenario Phases (Cross-Device Links Unresolved)
- **PHS-001** (`+58.816s`..`+62.087s`, profile=`protocol_command_transactions`): bundles=`[]`, verified_bridges=`[]`, sequential_same_device=`[]`, unverified_precursors=`[]`, RTUs=`['172.16.3.22']`, ARP=`[]`, unresolved_candidates=`0`.

### 2B.3 Layer 4 — Evidence-Anchored Competing Explanations & Missing Evidence
- **EXP-001** (`command_induced_device_transition_hypothesis`, status=`unresolved_competing_hypothesis`, causal_status=`not_established`): Observed IEC-104 control activation(s) ['TX001', 'TX002'] on the SCADA network, with 1 transaction(s) passing pre/post setpoint/state consistency checks. Consistent with RTU execution of the received IEC-104 command(s).
  - **Anchored by**: `{'transaction_ids': ['TX001', 'TX002'], 'verified_transition_transaction_ids': ['TX002'], 'evidence_ids': ['EV-1ce1899f6eebeff2', 'EV-3cccc3750ec52e13', 'EV-1847dbaeb32a1e72', 'EV-4cdb321ac3919dcd', 'EV-52cb37ee29c71e25', 'EV-226873e1895281f8', 'EV-8943cd03f7e42744', 'EV-6aa6324f0b33d7c6']}`
  - **Unverified/candidate links required**: `['TX001']`
  - **Alternative comparison**: Competes with coincidence or unverified physical actuation where protocol confirmation (COT=7) or telemetry shifts occur without independent physical sensor verification.
  - **Missing disambiguating evidence**: `['Independent out-of-band physical process sensor or PMU log not derived from IEC-104', 'Master station operator/application audit log identifying the initiating process', 'Pre-command IEC-104 state baseline (COT=20/COT=1) for switch transactions']`
- **EXP-002** (`arp_and_iec104_link_observations_without_supported_precedence`, status=`unresolved_competing_hypothesis`, causal_status=`not_established`): ARP activity ['A001', 'A002', 'A003', 'A004', 'A005'] and IEC-104 link changes ['A006', 'A007'] were both observed. No pair has per-target ARP overlap with the affected RTU before the link change and within 15s. No precedence between them is claimed.
  - **Anchored by**: `{'arp_anchor_ids': ['A001', 'A002', 'A003', 'A004', 'A005'], 'communication_anchor_ids': ['A006', 'A007'], 'arp_source_hosts': ['172.16.3.18', '172.16.3.22', '172.16.3.23', '172.16.3.28', '172.16.3.33'], 'evidence_ids': ['EV-24707bab28883f76', 'EV-23beb4293f4c8718', 'EV-296197d76a3979b9', 'EV-25afa93d93385a60', 'EV-bed2173ec9a82916', 'EV-80511170887385d4', 'EV-3d486f5c40b50bb9', 'EV-59e26c0f89af8487', 'EV-c6b91710818f598a', 'EV-92a2dd8448f32290']}`
  - **Alternative comparison**: A general co-observation only. It does not say the ARP activity came first or addressed the RTU whose session changed.
  - **Missing disambiguating evidence**: `['ARP target addresses that match the RTU whose IEC-104 session changed', 'Per-target ARP timestamps before that session change and inside the horizon']`
- **EXP-003** (`concurrent_l2_link_disturbance_and_arp_re_resolution_hypothesis`, status=`unresolved_competing_hypothesis`, causal_status=`not_established`): IEC-104 links ['A006', 'A007'] (sharing master 172.16.1.2) experienced session loss and re-establishment in the same window as ARP burst ['A001', 'A002', 'A003', 'A004', 'A005'], without requiring ['172.16.3.18', '172.16.3.22', '172.16.3.23', '172.16.3.28', '172.16.3.33'] to have caused the TCP session drops (e.g. switch path reset or interface flap accompanied by neighbor re-resolution).
  - **Anchored by**: `{'arp_anchor_ids': ['A001', 'A002', 'A003', 'A004', 'A005'], 'communication_anchor_ids': ['A006', 'A007'], 'evidence_ids': ['EV-24707bab28883f76', 'EV-23beb4293f4c8718', 'EV-296197d76a3979b9', 'EV-25afa93d93385a60', 'EV-bed2173ec9a82916', 'EV-80511170887385d4', 'EV-3d486f5c40b50bb9', 'EV-59e26c0f89af8487', 'EV-c6b91710818f598a', 'EV-92a2dd8448f32290']}`
  - **Alternative comparison**: Treats the ARP burst and the TCP session drops as co-occurring L2/L3 network events rather than assuming causal ARP interference.
  - **Missing disambiguating evidence**: `['Switch interface link-state / spanning-tree logs during the telemetry gap', "Host ['172.16.3.18', '172.16.3.22', '172.16.3.23', '172.16.3.28', '172.16.3.33'] network service and ARP table logs"]`

## 2. Key Findings & Reconstructed Storylines (Contiguous Directed Spines)
### SL001 — Anchor `switch.17:closed` (tx=`TX001`, status=`incomplete_confirmation_observed_without_state_report`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`2`)
- Step 1 [R0001 | N-N | iec104_command_confirmation | level=observed_fact | gate=direct_record_observation | independent_evidence]: EF001 (switch.17:closed @ 1742949983.0829) -> EF002 (switch.17:closed @ 1742949983.1121) [src_ev=EV-1ce1899f6eebeff2, EV-3cccc3750ec52e13; dst_ev=EV-1847dbaeb32a1e72, EV-4cdb321ac3919dcd]
- **Evidence Gaps**: `['activation_termination_cot10', 'post_command_state_or_measurement_change']`
### SL002 — Anchor `switch.0:closed` (tx=`TX002`, status=`partial_missing_cot10_but_verified_measurement_transition`, contiguous_path=`True`, logical_nodes=`3`, independent_sources=`3`, independent_edges=`2`, vantage_captures=`3`)
- Step 1 [R0002 | N-N | iec104_command_confirmation | level=observed_fact | gate=direct_record_observation | independent_evidence]: EF003 (switch.0:closed @ 1742949986.0844) -> EF004 (switch.0:closed @ 1742949986.1141) [src_ev=EV-52cb37ee29c71e25, EV-226873e1895281f8; dst_ev=EV-8943cd03f7e42744, EV-6aa6324f0b33d7c6]
- Step 2 [R0003 | N-N | subsequent_same_device_state_report | level=observed_fact | gate=direct_record_observation | independent_evidence]: EF004 (switch.0:closed @ 1742949986.1141) -> EF005 (switch.0:is_closed @ 1742949986.3144) [src_ev=EV-8943cd03f7e42744, EV-6aa6324f0b33d7c6; dst_ev=EV-3c092a2996c4d9da, EV-391b52febebb3bf0]
- **Evidence Gaps**: `['activation_termination_cot10']`
### SL003 — Anchor `line.4:current_to` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`262`)
- Step 1 [R0017 | N-N | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL011 (line.4:current_to @ 1742949925.183) -> TL012 (line.4:current_from @ 1742949927.6525) [src_ev=EV-b6fecab45662c177, EV-78aad3630107ca15; dst_ev=EV-3a97e1ea7e657307, EV-55a4855708d6bc8a]
- Time-aligned IPAL row [R0011 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL015 (line.4:current_to=0.1616704910993576 @ 1742949925.8582) aligned with TL011; not an independent source
- Time-aligned IPAL row [R0013 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL016 (line.4:current_from=0.4565335810184479 @ 1742949927.8582) aligned with TL012; not an independent source
### SL004 — Anchor `line.4:current_to` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`66`)
- Step 1 [R0018 | P-P | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL015 (line.4:current_to @ 1742949925.8582) -> TL016 (line.4:current_from @ 1742949927.8582) [src_ev=EV-545c7903f0fbce1a, EV-54bd396d7223378a; dst_ev=EV-8c3a1f77e42cf675, EV-aae216eb26e3fba1]
### SL005 — Anchor `line.11:current_to` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`66`)
- Step 1 [R0020 | P-P | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL017 (line.11:current_to @ 1742949928.8582) -> TL021 (line.11:current_from @ 1742949932.8582) [src_ev=EV-520d47b96aa58696, EV-92399be5c4e65c96; dst_ev=EV-9c36f4f25c420640, EV-20a2470b1d5e7acb]
### SL006 — Anchor `line.9:active_power_from` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`132`)
- Step 1 [R0019 | N-N | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL023 (line.9:active_power_from @ 1742949928.5825) -> TL014 (line.9:active_power_to @ 1742949929.1158) [src_ev=EV-582dae6ca2faa009, EV-1f2827e09ef3c7dd; dst_ev=EV-b21b085ea5efbd32, EV-8119ec242362ff5b]
- Time-aligned IPAL row [R0015 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL018 (line.9:active_power_from=73362.921875 @ 1742949928.8582) aligned with TL023; not an independent source
- Time-aligned IPAL row [R0016 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL019 (line.9:active_power_to=-71177.90625 @ 1742949929.8582) aligned with TL014; not an independent source

## 3. Observed Network & Electrical Impact (Epistemically Stratified)
### 3.1 Verified Same-Device Measurement/State Transitions (Consistency Gate Passed)
- [TX002 | verified_state_transition] Point switch.0:is_closed (CA/IOA=127.10140) shifted from pre-command state 1.0 to 0.0 (@ 1742949986.3144, ev=EV-3c092a2996c4d9da).

### 3.2 Protocol State Reports Observed Without Verified Transition (Value Undecoded or No Pre-Baseline)
- None.

### 3.3 Candidate Cross-Entity Co-occurring Changes (Unresolved Hypotheses, Not Causal Proof)
- [SL002 / R0008 | command_to_device_state_candidate] (level=unresolved, status=unresolved, gate=failed_gate_kept_unresolved, causal_status=not_established): switch.0:is_closed (EF007) at 1742949986.3542 after EF003 (0 <= dt (0.2698s) <= 15.0s) [src_ev=EV-52cb37ee29c71e25, EV-226873e1895281f8; dst_ev=EV-bafae988aff61acf, EV-c19f557850d1e28b].

## 4. Alternative Explanations & Competing Hypotheses
- **[SL001 | confirmation_without_state_report | status=`unresolved`]**: RTU 172.16.3.22 sent COT=7 on switch.17:closed (acceptance_status=accepted_by_rtu), but no subsequent COT=3 state report or IPAL new state update occurred. Alternative explanations: (a) the switch/point was already in the target state, or (b) physical actuation did not occur or was not reported within the window.

## 5. Unresolved Questions, Evidence Gaps & Unattached Observations
- **Evidence Gap**: `{"scope": "TX001", "entity": "switch.17:closed", "missing_stages": ["activation_termination_cot10", "post_command_state_or_measurement_change"]}`
- **Evidence Gap**: `{"scope": "TX002", "entity": "switch.0:closed", "missing_stages": ["activation_termination_cot10"]}`
- **Evidence Gap**: `{"scope": "cross_vantage_payload_conflicts", "count": 712}`
- **Unattached Observations (`14` nodes not on a storyline spine)**:
  - `TL024` (`1742949926.1872`, `network`, `electrical_report`): `bus.0:voltage_angle` (`not_on_confirmed_storyline_spine`) [`EV-13f95966e507c842, EV-85fbd68887ba6ff9`]
  - `TL020` (`1742949926.8582`, `electrical`, `electrical_change`): `bus.0:voltage_angle` (`not_on_confirmed_storyline_spine`) [`EV-d217125e6d38c4a5, EV-4c9d1de3c7d94a47`]
  - `TL001` (`1742949927.2273`, `network`, `communication`): `172.16.3.22:2404->172.16.1.2:34946/TCP` (`isolated_no_graph_edge`) [`EV-856b487741d19554, EV-5d974e82d1f385ba`]
  - `TL013` (`1742949928.1527`, `network`, `electrical_report`): `line.11:current_to` (`not_on_confirmed_storyline_spine`) [`EV-77142a20a6fcfad2, EV-8845dc1cae6c7ee1`]
  - `TL018` (`1742949928.8582`, `electrical`, `electrical_change`): `line.9:active_power_from` (`not_on_confirmed_storyline_spine`) [`EV-f46d7da9fc23f688, EV-344b69eba9850113`]
  - `TL002` (`1742949929.6807`, `network`, `communication`): `172.16.1.2:37458->172.16.3.18:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-a2a3cf7a22f1c056, EV-636fa6ae398c9088`]
  - `TL004` (`1742949929.7008`, `network`, `communication`): `172.16.3.18:2404->172.16.1.2:37458/TCP` (`not_on_confirmed_storyline_spine`) [`EV-39635d67ece8c983, EV-eacebf59bcd8c532`]
  - `TL019` (`1742949929.8582`, `electrical`, `electrical_change`): `line.9:active_power_to` (`not_on_confirmed_storyline_spine`) [`EV-9207c4448e9ce5ec, EV-a6af4a18ea11e59d`]
  - `TL003` (`1742949930.0209`, `network`, `communication`): `172.16.3.23:2404->172.16.1.2:60408/TCP` (`isolated_no_graph_edge`) [`EV-c445e291e43e0183, EV-c5f72ea77b0781d0`]
  - `TL022` (`1742949932.8582`, `electrical`, `electrical_change`): `line.13:current_to` (`isolated_no_graph_edge`) [`EV-b27da69c9688da37, EV-5b98787bee610740`]
