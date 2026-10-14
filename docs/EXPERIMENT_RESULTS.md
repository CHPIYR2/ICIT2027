# Experiment results

One Basic test window, local Qwen3.5 9B, temperature 0. The run is a case study. It is not a confirmatory holdout, and it does not support edge precision, attack-type accuracy, or a claim that ETGI answers investigation questions better than the baselines.

## Index

The incident interval contains 1,759 new electrical values on 254 entities, 3,216 monitor-direction IEC-104 objects, 16 control-direction objects on 4 CA/IOA values, and 89 TCP flows. ARP count in the interval is 0. Shared Ethernet frame hashes across vantages: 0. tshark decoded every sliced ASDU row onto a packet (`iec104_unmatched` 0). Of 312 decoded values that had an IPAL sample of the same entity within 2 s, 312 matched. Electrical rows remain network-reported state.

Question gold from that index, written before scoring:

| Question | Gold |
| --- | --- |
| Control-direction CA/IOA values | 4 values, 16 evidence ids |
| Entities with a new electrical value | 254 entities, 1,759 ids |
| Frame hashes seen at two vantages | 0 |
| Control ASDU with a later reversed-socket ASDU within 5 s | 8 of 16 |
| Value of `EV-003297b621f443a0` | 30002.75390625 for `sgen.3:active_power` |

The gold id set has 1,775 ids after overlaps are removed.

## What the model did

On the full ETGI run the model did not emit a tool call during the search loop, including when Ollama was asked for a required tool call. The gap controller issued all 6 queries and the trace marks them `controller_gap`: IEC-104 (20 of 3,232), electrical changes (20 of 1,759), TCP flows (20 of 89), ARP (0), shared frames (0), and a window comparison. The closing call was `propose_relations` with an empty argument list, so no inferred edge was added. The narrative cited the timestamp 1742961053.85, which is not in the findings, and was discarded. Completion is `INCOMPLETE_BUDGET_EXHAUSTED` because the tool cap stopped the search. Prompt tokens 16,174, completion tokens 4,716, 12 model calls.

The published graph is the record-link graph after verification:

| Pair | Type | Status | Count |
| --- | --- | --- | --- |
| N–N | communication | supported | 7 |
| P–P | same_device | supported | 4 |
| N–P | shared_source | supported | 25 |

Citation validity on those edges is 1.0. None of the 36 supported edges fails the record-link check, so the unsupported-relation rate is 0. That rate is not edge precision. Temporal-order errors: 0. Source-dependency errors on published cross-modal associations: 0, because the cross-modal edges are labeled shared-source rather than independent confirmation.

Necessity was run on one communication edge, one repeat. The full judgment was stably `supported`. Removing each of three cited packet ids left the judgment `supported` (0 of 3 sensitive). One removal also hid a same-frame derived row. This does not show that the packets were unnecessary in the world. It shows that this model's supported judgment did not depend on any one of those three cards.

Question exact match is 1/5. The matched question is the shared-frame count, whose gold answer is 0, so an empty retrieval also matches. The other four questions do not match. Gold-id recall is 24/1,775.

## Baselines

Same database and model. B0 uses the earliest 20 rows, B1 a stratified sample, B2 the first 60 evidence ids already attached to record-link edges, B3 the tool loop without verification, necessity, dependency audit, or revision. B2 is not Microsoft GraphRAG.

| Method | Completion | Exact questions | Gold ids retrieved | Published supported | Edges left unresolved |
| --- | --- | --- | --- | --- | --- |
| B0 | COMPLETE | 1/5 | 4/1775 | 0 | 0 |
| B1 | COMPLETE | 1/5 | 19/1775 | 0 | 0 |
| B2 | COMPLETE | 1/5 | 0/1775 | 0 | 36 |
| B3 | budget exhausted | 1/5 | 24/1775 | 0 | 36 |
| ETGI | budget exhausted | 1/5 | 24/1775 | 36 | 0 |

B2's 60 ids are packet ids from the communication edges, which are not in the question gold, so recall is 0 even though citation validity on the unresolved edges is 1.0. B3 retrieves the same 24 gold ids as ETGI and does not publish any supported edge, because revision is off. ETGI does not answer more questions than B3.

## Modality filter

| Visible records | Supported N–N | Supported P–P | Supported N–P |
| --- | --- | --- | --- |
| Network only | 7 | 0 | 0 |
| Electrical only | 0 | 4 | 0 |
| Both | 7 | 4 | 25 |

Electrical-only still uses network-reported state. The 25 cross-modal edges appear only when both views are visible, and they are shared-source links. Hiding either view removes them rather than turning them into within-modality edges.

## Length diagnosis and interface comparison, 2026-10-14

