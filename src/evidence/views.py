def records_for_view(episode, view):
    if view not in ("E", "N", "EN"):
        raise ValueError("Unknown visibility condition")
    return [r for r in episode.evidence_records if view == "EN" or r.view == view]
