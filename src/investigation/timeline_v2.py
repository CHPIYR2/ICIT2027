"""B0 v2: exact address mappings and capture-time links, never causal claims."""
import copy
from retrieval.evidence_formatter import digest
from retrieval.investigation_retriever_v2 import validate_bundle,address_records,matching_e
from investigation.timeline import timeline as timeline_v1
from investigation.support_v2 import make_claim,validate_supported_claim


def timeline(bundle,receipt):
    validate_bundle(bundle)
    if digest(bundle)!=receipt['retrieved_bundle_sha256']:raise ValueError('Bundle/receipt mismatch')
    legacy=copy.deepcopy(bundle);legacy['entries']=[r for r in legacy['entries'] if r['source_type']!='command_address_observation']
    legacy_receipt={**receipt,'retrieved_bundle_sha256':digest(legacy)}
    report=timeline_v1(legacy,legacy_receipt)
    report.update(schema_version='investigation-b0-v2',retrieval_bundle_sha256=digest(bundle))
    # State changes are optional observations, never a mandatory sufficiency gate.
    report['unknowns']=[u for u in report['unknowns'] if u['subject']!='reported_state_change']
    report['optional_claim_types']=['reported_state_change']
    entries=bundle['entries'];addresses=address_records(entries);claims=[];insufficient=[]
    for m in entries:
        if m['source_type']!='message' or m['fields']['asdu_type'] not in (45,47,50) or m['fields']['cause_of_transmission']!=6:continue
        children=[a for a in addresses if a['parent_ids']==[m['evidence_id']]]
        exact=[a for a in children if a['mapping_status']=='exact_static_match']
        for a in exact or [None]:
            cm=bundle['control_metadata'][a['mapping_evidence_id']] if a else None
            p={'record_id':m['evidence_id'],'asdu_type':m['fields']['asdu_type'],'cause_of_transmission':6,'time':m['observation_time'],
                'address_evidence_id':a['evidence_id'] if a else None,'mapping_evidence_id':cm['evidence_id'] if cm else None,
                'mapped_control_point_id':cm['control_point_id'] if cm else None,'mapped_target_asset_id':cm['asset_id'] if cm else None}
            citations=[m['evidence_id']]+([a['evidence_id'],cm['evidence_id']] if a else [])
            claims.append(make_claim(len(claims)+1,'command_observed',p,citations,cm['asset_id'] if cm else None))
        for a in children:
            if a['mapping_status']!='exact_static_match':
                insufficient.append({'status':'INSUFFICIENT','subject':'command_target','evidence_ids':[m['evidence_id'],a['evidence_id']],'reason':a['reason']});continue
            cm=bundle['control_metadata'][a['mapping_evidence_id']];asset=cm['asset_id'];citations=[m['evidence_id'],a['evidence_id'],cm['evidence_id']]
            claims.append(make_claim(len(claims)+1,'asset_relationship',{'relation':'command_address_maps_to_asset','record_ids':[m['evidence_id'],a['evidence_id']],
                'mapping_ids':[cm['evidence_id']],'mapped_asset_id':asset},citations,asset))
            matches=matching_e(a,entries,later=True)
            if matches:
                e=matches[0];em=bundle['metadata'][e['fields']['channel_id']]
                p={'earlier_id':a['evidence_id'],'later_id':e['evidence_id'],'relation':'precedes','delta_seconds':e['observation_time']-a['observation_time'],
                    'scope':'same_observed_asset','mapping_ids':[cm['evidence_id'],em['evidence_id']],'mapped_asset_id':asset}
                claims.append(make_claim(len(claims)+1,'temporal_association',p,citations+[e['evidence_id'],em['evidence_id']],asset,e['fields']['channel_id']))
            else:
                reason='view_excluded' if 'E' not in bundle['scope']['view'] else ('not_retrieved' if a['evidence_id'] in receipt['eligible_same_asset_later_E_address_ids'] else 'no_valid_later_same_asset_E_in_allowed_window')
                insufficient.append({'status':'INSUFFICIENT','subject':'same_observed_asset_temporal_association','evidence_ids':citations+[bundle['scope']['evidence_id']],
                    'mapped_asset_id':asset,'reason':reason,'does_not_imply':'execution failure, benignness, stability, or safety'})
        if not children:insufficient.append({'status':'INSUFFICIENT','subject':'command_target','evidence_ids':[m['evidence_id']],'reason':'address_not_retrieved_or_unavailable'})
    if not any(c['claim_type']=='command_observed' for c in claims):
        insufficient.append({'status':'INSUFFICIENT','subject':'command_request','evidence_ids':[bundle['scope']['evidence_id']],
            'reason':'view_excluded' if 'N' not in bundle['scope']['view'] else ('request_not_retrieved' if receipt['eligible_request_count'] else 'no_command_request_in_allowed_window')})
    for claim in claims:validate_supported_claim(claim,bundle)
    # The amendment claims are authoritative for command strength; legacy observation rows remain a compact index.
    for row in report['observations']:
        if row['claim_type']=='command_observed':
            mapped=[c for c in claims if c['claim_type']=='command_observed' and c['payload']['record_id']==row['evidence_ids'][0] and c['payload']['mapped_target_asset_id']]
            row['target_status']='see_validated_amendment_claims' if mapped else 'address_mapping_unavailable'
    report['amendment_claims']=claims;report['amendment_insufficiency']=insufficient
    report['accounting']['mechanically_supported_amendment_claims']=len(claims)
    report['boundary']='Asset-linked temporal evidence only. Execution, physical effect, causation, malicious intent, attack success and attribution are not established.'
    return report
