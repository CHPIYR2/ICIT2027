# T3 Pilot Evaluation with Author-Validated Reference Labels

- **Run directory**: `runs/etgi/t3-author-validated-20261015/`
- **Frozen code SHA-256 (`postalert/*.py`)**: `e7d810baaabf14b8aceb8ef931d8637d10175786c05a488f135788f5e63b65c7`
- **Reference labels file**: `runs/etgi/t3-author-validated-20261015/reference_labels.json`
- **Summary metrics file**: `runs/etgi/t3-author-validated-20261015/evaluation_summary.json`
- **Failure cases file**: `runs/etgi/t3-author-validated-20261015/failure_cases.json`

> **Methodological Boundaries**:
> 1. **Single Author-Validated Pilot Set**: The 44 labels (`22` in `PILOT-W01`, `22` in `PILOT-W02`) are an author-reviewed AI-assisted reference set (`annotator_id = "GPT-6_AI_PILOT_20261015"`). They are **not** a dual-annotator human consensus gold, and no inter-annotator agreement ($\kappa$) is claimed or computed.
> 2. **Non-Independence of Windows**: `PILOT-W01` (`ev_3e4d36008b29595ef246`, `1742959890.189`–`1742959950.383`, 60.19 s) and `PILOT-W02` (`1742959950.383`–`1742959965.383`, the immediately following 15.0 s interval) belong to the same episode and adjacent time ranges. They cannot be treated as independent events for statistical significance testing.
> 3. **Unlabeled Candidates Not Treated as Zero**: Out of `1,239` total atomic candidates across both windows (`627` in `PILOT-W01`, `612` in `PILOT-W02`), `44` units are labeled and `1,195` units are unlabeled. Unlabeled units are **never** treated as `Not Needed (0)`. Full-pool Recall (and full-pool Precision whenever unlabeled units appear in top-$K$) is reported as `NOT_ESTIMABLE`.

---

## 1. Author-Validated Reference Labels & Canonical Mapping Verification

Both annotation files were located recursively under `runs/etgi/t3-pilot-pool-20261015/author_annotations/` and verified without modification:

| Window | Source File | SHA-256 Prefix | Validated Units | Unique Blind IDs (`U001`–`U022`) | Unique Canonical `unit_id` | Pack A vs Pack B Permutation Invariant | Window Sufficiency | `Needed (2)` | `Useful (1)` | `Not Needed (0)` |
| --- | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: |
| `PILOT-W01` | `PILOT-W01_AI_expert_response.json` | `51990184...` | 22 | 22 | 22 | `True` (`orders_differ = True`) | `sufficient` | **6** (`5` net, `1` elec) | **16** (`9` net, `7` elec) | **0** |
| `PILOT-W02` | `PILOT-W02_AI_expert_response.json` | `25884a70...` | 22 | 22 | 22 | `True` (`orders_differ = True`) | `sufficient` | **4** (`2` net, `2` elec) | **15** (`11` net, `4` elec) | **3** (`1` net, `2` elec) |
| **Total** | — | — | **44** | **44** | **44** | **`True`** | — | **10** | **31** | **3** |

### Author-Validated `Needed (score = 2)` Units (10 total)

- **`PILOT-W01` (6 `Needed` units)**:
  1. `TL009` (`U015`, `network`, `command`): `switch.31:closed` (`CA/IOA = 117.10150`, 2 source frames at `t = +0.04s`) — **Exposed at Card #1**.
  2. `TL010` (`U008`, `network`, `command`): `switch.30:closed` (`CA/IOA = 116.10150`, 2 source frames at `t = +10.12s`) — **Exposed at Card #10**.
  3. `TL011` (`U001`, `network`, `command`): `switch.27:closed` (`CA/IOA = 131.10270`, 2 source frames at `t = +20.16s`) — **Missed at Stage 1** (excluded by `command` role quota = 2 in `expose_timeline`).
  4. `TL013` (`U010`, `network`, `electrical_report`): `line.11:active_power_to` (`117.10050`, `301,181 -> 265,658`, $-11.8\%$) — **Exposed at Card #6**.
  5. `TL014` (`U006`, `network`, `electrical_report`): `line.11:active_power_from` (`116.10090`, `-292,740 -> -254,333`, $+13.1\%$) — **Missed at Stage 1** (excluded by `electrical_report` quota = 2).
  6. `TL023` (`U002`, `electrical`, `electrical_change`): `line.10:active_power_from` (`103.10050`, `-284,326 -> -248,150`, $+12.7\%$) — **Missed at Stage 1** (`selector_score = 7.9254`, ranked 5th among electrical updates behind four higher-z `line.11`/`line.10` reactive/current series).
