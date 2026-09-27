"""Versioned investigation export; old evidence schema and exports are untouched."""
import copy
from retrieval.evidence_formatter import export_episode as export_v1,validate_public as validate_v1,digest
from investigation.schema_v2 import validate,require_id
from evidence.command_address_v2 import ATTRIBUTES


def validate_mapping(meta):
    if set(meta)!={'evidence_id','control_point_id','asset_id','context','attribute'}:raise ValueError('Unapproved static mapping fields')
    require_id(meta['evidence_id'],'mapping')
    import re
    if not re.fullmatch(r'cp_[0-9a-f]{16}',meta['control_point_id']) or not re.fullmatch(r'asset_[0-9a-f]{16}',meta['asset_id']):raise ValueError('Raw mapping identity leak')
    if meta['context']!='CONFIGURATION' or meta['attribute'] not in ATTRIBUTES:raise ValueError('Non-allowlisted control metadata')


def base_export(public):
    return {'schema_version':'investigation-export-phase1','scope':public['scope'],'metadata':public['metadata'],
            'records':[r for r in public['records'] if r['source_type']!='command_address_observation']}


def validate_public(public):
    if set(public)!={'schema_version','scope','metadata','control_metadata','records'} or public['schema_version']!='investigation-export-v2':raise ValueError('Wrong v2 envelope')
    validate_v1(base_export(public))
    if public['scope']['command_target_mapping']!='approved_static_command_address_v2':raise ValueError('Wrong amendment scope')
    for mid,meta in public['control_metadata'].items():
        validate_mapping(meta)
        if mid!=meta['evidence_id']:raise ValueError('Mapping ID mismatch')
    index={r['evidence_id']:r for r in public['records']}
    if len(index)!=len(public['records']):raise ValueError('Duplicate evidence ID')
    for a in public['records']:
        if a['source_type']!='command_address_observation':continue
        validate('command_address.v2.json',a)
        if 'N' not in public['scope']['view']:raise ValueError('Address leaked into E-only')
        parent=index.get(a['parent_ids'][0])
        if parent is None or parent['source_type']!='message':raise ValueError('Missing visible command parent')
        if a['asdu_type']!=parent['fields']['asdu_type'] or a['cause_of_transmission']!=parent['fields']['cause_of_transmission'] or a['observation_time']!=parent['observation_time']:raise ValueError('Address/message mismatch')
        if a['mapping_status']=='exact_static_match':
            meta=public['control_metadata'].get(a['mapping_evidence_id'])
            if meta is None or meta['control_point_id']!=a['mapped_control_point_id'] or meta['asset_id']!=a['mapped_target_asset_id']:raise ValueError('Address/static mapping mismatch')
            if a['reason']!='exact_allowlisted_static_mapping' or a['object_index'] is None:raise ValueError('Invalid exact mapping')
        elif any(a[k] is not None for k in ('mapped_control_point_id','mapped_target_asset_id','mapping_evidence_id')):raise ValueError('Unmapped child carries guessed target')
    return public


def export_episode(episode,view,sidecar,control_metadata):
    public,provenance=export_v1(episode,view)
    if sidecar['event_id']!=episode.episode_id:raise ValueError('Sidecar event mismatch')
    public['schema_version']='investigation-export-v2'
    public['scope']['command_target_mapping']='approved_static_command_address_v2'
    public['control_metadata']=copy.deepcopy(control_metadata)
    if 'N' in view:public['records'].extend(copy.deepcopy(sidecar['records']))
    validate_public(public)
    provenance['public_universe_sha256']=digest(public)
    for a in sidecar['records']:
        provenance['records'][a['evidence_id']]={'parent_ids':a['parent_ids'],'observation_time':a['observation_time'],
            'source_type':'command_address_observation','exported':'N' in view}
    visibility={'schema_version':'investigation-visibility-v2','event_id':episode.episode_id,'view':view,
        'visible_record_ids':[r['evidence_id'] for r in public['records']],
        'address_parents':{r['evidence_id']:r['parent_ids'][0] for r in public['records'] if r['source_type']=='command_address_observation'}}
    validate_visibility(visibility,public)
    return public,provenance,visibility


def validate_visibility(visibility,public):
    validate('visibility_ids.v2.json',visibility)
    if visibility['event_id']!=public['scope']['event_id'] or visibility['view']!=public['scope']['view']:raise ValueError('Visibility scope mismatch')
    if set(visibility['visible_record_ids'])!={r['evidence_id'] for r in public['records']}:raise ValueError('Visibility ID mismatch')
    parents={r['evidence_id']:r['parent_ids'][0] for r in public['records'] if r['source_type']=='command_address_observation'}
    if visibility['address_parents']!=parents:raise ValueError('Visibility parent mismatch')
    if not set(parents.values())<=set(visibility['visible_record_ids']):raise ValueError('Hidden address parent')
    return True
