"""Layer-by-layer audit of IEC-104 fields and IPAL lineage.

For every information object found in the raw TCP payload, each field is traced
through four layers and assigned the first layer where it is lost:

    raw_absent           the element type does not carry the field in the packet
    tshark_not_decoded   the octet is in the packet but tshark emitted no matching field
    parser_not_read      tshark emitted it but the parser output has no value
    db_not_stored        the parser produced it but the database row does not hold it

Mismatches (a value that disagrees with the raw octets) are kept separate from
absence. IPAL lineage is checked against the raw state records; it is never
inferred from time proximity.
"""
from __future__ import annotations
import collections
import gzip
import hashlib
import importlib.util
import io
import json
import sqlite3
import subprocess
import sys
import zipfile
from pathlib import Path
from . import iec104, iec104_raw

FIELDS = ("cot_negative", "cot_test", "select_execute", "quality_iv", "quality_other", "value")
_HEADER_TSHARK = {"cot_negative": "iec60870_asdu.nega", "cot_test": "iec60870_asdu.test"}
_PACKET_REFERENCE_KEYS = {"id", "frame", "frame_number", "packet", "packet_id", "src", "dest", "source",
                          "destination", "seq", "tcp_seq", "parent", "parent_id", "flow"}


def load_parser_from_git(repo_root: Path, commit: str):
    """Load `evidence/iec104.py` as it was at `commit`, for auditing an index built by that code."""
    source = subprocess.check_output(
        ["git", "show", f"{commit}:src/mirage_ot/etgi/evidence/iec104.py"], cwd=repo_root, text=True,
    )
    name = f"_iec104_legacy_{commit}"
    spec = importlib.util.spec_from_loader(name, loader=None)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    exec(compile(source, f"{commit}:iec104.py", "exec"), module.__dict__)
    return module


def object_class(type_id: int | None, cause: int | None) -> str:
    if type_id is None:
        return "other"
    if 45 <= type_id <= 64:
        return {6: "control_command", 7: "control_confirmation", 10: "control_termination"}.get(cause, "control_other")
    if type_id in (1, 2, 3, 4, 30, 31):
        return "state_report" if cause == 3 else "state_point_other"
    if type_id in (9, 10, 11, 12, 13, 14, 34, 35, 36):
        return "measurement"
    return "other"


def _raw_field(obj: dict, field: str):
    """Return (applicable, value) from the byte-level decode."""
    type_id = obj.get("type_id")
    if obj.get("layout") == "type_not_modeled":
        return False, None
    if field in ("cot_negative", "cot_test"):
        return True, obj[field]
    if field == "select_execute":
        return (type_id in iec104._SE_FIELD), obj.get("select_execute")
    flags = obj.get("quality_flags")
    if field == "quality_iv":
        return (flags is not None), (flags or {}).get("iv")
    if field == "quality_other":
        return (flags is not None), ({k: v for k, v in flags.items() if k != "iv"} if flags else None)
    if field == "value":
        return (type_id in iec104._VALUE_FIELD), obj.get("value")
    raise KeyError(field)


def _parsed_field(obj: dict, field: str):
    if field in ("cot_negative", "cot_test", "select_execute"):
        return obj.get(field)
    flags = obj.get("quality_flags") if isinstance(obj.get("quality_flags"), dict) else None
    if field == "quality_iv":
        if flags is not None:
            return flags.get("iv")
        return obj.get("quality_invalid") if isinstance(obj.get("quality_invalid"), bool) else None
    if field == "quality_other":
        if flags is None:
            return None
        others = {k: v for k, v in flags.items() if k != "iv"}
        return None if any(v is None for v in others.values()) else others
    if field == "value":
        return obj.get("value") if obj.get("value_present") else None
    raise KeyError(field)


def _same(a, b) -> bool:
    if isinstance(a, float) or isinstance(b, float):
        try:
            a_f, b_f = float(a), float(b)
        except (TypeError, ValueError):
            return False
        return abs(a_f - b_f) <= max(1e-9, 1e-6 * max(abs(a_f), abs(b_f)))
    return a == b


