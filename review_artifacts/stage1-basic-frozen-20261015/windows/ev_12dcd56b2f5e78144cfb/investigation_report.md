# Evidence-Grounded Incident Reconstruction Report

- **Report Status**: `quality_consistent`
- **Quality & Behavioral Consistency (`quality_consistency.json`)**: `consistent`
- **Evidence Lineage Audit (`lineage_consistency.json`)**: `consistent`

- **Incident Window**: `1742949082.2307525` to `1742949112.2784526`
- **Reconstructed IEC-104 Transactions**: `1`
- **Reconstructed Event Storylines**: `6`
- **Verified Same-Device Transitions (Consistency Gate Passed)**: `1`
- **Unverified Protocol State Reports (Value Undecoded or No Pre-Baseline)**: `0`
- **LLM Claim Verifier Output (Separate from Graph Gate)**: `0` verified, `0` withheld

## 1. Incident Sequence & Protocol Transactions
- **TX001** (`1742949082.2828`–`1742949085.5235`): `C_SE_NC_1 (Setpoint command, short float)` on `sgen.10:target_active_power` (`CA/IOA=108.10040`, value=`270000.0`) over `172.16.1.2:59440 -> 172.16.3.3:2404` at vantages `['n302']`. **Command Acceptance (`COT=7` P/N)**: `accepted_by_rtu`; **Device State Verification**: `verified_measurement_transition` (reason=`pre_to_post_shift_and_setpoint_match_verified`); **Completeness**: `partial_no_cot10_but_verified_measurement_transition`; **Missing/Unverified Stages**: `['activation_termination_cot10']` (`EV-fe4bc0d7a9f72070, EV-4634be0743bce55a, EV-5a7f4bc8ea560bbd, EV-1264e9b2b2106c6a`).
  - Inference gate (`measurement_transition`): passed=`True`; pre IV=`False` other flags=`[]`; post IV=`False` other flags=`[]`; COT test bits=`{'command': False, 'confirmation': False, 'pre': False, 'post': False}`; failed=`[]`.

## 2A. Behavioral Incident Reconstruction (No Control Command)
- `0` event anchors found; a control transaction is present, so anchors are listed in `event_anchors.json` and do not root storylines.

## 2B. Incident Scenario Synthesis (Four-Layer Epistemic Integration)
- **Scenario Status**: `synthesized_consistent`
- **Layer 1 Partition**: `1` supported multi-node chains, `0` verified single-anchor chains, `0` sequential same-entity observations (gate failed), `0` quarantined unverified observations (`0` unverified COT=3 precursor reports).
- **Layer 2 Bundles & Bridges**: `0` source bundles (each counted as `1` container), `0` cross-RTU verified element bridges, `0` same-RTU supported relations (not cross-RTU support), `0` multi-bundle bridged components.
- **Layer 3 Candidate Phases**: `1` candidate scenario phases (all cross-device links kept `unresolved`).
- **Layer 4 Source Dependency Ledger**: `0` IEC-104 ASDU, `0` TCP link, `0` ARP, `4` composite containers across `1` RTU(s) (`['172.16.3.3']`), `0` co-reported same-ASDU points collapsed, mirror vantages `['n302']`, `0` IPAL rows excluded (`weight=0`).

### 2B.2 Layer 3 — Candidate Scenario Phases (Cross-Device Links Unresolved)
- **PHS-001** (`+0.052s`..`+3.293s`, profile=`protocol_command_transactions`): bundles=`[]`, verified_bridges=`[]`, sequential_same_device=`[]`, unverified_precursors=`[]`, RTUs=`['172.16.3.3']`, ARP=`[]`, unresolved_candidates=`16`.

