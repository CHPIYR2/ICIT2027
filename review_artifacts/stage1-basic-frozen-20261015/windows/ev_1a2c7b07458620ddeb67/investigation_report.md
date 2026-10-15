# Evidence-Grounded Incident Reconstruction Report

- **Report Status**: `quality_consistent`
- **Quality & Behavioral Consistency (`quality_consistency.json`)**: `consistent`
- **Evidence Lineage Audit (`lineage_consistency.json`)**: `consistent`

- **Incident Window**: `1742929812.2699013` to `1742930172.8976083`
- **Reconstructed IEC-104 Transactions**: `2`
- **Reconstructed Event Storylines**: `6`
- **Verified Same-Device Transitions (Consistency Gate Passed)**: `2`
- **Unverified Protocol State Reports (Value Undecoded or No Pre-Baseline)**: `0`
- **LLM Claim Verifier Output (Separate from Graph Gate)**: `0` verified, `0` withheld

## 1. Incident Sequence & Protocol Transactions
- **TX001** (`1742929870.9868`–`1742929871.5481`): `C_SC_NA_1 (Single command)` on `switch.29:closed` (`CA/IOA=116.10130`, value=`0.0`) over `172.16.3.32:33558 -> 172.16.3.11:2404` at vantages `['n318']`. **Command Acceptance (`COT=7` P/N)**: `accepted_by_rtu`; **Device State Verification**: `verified_state_transition` (reason=`decoded_spontaneous_state_shift_verified`); **Completeness**: `partial_no_cot10_but_verified_measurement_transition`; **Missing/Unverified Stages**: `['activation_termination_cot10']` (`EV-88c5b849f2e0a429, EV-1f0797f58a768fc7, EV-b0a05c85903ccbe0, EV-11ef9d03786b5769`).
  - Inference gate (`state_report`): passed=`True`; pre IV=`False` other flags=`[]`; post IV=`False` other flags=`[]`; COT test bits=`{'command': False, 'confirmation': False, 'pre': False, 'post': False}`; failed=`[]`.
- **TX002** (`1742929873.9886`–`1742929874.2387`): `C_SC_NA_1 (Single command)` on `switch.30:closed` (`CA/IOA=116.10150`, value=`0.0`) over `172.16.3.32:33558 -> 172.16.3.11:2404` at vantages `['n318']`. **Command Acceptance (`COT=7` P/N)**: `accepted_by_rtu`; **Device State Verification**: `verified_state_transition` (reason=`decoded_spontaneous_state_shift_verified`); **Completeness**: `partial_no_cot10_but_verified_measurement_transition`; **Missing/Unverified Stages**: `['activation_termination_cot10']` (`EV-f09b18c4ac3c0b6f, EV-d8b8c5214a0aff5e, EV-56f32e9db35571c6, EV-08b83291021e4ab9`).
  - Inference gate (`state_report`): passed=`True`; pre IV=`False` other flags=`[]`; post IV=`False` other flags=`[]`; COT test bits=`{'command': False, 'confirmation': False, 'pre': False, 'post': False}`; failed=`[]`.

## 2A. Behavioral Incident Reconstruction (No Control Command)
- `254` event anchors found; a control transaction is present, so anchors are listed in `event_anchors.json` and do not root storylines.

## 2B. Incident Scenario Synthesis (Four-Layer Epistemic Integration)
- **Scenario Status**: `synthesized_consistent`
- **Layer 1 Partition**: `2` supported multi-node chains, `0` verified single-anchor chains, `0` sequential same-entity observations (gate failed), `0` quarantined unverified observations (`0` unverified COT=3 precursor reports).
- **Layer 2 Bundles & Bridges**: `0` source bundles (each counted as `1` container), `0` cross-RTU verified element bridges, `0` same-RTU supported relations (not cross-RTU support), `0` multi-bundle bridged components.
- **Layer 3 Candidate Phases**: `1` candidate scenario phases (all cross-device links kept `unresolved`).
- **Layer 4 Source Dependency Ledger**: `0` IEC-104 ASDU, `0` TCP link, `0` ARP, `10` composite containers across `1` RTU(s) (`['172.16.3.11']`), `0` co-reported same-ASDU points collapsed, mirror vantages `['n318']`, `673` IPAL rows excluded (`weight=0`).

### 2B.2 Layer 3 — Candidate Scenario Phases (Cross-Device Links Unresolved)
- **PHS-001** (`+58.717s`..`+61.969s`, profile=`protocol_command_transactions`): bundles=`[]`, verified_bridges=`[]`, sequential_same_device=`[]`, unverified_precursors=`[]`, RTUs=`['172.16.3.11']`, ARP=`[]`, unresolved_candidates=`0`.

