"""Synthetic execution tests only; inherited request and verifier semantics unchanged."""
import copy,json,tempfile,unittest
from pathlib import Path
from investigation_dryrun.common import ROOT,load
from investigation_r6_live.adapter import RateAwareScheduler,classify_http_failure,process_position,CaptureFailure
from test_investigation_r5 import output,envelope
from test_investigation_r5_live import FakeClock,Fake
PLAN=load(ROOT/'results/investigation-r6/validation_manifest.json')

class R6LiveTests(unittest.TestCase):
    def scheduler(self):
        clock=FakeClock();return clock,RateAwareScheduler(clock.now,clock.sleep,clock.now,initial_limits={'x-ratelimit-limit-tokens':'30000'})
    def provider(self,p,**kw):
        x=output(p['view'],p['citation_mode']);x['event_id']=p['event_id'];return envelope(x,**kw)
    def run_position(self,p,replies):
        clock,scheduler=self.scheduler();fake=Fake(replies)
        with tempfile.TemporaryDirectory() as td:
            d=Path(td)/'p';m=process_position(p,d,fake,scheduler,lambda:None)
            v=load(d/'V1-EN.replay.json') if p['cell_id']=='G1-EN' else None
            self.assertEqual(len(list(d.glob('attempt-*/attempt.json'))),len(m['attempts']))
        return m,fake,v
    def test_same24576_normal_delivery(self):
        p=PLAN['positions'][0];m,f,_=self.run_position(p,[self.provider(p)])
        self.assertEqual(m['status'],'DELIVERED');self.assertEqual(f.requests[0]['max_output_tokens'],24576)
    def test_exact_replay_no_model_calls(self):
        p=next(p for p in PLAN['positions'] if p['cell_id']=='G1-EN');m,f,v=self.run_position(p,[self.provider(p)])
        self.assertEqual(v['source_output_sha256'],m['output_sha256']);self.assertEqual(v['llm_calls'],0);self.assertEqual(len(f.requests),1)
    def test_cap_hard_stop_no_retry(self):
        p=PLAN['positions'][0];m,f,_=self.run_position(p,[self.provider(p,status='incomplete',reason='max_output_tokens')])
        self.assertTrue(m['capacity_hard_stop']);self.assertFalse(m['attempts'][0]['will_retry']);self.assertEqual(len(f.requests),1)
    def test_other_incomplete_not_cap_not_retry(self):
        p=PLAN['positions'][0];m,f,_=self.run_position(p,[self.provider(p,status='incomplete',reason='content_filter')])
        self.assertFalse(m['capacity_hard_stop']);self.assertEqual(len(f.requests),1)
    def test_temporary429_wait_and_retry_same_request(self):
        p=PLAN['positions'][0]
        m,f,_=self.run_position(p,[(429,{'retry-after':'90','x-ratelimit-reset-tokens':'100s'},b'{"error":{"code":"rate_limit_exceeded","message":"Limit 30000 Used 15000 Requested 24576 tokens"}}'),self.provider(p)])
        self.assertEqual(m['status'],'DELIVERED');self.assertEqual(len(f.requests),2);self.assertEqual(f.requests[0],f.requests[1])
        self.assertGreaterEqual(m['attempts'][1]['start_monotonic']-m['attempts'][0]['start_monotonic'],100)
    def test_single_request_too_large_no_retry(self):
        p=PLAN['positions'][0];body=b'{"error":{"code":"rate_limit_exceeded","message":"Request too large on tokens per min (TPM): Limit 30000, Requested 31000"}}'
        m,f,_=self.run_position(p,[(429,{},body)])
        self.assertEqual(m['status'],'RATE_FEASIBILITY_BLOCKER');self.assertEqual(m['fatal_stop'],'SINGLE_REQUEST_EXCEEDS_RATE_LIMIT');self.assertEqual(len(f.requests),1)
    def test_explicit_demand_above_limit_is_not_temporary(self):
        self.assertEqual(classify_http_failure(429,{'error':{'message':'tokens per min Limit: 30,000 Requested: 31,000'}}),'SINGLE_REQUEST_EXCEEDS_RATE_LIMIT')
    def test_quota_no_retries(self):
        p=PLAN['positions'][0];m,f,_=self.run_position(p,[(429,{},b'{"error":{"code":"insufficient_quota"}}')])
        self.assertEqual(m['fatal_stop'],'ACCOUNT_ACTION_REQUIRED');self.assertEqual(len(f.requests),1)
    def test_lower_live_limit_stops_future_requests(self):
        p=PLAN['positions'][0];code,h,body=self.provider(p);h={'x-ratelimit-limit-tokens':'20000'}
        m,f,_=self.run_position(p,[(code,h,body)])
        self.assertEqual(m['fatal_stop'],'PROVIDER_TOKEN_LIMIT_BELOW_REQUEST_ALLOWANCE')
    def test_missing_headers_retains_known_limit_not_fabricated_headers(self):
        p=PLAN['positions'][0];m,f,_=self.run_position(p,[self.provider(p)])
        self.assertEqual(m['attempts'][0]['response_headers'],{});self.assertIsNone(m['fatal_stop'])
    def test_unknown_delivery_preserved_max_three(self):
        p=PLAN['positions'][0];m,f,_=self.run_position(p,[CaptureFailure(TimeoutError())]*3)
        self.assertEqual(len(f.requests),3);self.assertTrue(all(a['delivery_status']=='UNKNOWN' and a['usage'] is None for a in m['attempts']))
    def test_wrong_request_binding_before_send(self):
        p=copy.deepcopy(PLAN['positions'][0]);p['request_sha256']='bad';clock,s=self.scheduler();f=Fake([])
        with tempfile.TemporaryDirectory() as td,self.assertRaises(AssertionError):process_position(p,Path(td)/'p',f,s,lambda:None)
        self.assertFalse(f.requests)
    def test_schema_context_error_not_retry(self):
        p=PLAN['positions'][0];x=output(p['view'],p['citation_mode']);x['event_id']='ev_'+'9'*20
        m,f,_=self.run_position(p,[envelope(x)])
        self.assertEqual(m['status'],'DELIVERED_SCHEMA_OR_VISIBILITY_INVALID');self.assertEqual(len(f.requests),1)
    def test_global_start_spacing(self):
        clock,s=self.scheduler();s.start();s.observe({});s.start();self.assertGreaterEqual(clock.t,160)
    def test_unparseable_reset_stops(self):
        p=PLAN['positions'][0];code,h,body=self.provider(p)
        m,f,_=self.run_position(p,[(code,{'x-ratelimit-reset-tokens':'bad'},body)])
        self.assertEqual(m['fatal_stop'],'RATE_HEADER_PARSE_FAILURE')
    def test_execution_defect_not_retried(self):
        p=PLAN['positions'][0];m,f,_=self.run_position(p,[CaptureFailure(ValueError())])
        self.assertEqual(m['status'],'IMPLEMENTATION_FAILURE');self.assertEqual(len(f.requests),1)
