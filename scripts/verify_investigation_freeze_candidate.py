"""Audit sealed pilot snapshot and proposed freeze inventory; never score systems."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import json
from sherlock.io import ROOT,read_json,sha256


def verify():
    gold=ROOT/'annotations/gold/pilot-v1';manifest=read_json(gold/'manifest.json')
    assert sha256(gold/'manifest.json')==(gold/'manifest.sha256').read_text().split()[0]
    assert manifest['methodology']=='single-reviewer gold' and not manifest['protocol_frozen']
    assert manifest['positive_facts']==30 and manifest['guardrails']==24 and manifest['reviewed_question_judgments']==28
    for entry in manifest['files']:
        path=ROOT/entry['snapshot_path'];assert sha256(path)==entry['sha256'],str(path)
        assert path.stat().st_mode&0o222==0,'Snapshot unexpectedly writable'
    for e in manifest['events']:
        assert sha256(ROOT/e['annotation']['original_path'])==e['annotation']['sha256'],'Reviewed facts changed'
        d=read_json(ROOT/e['annotation']['snapshot_path'])
        assert d['signoff']['reviewer_id']==e['reviewer_id']=='R1'
        assert d['signoff']['reviewed_at']==e['review_timestamp']
        assert all(f['review_status']=='HUMAN_REVIEWED' for f in d['facts'])
        assert all(f['view_accounting'][v]['recovered_by_system'] is None for f in d['facts'] for v in ('E','N','EN'))
    candidate=read_json(ROOT/'configs/investigation_protocol.v1.freeze_candidate.json')
    assert candidate['protocol_frozen'] is False and candidate['numeric_tolerance_profile'] is None
    assert candidate['llm_calls_authorized'] is False and candidate['B1_B4_implementation_authorized'] is False
    assert [(b['baseline'],b['view']) for b in candidate['primary_baselines']]==[('B0','EN'),('B1','N'),('B2','EN'),('B3','EN'),('B4','EN')]
    for entry in candidate['artifacts'].values():assert sha256(ROOT/entry['path'])==entry['sha256'],entry['path']
    audit=read_json(ROOT/'results/investigation-freeze-v1/numeric_precision.pilots.json')
    assert audit['evaluation_events_accessed']==0
    for path,expected in audit['input_hashes'].items():assert sha256(ROOT/path)==expected,path
    for unit,row in audit['units'].items():
        assert row['values']['n']==row['exact_float32_roundtrip_count']
        assert row['json_float_roundtrip_exact']
        assert row['eight_significant_digits_relative_error_nonzero']['max']<=5e-8
    inventory_path=ROOT/'configs/investigation_protocol.v1.freeze_inventory.json'
    if inventory_path.exists():
        inventory=read_json(inventory_path)
        for entry in inventory['existing_files_to_seal_on_future_protocol_freeze']:
            assert sha256(ROOT/entry['path'])==entry['sha256'],entry['path']
    return {'status':'PASS','pilot_gold_manifest_sha256':sha256(gold/'manifest.json'),'sealed_snapshot_files':len(manifest['files']),
        'reviewed_annotation_files_byte_identical':4,'single_reviewer':'R1','positive_facts':30,'guardrails':24,'reviewed_questions':28,
        'numeric_observations_audited':audit['total_valid_numeric_observations'],'evaluation_events_used_for_precision':0,
        'protocol_frozen':False,'llm_calls':0,'B1_B4_implemented':False,'research_results_computed':False}


if __name__=='__main__':print(json.dumps(verify(),indent=2))
