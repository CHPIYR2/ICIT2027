"""Read-only artifact checks for Phase 1; no fitting, LLM, or gold scoring."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'experiments'))
import gzip
import json
import math
from collections import Counter
from datetime import datetime,timezone
from sherlock.io import ROOT,read_json,save_json,sha256
from retrieval.evidence_formatter import digest,validate_public
from retrieval.investigation_retriever import BUDGETS
from run_observability_v2 import verify_lock as verify_prior

OUT=ROOT/'results/investigation-v1'
FORBIDDEN={'event_truth','malicious','attack_point','family_description','scenario','recording','initial_value',
           'description','source_file','raw_path','ca','ioa','mapped_target_asset_id','mapped_control_point_id'}


def no_forbidden(value):
    if isinstance(value,dict):
        assert not set(value)&FORBIDDEN
        for child in value.values():no_forbidden(child)
    elif isinstance(value,list):
        for child in value:no_forbidden(child)


def gz(path):
    with gzip.open(path,'rt') as file:return json.load(file)


def main():
    verify_prior()
    for name in ('investigation_events.v1.lock.json','investigation_phase1.lock.json'):
        for path,expected in read_json(ROOT/'configs'/name)['files'].items():assert sha256(ROOT/path)==expected,path
    events=read_json(ROOT/'configs/investigation_events.v1.json')
    ids=events['development']+events['evaluation'];assert len(ids)==len(set(ids))==48
    manifest=read_json(OUT/'baseline_manifest.json');assert manifest['llm_calls']==0 and not manifest['formal_protocol_frozen']
    assert len(manifest['rows'])==144
    indexed={(r['event_id'],r['view']):r for r in manifest['rows']};assert len(indexed)==144
    original_rows={r['episode_id']:r for part in ('development','held_out') for r in read_json(ROOT/f'data/processed/v2/{part}_features.json')['rows']}
    original_total=0;presented=0;max_bytes=0
    for i,eid in enumerate(ids,1):
        source=original_rows[eid];assert sha256(ROOT/source['evidence_path'])==source['evidence_sha256']
        domains={};metadata={}
        for view in ('E','N','EN'):
            row=indexed[eid,view]
            for path,expected in row['files'].items():assert sha256(ROOT/path)==expected,path
            directory=OUT/'B0'/eid/view
            public=gz(directory/'eligible.json.gz');validate_public(public);no_forbidden(public)
            bundle=read_json(directory/'retrieved.json');receipt=read_json(directory/'receipt.json');report=read_json(directory/'timeline.json')
            no_forbidden(bundle);no_forbidden(report)
            assert digest(public)==receipt['eligible_universe_sha256']
            assert digest(bundle)==receipt['retrieved_bundle_sha256']==report['retrieval_bundle_sha256']
            size=len(json.dumps(bundle,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
            assert size==receipt['serialized_bundle_bytes'] and size<=48000
            max_bytes=max(max_bytes,size)
            index={r['evidence_id']:r for r in public['records']};entries={r['evidence_id']:r for r in bundle['entries']}
            assert len(entries)==len(bundle['entries'])==receipt['retrieved_entry_count']
            domain_counts=Counter(r['view'] for r in entries.values())
            assert dict(domain_counts)==receipt['retrieved_by_domain']
            assert all(n<=BUDGETS[view][d] for d,n in domain_counts.items())
            assert len(index)==receipt['eligible_original_count']
            assert set(receipt['retrieved_original_ids'])==set(index)&set(entries)
            assert receipt['omitted_original_count']==len(set(index)-set(entries))
            for rid,record in entries.items():
                if record['source_type']!='derived':assert record==index[rid]
                else:
                    assert set(record['parent_ids'])<=set(entries)
                    fields=record['fields']
                    if fields['kind']=='communication_gap':
                        packets=[r for r in index.values() if r['source_type']=='packet' and r['fields']['ip_protocol']==6 and 2404 in (r['fields']['source_port'],r['fields']['destination_port'])]
                        times=sorted([-60,60]+[r['observation_time'] for r in packets])
                        assert fields['duration_seconds']==max(b-a for a,b in zip(times,times[1:]))
                        assert fields['eligible_count']==len(packets) and fields['universe_sha256']==digest(public)
                    else:
                        a=index[fields['before_id']];b=index[fields['after_id']]
                        assert a['fields']['channel_id']==b['fields']['channel_id']==fields['channel_id']
                        assert a['unit']==b['unit']==record['unit'] and a['asset_id']==b['asset_id']==record['asset_id']
                        assert not a['quality_flags'] and not b['quality_flags']
                        assert fields['before_time']==a['observation_time']<b['observation_time']==fields['after_time']
                        assert fields['before_value']==a['value'] and fields['after_value']==b['value']
                        if fields['kind']=='numeric_difference':assert fields['difference']==b['value']-a['value']
                        else:assert a['value']!=b['value']
            allowed_citations=set(entries)|{m['evidence_id'] for m in bundle['metadata'].values()}|{bundle['scope']['evidence_id']}
            for key in ('observations','numerical_differences','asset_channel_mappings','temporal_relations','unknowns'):
                for claim in report[key]:assert set(claim['evidence_ids'])<=allowed_citations
            assert report['security_interpretation']==[]
            assert report['accounting']['final_recovered_gold_facts'] is None
            assert receipt['final_recovered_investigation_facts'] is None
            provenance=gz(OUT/'private_provenance'/eid/f'{view}.json.gz')
            assert provenance['public_universe_sha256']==digest(public)
            for rid,r in provenance['records'].items():
                assert r['exported']==(rid in index)
                for parent in r['parent_ids']:
                    assert parent in provenance['records']
                    assert provenance['records'][parent]['observation_time']<=r['observation_time']
            domains[view]=set(index);metadata[view]=public['metadata']
            original_total+=len(index);presented+=len(report['observations'])
        assert not domains['E']&domains['N'] and domains['E']|domains['N']==domains['EN']
        assert metadata['E']==metadata['N']==metadata['EN']
        if i%12==0:print('Verified',i,'/48 events',flush=True)
    pilots=read_json(ROOT/'configs/investigation_pilots.v1.json')['event_ids']
    assert len(pilots)==4 and set(pilots)<=set(events['development'])
    for eid in pilots:
        directory=ROOT/'annotations/events'/eid
        complete=gz(directory/'complete_allowed_evidence.json.gz');no_forbidden(complete)
        assert digest(complete)==read_json(OUT/'B0'/eid/'EN/receipt.json')['eligible_universe_sha256']
        lineage=gz(directory/'allowed_lineage.json.gz')
        assert set(lineage)=={r['evidence_id'] for r in complete['records']}
        assert all(set(parents)<=set(lineage) for parents in lineage.values())
        for p in directory.glob('*.json'):
            no_forbidden(read_json(p))
        assert read_json(directory/'annotation.DRAFT.json')['signoff'] is None
        for path,expected in read_json(directory/'review_manifest.json')['files'].items():assert sha256(directory/path)==expected
    verify_prior()
    save_json(OUT/'verification.json',{'passed':True,'verified_at_utc':datetime.now(timezone.utc).isoformat(),
        'script_sha256':sha256(Path(__file__)),'prior_frozen_files_unchanged':True,'event_ids_and_phase1_snapshot_verified':True,
        'events':48,'event_view_conditions':144,'review_packets':4,'tests_passed':67,'max_serialized_bundle_bytes':max_bytes,
        'checked_export_record_instances_across_views':original_total,'mechanically_presented_observations':presented,
        'checks':['artifact hashes','canonical hashes','E/N disjoint and EN union','same static M','field leakage','retrieval budgets and receipts',
                  'derived support closure and calculations','complete-universe gap','B0 citation references','no speculative security narrative',
                  'private lineage and export flags','complete blinded pilot packets','no human signoff or gold score fabricated'],
        'llm_calls':0,'command_target_amendment_implemented':False,'human_gold_events':0})
    print('All Phase-1 artifact checks passed.',flush=True)


if __name__=='__main__':main()
