# MIRAGE-OT: Automated Evidence-Grounded Incident Reconstruction and Explanation Engine

- **R1 Run directory (preserved)**: `runs/etgi/reconstruction-20261015/` (`code_sha256 = c884c2d4...`, commit `b0bbe66`)
- **R2 Reliability-Hardened Run directory**: `runs/etgi/reconstruction-r2-20261015/`
- **R2 Frozen code SHA-256 (`postalert/*.py` + `reconstruction/*.py`)**: `f8a168270b3cc85e95aa0c3662fd11d4cffbba57406e5751049334c1ff6a8ee0` (Git commit `7203e32`)
- **Offline test suite**: **72 passed** (`8` in `tests/test_reconstruction.py`, `36` in `tests/test_postalert.py`, `28` in `tests/test_etgi.py`)

---

## 1. Summary of P0 & P1 Reliability Fixes (`commit 7203e32`)

Following the independent code & evidence audit (`docs/MIRAGE_OT_RECONSTRUCTION_AUDIT_20261015.md`), four P0 and three P1 fixes were implemented without redesigning the architecture or relaxing any verification criteria:

1. **P0-1 — IEC-104 Device State Verification & Boolean Decoder Support (`iec104.py`, `index.py`, `transactions.py`)**:
   - Extended `iec104.py` (`_FIELDS` & `_parse_value`) to decode `tshark` boolean strings (`"True"` / `"False"`) for `iec60870_asdu.siq.spi`, `iec60870_asdu.sco.on`, `iec60870_asdu.nega` (P/N bit), `iec60870_asdu.test`, `iec60870_asdu.sq`, `iec60870_asdu.sco.se` / `qos.se` (Select/Execute), `siq.iv` / `qds.iv` (quality invalid), and `iec60870_104.tx` / `rx`.
   - In `_finalize_transaction()`, mere presence of a `COT=3` (`M_SP_NA_1`) message or an IPAL `new` row **never** sets `state_change_observed`. When the state report value is undecoded (`value_present=False`), status is downgraded to `state_report_observed_value_unknown`; when decoded but lacking a pre-command IEC-104 baseline proving $v_{\text{pre}} \neq v_{\text{post}}$, status is `state_report_observed_no_pre_baseline`.
2. **P0-2 — Independent Consistency Gate for `supported_inference` (`transactions.py`, `event_graph.py`)**:
   - Implemented `evaluate_command_effect_inference()`, invoked directly inside `build_temporal_event_graph()` on the actual pre-command, command, and post-command values/flags.
   - An edge is upgraded to `claim_level="supported_inference"` (`graph_consistency_gate_status="passed_noncausal_inference_gate"`) **only** when: (a) same RTU/CA and device stem, (b) command not rejected by NACK or missing `COT=7`, (c) valid pre-command baseline exists, (d) valid post-command value exists with valid quality, (e) `shifted_from_pre_baseline` holds ($|\Delta| > \max(1\%, 10^{-3})$), (f) shift direction approaches target, and (g) post value matches commanded target within tolerance.
   - When any condition fails (including the audit counterexamples: `post_command_value = 39999.0`, wrong shift direction, missing pre-baseline, or undecoded switch values), the edge is downgraded to `claim_level="unresolved"`, `verification_status="unresolved"`, `relation_type="command_to_device_state_candidate"` (`graph_consistency_gate_status="failed_gate_kept_unresolved"`).
3. **P0-3 — Explicit `COT=7` P/N Bit (Positive vs. Negative Confirmation) Semantics (`transactions.py`)**:
   - `cot_negative is False` $\to$ `command_acceptance_status = "accepted_by_rtu"`
   - `cot_negative is True` $\to$ `command_acceptance_status = "rejected_negative_confirmation"` (blocks downstream inference)
   - `cot_negative is None` (when evaluating pre-existing DBs that did not index `nega`) $\to$ `command_acceptance_status = "confirmation_observed_acceptance_unknown"` (never claims `accepted_by_rtu` when the P/N bit is absent).
4. **P0-4 — Contiguous Directed Path Invariant on Storyline Spines (`storyline.py`)**:
   - Every storyline spine now enforces `_assert_contiguous_spine_path()`: `len(spine_fact_ids) == len(confirmed_and_supported_steps) + 1` and `step[i].source_fact_id == spine_fact_ids[i]`, `step[i].target_fact_id == spine_fact_ids[i+1]`.
   - Pre-command baseline nodes (`EF015` on `sgen.6`, `EF003` on `sgen.10`) and their `pre_to_post_measurement_transition` edges (`R0014`, `R0002`) are stored separately in `context_observations` and `supporting_evidence_edges`.
