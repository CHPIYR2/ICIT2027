# Evidence-Grounded Incident Reconstruction Report

- **Report Status**: `quality_consistent`
- **Quality & Behavioral Consistency (`quality_consistency.json`)**: `consistent`
- **Evidence Lineage Audit (`lineage_consistency.json`)**: `consistent`

- **Incident Window**: `1742946908.246947` to `1742947502.816791`
- **Reconstructed IEC-104 Transactions**: `0`
- **Reconstructed Event Storylines**: `11`
- **Verified Same-Device Transitions (Consistency Gate Passed)**: `0`
- **Unverified Protocol State Reports (Value Undecoded or No Pre-Baseline)**: `0`
- **LLM Claim Verifier Output (Separate from Graph Gate)**: `0` verified, `0` withheld

## 1. Incident Sequence & Protocol Transactions
- No IEC-104 control transactions were observed in this window.

## 2A. Behavioral Incident Reconstruction (No Control Command)
- Method: `evidence_anchor_discovery`. Inputs not used: `['official event labels', 'attack type', 'malicious flags', 'physical.zip']`. Control objects in window: `0`.
- `11` event anchors (`1` verified, `10` unverified), `11` behavioral storylines (`0` with corroborated multi-ASDU transitions, `1` verified single-anchor, `10` unverified observations), `1` sequential same-entity observations (gate failed), `2` unresolved cross-device branches.

### 2A.1 Event Anchors (by time)
- **A001** (rank `1`, `arp_activity_increase`, `verified_observation`, +`2.708`s, RTU `None`): ARP from 172.16.3.28: 295 packets in window (0 requests, 295 replies) to ['172.16.3.13']; 0 in background (verification=verified_observation).
- **A002** (rank `2`, `measurement_step`, `unverified_observation`, +`122.474`s, RTU `172.16.3.11`): line.10: 1 measurement(s) in one ASDU from RTU 172.16.3.11 changed current_to 0.898967147 -> 0.433943003 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A003** (rank `3`, `measurement_step`, `unverified_observation`, +`148.085`s, RTU `172.16.3.12`): line.11: 1 measurement(s) in one ASDU from RTU 172.16.3.12 changed current_to -0.0248276796 -> 0.290755123 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A004** (rank `4`, `measurement_step`, `unverified_observation`, +`167.476`s, RTU `172.16.3.18`): line.4: 1 measurement(s) in one ASDU from RTU 172.16.3.18 changed current_from 0.473995298 -> 1.14122808 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A005** (rank `5`, `measurement_step`, `unverified_observation`, +`292.578`s, RTU `172.16.3.11`): line.11: 1 measurement(s) in one ASDU from RTU 172.16.3.11 changed current_from -0.0605630055 -> 0.261926204 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A006** (rank `6`, `measurement_step`, `unverified_observation`, +`317.021`s, RTU `172.16.2.4`): line.10: 1 measurement(s) in one ASDU from RTU 172.16.2.4 changed current_from -0.030326616 -> 0.458204269 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A007** (rank `7`, `measurement_step`, `unverified_observation`, +`342.585`s, RTU `172.16.3.11`): line.11: 1 measurement(s) in one ASDU from RTU 172.16.3.11 changed current_from 0.0550413318 -> 0.26098001 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A008** (rank `8`, `measurement_step`, `unverified_observation`, +`347.628`s, RTU `172.16.3.9`): line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from 0.496662319 -> 0.14489311 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A009** (rank `9`, `measurement_step`, `unverified_observation`, +`348.213`s, RTU `172.16.3.12`): line.11: 1 measurement(s) in one ASDU from RTU 172.16.3.12 changed current_to -0.0478337966 -> -0.447272241 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A010** (rank `10`, `measurement_step`, `unverified_observation`, +`477.187`s, RTU `172.16.2.4`): line.10: 1 measurement(s) in one ASDU from RTU 172.16.2.4 changed current_from 0.209866717 -> 0.543748975 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A011** (rank `11`, `measurement_step`, `unverified_observation`, +`492.721`s, RTU `172.16.3.11`): line.10: 1 measurement(s) in one ASDU from RTU 172.16.3.11 changed current_to 0.376781285 -> 1.00972223 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).

