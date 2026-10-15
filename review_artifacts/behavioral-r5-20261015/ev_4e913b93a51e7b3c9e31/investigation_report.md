# Evidence-Grounded Incident Reconstruction Report

- **Report Status**: `quality_consistent`
- **Quality & Behavioral Consistency (`quality_consistency.json`)**: `consistent`
- **Evidence Lineage Audit (`lineage_consistency.json`)**: `consistent`

- **Incident Window**: `1742926251.1947885` to `1742926421.521569`
- **Reconstructed IEC-104 Transactions**: `0`
- **Reconstructed Event Storylines**: `6`
- **Verified Same-Device Transitions (Consistency Gate Passed)**: `0`
- **Unverified Protocol State Reports (Value Undecoded or No Pre-Baseline)**: `0`
- **LLM Claim Verifier Output (Separate from Graph Gate)**: `0` verified, `0` withheld

## 1. Incident Sequence & Protocol Transactions
- No IEC-104 control transactions were observed in this window.

## 2A. Behavioral Incident Reconstruction (No Control Command)
- Method: `evidence_anchor_discovery`. Inputs not used: `['official event labels', 'attack type', 'malicious flags', 'physical.zip']`. Control objects in window: `0`.
- `4` event anchors (`1` verified, `3` unverified), `4` behavioral storylines (`0` with corroborated multi-ASDU transitions, `1` verified single-anchor, `3` unverified observations), `1` sequential same-entity observations (gate failed), `0` unresolved cross-device branches.

### 2A.1 Event Anchors (by time)
- **A001** (rank `2`, `spontaneous_state_report`, `unverified_observation`, +`1.187`s, RTU `172.16.3.15`): sgen.0:is_connected (CA/IOA=120.10060) reported value 0.0 with COT=3 by RTU 172.16.3.15; prior IEC-104 value in window: not observed (state_report_no_prior_value_in_window; verification=unverified_observation).
- **A002** (rank `1`, `measurement_step`, `verified_observation`, +`10.839`s, RTU `172.16.3.15`): sgen.0: 1 measurement(s) in one ASDU from RTU 172.16.3.15 changed active_power 20000.4004 -> 0.0 (to_zero; quality good=True; sustained=True; verification=verified_observation).
- **A003** (rank `3`, `measurement_step`, `unverified_observation`, +`132.852`s, RTU `172.16.3.26`): line.14: 1 measurement(s) in one ASDU from RTU 172.16.3.26 changed current_to 0.0099699581 -> -0.270960242 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A004** (rank `4`, `measurement_step`, `unverified_observation`, +`151.897`s, RTU `172.16.3.12`): line.14: 1 measurement(s) in one ASDU from RTU 172.16.3.12 changed current_from -0.0392444469 -> 0.254208267 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['insufficient_post_samples']).

