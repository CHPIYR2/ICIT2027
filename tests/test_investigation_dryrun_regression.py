import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from test_investigation_v2 import fixture
from retrieval.investigation_retriever_v2 import retrieve
from retrieval.investigation_retriever import difference
from investigation_dryrun import claims as C
from investigation_dryrun.common import digest,dumps,load,file_hash
from investigation_dryrun.custody import development_ids,require_development,read_bundle,verify_access_log
from investigation_dryrun.tokens import audit,count
from investigation_dryrun.metrics import score_reviewed_run,PendingReview,failure_scores
from investigation_dryrun.statistics import aggregate
from investigation_dryrun.runner import generate,build_request,replay_bytes,approved_configuration,plan,OpenAITransport,TransportFailure

EID=development_ids()[0];OTHER=development_ids()[1]

def bundle_fixture(view='EN'):
    public,_,_=fixture(view);public['scope']['event_id']=EID
    return retrieve(public)

def claim_fixture(raw='reported_change'):
    b,r=bundle_fixture();es=sorted([x for x in b['entries'] if x['source_type']=='process'],key=lambda x:x['observation_time'])
    c=C.numeric_claim(b,es[0]['evidence_id'],es[1]['evidence_id'],raw_type=raw)
    return b,r,c

def refresh_text(c,b):
    c['claim_text']=C.typed_support(c,b)['canonical_text'];return c

def output_fixture(event=EID,view='EN',citation='required',claims=None):
    return {'schema_version':'investigation-claim-v3','event_id':event,'evidence_view':view,'citation_mode':citation,'claims':claims or [],'questions':[{'question_id':f'Q{i}','claim_ids':[c['claim_id'] for c in claims or [] if f'Q{i}' in c['question_ids']],'response':'substantive' if any(f'Q{i}' in c['question_ids'] for c in claims or []) else 'insufficient'} for i in range(1,8)]}

def provider_output(output,status='completed'):
    return {'id':'resp_fixture','model':'gpt-4.1-2025-04-14','status':status,'created_at':123,'usage':{'input_tokens':1,'output_tokens':1},'output':[{'type':'message','content':[{'type':'output_text','text':dumps(output)}]}]}

class FakeTransport:
    fixture=True
    def __init__(self,replies=None):self.replies=list(replies or []);self.requests=[]
    def __call__(self,request,client_id,timeout):
        self.requests.append(copy.deepcopy(request))
        if self.replies:
            item=self.replies.pop(0)
            if isinstance(item,Exception):raise item
            return item
        b=json.loads(request['input']);mode='required' if 'citation_mode to "required"' in request['instructions'] else 'optional_baseline'
        return 200,{'x-request-id':'fixture'},json.dumps(provider_output(output_fixture(b['scope']['event_id'],b['scope']['view'],mode))).encode()

