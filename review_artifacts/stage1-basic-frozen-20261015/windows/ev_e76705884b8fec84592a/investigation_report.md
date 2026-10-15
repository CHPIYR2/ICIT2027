# Evidence-Grounded Incident Reconstruction Report

- **Report Status**: `quality_consistent`
- **Quality & Behavioral Consistency (`quality_consistency.json`)**: `consistent`
- **Evidence Lineage Audit (`lineage_consistency.json`)**: `consistent`

- **Incident Window**: `1742928231.189216` to `1742928261.2682297`
- **Reconstructed IEC-104 Transactions**: `1`
- **Reconstructed Event Storylines**: `6`
- **Verified Same-Device Transitions (Consistency Gate Passed)**: `1`
- **Unverified Protocol State Reports (Value Undecoded or No Pre-Baseline)**: `0`
- **LLM Claim Verifier Output (Separate from Graph Gate)**: `0` verified, `0` withheld

## 1. Incident Sequence & Protocol Transactions
- **TX001** (`1742928231.2015`–`1742928237.4152`): `C_SE_NC_1 (Setpoint command, short float)` on `sgen.1:target_active_power` (`CA/IOA=122.10040`, value=`15000.0`) over `172.16.1.2:33402 -> 172.16.3.17:2404` at vantages `['n302']`. **Command Acceptance (`COT=7` P/N)**: `accepted_by_rtu`; **Device State Verification**: `verified_measurement_transition` (reason=`pre_to_post_shift_and_setpoint_match_verified`); **Completeness**: `partial_no_cot10_but_verified_measurement_transition`; **Missing/Unverified Stages**: `['activation_termination_cot10']` (`EV-9c83f12c8b0c4c2f, EV-bb6c0d35de4b0d52, EV-e8ce5554cc42318c, EV-c12bd6819a2b2092`).
  - Inference gate (`measurement_transition`): passed=`True`; pre IV=`False` other flags=`[]`; post IV=`False` other flags=`[]`; COT test bits=`{'command': False, 'confirmation': False, 'pre': False, 'post': False}`; failed=`[]`.

## 2A. Behavioral Incident Reconstruction (No Control Command)
- `1` event anchors found; a control transaction is present, so anchors are listed in `event_anchors.json` and do not root storylines.

## 2B. Incident Scenario Synthesis (Four-Layer Epistemic Integration)
- **Scenario Status**: `synthesized_consistent`
- **Layer 1 Partition**: `1` supported multi-node chains, `0` verified single-anchor chains, `0` sequential same-entity observations (gate failed), `0` quarantined unverified observations (`0` unverified COT=3 precursor reports).
- **Layer 2 Bundles & Bridges**: `0` source bundles (each counted as `1` container), `0` cross-RTU verified element bridges, `0` same-RTU supported relations (not cross-RTU support), `0` multi-bundle bridged components.
- **Layer 3 Candidate Phases**: `1` candidate scenario phases (all cross-device links kept `unresolved`).
- **Layer 4 Source Dependency Ledger**: `0` IEC-104 ASDU, `0` TCP link, `0` ARP, `4` composite containers across `1` RTU(s) (`['172.16.3.17']`), `0` co-reported same-ASDU points collapsed, mirror vantages `['n302']`, `1` IPAL rows excluded (`weight=0`).

### 2B.2 Layer 3 — Candidate Scenario Phases (Cross-Device Links Unresolved)
- **PHS-001** (`+0.012s`..`+6.226s`, profile=`protocol_command_transactions`): bundles=`[]`, verified_bridges=`[]`, sequential_same_device=`[]`, unverified_precursors=`[]`, RTUs=`['172.16.3.17']`, ARP=`[]`, unresolved_candidates=`16`.

