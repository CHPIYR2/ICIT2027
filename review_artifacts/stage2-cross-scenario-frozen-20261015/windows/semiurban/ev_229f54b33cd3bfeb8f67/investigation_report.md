# Evidence-Grounded Incident Reconstruction Report

- **Report Status**: `quality_consistent`
- **Quality & Behavioral Consistency (`quality_consistency.json`)**: `consistent`
- **Evidence Lineage Audit (`lineage_consistency.json`)**: `consistent`

- **Incident Window**: `1743600362.6279092` to `1743600721.0473928`
- **Reconstructed IEC-104 Transactions**: `1`
- **Reconstructed Event Storylines**: `5`
- **Verified Same-Device Transitions (Consistency Gate Passed)**: `1`
- **Unverified Protocol State Reports (Value Undecoded or No Pre-Baseline)**: `0`
- **LLM Claim Verifier Output (Separate from Graph Gate)**: `0` verified, `0` withheld

## 1. Incident Sequence & Protocol Transactions
- **TX001** (`1743600418.6475`–`1743600419.2802`): `C_SC_NA_1 (Single command)` on `switch.335:closed` (`CA/IOA=154.10380`, value=`0.0`) over `172.16.14.11:60950 -> 172.16.14.7:2404` at vantages `['n523']`. **Command Acceptance (`COT=7` P/N)**: `accepted_by_rtu`; **Device State Verification**: `verified_state_transition` (reason=`decoded_spontaneous_state_shift_verified`); **Completeness**: `partial_no_cot10_but_verified_measurement_transition`; **Missing/Unverified Stages**: `['activation_termination_cot10']` (`EV-00a00cd3fa83e497, EV-7c67612c711ec8cd, EV-3334e4f733bfeddb, EV-17d2cb3e83f2c955`).
  - Inference gate (`state_report`): passed=`True`; pre IV=`False` other flags=`[]`; post IV=`False` other flags=`[]`; COT test bits=`{'command': False, 'confirmation': False, 'pre': False, 'post': False}`; failed=`[]`.

## 2A. Behavioral Incident Reconstruction (No Control Command)
- `577` event anchors found; a control transaction is present, so anchors are listed in `event_anchors.json` and do not root storylines.

## 2B. Incident Scenario Synthesis (Four-Layer Epistemic Integration)
- **Scenario Status**: `synthesized_consistent`
- **Layer 1 Partition**: `1` supported multi-node chains, `0` verified single-anchor chains, `0` sequential same-entity observations (gate failed), `0` quarantined unverified observations (`0` unverified COT=3 precursor reports).
- **Layer 2 Bundles & Bridges**: `0` source bundles (each counted as `1` container), `0` cross-RTU verified element bridges, `0` same-RTU supported relations (not cross-RTU support), `0` multi-bundle bridged components.
- **Layer 3 Candidate Phases**: `1` candidate scenario phases (all cross-device links kept `unresolved`).
- **Layer 4 Source Dependency Ledger**: `0` IEC-104 ASDU, `0` TCP link, `0` ARP, `4` composite containers across `1` RTU(s) (`['172.16.14.7']`), `0` co-reported same-ASDU points collapsed, mirror vantages `['n523']`, `576` IPAL rows excluded (`weight=0`).

### 2B.2 Layer 3 — Candidate Scenario Phases (Cross-Device Links Unresolved)
- **PHS-001** (`+56.02s`..`+56.652s`, profile=`protocol_command_transactions`): bundles=`[]`, verified_bridges=`[]`, sequential_same_device=`[]`, unverified_precursors=`[]`, RTUs=`['172.16.14.7']`, ARP=`[]`, unresolved_candidates=`0`.

### 2B.3 Layer 4 — Evidence-Anchored Competing Explanations & Missing Evidence
- **EXP-001** (`command_induced_device_transition_hypothesis`, status=`unresolved_competing_hypothesis`, causal_status=`not_established`): Observed IEC-104 control activation(s) ['TX001'] on the SCADA network, with 1 transaction(s) passing pre/post setpoint/state consistency checks. Consistent with RTU execution of the received IEC-104 command(s).
  - **Anchored by**: `{'transaction_ids': ['TX001'], 'verified_transition_transaction_ids': ['TX001'], 'evidence_ids': ['EV-00a00cd3fa83e497', 'EV-7c67612c711ec8cd', 'EV-3334e4f733bfeddb', 'EV-17d2cb3e83f2c955']}`
  - **Alternative comparison**: Competes with coincidence or unverified physical actuation where protocol confirmation (COT=7) or telemetry shifts occur without independent physical sensor verification.
  - **Missing disambiguating evidence**: `['Independent out-of-band physical process sensor or PMU log not derived from IEC-104', 'Master station operator/application audit log identifying the initiating process']`