class NumericSemanticsTests(unittest.TestCase):
    def test_specialization_same_identity_raw_preserved(self):
        b,r,c=claim_fixture();e=copy.deepcopy(c);e['claim_type']='electrical_change'
        raw=dumps(e);a=C.canonical_numeric_fact(c,b);z=C.canonical_numeric_fact(e,b)
        self.assertEqual(a['identity'],z['identity']);self.assertEqual(dumps(e),raw);self.assertEqual(z['raw_claim']['claim_type'],'electrical_change')
    def test_wrong_numeric_never_normalizes(self):
        for field,value in [('result',12345),('before_value',12345),('after_value',12345)]:
            b,r,c=claim_fixture();c['payload'][field]=value
            with self.assertRaises(ValueError):C.canonical_numeric_fact(c,b)
    def test_exact_identity_gates(self):
        for field,value in [('asset_ids',['asset_'+'9'*16]),('channel_ids',['ch_'+'9'*16]),('endpoint_ids',['ep_'+'9'*16])]:
            b,r,c=claim_fixture();c[field]=value
            with self.assertRaises(ValueError):C.canonical_numeric_fact(c,b)
    def test_missing_wrong_or_reversed_pair(self):
        for mode in ('missing','same','reversed'):
            b,r,c=claim_fixture();p=c['payload']
            if mode=='missing':p['after_id']='e_'+'9'*24
            elif mode=='same':p['after_id']=p['before_id']
            else:p['before_id'],p['after_id']=p['after_id'],p['before_id']
            with self.assertRaises(ValueError):C.canonical_numeric_fact(c,b)
    def test_electrical_family_and_quality(self):
        for mode in ('family','metadata','quality'):
            b,r,c=claim_fixture('electrical_change');e=next(x for x in b['entries'] if x['evidence_id']==c['payload']['before_id'])
            if mode=='family':e['fields']['family']='temperature'
            elif mode=='metadata':b['metadata'][e['fields']['channel_id']]['family']='current'
            else:e['quality_flags']=['invalid']
            with self.assertRaises(ValueError):C.canonical_numeric_fact(c,b)
    def test_missing_mapping(self):
        b,r,c=claim_fixture();b['metadata']={}
        with self.assertRaises(ValueError):C.canonical_numeric_fact(c,b)
    def test_no_bool_numeric(self):
        b,r,c=claim_fixture();c['payload']['before_value']=True
        with self.assertRaises(ValueError):C.canonical_numeric_fact(c,b)
        b,r,c=claim_fixture();e=next(x for x in b['entries'] if x['source_type']=='process');e['value']=True
        with self.assertRaises(ValueError):C.valid_e(e,b)
    def test_unit_and_operation_not_aliases(self):
        b,r,c=claim_fixture();p=C.numeric_claim(b,c['payload']['before_id'],c['payload']['after_id'],'percent_change')
        self.assertNotEqual(C.canonical_numeric_fact(c,b)['identity'],C.canonical_numeric_fact(p,b)['identity'])
        c['payload']['unit']='WATT'
        with self.assertRaises(ValueError):C.canonical_numeric_fact(c,b)
    def test_zero_tiny_and_tolerance_boundaries(self):
        self.assertFalse(C.numeric_equal(0,1e-15));self.assertFalse(C.numeric_equal(1e-15,0));self.assertTrue(C.numeric_equal(0,0))
        self.assertTrue(C.numeric_equal(1.00000005,1));self.assertFalse(C.numeric_equal(1.000000051,1));self.assertFalse(C.numeric_equal(-1,1))
    def test_zero_baseline_percent(self):
        b,r,c=claim_fixture();a=next(x for x in b['entries'] if x['evidence_id']==c['payload']['before_id']);a['value']=0
        with self.assertRaises(ValueError):C.numeric_claim(b,c['payload']['before_id'],c['payload']['after_id'],'percent_change')
    def test_timestamp_exact_despite_duration_tolerance(self):
        b,r,c=claim_fixture();c['payload']['before_time']+=1e-8
        with self.assertRaises(ValueError):C.canonical_numeric_fact(c,b)
        self.assertTrue(C.numeric_equal(1.0000005,1,True));self.assertFalse(C.numeric_equal(1.00000051,1,True))
    def test_stronger_text_is_not_hidden(self):
        b,r,c=claim_fixture();c['claim_text']='The command caused this change; malicious intent is established.'
        with self.assertRaises(ValueError):C.canonical_numeric_fact(c,b)
        self.assertEqual(C.verify_claim(c,b)['disposition'],'INSUFFICIENT')
    def test_review_is_hash_bound(self):
        b,r,c=claim_fixture();c['claim_text']='A noncanonical but reviewed reported numerical observation.'
        review={'claim_sha256':digest(c),'bundle_sha256':digest(b),'supported':True,'reviewer_id':'R1','reviewed_at':'fixture'}
        C.canonical_numeric_fact(c,b,review)
        c['claim_text']+=' Another assertion.'
        with self.assertRaises(ValueError):C.canonical_numeric_fact(c,b,review)
    def test_optional_citation_content_vs_required_citation(self):
        b,r,c=claim_fixture();c['evidence_ids']=[]
        C.canonical_numeric_fact(c,b)
        with self.assertRaises(ValueError):C.canonical_numeric_fact(c,b,require_citations=True)
    def test_hidden_or_irrelevant_citation(self):
        b,r,c=claim_fixture();c['evidence_ids'].append('p_'+'9'*24)
        with self.assertRaises(ValueError):C.canonical_numeric_fact(c,b)
    def test_b0_sidecar_does_not_correct_raw_values(self):
        b,r,c=claim_fixture();d=next(x for x in b['entries'] if x['source_type']=='derived' and x['fields']['kind']=='numeric_difference')
        row={'claim_type':'reported_change','asset_id':d['asset_id'],'unit':d['unit'],'evidence_ids':[d['evidence_id'],*d['parent_ids']],**d['fields']}
        original=copy.deepcopy(row);out=C.adapt_b0_numeric(row,b)
        self.assertEqual(row,original);self.assertEqual(len(out),2);self.assertEqual(out[1]['adapted_claim']['payload']['unit'],'PERCENT')
        for field,value in [('difference',999),('family','current'),('asset_id','asset_'+'9'*16)]:
            bad=copy.deepcopy(row);bad[field]=value
            with self.assertRaises(ValueError):C.adapt_b0_numeric(bad,b)
    def test_matching_after_support_not_key_alone(self):
        b,r,c=claim_fixture();k=C.canonical_numeric_fact(c,b)['fact_key'];g={'event_id':EID,'claim_type':'electrical_change','fact_key':k}
        self.assertTrue(C.matches_gold(c,b,g));c['payload']['result']=9
        with self.assertRaises(ValueError):C.matches_gold(c,b,g)
    def test_raw_type_other_than_numeric_is_not_aliased(self):
        b,r,c=claim_fixture();k=C.canonical_numeric_fact(c,b)['fact_key']
        self.assertFalse(C.matches_gold(c,b,{'event_id':EID,'claim_type':'reported_value','fact_key':k}))

