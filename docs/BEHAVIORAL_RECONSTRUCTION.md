# Behavioral Incident Reconstruction (no IEC-104 control command)

Base: R4 (`b1edb00`). Data: Sherlock v3, `01-Basic`, windows indexed under `runs/etgi/behavioral-20261015/`.
Transaction, Temporal Graph, Storyline and Report are unchanged in role; this round adds event anchors as a second
way to root storylines when a window has no control transaction.

## 1. Two reliability fixes

1. **Quality inconsistency withholds verification.** The report starts as `pending_quality_consistency_check`.
   `apply_quality_consistency()` sets `quality_consistent`, or `diagnostic_only_quality_inconsistent`. In the second
   case `verified_device_transitions` is emptied into `withheld_verified_device_transitions`, the issues are copied,
   the Markdown title says "DIAGNOSTIC ONLY, NOT VERIFIED", and every transaction and storyline line is tagged
   "WITHHELD". All other artifacts are still written.
2. **IPAL alignment is not a common source.** An IEC-104 fact and an IPAL row of the same point with no lineage are
   joined by `temporal_correspondence / temporally_aligned_same_point_stream`, status `common_source_unconfirmed`.
   `shared_source` is kept for parent-lineage derivation and for objects in one IEC-104 frame or ASDU. Correspondence
   edges never form a storyline step; storylines list them under `temporal_correspondences` with
   `common_source_status=unconfirmed_no_lineage`.

   The P0 storyline test changed accordingly: the `sgen.6` spine is command, confirmation and post-command
   measurement (3 nodes, 2 steps). The IPAL row is a correspondence of the last node. Independent containers stay 3.

The frozen T2/T3 module `postalert/relations.py` still names a same-point pair `shared_source`. Reconstruction
outputs do not use it, and it was left unchanged to keep that protocol frozen.

## 2. Which Basic windows have no control command

`scripts/screen_basic_windows.py` streams both mirror PCAPs (`switch-n302-pcap-mir2`, `switch-n318-pcap-mir3`) from
the ZIP and counts IEC-104 objects in `[start - 15 s, end]`. Window times come from episode id, start and end only
(`windows_times_only.json`); no label, attack type or `physical.zip` field is read, and the reconstruction never
sees the catalog.

Of 28 Basic test windows, 12 contain no control object (type 45–69). They fall into three observation profiles:

| Profile | Windows | Network observations besides periodic M_ME_NC_1 (COT=1) |
| --- | --- | --- |
| Spontaneous state report, then measurements drop | `ev_564beb`, `ev_4e913b`, `ev_b15ac1`, `ev_9c2ee5`, `ev_52f5ee` | 1–2 M_SP_NA_1 COT=3 |
| Link loss and re-establishment | `ev_812f80`, `ev_cbe1e5` | FIN/RST, unanswered SYN, general interrogation (COT 6/7/10/20), clock sync; `ev_cbe1e5` also 137 ARP and 2 UDP |
| Periodic measurements only | `ev_21f185`, `ev_d58f41`, `ev_a34715`, `ev_19f98c`, `ev_0c16cb` | none |

There is no grid topology in the data. `initial_state.json` holds initial values; the data point map gives
element, attribute and CA/IOA. A line has a `from` and a `to` side, each reported by the RTU at that end.

## 3. Event Anchor Discovery (`reconstruction/anchors.py`)

Rows are read from the window and its 15 s background. Mirror captures of one information object (same 4-tuple,
APCI send sequence, ASDU index, CA/IOA, object index, within 0.5 s) become one observation.

