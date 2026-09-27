"""Manifest and numerical representation tests; not model evaluation."""
import json
import math
from pathlib import Path
import struct
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
from audit_pilot_numeric_precision import float32_ulp
from verify_investigation_freeze_candidate import verify
from prepare_investigation_freeze_v1 import prepare


class FreezePreparationTests(unittest.TestCase):
    def test_float32_spacing_is_magnitude_dependent(self):
        self.assertEqual(float32_ulp(1.0),2**-23)
        self.assertEqual(float32_ulp(-1.0),2**-23)
        self.assertEqual(float32_ulp(2**24),2)
        self.assertEqual(float32_ulp(0.0),2**-149)

    def test_eight_digit_rounding_preserves_small_magnitude(self):
        for value in (1e-9,1.,1e7,-1e-8,-12345.6):
            x=struct.unpack('<f',struct.pack('<f',value))[0]
            self.assertLessEqual(abs(float(f'{x:.8g}')-x)/abs(x),5e-8)
        self.assertNotEqual(float(f'{1e-9:.8g}'),0)
        self.assertEqual(float(f'{1e-9:.6f}'),0)

    def test_protocol_not_implicitly_frozen(self):
        cfg=json.loads((ROOT/'configs/investigation_protocol.v1.freeze_candidate.json').read_text())
        self.assertFalse(cfg['protocol_frozen']);self.assertIsNone(cfg['numeric_tolerance_profile'])
        self.assertFalse(cfg['model_comparison_primary_experiments'])
        self.assertFalse(cfg['llm_calls_authorized'])

    def test_no_model_or_prompt_invented(self):
        cfg=json.loads((ROOT/'configs/investigation_model.v1.pending.json').read_text())
        for key in ('provider','exact_model_snapshot_version','temperature','seed','max_input_tokens','max_output_tokens','prompt_version','prompt_hash'):
            self.assertIsNone(cfg[key])
        self.assertTrue(cfg['B4_uses_exact_B3_output_replay'])

    def test_literal_types_and_zero_time_order_tolerance(self):
        cfg=json.loads((ROOT/'configs/investigation_matching.v1.candidate.json').read_text())
        self.assertEqual(cfg['exact_rules']['claim_type'],'exact_literal')
        self.assertEqual(cfg['duration_rendering']['ordering_tolerance'],0)
        self.assertFalse(cfg['natural_language_similarity_is_correctness_metric'])
        self.assertIsNone(cfg['active_numeric_profile'])

    def test_snapshot_seals_and_annotation_preservation(self):
        self.assertEqual(verify()['reviewed_annotation_files_byte_identical'],4)

    def test_prepare_refuses_version_overwrite(self):
        path=ROOT/'annotations/gold/pilot-v1/manifest.json';before=path.read_bytes()
        with self.assertRaises(ValueError):prepare()
        self.assertEqual(path.read_bytes(),before)


if __name__=='__main__':unittest.main()
