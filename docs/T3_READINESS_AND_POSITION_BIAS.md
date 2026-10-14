# T3 Readiness & Position Bias Diagnostic (2026-10-15)

This document records the pre-T3 diagnostic experiments and engineering deliverables:
1. **Task 1 — Position & ID-Number Bias Diagnostic** (`runs/etgi/position-bias-20261015/`, code in `src/mirage_ot/etgi/postalert/position_bias.py`)
2. **Task 2 — De-identified Pilot Candidate Pool for Human Annotation** (`runs/etgi/t3-pilot-pool-20261015/`, code in `src/mirage_ot/etgi/postalert/pilot_pool.py`)
3. **Task 3 — Two-Stage Evaluation Harness** (`src/mirage_ot/etgi/postalert/eval_t3.py`)
4. **Task 4 — Engineering Fixes** (`unknown_edge_id` / `unknown_fact_id` precedence in `verify.py`; frame-occurrence scoring for valueless IEC-104 control commands in `select.py` and `explain.py`)

No T2 or earlier T3 run directories were overwritten. No model output or selector score is used as gold.

---

## 1. Task 4: Engineering Fixes Verified First

1. **`unknown_edge_id` and `unknown_fact_id` checked before `missing_evidence_ids` (`verify.py`)**:
   - Previously, when a baseline emitted a non-existent `edge_id` (such as `R_TL001-TL003` in `B1`) without `evidence_ids`, `_normalize()` could not populate `evidence_ids` from the missing anchor and `_check()` exited early with `missing_evidence_ids`.
   - Now `_check()` verifies that any supplied `fact_id` exists in `timeline_by_id` (`unknown_fact_id`) and any supplied `edge_id` exists in `edge_by_id` (`unknown_edge_id`) before checking `evidence_ids`.
2. **IEC-104 control commands without numeric values (`select.py`, `explain.py`)**:
   - Single-point commands (`C_SC_NA_1`, type 45, e.g. `switch.23:closed`) carry `value_present = False`, and setpoint commands (`C_SE_NC_1`, type 50, e.g. `sgen.6:target_active_power = 20000.0`) repeat the same setpoint across activation (`COT=6`) and confirmation (`COT=7`) frames, yielding zero within-window numeric range (`z = 0.0`) when absent from the background.
   - Previously, all control commands received `score = 0.0`, causing the 4th control command in `ev_0961` (`sgen.6:target_active_power`) to fall behind every `score > 0` candidate and drop out of the 24-event timeline.
   - Now `packet_control` groups score by `max(excess_control_frames_over_background, numeric_robust_z)` on the same `min(log1p(z), 10.0)` scale (`basis = "control_frames_minus_background"` or `"control_frame_occurrence"`), and `_compact_card()` exposes `source_frame_count` when `value_present` is false. All four control commands in `ev_0961` (`switch.23:closed`, `switch.24:closed`, `switch.25:closed`, `sgen.6:target_active_power`) now receive `score = 1.609` (`log1p(4)`) and remain in the selected timeline.

---

## 2. Task 1: Position & ID-Number Bias Diagnostic

Saved under `runs/etgi/position-bias-20261015/` (`code_sha256 = 15f741e0cb8e51f33b8787e7ec5f7c0d74b0b70fb951339428f3e319144c0f83`, model `qwen3.5:9b-q4_K_M`, temperature `0`, seed `1`, `num_ctx = 8192`).

For each of the three Basic development windows (`supplied-ev0961`, `preceding-ev0961`, `supplied-ev12`), the exact same 10 Fact Cards (`exposed_timeline`) and 8 Candidate Relations (`exposed_relations`) are tested under four permutations:
- `original`: canonical chronological order and canonical IDs (`TL...`, `R...`).
- `reversed`: reversed list order, canonical IDs preserved.
- `seeded_shuffle`: deterministic shuffle (`seed = 42`), canonical IDs preserved.
- `remapped_ids`: reversible bijective ID remapping (`TL... <-> TL101..TL110`, `R... <-> R0101..R0108`) where electrical cards receive the lowest remapped ID numbers (`TL101`–`TL104`), while card content is untouched. Model outputs are mapped back via `inverse_fact_map` / `inverse_edge_map` before running the exact same `verify_claims()`.

