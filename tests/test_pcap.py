import io
import ipaddress
import struct
from mirage_ot.pcap import iter_pcap, UnsupportedCapture


def _arp_packet():
    eth = bytes.fromhex('ffffffffffff0011223344550806')
    arp = (struct.pack('!HHBBH',1,0x0800,6,4,1) + bytes.fromhex('001122334455')
           + ipaddress.IPv4Address('192.0.2.1').packed + bytes(6)
           + ipaddress.IPv4Address('192.0.2.2').packed)
    return eth+arp


def test_decode_arp():
    blob = _arp_packet()
    header = bytes.fromhex('d4c3b2a1') + struct.pack('<HHIIII',2,4,0,0,65535,1)
    rec = struct.pack('<IIII',1700000000,500000,len(blob),len(blob))+blob
    events = list(iter_pcap(io.BytesIO(header+rec), source='test.pcap'))
    assert len(events) == 1
    assert events[0].kind == 'arp_packet'
    assert events[0].attrs['op'] == 1
    assert events[0].timestamp == 1700000000.5
