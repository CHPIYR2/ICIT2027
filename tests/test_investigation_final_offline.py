import copy,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from investigation_final_offline.contracts import *
from investigation_final_offline.scoring import score,IncompleteReview,surfaces
from investigation_final_offline.support import materialize_support_fields,retrieval_supported
from investigation_final_offline.fixtures import fixture,fixture_matrix,POLICY_HASH
from investigation_final_offline.reporting import products,aggregate,bootstrap
from investigation_final_offline.packet import review_worksheet

class ScoringTests(unittest.TestCase):
 def setUp(self):self.l,self.g,self.b,self.raw,self.stage=fixture()
 def runscore(self):return score(self.l,self.g,self.b,self.raw,self.stage,matching_policy_sha256=POLICY_HASH)
 def bindgold(self):
  self.g['commitment_sha256']=digest({k:v for k,v in self.g.items() if k!='commitment_sha256'});self.l['gold_sha256']=digest(self.g)
 def test_complete_funnel(self):
  s=self.runscore();self.assertEqual(s['funnel'],dict(full_gold_count=3,supportable_in_view_count=3,complete_support_retrieved_count=3,correctly_reconstructed_count=3))
  self.assertEqual(s['metrics']['unsupported_security_claim_rate']['value'],1)
 def test_guardrails_not_positive(self):self.assertEqual(self.runscore()['metrics']['evidence_completeness']['denominator'],3)
 def test_common_gold_denominator(self):
  for c in ('G1-E','G1-N','G1-EN'):
   l,g,b,r,s=fixture(cell=c);m=score(l,g,b,r,s,matching_policy_sha256=POLICY_HASH)['metrics'];self.assertEqual(m['evidence_completeness']['denominator'],3)
 def test_view_and_retrieval_separate(self):
  l,g,b,r,s=fixture(event='SYNTHETIC_A2');x=score(l,g,b,r,s,matching_policy_sha256=POLICY_HASH)
  self.assertEqual(x['funnel']['supportable_in_view_count'],3);self.assertEqual(x['funnel']['complete_support_retrieved_count'],2)
 def test_optional_citation_is_not_free_credit(self):
  l,g,b,r,s=fixture(cell='G0');x=score(l,g,b,r,s,matching_policy_sha256=POLICY_HASH)
  self.assertEqual(x['metrics']['complete_support_rate']['numerator'],0);self.assertEqual(x['metrics']['evidence_completeness']['numerator'],3)
 def test_pending_review_rejected(self):
  self.l['review']['reviewed_at']=None
  with self.assertRaises(ValueError):self.runscore()
 def test_second_reviewer_rejected(self):
  self.l['review']['reviewer_id']='R2'
  with self.assertRaises(ValueError):self.runscore()
 def test_policy_hash_drift(self):
  self.l['assertions'][0]['matching_policy_sha256']='c'*64
  with self.assertRaises(ValueError):self.runscore()
 def test_raw_hash_drift(self):
  self.raw+=b' '
  with self.assertRaises(ValueError):self.runscore()
 def test_stage_hash_drift(self):
  self.stage+=b' '
  with self.assertRaises(ValueError):self.runscore()
 def test_gold_hash_drift(self):
  self.g['unresolved_conclusions'].append('new')
  with self.assertRaises(ValueError):self.runscore()
 def test_bundle_hash_drift(self):
  self.b['visible_evidence_ids'].pop()
  with self.assertRaises(ValueError):self.runscore()
 def test_omitted_text_rejected(self):
  self.l['reviewed_surfaces'].pop()
  with self.assertRaises(ValueError):self.runscore()
 def test_changed_text_rejected(self):
  self.l['assertions'][0]['source']['text']='invented'
  with self.assertRaises(ValueError):self.runscore()
 def test_innocuous_type_still_security(self):
  self.assertEqual(self.l['assertions'][-1]['raw_claim_type'],'SYNTHETIC_observation')
  self.assertEqual(self.runscore()['counts']['security_sensitive_assertions'],1)
 def test_overclaim_cannot_hide_from_denominator(self):
  self.l['assertions'][-1]['security_sensitive']=False
  with self.assertRaises(ValueError):self.runscore()
 def test_support_cannot_exceed_visibility(self):
  self.l['assertions'][0]['required_support_sets']=[['hidden']]
  with self.assertRaises(ValueError):self.runscore()
 def test_complete_citations_required(self):
  self.l['assertions'][0]['citations'].pop()
  with self.assertRaises(ValueError):self.runscore()
 def test_role_support_not_id_only(self):
  a=self.l['assertions'][0];a['citations'][0]['role_supported']=False;a['cited_complete_support']=False
  s=self.runscore();self.assertLess(s['metrics']['citation_precision']['value'],1)
 def test_no_security_is_na(self):
  l,g,b,r,s=fixture(event='SYNTHETIC_A2',cell='G1-E')
  self.assertIsNone(score(l,g,b,r,s,matching_policy_sha256=POLICY_HASH)['metrics']['unsupported_security_claim_rate']['value'])
 def test_no_numeric_is_na(self):
  l,g,b,r,s=fixture(cell='G1-N');self.assertIsNone(score(l,g,b,r,s,matching_policy_sha256=POLICY_HASH)['metrics']['numerical_consistency']['value'])
 def test_unit_error_is_numerical_error(self):
  self.l['assertions'][0]['numerical']['unit']=False;self.assertEqual(self.runscore()['metrics']['numerical_consistency']['value'],0)
 def test_asset_mapping_required(self):
  self.l['assertions'][0]['asset']['approved_mapping']=False;self.assertEqual(self.runscore()['metrics']['asset_consistency']['value'],0)
 def test_q7_not_coverage(self):
  self.l['questions'][-1].update(adequate=True,adequate_assertion_ids=['a0'])
  self.assertEqual(self.runscore()['metrics']['q1_q6_substantive_coverage']['numerator'],2)
 def test_unsupported_does_not_cover(self):
  self.l['questions'][0]['adequate_assertion_ids']=['a3']
  with self.assertRaises(ValueError):self.runscore()
 def test_q6_requires_human_judgment(self):
  self.l['questions'][5].update(adequate=True,adequate_assertion_ids=['a0']);self.l['assertions'][0]['q6_relevance']=None
  with self.assertRaises(ValueError):self.runscore()
 def test_wrong_withholding_scope(self):
  self.l['actions'][0]['scope_correct']=False;m=self.runscore()['metrics']
  self.assertEqual(m['required_withholding_recall']['value'],0);self.assertEqual(m['withholding_precision']['value'],0)
 def test_wrong_withholding_reason(self):
  self.l['actions'][0]['reason_correct']=False;self.assertEqual(self.runscore()['metrics']['required_withholding_recall']['numerator'],0)
 def test_silence_is_not_correct_withholding(self):
  self.l['actions']=[];m=self.runscore()['metrics'];self.assertEqual(m['required_withholding_recall']['value'],0);self.assertIsNone(m['withholding_precision']['value'])
 def test_unlisted_action_counts_precision(self):
  self.l['actions'][0].update(opportunity_id=None,action_correct=False)
  self.assertEqual(self.runscore()['metrics']['withholding_precision']['denominator'],1)
 def test_guardrail_action_cannot_be_invented(self):
  self.l['actions'][0]['opportunity_id']='invented'
  with self.assertRaises(ValueError):self.runscore()
 def test_human_gold_alias_counts_once(self):
  self.g['aliases']=[{'alias_id':'aliasE','canonical_gold_id':'gE','rationale':'SYNTHETIC approved semantic equivalence','review':copy.deepcopy(self.g['review'])}]
  self.bindgold();self.l['assertions'][0]['matched_gold_ids']=['gE','aliasE']
  self.assertEqual(self.runscore()['metrics']['evidence_completeness']['numerator'],3)
 def test_alias_requires_human_approval(self):
  self.g['aliases']=[{'alias_id':'aliasE','canonical_gold_id':'gE','rationale':'no review'}];self.bindgold()
  with self.assertRaises(ValueError):self.runscore()
 def test_duplicate_assertion_dedup(self):
  dup=copy.deepcopy(self.l['assertions'][0]);dup.update(assertion_id='a4',duplicate_of='a0',duplicate_rationale='SYNTHETIC equivalent');self.l['assertions'].append(dup)
  next(s for s in self.l['reviewed_surfaces'] if s['pointer']==dup['source']['pointer'])['assertion_ids'].append('a4')
  self.assertEqual(self.runscore()['metrics']['complete_support_rate']['denominator'],4)
 def test_conflicting_duplicate_rejected(self):
  dup=copy.deepcopy(self.l['assertions'][0]);dup.update(assertion_id='a4',duplicate_of='a0',duplicate_rationale='SYNTHETIC',supported=False);self.l['assertions'].append(dup)
  next(s for s in self.l['reviewed_surfaces'] if s['pointer']==dup['source']['pointer'])['assertion_ids'].append('a4')
  with self.assertRaises(ValueError):self.runscore()
 def test_invalid_delivery_all_na(self):
  self.l.update(delivery='INVALID_PROVIDER_DELIVERY',delivery_reason='SYNTHETIC incomplete')
  self.l['delivery_receipt'].update(status='PROVIDER_INCOMPLETE',termination_reason='max_output_tokens')
  self.assertTrue(all(m['value'] is None for m in self.runscore()['metrics'].values()))
 def test_empty_valid_output_zero_fixed_denominators(self):
  self.raw=dumps({'event_id':self.l['event_id'],'claims':[]}).encode();self.stage=self.raw
  self.l.update(raw_output_sha256=sha(self.raw),stage_artifact_sha256=sha(self.stage),assertions=[],actions=[])
  self.l['reviewed_surfaces']=[{'pointer':'/event_id','text':self.l['event_id'],'assertion_ids':[],'nonassertive_reason':'SYNTHETIC metadata'}]
  for q in self.l['questions']:q.update(adequate=False,adequate_assertion_ids=[])
  m=self.runscore()['metrics'];self.assertEqual(m['evidence_completeness']['value'],0);self.assertEqual(m['q1_q6_substantive_coverage']['value'],0);self.assertIsNone(m['unsupported_security_claim_rate']['value'])
 def test_worksheet_is_pending(self):
  w=review_worksheet(self.l['event_id'],'G1-EN',1,self.raw,self.stage,self.b,digest(self.g))
  self.assertFalse(w['all_text_reviewed']);self.assertIsNone(w['reviewed_at'])
 def test_d0_once(self):
  l,g,b,r,s=fixture(cell='D0');self.assertEqual(score(l,g,b,r,s,matching_policy_sha256=POLICY_HASH)['repetition'],0)
 def test_replay_exact(self):
  l,g,b,r,s=fixture(cell='V1-EN');self.assertEqual(score(l,g,b,r,s,matching_policy_sha256=POLICY_HASH)['metrics']['unsupported_security_claim_rate']['value'],None)
 def test_missing_publication_rejected(self):
  l,g,b,r,s=fixture(cell='V1-EN');x=json.loads(s);del x['published_report'];s=dumps(x).encode();l['stage_artifact_sha256']=sha(s)
  with self.assertRaises(ValueError):score(l,g,b,r,s,matching_policy_sha256=POLICY_HASH)

class ReportTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.rows,cls.strata,_=fixture_matrix();cls.report=products(cls.rows,cls.strata,data_label='SYNTHETIC_TEST_ONLY_NOT_PAPER_RESULTS')
 def test_every_product_validates(self):
  for k in TABLE_SCHEMAS:validate(k,self.report[k])
 def test_table_row_counts(self):self.assertEqual([len(self.report[t]) for t in ('table4','table5','table6','table7')],[6,8,10,5])
 def test_complete_matrix(self):self.assertEqual(len(self.rows),64)
 def test_no_na_to_zero_plot(self):self.assertTrue(any(x['uscr'] is None and not x['uscr_defined'] for x in self.report['figure2']))
 def test_event_counts_preserved(self):self.assertTrue(all(r['conditions']['G1-EN']['population_event_count']==4 for r in self.report['table4']))
 def test_structural_dash(self):
  for row in self.report['table6'][-2:]:self.assertEqual(row['contrasts']['V1_minus_G1']['display'],'—')
 def test_d0_micro_count_once(self):self.assertEqual(self.report['micro_supplementary']['evidence_completeness']['D0']['denominator'],12)
 def test_micro_generation_three_repetitions(self):self.assertEqual(self.report['micro_supplementary']['evidence_completeness']['G0']['denominator'],36)
 def test_missing_repetition_blocks(self):
  with self.assertRaises(ValueError):aggregate(self.rows[:-1],self.strata)
 def test_duplicate_blocks(self):
  with self.assertRaises(ValueError):aggregate(self.rows+[self.rows[0]],self.strata)
 def test_missing_stratum_blocks(self):
  with self.assertRaises(ValueError):aggregate(self.rows,{})
 def test_replay_identity_changed_blocks(self):
  rows=copy.deepcopy(self.rows);next(r for r in rows if r['cell_id']=='V1-EN')['raw_output_sha256']='f'*64
  with self.assertRaises(ValueError):aggregate(rows,self.strata)
 def test_gold_denominator_changed_blocks(self):
  rows=copy.deepcopy(self.rows);rows[0]['gold_sha256']='f'*64
  with self.assertRaises(ValueError):aggregate(rows,self.strata)
 def test_final_guard(self):
  with self.assertRaises(ValueError):products(self.rows,self.strata,data_label='FROZEN_EVALUATION_REVIEWED')
 def test_development_never_paper(self):
  with self.assertRaises(ValueError):products(self.rows,self.strata,data_label='DEVELOPMENT')
 def test_stratified_bootstrap_constant_delta(self):
  b=bootstrap({'a':.25,'b':.25},{'a':'s1','b':'s2'},['a','b'],'B minus A');self.assertEqual(b['ci95'],[.25,.25]);self.assertEqual(b['singleton_strata'],['s1','s2'])
 def test_bootstrap_reproducible(self):
  args=({'a':.1,'b':.5,'c':-.1},{'a':'s1','b':'s1','c':'s2'},['a','b','c'],'B minus A')
  self.assertEqual(bootstrap(*args),bootstrap(*args))
 def test_bootstrap_empty(self):self.assertIsNone(bootstrap({}, {}, ['a'], 'B minus A')['mean_difference'])
 def test_na_repetitions_average_defined_only(self):
  rows=copy.deepcopy(self.rows)
  s=next(s for s in rows if s['event_id']=='SYNTHETIC_A1' and s['cell_id']=='G0' and s['repetition']==1)
  s['metrics']['unsupported_security_claim_rate']={'numerator':0,'denominator':0,'value':None}
  a=aggregate(rows,self.strata);v=next(x for x in a['stability'] if x['event_id']=='SYNTHETIC_A1' and x['condition']=='G0' and x['metric']=='unsupported_security_claim_rate')
  self.assertEqual(v['n_defined_repetitions'],2);self.assertEqual(v['event_mean'],1)


