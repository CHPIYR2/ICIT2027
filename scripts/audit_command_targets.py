"""Private, read-only raw feasibility audit. Never used by investigation retrieval.

Only existing decoder-supported command layouts are examined. Command value and
qualifier bytes are skipped, never emitted; this is NOT a contract amendment.
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
import gzip
import json
import zipfile
from collections import Counter, defaultdict
from sherlock.io import ROOT, read_json, save_json, sha256, opaque
from sherlock.capture_v2 import read_pcap
from sherlock.parser import SIZES
from sherlock.parser_v2 import APDUDeduplicator
from sherlock.build_v2 import sanitize_mapping

OUT = ROOT/'results/investigation-v1/audit'


def command_addresses(payload, message):
    """Extract addresses only from a validated complete APDU; no control values."""
    start = message['offset']
    pdu = payload[start:start+payload[start+1]+2]
    if message['type'] not in range(45, 52):
        return []
    size = SIZES.get(message['type'])
    if size is None:
        raise ValueError('Command layout not audited by existing decoder')
    ca, count, sequential = int.from_bytes(pdu[10:12], 'little'), pdu[7]&127, bool(pdu[7]&128)
    pos, ioa, result = 12, None, []
    for index in range(count):
        if index == 0 or not sequential:
            if pos+3 > len(pdu):
                raise ValueError('Truncated command address')
            ioa = int.from_bytes(pdu[pos:pos+3], 'little')
            pos += 3
        else:
            ioa += 1
        if ioa > 0xffffff or pos+size > len(pdu):
            raise ValueError('Invalid address or command object length')
        result.append({'ca': ca, 'ioa': ioa, 'object_index': index})
        pos += size  # Do not decode or output setpoint/select/execute bytes.
    if pos != len(pdu):
        raise ValueError('Unexplained command bytes')
    return result


def main():
    dest = OUT/'command_target_feasibility.json'
    if dest.exists():
        raise ValueError('Audit already exists; do not overwrite')
    frozen = read_json(ROOT/'configs/investigation_events.v1.json')
    selected = set(frozen['development']+frozen['evaluation'])
    feature_rows = [r for part in ('development','held_out') for r in read_json(ROOT/f'data/processed/v2/{part}_features.json')['rows'] if r['episode_id'] in selected]
    scopes, expected = defaultdict(list), {}
    for row in feature_rows:
        assert sha256(ROOT/row['evidence_path']) == row['evidence_sha256']
        with gzip.open(ROOT/row['evidence_path'], 'rt') as f:
            episode = json.load(f)
        records = episode['evidence_records']
        source = records[0]['source_file']
        scopes[source].append((episode['anchor_time'], row['episode_id']))
        expected[row['episode_id']] = {r['evidence_id'] for r in records if r['source_type']=='message' and r['fields']['asdu_type'] in range(45,52)}
    archives = {a['sha256']: ROOT/a['local_path'] for a in read_json(ROOT/'data/manifests/sherlock_manifest.json')['archives']}
    sources = [s for p in ('development','held_out') for s in read_json(ROOT/f'data/manifests/{p}_source_resolver.v2.json')['sources']]
    objects, mapping_audits = [], []
    contract = read_json(ROOT/'configs/evidence_contract.v1.json')
    verified = set()
    for source in sources:
        sid = source['source_id']
        if sid not in scopes:
            continue
        archive = archives[source['archive_sha256']]
        if archive not in verified:
            if sha256(archive) != source['archive_sha256']:
                raise ValueError('Raw archive hash mismatch')
            verified.add(archive)
        windows = sorted(scopes[sid]); wi = 0
        with zipfile.ZipFile(archive) as z:
            duplicates = []
            def pairs(items):
                result = {}
                for key, value in items:
                    if key in result:
                        duplicates.append(key)
                    result[key] = value
                return result
            raw_mapping = z.read(source['mapping_member'])
            mapping = json.loads(raw_mapping, object_pairs_hook=pairs)
            if duplicates:
                raise ValueError('Ambiguous duplicate mapping keys')
            channels, existing_lookup = sanitize_mapping(mapping, contract, sid)
            by_semantics = defaultdict(list)
            for address, row in mapping.items():
                by_semantics[(row['element'],row['attribute'])].append((address,row['context']))
            collisions = [items for items in by_semantics.values() if len({context for _,context in items}) > 1]
            aliases = [items for items in by_semantics.values() if len(items)>1]
            audit = {'source_id':sid,'mapping_raw_sha256':__import__('hashlib').sha256(raw_mapping).hexdigest(),
                     'mapping_entries':len(mapping),'duplicate_keys':duplicates,
                     'same_element_attribute_multi_address_groups':len(aliases),
                     'configuration_measurement_same_attribute_groups':len(collisions),
                     'contexts':dict(Counter(r['context'] for r in mapping.values()))}
            mapping_audits.append(audit)
            dedup = APDUDeduplicator(); packet_count = 0
            with z.open(source['member']) as f:
                for packet in read_pcap(f):
                    packet_count += 1
                    while wi < len(windows) and packet.timestamp >= windows[wi][0]+60:
                        wi += 1
                    if wi == len(windows):
                        break
                    messages = dedup.messages(packet)
                    anchor, eid = windows[wi]
                    if packet.timestamp < anchor-60:
                        continue
                    pid = opaque('p_',sid+'|'+str(packet.index),24)
                    for message in messages:
                        if message['type'] not in range(45,52):
                            continue
                        mid = opaque('m_',pid+'|'+str(message['offset']),24)
                        if mid not in expected[eid]:
                            raise ValueError('Raw command does not match canonical evidence')
                        for obj in command_addresses(packet.payload,message):
                            address = f"{obj['ca']}.{obj['ioa']}"
                            match = mapping.get(address)
                            asset = opaque('asset_',sid+'|'+match['element']) if match else None
                            objects.append({'episode_id':eid,'command_evidence_id':mid,'packet_id':pid,'observation_time':packet.timestamp-anchor,
                                'asdu_type':message['type'],'cause_of_transmission':message['cot'],**obj,
                                'raw_static_mapping_available':match is not None,
                                'mapping_context':match['context'] if match else None,
                                'mapping_attribute':match['attribute'] if match else None,
                                'existing_measurement_lookup_available':address in existing_lookup,
                                'proposed_asset_id':asset,
                                'proposed_control_point_id':opaque('cp_',sid+'|'+address+'|'+match['context']) if match else None,
                                'same_asset_in_existing_E_metadata':asset in {v['asset_id'] for v in channels.values()} if match else False,
                                'status':'FEASIBILITY_ONLY_NOT_RUNTIME_EVIDENCE'})
            audit['packets_scanned'] = packet_count
            print('Audited',sid,'packets',packet_count,flush=True)
    per_event = []
    for eid in sorted(selected):
        obs = [o for o in objects if o['episode_id']==eid]
        if {o['command_evidence_id'] for o in obs} != expected[eid]:
            raise ValueError('Canonical/raw command coverage differs')
        requests = [o for o in obs if o['cause_of_transmission']==6]
        per_event.append({'episode_id':eid,'command_objects':len(obs),'activation_request_objects':len(requests),
                          'mapped_request_objects':sum(o['raw_static_mapping_available'] for o in requests),
                          'existing_measurement_lookup_requests':sum(o['existing_measurement_lookup_available'] for o in requests)})
    requests = [o for o in objects if o['cause_of_transmission']==6]
    save_json(dest, {'access':'PRIVATE_AUDIT_ONLY_NEVER_RETRIEVAL_OR_REVIEW_PACKET','contract_amendment_implemented':False,
        'event_manifest_sha256':sha256(ROOT/'configs/investigation_events.v1.json'),'candidate_events':len(selected),
        'events_with_requests':sum(r['activation_request_objects']>0 for r in per_event),
        'events_with_any_mapped_request':sum(r['mapped_request_objects']>0 for r in per_event),
        'events_with_all_requests_mapped':sum(r['activation_request_objects']>0 and r['mapped_request_objects']==r['activation_request_objects'] for r in per_event),
        'request_objects':len(requests),'mapped_request_objects':sum(r['raw_static_mapping_available'] for r in requests),
        'observed_command_types':dict(Counter(o['asdu_type'] for o in objects)),
        'not_empirically_audited_command_types':sorted(set(range(45,52))-{o['asdu_type'] for o in objects}),
        'mapping_audits':mapping_audits,'per_event':per_event,'objects':objects})
    print('Audit complete:',len(requests),'request objects;',sum(r['activation_request_objects']>0 for r in per_event),'events with requests',flush=True)


if __name__ == '__main__':
    main()
