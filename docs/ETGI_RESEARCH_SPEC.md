# ETGI research specification

ETGI (Evidence-Seeking Temporal Graph Investigation) is the current method on the `mirage-ot` branch. The earlier GRU encoder and learned adjacency remain in the repository as a negative result: on the Basic normal window they did not beat a no-graph forecast, and the learned gates tended to close. ETGI does not call that model.

## Problem

An investigation is a time window

\[
I = (t_s, t_e, \mathcal{O})
\]

with allowed observation sources \(\mathcal{O}\). The system may read network captures and IPAL state inside the window and a short context around it. It returns a temporal evidence graph \(G_I = (V_I, E_I)\), a timeline, an explanation, supporting and contradicting evidence, alternative explanations, and an uncertainty label for every relation. Attack-type classification is not the output.

## What is implemented

| Module | Role in this repository |
| --- | --- |
| A. Evidence query engine | `mirage_ot.etgi.evidence`. Streams a Sherlock v3 ZIP into SQLite. Tools take structured arguments, paginate, and never see evaluator fields. |
| B. Investigator | `agent.controller`. The local model chooses the next tool. If it does not, a fixed gap ranking issues one query and the trace marks `controller_gap`. |
| C. Temporal evidence graph | `graph.temporal` plus record-link candidates in `graph.observed`. Exports JSON, GraphML, and an offline HTML view. |
| D. Verification | `verification.assess`. Retrieves the cited rows and checks entity match, time order, holds cited as changes, and whether a record link exists. |
| E. Evidence necessity | `verification.necessity`. Re-judges one relation with tools disabled after removing a cited id and every row that shares its frame or parent. |
| F. Revision and report | Status changes append history. The report is generated from the graph. A model narrative is kept only when every evidence id and number in it already appears in the findings. |

## Record link

A published status of `supported` requires one of these record facts:

- both directions of a TCP 5-tuple at one vantage (`communication`);
- one Ethernet frame hash at two vantages (`same_frame`);
- an IEC-104 CA/IOA and the IPAL name of that point within two seconds (`shared_source`);
- two attributes of one device (`same_device`).

Two electrical values that change in the same window do not satisfy this test. The edge stays `unresolved`. A shared IEC-104 report is one source. If a model calls that pair a cross-modal association, revision relabels it `shared_source` and records that the modalities are not independent.

`disputed` means a concrete contradiction was retrieved: a hold or initial fill cited as a new measurement, disagreeing values for one point inside one second, or a claimed time order the timestamps violate.

## Gap ranking

The fallback query is not a probability from the model. Uncalled tools are taken in a fixed order: IEC-104 messages, electrical changes, TCP flows, ARP, multi-vantage frames, then a comparison of the incident window with the preceding context. After those, an unresolved relation whose endpoint has no timeline query is queried. The trace records `selected_by`.

## Evidence necessity

For at most two inferred relations, and at most three cited ids each, the model judges the relation from those cards only. The same judgment is repeated with a fixed seed and temperature 0. Each cited id is then removed together with rows that share its fingerprint or parent packet, and the judgment is repeated. A citation is judgment-sensitive when both the full run and the ablated run have a strict majority status and those statuses differ. A change does not prove the relation and does not prove causal necessity. An unstable full judgment is reported as unstable and is not counted as sensitivity.

## Data boundary

Investigation inputs are the clock bounds, the scenario ZIP, the n302 IPAL state, the point map, the initial state, and the switch PCAPs. The loader does not open `events.json`, `events.jsonl`, `malicious`, or `physical.zip`. Electrical values are marked `network-reported-not-simulator-truth`. Holds are stored as one summary per entity. A missing numeric value is SQL NULL; a stored 0 is a real zero.

IEC-104 ASDUs are decoded with tshark's `iec60870_asdu` dissector because `ipal-transcriber` is not on PATH. Type-id ranges (`monitor`, `control`, `system`) are the IEC 60870-5-104 classes, not Sherlock attack labels. On the indexed Basic window, 312 decoded values that had a nearby IPAL sample all matched that sample. That check is a decoder audit, not evidence that the two rows are independent.

The model cannot emit SQL or shell. Tool results are marked as untrusted telemetry. Packet payloads are not stored.

## Comparisons

All methods see the same indexed database, the same model, temperature 0, and the same question set. Single-shot methods do not get tools. Agent methods share a tool-call ceiling. ETGI's necessity judgments reuse already retrieved cards; they are not an extra search of the archive.

| Method | What it actually is |
| --- | --- |
| B0 | One reply from the earliest 20 rows. Not a tuned prompt. |
| B1 | One reply from a fixed sample stratified by record kind. Not a vector RAG system. |
| B2 | One reply from the evidence ids already attached to record-link edges. Not Microsoft GraphRAG: there is no entity extraction, community detection, or hierarchical summary. |
| B3 | The same tool loop without contradiction search, source-dependency audit, necessity testing, or revision. |
| ETGI | The full loop. |
| Ablations | ETGI with one of those six switches off. |
| Modality filter | The same database with network rows, electrical rows, or both visible. Electrical-only still means network-reported state. |

## Evaluation

Gold answers for investigation questions are SQL over the index, written before the model answers. A method scores by whether the evidence ids it actually received reproduce that gold. The model is not asked to grade itself.

Graph metrics are citation validity, temporal-order violations, source-dependency errors on published cross-modal edges, and the share of published `supported` edges that the record-link check rejects. Sherlock has no relation-graph gold. Edge precision, edge recall, and causal accuracy are not computed. A synthetic case where a planted coincidence must stay unresolved is reported separately from Sherlock.

## Completion

The run is `COMPLETE` only when every remaining edge is supported, disputed, or unresolved, contradiction search has run where it was enabled, and necessity has run when an inferred edge with citations exists and that switch is on. Exhausting the tool, call, or time budget yields `INCOMPLETE_BUDGET_EXHAUSTED`.

## Decisions

SQLite is the index because it is in the standard library and the model never writes to it. NetworkX writes GraphML. The HTML view is offline and does not load Cytoscape. Ollama runs one model at a time; Qwen3.5 9B is the default because a tool-call check succeeded locally. Gemma 12B is the second model and is not loaded together with Qwen. The prior learned-graph stack is unused by ETGI. Torch remains installed only so the old prototype still runs.
