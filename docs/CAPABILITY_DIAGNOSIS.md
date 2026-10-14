# Direction after Table 3 and the capability checks

The goal is a report that explains one supplied time window with network and electrical rows. This note records why that work does not switch to anomaly detection, and what Qwen3.5 9B and Gemma 4 12B can do when the question is small enough to score.

## Sherlock Table 3 is not the next experiment

Wagner, Bader, Wolsing, and Serror, CODASPY 2025, Table 3 reports five process-aware detectors on 01-Basic after heavily filtering measurements affected by switching and maintenance. The paper says that filter is not feasible in a deployment, because any measurement may later be affected by a grid change. The filtered operating points are:

| Detector | Detected attacks | False alarms (benign-event alarms) | Average time to detection |
| --- | ---: | ---: | ---: |
| PASAD | 0/18 | 1 (0) | — |
| Invariant | 0/18 | 1 (0) | — |
| Seq2SeqNN | 7/18 | 10 (0) | 149.63 s |
| SIMPLE | 16/18 | 33 (33) | 81.43 s |
| GeCo | 15/18 | 94 (30) | 75.89 s |

Before that filter, PASAD and Invariant produced one continuous alert over most of the test data, and the other three were described as mediocre. A result that beats this table has to detect more of the 18 attacks and raise fewer false alarms, on that event-level protocol, without training on attack labels. A supervised row classifier with a high accuracy is a different task. This repository does not have a reproduction of the filtered operating point, and a better alarm would still not state which records support a claim. The downstream report remains the work.

## Capability checks

Same window, `ev_0961f1c2da8a257e3ebc`, already used in development. Temperature 0, seed 1, `num_predict` 256, `num_ctx` 8192. Gold comes from the evidence index. Official event text and attack labels are not in the prompts. Outputs are under `runs/etgi/capability-20261014`.

The first stored `correct` flag treated only JSON `true` as a yes, and only `relation_type=communication` as a TCP proposal. Both models answered the TCP question with a sentence beginning "Yes", cited both real packet ids, and described a bidirectional exchange. Qwen left `relation_type` null. Gemma wrote `bidirectional_tcp_exchange`. The checker now accepts a leading yes, that synonym, and a null type when the reason says bidirectional and both ids are cited. The rescored flags below use that checker. The raw replies are unchanged.

| Check | Qwen3.5 9B | Gemma 4 12B |
| --- | --- | --- |
| D1 read one electrical value | correct, 30002.75390625 | correct, the same value |
| D1 both directions of one TCP socket | yes | yes |
| D2 select that value's id from seven cards | exact | exact |
| D3 retrieve the value's id with one tool call | page contains the id; no JSON value returned | page contains the id; no JSON value returned |
| D4 propose the TCP pair | both ids, observed fact, bidirectional reason | both ids, observed fact, bidirectional reason |
| D4 two electrical rows within 2 s | abstain, `temporal_cooccurrence` | abstain, `unresolved` |

Qwen called `query_electrical_changes`. Gemma called `query_entity_timeline`. Neither call was a controller choice. On the coincidence pair, neither model promoted the rows to a communication, a shared source, or a cause.

D1 and D4 therefore succeed for both models when the prompt contains only the rows under judgment. D3 shows the break that the long investigations also hit: after a tool returns several rows, the next generation does not emit the value that is in the page. The two models do not separate on these checks, so the gap is not specific to the 9B model.

## What this changes

Another planner, memory, or agent role is not the next change. On a short card set the models can read a value, choose the relevant id, name a bidirectional TCP exchange with the real ids, and abstain when the rows only share time. On the full investigation state they still spend the turn on prose or on another retrieve, and they do not close the report.

The report path that matches these checks is a small, complete card set assembled from the indexed rows and the existing record links, with the model answering or abstaining on that set. A generation budget is reserved before the request: if the estimated prompt plus `num_predict` would fill `num_ctx`, earlier tool messages are dropped, and a call that still does not fit is recorded as `CONTEXT_LIMITED` without being sent. That status is separate from `NO_VALID_MODEL_ACTION`, `INCOMPLETE_BUDGET_EXHAUSTED`, and `MODEL_ABSTAINED`.
