#!/usr/bin/env python3
"""Basic-only OOF baselines. No held-out construction, prediction, or tuning."""
from datetime import datetime, timezone
import gzip
import importlib.metadata
import json
import platform
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import joblib
import numpy as np

from evidence.schema import EvidenceEpisode
from evaluation.metrics import classification_metrics
from features.extract import extract
from sherlock.io import read_json, save_json, sha256, verify_protocol
from triage.baseline import contributions, make_pipeline, matrix, names


def implementation_files():
    paths=sorted((ROOT/'src').rglob('*.py'))+sorted((ROOT/'experiments').glob('*.py'))+sorted((ROOT/'tests').glob('*.py'))
    paths += [ROOT/'configs/pipeline.v2.json',ROOT/'configs/evaluation.v1.json',ROOT/'configs/features.v1.json',ROOT/'configs/models.v1.json',ROOT/'requirements.lock',ROOT/'pyproject.toml']
    return {str(p.relative_to(ROOT)):sha256(p) for p in paths}


def main():
    split, _ = verify_protocol()
    config = read_json(ROOT/'configs/models.v1.json')
    output = ROOT/'results/development-v2'
    if (output/'metrics.json').exists():
        raise SystemExit('Completed run already exists; preserve it and use a new version for changes.')
    rows = read_json(ROOT/'data/processed/v2/development_features.json')['rows']
    if [r['episode_id'] for r in rows] != split['development']:
        raise ValueError('Feature rows do not match frozen development IDs/order')
    # Revalidate the evidence boundary and recompute features before any fit.
    for row in rows:
        path = ROOT/row['evidence_path']
        if sha256(path) != row['evidence_sha256']: raise ValueError('Evidence changed')
        with gzip.open(path,'rt') as f: episode=EvidenceEpisode.from_dict(json.load(f))
        if episode.episode_id != row['episode_id'] or extract(episode) != row['values']:
            raise ValueError('Feature recipe/evidence mismatch')
    source_files=implementation_files()
    lock={'created_at_utc':datetime.now(timezone.utc).isoformat(),
          'scope':'Development baseline implementation snapshot, before first fit; held-out still gated.',
          'files':source_files,'protocol_lock_sha256':sha256(ROOT/'configs/protocol.v1.lock.json')}
    save_json(output/'implementation.lock.json',lock)
    # The evaluator reads truth separately. Only the numeric matrix goes to sklearn.
    truth = {e['episode_id']:e for e in read_json(ROOT/'data/evaluator/event_catalog.json')['events'] if e['episode_id'] in set(split['development'])}
    y=np.array([int(truth[r['episode_id']]['event_truth']=='CYBER') for r in rows])
    folds=np.array([split['development_fold_assignment'][r['episode_id']] for r in rows])
    metrics, predictions = {}, []
    for model_name in config['models']:
        metrics[model_name]={}
        for view in config['views']:
            x=matrix(rows,view);scores=np.full(len(rows),np.nan);explanations={}
            for fold in sorted(set(folds)):
                train,valid=folds!=fold,folds==fold
                pipeline=make_pipeline(model_name,config).fit(x[train],y[train])
                scores[valid]=pipeline.predict_proba(x[valid])[:,1]
                cs=contributions(pipeline,x[valid],names(view))
                if cs:
                    explanations.update(zip(np.flatnonzero(valid).tolist(),cs))
            assert np.isfinite(scores).all()
            metrics[model_name][view]={'overall':classification_metrics(y,scores,config['prediction_threshold']),
                                     'by_recording':{},'by_family':{}}
            for field,destination in [('recording','by_recording'),('family_description','by_family')]:
                for group in sorted({e[field] for e in truth.values()}):
                    mask=np.array([truth[r['episode_id']][field]==group for r in rows])
                    metrics[model_name][view][destination][group]=classification_metrics(y[mask],scores[mask],config['prediction_threshold'])
            for i,row in enumerate(rows):
                predictions.append({'episode_id':row['episode_id'],'model':model_name,'view':view,'fold':int(folds[i]),
                                    'event_truth':int(y[i]),'cyber_score':float(scores[i]),
                                    'prediction':'CYBER_RELATED' if scores[i]>=config['prediction_threshold'] else 'BENIGN_OPERATIONAL',
                                    'evidence_sha256':row['evidence_sha256'],'contributions':explanations.get(i)})
            final=make_pipeline(model_name,config).fit(x,y)
            model_path=output/'models'/f'{model_name}_{view}.joblib'
            model_path.parent.mkdir(parents=True,exist_ok=True)
            joblib.dump(final,model_path)
            m=metrics[model_name][view]['overall']
            print(json.dumps({'model':model_name,'view':view,'macro_f1':m['macro_f1'],'balanced_accuracy':m['balanced_accuracy']}),flush=True)
    if implementation_files()!=source_files:
        raise ValueError('Implementation changed during run')
    save_json(output/'predictions.json',{'access':'EVALUATOR_ONLY','partition':'development_oof','rows':predictions})
    save_json(output/'metrics.json',{'partition':'development_oof','held_out_evaluated':False,'metrics':metrics})
    save_json(output/'run_manifest.json',{
        'finished_at_utc':datetime.now(timezone.utc).isoformat(),'python':sys.version,'platform':platform.platform(),
        'packages':{name:importlib.metadata.version(name) for name in ['scikit-learn','numpy','scipy','joblib','threadpoolctl']},
        'git_commit':None,'code_version_method':'SHA256 implementation.lock.json; workspace has no Git repository',
        'implementation_lock_sha256':sha256(output/'implementation.lock.json'),
        'features_sha256':sha256(ROOT/'data/processed/v2/development_features.json'),
        'dataset_manifest_sha256':sha256(ROOT/'data/manifests/sherlock_manifest.json'),
        'prediction_sha256':sha256(output/'predictions.json'),'metrics_sha256':sha256(output/'metrics.json'),
        'development_ids':split['development'],'held_out_evaluated':False,
        'model_hashes':{p.name:sha256(p) for p in sorted((output/'models').glob('*.joblib'))}})


if __name__=='__main__':main()
