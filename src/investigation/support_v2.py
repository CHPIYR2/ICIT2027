"""Finite B0 amendment support checks. Not a free-text or LLM verifier."""
from investigation.schema_v2 import validate_claim_shape
from retrieval.investigation_retriever_v2 import validate_bundle
from retrieval.investigation_retriever import valid_e

WEAK='A command-type activation request was observed.'
MAPPED='A command-type activation request addressed to a control point mapped to asset {asset} was observed.'
ASSET='A captured command address maps via approved static metadata to a control point associated with asset {asset}.'
TEMPORAL='A command request mapped to asset {asset} was captured before a process observation associated with the same mapped asset. This is asset-linked temporal evidence; execution, causation and malicious intent are not established.'


def command_support(bundle,aid):
    validate_bundle(bundle)
    index={r['evidence_id']:r for r in bundle['entries']}
    a=index[aid]
    if a['source_type']!='command_address_observation' or a['mapping_status']!='exact_static_match' or a['cause_of_transmission']!=6:raise ValueError('No exact mapped request')
    m=index[a['parent_ids'][0]];meta=bundle['control_metadata'][a['mapping_evidence_id']]
    return m,a,meta


def temporal_support(bundle,aid,eid):
    m,a,cm=command_support(bundle,aid)
    e=next(r for r in bundle['entries'] if r['evidence_id']==eid)
    if not valid_e(e) or e['asset_id']!=a['mapped_target_asset_id'] or e['observation_time']<=a['observation_time']:raise ValueError('No valid later same-asset E')
    em=bundle['metadata'][e['fields']['channel_id']]
    if em['asset_id']!=cm['asset_id']:raise ValueError('Static asset edges disagree')
    return m,a,cm,e,em


def make_claim(number,kind,payload,citations,asset=None,channel=None):
    text={'command_observed':MAPPED if asset else WEAK,'asset_relationship':ASSET,'temporal_association':TEMPORAL}[kind].format(asset=asset)
    claim={'claim_id':f'c_{number}','question_ids':{'command_observed':['Q1','Q3'],'asset_relationship':['Q3'],'temporal_association':['Q4','Q5']}[kind],
        'claim_type':kind,'claim_text':text,'support_assertion':'asserted','evidence_ids':list(dict.fromkeys(citations)),
        'asset_ids':[asset] if asset else [],'channel_ids':[channel] if channel else [],'endpoint_ids':[],'payload':payload}
    return validate_claim_shape(claim)


def validate_supported_claim(claim,bundle):
    """Accept only canonical B0 text and precisely matching finite support payloads."""
    validate_claim_shape(claim);validate_bundle(bundle)
    p=claim['payload'];kind=claim['claim_type'];index={r['evidence_id']:r for r in bundle['entries']}
    if kind=='command_observed':
        m=index[p['record_id']]
        if m['source_type']!='message' or m['fields']['cause_of_transmission']!=6:raise ValueError('Not a request')
        expected={'record_id':m['evidence_id'],'asdu_type':m['fields']['asdu_type'],'cause_of_transmission':6,'time':m['observation_time'],
            'address_evidence_id':None,'mapping_evidence_id':None,'mapped_control_point_id':None,'mapped_target_asset_id':None}
        citations=[m['evidence_id']];asset=None;channel=None
        if p['address_evidence_id']:
            parent,a,cm=command_support(bundle,p['address_evidence_id'])
            if parent['evidence_id']!=m['evidence_id']:raise ValueError('Wrong parent request')
            expected.update(address_evidence_id=a['evidence_id'],mapping_evidence_id=cm['evidence_id'],mapped_control_point_id=cm['control_point_id'],mapped_target_asset_id=cm['asset_id'])
            citations += [a['evidence_id'],cm['evidence_id']];asset=cm['asset_id']
    elif kind=='asset_relationship':
        aid=next(x for x in p['record_ids'] if x.startswith('a_'));m,a,cm=command_support(bundle,aid)
        expected={'relation':'command_address_maps_to_asset','record_ids':[m['evidence_id'],aid],'mapping_ids':[cm['evidence_id']],'mapped_asset_id':cm['asset_id']}
        citations=[m['evidence_id'],aid,cm['evidence_id']];asset=cm['asset_id'];channel=None
    elif kind=='temporal_association':
        m,a,cm,e,em=temporal_support(bundle,p['earlier_id'],p['later_id'])
        expected={'earlier_id':a['evidence_id'],'later_id':e['evidence_id'],'relation':'precedes','delta_seconds':e['observation_time']-a['observation_time'],
            'scope':'same_observed_asset','mapping_ids':[cm['evidence_id'],em['evidence_id']],'mapped_asset_id':cm['asset_id']}
        citations=[m['evidence_id'],a['evidence_id'],cm['evidence_id'],e['evidence_id'],em['evidence_id']];asset=cm['asset_id'];channel=e['fields']['channel_id']
    else:raise ValueError('Outside finite amendment support checks')
    canonical=make_claim(int(claim['claim_id'][2:]),kind,expected,citations,asset,channel)
    if canonical!=claim:raise ValueError('Unsupported payload, citation, scope or stronger/noncanonical text')
    return True
