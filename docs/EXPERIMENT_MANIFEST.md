# Experiment manifest

Reported runs use Sherlock v3 only. The ZIPs were not modified. MD5 checks at the start of this work matched the handoff: Basic `c482e0dc7e56b063b357d8b03be5cce6`, Semiurban `0f7d3eb61e478d05f4b431ae99d45564`, Rural `0cc7807bd5a76ea5bc85a1da6fd6c061`.

## What was visible before these runs

The event catalog in the earlier repository had already been read, including family descriptions. Clock bounds for the reported windows were taken from that catalog. The descriptions were not written into the investigator prompt, the tool results, or `configs/etgi/basic_ev0961.json`. These windows are not an unseen confirmatory split. Basic train intervals were also used while the earlier GRU prototype was being debugged. Semiurban and Rural labels had been inspected in that earlier work.

## Reported window

| Field | Value |
| --- | --- |
| Id | `basic-test-ev_0961f1c2` |
| Scenario / recording | 01-Basic / test |
| Start, end | 1742961051.1897168, 1742961125.4603136 |
| Context | 15 s on either side, indexed but not the question interval |
| Sources | `test.n302.state.gz` and the four test switch PCAPs |
| Not opened | `events.json`, `events.jsonl`, `physical.zip`, malicious flags |

A second window, Semiurban test `ev_0431e34c3ed30056a8f0` (1743640079.1774833–1743640109.233572, context 10 s), is one ETGI transfer run with tool cap 4. Rural was not run.

## Fixed before the reported runs

Model `qwen3.5:9b-q4_K_M` through Ollama at `127.0.0.1:11434`. Temperature 0. Gemma 12B was installed and was not run; the two models were not loaded together. Tool budget 6 for the Basic comparison and 4 for the modality and Semiurban checks. Necessity uses one relation, one repeat, and at most three cited ids. Page size is the tool default of 20, capped at 30 in some stratified contexts.

The packet-length bug (frame size treated as a measurement disagreement) was fixed before the reported ETGI run and before the suite. The earlier pilot is kept under `runs/etgi/basic-ev0961/pilot-packet-length-disputes` and is not a result row.

## Role of each run

| Run | Role |
| --- | --- |
| Basic ETGI | Case study of the full controller |
| Suite B0–B3 and six ablations | Same window, same model, same database |
| Network-only and electrical-only | Modality filter on that database |
| Semiurban ETGI | One transfer window, not a second full suite |

Question gold was computed from the index before the model answers were scored. No relation-graph gold exists, so edge precision and recall are not reported.
