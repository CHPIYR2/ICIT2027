"""Small stdlib PCAP decoder for smoke tests and conservative network features.

Supports classic PCAP, Ethernet, IPv4, TCP and ARP. Does NOT perform TCP
reassembly, PCAPNG decode, IP fragmentation assembly, or full IEC104 ASDU decode.
For paper-quality protocol analysis replace with a validated transcriber and test
cross vantage point duplicate packets. Parser limitations are always reported.
"""
import gzip
import hashlib
import io
import ipaddress
import struct
from pathlib import Path
from typing import Iterator
from .types import Observation


class UnsupportedCapture(ValueError):
    pass


def _mac(b: bytes) -> str:
    return ':'.join(f'{x:02x}' for x in b)


def iter_pcap(handle, *, source: str, start: float | None = None,
              end: float | None = None, max_packets: int | None = None) -> Iterator[Observation]:
    if source.endswith('.gz'):
        handle = gzip.GzipFile(fileobj=handle)
    hdr = handle.read(24)
    if len(hdr) != 24:
        raise UnsupportedCapture('Truncated PCAP header')
    magic = hdr[:4]
    formats = {b'\xd4\xc3\xb2\xa1': ('<', 1e6),
               b'\xa1\xb2\xc3\xd4': ('>', 1e6),
               b'\x4d\x3c\xb2\xa1': ('<', 1e9),
               b'\xa1\xb2\x3c\x4d': ('>', 1e9)}
    if magic not in formats:
        raise UnsupportedCapture('Only classic PCAP is supported, not PCAPNG')
    endian, units = formats[magic]
    linktype = struct.unpack(endian + 'I', hdr[20:24])[0]
    if linktype != 1:
        raise UnsupportedCapture(f'Unsupported linktype {linktype} (need Ethernet=1)')
    pkt_header = struct.Struct(endian + 'IIII')
    count = 0
    while True:
        raw_hdr = handle.read(16)
        if not raw_hdr:
            break
        if len(raw_hdr) != 16:
            raise UnsupportedCapture('Truncated packet record')
        secs, subsec, incl, orig = pkt_header.unpack(raw_hdr)
        if incl > 64 * 1024 * 1024:
            raise UnsupportedCapture(f'Unreasonable captured packet length {incl}')
        blob = handle.read(incl)
        if len(blob) != incl:
            raise UnsupportedCapture('Truncated packet payload')
        count += 1
        if max_packets is not None and count > max_packets:
            break
        t = secs + subsec / units
        if (start is not None and t < start) or (end is not None and t >= end):
            continue
        if len(blob) < 14:
            continue
        etype = int.from_bytes(blob[12:14], 'big')
        pos = 14
        for _ in range(2):
            if etype in (0x8100, 0x88a8) and len(blob) >= pos + 4:
                etype = int.from_bytes(blob[pos + 2:pos + 4], 'big')
                pos += 4
        packet_id = f'{source}#packet={count}'
        if etype == 0x0806 and len(blob) >= pos + 28:
            op = int.from_bytes(blob[pos + 6:pos + 8], 'big')
            sha = _mac(blob[pos + 8:pos + 14])
            spa = str(ipaddress.IPv4Address(blob[pos + 14:pos + 18]))
            tpa = str(ipaddress.IPv4Address(blob[pos + 24:pos + 28]))
            entity = f'{spa}->{tpa}/ARP'
            yield Observation(t, 'network', entity, 'arp_packet', 1.0, packet_id,
                              {'op': op, 'src_mac': sha, 'ethertype': '0x0806',
                               'source_ip': spa, 'destination_ip': tpa,
                               'frame_sha256': hashlib.sha256(blob).hexdigest()})
        elif etype == 0x0800 and len(blob) >= pos + 20:
            pkt = blob[pos:]
            ver = pkt[0] >> 4
            ihl = (pkt[0] & 15) * 4
            if ver != 4 or ihl < 20 or len(pkt) < ihl:
                continue
            proto = pkt[9]
            src = str(ipaddress.IPv4Address(pkt[12:16]))
            dst = str(ipaddress.IPv4Address(pkt[16:20]))
            transport = pkt[ihl:]
            if proto == 6 and len(transport) >= 20:
                sport, dport = struct.unpack('>HH', transport[:4])
                offset = (transport[12] >> 4) * 4
                if offset < 20 or len(transport) < offset:
                    continue
                flags = transport[13]
                seq = int.from_bytes(transport[4:8], 'big')
                payload = transport[offset:]
                entity = f'{src}:{sport}->{dst}:{dport}/TCP'
                yield Observation(t, 'network', entity, 'tcp_packet', float(incl), packet_id,
                                  {'tcp_flags': flags, 'tcp_seq': seq, 'payload_bytes': len(payload),
                                   'iec104_candidate': int(sport == 2404 or dport == 2404),
                                   'source_ip': src, 'destination_ip': dst,
                                   'source_port': sport, 'destination_port': dport,
                                   'frame_sha256': hashlib.sha256(blob).hexdigest()})
            elif proto == 17 and len(transport) >= 8:
                sport, dport = struct.unpack('>HH', transport[:4])
                entity = f'{src}:{sport}->{dst}:{dport}/UDP'
                yield Observation(t, 'network', entity, 'udp_packet', float(incl), packet_id,
                                  {'source_ip': src, 'destination_ip': dst})


def read_pcap(path: Path, **kwargs) -> Iterator[Observation]:
    with path.open('rb') as f:
        yield from iter_pcap(f, source=path.name, **kwargs)
