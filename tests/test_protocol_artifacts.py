"""Cross-artifact research invariants for the generated audit/proposal files."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class ProtocolArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.split=json.loads((ROOT/'configs/split.proposed.json').read_text())
        cls.catalog=json.loads((ROOT/'data/evaluator/event_catalog.json').read_text())['events']
        cls.summary=json.loads((ROOT/'data/manifests/content_audit/summary.json').read_text())

    def test_scenario_holdout_has_no_event_overlap_or_omission(self):
        dev=set(self.split['development']);held=set(self.split['held_out'])
        self.assertFalse(dev & held)
        self.assertEqual(dev | held,{e['episode_id'] for e in self.catalog})
        for e in self.catalog:
            self.assertEqual(e['episode_id'] in dev,e['scenario']=='01-Basic')

    def test_cv_uses_only_development_and_each_fold_has_both_classes(self):
        folds=self.split['development_fold_assignment']
        self.assertEqual(set(folds),set(self.split['development']))
        labels={e['episode_id']:e['event_truth'] for e in self.catalog}
        for fold in range(5):
            self.assertEqual({labels[e] for e in folds if folds[e]==fold},{'CYBER','BENIGN'})

    def test_catalog_hash_prevents_silent_target_changes(self):
        data=(ROOT/'data/evaluator/event_catalog.json').read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(),self.split['event_catalog_sha256'])

    def test_proposed_fixed_windows_do_not_share_observations_between_events(self):
        for i,a in enumerate(self.catalog):
            for b in self.catalog[i+1:]:
                if (a['scenario'],a['recording'])!=(b['scenario'],b['recording']):continue
                self.assertGreaterEqual(abs(a['start']-b['start']),120)

    def test_reports_match_sources_and_manifest_completion(self):
        manifest=json.loads((ROOT/'data/manifests/sherlock_manifest.json').read_text())
        self.assertTrue(manifest['phase1_complete'])
        archives={a['sha256'] for a in manifest['archives']}
        for r in self.summary['reports']:
            self.assertIn(r['archive_sha256'],archives)
            self.assertEqual(hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest(),r['sha256'])
        self.assertEqual(sum(r['events'] for r in self.summary['recordings']),len(self.catalog))

    def test_E_candidates_exclude_configuration_and_all_N_payloads(self):
        fields=json.loads((ROOT/'data/manifests/field_catalog.proposed.json').read_text())['entries']
        for f in fields:
            self.assertFalse(f['N_payload_allowed'])
            self.assertFalse(f['initial_value_allowed'])
            if f['candidate_E_allowed_if_observed']:
                self.assertEqual(f['context'],'MEASUREMENT')
                self.assertNotIn(f['attribute'],['test','tap_position','closed','connected'])


if __name__=='__main__':unittest.main()
