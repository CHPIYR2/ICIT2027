"""Pure scheduling, capacity and usage accounting gates; no network transport."""
from decimal import Decimal
from investigation_r5.transport import next_delay, retry_exception
from investigation_r5_live.adapter import reset_seconds
from investigation_r5.acceptance import assess as r5_assess

def rate_feasibility(headers, cap=24576, estimated_request_tokens=None):
    headers = {k.lower(): v for k, v in headers.items()}
    limits = {}
    for key, value in headers.items():
        if key.startswith('x-ratelimit-limit-') and 'token' in key:
            try: limit = int(value)
            except (ValueError, TypeError):
                return {'status': 'REQUIRES_PREFLIGHT_CONFIRMATION', 'reason': 'unparseable_token_limit', 'live_authorized': False}
            if limit < 0: return {'status': 'REQUIRES_PREFLIGHT_CONFIRMATION', 'reason': 'invalid_token_limit', 'live_authorized': False}
            limits[key] = limit
    needed = max(cap, estimated_request_tokens or 0)
    if any(v < needed for v in limits.values()):
        return {'status': 'STOP_TOKEN_LIMIT_BELOW_REQUIRED_ALLOWANCE', 'limits': limits, 'required_allowance': needed, 'live_authorized': False}
    return {'status': 'PRESERVED_LIMIT_SUPPORTS_CANDIDATE_PENDING_LIVE_PREFLIGHT' if limits else 'REQUIRES_PREFLIGHT_CONFIRMATION',
            'limits': limits, 'required_allowance': needed, 'live_authorized': False,
            'limitation': 'Historical header is not current balance or proof of request acceptance; provider estimate and project/account state need execution preflight'}

def scheduling_gate(headers, elapsed_since_start, elapsed_since_response, cap=24576,
                    estimated_request_tokens=None, response_wall_time=0):
    """Evaluate before EVERY future request; caller supplies latest response state."""
    if min(elapsed_since_start, elapsed_since_response) < 0: raise ValueError('Negative elapsed time')
    headers = {k.lower(): v for k, v in headers.items()}
    gate = rate_feasibility(headers, cap, estimated_request_tokens)
    if gate['status'].startswith('STOP') or gate['status'] == 'REQUIRES_PREFLIGHT_CONFIRMATION':
        return {'status': gate['status'], 'wait_seconds': None, 'rate_gate': gate}
    retry_wait = max(0, next_delay(headers, 60, response_wall_time) - elapsed_since_response)
    reset_waits = [max(0, reset_seconds(v)-elapsed_since_response) for k,v in headers.items() if k.startswith('x-ratelimit-reset-')]
    needed = max(cap, estimated_request_tokens or 0)
    for key,value in headers.items():
        if key.startswith('x-ratelimit-remaining-'):
            suffix = key.removeprefix('x-ratelimit-remaining-')
            threshold = needed if 'token' in suffix else 1
            try: remaining = int(value)
            except (ValueError, TypeError): return {'status': 'REQUIRES_PREFLIGHT_CONFIRMATION', 'wait_seconds': None}
            if remaining < threshold and 'x-ratelimit-reset-'+suffix not in headers:
                return {'status': 'REQUIRES_PREFLIGHT_CONFIRMATION', 'wait_seconds': None, 'reason': 'insufficient_remaining_without_reset'}
    wait = max([0, 60-elapsed_since_start, retry_wait, *reset_waits])
    return {'status': 'WAIT' if wait else 'READY_SUBJECT_TO_AUTHORIZATION', 'wait_seconds': wait,
            'rate_gate': gate, 'max_inflight': 1, 'model_calls_authorized': False}

def capacity_stop(provider):
    return provider.get('status') == 'incomplete' and (provider.get('incomplete_details') or {}).get('reason') == 'max_output_tokens'

def capacity_action(provider):
    stopped = capacity_stop(provider)
    return {'stop_scheduling_new_positions': stopped, 'capacity_failed': stopped,
            'retry_output_cap': False, 'automatic_limit_increase': False, 'preserve_response': True}

def assess(manifest, rows, bindings_unchanged, replays=None):
    result = r5_assess(manifest, rows, bindings_unchanged)
    if result['truncated']: return result
    bad = [r['position_id'] for r in rows if r['status'] in ('DELIVERED','DELIVERED_SCHEMA_OR_VISIBILITY_INVALID')
           and not r.get('schema_and_visibility_valid', False)]
    if bad:
        result['status'] = 'FAIL_CONFORMANCE'; result['invalid'] = sorted(set(result['invalid'] + bad))
    if result['status'] == 'PASS_DEVELOPMENT_CAP_ONLY_NOT_FREEZE':
        if replays is None:
            result['status'] = 'INCONCLUSIVE_REPLAY_PENDING'
        else:
            expected = {p['position_id'] for p in manifest['positions'] if p['cell_id']=='G1-EN'}
            rowmap = {r['position_id']:r for r in rows}
            ids = [r['position_id'] for r in replays]
            valid = len(ids)==len(set(ids)) and set(ids)==expected
            valid = valid and all(r.get('status')=='REPLAYED' and r.get('llm_calls')==0
                and r.get('source_output_sha256') and r['source_output_sha256']==rowmap[r['position_id']].get('output_sha256') for r in replays)
            if not valid: result['status'] = 'FAIL_REPLAY_CONFORMANCE'
    return result

def usage_components(usage):
    """Missing provider meters remain missing, never inferred as zero."""
    if not usage: return {'input_tokens': None, 'uncached_input_tokens': None, 'cached_input_tokens': None, 'output_tokens': None, 'usage_missing': True}
    total = usage.get('input_tokens'); cached = (usage.get('input_tokens_details') or {}).get('cached_tokens'); output = usage.get('output_tokens')
    for value in (total, cached, output):
        if value is not None and (type(value) is not int or value < 0): raise ValueError('Invalid provider usage')
    if total is not None and cached is not None and cached > total: raise ValueError('Cache cannot exceed input')
    return {'input_tokens': total, 'uncached_input_tokens': total-cached if total is not None and cached is not None else None,
            'cached_input_tokens': cached, 'output_tokens': output, 'usage_missing': any(x is None for x in (total,cached,output))}

def calculable_cost(usage, rates):
    parts = usage_components(usage)
    if parts['usage_missing']: return None
    return sum(Decimal(parts[k])*Decimal(str(rates[k]))/Decimal(1000000)
               for k in ('uncached_input_tokens','cached_input_tokens','output_tokens'))

def exercise_sequence(requests, fixture, directory):
    """Offline synthetic stop-policy proof only; never accepts a network adapter."""
    from investigation_r5.transport import FixtureTransport, exercise
    if type(fixture) is not FixtureTransport: raise PermissionError('Synthetic fixtures only')
    results=[]
    for index,request in enumerate(requests):
        if request['max_output_tokens'] != 24576: raise ValueError('Mixed candidate caps')
        result=exercise(request,fixture,directory/str(index))
        results.append(result)
        if any(capacity_stop(a.get('provider_metadata') or {}) for a in result['attempts']): break
    return {'synthetic':True,'positions':results,'not_scheduled':len(requests)-len(results),'model_calls':0}