- **`PILOT-W02` (4 `Needed` units)**:
  1. `TL010` (`U017`, `network`, `electrical_report`): `line.13:current_from` (`114.10110`, `0.43175 -> 0.19473`, $-54.9\%$) — **Exposed at Card #6**.
  2. `TL017` (`U011`, `electrical`, `electrical_change`): `line.6:active_power_to` (`106.10050`, `52,455.3 -> 40,647.0`, $-22.5\%$) — **Missed at Stage 1** (`selector_score = 3.613`, ranked 5th among electrical updates).
  3. `TL019` (`U009`, `electrical`, `electrical_change`): `line.8:current_to` (`114.10070`, `3.3326 -> 3.8772`, $+16.3\%$) — **Missed at Stage 1** (`selector_score = 2.9666`).
  4. `TL021` (`U012`, `network`, `electrical_report`): `line.9:current_from` (`119.10150`, `1.2118 -> 0.5976`, $-50.7\%$) — **Missed at Stage 1** (`selector_score = 3.7319`).

---

## 2. Stage 1 Evaluation — Evidence Selection (`Candidate Pool -> 10 Fact Cards`)

### 2.1 Full Candidate Pool (`627` units in `PILOT-W01`, `612` units in `PILOT-W02`)

Because `605` units in `PILOT-W01` and `590` units in `PILOT-W02` are unlabeled, full-pool Recall is `NOT_ESTIMABLE`, and full-pool Precision is `NOT_ESTIMABLE` whenever top-$K$ contains unlabeled units:

| Window | Method | Top-5 Labeled Coverage | Unlabeled @ 5 | `P@5` / `P_needed@5` | Top-10 Labeled Coverage | Unlabeled @ 10 | `P@10` / `P_needed@10` | Full-Pool `R@10` |
| --- | --- | ---: | ---: | --- | ---: | ---: | --- | --- |
| `PILOT-W01` | `random_50_seeds` | `0.0320` | `4.84` | `NOT_ESTIMABLE` | `0.0380` | `9.62` | `NOT_ESTIMABLE` | `NOT_ESTIMABLE` |
| `PILOT-W01` | `statistical_global_score` | `1.0000` (5/5) | `0` | `1.0000` / `0.4000` | `0.8000` (8/10) | `2` | `NOT_ESTIMABLE` (subset: `1.00` / `0.25`) | `NOT_ESTIMABLE` |
| `PILOT-W01` | `statistical_role_quota` | `1.0000` (5/5) | `0` | `1.0000` / `0.2000` | `1.0000` (10/10) | `0` | `1.0000` / `0.3000` | `NOT_ESTIMABLE` |
| `PILOT-W02` | `random_50_seeds` | `0.0240` | `4.88` | `NOT_ESTIMABLE` | `0.0300` | `9.70` | `NOT_ESTIMABLE` | `NOT_ESTIMABLE` |
| `PILOT-W02` | `statistical_global_score` | `1.0000` (5/5) | `0` | `0.8000` / `0.2000` | `1.0000` (10/10) | `0` | `0.8000` / `0.3000` | `NOT_ESTIMABLE` |
| `PILOT-W02` | `statistical_role_quota` | `1.0000` (5/5) | `0` | `1.0000` / `0.0000` | `1.0000` (10/10) | `0` | `0.9000` / `0.1000` | `NOT_ESTIMABLE` |

### 2.2 Within the 22-Unit Author-Validated Pool (`22 Labeled Units -> 10 Fact Cards`, 100% Coverage)

Within the 22 author-validated units per window, every candidate has a ground-truth label (`2 / 1 / 0`), enabling exact `P@K`, `R@K`, `P_needed@K`, `R_needed@K`, and graded `nDCG@K`:

| Window | Stage 1 Method | Top-10 `Needed / Useful / Not` | `P@5` | `P_needed@5` | `R_needed@5` | `nDCG@5` | `P@10` | `P_needed@10` | `R_needed@10` | `nDCG@10` |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `PILOT-W01` | `random_50_seeds` (mean) | — | `1.0000` | `0.2880` | `0.2400` | `0.5194` | `1.0000` | `0.2720` | `0.4533` | `0.6273` |
| `PILOT-W01` | `statistical_global_score` | `2 / 8 / 0` | `1.0000` | **`0.4000`** | **`0.3333`** | **`0.5890`** | `1.0000` | `0.2000` | `0.3333` | `0.6102` |
| `PILOT-W01` | `statistical_role_quota` | **`3 / 7 / 0`** | `1.0000` | `0.2000` | `0.1667` | `0.5594` | `1.0000` | **`0.3000`** | **`0.5000`** | **`0.7024`** |
| `PILOT-W02` | `random_50_seeds` (mean) | — | `0.8840` | `0.1720` | `0.2150` | **`0.4392`** | `0.8740` | `0.1700` | `0.4250` | `0.5638` |
| `PILOT-W02` | `statistical_global_score` | **`3 / 5 / 2`** | `0.8000` | **`0.2000`** | **`0.2500`** | `0.4110` | `0.8000` | **`0.3000`** | **`0.7500`** | **`0.5958`** |
| `PILOT-W02` | `statistical_role_quota` | `1 / 8 / 1` | **`1.0000`** | `0.0000` | `0.0000` | `0.3653` | **`0.9000`** | `0.1000` | `0.2500` | `0.5138` |

