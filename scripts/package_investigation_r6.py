"""Bind the reviewed offline r6 package without changing any historical artifact."""
import json,os,socket,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
os.environ['TIKTOKEN_CACHE_DIR']=str(ROOT/'.cache/tiktoken')
def blocked(*a,**k):raise RuntimeError('Offline packaging: network forbidden')
socket.create_connection=blocked;socket.socket.connect=blocked
from investigation_dryrun.common import load,binding,create_json,file_hash,utc
from investigation_r6.candidate import OUT,CONFIG,protected_references,validate_manifest

def package():
    tests_path=max(OUT.glob('offline_tests.*.json'),key=lambda p:int(p.name.split('.')[1]))
    tests=load(tests_path)
    if tests['status']!='PASS':raise ValueError('Latest local tests did not pass')
    for ref in tests['source_files']+tests['test_files']:
        if file_hash(ROOT/ref['path'])!=ref['sha256']:raise ValueError('Source changed since tests: '+ref['path'])
    old=protected_references();before=load(OUT/'preservation.before.json')['files']
    if old!=before:raise ValueError('Historical protected set changed')
    verification=validate_manifest(load(OUT/'validation_manifest.json'))
    create_json(OUT/'preservation.final.json',{'status':'PASS','files':old,'verified_files':len(old),
        'r4_r5_and_8192_validation_and_forensic_inputs_unchanged':True,'sealed_gold_unchanged':True,
        'no_evaluation_material_accessed':True,'model_calls':0,'created_at':utc()})
    rate=load(OUT/'rate_limit_evidence.json');est=load(OUT/'input_rate_estimates.json');plan=load(OUT/'validation_manifest.json')
    latest=rate['latest_available_token_header_record'];headers=latest['response_headers'] if latest else {}
    rows=rate['records']
    header_lines=[]
    for record in rows:
        h=record['response_headers']
        header_lines.append('| '+ ' | '.join(str(x) for x in [record['started_at'],record['provider_status'],h.get('x-ratelimit-limit-tokens','not present'),h.get('x-ratelimit-remaining-tokens','not present'),h.get('x-ratelimit-reset-tokens','not present')])+' |')
    report=ROOT/'docs/investigation_protocol.v1.offline_report.r6.md'
    report.write_text(f'''# Investigation Protocol v1 — r6 output-only OFFLINE candidate

OFFLINE COMPLETE. No model/API calls, no generation positions executed, no evaluation access, no custody provisioning, no protocol freeze. 24,576 is the next and intended FINAL DEVELOPMENT CANDIDATE, subject to validation, not a mathematical sufficiency guarantee. The author rejected 32,768 at this stage for account/project rate feasibility, not model capability.

## A. Candidate configuration

| Field | r6 value |
|---|---|
| Model snapshot | gpt-4.1-2025-04-14 |
| API / temperature / seed | Responses / 0 / omitted, no seed assumption |
| evidence_input_token_safety_ceiling | 16,384 |
| prompt_plus_evidence_input_token_ceiling | 21,152, unchanged scope excluding strict schema/provider framing |
| model_max_output_tokens | 24,576 |
| Provider request mapping | internal model_max_output_tokens → Responses max_output_tokens |
| Model context / documented max output | 1,047,576 / 32,768 |
| Execution | Disabled; generate() fails closed |

New names live only in configs/investigation-r6/. No historical global rename. Old fixed_evidence_tokens and evidence_token_safety_ceiling both represented 16,384; r6 exposes one unambiguous evidence ceiling. Source reuse still calls the unchanged r5 input validator. Model output and prompt-plus-evidence limits have separate keys. Provider usage includes additional schema/framing and is not the evidence ceiling.

## B. Exact scientific diff

Across every provider request, the only substantive change is max_output_tokens: 8192 → 24576. Prompt bytes, serialized evidence bytes, compiled strict schema bytes, snapshot, temperature, view and citation policy are equal. All other provider fields, including store=false, truncation=disabled and tools=[], are equal.

The r6 wrapper builds the bound r5 request and changes exactly that one value; equivalence rejects any other field change. Original scientific files are reused by path/hash rather than edited. Human gold, aliases, guardrails, support rules, Q1–Q7, claim/evidence schema, retrieval ranking/quotas/48,000-byte limit, input ceiling, visibility, verifier, matching, metrics/denominators, event IDs, strata, repetitions and statistics/bootstrap remain unchanged. Non-semantic differences are r6 configuration names, versions, provenance and output paths.

## C. Cap-selection rationale and history

- 4,096: rejected after 55/144 development positions ended specifically at max_output_tokens.
- 8,192: predeclared validation stopped at the first cap failure, after 18 positions (17 complete, 1 truncated); 46 unexecuted.
- Accepted forensic diagnosis: LIKELY_LEGITIMATE_CAPACITY, development only. No observed pathological repetition, combinatorial temporal expansion or serialization duplication sufficient to justify prompt/schema changes. The partial response remains incomplete and excluded from performance scoring.
- 12,288: the right-censored 8,192 observation does not establish that another 4,096 is adequate.
- 16,384: more headroom, but another sequential selection round remains possible; its name/value can be confused with the separate input evidence ceiling.
- 24,576: 3× the failed output allowance, below the historically observed 30,000-token rate allowance. Intended final development candidate, not guaranteed to complete.
- 32,768: documented model capability, but not approved at this stage because a configured allowance that large may exceed current account/project TPM feasibility.

No factual performance scores were computed or used to select the cap. Prior runs are configuration-selection provenance, not pieces of the new same-configuration matrix.

## D. Preserved rate-limit evidence

Assessment: **{rate['status']}**. Latest successful record with token headers: {latest['artifact']['path'] if latest else 'none'}.

17 successful completed r5 responses preserved generic x-ratelimit-limit-tokens=30000, limit-requests=500, remaining-requests=499 and reset-requests=120ms. Remaining tokens ranged 23008–27843; token reset intervals ranged 4.314–13.984s. Latest complete response: remaining-tokens={headers.get('x-ratelimit-remaining-tokens')}, reset-tokens={headers.get('x-ratelimit-reset-tokens')}, date={headers.get('date')}. The final truncated response omitted token-rate headers; it is retained rather than substituted with fabricated values. No project-specific token headers or Retry-After were present. All original headers, request IDs, dates, HTTP and provider statuses are bound in results/investigation-r6/rate_limit_evidence.json.

| Request start UTC | Provider status | Limit tokens | Remaining tokens | Reset tokens |
|---|---|---:|---:|---|
{chr(10).join(header_lines)}

The preserved 30,000 allowance exceeds 24,576 by 5,424. Across the exact 64 requests, the maximum local prompt+evidence+compiled-schema token count is {est['maximum_local_prompt_evidence_schema_tokens']:,}; this is advisory, not the provider's exact rate estimate and excludes provider framing. The larger of candidate allowance and this local estimate is below 30,000, but the remaining margin must not be treated as guaranteed operational headroom. A configured cap below a recorded TPM limit is necessary evidence, not sufficient proof of current request acceptance.

Four separate concepts: (1) model maximum output capability; (2) organization/project rate allowance, whose exact scope the generic recorded headers do not identify; (3) monthly/account/billing quota, unavailable here; (4) actual billable provider input/cache/output usage. None substitutes for another. Historical remaining balances/reset timers are not current account state. Freshness, project-specific constraints and concurrent account traffic need execution preflight. Any observed relevant token limit below 24,576 stops readiness. Missing/unparseable limits require confirmation. No new API limit query occurred.

## E. Full 64-position validation design

| Cell | Positions | Source |
|---|---:|---|
| G0 | 19 | Original B2 4096-cap stress positions |
| G1-EN | 21 | Original B3 4096-cap stress positions |
| G1-E | 12 | Same four reviewed pilots × three repetitions |
| G1-N | 12 | Same four reviewed pilots × three repetitions |
| Total generation | 64 | All use 24,576 |
| V1-EN | 21 corresponding replay positions | Exact eligible G1-EN bytes; zero model calls |

The author deliberately chose full 64 rather than 47-position continuation: a clean same-configuration final development validation. All 18 positions previously attempted at 8192 are included anew, alongside the prior 46 unsent positions. No old answer is reused or relabeled. Revalidation is triggered solely by predeclared configuration-level capacity failure, not answer performance. Logical identities and order equal r5; r6 run namespace and request hashes are new. Historical B1 15 truncations and the excluded non-cap B3 failure remain excluded.

## F. Request-equivalence verification

64/64 verified, with a saved r6 request artifact and position-level equivalence record for each. For 18 previously sent positions, the actual saved r5 request is also compared. For the other 46, the r5 request is reconstructed from unchanged, hash-bound predeclared artifacts and must match its predeclared request hash. No unsent request is described as an actual provider delivery.

Files: results/investigation-r6/validation_manifest.json, request_equivalence.json, manifest_verification.json, and requests/<event>/<cell>/rep-N.json. All 64 input bundles/receipts pass the unchanged r5 validators. The only generation change is 8192→24576; no mixed-cap positions.

## G. Capacity and conformance acceptance

Capacity requires zero delivered incomplete/max_output_tokens responses. FIRST such response: preserve raw envelope/text/metadata, no retry, stop new positions, fail 24,576 and return to author. No automatic 32,768, schema/prompt/retrieval change or completing the matrix after failure. Other failures retain their own categories and unchanged transport policy; missing/no-delivery positions are inconclusive, never silently successful.

Conformance retains strict local schema/context parsing, visible references/entities, E without hidden N, N without hidden E/process values, exact input budgets/receipts/hashes and unchanged finite verifier behavior. No conformance/quality/citation/score-driven retries. A complete candidate pass also needs every eligible G1-EN replay to retain exact raw input hash, zero model calls and separate raw/published artifacts. Missing replay is pending; mismatched replay cannot pass. New readiness aggregation enforces these author-required gates, not new research metrics or claim rules. No factual scores select the cap. Successful development validation would not guarantee final-evaluation capacity or authorize freeze.

## H. Proposed pacing and cost accounting

Global single flight, no batching, at least 60 seconds between request starts. Before every future request, evaluate latest available token/project limits, remaining/reset state, Retry-After and conservative request demand. Respect the longer wait. Insufficient remaining allowance without reset metadata requires confirmation; an allowance below the request requirement cannot be repaired by sleeping. Maximum three transport attempts under the unchanged approved narrow retry policy; preserve every attempt and unknown delivery. Monthly billing/quota errors require account action rather than pacing.

The r6 module supplies pure policy gates and an explicitly synthetic sequence harness, not a live runner. Any future authorized adapter must wire these gates before each request and retain the existing hard stop, provenance and isolated output namespace.

Accounting records actual input, cached input, derived uncached input=input−cached, output and unknown-usage attempts. Use the existing documented pricing formula/service-tier policy; missing usage remains missing, unknown cost remains unknown. Configured maximum output is not actual billed output. No fixed 64-position bill is predicted; this offline turn uses zero API tokens.

## I. Local tests

Latest suite: **{tests['tests_run']} PASS**, zero failures/errors/skips. Includes 259 prior relevant tests and 30 new r6 tests, with network blocked, local tokenizer cache and historical output roots redirected to temporary paths.

Coverage: distinct 24,576 output and 16,384 evidence limits; all 64 identities/same cap; actual/predeclared comparisons; unexpected request/schema/prompt/model changes rejected; no evaluation bundle read; live entrypoint denied; token/project limits, missing headers, remaining/reset/Retry-After and every-request state; first-cap synthetic stop and no retry; max-three transport attempts; actual usage accounting; full-matrix/replay readiness; exact unchanged replay engine and altered-byte rejection; historical preservation.

First suite: 289 tests, one error in the new synthetic replay fixture because it omitted required output_sha256. Only fixture metadata was corrected; verifier and scientific files stayed unchanged. Initial failure log retained. A subsequent pass preceded the final replay-readiness gate addition; the latest pass binds final tested source/test hashes. No model output was used to tune tests.

## J. Preservation

{len(old)} protected historical file bindings match exactly before and after tests: r4/legacy, r5 candidate, r5 8192 raw/request/attempt/replay/report files, forensic inputs and sealed gold. Includes the pilot manifest and its 98 snapshot files. The previous forensic report was delivered in chat; no nonexistent file/hash is invented. Its accepted diagnosis is recorded in the author decision; its preserved inputs are bound unchanged.

New artifacts exist only in r6 namespace files plus new r6 source/scripts/tests/documentation. No historical manifest overwritten. No evaluation material accessed; no custody provisioning; no protocol freeze. The 8192 partial claims remain configuration-selection diagnostics, never valid research output.

## K. Candidate inventory and hash

configs/investigation_protocol.v1.freeze_inventory.r6.json binds the exact candidate files and inherited protected dependencies. Its .sha256 sidecar records its digest; results/investigation-r6/delivery_manifest.json and .sha256 bind the inventory/report/candidate/tests without a circular self-hash. Status is FOR_AUTHOR_REVIEW_NOT_FROZEN; no seal/chmod operation.

## L. Remaining blockers

1. Explicit author approval for the full clean 64-position r6 development run; current model_calls_authorized remains false.
2. Execution preflight confirmation of current organization/project rate feasibility, including provider estimation/headroom and stale/missing project metadata. Monthly billing quota is not established by these headers.
3. A separately authorized, preflight-bound live adapter must consume these exact request artifacts and gates; current r6 entrypoint deliberately cannot execute models.
4. Capacity and conformance/replay results do not yet exist. 24,576 remains unvalidated and may fail.
5. Evaluation custody and later protocol freeze/final evaluation remain separate author decisions; no preparation here authorizes them.

## M. Exact recommended next authorization

Approve this bound r6 output-only offline package, then explicitly authorize connecting and preflight-locking a development-only live adapter and executing exactly the newly declared 64 positions at 24,576 with the fixed model/prompts/evidence/schema. Include all prior 8192 completions as fresh r6 requests; no historical output reuse. Authorization must retain global single-flight rate-aware pacing, max-three transport-only attempts, first-cap hard stop, exact eligible V1-EN replay, full actual usage/cost accounting and post-run preservation/tests. A failed integrity/rate gate stops before model calls. This would not authorize evaluation, custody provisioning, a cap increase or protocol freeze.

Explicit answers: human-gold modification required? **NO**. Prompt/schema/retrieval/verifier/metrics changed? **NO**, only output configuration and non-semantic version/config/readiness plumbing. Guaranteed no truncation at 24,576? **NO**. Is 32,768 rejected because the model cannot support it? **NO**; the concern is account/project execution feasibility.

STOP for explicit author approval.
''')
    candidate_path=ROOT/'configs/investigation_protocol.v1.offline_candidate.r6.json'
    create_json(candidate_path,{'version':'investigation-protocol-v1-offline-candidate-r6','status':'OFFLINE_COMPLETE_AWAITING_AUTHOR',
        'protocol_frozen':False,'model_calls_authorized':False,'model_calls_executed':0,'model_max_output_tokens':24576,
        'evidence_input_token_safety_ceiling':16384,'output_cap_status':'INTENDED_FINAL_DEVELOPMENT_CANDIDATE_NOT_YET_VALIDATED',
        'parent':binding(ROOT/'configs/investigation_protocol.v1.offline_candidate.r5.json'),
        'author_decision':binding(OUT/'author_decision.txt'),'model':binding(CONFIG/'model.candidate.json'),
        'token_budget':binding(CONFIG/'token_budget.candidate.json'),'scientific_bindings':binding(CONFIG/'scientific_bindings.json'),
        'execution_policy':binding(CONFIG/'execution_policy.candidate.json'),'rate_evidence':binding(OUT/'rate_limit_evidence.json'),
        'validation_manifest':binding(OUT/'validation_manifest.json'),'request_equivalence':binding(OUT/'request_equivalence.json'),
        'tests':binding(tests_path),'preservation':binding(OUT/'preservation.final.json'),'report':binding(report),
        'human_gold_modification_required':False,'prompt_schema_retrieval_verifier_metrics_changed':False,
        'guaranteed_no_truncation':False,'model_supports32768_but_account_feasibility_unapproved':True})
    paths={r['path'] for r in old}
    for folder in [OUT,CONFIG,ROOT/'src/investigation_r6']:
        paths.update(str(p.relative_to(ROOT)) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    paths.update(str(p.relative_to(ROOT)) for p in [candidate_path,report,ROOT/'tests/test_investigation_r6.py',*list((ROOT/'scripts').glob('*investigation_r6.py'))])
    inventory_path=ROOT/'configs/investigation_protocol.v1.freeze_inventory.r6.json'
    inventory={'version':'r6-output-only-candidate-inventory','status':'FOR_AUTHOR_REVIEW_NOT_FROZEN','protocol_frozen':False,
        'candidate':binding(candidate_path),'files':[binding(ROOT/p) for p in sorted(paths)],
        'excluded':'Credentials, caches, evaluation gold/results, self and delivery manifest; historical protected references reused exactly'}
    create_json(inventory_path,inventory)
    sidecar=Path(str(inventory_path)+'.sha256');sidecar.write_text(file_hash(inventory_path)+'  '+inventory_path.name+'\n')
    delivery={'version':'r6-offline-delivery','model_calls':0,'protocol_frozen':False,'inventory':binding(inventory_path),
        'inventory_sidecar':binding(sidecar),'inventory_files':len(paths),'candidate':binding(candidate_path),
        'report':binding(report),'validation_manifest':binding(OUT/'validation_manifest.json'),'tests':binding(tests_path),
        'preservation':binding(OUT/'preservation.final.json')}
    create_json(OUT/'delivery_manifest.json',delivery)
    (OUT/'delivery_manifest.json.sha256').write_text(file_hash(OUT/'delivery_manifest.json')+'  delivery_manifest.json\n')
    print(json.dumps(delivery,indent=2))

if __name__=='__main__': package()
