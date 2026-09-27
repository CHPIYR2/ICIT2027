"""Pre-run tests, production-bundle token audit, and immutable batch bindings."""
import io,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests'),str(ROOT/'scripts')]
from investigation_dryrun.common import *
from investigation_dryrun.tokens import audit
from investigation_dryrun.custody import development_ids
from investigation_dryrun.runner import plan,build_request,approved_configuration,OpenAITransport
from investigation_dryrun.structured import compile_schema
from verify_investigation_development import verify as verify_previous
OUT=ROOT/'results/investigation-dryrun-v1'
if (OUT/'preflight_manifest.json').exists():raise SystemExit('Preflight already exists; do not revise a started batch')
patterns=['test_investigation_dryrun_regression.py','test_investigation_dryrun_amendments.py','test_investigation_development.py','test_investigation_freeze_preparation.py','test_investigation_v2.py']
suite=unittest.TestSuite()
for pattern in patterns:
 sys.path.insert(0,str(ROOT/'tests'))
 suite.addTests(unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern=pattern,top_level_dir=str(ROOT/'tests')))
stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
(OUT/'preflight_tests.log').write_text(stream.getvalue())
if not result.wasSuccessful():print(stream.getvalue());raise SystemExit(1)
create_json(OUT/'preflight_tests.json',{'status':'PASS','tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'test_files':[binding(ROOT/'tests'/x) for x in patterns],'provider_calls':0,'evaluation_gold_or_results_inspected':False,'interpretation':'synthetic provider fixtures and sealed development conformance only; not model recovery scores'})
create_json(OUT/'prior_package_verification.json',verify_previous())
texts={b:(ROOT/f'prompts/investigation-v1-r4/{b}.v1.txt').read_text() for b in ['B1','B2','B3']}
create_json(OUT/'token_audit.json',audit(OUT/'preflight_access.jsonl',texts))
create_json(OUT/'run_plan.json',plan())
# Existing B0 output, one physical artifact and three explicit references per event.
create_json(OUT/'B0_references.json',[{'event_id':eid,'baseline':'B0','repetition':rep,'artifact':binding(ROOT/f'results/investigation-v2/B0/{eid}/EN/timeline.json'),'independent_generation':False} for eid in development_ids() for rep in (1,2,3)])
# Validate every actual request before the first provider call, without changing inputs.
from investigation_dryrun.custody import read_bundle
model,budget,_=approved_configuration(OpenAITransport());requests=[]
for eid in development_ids():
 for baseline in ['B1','B2','B3']:
  bundle,_=read_bundle(eid,'N' if baseline=='B1' else 'EN',OUT/'preflight_access.jsonl');request,_=build_request(eid,baseline,bundle,model,budget)
  requests.append({'event_id':eid,'baseline':baseline,'request_sha256':digest(request)})
create_json(OUT/'request_preflight.json',requests)
paths=set()
# Prior inventory binds all reused policy/implementation and original pilot bytes.
for ref in load(ROOT/'configs/investigation_protocol.v1.freeze_inventory.r3.json')['existing_files_to_seal_on_future_protocol_freeze']:paths.add(ref['path'])
for folder,pattern in [('src/investigation_dryrun','*.py'),('configs/investigation-dryrun-v1','*.json'),('prompts/investigation-v1-r4','*'),('schemas','*.v3*.json')]:
 paths.update(str(p.relative_to(ROOT)) for p in (ROOT/folder).glob(pattern) if p.is_file())
paths.update(['scripts/run_investigation_dryrun.py','scripts/prepare_investigation_dryrun.py','tests/test_investigation_dryrun_regression.py','tests/test_investigation_dryrun_amendments.py'])
paths.update(str(p.relative_to(ROOT)) for p in OUT.iterdir() if p.is_file())
manifest={'version':'authorized-development-preflight-r4','status':'READY_FOR_AUTHORIZED_DEVELOPMENT_ONLY','created_at':utc(),'protocol_frozen':False,'evaluation_authorized':False,'development_event_ids':list(development_ids()),'planned_generation_cells':144,'planned_B4_replays':48,'all_repetitions_retained':True,'no_prompt_or_rule_changes_during_batch':True,'files':[binding(ROOT/p) for p in sorted(paths)]}
create_json(OUT/'preflight_manifest.json',manifest)
print(json.dumps({'status':'READY','tests':result.testsRun,'bindings':len(paths),'generation_cells':144,'B4_replays':48,'model_calls_so_far':0},indent=2))
