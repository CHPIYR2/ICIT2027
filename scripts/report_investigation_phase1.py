"""Readable Phase-1 artifacts; reads saved B0 and full pilot evidence, no LLM."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import gzip
import json
from collections import Counter
from sherlock.io import ROOT,read_json,save_json,sha256


def fmt(value):
    return '—' if value is None else format(value,'.7g') if type(value) in (int,float) else str(value)


def render_pilot(directory):
    manifest=read_json(directory/'manifest.json')
    report=read_json(directory/'B0_EN.json')
    audit=read_json(directory/'claim_supportability.DRAFT.json')
    candidates=read_json(directory/'numerical_candidates.DRAFT.json')['entries']
    with gzip.open(directory/'complete_allowed_evidence.json.gz','rt') as f:public=json.load(f)
    numeric={c:m for c,m in public['metadata'].items() if m['family']!='reported_state'}
    post={r['fields']['channel_id'] for r in public['records'] if r['source_type']=='process' and r['value'] is not None and not r['quality_flags'] and r['observation_time']>=0}
    state=[r for r in public['records'] if r['source_type']=='process' and r['fields']['family']=='reported_state' and not r['quality_flags'] and r['value'] is not None and r['observation_time']>=0]
    pair_scopes=Counter('pre_post' if r['fields']['before_time']<0<=r['fields']['after_time'] else 'pre_only' if r['fields']['after_time']<0 else 'post_only' for r in candidates)
    lines=['# Pilot evidence review — DRAFT_UNREVIEWED','',f"Event: `{manifest['event_id']}`。本文件是自動整理的審查入口，不是 gold。",'',
        '## 完整證據與 retrieval accounting','',
        f"完整允許的 record counts：{manifest['complete_allowed_counts']}。共 {len(public['records'])} 筆。",
        f"mapped numeric channels 中 {len(set(numeric)-post)} 個沒有有效 post observation；post state observations {len(state)} 筆。",
        f'完整來源數值候選 pair 範圍：{dict(pair_scopes)}；pre-only pair 不能描述為事件後變化。','',
        '| View | Eligible 原始 records | Retrieved entries | B0 觀測列 | B0 differences | Gold recovered |','|---|---:|---:|---:|---:|---|']
    for view in ('E','N','EN'):
        result=read_json(directory/f'B0_{view}.json')['accounting']
        lines.append(f"| {view} | {result['eligible_original_count']} | {result['retrieved_entries']} | {result['mechanically_presented_observations']} | {result['mechanically_computed_differences']} | 未評分 |")
    lines+=['','## 代表性 B0 網路觀測（capture seconds relative to anchor）','',
        '| Time | Claim type | Evidence ID | 可說的內容 |','|---:|---|---|---|']
    selected=[r for r in report['observations'] if r['claim_type'] in ('command_observed','acknowledgement_observed')]
    if not selected:selected=[r for r in report['observations'] if r['claim_type']=='network_activity'][:8]
    for row in selected:
        message='命令型 activation request；target 與 execution 仍 unknown' if row['claim_type']=='command_observed' else 'protocol response；不代表 physical success' if row['claim_type']=='acknowledgement_observed' else str(row.get('activity'))
        lines.append(f"| {fmt(row['observation_time'])} | {row['claim_type']} | `{row['evidence_ids'][0]}` | {message} |")
    lines+=['','## B0 數值差（僅兩筆 reported values）','',
        '| Family | Channel | Before time/value | After time/value | Δ | Unit |','|---|---|---|---|---:|---|']
    for row in report['numerical_differences']:
        lines.append(f"| {row['family']} | `{row['channel_id']}` | {fmt(row['before_time'])} / {fmt(row['before_value'])} | {fmt(row['after_time'])} / {fmt(row['after_value'])} | {fmt(row['difference'])} | {row['unit']} |")
    lines+=['','完整精度與 before/after evidence IDs 在 B0_EN.json；不以截取表格取代原始引用。',
        '所有數字是 captured reported measurements；沒有物理因果或惡意意圖結論。','',
        '## 全部原始來源的 claim-type 可行性草稿','',
        '| Type | 可支持候選／機會 | 不足 probes | 人工確認 |','|---|---:|---:|---|']
    for row in audit['rows']:
        lines.append(f"| {row['claim_type']} | {row['supportable_candidate_examples']} | {row['insufficient_probe_examples']} | 尚未 |")
    lines+=['','不同 claim type 的計數單位不同，詳見 claim_supportability.DRAFT.json；不能直接相除成精確率。',
        'security_* 的 0 是未自動核准安全語意；primitive observations 仍存在，需人工判斷有無調查價值。',
        'reported_change 與 electrical_change 是同一組 pair 的別名，不能雙重計分。',
        'temporal candidate 計數只涵蓋 request 後出現 E 的 episode-level 機會，不是全部可能時間關係。','',
        '## 檔案與下一步','',
        '- complete_allowed_evidence.json.gz：整個允許視窗，包含 metadata、packet/message/process records。',
        '- allowed_lineage.json.gz：包內的完整 parent edges。',
        '- numerical_candidates.DRAFT.json：從完整 universe 產生的 candidates，不限 top-k。',
        '- retrieved_E/N/EN.json、B0_E/N/EN.json：固定預算對照。',
        '- annotation.DRAFT.json：待 reviewer 填寫、簽核；不要把自動候選直接當 gold。','']
    (directory/'review.md').write_text('\n'.join(lines))
    save_json(directory/'review_manifest.json',{'status':'DRAFT_UNREVIEWED','files':{p.name:sha256(p) for p in sorted(directory.iterdir()) if p.is_file() and p.name!='review_manifest.json'}})
    return {'event_id':manifest['event_id'],'counts':manifest['complete_allowed_counts'],'missing_numeric_post_channels':len(set(numeric)-post),'post_state_observations':len(state),'pair_scope_counts':dict(pair_scopes)}


def main():
    pilots=read_json(ROOT/'configs/investigation_pilots.v1.json')['event_ids']
    summaries=[render_pilot(ROOT/'annotations/events'/eid) for eid in pilots]
    save_json(ROOT/'results/investigation-v1/pilot_readable_summary.json',{'status':'DRAFT_UNREVIEWED','rows':summaries})
    print(json.dumps(summaries,indent=2))


if __name__=='__main__':main()
