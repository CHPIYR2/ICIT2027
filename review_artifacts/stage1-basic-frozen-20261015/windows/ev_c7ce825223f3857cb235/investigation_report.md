# Evidence-Grounded Incident Reconstruction Report

- **Report Status**: `quality_consistent`
- **Quality & Behavioral Consistency (`quality_consistency.json`)**: `consistent`
- **Evidence Lineage Audit (`lineage_consistency.json`)**: `consistent`

- **Incident Window**: `1742955920.189304` to `1742955950.2732954`
- **Reconstructed IEC-104 Transactions**: `1`
- **Reconstructed Event Storylines**: `6`
- **Verified Same-Device Transitions (Consistency Gate Passed)**: `0`
- **Unverified Protocol State Reports (Value Undecoded or No Pre-Baseline)**: `1`
- **LLM Claim Verifier Output (Separate from Graph Gate)**: `0` verified, `0` withheld

## 1. Incident Sequence & Protocol Transactions
- **TX001** (`1742955920.2077`–`1742955920.4664`): `type_47` on `trafo.0:tap_position` (`CA/IOA=104.10010`, value=`None`) over `172.16.1.2:46184 -> 172.16.2.5:2404` at vantages `['n302', 'n303']`. **Command Acceptance (`COT=7` P/N)**: `accepted_by_rtu`; **Device State Verification**: `state_report_observed_value_unknown` (reason=`command_value_unknown,missing_pre_command_baseline,post_state_or_measurement_value_unknown,pre_test_bit_unknown`); **Completeness**: `partial_state_report_observed_transition_unverified`; **Missing/Unverified Stages**: `['activation_termination_cot10', 'unverified_state_transition:command_value_unknown,missing_pre_command_baseline,post_state_or_measurement_value_unknown,pre_test_bit_unknown']` (`EV-34d5c3792cecd99b, EV-a6cdc9c6b564ba23, EV-2c15077d29f240f6, EV-4d29b7d559c8b765`).
  - Inference gate (`state_report`): passed=`False`; pre IV=`None` other flags=`None`; post IV=`None` other flags=`None`; COT test bits=`{'command': False, 'confirmation': False, 'pre': None, 'post': False}`; failed=`['command_value_unknown', 'missing_pre_command_baseline', 'post_state_or_measurement_value_unknown', 'pre_test_bit_unknown']`.

## 2A. Behavioral Incident Reconstruction (No Control Command)
- `0` event anchors found; a control transaction is present, so anchors are listed in `event_anchors.json` and do not root storylines.

## 2B. Incident Scenario Synthesis (Four-Layer Epistemic Integration)
- **Scenario Status**: `synthesized_consistent`
- **Layer 1 Partition**: `0` supported multi-node chains, `0` verified single-anchor chains, `0` sequential same-entity observations (gate failed), `0` quarantined unverified observations (`0` unverified COT=3 precursor reports).
- **Layer 2 Bundles & Bridges**: `0` source bundles (each counted as `1` container), `0` cross-RTU verified element bridges, `0` same-RTU supported relations (not cross-RTU support), `0` multi-bundle bridged components.
- **Layer 3 Candidate Phases**: `1` candidate scenario phases (all cross-device links kept `unresolved`).
- **Layer 4 Source Dependency Ledger**: `0` IEC-104 ASDU, `0` TCP link, `0` ARP, `3` composite containers across `1` RTU(s) (`['172.16.2.5']`), `0` co-reported same-ASDU points collapsed, mirror vantages `['n302', 'n303']`, `0` IPAL rows excluded (`weight=0`).

### 2B.2 Layer 3 — Candidate Scenario Phases (Cross-Device Links Unresolved)
- **PHS-001** (`+0.018s`..`+0.277s`, profile=`protocol_command_transactions`): bundles=`[]`, verified_bridges=`[]`, sequential_same_device=`[]`, unverified_precursors=`[]`, RTUs=`['172.16.2.5']`, ARP=`[]`, unresolved_candidates=`16`.

