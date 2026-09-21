"""Read-only verification of completed exploratory artifacts; no fitting or scoring."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments'))
import gzip
import json
from collections import defaultdict
import numpy as np
import run_observability_v2 as run


def main():
    root, out = run.ROOT, run.OUT
    run.verify_lock()
    split, _ = run.verify_protocol()
    assert not set(split['development']) & set(split['held_out'])
    fitting = run.read_json(out / 'development/fitting.json')
    assert fitting['final_fit_ids'] == split['development']
    assert len(fitting['fold_fits']) == 120
    for fit in fitting['fold_fits']:
        train, valid = set(fit['training_ids']), set(fit['validation_ids'])
        assert not train & valid and train | valid == set(split['development'])
        assert valid == {e for e in split['development'] if split['development_fold_assignment'][e] == fit['fold']}
    models = run.read_json(out / 'development/models.json')
    assert len(models) == 24
    for path, digest in models.items():
        assert run.sha256(root / path) == digest
    totals = {}
    for partition, destination, expected_count in [('development', 'development', 35), ('held_out', 'evaluation', 84)]:
        rows = run.load_rows(partition)
        assert len(rows) == expected_count
        originals = {r['episode_id']: r for r in run.read_json(root / f'data/processed/v2/{partition}_features.json')['rows']}
        for row in rows:
            old = originals[row['episode_id']]
            assert row['E'] == {n: old['values'][n] for n in run.E_NAMES}
            assert row['N_FULL'] == {n: old['values'][n] for n in run.N_NAMES}
            assert run.sha256(root / row['evidence_path']) == row['evidence_sha256']
            with gzip.open(root / row['visibility_path'], 'rt') as file:
                receipt = json.load(file)
            assert receipt['canonical_evidence_sha256'] == row['evidence_sha256']
            assert receipt['protocol_lock_sha256'] == run.sha256(run.LOCK)
            all_ids = set(receipt['levels']['60']['visible_packet_ids'])
            previous = all_ids
            for duration in (60, 45, 30, 15):
                level = receipt['levels'][str(duration)]
                visible, hidden = set(level['visible_packet_ids']), set(level['hidden_packet_ids'])
                assert len(visible) == len(level['visible_packet_ids'])
                assert len(hidden) == len(level['hidden_packet_ids'])
                assert not visible & hidden and visible | hidden == all_ids
                assert visible <= previous
                assert level['post_visible_seconds'] == duration and level['pre_visible_seconds'] == 60
                previous = visible
        predictions = run.read_json(out / destination / 'predictions.json')['rows']
        grouped = defaultdict(dict)
        for prediction in predictions:
            key = prediction['regime'], prediction['model'], prediction['view']
            assert prediction['episode_id'] not in grouped[key]
            grouped[key][prediction['episode_id']] = prediction
        assert len(grouped) == 33 and len(predictions) == 33 * expected_count
        metadata, truth = run.metadata(rows)
        metrics = run.read_json(out / destination / 'metrics.json')['metrics']
        for (regime, model, view), values in grouped.items():
            assert set(values) == set(split[partition])
            scores = np.array([values[r['episode_id']]['score'] for r in rows])
            assert np.isfinite(scores).all() and ((scores >= 0) & (scores <= 1)).all()
            assert [values[r['episode_id']]['event_truth'] for r in rows] == truth.tolist()
            assert run.grouped_metrics(truth, scores, metadata) == metrics[regime][model][view]
        for reference in run.reuse_references(rows, partition):
            assert grouped[(reference['regime'], reference['model'], reference['view'])][reference['episode_id']] == reference
        transitions = run.read_json(out / f'transitions/{destination}.json')['rows']
        assert len(transitions) == 15 * expected_count
        seen = set()
        for transition in transitions:
            key = transition['regime'], transition['model'], transition['episode_id']
            assert key not in seen
            seen.add(key)
            n = grouped[(key[0], key[1], 'N')][key[2]]
            en = grouped[(key[0], key[1], 'EN')][key[2]]
            assert transition['N_score'] == n['score'] and transition['EN_score'] == en['score']
            nc = (n['score'] >= .5) == n['event_truth']
            ec = (en['score'] >= .5) == en['event_truth']
            status = ('unchanged_both_correct' if nc else 'unchanged_both_wrong') if nc == ec else ('corrected_N' if ec else 'hurt_N')
            assert transition['transition'] == status
        bootstrap = run.read_json(out / destination / 'paired_bootstrap.json')
        scenes = np.array([m['scenario'] for m in metadata])
        for regime, model in [('N_TRANSPORT_T60', 'random_forest'), ('N_DEGRADED_TRANSPORT_T45', 'gradient_boosting')]:
            scores = {view: np.array([grouped[(regime, model, view)][r['episode_id']]['score'] for r in rows]) for view in ['N', 'EN']}
            scores['E'] = np.array([grouped[('E_REFERENCE', model, 'E')][r['episode_id']]['score'] for r in rows])
            assert run.contrasts(truth, scores, scenes, bootstrap['config']) == bootstrap['results'][regime][model]['overall']
        totals[destination] = {'events': expected_count, 'conditions': len(grouped), 'predictions': len(predictions), 'transitions': len(transitions)}
    manifest = run.read_json(out / 'evaluation/run_manifest.json')
    for key, file in [('prediction_sha256', 'predictions.json'), ('metrics_sha256', 'metrics.json'), ('bootstrap_sha256', 'paired_bootstrap.json')]:
        assert manifest[key] == run.sha256(out / 'evaluation' / file)
    assert manifest['protocol_lock_sha256'] == run.sha256(run.LOCK)
    tests = run.read_json(out / 'tests.json')
    assert tests['passed'] and tests['count'] == 48
    assert tests['log_sha256'] == run.sha256(out / 'tests.log')
    run.save_json(out / 'verification.json', {
        'verified_at_utc': run.now(), 'interpretation': run.TAG, 'passed': True,
        'verifier_sha256': run.sha256(Path(__file__)), 'protocol_lock_sha256': run.sha256(run.LOCK),
        'original_frozen_artifacts_unchanged': True, 'trained_models': len(models),
        'basic_only_fold_fits_verified': len(fitting['fold_fits']), 'unit_tests_passed': 48,
        'canonical_and_visibility_hashes_verified': 119, 'nested_masks_verified': True,
        'E_and_FULL_features_unchanged': True, 'all_grouped_metrics_recomputed': True,
        'original_reference_rows_exact_match': True, 'paired_bootstrap_spot_checks': 4,
        'transition_records_verified': True, 'counts': totals,
    })
    print(json.dumps(totals, indent=2))
    print('All completed-artifact checks passed; no models refitted or rescored.')


if __name__ == '__main__':
    main()
