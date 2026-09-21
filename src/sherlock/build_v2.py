"""Offline builder: event metadata is projected to ID/start before decoding."""
import argparse
import gzip
import json
import zipfile
from collections import Counter

from evidence.schema import EvidenceEpisode, EvidenceRecord
from features.extract import extract
from sherlock.io import ROOT, opaque, read_json, save_json, sha256, verify_protocol
from sherlock.capture_v2 import read_pcap
from sherlock.parser_v2 import APDUDeduplicator


def sanitize_mapping(mapping, contract, source_id):
    channels, lookup = {}, {}
    for address, row in mapping.items():
        family = next((f for f, attrs in contract['E']['attribute_families'].items() if row['attribute'] in attrs), None)
        if family is None or row['context'] != 'MEASUREMENT' or row['unit'] != contract['E']['units'][family]:
            continue
        if row['scale'] not in ('BASE','NONE'):
            raise ValueError('Unaudited unit scale')
        channel = opaque('ch_', source_id+'|'+address)
        metadata = {'asset_id': opaque('asset_',source_id+'|'+row['element']), 'family':family,
                    **{k: row[k] for k in ('attribute','context','unit','scale')}}
        channels[channel] = metadata
        lookup[address] = (channel, metadata)
    return channels, lookup


def build_recording(archive, member, mapping_member, archive_hash, vantage, scopes, contract, destination):
    """scopes contains ONLY opaque episode_id/start; never labels/end/attack_point."""
    source_id = opaque('src_',archive_hash+'|'+member,20)
    vantage_id = opaque('vp_',source_id+'|'+vantage)
    with zipfile.ZipFile(archive) as z:
        channels, lookup = sanitize_mapping(json.loads(z.read(mapping_member)), contract, source_id)
        scopes = sorted(scopes, key=lambda s:s['start'])
        if any(b['start']-a['start']<120 for a,b in zip(scopes,scopes[1:])):
            raise ValueError('Overlapping episode windows require grouping')
        assets = sorted({m['asset_id'] for m in channels.values()})
        iterator = iter(scopes)
        current = next(iterator,None)
        records, rows, counts = [], [], Counter()
        dedup = APDUDeduplicator()

        def finish():
            if not records:
                raise ValueError('No captured evidence in episode')
            t0 = current['start']
            episode = EvidenceEpisode(current['episode_id'],assets,(t0-60,t0+60),t0,records,channels).validate()
            path = destination/'episodes'/f"{episode.episode_id}.json.gz"
            path.parent.mkdir(parents=True,exist_ok=True)
            # Deterministic gzip header; identical input yields identical artifact hashes.
            with path.open('wb') as raw, gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0,compresslevel=3) as f:
                f.write(json.dumps(episode.to_dict(),separators=(',',':'),allow_nan=False).encode())
            values = extract(episode)
            rows.append({'episode_id':episode.episode_id,'values':values,
                         'evidence_sha256':sha256(path),'evidence_records':len(records),
                         'evidence_path':str(path.relative_to(ROOT))})
            print(json.dumps({'episode':episode.episode_id,'records':len(records),'missing_features':sum(v is None for v in values.values())}),flush=True)

        with z.open(member) as stream:
            first_time, last_time = None, None
            for p in read_pcap(stream,stats=counts):
                first_time = p.timestamp if first_time is None else first_time
                last_time = p.timestamp
                counts['packets_scanned'] += 1
                iec = p.ip_protocol == 6 and 2404 in (p.sport,p.dport)
                while current and p.timestamp >= current['start']+60:
                    if first_time > current['start']-60:
                        raise ValueError('Incomplete pre-event capture')
                    finish();records=[];current=next(iterator,None)
                if current is None:
                    break
                messages = dedup.messages(p)
                counts['duplicate_apdus'] += dedup.duplicates
                if p.timestamp < current['start']-60:
                    continue
                counts['duplicate_apdus_in_windows'] += dedup.duplicates
                base = {'asset_id':None,'observation_time':p.timestamp,'reported_time':None,'value':None,'unit':None,
                        'source_file':source_id,'vantage_point':vantage_id,'quality_flags':(),
                        'transformation':'pcap-iec104-v1','view':'N'}
                packet_id = opaque('p_',source_id+'|'+str(p.index),24)
                records.append(EvidenceRecord(evidence_id=packet_id,source_type='packet',protocol='TCP' if p.ip_protocol==6 else 'OTHER',parent_ids=(),
                    fields={'ip_protocol':p.ip_protocol,'source_endpoint':opaque('ep_',source_id+'|'+p.src) if p.src else None,
                            'destination_endpoint':opaque('ep_',source_id+'|'+p.dst) if p.dst else None,
                            'source_port':p.sport,'destination_port':p.dport,'tcp_flags':p.flags,'packet_length':p.length},**base))
                if not messages:
                    continue
                for message in messages:
                    mid = opaque('m_',packet_id+'|'+str(message['offset']),24)
                    records.append(EvidenceRecord(evidence_id=mid,source_type='message',protocol='IEC104',parent_ids=(packet_id,),
                        fields={'apci_format':message['format'],'asdu_type':message['type'],'cause_of_transmission':message['cot']},**base))
                    for obj in message['objects']:
                        if obj['ca_ioa'] not in lookup: continue
                        channel, meta = lookup[obj['ca_ioa']]
                        if (meta['family']=='reported_state') != (message['type']==1):
                            raise ValueError('Mapping/ASDU type mismatch')
                        eid = opaque('e_',mid+'|'+str(obj['offset']),24)
                        records.append(EvidenceRecord(evidence_id=eid,source_type='process',protocol='IEC104',parent_ids=(mid,),
                            fields={'channel_id':channel,**{k:meta[k] for k in ('family','attribute','context')}},
                            **{**base,'asset_id':meta['asset_id'],'value':obj['value'],'unit':meta['unit'],
                               'quality_flags':tuple(obj['quality'])+base['quality_flags'],'view':'E'}))
            if current is not None:
                raise ValueError(f'Capture ends before decision cutoff: {last_time}')
    return rows, {'source_id':source_id,'archive_sha256':archive_hash,'member':member,
                  'mapping_member':mapping_member,'mapping_sha256':__import__('hashlib').sha256(json.dumps(channels,sort_keys=True).encode()).hexdigest(),
                  'vantage':vantage,'counts':dict(counts)}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--partition',choices=['development','held_out'],default='development')
    args=parser.parse_args()
    split, contract = verify_protocol()
    if args.partition == 'held_out':
        raise SystemExit('Held-out construction is intentionally gated until development validation and experiment lock are complete.')
    catalog = read_json(ROOT/'data/evaluator/event_catalog.json')['events']
    selected = set(split[args.partition])
    archives = read_json(ROOT/'data/manifests/sherlock_manifest.json')['archives']
    rows, sources = [], []
    destination = ROOT/'data/processed/v2'
    for archive in archives:
        scenario = archive['filename'][:-4]
        events = [e for e in catalog if e['episode_id'] in selected and e['scenario']==scenario]
        if not events: continue
        path = ROOT/archive['local_path']
        if sha256(path) != archive['sha256']:
            raise ValueError('Archive no longer matches frozen dataset')
        for recording in sorted({e['recording'] for e in events}):
            vantage = contract['primary_vantages'][scenario]
            scopes = [{k:e[k] for k in ('episode_id','start')} for e in events if e['recording']==recording]
            new_rows, source = build_recording(path,f'{scenario}/raw/{recording}/pcap/switch-{vantage}-pcap-mir2.pcap',
                f'{scenario}/raw/{recording}/data-point-map.json',archive['sha256'],vantage,scopes,contract,destination)
            rows.extend(new_rows);sources.append(source)
    if {r['episode_id'] for r in rows} != selected:
        raise ValueError('Partition coverage mismatch')
    save_json(destination/f'{args.partition}_features.json',{'recipe':'features-v1+apdu-dedup-v2','rows':sorted(rows,key=lambda r:r['episode_id'])})
    save_json(ROOT/f'data/manifests/{args.partition}_source_resolver.v2.json',{'access':'PRIVATE_LOADER_ONLY; never model input','sources':sources})


if __name__=='__main__':main()
