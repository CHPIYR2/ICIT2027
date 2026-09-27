"""Event-first macro estimates and paired scenario-stratified event bootstrap."""
import random
import statistics
from collections import defaultdict
from .custody import require_development
from .tokens import quantile

BASELINES=('B0','B1','B2','B3','B4')
CONTRASTS=(('B1','B2'),('B2','B3'),('B3','B4'))

def aggregate(cells,metric,strata=None,stratified=True,resamples=2000,seed=20270922):
    if resamples!=2000 or seed!=20270922:raise ValueError('Statistical configuration differs from approved plan')
    B4_ONLY={'verifier_disposition_accuracy','fixed_opportunity_action_accuracy','positive_action_accuracy','guardrail_action_accuracy'}
    applicable=('B4',) if metric in B4_ONLY else BASELINES
    contrasts=() if metric in B4_ONLY else CONTRASTS
    grouped=defaultdict(dict)
    for c in cells:
        require_development(c['event_id'])
        if c['baseline'] not in BASELINES or c['repetition'] not in (1,2,3):raise ValueError('Invalid cell')
        if c['baseline'] not in applicable:continue
        k=(c['event_id'],c['baseline']);r=c['repetition']
        if r in grouped[k]:raise ValueError('Duplicate repetition')
        grouped[k][r]=c['metrics'][metric]
    if not grouped:raise ValueError('No reviewed cells')
    if any(set(g)!={1,2,3} for g in grouped.values()):raise ValueError('All three repetitions must be retained, including NA/failures')
    events={k[0] for k in grouped}
    if any((e,b) not in grouped for e in events for b in applicable):raise ValueError('Complete planned baseline matrix required')
    if stratified and (strata is None or any(e not in strata or strata[e] is None for e in events)):raise ValueError('Predeclared scenario map required')
    strata={e:strata[e] if stratified else 'explicitly_unstratified' for e in events}
    event_scores={};stability=[]
    for (e,b),reps in sorted(grouped.items()):
        values=[]
        for r,m in sorted(reps.items()):
            n,d=m['numerator'],m['denominator']
            if not 0<=n<=d or m['value']!=(n/d if d else None):raise ValueError('Metric count/ratio mismatch')
            if m['value'] is not None:values.append(m['value'])
        event_scores[e,b]=statistics.mean(values) if values else None
        stability.append({'event_id':e,'baseline':b,'repetition_values':[reps[r]['value'] for r in (1,2,3)],'defined_repetitions':len(values),'event_mean':event_scores[e,b],'range':max(values)-min(values) if values else None,'population_sd':statistics.pstdev(values) if values else None})
    rng=random.Random(seed)
    def estimate(vals):
        if not vals:return {'estimate':None,'CI95':[None,None],'defined_events':0,'strata_counts':{}}
        groups=defaultdict(list)
        for e in sorted(vals):groups[strata[e]].append(e)
        boots=[]
        for _ in range(resamples):
            sample=[rng.choice(g) for _,g in sorted(groups.items()) for _ in range(len(g))]
            boots.append(statistics.mean(vals[e] for e in sample))
        return {'estimate':statistics.mean(vals.values()),'CI95':[quantile(boots,.025),quantile(boots,.975)],'defined_events':len(vals),'strata_counts':{s:len(g) for s,g in sorted(groups.items())},'singleton_strata':[s for s,g in groups.items() if len(g)==1]}
    macro={};micro={}
    for b in applicable:
        vals={e:event_scores[e,b] for e in events if event_scores[e,b] is not None}
        macro[b]=estimate(vals);macro[b]['NA_events']=len(events)-len(vals)
        if b=='B0' and any(not(reps[1]==reps[2]==reps[3]) for (e,x),reps in grouped.items() if x==b):raise ValueError('Deterministic B0 slots must reference one identical result')
        ms=[m for (e,x),reps in grouped.items() if x==b for m in ([reps[1]] if b=='B0' else reps.values())]
        n=sum(m['numerator'] for m in ms);d=sum(m['denominator'] for m in ms)
        micro[b]={'numerator':n,'denominator':d,'value':n/d if d else None,'diagnostic_only':True}
    paired={}
    for a,b in contrasts:
        vals={e:event_scores[e,b]-event_scores[e,a] for e in events if event_scores[e,a] is not None and event_scores[e,b] is not None}
        paired[a+'_vs_'+b]=estimate(vals);paired[a+'_vs_'+b]['direction']=b+' minus '+a
        paired[a+'_vs_'+b]['omitted_unpaired_events']=sorted(events-set(vals))
    return {'metric':metric,'primary':'event_macro','macro':macro,'micro_diagnostic':micro,'paired_contrasts':paired,'stability':stability,'bootstrap_resamples':resamples,'bootstrap_seed':seed,'stratified':stratified,'CI_scope':'conditional on these Sherlock events/scenarios, not real-world OT deployments'}
