"""Development-only B1/B2/B3 generation and exact stored-output B4 replay.

Live calls are disabled until the model/budget are explicitly approved. The same
code is exercised with injected transport fixtures; no answer-dependent retries.
"""
import copy
import hashlib
import json
import re
import time
import urllib.request
import urllib.error
import socket
from pathlib import Path
from .common import ROOT, load, dumps, digest, file_hash, create_json, utc, binding
from .custody import require_development, read_bundle
from .tokens import count
from .claims import verify_claim
from investigation.schema_v2 import validate

CONFIG = ROOT/'configs/investigation-dev-v1'
RUNS = ROOT/'results/investigation-development-v1/runs'

class RetryableDelivery(Exception):
    pass
class TransportFailure(Exception):
    pass

class OpenAITransport:
    fixture = False
    def __call__(self,request,client_id,timeout):
        # Credentials are read only on an explicitly enabled live request, never logged.
        import os
        key=os.environ.get('OPENAI_API_KEY')
        if not key:raise RuntimeError('OPENAI_API_KEY is not configured')
        req=urllib.request.Request('https://api.openai.com/v1/responses',data=dumps(request).encode(),method='POST',headers={'Authorization':'Bearer '+key,'Content-Type':'application/json','X-Client-Request-Id':client_id})
        try:
            with urllib.request.urlopen(req,timeout=timeout) as response:
                return response.status, {k.lower():v for k,v in response.headers.items() if k.lower() in {'x-request-id','date','retry-after'}}, response.read()
        except urllib.error.HTTPError as e:
            return e.code,{k.lower():v for k,v in e.headers.items() if k.lower() in {'x-request-id','date','retry-after'}},e.read()
        except (urllib.error.URLError,TimeoutError,socket.timeout) as e:
            raise TransportFailure(type(e).__name__) from e

def approved_configuration(transport):
    model=load(CONFIG/'model.candidate.json');budget=load(CONFIG/'token_budget.candidate.json');generation=load(CONFIG/'generation.json')
    if not getattr(transport,'fixture',False):
        if not model['live_api_enabled'] or model['final_model_approval']!='APPROVED' or budget['status']!='APPROVED':
            raise PermissionError('Final model and token-budget approval required before live API calls')
    if model['temperature']!=0 or model['exact_callable_model']!='gpt-4.1-2025-04-14' or generation['repetitions']!=3:raise ValueError('Generation configuration drift')
    return model,budget,generation

