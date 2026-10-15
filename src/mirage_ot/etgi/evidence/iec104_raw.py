"""Byte-level IEC-104 APDU reader used only to audit the tshark path.

It reads classic Ethernet PCAP records directly and decodes APCI and ASDU
octets from the TCP payload without the Wireshark IEC-104 dissector. It does
not reassemble TCP streams; an APDU cut by a segment boundary is reported as
truncated rather than guessed.
"""
from __future__ import annotations
import struct
from pathlib import Path

_CP24, _CP56 = 3, 7
# type id -> ordered element parts after the 3-octet IOA
_LAYOUT = {
    1: ("siq",), 2: ("siq", "cp24"), 3: ("diq",), 4: ("diq", "cp24"),
    9: ("nva", "qds"), 10: ("nva", "qds", "cp24"), 11: ("sva", "qds"), 12: ("sva", "qds", "cp24"),
    13: ("float", "qds"), 14: ("float", "qds", "cp24"),
    30: ("siq", "cp56"), 31: ("diq", "cp56"), 34: ("nva", "qds", "cp56"),
    35: ("sva", "qds", "cp56"), 36: ("float", "qds", "cp56"),
    45: ("sco",), 46: ("dco",), 48: ("nva", "qos"), 49: ("sva", "qos"), 50: ("float", "qos"),
    58: ("sco", "cp56"), 59: ("dco", "cp56"), 61: ("nva", "qos", "cp56"),
    62: ("sva", "qos", "cp56"), 63: ("float", "qos", "cp56"),
    70: ("coi",), 100: ("qoi",), 101: ("qcc",), 103: ("cp56",), 105: ("qrp",),
}
_SIZE = {"siq": 1, "diq": 1, "qds": 1, "sco": 1, "dco": 1, "qos": 1, "coi": 1, "qoi": 1, "qcc": 1,
         "qrp": 1, "nva": 2, "sva": 2, "float": 4, "cp24": _CP24, "cp56": _CP56}


def iter_frames(path: Path):
    """Yield (frame_number, timestamp, src_ip, dst_ip, src_port, dst_port, tcp_payload)."""
    data = Path(path).read_bytes()
    magic = data[:4]
    formats = {b"\xd4\xc3\xb2\xa1": ("<", 1e6), b"\xa1\xb2\xc3\xd4": (">", 1e6),
               b"\x4d\x3c\xb2\xa1": ("<", 1e9), b"\xa1\xb2\x3c\x4d": (">", 1e9)}
    if magic not in formats:
        raise ValueError("Only classic PCAP is supported")
    endian, units = formats[magic]
    record = struct.Struct(endian + "IIII")
    offset, number = 24, 0
    while offset + 16 <= len(data):
        secs, sub, incl, _orig = record.unpack_from(data, offset)
        offset += 16
        frame = data[offset:offset + incl]
        offset += incl
        number += 1
        parsed = _tcp_payload(frame)
        if parsed is None:
            continue
        src, dst, sport, dport, payload = parsed
        yield number, secs + sub / units, src, dst, sport, dport, payload


def _tcp_payload(frame: bytes):
    if len(frame) < 14:
        return None
    ethertype = struct.unpack_from("!H", frame, 12)[0]
    pos = 14
    while ethertype in (0x8100, 0x88A8) and len(frame) >= pos + 4:
        ethertype = struct.unpack_from("!H", frame, pos + 2)[0]
        pos += 4
    if ethertype != 0x0800 or len(frame) < pos + 20:
        return None
    ihl = (frame[pos] & 0x0F) * 4
    total = struct.unpack_from("!H", frame, pos + 2)[0]
    if frame[pos + 9] != 6:
        return None
    src = ".".join(str(b) for b in frame[pos + 12:pos + 16])
    dst = ".".join(str(b) for b in frame[pos + 16:pos + 20])
    tcp = pos + ihl
    if len(frame) < tcp + 20:
        return None
    sport, dport = struct.unpack_from("!HH", frame, tcp)
    doff = (frame[tcp + 12] >> 4) * 4
    end = min(len(frame), pos + total) if total else len(frame)
    return src, dst, sport, dport, frame[tcp + doff:end]


