"""Reparse frozen primary captures into investigation-only command child evidence."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import gzip
import json
import zipfile
from collections import defaultdict,Counter
from sherlock.io import ROOT,read_json,save_json,sha256,opaque
from sherlock.capture_v2 import read_pcap
from sherlock.parser_v2 import APDUDeduplicator
from evidence.command_address_v2 import static_mapping,address_children,OBJECT_BYTES


def main():
    out=ROOT/'results/investigation-v2'
    if (out/'command_addresses/manifest.json').exists():raise ValueError('Preserve completed address build')
    frozen=read_json(ROOT/'configs/investigation_events.v1.json')
    selected=set(frozen['development']+frozen['evaluation'])
    scopes=defaultdict(list);expected={};sidecars={};private={}
    for part in ('development','held_out'):
        for row in read_json(ROOT/f'data/processed/v2/{part}_features.json')['rows']:
            eid=row['episode_id']
            if eid not in selected:continue
            assert sha256(ROOT/row['evidence_path'])==row['evidence_sha256']
            with gzip.open(ROOT/row['evidence_path'],'rt') as f:episode=json.load(f)
            sid=episode['evidence_records'][0]['source_file']
            scopes[sid].append((episode['anchor_time'],eid))
            expected[eid]={r['evidence_id'] for r in episode['evidence_records'] if r['source_type']=='message' and r['fields']['asdu_type'] in OBJECT_BYTES}
            sidecars[eid]={'schema_version':'investigation-command-address-v2','event_id':eid,'records':[]}
            private[eid]={}
    archives={a['sha256']:ROOT/a['local_path'] for a in read_json(ROOT/'data/manifests/sherlock_manifest.json')['archives']}
    sources=[s for p in ('development','held_out') for s in read_json(ROOT/f'data/manifests/{p}_source_resolver.v2.json')['sources']]
    verified=set();source_audits=[]
    for source in sources:
        sid=source['source_id']
        if sid not in scopes:continue
        archive=archives[source['archive_sha256']]
        if archive not in verified:
            assert sha256(archive)==source['archive_sha256'];verified.add(archive)
        windows=sorted(scopes[sid]);wi=0;dedup=APDUDeduplicator()
        with zipfile.ZipFile(archive) as z:
            mapping=static_mapping(z.read(source['mapping_member']),sid)
            for _,eid in windows:
                save_json(out/'command_addresses'/f'{eid}.metadata.json',mapping['public_metadata'])
            with z.open(source['member']) as f:
                for packet in read_pcap(f):
                    while wi<len(windows) and packet.timestamp>=windows[wi][0]+60:wi+=1
                    if wi==len(windows):break
                    messages=dedup.messages(packet)
                    # Support overlapping windows without resetting stream deduplication.
                    active=[(anchor,eid) for anchor,eid in windows[wi:] if anchor-60<=packet.timestamp<anchor+60]
                    for anchor,eid in active:
                        pid=opaque('p_',sid+'|'+str(packet.index),24)
                        for msg in messages:
                            if msg['type'] not in OBJECT_BYTES:continue
                            mid=opaque('m_',pid+'|'+str(msg['offset']),24)
                            if mid not in expected[eid]:raise ValueError('Raw/canonical command mismatch')
                            message={'evidence_id':mid,'asdu_type':msg['type'],'cause_of_transmission':msg['cot'],'observation_time':packet.timestamp-anchor}
                            children,provenance=address_children(message,packet.payload,msg['offset'],mapping)
                            sidecars[eid]['records'].extend(children);private[eid].update(provenance)
            source_audits.append({'source_id':sid,'mapping_sha256':mapping['mapping_sha256'],'packets_scanned':packet.index,
                'public_mapping_count':len(mapping['public_metadata']),'mapping_status_counts':dict(Counter(v['status'] for v in mapping['private_address_lookup'].values()))})
            print('Reparsed',sid,flush=True)
    for eid,sidecar in sidecars.items():
        if {r['parent_ids'][0] for r in sidecar['records']}!=expected[eid]:raise ValueError('Incomplete command coverage')
        if len({r['evidence_id'] for r in sidecar['records']})!=len(sidecar['records']):raise ValueError('Duplicate child IDs')
        save_json(out/'command_addresses'/f'{eid}.json',sidecar)
        save_json(out/'private_provenance'/f'{eid}.addresses.json',private[eid])
    all_records=[r for s in sidecars.values() for r in s['records']]
    save_json(out/'command_addresses/manifest.json',{'schema_version':'investigation-command-address-v2','events':len(sidecars),
        'children':len(all_records),'request_children':sum(r['cause_of_transmission']==6 for r in all_records),
        'status_counts':dict(Counter(r['mapping_status'] for r in all_records)),
        'types':dict(Counter(r['asdu_type'] for r in all_records)),'sources':source_audits,
        'files':{str(p.relative_to(ROOT)):sha256(p) for folder in ('command_addresses','private_provenance') for p in (out/folder).glob('*.json')}})


if __name__=='__main__':main()