def parse_experiment(raw):
    try:
        # No code-fence repair, continuation, JSON regeneration or selection of an answer.
        value=json.loads(raw,parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
    except (ValueError,UnicodeError) as e:raise RetryableDelivery('no_valid_JSON_delivery') from e
    if not isinstance(value,dict) or not isinstance(value.get('claims'),list) or not isinstance(value.get('questions'),list):
        raise RetryableDelivery('no_recoverable_experiment_envelope')
    return value

def extract_provider(body):
    try:obj=json.loads(body)
    except (ValueError,UnicodeError) as e:raise RetryableDelivery('malformed_provider_envelope') from e
    if not isinstance(obj,dict) or not isinstance(obj.get('status'),str):raise RetryableDelivery('malformed_provider_envelope')
    # Refusal/incomplete delivery is an outcome, not a retry to obtain a better answer.
    output=obj.get('output',[])
    if not isinstance(output,list):raise RetryableDelivery('malformed_provider_output')
    pieces=[];refused=False
    for item in output:
        if not isinstance(item,dict):raise RetryableDelivery('malformed_provider_item')
        if item.get('type')=='message':
            if not isinstance(item.get('content'),list):raise RetryableDelivery('malformed_provider_message')
            for part in item['content']:
                if not isinstance(part,dict):raise RetryableDelivery('malformed_provider_content')
                if part.get('type')=='refusal':refused=True
                if part.get('type')=='output_text':
                    if not isinstance(part.get('text'),str):raise RetryableDelivery('malformed_provider_text')
                    pieces.append(part['text'])
    raw=''.join(pieces).encode()
    if refused:return obj,raw,None,'provider_refusal'
    if obj['status']!='completed':return obj,raw,None,'provider_'+obj['status']
    return obj,raw,parse_experiment(raw),'delivered'

def delivery_validation(value,event_id,view,citation_mode):
    errors=[]
    try:validate('investigation_claim.v2.json',value)
    except (ValueError,TypeError,KeyError) as e:errors.append('schema:'+str(e))
    if value.get('event_id')!=event_id or value.get('evidence_view')!=view or value.get('citation_mode')!=citation_mode:errors.append('experiment_context_mismatch')
    if value.get('schema_version')!='investigation-claim-v2':errors.append('schema_version_mismatch')
    claims=value['claims'];qs=value['questions']
    if len(claims)>64:errors.append('claim_limit_exceeded')
    ids=[c.get('claim_id') for c in claims if isinstance(c,dict)]
    valid_ids={x for x in ids if isinstance(x,str)}
    if len(ids)!=len(claims) or len(valid_ids)!=len(ids):errors.append('invalid_or_duplicate_claim_ids')
    qids=[q.get('question_id') for q in qs if isinstance(q,dict)]
    if len(qids)!=7 or {x for x in qids if isinstance(x,str)}!={f'Q{i}' for i in range(1,8)}:errors.append('invalid_question_slots')
    for q in qs:
        if not isinstance(q,dict) or not isinstance(q.get('claim_ids'),list) or not all(isinstance(x,str) and x in valid_ids for x in q['claim_ids']):errors.append('invalid_question_claim_links')
    return errors

def build_request(event_id,baseline,bundle,model,budget):
    require_development(event_id)
    if baseline not in ('B1','B2','B3'):raise ValueError('B4 has no generation request')
    view='N' if baseline=='B1' else 'EN'
    if bundle['scope']['event_id']!=event_id or bundle['scope']['view']!=view:raise ValueError('Wrong event/view')
    manifest=load(ROOT/'prompts/investigation-v1/manifest.v1.json');ref=manifest['prompts'][baseline]
    path=ROOT/ref['path']
    if file_hash(path)!=ref['sha256']:raise ValueError('Prompt hash drift')
    prompt=path.read_text();evidence=dumps(bundle)
    if count(evidence)>budget['fixed_evidence_tokens']:raise ValueError('evidence_token_budget_exceeded_no_reselection')
    if count(prompt)+count(evidence)>budget['max_input_text_tokens']:raise ValueError('input_text_budget_exceeded')
    if count(prompt)+count(evidence)+model['max_output_tokens']>model['context_window']:raise ValueError('context_budget_exceeded')
    request={'model':model['exact_callable_model'],'instructions':prompt,'input':evidence,'temperature':0,'max_output_tokens':model['max_output_tokens'],'store':False,'truncation':'disabled','tools':[],'text':{'format':{'type':'json_object'}}}
    return request,ref

def generate(event_id,baseline,repetition,run_id,transport=None,fixture_root=None,sleep=time.sleep):
    require_development(event_id)
    if repetition not in (1,2,3) or not re.fullmatch('[a-zA-Z0-9_-]{1,80}',run_id):raise ValueError('Invalid run identity')
    transport=transport or OpenAITransport()
    model,budget,controls=approved_configuration(transport)
    if fixture_root is not None and not getattr(transport,'fixture',False):raise PermissionError('Custom paths only for test fixtures')
    root=Path(fixture_root) if fixture_root else RUNS
    directory=root/run_id/event_id/baseline/f'rep-{repetition}'
    directory.mkdir(parents=True,exist_ok=False)
    kind='TEST_FIXTURE_NOT_RESEARCH' if getattr(transport,'fixture',False) else 'DEVELOPMENT_EXPERIMENT'
    b,r=read_bundle(event_id,'N' if baseline=='B1' else 'EN',directory/'access.jsonl')
    manifest={'version':'investigation-development-run-v1','kind':kind,'event_id':event_id,'baseline':baseline,'repetition':repetition,'run_id':run_id,'started_at':utc(),'status':'STARTED','bundle_sha256':digest(b),'receipt_sha256':digest(r),'configuration':{f:binding(CONFIG/f) for f in ('model.candidate.json','token_budget.candidate.json','generation.json')},'attempts':[]}
    manifest['implementation']=[binding(p) for p in sorted((ROOT/'src/investigation_dev').glob('*.py'))]+[binding(ROOT/'schemas/investigation_claim.v2.json'),binding(ROOT/'prompts/investigation-v1/canonical_text.v1.json')]
    create_json(directory/'started.json',manifest)
    create_json(directory/'bundle.json',b);create_json(directory/'receipt.json',r)
    try:request,prompt=build_request(event_id,baseline,b,model,budget)
    except ValueError as e:
        manifest.update(status='PREFLIGHT_FAILURE',reason=str(e),finished_at=utc());create_json(directory/'completed.json',manifest);return manifest
    request_hash=digest(request);manifest.update(request_sha256=request_hash,prompt=prompt)
    create_json(directory/'request.json',request)
    status='FAILED_NO_VALID_DELIVERY'
    for attempt in range(1,controls['max_attempts_per_repetition']+1):
        folder=directory/f'attempt-{attempt}';folder.mkdir();started=utc();retry=False
        client_id=hashlib.sha256(f'{run_id}|{event_id}|{baseline}|{repetition}|{attempt}'.encode()).hexdigest()
        log={'attempt':attempt,'started_at':started,'client_request_id':client_id,'request_sha256':request_hash}
        try:
            code,headers,body=transport(copy.deepcopy(request),client_id,controls['timeout_seconds'])
            (folder/'response.raw').write_bytes(body)
            log.update(HTTP_status=code,response_headers=headers,response_sha256=hashlib.sha256(body).hexdigest())
            if code in (408,429) or 500<=code<600:raise RetryableDelivery('retryable_HTTP_transport_status')
            if not 200<=code<300:
                status='TERMINAL_HTTP_FAILURE';log['reason']='nonretryable_HTTP_status'
            else:
                provider,raw,experiment,outcome=extract_provider(body)
                log['provider_metadata']={k:provider.get(k) for k in ('id','model','created_at','status','usage','incomplete_details','error','service_tier','temperature','max_output_tokens','system_fingerprint')}
                (folder/'output.raw').write_bytes(raw)
                if provider.get('model')!=model['exact_callable_model']:
                    status='MODEL_IDENTIFIER_MISMATCH';log['reason']='provider_returned_different_model'
                else:
                    (directory/'output.raw.json').write_bytes(raw)
                    manifest['output_sha256']=hashlib.sha256(raw).hexdigest()
                    if experiment is not None:
                        errors=delivery_validation(experiment,event_id,b['scope']['view'],'required' if baseline=='B3' else 'optional_baseline')
                        status='DELIVERED_SCHEMA_INVALID' if errors else 'DELIVERED'
                        log['experiment_validation_errors']=errors
                    else:status=outcome.upper()
        except (RetryableDelivery,TransportFailure,TimeoutError) as e:
            retry=True;log['reason']=str(e);status='FAILED_NO_VALID_DELIVERY'
        except Exception as e:
            status='RUNNER_CONFIGURATION_OR_IMPLEMENTATION_FAILURE';log['reason']=type(e).__name__;retry=False
        finally:
            log['finished_at']=utc();log['will_retry']=retry and attempt<controls['max_attempts_per_repetition']
            create_json(folder/'attempt.json',log);manifest['attempts'].append(log)
        if not retry:break
        if attempt<controls['max_attempts_per_repetition']:sleep(controls['backoff_seconds'][attempt-1])
    manifest.update(status=status,finished_at=utc());create_json(directory/'completed.json',manifest)
    return manifest

def replay_bytes(event_id,raw,b3_manifest,bundle,receipt):
    require_development(event_id)
    if b3_manifest['event_id']!=event_id or b3_manifest['baseline']!='B3' or b3_manifest['repetition'] not in (1,2,3):raise ValueError('Wrong B3 provenance')
    if hashlib.sha256(raw).hexdigest()!=b3_manifest['output_sha256']:raise ValueError('B3 raw output changed')
    if digest(bundle)!=b3_manifest['bundle_sha256'] or digest(receipt)!=b3_manifest['receipt_sha256'] or digest(bundle)!=receipt['retrieved_bundle_sha256']:raise ValueError('Replay evidence mismatch')
    if bundle['scope']['event_id']!=event_id or bundle['scope']['view']!='EN':raise ValueError('Replay event/view mismatch')
    exp=parse_experiment(raw)
    errors=delivery_validation(exp,event_id,'EN','required')
    context_failure=any(e in errors for e in ('experiment_context_mismatch','invalid_or_duplicate_claim_ids','invalid_question_slots','invalid_question_claim_links','schema_version_mismatch','claim_limit_exceeded'))
    dispositions=[]
    for c in exp['claims']:
        if context_failure or not isinstance(c,dict):
            dispositions.append({'claim_id':c.get('claim_id') if isinstance(c,dict) else None,'disposition':'INSUFFICIENT','reason':'invalid_experiment_context_or_links','published_claim':None})
        else:dispositions.append(verify_claim(c,bundle))
    published=[d['published_claim'] for d in dispositions if d['published_claim'] is not None]
    ids={c['claim_id'] for c in published};questions=[];question_actions=[]
    for i in range(1,8):
        old=next((q for q in exp['questions'] if isinstance(q,dict) and q.get('question_id')==f'Q{i}'),{})
        raw_links=old.get('claim_ids',[])
        retained=[x for x in raw_links if isinstance(x,str) and x in ids] if isinstance(raw_links,list) else []
        # Retain the original response only when all its links survive. A partial
        # publication is explicitly qualified in the sidecar, not inferred answerability.
        unchanged=bool(retained) and retained==old.get('claim_ids',[])
        response=old.get('response','insufficient') if unchanged else 'insufficient'
        questions.append({'question_id':f'Q{i}','claim_ids':retained,'response':response})
        question_actions.append({'question_id':f'Q{i}','action':'retain_original_response' if unchanged else 'partial_or_withheld_replayed_answer','reason':'Only checked B3 content is retained; missing checked claims do not prove full-view evidence absence.','full_view_diagnosis':'not_inferred_by_verifier'})
    return {'version':'B4-replay-development-v1','event_id':event_id,'baseline':'B4','repetition':b3_manifest['repetition'], 'B3_run_id':b3_manifest['run_id'],'B3_input_sha256':hashlib.sha256(raw).hexdigest(),'bundle_sha256':digest(bundle),'receipt_sha256':digest(receipt),'verifier_implementation':[binding(ROOT/'src/investigation_dev/claims.py'),binding(ROOT/'src/investigation_dev/runner.py'),binding(ROOT/'schemas/investigation_claim.v2.json'),binding(ROOT/'prompts/investigation-v1/canonical_text.v1.json')],'llm_calls':0,'new_generation_prompt':None,'raw_B3_validation_errors':errors,'question_actions':question_actions,'dispositions':dispositions,'published_report':{'schema_version':'investigation-claim-v2','event_id':event_id,'evidence_view':'EN','citation_mode':'required','claims':published,'questions':questions},'question_action_limit':'Question links are retained; independent human scoring decides substantive minimum and correct insufficiency reason. No answerability inferred from claim count.'}

def replay(event_id,repetition,run_id):
    require_development(event_id)
    if repetition not in (1,2,3) or not re.fullmatch('[a-zA-Z0-9_-]{1,80}',run_id):raise ValueError('Invalid run identity')
    base=RUNS/run_id/event_id/'B3'/f'rep-{repetition}'
    for name in ('completed.json','bundle.json','receipt.json','output.raw.json'):
        p=base/name
        if p.resolve()!=p.absolute():raise PermissionError('Replay symlink forbidden')
    m=load(base/'completed.json')
    output=replay_bytes(event_id,(base/'output.raw.json').read_bytes(),m,load(base/'bundle.json'),load(base/'receipt.json'))
    target=RUNS/run_id/event_id/'B4'/f'rep-{repetition}'/'replay.json'
    create_json(target,output);return output

def plan():
    from .custody import development_ids
    return [{'event_id':e,'baseline':b,'view':'N' if b=='B1' else 'EN','repetition':r,
             'action':'generation' if b in ('B1','B2','B3') else 'replay_B3' if b=='B4' else 'reference_existing_deterministic_B0'}
            for e in development_ids() for b in ('B0','B1','B2','B3','B4') for r in (1,2,3)]
