# Stage 3 Paper-Readiness Audit Response Review Artifacts (`stage3-audit-response-20261015`)

This directory contains the audit-hardened Stage 3 evaluation outputs across all **103 Sherlock v3 `test` windows** (`28` `01-Basic`, `39` `02-Semiurban`, `36` `03-Rural`), preserving the earlier `review_artifacts/stage3-baseline-ablation-20261015/` directory untouched.

| Field | Value |
| --- | --- |
| **Frozen Engine Commit (`git_commit`)** | `2981fb062b127218a34f23f2ff0292e4ca8cfea7` |
| **Reconstruction Code Hash (`code_sha256`)** | `d43d9867ce847df169e13345e4c3461cd99fd5167292a85cedaaa553d93e5bb3` |
| **Evidence Layer Code Hash (`evidence_code_sha256`)** | `032c6977ac0507e9c442b37e4e78455d0ab6d1a21b1efe751a0ccf37242a3b85` |
| **Updated Paper Documents** | `docs/STAGE3_BASELINE_ABLATION_RESULTS.md`, `docs/MIRAGE_OT_ICIT2027_EXPERIMENTAL_FINDINGS.md` |

## Audit Corrections Included in This Directory

1. **`stage3b_full_summary.json`**:
   - **Task 1 (`B1`)**: Separates `unsubstantiated_temporal_candidates` (`18,130`) from `explicit_evidence_constraint_conflicts` (`66,706`) and `corroborated_same_device_candidates` (`22,830`), plus `topology_breakdown` (`78,238` cross-device, `26,800` same-device separate-ASDU, `2,628` same-ASDU co-report).
   - **Task 2 (`A2`)**: Decomposes the `5,343` excess raw observations over `4,493` containers using `evidence.sqlite` packet identities into `true_cross_vantage_mirror_duplicate_count` (`1,845`), `same_asdu_different_ioa_point_count` (`572`), `distinct_messages_in_same_tcp_session_count` (`268`), `distinct_time_network_events_in_anchor_count` (`396`), `ipal_derived_observation_count` (`2,262`), and `unknown_provenance_relation_count` (`0`).
   - **Task 3 (`A1`)**: Includes both `all_windows` (`N=103`: `2,171` unsupported promotions, `409` spurious bridges) and `sensitivity_excluding_max_outlier_ev_52f5ee` (`N=102`: `205` unsupported promotions, `49` spurious bridges).
   - **Task 4 (`E3`)**: Separates `1_evidence_citation_presence` (`103/103`), `2_evidence_id_resolution` (`103/103`), `3_evidence_to_fact_anchor_consistency` (`102/103`), and `4_full_lineage_consistency` (`102/103`).
2. **`post_freeze_physical_state_evaluation.json`** (**Task 6**): Air-gapped, read-only post-freeze check against `01-Basic/raw/test/physical.zip` (`9/9` verified transactions and `6/6` cross-RTU bridges agree with simulator physical state transitions).
3. **`representative_cases_and_counterexamples.json`**: 7 categories / 11 real Sherlock case instances (`C1–C7`) plus 4 synthetic known-answer counterexamples (`S-KA1–S-KA4`, including `S_KA4_communication_anchor_multi_event_not_mirror_duplicate`).
4. **`ALL_103_WINDOWS_STAGE3_AUDIT_SHA256SUMS.txt` & `SHA256SUMS.txt`**: Verifiable SHA256 digests (`shasum -a 256 -c SHA256SUMS.txt`).