**Stage 1 Finding**:
- In `PILOT-W01` (which contains 3 IEC-104 control commands), `statistical_role_quota` outperforms `statistical_global_score` at $K=10$ (`nDCG@10 = 0.7024` vs `0.6102`, `R_needed@10 = 0.5000` vs `0.3333`) because the `command` quota preserves `switch.31:closed` and `switch.30:closed`, whose frame-occurrence score (`1.0986`) is lower than the high-z measurement series (`7.92`–`10.0`).
- Conversely, in `PILOT-W02` (which has **0** control commands), `statistical_role_quota` reserves 4 slots for low-score TCP `communication` flows (`Useful = 1`), crowding out two `Needed = 2` measurement changes (`TL017` `line.6:active_power_to` and `TL021` `line.9:current_from`). As a result, `statistical_global_score` achieves much higher `R_needed@10` (`0.7500` vs `0.2500`) and `nDCG@10` (`0.5958` vs `0.5138`), and `statistical_role_quota` even trails the 50-seed random mean within the 22-unit pool (`nDCG@10 = 0.5138` vs `0.5638`).

---

## 3. Stage 2 Evaluation — LLM Fact Selection (`Same 10 Fact Cards -> Chosen Facts`)

Stage 2 evaluates what each method selects **given the exact same 10 exposed Fact Cards**. Only `model_selected_fact_ids` (directly chosen by the LLM) are counted as autonomous fact selections; `system_resolved_evidence_ids` and edge endpoints are strictly excluded from the model's fact selection counts.

### 3.1 Non-LLM Baselines on the Same 10 Exposed Fact Cards

| Window | Exposed 10 Cards (`Needed / Useful / Not`) | Stage 2 Baseline | `P@1` / `P_needed@1` | `nDCG_10@1` | `P@3` / `P_needed@3` | `nDCG_10@3` | `nDCG_22@3` | `P@5` / `P_needed@5` | `nDCG_10@5` |
| --- | --- | --- | --- | ---: | --- | ---: | ---: | --- | ---: |
| `PILOT-W01` | `3 / 7 / 0` | `random_within_10` (50 seeds) | `1.0000` / `0.2800` | `0.5200` | `1.0000` / `0.3267` | **`0.5435`** | **`0.5435`** | `1.0000` / `0.3160` | **`0.6626`** |
| `PILOT-W01` | `3 / 7 / 0` | `score_top_k_within_10` | `1.0000` / `0.0000` | `0.3333` | `1.0000` / `0.3333` | `0.5307` | `0.5307` | `1.0000` / `0.2000` | `0.5839` |
| `PILOT-W02` | `1 / 8 / 1` | `random_within_10` (50 seeds) | `0.9200` / `0.0800` | `0.3600` | `0.8933` / `0.1200` | `0.5803` | `0.3750` | `0.8880` / `0.1040` | `0.6569` |
| `PILOT-W02` | `1 / 8 / 1` | `score_top_k_within_10` | `1.0000` / `0.0000` | `0.3333` | `0.6667` / **`0.3333`** | **`0.6052`** | **`0.3911`** | `0.8000` / **`0.2000`** | **`0.6704`** |

### 3.2 Qwen3.5 9B vs Gemma4 12B Across All 32 Runs (`2 Windows x 2 Models x 2 Levels x 4 Permutations`)

