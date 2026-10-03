"""Pure evaluator arithmetic over R1-reviewed, byte-bound inputs.

No path loader, generator, retrieval, truth lookup, or semantic verifier mutation.
Human judgments are mandatory for prose, scope, security relevance and equivalence.
"""
import json
from .contracts import *
from .support import bundle_records,retrieval_supported

class IncompleteReview(ValueError): pass

def need(ok,message):
 if not ok: raise IncompleteReview(message)

def index(rows,key):
 result={r[key]:r for r in rows}
 need(len(result)==len(rows),'Duplicate '+key)
 return result

def ratio(n,d):
 need(type(n) is int and type(d) is int and 0<=n<=d,'Invalid ratio counts')
 return {'numerator':n,'denominator':d,'value':n/d if d else None}

def surfaces(value,path=''):
 """All string leaves, including narrative/reasons outside typed claims."""
 result={}
 if isinstance(value,dict):
  for k,v in value.items(): result.update(surfaces(v,path+'/'+k.replace('~','~0').replace('/','~1')))
 elif isinstance(value,list):
  for i,v in enumerate(value): result.update(surfaces(v,path+'/'+str(i)))
 elif isinstance(value,str): result[path or '/']=value
 return result

def decode(raw):
 try:
  obj=json.loads(raw)
  return obj if isinstance(obj,dict) else {'unparsed_text':raw.decode('utf-8',errors='replace')}
 except (ValueError,UnicodeDecodeError):return {'unparsed_text':raw.decode('utf-8',errors='replace')}

def claim_list(obj):
 rows=obj.get('claims',[])
 return [c for c in rows if isinstance(c,dict) and isinstance(c.get('claim_id'),str)] if isinstance(rows,list) else []

VALID_DELIVERIES={'DELIVERED','DELIVERED_SCHEMA_INVALID','DELIVERED_SCHEMA_OR_VISIBILITY_INVALID','DETERMINISTIC_REFERENCE'}
INVALID_DELIVERIES={'PROVIDER_INCOMPLETE','PROVIDER_REFUSAL','FAILED_NO_VALID_DELIVERY','TERMINAL_HTTP_FAILURE'}

def delivery_valid(receipt,event,cell,repetition):
 need((receipt['event_id'],receipt['cell_id'],receipt['repetition'])==(event,cell,repetition),'Delivery receipt context mismatch')
 status=receipt['status']
 need(status in VALID_DELIVERIES|INVALID_DELIVERIES,'Unknown/configuration failure needs author review, not automatic scoring')
 if status=='PROVIDER_INCOMPLETE':need(bool(receipt['termination_reason']),'Incomplete reason missing')
 return status in VALID_DELIVERIES

def bound_source(ledger,raw,stage,bundle):
 need(sha(raw)==ledger['raw_output_sha256'],'Raw response binding mismatch')
 need(sha(stage)==ledger['stage_artifact_sha256'],'Stage artifact binding mismatch')
 need(digest(bundle)==ledger['bundle_sha256'],'Bundle binding mismatch')
 need(bundle['event_id']==ledger['event_id'] and bundle['view']==VIEWS[ledger['cell_id']],'Bundle context')
 raw_obj=decode(raw);stage_obj=decode(stage)
 if ledger['cell_id']=='V1-EN':
  need(ledger['output_stage']=='VERIFIED_PUBLISHED','Wrong replay stage')
  need(stage_obj.get('source_output_sha256',stage_obj.get('B3_input_sha256'))==sha(raw),'Replay source identity')
  need(stage_obj.get('llm_calls')==0,'Replay must make zero model calls')
  need(stage_obj.get('event_id')==ledger['event_id'] and stage_obj.get('repetition')==ledger['repetition'],'Replay context')
  # Real replay records bind the exact retrieved bundle digest, passed as a receipt field.
  need(stage_obj.get('bundle_sha256')==bundle['source_bundle_sha256'],'Replay bundle identity')
  need('published_report' in stage_obj,'Missing publication: never fabricate V1 content')
  if stage_obj['published_report'] is None:
   need(ledger['delivery']=='INVALID_PROVIDER_DELIVERY','Unavailable replay cannot be valid')
  report=stage_obj['published_report'] or {}
  source={'published_report':report,'dispositions':stage_obj.get('dispositions',[]),
          'question_actions':stage_obj.get('question_actions',[])}
  claim_ids={c['claim_id'] for c in claim_list(raw_obj)}
  for c in claim_list(report):need(c['claim_id'] in claim_ids,'Invented published claim ID')
 else:
  need(stage==raw,'Raw/reference stage must preserve exact bytes')
  need(ledger['output_stage']==('DETERMINISTIC_REFERENCE' if ledger['cell_id']=='D0' else 'RAW_GENERATED'),'Wrong output stage')
  source=raw_obj
 if 'event_id' in raw_obj:need(raw_obj['event_id']==ledger['event_id'],'Output event mismatch')
 return source,raw_obj

