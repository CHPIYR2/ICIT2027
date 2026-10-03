# OT Security Event Triage

Research target: IEEE ICIT 2027. Primary question: whether electrical/process and
network evidence improve event-conditioned OT security triage when combined.

The research specification is `Codex_OT_Security_Research_Brief_v2.md`.

Current stage: the approved Protocol-v2 exploratory observability matrix is complete.
The 84 evaluation events were previously observed; these new results are
post-confirmatory, not a new unseen test. The run contains 33 model/view conditions
(9 preserved E/FULL references and 24 new transport conditions), with Basic-only
training and fixed network post-event visibility of 60/45/30/15 seconds.
Electrical evidence improves some restricted-network baselines, with non-monotonic
gains and event-family tradeoffs. E-only nevertheless exceeds E+N in all 12 new
transport/model conditions. See [full results](docs/network_observability_results_v2.md),
[family analysis](docs/observability_family_results_v2.md). All 48 tests passed; final artifact
verification is recorded in `results/exploratory-v2/verification.json`.

The first cross-scenario held-out evaluation is preserved below.
The approved split/source/window protocol remains frozen. Pipeline v2 fixes APDU
regrouping duplicates and microsecond capture ordering; v1 artifacts are retained.
All 84 held-out episodes were scored once with Basic-only fitted models under a
pre-evaluation SHA256 lock, including command-group ablation and paired bootstrap.

Main N and EN binary predictions are identical for each model: RF/GB score Macro
F1 1.000, LR scores 0.243 and misses all 57 cyber events. A command-presence rule
also scores 1.000; the main experiment does not demonstrate an EN advantage over N.
See `docs/heldout_results.md` for full results and limits.
37 tests passed at that original stage. No LLM or full verifier is implemented.

The held-out results are now exposed: changes motivated by these scores are
exploratory and must not be described as a new unseen test on the same events.

## Development pipeline

```sh
UV_CACHE_DIR=.cache/uv uv pip sync --python .venv/bin/python requirements.lock
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
PYTHONPATH=src .venv/bin/python -m sherlock.build_v2 --partition development
.venv/bin/python experiments/run_development_v2.py
```

The completed run is protected against overwrite. Dependencies are pinned in
`requirements.lock`; the run stores a pre-fit code/config SHA256 snapshot, episode
hashes, model hashes, OOF predictions, metrics, and platform/package metadata.

## Preserved formal evaluation

`experiments/run_heldout.py` has separate `freeze`, `build`, and `score` phases.
The current completed run refuses overwrite; review `configs/evaluation.v1.lock.json`
and `results/heldout-v1/` for provenance. `scripts/report_heldout.py` renders the
existing scores only. Do not rerun build against frozen evidence in this workspace.

## Historical audit commands

The commands below document Phase 1 acquisition/audit. The report writers update
manifest timestamps and proposals. Run them in a separate audit copy after freeze;
do not overwrite the manifests referenced by `configs/protocol.v1.lock.json`.

```sh
python3 scripts/audit_sherlock.py
python3 scripts/audit_contents.py
python3 scripts/audit_followup.py
python3 scripts/build_audit_deliverables.py
python3 scripts/audit_sherlock.py
python3 -m unittest discover -s tests -v
```

The audit scripts use only Python's standard library; the complete test suite also needs the pinned ML environment. The content scan is a full
offline scan and can take several minutes. See `data/README.md` for the
pinned data source and integrity policy. Phase 1 findings are in
`docs/sherlock_audit.md`; candidate field permissions belong in
`docs/evidence_contract.md`. Do not ingest
`data/evaluator/` or audit reports into model features, retrieval, or LLM prompts.

Some preserved execution/provenance artifacts contain environment-specific absolute paths from the original run. These paths are non-secret provenance metadata and are not required for reproduction; reproduction instructions use repository-relative paths.

## ICIT 2027 final investigation experiment

The current manuscript is a draft: [paper source](icit2027_ot_investigation.tex),
[compiled PDF](icit2027_ot_investigation.pdf), and [build/status notes](BUILD_NOTES.md).
The final experiment methodology and results interpretation are in
[the experimental methodology](docs/final_experimental_methodology.md) and
[the final scoring results](docs/final_scoring_results.md). The frozen matching
policy is `configs/investigation-r5/matching.json`; final review-ledger and
report schemas are under `schemas/investigation-final-offline/`.

### Reproduce final scoring

Requirements: Python 3.11 or later and the repository checkout. The scoring
validator and scorer use the Python standard library; no API key, provider
account, network access, or model call is used.

From the repository root, run:

```sh
python3 scripts/reproduce_final_scoring.py
```

This verifies the portable public input archive against its manifest, checks
the frozen input commitment, matching-policy hash, scoring authorization,
scope-correction seal, completed R1 ledger hashes, output hashes, frozen schema
and scorer hashes, and committed per-run scores, then reruns scoring and
compares the resulting tables and result seal. The D0 diagnostic block is
carried through from the sealed result because D0 is a descriptive reference,
not part of the R1 subjective score matrix. The expected frozen scoring-input commitment is
`706fbbb5e8561981d3d0b2fc7f31aa139449bfc1a911b98801a456965fc8b1ad`; the
portable public archive has commitment
`14c24e47dfba2f9b8e0581ad02ebe3fdc94b90ebcbb8bf14afc442db7631ea87`. The
expected final result seal is
`17a86e07f16a8f4871de57e367bf61aeaf5ed95662ff86e3a1188db4c69c9e96`.

Expected headline results: Evidence Completeness is 0.0000 for E/N/EN;
G1-EN Complete-Support Rate is 0.9261; G0 Complete-Support Rate is 0.8723;
V1 Citation Precision and Complete-Support Rate are both 1.0000; V1 Q1–Q6
Coverage is 0.5278; V1 Required Withholding Recall is 0.3344; and V1 USCR is
NA because its denominator is zero.

The public archive contains the 477 completed R1 ledgers, three frozen
provider-incomplete delivery receipts, final generation outputs, V1 replay
outputs, event/view gold, scorer-visible evidence records, and the final
scope-context mapping needed by the scoring adapter. It omits API request and
provider response envelopes; rescoring uses the frozen final generation
outputs and R1 judgments, so those envelopes are unnecessary. D0 remains a
descriptive deterministic reference and is excluded from the subjective R1
score matrix.
