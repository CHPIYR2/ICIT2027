import gzip
import io
import ipaddress
import json
import struct
import zipfile
from mirage_ot.archive import inspect_archive, load_selected


def pcap_bytes():
    eth = bytes.fromhex('ffffffffffff0011223344550806')
    arp = (struct.pack('!HHBBH', 1, 0x0800, 6, 4, 1)
           + bytes.fromhex('001122334455')
           + ipaddress.IPv4Address('192.0.2.1').packed
           + bytes(6)
           + ipaddress.IPv4Address('192.0.2.2').packed)
    frame = eth + arp
    header = bytes.fromhex('d4c3b2a1') + struct.pack('<HHIIII', 2, 4, 0, 0, 65535, 1)
    rec = struct.pack('<IIII', 1700000000, 0, len(frame), len(frame)) + frame
    return header + rec


def test_nested_gzip_in_zip_without_extract(tmp_path):
    zip_path = tmp_path / 'dummy-sherlock.zip'
    state = [{'timestamp': 1700000000, 'values': {'bus.0.MEASUREMENT.voltage': 1.01}}]
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.writestr('dummy/ipal/train.n302.state.gz', gzip.compress(json.dumps(state).encode()))
        zf.writestr('dummy/pcap/train.n302.pcap.gz', gzip.compress(pcap_bytes()))
        zf.writestr('dummy/raw/physical.zip', b'DO-NOT-OPEN')
    info = inspect_archive(zip_path)
    assert info['physical_zip_present']
    assert len(info['state_members']) == 1 and len(info['pcap_members']) == 1
    observed = list(load_selected(zip_path, state_member=info['state_members'][0],
                                  pcap_members=info['pcap_members'],
                                  start=1699999999, end=1700000001))
    assert {o.modality for o in observed} == {'physical','network'}
    assert all('dummy-sherlock.zip:' in o.source_id for o in observed)
