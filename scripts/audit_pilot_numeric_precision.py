"""Descriptive precision audit of approved development pilots only. No scoring."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import gzip
import json
import math
import struct
import zipfile
from collections import Counter,defaultdict
from fractions import Fraction
from sherlock.io import ROOT,read_json,sha256
from investigation.review_phase2a import pilot_ids,load_universe


def float32_ulp(value):
    magnitude=abs(value)
    bits=struct.unpack('<I',struct.pack('<f',magnitude))[0]
    adjacent=struct.unpack('<f',struct.pack('<I',bits+1))[0]
    return adjacent-magnitude


def describe(values):
    if not values:return {'n':0}
    values=sorted(values)
    return {'n':len(values),'min':values[0],'median':values[len(values)//2],'max':values[-1]}


def audit():
    ids=pilot_ids();units=defaultdict(list);channels=defaultdict(list);sources=set();anchors=[];types=Counter();input_hashes={}
    timestamp_errors=[];gold_numeric=[]
    dev_rows={r['episode_id']:r for r in read_json(ROOT/'data/processed/v2/development_features.json')['rows']}
    for eid in ids:
        if eid not in dev_rows:raise ValueError('Non-development event forbidden')
        row=dev_rows[eid];path=ROOT/row['evidence_path']
        if sha256(path)!=row['evidence_sha256']:raise ValueError('Canonical source hash changed')
        input_hashes[str(path.relative_to(ROOT))]=sha256(path)
        with gzip.open(path,'rt') as f:episode=json.load(f)
        records={r['evidence_id']:r for r in episode['evidence_records']};anchors.append(episode['anchor_time'])
        sources.update(r['source_file'] for r in records.values())
        public=load_universe(eid,'EN');index={r['evidence_id']:r for r in public['records']}
        for r in public['records']:
            timestamp_errors.append(abs(float(Fraction.from_float(r['observation_time'])*1000000-round(r['observation_time']*1000000)))/1000000)
            if r['source_type']!='process' or r['value'] is None or r['quality_flags']:continue
            parent=records[records[r['evidence_id']]['parent_ids'][0]]
            types[str(parent['fields']['asdu_type'])]+=1
            if type(r['value']) is bool:continue
            units[r['unit']].append(r['value']);channels[(eid,r['fields']['channel_id'])].append(r['value'])
        annotation_path=ROOT/'annotations/phase2a/pilots'/eid/'reviewer_annotation.json'
        input_hashes[str(annotation_path.relative_to(ROOT))]=sha256(annotation_path)
        public_path=ROOT/'results/investigation-v2/B0'/eid/'EN/eligible.json.gz'
        input_hashes[str(public_path.relative_to(ROOT))]=sha256(public_path)
        annotation=read_json(annotation_path)
        for fact in annotation['facts']:
            if fact['claim_type'] not in ('electrical_change','reported_change'):continue
            key=fact['key_identity'];a=index[key['before_id']];b=index[key['after_id']]
            value=b['value']-a['value']
            gold_numeric.append({'event_id':eid,'gold_claim_id':fact['gold_claim_id'],'unit':a['unit'],
                'canonical_before':a['value'],'canonical_after':b['value'],'canonical_difference':value,
                'canonical_reference':'Recompute from cited evidence; human free-text decimal rendering does not replace numeric reference'})
    summaries={}
    for unit,values in sorted(units.items()):
        ulps=[float32_ulp(v) for v in values if v!=0]
        steps=[]
        for key,vals in channels.items():
            # Unit follows channel metadata in the approved public evidence.
            if load_universe_cached_unit(key)!=unit:continue
            ordered=sorted(set(vals));steps.extend(b-a for a,b in zip(ordered,ordered[1:]))
        summaries[unit]={'values':describe(values),'zeros':sum(v==0 for v in values),
            'exact_float32_roundtrip_count':sum(struct.unpack('<f',struct.pack('<f',v))[0]==v for v in values),
            'float32_ulp_at_nonzero_values':describe(ulps),'positive_observed_same_channel_value_spacing':describe(steps),
            'decimal_6_places_rounding_error':describe([abs(float(f'{v:.6f}')-v) for v in values]),
            'eight_significant_digits_relative_error_nonzero':describe([abs(float(f'{v:.8g}')-v)/abs(v) for v in values if v]),
            'json_float_roundtrip_exact':all(json.loads(json.dumps(v))==v for v in values)}
    pair_summary=defaultdict(lambda:defaultdict(list));zero_baselines=0
    for eid in ids:
        path=ROOT/'annotations/events-v2'/eid/'numerical_candidates.DRAFT.json';input_hashes[str(path.relative_to(ROOT))]=sha256(path)
        for d in read_json(path)['entries']:
            f=d['fields']
            if f['kind']!='numeric_difference':continue
            unit=d['unit'];a=f['before_value'];b=f['after_value'];delta=f['difference']
            pair_summary[unit]['difference'].append(delta)
            err=abs(Fraction.from_float(delta)-(Fraction.from_float(b)-Fraction.from_float(a)))
            pair_summary[unit]['binary64_subtraction_error'].append(float(err))
            pair_summary[unit]['decimal_6_places_difference_rounding_error'].append(abs(float(f'{delta:.6f}')-delta))
            if a==0:zero_baselines+=1;continue
            pct=f['percent_change'];exact=100*(Fraction.from_float(b)-Fraction.from_float(a))/abs(Fraction.from_float(a))
            pair_summary[unit]['percent_change'].append(pct)
            pair_summary[unit]['binary64_percent_error'].append(float(abs(Fraction.from_float(pct)-exact)))
    resolver=read_json(ROOT/'data/manifests/development_source_resolver.v2.json')['sources']
    archives={a['sha256']:ROOT/a['local_path'] for a in read_json(ROOT/'data/manifests/sherlock_manifest.json')['archives']}
    headers=[]
    for source in resolver:
        if source['source_id'] not in sources:continue
        with zipfile.ZipFile(archives[source['archive_sha256']]) as z:
            with z.open(source['member']) as f:head=f.read(24)
        quantum={b'\xd4\xc3\xb2\xa1':1e-6,b'\xa1\xb2\xc3\xd4':1e-6,b'\x4d\x3c\xb2\xa1':1e-9,b'\xa1\xb2\x3c\x4d':1e-9}[head[:4]]
        headers.append({'source_id':source['source_id'],'magic_hex':head[:4].hex(),'timestamp_tick_seconds':quantum,
            'header_sha256':__import__('hashlib').sha256(head).hexdigest(),'archive_sha256_from_existing_resolver':source['archive_sha256']})
    return {'status':'EMPIRICAL_PILOT_PRECISION_AUDIT_NOT_PERFORMANCE','pilot_event_ids':ids,'evaluation_events_accessed':0,
        'units':summaries,'process_asdu_types':dict(types),'total_valid_numeric_observations':sum(len(v) for v in units.values()),
        'numeric_pairs':{unit:{k:describe(v) for k,v in rows.items()} for unit,rows in pair_summary.items()},
        'zero_baseline_pairs_percent_unavailable':zero_baselines,'reviewed_numeric_gold_references':gold_numeric,
        'capture_headers':headers,'anchor_binary64_ulp_seconds':describe([math.ulp(a) for a in anchors]),
        'relative_time_distance_from_nearest_microsecond':describe(timestamp_errors),
        'interpretation':['Observed decoder uses little-endian binary32 for type13, then lossless Python binary64/JSON representation for these finite values.',
            'ULP and observed spacing describe stored representation/data, not sensor calibration accuracy or physical resolution.',
            'Pair differences and percentages are computed binary64 values; near-zero denominator can amplify percentages. No initial values used.',
            'Tolerance proposals may accommodate explicit output rendering, not change unit/identity/order or excuse unsupported evidence.'],
        'input_hashes':input_hashes,'decoder_files':{p:sha256(ROOT/p) for p in ('src/sherlock/parser.py','src/sherlock/parser_v2.py','src/sherlock/capture_v2.py','src/retrieval/investigation_retriever.py')}}


from functools import lru_cache
@lru_cache(None)
def public_for_unit(eid):return load_universe(eid,'EN')['metadata']


def load_universe_cached_unit(key):return public_for_unit(key[0])[key[1]]['unit']


if __name__=='__main__':
    result=audit();out=ROOT/'results/investigation-freeze-v1/numeric_precision.pilots.json'
    with out.open('x') as f:json.dump(result,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
    print(json.dumps({k:result[k] for k in ('total_valid_numeric_observations','process_asdu_types','units','capture_headers','anchor_binary64_ulp_seconds')},indent=2))
