"""Proposed bounded transport policy, exercised solely with in-memory fixtures."""
import copy,errno,http.client,json,urllib.error,hashlib
from email.utils import parsedate_to_datetime
from investigation_dryrun.common import create_json,digest
from investigation_dryrun.runner import extract_provider,RetryableDelivery

RETRY_ERRNOS={errno.ECONNRESET,errno.ECONNABORTED,errno.ECONNREFUSED,errno.EPIPE,errno.ETIMEDOUT,errno.ENETUNREACH,errno.EHOSTUNREACH}

def retry_exception(exc):
    if isinstance(exc,urllib.error.HTTPError):return exc.code in (408,429) or 500<=exc.code<600
    if isinstance(exc,urllib.error.URLError):return isinstance(exc.reason,BaseException) and retry_exception(exc.reason)
    return isinstance(exc,(ConnectionError,TimeoutError,http.client.RemoteDisconnected,http.client.IncompleteRead)) or isinstance(exc,OSError) and exc.errno in RETRY_ERRNOS

def next_delay(headers,elapsed,wall_time=0):
    value=headers.get('retry-after');delay=0
    if value is not None:
        try:delay=max(0,float(value))
        except (ValueError,TypeError):
            try:delay=max(0,parsedate_to_datetime(value).timestamp()-wall_time)
            except (ValueError,TypeError,OverflowError):delay=0
    return max(0,60-elapsed,delay)

class FixtureTransport:
    """Finite prerecorded synthetic replies only; not an arbitrary network callback."""
    def __init__(self,replies):self.replies=list(replies);self.requests=[]
    def send(self,request):
        self.requests.append(copy.deepcopy(request));reply=self.replies.pop(0)
        if isinstance(reply,Exception):raise reply
        return reply


def exercise(request,fixture,directory,validate=lambda exp:[],clock=lambda:0,sleep=lambda _:None):
    if type(fixture) is not FixtureTransport:raise PermissionError('Only built-in synthetic transport fixtures allowed')
    directory.mkdir(parents=True,exist_ok=False);attempts=[];status='FAILED_NO_VALID_DELIVERY'
    for number in range(1,4):
        started=clock();headers={};retry=False;log={'kind':'OFFLINE_SYNTHETIC_TEST_NOT_RESEARCH','attempt':number,'request_sha256':digest(request),'HTTP_status':None,'usage':None}
        folder=directory/f'attempt-{number}';folder.mkdir()
        try:
            code,headers,body=fixture.send(request);(folder/'response.raw').write_bytes(body)
            log.update(HTTP_status=code,response_sha256=hashlib.sha256(body).hexdigest())
            if code in (408,429) or 500<=code<600:raise RetryableDelivery('HTTP_TRANSPORT')
            if not 200<=code<300:status='TERMINAL_HTTP_FAILURE'
            else:
                try:meta=json.loads(body)
                except (ValueError,UnicodeError):meta=None
                if isinstance(meta,dict):log['provider_metadata']={k:meta.get(k) for k in ('id','model','status','usage','incomplete_details')}
                provider,raw,exp,outcome=extract_provider(body);(folder/'output.raw').write_bytes(raw)
                log['usage']=provider.get('usage');log['outcome']=outcome
                if provider.get('model')!=request['model']:status='MODEL_IDENTIFIER_MISMATCH'
                elif exp is not None:
                    log['validation_errors']=validate(exp);status='DELIVERED_SCHEMA_OR_VISIBILITY_INVALID' if log['validation_errors'] else 'DELIVERED'
                else:
                    status=outcome.upper()
                    log['capacity_stop_required']=(provider.get('incomplete_details') or {}).get('reason')=='max_output_tokens'
        except RetryableDelivery as e:retry=True;log['reason']=str(e)
        except Exception as e:
            retry=retry_exception(e);log['reason']=type(e).__name__;log['delivery_status']='UNKNOWN' if retry else 'LOCAL_OR_UNCLASSIFIED_FAILURE'
            status='FAILED_NO_VALID_DELIVERY' if retry else 'RUNNER_FAILURE'
        log['will_retry']=retry and number<3;create_json(folder/'attempt.json',log);attempts.append(log)
        if not log['will_retry']:break
        sleep(next_delay(headers,clock()-started))
    result={'kind':'OFFLINE_SYNTHETIC_TEST_NOT_RESEARCH','status':status,'attempts':attempts,'model_calls':0};create_json(directory/'completed.json',result);return result