| Anchor | Rule |
| --- | --- |
| `spontaneous_state_report` | M_SP/M_DP (types 1, 3, 30, 31) with COT=3. Status: `state_change_observed` only when a prior IEC-104 value differs and both quality and T bits are decoded good; otherwise `state_report_no_prior_value_in_window`, `state_report_same_as_prior`, `state_report_value_undecoded` or `state_change_quality_or_test_bit_unverified`. |
| `measurement_step` | Consecutive samples of one point: `to_zero` / `from_zero` (one side within 1e-6 of the other's magnitude), or `level_shift` (≥ 50 % relative change) that persists in a later sample before any reversion. Both values below 1e-3 are ignored. Steps are grouped per ASDU and element. |
| `communication_change` | Per master–RTU link: FIN/RST, SYN answered or unanswered, general interrogation, clock synchronisation, interrogated objects, telemetry gap (≥ 25 s and ≥ 3× the background cadence). |
| `arp_activity_increase` | Per source host: ≥ 10 packets and ≥ 5× the background rate. |

Anchors are numbered by time (`A001`…) and ranked by a fixed score. IPAL rows of the anchor's points (or, for a state
report, of the same element) within [−0.5 s, +2.5 s] are attached as `ipal_rows`. The method has no attack names
and no attack-specific rules.

## 4. Graph relations (`reconstruction/behavior.py`)

Without a transaction, each anchor becomes a fact (`BA…`) and its IPAL rows one non-independent fact (`BI…`).

| Relation | Condition | Level |
| --- | --- | --- |
| `same_device_behavior_in_separate_asdu` | same element, separate ASDU, 0–15 s | `measurement_state_transition`, supported; independent only when the RTUs differ |
| `same_iec104_asdu` | different elements in one ASDU | `shared_source`; reported together, no device relation |
| `cross_device_temporal_candidate` | different elements, separate messages, 0–15 s, ≤ 6 per anchor | `temporal_cooccurrence`, unresolved; shared RTU, master or ARP target is noted as context only |
| `temporally_aligned_same_point_stream` / `..._same_device_ipal_row` | IPAL rows of the anchor | `temporal_correspondence`, common source unconfirmed |

`audit_anchor_lineage()` checks each anchor evidence row against the point (entity, CA/IOA, pre or post sample
time), link hosts or ARP host it is cited for.

## 5. Behavioral storyline search

Roots are anchors in time order. Beam search may step only over supported `direct_protocol_relation` or
`measurement_state_transition` edges between anchors, and never into an anchor already on a storyline, so each anchor
sits on exactly one storyline. A single-anchor storyline is allowed. Each storyline carries `reconstructed_behavior`,
its supported steps, `co_reported_in_same_asdu`, `temporal_correspondences`, outgoing and incoming unresolved
branches, and `not_reconstructed`.

## 6. Milestone: `ev_564bebaa45f0686cf98d`

Window 180.2 s, 0 control objects, 7562 IEC-104 rows, 3470 IPAL updates, 0 TCP SYN/FIN/RST, 2 ARP. Times are relative
to the window start.

Anchors: 32 (2 state reports, 30 measurement steps). The early sequence:

- +0.896 s `A001`: RTU .16 reports `switch.13:is_closed=0` (COT=3); no prior IEC-104 value in the window.
- +4.391 s `A002`: `line.0` from-side power −404 kW → −1287 kW.
- +5.645 s `A003`–`A006`: one ASDU from RTU .18; `bus.5`, `line.3` to-side, `line.4` from-side and `load.3` all → 0.
- +6.046 s `A007`: RTU .16 reports `switch.14:is_closed=0`.
- +6.55–6.78 s `A008`–`A011`: `line.0` to-side, `line.1` both sides rise ~3×; `line.2` from-side → 0.
- +7.77–7.84 s `A013`–`A017`: RTU .22 `bus.6`, `line.12` from-side, `line.4` to-side, `load.4` → 0; RTU .24 `line.12` to-side → 0.
- +7.66–9.75 s: `sgen.1`, `sgen.3`, `storage.0`, `sgen.2`, `sgen.9` → 0.
- +10.695 s `A022`–`A025`: RTU .16 `bus.4`, `line.2` to-side, `line.3` from-side, `load.2` → 0.
- Later: small current level shifts on `line.13`, `line.14`, `line.2`.

Every step has good quality and is sustained in later samples. The 24 behavioral storylines include 8 with a
supported relation:

