# Stage 1 Frozen Basic 28-Window Review Artifacts (`stage1-basic-frozen-20261015`)

This directory contains the public review artifacts for the complete 28-window Sherlock v3 `01-Basic` (`test`) evaluation under the frozen MIRAGE-OT engine (`configs/etgi/method_freeze.v1.json`).

| Field | Value |
| --- | --- |
| **Frozen Engine Commit (`git_commit`)** | `2981fb062b127218a34f23f2ff0292e4ca8cfea7` |
| **Reconstruction Code Hash (`code_sha256`)** | `d43d9867ce847df169e13345e4c3461cd99fd5167292a85cedaaa553d93e5bb3` |
| **Evidence Layer Code Hash (`evidence_code_sha256`)** | `032c6977ac0507e9c442b37e4e78455d0ab6d1a21b1efe751a0ccf37242a3b85` |
| **Total Windows Evaluated** | `28 / 28` (`100%` Quality Consistency pass rate, `100%` Lineage Consistency pass rate) |
| **Full Results & Per-Window Analysis** | `docs/STAGE1_BASIC_FROZEN_EXPERIMENT_RESULTS.md` |

## Contents of This Directory

1. **`stage1_summary.json`**: Complete machine-readable master table for all 28 windows (counts of transactions, anchors, storylines, bundles, cross-RTU bridges, unresolved branches, source container ledgers, index compatibility audits, runtime, storage, and explicit abstention/failure codes).
2. **`ALL_28_WINDOWS_ARTIFACT_SHA256SUMS.txt`**: Exact byte sizes and SHA256 digests for all `504` generated files (`28 windows x 18 files`) in `runs/etgi/stage1-basic-frozen-20261015/reconstruction/`.
3. **`windows/<episode_id>/`**:
   - For all 28 windows: `run_manifest.json`, `lineage_consistency.json`, and compact `incident_synthesis.json` / `quality_consistency.json` / `investigation_report.md`.
   - Full 9-file review bundles (including `evidence_audit_bundle.json`, `transactions.json`, `event_anchors.json`, `investigation_report.json`) for four newly indexed representative windows across strata:
     - `ev_b15ac1c8e04d148f09cb` (`S2`: no-command window with 5 RTU bundles and 1 Cross-RTU Verified Element Bridge `BRG-001` on `line.2` across RTUs `172.16.3.14` and `172.16.3.16`).
     - `ev_e76705884b8fec84592a` (`S1`: control-command window with verified setpoint measurement transition on `sgen.1:active_power`).
     - `ev_d58f418ff4f085ccc0a7` & `ev_0c16cbd74b1af46886cc` (`S4`: periodic-measurement-only low-information windows demonstrating honest abstention with `0` verified anchors and `0` bridges).
   - Full review bundles for `ev_564bebaa45f0686cf98d`, `ev_4e913b93a51e7b3c9e31`, `ev_812f8057d7c974d9cf36`, and `ev_cbe1e5bef23346604396` remain in `review_artifacts/behavioral-r5-20261015/` and `review_artifacts/synthesis-method-freeze-20261015/`.
4. **`SHA256SUMS.txt`**: Verifiable checksums (`shasum -a 256 -c SHA256SUMS.txt`) for all 150 tracked files in this directory.

## Non-Equivalence & Scope Notice
These review artifacts do not contain raw Sherlock PCAPs, `.state.gz` archives, or full `evidence.sqlite` files (`547.44 MiB` total). `evidence_audit_bundle.json` contains only the cited lineage subset. Zero bytes were redacted or renumbered.
