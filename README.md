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
[family analysis](docs/observability_family_results_v2.md), and
[execution record](docs/protocol_v2_execution.md). All 48 tests passed; final artifact
verification is recorded in `results/exploratory-v2/verification.json`.

The first cross-scenario held-out evaluation is preserved below.
The approved split/source/window protocol remains frozen. Pipeline v2 fixes APDU
regrouping duplicates and microsecond capture ordering; v1 artifacts are retained.
All 84 held-out episodes were scored once with Basic-only fitted models under a
pre-evaluation SHA256 lock, including command-group ablation and paired bootstrap.

Main N and EN binary predictions are identical for each model: RF/GB score Macro
F1 1.000, LR scores 0.243 and misses all 57 cyber events. A command-presence rule
also scores 1.000; the main experiment does not demonstrate an EN advantage over N.
See `docs/heldout_results.md` for full results and limits, and
`docs/pre_evaluation_notes.md` for pre-score fixes and diagnostic choices.
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
pinned data source and integrity policy. Phase 1 findings belong in
`docs/sherlock_audit.md`; candidate field permissions belong in
`docs/evidence_contract.md`. Do not ingest
`data/evaluator/` or audit reports into model features, retrieval, or LLM prompts.
