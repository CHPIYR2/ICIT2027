"""Post-confirmatory descriptive audit only: no feature-regime implementation or fitting."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'experiments'))
import gzip,json
from collections import defaultdict,Counter
from datetime import datetime,timezone
import numpy as np
from sherlock.io import ROOT,read_json,save_json,sha256
from run_heldout import verify_lock
from features.extract import FAMILIES,E_NAMES,N_NAMES

OUT=ROOT/'results/exploratory-v2/audit'


def summary(values):
    x=np.array([v for v in values if v is not None],dtype=float)
    if not len(x):return {'n':len(values),'valid':0,'missing':len(values)}
    q1,median,q3=np.quantile(x,[.25,.5,.75])
    return {'n':len(values),'valid':len(x),'missing':len(values)-len(x),'unique':len(set(x.tolist())),
            'min':float(x.min()),'q1':float(q1),'median':float(median),'q3':float(q3),'iqr':float(q3-q1),'max':float(x.max())}


def grouping_keys(e):
    return [('overall','all'),('scenario',e['scenario']),('truth',e['event_truth']),
            ('scenario_truth',e['scenario']+'|'+e['event_truth']),
            ('recording',e['scenario']+'/'+e['recording']),
            ('family',e['family_description']),('family_truth',e['family_description']+'|'+e['event_truth'])]


def main():
    verify_lock()
    if (OUT/'manifest.json').exists():raise SystemExit('Audit exists; preserve versioned output')
    protected={}
    for folder in ['configs','results/development-v1','results/development-v2','results/ablation-development-v1','results/ablation-development-v2','results/heldout-v1']:
        for p in (ROOT/folder).rglob('*'):
            if p.is_file():protected[str(p.relative_to(ROOT))]=sha256(p)
    save_json(OUT/'immutable_inputs.before.json',protected)
    catalog={e['episode_id']:e for e in read_json(ROOT/'data/evaluator/event_catalog.json')['events']}
    rows=[]
    for partition in ['development','held_out']:
        rows.extend(read_json(ROOT/f'data/processed/v2/{partition}_features.json')['rows'])
    grouped=defaultdict(list)
    for row in rows:
        for group,key in grouping_keys(catalog[row['episode_id']]):grouped[(group,key)].append(row)
    distributions=defaultdict(dict)
    for (group,key),rs in grouped.items():
        distributions[group][key]={'events':len(rs),'features':{n:summary([r['values'][n] for r in rs]) for n in E_NAMES+N_NAMES}}
    save_json(OUT/'feature_distributions.json',distributions)
    coverage=[]
    for row in rows:
        path=ROOT/row['evidence_path']
        if sha256(path)!=row['evidence_sha256']:raise ValueError('Episode hash changed')
        with gzip.open(path,'rt') as f:ep=json.load(f)
        pre=defaultdict(set);post=defaultdict(set);valid=Counter();invalid=Counter();post_n=Counter()
        for r in ep['evidence_records']:
            if r['source_type']=='process':
                family=r['fields']['family']
                if r['value'] is not None and not r['quality_flags']:
                    target=pre if r['observation_time']<ep['anchor_time'] else post
                    target[family].add(r['fields']['channel_id']);valid[family]+=1
                else:invalid[family]+=1
            elif r['source_type']=='packet' and r['observation_time']>=ep['anchor_time'] and r['fields']['ip_protocol']==6 and 2404 in (r['fields']['source_port'],r['fields']['destination_port']):
                offset=r['observation_time']-ep['anchor_time']
                for seconds in [15,30,45,60]:
                    if offset<seconds:post_n[str(seconds)]+=1
        e=catalog[row['episode_id']]
        coverage.append({'episode_id':row['episode_id'],**{k:e[k] for k in ('scenario','recording','event_truth','family_description')},
            'families':{f:{'mapped_channels':sum(m['family']==f for m in ep['channels'].values()),
                          'pre_channels':len(pre[f]),'post_channels':len(post[f]),'both_channels':len(pre[f]&post[f]),
                          'valid_observations':valid[f],'invalid_observations':invalid[f]} for f in FAMILIES},
            'transport_window_feasibility_counts':{str(t):post_n[str(t)] for t in [15,30,45,60]}})
        if len(coverage)%20==0:print('Audited evidence coverage',len(coverage),'/',len(rows),flush=True)
    save_json(OUT/'episode_coverage.json',{'access':'EVALUATOR_ONLY','purpose':'descriptive coverage and feasibility only; no degraded features or scores','rows':coverage})
    by_scenario={}
    for scene in sorted({r['scenario'] for r in coverage}):
        rs=[r for r in coverage if r['scenario']==scene]
        by_scenario[scene]={'events':len(rs),'families':{f:{k:summary([r['families'][f][k] for r in rs]) for k in rs[0]['families'][f]} for f in FAMILIES},
            'window_packet_counts':{str(t):summary([r['transport_window_feasibility_counts'][str(t)] for r in rs]) for t in [15,30,45,60]}}
    save_json(OUT/'coverage_summary.json',by_scenario)
    rule={}
    for (group,key),rs in grouped.items():
        counts=Counter()
        for r in rs:
            truth=catalog[r['episode_id']]['event_truth'];pred='BENIGN' if r['values']['n_command_log_count']>0 else 'CYBER'
            counts[truth]+=1;counts['correct']+=pred==truth;counts['command_present']+=r['values']['n_command_log_count']>0
        rule.setdefault(group,{})[key]={'events':len(rs),**counts}
    save_json(OUT/'existing_command_rule.json',{'description':'Re-tabulation of existing development-derived rule, no new threshold search','groups':rule})
    # Re-tabulate existing N/EN predictions; these are not new observability models.
    predictions=read_json(ROOT/'results/heldout-v1/predictions.json')['rows'];lookup={}
    for r in predictions:lookup[(r['condition'],r['model'],r['view'],r['episode_id'])]=r
    transitions=[]
    for r in predictions:
        if r['view']!='N':continue
        en=lookup[(r['condition'],r['model'],'EN',r['episode_id'])]
        n_correct=int(r['prediction']=='CYBER_RELATED')==r['event_truth'];en_correct=int(en['prediction']=='CYBER_RELATED')==en['event_truth']
        changed=r['prediction']!=en['prediction']
        status='corrected_N' if changed and en_correct else 'hurt_N' if changed else 'unchanged'
        transitions.append({'episode_id':r['episode_id'],'scenario':catalog[r['episode_id']]['scenario'],
             'family':catalog[r['episode_id']]['family_description'],'condition':r['condition'],'model':r['model'],
             'N_prediction':r['prediction'],'EN_prediction':en['prediction'],'N_score':r['cyber_score'],'EN_score':en['cyber_score'],
             'N_correct':n_correct,'EN_correct':en_correct,'transition':status,'evidence_sha256':r['evidence_sha256']})
    save_json(OUT/'existing_prediction_transitions.json',{'scope':'Exploratory reanalysis of frozen v1 outputs, not Protocol-v2 predictions','rows':transitions})
    transition_summary={}
    for r in transitions:
        key=r['condition']+'|'+r['model'];transition_summary.setdefault(key,Counter())[r['transition']]+=1
    save_json(OUT/'transition_summary.json',transition_summary)
    for path,digest in protected.items():
        if sha256(ROOT/path)!=digest:raise ValueError(f'Protected artifact changed: {path}')
    verify_lock()
    save_json(OUT/'manifest.json',{'status':'audit_complete_protocol_pending_author_approval',
        'interpretation':'Exploratory / post-confirmatory / Protocol v2; same previously evaluated 84 events',
        'new_models_run':False,'existing_files_unchanged':True,'protected_files':len(protected),
        'completed_at_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':sha256(Path(__file__)),
        'inputs':{str(ROOT.relative_to(ROOT)/p):sha256(ROOT/p) for p in ['data/processed/v2/development_features.json','data/processed/v2/held_out_features.json','data/evaluator/event_catalog.json','results/heldout-v1/predictions.json']},
        'outputs':{p.name:sha256(p) for p in sorted(OUT.glob('*.json'))}})
    print('Descriptive audit complete; no models fit or predicted.',flush=True)

if __name__=='__main__':main()
