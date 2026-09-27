"""Deterministic fixed-budget retrieval. No evaluator metadata or classifier input."""
from collections import defaultdict, deque, Counter
import copy
import json
import math
from sherlock.io import opaque
from retrieval.evidence_formatter import digest, counts, validate_public

FAMILIES = ('voltage','current','active_power','reactive_power','reported_state')
BUDGETS = {'E':{'E':64,'N':0},'N':{'E':0,'N':64},'EN':{'E':32,'N':32}}


def valid_e(record):
    return record['source_type']=='process' and record['value'] is not None and not record['quality_flags']


def channel_groups(public):
    channels = defaultdict(list)
    for record in public['records']:
        if valid_e(record):
            channels[record['fields']['channel_id']].append(record)
    for values in channels.values():
        values.sort(key=lambda r:(r['observation_time'],r['evidence_id']))
    return channels


def pair_for_channel(records):
    pre = [r for r in records if r['observation_time'] < 0]
    post = [r for r in records if r['observation_time'] >= 0]
    if records[0]['fields']['family']=='reported_state':
        for a,b in zip(records,records[1:]):
            if a['value'] != b['value'] and a['observation_time'] < b['observation_time']:
                return a,b
        return None
    if pre and post:
        return pre[0],post[-1]
    if len(records)>1 and records[0]['observation_time']<records[-1]['observation_time']:
        return records[0],records[-1]
    return None


def difference(a,b):
    if not(valid_e(a) and valid_e(b)):
        raise ValueError('Invalid numerical evidence')
    if a['fields']['channel_id']!=b['fields']['channel_id'] or a['asset_id']!=b['asset_id'] or a['unit']!=b['unit'] or a['observation_time']>=b['observation_time']:
        raise ValueError('Incompatible pair')
    state = isinstance(a['value'],bool)
    if state != isinstance(b['value'],bool):
        raise ValueError('Boolean/numeric mismatch')
    if state and a['value']==b['value']:
        raise ValueError('No observed state transition')
    fields = {'kind':'reported_state_change' if state else 'numeric_difference','channel_id':a['fields']['channel_id'],
        'family':a['fields']['family'],'before_id':a['evidence_id'],'after_id':b['evidence_id'],
        'before_value':a['value'],'after_value':b['value'],'before_time':a['observation_time'],'after_time':b['observation_time'],
        'difference':None if state else b['value']-a['value'],'percent_change':None if state or a['value']==0 else 100*(b['value']-a['value'])/abs(a['value']),
        'percent_unavailable_reason':'boolean_state' if state else ('zero_baseline' if a['value']==0 else None)}
    if not state and any(v is not None and not math.isfinite(v) for v in (fields['difference'],fields['percent_change'])):
        raise ValueError('Nonfinite derived value')
    return {'evidence_id':opaque('d_','pair|'+a['evidence_id']+'|'+b['evidence_id'],24),'view':'E','source_type':'derived',
        'asset_id':a['asset_id'],'observation_time':b['observation_time'],'unit':a['unit'],
        'parent_ids':[a['evidence_id'],b['evidence_id']],'fields':fields}


def largest_gap(public):
    packets = sorted([r for r in public['records'] if r['source_type']=='packet' and r['fields']['ip_protocol']==6 and 2404 in (r['fields']['source_port'],r['fields']['destination_port'])],key=lambda r:(r['observation_time'],r['evidence_id']))
    points = [(-60,None)]+[(r['observation_time'],r['evidence_id']) for r in packets]+[(60,None)]
    left,right = max(zip(points,points[1:]),key=lambda pair:pair[1][0]-pair[0][0])
    query = {'population':'captured_TCP_2404_packets','window':[-60,60],'complete_visible_query':True,
        'eligible_count':len(packets),'ordered_population_sha256':digest([r['evidence_id'] for r in packets]),
        'universe_sha256':digest(public),'start':left[0],'end':right[0],'duration_seconds':right[0]-left[0],
        'left_id':left[1],'right_id':right[1],'left_censored':left[1] is None,'right_censored':right[1] is None,
        'interpretation':'No matching captured packet inside this interval; not proof of outage or attack.'}
    return {'evidence_id':opaque('d_',public['scope']['evidence_id']+'|gap|'+digest(query),24),'view':'N','source_type':'derived',
        'asset_id':None,'observation_time':right[0],'unit':'SECOND','parent_ids':[p for p in (left[1],right[1]) if p],
        'fields':{'kind':'communication_gap',**query}}


def e_units(public):
    queues = {family:deque() for family in FAMILIES}
    groups = channel_groups(public)
    for channel in sorted(groups):
        values = groups[channel]; pair = pair_for_channel(values)
        family = values[0]['fields']['family']
        if pair:
            a,b=pair
            queues[family].append([a,b,difference(a,b)])
        else:
            queues[family].append([values[0]])
    output=[]
    while any(queues.values()):
        for family in FAMILIES:
            if queues[family]:output.append(queues[family].popleft())
    # Remaining original records are an explicit lower-priority fallback.
    output.extend([r] for r in sorted(public['records'],key=lambda r:(r['observation_time'],r['evidence_id'])) if r['view']=='E')
    return output