class ReplayTests(unittest.TestCase):
    def setup_replay(self,c=None):
        b,r,n=claim_fixture();c=c or n;raw=dumps(output_fixture(claims=[c])).encode()
        m={'event_id':EID,'baseline':'B3','repetition':1,'run_id':'fixture','output_sha256':hashlib.sha256(raw).hexdigest(),'bundle_sha256':digest(b),'receipt_sha256':digest(r)}
        return b,r,raw,m
    def test_exact_b3_replay_no_provider(self):
        b,r,raw,m=self.setup_replay();v=replay_bytes(EID,raw,m,b,r)
        self.assertEqual(v['B3_input_sha256'],m['output_sha256']);self.assertEqual(v['llm_calls'],0);self.assertEqual(v['dispositions'][0]['disposition'],'SUPPORTED')
    def test_mutated_b3_bytes_blocked(self):
        b,r,raw,m=self.setup_replay()
        with self.assertRaises(ValueError):replay_bytes(EID,raw+b' ',m,b,r)
    def test_changed_bundle_or_receipt_blocked(self):
        b,r,raw,m=self.setup_replay();r['omitted_original_count']+=1
        with self.assertRaises(ValueError):replay_bytes(EID,raw,m,b,r)
    def test_replay_wrong_context_not_published(self):
        b,r,raw,m=self.setup_replay();e=json.loads(raw);e['event_id']=OTHER;raw=dumps(e).encode();m['output_sha256']=hashlib.sha256(raw).hexdigest()
        self.assertFalse(replay_bytes(EID,raw,m,b,r)['published_report']['claims'])
    def test_incorrect_numeric_withheld_not_repaired(self):
        b,r,c=claim_fixture();c['payload']['result']=999;b,r,raw,m=self.setup_replay(c)
        v=replay_bytes(EID,raw,m,b,r);self.assertEqual(v['dispositions'][0]['disposition'],'INSUFFICIENT');self.assertFalse(v['published_report']['claims'])
    def test_q6_not_automatic_security_rule(self):
        b,r,c=claim_fixture();c.update(claim_type='security_interpretation',claim_text='Worth investigating.',question_ids=['Q6'],asset_ids=[],channel_ids=[])
        c['payload']={'conclusion':'review_required','basis_ids':c['evidence_ids']}
        self.assertEqual(C.verify_claim(c,b)['disposition'],'INSUFFICIENT')
    def test_strict_temporal_order_and_both_edges(self):
        from investigation.timeline_v2 import timeline
        b,r=bundle_fixture();c=next(x for x in timeline(b,r)['amendment_claims'] if x['claim_type']=='temporal_association');refresh_text(c,b)
        self.assertEqual(C.verify_claim(c,b)['disposition'],'SUPPORTED')
        bad=copy.deepcopy(c);bad['payload']['delta_seconds']+=1e-3
        self.assertEqual(C.verify_claim(bad,b)['disposition'],'INSUFFICIENT')
        bad=copy.deepcopy(c);bad['payload']['mapped_asset_id']='asset_'+'9'*16;bad['asset_ids']=['asset_'+'9'*16]
        p=bad['payload'];bad['claim_text']=C.render('temporal',earlier_id=p['earlier_id'],later_id=p['later_id'],relation=p['relation'],delta=p['delta_seconds'],scope=p['scope'],asset=p['mapped_asset_id'])
        v=C.verify_claim(bad,b);self.assertEqual(v['disposition'],'QUALIFIED');self.assertEqual(v['published_claim']['payload']['scope'],'episode_only');self.assertIsNone(v['published_claim']['payload']['mapped_asset_id'])
    def test_non_numeric_finite_commands(self):
        from investigation.timeline_v2 import timeline
        b,r=bundle_fixture()
        for c in timeline(b,r)['amendment_claims']:
            refresh_text(c,b);self.assertEqual(C.verify_claim(c,b)['disposition'],'SUPPORTED')