| Window | Model | Level | Mode | Directly Chosen `fact_id`s | Chosen `edge_id`s | `Needed / Useful / Not` | Modality (`Net / Elec`) | `P@K` | `P_needed@K` | `nDCG_10@3` | `nDCG_22@3` | Faithfulness | Unsupp. Rel. Rate | Display Pos |
| --- | --- | --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `PILOT-W01` | `qwen3.5:9b` | `B2` | `original` | `[]` (abstain) | `[]` | `0 / 0 / 0` | `0 / 0` | `0.00` | `0.00` | `0.0000` | `0.0000` | `None` | `None` | `[]` |
| `PILOT-W01` | `qwen3.5:9b` | `B2` | `reversed` | `[]` (abstain) | `[]` | `0 / 0 / 0` | `0 / 0` | `0.00` | `0.00` | `0.0000` | `0.0000` | `None` | `None` | `[]` |
| `PILOT-W01` | `qwen3.5:9b` | `B2` | `seeded_shuffle` | `['TL016','TL019','TL003','TL017']` | `[]` | `0 / 4 / 0` | `1 / 3` | `1.00` | `0.00` | `0.3333` | `0.3333` | `1.0000` | `None` | `[1, 2, 3, 4]` |
| `PILOT-W01` | `qwen3.5:9b` | `B2` | `remapped_ids` | `[]` (abstain) | `[]` | `0 / 0 / 0` | `0 / 0` | `0.00` | `0.00` | `0.0000` | `0.0000` | `None` | `None` | `[]` |
| `PILOT-W01` | `qwen3.5:9b` | `B4` | `original` | `['TL001']` | `['R0001']` | `0 / 1 / 0` | `1 / 0` | `1.00` | `0.00` | `0.1564` | `0.1564` | `0.5000` | `1.0000` | `[2]` |
| `PILOT-W01` | `qwen3.5:9b` | `B4` | `reversed` | `['TL017']` | `['R0006']` | `0 / 1 / 0` | `0 / 1` | `1.00` | `0.00` | `0.1564` | `0.1564` | `1.0000` | `0.0000` | `[2]` |
| `PILOT-W01` | `qwen3.5:9b` | `B4` | `seeded_shuffle` | `['TL016']` | `['R0005']` | `0 / 1 / 0` | `0 / 1` | `1.00` | `0.00` | `0.1564` | `0.1564` | `1.0000` | `0.0000` | `[1]` |
| `PILOT-W01` | `qwen3.5:9b` | `B4` | `remapped_ids` | `['TL001']` | `['R0001']` | `0 / 1 / 0` | `1 / 0` | `1.00` | `0.00` | `0.1564` | `0.1564` | `0.5000` | `1.0000` | `[2]` |
| `PILOT-W01` | `gemma4:12b` | `B2` | `original` | `['TL009','TL001','TL003','TL019','TL012','TL013']` | `[]` | **`2 / 4 / 0`** | `5 / 1` | `1.00` | `0.3333` | `0.6462` | `0.6462` | `1.0000` | `None` | `[1, 2, 3, 4, 5, 6]` |
| `PILOT-W01` | `gemma4:12b` | `B2` | `reversed` | `['TL017','TL016','TL018','TL013','TL012','TL019']` | `[]` | `1 / 5 / 0` | `2 / 4` | `1.00` | `0.1667` | `0.3333` | `0.3333` | `1.0000` | `None` | `[2, 3, 4, 5, 6, 7]` |
| `PILOT-W01` | `gemma4:12b` | `B2` | `seeded_shuffle` | `['TL016','TL019','TL003','TL017','TL013','TL018']` | `[]` | `1 / 5 / 0` | `2 / 4` | `1.00` | `0.1667` | `0.3333` | `0.3333` | `1.0000` | `None` | `[1, 2, 3, 4, 5, 6]` |
| `PILOT-W01` | `gemma4:12b` | `B2` | `remapped_ids` | `['TL009','TL001','TL003','TL019','TL012','TL013']` | `[]` | **`2 / 4 / 0`** | `5 / 1` | `1.00` | `0.3333` | `0.6462` | `0.6462` | `1.0000` | `None` | `[1, 2, 3, 4, 5, 6]` |
| `PILOT-W01` | `gemma4:12b` | `B4` | `original` | `['TL009','TL001','TL003','TL019','TL012','TL013']` | `[]` | **`2 / 4 / 0`** | `5 / 1` | `1.00` | `0.3333` | `0.6462` | `0.6462` | `1.0000` | `None` | `[1, 2, 3, 4, 5, 6]` |
| `PILOT-W01` | `gemma4:12b` | `B4` | `reversed` | `['TL010','TL017','TL016','TL018','TL013','TL012']` | `[]` | **`2 / 4 / 0`** | `3 / 3` | `1.00` | `0.3333` | `0.6462` | `0.6462` | `1.0000` | `None` | `[1, 2, 3, 4, 5, 6]` |
| `PILOT-W01` | `gemma4:12b` | `B4` | `seeded_shuffle` | `['TL009','TL013','TL016','TL017','TL018']` | `['R0008']` | **`2 / 3 / 0`** | `2 / 3` | `1.00` | **`0.4000`** | **`0.8436`** | **`0.8436`** | `0.8333` | `1.0000` | `[9, 5, 1, 4, 6]` |
| `PILOT-W01` | `gemma4:12b` | `B4` | `remapped_ids` | `['TL009','TL001','TL003','TL019','TL012','TL013']` | `[]` | **`2 / 4 / 0`** | `5 / 1` | `1.00` | `0.3333` | `0.6462` | `0.6462` | `1.0000` | `None` | `[1, 2, 3, 4, 5, 6]` |
| `PILOT-W02` | `qwen3.5:9b` | `B2` | `original` | `['TL001','TL003','TL015']` | `[]` | `0 / 3 / 0` | `2 / 1` | `1.00` | `0.00` | `0.5158` | `0.3333` | `1.0000` | `None` | `[1, 2, 5]` |
| `PILOT-W02` | `qwen3.5:9b` | `B2` | `reversed` | `['TL016','TL014','TL015']` | `[]` | `0 / 3 / 0` | `0 / 3` | `1.00` | `0.00` | `0.5158` | `0.3333` | `1.0000` | `None` | `[3, 4, 6]` |
| `PILOT-W02` | `qwen3.5:9b` | `B2` | `seeded_shuffle` | `['TL016']` | `[]` | `0 / 1 / 0` | `0 / 1` | `1.00` | `0.00` | `0.2421` | `0.1564` | `0.5000` | `1.0000` | `[1]` |
| `PILOT-W02` | `qwen3.5:9b` | `B2` | `remapped_ids` | `['TL001','TL003','TL005']` | `[]` | `0 / 3 / 0` | `3 / 0` | `1.00` | `0.00` | `0.5158` | `0.3333` | `1.0000` | `None` | `[1, 2, 3]` |
| `PILOT-W02` | `qwen3.5:9b` | `B4` | `original` | `['TL001']` | `['R0001']` | `0 / 1 / 0` | `1 / 0` | `1.00` | `0.00` | `0.2421` | `0.1564` | `0.5000` | `1.0000` | `[1]` |
| `PILOT-W02` | `qwen3.5:9b` | `B4` | `reversed` | `['TL013']` | `['R0022']` | `0 / 0 / 1` | `0 / 1` | **`0.00`** | `0.00` | **`0.0000`** | **`0.0000`** | `1.0000` | `0.0000` | `[1]` |
| `PILOT-W02` | `qwen3.5:9b` | `B4` | `seeded_shuffle` | `['TL016']` | `['R0009']` | `0 / 1 / 0` | `0 / 1` | `1.00` | `0.00` | `0.2421` | `0.1564` | `0.5000` | `1.0000` | `[1]` |
| `PILOT-W02` | `qwen3.5:9b` | `B4` | `remapped_ids` | `['TL015','TL010']` | `[]` | **`1 / 1 / 0`** | `1 / 1` | `1.00` | **`0.5000`** | **`0.7003`** | **`0.4525`** | `1.0000` | `None` | `[5, 6]` |
| `PILOT-W02` | `gemma4:12b` | `B2` | `original` | `['TL001','TL003','TL005','TL006','TL015','TL014']` | `[]` | `0 / 6 / 0` | `4 / 2` | `1.00` | `0.00` | `0.5158` | `0.3333` | `1.0000` | `None` | `[1, 2, 3, 4, 5, 7]` |
| `PILOT-W02` | `gemma4:12b` | `B2` | `reversed` | `['TL013','TL009','TL016','TL014','TL010','TL015']` | `[]` | `1 / 4 / 1` | `2 / 4` | `0.8333` | `0.1667` | `0.2738` | `0.1769` | `1.0000` | `None` | `[1, 2, 3, 4, 5, 6]` |
| `PILOT-W02` | `gemma4:12b` | `B2` | `seeded_shuffle` | `['TL016','TL006','TL005','TL009','TL010','TL014']` | `[]` | `1 / 5 / 0` | `4 / 2` | `1.00` | `0.1667` | `0.5158` | `0.3333` | `1.0000` | `None` | `[1, 2, 3, 4, 5, 6]` |
| `PILOT-W02` | `gemma4:12b` | `B2` | `remapped_ids` | `['TL001','TL003','TL005','TL006','TL015','TL010']` | `[]` | `1 / 5 / 0` | `5 / 1` | `1.00` | `0.1667` | `0.5158` | `0.3333` | `1.0000` | `None` | `[1, 2, 3, 4, 5, 6]` |
| `PILOT-W02` | `gemma4:12b` | `B4` | `original` | `['TL001','TL003','TL005','TL006']` | `['R0001','R0002']` | `0 / 4 / 0` | `4 / 0` | `1.00` | `0.00` | `0.5158` | `0.3333` | `1.0000` | `0.0000` | `[1, 2, 3, 4]` |
| `PILOT-W02` | `gemma4:12b` | `B4` | `reversed` | `['TL013','TL009','TL016','TL014','TL010']` | `['R0012']` | `1 / 3 / 1` | `2 / 3` | `0.8000` | `0.2000` | `0.2738` | `0.1769` | `1.0000` | `0.0000` | `[1, 2, 3, 4, 5]` |
| `PILOT-W02` | `gemma4:12b` | `B4` | `seeded_shuffle` | `['TL016','TL006','TL005','TL009','TL010','TL014']` | `[]` | `1 / 5 / 0` | `4 / 2` | `1.00` | `0.1667` | `0.5158` | `0.3333` | `1.0000` | `None` | `[1, 2, 3, 4, 5, 6]` |
| `PILOT-W02` | `gemma4:12b` | `B4` | `remapped_ids` | `['TL001','TL003','TL005','TL006']` | `['R0001','R0002']` | `0 / 4 / 0` | `4 / 0` | `1.00` | `0.00` | `0.5158` | `0.3333` | `1.0000` | `0.0000` | `[1, 2, 3, 4]` |

