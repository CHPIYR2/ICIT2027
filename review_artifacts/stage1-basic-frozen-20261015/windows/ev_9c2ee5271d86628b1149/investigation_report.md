# Evidence-Grounded Incident Reconstruction Report

- **Report Status**: `quality_consistent`
- **Quality & Behavioral Consistency (`quality_consistency.json`)**: `consistent`
- **Evidence Lineage Audit (`lineage_consistency.json`)**: `consistent`

- **Incident Window**: `1742942527.200247` to `1742942708.3687804`
- **Reconstructed IEC-104 Transactions**: `0`
- **Reconstructed Event Storylines**: `10`
- **Verified Same-Device Transitions (Consistency Gate Passed)**: `0`
- **Unverified Protocol State Reports (Value Undecoded or No Pre-Baseline)**: `0`
- **LLM Claim Verifier Output (Separate from Graph Gate)**: `0` verified, `0` withheld

## 1. Incident Sequence & Protocol Transactions
- No IEC-104 control transactions were observed in this window.

## 2A. Behavioral Incident Reconstruction (No Control Command)
- Method: `evidence_anchor_discovery`. Inputs not used: `['official event labels', 'attack type', 'malicious flags', 'physical.zip']`. Control objects in window: `0`.
- `10` event anchors (`4` verified, `6` unverified), `10` behavioral storylines (`0` with corroborated multi-ASDU transitions, `4` verified single-anchor, `6` unverified observations), `2` sequential same-entity observations (gate failed), `6` unresolved cross-device branches.

### 2A.1 Event Anchors (by time)
- **A001** (rank `5`, `spontaneous_state_report`, `unverified_observation`, +`0.733`s, RTU `172.16.3.11`): load.16:is_connected (CA/IOA=116.10180) reported value 0.0 with COT=3 by RTU 172.16.3.11; prior IEC-104 value in window: not observed (state_report_no_prior_value_in_window; verification=unverified_observation).
- **A002** (rank `3`, `measurement_step`, `verified_observation`, +`5.161`s, RTU `172.16.2.4`): line.10: 2 measurement(s) in one ASDU from RTU 172.16.2.4 changed active_power_from 30638.1113 -> 0.311625749; reactive_power_from 11038.1484 -> -10043.5742 (level_shift; quality good=True; sustained=True; verification=verified_observation).
- **A003** (rank `1`, `measurement_step`, `verified_observation`, +`10.572`s, RTU `172.16.3.11`): bus.13: 2 measurement(s) in one ASDU from RTU 172.16.3.11 changed active_power 30621.0742 -> 0.0; reactive_power 21073.2598 -> 0.0 (to_zero; quality good=True; sustained=True; verification=verified_observation).
- **A004** (rank `4`, `measurement_step`, `verified_observation`, +`10.572`s, RTU `172.16.3.11`): line.10: 2 measurement(s) in one ASDU from RTU 172.16.3.11 changed active_power_to -30621.9629 -> -0.0137795694; reactive_power_to -17263.7832 -> 3811.06934 (level_shift; quality good=True; sustained=True; verification=verified_observation).
- **A005** (rank `2`, `measurement_step`, `verified_observation`, +`10.572`s, RTU `172.16.3.11`): load.16: 2 measurement(s) in one ASDU from RTU 172.16.3.11 changed active_power 30621.9492 -> 0.0; reactive_power 21071.9004 -> 0.0 (to_zero; quality good=True; sustained=True; verification=verified_observation).
- **A006** (rank `6`, `measurement_step`, `unverified_observation`, +`46.295`s, RTU `172.16.3.12`): line.11: 1 measurement(s) in one ASDU from RTU 172.16.3.12 changed current_to 0.0223176442 -> 0.38878718 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A007** (rank `7`, `measurement_step`, `unverified_observation`, +`70.62`s, RTU `172.16.3.11`): line.10: 1 measurement(s) in one ASDU from RTU 172.16.3.11 changed current_to 0.0235012006 -> 0.308698058 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A008** (rank `8`, `measurement_step`, `unverified_observation`, +`105.755`s, RTU `172.16.3.9`): line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from 0.629656732 -> -0.173746914 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A009** (rank `9`, `measurement_step`, `unverified_observation`, +`140.715`s, RTU `172.16.3.11`): line.11: 1 measurement(s) in one ASDU from RTU 172.16.3.11 changed current_from 0.256064206 -> 0.0757326558 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A010** (rank `10`, `measurement_step`, `unverified_observation`, +`153.424`s, RTU `172.16.3.22`): line.4: 1 measurement(s) in one ASDU from RTU 172.16.3.22 changed current_to 0.278781056 -> -0.111888058 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).