### 2B.3 Layer 4 — Evidence-Anchored Competing Explanations & Missing Evidence
- **EXP-001** (`command_induced_device_transition_hypothesis`, status=`unresolved_competing_hypothesis`, causal_status=`not_established`): Observed IEC-104 control activation(s) ['TX001', 'TX002'] on the SCADA network, with 2 transaction(s) passing pre/post setpoint/state consistency checks. Consistent with RTU execution of the received IEC-104 command(s).
  - **Anchored by**: `{'transaction_ids': ['TX001', 'TX002'], 'verified_transition_transaction_ids': ['TX001', 'TX002'], 'evidence_ids': ['EV-88c5b849f2e0a429', 'EV-1f0797f58a768fc7', 'EV-b0a05c85903ccbe0', 'EV-11ef9d03786b5769', 'EV-f09b18c4ac3c0b6f', 'EV-d8b8c5214a0aff5e', 'EV-56f32e9db35571c6', 'EV-08b83291021e4ab9']}`
  - **Alternative comparison**: Competes with coincidence or unverified physical actuation where protocol confirmation (COT=7) or telemetry shifts occur without independent physical sensor verification.
  - **Missing disambiguating evidence**: `['Independent out-of-band physical process sensor or PMU log not derived from IEC-104', 'Master station operator/application audit log identifying the initiating process']`
- **EXP-002** (`arp_and_iec104_link_observations_without_supported_precedence`, status=`unresolved_competing_hypothesis`, causal_status=`not_established`): ARP activity ['A001', 'A002', 'A003'] and IEC-104 link changes ['A005'] were both observed. No pair has per-target ARP overlap with the affected RTU before the link change and within 15s. No precedence between them is claimed.
  - **Anchored by**: `{'arp_anchor_ids': ['A001', 'A002', 'A003'], 'communication_anchor_ids': ['A005'], 'arp_source_hosts': ['172.16.3.11', '172.16.3.28', '172.16.3.32'], 'evidence_ids': ['EV-1ec38f9da7651aee', 'EV-0da50eea597706ad', 'EV-bb56165716836ec6', 'EV-bb8df4fd7aa300ad', 'EV-ae8c1dc76070b27a', 'EV-2e1c6b9fd2f32fb8', 'EV-42dc31a7a1eec1e8', 'EV-866900bb78b5575a', 'EV-7c4835b383a1dde0', 'EV-0e2375181933ea5a']}`
  - **Alternative comparison**: A general co-observation only. It does not say the ARP activity came first or addressed the RTU whose session changed.
  - **Missing disambiguating evidence**: `['ARP target addresses that match the RTU whose IEC-104 session changed', 'Per-target ARP timestamps before that session change and inside the horizon']`
- **EXP-003** (`concurrent_l2_link_disturbance_and_arp_re_resolution_hypothesis`, status=`unresolved_competing_hypothesis`, causal_status=`not_established`): IEC-104 links ['A005'] (sharing master 172.16.1.2) experienced session loss and re-establishment in the same window as ARP burst ['A001', 'A002', 'A003'], without requiring ['172.16.3.11', '172.16.3.28', '172.16.3.32'] to have caused the TCP session drops (e.g. switch path reset or interface flap accompanied by neighbor re-resolution).
  - **Anchored by**: `{'arp_anchor_ids': ['A001', 'A002', 'A003'], 'communication_anchor_ids': ['A005'], 'evidence_ids': ['EV-1ec38f9da7651aee', 'EV-0da50eea597706ad', 'EV-bb56165716836ec6', 'EV-bb8df4fd7aa300ad', 'EV-ae8c1dc76070b27a', 'EV-2e1c6b9fd2f32fb8', 'EV-42dc31a7a1eec1e8', 'EV-866900bb78b5575a', 'EV-7c4835b383a1dde0', 'EV-0e2375181933ea5a']}`
  - **Alternative comparison**: Treats the ARP burst and the TCP session drops as co-occurring L2/L3 network events rather than assuming causal ARP interference.
  - **Missing disambiguating evidence**: `['Switch interface link-state / spanning-tree logs during the telemetry gap', "Host ['172.16.3.11', '172.16.3.28', '172.16.3.32'] network service and ARP table logs"]`

