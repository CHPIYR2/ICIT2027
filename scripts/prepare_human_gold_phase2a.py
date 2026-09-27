"""Create blank pilot worksheets and separate full-universe mechanical candidates."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import argparse
import json
from collections import Counter
from sherlock.io import ROOT,read_json,save_json,sha256
from investigation.review_phase2a import pilot_ids,load_universe,blank_fact,PROHIBITED
from investigation.fact_keys_phase2a import propose_fact_key,duplicate_proposals
from retrieval.investigation_retriever import valid_e,largest_gap
from retrieval.investigation_retriever_v2 import matching_e,address_records


def candidates(public,pairs):
    eid=public['scope']['event_id'];rows=[]
    def add(kind,key_kind,identity,ids,payload):
        rows.append({'candidate_id':f'candidate_{len(rows)+1:06d}','status':'DRAFT_UNREVIEWED','claim_type':kind,
            'key_kind':key_kind,'key_identity':identity,'proposed_fact_key':propose_fact_key(eid,key_kind,identity),
            'evidence_ids':ids,'observed_payload':payload,'human_judgment':None})
    seen_channels=set()
    for r in public['records']:
        rid=r['evidence_id']
        if valid_e(r):
            add('reported_value','reported_value',{'record_id':rid},[rid],{'value':r['value'],'unit':r['unit'],'capture_time':r['observation_time']})
            channel=r['fields']['channel_id'];meta=public['metadata'][channel]
            if channel not in seen_channels:
                add('asset_relationship','observation_channel_maps_to_asset',{'record_id':rid,'mapping_id':meta['evidence_id'],'channel_id':channel,'asset_id':r['asset_id']},[rid,meta['evidence_id']],{'relation':'observation_channel_maps_to_asset'})
                seen_channels.add(channel)
        elif r['source_type']=='message' and r['fields']['asdu_type'] in (45,47,50) and r['fields']['cause_of_transmission']==6:
            add('command_observed','command_observed',{'message_id':rid},[rid],{'asdu_type':r['fields']['asdu_type'],'cause_of_transmission':6,'capture_time':r['observation_time'],'strength':'request_observed_only'})
        elif r['source_type']=='packet' and (r['fields']['tcp_flags'] or 0)&4:
            add('network_activity','network_activity',{'record_id':rid,'activity':'tcp_rst_observed'},[rid],{'capture_time':r['observation_time'],'security_relevance':'HUMAN_REVIEW_PENDING'})
    for d in pairs:
        f=d['fields'];is_state=f['kind']=='reported_state_change'
        if is_state:
            if type(f['before_value']) is not bool or type(f['after_value']) is not bool or f['before_value']==f['after_value'] or f['before_time']>=f['after_time']:raise ValueError('Invalid state candidate')
            kinds=['reported_state_change'];identity={'before_id':f['before_id'],'after_id':f['after_id']}
        else:kinds=['reported_change','electrical_change'];identity={'before_id':f['before_id'],'after_id':f['after_id'],'quantity':'difference','unit':d['unit']}
        for kind in kinds:add(kind,kind,identity,d['parent_ids'],f)
    for a in address_records(public['records']):
        if a['cause_of_transmission']!=6 or a['mapping_status']!='exact_static_match':continue
        cm=public['control_metadata'][a['mapping_evidence_id']];ids=[a['parent_ids'][0],a['evidence_id'],cm['evidence_id']]
        identity={'message_id':ids[0],'address_id':ids[1],'mapping_id':ids[2],'asset_id':cm['asset_id']}
        add('command_observed','mapped_command_observed',{**identity,'control_point_id':cm['control_point_id']},ids,{'strength':'addressed_to_static_mapped_control_point_only','capture_time':a['observation_time']})
        add('asset_relationship','command_address_maps_to_asset',identity,ids,{'relation':'command_address_maps_to_asset'})
        matches=matching_e(a,public['records'],later=True)
        if matches:
            e=matches[0];em=public['metadata'][e['fields']['channel_id']]
            ident={'earlier_id':a['evidence_id'],'later_id':e['evidence_id'],'relation':'precedes','scope':'same_observed_asset',
                'mapping_ids':[cm['evidence_id'],em['evidence_id']],'asset_id':cm['asset_id']}
            add('temporal_association','temporal_association',ident,ids+[e['evidence_id'],em['evidence_id']],{'delta_seconds':e['observation_time']-a['observation_time'],'interpretation':'asset-linked temporal evidence only'})
    gap=largest_gap(public);f=gap['fields']
    add('communication_gap','communication_gap',{'coverage_id':gap['evidence_id'],'population':f['population'],'start':f['start'],'end':f['end']},[gap['evidence_id'],*gap['parent_ids']],f)
    return rows


def main():
    p=argparse.ArgumentParser();p.add_argument('--create',action='store_true',required=True);p.parse_args()
    out=ROOT/'annotations/phase2a/pilots';ids=pilot_ids()
    if any((out/eid).exists() for eid in ids):raise ValueError('Never overwrite a reviewer worksheet')
    event_set=read_json(ROOT/'configs/investigation_events.v1.json')
    if not set(ids)<=set(event_set['development']):raise ValueError('Pilot/evaluation isolation violation')
    for eid in ids:
        source=ROOT/'annotations/events-v2'/eid;public=load_universe(eid)
        pairs=read_json(source/'numerical_candidates.DRAFT.json')['entries'];rows=candidates(public,pairs)
        template={'schema_version':'human-review-phase2a-proposed-v1','event_id':eid,'partition':'development_pilot',
            'review_status':'UNREVIEWED','reviewer_id':None,'signoff':None,
            'source_packet':str(source.relative_to(ROOT)),'source_packet_manifest_sha256':sha256(source/'manifest.json'),
            'full_universe_path':str((source/'complete_allowed_evidence.json.gz').relative_to(ROOT)),
            'full_universe_sha256':sha256(source/'complete_allowed_evidence.json.gz'),
            'production_retrieval_paths':{v:f'results/investigation-v2/B0/{eid}/{v}/retrieved.json' for v in ('E','N','EN')},
            'instructions':'Copy blank_fact_template into facts for each atomic human judgment. Do not edit the blank template. Candidates are separate, not gold.',
            'blank_fact_template':blank_fact(eid),'facts':[],
            'question_review':[{'question_id':f'Q{i}','answerability':{v:None for v in ('E','N','EN')},'gold_claim_ids':[],
                'reviewer_id':None,'review_status':'UNREVIEWED','notes':None} for i in range(1,8)]}
        dest=out/eid
        save_json(dest/'reviewer_annotation.BLANK.json',template)
        save_json(dest/'observation_candidates.DRAFT.json',{'status':'DRAFT_UNREVIEWED','event_id':eid,
            'source':'complete approved EN universe, not 64-entry production retrieval','exhaustive_gold':False,
            'selection':'all valid reported values; first observed mapping per channel; approved numeric/state pairs; requests; mapped request edges; nearest later same-asset E; RST; full-query gap',
            'candidate_count':len(rows),'counts_by_type':dict(Counter(r['claim_type'] for r in rows)),
            'candidates':rows})
        save_json(dest/'deduplication_proposals.DRAFT.json',{'status':'DRAFT_UNREVIEWED','automatically_merged':0,'groups':duplicate_proposals(rows)})
        save_json(dest/'guardrail_opportunities.DRAFT.json',{'status':'DRAFT_UNREVIEWED','human_judgments':None,
            'opportunities':[{'prohibited_conclusion':term,'human_decision':None,'note':'Not established by current approved evidence policy; reviewer records appropriate insufficiency.'} for term in PROHIBITED],
            'weak_review_required':{'meaningful':None,'support_sets':None,'reviewer_id':None},
            'reported_state_change_required':False})
        print(eid,'blank template;',len(rows),'separate unreviewed candidates',flush=True)


if __name__=='__main__':main()
