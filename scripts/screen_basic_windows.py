"""Count IEC-104 ASDU kinds per window directly from raw Sherlock PCAPs.

Input is a JSON list of {"episode_id", "start", "end"} (times only). Used to pick
windows without control commands; the reconstruction never sees this file.
"""
from __future__ import annotations
import argparse
import collections
import json
import struct
import zipfile
from pathlib import Path
from mirage_ot.etgi.evidence.iec104_raw import _tcp_payload, decode_apdus

PCAPS = ("switch-n302-pcap-mir2.pcap", "switch-n318-pcap-mir3.pcap")


def _frames(blob: bytes):
    endian, units = {b"\xd4\xc3\xb2\xa1": ("<", 1e6), b"\x4d\x3c\xb2\xa1": ("<", 1e9)}[blob[:4]]
    record = struct.Struct(endian + "IIII")
    offset = 24
    while offset + 16 <= len(blob):
        secs, sub, incl, _ = record.unpack_from(blob, offset)
        offset += 16
        yield secs + sub / units, blob[offset:offset + incl]
        offset += incl


def screen(archive: Path, recording: str, windows: list[dict], context: float) -> list[dict]:
    spans = [(w["episode_id"], float(w["start"]) - context, float(w["end"])) for w in windows]
    stats = {w["episode_id"]: {"control_by_type_cause": collections.Counter(), "monitor_by_type_cause": collections.Counter(),
                               "tcp_flags": collections.Counter()} for w in windows}
    with zipfile.ZipFile(archive) as zf:
        for name in PCAPS:
            blob = zf.read(f"01-Basic/raw/{recording}/pcap/{name}")
            vantage = name.split("-")[1]
            for ts, frame in _frames(blob):
                hits = [ep for ep, a, b in spans if a <= ts < b]
                if not hits:
                    continue
                parsed = _tcp_payload(frame)
                if parsed is None:
                    continue
                _src, _dst, sport, dport, payload = parsed
                if 2404 not in (sport, dport) or not payload:
                    continue
                objs, _ = decode_apdus(payload)
                for ep in hits:
                    for o in objs:
                        key = f"{vantage}:t{o['type_id']}:c{o['cause']}"
                        bucket = "control_by_type_cause" if 45 <= (o["type_id"] or 0) <= 69 else "monitor_by_type_cause"
                        stats[ep][bucket][key] += 1
    out = []
    for w in windows:
        s = stats[w["episode_id"]]
        out.append({
            "episode_id": w["episode_id"], "start": w["start"], "end": w["end"],
            "control_objects": sum(s["control_by_type_cause"].values()),
            "control_by_type_cause": dict(s["control_by_type_cause"]),
            "monitor_by_type_cause": dict(s["monitor_by_type_cause"]),
        })
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=Path("data/raw/sherlock/v3/01-Basic.zip"))
    parser.add_argument("--recording", default="test")
    parser.add_argument("--windows", type=Path, required=True)
    parser.add_argument("--context-seconds", type=float, default=15.0)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    windows = json.loads(args.windows.read_text())
    result = screen(args.archive, args.recording, windows, args.context_seconds)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    for row in result:
        print(row["episode_id"], round(float(row["end"]) - float(row["start"]), 1), row["control_objects"],
              {k: v for k, v in row["monitor_by_type_cause"].items() if not k.endswith(":c1")})


if __name__ == "__main__":
    main()
