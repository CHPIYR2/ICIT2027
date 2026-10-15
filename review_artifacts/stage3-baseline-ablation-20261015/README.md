# Stage 3 Baseline, Ablation & Paper Evidence Review Artifacts (`stage3-baseline-ablation-20261015`)

This directory contains the public review artifacts for the Stage 3 Baseline (`B1`, `B2`), Ablation (`A1`, `A2`, `A3`), Representative Case Studies (`C1–C7`), and Synthetic Known-Answer Counterexamples (`S-KA1–S-KA3`) across all **103 Sherlock v3 `test` windows** (`28` `01-Basic`, `39` `02-Semiurban`, `36` `03-Rural`).

| Field | Value |
| --- | --- |
| **Frozen Engine Commit (`git_commit`)** | `2981fb062b127218a34f23f2ff0292e4ca8cfea7` |
| **Reconstruction Code Hash (`code_sha256`)** | `d43d9867ce847df169e13345e4c3461cd99fd5167292a85cedaaa553d93e5bb3` |
| **Evidence Layer Code Hash (`evidence_code_sha256`)** | `032c6977ac0507e9c442b37e4e78455d0ab6d1a21b1efe751a0ccf37242a3b85` |
| **Protocol & Results Documents** | `docs/STAGE3_BASELINE_ABLATION_PROTOCOL.md`, `docs/STAGE3_BASELINE_ABLATION_RESULTS.md`, `docs/MIRAGE_OT_ICIT2027_EXPERIMENTAL_FINDINGS.md` |

## Files in This Directory

- `stage3b_full_summary.json`: Complete 103-window baseline & ablation statistics (`Total, Mean, Median, P95, Max`, paired bootstrap 95% CIs, and per-window summaries).
- `stage3a_pilot_summary.json`: 12-window stratified pilot summary verified prior to Stage 3B.
- `representative_cases_and_counterexamples.json`: Full 6-part case study records for the 7 real Sherlock case categories (`C1–C7`) plus the 3 synthetic known-answer counterexamples (`S-KA1–S-KA3`).
- `ALL_103_WINDOWS_STAGE3_SHA256SUMS.txt`: Byte sizes and SHA256 checksums for all 103 per-window `stage3_window_comparison.json` files in `runs/etgi/stage3-baseline-ablation-20261015/windows/`.
- `SHA256SUMS.txt`: Verifiable checksums (`shasum -a 256 -c SHA256SUMS.txt`) for all tracked files in this directory.
