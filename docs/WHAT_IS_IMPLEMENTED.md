# Implemented vs not yet implemented

| Capability | Current status |
| --- | --- |
| New, standalone package | Implemented |
| Sherlock ZIP native read (exact member) | Implemented. Basic v3 member layout checked on Mac; Semiurban and Rural checksummed only |
| IPAL reported electrical snapshot read | Basic train JSONL (`timestamp` + `state`) checked. Values stay network-reported |
| Classic PCAP Ethernet IPv4 TCP ARP | Basic train captures are classic Ethernet PCAP. IPv6, OSPF, TCP reassembly, and IEC104 ASDU are not decoded |
| Full IEC104, TCP stream reassembly, PCAPNG | NOT IMPLEMENTED |
| Bounded window time grid / per-flow or per-value nodes | Implemented |
| Learned GRU temporal representation | Implemented |
| Learned row-normalized adjacency | Implemented; not calibrated edges. On the Basic smoke fit the rows are near-uniform softmax |
| Multi-type edges N-N / P-P / N-P | Implemented as learned display links |
| Forecast MAE and no-graph ablation | Implemented, needs fair real data eval |
| Edge ablation/graph stability multi-seed | NOT IMPLEMENTED |
| True masked reconstruction | NOT IMPLEMENTED; forecasting objective only |
| Train/test split automation / leakage audit | NOT IMPLEMENTED (user provides separate paths) |
| Interactive offline HTML + JSON/GraphML | Implemented |
| Ollama graph explanation interface | Implemented (not run locally here) |
| LLM evidence-ID hallucination validator | NOT IMPLEMENTED |
| Incident hypothesis inference | NOT IMPLEMENTED; LLM can propose, not scored |
| Edge calibrated correctness probability | NOT IMPLEMENTED (no independent labels) |
| Sherlock paper-grade benchmark | NOT IMPLEMENTED |