Every run directory (`<case>/<level>_<mode>/`) stores `prompt.json`, `raw_output.txt`, `id_mapping.json`, `verification.json`, and `trace.json`.

### 2.1 Results across Permutations (`B4`: 10 Fact Cards + 8 Candidate Relations)

| Window | Mode | Shown Fact IDs | Canonical Fact IDs | Canonical Edge IDs | Original Pos (1–10) | Display Pos (1–10) | Direct Modality (Net / Elec) | Verified / Rejected |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `supplied-ev0961` | `original` | `['TL009']` | `['TL009']` | `['R0002']` | `[1]` | `[1]` | `1 / 0` (100% Net) | `1 / 1` |
| `supplied-ev0961` | `reversed` | `['TL018']` | `['TL018']` | `['R0003']` | `[5]` | `[6]` | `0 / 1` (100% Elec) | `2 / 0` |
| `supplied-ev0961` | `seeded_shuffle` | `['TL019']` | `['TL019']` | `['R0005']` | `[8]` | `[1]` | `0 / 1` (100% Elec) | `2 / 0` |
| `supplied-ev0961` | `remapped_ids` | `['TL109']` | `['TL001']` | `['R0002']` | `[2]` | `[2]` | `1 / 0` (100% Net) | `1 / 1` |
| `preceding-ev0961` | `original` | `['TL001']` | `['TL001']` | `['R0001']` | `[1]` | `[1]` | `1 / 0` (100% Net) | `1 / 1` |
| `preceding-ev0961` | `reversed` | `['TL016','TL014','TL015']` | `['TL016','TL014','TL015']` | `[]` | `[10, 9, 5]` | `[1, 2, 6]` | `0 / 3` (100% Elec) | `3 / 0` |
| `preceding-ev0961` | `seeded_shuffle` | `['TL014']` | `['TL014']` | `['R0012']` | `[9]` | `[4]` | `0 / 1` (100% Elec) | `1 / 1` |
| `preceding-ev0961` | `remapped_ids` | `['TL104']` | `['TL015']` | `['R0001']` | `[5]` | `[5]` | `0 / 1` (100% Elec) | `1 / 1` |
| `supplied-ev12` | `original` | `['TL001']` | `['TL001']` | `['R0001']` | `[1]` | `[1]` | `1 / 0` (100% Net) | `1 / 1` |
| `supplied-ev12` | `reversed` | `['TL017']` | `['TL017']` | `['R0005']` | `[4]` | `[7]` | `0 / 1` (100% Elec) | `1 / 1` |
| `supplied-ev12` | `seeded_shuffle` | `['TL014']` | `['TL014']` | `['R0012']` | `[8]` | `[1]` | `0 / 1` (100% Elec) | `1 / 1` |
| `supplied-ev12` | `remapped_ids` | `['TL109','TL104']` | `['TL009','TL017']` | `[]` | `[2, 4]` | `[2, 4]` | `1 / 1` (50% Elec) | `2 / 0` |

### 2.2 Results across Permutations (`B2`: 10 Fact Cards Only, No Relations)