### 2B.3 Layer 4 — Evidence-Anchored Competing Explanations & Missing Evidence
- **EXP-001** (`command_induced_device_transition_hypothesis`, status=`unresolved_competing_hypothesis`, causal_status=`not_established`): Observed IEC-104 control activation(s) ['TX001'] on the SCADA network, with 1 transaction(s) passing pre/post setpoint/state consistency checks. Consistent with RTU execution of the received IEC-104 command(s).
  - **Anchored by**: `{'transaction_ids': ['TX001'], 'verified_transition_transaction_ids': ['TX001'], 'evidence_ids': ['EV-9c83f12c8b0c4c2f', 'EV-bb6c0d35de4b0d52', 'EV-e8ce5554cc42318c', 'EV-c12bd6819a2b2092']}`
  - **Alternative comparison**: Competes with coincidence or unverified physical actuation where protocol confirmation (COT=7) or telemetry shifts occur without independent physical sensor verification.
  - **Missing disambiguating evidence**: `['Independent out-of-band physical process sensor or PMU log not derived from IEC-104', 'Master station operator/application audit log identifying the initiating process']`

## 2. Key Findings & Reconstructed Storylines (Contiguous Directed Spines)
### SL001 — Anchor `sgen.1:target_active_power` (tx=`TX001`, status=`partial_missing_cot10_but_verified_measurement_transition`, contiguous_path=`True`, logical_nodes=`3`, independent_sources=`3`, independent_edges=`2`, vantage_captures=`3`)
- Step 1 [R0001 | N-N | iec104_command_confirmation | level=observed_fact | gate=direct_record_observation | independent_evidence]: EF001 (sgen.1:target_active_power @ 1742928231.2015) -> EF002 (sgen.1:target_active_power @ 1742928231.2643) [src_ev=EV-9c83f12c8b0c4c2f, EV-bb6c0d35de4b0d52; dst_ev=EV-e8ce5554cc42318c, EV-c12bd6819a2b2092]
- Step 2 [R0003 | N-N | command_to_device_state_transition | level=supported_inference | gate=passed_noncausal_inference_gate | independent_evidence]: EF002 (sgen.1:target_active_power @ 1742928231.2643) -> EF004 (sgen.1:active_power @ 1742928237.4152) [src_ev=EV-e8ce5554cc42318c, EV-c12bd6819a2b2092; dst_ev=EV-d1b519b062899fc7, EV-56b422da31eeb916]
- Supporting Edge [R0002 | N-N | pre_to_post_measurement_transition | level=observed_fact]: EF003 (sgen.1:active_power=19999.3438 @ 1742928227.3674) -> EF004 (sgen.1:active_power=15001.9707 @ 1742928237.4152) [src_ev=EV-fd365583d8937e96, EV-44a49141baaa56e6; dst_ev=EV-d1b519b062899fc7, EV-56b422da31eeb916]
- Time-aligned IPAL row [R0007 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: EF005 (sgen.1:target_active_power=15000.0 @ 1742928231.8582) aligned with EF001; not an independent source
- Time-aligned IPAL row [R0008 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: EF005 (sgen.1:target_active_power=15000.0 @ 1742928231.8582) aligned with EF002; not an independent source
- Time-aligned IPAL row [R0015 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: EF006 (sgen.1:active_power=15001.970703125 @ 1742928237.8582) aligned with EF004; not an independent source
- **Evidence Gaps**: `['activation_termination_cot10']`
### SL002 — Anchor `line.12:current_to` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`6`)
- Step 1 [R0022 | P-P | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL014 (line.12:current_to @ 1742928235.8582) -> TL017 (line.12:current_from @ 1742928235.8582) [src_ev=EV-afa644610e9ad279, EV-d273ea314021db17; dst_ev=EV-9f6a1bdd4d1dd3ce, EV-5b9341f93a905c05]
### SL003 — Anchor `line.12:current_from` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`12`)
- Step 1 [R0021 | N-N | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL013 (line.12:current_from @ 1742928235.6377) -> TL010 (line.12:current_to @ 1742928235.7888) [src_ev=EV-7eafeb1490cdd32a, EV-742f8354c360f293; dst_ev=EV-7e21d52997ec0561, EV-c54ae2b0f2149c2f]
- Time-aligned IPAL row [R0013 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL017 (line.12:current_from=0.3092058002948761 @ 1742928235.8582) aligned with TL013; not an independent source
- Time-aligned IPAL row [R0014 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL014 (line.12:current_to=-0.25940656661987305 @ 1742928235.8582) aligned with TL010; not an independent source
### SL004 — Anchor `line.13:current_from` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`18`)
- Step 1 [R0017 | N-N | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL022 (line.13:current_from @ 1742928233.7522) -> TL024 (line.13:current_to @ 1742928238.4932) [src_ev=EV-73bfde5d2fb5d023, EV-4143dd5fa10fc0ee; dst_ev=EV-f44ee5a8224bfb65, EV-dcfa6bc4e0c5703d]
- Time-aligned IPAL row [R0010 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL018 (line.13:current_from=-0.12367453426122665 @ 1742928233.8582) aligned with TL022; not an independent source
- Time-aligned IPAL row [R0016 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL020 (line.13:current_to=0.1944163292646408 @ 1742928238.8582) aligned with TL024; not an independent source
### SL005 — Anchor `line.13:current_from` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`6`)
- Step 1 [R0018 | P-P | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL018 (line.13:current_from @ 1742928233.8582) -> TL020 (line.13:current_to @ 1742928238.8582) [src_ev=EV-852d376966287a13, EV-3722f2e1853a9b42; dst_ev=EV-3879743c94a25dd6, EV-9fb9681cafa941dc]
### SL006 — Anchor `line.14:current_from` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`6`)
- Step 1 [R0020 | P-P | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL019 (line.14:current_from @ 1742928234.8582) -> TL015 (line.14:current_to @ 1742928235.8582) [src_ev=EV-4c5e290cf4d33bfd, EV-687add7f278a1f19; dst_ev=EV-0b3eae7f49d47383, EV-e0c88e05cc38f901]

## 3. Observed Network & Electrical Impact (Epistemically Stratified)
### 3.1 Verified Same-Device Measurement/State Transitions (Consistency Gate Passed)
- [TX001 | verified_measurement_transition] Controlled point sgen.1:active_power (CA/IOA=122.10080) shifted from pre-command baseline 19999.3438 (@ 1742928227.3674, pre_ev=EV-fd365583d8937e96, EV-44a49141baaa56e6) to 15001.9707 (@ 1742928237.4152, post_ev=EV-d1b519b062899fc7), matching commanded setpoint 15000.0. Non-causal protocol/measurement alignment.

### 3.2 Protocol State Reports Observed Without Verified Transition (Value Undecoded or No Pre-Baseline)
- None.

### 3.3 Candidate Cross-Entity Co-occurring Changes (Unresolved Hypotheses, Not Causal Proof)
- [SL001 / R0023 | cross_entity_temporal_cooccurrence] (level=temporal_cooccurrence, status=unresolved, gate=unresolved_cooccurrence, causal_status=not_established): bus.0:voltage_angle (TL012) at 1742928232.1948 after EF001 (0 <= dt (0.9933s) <= 10.0s) [src_ev=EV-9c83f12c8b0c4c2f, EV-bb6c0d35de4b0d52; dst_ev=EV-f4d1f3c6820f22cb, EV-2a9b4c88e1e068bd].
- [SL001 / R0024 | cross_entity_temporal_cooccurrence] (level=temporal_cooccurrence, status=unresolved, gate=unresolved_cooccurrence, causal_status=not_established): bus.0:voltage_angle (TL016) at 1742928232.8582 after EF001 (0 <= dt (1.6567s) <= 10.0s) [src_ev=EV-9c83f12c8b0c4c2f, EV-bb6c0d35de4b0d52; dst_ev=EV-33b8b34c5318506c, EV-07f5d70aabe7fd23].
- [SL001 / R0025 | cross_entity_temporal_cooccurrence] (level=temporal_cooccurrence, status=unresolved, gate=unresolved_cooccurrence, causal_status=not_established): line.13:current_from (TL022) at 1742928233.7522 after EF001 (0 <= dt (2.5507s) <= 10.0s) [src_ev=EV-9c83f12c8b0c4c2f, EV-bb6c0d35de4b0d52; dst_ev=EV-73bfde5d2fb5d023, EV-4143dd5fa10fc0ee].
- [SL001 / R0026 | cross_entity_temporal_cooccurrence] (level=temporal_cooccurrence, status=unresolved, gate=unresolved_cooccurrence, causal_status=not_established): line.13:current_from (TL018) at 1742928233.8582 after EF001 (0 <= dt (2.6567s) <= 10.0s) [src_ev=EV-9c83f12c8b0c4c2f, EV-bb6c0d35de4b0d52; dst_ev=EV-852d376966287a13, EV-3722f2e1853a9b42].

## 4. Alternative Explanations & Competing Hypotheses
- **[SL001 | competing_cross_entity_cooccurrences | status=`unresolved`]**: Multiple distinct grid measurements (bus.0:voltage_angle, bus.0:voltage_angle, line.13:current_from, line.13:current_from) changed within the time horizon after sgen.1:target_active_power. Without an independent physical topology/power-flow model in the loop, these remain competing unresolved temporal co-occurrences rather than confirmed causal effects.

## 5. Unresolved Questions, Evidence Gaps & Unattached Observations
- **Evidence Gap**: `{"scope": "TX001", "entity": "sgen.1:target_active_power", "missing_stages": ["activation_termination_cot10"]}`
- **Unattached Observations (`12` nodes not on a storyline spine)**:
  - `EF005` (`1742928231.8582`, `electrical`, `electrical_state_update`): `sgen.1:target_active_power` (`not_on_confirmed_storyline_spine`) [`EV-f9445e96af002a77`]
  - `TL003` (`1742928232.1948`, `network`, `communication`): `172.16.2.2:2404->172.16.1.2:36624/TCP` (`not_on_confirmed_storyline_spine`) [`EV-1cb19f8857325441, EV-cc3bdea238cf372a`]
  - `TL012` (`1742928232.1948`, `network`, `electrical_report`): `bus.0:voltage_angle` (`not_on_confirmed_storyline_spine`) [`EV-f4d1f3c6820f22cb, EV-2a9b4c88e1e068bd`]
  - `TL005` (`1742928232.2088`, `network`, `communication`): `172.16.1.2:36624->172.16.2.2:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-3575640815d24012, EV-8220a76506e55302`]
  - `TL007` (`1742928232.3279`, `network`, `communication`): `172.16.2.3:2404->172.16.1.2:42436/TCP` (`not_on_confirmed_storyline_spine`) [`EV-f30c9cbead9a4862, EV-8147da700b781118`]
  - `TL025` (`1742928232.3420`, `network`, `communication`): `172.16.1.2:42436->172.16.2.3:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-55e7099dc153d37d, EV-34a558decc8297e5`]
  - `TL016` (`1742928232.8582`, `electrical`, `electrical_change`): `bus.0:voltage_angle` (`not_on_confirmed_storyline_spine`) [`EV-33b8b34c5318506c, EV-07f5d70aabe7fd23`]
  - `TL001` (`1742928233.7522`, `network`, `communication`): `172.16.3.9:2404->172.16.1.2:54426/TCP` (`not_on_confirmed_storyline_spine`) [`EV-b178c62d2042ff7e, EV-d656d111c22d2af6`]
  - `TL002` (`1742928233.7964`, `network`, `communication`): `172.16.1.2:54426->172.16.3.9:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-83ed2adb3812a77a, EV-5f0d40f1f3520146`]
  - `TL023` (`1742928234.3030`, `network`, `electrical_report`): `line.14:current_from` (`not_on_confirmed_storyline_spine`) [`EV-60f9e30200e82192, EV-4c665ef609aa0913`]
