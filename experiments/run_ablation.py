"""Development-only predeclared command-group ablation; main baseline preserved."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from datetime import datetime,timezone
import joblib
import numpy as np
from sherlock.io import ROOT,read_json,save_json,sha256,verify_protocol
from triage.baseline import make_pipeline,matrix,names
from evaluation.metrics import classification_metrics


def main():
    split,_=verify_protocol();cfg=read_json(ROOT/'configs/models.v1.json');ev=read_json(ROOT/'configs/evaluation.v1.json')
    out=ROOT/'results/ablation-development-v1'
    if (out/'metrics.json').exists():raise SystemExit('Run already exists')
    rows=read_json(ROOT/'data/processed/development_features.json')['rows']
    if [r['episode_id'] for r in rows]!=split['development']:raise ValueError('Development ID mismatch')
    truth={e['episode_id']:e['event_truth'] for e in read_json(ROOT/'data/evaluator/event_catalog.json')['events']}
    y=np.array([int(truth[r['episode_id']]=='CYBER') for r in rows])
    folds=np.array([split['development_fold_assignment'][r['episode_id']] for r in rows])
    save_json(out/'prefit.json',{'created_at_utc':datetime.now(timezone.utc).isoformat(),
              'script_sha256':sha256(Path(__file__)),'config_sha256':sha256(ROOT/'configs/evaluation.v1.json'),
              'features_sha256':sha256(ROOT/'data/processed/development_features.json')})
    results={};predictions=[]
    for model in cfg['models']:
        results[model]={}
        for view in ev['diagnostic_views']:
            indices=[i for i,n in enumerate(names(view)) if n not in ev['diagnostic_drop_features']]
            x=matrix(rows,view)[:,indices];scores=np.full(len(rows),np.nan)
            for fold in sorted(set(folds)):
                train,valid=folds!=fold,folds==fold
                pipeline=make_pipeline(model,cfg).fit(x[train],y[train])
                scores[valid]=pipeline.predict_proba(x[valid])[:,1]
            results[model][view]=classification_metrics(y,scores)
            predictions.extend({'episode_id':r['episode_id'],'model':model,'view':view,'fold':int(folds[i]),'event_truth':int(y[i]),'score':float(scores[i])} for i,r in enumerate(rows))
            final=make_pipeline(model,cfg).fit(x,y)
            path=out/'models'/f'{model}_{view}.joblib';path.parent.mkdir(parents=True,exist_ok=True);joblib.dump(final,path)
            print(model,view,results[model][view]['macro_f1'],flush=True)
    save_json(out/'predictions.json',predictions)
    save_json(out/'metrics.json',{'scope':'Basic-only diagnostic OOF','removed':ev['diagnostic_drop_features'],'metrics':results})
    save_json(out/'models.json',{str(p.relative_to(ROOT)):sha256(p) for p in sorted((out/'models').glob('*.joblib'))})

if __name__=='__main__':main()
