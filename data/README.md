# Sherlock data

Pinned release: **v3**, Zenodo record **18467070**, DOI
[10.5281/zenodo.18467070](https://doi.org/10.5281/zenodo.18467070).
License in the saved publisher metadata: CC BY 4.0.

- `raw/sherlock/v3/`: original scenario ZIPs; `.part` means acquisition is incomplete.
- `manifests/zenodo_18467070.json`: publisher metadata retrieved for this release.
- `manifests/sherlock_manifest.json`: local acquisition and integrity status.
- `manifests/*.members.json`: archive member inventories, generated after verification.
- `manifests/acquisition_status.json`: current finite download-supervision status.
- `manifests/acquisition.log`: progress and integrity log.
- `manifests/sherlock_preliminary.json`: CRC-checked member probe, explicitly not a complete audit.

Run `python3 scripts/audit_sherlock.py` from the project root to verify completed
downloads against publisher sizes and MD5 checksums, compute local SHA256 hashes,
and inventory ZIP members. Exit code 2 means acquisition is not yet fully verified.
Archive verification is not a completed semantic dataset audit.

All three downloads and their acquisition supervisor have completed. The finite
`scripts/finish_sherlock_acquisition.py` job was used for that acquisition only;
it is not a recurring monitor and should not be restarted for content auditing.

The scoped Phase 1 audit is complete; see `manifests/content_audit/summary.json`
for full-scan versus schema-sampling coverage and documented unknowns. Use
`python3 scripts/audit_contents.py` to rerun core scans. `evaluator/event_catalog.json`
contains ground truth and must never be ingested into model features or retrieval.
Proposed split and evidence contract remain under `configs/*.proposed.json`.

To inspect complete members while downloading, run `python3 scripts/probe_sherlock.py`.
This preliminary probe is now superseded by the complete core scan. It never
supplies a whole-archive SHA256 or completed audit status.

No raw data or privileged event descriptions should enter model prompts. Keep
event labels, simulator truth and scenario configuration in evaluator-only access.
Do not execute Python files shipped inside the dataset during inspection.
