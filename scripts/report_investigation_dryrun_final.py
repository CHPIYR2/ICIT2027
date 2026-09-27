"""Audit the retained original/recovery artifacts without gold or performance tuning."""
import collections,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from investigation_dryrun.common import load,file_hash,digest,binding,create_json,utc
from investigation_dryrun.custody import development_ids,verify_access_log
from investigation_dryrun.batch import expected_cells,verify_preflight,BATCH_ID
from investigation_dryrun.runner import parse_experiment,delivery_validation
from investigation_dryrun.tokens import count,summary
from investigation_dryrun.claims import typed_support,validate_raw_support,canonical_numeric_fact
OUT=ROOT/'results/investigation-dryrun-v1';RUNS=OUT/'runs'

def dist(xs):return summary(xs) if xs else {'n':0,'minimum':None,'median':None,'p90':None,'p95':None,'maximum':None}

def cell(run,eid,b,rep):
 p=RUNS/run/eid/b/f'rep-{rep}';m=load(p/'completed.json')
 assert (m['run_id'],m['event_id'],m['baseline'],m['repetition'])==(run,eid,b,rep)
 bnd=load(p/'bundle.json');receipt=load(p/'receipt.json');request=load(p/'request.json')
 assert digest(bnd)==m['bundle_sha256']==receipt['retrieved_bundle_sha256']
 assert digest(receipt)==m['receipt_sha256'] and digest(request)==m['request_sha256']
 assert request['input']==__import__('investigation_dryrun.common',fromlist=['dumps']).dumps(bnd)
 assert m['actual_evidence_tokens']==count(request['input'])<=16384
 assert request['model']=='gpt-4.1-2025-04-14' and request['temperature']==0 and request['max_output_tokens']==4096
 assert request['text']['format']['type']=='json_schema' and request['text']['format']['strict'] is True
 assert request['truncation']=='disabled' and request['tools']==[] and request['store'] is False and 'seed' not in request
 verify_access_log(p/'access.jsonl')
 for line in (p/'access.jsonl').read_text().splitlines():
  log=json.loads(line);assert log['event_id'] in development_ids()
 if 'output_sha256' in m:assert file_hash(p/'output.raw.json')==m['output_sha256']
 for a in m['attempts']:
  folder=p/f"attempt-{a['attempt']}";assert load(folder/'attempt.json')==a and a['request_sha256']==m['request_sha256']
  if 'response_sha256' in a:assert file_hash(folder/'response.raw')==a['response_sha256']
 assert len(m['attempts'])<=3
 return {'manifest':m,'directory':p,'bundle':bnd,'request':request}

def summarize(rows):
 states=collections.Counter();by=collections.defaultdict(collections.Counter);models=collections.Counter();statuses=collections.Counter();http=collections.Counter();usage=[];attempts=[];trunc=[];reasons=collections.Counter();evidence=[]
 for row in rows:
  m=row['manifest'];states[m['status']]+=1;by[m['baseline']][m['status']]+=1;evidence.append(m['actual_evidence_tokens'])
  for a in m['attempts']:
   attempts.append(a);http[str(a.get('HTTP_status'))]+=1
   if a.get('will_retry'):reasons[a.get('reason','unspecified')]+=1
   md=a.get('provider_metadata')
   if md:
    models[md.get('model')]+=1;statuses[md.get('status')]+=1
    if md.get('usage') is not None:usage.append(md['usage'])
    if md.get('status')=='incomplete' and (md.get('incomplete_details') or {}).get('reason')=='max_output_tokens':
     trunc.append({'event_id':m['event_id'],'baseline':m['baseline'],'repetition':m['repetition'],'run_id':m['run_id'],'attempt':a['attempt'],'response_id':md.get('id'),'status':md['status'],'incomplete_details':md['incomplete_details'],'usage':md.get('usage'),'response_sha256':a.get('response_sha256')})
 return {'generation_cells':len(rows),'statuses':dict(states),'statuses_by_baseline':{b:dict(v) for b,v in by.items()},'schema_valid_complete':states['DELIVERED'],'schema_invalid_complete':states['DELIVERED_SCHEMA_INVALID'],'attempt_records':len(attempts),'HTTP_responses':dict(http),'transport_retry_attempts':sum(a['attempt']>1 for a in attempts),'retry_reasons':dict(reasons),'unknown_delivery_attempts':sum(a.get('HTTP_status') is None for a in attempts),'models':dict(models),'provider_statuses':dict(statuses),'response_ids':[a['provider_metadata']['id'] for a in attempts if a.get('provider_metadata',{}).get('id')],'usage_record_count':len(usage),'attempts_without_usage':len(attempts)-len(usage),'usage':{k:{'distribution':dist([u[k] for u in usage if type(u.get(k)) is int]),'total':sum(u.get(k,0) for u in usage)} for k in ['input_tokens','output_tokens','total_tokens']},'evidence_tokens':dist(evidence),'output_truncations':trunc,'truncation_count':len(trunc)}

