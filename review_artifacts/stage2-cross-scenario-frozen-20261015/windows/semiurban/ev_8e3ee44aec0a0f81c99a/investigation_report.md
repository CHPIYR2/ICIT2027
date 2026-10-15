# Evidence-Grounded Incident Reconstruction Report

- **Report Status**: `quality_consistent`
- **Quality & Behavioral Consistency (`quality_consistency.json`)**: `consistent`
- **Evidence Lineage Audit (`lineage_consistency.json`)**: `consistent`

- **Incident Window**: `1743617001.538587` to `1743617497.9206042`
- **Reconstructed IEC-104 Transactions**: `0`
- **Reconstructed Event Storylines**: `20`
- **Verified Same-Device Transitions (Consistency Gate Passed)**: `0`
- **Unverified Protocol State Reports (Value Undecoded or No Pre-Baseline)**: `0`
- **LLM Claim Verifier Output (Separate from Graph Gate)**: `0` verified, `0` withheld

## 1. Incident Sequence & Protocol Transactions
- No IEC-104 control transactions were observed in this window.

## 2A. Behavioral Incident Reconstruction (No Control Command)
- Method: `evidence_anchor_discovery`. Inputs not used: `['official event labels', 'attack type', 'malicious flags', 'physical.zip']`. Control objects in window: `0`.
- `20` event anchors (`0` verified, `20` unverified), `20` behavioral storylines (`0` with corroborated multi-ASDU transitions, `0` verified single-anchor, `20` unverified observations), `1` sequential same-entity observations (gate failed), `12` unresolved cross-device branches.

### 2A.1 Event Anchors (by time)
- **A001** (rank `1`, `measurement_step`, `unverified_observation`, +`5.981`s, RTU `172.16.7.17`): line.116: 1 measurement(s) in one ASDU from RTU 172.16.7.17 changed current_from -0.205945596 -> 0.461382389 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A002** (rank `2`, `measurement_step`, `unverified_observation`, +`67.623`s, RTU `172.16.7.31`): line.53: 1 measurement(s) in one ASDU from RTU 172.16.7.31 changed current_from 0.778019905 -> 0.254447192 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A003** (rank `3`, `measurement_step`, `unverified_observation`, +`69.707`s, RTU `172.16.7.22`): line.53: 1 measurement(s) in one ASDU from RTU 172.16.7.22 changed current_to -0.269961298 -> 0.320598006 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A004** (rank `4`, `measurement_step`, `unverified_observation`, +`87.936`s, RTU `172.16.12.1`): line.20: 1 measurement(s) in one ASDU from RTU 172.16.12.1 changed current_from 0.197802454 -> -0.369551688 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A005** (rank `5`, `measurement_step`, `unverified_observation`, +`89.721`s, RTU `172.16.7.22`): line.53: 1 measurement(s) in one ASDU from RTU 172.16.7.22 changed current_to 0.303815931 -> -0.125210196 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A006** (rank `6`, `measurement_step`, `unverified_observation`, +`91.044`s, RTU `172.16.13.1`): line.119: 1 measurement(s) in one ASDU from RTU 172.16.13.1 changed current_to 0.112146117 -> 0.337697476 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A007** (rank `7`, `measurement_step`, `unverified_observation`, +`97.552`s, RTU `172.16.8.14`): line.120: 1 measurement(s) in one ASDU from RTU 172.16.8.14 changed current_from 0.463926762 -> 0.182779357 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A008** (rank `8`, `measurement_step`, `unverified_observation`, +`137.68`s, RTU `172.16.7.31`): line.53: 1 measurement(s) in one ASDU from RTU 172.16.7.31 changed current_from 0.414910138 -> 0.108538605 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A009** (rank `9`, `measurement_step`, `unverified_observation`, +`149.765`s, RTU `172.16.7.22`): line.114: 1 measurement(s) in one ASDU from RTU 172.16.7.22 changed current_from -0.5 -> -0.15199478 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A010** (rank `10`, `measurement_step`, `unverified_observation`, +`185.187`s, RTU `172.16.7.13`): line.115: 1 measurement(s) in one ASDU from RTU 172.16.7.13 changed current_to 0.0742718503 -> -0.336131603 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A011** (rank `11`, `measurement_step`, `unverified_observation`, +`217.74`s, RTU `172.16.7.31`): line.53: 1 measurement(s) in one ASDU from RTU 172.16.7.31 changed current_from -0.00941384956 -> 0.269286245 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A012** (rank `12`, `measurement_step`, `unverified_observation`, +`315.28`s, RTU `172.16.7.13`): line.115: 1 measurement(s) in one ASDU from RTU 172.16.7.13 changed current_to -0.0166370943 -> -0.227072537 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A013** (rank `13`, `measurement_step`, `unverified_observation`, +`327.731`s, RTU `172.16.8.14`): line.120: 1 measurement(s) in one ASDU from RTU 172.16.8.14 changed current_from -0.0179250333 -> -0.142982289 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A014** (rank `14`, `measurement_step`, `unverified_observation`, +`358.14`s, RTU `172.16.12.1`): line.20: 1 measurement(s) in one ASDU from RTU 172.16.12.1 changed current_from 0.0601472892 -> 0.0190477166 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A015** (rank `15`, `measurement_step`, `unverified_observation`, +`359.943`s, RTU `172.16.7.22`): line.53: 1 measurement(s) in one ASDU from RTU 172.16.7.22 changed current_to 0.19602865 -> -0.191089422 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A016** (rank `16`, `measurement_step`, `unverified_observation`, +`367.664`s, RTU `172.16.7.9`): line.115: 1 measurement(s) in one ASDU from RTU 172.16.7.9 changed current_from 0.24462761 -> 0.619677663 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A017** (rank `17`, `measurement_step`, `unverified_observation`, +`416.303`s, RTU `172.16.7.17`): line.116: 1 measurement(s) in one ASDU from RTU 172.16.7.17 changed current_from 0.33833459 -> -0.231765553 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A018** (rank `18`, `measurement_step`, `unverified_observation`, +`417.797`s, RTU `172.16.8.14`): line.120: 1 measurement(s) in one ASDU from RTU 172.16.8.14 changed current_from -0.0900563896 -> 0.369867206 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A019** (rank `19`, `measurement_step`, `unverified_observation`, +`437.721`s, RTU `172.16.7.9`): line.115: 1 measurement(s) in one ASDU from RTU 172.16.7.9 changed current_from 0.0523650609 -> 0.790082872 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A020** (rank `20`, `measurement_step`, `unverified_observation`, +`478.234`s, RTU `172.16.12.1`): line.20: 1 measurement(s) in one ASDU from RTU 172.16.12.1 changed current_from 0.0571096689 -> 0.459485233 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['insufficient_post_samples']).

