"""Event-first tables and paired stratified bootstrap; no final-data loader."""
import random
from statistics import mean, pstdev
from collections import defaultdict
from .contracts import *
from .scoring import need, ratio

CONTRASTS={'EN_minus_E':('G1-E','G1-EN'),'EN_minus_N':('G1-N','G1-EN'),
 'EN_minus_G0':('G0','G1-EN'),'V1_minus_G1':('G1-EN','V1-EN')}

def quantile(xs,q):
 xs=sorted(xs);i=(len(xs)-1)*q;lo=int(i);hi=min(lo+1,len(xs)-1)
 return xs[lo]+(xs[hi]-xs[lo])*(i-lo)

def bootstrap(values,strata,all_events,direction,structural=False):
 base={'direction':direction,'mean_difference':None,'ci95':[None,None],
 'paired_event_count':len(values),'omitted_event_ids':sorted(set(all_events)-set(values)),
 'stratum_counts':{},'singleton_strata':[],'structural_not_applicable':structural,'display':'—' if structural else 'NA'}
 if structural:return base
 if not values:return base
 groups=defaultdict(list)
 for e in sorted(values):groups[strata[e]].append(e)
 rng=random.Random(20270922);boots=[]
 for _ in range(2000):
  sampled=[rng.choice(g) for _,g in sorted(groups.items()) for _ in range(len(g))]
  boots.append(mean(values[e] for e in sampled))
 base.update(mean_difference=mean(values.values()),ci95=[quantile(boots,.025),quantile(boots,.975)],
  stratum_counts={k:len(v) for k,v in sorted(groups.items())},singleton_strata=sorted(k for k,v in groups.items() if len(v)==1),display='defined')
 return base

def aggregate(scores,strata):
 runs={}
 for s in scores:
  e,c,r=s['event_id'],s['cell_id'],s['repetition']
  need((e,c,r) not in runs,'Duplicate repetition')
  need(c in VIEWS and r in ((0,) if c=='D0' else (1,2,3)),'Invalid cell/repetition')
  need(set(s['metrics'])==set(METRICS),'Wrong canonical metric set')
  for m in s['metrics'].values():need(m==ratio(m['numerator'],m['denominator']),'Ratio mismatch')
  runs[e,c,r]=s
 events=sorted({e for e,c,r in runs});need(bool(events),'No runs')
 need(set(strata)==set(events) and all(isinstance(x,str) and x for x in strata.values()),'Exact predeclared scenario strata required')
 include_d0=any(c=='D0' for e,c,r in runs);conditions=CELLS+(('D0',) if include_d0 else ())
 expected={(e,c,r) for e in events for c in conditions for r in ((0,) if c=='D0' else (1,2,3))}
 need(set(runs)==expected,'All planned positions required, including NA/delivery failures')
 for e in events:
  need(len({s['gold_sha256'] for (x,c,r),s in runs.items() if x==e})==1,'Common gold denominator changed between conditions')
  for r in (1,2,3):
   a,b=runs[e,'G1-EN',r],runs[e,'V1-EN',r]
   need(a['raw_output_sha256']==b['raw_output_sha256'] and a['bundle_sha256']==b['bundle_sha256'],'RQ3 must pair identical stored raw response and bundle')
 event_metrics={};stability=[];macro={};micro={};paired={}
 for m in METRICS:
  macro[m]={};micro[m]={};paired[m]={}
  for c in conditions:
   for e in events:
    ss=[runs[e,c,r] for r in ((0,) if c=='D0' else (1,2,3))]
    vals=[s['metrics'][m]['value'] for s in ss if s['metrics'][m]['value'] is not None]
    event_metrics[e,c,m]=mean(vals) if vals else None
    stability.append({'event_id':e,'condition':c,'metric':m,'repetition_values':[s['metrics'][m]['value'] for s in ss],
     'n_defined_repetitions':len(vals),'event_mean':event_metrics[e,c,m],
     'range':max(vals)-min(vals) if vals else None,'population_sd':pstdev(vals) if vals else None})
   vals=[event_metrics[e,c,m] for e in events if event_metrics[e,c,m] is not None]
   macro[m][c]={'mean':mean(vals) if vals else None,'defined_event_count':len(vals),
    'undefined_event_ids':[e for e in events if event_metrics[e,c,m] is None],'population_event_count':len(events)}
   counts=[s['metrics'][m] for (e,x,r),s in runs.items() if x==c]
   micro[m][c]=ratio(sum(s['numerator'] for s in counts),sum(s['denominator'] for s in counts))
  for label,(a,b) in CONTRASTS.items():
   structural=label=='V1_minus_G1' and m in ('required_withholding_recall','withholding_precision')
   vals={} if structural else {e:event_metrics[e,b,m]-event_metrics[e,a,m] for e in events if event_metrics[e,a,m] is not None and event_metrics[e,b,m] is not None}
   paired[m][label]=bootstrap(vals,strata,events,b+' minus '+a,structural)
 return {'events':events,'conditions':conditions,'runs':runs,'event_metrics':event_metrics,'stability':stability,
  'macro':macro,'micro':micro,'paired':paired}

