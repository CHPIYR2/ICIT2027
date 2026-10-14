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
    "frame.time_epoch",
    "ip.src",
    "ip.dst",
    "tcp.srcport",
    "tcp.dstport",
    "iec60870_104.type",
    "iec60870_104.tx",
    "iec60870_104.rx",
    "iec60870_asdu.typeid",
    "iec60870_asdu.addr",
    "iec60870_asdu.causetx",
    "iec60870_asdu.nega",
    "iec60870_asdu.test",
    "iec60870_asdu.sq",
    "iec60870_asdu.ioa",
    "iec60870_asdu.float",
    "iec60870_asdu.normval",
    "iec60870_asdu.scalval",
    "iec60870_asdu.siq.spi",
    "iec60870_asdu.siq.iv",
    "iec60870_asdu.qds.iv",
    "iec60870_asdu.sco.on",
    "iec60870_asdu.sco.se",
    "iec60870_asdu.qos.se",
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
    """Split a dissected ASDU into information objects without shifting indexes.

    Empty aggregator slots are kept so a missing middle value cannot move a later
    value onto the wrong IOA. A header that occurs once (type id, COT, CA) is
    shared by every object. A value list whose length is neither 1 nor the IOA
    count is not reindexed.
    """
    ioas = _cells(row.get("iec60870_asdu.ioa"), preserve_gaps=True)
    type_ids = _cells(row.get("iec60870_asdu.typeid"), preserve_gaps=True)
    causes = _cells(row.get("iec60870_asdu.causetx"), preserve_gaps=True)
    addresses = _cells(row.get("iec60870_asdu.addr"), preserve_gaps=True)
    negas = _cells(row.get("iec60870_asdu.nega"), preserve_gaps=True)
    tests = _cells(row.get("iec60870_asdu.test"), preserve_gaps=True)
    sqs = _cells(row.get("iec60870_asdu.sq"), preserve_gaps=True)
    siq_ivs = _cells(row.get("iec60870_asdu.siq.iv"), preserve_gaps=True)
    qds_ivs = _cells(row.get("iec60870_asdu.qds.iv"), preserve_gaps=True)
    sco_ses = _cells(row.get("iec60870_asdu.sco.se"), preserve_gaps=True)
    qos_ses = _cells(row.get("iec60870_asdu.qos.se"), preserve_gaps=True)

    value_sets = {
        "float": _cells(row.get("iec60870_asdu.float"), preserve_gaps=True),
        "normval": _cells(row.get("iec60870_asdu.normval"), preserve_gaps=True),
        "scalval": _cells(row.get("iec60870_asdu.scalval"), preserve_gaps=True),
        "spi": _cells(row.get("iec60870_asdu.siq.spi"), preserve_gaps=True),
        "sco": _cells(row.get("iec60870_asdu.sco.on"), preserve_gaps=True),
    }
    nonempty_ioas = [part for part in ioas if part]
    if not nonempty_ioas:
        return [_header(
            row, ioa=None, type_id=_first_int(type_ids), cause=_first(causes),
            address=_first(addresses), value=None, value_present=False,
            alignment="no_ioa", cot_negative=_bool(_first(negas)),
            cot_test=_bool(_first(tests)), sq=_bool(_first(sqs)),
            select_execute=None, quality_invalid=None,
        )]
    sq_flag = _bool(_aligned(sqs, 0, len(ioas)))
    longest_values = max((len(cells) for cells in value_sets.values() if cells), default=0)
    if sq_flag is True and len(nonempty_ioas) == 1 and longest_values > 1:
        base = _int(nonempty_ioas[0])
        if base is not None:
            ioas = [str(base + offset) for offset in range(longest_values)]
    count = len(ioas)
    objects = []
    for index, ioa in enumerate(ioas):
        if not ioa:
            continue
        type_id = _int(_aligned(type_ids, index, count))
        cot_neg = _bool(_aligned(negas, index, count))
        cot_tst = _bool(_aligned(tests, index, count))
        sq_here = _bool(_aligned(sqs, index, count))
        se_flag = _bool(_aligned(sco_ses, index, count))
        if se_flag is None:
            se_flag = _bool(_aligned(qos_ses, index, count))
        se_mode = None if se_flag is None else ("select" if se_flag else "execute")
        q_inv = _bool(_aligned(siq_ivs, index, count))
        if q_inv is None:
            q_inv = _bool(_aligned(qds_ivs, index, count))

        choices = []
        mismatched = False
        for name, cells in value_sets.items():
            if not cells:
                continue
            # A single measurement value is not a shared ASDU header. Do not copy it onto every IOA.
            if len(cells) == count or (len(cells) == 1 and count == 1):
                text = cells[index] if len(cells) == count else cells[0]
                if text:
                    choices.append((name, text))
            else:
                mismatched = True
        if not choices:
            objects.append(_header(
                row, ioa=ioa, type_id=type_id, cause=_aligned(causes, index, count),
                address=_aligned(addresses, index, count), value=None, value_present=False,
                alignment="value_count_mismatch_not_shifted" if mismatched else "identifier_without_aligned_value",
                cot_negative=cot_neg, cot_test=cot_tst, sq=sq_here,
                select_execute=se_mode, quality_invalid=q_inv,
            ))
            continue
        name, text = choices[0]
        number = _parse_value(name, text)
        objects.append(_header(
            row, ioa=ioa, type_id=type_id, cause=_aligned(causes, index, count),
            address=_aligned(addresses, index, count), value=number, value_present=number is not None,
            alignment=name if number is not None else "unparsed_value",
            cot_negative=cot_neg, cot_test=cot_tst, sq=sq_here,
            select_execute=se_mode, quality_invalid=q_inv,
        ))
    return objects