class RunnerIsolationTests(unittest.TestCase):
    def test_evaluation_denied_before_read_or_transport(self):
        e=load(ROOT/'configs/investigation_events.v1.json')['evaluation'][0]
        fake=FakeTransport()
        with self.assertRaises(PermissionError):generate(e,'B1',1,'fixture',fake)
        self.assertFalse(fake.requests)
        b,r,c=claim_fixture();b['scope']['event_id']=e
        with self.assertRaises(PermissionError):C.canonical_numeric_fact(c,b)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(PermissionError):read_bundle(e,'N',Path(tmp)/'log.jsonl')
            self.assertIsNotNone(verify_access_log(Path(tmp)/'log.jsonl'))
    def test_live_model_approval_gate(self):
        self.assertTrue(approved_configuration(OpenAITransport())[0]['live_api_enabled'])
    def test_plan_has_no_evaluation_or_new_B4_generation(self):
        p=plan();self.assertEqual(len(p),16*5*3);self.assertEqual(sum(x['action']=='generation' for x in p),144)
        self.assertTrue(all(x['event_id'] in development_ids() for x in p))
    def test_transport_retry_identical_body_logs_all(self):
        fake=FakeTransport([(503,{},b'failure')])
        with tempfile.TemporaryDirectory() as tmp:
            m=generate(EID,'B1',1,'fixture',fake,Path(tmp),sleep=lambda _:None)
            self.assertEqual(m['status'],'DELIVERED');self.assertEqual(len(m['attempts']),2);self.assertEqual(fake.requests[0],fake.requests[1])
            self.assertTrue((Path(tmp)/'fixture'/EID/'B1'/'rep-1'/'attempt-1'/'response.raw').exists())
    def test_timeout_retry_bounded(self):
        fake=FakeTransport([TimeoutError('timeout')]*3)
        with tempfile.TemporaryDirectory() as tmp:
            m=generate(EID,'B2',1,'fixture',fake,Path(tmp),sleep=lambda _:None)
            self.assertEqual(len(m['attempts']),3);self.assertEqual(m['status'],'FAILED_NO_VALID_DELIVERY')
    def test_bad_answer_missing_citations_not_retried(self):
        bad=output_fixture();bad['claims']=[{'claim_id':'c_1','claim_type':'electrical_change','payload':{'result':999},'evidence_ids':[]}]
        fake=FakeTransport([(200,{},json.dumps(provider_output(bad)).encode())])
        with tempfile.TemporaryDirectory() as tmp:
            m=generate(EID,'B3',1,'fixture',fake,Path(tmp),sleep=lambda _:None)
            self.assertEqual(m['status'],'DELIVERED_SCHEMA_INVALID');self.assertEqual(len(fake.requests),1)
    def test_malformed_delivery_can_retry(self):
        malformed=provider_output({});malformed['output'][0]['content'][0]['text']='not-json'
        fake=FakeTransport([(200,{},json.dumps(malformed).encode())])
        with tempfile.TemporaryDirectory() as tmp:
            m=generate(EID,'B1',1,'fixture',fake,Path(tmp),sleep=lambda _:None);self.assertEqual(len(fake.requests),2)
    def test_truncation_refusal_auth_not_retried(self):
        trunc=provider_output({},'incomplete');refusal=provider_output({});refusal['output'][0]['content']=[{'type':'refusal','refusal':'refused'}]
        for reply in [(200,{},json.dumps(trunc).encode()),(200,{},json.dumps(refusal).encode()),(401,{},b'bad auth')]:
            fake=FakeTransport([reply])
            with tempfile.TemporaryDirectory() as tmp:
                m=generate(EID,'B3',1,'fixture',fake,Path(tmp),sleep=lambda _:None);self.assertEqual(len(fake.requests),1)
    def test_all_repetitions_retained_create_once(self):
        fake=FakeTransport()
        with tempfile.TemporaryDirectory() as tmp:
            for rep in (1,2,3):generate(EID,'B2',rep,'fixture',fake,Path(tmp),sleep=lambda _:None)
            self.assertEqual(len(list((Path(tmp)/'fixture'/EID/'B2').glob('rep-*/completed.json'))),3)
            with self.assertRaises(FileExistsError):generate(EID,'B2',1,'fixture',fake,Path(tmp),sleep=lambda _:None)
    def test_over_budget_never_trims_or_calls_provider(self):
        fake=FakeTransport();model,budget,_=approved_configuration(fake)
        b,r=bundle_fixture();budget['fixed_evidence_tokens']=1
        before=digest(b)
        with self.assertRaises(ValueError):build_request(EID,'B3',b,model,budget)
        self.assertEqual(digest(b),before);self.assertFalse(fake.requests)
    def test_B4_generation_request_rejected(self):
        fake=FakeTransport();m,t,_=approved_configuration(fake);b,_=bundle_fixture()
        with self.assertRaises(ValueError):build_request(EID,'B4',b,m,t)
    def test_prompt_controlled_differences_and_hashes(self):
        common=(ROOT/'prompts/investigation-v1-r4/common.v1.txt').read_text();manifest=load(ROOT/'prompts/investigation-v1-r4/manifest.v1.json')
        for b,ref in manifest['prompts'].items():self.assertEqual(file_hash(ROOT/ref['path']),ref['sha256']);self.assertTrue((ROOT/ref['path']).read_text().startswith(common))
        b1=(ROOT/manifest['prompts']['B1']['path']).read_text();b2=(ROOT/manifest['prompts']['B2']['path']).read_text();self.assertEqual(b1.replace('Evidence view: N.','Evidence view: EN.').replace('evidence_view to "N"','evidence_view to "EN"'),b2)
    def test_token_audit_is_only_fixed_development_bundles(self):
        a=load(ROOT/'results/investigation-development-v1/token_budget_audit.json')
        self.assertEqual(len(a['rows']),32);self.assertEqual({r['event_id'] for r in a['rows']},set(development_ids()));self.assertEqual(a['proposed_fixed_evidence_tokens'],max(r['tokens'] for r in a['rows']))
        self.assertEqual(a['evaluation_events_accessed'],0)