- **EXP-002** (`arp_and_iec104_link_observations_without_supported_precedence`, status=`unresolved_competing_hypothesis`, causal_status=`not_established`): ARP activity ['A001', 'A002'] and IEC-104 link changes ['A074'] were both observed. No pair has per-target ARP overlap with the affected RTU before the link change and within 15s. No precedence between them is claimed.
  - **Anchored by**: `{'arp_anchor_ids': ['A001', 'A002'], 'communication_anchor_ids': ['A074'], 'arp_source_hosts': ['172.16.14.7', '172.16.14.8'], 'evidence_ids': ['EV-5b22fe895f2c795d', 'EV-65ebf26ca8e9e5e4', 'EV-d3e19441cf7377bd', 'EV-de0e6d51086a4384', 'EV-bcd4a8979aabf22e', 'EV-969e00fb85435a55', 'EV-444ffd8fc42219d2', 'EV-25b470a310bc36b7', 'EV-3139e232246eea64']}`
  - **Alternative comparison**: A general co-observation only. It does not say the ARP activity came first or addressed the RTU whose session changed.
  - **Missing disambiguating evidence**: `['ARP target addresses that match the RTU whose IEC-104 session changed', 'Per-target ARP timestamps before that session change and inside the horizon']`
- **EXP-003** (`concurrent_l2_link_disturbance_and_arp_re_resolution_hypothesis`, status=`unresolved_competing_hypothesis`, causal_status=`not_established`): IEC-104 links ['A074'] (sharing master 172.16.1.2) experienced session loss and re-establishment in the same window as ARP burst ['A001', 'A002'], without requiring ['172.16.14.7', '172.16.14.8'] to have caused the TCP session drops (e.g. switch path reset or interface flap accompanied by neighbor re-resolution).
  - **Anchored by**: `{'arp_anchor_ids': ['A001', 'A002'], 'communication_anchor_ids': ['A074'], 'evidence_ids': ['EV-5b22fe895f2c795d', 'EV-65ebf26ca8e9e5e4', 'EV-d3e19441cf7377bd', 'EV-de0e6d51086a4384', 'EV-bcd4a8979aabf22e', 'EV-969e00fb85435a55', 'EV-444ffd8fc42219d2', 'EV-25b470a310bc36b7', 'EV-3139e232246eea64']}`
  - **Alternative comparison**: Treats the ARP burst and the TCP session drops as co-occurring L2/L3 network events rather than assuming causal ARP interference.
  - **Missing disambiguating evidence**: `['Switch interface link-state / spanning-tree logs during the telemetry gap', "Host ['172.16.14.7', '172.16.14.8'] network service and ARP table logs"]`