The four saved Basic turns in `etgi-qwen-agentfix` each have `prompt_eval_count` 2050, `eval_count` 700, `done_reason` length, empty `tool_calls`, and about 2,200–3,081 characters of `message.content`. The trace did not store `message.thinking`. Replaying that same initial prompt against Ollama 0.32.5, saved under `runs/etgi/basic-ev0961/diagnostic-length-20261014`, shows where the budget went:

| Setting | prompt tokens | eval tokens | done_reason | thinking chars | content chars | tool call |
| --- | ---: | ---: | --- | ---: | ---: | --- |
| num_predict 700, thinking off | 2050 | 700 | length | 0 | 3081 | no |
| num_predict 2048, thinking off | 2050 | 2046 | length | 0 | 8983 | no |
| num_predict 700, thinking on | 2050 | 562 | stop | 1889 | 793 | no |
| num_predict 2048, thinking on | 2050 | 562 | stop | 1889 | 793 | no |

With thinking off, the whole generation budget is `message.content`: a markdown analysis that stops mid-sentence at the token cap. Raising the cap to 2048 only lengthens that essay. It still does not emit a tool call, so `tool_choice=required` is not honored on this prompt. With thinking on, the budget is mostly `message.thinking` (1,889 characters) plus a short content, and the model stops on its own, still without a tool call. A follow-up turn that adds one short evidence page raises the prompt from 2,050 to 2,122 tokens and then returns a tool call in 63 tokens. The initial task had also embedded 170 evidence ids from the first graph edges without their row bodies. The later run's 280 exposed ids were mostly those ids plus later pages, not 280 full records.

After the page summary change, native tool calling on the same Basic window (`interface-native-20261014`, no controller gap, num_predict 512) chose `retrieve_raw_evidence` for three ids that are in the database (`EV-43ead8119c854618`, `EV-c248e2d16d8acd65`, `EV-35343629250fd956`). Prompt 3,778 then 3,665 tokens; generation 138 and 125 tokens; both `done_reason=stop`. The second call repeated the same ids and was skipped. The closing call asked for another retrieve and was not executed, because that turn only accepts a proposal or a stop. No inferred edge was added. The 36 record links remain observed facts. JSON actions on the same window (`interface-json-20261014`, num_predict 256) produced one truncated proposal, 1,958 prompt tokens, 256 generation tokens, `done_reason=length`, and no tool call. Native calling is the interface that selected a valid query. JSON calling did not, at this budget.

On the two-packet known-answer case, native calling with num_predict 512 queried the network, quoted both returned evidence ids, and proposed one communication citing `EV-aaaaaaaaaaaaaaaa` and `EV-bbbbbbbbbbbbbbbb`. Verification kept it as `observed_fact` / `communication`, `causal_status=not_established`. A 2-second-only pair is now `temporal_cooccurrence`, not a trusted inference. Baseline and Gemma runs were not repeated.

## Agent-loop rerun, 2026-10-14

The earlier Basic numbers above are unchanged. A later run is in `runs/etgi/basic-ev0961/etgi-qwen-agentfix` and does not replace them.

Ollama 0.32.5 accepts `tool_choice=required`. A one-line probe did return a tool call. That does not carry over to the investigation prompt: the four search turns have `done_reason=length`, `truncated=true`, and no tool call. The four queries are still `controller_gap`. Their rows are now in the following turn; the trace records 280 exposed evidence ids. The closing proposal named `firewall` and `switch_2` and cited `ev-001`, which is not in the database. Verification removed both edges. The published graph is again 7 communications, 4 same-device edges, and 25 shared-source edges, each with `claim_level=observed_fact` and `causal_status=not_established`. No inferred edge remained. Question baselines, Gemma, and a new cross-scene suite were not started, because this Sherlock run still did not show the model choosing a tool.

A separate known-answer case with two TCP packets did show a model-chosen tool call and a later step after that result (`tests/test_etgi_ollama_loop.py`, 1 passed). That check is not a Sherlock result.

## Semiurban transfer

One test window, `ev_0431e34c3ed30056a8f0`, 1743640079.1774833–1743640109.233572, context 10 s, tool cap 4. The state file is `test.n406.state.gz`, not the Basic n302 name. The index has 8,511 new electrical values, 9,550 TCP packets, 18,032 IEC-104 objects, and 0 unmatched ASDU rows. Of 339 decoded values with a nearby IPAL sample, 339 match.

The transfer run repeats the Basic pattern. All 4 tool calls are gap fallbacks. The proposal argument list is empty. The narrative is rejected because it introduces the number 17436400. Completion is `INCOMPLETE_BUDGET_EXHAUSTED`. The published graph has 7 supported communications, 5 supported same-device edges, and 18 supported shared-source edges. Necessity on one communication again stays supported with no sensitive citation. This is not a second suite, and Rural was not run.
