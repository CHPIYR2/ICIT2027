# Stage 2 Frozen Cross-Scenario Review Artifacts (`stage2-cross-scenario-frozen-20261015`)

This directory contains the public review artifacts for the complete 75-window Stage 2 cross-scenario evaluation (`39` `02-Semiurban` test windows + `36` `03-Rural` test windows) and the unified 103-window comparison with Stage 1 `01-Basic`.

| Field | Value |
| --- | --- |
| **Frozen Engine Commit (`git_commit`)** | `2981fb062b127218a34f23f2ff0292e4ca8cfea7` |
| **Reconstruction Code Hash (`code_sha256`)** | `d43d9867ce847df169e13345e4c3461cd99fd5167292a85cedaaa553d93e5bb3` |
| **Evidence Layer Code Hash (`evidence_code_sha256`)** | `032c6977ac0507e9c442b37e4e78455d0ab6d1a21b1efe751a0ccf37242a3b85` |
| **Stage 2 Windows Evaluated** | `75 / 75` (`0` Execution Failures; `75/75` Quality Consistency pass; `74/75` Lineage Consistency pass, with `ev_5dd0102bf58bf2ce9487` automatically downgraded to `diagnostic_only_lineage_inconsistent`) |
| **Full Cross-Scenario Report** | `docs/STAGE2_CROSS_SCENARIO_EXPERIMENT_RESULTS.md` |

## Contents of This Directory

1. **`stage2_summary.json`**: Complete machine-readable master table for all 75 Stage 2 windows (`39` Semiurban + `36` Rural), including per-window distributions (`sum, mean, median, p95, max`), per-type quality bit audits, runtime, storage, and peak RSS.
2. **`stage2a_pilot_summary.json`**: Summary of the 6-window Stage 2A engineering compatibility pilot (3 Semiurban + 3 Rural).
3. **`execution_audit.json`**: Standalone audit of frozen module SHA256 hashes, Sherlock v3 archive sizes/MD5s, existing index compatibility rejection (`runs/etgi/semiurban-ev0431/evidence.sqlite`), separate audit vs. worker timing breakdown, and zero execution failures.
4. **`cross_scenario_comparison.json`**: Unified 103-window comparison across `01-Basic` (`28`), `02-Semiurban` (`39`), and `03-Rural` (`36`).
5. **`ALL_1500_STAGE2_ARTIFACT_SHA256SUMS.txt`**: Exact byte sizes and SHA256 digests for all `1,500` generated files (`75 windows x 20 files`) in `runs/etgi/stage2-cross-scenario-frozen-20261015/`.
6. **`windows/semiurban/<episode_id>/` & `windows/rural/<episode_id>/`**:
   - For all 75 windows: `run_manifest.json`, `quality_consistency.json`, and `lineage_consistency.json`.
   - For 8 representative windows across both scenarios (`ev_c77d85a14214995d2a2e`, `ev_d3c46672f9814dcdc40c`, `ev_229f54b33cd3bfeb8f67`, `ev_5dd0102bf58bf2ce9487`, `ev_8e3ee44aec0a0f81c99a`, `ev_bdac022dece4728f5d4e`, `ev_0d966f97d1922adb09bb`, `ev_33a53478089ef5a96639`): `transactions.json`, `incident_synthesis.json`, `investigation_report.md`, and `evidence_audit_bundle.subset.json` (explicitly marked `is_trimmed_review_subset = true` with the full bundle's byte size and SHA256).
7. **`SHA256SUMS.txt`**: Verifiable checksums (`shasum -a 256 -c SHA256SUMS.txt`) for all 262 tracked files in this directory.