def decode_apdus(payload: bytes) -> tuple[list[dict], str]:
    """Return information objects for every I-format APDU in one TCP payload."""
    objects: list[dict] = []
    pos, i_index, status = 0, 0, "complete"
    while pos < len(payload):
        if payload[pos] != 0x68:
            return objects, "apdu_start_octet_missing"
        if pos + 2 > len(payload):
            return objects, "truncated_apci"
        length = payload[pos + 1]
        apdu = payload[pos + 2:pos + 2 + length]
        if len(apdu) < length or length < 4:
            return objects, "truncated_apdu"
        pos += 2 + length
        if apdu[0] & 0x01:
            continue
        tx = (apdu[0] | apdu[1] << 8) >> 1
        rx = (apdu[2] | apdu[3] << 8) >> 1
        asdu = apdu[4:]
        if len(asdu) < 6:
            status = "truncated_asdu_header"
            continue
        type_id, vsq, cot, oa = asdu[0], asdu[1], asdu[2], asdu[3]
        ca = asdu[4] | asdu[5] << 8
        sq, count = bool(vsq & 0x80), vsq & 0x7F
        layout = _LAYOUT.get(type_id)
        header = {
            "asdu_index": i_index, "apci_tx": tx, "apci_rx": rx, "type_id": type_id,
            "cause": cot & 0x3F, "cot_negative": bool(cot & 0x40), "cot_test": bool(cot & 0x80),
            "sq": sq, "numix": count, "oa": oa, "ca": ca,
        }
        i_index += 1
        if layout is None:
            objects.append({**header, "object_index": None, "ioa": None, "layout": "type_not_modeled"})
            continue
        size = sum(_SIZE[part] for part in layout)
        body, cursor = asdu[6:], 0
        base_ioa = None
        for j in range(count):
            if sq:
                if j == 0:
                    if cursor + 3 > len(body):
                        status = "truncated_information_object"
                        break
                    base_ioa = body[0] | body[1] << 8 | body[2] << 16
                    cursor = 3
                ioa = base_ioa + j
            else:
                if cursor + 3 > len(body):
                    status = "truncated_information_object"
                    break
                ioa = body[cursor] | body[cursor + 1] << 8 | body[cursor + 2] << 16
                cursor += 3
            if cursor + size > len(body):
                status = "truncated_information_object"
                break
            element = _decode_element(layout, body[cursor:cursor + size])
            cursor += size
            objects.append({**header, "object_index": j, "ioa": ioa, "layout": "+".join(layout), **element})
    return objects, status


def _decode_element(layout: tuple[str, ...], blob: bytes) -> dict:
    out: dict = {"value": None, "quality_flags": None, "select_execute": None}
    pos = 0
    for part in layout:
        size = _SIZE[part]
        octets = blob[pos:pos + size]
        pos += size
        if part in ("siq", "diq"):
            b = octets[0]
            out["value"] = float(b & 0x01) if part == "siq" else float(b & 0x03)
            out["quality_flags"] = {"iv": bool(b & 0x80), "nt": bool(b & 0x40),
                                    "sb": bool(b & 0x20), "bl": bool(b & 0x10)}
        elif part == "qds":
            b = octets[0]
            out["quality_flags"] = {"iv": bool(b & 0x80), "nt": bool(b & 0x40), "sb": bool(b & 0x20),
                                    "bl": bool(b & 0x10), "ov": bool(b & 0x01)}
        elif part == "float":
            out["value"] = struct.unpack("<f", octets)[0]
        elif part == "nva":
            out["value"] = struct.unpack("<h", octets)[0] / 32768.0
        elif part == "sva":
            out["value"] = float(struct.unpack("<h", octets)[0])
        elif part in ("sco", "dco"):
            b = octets[0]
            out["value"] = float(b & 0x01) if part == "sco" else float(b & 0x03)
            out["select_execute"] = "select" if b & 0x80 else "execute"
        elif part == "qos":
            out["select_execute"] = "select" if octets[0] & 0x80 else "execute"
    return out


def decode_pcap(path: Path, *, port: int = 2404) -> list[dict]:
    rows = []
    for number, ts, src, dst, sport, dport, payload in iter_frames(path):
        if port not in (sport, dport) or not payload:
            continue
        objects, status = decode_apdus(payload)
        for obj in objects:
            rows.append({"frame_number": number, "timestamp": ts, "src_ip": src, "dst_ip": dst,
                         "src_port": sport, "dst_port": dport, "segment_status": status, **obj})
    return rows
