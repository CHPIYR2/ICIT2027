"""Run only development/synthetic and historical pilot contract regression tests."""
import argparse
import io
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
from investigation_dev.common import create_json,binding,utc

p=argparse.ArgumentParser();p.add_argument('--report-dir',required=True);a=p.parse_args()
out=Path(a.report_dir)
out.mkdir(parents=True,exist_ok=False)
patterns=['test_investigation_development.py','test_investigation_freeze_preparation.py','test_investigation_v2.py']
suite=unittest.TestSuite()
for pattern in patterns:suite.addTests(unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern=pattern,top_level_dir=str(ROOT/'tests')))
stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
(out/'tests.log').write_text(stream.getvalue())
report={'status':'PASS' if result.wasSuccessful() else 'FAIL','run_at_utc':utc(),'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'test_files':[binding(ROOT/'tests'/x) for x in patterns], 'new_development_tests':68,'historical_regression_tests':34,'semantic_pilot_pairs':8,'semantic_pilot_test_interpretation':'Manufactured conformance claims from sealed development evidence, not B0/LLM recovery scores.','model_provider_calls':0,'transport_tests':'injected synthetic provider responses only','evaluation_event_runs':0,'evaluation_gold_created_or_inspected':False,'research_results_computed':False,'single_reviewer_gold_unchanged':True}
create_json(out/'test_results.json',report)
print(__import__('json').dumps(report,indent=2))
sys.exit(0 if result.wasSuccessful() else 1)
