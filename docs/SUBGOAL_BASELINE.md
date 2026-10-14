# Subgoal baseline and the 46-token stop

This comparison is a development diagnosis on three Basic windows that had already been inspected. It is not a confirmatory test. The fixed settings are in `configs/etgi/subgoal_protocol.json`. Outputs are under `runs/etgi/subgoal-comparison-20261014`. Earlier negative runs were not replaced.

## What the 46-token stop was

The saved turn on `ev_0961f1c2da8a257e3ebc` with investigation memory had `prompt_eval_count` 4050, `eval_count` 46, `done_reason` length, empty `content`, empty `thinking`, and no tool call. `num_predict` for that run was 512, so the generation budget was not what stopped it. The client sends `stream: false` and stores `message.content` as returned.

Ollama 0.32.5 had loaded `llama-server` with `-c 4096`. The client had not set `num_ctx`, and the Modelfile does not set one either. The model's own context length is 262144; the runner window was the request default. 4050 + 46 = 4096.

A replay with tools, `tool_choice` required, `num_predict` 512, and no `num_ctx` reproduced the same arithmetic: prompt 4050, eval 46, sum 4096, `done_reason` length. The visible text stopped mid-sentence. The same prompt with `num_ctx` 8192 finished that sentence in 56 tokens and stopped with `done_reason` stop. A completed tool call can also come back with empty content and a populated `tool_calls` field; that shape is a normal tool turn, not the saved failure. The saved failure is the 4096 window filling before a parseable action. Raising `num_predict` does not add room past that window. The comparison below sets `num_ctx` to 8192 and leaves `num_predict` at 512.

## What is taken from the papers

HiAgent (Hu, Chen, Chen, Mu, Shao, and Luo, ACL 2025) manages in-trial working memory by subgoal. The model names a subgoal before actions. Action-observation pairs are kept for the current subgoal. When the model says the subgoal is finished, those pairs are replaced by a summary that includes whether it was achieved. A past subgoal's pairs are returned only if the model asks for that subgoal. HiAgent allows the summary to be produced by a model or by another summarizer. ETGI uses the second option: the summary is the stored tool name, new evidence ids, duplicate flag, and the status string the model supplied. There is no second summary model, and there is no in-context example.

CoEx (Kim and Hwang, Findings of EMNLP 2025) splits a planner from an actor. The planner's action is a subgoal conditioned on an explicit belief state. The actor carries out that subgoal and can end it as completed, unachievable, or out of steps. After the subgoal, the belief state is updated. ETGI follows that split. The planner may name one subgoal, propose relations, stop, or ask for one past trajectory. The investigator may call the existing evidence tools, close the subgoal, propose, or stop. The controller executes, validates arguments, blocks a repeated query, and enforces the tool and call budgets. It does not choose the next subgoal or the next evidence tool.

The belief fields are known facts, unknowns, contradictory statements, and verification results. A known fact or a contradiction is stored only when it cites an evidence id that is in the database. Unknowns are the model's own open questions and do not require an id. Verification results are the existing record check and inference assessment, run as a preview when a relation is proposed and again when the graph is published. They are not a new judge.

## What ETGI did not take from the papers

CoEx's symbolic memory is a code object updated from environment actions, and its textual memory is written by a separate verification and synthesis model. Those calls are not added. The evidence database is already the store of rows, and another model call would spend the shared budget of six calls. CoEx's skill library of few-shot subgoal trajectories is not used. HiAgent's one in-context example per task is not used. No attack-class menu and no hand-written subgoal list from these Sherlock windows are provided.

Agent Workflow Memory (Wang, Mao, Fried, and Neubig, ICML 2025) induces reusable workflows from past trajectories and feeds them to later tasks, offline or online. That is cross-trial memory. It is not implemented. Inducing a workflow from these three windows would reuse episodes that are only a development diagnosis.

Relations that are close in time and have no other shared identifier stay `temporal_cooccurrence` / unresolved. The model is not required to propose an edge. A model call to `stop_investigation` with no proposed edge is `MODEL_ABSTAINED`. A run that ends because the call budget or the tool budget is exhausted, without that stop, is `INCOMPLETE_BUDGET_EXHAUSTED`. A generation that returns no action is `NO_VALID_MODEL_ACTION`. Those labels are not interchangeable.

