"""Offline candidate tests. Synthetic outputs only; no research generation."""
import copy,hashlib,json,socket,sys,tempfile,unittest,urllib.error
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
from investigation_r5.core import *
from investigation_r5.runner import build_request,generate,replay_bytes,validate_delivery
from investigation_r5.gold_contract import pilot_contract
from investigation_r5.metrics import score_reviewed_run,PendingReview,ratio
from investigation_r5.statistics import aggregate,BASELINES,CONTRASTS
from investigation_r5.transport import FixtureTransport,exercise,retry_exception,next_delay
from investigation_r5.acceptance import assess
from investigation_dryrun.common import dumps,digest,file_hash
from test_investigation_development import bundle_fixture,ledger_fixture
from investigation_dryrun.claims import numeric_claim
EID=development_ids()[0]

def output(view='EN',mode='required',claims=None):
 return {'schema_version':'investigation-claim-v3','event_id':EID,'evidence_view':view,'citation_mode':mode,'claims':claims or [],'questions':[{'question_id':f'Q{i}','claim_ids':[],'response':'insufficient'} for i in range(1,8)]}

def envelope(exp=None,status='completed',reason=None,refusal=False):
 parts=[{'type':'refusal','refusal':'fixture'}] if refusal else [{'type':'output_text','text':dumps(exp or output())}]
 return 200,{},json.dumps({'id':'synthetic_response','model':'gpt-4.1-2025-04-14','status':status,'incomplete_details':{'reason':reason} if reason else None,'usage':{'input_tokens':1,'output_tokens':1},'output':[{'type':'message','content':parts}]}).encode()

def reviewed(cell='G1-EN'):
 l=ledger_fixture();l.update(cell_id=cell,bundle_sha256='bundle',schema_compliant=True)
 for g in l['gold']:g['retrieved_support']=g['view_eligible']
 for a in l['assertions']:
  a['citations']=[{'evidence_id':c['evidence_id'],'exists_in_event':True,'visible_in_bundle':True,'supports_claim_role':True} for c in a['citations']]
  a['consistency']={'numerical_accuracy':True,'asset_consistency':None,'temporal_consistency':None}
 l['opportunities']=[{'opportunity_id':f'question:Q{i}','expected_action':'ASSERT','actual_action':'ASSERT','scope_and_reason_correct':True,'full_view_answerability':'supported'} for i in range(1,8)]+[{'opportunity_id':'guardrail:H1','expected_action':'WITHHOLD','actual_action':'WITHHOLD','scope_and_reason_correct':True}]
 l['withholding_decisions']=[{'decision_id':'w1','action':'WITHHOLD','needed':True,'scope_and_reason_correct':True,'opportunity_id':'guardrail:H1','proposition_fingerprint':'h1'}]
 g={'event_id':EID,'view':cell_spec(cell)['view'],'gold':copy.deepcopy(l['gold']),'bundle_sha256':'bundle','question_answerability':{f'Q{i}':'supported' for i in range(1,8)}}
 return l,g

