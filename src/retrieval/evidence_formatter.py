"""Field-scoped public export; canonical ancestry stays in a private receipt."""
import hashlib
import json
import math
import re
from collections import Counter
from sherlock.io import opaque
from sherlock.sanitizer import FIELDS, validate_channel

SCOPE_KEYS={'evidence_id','event_id','view','window','right_boundary_exclusive','time_basis',
    'reported_measurement_time_available','source_relationship','visibility','available_domains','command_target_mapping'}
RECORD_KEYS={'evidence_id','view','source_type','observation_time','reported_time','asset_id','protocol','value','unit','quality_flags','fields','lineage_ref'}


def validate_public(public):
    if set(public)!={'schema_version','scope','metadata','records'} or public['schema_version']!='investigation-export-phase1':
        raise ValueError('Invalid public envelope')
    scope=public['scope'];view=scope['view']
    if set(scope)!=SCOPE_KEYS or view not in ('E','N','EN') or scope['window']!=[-60,60] or not scope['right_boundary_exclusive']:
        raise ValueError('Invalid public scope')
    if not re.fullmatch(r'ev_[0-9a-f]{20}',scope['event_id']) or scope['available_domains']!=list(view):
        raise ValueError('Invalid event/view scope')
    for channel,values in public['metadata'].items():
        validate_channel(channel,{k:v for k,v in values.items() if k!='evidence_id'})
        if values['evidence_id']!=opaque('meta_',channel,24):raise ValueError('Bad metadata ID')
    seen=set()
    for r in public['records']:
        if set(r)!=RECORD_KEYS or r['source_type'] not in FIELDS:raise ValueError('Unapproved public record')
        kind=r['source_type'];expected='E' if kind=='process' else 'N'
        if r['view']!=expected or expected not in view or set(r['fields'])!=FIELDS[kind]:raise ValueError('View/field leak')
        if not re.fullmatch({'packet':r'p_[0-9a-f]{24}','message':r'm_[0-9a-f]{24}','process':r'e_[0-9a-f]{24}'}[kind],r['evidence_id']) or r['evidence_id'] in seen:
            raise ValueError('Invalid or duplicate ID')
        seen.add(r['evidence_id'])
        if not math.isfinite(r['observation_time']) or not -60<=r['observation_time']<60 or r['reported_time'] is not None:raise ValueError('Invalid observation time')
        if kind!='process' and (r['value'] is not None or r['unit'] is not None or r['asset_id'] is not None):raise ValueError('Process data in N')
        if kind=='process':
            m=public['metadata'].get(r['fields']['channel_id'])
            if m is None or m['asset_id']!=r['asset_id'] or m['unit']!=r['unit'] or any(m[k]!=r['fields'][k] for k in ('family','attribute','context')):
                raise ValueError('Process metadata mismatch')
        if r['value'] is not None and (type(r['value']) not in (int,float,bool) or not math.isfinite(r['value'])):raise ValueError('Invalid value')
        if not set(r['quality_flags'])<={'invalid','not_topical','substituted','blocked','overflow','nonfinite'}:raise ValueError('Invalid quality')
    return public


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def export_episode(episode, view):
    episode.validate()
    if view not in ('E','N','EN'):
        raise ValueError('Invalid investigation view')
    records = []
    for record in episode.evidence_records:
        if record.view not in view:
            continue
        # No raw path, parent headers, resolver, labels, or back-reference.
        records.append({'evidence_id':record.evidence_id,'view':record.view,
            'source_type':record.source_type,'observation_time':record.observation_time-episode.anchor_time,
            'reported_time':None,'asset_id':record.asset_id,'protocol':record.protocol,
            'value':record.value,'unit':record.unit,'quality_flags':list(record.quality_flags),
            'fields':dict(record.fields),'lineage_ref':opaque('lin_',record.evidence_id,24)})
    metadata = {channel:{'evidence_id':opaque('meta_',channel,24),**dict(values)} for channel,values in sorted(episode.channels.items())}
    scope = {'evidence_id':opaque('d_',episode.episode_id+'|scope|'+view,24),'event_id':episode.episode_id,
        'view':view,'window':[-60,60],'right_boundary_exclusive':True,'time_basis':'capture_time_relative_to_supplied_event_anchor',
        'reported_measurement_time_available':False,'source_relationship':'E and N may share packet ancestry; not independent sensors',
        'visibility':'export view restriction, not canonical source removal',
        'available_domains':list(view),'command_target_mapping':'not_in_current_contract'}
    public = {'schema_version':'investigation-export-phase1','scope':scope,'metadata':metadata,'records':records}
    receipt = {'access':'PRIVATE_PROVENANCE_ONLY_NOT_LLM_OR_REVIEW_PACKET','event_id':episode.episode_id,'view':view,
        'public_universe_sha256':digest(public),'records':{r.evidence_id:{'parent_ids':list(r.parent_ids),
        'source_file':r.source_file,'vantage_point':r.vantage_point,'observation_time':r.observation_time-episode.anchor_time,
        'source_type':r.source_type,'exported':r.view in view} for r in episode.evidence_records}}
    return public, receipt


def counts(public):
    return dict(Counter(r['source_type'] for r in public['records']))