def fixture_contract(l):
    return {'event_id':l['event_id'],'view':'N' if l['baseline']=='B1' else 'EN','gold':copy.deepcopy(l['gold'])}

def ledger_fixture(baseline='B3'):
    return {'event_id':EID,'baseline':baseline,'repetition':1,'output_sha256':'fixture-hash','review_status':'HUMAN_REVIEWED','reviewer_id':'R1','reviewed_at':'fixture',
    'gold':[{'gold_id':'g1','canonical_gold_id':'G1','kind':'positive','view_eligible':True},{'gold_id':'g1_alias','canonical_gold_id':'G1','kind':'positive','view_eligible':True},{'gold_id':'g2','canonical_gold_id':'G2','kind':'positive','view_eligible':False},{'gold_id':'h1','canonical_gold_id':'H1','kind':'guardrail','view_eligible':True}],
    'assertions':[{'assertion_id':'a1','substantive':True,'supported':True,'cited_complete_support':True,'security_interpretation':False,'matched_gold_ids':['g1'],'proposition_fingerprint':'same supported numeric proposition','duplicate_of':None,'citations':[{'evidence_id':'e1','valid':True},{'evidence_id':'e1','valid':True}]}],
    'questions':[{'question_id':f'Q{i}','coverage_minimum_met':i==2,'full_view_decision_correct':True,'retrieved_action_correct':True} for i in range(1,8)],
    'verifier_input_units':[{'unit_id':'u1','expected_disposition':'SUPPORTED','actual_disposition':'SUPPORTED','disposition_correct':True,'content_and_reason_correct':True,'duplicate_of':None,'proposition_fingerprint':'p1'}],
    'opportunity_actions':[{'canonical_gold_id':g,'addressed':g!='G2','correct_action_scope_reason':g!='G2'} for g in ('G1','G2','H1')]}

