"""Authorized r6 serial execution; all scientific request artifacts remain immutable."""
import copy,fcntl,hashlib,json,re,time,urllib.request,urllib.error
from pathlib import Path
from investigation_dryrun.common import ROOT,load,dumps,digest,file_hash,create_json,binding,utc
from investigation_dryrun.runner import extract_provider,RetryableDelivery,delivery_validation
from investigation_r5.core import read_bundle,cell_spec,require_development
from investigation_r5.runner import validate_delivery,replay_bytes
from investigation_r6.candidate import build_request as r6_request
from investigation_r6.policy import rate_feasibility,scheduling_gate,capacity_stop
from investigation_dryrun.tokens import count
from investigation_r5.transport import retry_exception,next_delay

OUT=ROOT/'results/investigation-r6-validation'
RUN_ID='authorized-r6-24576-v1'

class CaptureFailure(Exception):
    def __init__(self,cause,code=None,headers=None,partial=None):self.cause=cause;self.code=code;self.headers=headers or {};self.partial=partial

class OpenAITransport:
    def __init__(self,key):self._key=key
    def send(self,request,client_id):
        req=urllib.request.Request('https://api.openai.com/v1/responses',data=dumps(request).encode(),method='POST',headers={'Authorization':'Bearer '+self._key,'Content-Type':'application/json','X-Client-Request-Id':client_id})
        code=None;headers={}
        def public_headers(h):return {k.lower():v for k,v in h.items() if k.lower().startswith('x-ratelimit-') or k.lower() in ('retry-after','x-request-id','date','openai-processing-ms','openai-version')}
        try:
            try:response=urllib.request.urlopen(req,timeout=120)
            except urllib.error.HTTPError as e:response=e
            with response:
                code=response.status;headers=public_headers(response.headers);body=response.read()
                return code,headers,body
        except Exception as e:raise CaptureFailure(e,code,headers,getattr(e,'partial',None)) from e

def reset_seconds(value):
    if value is None:return 0
    try:return max(0,float(value))
    except (TypeError,ValueError):pass
    parts=re.findall(r'(\d+(?:\.\d+)?)(ms|s|m|h|d)',str(value))
    if ''.join(n+u for n,u in parts)!=str(value):raise ValueError('Unparsed provider reset header')
    return sum(float(n)*{'ms':.001,'s':1,'m':60,'h':3600,'d':86400}[u] for n,u in parts)

class Scheduler:
    def __init__(self,clock=time.monotonic,sleep=time.sleep,wall=time.time):self.clock=clock;self.sleep=sleep;self.wall=wall;self.last_start=None;self.not_before=0
    def start(self):
        deadline=max(self.not_before,(self.last_start+60) if self.last_start is not None else 0)
        while deadline>self.clock():self.sleep(min(30,deadline-self.clock()))
        self.last_start=self.clock();return self.last_start
    def observe(self,headers):
        now=self.clock();elapsed=now-self.last_start if self.last_start is not None else 60
        delay=next_delay(headers,elapsed,self.wall())
        resets=[reset_seconds(v) for k,v in headers.items() if k.startswith('x-ratelimit-reset-')]
        self.not_before=max(self.not_before,now+max([delay,*resets]))
        return {'minimum_wait_from_response_seconds':max(0,self.not_before-now),'next_start_monotonic':self.not_before,'reset_policy':'conservative full reset when later than base spacing/Retry-After'}


def classify_http_failure(code,obj):
    error=obj.get('error') if isinstance(obj,dict) else None
    if not isinstance(error,dict):return 'TEMPORARY_TRANSPORT' if code!=429 else 'TEMPORARY_RATE_EXHAUSTION'
    error_code=str(error.get('code',''));message=str(error.get('message',''))
    if error_code in ('insufficient_quota','billing_hard_limit_reached'):return 'ACCOUNT_QUOTA_OR_BILLING'
    explicit=(re.search(r'request (?:is )?too large',message,re.I) and re.search(r'token|TPM',message,re.I))
    explicit=explicit or error_code in ('request_too_large_for_rate_limit','tokens_per_request_exceed_rate_limit')
    limit=re.search(r'\bLimit\s*:?\s*([\d,]+)',message,re.I);requested=re.search(r'\bRequested\s*:?\s*([\d,]+)',message,re.I)
    if limit and requested and re.search(r'token|TPM',message,re.I):
        explicit=explicit or int(requested.group(1).replace(',',''))>int(limit.group(1).replace(',',''))
    if code==429 and explicit:return 'SINGLE_REQUEST_EXCEEDS_RATE_LIMIT'
    return 'TEMPORARY_RATE_EXHAUSTION' if code==429 else 'TEMPORARY_TRANSPORT'