def products(scores,strata,*,data_label):
 need(data_label in ('SYNTHETIC_TEST_ONLY_NOT_PAPER_RESULTS','FROZEN_EVALUATION_REVIEWED'),'Unlabeled or development results forbidden in paper products')
 if data_label.startswith('SYNTHETIC'):
  need(all(s['event_id'].startswith('SYNTHETIC_') for s in scores),'Synthetic namespace required')
 else:
  # Pure API usable later; caller must present already frozen and signed receipts.
  need(all(s.get('frozen_evaluation_commitment') and s.get('scoring_authorization') for s in scores),'Final scoring not authorized by offline package')
 a=aggregate(scores,strata);ev=a['events'];runs=a['runs'];out={}
 for name,rows in TABLE_ROWS.items():
  cells={'table4':('G1-E','G1-N','G1-EN'),'table5':('G0','G1-EN'),'table6':('G1-EN','V1-EN')}[name]
  contrasts={'table4':('EN_minus_E','EN_minus_N'),'table5':('EN_minus_G0',),'table6':('V1_minus_G1',)}[name]
  out[name]=[]
  for m in rows:
   conditions={c:dict(a['macro'][m][c]) for c in cells}
   if name=='table6' and m in ('required_withholding_recall','withholding_precision'):
    conditions['G1-EN']={'mean':None,'defined_event_count':0,'undefined_event_ids':ev,'population_event_count':len(ev)}
   out[name].append({'metric':m,'interpretation':'lower is better; negative delta favors second condition' if m=='unsupported_security_claim_rate' else 'higher is better; positive delta favors second condition',
    'conditions':conditions,'contrasts':{c:a['paired'][m][c] for c in contrasts}})
 out['table7']=[]
 for c in CELLS:
  ss=[s for (e,x,r),s in runs.items() if x==c]
  counts={k:sum(s['counts'][k] for s in ss) for k in COUNT_FIELDS[:7]}
  conditioned={'uscr':'unsupported_security_claim_rate','numerical':'numerical_consistency','withholding_precision':'withholding_precision'}
  for label,m in conditioned.items():counts['defined_'+label+'_denominators']=sum(s['metrics'][m]['denominator']>0 for s in ss)
  out['table7'].append({'condition':c,**counts,'planned_runs':len(ss),
   'valid_delivery_runs':sum(s['delivery']=='VALID' for s in ss),'invalid_delivery_runs':sum(s['delivery']!='VALID' for s in ss),
   'defined_event_counts':{k:a['macro'][m][c]['defined_event_count'] for k,m in conditioned.items()}})
 out['figure2']=[]
 for e in ev:
  for c in CELLS:
   uscr=a['event_metrics'][e,c,'unsupported_security_claim_rate'];coverage=a['event_metrics'][e,c,'q1_q6_substantive_coverage']
   ss=[runs[e,c,r] for r in (1,2,3)]
   out['figure2'].append({'event_id':e,'scenario_stratum':strata[e],'condition':c,'coverage':coverage,
    'uscr':uscr,'uscr_defined':uscr is not None,'security_assertion_count':sum(s['counts']['security_sensitive_assertions'] for s in ss),
    'coverage_defined_repetitions':sum(s['metrics']['q1_q6_substantive_coverage']['value'] is not None for s in ss),
    'uscr_defined_repetitions':sum(s['metrics']['unsupported_security_claim_rate']['value'] is not None for s in ss)})
 out['rq1_funnel']=[]
 for e in ev:
  for c,v in (('G1-E','E'),('G1-N','N'),('G1-EN','EN')):
   ss=[runs[e,c,r] for r in (1,2,3)];fs=[s['funnel'] for s in ss]
   keys=('full_gold_count','supportable_in_view_count','complete_support_retrieved_count')
   need(all(all(f[k]==fs[0][k] for k in keys) for f in fs),'Deterministic retrieval/gold changed across repetitions')
   counts={k:fs[0][k] for k in keys};rec=[f['correctly_reconstructed_count'] for f in fs];vals=[x for x in rec if x is not None]
   out['rq1_funnel'].append({'event_id':e,'view':v,**counts,'correctly_reconstructed_count':mean(vals) if vals else None,
    'reconstructed_by_repetition':rec,'n_defined_repetitions':len(vals),
    'unavailable_in_view':counts['full_gold_count']-counts['supportable_in_view_count'],
    'available_not_retrieved':counts['supportable_in_view_count']-counts['complete_support_retrieved_count'],
    'retrieved_not_reconstructed':counts['complete_support_retrieved_count']-mean(vals) if vals else None})
 for k,v in out.items():validate(k,v)
 out['funnel_summary']={}
 for v in ('E','N','EN'):
  fs=[f for f in out['rq1_funnel'] if f['view']==v]
  fields=('full_gold_count','supportable_in_view_count','complete_support_retrieved_count','correctly_reconstructed_count')
  out['funnel_summary'][v]={k:{'macro_mean':mean([f[k] for f in fs if f[k] is not None]) if any(f[k] is not None for f in fs) else None,
   'event_equivalent_total':sum(f[k] for f in fs if f[k] is not None),
   'defined_events':sum(f[k] is not None for f in fs)} for k in fields}
  out['funnel_summary'][v]['raw_repetition_totals']={'correctly_reconstructed_count':sum(x for f in fs for x in f['reconstructed_by_repetition'] if x is not None),'defined_repetitions':sum(f['n_defined_repetitions'] for f in fs),'interpretation':'Repeated reconstructions across model outputs; not independent events or unique corpus facts'}
 out.update(data_label=data_label,protocol_frozen=False,macro=a['macro'],micro_supplementary=a['micro'],
  paired_bootstrap=a['paired'],repetition_stability=a['stability'],
  statistical_policy={'resamples':2000,'seed':20270922,'unit':'event','stratification':'scenario',
   'CI':'95% percentile, linear interpolation','paired_complete_case':True,
   'CI_scope':'Conditional on these Sherlock events/scenarios, not real-world OT deployments'},
  delivery_exclusions=[{'event_id':s['event_id'],'cell_id':s['cell_id'],'repetition':s['repetition']} for s in scores if s['delivery']!='VALID'])
 return out

def case_study_template():
 return {'status':'NO_CASES_SELECTED','selection_after_aggregate_scoring_only':True,
 'categories':{'A':'Verifier qualifies/blocks unsupported causal/security conclusion',
 'B':'EN recovers supported fact missed by one or both single-source conditions',
 'C':'Correct explicit insufficiency/withholding'},
 'candidate_fields':['event_id','category','repetition','visible_evidence_ids','raw_assertion_id','raw_text',
 'cited_evidence_ids','verifier_disposition','published_text','unresolved_conclusion','review_ledger_sha256','eligibility_reason'],
 'selection_rule':'After aggregate scoring, enumerate all human-confirmed eligible candidates per category; select lexicographically by event_id, then repetition, then assertion_id; disclose all candidate counts and any absence. No visual-drama ranking.',
 'candidates':[],'selected':[]}