def output_checks(row):
 m=row['manifest'];p=row['directory'];b=row['bundle'];counts=collections.Counter();reasons=collections.Counter()
 result={'event_id':m['event_id'],'baseline':m['baseline'],'repetition':m['repetition'],'run_id':m['run_id'],'status':m['status'],'not_a_research_performance_score':True}
 if m['status'] not in ('DELIVERED','DELIVERED_SCHEMA_INVALID'):return result
 exp=parse_experiment((p/'output.raw.json').read_bytes());errors=delivery_validation(exp,m['event_id'],'N' if m['baseline']=='B1' else 'EN','required' if m['baseline']=='B3' else 'optional_baseline');assert bool(errors)==(m['status']=='DELIVERED_SCHEMA_INVALID')
 available={r['evidence_id'] for r in b['entries']}|{r['evidence_id'] for r in b['metadata'].values()}|set(b['control_metadata'])|{b['scope']['evidence_id']}
 projections=[]
 for c in exp['claims']:
  counts['emitted_claims']+=1
  if not isinstance(c,dict):counts['malformed_claims']+=1;continue
  ids=c.get('evidence_ids')
  if isinstance(ids,list) and all(isinstance(x,str) for x in ids):
   counts['parseable_citation_arrays']+=1;counts['unique_citation_edges']+=len(set(ids));counts['invisible_citation_edges']+=sum(x not in available for x in set(ids))
  else:counts['unparseable_citation_arrays']+=1
  try:
   support=typed_support(c,b);counts['typed_support_pass']+=1
   validate_raw_support(c,b,require_citations=m['baseline']=='B3');counts['finite_wording_and_support_pass']+=1
   if c['claim_type'] in ('reported_change','electrical_change'):
    projection=canonical_numeric_fact(c,b,require_citations=m['baseline']=='B3');counts['canonical_numeric_projection_pass']+=1
    projections.append({'claim_id':c['claim_id'],'raw_claim_type':c['claim_type'],'raw_sha256':digest(c),'identity':projection['identity'],'fact_key':projection['fact_key']})
   if c['claim_type']=='asset_relationship' and c['payload']['relation']=='observation_channel_maps_to_asset':counts['channel_asset_mapping_pass']+=1
  except (ValueError,KeyError,TypeError,StopIteration) as e:counts['not_supported_or_not_checkable']+=1;reasons[str(e)]+=1
 result.update(counts=dict(counts),reasons=dict(reasons),schema_errors=errors,canonical_projections=projections)
 return result

