# Evidence-Grounded Incident Reconstruction Report

- **Report Status**: `quality_consistent`
- **Quality & Behavioral Consistency (`quality_consistency.json`)**: `consistent`
- **Evidence Lineage Audit (`lineage_consistency.json`)**: `consistent`

- **Incident Window**: `1742957112.2481863` to `1742957609.899807`
- **Reconstructed IEC-104 Transactions**: `0`
- **Reconstructed Event Storylines**: `6`
- **Verified Same-Device Transitions (Consistency Gate Passed)**: `0`
- **Unverified Protocol State Reports (Value Undecoded or No Pre-Baseline)**: `0`
- **LLM Claim Verifier Output (Separate from Graph Gate)**: `0` verified, `0` withheld

## 1. Incident Sequence & Protocol Transactions
- No IEC-104 control transactions were observed in this window.

## 2A. Behavioral Incident Reconstruction (No Control Command)
- Method: `evidence_anchor_discovery`. Inputs not used: `['official event labels', 'attack type', 'malicious flags', 'physical.zip']`. Control objects in window: `0`.
- `5` event anchors (`0` verified, `5` unverified), `5` behavioral storylines (`0` with corroborated multi-ASDU transitions, `0` verified single-anchor, `5` unverified observations), `0` sequential same-entity observations (gate failed), `0` unresolved cross-device branches.

### 2A.1 Event Anchors (by time)
- **A001** (rank `1`, `measurement_step`, `unverified_observation`, +`39.702`s, RTU `172.16.3.9`): line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from 0.139145181 -> 0.499894202 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A002** (rank `2`, `measurement_step`, `unverified_observation`, +`59.677`s, RTU `172.16.3.9`): line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from 0.473733366 -> 0.165008932 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A003** (rank `3`, `measurement_step`, `unverified_observation`, +`254.775`s, RTU `172.16.3.16`): line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.16 changed current_to -0.377042413 -> -0.183489144 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A004** (rank `4`, `measurement_step`, `unverified_observation`, +`349.875`s, RTU `172.16.3.9`): line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from 0.352965951 -> -0.113140844 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **A005** (rank `5`, `measurement_step`, `unverified_observation`, +`429.872`s, RTU `172.16.3.9`): line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from 0.0109071229 -> 0.717214584 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).

### 2A.2 Behavioral Storylines
#### SL001 — anchors `['A001']` (+`39.702`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A001] line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from 0.139145181 -> 0.499894202 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A001': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.13:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL002 — anchors `['A002']` (+`59.677`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A002] line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from 0.473733366 -> 0.165008932 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A002': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.13:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL003 — anchors `['A003']` (+`254.775`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A003] line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.16 changed current_to -0.377042413 -> -0.183489144 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A003': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.13:current_to (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL004 — anchors `['A004']` (+`349.875`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A004] line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from 0.352965951 -> -0.113140844 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A004': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.13:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.
#### SL005 — anchors `['A005']` (+`429.872`s, status=`behavioral_unverified_observation`)
- **Reconstructed**: [A005] line.13: 1 measurement(s) in one ASDU from RTU 172.16.3.9 changed current_from 0.0109071229 -> 0.717214584 (level_shift; quality good=True; sustained=False; verification=unverified_observation; issues=['not_sustained_in_later_samples']).
- **Unverified observation issues**: `{'A005': ['not_sustained_in_later_samples']}`
- **Evidence-supported relations**: none (unverified observation; excluded from supported spine)
- **IPAL time-aligned rows (not independent)**: line.13:current_from (temporally_aligned_same_point_stream; common source not confirmed)
- **Not reconstructed**: Cause, the initiating actor, and any relation to devices outside this chain. Cross-device links are listed only as unresolved branches; no grid topology is available.

## 2B. Incident Scenario Synthesis (Four-Layer Epistemic Integration)
- **Scenario Status**: `synthesized_consistent`
- **Layer 1 Partition**: `0` supported multi-node chains, `0` verified single-anchor chains, `0` sequential same-entity observations (gate failed), `5` quarantined unverified observations (`0` unverified COT=3 precursor reports).
- **Layer 2 Bundles & Bridges**: `0` source bundles (each counted as `1` container), `0` cross-RTU verified element bridges, `0` same-RTU supported relations (not cross-RTU support), `0` multi-bundle bridged components.
- **Layer 3 Candidate Phases**: `0` candidate scenario phases (all cross-device links kept `unresolved`).
- **Layer 4 Source Dependency Ledger**: `0` IEC-104 ASDU, `0` TCP link, `0` ARP, `0` composite containers across `0` RTU(s) (`[]`), `0` co-reported same-ASDU points collapsed, mirror vantages `[]`, `5` IPAL rows excluded (`weight=0`).

