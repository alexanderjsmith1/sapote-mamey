#!/usr/bin/env python3
"""Gate the LLM-facing BiG-SCAPE/GToTree instruction surface.

This is deliberately a documentation consistency gate. It does not prove that an external tool,
database, or biological result is valid.
"""

from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

import argparse
import json
from pathlib import Path
from typing import Any


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def audit(bundle_root: Path, policy: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def add(kind: str, rel: str, ok: bool, detail: str) -> None:
        checks.append({"kind": kind, "path": rel, "ok": ok, "detail": detail})

    for section, kind in (
        ("active_documents", "active-required"),
        ("routing_documents", "routing-required"),
        ("historical_documents", "historical-banner"),
    ):
        for rel, expected in policy[section].items():
            path = bundle_root / rel
            if not path.is_file():
                add(kind, rel, False, "missing file")
                continue
            text = _read(path)
            tokens = expected if isinstance(expected, list) else [expected]
            missing = [token for token in tokens if token not in text]
            add(kind, rel, not missing, "present" if not missing else "missing: " + " | ".join(missing))

    for rel, fragments in policy["forbidden_active_fragments"].items():
        path = bundle_root / rel
        if not path.is_file():
            add("active-forbidden", rel, False, "missing file")
            continue
        text = _read(path)
        found = [fragment for fragment in fragments if fragment in text]
        add(
            "active-forbidden",
            rel,
            not found,
            "none found" if not found else "found: " + " | ".join(found),
        )

    failures = [check for check in checks if not check["ok"]]
    return {
        "schema_version": "1.0",
        "gate": "LLM_COMPANION_INSTRUCTION_GATE",
        "bundle_root": str(bundle_root.resolve()),
        "status": "PASS" if not failures else "FAIL",
        "checks": len(checks),
        "failures": len(failures),
        "results": checks,
        "claim_ceiling": (
            "Documentation consistency only; not external-tool availability, run completion, "
            "biological validation, release approval, or publication readiness."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle-root", type=Path, default=Path("."))
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    policy_path = args.policy or args.bundle_root / "mamey/data/llm_companion_instruction_policy.json"
    policy = json.loads(_read(policy_path))
    report = audit(args.bundle_root, policy)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
    emit(payload, end="")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
