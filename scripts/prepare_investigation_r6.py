"""Create only the offline r6 namespace; preserve and reuse all scientific r5 bytes."""
import copy,json,os,socket,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ['TIKTOKEN_CACHE_DIR']=str(ROOT/'.cache/tiktoken')
def blocked(*args,**kwargs): raise RuntimeError('r6 OFFLINE: network forbidden')
socket.create_connection=blocked;socket.socket.connect=blocked
sys.path.insert(0,str(ROOT/'src'))
from investigation_dryrun.common import load,dumps,digest,binding,create_json,utc
from investigation_dryrun.tokens import count
from investigation_r6.candidate import OUT,CONFIG,PARENT_PLAN,protected_references,build_request,validate_manifest
from investigation_r6.policy import rate_feasibility

def prepare():
    protected=protected_references()
    OUT.mkdir(exist_ok=False);CONFIG.mkdir(exist_ok=False)
    create_json(OUT/'preservation.before.json',{'status':'PASS','files':protected,'created_at':utc(),'forensic_scope':'Preserved r5 raw provider/output/request/attempt bytes; accepted prior forensic report was in chat, not a standalone file; no partial claims used for scoring'})
    approval=Path('/Users/potinglu/.codex/attachments/525011d8-42ba-4cc5-8814-4ef505b51f72/貼上的文字.txt')
    (OUT/'author_decision.txt').write_bytes(approval.read_bytes())
    records=[]
    for path in (ROOT/'results/investigation-r5-validation/runs/authorized-r5-8192-v1').rglob('attempt.json'):
        a=load(path)
        records.append({'artifact':binding(path),'started_at':a['started_at'],'finished_at':a['finished_at'],
                        'provider_status':(a.get('provider_metadata') or {}).get('status'),'HTTP_status':a['HTTP_status'],
                        'response_headers':a['response_headers']})
    records.sort(key=lambda x:x['started_at'])
    gates=[rate_feasibility(x['response_headers']) for x in records]
    if any(x['status'].startswith('STOP') for x in gates):
        create_json(OUT/'rate_limit_blocker.json',{'status':'STOP','records':records,'gates':gates,'executable':False})
        raise RuntimeError('Preserved token limit below r6 allowance: STOP')
    usable=[x for x in records if any(k.startswith('x-ratelimit-limit-') and 'token' in k for k in x['response_headers'])]
    latest=usable[-1] if usable else None
    rate={'status':rate_feasibility(latest['response_headers'] if latest else {})['status'],
          'model_maximum_output_capability':32768,'candidate_model_max_output_tokens':24576,
          'model_capability_source':binding(ROOT/'docs/investigation_model.capabilities.v1.md'),
          'latest_available_token_header_record':latest,'records':records,
          'project_specific_token_headers_present':any('project' in k and 'token' in k for x in records for k in x['response_headers']),
          'monthly_or_billing_limit_known':False,'current_remaining_balance_known':False,'live_execution_authorized':False,
          'freshness_note':'Most recent response is preserved even when it lacks token headers; prior successful headers establish historical feasibility only. No new limit query.',
          'four_distinct_concepts':['model maximum output capability','provider organization/project rate allowance; exact scope not identified by generic headers','monthly account/billing quota, not present in headers','actual usage meters billed, not configured cap'],
          'no_fixed_total_bill_predicted':True}
    create_json(OUT/'rate_limit_evidence.json',rate)
    model=copy.deepcopy(load(ROOT/'configs/investigation-r5/model.candidate.json'))
    model.pop('max_output_tokens');model['model_max_output_tokens']=24576
    model.update(version='model-r6-offline-output-only-candidate',parent=binding(ROOT/'configs/investigation-r5/model.candidate.json'),
                 authorization_scope='OFFLINE ONLY; live execution requires explicit author approval',output_cap_validation='INTENDED_FINAL_DEVELOPMENT_CANDIDATE_NOT_YET_VALIDATED')
    create_json(CONFIG/'model.candidate.json',model)
    old_budget=load(ROOT/'configs/investigation-r5/token_budget.candidate.json')
    budget={'version':'r6-explicit-input-output-budgets','evidence_input_token_safety_ceiling':16384,'model_max_output_tokens':24576,
            'prompt_plus_evidence_input_token_ceiling':old_budget['max_input_text_tokens'],
            'input_scope':'Evidence serialization only; separate prompt-plus-evidence ceiling excludes strict-schema/framing input; no trimming or reselection',
            'retrieval_unchanged':True,'overflow_action':old_budget['overflow_action'],'parent':binding(ROOT/'configs/investigation-r5/token_budget.candidate.json')}
    create_json(CONFIG/'token_budget.candidate.json',budget)
    transport={'version':'r6-offline-scheduling-candidate','live_execution_authorized':False,
        'inherited_transport_policy':binding(ROOT/'configs/investigation-r5/transport.candidate.json'),
        'max_inflight':1,'minimum_seconds_between_request_starts':60,'maximum_transport_attempts':3,
        'retry_after_is_minimum':True,'use_longer_reset_headers':True,'before_each_request':'Evaluate latest provider token/project limits, remaining/reset state, elapsed time, Retry-After and conservative request estimate; missing or insufficient state requires preflight confirmation',
        'retry_policy_changed':False,'no_batching':True,'failure_cap':'FIRST incomplete/max_output_tokens: preserve, no retry, stop new positions, fail capacity, author review; no automatic 32768',
        'monthly_quota_or_billing_error':'Account action, never solved by longer pacing',
        'missing_usage':'Unknown, never zero; charge using actual uncached input, cached input and output meters',
        'accounting_source':binding(ROOT/'scripts/report_investigation_api_usage.py')}
    create_json(CONFIG/'execution_policy.candidate.json',transport)
    inherited=['configs/investigation-r5/matrix.json','configs/investigation-r5/metrics.json','configs/investigation-r5/statistics.json',
        'configs/investigation-r5/matching.json','configs/investigation-r5/scenario_strata.custodian.json',
        'prompts/investigation-v1-r5/manifest.json','schemas/investigation_claim.v3.json',
        'src/investigation_r5/core.py','src/investigation_r5/runner.py','src/investigation_r5/metrics.py',
        'src/investigation_r5/statistics.py','src/investigation_dryrun/claims.py','src/investigation_dryrun/structured.py',
        'annotations/gold/pilot-v1/manifest.json','configs/investigation_events.v1.json']
    create_json(CONFIG/'scientific_bindings.json',{'scientific_change':'OUTPUT CAP ONLY','reused_unchanged':[binding(ROOT/p) for p in inherited],
        'complete_transitive_preservation':binding(OUT/'preservation.before.json'),
        'internal_to_provider_mapping':{'model_max_output_tokens':'Responses.max_output_tokens'},
        'gold_or_alias_or_guardrail_changes_required':False})
    parent=load(PARENT_PLAN);positions=[];diffs=[];estimates=[]
    for p in parent['positions']:
        request,b,r,diff=build_request(p)
        directory=OUT/'requests'/p['event_id']/p['cell_id'];directory.mkdir(parents=True,exist_ok=True)
        target=directory/f"rep-{p['repetition']}.json";create_json(target,request)
        actual=ROOT/'results/investigation-r5-validation/runs/authorized-r5-8192-v1'/p['event_id']/p['cell_id']/f"rep-{p['repetition']}"/'request.json'
        if actual.exists():
            old=copy.deepcopy(request);old['max_output_tokens']=8192
            if load(actual)!=old: raise ValueError('Actual r5 request differs from predeclared request')
        diff.update(position_id=p['position_id'],r5_reference_kind='ACTUALLY_SENT_R5_REQUEST' if actual.exists() else 'PREDECLARED_R5_REQUEST_RECONSTRUCTED_AND_HASH_VERIFIED',
                    r5_actual_request=binding(actual) if actual.exists() else None,r5_manifest=binding(PARENT_PLAN),request_artifact=binding(target))
        diffs.append(diff)
        row={key:p[key] for key in ('position_id','event_id','cell_id','view','citation_mode','repetition','purpose','bundle_sha256','receipt_sha256')}
        row.update(request_sha256=digest(request),request_artifact=binding(target),r5_position=p,model_max_output_tokens=24576,
                   historical_output_reused=False,status='PREDECLARED_NOT_EXECUTED')
        positions.append(row)
        estimated=count(request['instructions'])+count(request['input'])+count(dumps(request['text']['format']['schema']))
        estimates.append({'position_id':p['position_id'],'advisory_local_prompt_evidence_schema_tokens':estimated,
                          'evidence_input_tokens':count(request['input']),'provider_rate_charge_known':False})
    create_json(OUT/'request_equivalence.json',{'status':'PASS','positions':diffs,'verified':64,'only_substantive_diff':'max_output_tokens:8192->24576',
        'actually_sent_r5_comparisons':sum(d['r5_actual_request'] is not None for d in diffs),'predeclared_unsent_r5_comparisons':sum(d['r5_actual_request'] is None for d in diffs)})
    create_json(OUT/'input_rate_estimates.json',{'advisory_only':True,'exact_provider_estimation_not_claimed':True,'rows':estimates,
        'maximum_local_prompt_evidence_schema_tokens':max(x['advisory_local_prompt_evidence_schema_tokens'] for x in estimates),
        'schema_and_provider_framing_distinct_from_input_evidence_safety_ceiling':True})
    manifest={'version':'r6-clean-64-output-only-validation','status':'PREDECLARED_NOT_EXECUTED','model_calls_authorized':False,'protocol_frozen':False,
        'run_id':'r6-24576-clean-64-candidate','model_max_output_tokens':24576,'counts':parent['counts'],
        'generation_positions':64,'V1_EN_replay_positions':21,'positions':positions,'parent_manifest':binding(PARENT_PLAN),
        'historical_outputs_reused':0,'historical_B1_truncations_excluded':parent['historical_B1_truncations_excluded'],
        'why_full_64':'Author deliberately selects clean same-cap validation including all prior completions; capacity-configuration selection, not performance-driven rerunning; 47-position continuation rejected',
        'capacity_acceptance':'Zero incomplete/max_output_tokens; first occurrence stops new positions without retry or automatic cap change',
        'conformance_acceptance':'Existing strict parsing, visibility, view isolation, input budget and receipt/hash checks; exact stored eligible G1-EN bytes replayed as V1-EN with zero model calls; no factual-score-based cap selection',
        'non_cap_failures':'Retained under unchanged transport policy; no delivery/pending is inconclusive, not cap success; conformance failures reported separately'}
    create_json(OUT/'validation_manifest.json',manifest)
    create_json(OUT/'manifest_verification.json',validate_manifest(manifest))
    print(json.dumps({'status':'OFFLINE_PREPARED','positions':64,'cap':24576,'protected_files':len(protected),'rate_status':rate['status'],'model_calls':0},indent=2))

if __name__=='__main__': prepare()
