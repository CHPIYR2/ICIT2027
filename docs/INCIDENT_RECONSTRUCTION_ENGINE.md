# MIRAGE-OT: Automated Evidence-Grounded Incident Reconstruction and Explanation Engine

- **Run directory**: `runs/etgi/reconstruction-20261015/`
- **Frozen code SHA-256 (`postalert/*.py` + `reconstruction/*.py`)**: `c884c2d4705e3458e5fb62378135eceb61c21067bc43cd3007f9f5e1054775ad` (Git commit `b0bbe66`)
- **Modules implemented**:
  - `src/mirage_ot/etgi/reconstruction/transactions.py` (Phase 1 — IEC-104 Protocol Transaction Reconstruction)
  - `src/mirage_ot/etgi/reconstruction/event_graph.py` (Phase 2 — Event-Level Temporal Graph: `N-N`, `P-P`, `N-P`)
  - `src/mirage_ot/etgi/reconstruction/storyline.py` (Phase 3 — Source-Deduplicated Bounded Beam Search Storyline Reconstruction)
  - `src/mirage_ot/etgi/reconstruction/report.py` & `engine.py` (Phase 4 — Typed-Reference Verified Investigation Explanation & Report Renderer)
  - `tests/test_reconstruction.py` (Unit tests covering protocol pairing invariants, missing confirmations/terminations, multi-vantage `tcp_seq` deduplication, state transitions, beam search, and source deduplication)

---

## 1. Algorithmic Provenance: Literature vs. MIRAGE-OT Novel Contributions

| Component | Prior Literature / Existing Concept | MIRAGE-OT Novel Design & ICS/OT Adaptation |
| --- | --- | --- |
| **Temporal Provenance Graph & Multi-Stage Campaign Chaining** | **SLEUTH** (Hossain et al., USENIX Security 2017) and **HOLMES** (Milajerdi et al., IEEE S&P 2019) construct host-audit provenance graphs and correlate low-level events into high-level scenario graphs using causal/temporal dependencies and path scoring. | Host OS syscalls have explicit kernel process/file descriptors, whereas OT/ICS network-electrical telemetry lacks cross-device causal pointers and suffers from multi-switch mirror duplication and protocol-to-state transcription aliases. MIRAGE-OT introduces **event-level timestamped observation nodes (`EFnnn`/`TLnnn`)** (rather than static entity nodes) and a **five-category `N-N`/`P-P`/`N-P` relation taxonomy** that strictly separates `direct_protocol_relation`, `shared_source` (`independent_support=False`), `measurement_state_transition`, `inference_hypothesis` (`command_to_device_state_transition`), and `temporal_cooccurrence` (`unresolved`). |
| **IEC-104 Protocol Transaction State Machine (Phase 1)** | Standard IEC 60870-5-104 specification defines `COT=6` (Activation), `COT=7` (Activation Confirmation), `COT=10` (Activation Termination), and `COT=3` (Spontaneous). | **Designed in this study (`transactions.py`)**: (1) **Cross-vantage L4 `tcp_seq` deduplication** that collapses routed packets across mirror ports (`n302`, `n318`) even when L2 frame hashes (`fingerprint`) change due to TTL/MAC rewrite, while preserving same-vantage retransmissions (`duplicate_command_messages`) and repeated operations (`TX001` vs `TX002`); (2) **Four-invariant pairing** requiring reverse TCP 5-tuple, matching `type_id`, matching `CA/IOA`, and matching command value (rejecting time-proximate + same-`CA/IOA` messages on mismatched sessions); (3) **Explicit separation of `command_acceptance_status` (`COT=7`) from `device_state_change_status` (`COT=3` feedback or pre-to-post setpoint shift)**. |
| **Source-Deduplicated Bounded Beam Search (Phase 3)** | Beam search / bounded path search over temporal graphs. | **Designed in this study (`storyline.py`)**: Tracks physical packet containers (`seen_source_containers`) along each candidate path. Edges representing derived IPAL state updates (`shared_source_ipal_transcription`) or sibling objects in the same frame (`same_iec104_frame`) are retained on the storyline spine for cross-layer consistency verification but contribute **`0` independent evidence edges (`independent_support=False`)**, preventing single-packet derivatives from inflating storyline confidence. |
| **Deterministic Claim Binding & Non-Causal Epistemic Guardrails (Phase 4)** | Structured output schemas and post-hoc claim verification. | **Designed in this study (`verify.py`, `report.py`)**: The LLM selects only typed anchors (`TX...`, `SL...`, `EF.../TL...`, `R...`); all timestamps, IP addresses, `CA/IOA` identifiers, and measurement numbers are rendered deterministically from the database. Cross-entity co-occurrences (`temporal_cooccurrence`) cannot be upgraded to `supported_inference` and are rendered strictly under unresolved competing hypotheses. |