| Window | Mode | Canonical Fact IDs | Original Pos (1–10) | Display Pos (1–10) | Direct Modality (Net / Elec) | Verified / Rejected |
| --- | --- | --- | --- | --- | --- | --- |
| `supplied-ev0961` | `original` | `[]` (abstain) | `[]` | `[]` | `0 / 0` | `0 / 0` |
| `supplied-ev0961` | `reversed` | `[]` (abstain) | `[]` | `[]` | `0 / 0` | `0 / 0` |
| `supplied-ev0961` | `seeded_shuffle` | `['TL019', 'TL013']` | `[8, 4]` | `[1, 2]` | `1 / 1` | `2 / 1` |
| `supplied-ev0961` | `remapped_ids` | `[]` (abstain) | `[]` | `[]` | `0 / 0` | `0 / 0` |
| `preceding-ev0961` | `original` | `['TL001', 'TL002', 'TL015']` | `[1, 2, 5]` | `[1, 2, 5]` | `2 / 1` | `3 / 0` |
| `preceding-ev0961` | `reversed` | `['TL016', 'TL014']` | `[10, 9]` | `[1, 2]` | `0 / 2` | `2 / 4` |
| `preceding-ev0961` | `seeded_shuffle` | `['TL010']` | `[8]` | `[1]` | `1 / 0` | `1 / 1` |
| `preceding-ev0961` | `remapped_ids` | `['TL015', 'TL009']` | `[5, 6]` | `[5, 6]` | `1 / 1` | `2 / 0` |
| `supplied-ev12` | `original` | `[]` (abstain) | `[]` | `[]` | `0 / 0` | `0 / 0` |
| `supplied-ev12` | `reversed` | `['TL017', 'TL016']` | `[4, 6]` | `[7, 5]` | `0 / 2` | `2 / 0` |
| `supplied-ev12` | `seeded_shuffle` | `[]` (abstain) | `[]` | `[]` | `0 / 0` | `0 / 0` |
| `supplied-ev12` | `remapped_ids` | `[]` (abstain) | `[]` | `[]` | `0 / 0` | `0 / 0` |

### 2.3 Cross-Permutation Consistency Summary

| Window | Level | Direct Fact Pairwise Jaccard Mean | All-Referenced Fact Jaccard Mean | Edge Pairwise Jaccard Mean | Exact Set Match Across All 4 | Display Pos #1 Selection Rate | Original Pos #1 Selection Rate |
| --- | --- | ---: | ---: | ---: | --- | ---: | ---: |
| `supplied-ev0961` | `B2` | `0.5000` (3 abstentions) | `0.5000` | `1.0000` | `False` | `0.25` | `0.00` |
| `supplied-ev0961` | `B4` | **`0.0000`** | `0.1111` | `0.1667` | `False` | **`0.50`** | `0.25` |
| `preceding-ev0961` | `B2` | **`0.0417`** | `0.0417` | `1.0000` | `False` | **`0.75`** | `0.25` |
| `preceding-ev0961` | `B4` | **`0.1111`** | `0.1861` | `0.1667` | `False` | **`0.50`** | `0.25` |
| `supplied-ev12` | `B2` | `0.5000` (3 abstentions) | `0.5000` | `1.0000` | `False` | `0.00` | `0.00` |
| `supplied-ev12` | `B4` | **`0.0833`** | `0.1111` | `0.0000` | `False` | **`0.50`** | `0.25` |

### 2.4 Diagnostic Conclusions on Position & ID Bias

1. **The previous "0% electrical fact selection" in `original` order was an artifact of presentation position and ID numbering, not a semantic preference for network facts**:
   - In chronological `original` order, network packets occur slightly earlier in the window than the 1 Hz IPAL electrical state snapshots, so `display_pos = 1` is always a network fact (`TL009` or `TL001`). Under `original` order in `B4`, Qwen picked `display_pos = 1` in **3 / 3** windows (100% network, 0% electrical).
   - When the exact same 10 cards are presented under `reversed`, `seeded_shuffle`, or `remapped_ids`, Qwen selects `electrical_change` facts in **9 / 9** `B4` runs (`TL018`, `TL019`, `TL016`, `TL014`, `TL015`, `TL017`).
2. **Severe order sensitivity (Pairwise Jaccard `0.00`–`0.11` in `B4`)**:
   - Across all three windows in `B4`, changing the card order or remapping `TL` IDs drops pairwise Jaccard similarity of chosen canonical Fact IDs to `0.0000` (`supplied-ev0961`), `0.1111` (`preceding-ev0961`), and `0.0833` (`supplied-ev12`).
   - Even whether `B2` abstains or emits claims changes when the 10 cards are shuffled (`supplied-ev0961` and `supplied-ev12`).