### 2A.2 Behavioral Storylines
#### SL001 — anchors `['A001']` (+`5.981`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A001] line.116: 1 measurement(s) in one ASDU from RTU 172.16.7.17 changed current_from -0.205945596 -> 0.461382389 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A001': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.116:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL002 — anchors `['A002']` (+`67.623`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A002] line.53: 1 measurement(s) in one ASDU from RTU 172.16.7.31 changed current_from 0.778019905 -> 0.254447192 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']). 1 same-device sequential observation(s) kept off-spine (failed behavioral consistency gate: [['left_not_sustained', 'right_not_sustained', 'left_anchor_unverified', 'right_anchor_unverified', 'magnitude_direction_mismatch:current']]).
- **Unverified observation issues**: `{'A002': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Sequential same-entity observations (failed behavioral consistency gate, NOT supported transition)**: R0047 same_entity_sequential_observation: line.53:current_from (@+67.623s) -> line.53:current_to (@+69.707s); failed_gate=['left_not_sustained', 'right_not_sustained', 'left_anchor_unverified', 'right_anchor_unverified', 'magnitude_direction_mismatch:current']
- **IPAL time-aligned rows (not independent)**: line.53:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL003 — anchors `['A003']` (+`69.707`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A003] line.53: 1 measurement(s) in one ASDU from RTU 172.16.7.22 changed current_to -0.269961298 -> 0.320598006 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']). 1 same-device sequential observation(s) kept off-spine (failed behavioral consistency gate: [['left_not_sustained', 'right_not_sustained', 'left_anchor_unverified', 'right_anchor_unverified', 'magnitude_direction_mismatch:current']]).
- **Unverified observation issues**: `{'A003': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Sequential same-entity observations (failed behavioral consistency gate, NOT supported transition)**: R0047 same_entity_sequential_observation: line.53:current_from (@+67.623s) -> line.53:current_to (@+69.707s); failed_gate=['left_not_sustained', 'right_not_sustained', 'left_anchor_unverified', 'right_anchor_unverified', 'magnitude_direction_mismatch:current']
- **IPAL time-aligned rows (not independent)**: line.53:current_to (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL004 — anchors `['A004']` (+`87.936`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A004] line.20: 1 measurement(s) in one ASDU from RTU 172.16.12.1 changed current_from 0.197802454 -> -0.369551688 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A004': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Candidate relations (unresolved, time proximity only; 3)**: R0048: -> line.53:current_to (@+89.721s); R0049: -> line.119:current_to (@+91.044s); R0050: -> line.120:current_from (@+97.552s)
- **IPAL time-aligned rows (not independent)**: line.20:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL005 — anchors `['A005']` (+`89.721`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A005] line.53: 1 measurement(s) in one ASDU from RTU 172.16.7.22 changed current_to 0.303815931 -> -0.125210196 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A005': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Candidate relations (unresolved, time proximity only; 3)**: R0051: -> line.119:current_to (@+91.044s); R0052: -> line.120:current_from (@+97.552s); R0048: line.20:current_from (@+87.936s) ->
- **IPAL time-aligned rows (not independent)**: line.53:current_to (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL006 — anchors `['A006']` (+`91.044`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A006] line.119: 1 measurement(s) in one ASDU from RTU 172.16.13.1 changed current_to 0.112146117 -> 0.337697476 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A006': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Candidate relations (unresolved, time proximity only; 3)**: R0053: -> line.120:current_from (@+97.552s); R0049: line.20:current_from (@+87.936s) ->; R0051: line.53:current_to (@+89.721s) ->
- **IPAL time-aligned rows (not independent)**: line.119:current_to (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL007 — anchors `['A007']` (+`97.552`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A007] line.120: 1 measurement(s) in one ASDU from RTU 172.16.8.14 changed current_from 0.463926762 -> 0.182779357 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A007': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Candidate relations (unresolved, time proximity only; 3)**: R0050: line.20:current_from (@+87.936s) ->; R0052: line.53:current_to (@+89.721s) ->; R0053: line.119:current_to (@+91.044s) ->
- **IPAL time-aligned rows (not independent)**: line.120:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL008 — anchors `['A008']` (+`137.68`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A008] line.53: 1 measurement(s) in one ASDU from RTU 172.16.7.31 changed current_from 0.414910138 -> 0.108538605 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A008': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Candidate relations (unresolved, time proximity only; 1)**: R0054: -> line.114:current_from (@+149.765s)
- **IPAL time-aligned rows (not independent)**: line.53:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL009 — anchors `['A009']` (+`149.765`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A009] line.114: 1 measurement(s) in one ASDU from RTU 172.16.7.22 changed current_from -0.5 -> -0.15199478 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A009': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Candidate relations (unresolved, time proximity only; 1)**: R0054: line.53:current_from (@+137.68s) ->
- **IPAL time-aligned rows (not independent)**: line.114:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL010 — anchors `['A010']` (+`185.187`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A010] line.115: 1 measurement(s) in one ASDU from RTU 172.16.7.13 changed current_to 0.0742718503 -> -0.336131603 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A010': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.115:current_to (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL011 — anchors `['A011']` (+`217.74`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A011] line.53: 1 measurement(s) in one ASDU from RTU 172.16.7.31 changed current_from -0.00941384956 -> 0.269286245 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A011': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.53:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL012 — anchors `['A012']` (+`315.28`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A012] line.115: 1 measurement(s) in one ASDU from RTU 172.16.7.13 changed current_to -0.0166370943 -> -0.227072537 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A012': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Candidate relations (unresolved, time proximity only; 1)**: R0055: -> line.120:current_from (@+327.731s)
- **IPAL time-aligned rows (not independent)**: line.115:current_to (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL013 — anchors `['A013']` (+`327.731`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A013] line.120: 1 measurement(s) in one ASDU from RTU 172.16.8.14 changed current_from -0.0179250333 -> -0.142982289 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A013': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Candidate relations (unresolved, time proximity only; 1)**: R0055: line.115:current_to (@+315.28s) ->
- **IPAL time-aligned rows (not independent)**: line.120:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL014 — anchors `['A014']` (+`358.14`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A014] line.20: 1 measurement(s) in one ASDU from RTU 172.16.12.1 changed current_from 0.0601472892 -> 0.0190477166 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A014': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Candidate relations (unresolved, time proximity only; 2)**: R0056: -> line.53:current_to (@+359.943s); R0057: -> line.115:current_from (@+367.664s)
- **IPAL time-aligned rows (not independent)**: line.20:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL015 — anchors `['A015']` (+`359.943`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A015] line.53: 1 measurement(s) in one ASDU from RTU 172.16.7.22 changed current_to 0.19602865 -> -0.191089422 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A015': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Candidate relations (unresolved, time proximity only; 2)**: R0058: -> line.115:current_from (@+367.664s); R0056: line.20:current_from (@+358.14s) ->
- **IPAL time-aligned rows (not independent)**: line.53:current_to (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL016 — anchors `['A016']` (+`367.664`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A016] line.115: 1 measurement(s) in one ASDU from RTU 172.16.7.9 changed current_from 0.24462761 -> 0.619677663 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A016': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Candidate relations (unresolved, time proximity only; 2)**: R0057: line.20:current_from (@+358.14s) ->; R0058: line.53:current_to (@+359.943s) ->
- **IPAL time-aligned rows (not independent)**: line.115:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL017 — anchors `['A017']` (+`416.303`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A017] line.116: 1 measurement(s) in one ASDU from RTU 172.16.7.17 changed current_from 0.33833459 -> -0.231765553 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A017': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Candidate relations (unresolved, time proximity only; 1)**: R0059: -> line.120:current_from (@+417.797s)
- **IPAL time-aligned rows (not independent)**: line.116:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL018 — anchors `['A018']` (+`417.797`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A018] line.120: 1 measurement(s) in one ASDU from RTU 172.16.8.14 changed current_from -0.0900563896 -> 0.369867206 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A018': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Candidate relations (unresolved, time proximity only; 1)**: R0059: line.116:current_from (@+416.303s) ->
- **IPAL time-aligned rows (not independent)**: line.120:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL019 — anchors `['A019']` (+`437.721`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A019] line.115: 1 measurement(s) in one ASDU from RTU 172.16.7.9 changed current_from 0.0523650609 -> 0.790082872 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A019': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.115:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL020 — anchors `['A020']` (+`478.234`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A020] line.20: 1 measurement(s) in one ASDU from RTU 172.16.12.1 changed current_from 0.0571096689 -> 0.459485233 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['insufficient_post_samples']).
- **Unverified observation issues**: `{'A020': ['insufficient_post_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.20:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.

## 2B. Incident Scenario Synthesis (Four-Layer Epistemic Integration)
- **Scenario Status**: `synthesized_consistent`
- **Layer 1 Partition**: `0` supported multi-node chains, `0` verified single-anchor chains, `1` sequential same-entity observations (gate failed), `20` quarantined unverified observations (`0` unverified COT=3 precursor reports).
- **Layer 2 Bundles & Bridges**: `0` source bundles (each counted as `1` container), `0` cross-RTU verified element bridges, `0` same-RTU supported relations (not cross-RTU support), `0` multi-bundle bridged components.
- **Layer 3 Candidate Phases**: `0` candidate scenario phases (all cross-device links kept `unresolved`).
- **Layer 4 Source Dependency Ledger**: `0` IEC-104 ASDU, `0` TCP link, `0` ARP, `0` composite containers across `0` RTU(s) (`[]`), `0` co-reported same-ASDU points collapsed, mirror vantages `[]`, `20` IPAL rows excluded (`weight=0`).

### 2B.3 Layer 4 — Evidence-Anchored Competing Explanations & Missing Evidence
- **EXP-001** (`local_device_disconnection_with_unverified_prior_state_hypothesis`, status=`unresolved_competing_hypothesis`, causal_status=`not_established`): On line.53, a spontaneous COT=3 state report (A002: line.53:current_from) preceded a verified measurement drop to zero (A003: line.53:current_to), recorded as sequential observation R0047 because A002 failed ['left_not_sustained', 'right_not_sustained', 'left_anchor_unverified', 'right_anchor_unverified', 'magnitude_direction_mismatch:current'].
  - **Anchored by**: `{'verified_anchor_ids': [], 'sequential_edge_id': 'R0047', 'device_stem': 'line.53', 'evidence_ids': ['EV-d31e1798d784fe7f', 'EV-324b7d8096077a93', 'EV-6c70c4696b372a69', 'EV-39d98246a583b9d9']}`
  - **Unverified/candidate links required**: `['A002', 'R0047']`
  - **Alternative comparison**: Assumes the COT=3 report reflects an actual disconnection from a prior connected state (1.0 -> 0.0), which is not provable from in-window IEC-104 traffic alone.
  - **Missing disambiguating evidence**: `['Pre-window IEC-104 state baseline (COT=20) for line.53:current_from', 'Local RTU line.53 breaker/controller event log']`
- **EXP-002** (`uncommanded_output_drop_with_redundant_state_report_hypothesis`, status=`unresolved_competing_hypothesis`, causal_status=`not_established`): Only the measurement step A003 (line.53:current_to -> 0.0) is a verified transition; the earlier COT=3 report A002 could be a redundant status re-transmission or unverified telemetry frame without a physical state transition.
  - **Anchored by**: `{'verified_anchor_ids': [], 'device_stem': 'line.53', 'evidence_ids': ['EV-d31e1798d784fe7f', 'EV-324b7d8096077a93', 'EV-6c70c4696b372a69', 'EV-39d98246a583b9d9']}`
  - **Alternative comparison**: Relies strictly on the verified measurement step A002 without promoting the unverified COT=3 state report A001.
  - **Missing disambiguating evidence**: `['Out-of-band physical meter for line.53', 'Pre-window IEC-104 state history prior to background_start']`

## 2. Key Findings & Reconstructed Storylines (Contiguous Directed Spines)

## 3. Observed Network & Electrical Impact (Epistemically Stratified)
### 3.1 Verified Same-Device Measurement/State Transitions (Consistency Gate Passed)
- No post-command device transition passed all pre/post and target consistency checks.

### 3.2 Protocol State Reports Observed Without Verified Transition (Value Undecoded or No Pre-Baseline)
- None.

### 3.3 Candidate Cross-Entity Co-occurring Changes (Unresolved Hypotheses, Not Causal Proof)
- [SL004 / R0048 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): line.53:current_to (BA005) at 1743617091.2601 after BA004 (0 <= dt (1.786s) <= 15.0s) [src_ev=EV-b22fde6d085aa45f, EV-986f1fc1f38e2249; dst_ev=EV-28a08de42cf7dea3, EV-20339005ab6476c6].
- [SL004 / R0049 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): line.119:current_to (BA006) at 1743617092.583 after BA004 (0 <= dt (3.109s) <= 15.0s) [src_ev=EV-b22fde6d085aa45f, EV-986f1fc1f38e2249; dst_ev=EV-ddceebabb8eca590, EV-98ed39ac5307731d].
- [SL004 / R0050 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): line.120:current_from (BA007) at 1743617099.0906 after BA004 (0 <= dt (9.616s) <= 15.0s) [src_ev=EV-b22fde6d085aa45f, EV-986f1fc1f38e2249; dst_ev=EV-1e4ea439bb619722, EV-9939dc3629f29cfd].
- [SL005 / R0051 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): line.119:current_to (BA006) at 1743617092.583 after BA005 (0 <= dt (1.323s) <= 15.0s) [src_ev=EV-28a08de42cf7dea3, EV-20339005ab6476c6; dst_ev=EV-ddceebabb8eca590, EV-98ed39ac5307731d].
- [SL005 / R0052 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): line.120:current_from (BA007) at 1743617099.0906 after BA005 (0 <= dt (7.83s) <= 15.0s) [src_ev=EV-28a08de42cf7dea3, EV-20339005ab6476c6; dst_ev=EV-1e4ea439bb619722, EV-9939dc3629f29cfd].
- [SL006 / R0053 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): line.120:current_from (BA007) at 1743617099.0906 after BA006 (0 <= dt (6.508s) <= 15.0s) [src_ev=EV-ddceebabb8eca590, EV-98ed39ac5307731d; dst_ev=EV-1e4ea439bb619722, EV-9939dc3629f29cfd].
- [SL008 / R0054 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): line.114:current_from (BA009) at 1743617151.3036 after BA008 (0 <= dt (12.085s) <= 15.0s) [src_ev=EV-41cf82f9124092e0, EV-fa9b64aa3e36a74b; dst_ev=EV-e939f57fe2e56890, EV-170a4f31c9c97eca].
- [SL012 / R0055 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): line.120:current_from (BA013) at 1743617329.27 after BA012 (0 <= dt (12.451s) <= 15.0s) [src_ev=EV-2522e6efdc5405bc, EV-b220fbf01483eab4; dst_ev=EV-f8103c1c8575481d, EV-7b1f27d8fe48bdb2].
- [SL014 / R0056 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): line.53:current_to (BA015) at 1743617361.482 after BA014 (0 <= dt (1.804s) <= 15.0s) [src_ev=EV-0c5d37227c3fd292, EV-36f1192459cc6a4f; dst_ev=EV-fd27fd4398569092, EV-f9aa22005d259cb0].
- [SL014 / R0057 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): line.115:current_from (BA016) at 1743617369.2028 after BA014 (0 <= dt (9.524s) <= 15.0s) [src_ev=EV-0c5d37227c3fd292, EV-36f1192459cc6a4f; dst_ev=EV-6c3fac46f95e3e9d, EV-6dfe2f12ad11cc94].
- [SL015 / R0058 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): line.115:current_from (BA016) at 1743617369.2028 after BA015 (0 <= dt (7.721s) <= 15.0s) [src_ev=EV-fd27fd4398569092, EV-f9aa22005d259cb0; dst_ev=EV-6c3fac46f95e3e9d, EV-6dfe2f12ad11cc94].
- [SL017 / R0059 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): line.120:current_from (BA018) at 1743617419.3352 after BA017 (0 <= dt (1.494s) <= 15.0s) [src_ev=EV-c892eacb3185906c, EV-7d56dd5ef4d5e5e2; dst_ev=EV-c12aff8b4bf95349, EV-4410dac5dcf6f3cd].

## 4. Alternative Explanations & Competing Hypotheses
- **[SL004 | competing_cross_entity_cooccurrences | status=`unresolved`]**: Multiple distinct grid measurements (line.53:current_to, line.119:current_to, line.120:current_from) changed within the time horizon after line.20:current_from. Without an independent physical topology/power-flow model in the loop, these remain competing unresolved temporal co-occurrences rather than confirmed causal effects.
- **[SL005 | competing_cross_entity_cooccurrences | status=`unresolved`]**: Multiple distinct grid measurements (line.119:current_to, line.120:current_from) changed within the time horizon after line.53:current_to. Without an independent physical topology/power-flow model in the loop, these remain competing unresolved temporal co-occurrences rather than confirmed causal effects.
- **[SL014 | competing_cross_entity_cooccurrences | status=`unresolved`]**: Multiple distinct grid measurements (line.53:current_to, line.115:current_from) changed within the time horizon after line.20:current_from. Without an independent physical topology/power-flow model in the loop, these remain competing unresolved temporal co-occurrences rather than confirmed causal effects.

## 5. Unresolved Questions, Evidence Gaps & Unattached Observations
- **Unattached Observations (`42` nodes not on a storyline spine)**:
  - `TL001` (`1743617002.5244`, `network`, `communication`): `172.16.8.4:2404->172.16.5.2:33184/TCP` (`not_on_confirmed_storyline_spine`) [`EV-efbcb8a42853f937, EV-10537f72705c186b`]
  - `TL003` (`1743617002.5362`, `network`, `communication`): `172.16.7.27:2404->172.16.5.2:52716/TCP` (`not_on_confirmed_storyline_spine`) [`EV-08c3c7fbb4bd316f, EV-4715791a59b5633c`]
  - `TL005` (`1743617002.5644`, `network`, `communication`): `172.16.5.2:52716->172.16.7.27:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-42cf63d6000df5b7, EV-8db6cc6771315a57`]
  - `TL002` (`1743617002.5688`, `network`, `communication`): `172.16.5.2:33184->172.16.8.4:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-b722060827fd5c12, EV-f469c9a972572215`]
  - `TL007` (`1743617002.6738`, `network`, `communication`): `172.16.5.2:48034->172.16.7.25:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-5a7158fbe1d15cd6, EV-5fbbd3bb19c900f4`]
  - `TL025` (`1743617002.7622`, `network`, `communication`): `172.16.7.25:2404->172.16.5.2:48034/TCP` (`not_on_confirmed_storyline_spine`) [`EV-a351de4685c118f9, EV-082df7660ba06b4c`]
  - `TL009` (`1743617004.0616`, `network`, `electrical_report`): `load.121:reactive_power` (`not_on_confirmed_storyline_spine`) [`EV-049892d2f5756d76, EV-48d7e67a7f20a72c`]
  - `TL010` (`1743617004.0616`, `network`, `electrical_report`): `load.121:active_power` (`not_on_confirmed_storyline_spine`) [`EV-87f334710cd83e84, EV-e999c35666b382a7`]
  - `TL013` (`1743617004.3672`, `electrical`, `electrical_change`): `load.121:active_power` (`not_on_confirmed_storyline_spine`) [`EV-937ad3a6126cc52e, EV-9912afe10aea4297`]
  - `TL014` (`1743617004.3672`, `electrical`, `electrical_change`): `load.121:reactive_power` (`not_on_confirmed_storyline_spine`) [`EV-cc87ef24aaf0e98d, EV-aad8c20fd1439d65`]