### 2B.3 Layer 4 — Evidence-Anchored Competing Explanations & Missing Evidence
- **EXP-001** (`command_induced_device_transition_hypothesis`, status=`unresolved_competing_hypothesis`, causal_status=`not_established`): Observed IEC-104 control activation(s) ['TX001'] on the SCADA network, with 1 transaction(s) passing pre/post setpoint/state consistency checks. Consistent with RTU execution of the received IEC-104 command(s).
  - **Anchored by**: `{'transaction_ids': ['TX001'], 'verified_transition_transaction_ids': ['TX001'], 'evidence_ids': ['EV-fe4bc0d7a9f72070', 'EV-4634be0743bce55a', 'EV-5a7f4bc8ea560bbd', 'EV-1264e9b2b2106c6a']}`
  - **Alternative comparison**: Competes with coincidence or unverified physical actuation where protocol confirmation (COT=7) or telemetry shifts occur without independent physical sensor verification.
  - **Missing disambiguating evidence**: `['Independent out-of-band physical process sensor or PMU log not derived from IEC-104', 'Master station operator/application audit log identifying the initiating process']`

## 2. Key Findings & Reconstructed Storylines (Contiguous Directed Spines)
### SL001 — Anchor `sgen.10:target_active_power` (tx=`TX001`, status=`partial_missing_cot10_but_verified_measurement_transition`, contiguous_path=`True`, logical_nodes=`3`, independent_sources=`3`, independent_edges=`2`, vantage_captures=`3`)
- Step 1 [R0001 | N-N | iec104_command_confirmation | level=observed_fact | gate=direct_record_observation | independent_evidence]: EF001 (sgen.10:target_active_power @ 1742949082.2828) -> EF002 (sgen.10:target_active_power @ 1742949082.356) [src_ev=EV-fe4bc0d7a9f72070, EV-4634be0743bce55a; dst_ev=EV-5a7f4bc8ea560bbd, EV-1264e9b2b2106c6a]
- Step 2 [R0003 | N-N | command_to_device_state_transition | level=supported_inference | gate=passed_noncausal_inference_gate | independent_evidence]: EF002 (sgen.10:target_active_power @ 1742949082.356) -> EF004 (sgen.10:active_power @ 1742949085.5235) [src_ev=EV-5a7f4bc8ea560bbd, EV-1264e9b2b2106c6a; dst_ev=EV-525c5316decdf147, EV-1be9254b88f5dbde]
- Supporting Edge [R0002 | N-N | pre_to_post_measurement_transition | level=observed_fact]: EF003 (sgen.10:active_power=309980.938 @ 1742949075.456) -> EF004 (sgen.10:active_power=269971.625 @ 1742949085.5235) [src_ev=EV-91e836fb7940ebc3, EV-ac0feed9b7c33c72; dst_ev=EV-525c5316decdf147, EV-1be9254b88f5dbde]
- Time-aligned IPAL row [R0008 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: EF005 (sgen.10:target_active_power=270000.0 @ 1742949082.8582) aligned with EF001; not an independent source
- Time-aligned IPAL row [R0009 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: EF005 (sgen.10:target_active_power=270000.0 @ 1742949082.8582) aligned with EF002; not an independent source
- Time-aligned IPAL row [R0011 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: EF006 (sgen.10:active_power=269971.625 @ 1742949085.8582) aligned with EF004; not an independent source
- **Evidence Gaps**: `['activation_termination_cot10']`
### SL002 — Anchor `line.11:current_to` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`12`)
- Step 1 [R0024 | N-N | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL010 (line.11:current_to @ 1742949087.6702) -> TL011 (line.11:current_from @ 1742949091.9443) [src_ev=EV-c9bc8229ca65829c, EV-cbb90b3f94473d44; dst_ev=EV-f9d1e352cdaf42e4, EV-fe0bb06ea0d20513]
- Time-aligned IPAL row [R0015 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL014 (line.11:current_to=0.0210324227809906 @ 1742949087.8582) aligned with TL010; not an independent source
- Time-aligned IPAL row [R0017 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL017 (line.11:current_from=-0.07940073311328888 @ 1742949082.8582) aligned with TL011; not an independent source
### SL003 — Anchor `line.13:current_from` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`18`)
- Step 1 [R0023 | N-N | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL012 (line.13:current_from @ 1742949087.0704) -> TL022 (line.13:current_to @ 1742949091.8185) [src_ev=EV-cee140ca39fed8d4, EV-fa025d29db0f53e6; dst_ev=EV-7a41318e0e75e44f, EV-a95775acf11a0802]
- Time-aligned IPAL row [R0014 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL015 (line.13:current_from=-0.12782934308052063 @ 1742949087.8582) aligned with TL012; not an independent source
- Time-aligned IPAL row [R0016 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL018 (line.13:current_to=-0.19982147216796875 @ 1742949082.8582) aligned with TL022; not an independent source
### SL004 — Anchor `line.4:current_to` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`12`)
- Step 1 [R0021 | N-N | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL013 (line.4:current_to @ 1742949084.6863) -> TL024 (line.4:current_from @ 1742949087.0626) [src_ev=EV-27cb5e4954cdfc9f, EV-a34a43be855036eb; dst_ev=EV-478fbb2f9cfa57ad, EV-c2591ff5aa35a0d0]
- Time-aligned IPAL row [R0010 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL016 (line.4:current_to=-0.11151884496212006 @ 1742949084.8582) aligned with TL013; not an independent source
- Time-aligned IPAL row [R0013 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL020 (line.4:current_from=0.8807488679885864 @ 1742949087.8582) aligned with TL024; not an independent source
### SL005 — Anchor `line.4:current_to` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`6`)
- Step 1 [R0022 | P-P | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL016 (line.4:current_to @ 1742949084.8582) -> TL020 (line.4:current_from @ 1742949087.8582) [src_ev=EV-f39e1dcd8a00d1f6, EV-9e13c3d65e5642fc; dst_ev=EV-7609be8cb444e12e, EV-0cfd3292d9c9180f]
### SL006 — Anchor `line.11:current_from` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`6`)
- Step 1 [R0019 | P-P | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL017 (line.11:current_from @ 1742949082.8582) -> TL014 (line.11:current_to @ 1742949087.8582) [src_ev=EV-9c6c71c035c1eb85, EV-40798202c26e6e1f; dst_ev=EV-ecd244922bdd32b6, EV-f49a19c3830e4816]

## 3. Observed Network & Electrical Impact (Epistemically Stratified)
### 3.1 Verified Same-Device Measurement/State Transitions (Consistency Gate Passed)
- [TX001 | verified_measurement_transition] Controlled point sgen.10:active_power (CA/IOA=108.10080) shifted from pre-command baseline 309980.938 (@ 1742949075.456, pre_ev=EV-91e836fb7940ebc3, EV-ac0feed9b7c33c72) to 269971.625 (@ 1742949085.5235, post_ev=EV-525c5316decdf147), matching commanded setpoint 270000.0. Non-causal protocol/measurement alignment.

### 3.2 Protocol State Reports Observed Without Verified Transition (Value Undecoded or No Pre-Baseline)
- None.

### 3.3 Candidate Cross-Entity Co-occurring Changes (Unresolved Hypotheses, Not Causal Proof)
- [SL001 / R0025 | cross_entity_temporal_cooccurrence] (level=temporal_cooccurrence, status=unresolved, gate=unresolved_cooccurrence, causal_status=not_established): line.11:current_from (TL017) at 1742949082.8582 after EF001 (0 <= dt (0.5754s) <= 10.0s) [src_ev=EV-fe4bc0d7a9f72070, EV-4634be0743bce55a; dst_ev=EV-9c6c71c035c1eb85, EV-40798202c26e6e1f].
- [SL001 / R0026 | cross_entity_temporal_cooccurrence] (level=temporal_cooccurrence, status=unresolved, gate=unresolved_cooccurrence, causal_status=not_established): line.13:current_to (TL018) at 1742949082.8582 after EF001 (0 <= dt (0.5754s) <= 10.0s) [src_ev=EV-fe4bc0d7a9f72070, EV-4634be0743bce55a; dst_ev=EV-82e747a2258618e2, EV-e722ac7efca640d4].
- [SL001 / R0027 | cross_entity_temporal_cooccurrence] (level=temporal_cooccurrence, status=unresolved, gate=unresolved_cooccurrence, causal_status=not_established): bus.9:active_power (TL021) at 1742949082.8582 after EF001 (0 <= dt (0.5754s) <= 10.0s) [src_ev=EV-fe4bc0d7a9f72070, EV-4634be0743bce55a; dst_ev=EV-b7c7c6c5ced67325, EV-bef95f3096e3a589].
- [SL001 / R0028 | cross_entity_temporal_cooccurrence] (level=temporal_cooccurrence, status=unresolved, gate=unresolved_cooccurrence, causal_status=not_established): line.4:current_to (TL013) at 1742949084.6863 after EF001 (0 <= dt (2.4035s) <= 10.0s) [src_ev=EV-fe4bc0d7a9f72070, EV-4634be0743bce55a; dst_ev=EV-27cb5e4954cdfc9f, EV-a34a43be855036eb].

## 4. Alternative Explanations & Competing Hypotheses
- **[SL001 | competing_cross_entity_cooccurrences | status=`unresolved`]**: Multiple distinct grid measurements (line.11:current_from, line.13:current_to, bus.9:active_power, line.4:current_to) changed within the time horizon after sgen.10:target_active_power. Without an independent physical topology/power-flow model in the loop, these remain competing unresolved temporal co-occurrences rather than confirmed causal effects.

## 5. Unresolved Questions, Evidence Gaps & Unattached Observations
- **Evidence Gap**: `{"scope": "TX001", "entity": "sgen.10:target_active_power", "missing_stages": ["activation_termination_cot10"]}`
- **Unattached Observations (`15` nodes not on a storyline spine)**:
  - `TL001` (`1742949082.2828`, `network`, `communication`): `172.16.1.2:59440->172.16.3.3:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-4634be0743bce55a, EV-08b83c9aeae3ec51`]
  - `TL002` (`1742949082.3431`, `network`, `communication`): `172.16.3.3:2404->172.16.1.2:59440/TCP` (`not_on_confirmed_storyline_spine`) [`EV-90ba513bf233c2ad, EV-1264e9b2b2106c6a`]
  - `EF005` (`1742949082.8582`, `electrical`, `electrical_state_update`): `sgen.10:target_active_power` (`not_on_confirmed_storyline_spine`) [`EV-2d2423325af71446`]
  - `TL018` (`1742949082.8582`, `electrical`, `electrical_change`): `line.13:current_to` (`not_on_confirmed_storyline_spine`) [`EV-82e747a2258618e2, EV-e722ac7efca640d4`]
  - `TL021` (`1742949082.8582`, `electrical`, `electrical_change`): `bus.9:active_power` (`not_on_confirmed_storyline_spine`) [`EV-b7c7c6c5ced67325, EV-bef95f3096e3a589`]
  - `TL003` (`1742949084.6149`, `network`, `communication`): `172.16.3.17:2404->172.16.1.2:33402/TCP` (`not_on_confirmed_storyline_spine`) [`EV-0de7833e4b1c6fdf, EV-c8e006453bd36af0`]
  - `TL004` (`1742949084.6189`, `network`, `communication`): `172.16.1.2:33402->172.16.3.17:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-338dec9307d4e9c2, EV-0ec0b0862bf8fc91`]
  - `TL005` (`1742949084.6863`, `network`, `communication`): `172.16.3.22:2404->172.16.1.2:34946/TCP` (`not_on_confirmed_storyline_spine`) [`EV-296bba636f5a9075, EV-f0fd6a0e7309e20a`]
  - `TL006` (`1742949084.6903`, `network`, `communication`): `172.16.1.2:34946->172.16.3.22:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-8e44132ffeafd548, EV-716c7630972379e0`]
  - `TL007` (`1742949084.7701`, `network`, `communication`): `172.16.3.8:2404->172.16.1.2:50438/TCP` (`not_on_confirmed_storyline_spine`) [`EV-48fae643af956bf9, EV-34818ebab7fe6d25`]