### 2A.2 Behavioral Storylines
#### SL001 — anchors `['A001']` (+`0.733`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A001] load.16:is_connected (CA/IOA=116.10180) reported value 0.0 with COT=3 by RTU 172.16.3.11; prior IEC-104 value in window: not observed (state_report_no_prior_value_in_window; verification=unverified_observation). 1 same-device sequential observation(s) kept off-spine (failed behavioral consistency gate: [['left_not_sustained', 'left_anchor_unverified', 'state_to_measurement_change_mismatch']]).
- **Unverified observation issues**: `{'A001': ['no_prior_state_value_in_window']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Sequential same-entity observations (failed behavioral consistency gate, NOT supported transition)**: R0040 same_entity_sequential_observation: load.16:is_connected (@+0.733s) -> load.16:active_power,reactive_power (@+10.572s); failed_gate=['left_not_sustained', 'left_anchor_unverified', 'state_to_measurement_change_mismatch']
- **Candidate relations (unresolved, time proximity only; 3)**: R0037: -> line.10:active_power_from,reactive_power_from (@+5.161s); R0038: -> bus.13:active_power,reactive_power (@+10.572s); R0039: -> line.10:active_power_to,reactive_power_to (@+10.572s)
- **IPAL time-aligned rows (not independent)**: load.16:connected (temporally_aligned_same_device_ipal_row; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL002 — anchors `['A002']` (+`5.161`s, status=`behavioral_single_anchor`)
- **Reconstructed**: [A002] line.10: 2 measurement(s) in one ASDU from RTU 172.16.2.4 changed active_power_from 30638.1113 -> 0.311625749; reactive_power_from 11038.1484 -> -10043.5742 (level_shift; quality good=True; sustained=True; verification=verified_observation). 1 same-device sequential observation(s) kept off-spine (failed behavioral consistency gate: [['magnitude_ratio_mismatch:active_power', 'magnitude_ratio_mismatch:reactive_power']]).
- **Evidence-supported relations**: none (single anchor)
- **Sequential same-entity observations (failed behavioral consistency gate, NOT supported transition)**: R0042 same_entity_sequential_observation: line.10:active_power_from,reactive_power_from (@+5.161s) -> line.10:active_power_to,reactive_power_to (@+10.572s); failed_gate=['magnitude_ratio_mismatch:active_power', 'magnitude_ratio_mismatch:reactive_power']
- **Candidate relations (unresolved, time proximity only; 3)**: R0041: -> bus.13:active_power,reactive_power (@+10.572s); R0043: -> load.16:active_power,reactive_power (@+10.572s); R0037: load.16:is_connected (@+0.733s) ->
- **IPAL time-aligned rows (not independent)**: line.10:active_power_from,reactive_power_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL003 — anchors `['A003']` (+`10.572`s, status=`behavioral_single_anchor`)
- **Reconstructed**: [A003] bus.13: 2 measurement(s) in one ASDU from RTU 172.16.3.11 changed active_power 30621.0742 -> 0.0; reactive_power 21073.2598 -> 0.0 (to_zero; quality good=True; sustained=True; verification=verified_observation). Co-reported in the same ASDU: line.10:active_power_to,reactive_power_to, load.16:active_power,reactive_power.
- **Evidence-supported relations**: none (single anchor)
- **Co-reported in the same ASDU (shared message, not a device relation)**: line.10:active_power_to,reactive_power_to (A004, R0044), load.16:active_power,reactive_power (A005, R0045)
- **Candidate relations (unresolved, time proximity only; 2)**: R0038: load.16:is_connected (@+0.733s) ->; R0041: line.10:active_power_from,reactive_power_from (@+5.161s) ->
- **IPAL time-aligned rows (not independent)**: bus.13:active_power,reactive_power (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL004 — anchors `['A004']` (+`10.572`s, status=`behavioral_single_anchor`)
- **Reconstructed**: [A004] line.10: 2 measurement(s) in one ASDU from RTU 172.16.3.11 changed active_power_to -30621.9629 -> -0.0137795694; reactive_power_to -17263.7832 -> 3811.06934 (level_shift; quality good=True; sustained=True; verification=verified_observation). 1 same-device sequential observation(s) kept off-spine (failed behavioral consistency gate: [['magnitude_ratio_mismatch:active_power', 'magnitude_ratio_mismatch:reactive_power']]). Co-reported in the same ASDU: bus.13:active_power,reactive_power, load.16:active_power,reactive_power.
- **Evidence-supported relations**: none (single anchor)
- **Sequential same-entity observations (failed behavioral consistency gate, NOT supported transition)**: R0042 same_entity_sequential_observation: line.10:active_power_from,reactive_power_from (@+5.161s) -> line.10:active_power_to,reactive_power_to (@+10.572s); failed_gate=['magnitude_ratio_mismatch:active_power', 'magnitude_ratio_mismatch:reactive_power']
- **Co-reported in the same ASDU (shared message, not a device relation)**: bus.13:active_power,reactive_power (A003, R0044), load.16:active_power,reactive_power (A005, R0046)
- **Candidate relations (unresolved, time proximity only; 1)**: R0039: load.16:is_connected (@+0.733s) ->
- **IPAL time-aligned rows (not independent)**: line.10:active_power_to,reactive_power_to (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL005 — anchors `['A005']` (+`10.572`s, status=`behavioral_single_anchor`)
- **Reconstructed**: [A005] load.16: 2 measurement(s) in one ASDU from RTU 172.16.3.11 changed active_power 30621.9492 -> 0.0; reactive_power 21071.9004 -> 0.0 (to_zero; quality good=True; sustained=True; verification=verified_observation). 1 same-device sequential observation(s) kept off-spine (failed behavioral consistency gate: [['left_not_sustained', 'left_anchor_unverified', 'state_to_measurement_change_mismatch']]). Co-reported in the same ASDU: bus.13:active_power,reactive_power, line.10:active_power_to,reactive_power_to.
- **Evidence-supported relations**: none (single anchor)
- **Sequential same-entity observations (failed behavioral consistency gate, NOT supported transition)**: R0040 same_entity_sequential_observation: load.16:is_connected (@+0.733s) -> load.16:active_power,reactive_power (@+10.572s); failed_gate=['left_not_sustained', 'left_anchor_unverified', 'state_to_measurement_change_mismatch']
- **Co-reported in the same ASDU (shared message, not a device relation)**: bus.13:active_power,reactive_power (A003, R0045), line.10:active_power_to,reactive_power_to (A004, R0046)
- **Candidate relations (unresolved, time proximity only; 1)**: R0043: line.10:active_power_from,reactive_power_from (@+5.161s) ->
- **IPAL time-aligned rows (not independent)**: load.16:active_power,reactive_power (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL006 — anchors `['A006']` (+`46.295`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A006] line.11: 1 measurement(s) in one ASDU from RTU 172.16.3.12 changed current_to 0.0223176442 -> 0.38878718 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A006': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.11:current_to (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL007 — anchors `['A007']` (+`70.62`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A007] line.10: 1 measurement(s) in one ASDU from RTU 172.16.3.11 changed current_to 0.0235012006 -> 0.308698058 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A007': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.10:current_to (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL008 — anchors `['A008']` (+`105.755`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A008] line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from 0.629656732 -> -0.173746914 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A008': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.13:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL009 — anchors `['A009']` (+`140.715`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A009] line.11: 1 measurement(s) in one ASDU from RTU 172.16.3.11 changed current_from 0.256064206 -> 0.0757326558 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A009': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Candidate relations (unresolved, time proximity only; 1)**: R0047: -> line.4:current_to (@+153.424s)
- **IPAL time-aligned rows (not independent)**: line.11:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL010 — anchors `['A010']` (+`153.424`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A010] line.4: 1 measurement(s) in one ASDU from RTU 172.16.3.22 changed current_to 0.278781056 -> -0.111888058 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A010': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Candidate relations (unresolved, time proximity only; 1)**: R0047: line.11:current_from (@+140.715s) ->
- **IPAL time-aligned rows (not independent)**: line.4:current_to (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.

## 2B. Incident Scenario Synthesis (Four-Layer Epistemic Integration)
- **Scenario Status**: `synthesized_consistent`
- **Layer 1 Partition**: `0` supported multi-node chains, `4` verified single-anchor chains, `2` sequential same-entity observations (gate failed), `6` quarantined unverified observations (`1` unverified COT=3 precursor reports).
- **Layer 2 Bundles & Bridges**: `2` source bundles (each counted as `1` container), `0` cross-RTU verified element bridges, `0` same-RTU supported relations (not cross-RTU support), `0` multi-bundle bridged components.
- **Layer 3 Candidate Phases**: `1` candidate scenario phases (all cross-device links kept `unresolved`).
- **Layer 4 Source Dependency Ledger**: `2` IEC-104 ASDU, `0` TCP link, `0` ARP, `0` composite containers across `2` RTU(s) (`['172.16.2.4', '172.16.3.11']`), `2` co-reported same-ASDU points collapsed, mirror vantages `['n302', 'n303']`, `14` IPAL rows excluded (`weight=0`).

### 2B.1 Layer 2 — RTU ASDU Bundles & Verified Element Bridges
- **BND-001** (`+5.161s`, RTU `172.16.2.4`, container=`SRC-ASDU-172.16.2.4|2404|172.16.1.2|53102|2425|0`, independent_sources=`1`): anchors `['A002']` -> `['line.10:active_power_from,reactive_power_from']`.
- **BND-002** (`+10.572s`, RTU `172.16.3.11`, container=`SRC-ASDU-172.16.3.11|2404|172.16.1.2|39462|2431|0`, independent_sources=`1`): anchors `['A003', 'A004', 'A005']` -> `['bus.13:active_power,reactive_power', 'line.10:active_power_to,reactive_power_to', 'load.16:active_power,reactive_power']`.
- **Cross-RTU Verified Element Bridges**: `none`.

### 2B.2 Layer 3 — Candidate Scenario Phases (Cross-Device Links Unresolved)
- **PHS-001** (`+0.733s`..`+10.572s`, profile=`localized_measurement_or_state_observations`): bundles=`['BND-001', 'BND-002']`, verified_bridges=`[]`, sequential_same_device=`['R0040', 'R0042']`, unverified_precursors=`['A001']`, RTUs=`['172.16.2.4', '172.16.3.11']`, ARP=`[]`, unresolved_candidates=`5`.

### 2B.3 Layer 4 — Evidence-Anchored Competing Explanations & Missing Evidence
- **EXP-001** (`local_device_disconnection_with_unverified_prior_state_hypothesis`, status=`unresolved_competing_hypothesis`, causal_status=`not_established`): On load.16, a spontaneous COT=3 state report (A001: load.16:is_connected) preceded a verified measurement drop to zero (A005: load.16:active_power,reactive_power), recorded as sequential observation R0040 because A001 failed ['left_not_sustained', 'left_anchor_unverified', 'state_to_measurement_change_mismatch'].
  - **Anchored by**: `{'verified_anchor_ids': ['A002', 'A003', 'A004', 'A005'], 'sequential_edge_id': 'R0040', 'device_stem': 'load.16', 'evidence_ids': ['EV-597e9017434c21ff', 'EV-825fdd49c3222ec4', 'EV-5aa0d989e898badb']}`
  - **Unverified/candidate links required**: `['A001', 'R0040']`
  - **Alternative comparison**: Assumes the COT=3 report reflects an actual disconnection from a prior connected state (1.0 -> 0.0), which is not provable from in-window IEC-104 traffic alone.
  - **Missing disambiguating evidence**: `['Pre-window IEC-104 state baseline (COT=20) for load.16:is_connected', 'Local RTU load.16 breaker/controller event log']`
- **EXP-002** (`uncommanded_output_drop_with_redundant_state_report_hypothesis`, status=`unresolved_competing_hypothesis`, causal_status=`not_established`): Only the measurement step A005 (load.16:active_power,reactive_power -> 0.0) is a verified transition; the earlier COT=3 report A001 could be a redundant status re-transmission or unverified telemetry frame without a physical state transition.
  - **Anchored by**: `{'verified_anchor_ids': ['A002', 'A003', 'A004', 'A005'], 'device_stem': 'load.16', 'evidence_ids': ['EV-597e9017434c21ff', 'EV-825fdd49c3222ec4', 'EV-5aa0d989e898badb']}`
  - **Alternative comparison**: Relies strictly on the verified measurement step A002 without promoting the unverified COT=3 state report A001.
  - **Missing disambiguating evidence**: `['Out-of-band physical meter for load.16', 'Pre-window IEC-104 state history prior to background_start']`

## 2. Key Findings & Reconstructed Storylines (Contiguous Directed Spines)

## 3. Observed Network & Electrical Impact (Epistemically Stratified)
### 3.1 Verified Same-Device Measurement/State Transitions (Consistency Gate Passed)
- No post-command device transition passed all pre/post and target consistency checks.

### 3.2 Protocol State Reports Observed Without Verified Transition (Value Undecoded or No Pre-Baseline)
- None.

### 3.3 Candidate Cross-Entity Co-occurring Changes (Unresolved Hypotheses, Not Causal Proof)
- [SL001 / R0037 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): line.10:active_power_from,reactive_power_from (BA002) at 1742942532.3617 after BA001 (0 <= dt (4.428s) <= 15.0s) [src_ev=EV-597e9017434c21ff; dst_ev=EV-1f5b15a73b56d71e, EV-a2cc2817cfa582f8].
- [SL001 / R0038 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): bus.13:active_power,reactive_power (BA003) at 1742942537.7727 after BA001 (0 <= dt (9.839s) <= 15.0s) [src_ev=EV-597e9017434c21ff; dst_ev=EV-e06a1a48c57981b6, EV-5d28a6829af845ef].
- [SL001 / R0039 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): line.10:active_power_to,reactive_power_to (BA004) at 1742942537.7727 after BA001 (0 <= dt (9.839s) <= 15.0s) [src_ev=EV-597e9017434c21ff; dst_ev=EV-57aab852575fae0f, EV-35d4dfd702e1ed47].
- [SL002 / R0041 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): bus.13:active_power,reactive_power (BA003) at 1742942537.7727 after BA002 (0 <= dt (5.411s) <= 15.0s) [src_ev=EV-1f5b15a73b56d71e, EV-a2cc2817cfa582f8; dst_ev=EV-e06a1a48c57981b6, EV-5d28a6829af845ef].
- [SL002 / R0043 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): load.16:active_power,reactive_power (BA005) at 1742942537.7727 after BA002 (0 <= dt (5.411s) <= 15.0s) [src_ev=EV-1f5b15a73b56d71e, EV-a2cc2817cfa582f8; dst_ev=EV-825fdd49c3222ec4, EV-5aa0d989e898badb].
- [SL009 / R0047 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): line.4:current_to (BA010) at 1742942680.6241 after BA009 (0 <= dt (12.709s) <= 15.0s) [src_ev=EV-fc6245f9e3638b27, EV-e90a8967c490f24c; dst_ev=EV-131109a10063482d, EV-52e49ef0ff4b0864].

## 4. Alternative Explanations & Competing Hypotheses
- **[SL001 | competing_cross_entity_cooccurrences | status=`unresolved`]**: Multiple distinct grid measurements (line.10:active_power_from,reactive_power_from, bus.13:active_power,reactive_power, line.10:active_power_to,reactive_power_to) changed within the time horizon after load.16:is_connected. Without an independent physical topology/power-flow model in the loop, these remain competing unresolved temporal co-occurrences rather than confirmed causal effects.
- **[SL002 | competing_cross_entity_cooccurrences | status=`unresolved`]**: Multiple distinct grid measurements (bus.13:active_power,reactive_power, load.16:active_power,reactive_power) changed within the time horizon after line.10:active_power_from,reactive_power_from. Without an independent physical topology/power-flow model in the loop, these remain competing unresolved temporal co-occurrences rather than confirmed causal effects.

## 5. Unresolved Questions, Evidence Gaps & Unattached Observations
- **Unattached Observations (`36` nodes not on a storyline spine)**:
  - `TL005` (`1742942527.2146`, `network`, `communication`): `172.16.3.23:2404->172.16.1.2:60408/TCP` (`not_on_confirmed_storyline_spine`) [`EV-cf0af913d1516465, EV-8845e3b207c616f3`]
  - `TL001` (`1742942527.7320`, `network`, `communication`): `172.16.3.16:2404->172.16.1.2:41276/TCP` (`not_on_confirmed_storyline_spine`) [`EV-29adf895f4651535, EV-0659ed5b88a2d4f9`]
  - `TL002` (`1742942527.7360`, `network`, `communication`): `172.16.1.2:41276->172.16.3.16:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-a19a47ba80fa69cc, EV-45f923b5c2d7130d`]
  - `TL019` (`1742942527.8582`, `electrical`, `electrical_change`): `line.13:current_to` (`isolated_no_graph_edge`) [`EV-513ca41534f0600b, EV-04229e5979fb5b23`]
  - `TL003` (`1742942527.9334`, `network`, `communication`): `172.16.3.11:2404->172.16.1.2:39462/TCP` (`not_on_confirmed_storyline_spine`) [`EV-fc87ca9742ccab02, EV-cc423ad4b1ba0414`]
  - `TL004` (`1742942527.9374`, `network`, `communication`): `172.16.1.2:39462->172.16.3.11:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-50458e2e3d103a31, EV-055827b0f878b4fb`]
  - `TL006` (`1742942528.1323`, `network`, `communication`): `172.16.1.2:47728->172.16.3.20:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-468bb94fa22635e0, EV-9c9e75e8c864a498`]
  - `TL007` (`1742942528.1924`, `network`, `communication`): `172.16.3.20:2404->172.16.1.2:47728/TCP` (`not_on_confirmed_storyline_spine`) [`EV-d4ccfdb447f2c8c3, EV-05d260eb6b5ee8be`]
  - `BI001` (`1742942528.8582`, `electrical`, `ipal_correspondence`): `load.16:connected` (`not_on_confirmed_storyline_spine`) [`EV-5d1781a7b5befef3`]
  - `TL008` (`1742942528.8590`, `network`, `communication`): `172.16.1.2:43150->172.16.3.15:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-ad00026fa120bb1a, EV-539c08a9876e3546`]
