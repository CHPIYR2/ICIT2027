# Evidence-Grounded Incident Reconstruction Report

- **Report Status**: `quality_consistent`
- **Quality & Behavioral Consistency (`quality_consistency.json`)**: `consistent`
- **Evidence Lineage Audit (`lineage_consistency.json`)**: `consistent`

- **Incident Window**: `1742924252.2367709` to `1742924739.2759666`
- **Reconstructed IEC-104 Transactions**: `0`
- **Reconstructed Event Storylines**: `19`
- **Verified Same-Device Transitions (Consistency Gate Passed)**: `0`
- **Unverified Protocol State Reports (Value Undecoded or No Pre-Baseline)**: `0`
- **LLM Claim Verifier Output (Separate from Graph Gate)**: `0` verified, `0` withheld

## 1. Incident Sequence & Protocol Transactions
- No IEC-104 control transactions were observed in this window.

## 2A. Behavioral Incident Reconstruction (No Control Command)
- Method: `evidence_anchor_discovery`. Inputs not used: `['official event labels', 'attack type', 'malicious flags', 'physical.zip']`. Control objects in window: `0`.
- `19` event anchors (`4` verified, `15` unverified), `19` behavioral storylines (`0` with corroborated multi-ASDU transitions, `4` verified single-anchor, `15` unverified observations), `0` sequential same-entity observations (gate failed), `9` unresolved cross-device branches.

### 2A.1 Event Anchors (by time)
- **A001** (rank `4`, `arp_activity_increase`, `verified_observation`, +`1.625`s, RTU `None`): ARP from 172.16.3.35: 16 packets in window (14 requests, 2 replies) to ['172.16.3.28', '172.16.3.5', '172.16.3.9']; 0 in background (verification=verified_observation).
- **A002** (rank `1`, `arp_activity_increase`, `verified_observation`, +`1.651`s, RTU `None`): ARP from 172.16.3.28: 245 packets in window (1 requests, 244 replies) to ['172.16.3.35', '172.16.3.9']; 0 in background (verification=verified_observation).
- **A003** (rank `2`, `arp_activity_increase`, `verified_observation`, +`1.691`s, RTU `None`): ARP from 172.16.3.9: 244 packets in window (1 requests, 243 replies) to ['172.16.3.28', '172.16.3.35']; 0 in background (verification=verified_observation).
- **A004** (rank `3`, `arp_activity_increase`, `verified_observation`, +`2.749`s, RTU `None`): ARP from 172.16.3.5: 484 packets in window (0 requests, 484 replies) to ['172.16.3.28']; 0 in background (verification=verified_observation).
- **A005** (rank `5`, `measurement_step`, `unverified_observation`, +`20.875`s, RTU `172.16.3.22`): line.12: 1 measurement(s) in one ASDU from RTU 172.16.3.22 changed current_from 0.28549549 -> -0.161818907 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A006** (rank `6`, `measurement_step`, `unverified_observation`, +`59.004`s, RTU `172.16.3.9`): line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from 0.15487504 -> 0.340078562 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A007** (rank `7`, `measurement_step`, `unverified_observation`, +`70.875`s, RTU `172.16.3.22`): line.12: 1 measurement(s) in one ASDU from RTU 172.16.3.22 changed current_from -0.16050145 -> 0.237829 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A008** (rank `8`, `measurement_step`, `unverified_observation`, +`90.471`s, RTU `172.16.3.26`): line.14: 1 measurement(s) in one ASDU from RTU 172.16.3.26 changed current_to 0.000569205149 -> 0.0750323683 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A009** (rank `9`, `measurement_step`, `unverified_observation`, +`109.487`s, RTU `172.16.3.12`): line.14: 1 measurement(s) in one ASDU from RTU 172.16.3.12 changed current_from 0.0218228176 -> 0.444890887 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A010** (rank `10`, `measurement_step`, `unverified_observation`, +`123.76`s, RTU `172.16.3.16`): line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.16 changed current_to 0.195931718 -> -0.153478697 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A011** (rank `11`, `measurement_step`, `unverified_observation`, +`168.99`s, RTU `172.16.3.9`): line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from 0.393310487 -> 0.158493578 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A012** (rank `12`, `measurement_step`, `unverified_observation`, +`219.118`s, RTU `172.16.3.9`): line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from 0.335593343 -> -0.241793811 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A013** (rank `13`, `measurement_step`, `unverified_observation`, +`269.055`s, RTU `172.16.3.9`): line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from -0.0802462026 -> 0.428831667 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A014** (rank `14`, `measurement_step`, `unverified_observation`, +`270.586`s, RTU `172.16.3.26`): line.14: 1 measurement(s) in one ASDU from RTU 172.16.3.26 changed current_to -0.158430174 -> 0.253409356 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A015** (rank `15`, `measurement_step`, `unverified_observation`, +`321.032`s, RTU `172.16.3.22`): line.12: 1 measurement(s) in one ASDU from RTU 172.16.3.22 changed current_from 0.029011853 -> -0.0227919649 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A016** (rank `16`, `measurement_step`, `unverified_observation`, +`379.224`s, RTU `172.16.3.9`): line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from 0.0903622285 -> 0.609422386 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A017** (rank `17`, `measurement_step`, `unverified_observation`, +`409.172`s, RTU `172.16.3.9`): line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from -0.242944121 -> 0.733677924 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A018** (rank `18`, `measurement_step`, `unverified_observation`, +`439.215`s, RTU `172.16.3.9`): line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from -0.243042573 -> 0.304604024 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A019** (rank `19`, `measurement_step`, `unverified_observation`, +`479.256`s, RTU `172.16.3.9`): line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from 0.199384868 -> 0.567971528 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['insufficient_post_samples']).