3. **Implication for T3 Evaluation**:
   - LLM fact selection over a multi-card prompt cannot be treated as order-invariant reasoning. Any T3 evaluation of LLM selection must evaluate across multiple deterministic card permutations/ID remappings and report position-sensitivity alongside selection metrics.

---

## 3. Task 2: Pilot Candidate Pool (`runs/etgi/t3-pilot-pool-20261015/`)

Built from two Sherlock `01-Basic/test` windows never used in any prior Post-Alert experiment:
- `PILOT-W01` (`ev_3e4d36008b29595ef246`, `1742959890.1894352`–`1742959950.3827677`, 60.193 s):
  - Full atomic candidate pool: **627** units (**5,085** lineage + parent rows verified, `missing_ids = []`, `row_check_failures = []`).
  - Bounded pilot annotation pool: **22** atomic units (`14` network: `3` IEC-104 control commands, `5` IEC-104 measurement reports, `6` TCP flows; `8` IPAL electrical updates; **222** lineage + parent rows verified, `missing_ids = []`).
- `PILOT-W02` (`ev_3e4d36008b29595ef246_post15s`, `1742959950.3827677`–`1742959965.3827677`, 15.0 s post-window interval):
  - Full atomic candidate pool: **612** units (**1,366** lineage + parent rows verified, `missing_ids = []`, `row_check_failures = []`).
  - Bounded pilot annotation pool: **22** atomic units (`14` network: `6` TCP flows, `8` IEC-104 measurement reports; `8` IPAL electrical updates; **87** lineage + parent rows verified, `missing_ids = []`).

Deliverable layout under `runs/etgi/t3-pilot-pool-20261015/`:
- `annotator_pack/ANNOTATION_INSTRUCTIONS_zh-TW.md`: Traditional Chinese annotation guide explaining atomic units, shared IEC-104 frames, IPAL/IEC-104 shared source dependency, and the `needed` / `useful` / `not_needed` / `cannot_judge` rubric.
- `annotator_pack/PILOT-W01_annotator_A.json`, `PILOT-W01_annotator_B.json`, `PILOT-W02_annotator_A.json`, `PILOT-W02_annotator_B.json`: de-identified candidate units (`U001`–`U022`) shuffled with independent seeds for Annotator A and Annotator B, with all selector scores, ranks, scenario names, and model outputs stripped.
- `annotator_pack/PILOT-W01_response_template.json`, `PILOT-W02_response_template.json`: structured response forms for human annotators.
- `custodian/custodian_key.json` & `custodian/PILOT-W0{1,2}/`: full canonical timelines, 627/612-unit full candidate pools, complete lineage audit bundles, and Stage 1 baseline selections (`stage1_baselines.json`).

---

## 4. Task 3: Two-Stage Evaluation Harness (`src/mirage_ot/etgi/postalert/eval_t3.py`)

Separates T3 evaluation into two independent stages:
1. **Stage 1 (`stage1_baselines`) — Evidence Selection (`Full Candidate Pool -> 10 Fact Cards`)**:
   - Evaluates `random` (50 fixed seeds), `statistical_global_score` (top-K by score without role quotas), and `statistical_role_quota` (`select_evidence` + `expose_timeline`) over the full 600+ unit candidate pool.
2. **Stage 2 (`stage2_selection`) — LLM Fact Selection (`Same 10 Fact Cards -> Chosen Facts & Claims`)**:
   - Evaluates the model's chosen facts (`model_direct_unit_ids` and `model_with_edge_endpoints_unit_ids`), `faithfulness_rate`, `unsupported_relation_rate`, and `abstained`.
3. **Scoring Guard (`evaluate_with_gold`)**:
   - Implements `P@K`, `R@K`, `P_needed@K`, `R_needed@K`, and graded `nDCG@K` (`needed = 2`, `useful = 1`, `not_needed = 0`).
   - When `gold_labels` is `None`, returns `status = "AWAITING_HUMAN_GOLD"` and refuses to compute pseudo-precision/recall against selector or model outputs.
