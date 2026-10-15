# Evidence-Grounded Incident Reconstruction Report

- **Report Status**: `quality_consistent`
- **Quality & Behavioral Consistency (`quality_consistency.json`)**: `consistent`
- **Evidence Lineage Audit (`lineage_consistency.json`)**: `consistent`

- **Incident Window**: `1742938056.2267296` to `1742938093.263869`
- **Reconstructed IEC-104 Transactions**: `2`
- **Reconstructed Event Storylines**: `6`
- **Verified Same-Device Transitions (Consistency Gate Passed)**: `0`
- **Unverified Protocol State Reports (Value Undecoded or No Pre-Baseline)**: `2`
- **LLM Claim Verifier Output (Separate from Graph Gate)**: `0` verified, `0` withheld

## 1. Incident Sequence & Protocol Transactions
- **TX001** (`1742938056.2689`–`1742938056.5154`): `C_SC_NA_1 (Single command)` on `switch.4:closed` (`CA/IOA=131.10210`, value=`1.0`) over `172.16.1.2:54802 -> 172.16.3.26:2404` at vantages `['n302']`. **Command Acceptance (`COT=7` P/N)**: `accepted_by_rtu`; **Device State Verification**: `state_report_observed_no_pre_baseline` (reason=`missing_pre_command_baseline,pre_test_bit_unknown`); **Completeness**: `partial_state_report_observed_transition_unverified`; **Missing/Unverified Stages**: `['activation_termination_cot10', 'unverified_state_transition:missing_pre_command_baseline,pre_test_bit_unknown']` (`EV-15ce6a45948b7e25, EV-397bf7adea19aef0, EV-3d5de49b0fe73810, EV-e259ad36c0195482`).
  - Inference gate (`state_report`): passed=`False`; pre IV=`None` other flags=`None`; post IV=`False` other flags=`[]`; COT test bits=`{'command': False, 'confirmation': False, 'pre': None, 'post': False}`; failed=`['missing_pre_command_baseline', 'pre_test_bit_unknown']`.
- **TX002** (`1742938063.2670`–`1742938063.5348`): `C_SC_NA_1 (Single command)` on `switch.31:closed` (`CA/IOA=117.10150`, value=`0.0`) over `172.16.1.2:55948 -> 172.16.3.12:2404` at vantages `['n302']`. **Command Acceptance (`COT=7` P/N)**: `accepted_by_rtu`; **Device State Verification**: `state_report_observed_no_pre_baseline` (reason=`missing_pre_command_baseline,pre_test_bit_unknown`); **Completeness**: `partial_state_report_observed_transition_unverified`; **Missing/Unverified Stages**: `['activation_termination_cot10', 'unverified_state_transition:missing_pre_command_baseline,pre_test_bit_unknown']` (`EV-65db70630c6674e1, EV-8d848b304b8aa2a0, EV-113cdc9868b71a0c, EV-af1a839800e61f35`).
  - Inference gate (`state_report`): passed=`False`; pre IV=`None` other flags=`None`; post IV=`False` other flags=`[]`; COT test bits=`{'command': False, 'confirmation': False, 'pre': None, 'post': False}`; failed=`['missing_pre_command_baseline', 'pre_test_bit_unknown']`.

## 2A. Behavioral Incident Reconstruction (No Control Command)
- `15` event anchors found; a control transaction is present, so anchors are listed in `event_anchors.json` and do not root storylines.

## 2B. Incident Scenario Synthesis (Four-Layer Epistemic Integration)
- **Scenario Status**: `synthesized_consistent`
- **Layer 1 Partition**: `0` supported multi-node chains, `0` verified single-anchor chains, `0` sequential same-entity observations (gate failed), `0` quarantined unverified observations (`0` unverified COT=3 precursor reports).
- **Layer 2 Bundles & Bridges**: `0` source bundles (each counted as `1` container), `0` cross-RTU verified element bridges, `0` same-RTU supported relations (not cross-RTU support), `0` multi-bundle bridged components.
- **Layer 3 Candidate Phases**: `1` candidate scenario phases (all cross-device links kept `unresolved`).
- **Layer 4 Source Dependency Ledger**: `0` IEC-104 ASDU, `0` TCP link, `0` ARP, `6` composite containers across `2` RTU(s) (`['172.16.3.12', '172.16.3.26']`), `0` co-reported same-ASDU points collapsed, mirror vantages `['n302']`, `30` IPAL rows excluded (`weight=0`).

