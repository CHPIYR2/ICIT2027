"""Investigate one visible-evidence JSON bundle. Does not read evaluator labels."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ebrl.contract import load_contract, load_ontology
from ebrl.pipeline import investigate


def main() -> None:
    parser = argparse.ArgumentParser(description="Run EBRL on one model-visible event bundle")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--method", default="P1")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    bundle = json.loads(args.input.read_text(encoding="utf-8"))
    artifact = investigate(bundle, load_contract(), load_ontology(), method=args.method)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(artifact["artifact_sha256"])


if __name__ == "__main__":
    main()