---

## 2. End-to-End Case 1: `ev_0961f1c2da8a257e3ebc` (`01-Basic`, Multi-Switch & Generator Setpoint Sequence)

- **Artifacts**: `runs/etgi/reconstruction-20261015/ev_0961f1c2da8a257e3ebc/`
- **Window**: `1742961051.1897168` to `1742961125.4603136` (`74.27s`, background `15.0s`)
- **Lineage Audit Bundle**: `312` requested / `312` exported (`missing_ids = []`, `row_check_failures = []`)
- **Event Graph**: `34` event nodes, `48` edges (`N-N = 23`, `N-P = 23`, `P-P = 2`; `direct_protocol_relation = 9`, `measurement_state_transition = 4`, `inference_hypothesis = 4`, `shared_source = 15`, `temporal_cooccurrence = 16`)

### 2.1 Reconstructed Protocol Transactions (`transactions.json`)

| TX ID | Time Span | Command ASDU & Point | Session (`Master -> RTU`) | Vantages | `command_acceptance_status` | `device_state_change_status` | Post-Command State / Measurement Evidence | Missing Stages |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `TX001` | `1742961051.2126`–`1742961051.4620` | `C_SC_NA_1 (type=45, COT=6)` `switch.23:closed` (`110.10130`) | `172.16.1.2:58630 -> 172.16.3.5:2404` | `n302, n318` | `accepted_by_rtu` (`COT=7` @ `.2438`) | `state_change_observed` | `M_SP_NA_1 (type=1, COT=3)` `switch.23:is_closed` (`110.10140` @ `.4440`) + IPAL `switch.23:closed=1.0` (@ `.8582`) | `['activation_termination_cot10']` |
| `TX002` | `1742961062.2701`–`1742961062.5201` | `C_SC_NA_1 (type=45, COT=6)` `switch.24:closed` (`110.10150`) | `172.16.1.2:58630 -> 172.16.3.5:2404` | `n302, n318` | `accepted_by_rtu` (`COT=7` @ `.3018`) | `state_change_observed` | `M_SP_NA_1 (type=1, COT=3)` `switch.24:is_closed` (`110.10160` @ `.5020`) + IPAL `switch.24:closed=0.0` (@ `.8582`) | `['activation_termination_cot10']` |
| `TX003` | `1742961073.3280`–`1742961073.5978` | `C_SC_NA_1 (type=45, COT=6)` `switch.25:closed` (`114.10150`) | `172.16.1.2:54778 -> 172.16.3.9:2404` | `n302, n318` | `accepted_by_rtu` (`COT=7` @ `.3675`) | `state_change_observed` | `M_SP_NA_1 (type=1, COT=3)` `switch.25:is_closed` (`114.10160` @ `.5677`) + IPAL `switch.25:closed=0.0` (@ `.8582`) | `['activation_termination_cot10']` |
| `TX004` | `1742961084.4062`–`1742961093.1166` | `C_SE_NC_1 (type=50, COT=6)` `sgen.6:target_active_power=20000.0` (`111.10040`) | `172.16.1.2:41978 -> 172.16.3.6:2404` | `n302, n318` | `accepted_by_rtu` (`COT=7` @ `.4377`) | `state_change_observed` | `M_ME_NC_1 (type=13)` `sgen.6:active_power` (`111.10080`) shifted `40004.5312 -> 20000.6875` (@ `1742961093.0986`, matches setpoint `20000.0`) | `['activation_termination_cot10']` |