5. **P1-5 — Cross-Vantage Payload Conflict Detection & Strict TCP Retransmission Rules (`transactions.py`)**:
   - If two mirror vantages (`n302`, `n318`) share `(5-tuple, tcp_seq, entity, ca_ioa, type_id, cot)` but differ in decoded value or flags, they are **never** merged; both are preserved and logged in `cross_vantage_conflicts` (`cross_vantage_payload_conflict`).
   - An unconfirmed `COT=6` is attached as `tcp_retransmission` **only** when `tcp_seq` (and `apci_tx` if present) matches the open command; a distinct `tcp_seq` starts a new transaction.
6. **P1-6 & P1-7 — Vantage-Invariant `canonical_source_id`, Stratified N-P Stream Types, and Endpoint Evidence Citations (`event_graph.py`, `storyline.py`, `report.py`)**:
   - `independent_source_container_count` now counts unique canonical sources (`3` on a 4-node `COT=6 -> COT=7 -> COT=3/POST -> IPAL` spine) rather than multiplying by mirror ports (`vantage_capture_count` is reported separately).
   - Every edge and report line explicitly prints `src_ev=[...]` and `dst_ev=[...]`.

---

## 2. All Downgraded or Corrected Transactions, Edges, and Storylines (R1 $\to$ R2)

| Event | Scope | R1 (`c884c2d4...`) | R2 (`f8a16827...`) | Reason for Downgrade / Correction |
| --- | --- | --- | --- | --- |
| `ev_0961` | `TX001` (`switch.23`), `TX002` (`switch.24`), `TX003` (`switch.25`) acceptance | `accepted_by_rtu` | **`confirmation_observed_acceptance_unknown`** | Existing DB rows lacked decoded `cot_negative` (P/N bit); cannot claim positive acceptance without P/N bit. |
| `ev_0961` | `TX001`, `TX002`, `TX003` device state status | `state_change_observed` | **`state_report_observed_value_unknown`** | `COT=3` (`switch.23/24/25:is_closed`) had `value=None` (`unparsed_value`) and no pre-command IEC-104 baseline. |
| `ev_0961` | Graph edges `EF001->EF003`, `EF005->EF007`, `EF009->EF011` (3 switch inference edges) | `command_to_device_state_transition` (`supported_inference` / `supported`) | **`command_to_device_state_candidate` (`unresolved` / `unresolved`)** | Failed consistency gate (`command_value_unknown, missing_pre_command_baseline, post_state_or_measurement_value_unknown`). Total `supported_inference` edges in `ev_0961` dropped from **4 $\to$ 1** (only `TX004` `sgen.6` remains `supported_inference`). |
| `ev_0961` | `SL004` (`sgen.6`) spine topology | Non-contiguous 5-node list `['EF015','EF013','EF014','EF016','EF018']` | **Contiguous 4-node spine `['EF013','EF014','EF016','EF018']` + `context_observations=['EF015']` + `supporting_evidence_edges=['R0014']`** | Enforced contiguous directed path invariant `edge[i].target == edge[i+1].source`. |
| `ev_0961` | `SL001`–`SL004` `independent_source_container_count` | `10` (inflated by dual mirror vantages + point keys) | **`3` on spine (`4` including supporting `EF015` on `SL004`), `vantage_captures=7` reported separately** | Canonical source IDs deduplicate mirror captures across `n302` and `n318`. |
| `ev_3e4d` | `TX001` (`switch.31`), `TX002` (`switch.30`), `TX003` (`switch.27`) acceptance | `accepted_by_rtu` | **`confirmation_observed_acceptance_unknown`** | Missing `cot_negative` P/N bit in pre-existing DB. |
| `ev_3e4d` | `TX001` (`switch.31`), `TX003` (`switch.27`) device state status | `state_change_observed` | **`state_report_observed_value_unknown`** | `COT=3` (`switch.31/27:is_closed`) had `value=None` and no pre-command baseline. |
| `ev_3e4d` | Graph edges `EF001->EF003`, `EF007->EF009` (2 switch inference edges) | `command_to_device_state_transition` (`supported_inference` / `supported`) | **`command_to_device_state_candidate` (`unresolved` / `unresolved`)** | Failed consistency gate. Total `supported_inference` edges in `ev_3e4d` dropped from **2 $\to$ 0**. |
| `ev_12dcd56b` | `TX001` (`sgen.10`) acceptance | `accepted_by_rtu` | **`confirmation_observed_acceptance_unknown`** | Missing `cot_negative` P/N bit in pre-existing DB (`device_state_change_status` remains `verified_measurement_transition` because `309980.938 -> 269971.625` matches target `270000.0`). |
| `ev_12dcd56b` | `SL001` (`sgen.10`) spine topology | Non-contiguous 5-node list `['EF003','EF001','EF002','EF004','EF006']` | **Contiguous 4-node spine `['EF001','EF002','EF004','EF006']` + `context_observations=['EF003']` + `supporting_evidence_edges=['R0002']`** | Enforced contiguous directed path invariant; `independent_source_container_count` corrected from `7` $\to$ `3` (`4` with `EF003`). |
