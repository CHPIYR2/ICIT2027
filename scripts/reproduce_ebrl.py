"""Replay the offline EBRL synthetic evaluation. No network and no LLM."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    python = sys.executable
    tests = subprocess.run(
        [python, "-m", "unittest", "discover", "-s", "tests", "-p", "test_ebrl_*.py", "-v"],
        cwd=ROOT,
        check=False,
    )
    evaluation = subprocess.run([python, str(ROOT / "scripts" / "evaluate_ebrl.py")], cwd=ROOT, check=False)
    audit = subprocess.run([python, str(ROOT / "scripts" / "audit_ebrl_provenance.py")], cwd=ROOT, check=False)
    if tests.returncode or evaluation.returncode or audit.returncode:
        raise SystemExit(tests.returncode or evaluation.returncode or audit.returncode)


if __name__ == "__main__":
    main()
