"""Pure predeclared capacity acceptance; no model execution or research scoring."""
def assess(manifest,results,bindings_unchanged):
    expected={r['position_id']:r for r in manifest['positions']}
    if len(expected)!=64:raise ValueError('Wrong validation manifest')
    seen=set();missing=[];no_delivery=[];invalid=[];truncated=[]
    for r in results:
        k=r['position_id']
        if k not in expected or k in seen:raise ValueError('Unexpected/duplicate position')
        seen.add(k)
        if r.get('termination_reason')=='max_output_tokens':truncated.append(k)
        elif r['status'] not in ('DELIVERED','DELIVERED_SCHEMA_OR_VISIBILITY_INVALID'):no_delivery.append(k)
        elif expected[k]['purpose']=='new_condition_smoke' and not r.get('schema_and_visibility_valid',False):invalid.append(k)
        if not r.get('request_diff_valid',False):invalid.append(k)
    missing=sorted(set(expected)-seen)
    if truncated:status='FAIL_OUTPUT_CAP_STOP_AUTHOR_REVIEW'
    elif invalid or not bindings_unchanged:status='FAIL_CONFORMANCE'
    elif no_delivery or missing:status='INCONCLUSIVE_NO_DELIVERY_OR_PENDING'
    else:status='PASS_DEVELOPMENT_CAP_ONLY_NOT_FREEZE'
    return {'status':status,'truncated':truncated,'invalid':invalid,'no_delivery':no_delivery,'missing':missing,'automatic_rerun':False,'automatic_limit_increase':False}
