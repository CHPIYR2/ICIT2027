"""Post-run provenance, conformance and actual usage accounting; no research scoring."""
import collections,json,os,socket,sys
from decimal import Decimal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
os.environ['TIKTOKEN_CACHE_DIR']=str(ROOT/'.cache/tiktoken')
def blocked(*a,**k):raise RuntimeError('Offline reporting: network forbidden')
socket.create_connection=blocked;socket.socket.connect=blocked
from investigation_dryrun.common import load,binding,file_hash,digest,create_json,utc
from investigation_dryrun.tokens import summary
from investigation_r6.candidate import build_request
from investigation_r6.policy import assess,usage_components
from report_investigation_api_usage import cost,RATES,SOURCE
from check_investigation_r6_validation import integrity
OUT=ROOT/'results/investigation-r6-validation'

def stats(values):
    return summary(values) if values else {'n':0,'minimum':None,'median':None,'p90':None,'p95':None,'maximum':None}

def report():
    state=load(OUT/'execution.finished.json');pre=load(OUT/'preflight.json');plan=load(ROOT/'results/investigation-r6/validation_manifest.json')
    postpath=max(OUT.glob('post-execution.tests.*.json'),key=lambda p:int(p.name.split('.')[2]));post=load(postpath)
    assert post['status']=='PASS';checks=integrity();root=OUT/'runs'/state['run_id']
    fields=('attempted_positions','input_isolation_budget_binding_passes','transport_attempts','retries','finalized_positions',
        'strict_schema_passes','strict_schema_failures','schema_not_assessed','schema_context_reference_all_passes',
        'view_reference_violations','context_mismatches','transport_exhausted_positions','completed_provider_deliveries',
        'max_output_tokens_truncations','other_incomplete_responses','provider_delivered_responses',
        'transport_or_rate_failure_attempts','positions_with_completed_provider_delivery')
    counters={c:collections.Counter({'planned':n,**dict.fromkeys(fields,0)}) for c,n in plan['counts'].items()}
    output_tokens={c:[] for c in counters};retries={c:collections.Counter() for c in counters}
    all_attempts=[];rows=[];replays=[];acceptance_rows=[];metered=[];unmetered=[];response_ids=set();totals=collections.Counter();prices=[];unfinished=[]
    for p in plan['positions']:
        directory=root/p['event_id']/p['cell_id']/f"rep-{p['repetition']}";counter=counters[p['cell_id']]
        if not directory.exists():continue
        q,b,r,diff=build_request(p['r5_position'])
        assert load(directory/'request.json')==q and digest(q)==p['request_sha256']
        assert load(directory/'bundle.json')==b and load(directory/'receipt.json')==r
        assert load(directory/'request_diff.json')==diff
        attempt_dirs=sorted(directory.glob('attempt-*'),key=lambda x:int(x.name.split('-')[1]))
        assert len(attempt_dirs)<=3
        counter['attempted_positions']+=bool(attempt_dirs);counter['input_isolation_budget_binding_passes']+=bool(attempt_dirs)
        counter['transport_attempts']+=len(attempt_dirs);counter['retries']+=max(0,len(attempt_dirs)-1)
        m=load(directory/'completed.json') if (directory/'completed.json').exists() else None
        if m:
            assert m['position_id']==p['position_id'] and m['request_sha256']==p['request_sha256']
            if m.get('output_sha256'):assert file_hash(directory/'output.raw.json')==m['output_sha256']
            counter['finalized_positions']+=1;counter[m['status']]+=1
            checked=m.get('schema_validation_performed',False)
            counter['strict_schema_passes']+=checked and m['strict_schema_valid']
            counter['strict_schema_failures']+=checked and not m['strict_schema_valid']
            counter['schema_not_assessed']+=not checked
            counter['schema_context_reference_all_passes']+=bool(m.get('schema_and_visibility_valid'))
            counter['view_reference_violations']+=checked and not m['reference_visibility_valid']
            counter['context_mismatches']+='experiment_context_mismatch' in m.get('validation_errors',[])
            counter['transport_exhausted_positions']+=m['status']=='FAILED_NO_VALID_DELIVERY' and len(attempt_dirs)==3
            acceptance_rows.append({'position_id':p['position_id'],'status':m['status'],'termination_reason':m.get('termination_reason'),
                'request_diff_valid':m['request_diff_valid'],'schema_and_visibility_valid':m.get('schema_and_visibility_valid',False),'output_sha256':m.get('output_sha256')})
        else:unfinished.append({'position_id':p['position_id'],'attempts':len(attempt_dirs),'status':'STARTED_WITHOUT_COMPLETION','no_automatic_resume':True})
        completed_delivery=False
        for index,folder in enumerate(attempt_dirs):
            ap=folder/'attempt.json';finished=ap.exists();a=load(ap if finished else folder/'started.json')
            assert a['request_sha256']==p['request_sha256']
            if finished and m:assert a==m['attempts'][index]
            if a.get('response_sha256'):assert file_hash(folder/'response.raw')==a['response_sha256']
            if (folder/'output.raw').exists() and m and m.get('output_sha256'):
                assert file_hash(folder/'output.raw')==m['output_sha256']
            row={'position_id':p['position_id'],'cell_id':p['cell_id'],'artifact':binding(ap if finished else folder/'started.json'),'attempt_log_complete':finished,**a}
            if not finished:row.update(delivery_status='UNKNOWN',usage=None,reason='INTERRUPTED_ATTEMPT_WITHOUT_FINAL_LOG')
            all_attempts.append(row)
            md=row.get('provider_metadata') or {};status=md.get('status');usage=md.get('usage')
            if status=='completed':counter['completed_provider_deliveries']+=1;completed_delivery=True
            if status=='incomplete':
                cap=(md.get('incomplete_details') or {}).get('reason')=='max_output_tokens'
                counter['max_output_tokens_truncations']+=cap;counter['other_incomplete_responses']+=not cap
            if status in ('completed','incomplete'):
                counter['provider_delivered_responses']+=1
                if type((usage or {}).get('output_tokens')) is int:output_tokens[p['cell_id']].append(usage['output_tokens'])
            if row.get('reason') or row.get('HTTP_status') in (408,429) or (row.get('HTTP_status') or 0)>=500:
                counter['transport_or_rate_failure_attempts']+=1
            if index+1<len(attempt_dirs):retries[p['cell_id']][row.get('reason',row.get('rate_failure_class','unspecified'))]+=1
            if usage:
                response_id=md.get('id')
                if response_id:
                    assert response_id not in response_ids,'Duplicate response ID accounting';response_ids.add(response_id)
                parts=usage_components(usage);parts['total_tokens']=usage.get('total_tokens')
                if all(type(parts[k]) is int for k in ('input_tokens','output_tokens','total_tokens')):
                    assert parts['input_tokens']+parts['output_tokens']==parts['total_tokens']
                price=cost(usage,md.get('service_tier')) if md.get('model')=='gpt-4.1-2025-04-14' else None
                if price is not None:prices.append(price)
                for key,value in parts.items():
                    if key!='usage_missing' and type(value) is int:totals[key]+=value
                metered.append({'attempt':row['artifact'],'response_id':response_id,'model':md.get('model'),'service_tier':md.get('service_tier'),
                    'provider_usage':usage,'normalized_usage':parts,'known_cost_USD':str(price) if price is not None else None})
            else:unmetered.append({'attempt':row['artifact'],'delivery_status':row.get('delivery_status'),'HTTP_status':row.get('HTTP_status'),'usage':None,'cost':None})
        counter['positions_with_completed_provider_delivery']+=completed_delivery
        if p['cell_id']=='G1-EN':
            rp=directory/'V1-EN.replay.json'
            if rp.exists():
                v=load(rp);assert v['llm_calls']==0
                identity=v['status']=='REPLAYED' and bool(m) and v['source_output_sha256']==m.get('output_sha256')==file_hash(directory/'output.raw.json')
                if v['status']=='REPLAYED':assert identity and v['B3_input_sha256']==m['output_sha256']
                replays.append({'position_id':p['position_id'],'status':v['status'],'source_output_sha256':v.get('source_output_sha256'),
                    'llm_calls':0,'identity_pass':identity,'artifact':binding(rp)})
            elif m:unfinished.append({'position_id':p['position_id'],'status':'REPLAY_ARTIFACT_MISSING','no_automatic_regeneration':True})
        rows.append({'position_id':p['position_id'],'cell_id':p['cell_id'],'status':m['status'] if m else 'STARTED',
            'completed_artifact':binding(directory/'completed.json') if m else None,'attempts':len(attempt_dirs),
            'validation_errors':m.get('validation_errors',[]) if m else None})
    ordered=sorted(all_attempts,key=lambda x:x['start_monotonic']);gaps=[b['start_monotonic']-a['start_monotonic'] for a,b in zip(ordered,ordered[1:])]
    assert not gaps or min(gaps)>=60
    for previous,current in zip(ordered,ordered[1:]):
        if previous.get('pacing'):assert current['start_monotonic']>=previous['pacing']['next_start_monotonic']
    accepted=assess(plan,acceptance_rows,True,replays)
    if not accepted['truncated'] and (state['status']!='ALL_64_POSITIONS_FINISHED' or unfinished):
        accepted['status']='NOT_ACCEPTED_EXECUTION_OR_RATE_FEASIBILITY_BLOCKER'
    per_cell={}
    for cell,counter in counters.items():
        counter['not_attempted']=counter['planned']-counter['attempted_positions']
        per_cell[cell]={**dict(counter),'output_tokens_delivered_responses':stats(output_tokens[cell]),'retry_reasons':dict(retries[cell])}
    usage={'known_totals':dict(totals),'responses_with_usage':len(metered),'priced_responses':len(prices),
        'attempts_without_provider_usage':len(unmetered),'responses_with_partial_usage':sum(x['normalized_usage']['usage_missing'] for x in metered),
        'known_calculable_cost_USD':str(sum(prices,Decimal(0))),'actual_invoice_total':None,'rates_USD_per_million':RATES,
        'pricing_source':SOURCE,'formula':'uncached_input*input_rate + cached_input*cache_rate + actual_output*output_rate, per million tokens',
        'configured_output_cap_is_not_billed_usage':True,'missing_usage_not_zero':True,'metered_attempts':metered,'unmetered_attempts':unmetered}
    create_json(OUT/'usage_and_cost.json',usage)
    replay_summary={'planned':21,'eligible_completed_G1_EN':sum(r['cell_id']=='G1-EN' and r['status'] in ('DELIVERED','DELIVERED_SCHEMA_OR_VISIBILITY_INVALID') for r in rows),
        'replayed':sum(v['status']=='REPLAYED' for v in replays),'unavailable':sum(v['status']=='REPLAY_UNAVAILABLE' for v in replays),
        'not_reached':21-len(replays),'identity_passes':sum(v['identity_pass'] for v in replays),'identity_failures':sum(v['status']=='REPLAYED' and not v['identity_pass'] for v in replays),
        'model_calls':0,'records':replays}
    transport={'HTTP_status_counts':dict(collections.Counter(str(x.get('HTTP_status')) for x in all_attempts)),
        'rate_failure_classes':dict(collections.Counter(x['rate_failure_class'] for x in all_attempts if x.get('rate_failure_class'))),
        'retry_count':sum(c['retries'] for c in counters.values()),'unknown_delivery_attempts':sum(x.get('delivery_status')=='UNKNOWN' for x in all_attempts),
        'minimum_start_spacing_seconds':min(gaps) if gaps else None,'single_inflight':True,
        'attempt_records':[{'position_id':x['position_id'],'attempt':x['attempt'],'artifact':x['artifact'],'response_headers':x.get('response_headers'),
            'provider_response_id':(x.get('provider_metadata') or {}).get('id'),'HTTP_status':x.get('HTTP_status'),'started_at':x['started_at'],
            'finished_at':x.get('finished_at'),'pacing':x.get('pacing'),'rate_pre_request_gate':x.get('rate_pre_request_gate')} for x in all_attempts]}
    result={'version':'r6-development-validation-results','created_at':utc(),'scope':'DEVELOPMENT CAPACITY/CONFORMANCE ONLY; no research performance metrics',
        'execution_status':state['status'],'attempted_positions':sum(c['attempted_positions'] for c in counters.values()),'transport_attempts':len(all_attempts),
        'per_cell':per_cell,'capacity_acceptance':accepted,'replay':replay_summary,'transport':transport,
        'usage':binding(OUT/'usage_and_cost.json'),'preflight':binding(OUT/'preflight.json'),'request_size_preflight':binding(OUT/'request_size_preflight.json'),
        'pre_tests':pre['tests'],'post_tests':binding(postpath),'post_integrity':checks,'historical_and_preflight_bindings_unchanged':True,
        'protocol_deviations':[],'unfinished_or_review_required':unfinished,'human_gold_changed':False,'evaluation_accessed':False,'protocol_frozen':False,'positions':rows}
    create_json(OUT/'validation_report.json',result)
    write_report(result,usage,post,pre)
    paths=[p for p in OUT.rglob('*') if p.is_file() and p.name not in ('execution.lock','post_validation_manifest.json','post_validation_manifest.json.sha256')]
    paths+=list((ROOT/'src/investigation_r6_live').glob('*.py'))+[ROOT/'scripts/run_investigation_r6_validation.py',ROOT/'scripts/check_investigation_r6_validation.py',Path(__file__).resolve(),ROOT/'tests/test_investigation_r6_live.py']
    manifest={'version':'r6-post-validation-artifacts','protocol_frozen':False,'parent_candidate_inventory':binding(ROOT/'configs/investigation_protocol.v1.freeze_inventory.r6.json'),
        'parent_validation_manifest':binding(ROOT/'results/investigation-r6/validation_manifest.json'),'files':[binding(p) for p in sorted(set(paths))]}
    mp=OUT/'post_validation_manifest.json';create_json(mp,manifest);Path(str(mp)+'.sha256').write_text(file_hash(mp)+'  post_validation_manifest.json\n')
    print(json.dumps({'acceptance':accepted['status'],'attempted_positions':result['attempted_positions'],'attempts':len(all_attempts),
        'per_cell':per_cell,'tokens':dict(totals),'cost_USD':usage['known_calculable_cost_USD'],'post_manifest_sha256':file_hash(mp)},indent=2))

