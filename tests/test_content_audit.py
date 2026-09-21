"""Tests for audit conclusions that affect labels, timing, and evidence views."""
import gzip
import io
import json
from pathlib import Path
import struct
import sys
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_contents import complete_apdus, event_audit, pcap_audit, state_audit


def packet(payload):
    tcp = struct.pack("!HHII", 2404, 30000, 1, 1) + b"\x50\x18" + b"\x00"*6 + payload
    ip = b"\x45\x00" + struct.pack("!H", 20+len(tcp)) + b"\x00"*4 + b"\x40\x06" + b"\x00"*2
    ip += bytes([10,0,0,1,10,0,0,2]) + tcp
    return b"\x00"*12 + b"\x08\x00" + ip


def capture(frame, nano=False):
    magic = b"\x4d\x3c\xb2\xa1" if nano else b"\xd4\xc3\xb2\xa1"
    header = magic + struct.pack("<HHiIII", 2,4,0,0,65535,1)
    return header + struct.pack("<IIII", 100, 500000000 if nano else 500000, len(frame), len(frame)) + frame


class ContentAuditTests(unittest.TestCase):
    def test_binary_label_comes_from_matching_raw_start(self):
        event = {"id":"0 (benign event)","description":"maintenance","start":10.0,"end":45.0}
        raw = [{"timestamp":10.0,"notification_data":{"id":"p","mark":"start","type":"procedure","malicious":False}},
               {"timestamp":15.0,"notification_data":{"id":"p","mark":"end","type":"procedure","malicious":False}}]
        result = event_audit([event],raw)
        self.assertEqual(result["benign"],1)
        self.assertEqual(result["cyber"],0)
        self.assertEqual(result["events"][0]["ipal_end_minus_raw_end_seconds"],30.0)

    def test_ambiguous_raw_start_is_not_guessed(self):
        event={"id":"1","description":"attack","start":10.0,"end":20.0}
        row={"timestamp":10.0,"notification_data":{"mark":"start","type":"procedure","malicious":True}}
        result=event_audit([event],[row,row])
        self.assertEqual(result["unresolved"],1)
        self.assertFalse(result["events"][0]["id_label_agrees"])

    def test_label_disagreement_is_visible(self):
        event={"id":"1 (benign event)","description":"x","start":10.0,"end":20.0}
        row={"timestamp":10.0,"notification_data":{"mark":"start","type":"procedure","malicious":True}}
        self.assertEqual(event_audit([event],[row])["label_disagreements"],["1 (benign event)"])

    def test_partial_apdu_not_counted_as_a_complete_observation(self):
        full=b"\x68\x04\x43\x00\x00\x00"
        self.assertEqual(complete_apdus(full[:-1]),([],5))
        self.assertEqual(complete_apdus(full+full),([full,full],0))

    def test_observed_float_value_retains_packet_and_time(self):
        # I-format, type 13, single object, CA 101, IOA 10010, float value, quality.
        body=b"\x00"*4+bytes([13,1,3,0,101,0])+int(10010).to_bytes(3,"little")+struct.pack("<f",1.25)+b"\x00"
        apdu=b"\x68"+bytes([len(body)])+body
        mapping={"101.10010":{"attribute":"voltage","unit":"PER_UNIT"}}
        for nano in [False,True]:
            result,_=pcap_audit(io.BytesIO(capture(packet(apdu),nano)),mapping)
            self.assertEqual(result["packets"],1)
            self.assertEqual(result["example_observable_value"]["value"],1.25)
            self.assertEqual(result["example_observable_value"]["timestamp"],100.5)
            self.assertEqual(result["mapped_ca_ioas"],["101.10010"])

    def test_truncated_pcap_fails(self):
        data=capture(packet(b"\x68\x04\x43\x00\x00\x00"))
        with self.assertRaisesRegex(ValueError,"Truncated PCAP record payload"):
            pcap_audit(io.BytesIO(data[:-1]),{})

    def test_state_label_types_missingness_and_new_fields_are_audited(self):
        rows=[{"timestamp":10.0,"state":{"voltage":None},"malicious":False},
              {"timestamp":11.0,"state":{"voltage":1.0,"test":1},"malicious":"0 (benign event)"}]
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,"w") as z:
            z.writestr("state.gz",gzip.compress(b"\n".join(json.dumps(r).encode() for r in rows)+b"\n"))
        stream.seek(0)
        with zipfile.ZipFile(stream) as z:
            result=state_audit(z,"state.gz",{"voltage":None})
        self.assertEqual(result["null_values"],1)
        self.assertEqual(result["fieldset_change_rows"],1)
        self.assertEqual(result["malicious_type_counts"],{"bool":1,"str":1})
        self.assertEqual(result["rows"],2)


if __name__ == "__main__":
    unittest.main()
