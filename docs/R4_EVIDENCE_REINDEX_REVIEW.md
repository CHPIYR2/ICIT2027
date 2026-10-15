# R4 IEC-104 evidence reindexing review

Scope: Sherlock v3 `01-Basic`, recording `test`, two windows only (`ev_0961f1c2da8a257e3ebc`, `ev_12dcd56b2f5e78144cfb`). The rest of Sherlock v3 was not reindexed. LLM was not called (`--no-llm`).

Local outputs, not committed (`runs/` is gitignored):

- New indexes: `runs/etgi/r4-reindex-20261015/<event>/evidence.sqlite` with their own `pcap-slices/` and `field_audit.json`.
- Reconstruction: `runs/etgi/reconstruction-r4-20261015/<event>/`, including `quality_consistency.json`.
- R1, R2, R3 run directories and the earlier indexes (`runs/etgi/basic-ev0961/`, `runs/etgi/memory-comparison-20261014/ev_12dcd56b2f5e78144cfb/`) were read, not written.

Code SHA-256 of `postalert/*.py` plus `reconstruction/*.py`: `2248ac7f6f58b7d15feaba19d420aa9d65c4206e8816b23d395fe35a0eb1bfc2`.
Code SHA-256 of `evidence/*.py`: `032c6977ac0507e9c442b37e4e78455d0ab6d1a21b1efe751a0ccf37242a3b85`.
New index SHA-256: ev_0961 `95503b9da54a419660752d05f897550928ca28530eb573e7f124cdbe3cfce3ba`, ev_12dcd56b `b4bbcac8df597aa8275c40b87d67b4c4b50d3cba2d0d83bf373f8e56ef4936fc`.

## Parser changes

- Type id, COT cause, P/N, T, SQ, NumIx, OA and CA are read once per ASDU and given only to that ASDU's objects.
- Value, quality bits and S/E are read once per information object. Each tshark field is consumed in frame order by the object types that carry it (SIQ: IV/NT/SB/BL; DIQ: same; QDS: IV/NT/SB/BL/OV; SCO/DCO/QOS: S/E).
- If a field's occurrence count differs from the number of objects that carry it, that field is unknown for the whole frame. It is never shifted to a neighbouring IOA and never copied to several IOAs.
- `quality_good` is `True` only when every bit of the element was decoded and is clear. One missing bit gives `None`.
- `iec104_raw.py` decodes the same APDUs from the TCP payload bytes without tshark. It is used only by the audit.

## Raw field audit

Each object found in the raw TCP payload was traced through tshark, the parser, and the database row. The slices of the old and new index are byte-identical (`slices_identical_to_legacy=true`), so the comparison isolates parser and storage.

Raw content of the two windows: every APDU segment was complete. ev_0961 has 4370 objects (4348 measurements, 8 commands, 8 confirmations, 6 COT=3 state reports). ev_12dcd56b has 2528 objects (2526 measurements, 1 command, 1 confirmation). Across both windows, P/N=1, T=1, IV, NT, SB, BL and OV each occur 0 times. All 18 control objects are Execute; no Select was sent.

| Field | Raw packet | tshark | Old index (parser `6a0c162`) | New index |
| --- | --- | --- | --- | --- |
| COT P/N | present on all objects | decoded | parser did not request the field; not stored | present in all layers |
| COT T (test) | present on all objects | decoded | parser did not request the field; not stored | present in all layers |
| Select/Execute | present on SCO and QOS commands and confirmations | decoded | parser did not request the field; not stored | present in all layers |
| QDS.IV and NT/SB/BL/OV (measurements) | present on 6874 objects | decoded | parser did not request the field; not stored | present in all layers |
| SIQ.IV and NT/SB/BL (COT=3 reports) | present on 6 objects | decoded | parser did not request the field; not stored | present in all layers |
| Control value, type 45 SCO | present on 12 objects (6 commands, 6 confirmations) | decoded | requested, but text `True/False` was left as `unparsed_value` | present in all layers |
| Control value, type 50 float | present on 6 objects (3 commands, 3 confirmations) | decoded | present | present |
| State report value, type 1 SPI | present on 6 objects | decoded | requested, but dropped as unparsed; not stored | present in all layers |
| Quality on commands | absent from the element (SCO/QOS carry no quality) | — | — | stays `None`; not counted as good |

No field fell into `tshark_not_decoded` or `db_not_stored`. The old loss was entirely at the parser layer (`parser_not_read`), so the old databases had nothing to store.

### IPAL parent and lineage

`01-Basic/test.n302.state.gz` records have only `timestamp`, `state` and `malicious` (the `malicious` value was not read into any output). Records are 1 s apart with one fractional second per window. They hold no frame number, TCP sequence, address or other packet reference.

Electrical rows with `parent_evidence_id`: 0 of 2416 (ev_0961), 0 of 1419 (ev_12dcd56b), in both old and new indexes. The new rows say `packet_lineage=not_present_in_ipal_state_source`. No IPAL row has the same timestamp as an IEC-104 row of the same CA/IOA; the nearest gap is 0.58 ms / 3.1 ms minimum and 0.50 s / 0.72 s median. The parent is absent from the raw source. No parent was assigned from time, and IPAL rows stay `unconfirmed_temporal_correspondence` with `counts_as_independent_source=false`.

