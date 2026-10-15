# Stage 3 Baseline, Ablation & Paper Evidence Suite (`experiments/stage3/`)

This package implements the Stage 3 evaluation framework for MIRAGE-OT without modifying any frozen engine module (`src/mirage_ot/etgi/postalert/`, `src/mirage_ot/etgi/reconstruction/`, `src/mirage_ot/etgi/evidence/`).

## Directory Structure

- `baselines/temporal_only.py`: **Baseline B1 (Temporal-Only Reconstruction)** — uses identical vantage-deduplicated event observations, timestamps, and 15.0s horizon (`MAX_LINKS_PER_EVENT=6`), without Behavioral Consistency Gate, Lineage Corroboration, or Incident Synthesis.
- `baselines/protocol_only.py`: **Baseline B2 (Protocol-Only Reconstruction)** — uses Phase 1 IEC-104 control transaction reconstruction (`COT=6/7/10`) with full protocol and quality checks, without Behavioral Event Anchor Discovery or Incident Synthesis. Marks no-command windows as `NOT_APPLICABLE_NO_CONTROL_COMMANDS`.
- `ablations/no_behavioral_gate.py`: **Ablation A1 (Without Behavioral Consistency Gate)** — removes `evaluate_behavioral_relation_consistency` and `evaluate_command_effect_inference`, quantifying `unsupported_promotion` and exact `evidence_constraint_violation` categories.
- `ablations/no_provenance_dedup.py`: **Ablation A2 (Without Provenance Deduplication)** — cancels multi-vantage mirror deduplication, same-ASDU container grouping, and IPAL zero-weight accounting.
- `ablations/no_incident_synthesis.py`: **Ablation A3 (Without Incident Synthesis)** — compares local storylines against Four-Layer Incident Synthesis (`rtu_asdu_bundles`, `verified_element_bridges`, `bridged_bundle_components`, `candidate_scenario_phases`, `competing_explanations`).
- `evaluation/metrics.py`: **Four-Category Evaluation (E1–E4)** and window-paired bootstrap 95% confidence intervals.
- `evaluation/case_studies.py`: **7 Real Sherlock Case Categories (C1–C7)** and **3 Synthetic Known-Answer Counterexamples (S-KA1–S-KA3)** (reported strictly separately).
- `run_stage3.py`: CLI runner supporting `--mode stage3a` (12-window stratified pilot) and `--mode stage3b` (full 103-window suite).

## Usage

```bash
# Stage 3A: 12-window stratified pilot (Basic 4 + Semiurban 4 + Rural 4)
.venv/bin/python -m experiments.stage3.run_stage3 --mode stage3a

# Stage 3B: Full 103-window comparison (Basic 28 + Semiurban 39 + Rural 36)
.venv/bin/python -m experiments.stage3.run_stage3 --mode stage3b
```
