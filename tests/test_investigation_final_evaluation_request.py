"""Offline final-evaluation request construction. No provider call and no persisted request hash."""
import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / 'src'))

from investigation_dryrun.common import digest, file_hash, load
from investigation_dryrun.custody import development_ids
from investigation_final_offline.contracts import digest as commitment_digest
from investigation_final_offline import request
from investigation_r5.runner import build_request as build_development_r5_request
from investigation_r6.candidate import build_request as build_development_r6_request


def _forbid_network(*args, **kwargs):
    raise AssertionError('NETWORK FORBIDDEN')


class FinalEvaluationRequestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = load(ROOT / 'configs/investigation_events.v1.json')['evaluation']
        cls.event = cls.events[0]
        cls.manifest = load(ROOT / 'results/investigation-final-offline/generation_manifest.candidate.json')

    def build(self, cell, repetition=1, event=None):
        return request.build_final_evaluation_request(event or self.event, cell, repetition)

    def test_g0_optional_baseline_en(self):
        body = self.build('G0')
        self.assertEqual(body['model'], 'gpt-4.1-2025-04-14')
        self.assertEqual(body['max_output_tokens'], 24576)
        self.assertEqual(body['temperature'], 0)
        self.assertEqual(body['store'], False)
        self.assertEqual(body['truncation'], 'disabled')
        self.assertEqual(body['tools'], [])
        self.assertNotIn('seed', body)
        self.assertEqual(body['text']['format']['schema']['properties']['citation_mode']['const'], 'optional_baseline')
        self.assertEqual(json.loads(body['input'])['scope']['view'], 'EN')
        self.assertEqual(body['instructions'], (ROOT / 'prompts/investigation-v1-r5/G0.txt').read_text())

    def test_grounded_cells_use_required_schema_and_own_views(self):
        expected = {'G1-E': 'E', 'G1-N': 'N', 'G1-EN': 'EN'}
        for cell, view in expected.items():
            body = self.build(cell)
            self.assertEqual(body['model'], 'gpt-4.1-2025-04-14')
            self.assertEqual(body['max_output_tokens'], 24576)
            self.assertEqual(body['text']['format']['schema']['properties']['citation_mode']['const'], 'required')
            self.assertEqual(json.loads(body['input'])['scope']['view'], view)
            self.assertEqual(body['instructions'], (ROOT / request.CELLS[cell]['prompt']).read_text())

    def test_repetition_reuses_the_same_request_body(self):
        for cell in ('G0', 'G1-E', 'G1-N', 'G1-EN'):
            self.assertEqual(self.build(cell, 1), self.build(cell, 3))

    def test_digest_helper_accepts_request_without_persisting(self):
        body = self.build('G1-EN')
        self.assertEqual(len(digest(body)), 64)
        reloaded = load(ROOT / 'results/investigation-final-offline/generation_manifest.candidate.json')
        self.assertTrue(all(row['request_sha256'] is None and row['output_sha256'] is None for row in reloaded['positions']))

    def test_gold_paths_cannot_enter_request_construction(self):
        opened = []
        real_bytes, real_text = Path.read_bytes, Path.read_text

        def wrap_bytes(path, *args, **kwargs):
            opened.append(str(path))
            return real_bytes(path, *args, **kwargs)

        def wrap_text(path, *args, **kwargs):
            opened.append(str(path))
            return real_text(path, *args, **kwargs)

        with patch.object(Path, 'read_bytes', wrap_bytes), patch.object(Path, 'read_text', wrap_text):
            self.build('G0')
        self.assertTrue(opened)
        for path in opened:
            self.assertNotIn('PRIVATE_GOLD', path)
            self.assertNotIn('PRIVATE_REVIEW', path)
            self.assertNotIn('PRIVATE_EVALUATOR', path)
        gold = Path('/Users/Shared/ICIT2027-custody/v1/PRIVATE_EVALUATOR/PRIVATE_GOLD/annotation-v1/evaluation_gold_seal.json')
        with self.assertRaises(PermissionError):
            request.read_allowed(gold)

    def test_noncanonical_event_rejected(self):
        with self.assertRaises(PermissionError):
            request.build_final_evaluation_request(development_ids()[0], 'G0', 1)
        with self.assertRaises(PermissionError):
            request.build_final_evaluation_request('ev_' + 'ab' * 10, 'G1-E', 1)

    def test_invalid_cell_rejected(self):
        for cell in ('D0', 'V1-EN', 'B3', 'G1'):
            with self.assertRaises(ValueError):
                request.build_final_evaluation_request(self.event, cell, 1)

    def test_invalid_repetition_rejected(self):
        for repetition in (0, 4, -1):
            with self.assertRaises(ValueError):
                request.build_final_evaluation_request(self.event, 'G0', repetition)

    def test_authorization_false_rejected(self):
        with self.assertRaises(PermissionError):
            request.require_generation_authorization({'evaluation_generation_authorized': False})
        real = request.load_authorized_configuration

        def unauthorized():
            config = copy.deepcopy(real())
            config['evaluation_generation_authorized'] = False
            return config

        with patch.object(request, 'load_authorized_configuration', unauthorized):
            with self.assertRaises(PermissionError):
                request.build_final_evaluation_request(self.event, 'G0', 1)

    def test_build_does_not_require_credentials_or_network(self):
        with patch('socket.create_connection', _forbid_network), patch('socket.socket.connect', _forbid_network), patch('urllib.request.urlopen', _forbid_network):
            body = self.build('G1-N', 2)
        self.assertEqual(body['max_output_tokens'], 24576)

    def test_development_builders_still_reject_evaluation_events(self):
        with self.assertRaises(PermissionError):
            build_development_r5_request(self.event, 'G0', {}, {})
        position = {'event_id': self.event, 'cell_id': 'G0', 'view': 'EN'}
        with patch('investigation_r6.candidate.read_bundle', side_effect=AssertionError('evaluation bundle read')) as reader:
            with self.assertRaises(PermissionError):
                build_development_r6_request(position)
            reader.assert_not_called()

    def test_development_r5_request_remains_8192(self):
        event = development_ids()[0]
        from investigation_r5.core import read_bundle
        bundle, receipt = read_bundle(event, 'EN')
        body = build_development_r5_request(event, 'G0', bundle, receipt)
        self.assertEqual(body['model'], 'gpt-4.1-2025-04-14')
        self.assertEqual(body['max_output_tokens'], 8192)

    def test_manifest_commitments_and_hash(self):
        manifest = self.manifest
        body = {key: value for key, value in manifest.items() if key != 'manifest_sha256'}
        self.assertEqual(commitment_digest(body), manifest['manifest_sha256'])
        self.assertEqual(manifest['gold_seal_sha256'], request.GOLD_SEAL_SHA256)
        self.assertEqual(manifest['custody_log_sha256'], request.CUSTODY_LOG_SHA256)
        self.assertEqual(manifest['matching_support_policy_sha256'], request.MATCHING_SUPPORT_POLICY_SHA256)
        self.assertEqual(manifest['config']['sha256'], request.AUTHORIZED_CONFIG_SHA256)
        self.assertEqual(file_hash(ROOT / manifest['config']['path']), request.AUTHORIZED_CONFIG_SHA256)
        self.assertEqual(manifest['historical_preauthorization_config_sha256'], request.HISTORICAL_PREAUTHORIZATION_CONFIG_SHA256)
        self.assertTrue(manifest['evaluation_generation_authorized'])
        self.assertEqual(manifest['model_call_count_at_freeze'], 0)
        self.assertEqual(len(manifest['positions']), 384)
        counts = {cell: 0 for cell in ('G0', 'G1-E', 'G1-N', 'G1-EN')}
        for row in manifest['positions']:
            counts[row['cell_id']] += 1
            self.assertIsNone(row['request_sha256'])
            self.assertIsNone(row['output_sha256'])
            self.assertEqual(row['expected_config_hash'], request.AUTHORIZED_CONFIG_SHA256)
            self.assertNotEqual(row['expected_config_hash'], request.HISTORICAL_PREAUTHORIZATION_CONFIG_SHA256)
        self.assertEqual(counts, {cell: 96 for cell in counts})

    def test_all_384_requests_build_offline(self):
        with patch('socket.create_connection', _forbid_network), patch('socket.socket.connect', _forbid_network), patch('urllib.request.urlopen', _forbid_network):
            result = request.build_all_final_evaluation_requests()
        self.assertEqual(result['built'], 384)
        self.assertEqual(result['by_cell'], {'G0': 96, 'G1-E': 96, 'G1-N': 96, 'G1-EN': 96})
        self.assertEqual(result['unique_request_bodies'], 128)
        self.assertEqual(result['persisted_request_or_output_hashes'], 0)


if __name__ == '__main__':
    unittest.main()
