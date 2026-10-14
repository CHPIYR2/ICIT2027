"""IEC-104 extraction through tshark's ASDU dissector.

This is protocol parsing, not an attack detector. Official ipal-transcriber is
used when it is on PATH; otherwise tshark is the decoder. Type-id ranges below
are the IEC 60870-5-104 classes (monitor, control, system). They are not
Sherlock attack labels.
"""
from __future__ import annotations
import shutil
import struct
import subprocess
from pathlib import Path

# Public type-id classes from IEC 60870-5-101/104. Not incident labels.
_CONTROL = set(range(45, 52)) | set(range(58, 65))
_SYSTEM = set(range(70, 107))


def asdu_class(type_id: int | None) -> str:
    if type_id is None:
        return "unknown"
    if 1 <= type_id <= 40 or type_id in range(52, 58):
        return "monitor"
    if type_id in _CONTROL:
        return "control"
    if type_id in _SYSTEM:
        return "system"
    return "other"


def find_decoder() -> str | None:
    return shutil.which("ipal-transcriber") or shutil.which("tshark")


def slice_pcap_stream(handle, dest: Path, start: float, end: float) -> int:
    """Write classic Ethernet frames in [start, end) without decoding them."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    header = handle.read(24)
    if len(header) != 24:
        raise ValueError("Truncated PCAP header")
    magic = header[:4]
    formats = {b"\xd4\xc3\xb2\xa1": ("<", 1e6), b"\xa1\xb2\xc3\xd4": (">", 1e6),
               b"\x4d\x3c\xb2\xa1": ("<", 1e9), b"\xa1\xb2\x3c\x4d": (">", 1e9)}
    if magic not in formats:
        raise ValueError("Only classic PCAP can be sliced")
    endian, units = formats[magic]
    linktype = struct.unpack(endian + "I", header[20:24])[0]
    if linktype != 1:
        raise ValueError(f"Unsupported linktype {linktype}")
    record = struct.Struct(endian + "IIII")
    kept = 0
    with dest.open("wb") as out:
        out.write(struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
        while True:
            raw = handle.read(16)
            if not raw:
                break
            if len(raw) != 16:
                raise ValueError("Truncated PCAP record")
            secs, sub, incl, orig = record.unpack(raw)
            blob = handle.read(incl)
            if len(blob) != incl:
                raise ValueError("Truncated PCAP payload")
            timestamp = secs + sub / units
            if timestamp < start or timestamp >= end:
                continue
            usec = int(round((timestamp - int(timestamp)) * 1_000_000))
            if usec == 1_000_000:
                secs_out = int(timestamp) + 1
                usec = 0
            else:
                secs_out = int(timestamp)
            out.write(struct.pack("<IIII", secs_out, usec, incl, orig))
            out.write(blob)
            kept += 1
    return kept


_FIELDS = [
    "frame.time_epoch", "ip.src", "ip.dst", "tcp.srcport", "tcp.dstport",
    "iec60870_104.type", "iec60870_asdu.typeid", "iec60870_asdu.addr",
    "iec60870_asdu.causetx", "iec60870_asdu.ioa", "iec60870_asdu.float",
    "iec60870_asdu.normval", "iec60870_asdu.scalval", "iec60870_asdu.siq.spi",
    "iec60870_asdu.sco.on",
]


def decode_slice(path: Path, *, timeout: int = 180) -> tuple[list[dict], str]:
    """Return one dict per tshark row. Values are not aligned if field counts disagree."""
    executable = shutil.which("tshark")
    if not executable:
        return [], "tshark is not installed; IEC-104 ASDU fields were not decoded"
    command = [executable, "-r", str(path), "-Y", "iec60870_asdu", "-T", "fields",
               "-E", "separator=\t", "-E", "occurrence=a", "-E", "aggregator=,",
               "-E", "quote=n"]
    for field in _FIELDS:
        command.extend(["-e", field])
    completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=timeout)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()[:500]
        return [], f"tshark failed ({completed.returncode}): {detail}"
    rows = []
    for line in completed.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        parts += [""] * (len(_FIELDS) - len(parts))
        item = dict(zip(_FIELDS, parts))
        rows.append(item)
    return rows, f"tshark {executable}"


def split_fields(row: dict) -> list[dict]:
    """Split a dissected ASDU into information objects without inventing alignment."""
    ioas = _cells(row.get("iec60870_asdu.ioa"))
    type_ids = _cells(row.get("iec60870_asdu.typeid"))
    causes = _cells(row.get("iec60870_asdu.causetx"))
    addresses = _cells(row.get("iec60870_asdu.addr"))
    value_sets = {
        "float": _cells(row.get("iec60870_asdu.float")),
        "normval": _cells(row.get("iec60870_asdu.normval")),
        "scalval": _cells(row.get("iec60870_asdu.scalval")),
        "spi": _cells(row.get("iec60870_asdu.siq.spi")),
        "sco": _cells(row.get("iec60870_asdu.sco.on")),
    }
    if not ioas:
        return [_header(row, ioa=None, type_id=_first_int(type_ids), cause=_first(causes),
                        address=_first(addresses), value=None, value_present=False,
                        alignment="no_ioa")]
    objects = []
    for index, ioa in enumerate(ioas):
        type_id = _at_int(type_ids, index)
        choices = []
        for name, cells in value_sets.items():
            if not cells:
                continue
            if len(cells) == len(ioas):
                choices.append((name, cells[index]))
            elif len(cells) == 1 and len(ioas) == 1:
                choices.append((name, cells[0]))
        if not choices:
            objects.append(_header(
                row, ioa=ioa, type_id=type_id, cause=_at(causes, index),
                address=_at(addresses, index), value=None, value_present=False,
                alignment="identifier_without_aligned_value",
            ))
            continue
        name, text = choices[0]
        number = _float(text)
        objects.append(_header(
            row, ioa=ioa, type_id=type_id, cause=_at(causes, index),
            address=_at(addresses, index), value=number, value_present=number is not None,
            alignment=name if number is not None else "unparsed_value",
        ))
    return objects


def _header(row, *, ioa, type_id, cause, address, value, value_present, alignment) -> dict:
    ca = address
    ca_ioa = None
    if ca not in (None, "") and ioa not in (None, ""):
        ca_ioa = f"{_int_text(ca)}.{_int_text(ioa)}"
    return {
        "timestamp": _float(row.get("frame.time_epoch")),
        "src_ip": row.get("ip.src") or None,
        "dst_ip": row.get("ip.dst") or None,
        "src_port": _int(row.get("tcp.srcport")),
        "dst_port": _int(row.get("tcp.dstport")),
        "apci_type": row.get("iec60870_104.type") or None,
        "type_id": type_id,
        "protocol_class": asdu_class(type_id),
        "cause": cause,
        "ca": None if ca in (None, "") else _int_text(ca),
        "ioa": None if ioa in (None, "") else _int_text(ioa),
        "ca_ioa": ca_ioa,
        "value": value,
        "value_present": value_present,
        "alignment": alignment,
    }


def _cells(text: str | None) -> list[str]:
    if text is None or text == "":
        return []
    return [part.strip() for part in str(text).split(",") if part.strip() != ""]


def _first(cells: list[str]):
    return cells[0] if cells else None


def _at(cells: list[str], index: int):
    if len(cells) == 1:
        return cells[0]
    if index < len(cells):
        return cells[index]
    return None


def _int(text) -> int | None:
    try:
        return int(text)
    except (TypeError, ValueError):
        return None


def _int_text(text) -> str:
    number = _int(text)
    return str(number if number is not None else text)


def _first_int(cells: list[str]) -> int | None:
    return _int(_first(cells)) if cells else None


def _at_int(cells: list[str], index: int) -> int | None:
    return _int(_at(cells, index))


def _float(text) -> float | None:
    try:
        return float(text)
    except (TypeError, ValueError):
        return None