### 2.2 Reconstructed Storylines (`storylines.json`)

1. **`SL001` (`TX001`, `switch.23`, 4 spine nodes, 3 spine edges, `2` independent edges + `1` shared-source edge)**:
   - `EF001` (`switch.23:closed` `COT=6` @ `1742961051.2126`, `EV-63b7a00ef9966369, EV-fe137d883659e4d2`) $\xrightarrow{\text{R0001: iec104\_command\_confirmation (N-N, observed\_fact, indep=True)}}$ `EF002` (`switch.23:closed` `COT=7` @ `1742961051.2438`, `EV-97acb130fa9468ec, EV-e7fc0b6837b890aa`) $\xrightarrow{\text{R0002: iec104\_spontaneous\_state\_report (N-N, observed\_fact, indep=True)}}$ `EF003` (`switch.23:is_closed` `COT=3` @ `1742961051.4440`, `EV-3109cd2175859fbc, EV-f2358df688ab9c19`) $\xrightarrow{\text{R0004: shared\_source\_ipal\_transcription (N-P, observed\_fact, indep=False)}}$ `EF004` (IPAL `switch.23:closed=1.0` @ `1742961051.8582`, `EV-e90ea94be9729465`).
   - **Unresolved Competing Branches**: `12` cross-entity co-occurrence edges (`R0033`–`R0044`, e.g., `line.7:active_power_from`, `line.7:current_from`, `line.7:reactive_power_from`, `line.6:active_power_to` changing `2.19s`–`2.65s` after `EF001`), retained strictly as `temporal_cooccurrence` (`unresolved`, `causal_status = not_established`).
2. **`SL002` (`TX002`, `switch.24`, 4 spine nodes, `2` independent edges + `1` shared-source edge)**:
   - `EF005` (`COT=6` @ `.2701`) $\xrightarrow{\text{R0005 (indep=True)}}$ `EF006` (`COT=7` @ `.3018`) $\xrightarrow{\text{R0006 (indep=True)}}$ `EF007` (`switch.24:is_closed` `COT=3` @ `.5020`) $\xrightarrow{\text{R0008 (indep=False)}}$ `EF008` (IPAL `switch.24:closed=0.0` @ `.8582`).
3. **`SL003` (`TX003`, `switch.25`, 4 spine nodes, `2` independent edges + `1` shared-source edge)**:
   - `EF009` (`COT=6` @ `.3280`) $\xrightarrow{\text{R0009 (indep=True)}}$ `EF010` (`COT=7` @ `.3675`) $\xrightarrow{\text{R0010 (indep=True)}}$ `EF011` (`switch.25:is_closed` `COT=3` @ `.5677`) $\xrightarrow{\text{R0012 (indep=False)}}$ `EF012` (IPAL `switch.25:closed=0.0` @ `.8582`).
4. **`SL004` (`TX004`, `sgen.6`, 5 spine nodes, 4 spine edges, `3` independent edges + `1` shared-source edge)**:
   - Step 1 (`R0014`, `N-N`, `pre_to_post_measurement_transition`, `observed_fact`, `indep=True`): `EF015` (`sgen.6:active_power = 40004.5312` @ `1742961083.0927`) $\to$ `EF016` (`sgen.6:active_power = 20000.6875` @ `1742961093.0986`).
   - Step 2 (`R0013`, `N-N`, `iec104_command_confirmation`, `observed_fact`, `indep=True`): `EF013` (`sgen.6:target_active_power = 20000.0` `COT=6` @ `1742961084.4062`) $\to$ `EF014` (`COT=7` @ `1742961084.4377`).
   - Step 3 (`R0015`, `N-N`, `command_to_device_state_transition`, `supported_inference`, `indep=True`): `EF014` (`COT=7` on `sgen.6:target_active_power=20000.0`) $\to$ `EF016` (`sgen.6:active_power = 20000.6875` on same RTU `172.16.3.6`, `CA=111`).
   - Step 4 (`R0017`, `N-P`, `shared_source_ipal_transcription`, `observed_fact`, `indep=False`): `EF016` $\to$ `EF018` (IPAL `sgen.6:active_power = 20000.6875` @ `1742961093.8582`).

