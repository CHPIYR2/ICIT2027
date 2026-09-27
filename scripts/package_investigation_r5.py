"""Create a NOT-FROZEN r5 review package after offline tests; no evaluation access."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from investigation_dryrun.common import load,file_hash,binding,create_json,utc
OUT=ROOT/'results/investigation-r5';CONFIG=ROOT/'configs/investigation-r5'

def package():
 tests=load(OUT/'offline_test_results.isolated.json');assert tests['status']=='PASS' and tests['tests_run']==247
 for ref in tests['source_files']+tests['test_files']:assert file_hash(ROOT/ref['path'])==ref['sha256'],ref['path']
 old=load(OUT/'preservation.before.json')['files']
 for ref in old:assert file_hash(ROOT/ref['path'])==ref['sha256'],ref['path']
 # Refresh only the NEW metric-spec binding after offline candidate clarification.
 mp=CONFIG/'metrics.json';m=load(mp);m['specification']=binding(ROOT/'docs/investigation-r5/metrics.md');mp.write_text(json.dumps(m,indent=2,ensure_ascii=False)+'\n')
 preservation={'status':'PASS','checked_files':len(old),'all_final_bytes_match_pre_r5_hashes':True,'original_gold_manifest_sha256':file_hash(ROOT/'annotations/gold/pilot-v1/manifest.json'),'human_gold_modified':False,'gold_semantics_change_required':False,'test_log_side_effect_and_exact_restoration':binding(OUT/'regression_side_effect_resolution.json'),'files':old}
 create_json(OUT/'preservation.final.json',preservation)
 folders=['src/investigation_r5','configs/investigation-r5','prompts/investigation-v1-r5','docs/investigation-r5','results/investigation-r5']
 new={str(p.relative_to(ROOT)) for folder in folders for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
 scripts={str(p.relative_to(ROOT)) for p in (ROOT/'scripts').glob('*investigation_r5.py')}
 new.update(scripts);new.add('tests/test_investigation_r5.py')
 report_path=ROOT/'docs/investigation_protocol.v1.offline_report.r5.md';candidate_path=ROOT/'configs/investigation_protocol.v1.offline_candidate.r5.json';inventory_path=ROOT/'configs/investigation_protocol.v1.freeze_inventory.r5.json'
 new.update([str(report_path.relative_to(ROOT)),str(candidate_path.relative_to(ROOT)),str(inventory_path.relative_to(ROOT)),'results/investigation-r5/changed_files.json','results/investigation-r5/delivery_manifest.json','results/investigation-r5/delivery_manifest.json.sha256'])
 create_json(OUT/'changed_files.json',{'existing_r4_files_intentionally_edited':[],'added_r5_files':sorted(new),'unchanged_file_list':binding(OUT/'preservation.final.json'),'note':'r4 denied-access test-log append was detected, separately preserved and restored by exact original-prefix hash; see resolution record. No human gold, research response or transport-history changes.'})
 manifest=load(OUT/'validation_manifest.json');audit=load(OUT/'input_audit.json')
 blockers=['Author review of r5 candidate, canonical ledger contract and proposed exact transport policy','8192 candidate has not been run; 64-position acceptance remains pending','Future live adapter/global single-flight scheduler and account headroom confirmation require authorization; r5 currently fails closed','Evaluation custody location/role ACL and OS logging not provisioned or verified; later separate authorization','Evaluation-gold version/hash commitment remains a custodian task; no access here','After successful authorized development validation, approve final bound inventory and explicit protocol freeze','Final 32-event evaluation requires separate authorization']
 added='\n'.join('- `'+p+'`' for p in sorted(new))
 report=f'''# Investigation Protocol v1 — r5 OFFLINE candidate report

**OFFLINE COMPLETE · NOT YET VALIDATED AT 8192 · NOT FROZEN.** Model API calls: 0. The 64-position development run was not executed. Evaluation evidence/gold/results were not accessed. Custody was not provisioned.

## A. Exact matrix

| Cell | View | Method | Citation | Repetitions |
|---|---|---|---|---|
| D0 | EN | Existing deterministic reference | Existing traceable links | One artifact/event |
| G0 | EN | GPT-4.1 fixed snapshot | Optional, not uncited | 3 |
| G1-E | E | Same model | Required | 3 |
| G1-N | N | Same model | Required; not historical B1 | 3 |
| G1-EN | EN | Same model | Required | 3 |
| V1-EN | EN | Exact corresponding G1-EN replay | Same citations | One/source repetition; zero model calls |

No V1-E/V1-N or new primary model/source/RQ arms. Full definitions: `docs/investigation-r5/methodology.md`, `configs/investigation-r5/matrix.json`.

## B. RQ contrasts

RQ1: G1-EN−G1-E and G1-EN−G1-N; view plus predeclared quota under fixed total budget, not adding E while retaining all N. Both contrasts reported; shared PCAP ancestry is not independent sensing.

RQ2: characterize G1-EN; compare G1-EN−G0 with identical EN bundle, measuring required-citation policy and schema enforcement, not citations versus no citations.

RQ3: V1-EN−the exact G1-EN raw output; only deterministic verification/publication added. Joint paired safety/coverage trade-off; no numerical non-inferiority margin, truth/causal verification or generator-improvement claim.

## C. Added/changed files

All candidate development changes are NEW r5 files. Exact machine list: `results/investigation-r5/changed_files.json`. Existing r4 files are not repurposed. Main additions: r5 routing/input checks, offline request builder/replay adapter, gold reader, canonical metric scorer, updated contrast routing, synthetic transport policy, pure acceptance function, shared prompt template, configs, documentation, tests and manifests. Full file list follows at the end.

## D. Intentionally unchanged

Final hash check covers **{len(old)}** pre-existing r4/parent bindings, including r4 inventory/delivery, prompts/configs/manifests, every response/failure/recovery/unknown record and sealed gold snapshots. Exact paths/hashes: `results/investigation-r5/preservation.final.json`.

Unchanged reusable core: `schemas/investigation_claim.v3.json`, `schemas/investigation_verification.v3.json`, both v3 Responses schemas, `src/investigation_dryrun/claims.py`, its canonical wording and replay engine, evidence formatter/retriever v2, event IDs, scenario map, matching and numeric specialization B. G0 bytes equal r4 B2; G1-EN bytes equal r4 B3. E/N prompts differ only by the bound view in one canonical required template.

## E. Metrics and denominators

Canonical specification and historical-name mapping: `docs/investigation-r5/metrics.md` and `configs/investigation-r5/metrics.json`.

Evidence Completeness uses common positive G_e; view-conditional completeness uses G_ev; retrieval recall uses complete retrieved support subset T_ev. Guardrails stay outside positive recall. Separate unavailable-view, not-retrieved and retrieved-not-recovered counts. Citation Precision counts supporting visible claim/evidence-role pairs, not ID existence. Complete-support rate requires the complete citation set support. Withholding uses predeclared Q1–Q7/guardrail opportunities, with separate strata and no credit for silence. Whole-output explicit withholding decisions form Withholding Precision. Numerical, Asset and Temporal consistency require completed human review, never verifier self-grading. Zero denominators are NA; all-withhold coverage is zero and no-security-assertions rate is NA.

Canonical names do not include a newly promoted Supported Claim Precision, verifier disposition accuracy or false-withhold rate. Historical fields remain explicitly labeled diagnostics only. Three-run within-event mean, event macro, supplementary micro, fixed scenario-stratified 2,000 bootstrap/seed 20270922 retained; only matrix/contrast routing changed.

## F. Disagreements and issues resolved

1. Old primary matrix omitted E and citation-required N despite RQ1; new approved two-axis matrix resolves that mismatch.
2. Citation Validity policy already required role support, but implementation accepted one opaque review Boolean. r5 mechanically requires existence, actual visibility and claim-role support judgments; it rejects contradictory historical validity fields.
3. Withholding/consistency/retrieval vocabulary existed in prior protocol but not completely in r4 scorer. r5 supplies the missing approved metrics without changing gold; Action Accuracy Q/guardrail opportunities are explicitly distinct from historical G_e∪H_e diagnostic.
4. Existing gold retrieval nulls for excluded facts/guardrails mean not applicable. Initial r5 strict check mistook them for pending review; corrected reader preserves null exactly. Eligible positive retrieval judgments must remain explicit Booleans. No gold edit was needed.
5. Synthetic replay test initially supplied numeric observations out of timestamp order; corrected fixture order, not verifier rules. First targeted run: 47 tests, 3 errors; next: 47 passed. First combined run: 245 tests, 1 nullable-accounting error; next: 247 tests, 1 preservation-side-effect failure; final isolated run: all 247 passed.
6. Historical regression deny test appended two synthetic denial records to r4 `runs/denied_access.jsonl`. Detected by preservation check, appended bytes retained separately under r5, exact original prefix recovered using its pre-r5 SHA-256. Historical log restored byte-for-byte. Subsequent regression runs patch output roots to temporary directories without editing old tests/code. No evaluation evidence was read. See `regression_side_effect_resolution.json`; do not claim there was never a temporary test side effect.
7. ConnectionResetError becomes a proposed transport-only retry in r5; historical terminal status is preserved. Local/config/TLS errors are not blanket-retried.

## G. Local tests

**{tests['tests_run']} passed; 0 failures; 0 errors; 0 skipped.** Includes 56 r5 tests plus 191 historical development/pilot/transport/cost tests. Network entry points disabled in harness. Synthetic fixtures only; no model outputs were used to tune tests or policies. Final evidence: `results/investigation-r5/offline_test_results.isolated.json` and `offline_tests.isolated.log`. Earlier failed logs retained for transparency.

## H. 64-position validation manifest

G0 19 prior B2 max_output_tokens positions; G1-EN 21 prior B3 positions; G1-E/G1-N four reviewed pilots × 3 each = 12+12. All 40 stress requests verified identical except max_output_tokens 4096→8192. Historical B1's 15 truncations and B3's one terminal non-cap failure are excluded, preserved unchanged.

Manifest: `results/investigation-r5/validation_manifest.json`. Status PREDECLARED_NOT_EXECUTED. V1-EN has 21 corresponding replay positions and no model calls. All 16 E inputs audited; max 12,870 evidence tokens. Total offline input audit: 48 event/view bundles. No gold semantics change is required.

Future acceptance: zero output-cap truncations; delivered smoke schema/view/reference checks pass; intended request diffs and immutable run bindings. No-delivery is separately reported and overall inconclusive, not cap success/failure. Any cap truncation stops capacity acceptance and returns to author; no automatic retry or output-cap increase.

## I. Proposed transport policy

Maximum 3 attempts/position, identical request; single flight, at least 60 seconds between starts with longer Retry-After respected; timeout 120s. Retry HTTP 408/429/5xx, narrow connection/reset/timeout/incomplete-read errors, or unrecoverable delivery envelope only. No retry for recoverable schema/visibility errors, citations, quality, scores, semantic errors, verifier outcomes, refusal, output-cap truncation, wrong model or local configuration errors. Preserve attempt history and unknown delivery. No auto recovery after exhaustion.

Exact classes/errno/pacing and limitations: `configs/investigation-r5/transport.candidate.json`, `docs/investigation-r5/validation_and_transport.md`. r5 has no live network adapter; generate() fails closed. A future authorized adapter must supply global pacing across positions, not only retry spacing. Last observed 30,000 TPM headroom must be confirmed; local conservative estimates are not exact provider TPM charges. No limit/API query occurred.

## J. Evaluation custody checklist

`docs/investigation-r5/custody_checklist.md` covers proposed location/role confirmation, OS/account ACL, deny proof for development/generation identity, restricted scoring access, OS access logs, external log commitments, non-sensitive sentinel allow/deny test, gold manifest/version/hash commitment and separate evaluation-runner authorization. No provisioning or directory inspection performed.

R1 reviewer and Author/R1 custodian; single-reviewer gold, no independent second custodian/reviewer, adjudication or IAA. Historical selected-event evidence/B0 inspection remains disclosed; no claim of historically untouched evaluation set.

## K. Candidate inventory and hashes

`configs/investigation_protocol.v1.freeze_inventory.r5.json` lists exact candidate paths/hashes, including authoritative RQs, current matrix/metrics, support-policy chain, schemas, prompts, model/output/input configs, runner/core dependencies, statistics, custody checklist and 64-position manifest. Parent r4 bindings retained. Inventory status FOR_AUTHOR_REVIEW_NOT_FROZEN; no chmod/seal operation performed. Delivery manifest and its SHA-256 sidecar bind the final package without circular self-hashes.

## L. Remaining freeze blockers

{chr(10).join('- '+x for x in blockers)}

## M. Recommended next authorization

Review and approve this r5 package, its proposed exact transport policy and the fixed 64-position DEVELOPMENT validation. That next authorization should explicitly allow connecting a gated live development adapter with global single-flight pacing and preflight hash locking, confirm account headroom, then execute only the declared 64 positions at 8192 with the stated stop/acceptance rules and exact G1-EN replay. No extra positions, evaluation run, custody provisioning or automatic freeze. All scientific prompt/evidence/schema/matching/metric/verifier bytes are locked before the first call.

**Does this invalidate or require modifying sealed human gold? NO.** Existing E/N/EN accounting and Q judgments are consumed without editing facts, aliases, guardrails or reviewer decisions. Current model calls: zero. STOP for author approval.

## Exact added-file list

{added}
'''
 report_path.write_text(report)
 authorities=['docs/investigation-r5/methodology.md','docs/investigation-r5/metrics.md','docs/investigation-r5/custody_checklist.md','docs/investigation-r5/validation_and_transport.md','docs/research_direction_lock.md','docs/investigation_protocol.md','configs/investigation_questions.v1.candidate.json','docs/investigation_questions.v1.candidate.md','results/investigation-semantic-r2/base_claim_support_policy.snapshot.md','docs/claim_support_policy_v2.md','docs/investigation_protocol.v1.semantic_resolution.r2.md','docs/investigation_protocol.v1.dryrun_amendment.r4.md']
 candidate={'version':'investigation-protocol-v1-offline-candidate-r5','status':'OFFLINE_COMPLETE_AWAITING_AUTHOR','protocol_frozen':False,'model_calls_authorized':False,'model_calls_executed':0,'output_cap':8192,'output_cap_status':'NOT_YET_VALIDATED','input_evidence_safety_ceiling':16384,'gold_semantics_change_required':False,'parent':binding(ROOT/'configs/investigation_protocol.v1.dryrun_candidate.r4.json'),'author_decision':binding(OUT/'author_decision.txt'),'matrix':binding(CONFIG/'matrix.json'),'metrics':binding(CONFIG/'metrics.json'),'statistics':binding(CONFIG/'statistics.json'),'model':binding(CONFIG/'model.candidate.json'),'token_budget':binding(CONFIG/'token_budget.candidate.json'),'prompt_manifest':binding(ROOT/'prompts/investigation-v1-r5/manifest.json'),'validation_manifest':binding(OUT/'validation_manifest.json'),'offline_tests':binding(OUT/'offline_test_results.isolated.json'),'report':binding(report_path),'authority_chain':[binding(ROOT/p) for p in authorities],'remaining_blockers':blockers}
 create_json(candidate_path,candidate)
 paths={ref['path'] for ref in old}|set(authorities)|new
 paths-= {str(inventory_path.relative_to(ROOT)),'results/investigation-r5/delivery_manifest.json','results/investigation-r5/delivery_manifest.json.sha256'}
 assert not any('api_key.txt' in p for p in paths)
 inventory={'version':'r5-freeze-candidate-inventory','status':'FOR_AUTHOR_REVIEW_NOT_FROZEN','protocol_frozen':False,'parent_inventory':binding(ROOT/'configs/investigation_protocol.v1.freeze_inventory.r4.json'),'candidate':binding(candidate_path),'files':[binding(ROOT/p) for p in sorted(paths)],'exclusion':'Credentials, caches, evaluation gold/results; self/delivery bound by external delivery manifest to avoid hash cycles'}
 create_json(inventory_path,inventory)
 delivery={'version':'r5-offline-delivery','protocol_frozen':False,'model_calls':0,'inventory':binding(inventory_path),'candidate':binding(candidate_path),'report':binding(report_path),'validation_manifest':binding(OUT/'validation_manifest.json'),'preservation':binding(OUT/'preservation.final.json'),'tests':binding(OUT/'offline_test_results.isolated.json'),'inventory_files':len(paths),'new_files':len(new)}
 create_json(OUT/'delivery_manifest.json',delivery);(OUT/'delivery_manifest.json.sha256').write_text(file_hash(OUT/'delivery_manifest.json')+'  delivery_manifest.json\n');print(json.dumps(delivery,indent=2))
if __name__=='__main__':package()
