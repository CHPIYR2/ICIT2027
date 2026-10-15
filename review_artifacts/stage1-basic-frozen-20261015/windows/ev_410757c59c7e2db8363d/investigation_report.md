# Evidence-Grounded Incident Reconstruction Report

- **Report Status**: `quality_consistent`
- **Quality & Behavioral Consistency (`quality_consistency.json`)**: `consistent`
- **Evidence Lineage Audit (`lineage_consistency.json`)**: `consistent`

- **Incident Window**: `1742960142.189464` to `1742960196.3960202`
- **Reconstructed IEC-104 Transactions**: `3`
- **Reconstructed Event Storylines**: `6`
- **Verified Same-Device Transitions (Consistency Gate Passed)**: `0`
- **Unverified Protocol State Reports (Value Undecoded or No Pre-Baseline)**: `2`
- **LLM Claim Verifier Output (Separate from Graph Gate)**: `0` verified, `0` withheld

## 1. Incident Sequence & Protocol Transactions
- **TX001** (`1742960142.1997`–`1742960142.4542`): `C_SC_NA_1 (Single command)` on `switch.2:closed` (`CA/IOA=121.10170`, value=`1.0`) over `172.16.1.2:41276 -> 172.16.3.16:2404` at vantages `['n302']`. **Command Acceptance (`COT=7` P/N)**: `accepted_by_rtu`; **Device State Verification**: `state_report_observed_no_pre_baseline` (reason=`missing_pre_command_baseline,pre_test_bit_unknown`); **Completeness**: `partial_state_report_observed_transition_unverified`; **Missing/Unverified Stages**: `['activation_termination_cot10', 'unverified_state_transition:missing_pre_command_baseline,pre_test_bit_unknown']` (`EV-54be1717dd05f183, EV-e9af0f3b5ed91f18, EV-0ef1ed28eb9802bb, EV-aad7e7733a9c077d`).
  - Inference gate (`state_report`): passed=`False`; pre IV=`None` other flags=`None`; post IV=`False` other flags=`[]`; COT test bits=`{'command': False, 'confirmation': False, 'pre': None, 'post': False}`; failed=`['missing_pre_command_baseline', 'pre_test_bit_unknown']`.
- **TX002** (`1742960150.2619`–`1742960150.3312`): `C_SC_NA_1 (Single command)` on `switch.3:closed` (`CA/IOA=114.10130`, value=`1.0`) over `172.16.1.2:54778 -> 172.16.3.9:2404` at vantages `['n302', 'n318']`. **Command Acceptance (`COT=7` P/N)**: `accepted_by_rtu`; **Device State Verification**: `no_state_change_observed` (reason=`no_post_command_feedback_observed`); **Completeness**: `confirmation_observed_only_no_state_report`; **Missing/Unverified Stages**: `['activation_termination_cot10', 'post_command_state_or_measurement_change']` (`EV-8be1630df59dc70b, EV-61f6d9a9169d196f, EV-ec51096d07e51d36, EV-ae8845d4685d8569`).
- **TX003** (`1742960158.3408`–`1742960158.5912`): `C_SC_NA_1 (Single command)` on `switch.23:closed` (`CA/IOA=110.10130`, value=`0.0`) over `172.16.1.2:58630 -> 172.16.3.5:2404` at vantages `['n302', 'n318']`. **Command Acceptance (`COT=7` P/N)**: `accepted_by_rtu`; **Device State Verification**: `state_report_observed_no_pre_baseline` (reason=`missing_pre_command_baseline,pre_test_bit_unknown`); **Completeness**: `partial_state_report_observed_transition_unverified`; **Missing/Unverified Stages**: `['activation_termination_cot10', 'unverified_state_transition:missing_pre_command_baseline,pre_test_bit_unknown']` (`EV-f1bca24dd2c3ec83, EV-4c8746bb4b8451a0, EV-e65991a15c342aa1, EV-a0b6452b0423db40`).
  - Inference gate (`state_report`): passed=`False`; pre IV=`None` other flags=`None`; post IV=`False` other flags=`[]`; COT test bits=`{'command': False, 'confirmation': False, 'pre': None, 'post': False}`; failed=`['missing_pre_command_baseline', 'pre_test_bit_unknown']`.

## 2A. Behavioral Incident Reconstruction (No Control Command)
- `23` event anchors found; a control transaction is present, so anchors are listed in `event_anchors.json` and do not root storylines.

