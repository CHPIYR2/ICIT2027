"""Observation semantics: evaluator-field rejection and alias collapse.

Attack labels and official event text are never features. Duplicate IPAL
attributes that carry the same value are one node, with both source ids kept.
"""
from __future__ import annotations
import collections
from .types import Observation

EVALUATOR_ATTR_KEYS = frozenset({
    'malicious', 'attack_point', 'label', 'labels', 'event_description',
    'recovery', 'attack_type', 'description',
})
ALIAS_PAIRS = (('is_closed', 'closed'), ('is_connected', 'connected'))


def reject_evaluator_fields(observations: list[Observation]) -> None:
    for obs in observations:
        attrs = obs.attrs or {}
        found = EVALUATOR_ATTR_KEYS & set(attrs)
        if found or obs.entity in EVALUATOR_ATTR_KEYS:
            raise ValueError('Evaluator-only field cannot enter the feature matrix: '
                             + ', '.join(sorted(found or {obs.entity})))


def contexts_from_point_map(raw: dict) -> dict[str, str]:
    """Map `element:attribute` to MEASUREMENT, CONFIGURATION, or AMBIGUOUS."""
    grouped: dict[str, set[str]] = collections.defaultdict(set)
    for point in raw.values():
        grouped[f"{point['element']}:{point['attribute']}"].add(point['context'])
    return {key: (next(iter(ctx)) if len(ctx) == 1 else 'AMBIGUOUS')
            for key, ctx in grouped.items()}


def apply_contexts(observations: list[Observation], contexts: dict[str, str]
                   ) -> list[Observation]:
    annotated = []
    for obs in observations:
        if obs.modality != 'physical':
            annotated.append(obs)
            continue
        attrs = dict(obs.attrs or {})
        attrs['ipal_context'] = contexts.get(obs.entity, 'UNMAPPED')
        annotated.append(Observation(obs.timestamp, obs.modality, obs.entity, obs.kind,
                                     obs.value, obs.source_id, attrs))
    return annotated


def _alias_role(entity: str):
    for alias, canonical in ALIAS_PAIRS:
        alias_suffix = ':' + alias
        canonical_suffix = ':' + canonical
        if entity.endswith(alias_suffix):
            return entity[:-len(alias_suffix)], 'alias', canonical
        if entity.endswith(canonical_suffix):
            return entity[:-len(canonical_suffix)], 'canonical', canonical
    return None


def collapse_aliases(observations: list[Observation]) -> tuple[list[Observation], dict]:
    """Drop an alias series when every shared timestamp matches the canonical one."""
    grouped: dict[tuple[str, str], list[Observation]] = collections.defaultdict(list)
    for obs in observations:
        grouped[(obs.modality, obs.entity)].append(obs)
    stems: dict[tuple[str, str], dict] = collections.defaultdict(dict)
    for (modality, entity), seq in grouped.items():
        if modality != 'physical':
            continue
        role = _alias_role(entity)
        if role is None:
            continue
        stem, which, canonical = role
        stems[(stem, canonical)][which] = (entity, seq)
    remove: set[tuple[str, str]] = set()
    collapsed = []
    disagreements = []
    for (stem, canonical_name), pair in stems.items():
        if 'alias' not in pair or 'canonical' not in pair:
            continue
        alias_entity, alias_seq = pair['alias']
        keep_entity, keep_seq = pair['canonical']
        alias_values = {obs.timestamp: obs.value for obs in alias_seq}
        keep_values = {obs.timestamp: obs.value for obs in keep_seq}
        matched = set(alias_values) & set(keep_values)
        conflict = any(abs(alias_values[t] - keep_values[t]) > 1e-5 for t in matched)
        if not matched or conflict or set(alias_values) != set(keep_values):
            disagreements.append({'canonical': keep_entity, 'alias': alias_entity,
                                  'overlapping_timestamps': len(matched), 'conflict': conflict})
            continue
        alias_ids = {obs.timestamp: obs.source_id for obs in alias_seq}
        rewritten = []
        for obs in keep_seq:
            attrs = dict(obs.attrs or {})
            attrs.setdefault('alias_source_ids', []).append(alias_ids[obs.timestamp])
            attrs['collapsed_alias'] = alias_entity
            rewritten.append(Observation(obs.timestamp, obs.modality, obs.entity, obs.kind,
                                         obs.value, obs.source_id, attrs))
        grouped[('physical', keep_entity)] = rewritten
        remove.add(('physical', alias_entity))
        collapsed.append({'canonical': keep_entity, 'alias': alias_entity,
                          'samples': len(alias_seq), 'stem': stem,
                          'canonical_attribute': canonical_name})
    kept = [obs for key, seq in grouped.items() if key not in remove for obs in seq]
    return kept, {'collapsed_aliases': collapsed, 'alias_disagreements': disagreements}