class RateAwareScheduler(Scheduler):
    def __init__(self,*args,initial_limits=None,**kwargs):
        super().__init__(*args,**kwargs)
        self.limits=dict(initial_limits or {});self.latest_headers={};self.response_at=None
        self.estimated_request_tokens=24576;self.last_gate=None;self.blocker=None
    def start(self):
        now=self.clock()
        headers={**self.limits,**self.latest_headers}
        self.last_gate=scheduling_gate(headers,now-self.last_start if self.last_start is not None else 60,
            now-self.response_at if self.response_at is not None else 0,
            estimated_request_tokens=self.estimated_request_tokens,response_wall_time=self.wall()-(now-self.response_at) if self.response_at is not None else self.wall())
        if self.last_gate['wait_seconds'] is None:raise RuntimeError('RATE_FEASIBILITY_PREFLIGHT_BLOCKER')
        self.not_before=max(self.not_before,now+self.last_gate['wait_seconds'])
        return super().start()
    def observe(self,headers):
        self.latest_headers=dict(headers);self.response_at=self.clock()
        self.limits.update({k:v for k,v in headers.items() if k.startswith('x-ratelimit-limit-')})
        gate=rate_feasibility(self.limits,estimated_request_tokens=self.estimated_request_tokens)
        if gate['status'].startswith('STOP'):self.blocker='PROVIDER_TOKEN_LIMIT_BELOW_REQUEST_ALLOWANCE'
        elif gate['status']=='REQUIRES_PREFLIGHT_CONFIRMATION':self.blocker='RATE_LIMIT_CONFIRMATION_REQUIRED'
        result=super().observe(headers);result['rate_limit_gate']=gate
        return result


