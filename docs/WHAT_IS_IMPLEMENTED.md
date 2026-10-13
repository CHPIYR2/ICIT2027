# Implemented vs not yet implemented

| Capability | Current status |
| --- | --- |
| New, standalone package | Implemented |
| Sherlock ZIP native read (exact member) | Implemented. Basic v3 member layout checked on Mac; Semiurban and Rural checksummed only |
| IPAL reported electrical snapshot read | Basic train JSONL (`timestamp` + `state`) checked. Values stay network-reported |
| Classic PCAP Ethernet IPv4 TCP ARP | Basic train captures are classic Ethernet PCAP. IPv6 and OSPF are still skipped by the flow counter |
| IEC-104 CA/IOA | Official `ipal-transcriber` 1.4.4 is called for checks. One Basic slice matched the published state 1767/1767. The package does not reimplement ASDU decoding |
| Alias collapse and evaluator-field rejection | Implemented. `malicious` and event text are dropped. Equal `closed`/`is_closed` and `connected`/`is_connected` pairs become one node |
| Bounded window time grid / per-flow or per-value nodes | Implemented |
| Learned GRU temporal representation | Implemented |
| Sparse low-rank gates | Default. Independent sigmoids plus a 3×3 block bias, so N–N, P–P, and N–P can each stay closed. Not calibrated probabilities |
| Legacy row-softmax adjacency | Still available with `--association softmax`. The first Basic smoke was near-uniform |
| Multi-type edges N-N / P-P / N-P | Display links only. The model does not force a cross-modal edge |
| Forecast comparison | `mirage-ot study` runs no-graph, sparse, random-graph, and shuffled-graph for network, physical, and both, on disjoint windows and multiple seeds |
| Edge precision / relation gold | NOT IMPLEMENTED |
| True masked reconstruction | NOT IMPLEMENTED; forecasting objective only |
| Train/eval leakage check | Overlapping windows are rejected. Normalization is fit on the train matrix only |
| Interactive offline HTML + JSON/GraphML | Implemented |
| Ollama graph explanation interface | Implemented (not run locally here) |
| LLM evidence-ID hallucination validator | NOT IMPLEMENTED |
| Incident hypothesis inference | NOT IMPLEMENTED; LLM can propose, not scored |
| Edge calibrated correctness probability | NOT IMPLEMENTED (no independent labels) |
| Sherlock paper-grade benchmark | NOT IMPLEMENTED |
