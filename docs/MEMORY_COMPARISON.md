# Investigation memory comparison

Fixed before any of these runs, in `configs/etgi/memory_protocol.json`. Qwen3.5 9B, temperature 0, seed 1, `num_predict` 512, at most 4 tool calls and 6 model calls, native tool calling, no controller gap. Three Basic test windows, clock bounds only. Each window was run twice: without investigation memory, then with it. Outputs are under `runs/etgi/memory-comparison-20261014`. Earlier negative runs were not replaced.

A query counts as autonomous only when `origin` is `llm`. Gap fallbacks were 0 in every run.

| Episode | Memory | Autonomous queries | Duplicates | Queries with new ids | Distinct tools | Inferred edges kept | Answer accuracy | Prompt tokens | Generation tokens |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ev_12dcd56b2f5e78144cfb | no | 1 | 1 | 1 | 1 | 0 | 0/5 | 9706 | 313 |
| ev_12dcd56b2f5e78144cfb | yes | 1 | 1 | 1 | 1 | 0 | 0/5 | 9833 | 446 |
| ev_3e4d36008b29595ef246 | no | 1 | 1 | 1 | 1 | 0 | 0/5 | 10169 | 417 |
| ev_3e4d36008b29595ef246 | yes | 2 | 1 | 2 | 1 | 0 | 0/5 | 14661 | 677 |
| ev_0961f1c2da8a257e3ebc | no | 2 | 0 | 1 | 1 | 0 | 0/5 | 13768 | 346 |
| ev_0961f1c2da8a257e3ebc | yes | 2 | 0 | 2 | 1 | 0 | 0/5 | 14399 | 494 |

Every autonomous call was `retrieve_raw_evidence`. None was a controller choice. Duplicate calls did not read the database again. With memory, the duplicate response is marked `already_queried` and the next turn receives the stored page summary plus a digest of known ids, not the raw rows from every earlier page.

On `ev_0961f1c2da8a257e3ebc` with memory the trace is:

1. The model called `retrieve_raw_evidence` for `EV-43ead8119c854618`, `EV-c248e2d16d8acd65`, and `EV-35343629250fd956`. All three were new.
2. After that page, it called `retrieve_raw_evidence` again for three different ids, `EV-220f7c262e3868ba`, `EV-0f762f7a2cbf76e0`, and `EV-b36e1277f83dc361`. Those were also new. The recorded goal quotes the TCP flows from the first page.
3. The next generation stopped at `done_reason=length` after 46 tokens and produced no action.
4. The closing turn asked for another retrieve. That call was not executed, because the closing turn only accepts a proposal or a stop. The model neither proposed a relation nor stopped.
5. Programmatic verification still ran on the 36 record-link edges. No inferred edge was kept. Citation use was 0 because nothing was proposed.

Memory changed one window from a repeated id set to a second id set with new evidence (`ev_3e4d36008b29595ef246`), and made both queries on `ev_0961` add new ids. It did not produce a different tool, a candidate relation, or a better answer to the investigation questions. Answer accuracy was 0/5 in all six runs. That is not evidence that memory improves investigation quality.

The two-packet known-answer case still has the proposal with valid ids. These three Basic windows do not. Baseline and Gemma comparisons were not restarted.
