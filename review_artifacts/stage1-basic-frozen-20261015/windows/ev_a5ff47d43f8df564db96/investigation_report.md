# Evidence-Grounded Incident Reconstruction Report

- **Report Status**: `quality_consistent`
- **Quality & Behavioral Consistency (`quality_consistency.json`)**: `consistent`
- **Evidence Lineage Audit (`lineage_consistency.json`)**: `consistent`

- **Incident Window**: `1742943841.2307465` to `1742943871.2929306`
- **Reconstructed IEC-104 Transactions**: `1`
- **Reconstructed Event Storylines**: `6`
- **Verified Same-Device Transitions (Consistency Gate Passed)**: `0`
- **Unverified Protocol State Reports (Value Undecoded or No Pre-Baseline)**: `1`
- **LLM Claim Verifier Output (Separate from Graph Gate)**: `0` verified, `0` withheld

## 1. Incident Sequence & Protocol Transactions
- **TX001** (`1742943841.2955`–`1742943841.6759`): `C_SC_NA_1 (Single command)` on `sgen.7:connected` (`CA/IOA=115.10020`, value=`0.0`) over `172.16.1.2:56094 -> 172.16.3.10:2404` at vantages `['n302', 'n318']`. **Command Acceptance (`COT=7` P/N)**: `accepted_by_rtu`; **Device State Verification**: `state_report_observed_no_pre_baseline` (reason=`missing_pre_command_baseline,pre_test_bit_unknown`); **Completeness**: `partial_state_report_observed_transition_unverified`; **Missing/Unverified Stages**: `['activation_termination_cot10', 'unverified_state_transition:missing_pre_command_baseline,pre_test_bit_unknown']` (`EV-258dbb454e4fcfed, EV-12acb029460190b1, EV-e65f39c54bb07b36, EV-dad5495b0ba6d0c1`).
  - Inference gate (`state_report`): passed=`False`; pre IV=`None` other flags=`None`; post IV=`False` other flags=`[]`; COT test bits=`{'command': False, 'confirmation': False, 'pre': None, 'post': False}`; failed=`['missing_pre_command_baseline', 'pre_test_bit_unknown']`.

## 2A. Behavioral Incident Reconstruction (No Control Command)
- `2` event anchors found; a control transaction is present, so anchors are listed in `event_anchors.json` and do not root storylines.

## 2B. Incident Scenario Synthesis (Four-Layer Epistemic Integration)
- **Scenario Status**: `synthesized_consistent`
- **Layer 1 Partition**: `0` supported multi-node chains, `0` verified single-anchor chains, `0` sequential same-entity observations (gate failed), `0` quarantined unverified observations (`0` unverified COT=3 precursor reports).
- **Layer 2 Bundles & Bridges**: `0` source bundles (each counted as `1` container), `0` cross-RTU verified element bridges, `0` same-RTU supported relations (not cross-RTU support), `0` multi-bundle bridged components.
- **Layer 3 Candidate Phases**: `1` candidate scenario phases (all cross-device links kept `unresolved`).
- **Layer 4 Source Dependency Ledger**: `0` IEC-104 ASDU, `0` TCP link, `0` ARP, `3` composite containers across `1` RTU(s) (`['172.16.3.10']`), `0` co-reported same-ASDU points collapsed, mirror vantages `['n302', 'n318']`, `3` IPAL rows excluded (`weight=0`).

### 2B.2 Layer 3 — Candidate Scenario Phases (Cross-Device Links Unresolved)
- **PHS-001** (`+0.065s`..`+0.445s`, profile=`protocol_command_transactions`): bundles=`[]`, verified_bridges=`[]`, sequential_same_device=`[]`, unverified_precursors=`[]`, RTUs=`['172.16.3.10']`, ARP=`[]`, unresolved_candidates=`16`.