def validate_gold(gold,policy_sha256):
 validate('gold',gold)
 need(gold['policy_sha256']==policy_sha256,'Gold matching policy drift')
 need(gold['commitment_sha256']==digest({k:v for k,v in gold.items() if k!='commitment_sha256'}),'Gold self-commitment mismatch')
 facts=index(gold['positive_facts'],'gold_id');index(gold['positive_facts'],'fact_key')
 aliases=index(gold['aliases'],'alias_id')
 need(not(set(facts)&set(aliases)),'Alias collides with canonical fact')
 evidence=index(gold['source_evidence_hashes'],'evidence_id')
 for a in aliases.values():need(a['canonical_gold_id'] in facts,'Alias must point directly to reviewed canonical gold')
 for f in facts.values():
  for v,s in f['views'].items():
   need(s['supportable']==bool(s['acceptable_support_sets']),'Supportability requires complete-view support sets')
   for support in s['acceptable_support_sets']:
    need(set(support)<=set(evidence),'Unknown gold support reference')
    need(all(v in evidence[i]['views'] for i in support),'Support set outside complete view')
  need(f['views']['EN']['supportable'],'Full EN gold fact not supportable')
 opportunities=index(gold['opportunities'],'opportunity_id')
 for o in opportunities.values():need(o['event_id']==gold['event_id'],'Opportunity event mismatch')
 return facts,aliases,opportunities,evidence

def span_check(span,strings):
 need(span['pointer'] in strings,'Text source missing')
 s=strings[span['pointer']]
 need(0<=span['start']<span['end']<=len(s) and s[span['start']:span['end']]==span['text'],'Text span mismatch')

def roots(rows,kind):
 ids=index(rows,kind+'_id');result=[]
 ignore={kind+'_id','source','original_claim_ids','raw_claim_type','reviewer_notes','duplicate_of','duplicate_rationale'}
 for row in rows:
  target=row['duplicate_of']
  if target is None:result.append(row);continue
  need(target in ids and ids[target]['duplicate_of'] is None,'Alias needs direct root')
  need(bool(row['duplicate_rationale']),'Human equivalence rationale required')
  need({k:v for k,v in row.items() if k not in ignore}=={k:v for k,v in ids[target].items() if k not in ignore},'Conflicting assertions/actions cannot collapse')
 return result