### 2A.2 Behavioral Storylines
#### SL001 — anchors `['A001']` (+`2.708`s, status=`behavioral_single_anchor`)
- **Reconstructed**: [A001] ARP from 172.16.3.28: 295 packets in window (0 requests, 295 replies) to ['172.16.3.13']; 0 in background (verification=verified_observation).
- **Evidence-supported relations**: none (single anchor)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL002 — anchors `['A002']` (+`122.474`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A002] line.10: 1 measurement(s) in one ASDU from RTU 172.16.3.11 changed current_to 0.898967147 -> 0.433943003 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A002': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.10:current_to (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL003 — anchors `['A003']` (+`148.085`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A003] line.11: 1 measurement(s) in one ASDU from RTU 172.16.3.12 changed current_to -0.0248276796 -> 0.290755123 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A003': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.11:current_to (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL004 — anchors `['A004']` (+`167.476`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A004] line.4: 1 measurement(s) in one ASDU from RTU 172.16.3.18 changed current_from 0.473995298 -> 1.14122808 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A004': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.4:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL005 — anchors `['A005']` (+`292.578`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A005] line.11: 1 measurement(s) in one ASDU from RTU 172.16.3.11 changed current_from -0.0605630055 -> 0.261926204 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A005': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.11:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL006 — anchors `['A006']` (+`317.021`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A006] line.10: 1 measurement(s) in one ASDU from RTU 172.16.2.4 changed current_from -0.030326616 -> 0.458204269 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A006': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.10:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL007 — anchors `['A007']` (+`342.585`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A007] line.11: 1 measurement(s) in one ASDU from RTU 172.16.3.11 changed current_from 0.0550413318 -> 0.26098001 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']). 1 same-device sequential observation(s) kept off-spine (failed behavioral consistency gate: [['left_not_sustained', 'right_not_sustained', 'left_anchor_unverified', 'right_anchor_unverified']]).
- **Unverified observation issues**: `{'A007': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Sequential same-entity observations (failed behavioral consistency gate, NOT supported transition)**: R0037 same_entity_sequential_observation: line.11:current_from (@+342.585s) -> line.11:current_to (@+348.213s); failed_gate=['left_not_sustained', 'right_not_sustained', 'left_anchor_unverified', 'right_anchor_unverified']
- **Candidate relations (unresolved, time proximity only; 1)**: R0036: -> line.13:current_from (@+347.628s)
- **IPAL time-aligned rows (not independent)**: line.11:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL008 — anchors `['A008']` (+`347.628`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A008] line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from 0.496662319 -> 0.14489311 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A008': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Candidate relations (unresolved, time proximity only; 2)**: R0038: -> line.11:current_to (@+348.213s); R0036: line.11:current_from (@+342.585s) ->
- **IPAL time-aligned rows (not independent)**: line.13:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL009 — anchors `['A009']` (+`348.213`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A009] line.11: 1 measurement(s) in one ASDU from RTU 172.16.3.12 changed current_to -0.0478337966 -> -0.447272241 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']). 1 same-device sequential observation(s) kept off-spine (failed behavioral consistency gate: [['left_not_sustained', 'right_not_sustained', 'left_anchor_unverified', 'right_anchor_unverified']]).
- **Unverified observation issues**: `{'A009': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Sequential same-entity observations (failed behavioral consistency gate, NOT supported transition)**: R0037 same_entity_sequential_observation: line.11:current_from (@+342.585s) -> line.11:current_to (@+348.213s); failed_gate=['left_not_sustained', 'right_not_sustained', 'left_anchor_unverified', 'right_anchor_unverified']
- **Candidate relations (unresolved, time proximity only; 1)**: R0038: line.13:current_from (@+347.628s) ->
- **IPAL time-aligned rows (not independent)**: line.11:current_to (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL010 — anchors `['A010']` (+`477.187`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A010] line.10: 1 measurement(s) in one ASDU from RTU 172.16.2.4 changed current_from 0.209866717 -> 0.543748975 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A010': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.10:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL011 — anchors `['A011']` (+`492.721`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A011] line.10: 1 measurement(s) in one ASDU from RTU 172.16.3.11 changed current_to 0.376781285 -> 1.00972223 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A011': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.10:current_to (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.

## 2B. Incident Scenario Synthesis (Four-Layer Epistemic Integration)
- **Scenario Status**: `synthesized_consistent`
- **Layer 1 Partition**: `0` supported multi-node chains, `1` verified single-anchor chains, `1` sequential same-entity observations (gate failed), `10` quarantined unverified observations (`0` unverified COT=3 precursor reports).
- **Layer 2 Bundles & Bridges**: `1` source bundles (each counted as `1` container), `0` cross-RTU verified element bridges, `0` same-RTU supported relations (not cross-RTU support), `0` multi-bundle bridged components.
- **Layer 3 Candidate Phases**: `1` candidate scenario phases (all cross-device links kept `unresolved`).
- **Layer 4 Source Dependency Ledger**: `0` IEC-104 ASDU, `0` TCP link, `1` ARP, `0` composite containers across `0` RTU(s) (`[]`), `0` co-reported same-ASDU points collapsed, mirror vantages `[]`, `10` IPAL rows excluded (`weight=0`).

### 2B.1 Layer 2 — RTU ASDU Bundles & Verified Element Bridges
- **BND-001** (`+2.708s`, RTU `None`, container=`SRC-ARP_ACTIVITY_INCREASE-172.16.3.28/ARP`, independent_sources=`1`): anchors `['A001']` -> `['172.16.3.28/ARP']`.
- **Cross-RTU Verified Element Bridges**: `none`.

### 2B.2 Layer 3 — Candidate Scenario Phases (Cross-Device Links Unresolved)
- **PHS-001** (`+2.708s`..`+590.738s`, profile=`localized_measurement_or_state_observations`): bundles=`['BND-001']`, verified_bridges=`[]`, sequential_same_device=`[]`, unverified_precursors=`[]`, RTUs=`[]`, ARP=`[{'anchor_id': 'A001', 'host_ip': '172.16.3.28', 'packet_count': 295, 'targets': {'172.16.3.13': 295}, 'target_first_seen': {'172.16.3.13': 1742946910.954899}, 'arp_target_overlap_rtu_ips': []}]`, unresolved_candidates=`0`.

### 2B.3 Layer 4 — Evidence-Anchored Competing Explanations & Missing Evidence
- **EXP-001** (`local_device_disconnection_with_unverified_prior_state_hypothesis`, status=`unresolved_competing_hypothesis`, causal_status=`not_established`): On line.11, a spontaneous COT=3 state report (A007: line.11:current_from) preceded a verified measurement drop to zero (A009: line.11:current_to), recorded as sequential observation R0037 because A007 failed ['left_not_sustained', 'right_not_sustained', 'left_anchor_unverified', 'right_anchor_unverified'].
  - **Anchored by**: `{'verified_anchor_ids': ['A001'], 'sequential_edge_id': 'R0037', 'device_stem': 'line.11', 'evidence_ids': ['EV-807e123964b4b09c', 'EV-14074831fa6d594e', 'EV-ef281e3ecb667415', 'EV-491983d8dd5ea8a5']}`
  - **Unverified/candidate links required**: `['A007', 'R0037']`
  - **Alternative comparison**: Assumes the COT=3 report reflects an actual disconnection from a prior connected state (1.0 -> 0.0), which is not provable from in-window IEC-104 traffic alone.
  - **Missing disambiguating evidence**: `['Pre-window IEC-104 state baseline (COT=20) for line.11:current_from', 'Local RTU line.11 breaker/controller event log']`
- **EXP-002** (`uncommanded_output_drop_with_redundant_state_report_hypothesis`, status=`unresolved_competing_hypothesis`, causal_status=`not_established`): Only the measurement step A009 (line.11:current_to -> 0.0) is a verified transition; the earlier COT=3 report A007 could be a redundant status re-transmission or unverified telemetry frame without a physical state transition.
  - **Anchored by**: `{'verified_anchor_ids': ['A001'], 'device_stem': 'line.11', 'evidence_ids': ['EV-807e123964b4b09c', 'EV-14074831fa6d594e', 'EV-ef281e3ecb667415', 'EV-491983d8dd5ea8a5']}`
  - **Alternative comparison**: Relies strictly on the verified measurement step A002 without promoting the unverified COT=3 state report A001.
  - **Missing disambiguating evidence**: `['Out-of-band physical meter for line.11', 'Pre-window IEC-104 state history prior to background_start']`

## 2. Key Findings & Reconstructed Storylines (Contiguous Directed Spines)

## 3. Observed Network & Electrical Impact (Epistemically Stratified)
### 3.1 Verified Same-Device Measurement/State Transitions (Consistency Gate Passed)
- No post-command device transition passed all pre/post and target consistency checks.

### 3.2 Protocol State Reports Observed Without Verified Transition (Value Undecoded or No Pre-Baseline)
- None.

### 3.3 Candidate Cross-Entity Co-occurring Changes (Unresolved Hypotheses, Not Causal Proof)
- [SL007 / R0036 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): line.13:current_from (BA008) at 1742947255.8749 after BA007 (0 <= dt (5.043s) <= 15.0s) [src_ev=EV-807e123964b4b09c, EV-14074831fa6d594e; dst_ev=EV-a258107d91e5428e, EV-cab5bdad66c25188].
- [SL008 / R0038 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): line.11:current_to (BA009) at 1742947256.4596 after BA008 (0 <= dt (0.585s) <= 15.0s) [src_ev=EV-a258107d91e5428e, EV-cab5bdad66c25188; dst_ev=EV-ef281e3ecb667415, EV-491983d8dd5ea8a5].

## 4. Alternative Explanations & Competing Hypotheses
- No competing multi-branch hypotheses triggered in this window.

## 5. Unresolved Questions, Evidence Gaps & Unattached Observations
- **Evidence Gap**: `{"scope": "cross_vantage_payload_conflicts", "count": 54}`
- **Unattached Observations (`34` nodes not on a storyline spine)**:
  - `TL001` (`1742946908.9495`, `network`, `communication`): `172.16.3.20:2404->172.16.1.2:47728/TCP` (`not_on_confirmed_storyline_spine`) [`EV-94de05d866007d41, EV-f876831986a84704`]
  - `TL002` (`1742946908.9535`, `network`, `communication`): `172.16.1.2:47728->172.16.3.20:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-d6d9da3d369f9b81, EV-9210deb6c8b5d158`]
  - `TL003` (`1742946909.7926`, `network`, `communication`): `172.16.3.15:2404->172.16.1.2:43150/TCP` (`not_on_confirmed_storyline_spine`) [`EV-5903e5031a3e2c96, EV-d446d8d55741576f`]
  - `TL004` (`1742946909.7966`, `network`, `communication`): `172.16.1.2:43150->172.16.3.15:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-a81fe07df278a699, EV-29867f72af8db996`]
  - `TL005` (`1742946910.4790`, `network`, `communication`): `172.16.3.16:2404->172.16.1.2:41276/TCP` (`not_on_confirmed_storyline_spine`) [`EV-771dac216f524bec, EV-25faa25fe61c98a9`]
  - `TL009` (`1742946910.4790`, `network`, `electrical_report`): `line.13:current_to` (`not_on_confirmed_storyline_spine`) [`EV-85566ac3528fccd2, EV-ff5ad8534c12e171`]
  - `TL006` (`1742946910.4830`, `network`, `communication`): `172.16.1.2:41276->172.16.3.16:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-da158cfbbfeb36f9, EV-aa26f8c7b2d15622`]
  - `TL007` (`1742946910.5778`, `network`, `communication`): `172.16.3.1:2404->172.16.1.2:55486/TCP` (`not_on_confirmed_storyline_spine`) [`EV-fac6dac04d33932c, EV-172fbd05474beb95`]
  - `TL008` (`1742946910.5818`, `network`, `communication`): `172.16.1.2:55486->172.16.3.1:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-023a1aeb17f3fc58, EV-94f44d418f6737f2`]
  - `TL021` (`1742946910.6146`, `network`, `electrical_report`): `line.11:current_from` (`not_on_confirmed_storyline_spine`) [`EV-2afc731d0aba4312, EV-4ed8b4459351427b`]
