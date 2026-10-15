# Evidence-Grounded Incident Reconstruction Report

- **Report Status**: `quality_consistent`
- **Quality & Behavioral Consistency (`quality_consistency.json`)**: `consistent`
- **Evidence Lineage Audit (`lineage_consistency.json`)**: `consistent`

- **Incident Window**: `1742958340.1891963` to `1742958370.2365925`
- **Reconstructed IEC-104 Transactions**: `1`
- **Reconstructed Event Storylines**: `6`
- **Verified Same-Device Transitions (Consistency Gate Passed)**: `0`
- **Unverified Protocol State Reports (Value Undecoded or No Pre-Baseline)**: `1`
- **LLM Claim Verifier Output (Separate from Graph Gate)**: `0` verified, `0` withheld

## 1. Incident Sequence & Protocol Transactions
- **TX001** (`1742958340.2070`–`1742958340.4328`): `type_47` on `trafo.0:tap_position` (`CA/IOA=104.10010`, value=`None`) over `172.16.1.2:46184 -> 172.16.2.5:2404` at vantages `['n302', 'n303']`. **Command Acceptance (`COT=7` P/N)**: `accepted_by_rtu`; **Device State Verification**: `state_report_observed_value_unknown` (reason=`command_value_unknown,missing_pre_command_baseline,post_state_or_measurement_value_unknown,pre_test_bit_unknown`); **Completeness**: `partial_state_report_observed_transition_unverified`; **Missing/Unverified Stages**: `['activation_termination_cot10', 'unverified_state_transition:command_value_unknown,missing_pre_command_baseline,post_state_or_measurement_value_unknown,pre_test_bit_unknown']` (`EV-76d8166fbc059abd, EV-0e17d643512ce648, EV-e1f31a89f722f504, EV-d952a87e9d0d49d2`).
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
- **PHS-001** (`+0.018s`..`+0.244s`, profile=`protocol_command_transactions`): bundles=`[]`, verified_bridges=`[]`, sequential_same_device=`[]`, unverified_precursors=`[]`, RTUs=`['172.16.2.5']`, ARP=`[]`, unresolved_candidates=`16`.

### 2B.3 Layer 4 — Evidence-Anchored Competing Explanations & Missing Evidence
- **EXP-001** (`command_induced_device_transition_hypothesis`, status=`unresolved_competing_hypothesis`, causal_status=`not_established`): Observed IEC-104 control activation(s) ['TX001'] on the SCADA network, with 0 transaction(s) passing pre/post setpoint/state consistency checks. Consistent with RTU execution of the received IEC-104 command(s).
  - **Anchored by**: `{'transaction_ids': ['TX001'], 'verified_transition_transaction_ids': [], 'evidence_ids': ['EV-76d8166fbc059abd', 'EV-0e17d643512ce648', 'EV-e1f31a89f722f504', 'EV-d952a87e9d0d49d2']}`
  - **Unverified/candidate links required**: `['TX001']`
  - **Alternative comparison**: Competes with coincidence or unverified physical actuation where protocol confirmation (COT=7) or telemetry shifts occur without independent physical sensor verification.
  - **Missing disambiguating evidence**: `['Independent out-of-band physical process sensor or PMU log not derived from IEC-104', 'Master station operator/application audit log identifying the initiating process', 'Pre-command IEC-104 state baseline (COT=20/COT=1) for switch transactions']`

