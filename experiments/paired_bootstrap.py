"""Fixed-stratum event bootstrap; one resampling matrix shared across contrasts."""
import numpy as np


def sampled_indices(y, groups, repetitions, seed):
    y=np.asarray(y);groups=np.asarray(groups)
    rng=np.random.default_rng(seed);parts=[]
    for group in sorted(set(groups.tolist())):
        for label in sorted(set(y.tolist())):
            indices=np.flatnonzero((groups==group)&(y==label))
            if len(indices):parts.append(rng.choice(indices,size=(repetitions,len(indices)),replace=True))
    if not parts:raise ValueError('Empty bootstrap')
    return np.concatenate(parts,axis=1)


def metric_vector(y, pred):
    y=np.asarray(y);pred=np.asarray(pred)
    tp=((y==1)&(pred==1)).sum(axis=-1);tn=((y==0)&(pred==0)).sum(axis=-1)
    fp=((y==0)&(pred==1)).sum(axis=-1);fn=((y==1)&(pred==0)).sum(axis=-1)
    return {'macro_f1':.5*(2*tp/(2*tp+fp+fn)+2*tn/(2*tn+fp+fn)),
            'balanced_accuracy':.5*(tp/(tp+fn)+tn/(tn+fp))}


def contrasts(y, scores, groups, config):
    y=np.asarray(y)
    if len(set(y.tolist()))!=2:return None
    indices=sampled_indices(y,groups,config['repetitions'],config['seed'])
    points={v:metric_vector(y,np.asarray(s)>=.5) for v,s in scores.items()}
    samples={v:metric_vector(y[indices],(np.asarray(s)>=.5)[indices]) for v,s in scores.items()}
    output={}
    for contrast in config['contrasts']:
        left,right=contrast.split('-');output[contrast]={}
        for metric in config['metrics']:
            delta=samples[left][metric]-samples[right][metric]
            output[contrast][metric]={'point':float(points[left][metric]-points[right][metric]),
                                     'ci95':np.percentile(delta,[2.5,97.5]).tolist(),
                                     'replicates':len(delta)}
    return output
