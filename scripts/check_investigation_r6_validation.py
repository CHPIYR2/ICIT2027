"""Pre/post execution gates; write only the new validation namespace."""
import io,json,os,socket,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
os.environ['TIKTOKEN_CACHE_DIR']=str(ROOT/'.cache/tiktoken')
def blocked(*a,**k):raise AssertionError('No network during local integrity/tests')
socket.create_connection=blocked;socket.socket.connect=blocked
from investigation_dryrun.common import load,binding,file_hash,create_json,dumps,utc
from investigation_dryrun.tokens import count,summary
from investigation_r6.candidate import protected_references,validate_manifest,configuration
from investigation_r6.policy import rate_feasibility
OUT=ROOT/'results/investigation-r6-validation'
INVENTORY=ROOT/'configs/investigation_protocol.v1.freeze_inventory.r6.json'
INVENTORY_SHA='cc0b0f9a03578aa1cecaf45f742bd29284a0cceccb510a4bd73b21d53e86f84e'
PLAN=ROOT/'results/investigation-r6/validation_manifest.json'
PLAN_SHA='ea3fb04e4c7a48c2db63e7fda185b205e422218906d93af1a93ecbb030affbc3'

def integrity():
    assert file_hash(INVENTORY)==INVENTORY_SHA,'r6 candidate inventory changed'
    assert file_hash(PLAN)==PLAN_SHA,'r6 64-position manifest changed'
    refs=load(INVENTORY)['files']
    for ref in refs:assert file_hash(ROOT/ref['path'])==ref['sha256'],ref['path']
    historical=protected_references();configuration();validate_manifest(load(PLAN))
    if (OUT/'preflight.json').exists():
        for ref in load(OUT/'preflight.json')['protected_files']:assert file_hash(ROOT/ref['path'])==ref['sha256'],ref['path']
    return {'status':'PASS','r6_inventory_files':len(refs),'historical_protected_files':len(historical),'all64_request_identities':True,'model_calls':0}

