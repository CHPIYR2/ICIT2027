"""View-specific export restrictions. Canonical source removal is a different API.

The network object contains only allowed headers: no episode back-reference,
application records, payload, full-window aggregates, or private parent resolver.
"""
from dataclasses import dataclass,asdict
import math
import re
from sherlock.sanitizer import validate_record

DURATIONS=(60,45,30,15)


@dataclass(frozen=True)
class TransportPacket:
    evidence_id:str
    observation_time:float
    source_endpoint:str
    destination_endpoint:str
    ip_protocol:int
    source_port:int
    destination_port:int
    tcp_flags:int

    def validate(self):
        if not re.fullmatch(r'p_[0-9a-f]{24}',self.evidence_id):raise ValueError('Non-opaque packet ID')
        if not math.isfinite(self.observation_time):raise ValueError('Invalid time')
        if self.ip_protocol!=6 or 2404 not in (self.source_port,self.destination_port):raise ValueError('Outside TCP/2404 scope')
        for endpoint in (self.source_endpoint,self.destination_endpoint):
            if not re.fullmatch(r'ep_[0-9a-f]{16}',endpoint):raise ValueError('Non-opaque endpoint')
        if type(self.tcp_flags) is not int or not 0<=self.tcp_flags<=255:raise ValueError('Invalid TCP flags')
        return self


@dataclass(frozen=True)
class NetworkProjection:
    episode_id:str
    anchor_time:float
    post_seconds:int
    packets:tuple[TransportPacket,...]

    def validate(self):
        if self.post_seconds not in DURATIONS:raise ValueError('Unapproved observability duration')
        if not re.fullmatch(r'ev_[0-9a-f]{20}',self.episode_id) or not math.isfinite(self.anchor_time):raise ValueError('Invalid episode scope')
        seen=set()
        for p in self.packets:
            p.validate()
            if p.evidence_id in seen:raise ValueError('Duplicate packet root')
            if not self.anchor_time-60<=p.observation_time<self.anchor_time+self.post_seconds:raise ValueError('Hidden/out-of-scope packet')
            seen.add(p.evidence_id)
        return self

    def restrict(self,seconds):
        if seconds not in DURATIONS or seconds>self.post_seconds:raise ValueError('Cannot recover hidden evidence')
        return NetworkProjection(self.episode_id,self.anchor_time,seconds,
                tuple(p for p in self.packets if p.observation_time<self.anchor_time+seconds)).validate()

    def lookup(self,evidence_id):
        for p in self.packets:
            if p.evidence_id==evidence_id:return asdict(p)
        raise PermissionError('Evidence is outside this visibility projection')

    def to_public_dict(self):
        return {'episode_id':self.episode_id,'anchor_time':self.anchor_time,'post_seconds':self.post_seconds,
                'visible_intervals':[[self.anchor_time-60,self.anchor_time],[self.anchor_time,self.anchor_time+self.post_seconds]],
                'packets':[asdict(p) for p in self.packets]}


def transport_projection(episode):
    """Reads packet roots only; IEC parsing/ASDU/COT never affects this projection."""
    packets=[]
    for r in episode.evidence_records:
        if r.source_type!='packet':continue
        validate_record(r)
        f=r.fields
        if f['ip_protocol']!=6 or 2404 not in (f['source_port'],f['destination_port']):continue
        packets.append(TransportPacket(r.evidence_id,r.observation_time,
            f['source_endpoint'],f['destination_endpoint'],f['ip_protocol'],
            f['source_port'],f['destination_port'],f['tcp_flags']))
    return NetworkProjection(episode.episode_id,episode.anchor_time,60,tuple(packets)).validate()


def public_evidence(episode,projection,include_e=False):
    """Future explanation boundary: no traversal to private E parents or IEC headers."""
    if projection.episode_id!=episode.episode_id or projection.anchor_time!=episode.anchor_time:
        raise ValueError('Mismatched episode and visibility')
    projection.validate()
    if include_e:
        for r in episode.evidence_records:
            if r.source_type=='process':
                validate_record(r)
                if not episode.anchor_time-60<=r.observation_time<episode.anchor_time+60:raise ValueError('E outside canonical scope')
    result=projection.to_public_dict()
    if include_e:
        result['electrical']=[{'evidence_id':r.evidence_id,'asset_id':r.asset_id,
            'observation_time':r.observation_time,'value':r.value,'unit':r.unit,
            'quality_flags':list(r.quality_flags),'fields':dict(r.fields),
            'lineage_access':'private_verifier_only'} for r in episode.evidence_records if r.source_type=='process']
    return result


def visibility_receipt(episode,full):
    """Private diagnostic IDs, never model or LLM input. Canonical E is unchanged."""
    service={p.evidence_id for p in full.packets}
    return {'access':'PRIVATE_EVALUATOR_VERIFIER_ONLY','episode_id':episode.episode_id,
        'mechanism':'N-export-view tail outage; not canonical raw-source removal',
        'anchor_time':episode.anchor_time,'E_window':list(episode.time_window),
        'outside_service_packet_ids':[r.evidence_id for r in episode.evidence_records if r.source_type=='packet' and r.evidence_id not in service],
        'semantic_denied_message_ids':[r.evidence_id for r in episode.evidence_records if r.source_type=='message'],
        'levels':{str(t):{'visible_packet_ids':[p.evidence_id for p in full.packets if p.observation_time<full.anchor_time+t],
                          'hidden_packet_ids':[p.evidence_id for p in full.packets if p.observation_time>=full.anchor_time+t],
                          'post_visible_seconds':t,'pre_visible_seconds':60} for t in DURATIONS}}
