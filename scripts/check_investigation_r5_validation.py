"""Read-only integrity and isolated regression gate; write only new validation namespace."""
import io,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
from investigation_dryrun.common import load,file_hash,create_json,binding,utc
OUT=ROOT/'results/investigation-r5-validation'
INVENTORY_SHA='5336d8fe9d2f526c32f0f4f510d4a7264d432fcc30c7b8303176b2a838dc0e0b'
PLAN_SHA='79fba58a9708acd7a8db75e58a1311d7efb484e5a5e334f0fbe7a56bfecc7ee8'

def integrity():
 ip=ROOT/'configs/investigation_protocol.v1.freeze_inventory.r5.json';mp=ROOT/'results/investigation-r5/validation_manifest.json'
 assert file_hash(ip)==INVENTORY_SHA,'r5 inventory changed';assert file_hash(mp)==PLAN_SHA,'64-position manifest changed'
 refs=load(ip)['files']+load(ROOT/'results/investigation-r5/preservation.before.json')['files']
 for e in refs:assert file_hash(ROOT/e['path'])==e['sha256'],e['path']
 from investigation_r5.core import read_bundle,cell_spec,CONFIG
 from investigation_r5.runner import build_request
 from investigation_dryrun.common import digest
 model=load(CONFIG/'model.candidate.json');budget=load(CONFIG/'token_budget.candidate.json')
 assert model['exact_callable_model']=='gpt-4.1-2025-04-14' and model['temperature']==0 and model['max_output_tokens']==8192 and model['seed'] is None
 assert model['endpoint']=='https://api.openai.com/v1/responses' and budget['evidence_token_safety_ceiling']==16384
 plan=load(mp);assert len(plan['positions'])==64
 for p in plan['positions']:
  b,r=read_bundle(p['event_id'],p['view']);q=build_request(p['event_id'],p['cell_id'],b,r)
  assert digest(q)==p['request_sha256'] and digest(b)==p['bundle_sha256'] and digest(r)==p['receipt_sha256']
  assert cell_spec(p['cell_id'])['citation_mode']==p['citation_mode']
  if p['purpose']=='capacity_stress':
   old=load(ROOT/p['parent_request']['path']);old['max_output_tokens']=8192;assert q==old
 return {'status':'PASS','r5_inventory_files':2991,'r4_legacy_protected_files':2937,'manifest_sha256':PLAN_SHA,'all_64_request_identities':True,'model_calls':0}

def tests(phase,include_live=False):
 integrity()
 patterns=['test_investigation_r5.py','test_investigation_dryrun_regression.py','test_investigation_dryrun_amendments.py','test_investigation_development.py','test_investigation_freeze_preparation.py','test_investigation_v2.py','test_investigation_transport_resume_v2.py','test_investigation_api_usage.py']
 if include_live:patterns.append('test_investigation_r5_live.py')
 suite=unittest.TestSuite()
 for p in patterns:suite.addTests(unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern=p,top_level_dir=str(ROOT/'tests')))
 stream=io.StringIO()
 with tempfile.TemporaryDirectory() as temp,patch('investigation_dryrun.runner.RUNS',Path(temp)/'r4'),patch('investigation_dev.runner.RUNS',Path(temp)/'r3'),patch('urllib.request.urlopen',side_effect=AssertionError('NETWORK FORBIDDEN IN TESTS')),patch('socket.create_connection',side_effect=AssertionError('NETWORK FORBIDDEN IN TESTS')):
  r=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
 (OUT/f'{phase}.tests.log').write_text(stream.getvalue())
 report={'phase':phase,'status':'PASS' if r.wasSuccessful() else 'FAIL','tests_run':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),'skipped':len(r.skipped),'model_calls':0,'test_files':[binding(ROOT/'tests'/p) for p in patterns],'post_test_integrity':integrity(),'created_at':utc()}
 create_json(OUT/f'{phase}.tests.json',report)
 assert r.wasSuccessful(),'Pre/post test suite failed: STOP'
 return report
if __name__=='__main__':print(json.dumps(tests(sys.argv[1],len(sys.argv)>2),indent=2))