### 2A.2 Behavioral Storylines
#### SL001 — anchors `['A001']` (+`1.187`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A001] sgen.0:is_connected (CA/IOA=120.10060) reported value 0.0 with COT=3 by RTU 172.16.3.15; prior IEC-104 value in window: not observed (state_report_no_prior_value_in_window; verification=unverified_observation). 1 same-device sequential observation(s) kept off-spine (failed behavioral consistency gate: [['left_not_sustained', 'left_anchor_unverified', 'state_to_measurement_change_mismatch']]).
- **Unverified observation issues**: `{'A001': ['no_prior_state_value_in_window']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Sequential same-entity observations (failed behavioral consistency gate, NOT supported transition)**: R0035 same_entity_sequential_observation: sgen.0:is_connected (@+1.187s) -> sgen.0:active_power (@+10.839s); failed_gate=['left_not_sustained', 'left_anchor_unverified', 'state_to_measurement_change_mismatch']
- **IPAL time-aligned rows (not independent)**: sgen.0:connected (temporally_aligned_same_device_ipal_row; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL002 — anchors `['A002']` (+`10.839`s, status=`behavioral_single_anchor`)
- **Reconstructed**: [A002] sgen.0: 1 measurement(s) in one ASDU from RTU 172.16.3.15 changed active_power 20000.4004 -> 0.0 (to_zero; quality good=True; sustained=True; verification=verified_observation). 1 same-device sequential observation(s) kept off-spine (failed behavioral consistency gate: [['left_not_sustained', 'left_anchor_unverified', 'state_to_measurement_change_mismatch']]).
- **Evidence-supported relations**: none (single anchor)
- **Sequential same-entity observations (failed behavioral consistency gate, NOT supported transition)**: R0035 same_entity_sequential_observation: sgen.0:is_connected (@+1.187s) -> sgen.0:active_power (@+10.839s); failed_gate=['left_not_sustained', 'left_anchor_unverified', 'state_to_measurement_change_mismatch']
- **IPAL time-aligned rows (not independent)**: sgen.0:active_power (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL003 — anchors `['A003']` (+`132.852`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A003] line.14: 1 measurement(s) in one ASDU from RTU 172.16.3.26 changed current_to 0.0099699581 -> -0.270960242 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A003': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.14:current_to (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL004 — anchors `['A004']` (+`151.897`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A004] line.14: 1 measurement(s) in one ASDU from RTU 172.16.3.12 changed current_from -0.0392444469 -> 0.254208267 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['insufficient_post_samples']).
- **Unverified observation issues**: `{'A004': ['insufficient_post_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.14:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.

## 2. Key Findings & Reconstructed Storylines (Contiguous Directed Spines)
### SL005 — Anchor `line.12:current_to` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`34`)
- Step 1 [R0019 | P-P | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL014 (line.12:current_to @ 1742926254.8582) -> TL017 (line.12:current_from @ 1742926254.8582) [src_ev=EV-508f51b8a75b85e0, EV-40dad601a12c491f; dst_ev=EV-6c9218e93258db7b, EV-285a8c65908ff789]
### SL006 — Anchor `line.14:current_from` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`34`)
- Step 1 [R0017 | P-P | same_device_attribute_coupling | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL016 (line.14:current_from @ 1742926253.8582) -> TL015 (line.14:current_to @ 1742926254.8582) [src_ev=EV-f94297fa1a923c71, EV-7fc4dec25dee6ed6; dst_ev=EV-d5befe0a70619096, EV-798ad97c72ab1274]

## 3. Observed Network & Electrical Impact (Epistemically Stratified)
### 3.1 Verified Same-Device Measurement/State Transitions (Consistency Gate Passed)
- No post-command device transition passed all pre/post and target consistency checks.

### 3.2 Protocol State Reports Observed Without Verified Transition (Value Undecoded or No Pre-Baseline)
- None.

### 3.3 Candidate Cross-Entity Co-occurring Changes (Unresolved Hypotheses, Not Causal Proof)
- [SL005 / R0029 | cross_entity_temporal_cooccurrence] (level=temporal_cooccurrence, status=unresolved, gate=unresolved_cooccurrence, causal_status=not_established): line.14:current_to (TL015) at 1742926254.8582 after TL014 (0 <= dt (0.0s) <= 2.0s) [src_ev=EV-508f51b8a75b85e0, EV-40dad601a12c491f; dst_ev=EV-d5befe0a70619096, EV-798ad97c72ab1274].
- [SL006 / R0027 | cross_entity_temporal_cooccurrence] (level=temporal_cooccurrence, status=unresolved, gate=unresolved_cooccurrence, causal_status=not_established): line.12:current_to (TL014) at 1742926254.8582 after TL016 (0 <= dt (1.0s) <= 2.0s) [src_ev=EV-f94297fa1a923c71, EV-7fc4dec25dee6ed6; dst_ev=EV-508f51b8a75b85e0, EV-40dad601a12c491f].
- [SL006 / R0028 | cross_entity_temporal_cooccurrence] (level=temporal_cooccurrence, status=unresolved, gate=unresolved_cooccurrence, causal_status=not_established): line.12:current_from (TL017) at 1742926254.8582 after TL016 (0 <= dt (1.0s) <= 2.0s) [src_ev=EV-f94297fa1a923c71, EV-7fc4dec25dee6ed6; dst_ev=EV-6c9218e93258db7b, EV-285a8c65908ff789].

## 4. Alternative Explanations & Competing Hypotheses
- **[SL006 | competing_cross_entity_cooccurrences | status=`unresolved`]**: Multiple distinct grid measurements (line.12:current_to, line.12:current_from) changed within the time horizon after line.14:current_from. Without an independent physical topology/power-flow model in the loop, these remain competing unresolved temporal co-occurrences rather than confirmed causal effects.

## 5. Unresolved Questions, Evidence Gaps & Unattached Observations
- **Unattached Observations (`24` nodes not on a storyline spine)**:
  - `TL013` (`1742926251.8582`, `electrical`, `electrical_change`): `bus.0:voltage_angle` (`not_on_confirmed_storyline_spine`) [`EV-0f95745100945a33, EV-627421b1178ba53c`]
  - `TL007` (`1742926251.8948`, `network`, `communication`): `172.16.2.5:2404->172.16.1.2:46184/TCP` (`not_on_confirmed_storyline_spine`) [`EV-95a0b61e27d0b945, EV-4568e462618945bd`]
  - `TL025` (`1742926251.9088`, `network`, `communication`): `172.16.1.2:46184->172.16.2.5:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-5e40a02421dc649f, EV-64a4021d911b47c7`]
  - `TL001` (`1742926252.4954`, `network`, `communication`): `172.16.3.9:2404->172.16.1.2:54426/TCP` (`not_on_confirmed_storyline_spine`) [`EV-03b2be8433a8f81e, EV-47e4902554fe48aa`]
  - `TL022` (`1742926252.4954`, `network`, `electrical_report`): `line.13:current_from` (`not_on_confirmed_storyline_spine`) [`EV-9bf90ef75e4113d8, EV-a9398ac5d0fe65a0`]
  - `TL002` (`1742926252.5396`, `network`, `communication`): `172.16.1.2:54426->172.16.3.9:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-cbed55e43bcfc9f3, EV-19642c88a68fc977`]
  - `BI001` (`1742926252.8582`, `electrical`, `ipal_correspondence`): `sgen.0:connected` (`not_on_confirmed_storyline_spine`) [`EV-6ec9af22f41a73b3`]
  - `TL019` (`1742926252.8582`, `electrical`, `electrical_change`): `line.13:current_from` (`not_on_confirmed_storyline_spine`) [`EV-c3ee3d0f40bd10c6, EV-c45cff4b5dab167f`]
  - `TL011` (`1742926252.9954`, `network`, `electrical_report`): `line.14:current_from` (`not_on_confirmed_storyline_spine`) [`EV-58c0e1b68e5b6417, EV-938d12dd2514c651`]
  - `TL003` (`1742926253.0093`, `network`, `communication`): `172.16.3.1:2404->172.16.1.2:55486/TCP` (`not_on_confirmed_storyline_spine`) [`EV-a8619bff04580e39, EV-52e3d9f16dc44887`]
