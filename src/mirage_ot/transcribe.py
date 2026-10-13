"""Call the official ipal-transcriber. Do not reimplement IEC-104.

The command never receives events.json or --malicious. Message output is used
to check CA/IOA values against the published Sherlock state.
"""
from __future__ import annotations
import json
import re
import shutil
import struct
import subprocess
import zipfile
from pathlib import Path

_VAR_NAME = re.compile(
    r'"var"\s*:\s*\[\s*"(\d+\.\d+)"\s*\]\s*,\s*"name"\s*:\s*"([^"]+)"')


def parse_rule_names(rules_text: str) -> dict[str, str]:
    """Read CA.IOA -> state-name pairs without executing the rules file."""
    found = dict(_VAR_NAME.findall(rules_text))
    if not found:
        raise ValueError('No IPAL var/name rules found')
    return found


def transcriber_command(*, executable: str, pcap: Path, output: Path,
                        rules: Path | None = None) -> list[str]:
    argv = [executable, '--protocols', 'iec104', '--pcap', str(pcap),
            '--ipal.output', str(output), '--log', 'WARNING']
    if rules is not None:
        argv.extend(['--rules', str(rules)])
    if '--malicious' in argv or '--malicious.default' in argv:
        raise RuntimeError('Evaluator event labels are not transcriber inputs')
    if any(Path(part).name == 'events.json' for part in argv):
        raise RuntimeError('events.json cannot be passed to the transcriber')
    return argv


def slice_classic_pcap(source: Path, dest: Path, start: float, end: float) -> int:
    """Copy classic Ethernet PCAP records inside [start, end). Not a protocol decode."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    kept = 0
    with source.open('rb') as handle, dest.open('wb') as out:
        header = handle.read(24)
        if header[:4] != b'\xd4\xc3\xb2\xa1':
            raise ValueError('Need a classic little-endian microsecond PCAP')
        out.write(header)
        record = struct.Struct('<IIII')
        while True:
            raw = handle.read(16)
            if not raw:
                break
            if len(raw) != 16:
                raise ValueError('Truncated PCAP record')
            secs, sub, incl, _orig = record.unpack(raw)
            blob = handle.read(incl)
            if len(blob) != incl:
                raise ValueError('Truncated PCAP payload')
            timestamp = secs + sub / 1_000_000
            if start <= timestamp < end:
                out.write(raw)
                out.write(blob)
                kept += 1
    return kept


def extract_member(archive: Path, member: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf, zf.open(member) as src, dest.open('wb') as out:
        shutil.copyfileobj(src, out)


def iter_concatenated_json(path: Path):
    decoder = json.JSONDecoder()
    blob = path.read_text(encoding='utf-8')
    index = 0
    while index < len(blob):
        while index < len(blob) and blob[index].isspace():
            index += 1
        if index >= len(blob):
            break
        obj, end = decoder.raw_decode(blob, index)
        yield obj
        index = end


def compare_messages_to_state(messages: list[dict], rules: dict[str, str],
                              states: list[tuple[float, dict]]) -> dict:
    """Match each transcribed CA.IOA value to the next official timeslice."""
    states = sorted(states)
    activities: dict[str, int] = {}
    types: dict[str, int] = {}
    compared = matched = unmatched = 0
    examples = []
    label_fields = 0
    for message in messages:
        if message.get('malicious') not in (None, False):
            label_fields += 1
            continue
        activity = str(message.get('activity', ''))
        activities[activity] = activities.get(activity, 0) + 1
        kind = str(message.get('type', ''))
        types[kind] = types.get(kind, 0) + 1
        data = message.get('data') or {}
        timestamp = float(message['timestamp'])
        later = next(((t, row) for t, row in states if t + 1e-6 >= timestamp), None)
        for key, value in data.items():
            if not re.fullmatch(r'\d+\.\d+', str(key)):
                continue
            name = rules.get(str(key))
            if name is None or later is None or name not in later[1]:
                continue
            if isinstance(value, bool):
                value = float(value)
            if not isinstance(value, (int, float)):
                continue
            official = later[1][name]
            if isinstance(official, bool):
                official = float(official)
            if not isinstance(official, (int, float)):
                continue
            compared += 1
            ok = abs(float(value) - float(official)) <= 1e-3 * max(1.0, abs(float(official)))
            matched += int(ok)
            unmatched += int(not ok)
            if len(examples) < 6:
                examples.append({'ca_ioa': key, 'name': name, 'activity': activity,
                                 'type': kind, 'transcribed': float(value),
                                 'official_state': float(official), 'match': ok,
                                 'message_time': timestamp, 'state_time': later[0]})
    return {'messages': len(messages), 'activities': activities, 'iec104_types': types,
            'compared_points': compared, 'matched_points': matched,
            'unmatched_points': unmatched,
            'match_rate': (matched / compared) if compared else None,
            'messages_with_positive_malicious_flag': label_fields,
            'examples': examples}


def find_transcriber(explicit: str | None = None) -> str:
    if explicit:
        return explicit
    found = shutil.which('ipal-transcriber')
    if not found:
        raise FileNotFoundError(
            'ipal-transcriber is not on PATH. Install ipal-ids/ipal_transcriber '
            'and Wireshark/tshark; do not substitute a local IEC-104 decoder.')
    return found


def run_transcriber(argv: list[str]) -> None:
    if '--malicious' in argv or any(Path(part).name == 'events.json' for part in argv):
        raise RuntimeError('Refusing evaluator labels in the transcriber command')
    subprocess.run(argv, check=True)


def _state_rows(archive: Path, member: str, start: float, end: float):
    import gzip
    rows = []
    with zipfile.ZipFile(archive) as zf, zf.open(member) as raw, gzip.GzipFile(fileobj=raw) as gz:
        for line in gz:
            if not line.strip():
                continue
            marker = line.find(b'"timestamp":')
            stop = line.find(b',', marker)
            timestamp = float(line[marker + 12:stop])
            if timestamp < start:
                continue
            if timestamp >= end + 2:
                break
            row = json.loads(line)
            rows.append((float(row['timestamp']), row['state']))
    return rows


def check_archive_window(*, archive: Path, pcap_member: str, rules_member: str,
                         state_member: str, start: float, end: float, work: Path,
                         executable: str | None = None) -> dict:
    """Transcribe one PCAP slice with official IPAL and compare it to published state."""
    work.mkdir(parents=True, exist_ok=True)
    full = work / 'source.pcap'
    extract_member(archive, pcap_member, full)
    sliced = work / 'slice.pcap'
    kept = slice_classic_pcap(full, sliced, start, end)
    full.unlink()
    rules_path = work / 'rules.py'
    extract_member(archive, rules_member, rules_path)
    rules = parse_rule_names(rules_path.read_text(encoding='utf-8'))
    messages_path = work / 'messages.json'
    argv = transcriber_command(executable=find_transcriber(executable), pcap=sliced,
                               output=messages_path)
    run_transcriber(argv)
    messages = list(iter_concatenated_json(messages_path))
    report = compare_messages_to_state(messages, rules, _state_rows(archive, state_member, start, end))
    report.update({'pcap_packets_in_slice': kept, 'rule_names': len(rules),
                   'transcriber_argv': argv, 'events_json_passed': False,
                   'malicious_flag_passed': False,
                   'state_member': state_member, 'pcap_member': pcap_member,
                   'rules_member': rules_member})
    return report