## 2B. Incident Scenario Synthesis (Four-Layer Epistemic Integration)
- **Scenario Status**: `synthesized_consistent`
- **Layer 1 Partition**: `0` supported multi-node chains, `0` verified single-anchor chains, `0` sequential same-entity observations (gate failed), `0` quarantined unverified observations (`0` unverified COT=3 precursor reports).
- **Layer 2 Bundles & Bridges**: `0` source bundles (each counted as `1` container), `0` cross-RTU verified element bridges, `0` same-RTU supported relations (not cross-RTU support), `0` multi-bundle bridged components.
- **Layer 3 Candidate Phases**: `1` candidate scenario phases (all cross-device links kept `unresolved`).
- **Layer 4 Source Dependency Ledger**: `0` IEC-104 ASDU, `0` TCP link, `0` ARP, `8` composite containers across `3` RTU(s) (`['172.16.3.16', '172.16.3.5', '172.16.3.9']`), `0` co-reported same-ASDU points collapsed, mirror vantages `['n302', 'n318']`, `27` IPAL rows excluded (`weight=0`).

### 2B.2 Layer 3 — Candidate Scenario Phases (Cross-Device Links Unresolved)
- **PHS-001** (`+0.01s`..`+16.402s`, profile=`protocol_command_transactions`): bundles=`[]`, verified_bridges=`[]`, sequential_same_device=`[]`, unverified_precursors=`[]`, RTUs=`['172.16.3.16', '172.16.3.5', '172.16.3.9']`, ARP=`[]`, unresolved_candidates=`16`.

### 2B.3 Layer 4 — Evidence-Anchored Competing Explanations & Missing Evidence
- **EXP-001** (`command_induced_device_transition_hypothesis`, status=`unresolved_competing_hypothesis`, causal_status=`not_established`): Observed IEC-104 control activation(s) ['TX001', 'TX002', 'TX003'] on the SCADA network, with 0 transaction(s) passing pre/post setpoint/state consistency checks. Consistent with RTU execution of the received IEC-104 command(s).
  - **Anchored by**: `{'transaction_ids': ['TX001', 'TX002', 'TX003'], 'verified_transition_transaction_ids': [], 'evidence_ids': ['EV-54be1717dd05f183', 'EV-e9af0f3b5ed91f18', 'EV-0ef1ed28eb9802bb', 'EV-aad7e7733a9c077d', 'EV-8be1630df59dc70b', 'EV-61f6d9a9169d196f', 'EV-ec51096d07e51d36', 'EV-ae8845d4685d8569']}`
  - **Unverified/candidate links required**: `['TX001', 'TX002', 'TX003']`
  - **Alternative comparison**: Competes with coincidence or unverified physical actuation where protocol confirmation (COT=7) or telemetry shifts occur without independent physical sensor verification.
  - **Missing disambiguating evidence**: `['Independent out-of-band physical process sensor or PMU log not derived from IEC-104', 'Master station operator/application audit log identifying the initiating process', 'Pre-command IEC-104 state baseline (COT=20/COT=1) for switch transactions']`

