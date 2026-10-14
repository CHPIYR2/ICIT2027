# Ablation results

Same Basic window, same Qwen3.5 9B, same index as the ETGI case study. Question exact match is 1/5 for every variant, and that one match is the shared-frame question whose answer is zero. Gold-id recall does not favor the full method over the agent that only retrieves.

| Variant | Supported N–N / P–P / N–P | Unresolved N–P | Gold ids | Necessity |
| --- | --- | --- | --- | --- |
| Full ETGI | 7 / 4 / 25 | 0 | 24/1775 | 0/3 citations changed a stable judgment |
| Without active retrieval | 7 / 4 / 25 | 0 | 19/1775 | 0/3 |
| Without the temporal graph | 0 / 0 / 0 | 0 | 24/1775 | not run; no edge was proposed |
| Without contradiction search | 7 / 4 / 25 | 0 | 24/1775 | 0/3 |
| Without source dependency | 7 / 4 / 0 | 25 | 24/1775 | 0/3 |
| Without necessity | 7 / 4 / 25 | 0 | 24/1775 | not run |
| Without revision | 0 / 0 / 0 | 25 | 24/1775 | 0/3; edges stay unresolved |

## What changed the graph

Revision is the switch that publishes record links. With it, 36 edges are supported. Without it, the same 36 edges stay at the initial unresolved label. Citation validity is 1.0 in both cases. The check can see the support; revision is what writes it onto the published edge.

Source dependency is the switch that establishes the 25 network–electrical edges. With the audit they are supported `shared_source` links, one independent group when the IEC-104 row and the IPAL row are the same point. Without the audit those 25 edges stay unresolved. They are not published as a second, independent modality. The 7 communications and 4 same-device edges do not need that audit.

Removing the temporal graph removes every edge. The model did not propose a replacement. Retrieval still returns 24 of 1,775 gold ids, the same count as full ETGI, because the gap queries still run.

## What did not change the graph

Contradiction search, after frame length was excluded from the measurement check, did not change any published status on this window. There was no hold cited as a new value and no reversed time order on the published edges.

Necessity did not remove or relabel an edge. On the one communication that was tested, the model stayed at supported after each cited packet was removed. The same 0/3 result appears in the ablations that still run the test. Active retrieval is not required for the 36 supported edges: the record-link graph is built from the index before the model searches. Turning retrieval off lowers gold-id overlap from 24 to 19 and leaves the published graph unchanged.

## Reading

On this window the graph differences come from revision and from the shared-source rule. They do not come from the model finding additional relations, and they do not improve question exact match. Necessity and contradiction search are implemented and, here, they have no measured effect on the published graph.
