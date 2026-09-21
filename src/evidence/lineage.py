from dataclasses import replace


def remove_sources(episode, hidden_ids):
    """Remove every descendant. Features must be recomputed from the returned episode."""
    hidden = set(hidden_ids)
    unknown = hidden - {r.evidence_id for r in episode.evidence_records}
    if unknown:
        raise ValueError("Unknown removal root")
    kept = []
    for record in episode.evidence_records:
        if record.evidence_id in hidden or any(p in hidden for p in record.parent_ids):
            hidden.add(record.evidence_id)
        else:
            kept.append(record)
    return replace(episode, evidence_records=kept).validate()