## 2. Key Findings & Reconstructed Storylines (Contiguous Directed Spines)
### SL001 — Anchor `switch.2:closed` (tx=`TX001`, status=`partial_state_report_observed_transition_unverified`, contiguous_path=`True`, logical_nodes=`3`, independent_sources=`3`, independent_edges=`2`, vantage_captures=`3`)
- Step 1 [R0001 | N-N | iec104_command_confirmation | level=observed_fact | gate=direct_record_observation | independent_evidence]: EF001 (switch.2:closed @ 1742960142.1997) -> EF002 (switch.2:closed @ 1742960142.254) [src_ev=EV-54be1717dd05f183, EV-e9af0f3b5ed91f18; dst_ev=EV-0ef1ed28eb9802bb, EV-aad7e7733a9c077d]
- Step 2 [R0002 | N-N | subsequent_same_device_state_report | level=observed_fact | gate=direct_record_observation | independent_evidence]: EF002 (switch.2:closed @ 1742960142.254) -> EF003 (switch.2:is_closed @ 1742960142.4542) [src_ev=EV-0ef1ed28eb9802bb, EV-aad7e7733a9c077d; dst_ev=EV-33fff48df4af2a78, EV-cf12faae1837b127]
- Time-aligned IPAL row [R0011 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: EF004 (switch.2:closed=1.0 @ 1742960142.8582) aligned with EF001; not an independent source
- Time-aligned IPAL row [R0012 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: EF004 (switch.2:closed=1.0 @ 1742960142.8582) aligned with EF002; not an independent source
- **Evidence Gaps**: `['activation_termination_cot10', 'unverified_state_transition:missing_pre_command_baseline,pre_test_bit_unknown']`
### SL002 — Anchor `switch.3:closed` (tx=`TX002`, status=`incomplete_confirmation_observed_without_state_report`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`4`)
- Step 1 [R0004 | N-N | iec104_command_confirmation | level=observed_fact | gate=direct_record_observation | independent_evidence]: EF005 (switch.3:closed @ 1742960150.2619) -> EF006 (switch.3:closed @ 1742960150.3012) [src_ev=EV-8be1630df59dc70b, EV-61f6d9a9169d196f; dst_ev=EV-b09acfb1be8d2821, EV-eab3abf599f49c3d]
- **Evidence Gaps**: `['activation_termination_cot10', 'post_command_state_or_measurement_change']`
### SL003 — Anchor `switch.23:closed` (tx=`TX003`, status=`partial_state_report_observed_transition_unverified`, contiguous_path=`True`, logical_nodes=`3`, independent_sources=`3`, independent_edges=`2`, vantage_captures=`6`)
- Step 1 [R0005 | N-N | iec104_command_confirmation | level=observed_fact | gate=direct_record_observation | independent_evidence]: EF007 (switch.23:closed @ 1742960158.3408) -> EF008 (switch.23:closed @ 1742960158.3728) [src_ev=EV-f1bca24dd2c3ec83, EV-4c8746bb4b8451a0; dst_ev=EV-407d1076d34c455f, EV-ee87113136748ebb]
- Step 2 [R0006 | N-N | subsequent_same_device_state_report | level=observed_fact | gate=direct_record_observation | independent_evidence]: EF008 (switch.23:closed @ 1742960158.3728) -> EF009 (switch.23:is_closed @ 1742960158.5731) [src_ev=EV-407d1076d34c455f, EV-ee87113136748ebb; dst_ev=EV-4fd04a0818c5d225, EV-6c7be67fd064e3a9]
- Time-aligned IPAL row [R0016 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: EF010 (switch.23:closed=0.0 @ 1742960158.8582) aligned with EF007; not an independent source
- Time-aligned IPAL row [R0017 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: EF010 (switch.23:closed=0.0 @ 1742960158.8582) aligned with EF008; not an independent source
- **Evidence Gaps**: `['activation_termination_cot10', 'unverified_state_transition:missing_pre_command_baseline,pre_test_bit_unknown']`
### SL004 — Anchor `line.13:active_power_from` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`0`, vantage_captures=`48`)
- Step 1 [R0018 | N-N | same_iec104_frame | level=observed_fact | gate=direct_record_observation | shared_source_not_double_counted]: TL012 (line.13:active_power_from @ 1742960143.7552) -> TL024 (line.13:current_from @ 1742960143.7552) [src_ev=EV-161a1ba1e455642d, EV-7494a15fde6e1551; dst_ev=EV-ff87f7ec1f15122f, EV-6b364ae5cd57a563]
- Time-aligned IPAL row [R0013 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL016 (line.13:active_power_from=12667.7607421875 @ 1742960143.8582) aligned with TL012; not an independent source
- Time-aligned IPAL row [R0014 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL017 (line.13:current_from=7.335753440856934 @ 1742960143.8582) aligned with TL024; not an independent source
### SL005 — Anchor `line.13:active_power_from` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`4`, independent_sources=`4`, independent_edges=`3`, vantage_captures=`23`)
- Step 1 [R0021 | P-P | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL016 (line.13:active_power_from @ 1742960143.8582) -> TL017 (line.13:current_from @ 1742960143.8582) [src_ev=EV-817101dd9054293f, EV-dc3c439a65e7fb16; dst_ev=EV-80705a9e596001a3, EV-deb5b2136a264919]
- Step 2 [R0024 | P-P | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL017 (line.13:current_from @ 1742960143.8582) -> TL019 (line.13:reactive_power_from @ 1742960143.8582) [src_ev=EV-80705a9e596001a3, EV-deb5b2136a264919; dst_ev=EV-f55bd2d558c121f2, EV-924309dbb2e211f1]
- Step 3 [R0026 | P-P | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL019 (line.13:reactive_power_from @ 1742960143.8582) -> TL018 (line.13:current_to @ 1742960148.8582) [src_ev=EV-f55bd2d558c121f2, EV-924309dbb2e211f1; dst_ev=EV-97399a6306ea20e1, EV-c1eff7ae2721a102]
### SL006 — Anchor `line.13:active_power_to` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`0`, vantage_captures=`20`)
- Step 1 [R0019 | N-N | same_iec104_frame | level=observed_fact | gate=direct_record_observation | shared_source_not_double_counted]: TL013 (line.13:active_power_to @ 1742960148.8053) -> TL014 (line.13:reactive_power_to @ 1742960148.8053) [src_ev=EV-9d2e5b3f7e695f51, EV-d6e9b7d75ff345e2; dst_ev=EV-f1c15d35bf6d5468, EV-51c2681ae5ad499c]

## 3. Observed Network & Electrical Impact (Epistemically Stratified)
### 3.1 Verified Same-Device Measurement/State Transitions (Consistency Gate Passed)
- No post-command device transition passed all pre/post and target consistency checks.

### 3.2 Protocol State Reports Observed Without Verified Transition (Value Undecoded or No Pre-Baseline)
- [TX001 | state_report_observed_no_pre_baseline] Observed subsequent M_SP_NA_1 (COT=3) state report message on switch.2:is_closed (CA/IOA=121.10180, value_present=True, value=1.0) at 1742960142.4542 [ev=EV-33fff48df4af2a78]; nearby IPAL state table row has value=1.0 (network-derived). Reason transition is NOT confirmed: missing_pre_command_baseline,pre_test_bit_unknown.
- [TX003 | state_report_observed_no_pre_baseline] Observed subsequent M_SP_NA_1 (COT=3) state report message on switch.23:is_closed (CA/IOA=110.10140, value_present=True, value=0.0) at 1742960158.5731 [ev=EV-4fd04a0818c5d225, EV-6c7be67fd064e3a9]; nearby IPAL state table row has value=0.0 (network-derived). Reason transition is NOT confirmed: missing_pre_command_baseline,pre_test_bit_unknown.

### 3.3 Candidate Cross-Entity Co-occurring Changes (Unresolved Hypotheses, Not Causal Proof)
- [SL001 / R0028 | cross_entity_temporal_cooccurrence] (level=temporal_cooccurrence, status=unresolved, gate=unresolved_cooccurrence, causal_status=not_established): bus.0:voltage_angle (TL020) at 1742960142.8582 after EF001 (0 <= dt (0.6585s) <= 10.0s) [src_ev=EV-54be1717dd05f183, EV-e9af0f3b5ed91f18; dst_ev=EV-0780182443628425, EV-07f6558bd83226b7].
- [SL001 / R0029 | cross_entity_temporal_cooccurrence] (level=temporal_cooccurrence, status=unresolved, gate=unresolved_cooccurrence, causal_status=not_established): line.13:active_power_from (TL012) at 1742960143.7552 after EF001 (0 <= dt (1.5555s) <= 10.0s) [src_ev=EV-54be1717dd05f183, EV-e9af0f3b5ed91f18; dst_ev=EV-161a1ba1e455642d, EV-7494a15fde6e1551].
- [SL001 / R0030 | cross_entity_temporal_cooccurrence] (level=temporal_cooccurrence, status=unresolved, gate=unresolved_cooccurrence, causal_status=not_established): line.13:current_from (TL024) at 1742960143.7552 after EF001 (0 <= dt (1.5555s) <= 10.0s) [src_ev=EV-54be1717dd05f183, EV-e9af0f3b5ed91f18; dst_ev=EV-ff87f7ec1f15122f, EV-6b364ae5cd57a563].
- [SL001 / R0031 | cross_entity_temporal_cooccurrence] (level=temporal_cooccurrence, status=unresolved, gate=unresolved_cooccurrence, causal_status=not_established): line.13:active_power_from (TL016) at 1742960143.8582 after EF001 (0 <= dt (1.6585s) <= 10.0s) [src_ev=EV-54be1717dd05f183, EV-e9af0f3b5ed91f18; dst_ev=EV-817101dd9054293f, EV-dc3c439a65e7fb16].

## 4. Alternative Explanations & Competing Hypotheses
- **[SL001 | competing_cross_entity_cooccurrences | status=`unresolved`]**: Multiple distinct grid measurements (bus.0:voltage_angle, line.13:active_power_from, line.13:current_from, line.13:active_power_from) changed within the time horizon after switch.2:closed. Without an independent physical topology/power-flow model in the loop, these remain competing unresolved temporal co-occurrences rather than confirmed causal effects.
- **[SL001 | state_report_without_verified_before_after_values | status=`unresolved`]**: A subsequent M_SP_NA_1 (COT=3) state report was observed for switch.2, but state_report_observed_no_pre_baseline (missing_pre_command_baseline,pre_test_bit_unknown). Therefore a state transition cannot be confirmed from protocol values alone.
- **[SL002 | confirmation_without_state_report | status=`unresolved`]**: RTU 172.16.3.9 sent COT=7 on switch.3:closed (acceptance_status=accepted_by_rtu), but no subsequent COT=3 state report or IPAL new state update occurred. Alternative explanations: (a) the switch/point was already in the target state, or (b) physical actuation did not occur or was not reported within the window.
- **[SL003 | state_report_without_verified_before_after_values | status=`unresolved`]**: A subsequent M_SP_NA_1 (COT=3) state report was observed for switch.23, but state_report_observed_no_pre_baseline (missing_pre_command_baseline,pre_test_bit_unknown). Therefore a state transition cannot be confirmed from protocol values alone.

## 5. Unresolved Questions, Evidence Gaps & Unattached Observations
- **Evidence Gap**: `{"scope": "TX001", "entity": "switch.2:closed", "missing_stages": ["activation_termination_cot10", "unverified_state_transition:missing_pre_command_baseline,pre_test_bit_unknown"]}`
- **Evidence Gap**: `{"scope": "TX002", "entity": "switch.3:closed", "missing_stages": ["activation_termination_cot10", "post_command_state_or_measurement_change"]}`
- **Evidence Gap**: `{"scope": "TX003", "entity": "switch.23:closed", "missing_stages": ["activation_termination_cot10", "unverified_state_transition:missing_pre_command_baseline,pre_test_bit_unknown"]}`
- **Unattached Observations (`13` nodes not on a storyline spine)**:
  - `TL005` (`1742960142.4097`, `network`, `communication`): `172.16.3.7:2404->172.16.1.2:44184/TCP` (`not_on_confirmed_storyline_spine`) [`EV-9906dcaf55aa5594, EV-f178fd1c3c27c521`]
  - `TL007` (`1742960142.4291`, `network`, `communication`): `172.16.2.3:2404->172.16.1.2:42436/TCP` (`not_on_confirmed_storyline_spine`) [`EV-68145c85bfb871c3, EV-a01ca49d848c634d`]
  - `TL008` (`1742960142.4318`, `network`, `communication`): `172.16.1.2:44184->172.16.3.7:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-d122ba838a8906be, EV-1fc1eb4f6fec8089`]
  - `TL026` (`1742960142.4532`, `network`, `communication`): `172.16.1.2:42436->172.16.2.3:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-c3f2c094ed04ca1c, EV-e222b37707aaf20f`]
  - `EF004` (`1742960142.8582`, `electrical`, `electrical_state_update`): `switch.2:closed` (`not_on_confirmed_storyline_spine`) [`EV-f0861350fc8b0977`]
  - `TL020` (`1742960142.8582`, `electrical`, `electrical_change`): `bus.0:voltage_angle` (`not_on_confirmed_storyline_spine`) [`EV-0780182443628425, EV-07f6558bd83226b7`]
  - `TL001` (`1742960143.7552`, `network`, `communication`): `172.16.3.9:2404->172.16.1.2:54778/TCP` (`not_on_confirmed_storyline_spine`) [`EV-e22dd4aae363b26f, EV-9c3f38a1a78c70bd`]
  - `TL003` (`1742960143.7893`, `network`, `communication`): `172.16.1.2:54778->172.16.3.9:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-15225921d3ad5092, EV-d81d7bd6b1cfa514`]
  - `TL023` (`1742960143.8582`, `electrical`, `electrical_change`): `line.8:reactive_power_to` (`not_on_confirmed_storyline_spine`) [`EV-a92149c5d4356cdb, EV-89dce5dbbdffba5d`]
  - `TL015` (`1742960149.1239`, `network`, `electrical_report`): `line.8:reactive_power_from` (`not_on_confirmed_storyline_spine`) [`EV-67a1e0afc1756b09, EV-9e6e0e90864ff1ea`]
