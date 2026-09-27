"""B0 observations only. No speculative security interpretation or B3 verifier."""
from collections import Counter
from retrieval.investigation_retriever import valid_e
from retrieval.evidence_formatter import digest


def timeline(bundle, receipt):
    if digest(bundle)!=receipt['retrieved_bundle_sha256']:
        raise ValueError('Bundle/receipt mismatch')
    entries=sorted(bundle['entries'],key=lambda r:(r['observation_time'],r['evidence_id']))
    observations=[];differences=[];mappings=[]
    for row in entries:
        fields=row['fields'];kind=row['source_type']
        claim={'evidence_ids':[row['evidence_id']],'observation_time':row['observation_time']}
        if kind=='process':
            if not valid_e(row):continue
            claim.update(claim_type='reported_value',asset_id=row['asset_id'],channel_id=fields['channel_id'],
                         value=row['value'],unit=row['unit'],quality='valid_reported_observation')
            metadata=bundle['metadata'][fields['channel_id']]
            mappings.append({'claim_type':'asset_relationship','relation':'observation_channel_maps_to_asset',
                'asset_id':row['asset_id'],'channel_id':fields['channel_id'],
                'evidence_ids':[row['evidence_id'],metadata['evidence_id']]})
        elif kind=='derived':
            if fields['kind']=='communication_gap':
                claim.update(claim_type='communication_gap',interval=[fields['start'],fields['end']],
                    duration_seconds=fields['duration_seconds'],query_receipt=fields,
                    boundary_censored=fields['left_censored'] or fields['right_censored'])
            else:
                differences.append({'claim_type':'reported_state_change' if fields['kind']=='reported_state_change' else 'reported_change',
                    'asset_id':row['asset_id'],'unit':row['unit'],'evidence_ids':[row['evidence_id'],*row['parent_ids']],**fields})
                continue
        elif kind=='message':
            if fields['asdu_type'] in range(45,52) and fields['cause_of_transmission']==6:
                claim.update(claim_type='command_observed',asdu_type=fields['asdu_type'],cause_of_transmission=6,
                    target_asset_id=None,target_status='mapping_amendment_not_approved',execution_status='unknown')
            elif fields['asdu_type'] in range(45,52) and fields['cause_of_transmission']==7:
                claim.update(claim_type='acknowledgement_observed',acknowledgement_kind='iec_activation_confirmation',
                    physical_success='unknown',request_correlation='unavailable')
            else:claim.update(claim_type='network_activity',activity='iec_'+fields['apci_format']+'_frame')
        else:
            claim.update(claim_type='network_activity',activity='captured_packet',protocol=row['protocol'],
                source_endpoint=fields['source_endpoint'],destination_endpoint=fields['destination_endpoint'],
                tcp_rst=bool((fields['tcp_flags'] or 0)&4),tcp_ack_bit=bool((fields['tcp_flags'] or 0)&16))
        observations.append(claim)
    # Capture ordering is restricted to actual observations, not gap boundary timestamps.
    timed=[c for c in observations if c['claim_type']!='communication_gap']
    relations=[]
    for a,b in zip(timed,timed[1:]):
        relations.append({'claim_type':'temporal_association','relation':'precedes' if a['observation_time']<b['observation_time'] else 'same_capture_time',
            'evidence_ids':[a['evidence_ids'][0],b['evidence_ids'][0]],
            'delta_seconds':b['observation_time']-a['observation_time'],'scope':'episode_capture_order_only',
            'causality':'not_established'})
    unknowns=[]
    sid=bundle['scope']['evidence_id']
    for subject in ('command_execution','physical_success','causal_link','malicious_intent','attacker_identity','benign_or_safe','true_measurement_time'):
        unknowns.append({'claim_type':'unknown','subject':subject,'evidence_ids':[sid],
            'reason':'not_established_by_permitted_observations','status':'INSUFFICIENT'})
    for domain in ('E','N'):
        if domain not in bundle['scope']['view']:
            unknowns.append({'claim_type':'unknown','subject':domain+'_observations','evidence_ids':[sid],'reason':'view_excluded','status':'INSUFFICIENT'})
    if receipt['omitted_original_count']:
        unknowns.append({'claim_type':'unknown','subject':'unretrieved_observations','evidence_ids':[sid],
            'reason':'retrieval_budget_truncation_not_evidence_absence','count':receipt['omitted_original_count'],'status':'INSUFFICIENT'})
    if not any(d['claim_type']=='reported_state_change' for d in differences):
        unknowns.append({'claim_type':'unknown','subject':'reported_state_change','evidence_ids':[sid],
            'reason':'no_qualifying_state_pair_in_retrieved_bundle_not_proof_of_stability','status':'INSUFFICIENT'})
    return {'schema_version':'investigation-b0-phase1','baseline':'B0','review_status':'DRAFT_UNREVIEWED',
        'event_id':bundle['scope']['event_id'],'view':bundle['scope']['view'],'scope':bundle['scope'],
        'retrieval_bundle_sha256':digest(bundle),'observations':observations,'numerical_differences':differences,
        'asset_channel_mappings':mappings,'temporal_relations':relations,'security_interpretation':[],
        'unknowns':unknowns,'accounting':{'eligible_original_count':receipt['eligible_original_count'],
            'retrieved_entries':receipt['retrieved_entry_count'],'mechanically_presented_observations':len(observations),
            'mechanically_computed_differences':len(differences),'final_recovered_gold_facts':None,
            'note':'Counts are not annotation gold or measured completeness.'}}