### 2B.3 Layer 4 — Evidence-Anchored Competing Explanations & Missing Evidence
- **EXP-001** (`command_induced_device_transition_hypothesis`, status=`unresolved_competing_hypothesis`, causal_status=`not_established`): Observed IEC-104 control activation(s) ['TX001'] on the SCADA network, with 0 transaction(s) passing pre/post setpoint/state consistency checks. Consistent with RTU execution of the received IEC-104 command(s).
  - **Anchored by**: `{'transaction_ids': ['TX001'], 'verified_transition_transaction_ids': [], 'evidence_ids': ['EV-34d5c3792cecd99b', 'EV-a6cdc9c6b564ba23', 'EV-2c15077d29f240f6', 'EV-4d29b7d559c8b765']}`
  - **Unverified/candidate links required**: `['TX001']`
  - **Alternative comparison**: Competes with coincidence or unverified physical actuation where protocol confirmation (COT=7) or telemetry shifts occur without independent physical sensor verification.
  - **Missing disambiguating evidence**: `['Independent out-of-band physical process sensor or PMU log not derived from IEC-104', 'Master station operator/application audit log identifying the initiating process', 'Pre-command IEC-104 state baseline (COT=20/COT=1) for switch transactions']`

## 2. Key Findings & Reconstructed Storylines (Contiguous Directed Spines)
### SL001 — Anchor `trafo.0:tap_position` (tx=`TX001`, status=`partial_state_report_observed_transition_unverified`, contiguous_path=`True`, logical_nodes=`3`, independent_sources=`3`, independent_edges=`2`, vantage_captures=`6`)
- Step 1 [R0001 | N-N | iec104_command_confirmation | level=observed_fact | gate=direct_record_observation | independent_evidence]: EF001 (trafo.0:tap_position @ 1742955920.2077) -> EF002 (trafo.0:tap_position @ 1742955920.2561) [src_ev=EV-34d5c3792cecd99b, EV-a6cdc9c6b564ba23; dst_ev=EV-eb5f02977c26b390, EV-6e8ef785dde61e18]
- Step 2 [R0002 | N-N | subsequent_same_device_state_report | level=observed_fact | gate=direct_record_observation | independent_evidence]: EF002 (trafo.0:tap_position @ 1742955920.2561) -> EF003 (trafo.0:tap_position @ 1742955920.4564) [src_ev=EV-eb5f02977c26b390, EV-6e8ef785dde61e18; dst_ev=EV-6faf64cb4bc98e72, EV-6772950d1af2b361]
- **Evidence Gaps**: `['activation_termination_cot10', 'unverified_state_transition:command_value_unknown,missing_pre_command_baseline,post_state_or_measurement_value_unknown,pre_test_bit_unknown']`
### SL002 — Anchor `line.11:current_to` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`12`)
- Step 1 [R0012 | N-N | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL022 (line.11:current_to @ 1742955922.0135) -> TL011 (line.11:current_from @ 1742955926.3493) [src_ev=EV-db46f901170dcec0, EV-47957cfa62766216; dst_ev=EV-9b8abf7204b9cc3b, EV-3ace256a8175c7a1]
- Time-aligned IPAL row [R0006 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL016 (line.11:current_to=0.30244946479797363 @ 1742955922.8582) aligned with TL022; not an independent source
- Time-aligned IPAL row [R0008 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL014 (line.11:current_from=0.34152287244796753 @ 1742955926.8582) aligned with TL011; not an independent source
### SL003 — Anchor `line.11:current_to` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`6`)
- Step 1 [R0013 | P-P | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL016 (line.11:current_to @ 1742955922.8582) -> TL014 (line.11:current_from @ 1742955926.8582) [src_ev=EV-deba608337bc9680, EV-0a438de14b124ef2; dst_ev=EV-b0efea0d57776175, EV-3fd67009dd020a25]
### SL004 — Anchor `line.0:voltage_to` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`24`)
- Step 1 [R0014 | N-N | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL023 (line.0:voltage_to @ 1742955928.7317) -> TL012 (line.0:voltage_from @ 1742955929.829) [src_ev=EV-1aa04b5817936a85, EV-bf7facee3e4c6ea2; dst_ev=EV-d36619d8c07f1332, EV-222ddd26dc702b6f]
### SL005 — Anchor `line.3:active_power_to` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`6`)
- Step 1 [R0010 | P-P | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL019 (line.3:active_power_to @ 1742955921.8582) -> TL018 (line.3:active_power_from @ 1742955926.8582) [src_ev=EV-98116503fd748d1c, EV-c33e4a7c1acaa0a8; dst_ev=EV-dea6e29227490369, EV-0a7a14d9dafe1504]
### SL006 — Anchor `line.13:current_from` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`6`)
- Step 1 [R0011 | P-P | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL021 (line.13:current_from @ 1742955921.8582) -> TL015 (line.13:current_to @ 1742955926.8582) [src_ev=EV-a78b7d3c04f223ee, EV-b1601ecbd64c5815; dst_ev=EV-318266d551866683, EV-9a3ff63f96d4c152]

## 3. Observed Network & Electrical Impact (Epistemically Stratified)
### 3.1 Verified Same-Device Measurement/State Transitions (Consistency Gate Passed)
- No post-command device transition passed all pre/post and target consistency checks.

### 3.2 Protocol State Reports Observed Without Verified Transition (Value Undecoded or No Pre-Baseline)
- [TX001 | state_report_observed_value_unknown] Observed subsequent M_SP_NA_1 (COT=3) state report message on trafo.0:tap_position (CA/IOA=104.10020, value_present=False, value=None) at 1742955920.4564 [ev=EV-6faf64cb4bc98e72, EV-6772950d1af2b361]; nearby IPAL state table row has value=255.0 (network-derived). Reason transition is NOT confirmed: command_value_unknown,missing_pre_command_baseline,post_state_or_measurement_value_unknown,pre_test_bit_unknown.

### 3.3 Candidate Cross-Entity Co-occurring Changes (Unresolved Hypotheses, Not Causal Proof)
- [SL001 / R0015 | cross_entity_temporal_cooccurrence] (level=temporal_cooccurrence, status=unresolved, gate=unresolved_cooccurrence, causal_status=not_established): bus.0:voltage_angle (TL017) at 1742955920.8582 after EF001 (0 <= dt (0.6505s) <= 10.0s) [src_ev=EV-34d5c3792cecd99b, EV-a6cdc9c6b564ba23; dst_ev=EV-18ff660ab47ea6ea, EV-496c97674fdc3ea9].
- [SL001 / R0016 | cross_entity_temporal_cooccurrence] (level=temporal_cooccurrence, status=unresolved, gate=unresolved_cooccurrence, causal_status=not_established): line.3:active_power_to (TL019) at 1742955921.8582 after EF001 (0 <= dt (1.6505s) <= 10.0s) [src_ev=EV-34d5c3792cecd99b, EV-a6cdc9c6b564ba23; dst_ev=EV-98116503fd748d1c, EV-c33e4a7c1acaa0a8].
- [SL001 / R0017 | cross_entity_temporal_cooccurrence] (level=temporal_cooccurrence, status=unresolved, gate=unresolved_cooccurrence, causal_status=not_established): line.13:current_from (TL021) at 1742955921.8582 after EF001 (0 <= dt (1.6505s) <= 10.0s) [src_ev=EV-34d5c3792cecd99b, EV-a6cdc9c6b564ba23; dst_ev=EV-a78b7d3c04f223ee, EV-b1601ecbd64c5815].
- [SL001 / R0018 | cross_entity_temporal_cooccurrence] (level=temporal_cooccurrence, status=unresolved, gate=unresolved_cooccurrence, causal_status=not_established): line.11:current_to (TL022) at 1742955922.0135 after EF001 (0 <= dt (1.8058s) <= 10.0s) [src_ev=EV-34d5c3792cecd99b, EV-a6cdc9c6b564ba23; dst_ev=EV-db46f901170dcec0, EV-47957cfa62766216].

## 4. Alternative Explanations & Competing Hypotheses
- **[SL001 | competing_cross_entity_cooccurrences | status=`unresolved`]**: Multiple distinct grid measurements (bus.0:voltage_angle, line.3:active_power_to, line.13:current_from, line.11:current_to) changed within the time horizon after trafo.0:tap_position. Without an independent physical topology/power-flow model in the loop, these remain competing unresolved temporal co-occurrences rather than confirmed causal effects.
- **[SL001 | state_report_without_verified_before_after_values | status=`unresolved`]**: A subsequent M_SP_NA_1 (COT=3) state report was observed for trafo.0, but state_report_observed_value_unknown (command_value_unknown,missing_pre_command_baseline,post_state_or_measurement_value_unknown,pre_test_bit_unknown). Therefore a state transition cannot be confirmed from protocol values alone.

## 5. Unresolved Questions, Evidence Gaps & Unattached Observations
- **Evidence Gap**: `{"scope": "TX001", "entity": "trafo.0:tap_position", "missing_stages": ["activation_termination_cot10", "unverified_state_transition:command_value_unknown,missing_pre_command_baseline,post_state_or_measurement_value_unknown,pre_test_bit_unknown"]}`
- **Unattached Observations (`10` nodes not on a storyline spine)**:
  - `TL001` (`1742955920.2077`, `network`, `communication`): `172.16.1.2:46184->172.16.2.5:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-2c15077d29f240f6, EV-8ae373944f614e7c`]
  - `TL003` (`1742955920.2217`, `network`, `communication`): `172.16.2.5:2404->172.16.1.2:46184/TCP` (`not_on_confirmed_storyline_spine`) [`EV-4c4cb0326fffffd7, EV-d37f5a2feea78094`]
  - `TL005` (`1742955920.3867`, `network`, `communication`): `172.16.3.6:2404->172.16.1.2:41978/TCP` (`not_on_confirmed_storyline_spine`) [`EV-b7750d75a163fb5f, EV-9407060436e17cf4`]
  - `TL007` (`1742955920.4088`, `network`, `communication`): `172.16.1.2:41978->172.16.3.6:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-8027a2541a22e517, EV-eb1799dbfa1e274b`]
  - `EF004` (`1742955920.8582`, `electrical`, `electrical_state_update`): `trafo.0:tap_position` (`isolated_no_graph_edge`) [`EV-83b0f96710712b82`]
  - `TL017` (`1742955920.8582`, `electrical`, `electrical_change`): `bus.0:voltage_angle` (`not_on_confirmed_storyline_spine`) [`EV-18ff660ab47ea6ea, EV-496c97674fdc3ea9`]
  - `TL013` (`1742955926.1647`, `network`, `electrical_report`): `line.13:current_to` (`not_on_confirmed_storyline_spine`) [`EV-9f1cbd40981d88b9, EV-15bff1533564b293`]
  - `TL010` (`1742955926.4001`, `network`, `electrical_report`): `line.7:reactive_power_to` (`not_on_confirmed_storyline_spine`) [`EV-5f26d778da177ff3, EV-a84aecd4cbf96222`]
  - `TL020` (`1742955926.8582`, `electrical`, `electrical_change`): `line.10:current_to` (`not_on_confirmed_storyline_spine`) [`EV-1ce0e955a5a93340, EV-86a653e336d196fe`]
  - `TL024` (`1742955928.7317`, `network`, `electrical_report`): `line.1:voltage_from` (`not_on_confirmed_storyline_spine`) [`EV-efd42bb1e6d5e286, EV-255bbfd4fcc1fb5d`]