class ContractBoundaryTests(unittest.TestCase):
 def test_delivery_quality_exclusion_forbidden(self):
  l,g,b,r,s=fixture();l['delivery']='INVALID_PROVIDER_DELIVERY'
  with self.assertRaises(ValueError):score(l,g,b,r,s,matching_policy_sha256=POLICY_HASH)
 def test_schema_failure_still_counts_fixed_opportunities(self):
  l,g,b,r,s=fixture();l['schema_compliant']=False;l['delivery_receipt']['status']='DELIVERED_SCHEMA_OR_VISIBILITY_INVALID'
  m=score(l,g,b,r,s,matching_policy_sha256=POLICY_HASH)['metrics']
  self.assertEqual(m['evidence_completeness']['denominator'],3);self.assertEqual(m['schema_compliance']['value'],0)
 def test_gold_commitment_tamper(self):
  l,g,b,r,s=fixture();g['commitment_sha256']='c'*64;l['gold_sha256']=digest(g)
  with self.assertRaises(ValueError):score(l,g,b,r,s,matching_policy_sha256=POLICY_HASH)
 def test_missing_provider_output_not_fabricated(self):
  from investigation_final_offline.scoring import score_delivery_failure
  l,g,b,r,s=fixture();receipt={**l['delivery_receipt'],'status':'FAILED_NO_VALID_DELIVERY'}
  row=score_delivery_failure(l['event_id'],l['cell_id'],1,g,b,receipt,matching_policy_sha256=POLICY_HASH)
  self.assertIsNone(row['raw_output_sha256']);self.assertTrue(all(x['value'] is None for x in row['metrics'].values()))
 def test_local_failure_remains_blocker(self):
  from investigation_final_offline.scoring import score_delivery_failure
  l,g,b,r,s=fixture();receipt={**l['delivery_receipt'],'status':'MODEL_IDENTIFIER_MISMATCH'}
  with self.assertRaises(ValueError):score_delivery_failure(l['event_id'],l['cell_id'],1,g,b,receipt,matching_policy_sha256=POLICY_HASH)
 def test_no_generated_citations_can_be_omitted(self):
  l,g,b,r,s=fixture();a=l['assertions'][0];a['citations'].pop();a['cited_complete_support']=False
  with self.assertRaises(ValueError):score(l,g,b,r,s,matching_policy_sha256=POLICY_HASH)
 def test_numeric_policy_preserves_tiny_nonzero(self):
  from investigation_dryrun.claims import numeric_equal
  self.assertFalse(numeric_equal(0,1e-20));self.assertTrue(numeric_equal(1e-20,1e-20))
 def test_duration_tolerance_never_ordering(self):
  from investigation_dryrun.claims import numeric_equal
  self.assertTrue(numeric_equal(1.0000004,1,duration=True));self.assertFalse(numeric_equal(1.0000006,1,duration=True))
  l,g,b,r,s=fixture();l['assertions'][0]['temporal']={'exact_timestamps':True,'exact_ordering':False,'scope':True,'required_mappings':True}
  self.assertEqual(score(l,g,b,r,s,matching_policy_sha256=POLICY_HASH)['metrics']['temporal_consistency']['value'],0)
 def test_always_withhold_coverage_zero(self):
  l,g,b,raw,stage=fixture(cell='G1-E');obj=json.loads(raw);obj['claims']=[];raw=dumps(obj).encode();stage=raw
  l.update(raw_output_sha256=sha(raw),stage_artifact_sha256=sha(stage),assertions=[])
  l['reviewed_surfaces']=[{'pointer':p,'text':s,'assertion_ids':[],'nonassertive_reason':'SYNTHETIC uncertainty only'} for p,s in surfaces(obj).items()]
  for q in l['questions']:q.update(adequate=False,adequate_assertion_ids=[])
  m=score(l,g,b,raw,stage,matching_policy_sha256=POLICY_HASH)['metrics']
  self.assertEqual(m['q1_q6_substantive_coverage']['value'],0);self.assertEqual(m['required_withholding_recall']['value'],1);self.assertIsNone(m['unsupported_security_claim_rate']['value'])

 def test_view_contamination_rejected(self):
  l,g,b,r,s=fixture(cell='G1-N');b['visible_evidence_ids'].append('e1');l['bundle_sha256']=digest(b)
  with self.assertRaises(ValueError):score(l,g,b,r,s,matching_policy_sha256=POLICY_HASH)
 def test_unknown_visible_evidence_rejected(self):
  l,g,b,r,s=fixture();b['visible_evidence_ids'].append('hidden');l['bundle_sha256']=digest(b)
  with self.assertRaises(ValueError):score(l,g,b,r,s,matching_policy_sha256=POLICY_HASH)
 def test_existential_accepts_different_witness(self):
  fact={'views':{'E':{'supportable':True,'acceptable_support_sets':[['witness-a']],'rationale':'reviewed witness'}},
        'fields':materialize_support_fields({'source_type':'message','protocol':'IEC104','window_start':-60,'window_end':60,'right_boundary_exclusive':True})}
  records=[{'evidence_id':'other','source_type':'message','protocol':'IEC104','observation_time':1.5,'quality_flags':[]}]
  self.assertTrue(retrieval_supported(fact,'E',{'other'},records))
  self.assertNotIn('other',fact['views']['E']['acceptable_support_sets'][0])
 def test_existential_miss_without_predicate_record(self):
  fact={'views':{'E':{'supportable':True,'acceptable_support_sets':[['witness-a']],'rationale':'reviewed witness'}},
        'fields':materialize_support_fields({'source_type':'message','protocol':'IEC104','window_start':-60,'window_end':60})}
  records=[{'evidence_id':'packet','source_type':'packet','protocol':'TCP','observation_time':1.5,'quality_flags':[]}]
  self.assertFalse(retrieval_supported(fact,'E',{'packet'},records))
 def test_role_accepts_different_tuple(self):
  fact={'views':{'EN':{'supportable':True,'acceptable_support_sets':[['old-before','old-after']],'rationale':'reviewed witness'}},
        'fields':materialize_support_fields({'source_type':'message','protocol':'IEC104','anchor_time':0,'interval_start':-1,'interval_end':1,'requires_observation_before_anchor':True,'requires_observation_after_anchor':True})}
  records=[{'evidence_id':'b','source_type':'message','protocol':'IEC104','observation_time':-0.2,'quality_flags':[]},
           {'evidence_id':'a','source_type':'message','protocol':'IEC104','observation_time':0.4,'quality_flags':[]}]
  self.assertTrue(retrieval_supported(fact,'EN',{'b','a'},records))
 def test_role_fails_when_one_role_absent(self):
  fact={'views':{'EN':{'supportable':True,'acceptable_support_sets':[['old-before','old-after']],'rationale':'reviewed witness'}},
        'fields':materialize_support_fields({'source_type':'message','protocol':'IEC104','anchor_time':0,'interval_start':-1,'interval_end':1,'requires_observation_before_anchor':True,'requires_observation_after_anchor':True})}
  records=[{'evidence_id':'b','source_type':'message','protocol':'IEC104','observation_time':-0.2,'quality_flags':[]}]
  self.assertFalse(retrieval_supported(fact,'EN',{'b'},records))
 def test_exact_still_requires_accepted_set(self):
  fact={'views':{'E':{'supportable':True,'acceptable_support_sets':[['e-before','e-after']],'rationale':'exact pair'}},
        'fields':materialize_support_fields({'before_evidence_id':'e-before','channel_id':'ch'})}
  records=[{'evidence_id':'other','source_type':'process','context':'MEASUREMENT','observation_time':1,'quality_flags':[]}]
  self.assertFalse(retrieval_supported(fact,'E',{'other'},records))
  self.assertTrue(retrieval_supported(fact,'E',{'e-before','e-after'},records))
 def test_retrieved_gate_uses_predicate_not_witness_id(self):
  l,g,b,raw,stage=fixture()
  fact=next(f for f in g['positive_facts'] if f['gold_id']=='gN')
  fact['fields']=materialize_support_fields({'source_type':'message','protocol':'IEC104','window_start':-60,'window_end':60})
  fact['views']['N']['acceptable_support_sets']=[['n-witness']]
  fact['views']['EN']['acceptable_support_sets']=[['n-witness']]
  g['source_evidence_hashes'].append({'evidence_id':'n-witness','sha256':sha(b'n-witness'),'views':['N','EN']})
  b['visible_records']=[{'evidence_id':'n1','source_type':'message','protocol':'IEC104','observation_time':3,'quality_flags':[]}]
  g['commitment_sha256']=digest({k:v for k,v in g.items() if k!='commitment_sha256'})
  l['gold_sha256']=digest(g);l['bundle_sha256']=digest(b)
  result=score(l,g,b,raw,stage,matching_policy_sha256=POLICY_HASH)
  self.assertIn('gN',result['recovered_gold_ids'])
  self.assertEqual(result['metrics']['citation_precision'],score(*fixture(),matching_policy_sha256=POLICY_HASH)['metrics']['citation_precision'])
  b['visible_records'][0].update(source_type='packet',protocol='TCP')
  l['bundle_sha256']=digest(b)
  with self.assertRaises(IncompleteReview):score(l,g,b,raw,stage,matching_policy_sha256=POLICY_HASH)
 def test_citation_precision_and_complete_support_unchanged(self):
  l,g,b,raw,stage=fixture()
  before=score(l,g,b,raw,stage,matching_policy_sha256=POLICY_HASH)
  b['visible_records']=[{'evidence_id':i,'source_type':'message','protocol':'IEC104','observation_time':1,'quality_flags':[]} for i in b['visible_evidence_ids']]
  l['bundle_sha256']=digest(b)
  after=score(l,g,b,raw,stage,matching_policy_sha256=POLICY_HASH)
  self.assertEqual(before['metrics']['citation_precision'],after['metrics']['citation_precision'])
  self.assertEqual(before['metrics']['complete_support_rate'],after['metrics']['complete_support_rate'])
  self.assertEqual(before['funnel']['complete_support_retrieved_count'],after['funnel']['complete_support_retrieved_count'])

class PipelineTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  from investigation_final_offline.fixtures import committed_fixture_packet
  cls.packet=committed_fixture_packet()
 def runpacket(self,p):
  from investigation_final_offline.pipeline import score_committed_packet
  return score_committed_packet(p,trusted_commitment_sha256=digest(self.packet['manifest']))
 def test_end_to_end(self):
  rows,report=self.runpacket(self.packet);self.assertEqual(len(rows),64);self.assertEqual(len(report['figure2']),20)
 def test_tampered_input(self):
  p=copy.deepcopy(self.packet);p['inputs'][0]['ledger']['assertions'][0]['supported']=False
  with self.assertRaises(ValueError):self.runpacket(p)
 def test_tampered_commitment(self):
  p=copy.deepcopy(self.packet);p['manifest']['matching_policy_sha256']='c'*64
  with self.assertRaises(ValueError):self.runpacket(p)
 def test_missing_position(self):
  p=copy.deepcopy(self.packet);p['inputs'].pop()
  with self.assertRaises(ValueError):self.runpacket(p)
 def test_synthetic_relabel_prohibited(self):
  from investigation_final_offline.pipeline import score_committed_packet
  p=copy.deepcopy(self.packet);p['manifest']['event_ids'][0]='ev_actual'
  with self.assertRaises(ValueError):score_committed_packet(p,trusted_commitment_sha256=digest(p['manifest']))


