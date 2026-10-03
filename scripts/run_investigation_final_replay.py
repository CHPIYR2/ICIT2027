"""Exact final V1 replay; creates only new replay artifacts and never scores.

The frozen engine has development-only entry guards. This explicitly authorized
final-stage adapter gives copies of its function objects a sealed evaluation
allowlist. Function code objects, support logic, and the original module globals
remain unchanged. There is no model transport, gold loader, or semantic repair.
"""
import collections
import json
import os
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.dont_write_bytecode = True

from investigation_final_offline.contracts import digest, dumps, sha
from investigation_dryrun.common import digest as evidence_digest, binding, create_json

OUT = ROOT / 'results/investigation-final-evaluation'
PLAN = ROOT / 'results/investigation-final-offline/replay_manifest.candidate.json'
GEN = ROOT / 'results/investigation-final-offline/generation_manifest.candidate.json'
RESULT = OUT / 'replay_result.json'
EXECUTION = '0fa34b16869d4f85c7608fe4e8aad13a09862f81338b59d217569a9291ad9242'
POLICY = '9a583d768f5588ece0b0cfb7ccb942b5e87beee50ca740444c606c4cfc5b9557'
PREGEN = '08629db1af115b89950cc81b083a7858f8a6cf5c010fe1484ae48fce92618407'


def need(value, message):
    if not value:
        raise ValueError(message)


def load(path):
    path = Path(path)
    need(path.resolve() == path.absolute(), 'Symlink input forbidden')
    return json.loads(path.read_bytes())


def check_seal(path, field, expected):
    value = load(path)
    need(value[field] == expected == digest({k: v for k, v in value.items() if k != field}),
         'Seal mismatch: ' + str(path))
    return value


def scoped_functions(module, overrides):
    """Reuse exact code in private globals; never patch a frozen module."""
    namespace = dict(vars(module))
    for name, value in vars(module).items():
        if isinstance(value, types.FunctionType) and value.__module__ == module.__name__:
            clone = types.FunctionType(value.__code__, namespace, value.__name__,
                                       value.__defaults__, value.__closure__)
            clone.__kwdefaults__ = value.__kwdefaults__
            namespace[name] = clone
    namespace.update(overrides)
    return namespace


def replay_engine(authorized_events):
    from investigation_dryrun import claims, runner
    from investigation_r5 import core, runner as r5

    allowed = frozenset(authorized_events)

    def require_authorized(event_id):
        if event_id not in allowed:
            raise PermissionError('Event outside sealed final replay authorization')

    scoped_claims = scoped_functions(claims, {'require_development': require_authorized})
    scoped_core = scoped_functions(core, {'require_development': require_authorized})
    scoped_runner = scoped_functions(runner, {
        'require_development': require_authorized,
        'verify_claim': scoped_claims['verify_claim'],
    })
    scoped_r5 = scoped_functions(r5, {
        'validate_input': scoped_core['validate_input'],
        'r4_replay': scoped_runner['replay_bytes'],
    })
    return scoped_r5['replay_bytes']


def install_boundary(outputs):
    """Fail closed on network, subprocess, private inputs, or unrelated writes."""
    allowed = {str(p.absolute()) for p in outputs}
    counters = collections.Counter()

    def audit(event, args):
        if event in ('socket.connect', 'socket.getaddrinfo', 'socket.sendto',
                     'subprocess.Popen', 'os.system', 'os.posix_spawn'):
            counters['forbidden_external_attempts'] += 1
            raise PermissionError('V1 is offline: ' + event)
        if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
            path = Path(os.fsdecode(args[0])).absolute()
            rendered = str(path)
            if any(x in rendered for x in ('PRIVATE_', '/annotations/gold/', 'api_key.txt')):
                counters['forbidden_private_reads'] += 1
                raise PermissionError('Private inputs are forbidden in V1')
            flags = args[2] or 0
            if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                if rendered not in allowed or path.resolve() != path:
                    raise PermissionError('Non-replay write forbidden: ' + rendered)
    sys.addaudithook(audit)
    return counters


