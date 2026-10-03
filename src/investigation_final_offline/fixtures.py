"""Fabricated examples only, never import development or evaluation results."""
from copy import deepcopy
from .contracts import *
from .scoring import surfaces

POLICY_HASH='a'*64
REVIEW_RECORD={'reviewer_id':'R1','reviewed_at':'2026-09-28T00:00:00Z','review_status':'HUMAN_REVIEWED',
 'notes':'SYNTHETIC FIXTURE: simulated review fields, NOT actual human annotation'}

def fixture(event='SYNTHETIC_A1',cell='G1-EN',rep=1):
 view=VIEWS[cell];i=int(event[-1]);vset={'E':['e1','e2','m1'],'N':['n1'],'EN':['e1','e2','n1','m1']}
 visible=vset[view].copy()
 if i==2 and view=='EN':visible.remove('e2')
 gold={'version':VERSION,'event_id':event,'annotation_version':'SYNTHETIC_v1','policy_sha256':POLICY_HASH,
 'committed_before_output_review':True,'commitment_sha256':'b'*64,'review':deepcopy(REVIEW_RECORD),
 'source_evidence_hashes':[{'evidence_id':e,'sha256':sha(e.encode()),'views':vs} for e,vs in
 [('e1',['E','EN']),('e2',['E','EN']),('n1',['N','EN']),('m1',['E','EN'])]],'positive_facts':[],
 'aliases':[],'opportunities':[],'temporal_relationships':['SYNTHETIC order only'],
 'asset_relationships':['SYNTHETIC approved mapping'], 'security_relevance_judgments':['SYNTHETIC warrants further investigation'],
 'unsupported_conclusions':['SYNTHETIC causation unsupported'],'unresolved_conclusions':['SYNTHETIC actor unknown']}
 for g,ss,views in [('gE',['e1','m1'],['E','EN']),('gN',['n1'],['N','EN']),('gEN',['e2','n1','m1'],['EN'])]:
  gold['positive_facts'].append({'gold_id':g,'fact_key':g,'raw_claim_type':'SYNTHETIC_observation',
   'canonical_representation':'SYNTHETIC_'+g,'statement':'SYNTHETIC '+g,'fields':{'test':True},
   'views':{v:{'supportable':v in views,'acceptable_support_sets':[ss] if v in views else [],'rationale':'SYNTHETIC predeclared complete view'} for v in ('E','N','EN')},
   'question_ids':['Q1' if g=='gN' else 'Q2'],'allowed_interpretation':'SYNTHETIC observation only','prohibited_interpretations':['causation']})
 gold['opportunities']=[{'event_id':event,'opportunity_id':'h1','semantic_scope':'SYNTHETIC causation','conclusion_category':'causation',
 'evidence_requirement':'SYNTHETIC temporal order does not establish cause','required_actions':dict.fromkeys(('E','N','EN'),'withhold'),
 'reason':'Causal support absent','question_ids':['Q5','Q7']}]
 gold['commitment_sha256']=digest({k:v for k,v in gold.items() if k!='commitment_sha256'})
 bundle={'event_id':event,'view':view,'visible_evidence_ids':visible,'source_bundle_sha256':sha(('SYNTHETIC bundle '+event+view).encode())}
 gs=[f for f in gold['positive_facts'] if f['views'][view]['supportable'] and all(e in visible for e in f['views'][view]['acceptable_support_sets'][0])]
 if rep==2 and cell not in ('D0',):gs=gs[:1]
 claims=[{'claim_id':f['gold_id'],'claim_type':'SYNTHETIC_observation','claim_text':'SYNTHETIC observed '+f['gold_id'],
 'evidence_ids':[] if cell=='G0' else f['views'][view]['acceptable_support_sets'][0]} for f in gs]
 # Innocuous model type deliberately carries a causal overclaim.
 if cell in ('G1-EN','V1-EN','G0','G1-N') and i==1:
  claims.append({'claim_id':'bad','claim_type':'SYNTHETIC_observation','claim_text':'SYNTHETIC command caused physical change','evidence_ids':['n1']})
 raw_obj={'event_id':event,'claims':claims,'questions':[{'question_id':'Q7','response':'SYNTHETIC insufficient: causal support absent'}]}
 raw=dumps(raw_obj).encode();stage=raw
 if cell=='V1-EN':
  published={**raw_obj,'claims':[c for c in claims if c['claim_id']!='bad']}
  replay={'event_id':event,'repetition':rep,'source_output_sha256':sha(raw),'bundle_sha256':bundle['source_bundle_sha256'],
  'llm_calls':0,'published_report':published,'dispositions':[{'claim_id':'bad','disposition':'INSUFFICIENT',
  'reason':'SYNTHETIC insufficient: causal support absent','published_claim':None}] if any(c['claim_id']=='bad' for c in claims) else [],'question_actions':[]}
  stage=dumps(replay).encode();source={k:replay[k] for k in ('published_report','dispositions','question_actions')};claimpath='/published_report/claims/'
  working=published['claims']
 else:source=raw_obj;claimpath='/claims/';working=claims
 ledger={'version':VERSION,'event_id':event,'cell_id':cell,'repetition':0 if cell=='D0' else rep,
 'output_stage':'VERIFIED_PUBLISHED' if cell=='V1-EN' else ('DETERMINISTIC_REFERENCE' if cell=='D0' else 'RAW_GENERATED'),
 'raw_output_sha256':sha(raw),'stage_artifact_sha256':sha(stage),'bundle_sha256':digest(bundle),'gold_sha256':digest(gold),
 'delivery_receipt':{'event_id':event,'cell_id':cell,'repetition':0 if cell=='D0' else rep,'status':'DETERMINISTIC_REFERENCE' if cell=='D0' else 'DELIVERED','termination_reason':None,'source_record_sha256':'d'*64},
 'delivery':'VALID','delivery_reason':'SYNTHETIC complete fixture','schema_compliant':True,'review':deepcopy(REVIEW_RECORD),
 'all_text_reviewed':True,'reviewed_surfaces':[],'assertions':[],'questions':[],'actions':[]}
 for j,c in enumerate(working):
  bad=c['claim_id']=='bad';f=next((f for f in gs if f['gold_id']==c['claim_id']),None)
  support=[] if bad else f['views'][view]['acceptable_support_sets']
  ledger['assertions'].append({'assertion_id':'a'+str(j),'source':{'pointer':claimpath+str(j)+'/claim_text','start':0,'end':len(c['claim_text']),'text':c['claim_text']},
   'original_claim_ids':[c['claim_id']],'raw_claim_type':c['claim_type'],'substantive':True,'supported':not bad,
   'security_sensitive':bad,'overclaims':{k:(bad and k=='causal') for k in ('causal','malicious_intent','command_execution','successful_compromise','attribution')},
   'q6_relevance':not bad,'matched_gold_ids':[] if bad else [c['claim_id']],'matching_policy_sha256':POLICY_HASH,
   'matching_reason':'SYNTHETIC literal match','required_support_sets':support,
   'citations':[{'evidence_id':e,'assigned_role':'SYNTHETIC observation','exists':True,'visible':True,'role_supported':not bad,'reason':'SYNTHETIC reviewed role'} for e in c['evidence_ids']],
   'cited_complete_support':not bad and bool(c['evidence_ids']),
   'numerical':{k:True for k in ('cited_values','transformation','unit','channel_asset_scope','approved_tolerance')} if c['claim_id']=='gE' else None,
   'asset':{'observation_identity':True,'approved_mapping':True,'scope':True} if c['claim_id']=='gE' else None,
   'temporal':None,'duplicate_of':None,'duplicate_rationale':'','reviewer_notes':'SYNTHETIC assertion'})
 for q in range(1,8):
  aa=[a['assertion_id'] for a in ledger['assertions'] if a['supported']][:1] if q<=2 else []
  ledger['questions'].append({'question_id':f'Q{q}','adequate_assertion_ids':aa,'adequate':bool(aa),'reason':'SYNTHETIC coverage'})
 ptr=('/published_report' if cell=='V1-EN' else '')+'/questions/0/response';text=surfaces(source)[ptr]
 ledger['actions']=[{'action_id':'w1','source':{'pointer':ptr,'start':0,'end':len(text),'text':text},'original_claim_ids':[],
  'action':'withhold','opportunity_id':'h1','action_correct':True,'scope_correct':True,'reason_correct':True,
  'duplicate_of':None,'duplicate_rationale':'','reviewer_notes':'SYNTHETIC explicit decision'}]
 for ptr,text in surfaces(source).items():
  ids=[a['assertion_id'] for a in ledger['assertions'] if a['source']['pointer']==ptr]
  ledger['reviewed_surfaces'].append({'pointer':ptr,'text':text,'assertion_ids':ids,'nonassertive_reason':'' if ids else 'SYNTHETIC metadata or explicit uncertainty'})
 return ledger,gold,bundle,raw,stage