class ViewsAndRequestTests(unittest.TestCase):
 def test_all_development_bundles_audited(self):
  rows=load(OUT/'input_audit.json')['rows'];self.assertEqual(len(rows),48)
  for row in rows:
   b,r=read_bundle(row['event_id'],row['view']);self.assertEqual(validate_input(b,r)['status'],'PASS')
 def test_E_blocks_hidden_N(self):
  e,r=bundle_fixture('E');n,_=bundle_fixture('N');e['entries'].append(n['entries'][0]);r['retrieved_bundle_sha256']=digest(e)
  with self.assertRaises(ValueError):validate_input(e,r)
 def test_N_blocks_hidden_E(self):
  n,r=bundle_fixture('N');e,_=bundle_fixture('E');n['entries'].append(e['entries'][0]);r['retrieved_bundle_sha256']=digest(n)
  with self.assertRaises(ValueError):validate_input(n,r)
 def test_unnecessary_metadata_blocked(self):
  e,r=bundle_fixture('E');e['control_metadata']={'meta_x':{}}
  with self.assertRaises(ValueError):validate_input(e,r)
 def test_common_prompt_required_semantics(self):
  template=(ROOT/'prompts/investigation-v1-r5/required.template.txt').read_text()
  for cell in ('G1-E','G1-N','G1-EN'):self.assertEqual(prompt_for(cell)[0],template.replace('{VIEW}',cell_spec(cell)['view']))
  self.assertEqual(prompt_for('G1-EN')[0],(ROOT/'prompts/investigation-v1-r4/B3.v1.txt').read_text())
  self.assertEqual(prompt_for('G0')[0],(ROOT/'prompts/investigation-v1-r4/B2.v1.txt').read_text())
 def test_cell_view_citation_separation(self):
  for cell in ('G0','G1-E','G1-N','G1-EN'):
   s=cell_spec(cell);b,r=read_bundle(EID,s['view']);q=build_request(EID,cell,b,r)
   self.assertEqual(q['text']['format']['schema']['properties']['citation_mode']['const'],s['citation_mode']);self.assertEqual(q['input'],dumps(b))
  b,r=read_bundle(EID,'N')
  with self.assertRaises(ValueError):build_request(EID,'G1-E',b,r)
 def test_8192_output_16384_input(self):
  b,r=read_bundle(EID,'EN');q=build_request(EID,'G0',b,r)
  self.assertEqual(q['max_output_tokens'],8192);self.assertEqual(load(CONFIG/'token_budget.candidate.json')['evidence_token_safety_ceiling'],16384)
  self.assertFalse(load(CONFIG/'model.candidate.json')['live_api_enabled'])
 def test_input_safety_boundary(self):
  b,r=read_bundle(EID,'E')
  with patch('investigation_r5.core.count',return_value=16384):validate_input(b,r)
  with patch('investigation_r5.core.count',return_value=16385):
   with self.assertRaises(ValueError):validate_input(b,r)
 def test_zero_network_generation(self):
  with patch('urllib.request.urlopen',side_effect=AssertionError('NETWORK FORBIDDEN')):
   with self.assertRaises(PermissionError):generate(EID,'G1-EN',1)
 def test_non_generation_cells_no_request(self):
  b,r=read_bundle(EID,'EN')
  for c in ('D0','V1-EN','B1'):
   with self.assertRaises(ValueError):build_request(EID,c,b,r)
 def test_reference_visibility_checks_payload(self):
  b,r=read_bundle(EID,'E');x=output('E');x['claims']=[{'evidence_ids':['p_'+'9'*24],'payload':{'record_id':'p_'+'9'*24}}]
  self.assertTrue(any('invisible_reference' in e for e in validate_delivery(x,EID,'G1-E',b)))
 def test_evaluation_denied_before_read(self):
  ev=load(ROOT/'configs/investigation_events.v1.json')['evaluation'][0]
  with self.assertRaises(PermissionError):read_bundle(ev,'E')

