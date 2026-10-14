# Research findings

ETGI runs on a real Sherlock Basic window. The program builds a traceable graph, rejects a narrative that cites a number it was not given, and distinguishes a shared IEC-104 report from an independent electrical observation. The research claims are only partly borne out, and the part that fails is the part that required the model to investigate.

## Supported by this case study

Record links are checkable without a relation-graph gold standard. After verification and revision, the published graph has 7 bidirectional TCP conversations, 4 same-device attribute pairs, and 25 shared-source links between an IEC-104 object and the IPAL name of that point. Citation validity is 1.0. None of those supported edges fails the same check when it is reapplied as an oracle. Two values changing in the window are not in that set, because the model did not succeed in proposing them and the record linker does not invent them.

Revision and the source audit are the switches that change this graph. Without revision, all 36 edges stay unresolved. Without the source audit, the 25 cross-modal edges stay unresolved and the 11 within-modality record links remain supported. Network-only input yields the 7 conversations. Electrical-only input yields the 4 same-device edges. The cross-modal edges are not available as a second modality when either view is hidden.

The grounding check discarded every model narrative in the comparison. That is a functioning filter, not a successful explanation.

## Not supported

The model was supposed to choose queries, propose relations, and revise them. On this prompt it did none of those. Gap fallback did the searching. `propose_relations` was called with no relations. Question exact match is 1/5 for ETGI and for every baseline, and the matched question is a zero count. Gold-id recall for ETGI is 24/1,775, the same as agentic retrieval without the ETGI checks. Active retrieval is not what creates the supported edges.

Contradiction search does not change published status on this window. Necessity, on the one supported communication that was tested, changes 0 of 3 judgments. Those components are not shown to reduce unsupported edges here, because the published supported set was already the record-link set.

No attack type is predicted or scored. No edge precision or causal accuracy is computed. Gemma was not compared. Rural was not run. A short Semiurban window repeats the same split: the record linker publishes 7 communications, 5 same-device edges, and 18 shared-source edges, and the model again does not call tools or propose relations. The Basic window was not unseen.

## What would be a next experiment, not a new claim

A page size of 20 cannot answer an entity-list question with 254 names. Raising the page size would change recall and would still not create inferred edges if the model does not propose any. The open problem on this hardware is that Qwen3.5 9B does not stay inside the tool call on the investigation state, while it does on a one-line request. That is a controller failure mode to measure on more windows, not a reason to retune the prompt against this event.
