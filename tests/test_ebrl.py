import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ebrl.contract import LeakageError, load_contract, load_ontology, load_verifier_rules
from ebrl.llm import LocalOnlyViolation, assert_local_endpoint
from ebrl.normalize import network_episodes, process_episodes
from ebrl.pipeline import investigate
from ebrl.reference import overlay_independent_labels, policy_reference
from ebrl.scorer import align_event, score_events
from ebrl.suite import build_suite
from ebrl.verifier import verify_row
from sherlock.parser import decode_apdus


def _row(artifact, network_id=None):
    if network_id is None:
        return artifact["ledger"][0]
    commands = {item["episode_id"]: item for item in artifact["episodes"]["command_episodes"]}
    for row in artifact["ledger"]:
        command = commands[row["command_episode_id"]]
        if network_id in command["evidence_ids"]:
            return row
    raise AssertionError(network_id)


class DecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load_contract()
        cls.ontology = load_ontology()
        cls.cases = {case["case_id"]: case for case in build_suite()}

    def run_case(self, case_id, method="P1"):
        return investigate(self.cases[case_id]["bundle"], self.contract, self.ontology, method=method)

    def test_open_is_bounded_association_not_execution(self):
        row = _row(self.run_case("syn_open_supported"))
        self.assertEqual(row["published_disposition"], "L")
        self.assertEqual(row["published_level"], "R2")
        self.assertFalse(any(row["published_flags"].values()))
        self.assertNotIn("open_ack", row["support_evidence_ids"])

    def test_acknowledgement_does_not_raise_level(self):
        row = _row(self.run_case("syn_open_supported"))
        self.assertEqual(row["published_level"], "R2")
        self.assertFalse(row["published_flags"]["execution"])
        self.assertFalse(row["published_flags"]["completion"])

    def test_wrong_asset_is_nonlink(self):
        row = _row(self.run_case("syn_wrong_asset"))
        self.assertEqual((row["published_disposition"], row["reason_code"]), ("N", "ASSET_CONTRADICTION"))

    def test_incompatible_semantics_is_nonlink(self):
        row = _row(self.run_case("syn_incompatible"))
        self.assertEqual(row["reason_code"], "SEMANTIC_INCOMPATIBILITY")

    def test_reverse_time_is_nonlink(self):
        row = _row(self.run_case("syn_reverse_time"))
        self.assertEqual(row["reason_code"], "TIME_ORDER_CONTRADICTION")

    def test_clock_skew_stays_temporal(self):
        row = _row(self.run_case("syn_clock_skew"))
        self.assertEqual((row["published_disposition"], row["published_level"]), ("L", "R1"))
        self.assertEqual(row["reason_code"], "CLOCK_COOC_ORDER_UNRESOLVED")

    def test_stale_is_unknown(self):
        row = _row(self.run_case("syn_stale"))
        self.assertEqual(row["published_disposition"], "U")
        self.assertEqual(row["reason_code"], "STALE_OR_BAD_QUALITY")

    def test_competition_keeps_nearer_command(self):
        artifact = self.run_case("syn_competition")
        near = _row(artifact, "near_act")
        far = _row(artifact, "far_act")
        self.assertEqual((near["published_disposition"], near["published_level"]), ("L", "R2"))
        self.assertEqual((far["published_disposition"], far["reason_code"]), ("U", "COMPETING_COMMAND"))

    def test_operational_response_reaches_r3_without_completion(self):
        row = _row(self.run_case("syn_operational_response"))
        self.assertEqual(row["published_level"], "R3")
        self.assertTrue(row["published_flags"]["execution"])
        self.assertFalse(row["published_flags"]["completion"])
        self.assertFalse(row["published_flags"]["causal"])

    def test_action_effect_reaches_r4(self):
        row = _row(self.run_case("syn_action_effect"))
        self.assertEqual(row["published_level"], "R4")
        self.assertTrue(row["published_flags"]["causal"])
        self.assertTrue(row["published_flags"]["completion"])
        self.assertFalse(row["published_flags"]["security"])

    def test_indirect_and_alias_and_select_abstain(self):
        self.assertEqual(_row(self.run_case("syn_indirect"))["reason_code"], "INDIRECT_PROPAGATION")
        self.assertEqual(_row(self.run_case("syn_alias_collision"))["reason_code"], "CONTEXT_ALIAS_COLLISION")
        self.assertEqual(_row(self.run_case("syn_select_only"))["reason_code"], "SELECT_WITHOUT_OPERATE")

    def test_direction_conflict(self):
        self.assertEqual(_row(self.run_case("syn_direction_conflict"))["reason_code"], "DIRECTION_CONTRADICTION")

    def test_unmapped_is_temporal_only(self):
        row = _row(self.run_case("syn_unmapped_temporal"))
        self.assertEqual((row["published_disposition"], row["published_level"]), ("L", "R1"))

    def test_pump_fixture_is_not_hardcoded_to_breakers(self):
        row = _row(self.run_case("syn_pump_portability"))
        self.assertEqual((row["published_disposition"], row["published_level"]), ("L", "R2"))

    def test_outside_window_is_not_a_candidate(self):
        artifact = self.run_case("syn_outside_window")
        self.assertEqual(artifact["candidate_manifest"]["candidate_count"], 0)
        self.assertEqual(len(artifact["episodes"]["command_episodes"]), 1)
        self.assertEqual(len(artifact["episodes"]["process_episodes"]), 1)

    def test_missing_value_is_not_zero(self):
        bundle = {
            "event_id": "syn_missing",
            "network_records": [],
            "process_records": [
                {"evidence_id": "a", "observed_at": 1, "asset_id": "x", "variable": "closed", "unit": "NONE", "value": True, "quality": [], "stale": False, "context": "MEASUREMENT", "parent_ids": []},
                {"evidence_id": "b", "observed_at": 2, "asset_id": "x", "variable": "closed", "unit": "NONE", "value": None, "quality": [], "stale": False, "context": "MEASUREMENT", "parent_ids": []},
                {"evidence_id": "c", "observed_at": 3, "asset_id": "x", "variable": "closed", "unit": "NONE", "value": True, "quality": [], "stale": False, "context": "MEASUREMENT", "parent_ids": []},
            ],
            "mappings": [],
        }
        self.assertEqual(process_episodes(bundle, self.contract), [])

    def test_select_before_operate_is_one_episode(self):
        bundle = {
            "event_id": "syn_sbo",
            "network_records": [
                {"evidence_id": "s", "observed_at": 10, "flow": "f", "format": "I", "type_id": 45, "cot": 6, "ca": 1, "ioa": 2, "value": 0, "qualifier_select": True, "is_retransmission": False, "tcp_ack_only": False, "parent_ids": []},
                {"evidence_id": "o", "observed_at": 11, "flow": "f", "format": "I", "type_id": 45, "cot": 6, "ca": 1, "ioa": 2, "value": 0, "qualifier_select": False, "is_retransmission": False, "tcp_ack_only": False, "parent_ids": []},
                {"evidence_id": "c", "observed_at": 11.2, "flow": "f", "format": "I", "type_id": 45, "cot": 7, "ca": 1, "ioa": 2, "value": 0, "qualifier_select": False, "is_retransmission": False, "tcp_ack_only": False, "parent_ids": ["s"]},
                {"evidence_id": "r", "observed_at": 11.3, "flow": "f", "format": "I", "type_id": 45, "cot": 6, "ca": 1, "ioa": 2, "value": 0, "qualifier_select": False, "is_retransmission": True, "tcp_ack_only": False, "parent_ids": ["o"]},
            ],
            "process_records": [],
            "mappings": [{"evidence_id": "m", "ca": 1, "ioa": 2, "asset_id": "breaker_7", "variable": "closed", "command_semantics": "open_breaker", "context": "MEASUREMENT", "unit": "NONE"}],
        }
        episodes = network_episodes(bundle, self.contract)
        self.assertEqual(len(episodes), 1)
        self.assertEqual(episodes[0]["phase"], "select_before_operate")
        self.assertEqual(episodes[0]["t_command"], 11)
        self.assertIn("c", episodes[0]["confirmation_ids"])
        self.assertNotIn("c", episodes[0]["evidence_ids"])

    def test_replay_hash_is_stable(self):
        first = self.run_case("syn_open_supported")
        second = self.run_case("syn_open_supported")
        self.assertEqual(first["artifact_sha256"], second["artifact_sha256"])
        self.assertEqual(first["candidate_manifest"]["freeze_sha256"], second["candidate_manifest"]["freeze_sha256"])

    def test_b1_links_wrong_asset_and_p1_does_not(self):
        p1 = _row(self.run_case("syn_wrong_asset", "P1"))
        b1 = _row(self.run_case("syn_wrong_asset", "B1"))
        self.assertEqual(p1["published_disposition"], "N")
        self.assertEqual((b1["published_disposition"], b1["published_level"]), ("L", "R1"))

    def test_report_does_not_promote_r2(self):
        artifact = self.run_case("syn_open_supported")
        text = artifact["report"]["statements"][0]["text"].lower()
        self.assertIn("does not establish execution", text)
        self.assertNotIn("caused the", text)
        self.assertNotIn("compromised", text)

    def test_iec104_command_apdu_decodes(self):
        payload = bytes([
            0x68, 0x0E,
            0x00, 0x00, 0x00, 0x00,
            0x2D, 0x01, 0x06, 0x00,
            0x0B, 0x00,
            0x46, 0x00, 0x00,
            0x00,
        ])
        messages = decode_apdus(payload)
        self.assertEqual(messages[0]["type"], 45)
        self.assertEqual(messages[0]["cot"], 6)


class VerifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load_contract()
        cls.ontology_doc = load_ontology()
        cls.rules = load_verifier_rules()

    def test_rule_table_loads(self):
        self.assertIn("retain", self.rules["actions"])
        self.assertGreaterEqual(len(self.rules["precedence"]), 10)

    def test_overclaim_is_downgraded(self):
        case = next(item for item in build_suite() if item["case_id"] == "syn_open_supported")
        artifact = investigate(case["bundle"], self.contract, self.ontology_doc, method="A_NO_CEILING")
        from ebrl.ontology import Ontology
        ontology = Ontology(self.ontology_doc)
        bundle = dict(case["bundle"])
        bundle["_command_episodes"] = artifact["episodes"]["command_episodes"]
        commands = {item["episode_id"]: item for item in artifact["episodes"]["command_episodes"]}
        processes = {item["episode_id"]: item for item in artifact["episodes"]["process_episodes"]}
        raw = artifact["ledger"][0]
        self.assertEqual(raw["raw_level"], "R4")
        self.assertTrue(raw["raw_flags"]["causal"])
        checked = verify_row(
            raw,
            artifact["candidate_manifest"]["candidates"][0],
            commands[raw["command_episode_id"]],
            processes[raw["process_episode_id"]],
            bundle,
            self.contract,
            ontology,
        )
        self.assertEqual(checked["published_level"], "R2")
        self.assertFalse(checked["published_flags"]["causal"])
        self.assertEqual(checked["verifier_action"], "downgrade")

    def test_hallucinated_id_is_invalid_not_abstention(self):
        case = next(item for item in build_suite() if item["case_id"] == "syn_open_supported")
        artifact = investigate(case["bundle"], self.contract, self.ontology_doc, method="P0")
        from ebrl.ontology import Ontology
        ontology = Ontology(self.ontology_doc)
        bundle = dict(case["bundle"])
        bundle["_command_episodes"] = artifact["episodes"]["command_episodes"]
        raw = dict(artifact["ledger"][0])
        raw["network_evidence_ids"] = ["does_not_exist"]
        commands = {item["episode_id"]: item for item in artifact["episodes"]["command_episodes"]}
        processes = {item["episode_id"]: item for item in artifact["episodes"]["process_episodes"]}
        checked = verify_row(
            raw,
            artifact["candidate_manifest"]["candidates"][0],
            commands[raw["command_episode_id"]],
            processes[raw["process_episode_id"]],
            bundle,
            self.contract,
            ontology,
        )
        self.assertFalse(checked["row_valid"])
        self.assertIsNone(checked["published_disposition"])

    def test_verifier_cannot_turn_unknown_into_nonlink(self):
        case = next(item for item in build_suite() if item["case_id"] == "syn_stale")
        artifact = investigate(case["bundle"], self.contract, self.ontology_doc, method="P1")
        self.assertEqual(artifact["ledger"][0]["published_disposition"], "U")