## Test bit and acceptance

Before R4, a command with T=1 could pass the gate, because T was neither read nor checked. The gate now requires T decoded and clear on the command, its confirmation, the pre-command observation and the post-command observation (`*_test_bit_set`, `*_test_bit_unknown`, `test_bits_unknown`). A COT=7 whose P/N was not decoded now fails as `command_acceptance_unknown`.

## Counterexample tests (`tests/test_reconstruction.py`)

- Two ASDUs (types 13 and 50) in one frame keep their own COT, T, APCI tx, value and quality. The command gets no quality.
- `qds.iv` with one occurrence for two IOAs leaves both objects' IV unknown and is not broadcast. Other bits with matching counts stay aligned.
- A QDS with only IV decoded keeps NT/SB/BL/OV as `None` and `quality_good=None`.
- Gate: acceptance unknown, flags unknown, one flag set, IV set, test bits unknown, and T set on command, confirmation or post observation each fail with their own condition.
- End to end, through transaction, event graph, storyline, report and the consistency file, for each of T=1 on the command, T=1 on the post measurement, NT=1 on post, OV unknown on pre, and P/N unknown. Every case stays unresolved with no `supported_inference`, and the four phases agree.
- The consistency checker reports a graph that upgrades an edge after the gate failed.
- The raw byte decoder reads per-object QDS, COT P/N and T, SCO value and S/E. It produces no object for a truncated information object.

## Results compared with R3

The engine and its thresholds are unchanged: shift above 1 % of the baseline, movement toward the setpoint, and post value within 2 % of the setpoint. `quality_consistency.json` reports `consistent=true` with no issues on both windows. Lineage export is 312/312 and 149/149.

### ev_0961f1c2da8a257e3ebc

Graph: 34 nodes, 45 edges. R3 had 0 `supported_inference` and 4 unresolved. R4 has 1 `supported_inference` and 3 unresolved.

| Transaction | R3 | R4 | Reason |
| --- | --- | --- | --- |
| TX001 `switch.23` | acceptance unknown, value unknown | accepted (P/N=0), command 1, COT=3 report 1, `state_report_observed_no_pre_baseline` | no IEC-104 value before the command |
| TX002 `switch.24` | same | accepted, command 0, report 0, `state_report_observed_no_pre_baseline` | no baseline |
| TX003 `switch.25` | same | accepted, command 0, report 0, `state_report_observed_no_pre_baseline` | no baseline |
| TX004 `sgen.6` | `measurement_observed_transition_unverified` (`pre/post_quality_unknown`) | `verified_measurement_transition` | 40004.5312 → 20000.6875, setpoint 20000.0; IV and other QDS bits 0, T=0 on all four packets, P/N=0 |

Actual chain SL004 (contiguous, 4 nodes, 3 independent sources):

1. EF013 `C_SE_NC_1` setpoint 20000.0, COT=6, Execute, T=0, at 1742961084.406. Observed.
2. EF014 COT=7 confirmation, P/N=0, T=0, at 1742961084.438. Observed protocol reply.
3. EF016 `sgen.6:active_power` 20000.6875, QDS good, T=0, at 1742961093.099. Edge EF014→EF016 is a `supported_inference`: a non-causal alignment of command and measurement, not proof of physical actuation.
4. EF018 IPAL `sgen.6:active_power` 20000.6875 at 1742961093.858. Temporal correspondence only, not an independent source.

Supporting edge: EF015 pre-command 40004.5312 (QDS good) → EF016.

SL001–SL003 stay `partial_state_report_observed_transition_unverified`: command → confirmation → COT=3 report.

### ev_12dcd56b2f5e78144cfb

Graph: 29 nodes, 40 edges. R3 had 0 `supported_inference` and 1 unresolved. R4 has 1 `supported_inference` and 0 unresolved.

| Transaction | R3 | R4 | Reason |
| --- | --- | --- | --- |
| TX001 `sgen.10` | `measurement_observed_transition_unverified` | `verified_measurement_transition` | 309980.938 → 269971.625, setpoint 270000.0 (0.011 % off); quality good, T=0, P/N=0 |

Actual chain SL001: EF001 setpoint 270000.0 (COT=6, Execute) → EF002 COT=7 accepted → EF004 `sgen.10:active_power` 269971.625 (`supported_inference`) → EF006 IPAL 269971.625 (temporal correspondence). Supporting edge: EF003 pre 309980.938 → EF004.

## Still limited

- Only two windows were reindexed. `ev_3e4d36008b29595ef246` and the rest of Sherlock v3 still use pre-R4 indexes.
- No real packet in these windows has T=1, P/N=1, a set quality bit or Select. Those paths are covered only by the counterexample tests.
- The switches have no IEC-104 value before the command, so their effect stays unresolved.
- IPAL cannot be tied to a packet because the source has no packet reference.
- The two verified transitions are protocol and measurement alignment. They do not establish causation or physical actuation.
