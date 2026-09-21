"""Label-free, source-scoped records. Raw source locators live in a private resolver."""
from dataclasses import asdict, dataclass
import math
import re


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    asset_id: str | None
    observation_time: float
    reported_time: float | None
    value: float | bool | None
    unit: str | None
    source_type: str
    source_file: str
    vantage_point: str
    protocol: str
    parent_ids: tuple[str, ...]
    quality_flags: tuple[str, ...]
    transformation: str
    view: str
    fields: dict

    def to_dict(self):
        return asdict(self)


@dataclass
class EvidenceEpisode:
    episode_id: str
    asset_scope: list[str]
    time_window: tuple[float, float]
    anchor_time: float
    evidence_records: list[EvidenceRecord]
    channels: dict
    visibility_condition: str = "EN"

    @property
    def lineage_graph(self):
        return {r.evidence_id: list(r.parent_ids) for r in self.evidence_records}

    def validate(self):
        from sherlock.sanitizer import validate_record, validate_channel
        if not re.fullmatch(r"ev_[0-9a-f]{20}", self.episode_id):
            raise ValueError("Non-opaque episode ID")
        lo, hi = self.time_window
        if (lo, hi) != (self.anchor_time-60, self.anchor_time+60):
            raise ValueError("Episode violates frozen -60/+60 scope")
        if self.visibility_condition not in ('E','N','EN'):
            raise ValueError('Unknown visibility condition')
        for channel, metadata in self.channels.items():
            validate_channel(channel, metadata)
        if set(self.asset_scope) != {m['asset_id'] for m in self.channels.values()}:
            raise ValueError('Asset scope is inconsistent with static mapping')
        seen = {}
        for r in self.evidence_records:
            validate_record(r)
            if not lo <= r.observation_time < hi:
                raise ValueError("Hidden/future evidence outside episode scope")
            if r.evidence_id in seen:
                raise ValueError("Duplicate evidence ID")
            for parent in r.parent_ids:
                if parent not in seen or seen[parent].observation_time > r.observation_time:
                    raise ValueError("Missing, future, or cyclic source lineage")
                pr = seen[parent]
                expected = {'message':'packet','process':'message'}.get(r.source_type)
                if pr.source_type != expected or pr.source_file!=r.source_file or pr.vantage_point!=r.vantage_point:
                    raise ValueError('Invalid parent type/source')
            if r.source_type != "packet" and not r.parent_ids:
                raise ValueError("Derived record has no parent")
            if r.source_type == 'process':
                m = self.channels.get(r.fields['channel_id'])
                if m is None or any(m[k]!=r.fields[k] for k in ('family','attribute','context')) or m['asset_id']!=r.asset_id or m['unit']!=r.unit:
                    raise ValueError('Process record disagrees with static metadata')
            seen[r.evidence_id] = r
        return self

    def to_dict(self):
        return {**asdict(self), "lineage_graph": self.lineage_graph}

    @classmethod
    def from_dict(cls, d):
        d = dict(d)
        graph = d.pop("lineage_graph")
        d["evidence_records"] = [EvidenceRecord(**{**r, "parent_ids":tuple(r["parent_ids"]),
                                                    "quality_flags":tuple(r["quality_flags"])}) for r in d["evidence_records"]]
        episode = cls(**d).validate()
        if graph != episode.lineage_graph:
            raise ValueError("Stored lineage graph does not match records")
        return episode
