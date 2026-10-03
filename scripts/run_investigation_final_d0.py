"""Create the 32 frozen D0 references without retrieval, gold, or model calls."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.dont_write_bytecode = True

from investigation_final_offline.contracts import digest, dumps, sha
from investigation_dryrun.common import binding, create_json
from investigation.timeline_v2 import timeline
from retrieval.evidence_formatter import digest as bundle_digest

OUT = ROOT / 'results/investigation-final-evaluation'
PLAN = ROOT / 'results/investigation-final-offline/reference_manifest.candidate.json'
SEAL = OUT / 'd0_result.seal.json'


def load(path):
    path = Path(path)
    if path.resolve() != path.absolute():
        raise ValueError('Symlink input forbidden')
    return json.loads(path.read_bytes())


def run():
    plan = load(PLAN)
    targets = [ROOT / p['expected_output_path'] for p in plan['positions']]
    if SEAL.exists() or any(p.exists() for p in targets):
        raise ValueError('D0 artifacts already exist; preserve them')
    allowed = {str(p) for p in [SEAL, *targets]}

    def audit(event, args):
        if event in ('socket.connect', 'socket.getaddrinfo', 'socket.sendto',
                     'subprocess.Popen', 'os.system', 'os.posix_spawn'):
            raise PermissionError('D0 has no external calls')
        if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
            path = Path(os.fsdecode(args[0])).absolute()
            if any(s in str(path) for s in ('PRIVATE_', '/annotations/gold/', 'api_key.txt')):
                raise PermissionError('D0 cannot read private inputs')
            if (args[2] or 0) & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                if str(path) not in allowed or path.resolve() != path:
                    raise PermissionError('D0 output path not authorized')
    sys.addaudithook(audit)
    selection = load(ROOT / 'configs/investigation_events.v1.json')
    events = selection['evaluation']
    assert len(events) == len(set(events)) == 32
    assert [p['event_id'] for p in plan['positions']] == events
    generation = load(OUT / 'execution_result.cumulative.json')
    assert generation['execution_sha256'] == '0fa34b16869d4f85c7608fe4e8aad13a09862f81338b59d217569a9291ad9242'
    assert digest({k: v for k, v in generation.items() if k != 'execution_sha256'}) == generation['execution_sha256']
    bundles = {p['event_id']: p['bundle_sha256'] for p in generation['positions'] if p['cell_id'] == 'G1-EN'}
    implementation = []
    for lock in ('configs/investigation_phase1.lock.json', 'configs/investigation_phase1.v2.lock.json'):
        for name, expected in load(ROOT / lock)['files'].items():
            if name.startswith(('src/', 'schemas/', 'experiments/')):
                assert sha((ROOT / name).read_bytes()) == expected, name
                implementation.append(binding(ROOT / name))
    rows, pending = [], []
    for p in plan['positions']:
        assert p['cell_id'] == 'D0' and p['repetition'] == 0 and p['model_calls'] == 0
        for ref in p['source_bindings']:
            assert binding(ROOT / ref['path']) == ref
        base = ROOT / 'results/investigation-v2/B0' / p['event_id'] / 'EN'
        bundle, receipt = load(base / 'retrieved.json'), load(base / 'receipt.json')
        assert bundle['scope']['event_id'] == p['event_id'] and bundle['scope']['view'] == 'EN'
        assert bundle_digest(bundle) == p['bundle_sha256'] == bundles[p['event_id']]
        result = timeline(bundle, receipt)
        assert dumps(result) == dumps(timeline(bundle, receipt)), 'Nondeterministic D0'
        assert result == load(base / 'timeline.json'), 'D0 differs from frozen baseline implementation'
        row = {**p, 'status': 'DETERMINISTIC_REFERENCE', 'result_sha256': digest(result),
               'bundle_binding': binding(base / 'retrieved.json'),
               'receipt_binding': binding(base / 'receipt.json'),
               'historical_reference_binding': binding(base / 'timeline.json')}
        rows.append(row)
        pending.append((ROOT / p['expected_output_path'], result))
    for (target, result), row in zip(pending, rows):
        row['result_file_sha256'] = create_json(target, result)
        assert digest(load(target)) == row['result_sha256']
    seal = {
        'version': 'final-d0-reference-result-v1', 'plan_version': plan['version'],
        'artifact_schema_version': 'investigation-b0-v2', 'status': 'D0_COMPLETE',
        'reference_plan': binding(PLAN), 'positions': rows,
        'generation_execution_seal_sha256': generation['execution_sha256'],
        'scheduled_positions': 32, 'processed_positions': 32, 'additional_model_calls': 0,
        'deterministic_repeat_checks': 32, 'historical_reference_equal': 32,
        'implementation': list({r['path']: r for r in implementation}.values()),
        'execution_adapter': binding(Path(__file__)),
        'hash_convention': 'SHA-256(contracts.dumps(result).encode()); seal excludes seal_sha256',
    }
    seal['seal_sha256'] = digest(seal)
    create_json(SEAL, seal)
    saved = load(SEAL)
    assert digest({k: v for k, v in saved.items() if k != 'seal_sha256'}) == saved['seal_sha256']
    print(json.dumps({'D0': len(rows), 'model_calls': 0, 'seal_sha256': seal['seal_sha256']}))


if __name__ == '__main__':
    run()