def _tshark_field_status(frame_row: dict | None, frame_objects: list[dict]) -> dict:
    """Status per (object position, audit field) for one frame, judged on tshark output alone."""
    status: dict[tuple[int, str], str] = {}
    if frame_row is None:
        for pos, obj in enumerate(frame_objects):
            for field in FIELDS:
                status[(pos, field)] = "tshark_not_decoded"
        return status

    def compare(tshark_name: str, expected: list, parse) -> str:
        cells = iec104._cells(frame_row.get(tshark_name), preserve_gaps=True)
        if not cells or not any(cells):
            return "tshark_not_decoded"
        if len(cells) != len(expected):
            return "tshark_mismatch"
        return "decoded" if all(_same(parse(c), e) for c, e in zip(cells, expected)) else "tshark_mismatch"

    asdus = collections.OrderedDict()
    for pos, obj in enumerate(frame_objects):
        asdus.setdefault(obj["asdu_index"], obj)
    for field, name in _HEADER_TSHARK.items():
        result = compare(name, [o[field] for o in asdus.values()], iec104._bool)
        for pos in range(len(frame_objects)):
            status[(pos, field)] = result

    by_tshark: dict[str, list[tuple[int, object]]] = collections.defaultdict(list)
    for pos, obj in enumerate(frame_objects):
        type_id = obj.get("type_id")
        if type_id in iec104._SE_FIELD:
            by_tshark[iec104._SE_FIELD[type_id]].append((pos, obj.get("select_execute") == "select"))
        prefix = iec104._QUALITY_PREFIX.get(type_id)
        if prefix and obj.get("quality_flags"):
            for bit in iec104._QUALITY_BITS[prefix]:
                by_tshark[f"iec60870_asdu.{prefix}.{bit}"].append((pos, obj["quality_flags"][bit]))
        if type_id in iec104._VALUE_FIELD:
            by_tshark[iec104._VALUE_FIELD[type_id][1]].append((pos, obj.get("value")))
    value_names = {tshark: name for name, tshark in iec104._VALUE_FIELD.values()}
    field_result = {}
    for name, items in by_tshark.items():
        if name in value_names:
            vname = value_names[name]
            parse = lambda c, vname=vname: iec104._parse_value(vname, c)  # noqa: E731
        else:
            parse = iec104._bool
        field_result[name] = compare(name, [v for _, v in items], parse)

    for pos, obj in enumerate(frame_objects):
        type_id = obj.get("type_id")
        if type_id in iec104._SE_FIELD:
            status[(pos, "select_execute")] = field_result[iec104._SE_FIELD[type_id]]
        prefix = iec104._QUALITY_PREFIX.get(type_id)
        if prefix and obj.get("quality_flags"):
            status[(pos, "quality_iv")] = field_result[f"iec60870_asdu.{prefix}.iv"]
            others = [field_result[f"iec60870_asdu.{prefix}.{bit}"]
                      for bit in iec104._QUALITY_BITS[prefix] if bit != "iv"]
            status[(pos, "quality_other")] = next((s for s in others if s != "decoded"), "decoded")
        if type_id in iec104._VALUE_FIELD:
            status[(pos, "value")] = field_result[iec104._VALUE_FIELD[type_id][1]]
    return status


def _key(ts, ca_ioa, type_id, cause) -> tuple:
    return (round(float(ts), 6), ca_ioa, None if type_id is None else int(type_id),
            None if cause in (None, "") else int(cause))


def _db_rows(db_path: Path, vantage: str) -> dict[tuple, list[dict]]:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    out: dict[tuple, list[dict]] = collections.defaultdict(list)
    for row in conn.execute("SELECT * FROM evidence WHERE kind = 'iec104_asdu' AND vantage = ?", (vantage,)):
        payload = json.loads(row["payload_json"])
        record = {**payload, "value": row["value"], "value_present": bool(row["value_present"])}
        out[_key(row["timestamp"], row["ca_ioa"], payload.get("type_id"), payload.get("cause"))].append(record)
    conn.close()
    return out


