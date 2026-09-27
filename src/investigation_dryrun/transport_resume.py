"""Transport-only continuation of fully logged interrupted development cells.
The approved three-attempt total and original request bytes remain unchanged.
"""
import copy,hashlib,time,json
from .common import ROOT,load,dumps,digest,file_hash,create_json,utc,binding
from .custody import require_development,read_bundle
from .runner import (approved_configuration,OpenAITransport,extract_provider,delivery_validation,RetryableDelivery,TransportFailure)

def continue_started(directory,transport,sleep=time.sleep):
    manifest=load(directory/'started.json');event_id=manifest['event_id'];baseline=manifest['baseline'];repetition=manifest['repetition'];run_id=manifest['run_id']
    require_development(event_id)
    if (directory/'completed.json').exists():raise FileExistsError('Already completed')
    model,budget,controls=approved_configuration(transport)
    b=load(directory/'bundle.json');r=load(directory/'receipt.json');request=load(directory/'request.json');request_hash=digest(request)
    if digest(b)!=manifest['bundle_sha256'] or digest(r)!=manifest['receipt_sha256']:raise ValueError('Interrupted evidence changed')
    from .runner import build_request
    rebuilt,prompt=build_request(event_id,baseline,b,model,budget)
    if request!=rebuilt:raise ValueError('Interrupted request changed')
    manifest['attempts']=[]
    folders=sorted(directory.glob('attempt-*'),key=lambda p:int(p.name.split('-')[1]))
    for expected,folder in enumerate(folders,1):
        if folder.name!=f'attempt-{expected}' or not (folder/'attempt.json').exists():raise RuntimeError('Ambiguous in-flight delivery requires manual reconciliation')
        log=load(folder/'attempt.json')
        if log.get('HTTP_status')!=429 or not log.get('will_retry'):raise RuntimeError('Only logged retryable transport interruption can continue')
        if file_hash(folder/'response.raw')!=log['response_sha256']:raise ValueError('Interrupted response changed')
        manifest['attempts'].append(log)
    if len(manifest['attempts'])>=controls['max_attempts_per_repetition']:raise RuntimeError('Original retry budget exhausted')
    manifest.update(request_sha256=request_hash,prompt=prompt,structured_schema_sha256=digest(request['text']['format']['schema']))
    manifest['transport_continuation']={'continued_at':utc(),'retained_attempts':len(manifest['attempts']),'same_request':True,'total_attempt_limit':controls['max_attempts_per_repetition']}
    status='FAILED_NO_VALID_DELIVERY'
    for attempt in range(len(manifest['attempts'])+1,controls['max_attempts_per_repetition']+1):
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
                # Preserve usage/response IDs even when a completed response has
                # an unrecoverable experiment envelope and delivery is retried.
                try:metadata=json.loads(body)
                except (ValueError,UnicodeError):metadata=None
                if isinstance(metadata,dict):
                    log['provider_metadata']={k:metadata.get(k) for k in ('id','model','created_at','status','usage','incomplete_details','error','service_tier','temperature','max_output_tokens','system_fingerprint')}
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
