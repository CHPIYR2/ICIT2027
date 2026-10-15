# Evidence-Grounded Incident Reconstruction Report

- **Report Status**: `quality_consistent`
- **Quality & Behavioral Consistency (`quality_consistency.json`)**: `consistent`
- **Evidence Lineage Audit (`lineage_consistency.json`)**: `consistent`

- **Incident Window**: `1742940856.249995` to `1742941406.864951`
- **Reconstructed IEC-104 Transactions**: `0`
- **Reconstructed Event Storylines**: `15`
- **Verified Same-Device Transitions (Consistency Gate Passed)**: `0`
- **Unverified Protocol State Reports (Value Undecoded or No Pre-Baseline)**: `0`
- **LLM Claim Verifier Output (Separate from Graph Gate)**: `0` verified, `0` withheld

## 1. Incident Sequence & Protocol Transactions
- No IEC-104 control transactions were observed in this window.

## 2A. Behavioral Incident Reconstruction (No Control Command)
- Method: `evidence_anchor_discovery`. Inputs not used: `['official event labels', 'attack type', 'malicious flags', 'physical.zip']`. Control objects in window: `0`.
- `15` event anchors (`1` verified, `14` unverified), `15` behavioral storylines (`0` with corroborated multi-ASDU transitions, `1` verified single-anchor, `14` unverified observations), `0` sequential same-entity observations (gate failed), `4` unresolved cross-device branches.

### 2A.1 Event Anchors (by time)
- **A001** (rank `1`, `arp_activity_increase`, `verified_observation`, +`1.535`s, RTU `None`): ARP from 172.16.3.11: 12 packets in window (12 requests, 0 replies) to ['172.16.3.18', '172.16.3.20', '172.16.3.28']; 0 in background (verification=verified_observation).
- **A002** (rank `2`, `measurement_step`, `unverified_observation`, +`53.216`s, RTU `172.16.3.22`): line.4: 1 measurement(s) in one ASDU from RTU 172.16.3.22 changed current_to 0.0311952736 -> -0.300520152 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A003** (rank `3`, `measurement_step`, `unverified_observation`, +`65.634`s, RTU `172.16.3.9`): line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from 0.318877041 -> 0.117757946 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A004** (rank `4`, `measurement_step`, `unverified_observation`, +`121.993`s, RTU `172.16.3.11`): line.11: 1 measurement(s) in one ASDU from RTU 172.16.3.11 changed current_from 0.0129206283 -> 0.191258579 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A005** (rank `5`, `measurement_step`, `unverified_observation`, +`153.293`s, RTU `172.16.3.22`): line.4: 1 measurement(s) in one ASDU from RTU 172.16.3.22 changed current_to 0.5 -> 0.0424250774 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A006** (rank `6`, `measurement_step`, `unverified_observation`, +`166.313`s, RTU `172.16.3.12`): line.11: 1 measurement(s) in one ASDU from RTU 172.16.3.12 changed current_to 0.25705871 -> -0.459528834 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A007** (rank `7`, `measurement_step`, `unverified_observation`, +`235.734`s, RTU `172.16.3.9`): line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from 0.0925605968 -> 0.377396315 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A008** (rank `8`, `measurement_step`, `unverified_observation`, +`403.426`s, RTU `172.16.3.22`): line.4: 1 measurement(s) in one ASDU from RTU 172.16.3.22 changed current_to 0.179985419 -> -0.0560054071 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A009** (rank `9`, `measurement_step`, `unverified_observation`, +`420.708`s, RTU `172.16.3.16`): line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.16 changed current_to 0.180731222 -> -0.432608038 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A010** (rank `10`, `measurement_step`, `unverified_observation`, +`455.34`s, RTU `172.16.2.4`): line.10: 1 measurement(s) in one ASDU from RTU 172.16.2.4 changed current_from 0.345893085 -> 0.730269432 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A011** (rank `11`, `measurement_step`, `unverified_observation`, +`460.751`s, RTU `172.16.3.16`): line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.16 changed current_to -0.0287365634 -> 0.0850577727 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A012** (rank `12`, `measurement_step`, `unverified_observation`, +`480.771`s, RTU `172.16.3.16`): line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.16 changed current_to 0.0789418891 -> -0.37457633 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A013** (rank `13`, `measurement_step`, `unverified_observation`, +`505.922`s, RTU `172.16.3.9`): line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from -0.0136902006 -> 0.323304713 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A014** (rank `14`, `measurement_step`, `unverified_observation`, +`523.532`s, RTU `172.16.3.22`): line.4: 1 measurement(s) in one ASDU from RTU 172.16.3.22 changed current_to -0.0992443711 -> 0.124717578 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A015** (rank `15`, `measurement_step`, `unverified_observation`, +`532.205`s, RTU `172.16.3.11`): line.11: 1 measurement(s) in one ASDU from RTU 172.16.3.11 changed current_from 0.039640937 -> 0.30446586 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['insufficient_post_samples']).