def process_position(p,directory,transport,scheduler,check_locked):
    require_development(p['event_id'])
    q,b,r,diff=r6_request(p['r5_position'])
    assert load(ROOT/p['request_artifact']['path'])==q and file_hash(ROOT/p['request_artifact']['path'])==p['request_artifact']['sha256'],'Stored r6 request changed'
    assert digest(q)==p['request_sha256'] and digest(b)==p['bundle_sha256'] and digest(r)==p['receipt_sha256'],'Manifest request/input mismatch'
    estimate=count(q['instructions'])+count(q['input'])+count(dumps(q['text']['format']['schema']))
    if estimate>30000:raise ValueError('Local request estimate exceeds preserved allowance')
    scheduler.estimated_request_tokens=estimate
    directory.mkdir(parents=True,exist_ok=False)
    m={**p,'run_id':RUN_ID,'status':'STARTED','started_at':utc(),'attempts':[],'request_diff_valid':True,'actual_evidence_tokens':count(q['input']),'schema_valid':False,'strict_schema_valid':False,'schema_validation_performed':False,'reference_visibility_valid':False}
    create_json(directory/'started.json',m);create_json(directory/'request.json',q);create_json(directory/'bundle.json',b);create_json(directory/'receipt.json',r)
    create_json(directory/'request_diff.json',diff)
    fatal=None;cap=False
    for number in range(1,4):
        check_locked();scheduler.start();check_locked()
        folder=directory/f'attempt-{number}';folder.mkdir()
        log={'attempt':number,'started_at':utc(),'start_monotonic':scheduler.last_start,'request_sha256':digest(q),'client_request_id':hashlib.sha256(f'{RUN_ID}|{p["position_id"]}|{number}'.encode()).hexdigest(),'HTTP_status':None,'usage':None,'delivery_status':'UNKNOWN','local_request_estimate':estimate,'rate_pre_request_gate':scheduler.last_gate}
        create_json(folder/'started.json',log);retry=False;headers={};body=None;code=None
        try:
            try:code,headers,body=transport.send(copy.deepcopy(q),log['client_request_id'])
            except CaptureFailure as failure:
                code=failure.code;headers=failure.headers;body=failure.partial
                raise failure.cause
            log['HTTP_status']=code;log['delivery_status']='HTTP_RESPONSE_RECEIVED';(folder/'response.raw').write_bytes(body);log['response_sha256']=file_hash(folder/'response.raw')
            try:obj=json.loads(body)
            except (ValueError,UnicodeError):obj=None
            if isinstance(obj,dict):
                md={k:obj.get(k) for k in ('id','model','created_at','status','usage','incomplete_details','error','service_tier','temperature','max_output_tokens','system_fingerprint')};log['provider_metadata']=md;log['usage']=md['usage']
                # Author's hard cap stop has priority over all other parsing/model checks.
                cap=capacity_stop(obj)
            if code in (408,429) or 500<=code<600:
                kind=classify_http_failure(code,obj);log['rate_failure_class']=kind
                if kind=='SINGLE_REQUEST_EXCEEDS_RATE_LIMIT':
                    m['status']='RATE_FEASIBILITY_BLOCKER';fatal='SINGLE_REQUEST_EXCEEDS_RATE_LIMIT'
                elif kind=='ACCOUNT_QUOTA_OR_BILLING':
                    m['status']='TERMINAL_QUOTA_FAILURE';fatal='ACCOUNT_ACTION_REQUIRED'
                else:raise RetryableDelivery('HTTP_TRANSPORT_'+str(code))
            elif not 200<=code<300:
                m['status']='TERMINAL_HTTP_FAILURE'
                if code in (400,401,403,404):fatal='REQUEST_OR_ACCOUNT_CONFIGURATION_REVIEW_REQUIRED'
            else:
                provider,raw,exp,outcome=extract_provider(body)
                (directory/'output.raw.json').write_bytes(raw);(folder/'output.raw').write_bytes(raw);m['output_sha256']=file_hash(directory/'output.raw.json')
                if cap:m['status']='PROVIDER_INCOMPLETE';m['termination_reason']='max_output_tokens'
                elif provider.get('model')!=q['model']:m['status']='MODEL_IDENTIFIER_MISMATCH';fatal='MODEL_IDENTIFIER_MISMATCH'
                elif provider.get('max_output_tokens') not in (None,24576) or provider.get('temperature') not in (None,0):m['status']='PROVIDER_CONFIGURATION_MISMATCH';fatal='PROVIDER_CONFIGURATION_MISMATCH'
                elif exp is None:
                    m['status']=outcome.upper();m['termination_reason']=(provider.get('incomplete_details') or {}).get('reason')
                else:
                    schema_errors=delivery_validation(exp,p['event_id'],p['view'],p['citation_mode']);errors=validate_delivery(exp,p['event_id'],p['cell_id'],b)
                    m['schema_validation_performed']=True;m['strict_schema_valid']=not any(e.startswith('schema:') for e in schema_errors)
                    m['schema_valid']=not schema_errors;m['reference_visibility_valid']=not any(e.startswith(('invisible_reference:','invisible_entity:')) for e in errors)
                    m['schema_and_visibility_valid']=not errors;m['validation_errors']=errors;m['status']='DELIVERED_SCHEMA_OR_VISIBILITY_INVALID' if errors else 'DELIVERED'
                    log['delivery_status']='RECOVERABLE_EXPERIMENT_DELIVERED'
        except Exception as e:
            if body is not None and not (folder/'response.raw').exists():(folder/'response.raw').write_bytes(body);log['response_sha256']=file_hash(folder/'response.raw')
            log['HTTP_status']=code;log['reason']=str(e) if isinstance(e,RetryableDelivery) else type(e).__name__
            if cap:m['status']='PROVIDER_INCOMPLETE';m['termination_reason']='max_output_tokens'
            elif isinstance(e,RetryableDelivery) or retry_exception(e):retry=True;m['status']='FAILED_NO_VALID_DELIVERY'
            else:m['status']='IMPLEMENTATION_FAILURE';fatal=type(e).__name__
        finally:
            log['response_headers']=headers
            try:
                log['pacing']=scheduler.observe(headers)
                if scheduler.blocker:fatal=scheduler.blocker
            except Exception as e:fatal='RATE_HEADER_PARSE_FAILURE';log['pacing_error']=type(e).__name__
            log['finished_at']=utc();log['will_retry']=retry and number<3 and not cap and not fatal
            create_json(folder/'attempt.json',log);m['attempts'].append(log)
        if cap or fatal or not log['will_retry']:break
    m.update(finished_at=utc(),capacity_hard_stop=cap,fatal_stop=fatal)
    create_json(directory/'completed.json',m)
    if p['cell_id']=='G1-EN':
        if m['status'] in ('DELIVERED','DELIVERED_SCHEMA_OR_VISIBILITY_INVALID'):
            raw=(directory/'output.raw.json').read_bytes();v=replay_bytes(p['event_id'],raw,m,b,r);v['status']='REPLAYED';assert v['source_output_sha256']==m['output_sha256']
        else:v={'status':'REPLAY_UNAVAILABLE','source_cell_id':'G1-EN','source_position_id':p['position_id'],'reason':m['status'],'source_output_sha256':m.get('output_sha256'),'llm_calls':0}
        create_json(directory/'V1-EN.replay.json',v)
    return m