class Event1SupportTests(unittest.TestCase):
 def test_fact_002_miss_and_fact_012_retrieved(self):
  root=Path(__file__).resolve().parents[1]
  eid='ev_eda32c84a9cf2952b292'
  worksheet=Path('/Users/Shared/ICIT2027-custody/v1/PRIVATE_EVALUATOR/PRIVATE_GOLD/annotation-v1')/eid/'annotation.worksheet.json'
  facts=json.loads(worksheet.read_text())['positive_facts']
  for fact in facts: fact['fields']=materialize_support_fields(fact['fields'])
  counts={}
  for view in ('E','N','EN'):
   bundle=json.loads((root/'results/investigation-v2/B0'/eid/view/'retrieved.json').read_text())
   visible={r['evidence_id'] for r in bundle['entries']}
   visible.update(m['evidence_id'] for m in bundle['metadata'].values())
   records=bundle['entries']
   supportable=[f for f in facts if f['views'][view]['supportable']]
   retrieved=[f['gold_id'][-3:] for f in supportable if retrieval_supported(f,view,visible,records)]
   counts[view]=(len(retrieved),len(supportable),retrieved)
  self.assertEqual(counts['E'][:2],(1,9));self.assertEqual(counts['E'][2],['003'])
  self.assertEqual(counts['N'][:2],(1,2));self.assertEqual(counts['N'][2],['001'])
  self.assertNotIn('002',counts['N'][2]);self.assertNotIn('002',counts['EN'][2])
  self.assertEqual(counts['EN'][:2],(3,12));self.assertEqual(counts['EN'][2],['001','003','012'])

class PreparedManifestTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.root=Path(__file__).resolve().parents[1]
  out=cls.root/'results/investigation-final-offline'
  cls.gen=json.loads((out/'generation_manifest.candidate.json').read_text())
  cls.replay=json.loads((out/'replay_manifest.candidate.json').read_text())
  cls.reference=json.loads((out/'reference_manifest.candidate.json').read_text())
 def test_384_generation_positions(self):
  positions=self.gen['positions'];self.assertEqual(len(positions),384);self.assertEqual(len({p['position_id'] for p in positions}),384)
  self.assertTrue(all(sum(p['cell_id']==c for p in positions)==96 for c in ('G0','G1-E','G1-N','G1-EN')))
 def test_exact_selected_ids_only(self):
  selected=json.loads((self.root/'configs/investigation_events.v1.json').read_text())
  self.assertEqual({p['event_id'] for p in self.gen['positions']},set(selected['evaluation']))
 def test_96_one_to_one_replays(self):
  self.assertEqual(len(self.replay['positions']),96)
  self.assertEqual({p['source_position_id'] for p in self.replay['positions']},{p['position_id'] for p in self.gen['positions'] if p['cell_id']=='G1-EN'})
  self.assertTrue(all(p['model_calls']==0 and not p['regeneration_permitted'] for p in self.replay['positions']))
 def test_32_d0_once(self):
  self.assertEqual(self.reference['independent_executions'],32);self.assertEqual(len(self.reference['positions']),32)
  self.assertTrue(all(p['repetition']==0 and p['executions']==1 for p in self.reference['positions']))
 def test_expected_configuration_bindings(self):
  cb=self.gen['config'];self.assertEqual(sha((self.root/cb['path']).read_bytes()),cb['sha256'])
  config=json.loads((self.root/cb['path']).read_text())
  for p in self.gen['positions']:
   self.assertEqual(p['expected_config_hash'],cb['sha256']);self.assertEqual(p['expected_max_output_tokens'],24576)
   self.assertEqual(p['expected_prompt_hash'],config['prompts'][p['cell_id']]['sha256'])
   self.assertEqual(p['expected_schema_hash'],config['compiled_schemas'][p['expected_citation_mode']]['canonical_json_sha256'])
 def test_no_execution_or_invented_binding(self):
  self.assertTrue(self.gen['protocol_frozen']);self.assertFalse(self.gen['execution_authorized'])
  self.assertTrue(all(p['output_sha256'] is None and p['request_sha256'] is None and p['bundle_sha256'] for p in self.gen['positions']))
  groups={}
  for p in self.gen['positions']: groups.setdefault((p['event_id'],p['evidence_view']),set()).add(p['bundle_sha256'])
  self.assertTrue(all(len(v)==1 for v in groups.values()))
  for p in self.replay['positions']:
   source=next(g for g in self.gen['positions'] if g['position_id']==p['source_position_id'])
   self.assertEqual(p['source_bundle_sha256'],source['bundle_sha256']);self.assertIsNone(p['source_output_sha256'])
  for p in self.reference['positions']:
   match=next(g['bundle_sha256'] for g in self.gen['positions'] if g['event_id']==p['event_id'] and g['evidence_view']=='EN')
   self.assertEqual(p['bundle_sha256'],match)

if __name__=='__main__':unittest.main()