def build():
 verify_preflight();authorization=load(OUT/'transport_recovery_authorization.json');rid=authorization['recovery_run_id'];authorized={(x['event_id'],x['baseline'],x['repetition']) for x in authorization['cells']};assert len(authorized)==86
 original=[];recovery=[];effective=[];selection=[];b4=[]
 for eid,b,rep in expected_cells():
  old=cell(BATCH_ID,eid,b,rep);original.append(old);chosen=old
  if (eid,b,rep) in authorized:
   assert old['manifest']['status']=='FAILED_NO_VALID_DELIVERY' and all(a.get('HTTP_status')==429 for a in old['manifest']['attempts'])
   chosen=cell(rid,eid,b,rep);assert chosen['request']==old['request'];recovery.append(chosen)
  effective.append(chosen);m=chosen['manifest']
  selection.append({'event_id':eid,'baseline':b,'repetition':rep,'selected_manifest':binding(chosen['directory']/'completed.json'),'selection_reason':'separately_authorized_pure_transport_recovery' if chosen is not old else 'original_retained_no_quality_selection'})
  if b=='B3':
   rpath=RUNS/m['run_id']/eid/'B4'/f'rep-{rep}'/'replay.json';r=load(rpath)
   assert r['B3_input_sha256']==m.get('output_sha256') and r['llm_calls']==0 and r['repetition']==rep
   if r['status']=='REPLAYED':
    for binding_ in r['verifier_implementation']:assert file_hash(ROOT/binding_['path'])==binding_['sha256']
   b4.append({'event_id':eid,'repetition':rep,'run_id':m['run_id'],'status':r['status'],'B3_raw_input_sha256':r['B3_input_sha256'],'stored_output_present':m.get('output_sha256') is not None,'exact_input_identity':True if m.get('output_sha256') is not None else None,'llm_calls':0,'dispositions':dict(collections.Counter(d['disposition'] for d in r['dispositions'])),'reasons':dict(collections.Counter(d.get('reason') for d in r['dispositions'])),'artifact':binding(rpath)})
 diagnostics=[output_checks(r) for r in effective];totals=collections.Counter();reasons=collections.Counter();dispositions=collections.Counter()
 for d in diagnostics:totals.update(d.get('counts',{}));reasons.update(d.get('reasons',{}))
 for d in b4:dispositions.update(d['dispositions'])
 return {'version':'investigation-development-r4-final-conformance','created_at':utc(),'scope':'DEVELOPMENT ONLY; NOT final evaluation; no research performance metrics','protocol_frozen':False,'original':summarize(original),'authorized_recovery':summarize(recovery),'all_retained_delivery_cells':summarize(original+recovery),'effective_144_slots':summarize(effective),'effective_baseline_usage':{b:summarize([r for r in effective if r['manifest']['baseline']==b]) for b in ['B1','B2','B3']},'all_three_repetitions_retained':len(effective)==144 and len(selection)==len({(x['event_id'],x['baseline'],x['repetition']) for x in selection}),'effective_selection':selection,'B4':{'effective_replays':len(b4),'statuses':dict(collections.Counter(r['status'] for r in b4)),'dispositions':dict(dispositions),'stored_B3_output_count':sum(r['stored_output_present'] for r in b4),'exact_stored_input_identity_checks_passed':sum(r['exact_input_identity'] is True for r in b4),'identical_stored_B3_input_all':all(r['exact_input_identity'] for r in b4 if r['stored_output_present']),'model_calls':0,'records':b4},'finite_conformance_counts':dict(totals),'not_supported_or_not_checkable_reasons':dict(reasons),'per_output_conformance':diagnostics,'metric_boundary':'Finite support checks are conformance diagnostics, not a human oracle. No Gold Fact Recall, Supported Claim Precision, Unsupported Claim Rate, sufficiency score, citation correctness score, or verifier accuracy is inferred here. Q6/free-text NOT_CHECKABLE is distinct from a proven factual error.','evaluation_evidence_accesses':0,'evaluation_gold_or_results_inspected':False,'human_gold_modified':False,'single_reviewer_methodology':'R1; custodian Author/R1; no independent second custodian','implementation_defects':[{'defect':'Concurrency and short backoff inadequate for observed 30000 TPM account limit','remedy':'Single-flight minimum 60-second start spacing; separate author-approved 86-cell transport recovery; all initial failures retained','research_prompts_matching_ontology_metrics_changed':False},{'defect':'Operator-stop reconciliation needed for two response-less attempt folders','remedy':'Unknown delivery recorded without fabricated status/usage; consumed original attempt slots before transport continuation','affected_attempts':2},{'defect':'ConnectionResetError recorded as a terminal runner failure by the existing catch-all handler','remedy':'Retained exactly as logged; no automatic rerun, no in-run code or retry-policy change; report as a transport-handling limitation, not a model error'}],'remaining_freeze_decisions':['Accept final conformance findings and model limitations','If actual max_output_tokens truncation exists, approve or reject a proposed 8192 candidate and any further development-only validation; current requests remain 4096','Verify external custody filesystem/account ACL and custodian access logging; application guard alone is not OS isolation','Explicitly approve exact final protocol inventory and formal freeze; 32-event evaluation requires separate authorization']}

if __name__=='__main__':
 result=build();path=OUT/'final_conformance_report.json';create_json(path,result)
 print(json.dumps({k:result[k] for k in ['protocol_frozen','all_three_repetitions_retained','evaluation_evidence_accesses']},indent=2));print('Report:',path)
