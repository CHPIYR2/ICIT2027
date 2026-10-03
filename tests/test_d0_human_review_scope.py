"""Corrected scope: D0 stays a deterministic reference and is not R1-scored."""
import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investigation_final_offline.contracts import CELLS, METRICS
from investigation_final_offline.fixtures import fixture_matrix
from investigation_final_offline.reporting import aggregate, products
from investigation_final_offline.human_review_scope import (
    aggregate_human_scored, products_human_scored, deterministic_d0_diagnostic, validate_correction)
from investigation_final_offline.scoring import IncompleteReview


class HumanReviewScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.strata, _inputs = fixture_matrix()
        cls.full = aggregate(cls.rows, cls.strata)
        cls.corrected = aggregate_human_scored(cls.rows, cls.strata)
        label = 'SYNTHETIC_TEST_ONLY_NOT_PAPER_RESULTS'
        cls.full_products = products(cls.rows, cls.strata, data_label=label)
        cls.corrected_products = products_human_scored(cls.rows, cls.strata, data_label=label)

    def test_d0_diagnostic_does_not_require_r1_ledger(self):
        diagnostic = deterministic_d0_diagnostic(
            {'schema_version': 'investigation-b0-v2'},
            {'status': 'DETERMINISTIC_REFERENCE', 'repetition': 0, 'cell_id': 'D0', 'event_id': 'event'})
        self.assertFalse(diagnostic['requires_r1_ledger'])
        self.assertTrue(diagnostic['counted_once'])
        with self.assertRaises(IncompleteReview):
            deterministic_d0_diagnostic({'schema_version': 'investigation-b0-v2'},
                                        {'status': 'DELIVERED', 'repetition': 0, 'cell_id': 'D0', 'event_id': 'event'})

    def test_human_scored_macro_micro_exclude_d0_and_preserve_research_cells(self):
        self.assertNotIn('D0', self.corrected['conditions'])
        self.assertIn('D0', self.full['conditions'])
        for metric in METRICS:
            self.assertNotIn('D0', self.corrected['macro'][metric])
            self.assertNotIn('D0', self.corrected['micro'][metric])
            self.assertIn('D0', self.full['macro'][metric])
            for cell in CELLS:
                self.assertEqual(self.full['macro'][metric][cell], self.corrected['macro'][metric][cell])
                self.assertEqual(self.full['micro'][metric][cell], self.corrected['micro'][metric][cell])

    def test_primary_products_keep_the_same_membership(self):
        for key in ('table4', 'table5', 'table6', 'table7', 'figure2', 'rq1_funnel'):
            self.assertEqual(self.full_products[key], self.corrected_products[key])
        self.assertEqual([row['condition'] for row in self.corrected_products['table7']], list(CELLS))
        self.assertTrue(all(row['view'] in ('E', 'N', 'EN') for row in self.corrected_products['rq1_funnel']))
        self.assertTrue(all(row['condition'] in CELLS for row in self.corrected_products['figure2']))

    def test_corrected_review_universe(self):
        result = validate_correction()
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['human_review_count'], 477)
        self.assertEqual(result['counts_by_cell'],
                         {'G0': 96, 'G1-E': 93, 'G1-N': 96, 'G1-EN': 96, 'V1-EN': 96})
        self.assertEqual(result['d0_diagnostics'], 32)
        self.assertEqual(result['version'], 'r1-human-review-scope-correction-v1')
        self.assertEqual(result['seal_sha256'], '39d65267724f4b1a3d291b1a28e4e1b5d7650f5a755f4cbbaef101f0aa94e6f0')