def fixture_matrix():
 from .scoring import score
 rows=[];inputs=[];strata={}
 for event in ('SYNTHETIC_A1','SYNTHETIC_A2','SYNTHETIC_B1','SYNTHETIC_B2'):
  strata[event]='SYNTHETIC_STRATUM_'+event[-2]
  for c in (*CELLS,'D0'):
   for r in ((1,) if c=='D0' else (1,2,3)):
    l,g,b,raw,stage=fixture(event,c,r)
    rows.append(score(l,g,b,raw,stage,matching_policy_sha256=POLICY_HASH))
    inputs.append({'ledger':l,'gold':g,'bundle':b,'raw_utf8':raw.decode(),'stage_utf8':stage.decode()})
 return rows,strata,inputs


def committed_fixture_packet():
 rows,strata,inputs=fixture_matrix();positions=[];items=[]
 for x in inputs:
  l=x['ledger'];key={k:l[k] for k in ('event_id','cell_id','repetition')}
  item={**key,**x,'delivery_receipt':l['delivery_receipt'],'kind':'REVIEWED_OUTPUT'}
  items.append(item);positions.append({**key,'input_sha256':digest(item),'gold_sha256':digest(x['gold']),
   'bundle_sha256':digest(x['bundle']),'delivery_receipt_sha256':digest(l['delivery_receipt']),
   'delivery_source_record_sha256':l['delivery_receipt']['source_record_sha256'],
   'review_ledger_sha256':digest(l),'raw_output_sha256':l['raw_output_sha256'],'stage_output_sha256':l['stage_artifact_sha256']})
 manifest={'data_label':'SYNTHETIC_TEST_ONLY_NOT_PAPER_RESULTS','event_ids':sorted(strata),'scenario_strata':strata,
  'positions':positions,'matching_policy_sha256':POLICY_HASH,'protocol_frozen':False,
  'separate_scoring_authorization_sha256':None,'gold_committed_before_output_review':True,'custody_receipt_sha256':None}
 return {'manifest':manifest,'inputs':items}
