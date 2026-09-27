"""Versioned B0 retrieval: address/message closure and observable same-asset priority."""
import copy
import json
from collections import Counter
from retrieval.evidence_formatter import digest
from retrieval.evidence_formatter_v2 import validate_public,base_export,validate_mapping
from retrieval.investigation_retriever import BUDGETS,e_units,n_units,largest_gap,valid_e
from investigation.schema_v2 import validate,require_id


def address_records(records):
    return [r for r in records if r['source_type']=='command_address_observation']


def matching_e(address,records,later=False):
    return sorted([r for r in records if valid_e(r) and address['mapping_status']=='exact_static_match'
        and r['asset_id']==address['mapped_target_asset_id']
        and (not later or r['observation_time']>address['observation_time'])],
        key=lambda r:(r['observation_time'],r['evidence_id']))


def bundle_for(public,entries):
    channels={r['fields']['channel_id'] for r in entries if 'channel_id' in r.get('fields',{})}
    mids={r['mapping_evidence_id'] for r in address_records(entries) if r['mapping_evidence_id']}
    return {'schema_version':'investigation-retrieval-v2','scope':copy.deepcopy(public['scope']),
        'entries':copy.deepcopy(entries),'metadata':{c:copy.deepcopy(public['metadata'][c]) for c in sorted(channels)},
        'control_metadata':{m:copy.deepcopy(public['control_metadata'][m]) for m in sorted(mids)}}


def validate_bundle(bundle):
    if bundle['schema_version']!='investigation-retrieval-v2':raise ValueError('Wrong bundle version')
    if set(bundle)!={'schema_version','scope','entries','metadata','control_metadata'}:raise ValueError('Unapproved bundle fields')
    validate_public({'schema_version':'investigation-export-v2','scope':bundle['scope'],'metadata':bundle['metadata'],
        'control_metadata':bundle['control_metadata'],'records':[r for r in bundle['entries'] if r['source_type']!='derived']})
    index={r['evidence_id']:r for r in bundle['entries']}
    if len(index)!=len(bundle['entries']):raise ValueError('Duplicate retrieved evidence')
    for r in bundle['entries']:
        require_id(r['evidence_id'],'retrieved_record')
        if r['view'] not in bundle['scope']['view']:raise ValueError('Hidden evidence view')
        if r['source_type']=='derived':
            if not set(r['parent_ids'])<=set(index):raise ValueError('Missing derived parent')
        elif r['source_type']=='command_address_observation':
            validate('command_address.v2.json',r)
            m=index.get(r['parent_ids'][0])
            if not m or m['source_type']!='message':raise ValueError('Missing command parent')
            if (m['fields']['asdu_type'],m['fields']['cause_of_transmission'],m['observation_time'])!=(r['asdu_type'],r['cause_of_transmission'],r['observation_time']):raise ValueError('Command parent mismatch')
            if r['mapping_status']=='exact_static_match':
                meta=bundle['control_metadata'].get(r['mapping_evidence_id'])
                if not meta:raise ValueError('Missing control mapping')
                validate_mapping(meta)
                if (meta['control_point_id'],meta['asset_id'])!=(r['mapped_control_point_id'],r['mapped_target_asset_id']):raise ValueError('Control mapping mismatch')
        elif r['source_type']=='process':
            meta=bundle['metadata'].get(r['fields']['channel_id'])
            if not meta or meta['asset_id']!=r['asset_id']:raise ValueError('Channel mapping mismatch')
    envelope={'schema_version':'investigation-retrieval-v2','event_id':bundle['scope']['event_id'],'view':bundle['scope']['view'],
        'retrieved_ids':sorted(index),'mapping_ids':sorted([m['evidence_id'] for m in bundle['metadata'].values()]+list(bundle['control_metadata'])),
        'scope_id':bundle['scope']['evidence_id']}
    validate('retrieval_ids.v2.json',envelope)
    return envelope


def retrieve(public,max_bytes=48000):
    validate_public(public)
    budget=BUDGETS[public['scope']['view']];base=base_export(public)
    index={r['evidence_id']:r for r in public['records']};selected=[];seen=set();units=[];used=Counter()
    def add(unit,domain):
        fresh=[r for r in unit if r['evidence_id'] not in seen]
        if not fresh or used[domain]+len(fresh)>budget[domain]:return
        selected.extend(fresh);seen.update(r['evidence_id'] for r in fresh);units.append(fresh);used[domain]+=len(fresh)
    if budget['N']:
        addresses=sorted(address_records(public['records']),key=lambda r:(r['cause_of_transmission']!=6,r['observation_time'],r['evidence_id']))
        for a in addresses:add([index[a['parent_ids'][0]],a],'N')
        gap=largest_gap(public)
        add([index[p] for p in gap['parent_ids']]+[gap],'N')
        for unit in n_units(base)[1:]:add(unit,'N')
    if budget['E']:
        # EN-only, explicitly versioned cross-source retrieval. No labels or scores.
        for a in address_records(selected):
            if a['cause_of_transmission']!=6:continue
            matches=matching_e(a,public['records'],later=True)
            if matches:add([matches[0]],'E')
        for unit in e_units(base):add(unit,'E')
    while True:
        bundle=bundle_for(public,selected)
        size=len(json.dumps(bundle,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
        if size<=max_bytes:break
        if not units:raise ValueError('Scope exceeds byte budget')
        removed={r['evidence_id'] for r in units.pop()};selected=[r for r in selected if r['evidence_id'] not in removed]
    envelope=validate_bundle(bundle)
    original=set(index);selected_ids={r['evidence_id'] for r in selected};addresses=address_records(public['records'])
    receipt={'schema_version':'investigation-receipt-v2','event_id':public['scope']['event_id'],'view':public['scope']['view'],
        'eligible_universe_sha256':digest(public),'eligible_original_count':len(original),
        'eligible_by_source_type':dict(Counter(r['source_type'] for r in public['records'])),
        'eligible_canonical_count':len(original)-len(addresses),'eligible_address_count':len(addresses),
        'eligible_request_count':sum(r['source_type']=='message' and r['fields']['asdu_type'] in range(45,52) and r['fields']['cause_of_transmission']==6 for r in public['records']),
        'retrieved_original_ids':sorted(selected_ids&original),'retrieved_derived_ids':sorted(selected_ids-original),
        'retrieved_entry_count':len(selected),'retrieved_by_domain':dict(Counter(r['view'] for r in selected)),
        'retrieved_address_ids':sorted(r['evidence_id'] for r in address_records(selected)),
        'eligible_address_ids':sorted(r['evidence_id'] for r in addresses),
        'eligible_same_asset_later_E_address_ids':[a['evidence_id'] for a in addresses if matching_e(a,public['records'],later=True)],
        'omitted_original_count':len(original-selected_ids),'budget':budget,'max_bytes':max_bytes,'serialized_bundle_bytes':size,
        'retrieved_bundle_sha256':digest(bundle),'namespace_envelope':envelope,
        'final_recovered_investigation_facts':None,'recovery_status':'NOT_SCORED_NO_HUMAN_GOLD',
        'selection':'N request-first atomic m+a; complete gap; N round-robin. EN prioritizes nearest later same-asset valid E per retrieved request, then E family round-robin. E-only never reads N.',
        'metadata_policy':'same static M universe; only referenced mappings in bundle; a entries count against N and all mappings against byte budget',
        'accounting':'eligible records != retrieved entries != human-scored recovered facts'}
    return bundle,receipt
