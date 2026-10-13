# Basic data-quality audit — Mac continuation, 2026-10-14

Pipeline check only. Nothing in this file is a paper metric, an edge-accuracy
number, or a claim that MIRAGE-OT has explained a Sherlock event.

The model inputs were observations from one train-split window. Event
descriptions were used only to choose the clock interval and were not written
into the feature sidecar.

## Git and data mount

- Worktree: `/Users/potinglu/Documents/ICIT2027-mirage`
- Branch: orphan `mirage-ot`, no commit yet. The original worktree stays on
  `ebrl-investigation`.
- Sherlock v3 is a symlink, not a copy:
  `data/raw/sherlock/v3` → `/Users/potinglu/Documents/ICIT2027/data/raw/sherlock/v3`
- `.gitignore` keeps `data/` and `runs/` untracked.
- MD5 matches the handoff values:
  - `01-Basic.zip` `c482e0dc7e56b063b357d8b03be5cce6`
  - `02-Semiurban.zip` `0f7d3eb61e478d05f4b431ae99d45564`
  - `03-Rural.zip` `0cc7807bd5a76ea5bc85a1da6fd6c061`
- Semiurban and Rural were not opened. `01-Basic/raw/train/physical.zip` is
  present and the loader refuses it.

Environment: CPython 3.14.6, PyTorch 2.14.1, Apple M4. `pytest -q` → 9 passed.
The real fit used `--device cpu`.

## Basic archive layout

`mirage-ot inspect-archive` reports 118 members, 2 `.state.gz` files, 8 classic
`.pcap` files, and `physical.zip` in both train and test. State and packet
paths used here:

- `01-Basic/train.n302.state.gz`
- `01-Basic/raw/train/pcap/switch-n302-pcap-mir2.pcap` (the only capture fed to the model)
- The other train vantages were scanned for overlap and not loaded into the matrix.

Train state is JSONL, one object per second: `timestamp` plus a flat `state`
dictionary. 43,204 rows, 2025-03-09 21:29:16.202Z through 2025-03-10 09:29:19.202Z
(43,203 s). The n302 PCAP is classic little-endian microsecond Ethernet
(`magic d4c3b2a1`, linktype 1), 618,591 packets, starting about 13 ms earlier
than the state file and ending inside the same second. Ten-second bins therefore
share a clock. That does not show that an IEC104 point and a state key are the
same measurement: the PCAP parser never decodes ASDU values.

## Window used for the executable example

| Role | Unix interval | UTC | Contents |
| --- | --- | --- | --- |
| Fit only | 1741560200–1741560550 | 2025-03-09 22:43:20Z–22:49:10Z | No labeled train event |
| Graph and forecast check | 1741560550–1741560900 | 22:49:10Z–22:55:00Z | Contains train event 0 |

Train event 0 is the benign interval labeled `control center:Cable Maintenance`,
22:50:39.471Z–22:51:39.674Z. The next labeled train interval starts at
1741565014, outside this window. The dataset test split starts on 2025-03-25
and was not read.

Both matrices are `(35, 534, 8)`: 470 physical keys and 64 TCP flows, with
`dropped_channel_counts` of 0. Node entity sets match. Sidecars contain no
event-description strings. `physical.zip` was not an input.

`--max-state-rows` and `--max-packets` were not used. Those caps count from the
start of the member, so a small cap would stop before a window this far into
the capture.

## Measurement and configuration

`data-point-map.json` has 500 IOA rows: 373 `MEASUREMENT` and 127
`CONFIGURATION`. There is no context named `SETPOINT`. Commanded quantities
appear as configuration attributes such as `target_active_power`.

The state snapshot has 470 keys, all of which join to that map:

- 358 measurement keys
- 110 configuration keys
- 2 collisions: `trafo.0:tap_position` and `trafo.1:tap_position` are each both
  measurement and configuration, so one number cannot be split
- 28 map rows are absent from the snapshot: 15 `target_cos_phi` and 13
  `profile_percentage`

