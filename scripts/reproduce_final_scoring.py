#!/usr/bin/env python3
"""Validate the public scoring inputs and reproduce the frozen score tables."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
import tarfile
import types

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "src"))

from investigation_final_offline import scoring
from investigation_final_offline.contracts import digest, sha
from investigation_final_offline.reporting import products

INPUTS = ROOT / "results/investigation-final-scoring-public/public_scoring_inputs.tar.gz"
RESULTS = ROOT / "results/investigation-final-scoring-v1"
COMMITMENT_PATH = RESULTS / "scoring_input_commitment.json"
AUTHORIZATION_PATH = RESULTS / "scoring_authorization.json"
RESULT_PATH = RESULTS / "final_scoring_result.json"
CORRECTION_PATH = ROOT / "results/investigation-final-r1-scope-correction-v1/correction.seal.json"
POLICY_PATH = ROOT / "configs/investigation-r5/matching.json"
SECRET_PATTERN = re.compile(
    rb"sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|"
    rb"Bearer[ \t]+[A-Za-z0-9._~-]{20,}|"
    rb"-----BEGIN (?:RSA|OPENSSH|EC) PRIVATE KEY-----|"
    rb"api[_-]?key[ \t]*[:=][ \t]*[\"'][^\"']{12,}[\"']",
    re.IGNORECASE,
)


def load_json(raw: bytes):
    return json.loads(raw.decode("utf-8"))


def require(condition: bool, message: str):
    if not condition:
        raise ValueError(message)


def archive_files():
    require(INPUTS.is_file(), f"Missing public scoring inputs: {INPUTS}")
    found = {}
    with tarfile.open(INPUTS, "r:gz") as archive:
        for member in archive.getmembers():
            if not member.isfile():
                continue
            path = PurePosixPath(member.name)
            require(not path.is_absolute() and ".." not in path.parts,
                    "Unsafe archive member path")
            require(path.parts[0] == "public-scoring-inputs" and len(path.parts) > 1,
                    "Unexpected archive member root")
            key = str(PurePosixPath(*path.parts[1:]))
            require(key not in found, f"Duplicate archive member: {key}")
            stream = archive.extractfile(member)
            require(stream is not None, f"Cannot read archive member: {key}")
            raw = stream.read()
            require(not SECRET_PATTERN.search(raw),
                    f"Credential-like value in public input: {key}")
            require("response.raw" not in key and "request.canonical" not in key,
                    f"Provider request/response archive included: {key}")
            found[key] = raw
    manifest = load_json(found["manifest.json"])
    expected = manifest["files"]
    require(digest({k: v for k, v in manifest.items()
                    if k != "public_input_commitment_sha256"})
            == manifest["public_input_commitment_sha256"],
            "Public input commitment mismatch")
    require(set(found) == {"manifest.json", *(item["path"] for item in expected)},
            "Public archive inventory differs from its manifest")
    for item in expected:
        raw = found[item["path"]]
        require(sha(raw) == item["sha256"] and len(raw) == item["bytes"],
                f"Public input hash/size mismatch: {item['path']}")
        if item["path"].startswith(("gold/", "ledgers/")):
            require_no_private_notes(load_json(raw), item["path"])
    return manifest, found


def require_no_private_notes(value, label):
    if isinstance(value, dict):
        for key, item in value.items():
            if key in ("notes", "reviewer_notes", "discussion", "conversation"):
                if isinstance(item, str):
                    require(not item.strip(), f"Nonempty private note in {label}")
            require_no_private_notes(item, label)
    elif isinstance(value, list):
        for item in value:
            require_no_private_notes(item, label)


class PublicScope:
    """Use the sealed scope correction with portable public evidence views."""

    def __init__(self, files, records):
        self.gold = {}
        self.bundles = {}
        self.context = {}
        for record in records:
            bundle = load_json(files[record["bundle"]["path"]])
            key = (record["event_id"], bundle["view"])
            self.bundles[key] = bundle
        contexts = load_json(files["scope_contexts.json"])
        for row in contexts:
            scope = row["scope_context"]
            require(digest(scope) == row["scope_context_sha256"],
                    "Scope context hash mismatch")
            event_context = self.context.setdefault(row["event_id"], {})
            scope_id = scope["evidence_id"]
            require(scope_id not in event_context, "Duplicate scope identity")
            event_context[scope_id] = {
                "evidence_id": scope_id,
                "sha256": digest(scope),
                "views": [row["view"]],
            }

    def evidence_index(self, gold, policy):
        require(policy == POLICY_SHA256, "Matching policy hash mismatch")
        facts, aliases, opportunities, evidence = scoring.validate_gold(gold, policy)
        extra = self.context[gold["event_id"]]
        require(not (set(evidence) & set(extra)), "Scope/source identity collision")
        return facts, aliases, opportunities, {**evidence, **extra}

    def check_bundle(self, record, bundle):
        expected = self.bundles[(record["event_id"], bundle["view"])]
        require(bundle == expected, "Bundle differs from the committed public view")

    def score_reviewed(self, record, gold, bundle, ledger, raw, stage):
        self.check_bundle(record, bundle)
        namespace = {**scoring.score.__globals__, "validate_gold": self.evidence_index}
        fn = types.FunctionType(scoring.score.__code__, namespace,
                                scoring.score.__name__, scoring.score.__defaults__,
                                scoring.score.__closure__)
        return fn(ledger, gold, bundle, raw, stage,
                  matching_policy_sha256=POLICY_SHA256)

    def score_failure(self, record, gold, bundle):
        self.check_bundle(record, bundle)
        namespace = {**scoring.score_delivery_failure.__globals__,
                     "validate_gold": self.evidence_index}
        fn = types.FunctionType(scoring.score_delivery_failure.__code__, namespace,
                                scoring.score_delivery_failure.__name__,
                                scoring.score_delivery_failure.__defaults__,
                                scoring.score_delivery_failure.__closure__)
        return fn(record["event_id"], record["cell_id"], record["repetition"],
                  gold, bundle, record["delivery_receipt"],
                  matching_policy_sha256=POLICY_SHA256)


def main():
    global POLICY_SHA256
    commitment = load_json(COMMITMENT_PATH.read_bytes())
    require(digest({k: v for k, v in commitment.items()
                    if k != "commitment_sha256"}) == commitment["commitment_sha256"],
            "Frozen scoring input commitment is invalid")
    require(commitment["commitment_sha256"]
            == "706fbbb5e8561981d3d0b2fc7f31aa139449bfc1a911b98801a456965fc8b1ad",
            "Unexpected frozen scoring commitment")
    POLICY_SHA256 = sha(POLICY_PATH.read_bytes())
    require(POLICY_SHA256 == commitment["matching_policy_sha256"],
            "Frozen matching policy changed")
    authorization = load_json(AUTHORIZATION_PATH.read_bytes())
    require(digest(authorization) == commitment["separate_scoring_authorization_sha256"],
            "Scoring authorization hash mismatch")
    correction = load_json(CORRECTION_PATH.read_bytes())
    require(digest({k: v for k, v in correction.items() if k != "seal_sha256"})
            == correction["seal_sha256"] == commitment["correction_seal_sha256"],
            "R1 scope-correction seal mismatch")

    manifest, files = archive_files()
    require(manifest["source_commitment_sha256"] == commitment["commitment_sha256"],
            "Public package is bound to a different scoring commitment")
    require(manifest["source_authorization_sha256"]
            == commitment["separate_scoring_authorization_sha256"],
            "Public package authorization binding mismatch")
    require(manifest["source_scope_mapping_sha256"] == commitment["scope_mapping_sha256"],
            "Public package scope-mapping binding mismatch")
    require(manifest["source_r1_packet_manifest_sha256"]
            == commitment["r1_packet_manifest_sha256"],
            "Public package R1 manifest binding mismatch")
    require(manifest["matching_policy_sha256"] == POLICY_SHA256,
            "Public package policy binding mismatch")
    require(manifest["frozen_seals"] == commitment["frozen_seals"],
            "Frozen generation/V1/D0/gold seal set mismatch")
    for path, expected_hash in manifest["schema_hashes"].items():
        require(sha((ROOT / path).read_bytes()) == expected_hash,
                f"Frozen schema hash mismatch: {path}")
    for path, expected_hash in manifest["scorer_code_hashes"].items():
        require(sha((ROOT / path).read_bytes()) == expected_hash,
                f"Scorer implementation hash mismatch: {path}")
    records = load_json(files["positions.json"])
    require(len(records) == 480, "Expected 480 committed scoring positions")
    require(sum(r["kind"] == "REVIEWED_OUTPUT" for r in records) == 477,
            "Expected 477 completed R1 ledgers")
    require(sum(r["kind"] == "NO_PROVIDER_DELIVERY" for r in records) == 3,
            "Expected three committed provider-incomplete positions")
    require(len(load_json(files["scope_contexts.json"])) == 96,
            "Expected 32 events times three frozen view scopes")
    scope = PublicScope(files, records)
    original_reviewed = {x["position_id"]: x for x in commitment["reviewed_positions"]}
    original_failures = {x["position_id"]: x
                         for x in commitment["invalid_provider_delivery_positions"]}
    scores = []
    for record in records:
        gold = load_json(files[record["gold"]["path"]])
        bundle = load_json(files[record["bundle"]["path"]])
        expected = (original_reviewed if record["kind"] == "REVIEWED_OUTPUT"
                    else original_failures)[record["position_id"]]
        require(record["source_commitment"] == expected,
                f"Position commitment mismatch: {record['position_id']}")
        require(digest(gold) == expected["gold_sha256"],
                f"Gold input mismatch: {record['position_id']}")
        require(bundle["event_id"] == record["event_id"],
                "Bundle event identity mismatch")
        if record["kind"] == "REVIEWED_OUTPUT":
            ledger_raw = files[record["ledger"]["path"]]
            raw = files[record["raw"]["path"]]
            stage = files[record["stage"]["path"]]
            ledger = load_json(ledger_raw)
            require(sha(ledger_raw) == expected["review_ledger"]["sha256"],
                    f"R1 ledger hash mismatch: {record['review_item_id']}")
            require(sha(raw) == expected["raw"]["sha256"]
                    and sha(stage) == expected["stage"]["sha256"],
                    f"Frozen generation output hash mismatch: {record['position_id']}")
            require(ledger["delivery_receipt"] == record["delivery_receipt"],
                    "Ledger delivery receipt differs")
            result = scope.score_reviewed(record, gold, bundle, ledger, raw, stage)
        else:
            require(record["delivery_receipt"] == expected["delivery_receipt"],
                    "Provider failure receipt differs")
            result = scope.score_failure(record, gold, bundle)
        result.update(frozen_evaluation_commitment=commitment["commitment_sha256"],
                      scoring_authorization=commitment["separate_scoring_authorization_sha256"])
        scores.append(result)

    stored_runs = load_json((RESULTS / "scored_runs.json").read_bytes())
    score_key = lambda row: (row["event_id"], row["cell_id"], row["repetition"])
    require({score_key(x): x for x in scores} == {score_key(x): x for x in stored_runs},
            "Recomputed per-run scores differ from the committed scored-run file")
    report = products(scores, commitment["scenario_strata"],
                      data_label=commitment["data_label"])
    report["protocol_frozen"] = commitment["protocol_frozen"]
    # Preserve the committed invalid-delivery order from the frozen commitment.
    report["delivery_exclusions"] = [
        {"event_id": x["event_id"], "cell_id": x["cell_id"],
         "repetition": x["repetition"]}
        for x in commitment["invalid_provider_delivery_positions"]
    ]
    original = load_json(RESULT_PATH.read_bytes())
    # D0 is a sealed descriptive reference and is outside subjective R1 scoring.
    # Preserve its committed diagnostic block while recomputing all 480 scored runs.
    reconstructed = dict(report)
    reconstructed.update(
        d0_diagnostics=original["d0_diagnostics"],
        r1_completed=commitment["completed_r1_items"],
        invalid_provider_delivery_runs=len(commitment["invalid_provider_delivery_positions"]),
        correction_seal_sha256=commitment["correction_seal_sha256"],
        scoring_input_commitment_sha256=commitment["commitment_sha256"],
        scoring_authorization_sha256=commitment["separate_scoring_authorization_sha256"],
    )
    for key in report:
        require(report[key] == original[key], f"Recomputed result field differs: {key}")
    reproduced_seal = digest(reconstructed)
    require(reproduced_seal == original["result_seal_sha256"],
            "Reconstructed final result seal differs")
    macro = report["macro"]
    checks = {
        "EC_E": (macro["evidence_completeness"]["G1-E"]["mean"], 0.0),
        "EC_N": (macro["evidence_completeness"]["G1-N"]["mean"], 0.0),
        "EC_EN": (macro["evidence_completeness"]["G1-EN"]["mean"], 0.0),
        "G1-EN_CSR": (macro["complete_support_rate"]["G1-EN"]["mean"], 0.9261),
        "G0_CSR": (macro["complete_support_rate"]["G0"]["mean"], 0.8723),
        "V1_Citation_Precision": (macro["citation_precision"]["V1-EN"]["mean"], 1.0),
        "V1_CSR": (macro["complete_support_rate"]["V1-EN"]["mean"], 1.0),
        "V1_Coverage": (macro["q1_q6_substantive_coverage"]["V1-EN"]["mean"], 0.5278),
        "RWR": (macro["required_withholding_recall"]["V1-EN"]["mean"], 0.3344),
        "V1_USCR": (macro["unsupported_security_claim_rate"]["V1-EN"]["mean"], None),
    }
    for label, (actual, expected) in checks.items():
        if expected is None:
            require(actual is None, f"Unexpected {label}: {actual}")
        else:
            require(actual is not None and round(actual, 4) == expected,
                    f"Unexpected {label}: {actual}")
    print("VALIDATION PASS: public inputs, ledgers, outputs, policy, authorization, and seals")
    print("SCORING PASS: 480 run positions (477 R1 reviews, 3 provider-incomplete)")
    print("RESULT SEAL REPRODUCED:", reproduced_seal)
    print("HEADLINES: EC(E/N/EN)=0.0000/0.0000/0.0000; G1-EN CSR=0.9261; G0 CSR=0.8723")
    print("           V1 Citation Precision=1.0000; CSR=1.0000; Coverage=0.5278; RWR=0.3344; USCR=NA")


if __name__ == "__main__":
    main()
