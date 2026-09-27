import sys,unittest
from pathlib import Path
from decimal import Decimal
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from report_investigation_api_usage import cost
class UsageCostTests(unittest.TestCase):
 def test_cached_tokens_not_double_counted(self):
  u={'input_tokens':1000000,'input_tokens_details':{'cached_tokens':250000},'output_tokens':500000}
  self.assertEqual(cost(u,'default'),Decimal('5.625'))
 def test_missing_cache_or_unknown_tier_not_zero_cost(self):
  self.assertIsNone(cost({'input_tokens':100,'output_tokens':10},'default'))
  self.assertIsNone(cost({'input_tokens':100,'input_tokens_details':{'cached_tokens':0},'output_tokens':10},'unknown'))
 def test_impossible_cached_count_rejected(self):
  self.assertIsNone(cost({'input_tokens':100,'input_tokens_details':{'cached_tokens':101},'output_tokens':10},'default'))
