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
    "frame.number",
    "iec60870_asdu.numix",
    "iec60870_asdu.oa",
    "iec60870_asdu.siq.bl",
    "iec60870_asdu.siq.sb",
    "iec60870_asdu.siq.nt",
    "iec60870_asdu.diq.dpi",
    "iec60870_asdu.diq.iv",
    "iec60870_asdu.diq.bl",
    "iec60870_asdu.diq.sb",
    "iec60870_asdu.diq.nt",
    "iec60870_asdu.qds.ov",
    "iec60870_asdu.qds.bl",
    "iec60870_asdu.qds.sb",
    "iec60870_asdu.qds.nt",
    "iec60870_asdu.dco.on",
    "iec60870_asdu.dco.se",
]

# Information element layout per IEC 60870-5-101/104 type id. Field names are tshark's.
_VALUE_FIELD = {
    **{t: ("spi", "iec60870_asdu.siq.spi") for t in (1, 2, 30)},
    **{t: ("dpi", "iec60870_asdu.diq.dpi") for t in (3, 4, 31)},
    **{t: ("normval", "iec60870_asdu.normval") for t in (9, 10, 34, 48, 61)},
    **{t: ("scalval", "iec60870_asdu.scalval") for t in (11, 12, 35, 49, 62)},
    **{t: ("float", "iec60870_asdu.float") for t in (13, 14, 36, 50, 63)},
    **{t: ("sco", "iec60870_asdu.sco.on") for t in (45, 58)},
    **{t: ("dco", "iec60870_asdu.dco.on") for t in (46, 59)},
}
_QUALITY_PREFIX = {
    **{t: "siq" for t in (1, 2, 30)},
    **{t: "diq" for t in (3, 4, 31)},
    **{t: "qds" for t in (9, 10, 11, 12, 13, 14, 34, 35, 36)},
}
_QUALITY_BITS = {"siq": ("iv", "nt", "sb", "bl"), "diq": ("iv", "nt", "sb", "bl"),
                 "qds": ("iv", "nt", "sb", "bl", "ov")}
_SE_FIELD = {
    **{t: "iec60870_asdu.sco.se" for t in (45, 58)},
    **{t: "iec60870_asdu.dco.se" for t in (46, 59)},
    **{t: "iec60870_asdu.qos.se" for t in (48, 49, 50, 61, 62, 63)},
}


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


def element_fields(type_id: int | None) -> list[str]:
    """tshark fields that carry one occurrence per information object of this type."""
    fields = []
    if type_id in _VALUE_FIELD:
        fields.append(_VALUE_FIELD[type_id][1])
    prefix = _QUALITY_PREFIX.get(type_id)
    if prefix:
        fields.extend(f"iec60870_asdu.{prefix}.{bit}" for bit in _QUALITY_BITS[prefix])
    if type_id in _SE_FIELD:
        fields.append(_SE_FIELD[type_id])
    return fields