class ScorerTests(unittest.TestCase):
    def test_abstention_precision_is_undefined(self):
        events = [{
            "event_id": "e",
            "pairs": [{
                "valid": True, "disposition": "U", "linked": False, "admissible": False,
                "overpromoted": False, "path": False, "g": 1, "o_star": "L", "v_star": "U",
            }],
        }]
        metrics = score_events(events)["metrics"]
        self.assertIsNone(metrics["OLP"]["value"])
        self.assertEqual(metrics["OLR"]["value"], 0)

    def test_formula_matches_manuscript(self):
        events = [{
            "event_id": "e",
            "pairs": [
                {"valid": True, "disposition": "L", "linked": True, "admissible": True, "overpromoted": False, "path": True, "g": 1, "o_star": "L", "v_star": "L"},
                {"valid": True, "disposition": "L", "linked": True, "admissible": True, "overpromoted": False, "path": True, "g": 1, "o_star": "N", "v_star": "L"},
                {"valid": True, "disposition": "N", "linked": False, "admissible": False, "overpromoted": False, "path": False, "g": 1, "o_star": "N", "v_star": "N"},
            ],
        }]
        metrics = score_events(events)["metrics"]
        self.assertEqual(metrics["OLP"]["value"], 0.5)
        self.assertEqual(metrics["OLR"]["value"], 1)
        self.assertEqual(metrics["UOLR"]["value"], 0.5)
        self.assertEqual(metrics["EFRI"]["value"], 1)

    def test_policy_and_factual_axes_diverge(self):
        contract = load_contract()
        ontology = load_ontology()
        case = next(item for item in build_suite() if item["case_id"] == "syn_deceptive_cooccurrence")
        artifact = investigate(case["bundle"], contract, ontology, method="P1")
        from ebrl.ontology import Ontology
        reference = policy_reference(case["bundle"], artifact["episodes"], artifact["candidate_manifest"], contract, Ontology(ontology))
        self.assertEqual(reference["pairs"][0]["v_star"], "L")
        self.assertEqual(reference["pairs"][0]["g"], 0)
        labeled = overlay_independent_labels(reference, {reference["pairs"][0]["candidate_id"]: {"g": 1, "o_star": "N", "source": "synthetic_independent"}})
        scored = score_events([{
            "event_id": case["case_id"],
            "pairs": align_event(artifact["candidate_manifest"]["candidates"], artifact["ledger"], labeled["pairs"], case["bundle"]),
        }])
        self.assertEqual(scored["metrics"]["EAP"]["value"], 1)
        self.assertEqual(scored["metrics"]["UOLR"]["value"], 1)
        self.assertEqual(scored["factual_status"], "synthetic_or_independent")