def run():
    plan = load(PLAN)
    outputs = [ROOT / p['expected_output_path'] for p in plan['positions']]
    need(not RESULT.exists() and not any(p.exists() for p in outputs), 'Replay already exists')
    boundary = install_boundary([*outputs, RESULT])
    generation = check_seal(GEN, 'manifest_sha256', PREGEN)
    execution = check_seal(OUT / 'execution_result.cumulative.json', 'execution_sha256', EXECUTION)
    commitments = [
        ('execution_result.json', 'execution_sha256', 'b494f756e1118a41b6918bfbb29055dc2a2b31100796f0633465c3d609e57216'),
        ('generation_execution_recovery.json', 'recovery_sha256', 'ebe5a15a03e25a4b100b44549879a94c896ca70862aa0b15e909a011523d8a9e'),
        ('generation_execution_recovery_amendment.json', 'amendment_sha256', 'ec915b88446cb8bce654aa158b024a2f63a982dc44234260e703d8d0c3e57f84'),
    ]
    for path, field, expected in commitments:
        check_seal(OUT / path, field, expected)
    need(sha((ROOT / 'configs/investigation-r5/matching.json').read_bytes()) == POLICY,
         'Matching/support policy changed')
    need(generation['matching_support_policy_sha256'] == POLICY, 'Policy binding changed')
    need(binding(GEN) == plan['generation_manifest'], 'Replay schedule generation binding changed')
    selection = ROOT / generation['selection']['path']
    need(binding(selection) == generation['selection'], 'Event selection changed')
    events = load(selection)['evaluation']
    need(len(events) == len(set(events)) == 32, 'Wrong event population')
    expected = [f'{e}/G1-EN/rep-{r}' for e in events for r in (1, 2, 3)]
    need([p['source_position_id'] for p in plan['positions']] == expected, 'Replay matrix changed')
    need(len(execution['positions']) == 384, 'Generation incomplete')
    need([p['position_id'] for p in execution['positions']] ==
         [p['position_id'] for p in generation['positions']], 'Generation matrix drift')
    frozen = {p['position_id']: p for p in generation['positions']}
    records = {}
    for p in execution['positions']:
        base = OUT / p['position_id']
        record = load(base / 'completed.json')
        need(all(record[k] == v for k, v in p.items()), 'Completed receipt differs from seal')
        need(sha((base / 'output.raw.json').read_bytes()) == p['output_sha256'], 'Raw hash mismatch')
        need(sha((base / 'request.canonical.json').read_bytes()) == p['request_sha256'], 'Request hash mismatch')
        need(p['bundle_sha256'] == frozen[p['position_id']]['bundle_sha256'], 'Bundle binding drift')
        records[p['position_id']] = record
    config = load(ROOT / generation['config']['path'])
    need(binding(ROOT / generation['config']['path']) == generation['config'], 'Config drift')
    # Hash code/schema/prompt bindings only. No gold or evaluator input is loaded.
    for ref in config['scientific_bindings_preserved']:
        if ref['path'].startswith(('src/', 'schemas/', 'prompts/')):
            need(binding(ROOT / ref['path']) == ref, 'Frozen scientific binding changed')
    for p in plan['positions']:
        for ref in p['expected_verifier_bindings']:
            need(binding(ROOT / ref['path']) == ref, 'Frozen verifier changed')
    engine = replay_engine(events)
    counts = collections.Counter()
    rows, pending = [], []
    from investigation_dryrun.runner import parse_experiment, RetryableDelivery
    for p in plan['positions']:
        m = records[p['source_position_id']]
        need(m['cell_id'] == 'G1-EN' and p['cell_id'] == 'V1-EN' and
             m['event_id'] == p['event_id'] and m['repetition'] == p['repetition'], 'Source pairing drift')
        need(p['source_raw_path'] == str((OUT / m['position_id'] / 'output.raw.json').relative_to(ROOT)), 'Source path drift')
        raw = (ROOT / p['source_raw_path']).read_bytes()
        evidence_base = ROOT / 'results/investigation-v2/B0' / m['event_id'] / 'EN'
        bundle, receipt = load(evidence_base / 'retrieved.json'), load(evidence_base / 'receipt.json')
        need(evidence_digest(bundle) == p['source_bundle_sha256'] == m['bundle_sha256'], 'EN bundle mismatch')
        request = load(OUT / m['position_id'] / 'request.canonical.json')
        from investigation_dryrun.common import dumps as evidence_dumps
        need(request['input'] == evidence_dumps(bundle), 'Replay view differs from generation')
        provenance = {**m, 'view': 'EN', 'citation_mode': 'required',
                      'receipt_sha256': evidence_digest(receipt), 'run_id': execution['run_id']}
        parsed = None
        try:
            parsed = parse_experiment(raw)
            counts['parsed_sources'] += 1
        except RetryableDelivery:
            counts['unparseable_sources'] += 1
        if m['status'] in ('DELIVERED', 'DELIVERED_SCHEMA_OR_VISIBILITY_INVALID'):
            need(parsed is not None, 'Delivered source cannot be parsed by frozen parser')
            result = engine(m['event_id'], raw, provenance, bundle, receipt)
            result['status'] = 'REPLAYED'
            # Independent second execution must produce the exact canonical artifact.
            repeat = engine(m['event_id'], raw, provenance, bundle, receipt)
            repeat['status'] = 'REPLAYED'
            need(dumps(result) == dumps(repeat), 'Nondeterministic replay')
            need(len(result['dispositions']) == len(parsed['claims']), 'Claim loss')
            counts['replay_success'] += 1
            counts['claims_entering_verifier'] += len(result['dispositions'])
            counts.update(d['disposition'] for d in result['dispositions'])
        else:
            # Existing frozen runner's unavailable delivery state; no text invented.
            result = {'version': 'r5-exact-replay', 'event_id': m['event_id'],
                      'cell_id': 'V1-EN', 'source_cell_id': 'G1-EN', 'repetition': m['repetition'],
                      'source_position_id': m['position_id'], 'source_output_sha256': m['output_sha256'],
                      'status': 'REPLAY_UNAVAILABLE', 'reason': m['status'], 'llm_calls': 0,
                      'published_report': None, 'dispositions': []}
            counts['replay_unavailable'] += 1
        need(result['source_output_sha256'] == sha(raw) == m['output_sha256'], 'Source identity changed')
        need(result['llm_calls'] == 0, 'Unexpected model call')
        counts['schema_valid_sources'] += m.get('schema_valid') is True
        counts['schema_invalid_sources'] += m.get('schema_valid') is False
        counts['incomplete_sources'] += m['status'] == 'PROVIDER_INCOMPLETE'
        row = {**p, 'source_output_sha256': m['output_sha256'],
               'source_receipt_binding': binding(ROOT / p['source_receipt_path']),
               'bundle_binding': binding(evidence_base / 'retrieved.json'),
               'retrieval_receipt_binding': binding(evidence_base / 'receipt.json'),
               'source_status': m['status'], 'source_schema_valid': m.get('schema_valid'),
               'status': result['status'], 'result_sha256': digest(result),
               'input_identity_sha256': digest({'event_id': m['event_id'], 'repetition': m['repetition'],
                   'source_cell_id': 'G1-EN', 'source_output_sha256': m['output_sha256'],
                   'bundle_sha256': m['bundle_sha256'], 'receipt_sha256': evidence_digest(receipt)})}
        rows.append(row)
        pending.append((ROOT / p['expected_output_path'], result))
    need(len(rows) == 96 and sum(counts[s] for s in ('SUPPORTED', 'QUALIFIED', 'INSUFFICIENT')) ==
         counts['claims_entering_verifier'], 'Replay totals mismatch')
    need(not boundary, 'Forbidden operation attempted')
    for (path, result), row in zip(pending, rows):
        row['result_file_sha256'] = create_json(path, result)
        need(digest(load(path)) == row['result_sha256'], 'Persisted result hash mismatch')
    result_manifest = {
        'version': plan['version'], 'result_version': 'final-v1-replay-result-v1',
        'replay_artifact_version': 'r5-exact-replay', 'positions': rows,
        'replay_plan': binding(PLAN), 'generation_execution_seal_sha256': EXECUTION,
        'matching_support_policy_sha256': POLICY, 'generation_manifest_sha256': PREGEN,
        'execution_adapter': binding(Path(__file__)),
        'scope_adapter': 'Original function code objects in isolated globals; development guards replaced only with the sealed 32-event evaluation allowlist. Original modules unchanged.',
        'result_hash_convention': 'SHA-256(contracts.dumps(result).encode()); file SHA-256 recorded separately',
        'counts': {k: counts[k] for k in ('parsed_sources', 'unparseable_sources', 'schema_valid_sources',
            'schema_invalid_sources', 'incomplete_sources', 'replay_success', 'replay_unavailable',
            'claims_entering_verifier', 'SUPPORTED', 'QUALIFIED', 'INSUFFICIENT')},
        'scheduled_positions': 96, 'processed_positions': 96, 'source_hash_mappings_correct': 96,
        'additional_model_calls': 0, 'forbidden_external_attempts': 0, 'private_inputs_accessed': 0,
        'deterministic_repeat_checks': 96, 'D0_started': False, 'scoring_started': False,
        'status': 'REPLAY_PROCESSED_PENDING_INTEGRITY_SEAL',
    }
    create_json(RESULT, result_manifest)
    print(json.dumps({'manifest': str(RESULT), 'counts': result_manifest['counts']}, indent=2))


if __name__ == '__main__':
    run()
