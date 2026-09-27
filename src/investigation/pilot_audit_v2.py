"""Full-window amendment inventory. Every count remains unreviewed, never gold."""
from investigation.pilot_audit import supportability as old_inventory
from retrieval.evidence_formatter_v2 import base_export
from retrieval.investigation_retriever_v2 import address_records,matching_e


def supportability(public):
    result=old_inventory(base_export(public))
    addresses=address_records(public['records']);requests=[a for a in addresses if a['cause_of_transmission']==6]
    mapped=[a for a in requests if a['mapping_status']=='exact_static_match']
    linked=[a for a in mapped if matching_e(a,public['records'],later=True)]
    result['schema_version']='investigation-supportability-v2'
    result['address_counts']={'all_children':len(addresses),'exact_mapped_children':sum(a['mapping_status']=='exact_static_match' for a in addresses),
        'same_asset_valid_E_children':sum(bool(matching_e(a,public['records'])) for a in addresses),
        'same_asset_later_valid_E_children':sum(bool(matching_e(a,public['records'],later=True)) for a in addresses),
        'request_children':len(requests),'exact_mapped_request_children':len(mapped),'same_asset_later_valid_E_requests':len(linked)}
    for row in result['rows']:
        kind=row['claim_type'];row['required_for_minimum_question_sufficiency']=False if kind=='reported_state_change' else None
        if kind=='command_observed':
            row['mapped_request_address_examples']=len(mapped)
            row['ambiguities']='Counts message requests separately from address children; exact m+a+M supports addressed-to only. Object-level candidates may share one request.'
        if kind=='asset_relationship':
            row['channel_mapping_candidates']=row['supportable_candidate_examples']
            row['command_address_mapping_candidates']=len(mapped)
            row['supportable_candidate_examples']+=len(mapped)
            row['insufficient_probe_examples']=len(requests)-len(mapped)
            row['ambiguities']='Static E channel and CONFIGURATION control point mappings share opaque asset identity; no execution or physical-effect claim.'
            row['insufficient_probe_definition']='Request addresses without an exact allowlisted mapping; causal/execution probes remain in security interpretation.'
        if kind=='temporal_association':
            row['episode_only_later_E_request_candidates']=row['supportable_candidate_examples']
            row['supportable_candidate_examples']=len(linked)
            row['insufficient_probe_examples']=len(requests)-len(linked)
            row['ambiguities']='One candidate per request address with any later valid same-asset E; both static mapping edges required. Capture-time ordering only.'
            row['insufficient_probe_definition']='Request address without a qualifying later same-asset E, or without exact address mapping.'
        if kind=='reported_state_change':
            row['ambiguities']='Optional ontology type; requires two valid same-channel strictly ordered unequal boolean observations. No initial values; single state is reported_value.'
            row['requires_author_review']=False
    return result
