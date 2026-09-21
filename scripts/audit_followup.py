#!/usr/bin/env python3
"""Resolve audit findings using targeted local samples; no model inputs."""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import struct
import zipfile

from audit_contents import ROOT, complete_apdus, ethernet_tcp, save


def packets(z, name):
    with z.open(name) as stream:
        header=stream.read(24)
        formats={b"\xd4\xc3\xb2\xa1":("<",1e6), b"\x4d\x3c\xb2\xa1":("<",1e9)}
        endian,scale=formats[header[:4]]
        n=0
        while h:=stream.read(16):
            sec,sub,size,orig=struct.unpack(endian+"IIII",h)
            data=stream.read(size)
            n+=1
            yield n,sec+sub/scale,data


def main():
    out={"scope":"targeted follow-up after full core scans", "findings":{}}
    with zipfile.ZipFile(ROOT/'data/raw/sherlock/v3/02-Semiurban.zip') as z:
        d={}
        for split in ('train','test'):
            initial=json.loads(z.read(f'02-Semiurban/ipal/{split}/initial_state.json'))
            with z.open(f'02-Semiurban/{split}.n406.state.gz') as raw,gzip.GzipFile(fileobj=raw) as stream:
                first=json.loads(stream.readline())
                diff=[k for k,v in first['state'].items() if initial.get(k)!=v]
                d[split]={"initial_fields":len(initial),"first_row_fields_equal_to_initial":len(initial)-len(diff),
                          "first_row_different_fields":diff}
                if split=='test':
                    for n,line in enumerate(stream,2):
                        row=json.loads(line)
                        if 'test' in row['state']:
                            d['test_field']={"first_row_index":n,"first_timestamp":row['timestamp'],"value":row['state']['test']}
                            break
        target=d['test_field']['first_timestamp']
        u=[]
        name='02-Semiurban/raw/test/pcap/switch-n406-pcap-mir2.pcap'
        for n,t,frame in packets(z,name):
            if t>target+1:break
            if t<target-2:continue
            kind,tcp=ethernet_tcp(frame)
            if tcp is None or 2404 not in (tcp['src_port'],tcp['dst_port']):continue
            pdus,_=complete_apdus(tcp['payload'])
            for pdu in pdus:
                if pdu[2] in (0x43,0x83):
                    u.append({"member":name,"packet_index":n,"timestamp":t,"apdu_hex":pdu.hex(),
                              "control_octet":f"0x{pdu[2]:02x}"})
        d['test_field']['nearby_testfr_apdus']=u
        out['findings']['semiurban_initialization_and_test_field']=d
    # Match flow/sequence/payload, excluding mutable IP TTL/checksums and Ethernet.
    # Samples demonstrate duplicated observations, not an exhaustive deduplication.
    with zipfile.ZipFile(ROOT/'data/raw/sherlock/v3/01-Basic.zip') as z:
        samples={}
        for name in z.namelist():
            if '/raw/train/pcap/' not in name or not name.endswith('.pcap'):continue
            s={}
            for n,t,frame in packets(z,name):
                _,tcp=ethernet_tcp(frame)
                if tcp is None or not tcp['payload'] or 2404 not in (tcp['src_port'],tcp['dst_port']):continue
                ip=tcp['ip_bytes'];transport=ip[(ip[0]&15)*4:]
                identity=ip[12:20]+transport[:12]+bytes([transport[13]])+tcp['payload']
                h=hashlib.sha256(identity).hexdigest()
                s.setdefault(h,{"packet_index":n,"timestamp":t})
                if len(s)>=2000:break
            samples[name]=s
        matches=[]
        keys=list(samples)
        for i,a in enumerate(keys):
            for b in keys[i+1:]:
                common=samples[a].keys() & samples[b].keys()
                if common:
                    h=sorted(common)[0]
                    matches.append({"left":a,"right":b,"matching_sample_identities":len(common),
                                    "identity_sha256":h,"left_reference":samples[a][h],"right_reference":samples[b][h]})
        out['findings']['cross_vantage']={"sample_limit_per_capture":2000,
                                        "identity_fields":"src/dst IP, TCP ports/seq/ack/flags, payload; TTL/checksums/MAC excluded",
                                        "matches":matches}
    out['source_hashes']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'docs/sources').glob('*.txt')}
    out['source_note']='Current upstream source is corroborative; exact historical release transcriber commit remains unknown.'
    save(ROOT/'data/manifests/content_audit/followup.json',out)
    print(json.dumps(out,indent=2))


if __name__=='__main__':main()