## Comparison

Arms, all on Qwen3.5 9B, temperature 0, seed 1, `num_predict` 512, `num_ctx` 8192, at most 4 evidence queries and 6 model calls, native tool calling, controller gap fallback off:

| Arm | Agent |
| --- | --- |
| A | Original investigator |
| B | Investigator plus the existing investigation memory |
| C | Planner and investigator, plus that same memory |

A and B still use the existing loop, including the closing turn that accepts only a proposal or a stop. C does not use that closing restriction: after a subgoal the model can query, propose, or stop. A duplicate query in C is returned as `already_queried` and does not by itself end the run.

## Results

Nine runs, three windows, gap fallbacks 0, inferred edges kept 0, evidence ids used in a proposal 0, investigation-question accuracy 0/5. No run called `stop_investigation`. `context_limited_turns` counts a length stop that filled `num_ctx` before `num_predict`.

| Episode | Arm | Autonomous queries | With new ids | Distinct tools | Subgoals achieved | End | Answer |
| --- | --- | ---: | ---: | ---: | ---: | --- | ---: |
| ev_12dcd56b2f5e78144cfb | A | 4 | 4 | 4 |  | tool budget | 0/5 |
| ev_12dcd56b2f5e78144cfb | B | 4 | 4 | 4 |  | tool budget | 0/5 |
| ev_12dcd56b2f5e78144cfb | C | 3 | 1 | 3 | 0/1 | no action | 0/5 |
| ev_3e4d36008b29595ef246 | A | 4 | 4 | 4 |  | tool budget | 0/5 |
| ev_3e4d36008b29595ef246 | B | 4 | 3 | 3 |  | tool budget | 0/5 |
| ev_3e4d36008b29595ef246 | C | 1 | 1 | 1 | 0/1 | no action | 0/5 |
| ev_0961f1c2da8a257e3ebc | A | 4 | 3 | 3 |  | tool budget | 0/5 |
| ev_0961f1c2da8a257e3ebc | B | 3 | 2 | 2 |  | no action | 0/5 |
| ev_0961f1c2da8a257e3ebc | C | 4 | 4 | 4 | 0/1 | tool budget | 0/5 |

A and B, once the runner context is 8192, choose several evidence tools rather than only `retrieve_raw_evidence`. On five of those six runs the four-query cap is what ends the search. The closing turn then asks for another retrieve or another telemetry query. That call is not executed, and it is not a stop. On `ev_0961f1c2da8a257e3ebc` arm B, one turn had prompt 8062 and completion 130, summing to 8192, `done_reason` length, 627 characters of prose, and no tool call. The client marks that turn `context_limited`. The following closing turn used all 512 generation tokens, still with no parseable proposal or stop.

C does not improve answer accuracy, and it does not produce a candidate relation. The planner did name a subgoal on each window. The texts were "Investigate electrical node sgen.1 and its active_power measurements..." and, on the other two windows, "Request evidence for all open relations in the incident window." Those strings came from the planner turn. They were not a fixed list. The investigator then called evidence tools. It never called `complete_subgoal`, `propose_relations`, or `stop_investigation`.

On `ev_12dcd56b2f5e78144cfb` the investigator made three queries and only one added new ids, then returned a turn with no action. On `ev_3e4d36008b29595ef246` it retrieved one page, then wrote 2,337 characters with `eval_count` 512 and no tool call. That stop is `num_predict`, not the context window: prompt 5280 plus 512 is inside 8192. On `ev_0961f1c2da8a257e3ebc` it used four different tools, each adding new ids, then asked for another retrieve. The controller did not run that fifth query. The trace records it as `budget_blocked_tool` with origin `llm`.

Two saved C traces label the still-open subgoal `budget_ended` on runs whose completion is `NO_VALID_MODEL_ACTION`. Those processes used the label that was current while they ran. The completion field matches the trace: the model did not stop, and the tool budget was not what ended `ev_12dcd56b` or `ev_3e4d3600`. The code now records that open subgoal as `no_action`. The raw traces were not rewritten.

No arm showed the chain of a model proposal, or an explicit abstention, followed by the record check of that proposal. Baseline and Gemma comparisons were not restarted. Another planner or memory mechanism was not added on top of this result.

