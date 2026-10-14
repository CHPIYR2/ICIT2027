# Evidence-grounded post-alert investigation

The investigation now starts from a supplied time window. It selects observations, builds one timeline, records candidate relations, asks Qwen for structured claims, and publishes a claim only after the indexed rows agree. The earlier agent, memory, and subgoal runs stay in their original directories. They are not the pipeline.

## What the pipeline does

Selection reads the evidence table for the window and an optional background interval. A hold or an initial fill is excluded as forward-filled state. An IEC-104 row with a parent packet is kept on the timeline and counted as the same packet, not as a second independent observation. TCP flows, decoded packets, and electrical updates are ranked by change against the background, whether a value is present, and whether a device or CA/IOA name is present. IEC monitor/control/system is the decoder class, not an attack label. The exclusion counts and the query bounds are written to `selection.json`.

The timeline has a time, an entity, a source, an observation, and evidence ids. Roles are communication, command, response, electrical report, and electrical change. Packet rows are direct observations. IEC-104 and IPAL electrical updates are transcriptions of network-reported data. The same TCP 5-tuple at more than one switch is one communication. The same Ethernet frame is one event.

A bidirectional TCP capture, two attributes of one device, or an IEC-104 point joined to the IPAL name of that point is an `observed_fact`. A pair within 2 seconds that shares only time is `temporal_cooccurrence` and stays unresolved. A shared device stem can be `supported_inference`. A shared IP address is not enough. No relation is marked as a cause.

Qwen3.5 9B receives the window, and, depending on the condition, a short summary, eight timeline events, or those events plus six relations. It does not choose tools. Each claim is checked for evidence-id existence, entity or CA/IOA, time, value, direction, duplicate packet identity, and whether the claimed level matches a timeline relation. A failed claim is stored with the reason. If none of the model's inferred claims pass, the report is the verified timeline and the record links, and it says that no inferred relation was confirmed.

## Runs

Model `qwen3.5:9b-q4_K_M`, temperature 0, seed 1, `num_predict` 512, `num_ctx` 8192. Official event text was not an input. The windows were already used in development. This is not a confirmatory test.

`runs/etgi/postalert-20261014` sent the longer timeline. B2–B4 used the 512-token budget on prose and produced no parseable claims. B4 still wrote the timeline and the record links.

`runs/etgi/postalert-bounded-20261014` sends at most eight events and six relations, and asks for a JSON object. Closed claim objects are kept when the object is cut off at 512 tokens. Citation validity below is the fraction of cited ids that are on the timeline.

| Case | Timeline events | Observed record links | Co-occurrence, unresolved | B0/B1 claims | B2/B3 cited ids valid | B4 claims published |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| supplied ev_0961 | 24 | 6 | 8 | abstain | 2 and 2 claims, all cited ids on the timeline | 0; value or relation check failed |
| preceding 15 s | 20 | 8 | 8 | abstain | 2 and 1 claims, cited ids valid | 0; entity, time, or value check failed |
| supplied ev_12dcd56b | 21 | 8 | 8 | abstain | 2 and 2 claims, cited ids valid | 0; entity, time, or value check failed |

On the supplied ev_0961 window the published B4 report lists the TCP directions, IEC-104 reports, and electrical updates with evidence ids, and it restates bidirectional TCP and same-device record links as observations, not causes. The model did describe those TCP sessions and cited ids from the timeline. The value field did not match the stored row, so those sentences stay in the rejection file and are not published as facts. No supported inference was confirmed on any of the three windows.

The lexicographic first electrical-update id was not in the selected 24. Selection keeps the highest background-relative changes, not that arbitrary id. There is no relation-graph gold, so edge precision is not reported.

Unit tests cover hold exclusion, same-packet collapse, TCP as an observed fact, time-only pairs remaining co-occurrence, rejection with the reason kept, and a truncated claim list.
