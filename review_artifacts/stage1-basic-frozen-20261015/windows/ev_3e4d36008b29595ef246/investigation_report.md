# Evidence-Grounded Incident Reconstruction Report

- **Report Status**: `quality_consistent`
- **Quality & Behavioral Consistency (`quality_consistency.json`)**: `consistent`
- **Evidence Lineage Audit (`lineage_consistency.json`)**: `consistent`

- **Incident Window**: `1742959890.1894352` to `1742959950.3827677`
- **Reconstructed IEC-104 Transactions**: `3`
- **Reconstructed Event Storylines**: `6`
- **Verified Same-Device Transitions (Consistency Gate Passed)**: `0`
- **Unverified Protocol State Reports (Value Undecoded or No Pre-Baseline)**: `2`
- **LLM Claim Verifier Output (Separate from Graph Gate)**: `0` verified, `0` withheld

## 1. Incident Sequence & Protocol Transactions
- **TX001** (`1742959890.2245`–`1742959890.5023`): `C_SC_NA_1 (Single command)` on `switch.31:closed` (`CA/IOA=117.10150`, value=`1.0`) over `172.16.1.2:55948 -> 172.16.3.12:2404` at vantages `['n302']`. **Command Acceptance (`COT=7` P/N)**: `accepted_by_rtu`; **Device State Verification**: `state_report_observed_no_pre_baseline` (reason=`missing_pre_command_baseline,pre_test_bit_unknown`); **Completeness**: `partial_state_report_observed_transition_unverified`; **Missing/Unverified Stages**: `['activation_termination_cot10', 'unverified_state_transition:missing_pre_command_baseline,pre_test_bit_unknown']` (`EV-791de060d8603144, EV-e7746bd283b0f24f, EV-2a9f286e93fcbdac, EV-0a1b595ca8d66077`).
  - Inference gate (`state_report`): passed=`False`; pre IV=`None` other flags=`None`; post IV=`False` other flags=`[]`; COT test bits=`{'command': False, 'confirmation': False, 'pre': None, 'post': False}`; failed=`['missing_pre_command_baseline', 'pre_test_bit_unknown']`.
- **TX002** (`1742959900.3104`–`1742959900.3356`): `C_SC_NA_1 (Single command)` on `switch.30:closed` (`CA/IOA=116.10150`, value=`1.0`) over `172.16.1.2:39462 -> 172.16.3.11:2404` at vantages `['n302']`. **Command Acceptance (`COT=7` P/N)**: `accepted_by_rtu`; **Device State Verification**: `no_state_change_observed` (reason=`no_post_command_feedback_observed`); **Completeness**: `confirmation_observed_only_no_state_report`; **Missing/Unverified Stages**: `['activation_termination_cot10', 'post_command_state_or_measurement_change']` (`EV-1584efea78937735, EV-eeeef33791631632, EV-9ea7e1f8c572ba8f, EV-c2ead71c610adcca`).
- **TX003** (`1742959910.3446`–`1742959910.5786`): `C_SC_NA_1 (Single command)` on `switch.27:closed` (`CA/IOA=131.10270`, value=`0.0`) over `172.16.1.2:50978 -> 172.16.3.26:2404` at vantages `['n302']`. **Command Acceptance (`COT=7` P/N)**: `accepted_by_rtu`; **Device State Verification**: `state_report_observed_no_pre_baseline` (reason=`missing_pre_command_baseline,pre_test_bit_unknown`); **Completeness**: `partial_state_report_observed_transition_unverified`; **Missing/Unverified Stages**: `['activation_termination_cot10', 'unverified_state_transition:missing_pre_command_baseline,pre_test_bit_unknown']` (`EV-2b03558caa5c80ba, EV-01204992f7cb6854, EV-889bf81070aa2ebf, EV-d0a2d681d1d5d640`).
  - Inference gate (`state_report`): passed=`False`; pre IV=`None` other flags=`None`; post IV=`False` other flags=`[]`; COT test bits=`{'command': False, 'confirmation': False, 'pre': None, 'post': False}`; failed=`['missing_pre_command_baseline', 'pre_test_bit_unknown']`.

## 2A. Behavioral Incident Reconstruction (No Control Command)
- `33` event anchors found; a control transaction is present, so anchors are listed in `event_anchors.json` and do not root storylines.