def audit_slices(slice_dir: Path, pipelines: list[dict]) -> dict:
    """`pipelines`: [{"label", "parser" (module with decode_slice/split_fields), "db" (path)}]."""
    summary = {p["label"]: collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
               for p in pipelines}
    examples = {p["label"]: collections.defaultdict(list) for p in pipelines}
    raw_stats = {"objects": 0, "frames_with_iec104": 0, "segment_status": collections.Counter(),
                 "by_class": collections.Counter(), "bits_set": collections.Counter(),
                 "select_execute": collections.Counter()}
    slices = {}
    full_parser_fields = list(iec104._FIELDS)
    for pcap in sorted(Path(slice_dir).glob("*.pcap")):
        vantage = pcap.stem
        slices[vantage] = hashlib.sha256(pcap.read_bytes()).hexdigest()
        raw = iec104_raw.decode_pcap(pcap)
        tshark_rows, _ = iec104.decode_slice(pcap)
        tshark_by_frame = {iec104._int(r.get("frame.number")): r for r in tshark_rows}
        frames: dict[int, list[dict]] = collections.defaultdict(list)
        for obj in raw:
            frames[obj["frame_number"]].append(obj)
        raw_stats["frames_with_iec104"] += len(frames)
        for obj in raw:
            raw_stats["objects"] += 1
            raw_stats["segment_status"][obj["segment_status"]] += 1
            raw_stats["by_class"][object_class(obj.get("type_id"), obj.get("cause"))] += 1
            for bit in ("cot_negative", "cot_test"):
                raw_stats["bits_set"][bit] += int(bool(obj.get(bit)))
            for bit, value in (obj.get("quality_flags") or {}).items():
                raw_stats["bits_set"][f"quality_{bit}"] += int(bool(value))
            if obj.get("select_execute"):
                raw_stats["select_execute"][obj["select_execute"]] += 1
        tshark_status = {}
        for frame_number, objs in frames.items():
            per = _tshark_field_status(tshark_by_frame.get(frame_number), objs)
            for (pos, field), value in per.items():
                tshark_status[(frame_number, pos, field)] = value

        for pipe in pipelines:
            parser = pipe["parser"]
            rows, _ = parser.decode_slice(pcap)
            parsed: dict[tuple, list[dict]] = collections.defaultdict(list)
            for row in rows:
                for obj in parser.split_fields(row):
                    if obj.get("timestamp") is None:
                        continue
                    parsed[_key(obj["timestamp"], obj.get("ca_ioa"), obj.get("type_id"), obj.get("cause"))].append(obj)
            db = _db_rows(Path(pipe["db"]), vantage)
            for frame_number, objs in frames.items():
                for pos, obj in enumerate(objs):
                    cls = object_class(obj.get("type_id"), obj.get("cause"))
                    key = _key(obj["timestamp"], f"{obj['ca']}.{obj['ioa']}" if obj.get("ioa") is not None else None,
                               obj.get("type_id"), obj.get("cause"))
                    parsed_obj = (parsed.get(key) or [None])[0]
                    db_obj = (db.get(key) or [None])[0]
                    for field in FIELDS:
                        applicable, raw_value = _raw_field(obj, field)
                        if not applicable:
                            category = "raw_absent"
                        else:
                            t_status = tshark_status.get((frame_number, pos, field), "tshark_not_decoded")
                            if t_status != "decoded":
                                category = t_status
                            elif parsed_obj is None:
                                category = "parser_object_missing"
                            else:
                                p_value = _parsed_field(parsed_obj, field)
                                if p_value is None:
                                    category = "parser_not_read"
                                elif not _same(p_value, raw_value):
                                    category = "parser_mismatch"
                                elif db_obj is None:
                                    category = "db_row_missing"
                                else:
                                    d_value = _parsed_field(db_obj, field)
                                    if d_value is None:
                                        category = "db_not_stored"
                                    elif not _same(d_value, raw_value):
                                        category = "db_mismatch"
                                    else:
                                        category = "present_all_layers"
                        summary[pipe["label"]][cls][field][category] += 1
                        bucket = examples[pipe["label"]][f"{cls}.{field}.{category}"]
                        if category != "present_all_layers" and len(bucket) < 2:
                            bucket.append({"vantage": vantage, "frame_number": frame_number,
                                           "ca_ioa": key[1], "type_id": obj.get("type_id"),
                                           "cause": obj.get("cause"), "raw": raw_value})
    return {
        "layers": ["raw_tcp_payload", "tshark_fields", "parser_output", "database_row"],
        "categories": ["raw_absent", "tshark_not_decoded", "tshark_mismatch", "parser_object_missing",
                       "parser_not_read", "parser_mismatch", "db_row_missing", "db_not_stored",
                       "db_mismatch", "present_all_layers"],
        "tshark_fields_requested": full_parser_fields,
        "slice_sha256": slices,
        "raw": {k: (dict(v) if isinstance(v, collections.Counter) else v) for k, v in raw_stats.items()},
        "pipelines": {
            label: {cls: {field: dict(counter) for field, counter in fields.items()}
                    for cls, fields in classes.items()}
            for label, classes in summary.items()
        },
        "examples": {label: dict(v) for label, v in examples.items()},
    }