| Storyline | What it reconstructs | Supported relation |
| --- | --- | --- |
| `A004 → A024` | `line.3` to-side (RTU .18, +5.645 s) and from-side (RTU .16, +10.695 s) both → 0 | same element, two RTUs |
| `A005 → A015` | `line.4` from-side (.18) and to-side (.22) both → 0 | same element, two RTUs |
| `A014 → A017` | `line.12` from-side (.22) and to-side (.24) both → 0 | same element, two RTUs |
| `A011 → A023` | `line.2` from-side (.14) and to-side (.16) → 0 | same element, two RTUs |
| `A002 → A008` | `line.0` power magnitude rises ~3× at both ends (RTU 172.16.2.3, then .13) | same element, two RTUs |
| `A009 → A010` | `line.1` rises ~3× at both ends (.13, .14) | same element, two RTUs |
| `A028 → A029`, `A030 → A031` | later current shifts at both ends of `line.2` and `line.14` | same element, two RTUs |

These chains say that one line was observed to change at both ends by separate RTUs. They do not say why.

Single-anchor storylines: both switch reports, `bus.5`, `load.3`, `bus.6`, `load.4`, `bus.4`, `load.2`, the four
generators and storage, and the remaining current shifts.

**Candidates, not relations.** 129 `cross_device_temporal_candidate` branches remain unresolved, e.g. `switch.13`
(+0.896 s) → `bus.5`/`line.3`/`line.4`/`load.3` (+5.645 s), `switch.14` → `line.0`/`line.1`/`bus.6`, and the
generator drops after the bus drops. The switch-to-line links are plausible to a reader, but nothing in the data
(no topology, no shared message, no protocol link) supports them, so they stay candidates. 20 `same_iec104_asdu`
edges record which elements one RTU reported together (e.g. `bus.5`, `line.3`, `line.4`, `load.3` from RTU .18).

Quality consistency is true; both lineage checks have 0 failures (192 anchor evidence references checked).

## 7. Other no-command windows

| Window | Anchors | Result |
| --- | --- | --- |
| `ev_4e913b` | `sgen.0:is_connected=0` COT=3 (+1.19 s), `sgen.0` power 20000 → 0 (+10.84 s), two current shifts | `A001 → A002` supported (same element, separate ASDU); not independent because both come from RTU .15 |
| `ev_812f80` | link to RTU .22: 125.6 s telemetry gap, FIN, 34 unanswered connection attempts; link to .23: 36 unanswered attempts; both re-established, then general interrogation and clock sync | two single-anchor storylines; their relation is one unresolved candidate (shared master) |
| `ev_cbe1e5` | ARP from .28 (125 replies to .9/.10/.20, none in background); links to .10, .20, .9 lost and re-established; current shifts | 7 single-anchor storylines; ARP → link candidates note "ARP from .28 addressed .10 (63 packets)" but stay unresolved |

## 8. Limits

- No topology: a switch report and line drops cannot be connected, even when they look related.
- IPAL state rows have no packet reference: always temporal correspondence, never a source.
- Windows with periodic measurements only and no step produce few or no anchors.
- Anchor parameters are fixed constants and were set on these Basic windows.

## 9. Reproduce

```bash
.venv/bin/python scripts/screen_basic_windows.py --archive data/raw/sherlock/v3/01-Basic.zip --recording <recording> \
  --windows runs/etgi/behavioral-20261015/windows_times_only.json --out runs/etgi/behavioral-20261015/window_screen.json
.venv/bin/python -m mirage_ot.etgi.cli reconstruct \
  --db runs/etgi/behavioral-20261015/index/ev_564bebaa45f0686cf98d/evidence.sqlite \
  --out runs/etgi/behavioral-20261015/reconstruction/ev_564bebaa45f0686cf98d --no-llm
```

Outputs: `event_anchors.json`, `event_graph.json`, `behavioral_storylines.json`, `unresolved_branches.json`,
`storylines.json`, `investigation_report.md/.json`, `evidence_audit_bundle.json`, `quality_consistency.json`,
`run_manifest.json`.