class MetricTests(unittest.TestCase):
    def score(self,l):return score_reviewed_run(l,'fixture-hash',fixture_contract(l))['metrics']
    def test_denominators_alias_guardrail(self):
        m=self.score(ledger_fixture());self.assertEqual(m['gold_fact_recall']['denominator'],2);self.assertEqual(m['gold_fact_recall']['numerator'],1);self.assertEqual(m['view_conditional_recall']['denominator'],1);self.assertEqual(m['question_coverage']['denominator'],6);self.assertEqual(m['sufficiency_accuracy']['denominator'],7)
    def test_true_duplicate_once(self):
        l=ledger_fixture();a=copy.deepcopy(l['assertions'][0]);a.update(assertion_id='a2',duplicate_of='a1',duplicate_rationale='same full proposition and support');l['assertions'].append(a)
        m=self.score(l);self.assertEqual(m['supported_claim_precision']['denominator'],1);self.assertEqual(m['citation_validity']['denominator'],1)
    def test_correct_and_incorrect_variants_not_collapsed(self):
        l=ledger_fixture();a=copy.deepcopy(l['assertions'][0]);a.update(assertion_id='a2',supported=False,cited_complete_support=False,matched_gold_ids=[],duplicate_of='a1',duplicate_rationale='wrong');l['assertions'].append(a)
        with self.assertRaises(ValueError):self.score(l)
        a['duplicate_of']=None;m=self.score(l);self.assertEqual(m['supported_claim_precision']['value'],.5);self.assertEqual(m['unsupported_claim_rate']['value'],.5)
    def test_withhold_excluded_strong_guardrail_included(self):
        l=ledger_fixture();a=copy.deepcopy(l['assertions'][0]);a.update(assertion_id='a2',substantive=False,matched_gold_ids=[],cited_complete_support=False,citations=[]);l['assertions'].append(a)
        self.assertEqual(self.score(l)['supported_claim_precision']['denominator'],1)
        a.update(substantive=True,supported=False,security_interpretation=True)
        self.assertEqual(self.score(l)['supported_claim_precision']['denominator'],2)
    def test_pending_not_silently_scored(self):
        l=ledger_fixture();l['assertions'][0]['supported']=None
        with self.assertRaises(PendingReview):self.score(l)
    def test_hash_bound_review(self):
        with self.assertRaises(ValueError):score_reviewed_run(ledger_fixture(),'different',fixture_contract(ledger_fixture()))
    def test_one_assertion_no_multiple_gold_credit(self):
        l=ledger_fixture();l['gold'][2]['view_eligible']=True;l['assertions'][0]['matched_gold_ids']=['g1','g2']
        with self.assertRaises(ValueError):self.score(l)
    def test_precision_can_credit_non_gold(self):
        l=ledger_fixture();l['assertions'][0]['matched_gold_ids']=[];m=self.score(l);self.assertEqual(m['gold_fact_recall']['value'],0);self.assertEqual(m['supported_claim_precision']['value'],1)
    def test_empty_output_is_NA_not_perfect(self):
        l=ledger_fixture();l['assertions']=[];m=self.score(l);self.assertIsNone(m['supported_claim_precision']['value']);self.assertIsNone(m['citation_validity']['value']);self.assertEqual(m['gold_fact_recall']['value'],0)
    def test_joint_sufficiency_components(self):
        l=ledger_fixture();l['questions'][0]['retrieved_action_correct']=False;m=self.score(l);self.assertEqual(m['sufficiency_accuracy']['numerator'],6);self.assertEqual(m['full_view_decision_accuracy']['numerator'],7)
    def test_verifier_oracle_and_fixed_actions(self):
        l=ledger_fixture('B4');m=self.score(l);self.assertEqual(m['verifier_disposition_accuracy']['value'],1);self.assertEqual(m['fixed_opportunity_action_accuracy']['numerator'],2)
        l['opportunity_actions'][1]['correct_action_scope_reason']=True
        with self.assertRaises(ValueError):self.score(l)
    def test_failure_fixed_denominator_zero(self):
        f=failure_scores(EID,'B1',1,30,5);self.assertEqual(f['metrics']['gold_fact_recall']['value'],0);self.assertIsNone(f['metrics']['supported_claim_precision']['value'])