def audit_ipal_lineage(archive: Path, state_member: str, start: float, end: float, db_paths: dict) -> dict:
    """Check whether IPAL state rows carry any reference to a source packet."""
    keys: collections.Counter = collections.Counter()
    timestamps: list[float] = []
    with zipfile.ZipFile(archive) as zf, zf.open(state_member) as handle:
        stream = gzip.open(handle) if state_member.endswith(".gz") else handle
        for line in io.TextIOWrapper(stream, encoding="utf-8"):
            record = json.loads(line)
            ts = float(record.get("timestamp"))
            if ts >= end:
                break
            if ts < start:
                continue
            keys.update(record.keys())
            timestamps.append(ts)
    gaps = sorted(b - a for a, b in zip(timestamps, timestamps[1:]))
    fractions = collections.Counter(round(ts - int(ts), 6) for ts in timestamps)
    db_report = {}
    for label, path in db_paths.items():
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        total, with_parent = conn.execute(
            "SELECT COUNT(*), SUM(parent_evidence_id IS NOT NULL) FROM evidence WHERE kind = 'electrical_update'",
        ).fetchone()
        lineage_tags = collections.Counter(
            json.loads(r["payload_json"]).get("packet_lineage", "not_recorded")
            for r in conn.execute("SELECT payload_json FROM evidence WHERE kind = 'electrical_update'")
        )
        exact, compared, nearest = 0, 0, []
        for row in conn.execute(
            "SELECT timestamp, ca_ioa FROM evidence WHERE kind = 'electrical_update' AND ca_ioa IS NOT NULL",
        ):
            hit = conn.execute(
                """SELECT MIN(ABS(timestamp - ?)) AS d FROM evidence
                   WHERE kind = 'iec104_asdu' AND ca_ioa = ?""",
                (row["timestamp"], row["ca_ioa"]),
            ).fetchone()
            if hit["d"] is None:
                continue
            compared += 1
            nearest.append(hit["d"])
            exact += int(hit["d"] <= 1e-6)
        nearest.sort()
        conn.close()
        db_report[label] = {
            "electrical_update_rows": total,
            "rows_with_parent_evidence_id": with_parent or 0,
            "packet_lineage_tags": dict(lineage_tags),
            "rows_compared_to_same_ca_ioa_iec104": compared,
            "exact_timestamp_matches": exact,
            "nearest_iec104_dt_seconds": {
                "min": nearest[0] if nearest else None,
                "median": nearest[len(nearest) // 2] if nearest else None,
            },
        }
    packet_keys = sorted(_PACKET_REFERENCE_KEYS & set(keys))
    return {
        "state_member": state_member,
        "records_in_window": len(timestamps),
        "record_keys": sorted(keys),
        "packet_reference_keys_found": packet_keys,
        "record_interval_seconds": {"min": gaps[0] if gaps else None,
                                    "median": gaps[len(gaps) // 2] if gaps else None},
        "distinct_fractional_seconds": len(fractions),
        "databases": db_report,
        "conclusion": (
            "raw_absent: IPAL state records carry no packet reference; they are periodic state snapshots. "
            "No parent lineage can be established, so no time-based parent is assigned."
            if not packet_keys else "packet reference keys present; lineage can be checked"
        ),
    }