class ContractAndMetricTests(unittest.TestCase):
 def score(self,l,g):return score_reviewed_run(l,'fixture-hash',g)
 def test_existing_gold_E_contract(self):
  for e in load(ROOT/'annotations/gold/pilot-v1/manifest.json')['events']:
   cs=[pilot_contract(e['event_id'],v) for v in ('E','N','EN')]
   self.assertEqual(len({c['annotation_sha256'] for c in cs}),1)
   sets=[{g['canonical_gold_id'] for g in c['gold'] if g['kind']=='positive'} for c in cs];self.assertEqual(sets[0],sets[1]);self.assertEqual(sets[0],sets[2])
 def test_common_G_and_view_Gv(self):
  l,g=reviewed('G1-E');m=self.score(l,g)['metrics'];self.assertEqual(m['evidence_completeness'],ratio(1,2));self.assertEqual(m['view_conditional_completeness'],ratio(1,1));self.assertEqual(m['view_ceiling'],ratio(1,2))
 def test_zero_denominator_NA(self):self.assertEqual(ratio(0,0)['value'],None)
 def test_citation_precision_requires_role_not_existence(self):
  l,g=reviewed();l['assertions'][0]['cited_complete_support']=False
  for c in l['assertions'][0]['citations']:c['supports_claim_role']=False
  self.assertEqual(self.score(l,g)['metrics']['citation_precision'],ratio(0,1))
 def test_citation_visibility_missing_not_credit(self):
  l,g=reviewed();l['assertions'][0]['cited_complete_support']=False
  for c in l['assertions'][0]['citations']:c['visible_in_bundle']=False
  self.assertEqual(self.score(l,g)['metrics']['citation_precision']['value'],0)
 def test_citation_pending_blocks(self):
  l,g=reviewed();l['assertions'][0]['citations'][0]['supports_claim_role']=None
  with self.assertRaises(PendingReview):self.score(l,g)
 def test_historical_citation_valid_cannot_override_role(self):
  l,g=reviewed();l['assertions'][0]['citations'][0].update(valid=True,supports_claim_role=False)
  with self.assertRaises(ValueError):self.score(l,g)
 def test_duplicate_gold_not_extra_denominator(self):
  l,g=reviewed();self.assertEqual(self.score(l,g)['metrics']['evidence_completeness']['denominator'],2)
 def test_new_primary_metrics_not_added(self):
  l,g=reviewed();m=self.score(l,g)['metrics']
  for key in ('supported_claim_precision','verifier_disposition_accuracy','false_withhold_rate'):self.assertNotIn(key,m)
 def test_fixed_withholding_opportunities(self):
  l,g=reviewed();self.assertEqual(self.score(l,g)['metrics']['required_withholding_recall'],ratio(1,1));l['opportunities'].pop()
  with self.assertRaises(ValueError):self.score(l,g)
 def test_missing_is_not_correct_withholding(self):
  l,g=reviewed();l['opportunities'][-1].update(actual_action='MISSING',scope_and_reason_correct=False);l['withholding_decisions']=[]
  self.assertEqual(self.score(l,g)['metrics']['required_withholding_recall']['value'],0)
 def test_always_withhold_sanity(self):
  l,g=reviewed();l['assertions']=[];l['withholding_decisions']=[]
  for q in l['questions']:q['coverage_minimum_met']=False
  for i,s in enumerate(l['opportunities']):
   correct=s['expected_action']=='WITHHOLD';s.update(actual_action='WITHHOLD',scope_and_reason_correct=correct)
   l['withholding_decisions'].append({'decision_id':str(i),'action':'WITHHOLD','needed':correct,'scope_and_reason_correct':correct,'opportunity_id':s['opportunity_id'],'proposition_fingerprint':str(i)})
  m=self.score(l,g)['metrics'];self.assertEqual(m['q1_q6_substantive_coverage']['value'],0);self.assertIsNone(m['unsupported_security_claim_rate']['value']);self.assertEqual(m['withholding_precision'],ratio(1,8))
 def test_retrieval_partition(self):
  l,g=reviewed();p=self.score(l,g)['retrieval_partition'];self.assertEqual(p,{'source_unavailable':1,'supportable_not_retrieved':0,'retrieved_not_recovered':0,'recovered':1})
 def test_support_not_retrieved_no_recovery(self):
  l,g=reviewed()
  for item in l['gold'][:2]:item['retrieved_support']=False
  g['gold']=copy.deepcopy(l['gold'])
  with self.assertRaises(ValueError):self.score(l,g)
 def test_consistency_metrics(self):
  l,g=reviewed();m=self.score(l,g)['metrics'];self.assertEqual(m['numerical_accuracy'],ratio(1,1));self.assertIsNone(m['temporal_consistency']['value'])

class ReplayAndPlanTests(unittest.TestCase):
 def replay_fixture(self):
  b,r=bundle_fixture();es=sorted([e for e in b['entries'] if e['source_type']=='process'],key=lambda e:e['observation_time']);c=numeric_claim(b,es[0]['evidence_id'],es[1]['evidence_id']);x=output(claims=[c]);raw=dumps(x).encode();m={'event_id':EID,'cell_id':'G1-EN','view':'EN','citation_mode':'required','repetition':1,'run_id':'synthetic','output_sha256':hashlib.sha256(raw).hexdigest(),'bundle_sha256':digest(b),'receipt_sha256':digest(r)};return b,r,raw,m
 def test_exact_replay_no_model(self):
  b,r,raw,m=self.replay_fixture()
  with patch('urllib.request.urlopen',side_effect=AssertionError('NETWORK FORBIDDEN')):v=replay_bytes(EID,raw,m,b,r)
  self.assertEqual(v['source_output_sha256'],m['output_sha256']);self.assertEqual(v['llm_calls'],0);self.assertEqual(v['dispositions'][0]['disposition'],'SUPPORTED')
 def test_mutated_raw_replay_rejected(self):
  b,r,raw,m=self.replay_fixture()
  with self.assertRaises(ValueError):replay_bytes(EID,raw+b' ',m,b,r)
 def test_wrong_view_source_rejected(self):
  b,r,raw,m=self.replay_fixture();m['cell_id']='G1-E'
  with self.assertRaises(ValueError):replay_bytes(EID,raw,m,b,r)
 def test_manifest_identity_64(self):
  m=load(OUT/'validation_manifest.json');self.assertEqual(m['counts'],{'G0':19,'G1-EN':21,'G1-E':12,'G1-N':12});self.assertEqual(len({p['position_id'] for p in m['positions']}),64)
  for p in m['positions']:
   b,r=read_bundle(p['event_id'],p['view']);req=build_request(p['event_id'],p['cell_id'],b,r);self.assertEqual(digest(req),p['request_sha256'])
   if p['purpose']=='capacity_stress':
    old=load(ROOT/p['parent_request']['path']);old['max_output_tokens']=8192;self.assertEqual(req,old)
 def test_acceptance_no_delivery_not_pass(self):
  m=load(OUT/'validation_manifest.json');self.assertEqual(assess(m,[],True)['status'],'INCONCLUSIVE_NO_DELIVERY_OR_PENDING')
 def test_acceptance_truncation_stops(self):
  m=load(OUT/'validation_manifest.json');r={'position_id':m['positions'][0]['position_id'],'status':'PROVIDER_INCOMPLETE','termination_reason':'max_output_tokens','request_diff_valid':True};a=assess(m,[r],True);self.assertEqual(a['status'],'FAIL_OUTPUT_CAP_STOP_AUTHOR_REVIEW');self.assertFalse(a['automatic_rerun'])
 def test_acceptance_synthetic_all_completed(self):
  m=load(OUT/'validation_manifest.json');rows=[{'position_id':p['position_id'],'status':'DELIVERED','request_diff_valid':True,'schema_and_visibility_valid':True} for p in m['positions']];self.assertEqual(assess(m,rows,True)['status'],'PASS_DEVELOPMENT_CAP_ONLY_NOT_FREEZE')
 def test_preservation_all_r4_files(self):
  for ref in load(OUT/'preservation.before.json')['files']:self.assertEqual(file_hash(ROOT/ref['path']),ref['sha256'],ref['path'])