---

## 4. Selection of `Needed (score = 2)` Facts: Qwen vs Gemma vs Non-LLM

1. **`PILOT-W01` (3 `Needed` cards exposed in the 10-card prompt: `TL009`, `TL013`, `TL010`)**:
   - **`qwen3.5:9b-q4_K_M`**: Selected **0 `Needed` facts across all 8 runs** (`B2` and `B4`, all 4 permutations). In `B2` it abstained in 3 of 4 permutations; in `B4` it emitted exactly 1 `Useful` fact (`TL001`, `TL017`, or `TL016`) + 1 relation claim. Even in `original` order where `TL009` (`switch.31:closed`, `Needed`) was at `display_pos = 1`, Qwen skipped `TL009` and picked `TL001` (`display_pos = 2`) because `TL001` was an endpoint of `R0001` (`communication`). Its `nDCG_10@3` in `B4` is `0.1564` across all 4 permutations — far below both `random_within_10` (`0.5435`) and `score_top_k_within_10` (`0.5307`).
   - **`gemma4:12b-it-q4_K_M`**: Selected **1 to 2 `Needed` facts in all 8 runs** (`P_needed@K = 0.1667`–`0.4000`, `nDCG_10@3 = 0.3333`–`0.8436`), simply because Gemma emits 5–6 fact claims per run and sweeps the first 6 cards in display order (`[1, 2, 3, 4, 5, 6]`).
