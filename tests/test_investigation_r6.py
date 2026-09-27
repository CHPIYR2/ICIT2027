"""Necessary r6 identity/gate tests; finite fixtures, no model outputs used for tuning."""
import copy,json,tempfile,unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
from investigation_dryrun.common import ROOT,load,digest
from investigation_r6 import candidate as c
from investigation_r6.policy import rate_feasibility,scheduling_gate,capacity_action,assess,usage_components,calculable_cost,exercise_sequence
from investigation_r5.transport import FixtureTransport
from test_investigation_r5 import output,envelope

class R6Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent=load(c.PARENT_PLAN);cls.plan=load(c.OUT/'validation_manifest.json')
    def test_config_distinguishes_input_output(self):
        m,b=c.configuration()
        self.assertEqual(m['model_max_output_tokens'],24576)
        self.assertEqual(b['evidence_input_token_safety_ceiling'],16384)
        self.assertEqual(b['prompt_plus_evidence_input_token_ceiling'],21152)
        self.assertNotIn('max_output_tokens',m)
    def test_all64_same_cap_and_parent_identity(self):
        self.assertEqual(c.validate_manifest(self.plan)['positions'],64)
        self.assertEqual(self.plan['counts'],{'G1-E':12,'G1-EN':21,'G1-N':12,'G0':19})
    def test_completed_r5_positions_not_reused(self):
        old=load(ROOT/'results/investigation-r5-validation/execution.finished.json')
        self.assertEqual(len(set(old['finished_positions']) & {p['position_id'] for p in self.plan['positions']}),18)
        self.assertTrue(all(not p['historical_output_reused'] for p in self.plan['positions']))
    def test_18_actual_and_46_predeclared_comparisons(self):
        report=load(c.OUT/'request_equivalence.json')
        self.assertEqual((report['actually_sent_r5_comparisons'],report['predeclared_unsent_r5_comparisons']),(18,46))
    def test_rejects_scientific_diff(self):
        old,_,_=c.parent_request(self.parent['positions'][0]);new=copy.deepcopy(old);new['max_output_tokens']=24576
        for key,value in [('temperature',1),('instructions','changed'),('input','{}'),('model','different')]:
            changed=copy.deepcopy(new);changed[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):c.equivalence(old,changed)
    def test_rejects_schema_diff(self):
        old,_,_=c.parent_request(self.parent['positions'][0]);new=copy.deepcopy(old);new['max_output_tokens']=24576
        new['text']['format']['schema']['properties']['claims']['maxItems']=32
        with self.assertRaises(ValueError):c.equivalence(old,new)
    def test_plan_rejects_repetition_change(self):
        plan=copy.deepcopy(self.plan);plan['positions'][0]['repetition']=4
        with self.assertRaises(ValueError):c.validate_manifest(plan)
    def test_evaluation_denied_before_bundle_access(self):
        p=copy.deepcopy(self.parent['positions'][0]);p['event_id']='ev_'+'f'*20
        with patch.object(c,'read_bundle',side_effect=AssertionError('Must not read')) as reader:
            with self.assertRaises((ValueError,PermissionError)):c.build_request(p)
            reader.assert_not_called()
    def test_no_live_entrypoint(self):
        with self.assertRaises(PermissionError):c.generate()
    def test_limit30000_historical_support_only(self):
        r=rate_feasibility({'x-ratelimit-limit-tokens':'30000'})
        self.assertIn('PENDING_LIVE_PREFLIGHT',r['status']);self.assertFalse(r['live_authorized'])
    def test_limit_below_cap_stops(self):
        self.assertTrue(rate_feasibility({'x-ratelimit-limit-tokens':'24000'})['status'].startswith('STOP'))
    def test_lower_project_limit_stops(self):
        self.assertTrue(rate_feasibility({'x-ratelimit-limit-tokens':'30000','x-ratelimit-limit-project-tokens':'20000'})['status'].startswith('STOP'))
    def test_missing_header_requires_confirmation(self):
        self.assertEqual(rate_feasibility({})['status'],'REQUIRES_PREFLIGHT_CONFIRMATION')
    def test_unparseable_header_requires_confirmation(self):
        self.assertEqual(rate_feasibility({'x-ratelimit-limit-tokens':'unknown'})['status'],'REQUIRES_PREFLIGHT_CONFIRMATION')
    def test_request_estimate_cannot_be_ignored(self):
        self.assertTrue(rate_feasibility({'x-ratelimit-limit-tokens':'30000'},estimated_request_tokens=31000)['status'].startswith('STOP'))
    def test_base_global_spacing(self):
        self.assertEqual(scheduling_gate({'x-ratelimit-limit-tokens':'30000'},20,0)['wait_seconds'],40)
    def test_retry_after_and_longer_project_reset(self):
        h={'x-ratelimit-limit-tokens':'30000','retry-after':'90','x-ratelimit-reset-project-tokens':'2m3s'}
        self.assertEqual(scheduling_gate(h,30,10)['wait_seconds'],113)
    def test_low_remaining_without_reset_blocks(self):
        r=scheduling_gate({'x-ratelimit-limit-tokens':'30000','x-ratelimit-remaining-tokens':'1'},90,20)
        self.assertEqual(r['status'],'REQUIRES_PREFLIGHT_CONFIRMATION')
    def test_low_remaining_waits_for_reset(self):
        h={'x-ratelimit-limit-tokens':'30000','x-ratelimit-remaining-tokens':'23008','x-ratelimit-reset-tokens':'13.984s'}
        self.assertAlmostEqual(scheduling_gate(h,70,0)['wait_seconds'],13.984)
    def test_every_request_rechecks_changed_limit(self):
        self.assertEqual(scheduling_gate({'x-ratelimit-limit-tokens':'30000'},70,70)['status'],'READY_SUBJECT_TO_AUTHORIZATION')
        self.assertTrue(scheduling_gate({'x-ratelimit-limit-tokens':'20000'},70,70)['status'].startswith('STOP'))
    def test_cap_requires_exact_status_and_reason(self):
        self.assertTrue(capacity_action({'status':'incomplete','incomplete_details':{'reason':'max_output_tokens'}})['capacity_failed'])
        self.assertFalse(capacity_action({'status':'completed','incomplete_details':{'reason':'max_output_tokens'}})['capacity_failed'])
        self.assertFalse(capacity_action({'status':'incomplete','incomplete_details':{'reason':'content_filter'}})['capacity_failed'])
    def test_cap_sequence_stops_new_positions_without_retry(self):
        q,_,_,_=c.build_request(self.parent['positions'][0]);fixture=FixtureTransport([envelope(status='incomplete',reason='max_output_tokens'),envelope()])
        with tempfile.TemporaryDirectory() as td:r=exercise_sequence([q,q],fixture,Path(td))
        self.assertEqual(len(fixture.requests),1);self.assertEqual(r['not_scheduled'],1)
        self.assertFalse(r['positions'][0]['attempts'][0]['will_retry'])
    def test_retry_max_three_unchanged(self):
        q,_,_,_=c.build_request(self.parent['positions'][0]);fixture=FixtureTransport([TimeoutError()]*3)
        with tempfile.TemporaryDirectory() as td:r=exercise_sequence([q],fixture,Path(td))
        self.assertEqual(len(fixture.requests),3);self.assertFalse(r['positions'][0]['attempts'][-1]['will_retry'])
    def test_no_quality_retry(self):
        q,_,_,_=c.build_request(self.parent['positions'][0]);fixture=FixtureTransport([envelope(),envelope()])
        with tempfile.TemporaryDirectory() as td:r=exercise_sequence([q],fixture,Path(td))
        self.assertEqual(len(fixture.requests),1)
    def test_unknown_usage_not_zero(self):
        self.assertIsNone(usage_components(None)['output_tokens'])
        self.assertIsNone(calculable_cost(None,{}))
    def test_cost_actual_not_configured_max(self):
        usage={'input_tokens':100,'input_tokens_details':{'cached_tokens':40},'output_tokens':10}
        self.assertEqual(usage_components(usage)['uncached_input_tokens'],60)
        self.assertEqual(calculable_cost(usage,{'uncached_input_tokens':2,'cached_input_tokens':.5,'output_tokens':8}),Decimal('0.00022'))
    def test_full_matrix_acceptance_requires_all64(self):
        rows=[{'position_id':p['position_id'],'status':'DELIVERED','request_diff_valid':True,'schema_and_visibility_valid':True,'output_sha256':'synthetic-bound-hash'} for p in self.plan['positions']]
        replays=[{'position_id':p['position_id'],'status':'REPLAYED','source_output_sha256':'synthetic-bound-hash','llm_calls':0} for p in self.plan['positions'] if p['cell_id']=='G1-EN']
        self.assertEqual(assess(self.plan,rows,True,replays)['status'],'PASS_DEVELOPMENT_CAP_ONLY_NOT_FREEZE')
        self.assertEqual(assess(self.plan,rows,True)['status'],'INCONCLUSIVE_REPLAY_PENDING')
        invalid=copy.deepcopy(replays);invalid[0]['source_output_sha256']='different'
        self.assertEqual(assess(self.plan,rows,True,invalid)['status'],'FAIL_REPLAY_CONFORMANCE')
        self.assertIn('INCONCLUSIVE',assess(self.plan,rows[:-1],True)['status'])
        rows[0].update(status='PROVIDER_INCOMPLETE',termination_reason='max_output_tokens')
        self.assertEqual(assess(self.plan,rows,True)['status'],'FAIL_OUTPUT_CAP_STOP_AUTHOR_REVIEW')
    def test_schema_failure_recorded_as_conformance_not_capacity(self):
        p=next(p for p in self.plan['positions'] if p['cell_id']=='G0')
        row={'position_id':p['position_id'],'status':'DELIVERED_SCHEMA_OR_VISIBILITY_INVALID','schema_and_visibility_valid':False,'request_diff_valid':True}
        r=assess(self.plan,[row],True);self.assertEqual(r['status'],'FAIL_CONFORMANCE');self.assertFalse(r['truncated'])
    def test_exact_replay_uses_unchanged_engine_no_model(self):
        p=next(p for p in self.parent['positions'] if p['cell_id']=='G1-EN');q,b,r,_=c.build_request(p)
        x=output();x['event_id']=p['event_id'];raw=json.dumps(x,indent=3).encode()
        import hashlib
        fixture_manifest={**p,'run_id':'offline_fixture','output_sha256':hashlib.sha256(raw).hexdigest()}
        with patch.object(c,'generate',side_effect=AssertionError('No model calls')):
            v=c.replay_bytes(p['event_id'],raw,fixture_manifest,b,r)
        self.assertEqual(v['source_output_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(v['llm_calls'],0)
        with self.assertRaises(ValueError):c.replay_bytes(p['event_id'],raw+b' ',fixture_manifest,b,r)
    def test_all_historical_bindings_preserved(self):
        self.assertGreaterEqual(len(c.protected_references()),3216)