## 2. Key Findings & Reconstructed Storylines (Contiguous Directed Spines)
### SL001 — Anchor `switch.335:closed` (tx=`TX001`, status=`partial_missing_cot10_but_verified_measurement_transition`, contiguous_path=`True`, logical_nodes=`3`, independent_sources=`3`, independent_edges=`2`, vantage_captures=`4`)
- Step 1 [R0001 | N-N | iec104_command_confirmation | level=observed_fact | gate=direct_record_observation | independent_evidence]: EF001 (switch.335:closed @ 1743600418.6475) -> EF002 (switch.335:closed @ 1743600418.666) [src_ev=EV-00a00cd3fa83e497, EV-7c67612c711ec8cd; dst_ev=EV-3334e4f733bfeddb, EV-17d2cb3e83f2c955]
- Step 2 [R0002 | N-N | subsequent_same_device_state_report | level=observed_fact | gate=direct_record_observation | independent_evidence]: EF002 (switch.335:closed @ 1743600418.666) -> EF003 (switch.335:is_closed @ 1743600419.2545) [src_ev=EV-3334e4f733bfeddb, EV-17d2cb3e83f2c955; dst_ev=EV-aaff00103ec52494, EV-63822c10df2f0157]
- Time-aligned IPAL row [R0011 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: EF005 (switch.335:closed=0.0 @ 1743600419.3672) aligned with EF001; not an independent source
- Time-aligned IPAL row [R0012 | temporally_aligned_same_point_stream | level=temporal_correspondence | common source NOT confirmed (no lineage)]: EF005 (switch.335:closed=0.0 @ 1743600419.3672) aligned with EF002; not an independent source
- **Evidence Gaps**: `['activation_termination_cot10']`
### SL002 — Anchor `172.16.14.7:2404->172.16.5.2:49396/TCP` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`452`)
- Step 1 [R0009 | N-N | bidirectional_tcp_session | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL001 (172.16.14.7:2404->172.16.5.2:49396/TCP @ 1743600366.6773) -> TL002 (172.16.5.2:49396->172.16.14.7:2404/TCP @ 1743600374.7274) [src_ev=EV-8916a03b10ec9b6c, EV-22eaa4cce41c4ac9; dst_ev=EV-f814627f64fb1acd, EV-57f76fe792e0c0ef]
### SL003 — Anchor `172.16.8.15:2404->172.16.5.2:37014/TCP` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`358`)
- Step 1 [R0006 | N-N | bidirectional_tcp_session | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL003 (172.16.8.15:2404->172.16.5.2:37014/TCP @ 1743600363.6341) -> TL004 (172.16.5.2:37014->172.16.8.15:2404/TCP @ 1743600363.6381) [src_ev=EV-b0d6e9017da72779, EV-65bf7ba8ba5e9cdf; dst_ev=EV-062e28d3ee556b7d, EV-fbdd80df78889e7e]
### SL004 — Anchor `172.16.8.11:2404->172.16.5.2:52406/TCP` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`358`)
- Step 1 [R0007 | N-N | bidirectional_tcp_session | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL005 (172.16.8.11:2404->172.16.5.2:52406/TCP @ 1743600363.8905) -> TL006 (172.16.5.2:52406->172.16.8.11:2404/TCP @ 1743600363.8945) [src_ev=EV-2483652ea13c9bbb, EV-96a92bf030d38f2a; dst_ev=EV-00cc052f87b2c913, EV-ea5a913c1e64ab1f]
### SL005 — Anchor `172.16.8.16:2404->172.16.5.2:49242/TCP` (tx=`None`, status=`observed_state_or_session_chain`, contiguous_path=`True`, logical_nodes=`2`, independent_sources=`2`, independent_edges=`1`, vantage_captures=`358`)
- Step 1 [R0008 | N-N | bidirectional_tcp_session | level=observed_fact | gate=direct_record_observation | independent_evidence]: TL007 (172.16.8.16:2404->172.16.5.2:49242/TCP @ 1743600364.3852) -> TL008 (172.16.5.2:49242->172.16.8.16:2404/TCP @ 1743600364.3893) [src_ev=EV-f3ed7f57ab98c6b8, EV-8dcc06bb28a5126b; dst_ev=EV-69a4dd7117815798, EV-0beb7299828cd5d5]

## 3. Observed Network & Electrical Impact (Epistemically Stratified)
### 3.1 Verified Same-Device Measurement/State Transitions (Consistency Gate Passed)
- [TX001 | verified_state_transition] Point switch.335:is_closed (CA/IOA=154.10390) shifted from pre-command state 1.0 to 0.0 (@ 1743600419.2545, ev=EV-aaff00103ec52494, EV-63822c10df2f0157).

### 3.2 Protocol State Reports Observed Without Verified Transition (Value Undecoded or No Pre-Baseline)
- None.

### 3.3 Candidate Cross-Entity Co-occurring Changes (Unresolved Hypotheses, Not Causal Proof)
- No cross-entity temporal co-occurrences recorded.

## 4. Alternative Explanations & Competing Hypotheses
- No competing multi-branch hypotheses triggered in this window.

## 5. Unresolved Questions, Evidence Gaps & Unattached Observations
- **Evidence Gap**: `{"scope": "TX001", "entity": "switch.335:closed", "missing_stages": ["activation_termination_cot10"]}`
- **Evidence Gap**: `{"scope": "cross_vantage_payload_conflicts", "count": 803}`
- **Unattached Observations (`17` nodes not on a storyline spine)**:
  - `TL010` (`1743600364.5863`, `network`, `electrical_report`): `line.117:current_to` (`not_on_confirmed_storyline_spine`) [`EV-9e8dd387bfcbba13, EV-2ed51c7dbac28d5c`]
  - `TL014` (`1743600365.3672`, `electrical`, `electrical_change`): `line.117:current_to` (`not_on_confirmed_storyline_spine`) [`EV-f141117ec51862f0, EV-58c168e6e3618d62`]
  - `TL013` (`1743600367.3369`, `network`, `electrical_report`): `line.44:reactive_power_from` (`isolated_no_graph_edge`) [`EV-49d0c2f67ebdfafa, EV-b47e3a38ddfb2951`]
  - `TL012` (`1743600370.7485`, `network`, `electrical_report`): `trafo.50:current_lv` (`isolated_no_graph_edge`) [`EV-259947d3ef90fd0b, EV-82fa5273e84d0cda`]
  - `TL015` (`1743600386.3672`, `electrical`, `electrical_change`): `sgen.7:cos_phi` (`isolated_no_graph_edge`) [`EV-c6260d600ece6fa0, EV-2f75abf060e50236`]
  - `TL016` (`1743600386.3672`, `electrical`, `electrical_change`): `sgen.14:cos_phi` (`isolated_no_graph_edge`) [`EV-fd3751afa855577e, EV-e49c7286a81596e5`]
  - `TL017` (`1743600389.3672`, `electrical`, `electrical_change`): `sgen.89:cos_phi` (`isolated_no_graph_edge`) [`EV-1e4cc7c936c411e0, EV-30f07269a55e9293`]
  - `TL018` (`1743600391.3672`, `electrical`, `electrical_change`): `sgen.59:cos_phi` (`isolated_no_graph_edge`) [`EV-932bc584f8c1375b, EV-b232249e3808b128`]
  - `TL019` (`1743600393.3672`, `electrical`, `electrical_change`): `sgen.87:cos_phi` (`isolated_no_graph_edge`) [`EV-59d5af2095192e9a, EV-cdbc44bfe22797af`]
  - `TL020` (`1743600394.3672`, `electrical`, `electrical_change`): `sgen.106:cos_phi` (`isolated_no_graph_edge`) [`EV-3f8738cb5177cd38, EV-f5eb56f63914d27c`]
