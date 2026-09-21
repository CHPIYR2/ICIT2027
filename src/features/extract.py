"""Fixed, dimensionless episode summaries. No labels, paths, or IDs enter X."""
import math
from collections import defaultdict
from statistics import fmean

from sherlock.sanitizer import validate_features

FLOORS = {'voltage': .01, 'current': 1., 'active_power': 1000., 'reactive_power': 1000.}
FAMILIES = (*FLOORS, 'reported_state')
E_NAMES = [f'e_{f}_relative_change' for f in FLOORS] + [f'e_{f}_post_missing' for f in FAMILIES] + ['e_state_changed_fraction']
N_NAMES = ['n_post_log_rate', 'n_log_rate_change', 'n_command_log_count',
           'n_activation_response_log_count', 'n_rst_log_count', 'n_post_max_gap_fraction',
           'n_u_log_count', 'n_endpoint_log_count']


def extract(episode, view='EN'):
    if view not in ('E', 'N', 'EN'):
        raise ValueError('Unknown view')
    episode.validate()
    t0 = episode.anchor_time
    values = {}
    if 'E' in view:
        observations = defaultdict(lambda: [[], []])
        for r in episode.evidence_records:
            if r.view == 'E' and r.value is not None and not r.quality_flags:
                observations[r.fields['channel_id']][int(r.observation_time >= t0)].append(r.value)
        changes = defaultdict(list)
        total = defaultdict(int)
        missing = defaultdict(int)
        for channel, metadata in episode.channels.items():
            family = metadata['family']
            pre, post = observations[channel]
            total[family] += 1
            missing[family] += not bool(post)
            if pre and post:
                if family == 'reported_state':
                    changes[family].append(float(pre[-1] != post[-1]))
                else:
                    baseline = fmean(pre)
                    changes[family].append(abs(fmean(post)-baseline)/max(abs(baseline), FLOORS[family]))
        for family in FLOORS:
            values[f'e_{family}_relative_change'] = max(changes[family]) if changes[family] else None
        for family in FAMILIES:
            values[f'e_{family}_post_missing'] = missing[family]/total[family] if total[family] else None
        values['e_state_changed_fraction'] = fmean(changes['reported_state']) if changes['reported_state'] else None
    if 'N' in view:
        messages = [r for r in episode.evidence_records if r.source_type == 'message']
        post = [r for r in messages if r.observation_time >= t0]
        pre_count = len(messages)-len(post)
        packets = [r for r in episode.evidence_records if r.source_type == 'packet' and
                   r.observation_time >= t0 and 2404 in (r.fields['source_port'], r.fields['destination_port'])]
        endpoints = {r.fields[k] for r in packets for k in ('source_endpoint','destination_endpoint') if r.fields[k] is not None}
        times = sorted([t0, episode.time_window[1]]+[r.observation_time for r in post])
        command = lambda r: r.fields['asdu_type'] in range(45, 52) if r.fields['asdu_type'] is not None else False
        values.update(zip(N_NAMES, [
            math.log1p(len(post)/60), math.log1p(len(post)/60)-math.log1p(pre_count/60),
            math.log1p(sum(command(r) and r.fields['cause_of_transmission'] == 6 for r in post)),
            math.log1p(sum(command(r) and r.fields['cause_of_transmission'] == 7 for r in post)),
            math.log1p(sum(bool(r.fields['tcp_flags'] & 4) for r in packets)),
            max(b-a for a,b in zip(times,times[1:]))/60,
            math.log1p(sum(r.fields['apci_format'] == 'U' for r in post)), math.log1p(len(endpoints))]))
    return validate_features(values, (E_NAMES if 'E' in view else [])+(N_NAMES if 'N' in view else []))
