"""Unreviewed ontology feasibility counts, not gold, performance, or verification."""
from collections import Counter
from retrieval.investigation_retriever import channel_groups, pair_for_channel, valid_e

CLAIM_TYPES=('network_activity','command_observed','acknowledgement_observed','communication_gap',
    'reported_value','reported_change','reported_state_change','electrical_change','temporal_association',
    'asset_relationship','security_indicator','security_interpretation','unknown')


def supportability(public):
    records=public['records'];groups=channel_groups(public)
    messages=[r for r in records if r['source_type']=='message']
    packets=[r for r in records if r['source_type']=='packet']
    commands=[r for r in messages if r['fields']['asdu_type'] in range(45,52) and r['fields']['cause_of_transmission']==6]
    pairs=[pair_for_channel(values) for values in groups.values()]
    numerical=sum(p is not None and p[0]['fields']['family']!='reported_state' for p in pairs)
    states=sum(p is not None and p[0]['fields']['family']=='reported_state' for p in pairs)
    valid=[r for r in records if valid_e(r)]
    acknowledgements=sum(bool((r['fields']['tcp_flags'] or 0)&16) for r in packets)+sum(r['fields']['apci_format']=='S' or (r['fields']['asdu_type'] in range(45,52) and r['fields']['cause_of_transmission']==7) for r in messages)
    values={'network_activity':len(messages)+len(packets),'command_observed':len(commands),
        'acknowledgement_observed':acknowledgements,'communication_gap':1 if 'N' in public['scope']['view'] else 0,
        'reported_value':len(valid),'reported_change':numerical,'reported_state_change':states,
        'electrical_change':numerical,'temporal_association':sum(any(e['observation_time']>n['observation_time'] for e in valid) for n in commands),
        'asset_relationship':len(groups),'security_indicator':0,'security_interpretation':0,'unknown':7}
    missing_pairs=sum(m['family']!='reported_state' and (c not in groups or pair_for_channel(groups[c]) is None) for c,m in public['metadata'].items())
    insufficient={'network_activity':0,'command_observed':int(not commands),'acknowledgement_observed':int(not acknowledgements),
        'communication_gap':0,'reported_value':len(public['metadata'])-len(groups),'reported_change':missing_pairs,
        'reported_state_change':sum(m['family']=='reported_state' and (c not in groups or pair_for_channel(groups[c]) is None) for c,m in public['metadata'].items()),
        'electrical_change':missing_pairs,'temporal_association':len(commands),'asset_relationship':len(commands),
        'security_indicator':1,'security_interpretation':4,'unknown':0}
    result=[]
    for kind in CLAIM_TYPES:
        result.append({'claim_type':kind,'review_status':'DRAFT_UNREVIEWED',
            'supportable_candidate_examples':values[kind],'insufficient_probe_examples':insufficient[kind],
            'human_confirmed_supportable_examples':None,'human_confirmed_insufficient_examples':None,
            'requires_author_review':values[kind]==0,
            'mechanical_checkability':'limited primitives only; human review of meaning required' if kind.startswith('security_') else 'finite evidence consistency checks possible; not implemented as B3',
            'ambiguities':{'reported_state_change':'Count is first observed unequal adjacent pair per channel; missing baseline is not unchanged.',
                'asset_relationship':'E channel→asset available; command→asset not exported pending amendment.',
                'temporal_association':'Count is requests with any later valid E observation, episode-level only; not asset-linked or causal.',
                'security_indicator':'Primitive observations are available, but meaningful security relevance is not human established.',
                'security_interpretation':'No automatic positive security conclusion; four stronger-inference probes are insufficient.',
                'communication_gap':'Complete captured-packet query only, not physical outage.',
                'unknown':'Seven fixed unsupported-conclusion topics; not seven independent observed events.'}.get(kind,'Candidate counts are evidence-level opportunities, not independent gold facts.'),
            'duplicate_alias_issue':'reported_change and electrical_change share the same pairs; one gold fact maximum' if kind in ('reported_change','electrical_change') else 'Deduplicate semantically and by shared lineage during human review.',
            'insufficient_probe_definition':{'reported_value':'mapped channels without quality-valid observed value',
                'reported_state_change':'mapped state channels without observed unequal, time-ordered pair',
                'reported_change':'mapped numeric channels without a qualifying pair; diagnostic only',
                'electrical_change':'same mapped numeric pair deficit; not a gold denominator',
                'asset_relationship':'one unavailable command-target probe per request',
                'temporal_association':'one unsupported command→E causal probe per request',
                'security_indicator':'one observation-does-not-prove-attack probe',
                'security_interpretation':'execution, causation, intent/identity, benign-from-absence guardrails'}.get(kind,'Fixed availability probe; zero means no counted insufficient probe, not proof all claims would be supported.')})
    return {'status':'DRAFT_UNREVIEWED','event_id':public['scope']['event_id'],'counts_are':'automated evidence opportunities; NOT human annotations or final metric denominators',
        'primitive_security_observations':{'command_requests':len(commands),'tcp_rst_packets':sum(bool((r['fields']['tcp_flags'] or 0)&4) for r in packets),'numeric_pairs':numerical},
        'rows':result}