def _header(
    row,
    *,
    ioa,
    type_id,
    cause,
    address,
    value,
    value_present,
    alignment,
    cot_negative: bool | None = None,
    cot_test: bool | None = None,
    sq: bool | None = None,
    select_execute: str | None = None,
    quality_invalid: bool | None = None,
) -> dict:
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
        "apci_tx": _int(_first(_cells(row.get("iec60870_104.tx")))),
        "apci_rx": _int(_first(_cells(row.get("iec60870_104.rx")))),
        "type_id": type_id,
        "protocol_class": asdu_class(type_id),
        "cause": cause,
        "cot_negative": cot_negative,
        "cot_test": cot_test,
        "sq": sq,
        "select_execute": select_execute,
        "quality_invalid": quality_invalid,
        "ca": None if ca in (None, "") else _int_text(ca),
        "ioa": None if ioa in (None, "") else _int_text(ioa),
        "ca_ioa": ca_ioa,
        "value": value,
        "value_present": value_present,
        "alignment": alignment,
    }


def _cells(text: str | None, *, preserve_gaps: bool = False) -> list[str]:
    if text is None or text == "":
        return []
    parts = [part.strip() for part in str(text).split(",")]
    if preserve_gaps:
        return parts
    return [part for part in parts if part != ""]


def _aligned(cells: list[str], index: int, count: int):
    """Return the cell for this object. A single header is shared; a mismatched length is not shifted."""
    if not cells:
        return None
    nonempty = [part for part in cells if part]
    if len(cells) == 1:
        return nonempty[0] if nonempty else None
    if len(nonempty) == 1 and len(cells) != count:
        return nonempty[0]
    if len(cells) == count and index < len(cells):
        return cells[index] or None
    return None


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


def _bool(text) -> bool | None:
    if text is None or text == "":
        return None
    low = str(text).strip().lower()
    if low in ("true", "1", "0x01", "0x1", "yes"):
        return True
    if low in ("false", "0", "0x00", "0x0", "no"):
        return False
    return None


def _parse_value(name: str, text: str | None) -> float | None:
    num = _float(text)
    if num is not None:
        return num
    if name in ("spi", "sco"):
        b = _bool(text)
        if b is not None:
            return 1.0 if b else 0.0
    return None


def _float(text) -> float | None:
    try:
        return float(text)
    except (TypeError, ValueError):
        return None