### 2B.2 Layer 3 — Candidate Scenario Phases (Cross-Device Links Unresolved)
- **PHS-001** (`+0.042s`..`+7.308s`, profile=`protocol_command_transactions`): bundles=`[]`, verified_bridges=`[]`, sequential_same_device=`[]`, unverified_precursors=`[]`, RTUs=`['172.16.3.12', '172.16.3.26']`, ARP=`[]`, unresolved_candidates=`16`.

### 2B.3 Layer 4 — Evidence-Anchored Competing Explanations & Missing Evidence
- **EXP-001** (`command_induced_device_transition_hypothesis`, status=`unresolved_competing_hypothesis`, causal_status=`not_established`): Observed IEC-104 control activation(s) ['TX001', 'TX002'] on the SCADA network, with 0 transaction(s) passing pre/post setpoint/state consistency checks. Consistent with RTU execution of the received IEC-104 command(s).
  - **Anchored by**: `{'transaction_ids': ['TX001', 'TX002'], 'verified_transition_transaction_ids': [], 'evidence_ids': ['EV-15ce6a45948b7e25', 'EV-397bf7adea19aef0', 'EV-3d5de49b0fe73810', 'EV-e259ad36c0195482', 'EV-65db70630c6674e1', 'EV-8d848b304b8aa2a0', 'EV-113cdc9868b71a0c', 'EV-af1a839800e61f35']}`
  - **Unverified/candidate links required**: `['TX001', 'TX002']`
  - **Alternative comparison**: Competes with coincidence or unverified physical actuation where protocol confirmation (COT=7) or telemetry shifts occur without independent physical sensor verification.
  - **Missing disambiguating evidence**: `['Independent out-of-band physical process sensor or PMU log not derived from IEC-104', 'Master station operator/application audit log identifying the initiating process', 'Pre-command IEC-104 state baseline (COT=20/COT=1) for switch transactions']`