## 2B. Incident Scenario Synthesis (Four-Layer Epistemic Integration)
- **Scenario Status**: `synthesized_consistent`
- **Layer 1 Partition**: `0` supported multi-node chains, `0` verified single-anchor chains, `0` sequential same-entity observations (gate failed), `0` quarantined unverified observations (`0` unverified COT=3 precursor reports).
- **Layer 2 Bundles & Bridges**: `0` source bundles (each counted as `1` container), `0` cross-RTU verified element bridges, `0` same-RTU supported relations (not cross-RTU support), `0` multi-bundle bridged components.
- **Layer 3 Candidate Phases**: `1` candidate scenario phases (all cross-device links kept `unresolved`).
- **Layer 4 Source Dependency Ledger**: `0` IEC-104 ASDU, `0` TCP link, `0` ARP, `8` composite containers across `3` RTU(s) (`['172.16.3.11', '172.16.3.12', '172.16.3.26']`), `0` co-reported same-ASDU points collapsed, mirror vantages `['n302']`, `51` IPAL rows excluded (`weight=0`).

### 2B.2 Layer 3 — Candidate Scenario Phases (Cross-Device Links Unresolved)
- **PHS-001** (`+0.035s`..`+20.389s`, profile=`protocol_command_transactions`): bundles=`[]`, verified_bridges=`[]`, sequential_same_device=`[]`, unverified_precursors=`[]`, RTUs=`['172.16.3.11', '172.16.3.12', '172.16.3.26']`, ARP=`[]`, unresolved_candidates=`16`.

### 2B.3 Layer 4 — Evidence-Anchored Competing Explanations & Missing Evidence
- **EXP-001** (`command_induced_device_transition_hypothesis`, status=`unresolved_competing_hypothesis`, causal_status=`not_established`): Observed IEC-104 control activation(s) ['TX001', 'TX002', 'TX003'] on the SCADA network, with 0 transaction(s) passing pre/post setpoint/state consistency checks. Consistent with RTU execution of the received IEC-104 command(s).
  - **Anchored by**: `{'transaction_ids': ['TX001', 'TX002', 'TX003'], 'verified_transition_transaction_ids': [], 'evidence_ids': ['EV-791de060d8603144', 'EV-e7746bd283b0f24f', 'EV-2a9f286e93fcbdac', 'EV-0a1b595ca8d66077', 'EV-1584efea78937735', 'EV-eeeef33791631632', 'EV-9ea7e1f8c572ba8f', 'EV-c2ead71c610adcca']}`
  - **Unverified/candidate links required**: `['TX001', 'TX002', 'TX003']`
  - **Alternative comparison**: Competes with coincidence or unverified physical actuation where protocol confirmation (COT=7) or telemetry shifts occur without independent physical sensor verification.
  - **Missing disambiguating evidence**: `['Independent out-of-band physical process sensor or PMU log not derived from IEC-104', 'Master station operator/application audit log identifying the initiating process', 'Pre-command IEC-104 state baseline (COT=20/COT=1) for switch transactions']`