def score(ledger,gold,bundle,raw,stage,*,matching_policy_sha256):
 validate('review_ledger',ledger)
 facts,aliases,opportunities,evidence=validate_gold(gold,matching_policy_sha256)
 need(ledger['event_id']==gold['event_id'] and ledger['gold_sha256']==digest(gold),'Gold commitment binding mismatch')
 c=ledger['cell_id'];v=VIEWS[c]
 need(ledger['repetition'] in ((0,) if c=='D0' else (1,2,3)),'D0 executes once; other cells require three repetitions')
 source,raw_obj=bound_source(ledger,raw,stage,bundle)
 strings=surfaces(source);reviewed=index(ledger['reviewed_surfaces'],'pointer')
 need(set(reviewed)==set(strings),'Every actual text surface requires R1 inspection')
 aid=index(ledger['assertions'],'assertion_id')
 original_ids={x['claim_id'] for x in claim_list(raw_obj)}
 for p,s in strings.items():
  row=reviewed[p]
  need(row['text']==s,'Reviewed text differs from actual output')
  need(set(row['assertion_ids'])<=set(aid),'Unreviewed atomic assertion')
  need(bool(row['assertion_ids']) or bool(row['nonassertive_reason']),'Text omitted from assertion review')
  need(set(row['assertion_ids'])=={a['assertion_id'] for a in aid.values() if a['source']['pointer']==p},'Surface/assertion mapping mismatch')
 for a in aid.values():
  span_check(a['source'],strings)
  if c=='V1-EN':
   need(a['source']['pointer'].startswith('/published_report/'),'V1 substantive scoring cannot include rejected/raw disposition text')
  need(set(a['original_claim_ids'])<=original_ids,'Original claim identity lost')
  need(a['matching_policy_sha256']==matching_policy_sha256,'Assertion matching policy changed')
  if a['original_claim_ids']:
   report=source.get('published_report',source)
   published_claims={x['claim_id']:x for x in claim_list(report)}
   need(set(a['original_claim_ids'])<=set(published_claims),'Raw or blocked claim cannot count as published')
   generated_citations={i for cid in a['original_claim_ids'] for i in published_claims[cid].get('evidence_ids',[])}
   need({x['evidence_id'] for x in a['citations']}==generated_citations,'Cannot add/drop generated citations in review')
 visible=set(bundle['visible_evidence_ids'])
 need(len(visible)==len(bundle['visible_evidence_ids']),'Duplicate visible evidence IDs')
 need(visible<=set(evidence),'Visible evidence not in committed event inventory')
 need(all(v in evidence[i]['views'] for i in visible),'Evidence leaks across view boundary')
 records=bundle_records(bundle,visible)
 G=set(facts);Gv={g for g,f in facts.items() if f['views'][v]['supportable']}
 retrieved={g for g in Gv if retrieval_supported(facts[g],v,visible,records)}
 canonical=lambda i:aliases[i]['canonical_gold_id'] if i in aliases else i
 assertions=roots(ledger['assertions'],'assertion');recovered=set();pairs=[]
 for a in assertions:
  need(not(a['supported'] and any(a['overclaims'].values())),'Supported assertion has unsupported stronger interpretation')
  if any(a['overclaims'].values()):need(a['security_sensitive'] and a['substantive'],'Overclaim must enter security denominator')
  cs=index(a['citations'],'evidence_id')
  for citation in cs.values():
   need(citation['visible']==(citation['evidence_id'] in visible),'Citation visibility cannot be repaired by evaluator')
   # Evidence inventory is the committed complete event inventory; no dataset fallback.
   need(citation['exists']==(citation['evidence_id'] in evidence),'Citation existence disagrees with committed event inventory')
   pairs.append(citation['exists'] and citation['visible'] and citation['role_supported'])
  supports=a['required_support_sets']
  if a['supported'] and a['substantive']:
   need(any(set(s)<=visible for s in supports),'Supported substantive claim lacks complete visible support')
  fully_cited=bool(cs) and all(x['exists'] and x['visible'] and x['role_supported'] for x in cs.values()) and any(set(s)<=set(cs) for s in supports)
  need(a['cited_complete_support']==(a['substantive'] and a['supported'] and fully_cited),'Complete-support judgment/cited-set mismatch')
  matches={canonical(i) for i in a['matched_gold_ids']}
  need(len(matches)<=1 and matches<=G,'One atomic assertion recovers at most one positive fact')
  if matches:
   need(a['substantive'] and a['supported'] and matches<=retrieved,'Recovered fact requires visible complete support')
   recovered.update(matches)
  for k in ('numerical','asset','temporal'):
   if a[k] is not None:need(a['substantive'],'Non-substantive statement in consistency denominator')
 qs=index(ledger['questions'],'question_id');need(set(qs)=={f'Q{i}' for i in range(1,8)},'Exactly Q1-Q7')
 covered=0
 for q in qs.values():
  ids=q['adequate_assertion_ids'];need(set(ids)<=set(aid),'Unknown coverage assertion')
  need(q['adequate']==bool(ids),'Coverage requires concrete supported answer')
  for i in ids:
   a=aid[i];need(a['substantive'] and a['supported'],'Disclaimers/unsupported claims cannot provide coverage')
   if q['question_id']=='Q6':need(a['q6_relevance'] is True,'Q6 requires explicit human security-relevance judgment')
  if q['question_id']!='Q7':covered+=q['adequate']
 actions=roots(ledger['actions'],'action')
 for a in ledger['actions']:
  span_check(a['source'],strings)
  need(set(a['original_claim_ids'])<=original_ids,'Action original claim identity lost')
 for a in actions:
  if a['opportunity_id'] is not None:
   need(a['opportunity_id'] in opportunities,'Unknown withholding opportunity')
   need(opportunities[a['opportunity_id']]['required_actions'][v]!='not_applicable','Action assigned to inapplicable opportunity')
   if a['action_correct']:
    need(a['action']==opportunities[a['opportunity_id']]['required_actions'][v],'Incorrect action credited')
 required={i for i,o in opportunities.items() if o['required_actions'][v] in ('qualify','withhold')}
 correct=lambda a:a['action_correct'] and a['scope_correct'] and a['reason_correct']
 satisfied={a['opportunity_id'] for a in actions if correct(a) and a['opportunity_id'] in required}
 substantive=[a for a in assertions if a['substantive']]
 sec=[a for a in substantive if a['security_sensitive']]
 metrics={'evidence_completeness':ratio(len(recovered),len(G)),
 'view_conditional_completeness':ratio(len(recovered&Gv),len(Gv)),
 'retrieval_recall':ratio(len(retrieved),len(Gv)),
 'citation_precision':ratio(sum(pairs),len(pairs)),
 'complete_support_rate':ratio(sum(a['cited_complete_support'] for a in substantive),len(substantive)),
 'unsupported_security_claim_rate':ratio(sum(not a['supported'] for a in sec),len(sec)),
 'q1_q6_substantive_coverage':ratio(covered,6),
 'required_withholding_recall':ratio(len(satisfied),len(required)),
 'withholding_precision':ratio(sum(correct(a) for a in actions),len(actions)),
 'schema_compliance':ratio(int(ledger['schema_compliant']),1)}
 for k in ('numerical','asset','temporal'):
  judgments=[a[k] for a in substantive if a[k] is not None]
  metrics[k+'_consistency']=ratio(sum(all(x.values()) for x in judgments),len(judgments))
 valid=delivery_valid(ledger['delivery_receipt'],ledger['event_id'],c,ledger['repetition'])
 need(valid==(ledger['delivery']=='VALID'),'Cannot exclude valid output based on quality/schema/citations')
 if not valid:
  # Delivery policy excludes the whole position. Never fabricate valid content or
  # let preserved partial response become a successful research repetition.
  metrics={m:ratio(0,0) for m in METRICS}
  recovered=set()
 result={'event_id':ledger['event_id'],'cell_id':c,'repetition':ledger['repetition'],
  'output_stage':ledger['output_stage'],'delivery':ledger['delivery'],'metrics':metrics,
  'raw_output_sha256':sha(raw),'bundle_sha256':digest(bundle),'source_bundle_sha256':bundle['source_bundle_sha256'],
  'gold_sha256':digest(gold),'review_ledger_sha256':digest(ledger),
  'recovered_gold_ids':sorted(recovered),
  'funnel':{'full_gold_count':len(G),'supportable_in_view_count':len(Gv),
   'complete_support_retrieved_count':len(retrieved),'correctly_reconstructed_count':len(recovered) if valid else None},
  'counts':{'security_sensitive_assertions':metrics['unsupported_security_claim_rate']['denominator'],
   'citation_pairs':metrics['citation_precision']['denominator'],
   'numerical_assertions':metrics['numerical_consistency']['denominator'],
   'asset_assertions':metrics['asset_consistency']['denominator'],
   'temporal_assertions':metrics['temporal_consistency']['denominator'],
   'required_withholding_opportunities':metrics['required_withholding_recall']['denominator'],
   'explicit_qualify_withhold_actions':metrics['withholding_precision']['denominator']},
  'fixed_opportunity_counts_before_delivery_exclusion':{'gold':len(G),'coverage':6,'withholding':len(required)},
  'alias_accounting':{'gold_aliases':len(aliases),'assertion_duplicates':len(aid)-len(assertions),
   'action_duplicates':len(ledger['actions'])-len(actions)},
  'view_ceiling':ratio(len(Gv),len(G)),'methodology':'single-reviewer gold'}
 return result