### 2B.3 Layer 4 — Evidence-Anchored Competing Explanations & Missing Evidence
- **EXP-001** (`command_induced_device_transition_hypothesis`, status=`unresolved_competing_hypothesis`, causal_status=`not_established`): Observed IEC-104 control activation(s) ['TX001'] on the SCADA network, with 0 transaction(s) passing pre/post setpoint/state consistency checks. Consistent with RTU execution of the received IEC-104 command(s).
  - **Anchored by**: `{'transaction_ids': ['TX001'], 'verified_transition_transaction_ids': [], 'evidence_ids': ['EV-258dbb454e4fcfed', 'EV-12acb029460190b1', 'EV-e65f39c54bb07b36', 'EV-dad5495b0ba6d0c1']}`
  - **Unverified/candidate links required**: `['TX001']`
  - **Alternative comparison**: Competes with coincidence or unverified physical actuation where protocol confirmation (COT=7) or telemetry shifts occur without independent physical sensor verification.
  - **Missing disambiguating evidence**: `['Independent out-of-band physical process sensor or PMU log not derived from IEC-104', 'Master station operator/application audit log identifying the initiating process', 'Pre-command IEC-104 state baseline (COT=20/COT=1) for switch transactions']`

## 2. Key Findings & Reconstructed Storylines (Contiguous Directed Spines)
### SL001 — Anchor `sgen.7:connected` (tx=`TX001`, status=`partial_state_report_observed_transition_unverified`, contiguous_path=`True`, logical_nodes=`3`, independent_sources=`3`, independent_edges=`2`, vantage_captures=`6`)
- Step 1 [R0001 | N-N | iec104_command_confirmation | level=observed_fact | gate=direct_record_observation | independent_evidence]: EF001 (sgen.7:connected @ 1742943841.2955) -> EF002 (sgen.7:connected @ 1742943841.3575) [src_ev=EV-258dbb454e4fcfed, EV-12acb029460190b1; dst_ev=EV-eead89a58fb4229b, EV-274d78cbcbbdad88]
- Step 2 [R0002 | N-N | subsequent_same_device_state_report | level=observed_fact | gate=direct_record_observation | independent_evidence]: EF002 (sgen.7:connected @ 1742943841.3575) -> EF003 (sgen.7:is_connected @ 1742943841.6579) [src_ev=EV-eead89a58fb4229b, EV-274d78cbcbbdad88; dst_ev=EV-9fae0756b26cb604, EV-c86f3714aa8f2e40]
- Time-aligned IPAL row [R0007 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: EF004 (sgen.7:connected=0.0 @ 1742943841.8582) aligned with EF001; not an independent source
- Time-aligned IPAL row [R0009 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: EF004 (sgen.7:connected=0.0 @ 1742943841.8582) aligned with EF002; not an independent source
- **Evidence Gaps**: `['activation_termination_cot10', 'unverified_state_transition:missing_pre_command_baseline,pre_test_bit_unknown']`
### SL002 — Anchor `line.4:current_to` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`6`)
- Step 1 [R0017 | P-P | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL014 (line.4:current_to @ 1742943841.8582) -> TL021 (line.4:current_from @ 1742943843.8582) [src_ev=EV-6d46d8900ee02687, EV-c04bea185c008200; dst_ev=EV-4a35d0bd46a3f222, EV-92bb5620cde34126]
### SL003 — Anchor `line.13:current_from` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`6`)
- Step 1 [R0019 | P-P | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL016 (line.13:current_from @ 1742943843.8582) -> TL015 (line.13:current_to @ 1742943848.8582) [src_ev=EV-78ac8c198d28dff8, EV-4aa76591a0f981ba; dst_ev=EV-32619cc5edba1b2a, EV-968493bfbd7f4fd3]
### SL004 — Anchor `line.13:current_from` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`18`)
- Step 1 [R0018 | N-N | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL012 (line.13:current_from @ 1742943843.7752) -> TL011 (line.13:current_to @ 1742943848.5763) [src_ev=EV-4b8165bdb5e2f802, EV-313380a6a89f01c7; dst_ev=EV-69277ea8cf2c4aeb, EV-ba3c3bda76c53b7f]
- Time-aligned IPAL row [R0012 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL016 (line.13:current_from=0.13568826019763947 @ 1742943843.8582) aligned with TL012; not an independent source
- Time-aligned IPAL row [R0014 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL015 (line.13:current_to=0.003526140935719013 @ 1742943848.8582) aligned with TL011; not an independent source
### SL005 — Anchor `line.11:current_to` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`12`)
- Step 1 [R0020 | N-N | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL023 (line.11:current_to @ 1742943844.3247) -> TL013 (line.11:current_from @ 1742943848.6818) [src_ev=EV-89c00c29bed9b1ea, EV-54e2d8b29efc9440; dst_ev=EV-be09d46fde997e07, EV-5f4e96960cb8bd80]
- Time-aligned IPAL row [R0013 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL019 (line.11:current_to=-0.15823721885681152 @ 1742943844.8582) aligned with TL023; not an independent source
- Time-aligned IPAL row [R0015 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL017 (line.11:current_from=-0.3018469512462616 @ 1742943848.8582) aligned with TL013; not an independent source
### SL006 — Anchor `line.11:current_to` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`6`)
- Step 1 [R0021 | P-P | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL019 (line.11:current_to @ 1742943844.8582) -> TL017 (line.11:current_from @ 1742943848.8582) [src_ev=EV-33a76fed60dc05b6, EV-e409593e5b575b08; dst_ev=EV-66fa1c85935adacc, EV-8254aa19869a3e30]

## 3. Observed Network & Electrical Impact (Epistemically Stratified)
### 3.1 Verified Same-Device Measurement/State Transitions (Consistency Gate Passed)
- No post-command device transition passed all pre/post and target consistency checks.

### 3.2 Protocol State Reports Observed Without Verified Transition (Value Undecoded or No Pre-Baseline)
- [TX001 | state_report_observed_no_pre_baseline] Observed subsequent M_SP_NA_1 (COT=3) state report message on sgen.7:is_connected (CA/IOA=115.10060, value_present=True, value=0.0) at 1742943841.6579 [ev=EV-9fae0756b26cb604, EV-c86f3714aa8f2e40]; nearby IPAL state table row has value=0.0 (network-derived). Reason transition is NOT confirmed: missing_pre_command_baseline,pre_test_bit_unknown.

### 3.3 Candidate Cross-Entity Co-occurring Changes (Unresolved Hypotheses, Not Causal Proof)
- [SL001 / R0022 | cross_entity_temporal_cooccurrence] (level=temporal_cooccurrence, status=unresolved, gate=unresolved_cooccurrence, causal_status=not_established): line.4:current_to (TL010) at 1742943841.3308 after EF001 (0 <= dt (0.0353s) <= 10.0s) [src_ev=EV-258dbb454e4fcfed, EV-12acb029460190b1; dst_ev=EV-b9790ecd37b7aa0f, EV-ca2f417108ec175e].
- [SL001 / R0023 | cross_entity_temporal_cooccurrence] (level=temporal_cooccurrence, status=unresolved, gate=unresolved_cooccurrence, causal_status=not_established): line.4:current_to (TL014) at 1742943841.8582 after EF001 (0 <= dt (0.5627s) <= 10.0s) [src_ev=EV-258dbb454e4fcfed, EV-12acb029460190b1; dst_ev=EV-6d46d8900ee02687, EV-c04bea185c008200].
- [SL001 / R0024 | cross_entity_temporal_cooccurrence] (level=temporal_cooccurrence, status=unresolved, gate=unresolved_cooccurrence, causal_status=not_established): bus.0:voltage_angle (TL022) at 1742943842.3165 after EF001 (0 <= dt (1.0211s) <= 10.0s) [src_ev=EV-258dbb454e4fcfed, EV-12acb029460190b1; dst_ev=EV-25aa900e5aea533a, EV-83cba9443cff36a1].
- [SL001 / R0025 | cross_entity_temporal_cooccurrence] (level=temporal_cooccurrence, status=unresolved, gate=unresolved_cooccurrence, causal_status=not_established): bus.0:voltage_angle (TL018) at 1742943842.8582 after EF001 (0 <= dt (1.5627s) <= 10.0s) [src_ev=EV-258dbb454e4fcfed, EV-12acb029460190b1; dst_ev=EV-60f8e394484e858b, EV-377e89f235c5ac86].

## 4. Alternative Explanations & Competing Hypotheses
- **[SL001 | competing_cross_entity_cooccurrences | status=`unresolved`]**: Multiple distinct grid measurements (line.4:current_to, line.4:current_to, bus.0:voltage_angle, bus.0:voltage_angle) changed within the time horizon after sgen.7:connected. Without an independent physical topology/power-flow model in the loop, these remain competing unresolved temporal co-occurrences rather than confirmed causal effects.
- **[SL001 | state_report_without_verified_before_after_values | status=`unresolved`]**: A subsequent M_SP_NA_1 (COT=3) state report was observed for sgen.7, but state_report_observed_no_pre_baseline (missing_pre_command_baseline,pre_test_bit_unknown). Therefore a state transition cannot be confirmed from protocol values alone.

## 5. Unresolved Questions, Evidence Gaps & Unattached Observations
- **Evidence Gap**: `{"scope": "TX001", "entity": "sgen.7:connected", "missing_stages": ["activation_termination_cot10", "unverified_state_transition:missing_pre_command_baseline,pre_test_bit_unknown"]}`
- **Unattached Observations (`12` nodes not on a storyline spine)**:
  - `TL001` (`1742943841.2955`, `network`, `communication`): `172.16.1.2:56094->172.16.3.10:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-e65f39c54bb07b36, EV-c53d287a37ded733`]
  - `TL003` (`1742943841.3216`, `network`, `communication`): `172.16.3.10:2404->172.16.1.2:56094/TCP` (`not_on_confirmed_storyline_spine`) [`EV-9efc2d2420ca03b2, EV-186745cc85548ff0`]
  - `TL007` (`1742943841.3308`, `network`, `communication`): `172.16.3.22:2404->172.16.1.2:34946/TCP` (`not_on_confirmed_storyline_spine`) [`EV-88b3730ca7071ae4, EV-40af9aa7b4777289`]
  - `TL010` (`1742943841.3308`, `network`, `electrical_report`): `line.4:current_to` (`not_on_confirmed_storyline_spine`) [`EV-b9790ecd37b7aa0f, EV-ca2f417108ec175e`]
  - `TL008` (`1742943841.3348`, `network`, `communication`): `172.16.1.2:34946->172.16.3.22:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-db57dfffa75a8a0f, EV-6e047ceed6104c04`]
  - `TL024` (`1742943841.6589`, `network`, `electrical_report`): `sgen.7:active_power` (`not_on_confirmed_storyline_spine`) [`EV-6d35d6efd10c8d51, EV-36008e9cc8885612`]
  - `EF004` (`1742943841.8582`, `electrical`, `electrical_state_update`): `sgen.7:connected` (`not_on_confirmed_storyline_spine`) [`EV-5c503b86c82d99d3`]
  - `TL020` (`1742943841.8582`, `electrical`, `electrical_change`): `sgen.7:active_power` (`not_on_confirmed_storyline_spine`) [`EV-c1d2b2e9183ca021`]
  - `TL022` (`1742943842.3165`, `network`, `electrical_report`): `bus.0:voltage_angle` (`not_on_confirmed_storyline_spine`) [`EV-25aa900e5aea533a, EV-83cba9443cff36a1`]
  - `TL018` (`1742943842.8582`, `electrical`, `electrical_change`): `bus.0:voltage_angle` (`not_on_confirmed_storyline_spine`) [`EV-60f8e394484e858b, EV-377e89f235c5ac86`]