def write_report(result,usage,post,pre):
    size=load(OUT/'request_size_preflight.json');cells=result['per_cell'];replay=result['replay'];transport=result['transport'];total=usage['known_totals']
    def table(keys):
        return '\n'.join('| '+' | '.join([cell]+[str(cells[cell].get(key,0)) for key in keys])+' |' for cell in ('G0','G1-E','G1-N','G1-EN'))
    token_table='\n'.join('| '+' | '.join([cell]+[str(cells[cell]['output_tokens_delivered_responses'][key]) for key in ('n','minimum','median','p90','p95','maximum')])+' |' for cell in ('G0','G1-E','G1-N','G1-EN'))
    text=f'''# r6 24,576 Development Validation — Author Review

**{result['capacity_acceptance']['status']}**. Scope: development capacity, conformance, isolation, binding and exact replay only. No final research performance scores; protocol NOT FROZEN.

## A. Preflight integrity

PASS. Approved r6 inventory cc0b0f9a03578aa1cecaf45f742bd29284a0cceccb510a4bd73b21d53e86f84e verified; all 64 exact requests and 8192→24576 equivalence records verified. Model gpt-4.1-2025-04-14, Responses, temperature 0, no seed, original repetitions and scientific files unchanged. Evidence input ceiling 16,384 remains separate from output cap 24,576. Development IDs/bundles are guarded; no evaluation path or custody provisioning. Execution adapter was separately tested and bound before calls.

## B. Request-size/rate preflight

Local prompt+evidence+compiled-schema estimates over 64 positions: {size['request_token_summary']}. No estimate exceeded 30,000. Applicable rate-demand interpretation is max(configured maximum output allowance, estimated request demand), not their sum. Provider framing/estimator is not claimed exact. Historical token limit 30,000 was the author-approved starting feasibility evidence; live headers control subsequent waits/blockers. Model capability, TPM, monthly/account quota and actual billable usage remain distinct.

## C. Executed logical positions and attempts

{result['attempted_positions']}/64 positions attempted; {result['transport_attempts']} transport attempts. Execution status: {result['execution_status']}. No r5 output reused as r6. Unfinished/checkpoint-review records: {result['unfinished_or_review_required']}.

## D. Per-cell delivery and capacity

| Cell | Planned | Attempted | Completed provider deliveries | Cap truncations | Other incomplete | Strict schema passes | Strict schema failures | View/reference violations | Context mismatches |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
{table(['planned','attempted_positions','completed_provider_deliveries','max_output_tokens_truncations','other_incomplete_responses','strict_schema_passes','strict_schema_failures','view_reference_violations','context_mismatches'])}

Completed provider deliveries count provider responses, including retries if any; schema checks count finalized recoverable structured outputs. Incomplete/unrecoverable outputs are not automatically schema passes or schema failures; separate schema_not_assessed and transport categories remain in JSON.

| Cell | Attempts | Transport/rate failure attempts | Transport-exhausted positions | Retries | Not attempted |
|---|---:|---:|---:|---:|---:|
{table(['transport_attempts','transport_or_rate_failure_attempts','transport_exhausted_positions','retries','not_attempted'])}

Retry reasons by cell: { {c:cells[c]['retry_reasons'] for c in cells} }.

Output-token statistics for delivered completed/incomplete provider responses with usage; linear interpolation index=(n−1)q, not research performance:

| Cell | n | Min | Median | p90 | p95 | Max |
|---|---:|---:|---:|---:|---:|---:|
{token_table}

## E. 24,576 acceptance

{result['capacity_acceptance']['status']}. Truncated positions: {result['capacity_acceptance']['truncated']}. Conformance-invalid positions: {result['capacity_acceptance']['invalid']}. Missing/no-delivery positions remain explicit in validation_report.json. A first cap truncation stops new positions without retry or limit increase. A rate-feasibility/implementation blocker is not mislabeled as output-cap failure. No automatic freeze or guarantee of zero final-evaluation truncation.

## F. G1-E / G1-N isolation

| Cell | Attempted inputs passing unchanged isolation/budget/binding checks | All output schema/context/reference checks passed |
|---|---:|---:|
| G1-E | {cells['G1-E'].get('input_isolation_budget_binding_passes',0)} | {cells['G1-E'].get('schema_context_reference_all_passes',0)} |
| G1-N | {cells['G1-N'].get('input_isolation_budget_binding_passes',0)} | {cells['G1-N'].get('schema_context_reference_all_passes',0)} |

Only exact view and necessary metadata were provided; references/entities checked against each actual bundle. No hidden N in E or hidden E/process values in N. These are existing structural conformance gates, not a human factual/security oracle or new semantic tuning.

## G. G1-EN / V1-EN replay

Eligible completed G1-EN: {replay['eligible_completed_G1_EN']}; replayed: {replay['replayed']}; unavailable: {replay['unavailable']}; not reached: {replay['not_reached']}. Exact identity passes/failures: {replay['identity_passes']}/{replay['identity_failures']}. Verifier model calls: 0. Raw G1-EN and published/verifier artifacts are preserved separately. No V1-E/V1-N. No verifier accuracy claim.

## H. Rate-limit and transport events

HTTP status counts: {transport['HTTP_status_counts']}. Rate failure classes: {transport['rate_failure_classes']}. Retries: {transport['retry_count']}; UNKNOWN-delivery attempts: {transport['unknown_delivery_attempts']}. Minimum request-start spacing: {transport['minimum_start_spacing_seconds']} seconds. Global single flight, no batching. Recorded Retry-After/reset deadlines audited against subsequent starts. Full headers, IDs, statuses and timestamps retained per attempt. Temporary rate exhaustion is distinct from a single request exceeding the rate allowance and from billing/quota failure.

The inherited pure policy's live_authorized=false field does not itself grant execution authority; this run's authority is the separately preserved author_approval.txt and successful preflight. Scientific candidate flags remain unchanged.

## I. Actual usage and calculable cost

- Known input tokens: {total.get('input_tokens',0):,}
- Known cached input tokens (included in input): {total.get('cached_input_tokens',0):,}
- Known uncached input tokens: {total.get('uncached_input_tokens',0):,}
- Known output tokens: {total.get('output_tokens',0):,}
- Known total tokens: {total.get('total_tokens',0):,}
- Attempts without provider usage: {usage['attempts_without_provider_usage']}; partially missing usage responses: {usage['responses_with_partial_usage']}.
- Calculable subtotal: **USD {usage['known_calculable_cost_USD']}** across {usage['priced_responses']} priced responses.

Actual usage, documented GPT-4.1 rates/service tier and the approved formula are retained in usage_and_cost.json. Configured 24,576 is not billed output. Unknown usage/cost stays unknown; subtotal is not necessarily the final provider invoice. No fixed total bill was assumed.

## J. Pre/post local tests

Pre-execution: {load(ROOT/pre['tests']['path'])['tests_run']} PASS. Post-execution: {post['tests_run']} PASS. Network disabled during tests; synthetic fixtures only; historical result roots redirected to temporary directories. No output-driven scientific/test tuning during execution.

## K. r4/r5/r6/gold preservation

{result['post_integrity']}. All preflight-bound files and sealed pilot-gold snapshots remained byte-identical. Historical 4096/8192 runs and forensic inputs preserved. No aliases, facts, guardrails, reviewer decisions, prompts, schemas, retrieval, verifier, matching, metrics or tolerance changes. No evaluation evidence/gold/truth/ledgers/results accessed.

## L. Post-validation manifest/hash

New namespace: results/investigation-r6-validation/. post_validation_manifest.json and .sha256 bind all new execution/response/replay/accounting/report/test artifacts and adapter code; the r6 pre-run candidate inventory is not overwritten. Hash is provided in the sidecar and final author response.

## M. Deviations

{result['protocol_deviations']}. Any unfinished records listed above remain subject to author/checkpoint review, not automatic rerun. Early stopping under a hard-stop rule is compliance, not result selection.

## N. Remaining freeze blockers

Author review of this capacity/conformance outcome, any failed/pending position or execution blocker, separate custody/gold commitment arrangements and explicit final protocol freeze remain required. A successful development outcome alone authorizes neither evaluation nor freeze. Current protocol remains NOT FROZEN.

## O. Exact recommended next author action

Review the acceptance status and the per-position preserved failure/conformance records. If capacity or rate/implementation feasibility failed, decide a separately authorized next development action; no automatic cap increase or resumption. If all development gates passed, explicitly accept this development configuration, then address remaining custody and final freeze decisions under separate authorization. STOP for author review. No evaluation or custody action has been started.
'''
    (OUT/'author_review_report.md').write_text(text)

if __name__=='__main__':report()