def split_fields(row: dict) -> list[dict]:
    """Split a dissected frame into information objects by ASDU structure.

    Type id, COT (cause, P/N, T), SQ, CA and NumIx belong to one ASDU and are
    shared only by that ASDU's objects. Value, quality and S/E occur once per
    information object; each such field is consumed in frame order by the
    objects whose type carries it. A field whose occurrence count differs from
    the number of objects that carry it is left unknown for the whole frame:
    it is never shifted onto a neighbouring IOA and never copied across IOAs.
    """
    type_ids = _cells(row.get("iec60870_asdu.typeid"), preserve_gaps=True)
    ioas = _cells(row.get("iec60870_asdu.ioa"), preserve_gaps=True)
    if not [part for part in ioas if part]:
        return [_header(
            row, ioa=None, type_id=_first_int(type_ids), cause=_first(_cells(row.get("iec60870_asdu.causetx"))),
            address=_first(_cells(row.get("iec60870_asdu.addr"))), value=None, value_present=False,
            alignment="no_ioa", cot_negative=_bool(_first(_cells(row.get("iec60870_asdu.nega")))),
            cot_test=_bool(_first(_cells(row.get("iec60870_asdu.test")))),
            sq=_bool(_first(_cells(row.get("iec60870_asdu.sq")))),
        )]

    n_asdu = max(len(type_ids), 1)

    def per_asdu(field: str) -> list:
        cells = _cells(row.get(field), preserve_gaps=True)
        if len(cells) == n_asdu:
            return [c or None for c in cells]
        if len(cells) == 1 and n_asdu == 1:
            return [cells[0] or None]
        return [None] * n_asdu

    headers = {name: per_asdu(f"iec60870_asdu.{name}")
               for name in ("typeid", "causetx", "nega", "test", "sq", "addr", "numix", "oa")}
    header_alignment = {
        name: ("aligned" if any(v is not None for v in values) else "not_aligned_or_absent")
        for name, values in headers.items()
    }

    sq_flags = [_bool(v) for v in headers["sq"]]
    numix = [_int(v) for v in headers["numix"]]
    if n_asdu == 1 and numix[0] is None:
        numix[0] = len(ioas)
    counts_known = all(n is not None for n in numix)
    asdu_ioas: list[list[str]] | None = None
    if counts_known:
        if len(ioas) == sum(numix):
            asdu_ioas, cursor = [], 0
            for n in numix:
                asdu_ioas.append(ioas[cursor:cursor + n])
                cursor += n
        elif len(ioas) == sum(1 if sq_flags[k] else numix[k] for k in range(n_asdu)):
            asdu_ioas, cursor = [], 0
            for k, n in enumerate(numix):
                if sq_flags[k]:
                    base = _int(ioas[cursor])
                    asdu_ioas.append([str(base + i) for i in range(n)] if base is not None else [""] * n)
                    cursor += 1
                else:
                    asdu_ioas.append(ioas[cursor:cursor + n])
                    cursor += n
    if asdu_ioas is None:
        return [
            _header(row, ioa=None, type_id=_int(headers["typeid"][k]), cause=headers["causetx"][k],
                    address=headers["addr"][k], value=None, value_present=False,
                    alignment="ioa_count_mismatch_not_aligned",
                    cot_negative=_bool(headers["nega"][k]), cot_test=_bool(headers["test"][k]),
                    sq=sq_flags[k], asdu_index=k, numix=numix[k], oa=_int(headers["oa"][k]),
                    header_alignment=header_alignment)
            for k in range(n_asdu)
        ]

    object_types = [(_int(headers["typeid"][k]), k, j)
                    for k in range(n_asdu) for j in range(len(asdu_ioas[k]))]
    consumers: dict[str, int] = {}
    for type_id, _, _ in object_types:
        for field in element_fields(type_id):
            consumers[field] = consumers.get(field, 0) + 1
    field_status: dict[str, str] = {}
    field_cells: dict[str, list[str]] = {}
    for field, expected in consumers.items():
        cells = _cells(row.get(field), preserve_gaps=True)
        field_cells[field] = cells
        if not cells:
            field_status[field] = "not_decoded_by_tshark"
        elif len(cells) == expected:
            field_status[field] = "aligned"
        else:
            field_status[field] = "count_mismatch_not_shifted"
    cursors = {field: 0 for field in consumers}

    def take(field: str):
        position = cursors[field]
        cursors[field] = position + 1
        if field_status[field] != "aligned":
            return None
        return field_cells[field][position] or None

    apci = _apci_by_asdu(row, n_asdu)
    objects = []
    for type_id, k, j in object_types:
        ioa = asdu_ioas[k][j]
        mine = element_fields(type_id)
        taken = {field: take(field) for field in mine}
        value, value_present, alignment = None, False, "type_without_value_element"
        if type_id in _VALUE_FIELD:
            name, field = _VALUE_FIELD[type_id]
            text = taken[field]
            if field_status[field] == "count_mismatch_not_shifted":
                alignment = "value_count_mismatch_not_shifted"
            elif field_status[field] == "not_decoded_by_tshark":
                alignment = "value_not_decoded_by_tshark"
            elif text is None:
                alignment = "identifier_without_aligned_value"
            else:
                value = _parse_value(name, text)
                value_present = value is not None
                alignment = name if value_present else "unparsed_value"
        prefix = _QUALITY_PREFIX.get(type_id)
        quality_flags = None
        if prefix:
            quality_flags = {bit: _bool(taken[f"iec60870_asdu.{prefix}.{bit}"]) for bit in _QUALITY_BITS[prefix]}
        se_mode = None
        if type_id in _SE_FIELD:
            se_flag = _bool(taken[_SE_FIELD[type_id]])
            se_mode = None if se_flag is None else ("select" if se_flag else "execute")
        objects.append(_header(
            row, ioa=ioa or None, type_id=type_id, cause=headers["causetx"][k], address=headers["addr"][k],
            value=value, value_present=value_present, alignment=alignment,
            cot_negative=_bool(headers["nega"][k]), cot_test=_bool(headers["test"][k]), sq=sq_flags[k],
            select_execute=se_mode, quality_flags=quality_flags,
            asdu_index=k, object_index=j, numix=numix[k], oa=_int(headers["oa"][k]),
            apci=apci[k], header_alignment=header_alignment,
            field_alignment={field: field_status[field] for field in mine},
        ))
    return objects


