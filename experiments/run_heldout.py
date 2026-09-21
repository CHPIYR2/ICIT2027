"""Freeze, build and score are separate; scoring only loads Basic-fitted artifacts."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import argparse
from datetime import datetime,timezone
import gzip
import json
import platform
import importlib.metadata
import joblib
import numpy as np
from sherlock.io import ROOT,read_json,save_json,sha256,verify_protocol
from sherlock.build_v2 import build_recording
from evidence.schema import EvidenceEpisode
from features.extract import extract
from triage.baseline import matrix,names,contributions
from evaluation.metrics import classification_metrics
from paired_bootstrap import contrasts

LOCK=ROOT/'configs/evaluation.v1.lock.json'
OUT=ROOT/'results/heldout-v1'
FEATURES=ROOT/'data/processed/v2/held_out_features.json'


def verify_lock():
    verify_protocol()
    lock=read_json(LOCK)
    for path,digest in lock['files'].items():
        if sha256(ROOT/path)!=digest:raise ValueError(f'Pre-evaluation file changed: {path}')
    return lock


def freeze():
    split,_=verify_protocol()
    if LOCK.exists() or FEATURES.exists() or (OUT/'predictions.json').exists():
        raise ValueError('Cannot replace pre-evaluation lock or freeze after held-out construction')
    for path,digest in read_json(ROOT/'results/development-v2/implementation.lock.json')['files'].items():
        if sha256(ROOT/path)!=digest:raise ValueError('Original baseline implementation changed')
    audit=read_json(ROOT/'data/manifests/segmentation_audit.v2.json')
    if not audit['passed'] or len(audit['recordings'])!=5:raise ValueError('Segmentation audit gate failed')
    tests=read_json(ROOT/'results/pre_evaluation_tests.json')
    if not tests['passed']:raise ValueError('Tests not passed')
    files=[]
    for folder,pattern in [('src','*.py'),('experiments','*.py'),('tests','*.py'),('configs','*.json')]:
        files.extend((ROOT/folder).rglob(pattern))
    for folder in ['results/development-v2','results/ablation-development-v2']:
        files.extend((ROOT/folder).rglob('*.json'));files.extend((ROOT/folder).rglob('*.joblib'))
    files += [ROOT/'requirements.lock',ROOT/'pyproject.toml',ROOT/'data/manifests/segmentation_audit.v2.json',
              ROOT/'data/processed/v2/development_features.json',ROOT/'results/pre_evaluation_tests.json']
    for r in read_json(ROOT/'data/processed/v2/development_features.json')['rows']:
        path=ROOT/r['evidence_path']
        if sha256(path)!=r['evidence_sha256']:raise ValueError('Development evidence changed')
    for path,digest in read_json(ROOT/'results/ablation-development-v2/models.json').items():
        if sha256(ROOT/path)!=digest:raise ValueError('Ablation model changed')
    manifest=read_json(ROOT/'results/development-v2/run_manifest.json')
    for path,digest in manifest['model_hashes'].items():
        if sha256(ROOT/'results/development-v2/models'/path)!=digest:raise ValueError('Main model changed')
    save_json(LOCK,{'version':'evaluation-v1','frozen_at_utc':datetime.now(timezone.utc).isoformat(),
                   'held_out_predictions_exposed':False,'held_out_ids':split['held_out'],
                   'files':{str(p.relative_to(ROOT)):sha256(p) for p in sorted(set(files))}})
    print('Pre-evaluation lock saved',flush=True)


def build():
    verify_lock();split,contract=verify_protocol()
    if FEATURES.exists():raise ValueError('Held-out features already exist; preserve them')
    catalog=read_json(ROOT/'data/evaluator/event_catalog.json')['events'];selected=set(split['held_out'])
    rows=[];sources=[]
    for archive in read_json(ROOT/'data/manifests/sherlock_manifest.json')['archives']:
        scenario=archive['filename'][:-4]
        events=[e for e in catalog if e['episode_id'] in selected and e['scenario']==scenario]
        if not events:continue
        path=ROOT/archive['local_path']
        if sha256(path)!=archive['sha256']:raise ValueError('Archive changed')
        for recording in sorted({e['recording'] for e in events}):
            scopes=[{k:e[k] for k in ('episode_id','start')} for e in events if e['recording']==recording]
            vp=contract['primary_vantages'][scenario]
            rs,source=build_recording(path,f'{scenario}/raw/{recording}/pcap/switch-{vp}-pcap-mir2.pcap',
                   f'{scenario}/raw/{recording}/data-point-map.json',archive['sha256'],vp,scopes,contract,ROOT/'data/processed/v2')
            rows.extend(rs);sources.append(source)
    if len(rows)!=84 or {r['episode_id'] for r in rows}!=selected:raise ValueError('Held-out coverage mismatch')
    verify_lock()
    save_json(FEATURES,{'recipe':'features-v1+apdu-dedup-v2','pre_evaluation_lock_sha256':sha256(LOCK),
                       'rows':sorted(rows,key=lambda r:r['episode_id'])})
    save_json(ROOT/'data/manifests/held_out_source_resolver.v2.json',{'access':'PRIVATE_LOADER_ONLY','sources':sources})


def grouped_metrics(y,scores,metadata):
    result={'overall':classification_metrics(y,scores),'scenario':{},'recording':{},'family_description':{}}
    for field in ('scenario','recording','family_description'):
        # Recording names must include scenario: 'test' alone would pool two scenes.
        values=[m['scenario']+'/'+m[field] if field=='recording' else m[field] for m in metadata]
        for value in sorted(set(values)):
            mask=np.array([v==value for v in values]);result[field][value]=classification_metrics(y[mask],scores[mask])
    return result


def score():
    verify_lock();split,_=verify_protocol();cfg=read_json(ROOT/'configs/models.v1.json');ev=read_json(ROOT/'configs/evaluation.v1.json')
    if (OUT/'started.json').exists():raise ValueError('Evaluation already started; preserve exposure history and outputs')
    data=read_json(FEATURES);rows=data['rows']
    if data['pre_evaluation_lock_sha256']!=sha256(LOCK) or [r['episode_id'] for r in rows]!=split['held_out']:
        raise ValueError('Held-out provenance/order mismatch')
    for row in rows:
        path=ROOT/row['evidence_path']
        if sha256(path)!=row['evidence_sha256']:raise ValueError('Evidence hash mismatch')
        with gzip.open(path,'rt') as f:episode=EvidenceEpisode.from_dict(json.load(f))
        if episode.episode_id!=row['episode_id'] or extract(episode)!=row['values']:raise ValueError('Feature/evidence mismatch')
    save_json(OUT/'started.json',{'started_at_utc':datetime.now(timezone.utc).isoformat(),
                                'lock_sha256':sha256(LOCK),'features_sha256':sha256(FEATURES)})
    catalog={e['episode_id']:e for e in read_json(ROOT/'data/evaluator/event_catalog.json')['events']}
    metadata=[catalog[r['episode_id']] for r in rows]
    y=np.array([int(m['event_truth']=='CYBER') for m in metadata]);groups=np.array([m['scenario'] for m in metadata])
    results={};predictions=[];intervals={}
    for condition,folder,views in [('primary','development-v2',['E','N','EN']),('without_commands','ablation-development-v2',['N','EN'])]:
        results[condition]={};intervals[condition]={}
        for model in cfg['models']:
            results[condition][model]={};all_scores={}
            for view in views:
                feature_names=names(view);x=matrix(rows,view)
                if condition=='without_commands':
                    keep=[i for i,n in enumerate(feature_names) if n not in ev['diagnostic_drop_features']]
                    x=x[:,keep];feature_names=[feature_names[i] for i in keep]
                pipeline=joblib.load(ROOT/f'results/{folder}/models/{model}_{view}.joblib')
                if list(pipeline.classes_)!=[0,1] or pipeline.n_features_in_!=x.shape[1]:raise ValueError('Model schema mismatch')
                scores=pipeline.predict_proba(x)[:,1]
                if not np.isfinite(scores).all():raise ValueError('Nonfinite model scores')
                all_scores[view]=scores
                cs=contributions(pipeline,x,feature_names)
                results[condition][model][view]=grouped_metrics(y,scores,metadata)
                for i,row in enumerate(rows):
                    predictions.append({'episode_id':row['episode_id'],'condition':condition,'model':model,'view':view,
                                        'event_truth':int(y[i]),'cyber_score':float(scores[i]),
                                        'prediction':'CYBER_RELATED' if scores[i]>=.5 else 'BENIGN_OPERATIONAL',
                                        'evidence_sha256':row['evidence_sha256'],'contributions':cs[i] if cs else None})
                print(condition,model,view,results[condition][model][view]['overall']['macro_f1'],flush=True)
            if condition=='without_commands':
                # E is unchanged: use the primary E scores for paired diagnostic contrasts.
                all_scores['E']=np.array([p['cyber_score'] for p in predictions if p['condition']=='primary' and p['model']==model and p['view']=='E'])
            intervals[condition][model]={'overall':contrasts(y,all_scores,groups,ev['bootstrap']),'scenario':{}}
            for group in sorted(set(groups)):
                mask=groups==group
                intervals[condition][model]['scenario'][group]=contrasts(y[mask],{v:s[mask] for v,s in all_scores.items()},groups[mask],ev['bootstrap'])
    rule=np.array([float(r['values']['n_command_log_count']==0) for r in rows])
    results['command_presence_rule']=grouped_metrics(y,rule,metadata)
    save_json(OUT/'command_rule_predictions.json',[{'episode_id':r['episode_id'],'event_truth':int(y[i]),'cyber_prediction':int(rule[i])} for i,r in enumerate(rows)])
    verify_lock()
    save_json(OUT/'predictions.json',{'partition':'held_out','access':'EVALUATOR_ONLY','rows':predictions})
    save_json(OUT/'metrics.json',{'partition':'held_out','events':len(rows),'metrics':results})
    save_json(OUT/'paired_bootstrap.json',{'config':ev['bootstrap'],'results':intervals})
    save_json(OUT/'run_manifest.json',{'finished_at_utc':datetime.now(timezone.utc).isoformat(),
        'python':sys.version,'platform':platform.platform(),'git_commit':None,'version_method':'pre-evaluation SHA256 lock',
        'packages':{n:importlib.metadata.version(n) for n in ['numpy','scipy','scikit-learn','joblib']},
        'pre_evaluation_lock_sha256':sha256(LOCK),'features_sha256':sha256(FEATURES),
        'artifacts':{p.name:sha256(p) for p in OUT.glob('*.json')},'fit_during_evaluation':False})


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['freeze','build','score']);args=p.parse_args()
    {'freeze':freeze,'build':build,'score':score}[args.phase]()