## 2. Key Findings & Reconstructed Storylines (Contiguous Directed Spines)
### SL001 — Anchor `switch.31:closed` (tx=`TX001`, status=`partial_state_report_observed_transition_unverified`, contiguous_path=`True`, logical_nodes=`3`, independent_sources=`3`, independent_edges=`2`, vantage_captures=`3`)
- Step 1 [R0001 | N-N | iec104_command_confirmation | level=observed_fact | gate=direct_record_observation | independent_evidence]: EF001 (switch.31:closed @ 1742959890.2245) -> EF002 (switch.31:closed @ 1742959890.302) [src_ev=EV-791de060d8603144, EV-e7746bd283b0f24f; dst_ev=EV-2a9f286e93fcbdac, EV-0a1b595ca8d66077]
- Step 2 [R0002 | N-N | subsequent_same_device_state_report | level=observed_fact | gate=direct_record_observation | independent_evidence]: EF002 (switch.31:closed @ 1742959890.302) -> EF003 (switch.31:is_closed @ 1742959890.5023) [src_ev=EV-2a9f286e93fcbdac, EV-0a1b595ca8d66077; dst_ev=EV-358c43a69870cbc2, EV-633361ddd05d7a71]
- Time-aligned IPAL row [R0011 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: EF004 (switch.31:closed=1.0 @ 1742959890.8582) aligned with EF001; not an independent source
- Time-aligned IPAL row [R0012 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: EF004 (switch.31:closed=1.0 @ 1742959890.8582) aligned with EF002; not an independent source
- **Evidence Gaps**: `['activation_termination_cot10', 'unverified_state_transition:missing_pre_command_baseline,pre_test_bit_unknown']`
### SL002 — Anchor `switch.30:closed` (tx=`TX002`, status=`incomplete_confirmation_observed_without_state_report`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`2`)
- Step 1 [R0004 | N-N | iec104_command_confirmation | level=observed_fact | gate=direct_record_observation | independent_evidence]: EF005 (switch.30:closed @ 1742959900.3104) -> EF006 (switch.30:closed @ 1742959900.3356) [src_ev=EV-1584efea78937735, EV-eeeef33791631632; dst_ev=EV-9ea7e1f8c572ba8f, EV-c2ead71c610adcca]
- **Evidence Gaps**: `['activation_termination_cot10', 'post_command_state_or_measurement_change']`
### SL003 — Anchor `switch.27:closed` (tx=`TX003`, status=`partial_state_report_observed_transition_unverified`, contiguous_path=`True`, logical_nodes=`3`, independent_sources=`3`, independent_edges=`2`, vantage_captures=`3`)
- Step 1 [R0005 | N-N | iec104_command_confirmation | level=observed_fact | gate=direct_record_observation | independent_evidence]: EF007 (switch.27:closed @ 1742959910.3446) -> EF008 (switch.27:closed @ 1742959910.3784) [src_ev=EV-2b03558caa5c80ba, EV-01204992f7cb6854; dst_ev=EV-889bf81070aa2ebf, EV-d0a2d681d1d5d640]
- Step 2 [R0006 | N-N | subsequent_same_device_state_report | level=observed_fact | gate=direct_record_observation | independent_evidence]: EF008 (switch.27:closed @ 1742959910.3784) -> EF009 (switch.27:is_closed @ 1742959910.5786) [src_ev=EV-889bf81070aa2ebf, EV-d0a2d681d1d5d640; dst_ev=EV-3c2bcf65ece3c4dc, EV-2ae7f2e071bb8b99]
- Time-aligned IPAL row [R0015 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: EF010 (switch.27:closed=0.0 @ 1742959910.8582) aligned with EF007; not an independent source
- Time-aligned IPAL row [R0016 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: EF010 (switch.27:closed=0.0 @ 1742959910.8582) aligned with EF008; not an independent source
- **Evidence Gaps**: `['activation_termination_cot10', 'unverified_state_transition:missing_pre_command_baseline,pre_test_bit_unknown']`
### SL004 — Anchor `line.11:reactive_power_to` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`4`, independent_sources=`4`, independent_edges=`1`, vantage_captures=`48`)
- Step 1 [R0031 | N-N | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL012 (line.11:reactive_power_to @ 1742959894.5869) -> TL014 (line.11:active_power_from @ 1742959898.8427) [src_ev=EV-a7ba1aa9d4e187d8, EV-39144df9a7adf960; dst_ev=EV-1284d72058c2690b, EV-a1bf399ac48a2646]
- Step 2 [R0018 | N-N | same_iec104_frame | level=observed_fact | gate=direct_record_observation | shared_source_not_double_counted]: TL014 (line.11:active_power_from @ 1742959898.8427) -> TL015 (line.11:current_from @ 1742959898.8427) [src_ev=EV-1284d72058c2690b, EV-a1bf399ac48a2646; dst_ev=EV-4edc60e6f75c8a32, EV-32d4db9d5e698aee]
- Step 3 [R0020 | N-N | same_iec104_frame | level=observed_fact | gate=direct_record_observation | shared_source_not_double_counted]: TL015 (line.11:current_from @ 1742959898.8427) -> TL024 (line.11:reactive_power_from @ 1742959898.8427) [src_ev=EV-4edc60e6f75c8a32, EV-32d4db9d5e698aee; dst_ev=EV-a14b9bd6c1b8b01c, EV-95f4287466dabba4]
- Time-aligned IPAL row [R0013 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL017 (line.11:current_from=25.173728942871094 @ 1742959898.8582) aligned with TL015; not an independent source
- Time-aligned IPAL row [R0014 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL016 (line.11:reactive_power_from=830378.0 @ 1742959898.8582) aligned with TL024; not an independent source
### SL005 — Anchor `line.11:active_power_to` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`4`, independent_sources=`4`, independent_edges=`1`, vantage_captures=`48`)
- Step 1 [R0034 | N-N | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL013 (line.11:active_power_to @ 1742959894.5869) -> TL014 (line.11:active_power_from @ 1742959898.8427) [src_ev=EV-de52f60f586f0ccb, EV-aaeca6a76c4d243a; dst_ev=EV-1284d72058c2690b, EV-a1bf399ac48a2646]
- Step 2 [R0018 | N-N | same_iec104_frame | level=observed_fact | gate=direct_record_observation | shared_source_not_double_counted]: TL014 (line.11:active_power_from @ 1742959898.8427) -> TL015 (line.11:current_from @ 1742959898.8427) [src_ev=EV-1284d72058c2690b, EV-a1bf399ac48a2646; dst_ev=EV-4edc60e6f75c8a32, EV-32d4db9d5e698aee]
- Step 3 [R0020 | N-N | same_iec104_frame | level=observed_fact | gate=direct_record_observation | shared_source_not_double_counted]: TL015 (line.11:current_from @ 1742959898.8427) -> TL024 (line.11:reactive_power_from @ 1742959898.8427) [src_ev=EV-4edc60e6f75c8a32, EV-32d4db9d5e698aee; dst_ev=EV-a14b9bd6c1b8b01c, EV-95f4287466dabba4]
- Time-aligned IPAL row [R0013 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL017 (line.11:current_from=25.173728942871094 @ 1742959898.8582) aligned with TL015; not an independent source
- Time-aligned IPAL row [R0014 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL016 (line.11:reactive_power_from=830378.0 @ 1742959898.8582) aligned with TL024; not an independent source
### SL006 — Anchor `line.11:reactive_power_from` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`12`)
- Step 1 [R0042 | P-P | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL016 (line.11:reactive_power_from @ 1742959898.8582) -> TL017 (line.11:current_from @ 1742959898.8582) [src_ev=EV-4b36b2470389d74e, EV-69f2d483d1edb58a; dst_ev=EV-87f3da7a767339aa, EV-dff2e54e72a49e94]

## 3. Observed Network & Electrical Impact (Epistemically Stratified)
### 3.1 Verified Same-Device Measurement/State Transitions (Consistency Gate Passed)
- No post-command device transition passed all pre/post and target consistency checks.

### 3.2 Protocol State Reports Observed Without Verified Transition (Value Undecoded or No Pre-Baseline)
- [TX001 | state_report_observed_no_pre_baseline] Observed subsequent M_SP_NA_1 (COT=3) state report message on switch.31:is_closed (CA/IOA=117.10160, value_present=True, value=1.0) at 1742959890.5023 [ev=EV-358c43a69870cbc2]; nearby IPAL state table row has value=1.0 (network-derived). Reason transition is NOT confirmed: missing_pre_command_baseline,pre_test_bit_unknown.
- [TX003 | state_report_observed_no_pre_baseline] Observed subsequent M_SP_NA_1 (COT=3) state report message on switch.27:is_closed (CA/IOA=131.10280, value_present=True, value=0.0) at 1742959910.5786 [ev=EV-3c2bcf65ece3c4dc]; nearby IPAL state table row has value=0.0 (network-derived). Reason transition is NOT confirmed: missing_pre_command_baseline,pre_test_bit_unknown.

### 3.3 Candidate Cross-Entity Co-occurring Changes (Unresolved Hypotheses, Not Causal Proof)
- [SL001 / R0044 | cross_entity_temporal_cooccurrence] (level=temporal_cooccurrence, status=unresolved, gate=unresolved_cooccurrence, causal_status=not_established): line.10:reactive_power_from (TL019) at 1742959893.8582 after EF001 (0 <= dt (3.6337s) <= 10.0s) [src_ev=EV-791de060d8603144, EV-e7746bd283b0f24f; dst_ev=EV-19a35f6d5cbcd390, EV-30872e8b698c9fcf].
- [SL001 / R0045 | cross_entity_temporal_cooccurrence] (level=temporal_cooccurrence, status=unresolved, gate=unresolved_cooccurrence, causal_status=not_established): line.10:current_from (TL020) at 1742959893.8582 after EF001 (0 <= dt (3.6337s) <= 10.0s) [src_ev=EV-791de060d8603144, EV-e7746bd283b0f24f; dst_ev=EV-03746eee9baa3655, EV-d80f37e4216e654c].
- [SL001 / R0046 | cross_entity_temporal_cooccurrence] (level=temporal_cooccurrence, status=unresolved, gate=unresolved_cooccurrence, causal_status=not_established): line.10:active_power_from (TL023) at 1742959893.8582 after EF001 (0 <= dt (3.6337s) <= 10.0s) [src_ev=EV-791de060d8603144, EV-e7746bd283b0f24f; dst_ev=EV-d3fb94ee4f095e34, EV-9ecbceed5d3e51de].
- [SL001 / R0047 | cross_entity_temporal_cooccurrence] (level=temporal_cooccurrence, status=unresolved, gate=unresolved_cooccurrence, causal_status=not_established): line.11:reactive_power_to (TL012) at 1742959894.5869 after EF001 (0 <= dt (4.3624s) <= 10.0s) [src_ev=EV-791de060d8603144, EV-e7746bd283b0f24f; dst_ev=EV-a7ba1aa9d4e187d8, EV-39144df9a7adf960].

## 4. Alternative Explanations & Competing Hypotheses
- **[SL001 | competing_cross_entity_cooccurrences | status=`unresolved`]**: Multiple distinct grid measurements (line.10:reactive_power_from, line.10:current_from, line.10:active_power_from, line.11:reactive_power_to) changed within the time horizon after switch.31:closed. Without an independent physical topology/power-flow model in the loop, these remain competing unresolved temporal co-occurrences rather than confirmed causal effects.
- **[SL001 | state_report_without_verified_before_after_values | status=`unresolved`]**: A subsequent M_SP_NA_1 (COT=3) state report was observed for switch.31, but state_report_observed_no_pre_baseline (missing_pre_command_baseline,pre_test_bit_unknown). Therefore a state transition cannot be confirmed from protocol values alone.
- **[SL002 | confirmation_without_state_report | status=`unresolved`]**: RTU 172.16.3.11 sent COT=7 on switch.30:closed (acceptance_status=accepted_by_rtu), but no subsequent COT=3 state report or IPAL new state update occurred. Alternative explanations: (a) the switch/point was already in the target state, or (b) physical actuation did not occur or was not reported within the window.
- **[SL003 | state_report_without_verified_before_after_values | status=`unresolved`]**: A subsequent M_SP_NA_1 (COT=3) state report was observed for switch.27, but state_report_observed_no_pre_baseline (missing_pre_command_baseline,pre_test_bit_unknown). Therefore a state transition cannot be confirmed from protocol values alone.

## 5. Unresolved Questions, Evidence Gaps & Unattached Observations
- **Evidence Gap**: `{"scope": "TX001", "entity": "switch.31:closed", "missing_stages": ["activation_termination_cot10", "unverified_state_transition:missing_pre_command_baseline,pre_test_bit_unknown"]}`
- **Evidence Gap**: `{"scope": "TX002", "entity": "switch.30:closed", "missing_stages": ["activation_termination_cot10", "post_command_state_or_measurement_change"]}`
- **Evidence Gap**: `{"scope": "TX003", "entity": "switch.27:closed", "missing_stages": ["activation_termination_cot10", "unverified_state_transition:missing_pre_command_baseline,pre_test_bit_unknown"]}`
- **Unattached Observations (`14` nodes not on a storyline spine)**:
  - `EF004` (`1742959890.8582`, `electrical`, `electrical_state_update`): `switch.31:closed` (`not_on_confirmed_storyline_spine`) [`EV-abdda607499beb86`]
  - `TL001` (`1742959891.2189`, `network`, `communication`): `172.16.3.13:2404->172.16.1.2:59412/TCP` (`not_on_confirmed_storyline_spine`) [`EV-e17f49f9e8398da2, EV-e0e8dc9b4d8c9487`]
  - `TL003` (`1742959891.2390`, `network`, `communication`): `172.16.1.2:59412->172.16.3.13:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-b10610a52fdf18d1, EV-8d4baaae6bf6b421`]
  - `TL005` (`1742959891.9215`, `network`, `communication`): `172.16.3.17:2404->172.16.1.2:33402/TCP` (`not_on_confirmed_storyline_spine`) [`EV-2924afedff7bdc6e, EV-9f8203102ad87484`]
  - `TL006` (`1742959891.9255`, `network`, `communication`): `172.16.1.2:33402->172.16.3.17:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-9cc6da29a9ccd78f, EV-56630b3f25e21816`]
  - `TL007` (`1742959892.2076`, `network`, `communication`): `172.16.3.7:2404->172.16.1.2:44184/TCP` (`not_on_confirmed_storyline_spine`) [`EV-d2b1f3154bd6a4ee, EV-7a772b55b49975e6`]
  - `TL025` (`1742959892.2296`, `network`, `communication`): `172.16.1.2:44184->172.16.3.7:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-ed9cd3c00a0afb85, EV-7553e64b2ed85818`]
  - `TL019` (`1742959893.8582`, `electrical`, `electrical_change`): `line.10:reactive_power_from` (`not_on_confirmed_storyline_spine`) [`EV-19a35f6d5cbcd390, EV-30872e8b698c9fcf`]
  - `TL020` (`1742959893.8582`, `electrical`, `electrical_change`): `line.10:current_from` (`not_on_confirmed_storyline_spine`) [`EV-03746eee9baa3655, EV-d80f37e4216e654c`]
  - `TL023` (`1742959893.8582`, `electrical`, `electrical_change`): `line.10:active_power_from` (`not_on_confirmed_storyline_spine`) [`EV-d3fb94ee4f095e34, EV-9ecbceed5d3e51de`]