class StatisticsTests(unittest.TestCase):
    def cells(self):
        return [{'event_id':e,'baseline':b,'repetition':r,'metrics':{'metric':{'numerator':n,'denominator':d,'value':n/d}}} for e,n,d in [(EID,1,1),(OTHER,0,100)] for b in ('B0','B1','B2','B3','B4') for r in (1,2,3)]
    def test_event_macro_not_pooled_micro(self):
        x=aggregate(self.cells(),'metric',{EID:'s',OTHER:'s'});self.assertEqual(x['macro']['B1']['estimate'],.5);self.assertAlmostEqual(x['micro_diagnostic']['B1']['value'],1/101)
    def test_missing_repetition_blocked(self):
        with self.assertRaises(ValueError):aggregate(self.cells()[:-1],'metric',{EID:'s',OTHER:'s'})
    def test_fixed_seed_repeatable_and_paired(self):
        a=aggregate(self.cells(),'metric',{EID:'s',OTHER:'s'});b=aggregate(self.cells(),'metric',{EID:'s',OTHER:'s'});self.assertEqual(a,b)
        self.assertEqual(a['paired_contrasts']['B1_vs_B2']['CI95'],[0,0]);self.assertEqual(a['bootstrap_resamples'],2000)
    def test_scenario_strata_and_singletons(self):
        a=aggregate(self.cells(),'metric',{EID:'s1',OTHER:'s2'});self.assertEqual(a['macro']['B1']['CI95'],[.5,.5]);self.assertEqual(len(a['macro']['B1']['singleton_strata']),2)
    def test_missing_strata_never_guessed(self):
        with self.assertRaises(ValueError):aggregate(self.cells(),'metric')
    def test_evaluation_cells_forbidden(self):
        cells=self.cells();cells[0]['event_id']=load(ROOT/'configs/investigation_events.v1.json')['evaluation'][0]
        with self.assertRaises(PermissionError):aggregate(cells,'metric',{})

if __name__=='__main__':unittest.main()

class IntegratedPilotTests(unittest.TestCase):
    def test_eight_sealed_pairs_support_projection_without_gold_mutation(self):
        import gzip
        from retrieval.investigation_retriever_v2 import bundle_for
        manifest_path=ROOT/'annotations/gold/pilot-v1/manifest.json';before=file_hash(manifest_path)
        manifest=load(manifest_path);n=0
        for event in manifest['events']:
            ap=ROOT/event['annotation']['snapshot_path'];ah=file_hash(ap);annotation=load(ap)
            ep=ROOT/event['source_evidence_hashes']['EN/eligible.json.gz']['snapshot_path']
            public=json.loads(gzip.decompress(ep.read_bytes()));idx={r['evidence_id']:r for r in public['records']}
            for gold in annotation['facts']:
                if gold['claim_type']!='electrical_change':continue
                k=gold['key_identity'];b=bundle_for(public,[idx[k['before_id']],idx[k['after_id']]])
                # A manufactured conformance fixture, NOT an actual B0/model recovery result.
                c=C.numeric_claim(b,k['before_id'],k['after_id'])
                self.assertTrue(C.matches_gold(c,b,gold));c['claim_type']='electrical_change';self.assertTrue(C.matches_gold(c,b,gold))
                n+=1
            self.assertEqual(file_hash(ap),ah);self.assertEqual(file_hash(ROOT/event['annotation']['original_path']),event['annotation']['sha256'])
        self.assertEqual(n,8);self.assertEqual(file_hash(manifest_path),before)
    def test_complete_B0_adapter_retains_raw_native_mapping(self):
        from investigation.timeline_v2 import timeline
        from investigation_dryrun.adapter import adapt_b0
        b,r=bundle_fixture();raw=timeline(b,r);h=digest(raw);adapted=adapt_b0(raw,b,r)
        self.assertEqual(digest(raw),h);self.assertTrue(adapted['facts'])
        self.assertTrue(any(x['representation']=='approved_v3_single_observation_mapping' for x in adapted['facts']))
        bad=copy.deepcopy(raw);bad['boundary']='The command caused the change.'
        with self.assertRaises(ValueError):adapt_b0(bad,b,r)
    def test_non_numeric_value_network_gap_ack_support(self):
        from investigation_dryrun.claims import typed_support,verify_claim
        b,r=bundle_fixture();idx={x['evidence_id']:x for x in b['entries']}
        base={'claim_id':'c_1','question_ids':['Q1'],'claim_type':'network_activity','claim_text':'pending','support_assertion':'asserted','evidence_ids':[],'asset_ids':[],'channel_ids':[],'endpoint_ids':[]}
        p=next(x for x in b['entries'] if x['source_type']=='packet')
        examples=[('network_activity',{'record_id':p['evidence_id'],'activity':'packet_observed','time':p['observation_time']}),('acknowledgement_observed',{'record_id':p['evidence_id'],'kind':'tcp_ack_bit','time':p['observation_time']})]
        for kind,payload in examples:
            c={**base,'claim_type':kind,'payload':payload,'evidence_ids':[payload['record_id']]};refresh_text(c,b);self.assertEqual(verify_claim(c,b)['disposition'],'SUPPORTED')
        e=next(x for x in b['entries'] if x['source_type']=='process')
        c={**base,'claim_type':'reported_value','question_ids':['Q2'],'asset_ids':[e['asset_id']],'channel_ids':[e['fields']['channel_id']],'evidence_ids':[e['evidence_id']],'payload':{'record_id':e['evidence_id'],'value':e['value'],'unit':e['unit'],'time':e['observation_time']}};refresh_text(c,b);self.assertEqual(verify_claim(c,b)['disposition'],'SUPPORTED')
        gap=next(x for x in b['entries'] if x['source_type']=='derived' and x['fields']['kind']=='communication_gap');f=gap['fields']
        c={**base,'claim_type':'communication_gap','evidence_ids':[gap['evidence_id']]+gap['parent_ids'],'payload':{'coverage_id':gap['evidence_id'],'left_id':f['left_id'],'right_id':f['right_id'],'start':f['start'],'end':f['end'],'duration_seconds':f['duration_seconds'],'population':'observed_tcp_2404_packets'}};refresh_text(c,b);self.assertEqual(verify_claim(c,b)['disposition'],'SUPPORTED')

