import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from test_investigation_dryrun_regression import EID,FakeTransport
from investigation_dryrun import runner
from investigation_dryrun.common import load,file_hash
from investigation_dryrun.transport_resume_v2 import continue_started

class OperatorStop(BaseException):pass
class ResumeTests(unittest.TestCase):
 def test_resume_preserves_attempts_and_identical_request(self):
  fake=FakeTransport([(429,{},b'{"error":{"code":"rate_limit_exceeded"}}')])
  with tempfile.TemporaryDirectory() as tmp:
   def stop(_):raise OperatorStop()
   with self.assertRaises(OperatorStop):runner.generate(EID,'B1',1,'fixture',fake,Path(tmp),sleep=stop)
   d=Path(tmp)/'fixture'/EID/'B1'/'rep-1';old=file_hash(d/'attempt-1/attempt.json');request=load(d/'request.json')
   continued=FakeTransport();m=continue_started(d,continued,sleep=lambda _:None)
   self.assertEqual(m['status'],'DELIVERED');self.assertEqual(len(m['attempts']),2);self.assertEqual(file_hash(d/'attempt-1/attempt.json'),old);self.assertEqual(continued.requests,[request])
 def test_remaining_retry_budget_not_reset(self):
  fake=FakeTransport([(429,{},b'limit')]*2)
  with tempfile.TemporaryDirectory() as tmp:
   sleeps=[]
   def stop(_):
    sleeps.append(1)
    if len(sleeps)==2:raise OperatorStop()
   with self.assertRaises(OperatorStop):runner.generate(EID,'B2',1,'fixture',fake,Path(tmp),sleep=stop)
   continued=FakeTransport([(429,{},b'limit')]);m=continue_started(Path(tmp)/'fixture'/EID/'B2'/'rep-1',continued,sleep=lambda _:None)
   self.assertEqual(len(m['attempts']),3);self.assertEqual(len(continued.requests),1);self.assertEqual(m['status'],'FAILED_NO_VALID_DELIVERY')

class UnknownInterruptedDeliveryTest(unittest.TestCase):
 def test_unknown_delivery_consumes_attempt_and_does_not_reset_budget(self):
  from investigation_dryrun.common import create_json
  from investigation_dryrun.transport_resume_v2 import continue_started
  fake=FakeTransport([(429,{},b'limit')])
  with tempfile.TemporaryDirectory() as tmp:
   def stop(_):raise OperatorStop()
   with self.assertRaises(OperatorStop):runner.generate(EID,'B1',1,'fixture',fake,Path(tmp),sleep=stop)
   d=Path(tmp)/'fixture'/EID/'B1'/'rep-1';p=d/'attempt-1/attempt.json';m=load(p)
   # Synthetic operator interruption: no response bytes or provider status known.
   m.pop('response_sha256');m['HTTP_status']=None;m['reason']='OPERATOR_TRANSPORT_INTERRUPTION_NO_RECOVERABLE_DELIVERY';p.write_text(__import__('json').dumps(m));(d/'attempt-1/response.raw').unlink()
   continued=FakeTransport();out=continue_started(d,continued,sleep=lambda _:None)
   self.assertEqual(out['status'],'DELIVERED');self.assertEqual([a['attempt'] for a in out['attempts']],[1,2]);self.assertIsNone(out['attempts'][0]['HTTP_status'])