class BoundaryTests(unittest.TestCase):
    def test_visible_bundle_rejects_evaluator_keys(self):
        contract = load_contract()
        ontology = load_ontology()
        case = next(item for item in build_suite() if item["case_id"] == "syn_open_supported")
        leaked = dict(case["bundle"])
        leaked["event_truth"] = "CYBER"
        with self.assertRaises(LeakageError):
            investigate(leaked, contract, ontology)

    def test_model_modules_do_not_import_reference_builder(self):
        src = ROOT / "src" / "ebrl"
        for name in ("pipeline.py", "policy.py", "proposer.py", "verifier.py", "baselines.py", "normalize.py", "candidates.py", "report.py", "llm.py"):
            path = src / name
            if not path.exists():
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module and "reference" in node.module:
                    self.fail(f"{name} imports {node.module}")

    def test_cloud_endpoint_is_rejected(self):
        with self.assertRaises(LocalOnlyViolation):
            assert_local_endpoint("https://api.openai.com/v1")
        with self.assertRaises(LocalOnlyViolation):
            assert_local_endpoint("https://192.0.2.10/api")
        assert_local_endpoint("http://127.0.0.1:11434")

    def test_same_candidates_for_every_method(self):
        contract = load_contract()
        ontology = load_ontology()
        case = next(item for item in build_suite() if item["case_id"] == "syn_competition")
        first = investigate(case["bundle"], contract, ontology, method="B0")
        for method in ("B1", "B2", "B3", "P0", "P1"):
            other = investigate(case["bundle"], contract, ontology, method=method)
            self.assertEqual(first["candidate_manifest"]["freeze_sha256"], other["candidate_manifest"]["freeze_sha256"])
            self.assertEqual(len(other["ledger"]), len(first["candidate_manifest"]["candidates"]))

    def test_contract_hash_stable(self):
        self.assertEqual(load_contract()["contract_sha256"], load_contract()["contract_sha256"])
        self.assertEqual(len(load_contract()["contract_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
