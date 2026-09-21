"""Approved exploratory matrix; preserved v1 references and regime-matched Basic fitting."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import argparse,gzip,json,platform,importlib.metadata
from datetime import datetime,timezone
import joblib
import numpy as np
from sherlock.io import ROOT,read_json,save_json,sha256,verify_protocol
from run_heldout import verify_lock as verify_v1,grouped_metrics
from evidence.schema import EvidenceEpisode
from evidence.observability_v2 import transport_projection,visibility_receipt,DURATIONS
from features.network_transport_v2 import extract_transport,NAMES
from features.extract import extract,E_NAMES,N_NAMES
from sherlock.sanitizer import validate_features
from triage.baseline import make_pipeline,contributions,matrix as original_matrix
from paired_bootstrap import contrasts

OUT=ROOT/'results/exploratory-v2';LOCK=ROOT/'configs/protocol.v2.lock.json'
TAG='exploratory / post-confirmatory / Protocol v2; previously observed evaluation events'
REGIMES={60:'N_TRANSPORT_T60',45:'N_DEGRADED_TRANSPORT_T45',30:'N_DEGRADED_TRANSPORT_T30',15:'N_DEGRADED_TRANSPORT_T15'}


def now():return datetime.now(timezone.utc).isoformat()


def verify_original():
    verify_v1()
    for p,h in read_json(OUT/'audit/immutable_inputs.before.json').items():
        if sha256(ROOT/p)!=h:raise ValueError('Original artifact changed: '+p)


def verify_lock():
    verify_original();lock=read_json(LOCK)
    for p,h in lock['files'].items():
        if sha256(ROOT/p)!=h:raise ValueError('Protocol-v2 frozen artifact changed: '+p)
    return lock


def freeze():
    verify_original()
    if LOCK.exists():raise ValueError('Cannot overwrite protocol lock')
    tests=read_json(OUT/'tests.json')
    if not tests['passed']:raise ValueError('Tests not passed')
    for name in ['network_observability.v2.json','features.v2.json','evaluation.v2.json']:
        p=ROOT/'configs'/name;d=read_json(p)
        if not d['execution_enabled'] or d['status']!='approved_for_implementation':raise ValueError('Approval missing')
        d['status']='frozen_exploratory';save_json(p,d)
    paths=[]
    for folder in ['src','experiments','tests']:
        paths.extend((ROOT/folder).rglob('*.py'))
    for name in ['network_observability.v2.json','features.v2.json','evaluation.v2.json','evidence_contract.v1.json','split.v1.json','models.v1.json','features.v1.json','pipeline.v2.json','evaluation.v1.lock.json']:
        paths.append(ROOT/'configs'/name)
    paths.extend([ROOT/'requirements.lock',OUT/'tests.json',OUT/'approval/authorization.json',OUT/'review_manifest.json'])
    for partition in ['development','held_out']:paths.append(ROOT/f'data/processed/v2/{partition}_features.json')
    save_json(LOCK,{'protocol':'Protocol v2','status':'frozen_exploratory','interpretation':TAG,'frozen_at_utc':now(),
        'approval':read_json(OUT/'approval/authorization.json'),'files':{str(p.relative_to(ROOT)):sha256(p) for p in sorted(set(paths))}})
    print('Protocol v2 frozen before any new regime scores.',flush=True)


def save_gzip(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('wb') as raw,gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0,compresslevel=3) as f:
        f.write(json.dumps(data,separators=(',',':'),allow_nan=False).encode())


def build():
    verify_lock()
    if (OUT/'features/manifest.json').exists():raise ValueError('Features already built')
    total=0
    for partition in ['development','held_out']:
        rows=[]
        for old in read_json(ROOT/f'data/processed/v2/{partition}_features.json')['rows']:
            path=ROOT/old['evidence_path']
            if sha256(path)!=old['evidence_sha256']:raise ValueError('Canonical evidence changed')
            with gzip.open(path,'rt') as f:episode=EvidenceEpisode.from_dict(json.load(f))
            if episode.episode_id!=old['episode_id'] or extract(episode)!=old['values']:raise ValueError('E/FULL recipe mismatch')
            full=transport_projection(episode);receipt=visibility_receipt(episode,full)
            receipt['canonical_evidence_sha256']=old['evidence_sha256']
            receipt['protocol_lock_sha256']=sha256(LOCK)
            receipt_path=OUT/'features/visibility'/f'{episode.episode_id}.json.gz'
            save_gzip(receipt_path,receipt)
            regimes={};counts={}
            fullpost=sum(p.observation_time>=full.anchor_time for p in full.packets)
            for seconds,regime in REGIMES.items():
                projection=full.restrict(seconds)
                regimes[regime]=extract_transport(projection)
                post=sum(p.observation_time>=full.anchor_time for p in projection.packets)
                counts[regime]={'post_seconds':seconds,'post_packets':post,'full_post_packets':fullpost,
                               'packet_retention':post/fullpost if fullpost else None}
            rows.append({'episode_id':old['episode_id'],'E':{n:old['values'][n] for n in E_NAMES},
                'N_FULL':{n:old['values'][n] for n in N_NAMES},'network_regimes':regimes,'retention':counts,
                'evidence_path':old['evidence_path'],'evidence_sha256':old['evidence_sha256'],
                'visibility_path':str(receipt_path.relative_to(ROOT)),'visibility_sha256':sha256(receipt_path)})
            total+=1
            if total%20==0:print('Evidence projected:',total,'/119',flush=True)
        save_json(OUT/f'features/{partition}.json',{'interpretation':TAG,'rows':rows})
    verify_lock()
    save_json(OUT/'features/manifest.json',{'created_at_utc':now(),'interpretation':TAG,'events':total,
        'protocol_lock_sha256':sha256(LOCK),'files':{p.name:sha256(p) for p in (OUT/'features').glob('*.json')}})


def load_rows(partition):
    verify_lock();manifest=read_json(OUT/'features/manifest.json')
    if manifest['protocol_lock_sha256']!=sha256(LOCK):raise ValueError('Wrong feature protocol')
    path=OUT/f'features/{partition}.json'
    if sha256(path)!=manifest['files'][path.name]:raise ValueError('Feature file changed')
    rows=read_json(path)['rows'];split,_=verify_protocol()
    if [r['episode_id'] for r in rows]!=split[partition]:raise ValueError('Partition order mismatch')
    for row in rows:
        validate_features(row['E'],E_NAMES);validate_features(row['N_FULL'],N_NAMES)
        if set(row['network_regimes'])!=set(REGIMES.values()):raise ValueError('Regime mismatch')
        for vals in row['network_regimes'].values():validate_features(vals,NAMES)
        if sha256(ROOT/row['visibility_path'])!=row['visibility_sha256']:raise ValueError('Visibility receipt changed')
    return rows


def predictor_matrix(rows,regime,view):
    if regime not in REGIMES.values() or view not in ('N','EN'):raise ValueError('Unknown model condition')
    feature_names=(E_NAMES if view=='EN' else [])+NAMES
    data=[]
    for row in rows:
        vals={**(row['E'] if view=='EN' else {}),**row['network_regimes'][regime]}
        validate_features(vals,feature_names)
        data.append([float('nan') if vals[n] is None else vals[n] for n in feature_names])
    return np.asarray(data,dtype=float),feature_names


def metadata(rows):
    catalog={e['episode_id']:e for e in read_json(ROOT/'data/evaluator/event_catalog.json')['events']}
    ms=[catalog[r['episode_id']] for r in rows]
    return ms,np.array([int(m['event_truth']=='CYBER') for m in ms])


def reuse_references(rows,partition):
    path='results/development-v2/predictions.json' if partition=='development' else 'results/heldout-v1/predictions.json'
    old=read_json(ROOT/path)['rows'];result=[]
    for r in old:
        if partition=='held_out' and r['condition']!='primary':continue
        result.append({'episode_id':r['episode_id'],'model':r['model'],'regime':'E_REFERENCE' if r['view']=='E' else 'N_FULL_T60',
                       'view':r['view'],'event_truth':r['event_truth'],'score':r['cyber_score'],'reference_source':path,
                       'contributions':r['contributions'],'fold':r.get('fold')})
    return result


def verify_reference_predictions(rows):
    oldrows=[{'values':{**r['E'],**r['N_FULL']}} for r in rows]
    refs=reuse_references(rows,'held_out')
    for model in read_json(ROOT/'configs/models.v1.json')['models']:
        for view in ['E','N','EN']:
            pipeline=joblib.load(ROOT/f'results/development-v2/models/{model}_{view}.joblib')
            scores=pipeline.predict_proba(original_matrix(oldrows,view))[:,1]
            saved=[r['score'] for r in refs if r['model']==model and r['view']==view]
            if not np.allclose(scores,saved,rtol=0,atol=1e-12):raise ValueError('FULL/E reference reproduction failed')


def train():
    rows=load_rows('development');split,_=verify_protocol();ms,y=metadata(rows)
    cfg=read_json(ROOT/'configs/models.v1.json');dest=OUT/'development'
    if (dest/'started.json').exists():raise ValueError('Development run already started')
    save_json(dest/'started.json',{'at_utc':now(),'interpretation':TAG,'protocol_lock_sha256':sha256(LOCK)})
    folds=np.array([split['development_fold_assignment'][r['episode_id']] for r in rows])
    predictions=reuse_references(rows,'development');fitting=[]
    for regime in REGIMES.values():
        for model in cfg['models']:
            for view in ['N','EN']:
                x,feature_names=predictor_matrix(rows,regime,view);scores=np.full(len(rows),np.nan);cs={}
                for fold in sorted(set(folds)):
                    tr,va=folds!=fold,folds==fold;pipe=make_pipeline(model,cfg).fit(x[tr],y[tr])
                    scores[va]=pipe.predict_proba(x[va])[:,1]
                    contrib=contributions(pipe,x[va],feature_names)
                    if contrib:cs.update(zip(np.flatnonzero(va).tolist(),contrib))
                    fitting.append({'regime':regime,'model':model,'view':view,'fold':int(fold),
                        'training_ids':[r['episode_id'] for i,r in enumerate(rows) if tr[i]],
                        'validation_ids':[r['episode_id'] for i,r in enumerate(rows) if va[i]]})
                if not np.isfinite(scores).all():raise ValueError('Invalid OOF scores')
                for i,row in enumerate(rows):predictions.append({'episode_id':row['episode_id'],'regime':regime,'model':model,'view':view,
                    'event_truth':int(y[i]),'score':float(scores[i]),'fold':int(folds[i]),'contributions':cs.get(i)})
                final=make_pipeline(model,cfg).fit(x,y);path=dest/'models'/f'{regime}__{model}__{view}.joblib'
                path.parent.mkdir(parents=True,exist_ok=True);joblib.dump(final,path)
            print('Fitted',regime,model,flush=True)
    verify_lock()
    save_json(dest/'predictions.json',{'interpretation':TAG,'scope':'Basic OOF; reference rows reused','rows':predictions})
    save_json(dest/'fitting.json',{'fold_fits':fitting,'final_fit_ids':split['development']})
    save_json(dest/'models.json',{str(p.relative_to(ROOT)):sha256(p) for p in sorted((dest/'models').glob('*.joblib'))})
    summarize(rows,predictions,'development')


def score():
    rows=load_rows('held_out');ms,y=metadata(rows);dest=OUT/'evaluation'
    if (dest/'started.json').exists():raise ValueError('Exploratory evaluation already started')
    hashes=read_json(OUT/'development/models.json')
    for p,h in hashes.items():
        if sha256(ROOT/p)!=h:raise ValueError('Trained artifact changed')
    verify_reference_predictions(rows)
    save_json(dest/'started.json',{'at_utc':now(),'interpretation':TAG,'protocol_lock_sha256':sha256(LOCK),
                                 'models_manifest_sha256':sha256(OUT/'development/models.json')})
    predictions=reuse_references(rows,'held_out');cfg=read_json(ROOT/'configs/models.v1.json')
    for regime in REGIMES.values():
        for model in cfg['models']:
            for view in ['N','EN']:
                x,feature_names=predictor_matrix(rows,regime,view)
                pipe=joblib.load(OUT/f'development/models/{regime}__{model}__{view}.joblib')
                if pipe.n_features_in_!=len(feature_names) or list(pipe.classes_)!=[0,1]:raise ValueError('Model schema mismatch')
                scores=pipe.predict_proba(x)[:,1];cs=contributions(pipe,x,feature_names)
                if not np.isfinite(scores).all():raise ValueError('Nonfinite scores')
                for i,row in enumerate(rows):predictions.append({'episode_id':row['episode_id'],'regime':regime,'model':model,'view':view,
                    'event_truth':int(y[i]),'score':float(scores[i]),'contributions':cs[i] if cs else None})
    verify_lock()
    save_json(dest/'predictions.json',{'interpretation':TAG,'scope':'Previously observed 84 events; exploratory','rows':predictions})
    summarize(rows,predictions,'evaluation')
    save_json(dest/'run_manifest.json',{'interpretation':TAG,'finished_at_utc':now(),'protocol_lock_sha256':sha256(LOCK),
        'python':sys.version,'platform':platform.platform(),'fit_during_evaluation':False,
        'packages':{n:importlib.metadata.version(n) for n in ['numpy','scipy','scikit-learn','joblib']},
        'reference_reproduction_passed':True,'prediction_sha256':sha256(dest/'predictions.json'),
        'metrics_sha256':sha256(dest/'metrics.json'),'bootstrap_sha256':sha256(dest/'paired_bootstrap.json')})


def summarize(rows,predictions,partition):
    ms,y=metadata(rows);scene=np.array([m['scenario'] for m in ms]);lookup={}
    for r in predictions:
        k=(r['regime'],r['model'],r['view']);lookup.setdefault(k,{})[r['episode_id']]=r
    scores={k:np.array([v[r['episode_id']]['score'] for r in rows]) for k,v in lookup.items()}
    metrics={};boot={};transition_rows=[]
    bc={'repetitions':2000,'seed':20270921,'contrasts':['EN-N','EN-E'],'metrics':['macro_f1','balanced_accuracy']}
    for (regime,model,view),s in scores.items():
        metrics.setdefault(regime,{}).setdefault(model,{})[view]=grouped_metrics(y,s,ms)
    for regime in ['N_FULL_T60',*REGIMES.values()]:
        boot[regime]={}
        for model in read_json(ROOT/'configs/models.v1.json')['models']:
            ss={v:scores[(regime,model,v)] for v in ['N','EN']};ss['E']=scores[('E_REFERENCE',model,'E')]
            boot[regime][model]={'overall':contrasts(y,ss,scene,bc),'scenario':{}}
            for group in sorted(set(scene)):
                mask=scene==group
                boot[regime][model]['scenario'][group]=contrasts(y[mask],{v:a[mask] for v,a in ss.items()},scene[mask],bc)
            for i,row in enumerate(rows):
                n,en=ss['N'][i]>=.5,ss['EN'][i]>=.5;nc,ec=n==y[i],en==y[i]
                status=('unchanged_both_correct' if nc else 'unchanged_both_wrong') if n==en else ('corrected_N' if ec else 'hurt_N')
                transition_rows.append({'episode_id':row['episode_id'],'scenario':ms[i]['scenario'],
                    'recording':ms[i]['recording'],'family':ms[i]['family_description'],'truth':int(y[i]),
                    'regime':regime,'model':model,'N_score':float(ss['N'][i]),'EN_score':float(ss['EN'][i]),
                    'N_prediction':int(n),'EN_prediction':int(en),'N_correct':bool(nc),'EN_correct':bool(ec),'transition':status,
                    'canonical_evidence_path':row['evidence_path'],'canonical_evidence_sha256':row['evidence_sha256'],
                    'visibility_path':row['visibility_path'],'visibility_sha256':row['visibility_sha256'],
                    'visibility_key':'canonical_full' if regime=='N_FULL_T60' else regime.rsplit('T',1)[1],
                    'visibility_note':'FULL uses canonical N; transport uses receipt levels/T packet IDs and denies all IEC message records'})
    dest=OUT/partition
    save_json(dest/'metrics.json',{'interpretation':TAG,'metrics':metrics})
    save_json(dest/'paired_bootstrap.json',{'interpretation':TAG,'config':bc,'results':boot})
    save_json(OUT/f'transitions/{partition}.json',{'interpretation':TAG,'access':'EVALUATOR_ONLY; private visibility manifests','rows':transition_rows})
    print(partition,'summary complete:',len(predictions),'predictions',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['freeze','build','train','score']);args=p.parse_args()
    {'freeze':freeze,'build':build,'train':train,'score':score}[args.phase]()
