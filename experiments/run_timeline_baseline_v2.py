"""Approved Phase1 amendment runner: frozen 48 events, B0 only, four draft packets."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import argparse
import gzip
import json
from collections import Counter
from sherlock.io import ROOT,read_json,save_json,sha256
from evidence.schema import EvidenceEpisode
from retrieval.evidence_formatter import digest,counts
from retrieval.evidence_formatter_v2 import export_episode
from retrieval.investigation_retriever_v2 import retrieve
from retrieval.investigation_retriever import channel_groups,pair_for_channel,difference
from investigation.timeline_v2 import timeline
from investigation.pilot_audit_v2 import supportability
from run_timeline_baseline import write_gzip,check_event_lock
from run_observability_v2 import verify_lock as verify_prior

OUT=ROOT/'results/investigation-v2'


def verify_locks():
    verify_prior();check_event_lock()
    for name in ('investigation_phase1.lock.json','investigation_phase1.v2.lock.json'):
        for path,expected in read_json(ROOT/'configs'/name)['files'].items():
            if sha256(ROOT/path)!=expected:raise ValueError('Frozen input changed: '+path)
    for path,expected in read_json(OUT/'command_addresses/manifest.json')['files'].items():
        if sha256(ROOT/path)!=expected:raise ValueError('Address input changed: '+path)


def review_packet(public,provenance,reports,bundles,receipts):
    eid=public['scope']['event_id'];directory=ROOT/'annotations/events-v2'/eid
    directory.mkdir(parents=True,exist_ok=False)
    write_gzip(directory/'complete_allowed_evidence.json.gz',public)
    allowed={r['evidence_id'] for r in public['records']}
    edges={rid:r['parent_ids'] for rid,r in provenance['records'].items() if rid in allowed}
    if any(not set(parents)<=allowed for parents in edges.values()):raise ValueError('Ancestry not closed')
    write_gzip(directory/'allowed_lineage.json.gz',edges)
    audit=supportability(public);save_json(directory/'claim_supportability.DRAFT.json',audit)
    pairs=[difference(*pair) for rows in channel_groups(public).values() if (pair:=pair_for_channel(rows))]
    save_json(directory/'numerical_candidates.DRAFT.json',{'status':'DRAFT_UNREVIEWED','source':'full allowed window','entries':pairs})
    for view in ('E','N','EN'):
        save_json(directory/f'B0_{view}.json',reports[view]);save_json(directory/f'retrieved_{view}.json',bundles[view]);save_json(directory/f'receipt_{view}.json',receipts[view])
    save_json(directory/'annotation.DRAFT.json',{'status':'DRAFT_UNREVIEWED','event_id':eid,'reviewer':None,'reviewed_at':None,
        'questions':[{'question_id':f'Q{i}','answerability_by_view':{'E':None,'N':None,'EN':None},'gold_fact_ids':[],'review_notes':''} for i in range(1,8)],
        'facts':[],'supportability_review':audit['rows'],'review_tasks':['meaningful facts','aliases and duplicates','valid alternative support sets','unsupported stronger statements','unknowns','mechanical verifier feasibility'],
        'optional_claim_types':['reported_state_change'],'signoff':None})
    (directory/'README.md').write_text('\n'.join(['# 人工審查包 v2 — DRAFT_UNREVIEWED','',f'Event: `{eid}`。不是 gold；請人工審查與簽核。','',
        'complete_allowed_evidence.json.gz 是完整 [-60,+60) E/N/M；allowed_lineage.json.gz 是包內 p→m→e、m→a 關係。',
        'B0_E/N/EN 與 retrieved/receipt 是固定預算結果；完整證據與 top-k 必須分別檢查。',
        'command_address_observation 只含命令地址的 opaque 靜態映射，原始地址與控制值不在本包。',
        'amendment_claims 提供通過有限一致性檢查的 m+a+M 與同資產 capture-time 候選；amendment_insufficiency 保留不足原因。',
        '命令地址與同資產 E 的時間關聯不能證明執行、物理效果、因果、惡意或歸因。',
        'reported_state_change 為選配，單筆 state 只算 reported_value，不影響最低問題充分性。',
        '請審查 meaningful facts、aliases、support sets、較強但不被支援的敘述、unknowns 與機械驗證可行性。','']) )
    save_json(directory/'manifest.json',{'status':'DRAFT_UNREVIEWED','event_id':eid,'complete_allowed_counts':counts(public),
        'complete_allowed_universe_sha256':digest(public),'not_gold':True,'includes_entire_allowed_window':True,
        'files':{p.name:sha256(p) for p in directory.iterdir() if p.is_file()}})
    return {'event_id':eid,'packet_path':str(directory.relative_to(ROOT)),'counts':counts(public),'numeric_candidates':len(pairs),'supportability':audit,
        'retrieved_EN_same_asset_temporal_claims':sum(c['claim_type']=='temporal_association' for c in reports['EN']['amendment_claims'])}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',action='store_true',required=True);parser.parse_args()
    verify_locks()
    if (OUT/'baseline_manifest.json').exists() or (OUT/'baseline_started.json').exists():raise ValueError('Preserve existing run')
    save_json(OUT/'baseline_started.json',{'stage':'B0_ONLY','implementation_lock_sha256':sha256(ROOT/'configs/investigation_phase1.v2.lock.json')})
    events=read_json(ROOT/'configs/investigation_events.v1.json');pilots=set(read_json(ROOT/'configs/investigation_pilots.v1.json')['event_ids'])
    sources={r['episode_id']:r for p in ('development','held_out') for r in read_json(ROOT/f'data/processed/v2/{p}_features.json')['rows']}
    index=[];pilot_rows=[];inventories=[]
    for eid in events['development']+events['evaluation']:
        row=sources[eid]
        if sha256(ROOT/row['evidence_path'])!=row['evidence_sha256']:raise ValueError('Canonical evidence changed')
        with gzip.open(ROOT/row['evidence_path'],'rt') as f:episode=EvidenceEpisode.from_dict(json.load(f))
        sidecar=read_json(OUT/'command_addresses'/f'{eid}.json');metadata=read_json(OUT/'command_addresses'/f'{eid}.metadata.json')
        bundles={};reports={};receipts={}
        for view in ('E','N','EN'):
            public,provenance,visibility=export_episode(episode,view,sidecar,metadata)
            bundle,receipt=retrieve(public);report=timeline(bundle,receipt);dest=OUT/'B0'/eid/view
            write_gzip(dest/'eligible.json.gz',public);save_json(dest/'visibility.json',visibility)
            write_gzip(OUT/'private_provenance'/eid/f'{view}.json.gz',provenance)
            save_json(dest/'retrieved.json',bundle);save_json(dest/'receipt.json',receipt);save_json(dest/'timeline.json',report)
            index.append({'event_id':eid,'view':view,'retrieved_entries':receipt['retrieved_entry_count'],'retrieved_by_domain':receipt['retrieved_by_domain'],
                'amendment_claim_counts':dict(Counter(c['claim_type'] for c in report['amendment_claims'])),
                'final_recovered_gold_facts':None,'files':{str(p.relative_to(ROOT)):sha256(p) for p in dest.iterdir() if p.is_file()}})
            bundles[view]=bundle;reports[view]=report;receipts[view]=receipt
        inventories.append(supportability(public))
        if eid in pilots:pilot_rows.append(review_packet(public,provenance,reports,bundles,receipts))
        print('B0 v2',len(index)//3,'/48',eid,flush=True)
    verify_locks()
    save_json(OUT/'supportability_inventory.DRAFT.json',{'status':'DRAFT_UNREVIEWED','human_confirmed_gold_events':0,'events':inventories})
    save_json(OUT/'pilot_summary.json',{'status':'DRAFT_UNREVIEWED','human_signed_off_events':0,'rows':pilot_rows})
    save_json(OUT/'baseline_manifest.json',{'stage':'PHASE1_AMENDMENT_COMPLETE_B0_ONLY','formal_protocol_frozen':False,'llm_calls':0,
        'implementation_lock_sha256':sha256(ROOT/'configs/investigation_phase1.v2.lock.json'),'events':48,'conditions':144,
        'pilots':sorted(pilots),'command_mapping_amendment_implemented':True,'rows':index})


if __name__=='__main__':main()