def _apci_by_asdu(row: dict, n_asdu: int) -> list[dict]:
    """Map APCI tx/rx to the k-th I-format APDU. S/U frames in the same segment carry no ASDU."""
    types = [_int_hex(t) for t in _cells(row.get("iec60870_104.type"))]
    txs = _cells(row.get("iec60870_104.tx"))
    rxs = _cells(row.get("iec60870_104.rx"))
    if not types:
        types = [0] * n_asdu
    i_positions = [pos for pos, t in enumerate(types) if t == 0]
    with_rx = [pos for pos, t in enumerate(types) if t in (0, 1)]
    out = []
    for k in range(n_asdu):
        entry = {"apci_type": "I" if k < len(i_positions) else None, "apci_tx": None, "apci_rx": None}
        if len(i_positions) == n_asdu and len(txs) == n_asdu:
            entry["apci_tx"] = _int(txs[k])
        if len(i_positions) == n_asdu and len(rxs) == len(with_rx) and k < len(i_positions):
            entry["apci_rx"] = _int(rxs[with_rx.index(i_positions[k])])
        out.append(entry)
    return out


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
    quality_flags: dict | None = None,
    asdu_index: int | None = None,
    object_index: int | None = None,
    numix: int | None = None,
    oa: int | None = None,
    apci: dict | None = None,
    header_alignment: dict | None = None,
    field_alignment: dict | None = None,
) -> dict:
    ca = address
    ca_ioa = None
    if ca not in (None, "") and ioa not in (None, ""):
        ca_ioa = f"{_int_text(ca)}.{_int_text(ioa)}"
    if apci is None:
        apci = {
            "apci_type": None,
            "apci_tx": _int(_first(_cells(row.get("iec60870_104.tx")))),
            "apci_rx": _int(_first(_cells(row.get("iec60870_104.rx")))),
        }
    quality_invalid = None if quality_flags is None else quality_flags.get("iv")
    return {
        "timestamp": _float(row.get("frame.time_epoch")),
        "frame_number": _int(row.get("frame.number")),
        "src_ip": row.get("ip.src") or None,
        "dst_ip": row.get("ip.dst") or None,
        "src_port": _int(row.get("tcp.srcport")),
        "dst_port": _int(row.get("tcp.dstport")),
        "apci_type": apci.get("apci_type") or row.get("iec60870_104.type") or None,
        "apci_tx": apci.get("apci_tx"),
        "apci_rx": apci.get("apci_rx"),
        "asdu_index": asdu_index,
        "object_index": object_index,
        "numix": numix,
        "oa": oa,
        "type_id": type_id,
        "protocol_class": asdu_class(type_id),
        "cause": None if cause in (None, "") else str(cause),
        "cot_negative": cot_negative,
        "cot_test": cot_test,
        "sq": sq,
        "select_execute": select_execute,
        "quality_invalid": quality_invalid,
        "quality_flags": quality_flags,
        "quality_good": quality_good(quality_flags),
        "ca": None if ca in (None, "") else _int_text(ca),
        "ioa": None if ioa in (None, "") else _int_text(ioa),
        "ca_ioa": ca_ioa,
        "value": value,
        "value_present": value_present,
        "alignment": alignment,
        "header_alignment": header_alignment,
        "field_alignment": field_alignment,
    }


def quality_good(flags: dict | None) -> bool | None:
    """True only when every quality bit of the element was decoded and is clear."""
    if not flags:
        return None
    if any(v is True for v in flags.values()):
        return False
    if any(v is None for v in flags.values()):
        return None
    return True


def _cells(text: str | None, *, preserve_gaps: bool = False) -> list[str]:
    if text is None or text == "":
        return []
    parts = [part.strip() for part in str(text).split(",")]
    if preserve_gaps:
        return parts
    return [part for part in parts if part != ""]


def _first(cells: list[str]):
    return cells[0] if cells else None


def _int(text) -> int | None:
    try:
        return int(text)
    except (TypeError, ValueError):
        return None


def _int_hex(text) -> int | None:
    try:
        return int(str(text), 0) if str(text).lower().startswith("0x") else int(text)
    except (TypeError, ValueError):
        return None


def _int_text(text) -> str:
    number = _int(text)
    return str(number if number is not None else text)


def _first_int(cells: list[str]) -> int | None:
    return _int(_first(cells)) if cells else None


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