## 2. Key Findings & Reconstructed Storylines (Contiguous Directed Spines)
### SL001 — Anchor `trafo.0:tap_position` (tx=`TX001`, status=`partial_state_report_observed_transition_unverified`, contiguous_path=`True`, logical_nodes=`3`, independent_sources=`3`, independent_edges=`2`, vantage_captures=`6`)
- Step 1 [R0001 | N-N | iec104_command_confirmation | level=observed_fact | gate=direct_record_observation | independent_evidence]: EF001 (trafo.0:tap_position @ 1742958340.207) -> EF002 (trafo.0:tap_position @ 1742958340.2226) [src_ev=EV-76d8166fbc059abd, EV-0e17d643512ce648; dst_ev=EV-0d68ed16c17bbab4, EV-b70227d4866767d4]
- Step 2 [R0002 | N-N | subsequent_same_device_state_report | level=observed_fact | gate=direct_record_observation | independent_evidence]: EF002 (trafo.0:tap_position @ 1742958340.2226) -> EF003 (trafo.0:tap_position @ 1742958340.4228) [src_ev=EV-0d68ed16c17bbab4, EV-b70227d4866767d4; dst_ev=EV-0dabd234d446cc51, EV-a636912416969bf6]
- **Evidence Gaps**: `['activation_termination_cot10', 'unverified_state_transition:command_value_unknown,missing_pre_command_baseline,post_state_or_measurement_value_unknown,pre_test_bit_unknown']`
### SL002 — Anchor `line.13:current_to` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`0`, vantage_captures=`12`)
- Step 1 [R0013 | N-N | same_iec104_frame | level=observed_fact | gate=direct_record_observation | shared_source_not_double_counted]: TL010 (line.13:current_to @ 1742958347.6803) -> TL013 (line.2:active_power_to @ 1742958347.6803) [src_ev=EV-d30ae42b97f5b381, EV-dcddba8a2ebe4c9d; dst_ev=EV-5d01e9ea8fea3e76, EV-ab272c67121d0be2]
- Time-aligned IPAL row [R0010 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL014 (line.13:current_to=0.05784008279442787 @ 1742958347.8582) aligned with TL010; not an independent source
- Time-aligned IPAL row [R0011 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL017 (line.2:active_power_to=-608.5992431640625 @ 1742958347.8582) aligned with TL013; not an independent source
### SL003 — Anchor `line.11:current_to` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`12`)
- Step 1 [R0015 | N-N | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL011 (line.11:current_to @ 1742958343.5297) -> TL022 (line.11:current_from @ 1742958347.8376) [src_ev=EV-78bcca136feff552, EV-8aab0a995082e63b; dst_ev=EV-a65254bf2bf1c4fe, EV-9ba99fe145391aab]
- Time-aligned IPAL row [R0008 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL015 (line.11:current_to=-0.18463480472564697 @ 1742958343.8582) aligned with TL011; not an independent source
- Time-aligned IPAL row [R0012 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL018 (line.11:current_from=0.3698450028896332 @ 1742958347.8582) aligned with TL022; not an independent source
### SL004 — Anchor `line.11:current_to` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`6`)
- Step 1 [R0016 | P-P | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL015 (line.11:current_to @ 1742958343.8582) -> TL018 (line.11:current_from @ 1742958347.8582) [src_ev=EV-dde8a0c028cd73de, EV-2d4a991e4c8a2a30; dst_ev=EV-fcf63d57a39bdc93, EV-edc8377c7aeeb2e4]
### SL005 — Anchor `line.2:active_power_from` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`6`)
- Step 1 [R0018 | P-P | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL016 (line.2:active_power_from @ 1742958344.8582) -> TL017 (line.2:active_power_to @ 1742958347.8582) [src_ev=EV-9082d27f1d2f15dc, EV-fdc3cd48099c02d2; dst_ev=EV-dfd39e128444df2f, EV-491d6edef3ae05c3]
### SL006 — Anchor `line.2:active_power_from` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`12`)
- Step 1 [R0017 | N-N | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL012 (line.2:active_power_from @ 1742958343.976) -> TL013 (line.2:active_power_to @ 1742958347.6803) [src_ev=EV-5688600c195507de, EV-0d60a2faf6ab3f6b; dst_ev=EV-5d01e9ea8fea3e76, EV-ab272c67121d0be2]
- Time-aligned IPAL row [R0009 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL016 (line.2:active_power_from=3805.30615234375 @ 1742958344.8582) aligned with TL012; not an independent source
- Time-aligned IPAL row [R0011 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL017 (line.2:active_power_to=-608.5992431640625 @ 1742958347.8582) aligned with TL013; not an independent source

## 3. Observed Network & Electrical Impact (Epistemically Stratified)
### 3.1 Verified Same-Device Measurement/State Transitions (Consistency Gate Passed)
- No post-command device transition passed all pre/post and target consistency checks.

### 3.2 Protocol State Reports Observed Without Verified Transition (Value Undecoded or No Pre-Baseline)
- [TX001 | state_report_observed_value_unknown] Observed subsequent M_SP_NA_1 (COT=3) state report message on trafo.0:tap_position (CA/IOA=104.10020, value_present=False, value=None) at 1742958340.4228 [ev=EV-0dabd234d446cc51, EV-a636912416969bf6]; nearby IPAL state table row has value=0.0 (network-derived). Reason transition is NOT confirmed: command_value_unknown,missing_pre_command_baseline,post_state_or_measurement_value_unknown,pre_test_bit_unknown.

### 3.3 Candidate Cross-Entity Co-occurring Changes (Unresolved Hypotheses, Not Causal Proof)
- [SL001 / R0019 | cross_entity_temporal_cooccurrence] (level=temporal_cooccurrence, status=unresolved, gate=unresolved_cooccurrence, causal_status=not_established): bus.0:voltage_angle (TL024) at 1742958341.3939 after EF001 (0 <= dt (1.1868s) <= 10.0s) [src_ev=EV-76d8166fbc059abd, EV-0e17d643512ce648; dst_ev=EV-70a4b7958202b60d, EV-0f33f786905f3334].
- [SL001 / R0020 | cross_entity_temporal_cooccurrence] (level=temporal_cooccurrence, status=unresolved, gate=unresolved_cooccurrence, causal_status=not_established): bus.0:voltage_angle (TL020) at 1742958341.8582 after EF001 (0 <= dt (1.6512s) <= 10.0s) [src_ev=EV-76d8166fbc059abd, EV-0e17d643512ce648; dst_ev=EV-e4e78d76a2afc187, EV-6a6f8e7514ed5615].
- [SL001 / R0021 | cross_entity_temporal_cooccurrence] (level=temporal_cooccurrence, status=unresolved, gate=unresolved_cooccurrence, causal_status=not_established): line.13:current_from (TL023) at 1742958342.6661 after EF001 (0 <= dt (2.4591s) <= 10.0s) [src_ev=EV-76d8166fbc059abd, EV-0e17d643512ce648; dst_ev=EV-1535e88069b77d8a, EV-4e9bab5fb1c75908].
- [SL001 / R0022 | cross_entity_temporal_cooccurrence] (level=temporal_cooccurrence, status=unresolved, gate=unresolved_cooccurrence, causal_status=not_established): line.13:current_from (TL019) at 1742958342.8582 after EF001 (0 <= dt (2.6512s) <= 10.0s) [src_ev=EV-76d8166fbc059abd, EV-0e17d643512ce648; dst_ev=EV-02995bc07633e298, EV-428b73063a7d2843].

## 4. Alternative Explanations & Competing Hypotheses
- **[SL001 | competing_cross_entity_cooccurrences | status=`unresolved`]**: Multiple distinct grid measurements (bus.0:voltage_angle, bus.0:voltage_angle, line.13:current_from, line.13:current_from) changed within the time horizon after trafo.0:tap_position. Without an independent physical topology/power-flow model in the loop, these remain competing unresolved temporal co-occurrences rather than confirmed causal effects.
- **[SL001 | state_report_without_verified_before_after_values | status=`unresolved`]**: A subsequent M_SP_NA_1 (COT=3) state report was observed for trafo.0, but state_report_observed_value_unknown (command_value_unknown,missing_pre_command_baseline,post_state_or_measurement_value_unknown,pre_test_bit_unknown). Therefore a state transition cannot be confirmed from protocol values alone.

## 5. Unresolved Questions, Evidence Gaps & Unattached Observations
- **Evidence Gap**: `{"scope": "TX001", "entity": "trafo.0:tap_position", "missing_stages": ["activation_termination_cot10", "unverified_state_transition:command_value_unknown,missing_pre_command_baseline,post_state_or_measurement_value_unknown,pre_test_bit_unknown"]}`
- **Unattached Observations (`11` nodes not on a storyline spine)**:
  - `TL001` (`1742958340.2070`, `network`, `communication`): `172.16.1.2:46184->172.16.2.5:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-e1f31a89f722f504, EV-e13cc45e370718fc`]
  - `TL003` (`1742958340.2211`, `network`, `communication`): `172.16.2.5:2404->172.16.1.2:46184/TCP` (`not_on_confirmed_storyline_spine`) [`EV-6fcb95eceb738630, EV-eadae946b4ae509c`]
  - `TL005` (`1742958340.2301`, `network`, `communication`): `172.16.3.13:2404->172.16.1.2:59412/TCP` (`not_on_confirmed_storyline_spine`) [`EV-026d34f657ffbb09, EV-9df69575ffd8fb70`]
  - `TL007` (`1742958340.2502`, `network`, `communication`): `172.16.1.2:59412->172.16.3.13:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-24aafceb064d43ec, EV-aac31ca2c9fb918a`]
  - `EF004` (`1742958340.8582`, `electrical`, `electrical_state_update`): `trafo.0:tap_position` (`isolated_no_graph_edge`) [`EV-e19061504aad7456`]
  - `TL024` (`1742958341.3939`, `network`, `electrical_report`): `bus.0:voltage_angle` (`not_on_confirmed_storyline_spine`) [`EV-70a4b7958202b60d, EV-0f33f786905f3334`]
  - `TL020` (`1742958341.8582`, `electrical`, `electrical_change`): `bus.0:voltage_angle` (`not_on_confirmed_storyline_spine`) [`EV-e4e78d76a2afc187, EV-6a6f8e7514ed5615`]
  - `TL023` (`1742958342.6661`, `network`, `electrical_report`): `line.13:current_from` (`not_on_confirmed_storyline_spine`) [`EV-1535e88069b77d8a, EV-4e9bab5fb1c75908`]
  - `TL019` (`1742958342.8582`, `electrical`, `electrical_change`): `line.13:current_from` (`not_on_confirmed_storyline_spine`) [`EV-02995bc07633e298, EV-428b73063a7d2843`]
  - `TL014` (`1742958347.8582`, `electrical`, `electrical_change`): `line.13:current_to` (`not_on_confirmed_storyline_spine`) [`EV-15f5dbfd3ee06482, EV-c6dfe362dfa5c0be`]