class StatisticsTests(unittest.TestCase):
 def cells(self):return [{'event_id':e,'baseline':b,'repetition':r,'metrics':{'evidence_completeness':ratio(n,d)}} for e,n,d in [(EID,1,1),(development_ids()[1],0,100)] for b in BASELINES for r in (1,2,3)]
 def test_exact_contrasts(self):self.assertEqual(CONTRASTS,(('G1-E','G1-EN'),('G1-N','G1-EN'),('G0','G1-EN'),('G1-EN','V1-EN')))
 def test_macro_and_D0_micro_not_tripled(self):
  a=aggregate(self.cells(),'evidence_completeness',{e:'fixture' for e in development_ids()});self.assertEqual(a['macro']['G1-E']['estimate'],.5);self.assertEqual(a['micro_diagnostic']['D0']['denominator'],101);self.assertEqual(a['bootstrap_resamples'],2000)
 def test_missing_repetitions_rejected(self):
  with self.assertRaises(ValueError):aggregate(self.cells()[:-1],'evidence_completeness',{})

class TransportTests(unittest.TestCase):
 def run_fixture(self,replies,validate=lambda e:[]):
  t=FixtureTransport(replies)
  with tempfile.TemporaryDirectory() as td:
   result=exercise({'model':'gpt-4.1-2025-04-14'},t,Path(td)/'attempts',validate=validate)
   self.assertEqual(len(list((Path(td)/'attempts').glob('attempt-*/attempt.json'))),len(result['attempts']))
  return result,t
 def test_connection_reset_history_and_identical_requests(self):
  r,t=self.run_fixture([ConnectionResetError('synthetic'),envelope()]);self.assertEqual(r['status'],'DELIVERED');self.assertEqual(len(r['attempts']),2);self.assertEqual(t.requests[0],t.requests[1]);self.assertEqual(r['attempts'][0]['delivery_status'],'UNKNOWN')
 def test_related_exceptions(self):
  for e in (ConnectionAbortedError(),BrokenPipeError(),ConnectionRefusedError(),TimeoutError(),urllib.error.URLError(ConnectionResetError())):self.assertTrue(retry_exception(e))
  for e in (ValueError(),FileNotFoundError(),PermissionError(),urllib.error.URLError('certificate failure')):self.assertFalse(retry_exception(e))
 def test_three_attempt_ceiling(self):
  r,t=self.run_fixture([ConnectionResetError()]*3);self.assertEqual(len(t.requests),3);self.assertFalse(r['attempts'][-1]['will_retry'])
 def test_http_retry_and_pacing(self):
  r,t=self.run_fixture([(429,{'retry-after':'90'},b'{}'),envelope()]);self.assertEqual(len(t.requests),2);self.assertEqual(next_delay({'retry-after':'90'},2),90);self.assertEqual(next_delay({},20),40)
 def test_no_quality_citation_semantic_retry(self):
  r,t=self.run_fixture([envelope()],lambda _:['citation_wrong','numeric_wrong']);self.assertEqual(len(t.requests),1);self.assertEqual(r['status'],'DELIVERED_SCHEMA_OR_VISIBILITY_INVALID')
 def test_truncation_not_retried(self):
  r,t=self.run_fixture([envelope(status='incomplete',reason='max_output_tokens')]);self.assertEqual(len(t.requests),1);self.assertTrue(r['attempts'][0]['capacity_stop_required'])
 def test_refusal_not_retried(self):
  r,t=self.run_fixture([envelope(refusal=True)]);self.assertEqual(len(t.requests),1);self.assertEqual(r['status'],'PROVIDER_REFUSAL')
 def test_malformed_envelope_delivery_retry(self):
  r,t=self.run_fixture([(200,{},b'{'),envelope()]);self.assertEqual(len(t.requests),2)
 def test_arbitrary_transport_forbidden(self):
  with tempfile.TemporaryDirectory() as td:
   with self.assertRaises(PermissionError):exercise({},lambda _:None,Path(td)/'deny')

