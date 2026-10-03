"""Scope routing must preserve frozen replay semantics and provenance checks."""
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from run_investigation_final_replay import replay_engine
from test_investigation_dryrun_regression import ReplayTests, EID, OTHER
from investigation_dryrun.common import digest
from investigation_dryrun import claims, runner
from investigation_r5 import core, runner as r5


class FinalReplayAdapterTests(unittest.TestCase):
    def setUp(self):
        self.b, self.r, self.raw, self.m = ReplayTests().setup_replay()
        self.m.update(cell_id='G1-EN', view='EN', citation_mode='required')
        self.engine = replay_engine([EID])

    def test_exact_equivalence_and_original_guards_unchanged(self):
        modules = (claims, runner, core, r5)
        original = [dict(vars(m)) for m in modules]
        self.assertEqual(self.engine(EID, self.raw, self.m, self.b, self.r),
                         r5.replay_bytes(EID, self.raw, self.m, self.b, self.r))
        for module, namespace in zip(modules, original):
            self.assertEqual(dict(vars(module)), namespace)

    def test_outside_authorized_scope_rejected(self):
        with self.assertRaises(PermissionError):
            replay_engine([OTHER])(EID, self.raw, self.m, self.b, self.r)

    def test_raw_identity_change_rejected(self):
        with self.assertRaises(ValueError):
            self.engine(EID, self.raw + b' ', self.m, self.b, self.r)

    def test_receipt_change_rejected(self):
        r = copy.deepcopy(self.r)
        r['omitted_original_count'] += 1
        with self.assertRaises(ValueError):
            self.engine(EID, self.raw, self.m, self.b, r)

    def test_wrong_source_cell_rejected(self):
        for cell in ('G0', 'G1-E', 'G1-N'):
            with self.assertRaises(ValueError):
                self.engine(EID, self.raw, {**self.m, 'cell_id': cell}, self.b, self.r)

    def test_invalid_envelope_is_not_repaired(self):
        from investigation_final_offline.contracts import sha
        raw = self.raw[:-5]
        with self.assertRaises(runner.RetryableDelivery):
            self.engine(EID, raw, {**self.m, 'output_sha256': sha(raw)}, self.b, self.r)


if __name__ == '__main__':
    unittest.main()
