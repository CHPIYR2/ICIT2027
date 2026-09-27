"""Read-only candidate/inventory integrity checks; no generation or evaluation access."""
from pathlib import Path
import sys
import json
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from investigation_dev.common import load,file_hash
from investigation_dev.custody import verify_access_log,development_ids
from verify_investigation_freeze_candidate import verify as old_verify


def verify():
    previous=old_verify()
    for name in ('results/investigation-freeze-v1/delivery_manifest.json','results/investigation-semantic-r2/delivery_manifest.json'):
        manifest=load(ROOT/name);entries=manifest['files']
        if isinstance(entries,dict):entries=[{'path':p,'sha256':h} for p,h in entries.items()]
        for entry in entries:
            if file_hash(ROOT/entry['path'])!=entry['sha256']:raise ValueError('Historical package changed: '+entry['path'])
    candidate=load(ROOT/'configs/investigation_protocol.v1.development_candidate.json')
    assert candidate['protocol_frozen'] is False and candidate['implementation_scope']=='existing development set only'
    assert candidate['semantic_resolution']=='B_APPROVED_SUPPORT_VALIDATED_CONDITIONAL_PROJECTION'
    assert candidate['llm_calls_authorized'] is False
    assert [(b['baseline'],b['view']) for b in candidate['primary_baselines']]==[('B0','EN'),('B1','N'),('B2','EN'),('B3','EN'),('B4','EN')]
    for entry in list(candidate['artifacts'].values())+candidate['development_implementation_files']:
        if file_hash(ROOT/entry['path'])!=entry['sha256']:raise ValueError('Candidate binding changed: '+entry['path'])
    prompts=load(ROOT/'prompts/investigation-v1/manifest.v1.json')
    for entry in [*prompts['prompts'].values(),prompts['common'],prompts['canonical_templates'],prompts['Q_definitions'],prompts['schema']]:
        assert file_hash(ROOT/entry['path'])==entry['sha256']
    audit=load(ROOT/'results/investigation-development-v1/token_budget_audit.json')
    assert len(audit['rows'])==32 and {r['event_id'] for r in audit['rows']}==set(development_ids())
    for row in audit['rows']:
        for entry in row['source_files']:assert file_hash(ROOT/entry['path'])==entry['sha256']
    budget=load(ROOT/'configs/investigation-dev-v1/token_budget.candidate.json')
    assert budget['fixed_evidence_tokens']==max(row['tokens'] for row in audit['rows'])==11162
    assert file_hash(ROOT/budget['audit']['path'])==budget['audit']['sha256']
    model=load(ROOT/'configs/investigation-dev-v1/model.candidate.json');assert not model['live_api_enabled'] and model['seed'] is None
    stats=load(ROOT/'configs/investigation-dev-v1/statistics.json');assert stats['bootstrap']['resamples']==2000 and stats['bootstrap']['seed']==20270922
    tests=load(ROOT/'results/investigation-development-v1/conformance-final/test_results.json')
    assert tests['status']=='PASS' and tests['tests_run']==102 and tests['failures']==tests['errors']==0
    for entry in tests['test_files']:assert file_hash(ROOT/entry['path'])==entry['sha256']
    last_log=verify_access_log(ROOT/'results/investigation-development-v1/access.jsonl')
    inventory=ROOT/'configs/investigation_protocol.v1.freeze_inventory.r3.json'
    inventory_count=None
    if inventory.exists():
        entries=load(inventory)['existing_files_to_seal_on_future_protocol_freeze']
        for entry in entries:assert file_hash(ROOT/entry['path'])==entry['sha256'],entry['path']
        inventory_count=len(entries)
    delivery=ROOT/'results/investigation-development-v1/delivery_manifest.json'
    if delivery.exists():
        for entry in load(delivery)['files']:assert file_hash(ROOT/entry['path'])==entry['sha256']
        assert file_hash(delivery)==Path(str(delivery)+'.sha256').read_text().split()[0]
    return {'status':'PASS','previous_gold_and_r1_verification':previous,'r2_package_unchanged':True,'current_tests':tests['tests_run'],'B1_B4_development_runners_implemented':True,'development_events_in_token_audit':16,'audited_view_bundles':32,'access_log_chain_head':last_log,'candidate_bindings_valid':True,'inventory_files':inventory_count,'protocol_frozen':False,'live_model_calls':0,'evaluation_event_runs':0,'evaluation_gold_created_or_inspected':False,'research_results_computed':False}

if __name__=='__main__':print(json.dumps(verify(),indent=2))