if __name__=='__main__':unittest.main()

class SupplementalCandidateTests(unittest.TestCase):
 def test_failed_output_fixed_denominators(self):
  from investigation_r5.metrics import failure_scores
  l,g=reviewed();f=failure_scores(EID,'G1-EN',1,g,l['opportunities'])['metrics']
  self.assertEqual(f['evidence_completeness'],ratio(0,2));self.assertEqual(f['schema_compliance'],ratio(0,1));self.assertIsNone(f['unsupported_security_claim_rate']['value']);self.assertEqual(f['required_withholding_recall'],ratio(0,1))
 def test_fixture_integration_cell(self):
  from investigation_r5.runner import exercise_cell
  with tempfile.TemporaryDirectory() as td:
   for cell in ('G1-E','G1-N'):
    r=exercise_cell(EID,cell,FixtureTransport([envelope(output(cell_spec(cell)['view']))]),Path(td)/cell)
    self.assertEqual(r['status'],'DELIVERED');self.assertEqual(r['model_calls'],0)
 def test_unknown_scope_reference_visibility(self):
  from investigation_r5.runner import reference_visibility_errors
  b,r=read_bundle(EID,'E');self.assertTrue(reference_visibility_errors({'payload':{'scope_id':'d_'+'9'*24}},b))
 def test_failure_receipt_changed(self):
  b,r=read_bundle(EID,'E');r['retrieved_bundle_sha256']='changed'
  with self.assertRaises(ValueError):validate_input(b,r)
 def test_acceptance_smoke_schema_failure(self):
  m=load(OUT/'validation_manifest.json');p=next(p for p in m['positions'] if p['purpose']=='new_condition_smoke');r={'position_id':p['position_id'],'status':'DELIVERED_SCHEMA_OR_VISIBILITY_INVALID','schema_and_visibility_valid':False,'request_diff_valid':True}
  self.assertEqual(assess(m,[r],True)['status'],'FAIL_CONFORMANCE')
 def test_tls_and_local_errno_not_retried(self):
  import ssl,errno
  self.assertFalse(retry_exception(ssl.SSLCertVerificationError('fixture')));self.assertFalse(retry_exception(OSError(errno.EACCES,'fixture')));self.assertTrue(retry_exception(OSError(errno.ENETUNREACH,'fixture')))
 def test_all_withhold_has_no_positive_recovery(self):
  l,g=reviewed();l['assertions']=[]
  for q in l['questions']:q['coverage_minimum_met']=False
  m=score_reviewed_run(l,'fixture-hash',g)['metrics'];self.assertEqual(m['evidence_completeness'],ratio(0,2));self.assertIsNone(m['complete_support_rate']['value'])

class GoldNullableAccountingTests(unittest.TestCase):
 def test_ineligible_null_retained_not_new_gold_judgment(self):
  eid=load(ROOT/'annotations/gold/pilot-v1/manifest.json')['events'][0]['event_id'];g=pilot_contract(eid,'E');self.assertTrue(any(x['retrieved_support'] is None for x in g['gold']));self.assertTrue(all(type(x['retrieved_support']) is bool for x in g['gold'] if x['kind']=='positive' and x['view_eligible']))
 def test_eligible_positive_pending_retrieval_blocks(self):
  l,g=reviewed()
  for x in l['gold'][:2]:x['retrieved_support']=None
  g['gold']=copy.deepcopy(l['gold'])
  with self.assertRaises(PendingReview):score_reviewed_run(l,'fixture-hash',g)