## 2. Key Findings & Reconstructed Storylines (Contiguous Directed Spines)
### SL001 — Anchor `switch.4:closed` (tx=`TX001`, status=`partial_state_report_observed_transition_unverified`, contiguous_path=`True`, logical_nodes=`3`, independent_sources=`3`, independent_edges=`2`, vantage_captures=`3`)
- Step 1 [R0001 | N-N | iec104_command_confirmation | level=observed_fact | gate=direct_record_observation | independent_evidence]: EF001 (switch.4:closed @ 1742938056.2689) -> EF002 (switch.4:closed @ 1742938056.3151) [src_ev=EV-15ce6a45948b7e25, EV-397bf7adea19aef0; dst_ev=EV-3d5de49b0fe73810, EV-e259ad36c0195482]
- Step 2 [R0002 | N-N | subsequent_same_device_state_report | level=observed_fact | gate=direct_record_observation | independent_evidence]: EF002 (switch.4:closed @ 1742938056.3151) -> EF003 (switch.4:is_closed @ 1742938056.5154) [src_ev=EV-3d5de49b0fe73810, EV-e259ad36c0195482; dst_ev=EV-68ecc0b7cb6b71dc, EV-102046b5a9b64170]
- Time-aligned IPAL row [R0010 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: EF004 (switch.4:closed=1.0 @ 1742938056.8582) aligned with EF001; not an independent source
- Time-aligned IPAL row [R0011 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: EF004 (switch.4:closed=1.0 @ 1742938056.8582) aligned with EF002; not an independent source
- **Evidence Gaps**: `['activation_termination_cot10', 'unverified_state_transition:missing_pre_command_baseline,pre_test_bit_unknown']`
### SL002 — Anchor `switch.31:closed` (tx=`TX002`, status=`partial_state_report_observed_transition_unverified`, contiguous_path=`True`, logical_nodes=`3`, independent_sources=`3`, independent_edges=`2`, vantage_captures=`3`)
- Step 1 [R0004 | N-N | iec104_command_confirmation | level=observed_fact | gate=direct_record_observation | independent_evidence]: EF005 (switch.31:closed @ 1742938063.267) -> EF006 (switch.31:closed @ 1742938063.3346) [src_ev=EV-65db70630c6674e1, EV-8d848b304b8aa2a0; dst_ev=EV-113cdc9868b71a0c, EV-af1a839800e61f35]
- Step 2 [R0005 | N-N | subsequent_same_device_state_report | level=observed_fact | gate=direct_record_observation | independent_evidence]: EF006 (switch.31:closed @ 1742938063.3346) -> EF007 (switch.31:is_closed @ 1742938063.5348) [src_ev=EV-113cdc9868b71a0c, EV-af1a839800e61f35; dst_ev=EV-31df183b6c11670a, EV-cadf21723e02971d]
- Time-aligned IPAL row [R0016 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: EF008 (switch.31:closed=0.0 @ 1742938063.8582) aligned with EF005; not an independent source
- Time-aligned IPAL row [R0017 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: EF008 (switch.31:closed=0.0 @ 1742938063.8582) aligned with EF006; not an independent source
- **Evidence Gaps**: `['activation_termination_cot10', 'unverified_state_transition:missing_pre_command_baseline,pre_test_bit_unknown']`
### SL003 — Anchor `line.14:active_power_from` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`4`, independent_sources=`4`, independent_edges=`1`, vantage_captures=`32`)
- Step 1 [R0026 | N-N | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL011 (line.14:active_power_from @ 1742938060.6066) -> TL012 (line.14:reactive_power_to @ 1742938061.6179) [src_ev=EV-5d4f8dc478aeafb5, EV-b90b429664b76071; dst_ev=EV-05538aa33f248974, EV-98ad188c08a26b38]
- Step 2 [R0021 | N-N | same_iec104_frame | level=observed_fact | gate=direct_record_observation | shared_source_not_double_counted]: TL012 (line.14:reactive_power_to @ 1742938061.6179) -> TL013 (line.14:active_power_to @ 1742938061.6179) [src_ev=EV-05538aa33f248974, EV-98ad188c08a26b38; dst_ev=EV-50dab75dd0dea125, EV-f591f84c387b7db1]
- Step 3 [R0023 | N-N | same_iec104_frame | level=observed_fact | gate=direct_record_observation | shared_source_not_double_counted]: TL013 (line.14:active_power_to @ 1742938061.6179) -> TL024 (line.14:current_to @ 1742938061.6179) [src_ev=EV-50dab75dd0dea125, EV-f591f84c387b7db1; dst_ev=EV-91c2bbf0ce0edb89, EV-3e46e53b5df89bf6]
- Time-aligned IPAL row [R0014 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL019 (line.14:reactive_power_to=-515624.375 @ 1742938061.8582) aligned with TL012; not an independent source
- Time-aligned IPAL row [R0015 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL017 (line.14:current_to=15.229866981506348 @ 1742938061.8582) aligned with TL024; not an independent source
### SL004 — Anchor `line.14:reactive_power_from` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`4`, independent_sources=`4`, independent_edges=`3`, vantage_captures=`15`)
- Step 1 [R0036 | P-P | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL015 (line.14:reactive_power_from @ 1742938060.8582) -> TL016 (line.14:current_from @ 1742938060.8582) [src_ev=EV-24bac811bee09340, EV-af2c3810404a3d3f; dst_ev=EV-1348c9f414ff8d6b, EV-6f7cceda041e275b]
- Step 2 [R0039 | P-P | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL016 (line.14:current_from @ 1742938060.8582) -> TL017 (line.14:current_to @ 1742938061.8582) [src_ev=EV-1348c9f414ff8d6b, EV-6f7cceda041e275b; dst_ev=EV-5a2c2a30a91caca4, EV-25a111b8f65bee45]
- Step 3 [R0045 | P-P | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL017 (line.14:current_to @ 1742938061.8582) -> TL019 (line.14:reactive_power_to @ 1742938061.8582) [src_ev=EV-5a2c2a30a91caca4, EV-25a111b8f65bee45; dst_ev=EV-c7eee3d998c7195c, EV-a7d7083eb2dff400]
### SL005 — Anchor `line.14:reactive_power_from` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`4`, independent_sources=`4`, independent_edges=`1`, vantage_captures=`32`)
- Step 1 [R0030 | N-N | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL014 (line.14:reactive_power_from @ 1742938060.6066) -> TL012 (line.14:reactive_power_to @ 1742938061.6179) [src_ev=EV-488754bae25d8421, EV-5691251b7f28e8bc; dst_ev=EV-05538aa33f248974, EV-98ad188c08a26b38]
- Step 2 [R0021 | N-N | same_iec104_frame | level=observed_fact | gate=direct_record_observation | shared_source_not_double_counted]: TL012 (line.14:reactive_power_to @ 1742938061.6179) -> TL013 (line.14:active_power_to @ 1742938061.6179) [src_ev=EV-05538aa33f248974, EV-98ad188c08a26b38; dst_ev=EV-50dab75dd0dea125, EV-f591f84c387b7db1]
- Step 3 [R0023 | N-N | same_iec104_frame | level=observed_fact | gate=direct_record_observation | shared_source_not_double_counted]: TL013 (line.14:active_power_to @ 1742938061.6179) -> TL024 (line.14:current_to @ 1742938061.6179) [src_ev=EV-50dab75dd0dea125, EV-f591f84c387b7db1; dst_ev=EV-91c2bbf0ce0edb89, EV-3e46e53b5df89bf6]
- Time-aligned IPAL row [R0012 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL015 (line.14:reactive_power_from=513618.03125 @ 1742938060.8582) aligned with TL014; not an independent source
- Time-aligned IPAL row [R0014 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL019 (line.14:reactive_power_to=-515624.375 @ 1742938061.8582) aligned with TL012; not an independent source
- Time-aligned IPAL row [R0015 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL017 (line.14:current_to=15.229866981506348 @ 1742938061.8582) aligned with TL024; not an independent source
### SL006 — Anchor `line.14:current_from` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`4`, independent_sources=`4`, independent_edges=`1`, vantage_captures=`32`)
- Step 1 [R0033 | N-N | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL023 (line.14:current_from @ 1742938060.6066) -> TL012 (line.14:reactive_power_to @ 1742938061.6179) [src_ev=EV-f0a1719847ab08cd, EV-7d0a6fc16fba0f23; dst_ev=EV-05538aa33f248974, EV-98ad188c08a26b38]
- Step 2 [R0021 | N-N | same_iec104_frame | level=observed_fact | gate=direct_record_observation | shared_source_not_double_counted]: TL012 (line.14:reactive_power_to @ 1742938061.6179) -> TL013 (line.14:active_power_to @ 1742938061.6179) [src_ev=EV-05538aa33f248974, EV-98ad188c08a26b38; dst_ev=EV-50dab75dd0dea125, EV-f591f84c387b7db1]
- Step 3 [R0023 | N-N | same_iec104_frame | level=observed_fact | gate=direct_record_observation | shared_source_not_double_counted]: TL013 (line.14:active_power_to @ 1742938061.6179) -> TL024 (line.14:current_to @ 1742938061.6179) [src_ev=EV-50dab75dd0dea125, EV-f591f84c387b7db1; dst_ev=EV-91c2bbf0ce0edb89, EV-3e46e53b5df89bf6]
- Time-aligned IPAL row [R0013 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL016 (line.14:current_from=14.772528648376465 @ 1742938060.8582) aligned with TL023; not an independent source
- Time-aligned IPAL row [R0014 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL019 (line.14:reactive_power_to=-515624.375 @ 1742938061.8582) aligned with TL012; not an independent source
- Time-aligned IPAL row [R0015 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL017 (line.14:current_to=15.229866981506348 @ 1742938061.8582) aligned with TL024; not an independent source

## 3. Observed Network & Electrical Impact (Epistemically Stratified)
### 3.1 Verified Same-Device Measurement/State Transitions (Consistency Gate Passed)
- No post-command device transition passed all pre/post and target consistency checks.

### 3.2 Protocol State Reports Observed Without Verified Transition (Value Undecoded or No Pre-Baseline)
- [TX001 | state_report_observed_no_pre_baseline] Observed subsequent M_SP_NA_1 (COT=3) state report message on switch.4:is_closed (CA/IOA=131.10220, value_present=True, value=1.0) at 1742938056.5154 [ev=EV-68ecc0b7cb6b71dc]; nearby IPAL state table row has value=1.0 (network-derived). Reason transition is NOT confirmed: missing_pre_command_baseline,pre_test_bit_unknown.
- [TX002 | state_report_observed_no_pre_baseline] Observed subsequent M_SP_NA_1 (COT=3) state report message on switch.31:is_closed (CA/IOA=117.10160, value_present=True, value=0.0) at 1742938063.5348 [ev=EV-31df183b6c11670a]; nearby IPAL state table row has value=0.0 (network-derived). Reason transition is NOT confirmed: missing_pre_command_baseline,pre_test_bit_unknown.

### 3.3 Candidate Cross-Entity Co-occurring Changes (Unresolved Hypotheses, Not Causal Proof)
- [SL001 / R0046 | cross_entity_temporal_cooccurrence] (level=temporal_cooccurrence, status=unresolved, gate=unresolved_cooccurrence, causal_status=not_established): bus.0:voltage_angle (TL018) at 1742938058.8582 after EF001 (0 <= dt (2.5893s) <= 10.0s) [src_ev=EV-15ce6a45948b7e25, EV-397bf7adea19aef0; dst_ev=EV-161635a4e28e3b61, EV-8d54d5eeaa1a3e30].
- [SL001 / R0047 | cross_entity_temporal_cooccurrence] (level=temporal_cooccurrence, status=unresolved, gate=unresolved_cooccurrence, causal_status=not_established): line.14:active_power_from (TL011) at 1742938060.6066 after EF001 (0 <= dt (4.3377s) <= 10.0s) [src_ev=EV-15ce6a45948b7e25, EV-397bf7adea19aef0; dst_ev=EV-5d4f8dc478aeafb5, EV-b90b429664b76071].
- [SL001 / R0048 | cross_entity_temporal_cooccurrence] (level=temporal_cooccurrence, status=unresolved, gate=unresolved_cooccurrence, causal_status=not_established): line.14:reactive_power_from (TL014) at 1742938060.6066 after EF001 (0 <= dt (4.3377s) <= 10.0s) [src_ev=EV-15ce6a45948b7e25, EV-397bf7adea19aef0; dst_ev=EV-488754bae25d8421, EV-5691251b7f28e8bc].
- [SL001 / R0049 | cross_entity_temporal_cooccurrence] (level=temporal_cooccurrence, status=unresolved, gate=unresolved_cooccurrence, causal_status=not_established): line.14:current_from (TL023) at 1742938060.6066 after EF001 (0 <= dt (4.3377s) <= 10.0s) [src_ev=EV-15ce6a45948b7e25, EV-397bf7adea19aef0; dst_ev=EV-f0a1719847ab08cd, EV-7d0a6fc16fba0f23].

## 4. Alternative Explanations & Competing Hypotheses
- **[SL001 | competing_cross_entity_cooccurrences | status=`unresolved`]**: Multiple distinct grid measurements (bus.0:voltage_angle, line.14:active_power_from, line.14:reactive_power_from, line.14:current_from) changed within the time horizon after switch.4:closed. Without an independent physical topology/power-flow model in the loop, these remain competing unresolved temporal co-occurrences rather than confirmed causal effects.
- **[SL001 | state_report_without_verified_before_after_values | status=`unresolved`]**: A subsequent M_SP_NA_1 (COT=3) state report was observed for switch.4, but state_report_observed_no_pre_baseline (missing_pre_command_baseline,pre_test_bit_unknown). Therefore a state transition cannot be confirmed from protocol values alone.
- **[SL002 | state_report_without_verified_before_after_values | status=`unresolved`]**: A subsequent M_SP_NA_1 (COT=3) state report was observed for switch.31, but state_report_observed_no_pre_baseline (missing_pre_command_baseline,pre_test_bit_unknown). Therefore a state transition cannot be confirmed from protocol values alone.

## 5. Unresolved Questions, Evidence Gaps & Unattached Observations
- **Evidence Gap**: `{"scope": "TX001", "entity": "switch.4:closed", "missing_stages": ["activation_termination_cot10", "unverified_state_transition:missing_pre_command_baseline,pre_test_bit_unknown"]}`
- **Evidence Gap**: `{"scope": "TX002", "entity": "switch.31:closed", "missing_stages": ["activation_termination_cot10", "unverified_state_transition:missing_pre_command_baseline,pre_test_bit_unknown"]}`
- **Unattached Observations (`12` nodes not on a storyline spine)**:
  - `TL001` (`1742938056.3919`, `network`, `communication`): `172.16.3.11:2404->172.16.1.2:39462/TCP` (`not_on_confirmed_storyline_spine`) [`EV-b1da180d1508469a, EV-8f201f17dbd774bc`]
  - `TL002` (`1742938056.4180`, `network`, `communication`): `172.16.1.2:39462->172.16.3.11:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-4d6ebab49d4ba206, EV-f3f904f246e2660a`]
  - `EF004` (`1742938056.8582`, `electrical`, `electrical_state_update`): `switch.4:closed` (`not_on_confirmed_storyline_spine`) [`EV-456b8be597560b07`]
  - `TL007` (`1742938057.2938`, `network`, `communication`): `172.16.3.4:2404->172.16.1.2:58792/TCP` (`not_on_confirmed_storyline_spine`) [`EV-5a254fd4e073360f, EV-d15f6ab79e49570f`]
  - `TL008` (`1742938057.2978`, `network`, `communication`): `172.16.1.2:58792->172.16.3.4:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-3756177baef54a3c, EV-dc4b2cb285589b16`]
  - `TL018` (`1742938058.8582`, `electrical`, `electrical_change`): `bus.0:voltage_angle` (`not_on_confirmed_storyline_spine`) [`EV-161635a4e28e3b61, EV-8d54d5eeaa1a3e30`]
  - `TL003` (`1742938060.6066`, `network`, `communication`): `172.16.3.12:2404->172.16.1.2:55948/TCP` (`not_on_confirmed_storyline_spine`) [`EV-dd263a5fbd2e13a9, EV-c242b1ae80dc66ec`]
  - `TL004` (`1742938060.6106`, `network`, `communication`): `172.16.1.2:55948->172.16.3.12:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-19e99fa03a522f77, EV-0d86ce4e047ac54f`]
  - `TL021` (`1742938060.8582`, `electrical`, `electrical_change`): `line.13:current_from` (`not_on_confirmed_storyline_spine`) [`EV-ce6807faf2e786d1, EV-147a8ea0f91e9910`]
  - `TL022` (`1742938060.8582`, `electrical`, `electrical_change`): `line.11:reactive_power_to` (`not_on_confirmed_storyline_spine`) [`EV-3c704e9a40c15f04, EV-15ec184ccd75a20f`]
