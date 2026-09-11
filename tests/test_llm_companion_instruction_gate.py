from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_llm_companion_instruction_gate() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/audit_llm_companion_instructions.py"),
            "--bundle-root",
            str(ROOT),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = json.loads(proc.stdout)
    assert report["status"] == "PASS"
    assert report["failures"] == 0
    policy = json.loads((ROOT / "mamey/data/llm_companion_instruction_policy.json").read_text())
    kinds = {
        "active_documents": "active-required",
        "routing_documents": "routing-required",
        "historical_documents": "historical-banner",
        "forbidden_active_fragments": "active-forbidden",
    }
    expected = {(kind, path) for section, kind in kinds.items() for path in policy[section]}
    actual = {(row["kind"], row["path"]) for row in report["results"]}
    assert actual == expected
    assert report["checks"] == len(expected) == len(report["results"])
    assert all(row["ok"] for row in report["results"])
