"""Load the versioned EBRL contract, ontology, and verifier rule table."""
from __future__ import annotations

import json
from pathlib import Path

from ebrl.canonical import sha256_obj

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "configs" / "ebrl"

FORBIDDEN_BUNDLE_KEYS = frozenset({
    "malicious",
    "event_truth",
    "attack_label",
    "family_description",
    "o_star",
    "reference",
    "gold",
    "simulator_trace",
    "evaluator_only",
    "operational_universe",
    "source_event_id",
})


class LeakageError(ValueError):
    """Model-visible input contains evaluator-only material."""


def load_json(name: str) -> dict:
    path = CONFIG_DIR / name
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_contract() -> dict:
    contract = load_json("contract.v1.json")
    ontology = load_json("semantic_ontology.v1.json")
    rules = load_json("verifier_rules.v1.json")
    contract["ontology_sha256"] = sha256_obj(ontology)
    contract["verifier_rules_sha256"] = sha256_obj(rules)
    contract["contract_sha256"] = sha256_obj({
        k: v for k, v in contract.items() if k != "contract_sha256"
    })
    return contract


def load_ontology() -> dict:
    return load_json("semantic_ontology.v1.json")


def load_verifier_rules() -> dict:
    return load_json("verifier_rules.v1.json")


def assert_bundle_visible(bundle: dict) -> None:
    found = FORBIDDEN_BUNDLE_KEYS.intersection(bundle)
    if found:
        raise LeakageError(
            "Evaluator-only keys are not allowed in a model-visible bundle: "
            + ", ".join(sorted(found))
        )
    for record in bundle.get("network_records", []) + bundle.get("process_records", []):
        nested = FORBIDDEN_BUNDLE_KEYS.intersection(record)
        if nested:
            raise LeakageError(
                "Evaluator-only keys are not allowed on visible records: "
                + ", ".join(sorted(nested))
            )
