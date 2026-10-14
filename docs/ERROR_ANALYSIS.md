# Error analysis

## Model does not use the tools

The required-tool setting produced a tool call in a one-line check. On the investigation prompt, Qwen3.5 9B wrote a prose analysis at temperature 0 and seed 1, with an empty tool-call list. The same pattern appears in B3 and in every ablation that allows search: the trace's tool events are `controller_gap`, not `llm`. The closing `propose_relations` call had an empty argument object, so the proposal created no edge. The gap list then dominates the search. That is a controller result, and the trace says so. It is not evidence that the model chose IEC-104, flows, or electrical changes.

## Narratives do not survive the citation check

Every reported run rejected the narrative. The full ETGI narrative introduced the timestamp 1742961053.85, which is not a number in the findings JSON. The structured report remains. The rejection is the grounding check working. It also means this model did not produce a usable explanation under the fixed instruction.

## Question score looks less informative than it is

All methods score 1/5. The matched item is "how many frame hashes appear at two vantages?" The gold answer is 0, and a method that retrieves no shared frame also answers 0. The control-point, entity, reply, and measurement questions fail for every method. Gold-id recall is the clearer retrieval number: 24/1,775 for ETGI and B3, 19/1,775 for the stratified sample, 4/1,775 for the earliest 20 rows, and 0/1,775 for the packet ids attached to the first communication edges. A page of 20 rows cannot cover 1,759 new electrical values. The cap is predeclared. It also makes exact entity-list match an unrealistic bar, which is why both numbers are reported.

## Packet length was a false contradiction

An earlier pilot marked the 7 communication edges disputed because two TCP frames of the same flow had different captured lengths within one second. Those lengths are not measurements. The check is now limited to electrical and IEC-104 values. The pilot directory is `runs/etgi/basic-ev0961/pilot-packet-length-disputes`. The tables in the results use the run after that fix. The suite was not executed on the buggy checker.

## Shared frames do not collide

No fingerprint is shared by two vantages in the Basic incident interval, and the same was true of the context used for the multi-vantage query. The same-frame edge type is implemented and, on this window, has no input. Different switches can still carry the same 5-tuple; that is not counted as one frame.

## Necessity does not audit a weak edge

The only necessity test is a communication the record check already supports. The model keeps the supported judgment when any one of three packets is removed, which is what one would expect if the other packets of the flow remain in the card set. The test never saw an inferred coincidence, because the model did not propose one. A sensitivity of 0 here does not show that necessity would catch an unsupported relation. It shows that this trial did not.

## Cross-modal agreement is one source

The 25 network–electrical edges are the same CA/IOA in an ASDU and in the IPAL state. The decoder audit matched 312/312 nearby pairs. Treating that agreement as two sensors would be a source-dependency error. The published label is `shared_source`. The dependency ablation leaves those edges unresolved instead of supported, which is the intended conservative outcome, not a detection of a hidden attack.

## Budget label

Agent runs stop at the tool cap and are marked `INCOMPLETE_BUDGET_EXHAUSTED` even when the record-link graph has been checked. Single-shot runs that do not search are `COMPLETE` with an empty or unresolved graph. Complete does not mean the questions were answered.
