"""Phase 1: no LLM, no labels in runtime export. Emit B0 and four review packets."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import argparse
import gzip
import json
from collections import Counter
from datetime import datetime, timezone
from sherlock.io import ROOT,read_json,save_json,sha256
from evidence.schema import EvidenceEpisode
from retrieval.evidence_formatter import export_episode,digest,counts
from retrieval.investigation_retriever import retrieve,channel_groups,pair_for_channel,difference
from investigation.timeline import timeline
from investigation.pilot_audit import supportability
from run_observability_v2 import verify_lock as verify_prior

OUT=ROOT/'results/investigation-v1'


def write_gzip(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('wb') as raw,gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as f:
        f.write(json.dumps(data,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode())


def check_event_lock():
    for path,expected in read_json(ROOT/'configs/investigation_events.v1.lock.json')['files'].items():
        if sha256(ROOT/path)!=expected:raise ValueError('Frozen investigation IDs changed')


def review_packet(public,provenance,reports,bundles):
    eid=public['scope']['event_id'];directory=ROOT/'annotations/events'/eid
    directory.mkdir(parents=True,exist_ok=False)
    write_gzip(directory/'complete_allowed_evidence.json.gz',public)
    # Complete allowed EN parent edges only; no private raw resolver or source names.
    allowed={r['evidence_id'] for r in public['records']}
    edges={rid:r['parent_ids'] for rid,r in provenance['records'].items() if rid in allowed}
    if any(not set(parents)<=allowed for parents in edges.values()):raise ValueError('Review ancestry not closed')
    write_gzip(directory/'allowed_lineage.json.gz',edges)
    audit=supportability(public)
    save_json(directory/'claim_supportability.DRAFT.json',audit)
    pairs=[]
    for rows in channel_groups(public).values():
        pair=pair_for_channel(rows)
        if pair:pairs.append(difference(*pair))
    save_json(directory/'numerical_candidates.DRAFT.json',{'status':'DRAFT_UNREVIEWED','source':'complete allowed universe, not top-k','entries':pairs})
    for view in ('E','N','EN'):
        save_json(directory/f'B0_{view}.json',reports[view])
        save_json(directory/f'retrieved_{view}.json',bundles[view])
    save_json(directory/'annotation.DRAFT.json',{'status':'DRAFT_UNREVIEWED','event_id':eid,'reviewer':None,'reviewed_at':None,
        'questions':[{'question_id':f'Q{i}','answerability_by_view':{'E':None,'N':None,'EN':None},'gold_fact_ids':[],'review_notes':''} for i in range(1,8)],
        'facts':[],'supportability_review':audit['rows'],'signoff':None})
    manifest={'status':'DRAFT_UNREVIEWED','event_id':eid,'complete_allowed_counts':counts(public),
        'complete_allowed_universe_sha256':digest(public),'not_gold':True,'includes_entire_allowed_window':True,
        'files':{p.name:sha256(p) for p in directory.iterdir() if p.is_file()}}
    save_json(directory/'manifest.json',manifest)
    rows=['# 人工審查證據包 — DRAFT_UNREVIEWED','',f'Event: `{eid}`。本包不是 gold，待人工簽核。',
        '', 'complete_allowed_evidence.json.gz 包含完整 [-60,+60) 允許 E/N/M；不是 production top-k。',
        'allowed_lineage.json.gz 提供同一包內的 p→m→e 父子關係。reported_time 未知；時序僅為 capture time。',
        '',f'完整來源數：{counts(public)}。數值候選：{len(pairs)}。',
        '', 'B0_E/N/EN 與 retrieved_E/N/EN 是固定預算對照；annotation.DRAFT.json 留待人工審查填寫。',
        '不得將 evaluator metadata、攻擊描述或 classifier 輸出拿來補可觀測事實。',
        '命令目標映射尚未核准，B0 不包含；命令≠執行、回報變化≠因果、missing≠benign。',
        '', '請對照每個 claim type 的 DRAFT counts，記錄可支援／不足例子、歧義、alias 與可機械檢查性。',
        '查看方法：Python gzip.open(..., "rt") + json.load；完整事件亦可用 scripts/inspect_investigation_packet.py 依 ID/channel/time 查詢。']
    (directory/'README.md').write_text('\n'.join(rows)+'\n')
    return {'event_id':eid,'counts':counts(public),'numeric_candidates':len(pairs),'supportability':audit}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',action='store_true',required=True);parser.parse_args()
    verify_prior();check_event_lock()
    lock=read_json(ROOT/'configs/investigation_phase1.lock.json')
    for path,expected in lock['files'].items():
        if sha256(ROOT/path)!=expected:raise ValueError('Phase1 implementation/config hash mismatch')
    if (OUT/'baseline_manifest.json').exists() or (OUT/'baseline_started.json').exists():raise ValueError('Run already started; preserve artifacts')
    if not (OUT/'audit/command_target_feasibility.json').exists():raise ValueError('Command-target audit required first')
    save_json(OUT/'baseline_started.json',{'phase':'B0_only_not_formal_LLM_evaluation','at':datetime.now(timezone.utc).isoformat(),'phase1_lock_sha256':sha256(ROOT/'configs/investigation_phase1.lock.json')})
    events=read_json(ROOT/'configs/investigation_events.v1.json');pilots=set(read_json(ROOT/'configs/investigation_pilots.v1.json')['event_ids'])
    source_rows={r['episode_id']:r for partition in ('development','held_out') for r in read_json(ROOT/f'data/processed/v2/{partition}_features.json')['rows']}
    index=[];pilot_summaries=[]
    for eid in events['development']+events['evaluation']:
        original=source_rows[eid]
        if sha256(ROOT/original['evidence_path'])!=original['evidence_sha256']:raise ValueError('Canonical evidence changed')
        with gzip.open(ROOT/original['evidence_path'],'rt') as f:episode=EvidenceEpisode.from_dict(json.load(f))
        bundles={};reports={};en_public=en_provenance=None
        for view in ('E','N','EN'):
            public,provenance=export_episode(episode,view)
            bundle,receipt=retrieve(public)
            report=timeline(bundle,receipt)
            dest=OUT/'B0'/eid/view
            write_gzip(dest/'eligible.json.gz',public)
            write_gzip(OUT/'private_provenance'/eid/f'{view}.json.gz',provenance)
            save_json(dest/'retrieved.json',bundle);save_json(dest/'receipt.json',receipt);save_json(dest/'timeline.json',report)
            index.append({'event_id':eid,'view':view,'eligible_count':receipt['eligible_original_count'],
                'retrieved_entries':receipt['retrieved_entry_count'],'retrieved_by_domain':receipt['retrieved_by_domain'],
                'presented_observations':len(report['observations']),'computed_differences':len(report['numerical_differences']),
                'final_recovered_gold_facts':None,'files':{str(p.relative_to(ROOT)):sha256(p) for p in dest.iterdir() if p.is_file()}})
            bundles[view]=bundle;reports[view]=report
            if view=='EN':en_public,en_provenance=public,provenance
        if eid in pilots:pilot_summaries.append(review_packet(en_public,en_provenance,reports,bundles))
        print('B0 built',len(index)//3,'/48',eid,flush=True)
    verify_prior();check_event_lock()
    save_json(OUT/'pilot_summary.json',{'status':'DRAFT_UNREVIEWED','human_signed_off_events':0,'rows':pilot_summaries})
    save_json(OUT/'baseline_manifest.json',{'stage':'PHASE1_COMPLETE_B0_ONLY','formal_protocol_frozen':False,'llm_calls':0,
        'event_set_lock_sha256':sha256(ROOT/'configs/investigation_events.v1.lock.json'),'phase1_lock_sha256':sha256(ROOT/'configs/investigation_phase1.lock.json'),
        'events':48,'conditions':144,'pilots':sorted(pilots),'command_mapping_amendment_implemented':False,'rows':index})


if __name__=='__main__':main()