## 2. Key Findings & Reconstructed Storylines (Contiguous Directed Spines)
### SL006 — Anchor `line.13:current_to` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`0`, vantage_captures=`200`)
- Step 1 [R0011 | N-N | same_iec104_frame | level=observed_fact | gate=direct_record_observation | shared_source_not_double_counted]: TL009 (line.13:current_to @ 1742957116.9519) -> TL023 (line.3:active_power_from @ 1742957116.9519) [src_ev=EV-be082fdaf41dcd3f, EV-f7f53acf24b9b032; dst_ev=EV-762cc0164368331b, EV-83c63a3086be51ec]
- Time-aligned IPAL row [R0006 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL013 (line.13:current_to=-0.11175662279129028 @ 1742957117.8582) aligned with TL009; not an independent source
- Time-aligned IPAL row [R0007 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: TL019 (line.3:active_power_from=134650.15625 @ 1742957117.8582) aligned with TL023; not an independent source

## 3. Observed Network & Electrical Impact (Epistemically Stratified)
### 3.1 Verified Same-Device Measurement/State Transitions (Consistency Gate Passed)
- No post-command device transition passed all pre/post and target consistency checks.

### 3.2 Protocol State Reports Observed Without Verified Transition (Value Undecoded or No Pre-Baseline)
- None.

### 3.3 Candidate Cross-Entity Co-occurring Changes (Unresolved Hypotheses, Not Causal Proof)
- No cross-entity temporal co-occurrences recorded.

## 4. Alternative Explanations & Competing Hypotheses
- No competing multi-branch hypotheses triggered in this window.

## 5. Unresolved Questions, Evidence Gaps & Unattached Observations
- **Unattached Observations (`27` nodes not on a storyline spine)**:
  - `TL003` (`1742957112.7453`, `network`, `communication`): `172.16.3.19:2404->172.16.1.2:44700/TCP` (`not_on_confirmed_storyline_spine`) [`EV-2c9d0624170fb705, EV-906d0674ff7bb104`]
  - `TL004` (`1742957112.7494`, `network`, `communication`): `172.16.1.2:44700->172.16.3.19:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-9a1f6446d34c29b0, EV-0c1b97b3e8220825`]
  - `TL001` (`1742957112.7629`, `network`, `communication`): `172.16.3.12:2404->172.16.1.2:55948/TCP` (`not_on_confirmed_storyline_spine`) [`EV-a98efd927902a268, EV-f490b3daa9581998`]
  - `TL010` (`1742957112.7629`, `network`, `electrical_report`): `line.11:current_to` (`not_on_confirmed_storyline_spine`) [`EV-6f3218029a9914af, EV-f271d78f11580f0d`]
  - `TL002` (`1742957112.7669`, `network`, `communication`): `172.16.1.2:55948->172.16.3.12:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-5c62185f8fc350bf, EV-022a87ddc70addbc`]
  - `TL014` (`1742957112.8582`, `electrical`, `electrical_change`): `line.13:current_from` (`not_on_confirmed_storyline_spine`) [`EV-852ea4105e22cd74, EV-6950529ac908c2cb`]
  - `TL015` (`1742957112.8582`, `electrical`, `electrical_change`): `line.11:current_to` (`not_on_confirmed_storyline_spine`) [`EV-92a271dbe634d74c, EV-3fcfdf8c10fc707c`]
  - `TL020` (`1742957112.8582`, `electrical`, `electrical_change`): `line.3:active_power_to` (`not_on_confirmed_storyline_spine`) [`EV-bcf7dfa9d4d6e25a, EV-492323fac742206a`]
  - `TL005` (`1742957113.1394`, `network`, `communication`): `172.16.3.14:2404->172.16.1.2:60636/TCP` (`not_on_confirmed_storyline_spine`) [`EV-3521977873ecca95, EV-917c923bac580c20`]
  - `TL006` (`1742957113.1434`, `network`, `communication`): `172.16.1.2:60636->172.16.3.14:2404/TCP` (`not_on_confirmed_storyline_spine`) [`EV-a6a26a73ee910163, EV-8be7aae59c15b223`]
