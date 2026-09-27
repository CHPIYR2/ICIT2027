"""Reuse r5 scientific requests and validators; change only the output allowance."""
import copy
from investigation_dryrun.common import ROOT, load, dumps, digest, file_hash, binding
from investigation_r5.core import read_bundle, require_development, validate_input
from investigation_r5.runner import build_request as r5_request, replay_bytes, validate_delivery

CONFIG = ROOT / 'configs/investigation-r6'
OUT = ROOT / 'results/investigation-r6'
PARENT_PLAN = ROOT / 'results/investigation-r5/validation_manifest.json'
CAP = 24576
EVIDENCE_CEILING = 16384
EXPECTED = {
 'configs/investigation_protocol.v1.freeze_inventory.r5.json': '5336d8fe9d2f526c32f0f4f510d4a7264d432fcc30c7b8303176b2a838dc0e0b',
 'results/investigation-r5/validation_manifest.json': '79fba58a9708acd7a8db75e58a1311d7efb484e5a5e334f0fbe7a56bfecc7ee8',
 'results/investigation-r5-validation/post_validation_manifest.json': '309781753e8047ac26ab273ebec3d15413e546a17f96ace980eb3f79cc603edd',
 'annotations/gold/pilot-v1/manifest.json': '660ca033cd1c6a5bb9de98bb75c6a7ece5f28980716b9181152187e72c557d4a',
}

def protected_references():
    refs = {}
    def add(ref):
        path = ref['path']
        if path in refs and refs[path]['sha256'] != ref['sha256']:
            raise ValueError('Conflicting historical binding: ' + path)
        if file_hash(ROOT / path) != ref['sha256']:
            raise ValueError('Protected artifact changed: ' + path)
        refs[path] = binding(ROOT / path)
    for path, sha in EXPECTED.items():
        if file_hash(ROOT / path) != sha: raise ValueError('Historical manifest changed: ' + path)
        add(binding(ROOT / path))
    sources = [
        ('configs/investigation_protocol.v1.freeze_inventory.r5.json', 'files'),
        ('results/investigation-r5/preservation.before.json', 'files'),
        ('results/investigation-r5-validation/preflight.json', 'protected_files'),
        ('results/investigation-r5-validation/post_validation_manifest.json', 'files'),
    ]
    for path, key in sources:
        add(binding(ROOT / path))
        for ref in load(ROOT / path)[key]: add(ref)
    for ref in load(ROOT / 'annotations/gold/pilot-v1/manifest.json')['files']:
        add({'path': ref['snapshot_path'], 'sha256': ref['sha256']})
    sidecar = ROOT / 'results/investigation-r5-validation/post_validation_manifest.json.sha256'
    if sidecar.read_text().split()[0] != EXPECTED['results/investigation-r5-validation/post_validation_manifest.json']:
        raise ValueError('Historical post-validation sidecar changed')
    add(binding(sidecar))
    return [refs[p] for p in sorted(refs)]

def configuration():
    model = load(CONFIG / 'model.candidate.json')
    budget = load(CONFIG / 'token_budget.candidate.json')
    old_model = load(ROOT / 'configs/investigation-r5/model.candidate.json')
    changed_metadata = {'version', 'parent', 'authorization_scope', 'output_cap_validation', 'max_output_tokens'}
    expected_keys = (set(old_model) - {'max_output_tokens'}) | {'model_max_output_tokens'}
    if set(model) != expected_keys: raise ValueError('Unexpected model configuration field')
    for key in set(old_model) - changed_metadata:
        if model[key] != old_model[key]: raise ValueError('Scientific model configuration drift: ' + key)
    if model['model_max_output_tokens'] != CAP or model['live_api_enabled']:
        raise ValueError('Offline r6 output configuration drift')
    old_budget = load(ROOT / 'configs/investigation-r5/token_budget.candidate.json')
    if set(budget) != {'version', 'evidence_input_token_safety_ceiling', 'model_max_output_tokens',
                       'prompt_plus_evidence_input_token_ceiling', 'input_scope', 'retrieval_unchanged', 'overflow_action', 'parent'}:
        raise ValueError('Unexpected input-budget configuration field')
    if budget['evidence_input_token_safety_ceiling'] != EVIDENCE_CEILING:
        raise ValueError('Input evidence ceiling changed')
    if budget['model_max_output_tokens'] != CAP:
        raise ValueError('Output cap inconsistent across configs')
    if budget['prompt_plus_evidence_input_token_ceiling'] != old_budget['max_input_text_tokens']:
        raise ValueError('Prompt plus evidence input ceiling changed')
    if budget['retrieval_unchanged'] is not True or budget['overflow_action'] != old_budget['overflow_action']:
        raise ValueError('Input overflow policy changed')
    return model, budget

def parent_request(position):
    require_development(position['event_id'])
    b, receipt = read_bundle(position['event_id'], position['view'])
    q = r5_request(position['event_id'], position['cell_id'], b, receipt)
    if digest(q) != position['request_sha256'] or digest(b) != position['bundle_sha256'] or digest(receipt) != position['receipt_sha256']:
        raise ValueError('Predeclared r5 position binding changed')
    return q, b, receipt

def equivalence(old, new):
    expected = copy.deepcopy(old)
    if expected.get('max_output_tokens') != 8192: raise ValueError('Wrong parent output cap')
    expected['max_output_tokens'] = CAP
    if new != expected: raise ValueError('Unexpected substantive request diff')
    return {
        'status': 'PASS', 'only_provider_change': {'max_output_tokens': {'before': 8192, 'after': CAP}},
        'parent_request_sha256': digest(old), 'request_sha256': digest(new),
        'prompt_bytes_equal': old['instructions'].encode() == new['instructions'].encode(),
        'evidence_bytes_equal': old['input'].encode() == new['input'].encode(),
        'structured_schema_bytes_equal': dumps(old['text']['format']).encode() == dumps(new['text']['format']).encode(),
        'model_temperature_view_citation_and_all_other_fields_equal': True,
    }

def build_request(position):
    require_development(position['event_id'])
    model, budget = configuration()
    old, bundle, receipt = parent_request(position)
    new = copy.deepcopy(old)
    new['max_output_tokens'] = model['model_max_output_tokens']
    record = equivalence(old, new)
    return new, bundle, receipt, record

def validate_manifest(manifest):
    parent = load(PARENT_PLAN)
    if manifest['counts'] != parent['counts'] or len(manifest['positions']) != 64:
        raise ValueError('Wrong r6 matrix')
    if [p['position_id'] for p in manifest['positions']] != [p['position_id'] for p in parent['positions']]:
        raise ValueError('Position order/identity changed')
    for old, row in zip(parent['positions'], manifest['positions']):
        for key in ('event_id', 'cell_id', 'view', 'citation_mode', 'repetition', 'purpose', 'bundle_sha256', 'receipt_sha256'):
            if row[key] != old[key]: raise ValueError('Position semantics changed: ' + key)
        if row['r5_position'] != old: raise ValueError('Parent provenance changed')
        request, _, _, _ = build_request(old)
        if load(ROOT / row['request_artifact']['path']) != request or row['request_sha256'] != digest(request):
            raise ValueError('r6 request binding drift')
        if file_hash(ROOT / row['request_artifact']['path']) != row['request_artifact']['sha256']:
            raise ValueError('r6 request artifact drift')
    return {'status': 'PASS', 'positions': 64, 'same_cap': CAP, 'historical_outputs_reused': 0}

def generate(*args, **kwargs):
    raise PermissionError('r6 OFFLINE ONLY: explicit live authorization and execution preflight required')
