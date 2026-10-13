"""Bounded data-quality audit for one Sherlock Basic train window.

Streams ZIP members. Does not extract archives, does not open physical.zip,
and does not pass event descriptions into features.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import gzip
import hashlib
import ipaddress
import json
import math
import struct
import zipfile
from pathlib import Path

import numpy as np

from mirage_ot.archive import inspect_archive, load_selected
from mirage_ot.pcap import iter_pcap


def iso(ts: float) -> str:
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc).isoformat()


def _timestamp_prefix(line: bytes) -> float | None:
    key = b'"timestamp":'
    i = line.find(key)
    if i < 0:
        return None
    j = line.find(b',', i + len(key))
    if j < 0:
        return None
    return float(line[i + len(key):j])


def load_point_map(archive: Path) -> dict[tuple[str, str], list[str]]:
    contexts: dict[tuple[str, str], list[str]] = collections.defaultdict(list)
    with zipfile.ZipFile(archive) as zf:
        raw = json.loads(zf.read('01-Basic/raw/train/data-point-map.json'))
    for point in raw.values():
        contexts[(point['element'], point['attribute'])].append(point['context'])
    return contexts


def audit_state(archive: Path, member: str, start: float, end: float,
                contexts: dict[tuple[str, str], list[str]]) -> dict:
    rows = 0
    numeric = bools = non_numeric = 0
    context_counts: collections.Counter[str] = collections.Counter()
    unknown_keys: list[str] = []
    collisions: list[str] = []
    alias_pairs = 0
    alias_mismatch = 0
    samples = []
    seen_keys: set[str] = set()
    with zipfile.ZipFile(archive) as zf, zf.open(member) as raw, gzip.GzipFile(fileobj=raw) as gz:
        for line in gz:
            if not line.strip():
                continue
            ts = _timestamp_prefix(line)
            if ts is None:
                raise ValueError('State row has no timestamp prefix')
            if ts < start or ts >= end:
                continue
            row = json.loads(line)
            state = row['state']
            rows += 1
            if len(samples) < 2:
                samples.append({'timestamp': ts, 'iso': iso(ts), 'n_keys': len(state),
                                'bus.0:voltage': state.get('bus.0:voltage'),
                                'sgen.0:active_power': state.get('sgen.0:active_power'),
                                'sgen.0:target_active_power': state.get('sgen.0:target_active_power'),
                                'switch.8:closed': state.get('switch.8:closed'),
                                'switch.8:is_closed': state.get('switch.8:is_closed')})
            for key, value in state.items():
                if isinstance(value, bool):
                    bools += 1
                elif isinstance(value, (int, float)) and math.isfinite(float(value)):
                    numeric += 1
                else:
                    non_numeric += 1
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                element, _, attr = key.partition(':')
                ctx = contexts.get((element, attr), [])
                if not ctx:
                    unknown_keys.append(key)
                    context_counts['UNMAPPED'] += 1
                elif len(set(ctx)) > 1:
                    collisions.append(key)
                    context_counts['COLLISION'] += 1
                else:
                    context_counts[ctx[0]] += 1
            aliases = collections.defaultdict(dict)
            for key, value in state.items():
                if key.endswith(':is_closed'):
                    aliases[key[: -len(':is_closed')]]['is_closed'] = value
                elif key.endswith(':closed'):
                    aliases[key[: -len(':closed')]]['closed'] = value
                elif key.endswith(':is_connected'):
                    aliases[key[: -len(':is_connected')]]['is_connected'] = value
                elif key.endswith(':connected'):
                    aliases[key[: -len(':connected')]]['connected'] = value
            for pair in aliases.values():
                if 'closed' in pair and 'is_closed' in pair:
                    alias_pairs += 1
                    alias_mismatch += int(bool(pair['closed']) != bool(pair['is_closed']))
                if 'connected' in pair and 'is_connected' in pair:
                    alias_pairs += 1
                    alias_mismatch += int(bool(pair['connected']) != bool(pair['is_connected']))
    return {
        'member': member,
        'rows_in_window': rows,
        'unique_keys': len(seen_keys),
        'value_tokens': {'finite_number': numeric, 'bool': bools, 'other': non_numeric},
        'key_context_counts': dict(context_counts),
        'context_collisions': collisions,
        'unmapped_keys': unknown_keys[:20],
        'unmapped_key_count': len(unknown_keys),
        'alias_pairs': alias_pairs,
        'alias_mismatches': alias_mismatch,
        'samples': samples,
        'separation': (
            'MEASUREMENT and CONFIGURATION are different state keys when their '
            'attributes differ. tap_position can collide onto one key. '
            'closed/is_closed and connected/is_connected are duplicate aliases.'
        ),
    }


def _packet_view(blob: bytes) -> tuple[str, tuple | None]:
    if len(blob) < 14:
        return 'short_frame', None
    ethertype = int.from_bytes(blob[12:14], 'big')
    pos = 14
    if ethertype in (0x8100, 0x88A8) and len(blob) >= pos + 4:
        ethertype = int.from_bytes(blob[pos + 2:pos + 4], 'big')
        pos += 4
    if ethertype == 0x0806:
        return 'arp', None
    if ethertype != 0x0800 or len(blob) < pos + 20:
        return f'ethertype_{ethertype:#06x}', None
    pkt = blob[pos:]
    version = pkt[0] >> 4
    ihl = (pkt[0] & 15) * 4
    if version != 4 or ihl < 20 or len(pkt) < ihl:
        return 'bad_ipv4', None
    proto = pkt[9]
    src = str(ipaddress.IPv4Address(pkt[12:16]))
    dst = str(ipaddress.IPv4Address(pkt[16:20]))
    transport = pkt[ihl:]
    if proto == 6 and len(transport) >= 4:
        sport, dport = struct.unpack('>HH', transport[:4])
        kind = 'tcp_iec104_port' if sport == 2404 or dport == 2404 else 'tcp_other'
        return kind, (src, sport, dst, dport, 'TCP')
    if proto == 17 and len(transport) >= 4:
        sport, dport = struct.unpack('>HH', transport[:4])
        return 'udp', (src, sport, dst, dport, 'UDP')
    return f'ip_proto_{proto}', None


def scan_pcap(archive: Path, member: str, start: float, end: float) -> dict:
    counts: collections.Counter[str] = collections.Counter()
    flows: set[tuple] = set()
    fingerprints: set[tuple[int, str]] = set()
    yielded = collections.Counter()
    with zipfile.ZipFile(archive) as zf, zf.open(member) as handle:
        header = handle.read(24)
        magic = header[:4]
        if magic != b'\xd4\xc3\xb2\xa1':
            raise RuntimeError(f'Unexpected PCAP magic {magic.hex()} in {member}')
        linktype = struct.unpack('<I', header[20:24])[0]
        rec = struct.Struct('<IIII')
        while True:
            raw = handle.read(16)
            if not raw:
                break
            secs, sub, incl, _orig = rec.unpack(raw)
            blob = handle.read(incl)
            ts = secs + sub / 1_000_000
            if ts < start or ts >= end:
                continue
            kind, flow = _packet_view(blob)
            counts[kind] += 1
            if flow:
                flows.add(flow)
            fingerprints.add((int(round(ts * 1_000_000)), hashlib.sha1(blob).hexdigest()))
    source = f'{archive.name}:{member}'
    with zipfile.ZipFile(archive) as zf, zf.open(member) as handle:
        for obs in iter_pcap(handle, source=source, start=start, end=end):
            yielded[obs.kind] += 1
            if obs.attrs and obs.attrs.get('iec104_candidate'):
                yielded['iec104_candidate_flag'] += 1
    packets = sum(counts.values())
    parser_yielded = sum(yielded[k] for k in ('tcp_packet', 'udp_packet', 'arp_packet'))
    return {
        'member': member,
        'linktype': linktype,
        'magic': 'd4c3b2a1',
        'packets_in_window': packets,
        'independent_classes': dict(counts),
        'unique_flows': len(flows),
        'parser_yielded': dict(yielded),
        'parser_yield_rate': (parser_yielded / packets) if packets else None,
        'packets_not_emitted_by_parser': packets - parser_yielded,
        'iec104_semantic_decode': False,
        'fingerprints': fingerprints,
        'flows': flows,
    }


def compare_matrix(matrix_path: Path, archive: Path, state_member: str,
                   pcap_member: str, start: float, end: float) -> dict:
    with np.load(matrix_path, allow_pickle=False) as arr:
        data = arr['data']
    meta = json.loads(matrix_path.with_suffix('.json').read_text(encoding='utf-8'))
    beginning = float(meta['start'])
    bin_seconds = float(meta['bin_seconds'])
    nodes = meta['nodes']
    index = {node['entity']: i for i, node in enumerate(nodes)}
    forbidden = ('industroyer', 'arp-spoof', 'attack', 'Cable Maintenance', 'benign event')
    blob = json.dumps(meta)
    leaked = [word for word in forbidden if word in blob]

    wanted = ['bus.0:voltage', 'sgen.0:active_power', 'sgen.0:target_active_power',
              'switch.8:closed', 'switch.8:is_closed']
    sums = {key: collections.defaultdict(float) for key in wanted}
    ns = {key: collections.defaultdict(int) for key in wanted}
    with zipfile.ZipFile(archive) as zf, zf.open(state_member) as raw, gzip.GzipFile(fileobj=raw) as gz:
        for line in gz:
            ts = _timestamp_prefix(line)
            if ts is None or ts < start or ts >= end:
                continue
            row = json.loads(line)
            state = row['state']
            bin_id = int((ts - beginning) // bin_seconds)
            if not 0 <= bin_id < data.shape[0]:
                continue
            for key in wanted:
                if key not in state or key not in index:
                    continue
                value = state[key]
                value = float(value) if not isinstance(value, bool) else float(value)
                sums[key][bin_id] += value
                ns[key][bin_id] += 1
    checks = []
    for key in wanted:
        if key not in index or not ns[key]:
            checks.append({'entity': key, 'present_in_matrix': key in index})
            continue
        bin_id = sorted(ns[key])[len(ns[key]) // 2]
        expected = sums[key][bin_id] / ns[key][bin_id]
        got = float(data[bin_id, index[key], 0])
        checks.append({
            'entity': key,
            'bin_index': bin_id,
            'raw_samples': ns[key][bin_id],
            'raw_mean': expected,
            'matrix_mean': got,
            'abs_delta': abs(expected - got),
            'matches_float32': abs(expected - got) <= 1e-4 * max(1.0, abs(expected)),
        })
    modalities = collections.Counter(node['modality'] for node in nodes)
    return {
        'matrix': str(matrix_path),
        'shape': list(data.shape),
        'window_start': beginning,
        'window_end': beginning + data.shape[0] * bin_seconds,
        'node_counts': dict(modalities),
        'dropped_channel_counts': meta['metadata'].get('dropped_channel_counts'),
        'label_strings_found_in_sidecar': leaked,
        'physical_trust_note': meta['metadata'].get('note'),
        'raw_versus_matrix': checks,
        'pcap_member_used_for_this_matrix': pcap_member,
    }


def physical_zip_is_blocked(archive: Path) -> dict:
    member = '01-Basic/raw/train/physical.zip'
    try:
        next(load_selected(archive, state_member=member, pcap_members=[], start=None, end=None))
    except ValueError as exc:
        return {'member': member, 'blocked': True, 'error': str(exc)}
    except StopIteration:
        return {'member': member, 'blocked': False, 'error': 'iterator produced no error'}
    return {'member': member, 'blocked': False, 'error': 'member was readable'}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--state-member', required=True)
    parser.add_argument('--pcap-member', action='append', required=True)
    parser.add_argument('--start', type=float, required=True)
    parser.add_argument('--end', type=float, required=True)
    parser.add_argument('--matrix', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    contexts = load_point_map(args.archive)
    scans = [scan_pcap(args.archive, member, args.start, args.end) for member in args.pcap_member]
    primary, *others = scans
    def undirected(flow: tuple) -> tuple:
        src, sport, dst, dport, proto = flow
        ends = tuple(sorted(((src, sport), (dst, dport))))
        return (*ends, proto)

    overlap = []
    for other in others:
        shared = primary['fingerprints'] & other['fingerprints']
        shared_flows = primary['flows'] & other['flows']
        shared_undirected = {undirected(flow) for flow in primary['flows']} & {
            undirected(flow) for flow in other['flows']}
        overlap.append({
            'other_member': other['member'],
            'shared_timestamp_payload_fingerprints': len(shared),
            'shared_directed_flows': len(shared_flows),
            'shared_undirected_flows': len(shared_undirected),
            'primary_packets': primary['packets_in_window'],
            'other_packets': other['packets_in_window'],
            'primary_flows': len(primary['flows']),
            'other_flows': len(other['flows']),
        })
    for scan in scans:
        scan.pop('fingerprints')
        scan.pop('flows')
    report = {
        'generated_for': 'pipeline check only; not a paper metric',
        'archive': inspect_archive(args.archive),
        'window': {'start': args.start, 'end': args.end, 'start_iso': iso(args.start),
                   'end_iso': iso(args.end)},
        'physical_zip': physical_zip_is_blocked(args.archive),
        'state': audit_state(args.archive, args.state_member, args.start, args.end, contexts),
        'pcap': scans,
        'cross_vantage_exact_duplicates': overlap,
        'matrix_check': (
            compare_matrix(args.matrix, args.archive, args.state_member, args.pcap_member[0],
                           args.start, args.end)
            if args.matrix else None
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({
        'out': str(args.out),
        'state_rows': report['state']['rows_in_window'],
        'state_keys': report['state']['unique_keys'],
        'alias_mismatches': report['state']['alias_mismatches'],
        'context_collisions': report['state']['context_collisions'],
        'primary_parser_yield_rate': primary['parser_yield_rate'],
        'primary_not_emitted': primary['packets_not_emitted_by_parser'],
        'matrix_deltas': None if not report['matrix_check'] else [
            {'entity': item.get('entity'), 'abs_delta': item.get('abs_delta'),
             'matches_float32': item.get('matches_float32')}
            for item in report['matrix_check']['raw_versus_matrix']
        ],
    }, indent=2))


if __name__ == '__main__':
    main()