2. **`PILOT-W02` (1 `Needed` card exposed in the 10-card prompt: `TL010` `line.13:current_from` at original position #6)**:
   - **`qwen3.5:9b-q4_K_M`**: Missed `TL010` in 7 of 8 runs (`P_needed@K = 0.0000`), and in `B4_reversed` picked `display_pos = 1` (`TL013`, `line.9:current_to` single-sample IPAL update), which is `Not Needed (0)` (`P@1 = 0.0000`, `nDCG = 0.0000`). Only in `B4_remapped_ids` (where `TL015` and `TL010` received low remapped IDs `TL101` and `TL106`) did Qwen select `TL010` (`Needed`).
   - **`gemma4:12b-it-q4_K_M`**: Because `TL010` is at original position #6, Gemma's habit of copying the first 4–6 displayed cards misses `TL010` in `B4_original` and `B4_remapped_ids` (where it only emits 4 facts `[1, 2, 3, 4]` plus 2 edges), and hits `TL010` when `TL010` lands within the first 5–6 displayed positions (`reversed` and `seeded_shuffle`). However, in `reversed`, `TL013` (`Not Needed`) is at `display_pos = 1`, so Gemma immediately selects `TL013` first (`P@K` drops to `0.8000`–`0.8333` and `nDCG_10@3` drops to `0.2738` vs `score_top_k_within_10` `0.6052`).

---

## 5. Network vs Electrical Selection Ratio

| Window | Model | `original` (`B4`) Net / Elec | `reversed` (`B4`) Net / Elec | `seeded_shuffle` (`B4`) Net / Elec | `remapped_ids` (`B4`) Net / Elec |
| --- | --- | --- | --- | --- | --- |
| `PILOT-W01` | `qwen3.5:9b` | `1 / 0` (100% Net) | `0 / 1` (100% Elec) | `0 / 1` (100% Elec) | `1 / 0` (100% Net) |
| `PILOT-W01` | `gemma4:12b` | `5 / 1` (83% Net) | `3 / 3` (50% Elec) | `2 / 3` (60% Elec) | `5 / 1` (83% Net) |
| `PILOT-W02` | `qwen3.5:9b` | `1 / 0` (100% Net) | `0 / 1` (100% Elec) | `0 / 1` (100% Elec) | `1 / 1` (50% Elec) |
| `PILOT-W02` | `gemma4:12b` | `4 / 0` (100% Net) | `2 / 3` (60% Elec) | `4 / 2` (33% Elec) | `4 / 0` (100% Net) |

Both models' network-vs-electrical ratios are governed by which modality occupies the top display positions (`[1..K]`), confirming the Task 1 Position Bias finding on the new Pilot windows.

---

## 6. Impact of Position Bias on Selection Quality & Stability

| Window | Model | Level | Direct Fact Jaccard Mean | Edge Jaccard Mean | Exact Set Match (All 4) | Display Pos #1 Selection Rate | Original Pos #1 Selection Rate |
| --- | --- | --- | ---: | ---: | --- | ---: | ---: |
| `PILOT-W01` | `qwen3.5:9b` | `B2` | `0.5000` (3 abstentions) | `1.0000` | `False` | `0.25` | `0.00` |
| `PILOT-W01` | `qwen3.5:9b` | `B4` | **`0.1667`** | `0.1667` | `False` | `0.25` | `0.00` |
| `PILOT-W01` | `gemma4:12b` | `B2` | `0.5079` | `1.0000` | `False` | `0.75` | `0.50` |
| `PILOT-W01` | `gemma4:12b` | `B4` | `0.4026` | `0.5000` | `False` | **`1.00`** | `0.75` |
| `PILOT-W02` | `qwen3.5:9b` | `B2` | **`0.1722`** | `1.0000` | `False` | **`0.75`** | `0.50` |
| `PILOT-W02` | `qwen3.5:9b` | `B4` | **`0.0000`** | `0.0000` | `False` | **`0.75`** | `0.25` |
| `PILOT-W02` | `gemma4:12b` | `B2` | `0.3801` | `1.0000` | `False` | **`1.00`** | `0.50` |
| `PILOT-W02` | `gemma4:12b` | `B4` | `0.3452` | `0.1667` | `False` | **`1.00`** | `0.50` |

- **Gemma4 12B exhibits a rigid prefix-copying bias (`disp_pos = [1, 2, 3, 4, 5, 6]`)**: In `7 / 8` runs on `PILOT-W01` and `8 / 8` runs on `PILOT-W02`, Gemma selects `display_pos = 1`, and in almost every run its selected facts are literally the first 4–6 cards in the prompt (`[1, 2, 3, 4, 5, 6]`). Consequently, when a `Not Needed (0)` card (`TL013` in `PILOT-W02`) is placed at `display_pos = 1` (`reversed`), Gemma selects it as its top claim, cutting its `nDCG_10@3` nearly in half (`0.5158 -> 0.2738`).
- **Qwen3.5 9B exhibits extreme permutation instability (`Direct Fact Jaccard = 0.0000` on `PILOT-W02 B4`)**: Across the 4 permutations of `PILOT-W02 B4`, Qwen picks `['TL001']`, `['TL013']` (`Not Needed`), `['TL016']`, and `['TL015', 'TL010']` — four disjoint sets (`Jaccard = 0.0000`), with `nDCG_10@3` swinging from `0.0000` (`reversed`) to `0.7003` (`remapped_ids`).

---

## 7. Unsupported Relation Rate, Faithfulness, and Abstention Analysis

1. **Qwen3.5 9B Relation Over-Claiming & Hallucinated Edge IDs**:
   - In `PILOT-W01 B4` (`original` and `remapped_ids`) and `PILOT-W02 B4` (`original` and `seeded_shuffle`), Qwen upgrades an `observed_fact` record link (`R0001` `communication` or `R0009` `shared_source`) to `claim_level = "supported_inference"`. The verifier rejects all 4 with `observed_link_cannot_be_upgraded_to_inference` (`unsupported_relation_rate = 1.0`, `faithfulness = 0.5`).
   - In `PILOT-W02 B2_seeded_shuffle` (where **no** candidate relations are provided in the `B2` prompt), Qwen hallucinates an edge ID `R_TL006-TL005` (`claim_level = "supported_inference"`), which the updated verifier catches and rejects with `unknown_edge_id`.
   - In `PILOT-W01 B2`, Qwen abstains in 3 of 4 permutations even though the window is `sufficient` and contains 3 `Needed` facts (`unjustified abstention`).
2. **Gemma4 12B Faithfulness & Newly Discovered `same_frame` Verifier Bug**:
   - Across `15 / 16` runs, Gemma achieves `faithfulness_rate = 1.0000` and `unsupported_relation_rate = 0.0000` (when it selects edges `R0001`, `R0002`, `R0012` in `PILOT-W02 B4`, it preserves their canonical `claim_level = "observed_fact"`).
   - **Concrete Verifier Failure Case (`R0008` in `PILOT-W01 gemma4 B4_seeded_shuffle`)**: Gemma selected `edge_id = "R0008"` (`relation_type = "same_frame"` between `TL012` `line.11:reactive_power_to` and `TL013` `line.11:active_power_to`) with its exact canonical level `observed_fact`. However, `_same_frame()` in `relations.py` populated `edge["evidence_ids"]` only with the shared parent TCP frame IDs (`shared[:4]`, whose `entity` is the TCP 5-tuple), omitting the two child `iec104_asdu` evidence IDs. When `verify.py` checked `left_rows = [row for row in rows if _entity_matches(row, source)]`, neither endpoint entity matched the parent TCP rows, causing a false-negative rejection (`relation_missing_endpoint_evidence`).

---

## 8. Failure Cases, Limitations, and Overall Conclusion

### Summary of Concrete Failure Cases (`runs/etgi/t3-author-validated-20261015/failure_cases.json`)

1. **Stage 1 Role-Quota Failures (`needed_unit_excluded_from_10_exposed_cards`)**:
   - `PILOT-W01`: 3 of 6 `Needed` units (`TL011` `switch.27:closed`, `TL014` `line.11:active_power_from`, `TL023` `line.10:active_power_from`) were selected into the 22-unit timeline but excluded by the 10-card role quotas (`command = 2`, `electrical_report = 2`, `electrical_change = 4`).
   - `PILOT-W02`: 3 of 4 `Needed` units (`TL017` `line.6:active_power_to`, `TL019` `line.8:current_to`, `TL021` `line.9:current_from`) were excluded from the 10 exposed cards because 4 slots were reserved for low-score `communication` flows.
2. **Stage 2 Selection of `Not Needed (0)` Units (`selected_not_needed_unit`)**:
   - `PILOT-W02` (`TL013` / `U007`, single-sample IPAL `line.9:current_to = 0.19905`): Exposed at Card #10 due to high background z-score (`5.2905`). When `reversed` order moved `TL013` to `display_pos = 1`, both `qwen3.5:9b` (`B4_reversed`) and `gemma4:12b` (`B2_reversed`, `B4_reversed`) immediately selected `TL013` as their first fact.
3. **Stage 2 Relation Verification Failures (`rejected_model_claim`)**:
   - `qwen3.5:9b`: 4 instances of `observed_link_cannot_be_upgraded_to_inference` and 1 instance of `unknown_edge_id` (`R_TL006-TL005`).
   - `gemma4:12b`: 1 false-negative verifier rejection (`relation_missing_endpoint_evidence` on `same_frame` edge `R0008`).

### Answer to the Core Evaluation Question

> **Does current evidence support that MIRAGE-OT's LLM layer outperforms non-LLM methods in selecting important incident evidence?**
>
> **No.**
> 1. **In Stage 1 (`22 Labeled Units -> 10 Fact Cards`)**, all filtering is performed by deterministic non-LLM scoring (`select.py`) and role quotas (`expose_timeline`). In `PILOT-W01` the role quota improves `nDCG@10` over global score (`0.7024` vs `0.6102`), but in `PILOT-W02` it underperforms both global score (`0.5138` vs `0.5958`) and random selection (`0.5638`) because fixed `communication` quotas displace `Needed` measurement changes.
> 2. **In Stage 2 (`Same 10 Fact Cards -> Model Selection`)**, `qwen3.5:9b-q4_K_M` selects only 1 fact in `B4`, misses all 3 exposed `Needed` facts in `PILOT-W01` (`nDCG_10@3 = 0.1564` vs random `0.5435` and score top-3 `0.5307`), and has `0.0000`–`0.1667` cross-permutation Jaccard stability. `gemma4:12b-it-q4_K_M` achieves higher `nDCG_10@3` (`0.6462` in `PILOT-W01`, `0.5158` in `PILOT-W02` original order) only by mechanically copying the first 4–6 cards in prompt display order (`display_pos = [1..6]`), which degrades sharply (`0.2738`) when a `Not Needed` card appears at `display_pos = 1`.
> 3. **Value of the Pipeline Lies in Deterministic Verification, Not LLM Selection**: The verifier (`verify.py`) reliably blocks Qwen's repeated upgrades of `observed_fact` links to `supported_inference` and hallucinated edge IDs (`R_TL006-TL005`), ensuring that unverified claims are withheld from publication.
