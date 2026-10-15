# Evidence-Grounded Incident Reconstruction Report

- **Report Status**: `quality_consistent`
- **Quality & Behavioral Consistency (`quality_consistency.json`)**: `consistent`
- **Evidence Lineage Audit (`lineage_consistency.json`)**: `consistent`

- **Incident Window**: `1742939182.2377434` to `1742939676.7295613`
- **Reconstructed IEC-104 Transactions**: `0`
- **Reconstructed Event Storylines**: `14`
- **Verified Same-Device Transitions (Consistency Gate Passed)**: `0`
- **Unverified Protocol State Reports (Value Undecoded or No Pre-Baseline)**: `0`
- **LLM Claim Verifier Output (Separate from Graph Gate)**: `0` verified, `0` withheld

## 1. Incident Sequence & Protocol Transactions
- No IEC-104 control transactions were observed in this window.

## 2A. Behavioral Incident Reconstruction (No Control Command)
- Method: `evidence_anchor_discovery`. Inputs not used: `['official event labels', 'attack type', 'malicious flags', 'physical.zip']`. Control objects in window: `0`.
- `14` event anchors (`0` verified, `14` unverified), `14` behavioral storylines (`0` with corroborated multi-ASDU transitions, `0` verified single-anchor, `14` unverified observations), `2` sequential same-entity observations (gate failed), `2` unresolved cross-device branches.

### 2A.1 Event Anchors (by time)
- **A001** (rank `1`, `measurement_step`, `unverified_observation`, +`69.127`s, RTU `172.16.3.12`): line.11: 1 measurement(s) in one ASDU from RTU 172.16.3.12 changed current_to 0.174691111 -> 0.393390059 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A002** (rank `2`, `measurement_step`, `unverified_observation`, +`96.255`s, RTU `172.16.3.22`): line.4: 1 measurement(s) in one ASDU from RTU 172.16.3.22 changed current_to -0.0474878661 -> -0.406910092 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A003** (rank `3`, `measurement_step`, `unverified_observation`, +`118.667`s, RTU `172.16.3.9`): line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from -0.243443713 -> 0.434116423 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A004** (rank `4`, `measurement_step`, `unverified_observation`, +`133.489`s, RTU `172.16.3.16`): line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.16 changed current_to -0.300968766 -> 0.145832896 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A005** (rank `5`, `measurement_step`, `unverified_observation`, +`158.646`s, RTU `172.16.3.9`): line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from 0.0554669499 -> 0.756692052 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A006** (rank `6`, `measurement_step`, `unverified_observation`, +`268.766`s, RTU `172.16.3.18`): line.4: 1 measurement(s) in one ASDU from RTU 172.16.3.18 changed current_from 0.421496272 -> 1.06674421 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A007** (rank `7`, `measurement_step`, `unverified_observation`, +`295.037`s, RTU `172.16.3.11`): line.11: 1 measurement(s) in one ASDU from RTU 172.16.3.11 changed current_from -0.0439523607 -> 0.0815084204 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A008** (rank `8`, `measurement_step`, `unverified_observation`, +`328.727`s, RTU `172.16.3.9`): line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from 0.0898023695 -> 0.347525179 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A009** (rank `9`, `measurement_step`, `unverified_observation`, +`369.408`s, RTU `172.16.3.12`): line.11: 1 measurement(s) in one ASDU from RTU 172.16.3.12 changed current_to 0.0398311019 -> -0.185259432 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A010** (rank `10`, `measurement_step`, `unverified_observation`, +`428.82`s, RTU `172.16.3.9`): line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from 0.666610837 -> 0.0897212923 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A011** (rank `11`, `measurement_step`, `unverified_observation`, +`435.098`s, RTU `172.16.3.11`): line.11: 1 measurement(s) in one ASDU from RTU 172.16.3.11 changed current_from 0.0329138376 -> 0.315142423 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A012** (rank `12`, `measurement_step`, `unverified_observation`, +`456.444`s, RTU `172.16.3.22`): line.4: 1 measurement(s) in one ASDU from RTU 172.16.3.22 changed current_to 0.398810476 -> -0.1549422 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A013** (rank `13`, `measurement_step`, `unverified_observation`, +`458.827`s, RTU `172.16.3.9`): line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from 0.103873417 -> 0.525335431 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A014** (rank `14`, `measurement_step`, `unverified_observation`, +`473.698`s, RTU `172.16.3.16`): line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.16 changed current_to 0.0386401005 -> -0.125205368 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).

