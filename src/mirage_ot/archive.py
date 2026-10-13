"""ZIP-native, read-only Sherlock data access: no large archive extraction."""
import json
import zipfile
from pathlib import Path
from typing import Iterator
from .ipal import iter_state
from .pcap import iter_pcap
from .types import Observation


def inspect_archive(path: Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        files = archive.infolist()
    states = [f.filename for f in files if f.filename.endswith('.state.gz')]
    captures = [f.filename for f in files if f.filename.endswith(('.pcap', '.pcap.gz'))]
    return {'archive': str(path), 'members': len(files),
            'state_members': states, 'pcap_members': captures,
            'physical_zip_present': any(f.filename.endswith('physical.zip') for f in files)}


def load_selected(archive_path: Path, *, state_member: str | None,
                  pcap_members: list[str], start: float | None, end: float | None,
                  max_rows: int | None = None, max_packets: int | None = None
                  ) -> Iterator[Observation]:
    """Pass exact archive member names; never auto-open `physical.zip`."""
    with zipfile.ZipFile(archive_path) as zf:
        names = set(zf.namelist())
        selected = ([state_member] if state_member else []) + list(pcap_members)
        if not selected:
            raise ValueError('Explicit --state-member or --pcap-member required')
        for member in selected:
            if member not in names:
                raise FileNotFoundError(f'No member {member!r} in {archive_path}')
            if member.lower().endswith('physical.zip') or '/physical' in member.lower():
                raise ValueError('Simulator physical ground truth blocked in input loader')
        if state_member:
            with zf.open(state_member) as f:
                yield from iter_state(f, source=f'{archive_path.name}:{state_member}',
                                      start=start, end=end, max_rows=max_rows)
        for member in pcap_members:
            with zf.open(member) as f:
                yield from iter_pcap(f, source=f'{archive_path.name}:{member}',
                                     start=start, end=end, max_packets=max_packets)
