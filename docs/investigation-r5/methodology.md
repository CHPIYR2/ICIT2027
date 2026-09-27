# Investigation Protocol v1 — r5 offline methodology candidate

Status: OFFLINE CANDIDATE; NOT FROZEN. No API or evaluation authorization. The author decision in `results/investigation-r5/author_decision.txt` is the current authority. r4 is preserved as historical development evidence, not relabeled as an r5 run.

## Authoritative RQs

RQ1 — Does combining electrical/process and network evidence improve the completeness of OT incident reconstruction compared with either evidence source alone?

RQ2 — How reliably can an LLM generate structured OT incident explanations when every substantive claim must cite observable evidence?

RQ3 — Can deterministic evidence verification reduce unsupported security conclusions while preserving useful investigation coverage?

These preserve `docs/research_direction_lock.md`, sections 6 and 13. Historical B1–B4 labels in that document do not override the current author's explicit matrix.

## Matrix

| Cell | View | Method | Citation | Repetitions | Role |
|---|---|---|---|---|---|
| D0 | EN | Existing deterministic structured reference | Existing evidence links | One artifact/event, aligned slots only | Descriptive reference |
| G0 | EN | gpt-4.1-2025-04-14 | Optional, never called uncited | 3 | RQ2 |
| G1-E | E | Same snapshot | Required | 3 | RQ1 |
| G1-N | N | Same snapshot | Required | 3 | RQ1 |
| G1-EN | EN | Same snapshot | Required | 3 | RQ1/RQ2/RQ3 |
| V1-EN | EN | Exact-byte G1-EN replay | Identical source citations | One per corresponding repetition | RQ3 |

No V1-E/V1-N, model comparisons, agents, new datasets or RQs. Historical B2 maps conceptually to G0; B3 to G1-EN; B4 to V1-EN; B1 is historical N citation-optional and is not G1-N. Cell identifiers stay in run metadata; output schema remains v3.

## Contrasts and conclusions

- RQ1: G1-EN minus G1-E, and G1-EN minus G1-N. Keep event, Q1–Q7, model, temperature 0, three repetitions, required-citation policy, schema, common output limit and evaluation rules fixed. The independent variable is view plus its predeclared retrieval allocation. Both contrasts must be reported. No claim of superiority over both sources unless both are supported by final evaluation.
- RQ2: characterize G1-EN reliability; compare G1-EN minus G0 on exactly the same EN bundle. Intervention is required-citation policy plus its predeclared schema enforcement. G0 still carries typed observation IDs and may cite; this is not citations versus no citations.
- RQ3: V1-EN minus the exact corresponding stored G1-EN output; same raw bytes, bundle, receipt and evidence IDs. Only deterministic evidence-consistency/support verification and publish/qualify/withhold processing is added. No claim of truth or causality verification, or improvement of the original generator.

E=64, N=64, EN=32N+32E, no cross-source quota borrowing; 48,000 compact JSON UTF-8 bytes. Existing retrieval order, including EN same-asset request-following E priority, is unchanged. This estimates investigation performance under the fixed budget and predeclared retrieval policy, not adding E while keeping every N observation unchanged. E/N derived from the same PCAP can share lineage; they are not independent sensors.

E includes process observations and necessary approved channel/configuration M only; N includes network observations and necessary control mapping M, no process values. Bundle construction includes only referenced M. Opaque provenance handles do not authorize hidden N content in E-only. Same-view capture ordering may answer Q4; Q5 cross-source relationships still require N and E, with both approved mappings for same-asset scope. Evidence absence, command execution, physical causation, intent, compromise and attribution are not inferred from timing. Q6 retains its four-layer distinction and no automatic malicious/benign label.

## RQ3 paired trade-off, no invented margin

Jointly report Unsupported Security-Claim Rate, Q1–Q6 Substantive Coverage, Evidence Completeness, Required Withholding Recall and Withholding Precision before/after verification, with paired differences and approved uncertainty. There is no 5%, 10%, 20% or other non-inferiority/pass-fail margin. Reduced unsupported claims alone is not success when useful coverage collapses. Always-withhold has coverage 0; no security assertions means the rate is NA, not zero.

## Statistics and selection

Three repetition ratios first averaged within each event; event-macro primary, pooled micro supplementary. Zero-denominator ratios are NA with counts. Failures with nonzero fixed denominators remain zero, not discarded. Conditional metrics compare common defined event sets and disclose exclusions. D0 micro counts its one artifact once; aligned slots are not three independent generations.

Preserve 2,000 scenario-stratified event bootstrap resamples, seed 20270922, 95% percentile interval and existing quantile implementation. Each paired contrast carries complete event repetitions together. Only baseline/contrast routing changed; repetitions, claims and packets are not independent units. CI is conditional on selected Sherlock events/scenarios, not new real-world deployments. No selected IDs or scenario strata changed. Existing design metadata: 16 Basic development events; 32 evaluation events (18 Semiurban, 14 Rural). Historical evidence/B0 inspection is disclosed; the evaluation set is not historically untouched.

## Version precedence

Current author decision → r5 methodology/matrix/metric definitions → approved Q1–Q7 and r2 specialization B → r4 narrow mapping/schema compatibility → unchanged evidence/export/support/matching rules. Obsolete narrative about pending models, old baseline names, old tolerances or independent adjudication remains historical, not active. Parent artifacts are retained with hashes rather than edited.

G0 prompt bytes equal r4 B2; G1-EN prompt bytes equal r4 B3. G1-E/N are mechanically rendered from one required template by replacing only `{VIEW}`. Existing v3 schemas, canonical wording, claims.py verifier core and matching config are unchanged. 8192 is a NOT YET VALIDATED output candidate; 16384 is the separate input evidence safety ceiling.
