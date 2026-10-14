# T3: independent evidence gold and fixed-budget selection study

Status: design only. No human annotation has been done. The assistant cannot act as an annotator, and no model output, selector output, or official Sherlock event text may be turned into gold.

## 1. What the gold measures

The question is narrow: given a suspicious window, which observations would an investigator need in order to explain what happened on the network and on the electrical side? The gold is a set of judged evidence units for each window. It is not an attack label, not a cause, and not a relation gold. Sherlock has no relation ground truth, so this study does not report Edge Precision for inferred relations. Recorded links (`communication`, `same_device`, `shared_source`, `same_frame`) are never counted as inferred-edge hits.

## 2. Unit of annotation

The annotator judges candidate units from a frozen pool, not free text.

- TCP flow at one 5-tuple, all vantages merged, with per-vantage and distinct-frame counts shown.
- IEC-104 information object: one `(entity, CA/IOA)` within the window. The parent frame is shown as a shared container. Siblings carried by the same frame are shown as such and are never merged.
- IPAL electrical point: one `entity` with `new` updates only. Forward-filled `hold` and `initial` rows are not units.

Each unit shows its time span, values (first, last, min, max, distinct-frame sample count), source modality, vantages, and its full lineage ids. It does not show the selector score or rank, the model's choices, `malicious` flags, attack type, official event text, or `physical.zip`.

## 3. Labels

Per unit, each annotator records:

| Field | Values |
| --- | --- |
| `necessity` | `needed` / `useful` / `not_needed` / `cannot_judge` |
| `side` | `network` / `electrical` / `both` |
| `basis` | Short free text citing the unit's own values or lineage ids |

Per window, each annotator also records whether the evidence pool is sufficient to explain the window (`sufficient` / `insufficient` / `cannot_judge`). Relations are not labeled.

`needed` means the explanation would be wrong or incomplete without it. `useful` means it adds support but another unit carries the same point. Graded gain for nDCG is `needed = 2`, `useful = 1`, otherwise `0`.

## 4. Windows

- Sample from Sherlock v3 windows that have never been used in development. The development set is closed: `ev_0961f1c2da8a257e3ebc`, `ev_12dcd56b2f5e78144cfb`, every window in `runs/etgi/memory-comparison-20261014`, `subgoal-comparison-20261014`, `capability-20261014`, and every `postalert-*` run.
- Stratify by scenario and window length. Write the sampling seed and the list of window ids to a frozen file before anyone looks at the candidates.
- Include windows sampled at random from benign periods at the same rate as the suspicious windows, so that `not_needed` and `insufficient` are real options, and the annotators cannot assume every window holds an event.
- Window ids are shown to annotators as opaque hashes. Scenario names are hidden where they reveal the attack.

## 5. Procedure

1. Freeze the candidate pool per window with the same index, background policy (15 s before, clipped to the indexed range), atomicity rules, and lineage export as `postalert-t3-atomic`. Record the code hash.
2. Shuffle the units per annotator with a recorded seed so the order carries no rank information.
3. Two annotators label independently, blind to each other, to all selectors, and to all model outputs.
4. Report Cohen's kappa on `necessity` (collapsed to `needed or useful` vs `not_needed`) and weighted kappa on the full scale, per window and overall, before adjudication.
5. A third person adjudicates disagreements, using only the units and both annotators' `basis` text. Keep pre-adjudication labels.
6. Freeze the adjudicated gold with a SHA-256 before any selector or model is scored against it.

## 6. Fixed-budget selection study (T3-Study)

All methods see the same frozen pool per window and return a ranked list of `K` unit ids. `K` is fixed before scoring (planned: 5, 10).

| Method | Description |
| --- | --- |
| Random | Uniform shuffle with a recorded seed, averaged over 100 seeds |
| Statistical ranking | The non-LLM score in `select.py` (bounded log robust change, comparable within one role), with the same role quotas |
| Qwen | `qwen3.5:9b-q4_K_M`, typed references only, chooses up to `K` unit ids |
| Gemma | `gemma4:12b-it-q4_K_M`, same input and schema |

Both models: temperature 0, seed 1, `num_ctx` 8192, `num_predict` fixed in advance, no salvage. Output must reference unit ids. Ids outside the pool are counted as errors, not dropped silently.

Metrics:

- Precision@K, Recall@K, nDCG@K against the adjudicated gold.
- Faithfulness: share of published claims whose rendered text the verifier binds to the cited rows.
- Unsupported-relation rate: share of relation claims rejected by the verifier, by reason.
- Abstention: share of windows where the method emits nothing, split by whether gold says `sufficient` or `insufficient`.
- Recorded-link claims are reported in their own column and excluded from any inferred-relation figure.

Report per-window values and paired differences with bootstrap confidence intervals over windows. With the expected number of windows, the study can show whether one method is clearly worse than random or than the statistical ranking. It is not powered to claim one model is better than another unless the intervals separate.

## 7. Threats

- Annotators share knowledge of Sherlock scenarios. Hiding scenario names reduces, but does not remove, this.
- Unit boundaries come from our own atomicity rules. A different grouping may change which units look needed.
- IEC-104 values and IPAL values for one mapped point are one source. Annotators see them as separate units but the study does not treat their agreement as independent confirmation.
- `physical.zip` stays out of the pool. If it is used later, it is a separate physical-impact evaluation, not part of this gold.