### 2A.2 Behavioral Storylines
#### SL001 — anchors `['A001']` (+`69.127`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A001] line.11: 1 measurement(s) in one ASDU from RTU 172.16.3.12 changed current_to 0.174691111 -> 0.393390059 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A001': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.11:current_to (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL002 — anchors `['A002']` (+`96.255`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A002] line.4: 1 measurement(s) in one ASDU from RTU 172.16.3.22 changed current_to -0.0474878661 -> -0.406910092 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A002': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.4:current_to (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL003 — anchors `['A003']` (+`118.667`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A003] line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from -0.243443713 -> 0.434116423 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']). 1 same-device sequential observation(s) kept off-spine (failed behavioral consistency gate: [['left_not_sustained', 'right_not_sustained', 'left_anchor_unverified', 'right_anchor_unverified', 'transition_intervals_disjoint', 'magnitude_direction_mismatch:current']]).
- **Unverified observation issues**: `{'A003': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Sequential same-entity observations (failed behavioral consistency gate, NOT supported transition)**: R0037 same_entity_sequential_observation: line.13:current_from (@+118.667s) -> line.13:current_to (@+133.489s); failed_gate=['left_not_sustained', 'right_not_sustained', 'left_anchor_unverified', 'right_anchor_unverified', 'transition_intervals_disjoint', 'magnitude_direction_mismatch:current']
- **IPAL time-aligned rows (not independent)**: line.13:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL004 — anchors `['A004']` (+`133.489`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A004] line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.16 changed current_to -0.300968766 -> 0.145832896 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']). 1 same-device sequential observation(s) kept off-spine (failed behavioral consistency gate: [['left_not_sustained', 'right_not_sustained', 'left_anchor_unverified', 'right_anchor_unverified', 'transition_intervals_disjoint', 'magnitude_direction_mismatch:current']]).
- **Unverified observation issues**: `{'A004': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Sequential same-entity observations (failed behavioral consistency gate, NOT supported transition)**: R0037 same_entity_sequential_observation: line.13:current_from (@+118.667s) -> line.13:current_to (@+133.489s); failed_gate=['left_not_sustained', 'right_not_sustained', 'left_anchor_unverified', 'right_anchor_unverified', 'transition_intervals_disjoint', 'magnitude_direction_mismatch:current']
- **IPAL time-aligned rows (not independent)**: line.13:current_to (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL005 — anchors `['A005']` (+`158.646`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A005] line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from 0.0554669499 -> 0.756692052 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A005': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.13:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL006 — anchors `['A006']` (+`268.766`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A006] line.4: 1 measurement(s) in one ASDU from RTU 172.16.3.18 changed current_from 0.421496272 -> 1.06674421 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A006': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.4:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL007 — anchors `['A007']` (+`295.037`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A007] line.11: 1 measurement(s) in one ASDU from RTU 172.16.3.11 changed current_from -0.0439523607 -> 0.0815084204 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A007': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.11:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL008 — anchors `['A008']` (+`328.727`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A008] line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from 0.0898023695 -> 0.347525179 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A008': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.13:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL009 — anchors `['A009']` (+`369.408`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A009] line.11: 1 measurement(s) in one ASDU from RTU 172.16.3.12 changed current_to 0.0398311019 -> -0.185259432 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A009': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.11:current_to (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL010 — anchors `['A010']` (+`428.82`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A010] line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from 0.666610837 -> 0.0897212923 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A010': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Candidate relations (unresolved, time proximity only; 1)**: R0038: -> line.11:current_from (@+435.098s)
- **IPAL time-aligned rows (not independent)**: line.13:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL011 — anchors `['A011']` (+`435.098`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A011] line.11: 1 measurement(s) in one ASDU from RTU 172.16.3.11 changed current_from 0.0329138376 -> 0.315142423 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A011': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Candidate relations (unresolved, time proximity only; 1)**: R0038: line.13:current_from (@+428.82s) ->
- **IPAL time-aligned rows (not independent)**: line.11:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL012 — anchors `['A012']` (+`456.444`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A012] line.4: 1 measurement(s) in one ASDU from RTU 172.16.3.22 changed current_to 0.398810476 -> -0.1549422 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A012': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Candidate relations (unresolved, time proximity only; 1)**: R0039: -> line.13:current_from (@+458.827s)
- **IPAL time-aligned rows (not independent)**: line.4:current_to (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL013 — anchors `['A013']` (+`458.827`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A013] line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from 0.103873417 -> 0.525335431 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']). 1 same-device sequential observation(s) kept off-spine (failed behavioral consistency gate: [['left_not_sustained', 'right_not_sustained', 'left_anchor_unverified', 'right_anchor_unverified', 'transition_intervals_disjoint']]).
- **Unverified observation issues**: `{'A013': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Sequential same-entity observations (failed behavioral consistency gate, NOT supported transition)**: R0040 same_entity_sequential_observation: line.13:current_from (@+458.827s) -> line.13:current_to (@+473.698s); failed_gate=['left_not_sustained', 'right_not_sustained', 'left_anchor_unverified', 'right_anchor_unverified', 'transition_intervals_disjoint']
- **Candidate relations (unresolved, time proximity only; 1)**: R0039: line.4:current_to (@+456.444s) ->
- **IPAL time-aligned rows (not independent)**: line.13:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL014 — anchors `['A014']` (+`473.698`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A014] line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.16 changed current_to 0.0386401005 -> -0.125205368 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']). 1 same-device sequential observation(s) kept off-spine (failed behavioral consistency gate: [['left_not_sustained', 'right_not_sustained', 'left_anchor_unverified', 'right_anchor_unverified', 'transition_intervals_disjoint']]).
- **Unverified observation issues**: `{'A014': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Sequential same-entity observations (failed behavioral consistency gate, NOT supported transition)**: R0040 same_entity_sequential_observation: line.13:current_from (@+458.827s) -> line.13:current_to (@+473.698s); failed_gate=['left_not_sustained', 'right_not_sustained', 'left_anchor_unverified', 'right_anchor_unverified', 'transition_intervals_disjoint']
- **IPAL time-aligned rows (not independent)**: line.13:current_to (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.

## 2B. Incident Scenario Synthesis (Four-Layer Epistemic Integration)
- **Scenario Status**: `synthesized_consistent`
- **Layer 1 Partition**: `0` supported multi-node chains, `0` verified single-anchor chains, `2` sequential same-entity observations (gate failed), `14` quarantined unverified observations (`0` unverified COT=3 precursor reports).
- **Layer 2 Bundles & Bridges**: `0` source bundles (each counted as `1` container), `0` cross-RTU verified element bridges, `0` same-RTU supported relations (not cross-RTU support), `0` multi-bundle bridged components.
- **Layer 3 Candidate Phases**: `0` candidate scenario phases (all cross-device links kept `unresolved`).
- **Layer 4 Source Dependency Ledger**: `0` IEC-104 ASDU, `0` TCP link, `0` ARP, `0` composite containers across `0` RTU(s) (`[]`), `0` co-reported same-ASDU points collapsed, mirror vantages `[]`, `14` IPAL rows excluded (`weight=0`).

### 2B.3 Layer 4 — Evidence-Anchored Competing Explanations & Missing Evidence
- **EXP-001** (`local_device_disconnection_with_unverified_prior_state_hypothesis`, status=`unresolved_competing_hypothesis`, causal_status=`not_established`): On line.13, a spontaneous COT=3 state report (A003: line.13:current_from) preceded a verified measurement drop to zero (A004: line.13:current_to), recorded as sequential observation R0037 because A003 failed ['left_not_sustained', 'right_not_sustained', 'left_anchor_unverified', 'right_anchor_unverified', 'transition_intervals_disjoint', 'magnitude_direction_mismatch:current'].
  - **Anchored by**: `{'verified_anchor_ids': [], 'sequential_edge_id': 'R0037', 'device_stem': 'line.13', 'evidence_ids': ['EV-c5a1d0edc1f56808', 'EV-ce3ffd677fa3c9cc', 'EV-37b12ca1ac085502', 'EV-0123736e2c0a9532']}`
  - **Unverified/candidate links required**: `['A003', 'R0037']`
  - **Alternative comparison**: Assumes the COT=3 report reflects an actual disconnection from a prior connected state (1.0 -> 0.0), which is not provable from in-window IEC-104 traffic alone.
  - **Missing disambiguating evidence**: `['Pre-window IEC-104 state baseline (COT=20) for line.13:current_from', 'Local RTU line.13 breaker/controller event log']`
- **EXP-002** (`uncommanded_output_drop_with_redundant_state_report_hypothesis`, status=`unresolved_competing_hypothesis`, causal_status=`not_established`): Only the measurement step A004 (line.13:current_to -> 0.0) is a verified transition; the earlier COT=3 report A003 could be a redundant status re-transmission or unverified telemetry frame without a physical state transition.
  - **Anchored by**: `{'verified_anchor_ids': [], 'device_stem': 'line.13', 'evidence_ids': ['EV-c5a1d0edc1f56808', 'EV-ce3ffd677fa3c9cc', 'EV-37b12ca1ac085502', 'EV-0123736e2c0a9532']}`
  - **Alternative comparison**: Relies strictly on the verified measurement step A002 without promoting the unverified COT=3 state report A001.
  - **Missing disambiguating evidence**: `['Out-of-band physical meter for line.13', 'Pre-window IEC-104 state history prior to background_start']`

## 2. Key Findings & Reconstructed Storylines (Contiguous Directed Spines)

## 3. Observed Network & Electrical Impact (Epistemically Stratified)
### 3.1 Verified Same-Device Measurement/State Transitions (Consistency Gate Passed)
- No post-command device transition passed all pre/post and target consistency checks.

### 3.2 Protocol State Reports Observed Without Verified Transition (Value Undecoded or No Pre-Baseline)
- None.

### 3.3 Candidate Cross-Entity Co-occurring Changes (Unresolved Hypotheses, Not Causal Proof)
- [SL010 / R0038 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): line.11:current_from (BA011) at 1742939617.336 after BA010 (0 <= dt (6.278s) <= 15.0s) [src_ev=EV-9c5247c692541532, EV-c5cbed9b545e4e45; dst_ev=EV-59ba1c2d45b4f7e3, EV-fa8208eb4c8609ab].
- [SL012 / R0039 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): line.13:current_from (BA013) at 1742939641.065 after BA012 (0 <= dt (2.383s) <= 15.0s) [src_ev=EV-1bb1bb61d1da857b, EV-da90670f086501b6; dst_ev=EV-0ca783e7bc46f4a4, EV-93e0a848cf45dfb2].

## 4. Alternative Explanations & Competing Hypotheses
- No competing multi-branch hypotheses triggered in this window.

## 5. Unresolved Questions, Evidence Gaps & Unattached Observations
- **Unattached Observations (`38` nodes not on a storyline spine)**:
  - `TL001` (`1742939182.2605`, `network`, `communication`): `172.16.3.26:2404->172.16.1.2:54802/TCP` (`not_on_confirmed_storyline_spine`) [`EV-682ea6f639276f63, EV-c084c3a3ed4c4d6b`]
  - `TL002` (`1742939182.2645`, `network`, `communication`): `172.16.1.2:54802->172.16.3.26:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-0b5f44ec48efc8fd, EV-d059751c5fb49f50`]
  - `TL003` (`1742939182.8177`, `network`, `communication`): `172.16.3.24:2404->172.16.1.2:47958/TCP` (`not_on_confirmed_storyline_spine`) [`EV-d68400c9e415e54b, EV-b891124735a2d0c1`]
  - `TL004` (`1742939182.8217`, `network`, `communication`): `172.16.1.2:47958->172.16.3.24:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-5687bd5e6a777bab, EV-4e9c290eff611619`]
  - `TL005` (`1742939182.8367`, `network`, `communication`): `172.16.3.23:2404->172.16.1.2:60408/TCP` (`not_on_confirmed_storyline_spine`) [`EV-a7ba338cbf9c4cb7, EV-2177c2495078fe1d`]
  - `TL006` (`1742939182.8407`, `network`, `communication`): `172.16.1.2:60408->172.16.3.23:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-c0fedae96c30ab00, EV-982a7c77f4c20e62`]
  - `TL020` (`1742939182.8582`, `electrical`, `electrical_change`): `line.9:active_power_to` (`isolated_no_graph_edge`) [`EV-fd9cdaa77b38c138, EV-d6790e0be7dacd68`]
  - `TL007` (`1742939184.6685`, `network`, `communication`): `172.16.3.15:2404->172.16.1.2:43150/TCP` (`not_on_confirmed_storyline_spine`) [`EV-0a445865b62f8ab0, EV-b5a15bf72548418d`]
  - `TL008` (`1742939184.6725`, `network`, `communication`): `172.16.1.2:43150->172.16.3.15:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-078762ac590feebf, EV-c28e4bbca4010d43`]
  - `TL019` (`1742939185.8582`, `electrical`, `electrical_change`): `line.13:current_to` (`not_on_confirmed_storyline_spine`) [`EV-706025e797bdc34f, EV-b4878089e53a02ad`]