def run(phase):
    if phase not in ('pre-execution','post-execution'):raise ValueError('Unknown phase')
    OUT.mkdir(exist_ok=True)
    approval=OUT/'author_approval.txt'
    source=Path('/Users/potinglu/.codex/attachments/488db07b-021a-4056-9fa5-970dd4618d58/貼上的文字.txt')
    if approval.exists():assert approval.read_bytes()==source.read_bytes()
    else:approval.write_bytes(source.read_bytes())
    integrity()
    patterns=['test_investigation_r5.py','test_investigation_dryrun_regression.py','test_investigation_dryrun_amendments.py',
        'test_investigation_development.py','test_investigation_freeze_preparation.py','test_investigation_v2.py',
        'test_investigation_transport_resume_v2.py','test_investigation_api_usage.py','test_investigation_r5_live.py',
        'test_investigation_r6.py','test_investigation_r6_live.py']
    suite=unittest.TestSuite()
    for name in patterns:suite.addTests(unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern=name,top_level_dir=str(ROOT/'tests')))
    stream=io.StringIO()
    with tempfile.TemporaryDirectory() as temp,patch('investigation_dryrun.runner.RUNS',Path(temp)/'r4'),patch('investigation_dev.runner.RUNS',Path(temp)/'r3'),patch('urllib.request.urlopen',side_effect=blocked):
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    index=1
    while (OUT/f'{phase}.tests.{index}.json').exists():index+=1
    log=OUT/f'{phase}.tests.{index}.log';log.write_text(stream.getvalue())
    paths=list((ROOT/'src/investigation_r6_live').glob('*.py'))+[ROOT/'scripts/check_investigation_r6_validation.py',ROOT/'scripts/run_investigation_r6_validation.py',ROOT/'tests/test_investigation_r6_live.py']
    report={'phase':phase,'status':'PASS' if result.wasSuccessful() else 'FAIL','tests_run':result.testsRun,
        'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'model_calls':0,
        'network_disabled':True,'test_files':[binding(ROOT/'tests'/x) for x in patterns],
        'execution_source_files':[binding(p) for p in paths],'post_test_integrity':integrity(),'log':binding(log),'created_at':utc()}
    testpath=OUT/f'{phase}.tests.{index}.json';create_json(testpath,report)
    if not result.wasSuccessful():
        print(stream.getvalue()[-6000:]);raise RuntimeError('Tests failed: no model calls')
    if phase=='pre-execution':
        assert not (OUT/'preflight.json').exists(),'Existing preflight: checkpoint review required'
        estimates=[]
        for p in load(PLAN)['positions']:
            q=load(ROOT/p['request_artifact']['path'])
            a=count(q['instructions']);b=count(q['input']);s=count(dumps(q['text']['format']['schema']))
            estimates.append({'position_id':p['position_id'],'prompt_tokens':a,'evidence_tokens':b,'schema_tokens':s,
                'estimated_request_tokens':a+b+s,'configured_output_allowance':24576,'advisory_rate_demand':max(a+b+s,24576)})
            assert a+b+s<=30000,'Local request estimate exceeds 30000: STOP'
        rate=load(ROOT/'results/investigation-r6/rate_limit_evidence.json');latest=rate['latest_available_token_header_record']
        limits={k:v for k,v in latest['response_headers'].items() if k.startswith('x-ratelimit-limit-')}
        assert not rate_feasibility(limits,estimated_request_tokens=max(x['estimated_request_tokens'] for x in estimates))['status'].startswith('STOP')
        record={'status':'PASS','rows':estimates,'request_token_summary':summary([x['estimated_request_tokens'] for x in estimates]),
            'evidence_token_summary':summary([x['evidence_tokens'] for x in estimates]),'advisory_rate_demand_summary':summary([x['advisory_rate_demand'] for x in estimates]),
            'scope':'Local prompt + serialized evidence + compiled strict schema. Provider framing/estimator not claimed exact.',
            'approved_rate_interpretation':'max(configured maximum output allowance, applicable provider request estimate), not input+output allowance',
            'no_estimate_over30000':True,'preserved_rate_evidence':binding(ROOT/'results/investigation-r6/rate_limit_evidence.json'),
            'current_limit_not_guaranteed':True,'first_request_uses_author_approved_historical_feasibility_with_live_feedback':True}
        create_json(OUT/'request_size_preflight.json',record)
        refs={r['path']:r for r in load(INVENTORY)['files']}
        for p in paths+[INVENTORY,PLAN,approval,testpath,log,OUT/'request_size_preflight.json',ROOT/'results/investigation-r6/delivery_manifest.json']:
            refs[str(p.relative_to(ROOT))]=binding(p)
        create_json(OUT/'preflight.json',{'status':'PASS','created_at':utc(),'tests':binding(testpath),'inventory':binding(INVENTORY),
            'validation_manifest':binding(PLAN),'request_equivalence':binding(ROOT/'results/investigation-r6/request_equivalence.json'),
            'request_size_preflight':binding(OUT/'request_size_preflight.json'),'initial_rate_limits':limits,
            'author_approval':binding(approval),'protected_files':[refs[p] for p in sorted(refs)],
            'evaluation_access_policy':'Only exact manifest development IDs and hash-bound stored requests; require_development before bundle access; no evaluation paths, tools, retrieval, conversation or previous_response_id in requests',
            'custody_limit':'Application path is development-only; no OS custody provisioning/claims beyond approved scope',
            'maximum_inflight':1,'model_max_output_tokens':24576,'evidence_input_token_safety_ceiling':16384})
        print(json.dumps({'preflight':'PASS','tests':result.testsRun,'request_tokens':record['request_token_summary'],'advisory_rate_demand':record['advisory_rate_demand_summary'],'locked_files':len(refs),'model_calls':0},indent=2))
    else:print(json.dumps(report,indent=2))
if __name__=='__main__':run(sys.argv[1])