Where the attribute names differ, measurement and target stay on separate
channels. In bin 17 of the event window the raw mean and the matrix mean match:

| Entity | Role | Raw mean | Matrix feature 0 |
| --- | --- | ---: | ---: |
| `bus.0:voltage` | measurement | 1.029622638 | 1.029622674 |
| `sgen.0:active_power` | measurement | 19997.50390625 | 19997.50390625 |
| `sgen.0:target_active_power` | configuration | 20000 | 20000 |
| `switch.8:closed` | configuration | 1 | 1 |
| `switch.8:is_closed` | measurement alias | 1 | 1 |

`closed`/`is_closed` and `connected`/`is_connected` are duplicate aliases.
Across 22,750 alias pairs in this window there were 0 disagreements. Both
copies are kept as nodes, so those series are scored twice. The loader does
not attach the map context; separation is only the key string.

Provenance is kept. `bus.0:voltage` has 350 source rows and the node stores a
16-id sample. Network nodes cite packet ids such as
`01-Basic.zip:.../switch-n302-pcap-mir2.pcap#packet=62021`.

## PCAP decode coverage

Window 1741560550–1741560900. “Emitted” means the current parser yielded a TCP,
UDP, or ARP observation. It does not mean IEC104 was decoded.

| Vantage | Packets | Emitted | Not emitted | What was skipped | Directed flows |
| --- | ---: | ---: | ---: | --- | ---: |
| n302 | 4585 | 4550 (99.24%) | 35 | OSPF (IP protocol 89) | 64 |
| n318 | 883 | 840 (95.13%) | 43 | 35 OSPF + 8 IPv6 | 12 |
| n303 | 736 | 700 (95.11%) | 36 | 35 OSPF + 1 IPv6 | 10 |
| n321 | 182 | 140 (76.92%) | 42 | 35 OSPF + 7 IPv6 | 2 |

Every emitted packet in this window is TCP on port 2404, flagged
`iec104_candidate`. ASDU, CA, and IOA coverage is 0. There is no TCP
reassembly and no retransmission dedup. IPv6 and OSPF are ignored, not failed
parses of a supported header.

No two vantages shared a full-frame fingerprint (timestamp plus frame hash).
The conversations still overlap: every directed flow at n318, n303, and n321
is also present at n302 (12/12, 10/10, and 2/2). Merging those captures on the
5-tuple would count the same conversation more than once. This run did not
merge them.

## Train / eval isolation and the baseline that was actually run

Normalization is fit on the earlier window and stored in the checkpoint.
`evaluate` applies that checkpoint; it does not refit on the later window.
The two windows are adjacent slices of one recording, so they are dependent.
This is not the protocol’s attack-free Basic/Semiurban train versus held-out
Basic, Semiurban, and Rural test.

Shared smoke settings, trained separately:

- GRU hidden 16, input 8 features plus a 2-d modality indicator
- next-bin smooth-L1, AdamW learning rate 0.003
- context length 12, 2 epochs, 16 steps per epoch, seed 20261014
- graph model uses row-softmax query/key attention with the diagonal masked
- `--no-graph` zeros the message and is a second fit, not a flag flipped at eval
- seed is hardcoded; multi-seed is not available from the CLI

Wiring-check forecast MAE on the 23 later samples, normalized, not citable:

- graph checkpoint: 0.1996
- no-graph checkpoint: 0.1945

The learned attention is a flat softmax. Median entropy is 6.2746 against a
uniform entropy of 6.2785 (ratio 0.9994). The displayed top-2 edges hold about
0.56% of each row. `graph.html` says so. Those edges are a drawing of an almost
flat distribution, not identified N–N, P–P, or N–P relations.

Not run, and still required before a paper claim: a validated IEC104
transcriber, multi-vantage dedup, multi-seed and shuffled-edge controls,
network-only / process-only ablations, the official test split, bootstrap
intervals, calibration, and any edge precision or recall. There is no
relation gold. LLM reporting was not called.
