"""Exactly five approved header-only summaries, recomputed from visible roots."""
import math
from sherlock.sanitizer import validate_features

NAMES=['nt_post_log_packet_rate','nt_log_packet_rate_change','nt_rst_log_count',
       'nt_post_max_packet_gap_fraction','nt_endpoint_log_count']


def extract_transport(projection):
    projection.validate()
    t0,T=projection.anchor_time,projection.post_seconds
    pre=[p for p in projection.packets if p.observation_time<t0]
    post=[p for p in projection.packets if p.observation_time>=t0]
    times=sorted([t0,t0+T]+[p.observation_time for p in post])
    endpoints={endpoint for p in post for endpoint in (p.source_endpoint,p.destination_endpoint)}
    return validate_features(dict(zip(NAMES,[math.log1p(len(post)/T),
        math.log1p(len(post)/T)-math.log1p(len(pre)/60),
        math.log1p(sum(bool(p.tcp_flags&4) for p in post)),
        max(b-a for a,b in zip(times,times[1:]))/T,math.log1p(len(endpoints))])),NAMES)