def score_delivery_failure(event,cell,repetition,gold,bundle,receipt,*,matching_policy_sha256):
 """No invented output or human assertions when provider delivery is invalid.

 A future scoring loader must authenticate receipt bytes against the frozen run
 manifest. Configuration failures remain blockers; they are never scored away.
 """
 need(not delivery_valid(receipt,event,cell,repetition),'Delivered output requires actual-text human review')
 facts,aliases,opportunities,evidence=validate_gold(gold,matching_policy_sha256)
 need(event==gold['event_id']==bundle['event_id'] and bundle['view']==VIEWS[cell],'Failure context')
 need(repetition in (1,2,3),'Failure repetition')
 v=VIEWS[cell];visible=set(bundle['visible_evidence_ids']);records=bundle_records(bundle,visible)
 gv={g for g,f in facts.items() if f['views'][v]['supportable']}
 retrieved={g for g in gv if retrieval_supported(facts[g],v,visible,records)}
 return {'event_id':event,'cell_id':cell,'repetition':repetition,'output_stage':'VERIFIED_PUBLISHED' if cell=='V1-EN' else 'RAW_GENERATED',
 'delivery':'INVALID_PROVIDER_DELIVERY','metrics':{m:ratio(0,0) for m in METRICS},
 'raw_output_sha256':None,'bundle_sha256':digest(bundle),'source_bundle_sha256':bundle['source_bundle_sha256'],
 'gold_sha256':digest(gold),'review_ledger_sha256':None,'delivery_receipt':receipt,'recovered_gold_ids':[],
 'funnel':{'full_gold_count':len(facts),'supportable_in_view_count':len(gv),'complete_support_retrieved_count':len(retrieved),'correctly_reconstructed_count':None},
 'counts':{k:0 for k in COUNT_FIELDS[:7]},'fixed_opportunity_counts_before_delivery_exclusion':{'gold':len(facts),'coverage':6,
 'withholding':sum(o['required_actions'][v] in ('qualify','withhold') for o in opportunities.values())},
 'alias_accounting':{'gold_aliases':len(aliases),'assertion_duplicates':0,'action_duplicates':0},
 'view_ceiling':ratio(len(gv),len(facts)),'methodology':'single-reviewer gold'}