class FinalConformanceTests(unittest.TestCase):
    def test_B4_only_metric_aggregation(self):
        cells=[{'event_id':EID,'baseline':'B4','repetition':r,'metrics':{'verifier_disposition_accuracy':{'numerator':1,'denominator':2,'value':.5}}} for r in (1,2,3)]
        result=aggregate(cells,'verifier_disposition_accuracy',{EID:'s'})
        self.assertEqual(set(result['macro']),{'B4'});self.assertEqual(result['paired_contrasts'],{})
    def test_scope_gate_prevents_false_insufficiency_positive(self):
        b,r,c=claim_fixture();c['support_assertion']='insufficient'
        self.assertEqual(C.verify_claim(c,b)['disposition'],'INSUFFICIENT')
    def test_changed_development_file_binding_rejected(self):
        import investigation_dryrun.custody as custody
        original=custody.file_hash
        def altered(path):return 'bad' if str(path).endswith('/retrieved.json') else original(path)
        with tempfile.TemporaryDirectory() as tmp,patch.object(custody,'file_hash',side_effect=altered):
            with self.assertRaises(ValueError):read_bundle(EID,'N',Path(tmp)/'log')
    def test_evaluation_bootstrap_seed_is_not_provider_seed(self):
        model=load(ROOT/'configs/investigation-dev-v1/model.candidate.json');stat=load(ROOT/'configs/investigation-dev-v1/statistics.json')
        self.assertIsNone(model['seed']);self.assertFalse(model['seed_supported_by_selected_endpoint']);self.assertEqual(stat['bootstrap']['seed'],20270922)

class B0AggregationTests(unittest.TestCase):
    def test_B0_shared_repetition_reference_not_tripled_in_micro_counts(self):
        cells=StatisticsTests().cells();r=aggregate(cells,'metric',{EID:'s',OTHER:'s'})
        self.assertEqual(r['micro_diagnostic']['B0']['denominator'],101)
        self.assertEqual(r['micro_diagnostic']['B1']['denominator'],303)

class DenominatorBindingTests(unittest.TestCase):
    def test_reviewer_cannot_expand_gold_denominator(self):
        ledger=ledger_fixture();contract=fixture_contract(ledger);ledger['gold'].append({'gold_id':'new','canonical_gold_id':'new','kind':'positive','view_eligible':True})
        with self.assertRaises(ValueError):score_reviewed_run(ledger,'fixture-hash',contract)
    def test_existing_pilot_contract_only(self):
        from investigation_dryrun.gold_contract import pilot_contract
        c=pilot_contract(EID,'EN');self.assertEqual(sum(g['kind']=='positive' for g in c['gold']),8)
        with self.assertRaises(ValueError):pilot_contract(OTHER,'EN')
    def test_malformed_claim_ids_are_retained_schema_failure_not_retry(self):
        bad=output_fixture();bad['claims']=[{'claim_id':[]}]
        fake=FakeTransport([(200,{},json.dumps(provider_output(bad)).encode())])
        with tempfile.TemporaryDirectory() as tmp:
            m=generate(EID,'B3',1,'fixture',fake,Path(tmp),sleep=lambda _:None)
            self.assertEqual(m['status'],'DELIVERED_SCHEMA_INVALID');self.assertEqual(len(fake.requests),1)
