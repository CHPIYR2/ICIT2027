"""Label-blind APDU/segment duplicate equivalence audit, all primary captures."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import hashlib
import zipfile
from collections import Counter
from sherlock.io import ROOT,read_json,save_json,sha256,verify_protocol
from sherlock.parser import read_pcap,Deduplicator,decode_apdus


def audit_packets(packets, windows):
    segment=Deduplicator();flows={};counts=Counter();examples=[]
    for p in packets:
        counts['packets']+=1
        if p.ip_protocol!=6 or 2404 not in (p.sport,p.dport):continue
        repeated=segment.retransmission(p)
        flow=(p.src,p.sport,p.dst,p.dport)
        if p.flags&2:flows.pop(flow,None)
        if not p.payload:continue
        counts['payload_segments']+=1
        if repeated:counts['exact_segment_duplicates']+=1
        seen=flows.setdefault(flow,set())
        in_window=any(lo<=p.timestamp<hi for lo,hi in windows)
        for m in decode_apdus(p.payload):
            offset=m['offset'];size=p.payload[offset+1]+2
            key=((p.sequence+offset)%2**32,hashlib.sha256(p.payload[offset:offset+size]).digest())
            duplicate=key in seen
            if duplicate and not repeated:
                counts['extra_apdu_duplicates_outside_segment_dedup']+=1
                if in_window:counts['extra_apdu_duplicates_in_event_windows']+=1
                if len(examples)<10:examples.append({'packet_index':p.index,'time':p.timestamp,'offset':offset,'in_window':in_window})
            if repeated and not duplicate:raise ValueError('Segment duplicate missing prior APDU')
            seen.add(key);counts['apdus']+=1
    return {'counts':dict(counts),'examples':examples,
            'event_window_equivalent':counts['extra_apdu_duplicates_in_event_windows']==0}


def main():
    _,contract=verify_protocol()
    out=ROOT/'data/manifests/segmentation_audit.v1.json'
    if out.exists():raise SystemExit('Audit already exists; preserve it.')
    catalog=read_json(ROOT/'data/evaluator/event_catalog.json')['events']
    results=[]
    for a in read_json(ROOT/'data/manifests/sherlock_manifest.json')['archives']:
        scenario=a['filename'][:-4];path=ROOT/a['local_path']
        if sha256(path)!=a['sha256']:raise ValueError('Archive checksum mismatch')
        with zipfile.ZipFile(path) as z:
            for recording in sorted({e['recording'] for e in catalog if e['scenario']==scenario}):
                member=f"{scenario}/raw/{recording}/pcap/switch-{contract['primary_vantages'][scenario]}-pcap-mir2.pcap"
                windows=[(e['start']-60,e['start']+60) for e in catalog if e['scenario']==scenario and e['recording']==recording]
                with z.open(member) as stream:result=audit_packets(read_pcap(stream),windows)
                result.update(scenario=scenario,recording=recording,member=member,archive_sha256=a['sha256'])
                results.append(result);print(result,flush=True)
    save_json(out,{'scope':'Label-blind parsing/duplicate audit; no feature-label statistics or held-out predictions',
                   'script_sha256':sha256(Path(__file__)),'recordings':results,
                   'passed':all(r['event_window_equivalent'] for r in results)})

if __name__=='__main__':main()