def run(key_file):
    gate=load(OUT/'preflight.json');assert gate['status']=='PASS'
    def check_locked():
        for ref in gate['protected_files']:assert file_hash(ROOT/ref['path'])==ref['sha256'],ref['path']
    check_locked()
    lock=(OUT/'execution.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    root=OUT/'runs'/RUN_ID
    if root.exists():raise RuntimeError('Existing run directory: stop for checkpoint audit, never restart automatically')
    root.mkdir(parents=True)
    key=Path(key_file).read_text().strip()
    if not re.fullmatch(r'sk-[A-Za-z0-9_\-]+',key):raise ValueError('Credential file format unsupported; value not displayed')
    transport=OpenAITransport(key);scheduler=RateAwareScheduler(initial_limits=gate['initial_rate_limits']);plan=load(ROOT/'results/investigation-r6/validation_manifest.json');done=[];stop=None
    create_json(OUT/'execution.started.json',{'run_id':RUN_ID,'started_at':utc(),'preflight':binding(OUT/'preflight.json'),'position_order':[p['position_id'] for p in plan['positions']],'max_inflight':1})
    for p in plan['positions']:
        directory=root/p['event_id']/p['cell_id']/f"rep-{p['repetition']}"
        print(json.dumps({'event':'START_POSITION','position':p['position_id'],'finished_positions':len(done)}),flush=True)
        try:m=process_position(p,directory,transport,scheduler,check_locked)
        except Exception as e:
            stop='TRUSTWORTHY_CONTINUATION_BLOCKED_'+type(e).__name__;create_json(OUT/'execution.blocker.json',{'stop':stop,'position_id':p['position_id'],'at':utc(),'no_automatic_resume':True});break
        done.append(m['position_id']);print(json.dumps({'event':'POSITION_FINISHED','position':p['position_id'],'status':m['status'],'attempts':len(m['attempts']),'finished_positions':len(done),'capacity_hard_stop':m['capacity_hard_stop']}),flush=True)
        if m['capacity_hard_stop']:stop='FAILED_24576_OUTPUT_CAP_STOP_AUTHOR_REVIEW';break
        if m['fatal_stop']:stop='STOP_'+m['fatal_stop'];break
    state={'run_id':RUN_ID,'status':stop or 'ALL_64_POSITIONS_FINISHED','finished_positions':done,'not_scheduled':[p['position_id'] for p in plan['positions'] if p['position_id'] not in done],'finished_at':utc(),'automatic_freeze':False}
    create_json(OUT/'execution.finished.json',state);print(json.dumps({'event':'RUN_FINISHED','status':state['status'],'finished':len(done),'not_scheduled':len(state['not_scheduled'])}),flush=True)
    return state
