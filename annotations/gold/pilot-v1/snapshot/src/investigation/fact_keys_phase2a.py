"""Mechanical key proposals only: equality never establishes semantic correctness."""
import hashlib
import json
from investigation.schema_v2 import require_id

RECIPES={
    'command_observed':{'message_id':'command_message'},
    'mapped_command_observed':{'message_id':'command_message','address_id':'command_address','mapping_id':'mapping','asset_id':None,'control_point_id':None},
    'reported_value':{'record_id':'process_observation'},
    'reported_change':{'before_id':'process_observation','after_id':'process_observation','quantity':None,'unit':None},
    'reported_state_change':{'before_id':'process_observation','after_id':'process_observation'},
    'command_address_maps_to_asset':{'message_id':'command_message','address_id':'command_address','mapping_id':'mapping','asset_id':None},
    'observation_channel_maps_to_asset':{'record_id':'process_observation','mapping_id':'mapping','channel_id':None,'asset_id':None},
    'same_mapped_asset':{'record_ids':'process_observation','mapping_ids':'mapping','asset_id':None},
    'packet_endpoint_pair':{'packet_id':'packet','source_endpoint':None,'destination_endpoint':None},
    'temporal_association':{'earlier_id':'temporal_observation','later_id':'temporal_observation','relation':None,'scope':None,'mapping_ids':'mapping','asset_id':None},
    'network_activity':{'record_id':'network_observation','activity':None},
    'acknowledgement_observed':{'record_id':'network_observation','kind':None},
    'communication_gap':{'coverage_id':'derived','population':None,'start':None,'end':None},
}


def canonical_descriptor(event_id,kind,identity):
    import re
    if not re.fullmatch(r'ev_[0-9a-f]{20}',event_id):raise ValueError('Bad event ID')
    # This is the only automatic type alias. Direction and operation remain distinct.
    kind='reported_change' if kind=='electrical_change' else kind
    if kind not in RECIPES:raise ValueError('No mechanical key recipe; human key required')
    if set(identity)!=set(RECIPES[kind]):raise ValueError('Incomplete or extra identity fields')
    normalized=dict(identity)
    for field,role in RECIPES[kind].items():
        value=identity[field]
        if field in ('record_ids','mapping_ids'):
            if not isinstance(value,list) or len(value)!=len(set(value)):raise ValueError('Invalid ID set')
            for rid in value:require_id(rid,role)
            normalized[field]=sorted(value)
        elif role:require_id(value,role)
        elif value is None:
            if kind!='temporal_association' or field!='asset_id':raise ValueError('Missing identity')
        elif field.endswith('_id') or field.endswith('_endpoint'):
            prefix={'asset_id':'asset','channel_id':'ch','control_point_id':'cp','source_endpoint':'ep','destination_endpoint':'ep'}[field]
            if not re.fullmatch(prefix+r'_[0-9a-f]{16}',value):raise ValueError('Nonopaque entity ID')
    if kind in ('reported_change','reported_state_change') and identity['before_id']==identity['after_id']:raise ValueError('Identical before/after evidence')
    if kind=='reported_change' and identity['quantity'] not in ('difference','percent_change'):raise ValueError('Unknown numerical quantity')
    if kind=='temporal_association':
        if identity['earlier_id']==identity['later_id']:raise ValueError('Self relation')
        if identity['relation'] not in ('precedes','same_capture_time') or identity['scope'] not in ('episode_only','same_observed_asset'):raise ValueError('Unknown time relation/scope')
        if identity['scope']=='same_observed_asset':
            if {identity['earlier_id'][:2],identity['later_id'][:2]}!={'a_','e_'} or len(identity['mapping_ids'])!=2 or identity['asset_id'] is None:raise ValueError('Both asset edges required')
        elif identity['mapping_ids'] or identity['asset_id'] is not None:raise ValueError('Episode-only does not assert an asset')
        if identity['relation']=='same_capture_time':
            normalized['earlier_id'],normalized['later_id']=sorted([identity['earlier_id'],identity['later_id']])
    return {'key_version':'fact-key-phase2a-proposed-v1','event_id':event_id,'kind':kind,'identity':normalized}


def propose_fact_key(event_id,kind,identity):
    canonical=canonical_descriptor(event_id,kind,identity)
    encoded=json.dumps(canonical,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    return 'fk_'+hashlib.sha256(encoded).hexdigest()


def duplicate_proposals(candidates):
    groups={}
    for row in candidates:groups.setdefault(row['proposed_fact_key'],[]).append(row['candidate_id'])
    return [{'proposed_fact_key':key,'candidate_ids':ids,'decision':None,'status':'DRAFT_UNREVIEWED'}
            for key,ids in sorted(groups.items()) if len(ids)>1]
