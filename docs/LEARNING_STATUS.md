# Learning status after the first Basic semantic pass

This is a bounded Mac check on Sherlock v3 Basic train. It is not a paper result.
Sherlock v3 was not replaced, and no earlier project code was imported.
LLM explanation was not run.

## Where the state file comes from

Published member: `01-Basic/train.n302.state.gz` inside `01-Basic.zip`.
Sherlock documents this as the IPAL timeslice state for the control-center
vantage. The official command is `ipal-transcriber --protocols iec104` with
`01-Basic/ipal/rules.py`, `01-Basic/ipal/train/initial_state.json`,
`--short-state-keys`, and the `timeslice` extractor. The dataset transcription
also passes `01-Basic/ipal/train/events.json` through `--malicious`. Each
published row therefore has `timestamp`, `state`, and `malicious`.

`malicious` is ignored. A positive value cannot become a node. Event
descriptions are not read while building features. Re-transcription for the
check below did not pass `events.json` or `--malicious`.

## Official IEC-104 check

`ipal-transcriber` 1.4.4 (`18fe5fba`) and tshark 4.6.9 decoded
`switch-n302-pcap-mir2.pcap` from 1741560639 to 1741560700.
409 IPAL messages, 1,767 CA/IOA points compared with the next published
timeslice, 1,767 matches.

| Activity | Messages | What they were |
| --- | ---: | --- |
| confirmation | 202 | S frames |
| inform | 201 | I-13 measured floats and I-1 single points |
| command | 3 | I-45 single commands |
| action | 3 | I-45 activation confirmations |

Example: CA 129 IOA 10130 is `switch.1:closed` (command); IOA 10140 is
`switch.1:is_closed` (inform). On the 350 s feature windows, all 65 alias
pairs agreed and were collapsed. Zero pairs disagreed. Two transformer
`tap_position` keys remain ambiguous because the point map marks each as both
measurement and configuration. 190 of 405 physical channels in the first train
bin still equal `initial_state.json` (46.9%). That is hold-forward state, not
a fresh sample, and it is not copied in from the evaluation window.

## Sparse association model

The default graph is no longer a row-softmax. Each directed gate is

`sigmoid(q_i · k_j / sqrt(rank) + b[kind_i, kind_j])`

with rank 8 and a 3×3 block bias for network, measurement, and configuration.
The diagonal is zero. Gates are not normalized to sum to 1, and no term
requires a cross-modal edge. A small L1 penalty keeps unused gates closed.
`--no-graph` trains a separate model. `--freeze-association` is the random-graph
control. Evaluation can permute gate columns as the shuffled-graph control.

## Unseen-window comparison

Train 1741560200–1741560550. Evaluation 1741560550–1741560900. The study
refuses an overlap. Normalization comes from the train matrix. Seeds 1–3,
8 epochs, hidden 32, at most 32 steps, CPU. Matrices are 64 network nodes and
405 physical nodes after alias collapse.

Sparse minus no-graph forecast MAE (negative would be a gain):

| Subset | Seed 1 | Seed 2 | Seed 3 |
| --- | ---: | ---: | ---: |
| network | -0.0014 | +0.0034 | +0.0146 |
| physical | +0.0532 | +0.0144 | +0.0385 |
| both | +0.0649 | +0.0447 | +0.0395 |

Random gates, which stay near 0.5, increase MAE. Learned gates stay near 0.02,
and fewer than 0.2% exceed 0.2. A train-variation filter of 0.001 removed no
nodes, so the result is not caused by dropping static channels.

The sparse parameterization can represent N–N, P–P, and N–P relations and can
also represent no edge. On this unseen window it does not improve the forecast.
Displayed top-k edges are not identified event relations. The data scale should
stay here until a later model shows a consistent gain on a disjoint window.
