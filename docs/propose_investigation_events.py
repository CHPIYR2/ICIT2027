"""Evaluator-only proposal generator. No LLM output or classifier score is read."""
from pathlib import Path
from collections import defaultdict, Counter
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
SALT = 'investigation-candidate-v1-20260922'
INPUTS = ['data/evaluator/event_catalog.json',
          'results/exploratory-v2/audit/episode_coverage.json',
          'data/processed/v2/development_features.json',
          'data/processed/v2/held_out_features.json']
load = lambda p: json.loads((ROOT / p).read_text())
catalog = load(INPUTS[0])['events']
coverage = {r['episode_id']: r for r in load(INPUTS[1])['rows']}
features = {r['episode_id']: r['values'] for p in INPUTS[2:] for r in load(p)['rows']}
numeric_families = ['voltage', 'current', 'active_power', 'reactive_power']
feature_names = [f'e_{f}_relative_change' for f in numeric_families] + [
    'n_post_log_rate', 'n_command_log_count', 'n_activation_response_log_count',
    'n_post_max_gap_fraction', 'n_rst_log_count']


def tie(event):
    return hashlib.sha256((SALT + '|' + event['episode_id']).encode()).hexdigest()


def descriptor(event):
    eid = event['episode_id']
    cov = coverage[eid]['families']
    missing = max(1 - cov[f]['post_channels'] / cov[f]['mapped_channels'] for f in numeric_families)
    return [features[eid][f] for f in feature_names] + [missing, cov['reported_state']['post_channels']]


chosen = []
for scenario in sorted({e['scenario'] for e in catalog}):
    pool = [e for e in catalog if e['scenario'] == scenario]
    raw = {e['episode_id']: descriptor(e) for e in pool}
    assert all(v is not None for row in raw.values() for v in row)
    # Average percentile ranks within scenario prevent cross-unit/scale dominance.
    ranks = {}
    for e in pool:
        ranks[e['episode_id']] = [
            (sum(v[j] < x for v in raw.values()) + .5 * sum(v[j] == x for v in raw.values())) / len(pool)
            for j, x in enumerate(raw[e['episode_id']])]
    selected = []
    groups = defaultdict(list)
    for e in pool:
        groups[e['family_description']].append(e)
    def select(candidates, reason):
        available = [e for e in candidates if e not in selected]
        if not selected:
            best = min(available, key=tie)
        else:
            def distance(e):
                return min(sum((a-b)**2 for a,b in zip(ranks[e['episode_id']], ranks[s['episode_id']])) for s in selected)
            best = min(available, key=lambda e: (-distance(e), tie(e)))
        selected.append(best)
        chosen.append({k: best[k] for k in ('episode_id', 'scenario', 'recording', 'event_truth', 'family_description')} | {
            'partition': 'development' if scenario == '01-Basic' else 'evaluation',
            'selection_reason': reason, 'observable_descriptor': dict(zip(feature_names + ['max_numeric_post_missing_fraction', 'reported_state_post_channels'], raw[best['episode_id']]))})
    for family, candidates in sorted(groups.items()):
        quota = 1 if scenario == '01-Basic' or candidates[0]['event_truth'] == 'BENIGN' else 2
        for _ in range(quota):
            select(candidates, 'scenario × exact catalog family quota; observable-diversity maximin')
    extra = {'01-Basic': 0, '02-Semiurban': 2, '03-Rural': 1}[scenario]
    for _ in range(extra):
        select([e for e in pool if e['event_truth'] == 'BENIGN'], 'additional benign observable-diversity slot')

assert len(chosen) == 48 and len({e['episode_id'] for e in chosen}) == 48
assert Counter(e['scenario'] for e in chosen) == {'01-Basic': 16, '02-Semiurban': 18, '03-Rural': 14}
output = {'status': 'PROPOSED_NOT_FROZEN', 'access': 'EVALUATOR_ONLY; never retrieval/LLM input',
          'selection_salt': SALT, 'algorithm': 'Exact family quotas; greedy maximin squared distance of within-scenario midranks; SHA256 tie-break; no classifier predictions or LLM results.',
          'feature_order': feature_names + ['max_numeric_post_missing_fraction', 'reported_state_post_channels'],
          'inputs_sha256': {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in INPUTS},
          'rows': chosen}
(ROOT/'docs/investigation_event_candidates.proposed.json').write_text(json.dumps(output, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({'counts': dict(Counter(e['scenario'] for e in chosen)), 'recordings': dict(Counter(e['scenario']+'/'+e['recording'] for e in chosen)),
                  'truth': dict(Counter(e['partition']+'/'+e['event_truth'] for e in chosen)),
                  'numeric_missing_events': sum(e['observable_descriptor']['max_numeric_post_missing_fraction']>0 for e in chosen)},indent=2))
