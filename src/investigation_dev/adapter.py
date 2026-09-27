"""B0 native-output matching sidecars; immutable raw output and source roles retained."""
import copy
from .common import digest
from .custody import require_development
from .claims import adapt_b0_numeric,typed_support,need,valid_e
from investigation.fact_keys_phase2a import propose_fact_key
from investigation.timeline_v2 import timeline
from investigation.support_v2 import validate_supported_claim


def adapt_b0(report,bundle,receipt):
    require_development(bundle['scope']['event_id'])
    # Native B0 has no arbitrary prose. Exact regeneration checks its full emitted
    # content before sidecars can identify facts. This is development-only at the CLI.
    need(report==timeline(bundle,receipt),'B0_raw_output_or_generator_mismatch')
    event=bundle['scope']['event_id'];idx={r['evidence_id']:r for r in bundle['entries']};out=[]
    def put(section,position,row,kind,identity,scope='typed_or_native'):
        out.append({'source_section':section,'source_position':position,'raw_claim_type':row['claim_type'],
                    'raw_claim':copy.deepcopy(row),'raw_claim_sha256':digest(row),'raw_report_sha256':digest(report),
                    'bundle_sha256':digest(bundle),'receipt_sha256':digest(receipt),'fact_key':propose_fact_key(event,kind,identity),
                    'key_kind':kind,'key_identity':identity,'representation':scope,'raw_support_validated':True})
    for i,row in enumerate(report['numerical_differences']):
        if row['claim_type']=='reported_change':
            for sidecar in adapt_b0_numeric(row,bundle):
                c=sidecar['adapted_claim'];s=typed_support(c,bundle)
                put('numerical_differences',i,row,s['key_kind'],s['key_identity'])
                out[-1]['raw_field']=sidecar['raw_field'];out[-1]['checked_typed_sidecar']=c
        else:
            a,b=idx[row['before_id']],idx[row['after_id']];valid_e(a,bundle);valid_e(b,bundle)
            need(type(a['value']) is bool and type(b['value']) is bool and a['value']!=b['value'] and a['observation_time']<b['observation_time'],'invalid_B0_state')
            put('numerical_differences',i,row,'reported_state_change',{'before_id':row['before_id'],'after_id':row['after_id']})
    for i,row in enumerate(report['amendment_claims']):
        validate_supported_claim(row,bundle);s=typed_support(row,bundle)
        put('amendment_claims',i,row,s['key_kind'],s['key_identity'])
    for i,row in enumerate(report['observations']):
        kind=row['claim_type'];rid=row['evidence_ids'][0]
        if kind=='command_observed':continue # Explicit compact index; authoritative amendment claims above.
        if kind=='reported_value':identity={'record_id':rid}
        elif kind=='network_activity':identity={'record_id':rid,'activity':'packet_observed' if row['activity']=='captured_packet' else row['activity'].lower()}
        elif kind=='acknowledgement_observed':identity={'record_id':rid,'kind':row['acknowledgement_kind']}
        elif kind=='communication_gap':
            q=row['query_receipt'];identity={'coverage_id':rid,'population':'observed_tcp_2404_packets','start':q['start'],'end':q['end']}
        else:raise ValueError('Unknown native B0 observation')
        put('observations',i,row,kind,identity)
    for i,row in enumerate(report['asset_channel_mappings']):
        e=idx[row['evidence_ids'][0]];m=valid_e(e,bundle)
        identity={'record_id':e['evidence_id'],'mapping_id':m['evidence_id'],'channel_id':row['channel_id'],'asset_id':row['asset_id']}
        put('asset_channel_mappings',i,row,'observation_channel_maps_to_asset',identity,'existing_native_relation_absent_from_v2_generation_schema')
    for i,row in enumerate(report['temporal_relations']):
        identity={'earlier_id':row['evidence_ids'][0],'later_id':row['evidence_ids'][1],'relation':row['relation'],'scope':'episode_only','mapping_ids':[],'asset_id':None}
        put('temporal_relations',i,row,'temporal_association',identity)
    return {'status':'VALIDATED_NATIVE_B0_SIDECARS_NOT_SCORED','event_id':event,'raw_report_sha256':digest(report),'facts':out,
            'limitations':copy.deepcopy(report['unknowns']+report['amendment_insufficiency']),
            'no_new_gold_aliases':True,'single_observation_mapping_schema_gap':'Retained native key is already in reviewed policy; do not silently add a v2 schema enum or credit another raw claim type. Author schema representation decision required before freeze.'}
