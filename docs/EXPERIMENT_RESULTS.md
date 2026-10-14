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

## Semiurban transfer

One test window, `ev_0431e34c3ed30056a8f0`, 1743640079.1774833–1743640109.233572, context 10 s, tool cap 4. The state file is `test.n406.state.gz`, not the Basic n302 name. The index has 8,511 new electrical values, 9,550 TCP packets, 18,032 IEC-104 objects, and 0 unmatched ASDU rows. Of 339 decoded values with a nearby IPAL sample, 339 match.

The transfer run repeats the Basic pattern. All 4 tool calls are gap fallbacks. The proposal argument list is empty. The narrative is rejected because it introduces the number 17436400. Completion is `INCOMPLETE_BUDGET_EXHAUSTED`. The published graph has 7 supported communications, 5 supported same-device edges, and 18 supported shared-source edges. Necessity on one communication again stays supported with no sensitive citation. This is not a second suite, and Rural was not run.