### 2A.2 Behavioral Storylines
#### SL001 — anchors `['A001']` (+`1.625`s, status=`behavioral_single_anchor`)
- **Reconstructed**: [A001] ARP from 172.16.3.35: 16 packets in window (14 requests, 2 replies) to ['172.16.3.28', '172.16.3.5', '172.16.3.9']; 0 in background (verification=verified_observation).
- **Evidence-supported relations**: none (single anchor)
- **Candidate relations (unresolved, time proximity only; 3)**: R0036: -> 172.16.3.28/ARP (@+1.651s); R0037: -> 172.16.3.9/ARP (@+1.691s); R0038: -> 172.16.3.5/ARP (@+2.749s)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL002 — anchors `['A002']` (+`1.651`s, status=`behavioral_single_anchor`)
- **Reconstructed**: [A002] ARP from 172.16.3.28: 245 packets in window (1 requests, 244 replies) to ['172.16.3.35', '172.16.3.9']; 0 in background (verification=verified_observation).
- **Evidence-supported relations**: none (single anchor)
- **Candidate relations (unresolved, time proximity only; 3)**: R0039: -> 172.16.3.9/ARP (@+1.691s); R0040: -> 172.16.3.5/ARP (@+2.749s); R0036: 172.16.3.35/ARP (@+1.625s) ->
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL003 — anchors `['A003']` (+`1.691`s, status=`behavioral_single_anchor`)
- **Reconstructed**: [A003] ARP from 172.16.3.9: 244 packets in window (1 requests, 243 replies) to ['172.16.3.28', '172.16.3.35']; 0 in background (verification=verified_observation).
- **Evidence-supported relations**: none (single anchor)
- **Candidate relations (unresolved, time proximity only; 3)**: R0041: -> 172.16.3.5/ARP (@+2.749s); R0037: 172.16.3.35/ARP (@+1.625s) ->; R0039: 172.16.3.28/ARP (@+1.651s) ->
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL004 — anchors `['A004']` (+`2.749`s, status=`behavioral_single_anchor`)
- **Reconstructed**: [A004] ARP from 172.16.3.5: 484 packets in window (0 requests, 484 replies) to ['172.16.3.28']; 0 in background (verification=verified_observation).
- **Evidence-supported relations**: none (single anchor)
- **Candidate relations (unresolved, time proximity only; 3)**: R0038: 172.16.3.35/ARP (@+1.625s) ->; R0040: 172.16.3.28/ARP (@+1.651s) ->; R0041: 172.16.3.9/ARP (@+1.691s) ->
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL005 — anchors `['A005']` (+`20.875`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A005] line.12: 1 measurement(s) in one ASDU from RTU 172.16.3.22 changed current_from 0.28549549 -> -0.161818907 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A005': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.12:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL006 — anchors `['A006']` (+`59.004`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A006] line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from 0.15487504 -> 0.340078562 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A006': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Candidate relations (unresolved, time proximity only; 1)**: R0042: -> line.12:current_from (@+70.875s)
- **IPAL time-aligned rows (not independent)**: line.13:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL007 — anchors `['A007']` (+`70.875`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A007] line.12: 1 measurement(s) in one ASDU from RTU 172.16.3.22 changed current_from -0.16050145 -> 0.237829 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A007': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Candidate relations (unresolved, time proximity only; 1)**: R0042: line.13:current_from (@+59.004s) ->
- **IPAL time-aligned rows (not independent)**: line.12:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL008 — anchors `['A008']` (+`90.471`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A008] line.14: 1 measurement(s) in one ASDU from RTU 172.16.3.26 changed current_to 0.000569205149 -> 0.0750323683 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A008': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.14:current_to (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL009 — anchors `['A009']` (+`109.487`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A009] line.14: 1 measurement(s) in one ASDU from RTU 172.16.3.12 changed current_from 0.0218228176 -> 0.444890887 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A009': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Candidate relations (unresolved, time proximity only; 1)**: R0043: -> line.13:current_to (@+123.76s)
- **IPAL time-aligned rows (not independent)**: line.14:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL010 — anchors `['A010']` (+`123.76`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A010] line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.16 changed current_to 0.195931718 -> -0.153478697 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A010': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Candidate relations (unresolved, time proximity only; 1)**: R0043: line.14:current_from (@+109.487s) ->
- **IPAL time-aligned rows (not independent)**: line.13:current_to (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL011 — anchors `['A011']` (+`168.99`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A011] line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from 0.393310487 -> 0.158493578 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A011': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.13:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL012 — anchors `['A012']` (+`219.118`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A012] line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from 0.335593343 -> -0.241793811 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A012': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.13:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL013 — anchors `['A013']` (+`269.055`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A013] line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from -0.0802462026 -> 0.428831667 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A013': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Candidate relations (unresolved, time proximity only; 1)**: R0044: -> line.14:current_to (@+270.586s)
- **IPAL time-aligned rows (not independent)**: line.13:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL014 — anchors `['A014']` (+`270.586`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A014] line.14: 1 measurement(s) in one ASDU from RTU 172.16.3.26 changed current_to -0.158430174 -> 0.253409356 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A014': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **Candidate relations (unresolved, time proximity only; 1)**: R0044: line.13:current_from (@+269.055s) ->
- **IPAL time-aligned rows (not independent)**: line.14:current_to (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL015 — anchors `['A015']` (+`321.032`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A015] line.12: 1 measurement(s) in one ASDU from RTU 172.16.3.22 changed current_from 0.029011853 -> -0.0227919649 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A015': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.12:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL016 — anchors `['A016']` (+`379.224`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A016] line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from 0.0903622285 -> 0.609422386 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A016': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.13:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL017 — anchors `['A017']` (+`409.172`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A017] line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from -0.242944121 -> 0.733677924 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A017': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.13:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL018 — anchors `['A018']` (+`439.215`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A018] line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from -0.243042573 -> 0.304604024 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A018': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.13:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL019 — anchors `['A019']` (+`479.256`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A019] line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from 0.199384868 -> 0.567971528 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['insufficient_post_samples']).
- **Unverified observation issues**: `{'A019': ['insufficient_post_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.13:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.

## 2B. Incident Scenario Synthesis (Four-Layer Epistemic Integration)
- **Scenario Status**: `synthesized_consistent`
- **Layer 1 Partition**: `0` supported multi-node chains, `4` verified single-anchor chains, `0` sequential same-entity observations (gate failed), `15` quarantined unverified observations (`0` unverified COT=3 precursor reports).
- **Layer 2 Bundles & Bridges**: `4` source bundles (each counted as `1` container), `0` cross-RTU verified element bridges, `0` same-RTU supported relations (not cross-RTU support), `0` multi-bundle bridged components.
- **Layer 3 Candidate Phases**: `1` candidate scenario phases (all cross-device links kept `unresolved`).
- **Layer 4 Source Dependency Ledger**: `0` IEC-104 ASDU, `0` TCP link, `4` ARP, `0` composite containers across `0` RTU(s) (`[]`), `0` co-reported same-ASDU points collapsed, mirror vantages `[]`, `15` IPAL rows excluded (`weight=0`).

### 2B.1 Layer 2 — RTU ASDU Bundles & Verified Element Bridges
- **BND-001** (`+1.625s`, RTU `None`, container=`SRC-ARP_ACTIVITY_INCREASE-172.16.3.35/ARP`, independent_sources=`1`): anchors `['A001']` -> `['172.16.3.35/ARP']`.
- **BND-002** (`+1.651s`, RTU `None`, container=`SRC-ARP_ACTIVITY_INCREASE-172.16.3.28/ARP`, independent_sources=`1`): anchors `['A002']` -> `['172.16.3.28/ARP']`.
- **BND-003** (`+1.691s`, RTU `None`, container=`SRC-ARP_ACTIVITY_INCREASE-172.16.3.9/ARP`, independent_sources=`1`): anchors `['A003']` -> `['172.16.3.9/ARP']`.
- **BND-004** (`+2.749s`, RTU `None`, container=`SRC-ARP_ACTIVITY_INCREASE-172.16.3.5/ARP`, independent_sources=`1`): anchors `['A004']` -> `['172.16.3.5/ARP']`.
- **Cross-RTU Verified Element Bridges**: `none`.

### 2B.2 Layer 3 — Candidate Scenario Phases (Cross-Device Links Unresolved)
- **PHS-001** (`+1.625s`..`+484.785s`, profile=`localized_measurement_or_state_observations`): bundles=`['BND-001', 'BND-002', 'BND-003', 'BND-004']`, verified_bridges=`[]`, sequential_same_device=`[]`, unverified_precursors=`[]`, RTUs=`[]`, ARP=`[{'anchor_id': 'A001', 'host_ip': '172.16.3.35', 'packet_count': 16, 'targets': {'172.16.3.28': 7, '172.16.3.9': 5, '172.16.3.5': 4}, 'target_first_seen': {'172.16.3.28': 1742924253.862174, '172.16.3.9': 1742924253.920061, '172.16.3.5': 1742924253.92036}, 'arp_target_overlap_rtu_ips': []}, {'anchor_id': 'A002', 'host_ip': '172.16.3.28', 'packet_count': 245, 'targets': {'172.16.3.35': 4, '172.16.3.9': 241}, 'target_first_seen': {'172.16.3.35': 1742924253.887382, '172.16.3.9': 1742924255.972998}, 'arp_target_overlap_rtu_ips': []}, {'anchor_id': 'A003', 'host_ip': '172.16.3.9', 'packet_count': 244, 'targets': {'172.16.3.35': 3, '172.16.3.28': 241}, 'target_first_seen': {'172.16.3.35': 1742924253.928219, '172.16.3.28': 1742924255.973014}, 'arp_target_overlap_rtu_ips': []}, {'anchor_id': 'A004', 'host_ip': '172.16.3.5', 'packet_count': 484, 'targets': {'172.16.3.28': 484}, 'target_first_seen': {'172.16.3.28': 1742924254.98587}, 'arp_target_overlap_rtu_ips': []}]`, unresolved_candidates=`6`.

## 2. Key Findings & Reconstructed Storylines (Contiguous Directed Spines)

## 3. Observed Network & Electrical Impact (Epistemically Stratified)
### 3.1 Verified Same-Device Measurement/State Transitions (Consistency Gate Passed)
- No post-command device transition passed all pre/post and target consistency checks.

### 3.2 Protocol State Reports Observed Without Verified Transition (Value Undecoded or No Pre-Baseline)
- None.

### 3.3 Candidate Cross-Entity Co-occurring Changes (Unresolved Hypotheses, Not Causal Proof)
- [SL001 / R0036 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): 172.16.3.28/ARP (BA002) at 1742924253.8874 after BA001 (0 <= dt (0.025s) <= 15.0s) [src_ev=EV-2d9c015f3babaa6d, EV-1415459f075a162e; dst_ev=EV-7d2b59f4f609620a, EV-5233c5ee9498b135].
- [SL001 / R0037 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): 172.16.3.9/ARP (BA003) at 1742924253.9282 after BA001 (0 <= dt (0.066s) <= 15.0s) [src_ev=EV-2d9c015f3babaa6d, EV-1415459f075a162e; dst_ev=EV-0a17bd729a00b05d, EV-40bec397ddedfc11].
- [SL001 / R0038 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): 172.16.3.5/ARP (BA004) at 1742924254.9859 after BA001 (0 <= dt (1.124s) <= 15.0s) [src_ev=EV-2d9c015f3babaa6d, EV-1415459f075a162e; dst_ev=EV-7aaed16ad0bd2fd1, EV-339d523571d8ac68].
- [SL002 / R0039 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): 172.16.3.9/ARP (BA003) at 1742924253.9282 after BA002 (0 <= dt (0.041s) <= 15.0s) [src_ev=EV-7d2b59f4f609620a, EV-5233c5ee9498b135; dst_ev=EV-0a17bd729a00b05d, EV-40bec397ddedfc11].
- [SL002 / R0040 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): 172.16.3.5/ARP (BA004) at 1742924254.9859 after BA002 (0 <= dt (1.098s) <= 15.0s) [src_ev=EV-7d2b59f4f609620a, EV-5233c5ee9498b135; dst_ev=EV-7aaed16ad0bd2fd1, EV-339d523571d8ac68].
- [SL003 / R0041 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): 172.16.3.5/ARP (BA004) at 1742924254.9859 after BA003 (0 <= dt (1.058s) <= 15.0s) [src_ev=EV-0a17bd729a00b05d, EV-40bec397ddedfc11; dst_ev=EV-7aaed16ad0bd2fd1, EV-339d523571d8ac68].
- [SL006 / R0042 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): line.12:current_from (BA007) at 1742924323.1115 after BA006 (0 <= dt (11.87s) <= 15.0s) [src_ev=EV-e78e8572346eede8, EV-7960fa0c491dfdfe; dst_ev=EV-12f00fc3bdedf962, EV-46eb1d5f05a86c6c].
- [SL009 / R0043 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): line.13:current_to (BA010) at 1742924375.9973 after BA009 (0 <= dt (14.274s) <= 15.0s) [src_ev=EV-14857aa1d86b1d2e, EV-2fb8add289223e0d; dst_ev=EV-94204ab028dbb2bb, EV-15713c7364d1464e].
- [SL013 / R0044 | cross_device_temporal_candidate] (level=temporal_cooccurrence, status=unresolved, gate=no_direct_relation_evidence, causal_status=not_established): line.14:current_to (BA014) at 1742924522.8227 after BA013 (0 <= dt (1.531s) <= 15.0s) [src_ev=EV-2f379ecbefd23007, EV-8a46a3a8065350e2; dst_ev=EV-04967b1c212c1d27, EV-2a466827be7380da].

## 4. Alternative Explanations & Competing Hypotheses
- **[SL001 | competing_cross_entity_cooccurrences | status=`unresolved`]**: Multiple distinct grid measurements (172.16.3.28/ARP, 172.16.3.9/ARP, 172.16.3.5/ARP) changed within the time horizon after 172.16.3.35/ARP. Without an independent physical topology/power-flow model in the loop, these remain competing unresolved temporal co-occurrences rather than confirmed causal effects.
- **[SL002 | competing_cross_entity_cooccurrences | status=`unresolved`]**: Multiple distinct grid measurements (172.16.3.9/ARP, 172.16.3.5/ARP) changed within the time horizon after 172.16.3.28/ARP. Without an independent physical topology/power-flow model in the loop, these remain competing unresolved temporal co-occurrences rather than confirmed causal effects.

## 5. Unresolved Questions, Evidence Gaps & Unattached Observations
- **Evidence Gap**: `{"scope": "cross_vantage_payload_conflicts", "count": 42}`
- **Unattached Observations (`39` nodes not on a storyline spine)**:
  - `TL008` (`1742924252.2605`, `network`, `communication`): `172.16.3.5:2404->172.16.1.2:33798/TCP` (`not_on_confirmed_storyline_spine`) [`EV-15e66d9d266000d5, EV-19f7273c4ae247cf`]
  - `TL007` (`1742924252.3006`, `network`, `communication`): `172.16.1.2:33798->172.16.3.5:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-3ed09f9cc411977c, EV-4c2a91f049089469`]
  - `TL003` (`1742924252.5868`, `network`, `communication`): `172.16.3.26:2404->172.16.1.2:54802/TCP` (`not_on_confirmed_storyline_spine`) [`EV-35a4d8c8dac3d19b, EV-e8d5c4f7974b2af0`]
  - `TL004` (`1742924252.5908`, `network`, `communication`): `172.16.1.2:54802->172.16.3.26:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-7395bd424ca7c473, EV-ecb3008dd0026925`]
  - `TL018` (`1742924252.8582`, `electrical`, `electrical_change`): `line.14:current_to` (`not_on_confirmed_storyline_spine`) [`EV-137b8b605738a7af, EV-fae96302baf58296`]
  - `TL009` (`1742924253.0964`, `network`, `electrical_report`): `line.12:current_from` (`not_on_confirmed_storyline_spine`) [`EV-21e68d3f823bb0c2, EV-2964f8a323e1d80d`]
  - `TL012` (`1742924253.1144`, `network`, `electrical_report`): `line.12:current_to` (`not_on_confirmed_storyline_spine`) [`EV-b92a949c6f574fbe, EV-be21109f8db689dc`]
  - `TL001` (`1742924253.2491`, `network`, `communication`): `172.16.1.2:54426->172.16.3.9:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-4f28bfb6c2592cc0, EV-8b9e7cb2178e035c`]
  - `TL002` (`1742924253.2572`, `network`, `communication`): `172.16.3.9:2404->172.16.1.2:54426/TCP` (`not_on_confirmed_storyline_spine`) [`EV-cfa4a4746cc19430, EV-f367eeb541c911ac`]
  - `TL005` (`1742924253.4578`, `network`, `communication`): `172.16.3.15:2404->172.16.1.2:43150/TCP` (`not_on_confirmed_storyline_spine`) [`EV-f454ec9fcff4a45f, EV-03bca5a34ef6b64a`]