---

## 3. Generalization Across Other Sherlock Basic Incidents (Non-Specialization Verification)

### 3.1 Case 2: `ev_3e4d36008b29595ef246` (Demonstrating Partial / Unchanged-State Transactions)

- **Artifacts**: `runs/etgi/reconstruction-20261015/ev_3e4d36008b29595ef246/`
- **Lineage Audit Bundle**: `228` requested / `228` exported (`missing_ids = []`, `row_check_failures = []`)
- **Key Reconstruction Result**:
  - `SL001` (`TX001`, `switch.31:closed` @ `1742959890.2245`): Reconstructs full 4-node chain (`EF001 COT=6 -> EF002 COT=7 -> EF003 switch.31:is_closed COT=3 -> EF004 IPAL switch.31:closed=1.0`).
  - **`SL002` (`TX002`, `switch.30:closed` @ `1742959900.3104`) — Incomplete Storyline Caught**:
    - Master `172.16.1.2:39462` sent `C_SC_NA_1 (COT=6)` on `switch.30:closed` (`116.10150`) to RTU `172.16.3.11:2404` (`EF005`), and RTU replied with `COT=7` (`EF006` @ `1742959900.3356`).
    - However, **no `M_SP_NA_1 (COT=3)` spontaneous state report and no IPAL `new` state update occurred for `switch.30`**.
    - The engine outputs `command_acceptance_status = "accepted_by_rtu"`, `device_state_change_status = "no_state_change_observed"`, `completeness_status = "incomplete_command_accepted_without_state_change"`, `evidence_gaps = ["activation_termination_cot10", "post_command_state_or_measurement_change"]`, and generates an explicit alternative-explanation entry rather than fabricating a state change.
  - `SL003` (`TX003`, `switch.27:closed` @ `1742959910.3446`): Reconstructs full 4-node chain (`EF007 COT=6 -> EF008 COT=7 -> EF009 switch.27:is_closed COT=3 -> EF010 IPAL switch.27:closed=0.0`).

### 3.2 Case 3: `ev_12dcd56b2f5e78144cfb` (Generator Setpoint Step-Down Only)

- **Artifacts**: `runs/etgi/reconstruction-20261015/ev_12dcd56b2f5e78144cfb/`
- **Lineage Audit Bundle**: `149` requested / `149` exported (`missing_ids = []`, `row_check_failures = []`)
- **Key Reconstruction Result**:
  - `SL001` (`TX001`, `sgen.10:target_active_power = 270000.0` @ `1742949082.2828` on `172.16.1.2:59440 -> 172.16.3.3:2404`):
    - Reconstructs 5-node spine (`3` independent edges + `1` shared-source edge):
      - `EF003` (`sgen.10:active_power = 309980.938` @ `1742949075.456`) $\xrightarrow{\text{R0002: pre\_to\_post\_measurement\_transition (indep=True)}}$ `EF004` (`sgen.10:active_power = 269971.625` @ `1742949085.5235`)
      - `EF001` (`sgen.10:target_active_power = 270000.0` `COT=6` @ `1742949082.2828`) $\xrightarrow{\text{R0001: iec104\_command\_confirmation (indep=True)}}$ `EF002` (`COT=7` @ `1742949082.356`) $\xrightarrow{\text{R0003: command\_to\_device\_state\_transition (supported\_inference, indep=True)}}$ `EF004` (`sgen.10:active_power = 269971.625`) $\xrightarrow{\text{R0005: shared\_source\_ipal\_transcription (indep=False)}}$ `EF006` (IPAL `sgen.10:active_power = 269971.625` @ `1742949085.8582`).
    - All `15` subsequent line/bus measurement changes (`line.11:current_from`, `line.13:current_to`, `bus.9:active_power`, `line.4:current_to`) are kept in `unresolved_cooccurrence_branches` (`temporal_cooccurrence`).
