"""Run development/synthetic regression with network disabled; write only r5 test artifacts."""
import io,sys,unittest,json,tempfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
from investigation_dryrun.common import create_json,binding,utc
patterns=['test_investigation_r5.py','test_investigation_dryrun_regression.py','test_investigation_dryrun_amendments.py','test_investigation_development.py','test_investigation_freeze_preparation.py','test_investigation_v2.py','test_investigation_transport_resume_v2.py','test_investigation_api_usage.py']
suite=unittest.TestSuite()
for p in patterns:suite.addTests(unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern=p,top_level_dir=str(ROOT/'tests')))
stream=io.StringIO()
with tempfile.TemporaryDirectory() as temp,patch('investigation_dryrun.runner.RUNS',Path(temp)/'r4-deny-test-only'),patch('investigation_dev.runner.RUNS',Path(temp)/'r3-deny-test-only'),patch('urllib.request.urlopen',side_effect=AssertionError('NETWORK FORBIDDEN IN OFFLINE TESTS')),patch('socket.create_connection',side_effect=AssertionError('NETWORK FORBIDDEN IN OFFLINE TESTS')):
 result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
out=ROOT/'results/investigation-r5';(out/'offline_tests.isolated.log').write_text(stream.getvalue())
r={'status':'PASS' if result.wasSuccessful() else 'FAIL','tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'created_at':utc(),'test_files':[binding(ROOT/'tests'/p) for p in patterns],'model_calls':0,'network_disabled_by_test_harness':True,'evaluation_evidence_gold_results_accessed':False,'research_outputs_generated':False,'fixtures':'synthetic only; existing sealed development pilot conformance retained','source_files':[binding(p) for p in sorted((ROOT/'src/investigation_r5').glob('*.py'))]}
create_json(out/'offline_test_results.isolated.json',r);print(json.dumps(r,indent=2));sys.exit(0 if result.wasSuccessful() else 1)