## 2. Key Findings & Reconstructed Storylines (Contiguous Directed Spines)
### SL001 — Anchor `switch.29:closed` (tx=`TX001`, status=`partial_missing_cot10_but_verified_measurement_transition`, contiguous_path=`True`, logical_nodes=`3`, independent_sources=`3`, independent_edges=`2`, vantage_captures=`3`)
- Step 1 [R0001 | N-N | iec104_command_confirmation | level=observed_fact | gate=direct_record_observation | independent_evidence]: EF001 (switch.29:closed @ 1742929870.9868) -> EF002 (switch.29:closed @ 1742929871.0163) [src_ev=EV-88c5b849f2e0a429, EV-1f0797f58a768fc7; dst_ev=EV-b0a05c85903ccbe0, EV-11ef9d03786b5769]
- Step 2 [R0002 | N-N | subsequent_same_device_state_report | level=observed_fact | gate=direct_record_observation | independent_evidence]: EF002 (switch.29:closed @ 1742929871.0163) -> EF003 (switch.29:is_closed @ 1742929871.5169) [src_ev=EV-b0a05c85903ccbe0, EV-11ef9d03786b5769; dst_ev=EV-b71b2140c737dfbb, EV-703e8d4c4a831010]
- **Evidence Gaps**: `['activation_termination_cot10']`
### SL002 — Anchor `switch.30:closed` (tx=`TX002`, status=`partial_missing_cot10_but_verified_measurement_transition`, contiguous_path=`True`, logical_nodes=`3`, independent_sources=`3`, independent_edges=`2`, vantage_captures=`3`)
- Step 1 [R0008 | N-N | iec104_command_confirmation | level=observed_fact | gate=direct_record_observation | independent_evidence]: EF006 (switch.30:closed @ 1742929873.9886) -> EF007 (switch.30:closed @ 1742929874.0182) [src_ev=EV-f09b18c4ac3c0b6f, EV-d8b8c5214a0aff5e; dst_ev=EV-56f32e9db35571c6, EV-08b83291021e4ab9]
- Step 2 [R0009 | N-N | subsequent_same_device_state_report | level=observed_fact | gate=direct_record_observation | independent_evidence]: EF007 (switch.30:closed @ 1742929874.0182) -> EF008 (switch.30:is_closed @ 1742929874.2088) [src_ev=EV-56f32e9db35571c6, EV-08b83291021e4ab9; dst_ev=EV-fad7b52fa3a77dcc, EV-894482389f84e2b0]
- **Evidence Gaps**: `['activation_termination_cot10']`
### SL003 — Anchor `line.13:current_from` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`216`)
- Step 1 [R0023 | N-N | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL011 (line.13:current_from @ 1742929814.7557) -> TL012 (line.13:current_to @ 1742929819.5195) [src_ev=EV-192619c965a57805, EV-7e2043aa7179eaf8; dst_ev=EV-d39ca087b7366865, EV-4ab143ce6a7c3221]
- Time-aligned IPAL row [R0019 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL015 (line.13:current_from=-0.24153847992420197 @ 1742929814.8582) aligned with TL011; not an independent source
- Time-aligned IPAL row [R0022 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL017 (line.13:current_to=0.3778860867023468 @ 1742929819.8582) aligned with TL012; not an independent source
### SL004 — Anchor `line.13:current_from` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`72`)
- Step 1 [R0024 | P-P | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL015 (line.13:current_from @ 1742929814.8582) -> TL017 (line.13:current_to @ 1742929819.8582) [src_ev=EV-9b86a69926c1d085, EV-d4dd988f31bd0d21; dst_ev=EV-cea8f3f6380898af, EV-91fa6829db97529a]
### SL005 — Anchor `line.14:current_from` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`14`)
- Step 1 [R0025 | P-P | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL019 (line.14:current_from @ 1742929815.8582) -> TL022 (line.14:current_to @ 1742929816.8582) [src_ev=EV-ed4a29da6c0375db, EV-1d4776f165212142; dst_ev=EV-2256784cf8ad0636, EV-74fd5ff27681d00d]
### SL006 — Anchor `line.12:current_to` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`72`)
- Step 1 [R0026 | P-P | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL020 (line.12:current_to @ 1742929816.8582) -> TL021 (line.12:current_from @ 1742929816.8582) [src_ev=EV-5fc5fa8b730936d8, EV-5ce88d30bb43c3dd; dst_ev=EV-7afac0045bc682c8, EV-356fe62f9a09d97c]

## 3. Observed Network & Electrical Impact (Epistemically Stratified)
### 3.1 Verified Same-Device Measurement/State Transitions (Consistency Gate Passed)
- [TX001 | verified_state_transition] Point switch.29:is_closed (CA/IOA=116.10140) shifted from pre-command state 1.0 to 0.0 (@ 1742929871.5169, ev=EV-b71b2140c737dfbb).
- [TX002 | verified_state_transition] Point switch.30:is_closed (CA/IOA=116.10160) shifted from pre-command state 1.0 to 0.0 (@ 1742929874.2088, ev=EV-fad7b52fa3a77dcc).

### 3.2 Protocol State Reports Observed Without Verified Transition (Value Undecoded or No Pre-Baseline)
- None.

### 3.3 Candidate Cross-Entity Co-occurring Changes (Unresolved Hypotheses, Not Causal Proof)
- [SL001 / R0007 | command_to_device_state_candidate] (level=unresolved, status=unresolved, gate=failed_gate_kept_unresolved, causal_status=not_established): switch.29:is_closed (EF005) at 1742929871.5481 after EF001 (0 <= dt (0.5613s) <= 15.0s) [src_ev=EV-88c5b849f2e0a429, EV-1f0797f58a768fc7; dst_ev=EV-5a92f9e9c265fda3, EV-904c7e2bfd022a4d].
- [SL002 / R0014 | command_to_device_state_candidate] (level=unresolved, status=unresolved, gate=failed_gate_kept_unresolved, causal_status=not_established): switch.30:is_closed (EF010) at 1742929874.2387 after EF006 (0 <= dt (0.2501s) <= 15.0s) [src_ev=EV-f09b18c4ac3c0b6f, EV-d8b8c5214a0aff5e; dst_ev=EV-5268e24ee3fc9d59, EV-0d8bede16c699564].

## 4. Alternative Explanations & Competing Hypotheses
- No competing multi-branch hypotheses triggered in this window.

## 5. Unresolved Questions, Evidence Gaps & Unattached Observations
- **Evidence Gap**: `{"scope": "TX001", "entity": "switch.29:closed", "missing_stages": ["activation_termination_cot10"]}`
- **Evidence Gap**: `{"scope": "TX002", "entity": "switch.30:closed", "missing_stages": ["activation_termination_cot10"]}`
- **Evidence Gap**: `{"scope": "cross_vantage_payload_conflicts", "count": 408}`
- **Unattached Observations (`16` nodes not on a storyline spine)**:
  - `TL005` (`1742929813.2502`, `network`, `communication`): `172.16.2.2:2404->172.16.1.2:36624/TCP` (`not_on_confirmed_storyline_spine`) [`EV-181a0c6cf60c6e2b, EV-56021b16b592ca28`]
  - `TL013` (`1742929813.2502`, `network`, `electrical_report`): `bus.0:voltage_angle` (`not_on_confirmed_storyline_spine`) [`EV-58ff0f6d9a39cdc1, EV-5b3491fbf0423147`]
  - `TL007` (`1742929813.2643`, `network`, `communication`): `172.16.1.2:36624->172.16.2.2:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-f2f4d3699348d5ca, EV-b58c326ebdc97e9c`]
  - `TL003` (`1742929814.7557`, `network`, `communication`): `172.16.3.9:2404->172.16.1.2:54426/TCP` (`not_on_confirmed_storyline_spine`) [`EV-04c9544b23282a0a, EV-c80f0fe2a5faa722`]
  - `TL004` (`1742929814.7998`, `network`, `communication`): `172.16.1.2:54426->172.16.3.9:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-5fc82d5ec82f2aad, EV-8df73909bdcdac89`]
  - `TL014` (`1742929815.3508`, `network`, `electrical_report`): `line.14:current_from` (`not_on_confirmed_storyline_spine`) [`EV-f4c14050d9836e56, EV-af089f0e3be85a05`]
  - `TL023` (`1742929816.7449`, `network`, `electrical_report`): `line.12:current_to` (`not_on_confirmed_storyline_spine`) [`EV-44971e0d909fd8c8, EV-2c9a01b455c38906`]
  - `TL001` (`1742929817.8047`, `network`, `communication`): `172.16.1.2:39462->172.16.3.11:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-924e325e8fb2ab7e, EV-d71acfb055e7343d`]
  - `TL002` (`1742929817.8369`, `network`, `communication`): `172.16.3.11:2404->172.16.1.2:39462/TCP` (`not_on_confirmed_storyline_spine`) [`EV-8af7305cdd73493b, EV-f355804a5785682d`]
  - `TL018` (`1742929823.8582`, `electrical`, `electrical_change`): `bus.0:voltage_angle` (`not_on_confirmed_storyline_spine`) [`EV-72196ccfc5367d04, EV-035556df01c0a3a5`]