def n_units(public):
    index={r['evidence_id']:r for r in public['records']}
    gap=largest_gap(public)
    output=[[index[p] for p in gap['parent_ids']]+[gap]]
    buckets={key:deque() for key in ('command','activation_response','RST','I','S','U','packet')}
    for r in sorted(public['records'],key=lambda r:(r['observation_time'],r['evidence_id'])):
        if r['view']!='N':continue
        f=r['fields']
        if r['source_type']=='message':
            if f['asdu_type'] in range(45,52) and f['cause_of_transmission']==6:key='command'
            elif f['asdu_type'] in range(45,52) and f['cause_of_transmission']==7:key='activation_response'
            else:key=f['apci_format']
        elif f['tcp_flags'] is not None and f['tcp_flags']&4:key='RST'
        else:key='packet'
        buckets[key].append([r])
    # Spread ordinary packets across time, so a long early burst does not consume the quota.
    times=[deque() for _ in range(8)]
    for unit in buckets['packet']:
        times[min(7,max(0,int((unit[0]['observation_time']+60)//15)))].append(unit)
    buckets['packet']=deque()
    while any(times):
        for queue in times:
            if queue:buckets['packet'].append(queue.popleft())
    while any(buckets.values()):
        for queue in buckets.values():
            if queue:output.append(queue.popleft())
    return output


def _bundle(public,entries):
    channels={r['fields']['channel_id'] for r in entries if 'channel_id' in r['fields']}
    return {'schema_version':'investigation-retrieval-phase1','scope':copy.deepcopy(public['scope']),
        'entries':copy.deepcopy(entries),'metadata':{c:copy.deepcopy(public['metadata'][c]) for c in sorted(channels)}}


def retrieve(public,max_bytes=48000):
    validate_public(public)
    view=public['scope']['view'];budget=BUDGETS[view];selected=[];seen=set();units=[]
    for domain,source in [('E',e_units),('N',n_units)]:
        if not budget[domain]:continue
        used=0
        for unit in source(public):
            new=[r for r in unit if r['evidence_id'] not in seen]
            if not new or used+len(new)>budget[domain]:continue
            selected.extend(new);seen.update(r['evidence_id'] for r in new);used+=len(new);units.append(new)
            if used==budget[domain]:break
    while True:
        bundle=_bundle(public,selected)
        size=len(json.dumps(bundle,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
        if size<=max_bytes:break
        if not units:raise ValueError('Scope metadata exceeds byte budget')
        removed={r['evidence_id'] for r in units.pop()};selected=[r for r in selected if r['evidence_id'] not in removed]
    originals={r['evidence_id'] for r in public['records']}
    selected_ids={r['evidence_id'] for r in selected}
    for r in selected:
        if r['source_type']=='derived' and not set(r['parent_ids'])<=selected_ids:
            raise ValueError('Derived entry missing its retrieved support')
    receipt={'schema_version':'investigation-receipt-phase1','event_id':public['scope']['event_id'],'view':view,
        'eligible_universe_sha256':digest(public),'eligible_original_counts':counts(public),
        'eligible_original_count':len(originals),'retrieved_original_ids':sorted(selected_ids&originals),
        'retrieved_derived_ids':sorted(selected_ids-originals),'retrieved_entry_count':len(selected),
        'retrieved_by_domain':dict(Counter(r['view'] for r in selected)),
        'omitted_original_count':len(originals-selected_ids),'budget':budget,'max_bytes':max_bytes,'serialized_bundle_bytes':size,
        'retrieved_bundle_sha256':digest(bundle),'metadata_sha256':digest(public['metadata']),
        'final_recovered_investigation_facts':None,'recovery_status':'NOT_SCORED_NO_HUMAN_GOLD',
        'accounting':'eligible universe != retrieval bundle != final human-scored recovered facts',
        'selection':'family round-robin channel pairs; N activity round-robin and packet time bins; complete-query gap; atomic pair support; no labels/scores',
        'metadata_policy':'same authorized static M universe across views; bundle includes only referenced channel mappings'}
    return bundle,receipt


def fact_accounting(support_sets, eligible_ids, retrieved_ids, correctly_recovered=None):
    """Future gold audit row; unknown recovery stays None, never inferred from retrieval."""
    if not support_sets or any(not s for s in support_sets):
        raise ValueError('Nonempty alternative support sets required')
    eligible=any(set(s)<=set(eligible_ids) for s in support_sets)
    retrieved=any(set(s)<=set(retrieved_ids) for s in support_sets)
    if retrieved and not eligible:raise ValueError('Retrieved IDs outside eligible universe')
    return {'supportable_from_eligible_universe':eligible,'complete_support_retrieved':retrieved,
        'correctly_recovered_by_system':correctly_recovered}