### 2A.2 Behavioral Storylines
#### SL001 — anchors `['A001']` (+`1.535`s, status=`behavioral_single_anchor`)
- **Reconstructed**: [A001] ARP from 172.16.3.11: 12 packets in window (12 requests, 0 replies) to ['172.16.3.18', '172.16.3.20', '172.16.3.28']; 0 in background (verification=verified_observation).
- **Evidence-supported relations**: none (single anchor)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL002 — anchors `['A002']` (+`53.216`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A002] line.4: 1 measurement(s) in one ASDU from RTU 172.16.3.22 changed current_to 0.0311952736 -> -0.300520152 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A002': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Candidate relations (unresolved, time proximity only; 1)**: R0038: -> line.13:current_from (@+65.634s)
- **IPAL time-aligned rows (not independent)**: line.4:current_to (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL003 — anchors `['A003']` (+`65.634`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A003] line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from 0.318877041 -> 0.117757946 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A003': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Candidate relations (unresolved, time proximity only; 1)**: R0038: line.4:current_to (@+53.216s) ->
- **IPAL time-aligned rows (not independent)**: line.13:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL004 — anchors `['A004']` (+`121.993`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A004] line.11: 1 measurement(s) in one ASDU from RTU 172.16.3.11 changed current_from 0.0129206283 -> 0.191258579 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A004': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.11:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL005 — anchors `['A005']` (+`153.293`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A005] line.4: 1 measurement(s) in one ASDU from RTU 172.16.3.22 changed current_to 0.5 -> 0.0424250774 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A005': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Candidate relations (unresolved, time proximity only; 1)**: R0039: -> line.11:current_to (@+166.313s)
- **IPAL time-aligned rows (not independent)**: line.4:current_to (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL006 — anchors `['A006']` (+`166.313`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A006] line.11: 1 measurement(s) in one ASDU from RTU 172.16.3.12 changed current_to 0.25705871 -> -0.459528834 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A006': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Candidate relations (unresolved, time proximity only; 1)**: R0039: line.4:current_to (@+153.293s) ->
- **IPAL time-aligned rows (not independent)**: line.11:current_to (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL007 — anchors `['A007']` (+`235.734`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A007] line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from 0.0925605968 -> 0.377396315 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A007': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.13:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL008 — anchors `['A008']` (+`403.426`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A008] line.4: 1 measurement(s) in one ASDU from RTU 172.16.3.22 changed current_to 0.179985419 -> -0.0560054071 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A008': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.4:current_to (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL009 — anchors `['A009']` (+`420.708`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A009] line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.16 changed current_to 0.180731222 -> -0.432608038 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A009': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.13:current_to (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL010 — anchors `['A010']` (+`455.34`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A010] line.10: 1 measurement(s) in one ASDU from RTU 172.16.2.4 changed current_from 0.345893085 -> 0.730269432 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A010': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Candidate relations (unresolved, time proximity only; 1)**: R0040: -> line.13:current_to (@+460.751s)
- **IPAL time-aligned rows (not independent)**: line.10:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL011 — anchors `['A011']` (+`460.751`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A011] line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.16 changed current_to -0.0287365634 -> 0.0850577727 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A011': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Candidate relations (unresolved, time proximity only; 1)**: R0040: line.10:current_from (@+455.34s) ->
- **IPAL time-aligned rows (not independent)**: line.13:current_to (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL012 — anchors `['A012']` (+`480.771`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A012] line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.16 changed current_to 0.0789418891 -> -0.37457633 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A012': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.13:current_to (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL013 — anchors `['A013']` (+`505.922`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A013] line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from -0.0136902006 -> 0.323304713 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A013': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.13:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL014 — anchors `['A014']` (+`523.532`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A014] line.4: 1 measurement(s) in one ASDU from RTU 172.16.3.22 changed current_to -0.0992443711 -> 0.124717578 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A014': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Candidate relations (unresolved, time proximity only; 1)**: R0041: -> line.11:current_from (@+532.205s)
- **IPAL time-aligned rows (not independent)**: line.4:current_to (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL015 — anchors `['A015']` (+`532.205`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A015] line.11: 1 measurement(s) in one ASDU from RTU 172.16.3.11 changed current_from 0.039640937 -> 0.30446586 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['insufficient_post_samples']).
- **Unverified observation issues**: `{'A015': ['insufficient_post_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Candidate relations (unresolved, time proximity only; 1)**: R0041: line.4:current_to (@+523.532s) ->
- **IPAL time-aligned rows (not independent)**: line.11:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.

## 2B. Incident Scenario Synthesis (Four-Layer Epistemic Integration)
- **Scenario Status**: `synthesized_consistent`
- **Layer 1 Partition**: `0` supported multi-node chains, `1` verified single-anchor chains, `0` sequential same-entity observations (gate failed), `14` quarantined unverified observations (`0` unverified COT=3 precursor reports).
- **Layer 2 Bundles & Bridges**: `1` source bundles (each counted as `1` container), `0` cross-RTU verified element bridges, `0` same-RTU supported relations (not cross-RTU support), `0` multi-bundle bridged components.
- **Layer 3 Candidate Phases**: `1` candidate scenario phases (all cross-device links kept `unresolved`).
- **Layer 4 Source Dependency Ledger**: `0` IEC-104 ASDU, `0` TCP link, `1` ARP, `0` composite containers across `0` RTU(s) (`[]`), `0` co-reported same-ASDU points collapsed, mirror vantages `[]`, `14` IPAL rows excluded (`weight=0`).

### 2B.1 Layer 2 — RTU ASDU Bundles & Verified Element Bridges
- **BND-001** (`+1.535s`, RTU `None`, container=`SRC-ARP_ACTIVITY_INCREASE-172.16.3.11/ARP`, independent_sources=`1`): anchors `['A001']` -> `['172.16.3.11/ARP']`.
- **Cross-RTU Verified Element Bridges**: `none`.

### 2B.2 Layer 3 — Candidate Scenario Phases (Cross-Device Links Unresolved)
- **PHS-001** (`+1.535s`..`+1.669s`, profile=`localized_measurement_or_state_observations`): bundles=`['BND-001']`, verified_bridges=`[]`, sequential_same_device=`[]`, unverified_precursors=`[]`, RTUs=`[]`, ARP=`[{'anchor_id': 'A001', 'host_ip': '172.16.3.11', 'packet_count': 12, 'targets': {'172.16.3.28': 4, '172.16.3.20': 4, '172.16.3.18': 4}, 'target_first_seen': {'172.16.3.28': 1742940857.784495, '172.16.3.20': 1742940857.817129, '172.16.3.18': 1742940857.822169}, 'arp_target_overlap_rtu_ips': []}]`, unresolved_candidates=`0`.

## 2. Key Findings & Reconstructed Storylines (Contiguous Directed Spines)

## 3. Observed Network & Electrical Impact (Epistemically Stratified)
### 3.1 Verified Same-Device Measurement/State Transitions (Consistency Gate Passed)
- No post-command device transition passed all pre/post and target consistency checks.

### 3.2 Protocol State Reports Observed Without Verified Transition (Value Undecoded or No Pre-Baseline)
- None.

### 3.3 Candidate Cross-Entity Co-occurring Changes (Unresolved Hypotheses, Not Causal Proof)
- [SL002 / R0038 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): line.13:current_from (BA003) at 1742940921.8844 after BA002 (0 <= dt (12.418s) <= 15.0s) [src_ev=EV-7a3c007861a8f01a, EV-2c85700f528423af; dst_ev=EV-2977fd30fc8a9bff, EV-fff3ad85b7f8e207].
- [SL005 / R0039 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): line.11:current_to (BA006) at 1742941022.5628 after BA005 (0 <= dt (13.019s) <= 15.0s) [src_ev=EV-91a74cbeb56aa8a7, EV-13aec6212d32fb3a; dst_ev=EV-7525edee8b6d6ada, EV-05583ec4f15f832e].
- [SL010 / R0040 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): line.13:current_to (BA011) at 1742941317.0009 after BA010 (0 <= dt (5.41s) <= 15.0s) [src_ev=EV-66eddeb8cc7066c0, EV-93b27fdbd6c493c5; dst_ev=EV-e06095f33a18c900, EV-2bdfd878dde70ac1].
- [SL014 / R0041 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): line.11:current_from (BA015) at 1742941388.4545 after BA014 (0 <= dt (8.672s) <= 15.0s) [src_ev=EV-b1da4c1b9446f387, EV-93f9aea82426851f; dst_ev=EV-a8263ade67e36091, EV-0dcd08347f81599f].

## 4. Alternative Explanations & Competing Hypotheses
- No competing multi-branch hypotheses triggered in this window.

## 5. Unresolved Questions, Evidence Gaps & Unattached Observations
- **Unattached Observations (`38` nodes not on a storyline spine)**:
  - `TL001` (`1742940856.6955`, `network`, `communication`): `172.16.3.16:2404->172.16.1.2:41276/TCP` (`not_on_confirmed_storyline_spine`) [`EV-28d0899bc564f7d3, EV-13e3aaae0680ebb1`]
  - `TL022` (`1742940856.6955`, `network`, `electrical_report`): `line.13:current_to` (`not_on_confirmed_storyline_spine`) [`EV-a4c960378863a91d, EV-911485bc3dcc1b22`]
  - `TL002` (`1742940856.6995`, `network`, `communication`): `172.16.1.2:41276->172.16.3.16:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-46ddcca2d43834a3, EV-26591bb30f7877a8`]
  - `TL015` (`1742940856.8582`, `electrical`, `electrical_change`): `line.13:current_to` (`not_on_confirmed_storyline_spine`) [`EV-cde74a5e80ff160f, EV-29d727b489f6877e`]
  - `TL003` (`1742940858.1322`, `network`, `communication`): `172.16.3.11:2404->172.16.1.2:39462/TCP` (`not_on_confirmed_storyline_spine`) [`EV-0f6bf1ef05589430, EV-15a29aea42f36a34`]
  - `TL004` (`1742940858.1362`, `network`, `communication`): `172.16.1.2:39462->172.16.3.11:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-0e7e43788af0bd16, EV-8d58e9e67760c209`]
  - `TL018` (`1742940858.8582`, `electrical`, `electrical_change`): `line.10:current_to` (`not_on_confirmed_storyline_spine`) [`EV-75226a8525762210, EV-7c9078aac9d39b44`]
  - `TL020` (`1742940858.8582`, `electrical`, `electrical_change`): `line.11:current_from` (`not_on_confirmed_storyline_spine`) [`EV-f8fb32d59f694cf3, EV-0c6ff1b4b259fb3f`]
  - `TL005` (`1742940859.1655`, `network`, `communication`): `172.16.3.17:2404->172.16.1.2:33402/TCP` (`not_on_confirmed_storyline_spine`) [`EV-21ebd939f38acfc5, EV-1a5532949681c172`]
  - `TL006` (`1742940859.1695`, `network`, `communication`): `172.16.1.2:33402->172.16.3.17:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-e2752ad0fd194555, EV-ff1779135b5917f4`]
