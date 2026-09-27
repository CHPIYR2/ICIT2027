"""Execution-layer synthetic tests; no provider calls or scientific changes."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
from investigation_r5_live.adapter import Scheduler,reset_seconds,process_position,CaptureFailure
from investigation_dryrun.common import load
from test_investigation_r5 import envelope,output
PLAN=load(ROOT/'results/investigation-r5/validation_manifest.json')
class FakeClock:
 def __init__(self):self.t=100.;self.waits=[]
 def now(self):return self.t
 def sleep(self,n):self.waits.append(n);self.t+=n
class Fake:
 def __init__(self,replies):self.replies=list(replies);self.requests=[]
 def send(self,q,cid):
  self.requests.append(copy.deepcopy(q));item=self.replies.pop(0)
  if isinstance(item,Exception):raise item
  return item

def provider(p,**kwargs):
 x=output(p['view'],p['citation_mode']);x['event_id']=p['event_id'];return envelope(x,**kwargs)
class LiveTests(unittest.TestCase):
 def test_global_spacing_between_positions(self):
  c=FakeClock();s=Scheduler(c.now,c.sleep,c.now);s.start();s.observe({});s.start();self.assertGreaterEqual(c.t,160)
 def test_retry_after_and_resets(self):
  c=FakeClock();s=Scheduler(c.now,c.sleep,c.now);s.start();s.observe({'retry-after':'90','x-ratelimit-reset-tokens':'2m3s'});s.start();self.assertEqual(c.t,223)
 def test_duration_ms(self):self.assertEqual(reset_seconds('1m2.5s'),62.5);self.assertEqual(reset_seconds('500ms'),.5)
 def test_bad_header_fails_closed(self):
  with self.assertRaises(ValueError):reset_seconds('unrecognized')
 def run_position(self,p,replies):
  c=FakeClock();s=Scheduler(c.now,c.sleep,c.now);f=Fake(replies)
  with tempfile.TemporaryDirectory() as td:
   m=process_position(p,Path(td)/'cell',f,s,lambda:None)
   self.assertEqual(len(list((Path(td)/'cell').glob('attempt-*/attempt.json'))),len(m['attempts']))
   v=load(Path(td)/'cell/V1-EN.replay.json') if p['cell_id']=='G1-EN' else None
  return m,f,v
 def test_normal_delivery_and_replay_identity(self):
  p=next(x for x in PLAN['positions'] if x['cell_id']=='G1-EN');m,f,v=self.run_position(p,[provider(p)])
  self.assertEqual(m['status'],'DELIVERED');self.assertEqual(v['status'],'REPLAYED');self.assertEqual(v['source_output_sha256'],m['output_sha256']);self.assertEqual(v['llm_calls'],0)
 def test_cap_hard_stop_not_retry(self):
  p=PLAN['positions'][0];m,f,v=self.run_position(p,[provider(p,status='incomplete',reason='max_output_tokens')]);self.assertTrue(m['capacity_hard_stop']);self.assertEqual(len(f.requests),1);self.assertFalse(m['attempts'][0]['will_retry'])
 def test_reset_unknown_then_success_same_request(self):
  p=PLAN['positions'][0];m,f,v=self.run_position(p,[CaptureFailure(ConnectionResetError()),provider(p)]);self.assertEqual(len(f.requests),2);self.assertEqual(f.requests[0],f.requests[1]);self.assertEqual(m['attempts'][0]['delivery_status'],'UNKNOWN');self.assertIsNone(m['attempts'][0]['usage'])
 def test_429_retry_metadata(self):
  p=PLAN['positions'][0];m,f,v=self.run_position(p,[(429,{'retry-after':'80','x-ratelimit-reset-tokens':'81s'},b'{}'),provider(p)]);self.assertEqual(m['status'],'DELIVERED');self.assertEqual(len(f.requests),2);self.assertEqual(m['attempts'][0]['response_headers']['retry-after'],'80')
 def test_visibility_error_retained_no_retry(self):
  p=PLAN['positions'][0];x=output(p['view'],p['citation_mode']);x['event_id']='ev_'+'9'*20;m,f,v=self.run_position(p,[envelope(x)]);self.assertEqual(len(f.requests),1);self.assertEqual(m['status'],'DELIVERED_SCHEMA_OR_VISIBILITY_INVALID')
 def test_attempts_maximum_three(self):
  p=PLAN['positions'][0];m,f,v=self.run_position(p,[CaptureFailure(TimeoutError())]*3);self.assertEqual(len(f.requests),3);self.assertEqual(m['status'],'FAILED_NO_VALID_DELIVERY')
 def test_implementation_failure_stops(self):
  p=PLAN['positions'][0];m,f,v=self.run_position(p,[CaptureFailure(ValueError())]);self.assertEqual(m['status'],'IMPLEMENTATION_FAILURE');self.assertTrue(m['fatal_stop']);self.assertEqual(len(f.requests),1)
 def test_wrong_request_manifest_no_transport(self):
  p=copy.deepcopy(PLAN['positions'][0]);p['request_sha256']='bad';f=Fake([])
  with tempfile.TemporaryDirectory() as td:
   with self.assertRaises(AssertionError):process_position(p,Path(td)/'cell',f,Scheduler(),lambda:None)
  self.assertFalse(f.requests)
