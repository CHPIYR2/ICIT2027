"""Isolated local regression suite; never writes into r3/r4/r5 result roots."""
import io,json,os,socket,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
os.environ['TIKTOKEN_CACHE_DIR']=str(ROOT/'.cache/tiktoken')
def blocked(*a,**k):raise AssertionError('Offline tests: network forbidden')
socket.create_connection=blocked;socket.socket.connect=blocked
from investigation_r6.candidate import OUT,protected_references,validate_manifest
from investigation_dryrun.common import load,binding,create_json,utc

def run():
    protected_references();validate_manifest(load(OUT/'validation_manifest.json'))
    patterns=['test_investigation_r5.py','test_investigation_dryrun_regression.py','test_investigation_dryrun_amendments.py',
              'test_investigation_development.py','test_investigation_freeze_preparation.py','test_investigation_v2.py',
              'test_investigation_transport_resume_v2.py','test_investigation_api_usage.py','test_investigation_r5_live.py','test_investigation_r6.py']
    suite=unittest.TestSuite()
    for pattern in patterns:suite.addTests(unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern=pattern,top_level_dir=str(ROOT/'tests')))
    stream=io.StringIO()
    with tempfile.TemporaryDirectory() as temp,patch('investigation_dryrun.runner.RUNS',Path(temp)/'r4'),patch('investigation_dev.runner.RUNS',Path(temp)/'r3'),patch('urllib.request.urlopen',side_effect=blocked):
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    index=1
    while (OUT/f'offline_tests.{index}.json').exists():index+=1
    log=OUT/f'offline_tests.{index}.log';log.write_text(stream.getvalue())
    preserved=protected_references()
    files=list((ROOT/'src/investigation_r6').glob('*.py'))+[ROOT/'scripts/test_investigation_r6.py',ROOT/'scripts/prepare_investigation_r6.py']
    report={'status':'PASS' if result.wasSuccessful() else 'FAIL','tests_run':result.testsRun,'failures':len(result.failures),
            'errors':len(result.errors),'skipped':len(result.skipped),'model_calls':0,'network_disabled':True,
            'historical_result_roots_redirected_to_temporary_directories':True,'preserved_files':len(preserved),
            'test_files':[binding(ROOT/'tests'/p) for p in patterns],'source_files':[binding(p) for p in files],
            'log':binding(log),'created_at':utc()}
    create_json(OUT/f'offline_tests.{index}.json',report)
    print(json.dumps(report,indent=2))
    if not result.wasSuccessful(): print(stream.getvalue());raise SystemExit(1)
if __name__=='__main__':run()
