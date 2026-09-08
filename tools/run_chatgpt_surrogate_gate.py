#!/usr/bin/env python3
"""Fast ChatGPT surrogate release gate for Sapote--Mamey.

This is intentionally not a replacement for the full pytest suite.  It is a
small, high-yield gate for capped ChatGPT/Claude review loops where the full
partitioned suite is too slow for every iteration.

Default target: < 1/10 of the v9.7.141c partitioned full-suite runtime.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

import argparse
import csv
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Iterable

SURROGATE_PYTEST_FILES: list[str] = [
    # Release identity / version provenance
    "tests/test_build_stamp_consistency.py",
    "tests/test_build_stamp.py",
    "tests/test_version_sync.py",
    "tests/test_chatgpt_start_here_current.py",
    "tests/test_bootstrap_contract_generation.py",
    # ChatGPT operational contract
    "tests/test_chatgpt_safe_first_run_guard.py",
    "tests/test_chatgpt_safe_batch_profile.py",
    "tests/test_chatgpt_safe_batch_size_guard.py",
    "tests/test_chatgpt_heartbeat_finalization.py",
    "tests/test_chatgpt_bootstrap_timeout_safe_defaults_v97134.py",
    "tests/test_inspector_commands.py",
    # Receipt/status/timing parity
    "tests/test_v97141_phase_receipt_and_status.py",
    "tests/test_validate_timing_receipt_parity.py",
    "tests/test_mode_b_receipt.py",
    "tests/test_recovery_status_schema.py",
    "tests/test_release_blocker_phase_receipts.py",
    "tests/test_timing_breakdown_files.py",
    "tests/test_tier_parity_receipt.py",
    # Registry/workbook guardrails with low runtime
    "tests/test_b2_registry_parity.py",
    "tests/test_gate_wiring_invariant.py",
    "tests/test_workbook_populated_sheet_gate.py",
    "tests/test_chatgpt_surrogate_gate_manifest.py",
]

PY_COMPILE_TARGETS: list[str] = [
    "mamey/cli.py",
    "mamey/chatgpt_commands.py",
    "mamey/llm_handoff.py",
    "mamey/mode_b_receipt.py",
    "mamey/recovery_status.py",
    "tools/validate_timing_receipt_parity.py",
    "tools/run_chatgpt_surrogate_gate.py",
    "tools/render_bootstrap_contract.py",
]

BASH_SYNTAX_TARGETS: list[str] = [
    "tools/build_all_deliverables.sh",
]


def _run(cmd: list[str], cwd: Path, timeout: float) -> tuple[int, float, str]:
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        elapsed = time.perf_counter() - started
        return proc.returncode, elapsed, proc.stdout
    except subprocess.TimeoutExpired as exc:
        elapsed = time.perf_counter() - started
        out = exc.stdout or ""
        if isinstance(out, bytes):
            out = out.decode("utf-8", errors="replace")
        out += f"\nTIMEOUT after {timeout:.1f}s\n"
        return 124, elapsed, out


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _existing(paths: Iterable[str], root: Path) -> list[str]:
    return [p for p in paths if (root / p).exists()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the fast ChatGPT surrogate release gate.")
    parser.add_argument("--root", default=".", help="Sapote--Mamey CODE tier root")
    parser.add_argument("--out", default="validation/chatgpt_surrogate_gate", help="output directory")
    parser.add_argument("--pytest-timeout", type=float, default=180.0, help="pytest subset timeout seconds")
    parser.add_argument("--doctor-timeout", type=float, default=45.0, help="doctor timeout seconds")
    parser.add_argument("--skip-doctor", action="store_true", help="skip python -m mamey doctor")
    parser.add_argument("--json", action="store_true", help="print JSON summary to stdout")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    out = (root / args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    steps: list[dict[str, object]] = []

    def record(name: str, cmd: list[str], timeout: float, log_name: str) -> int:
        rc, elapsed, output = _run(cmd, root, timeout)
        _write_text(out / log_name, output)
        _out_l = output if isinstance(output, str) else ""
        _env_missing = rc != 0 and "No module named" in _out_l
        steps.append({
            "name": name,
            "command": " ".join(cmd),
            "returncode": rc,
            "elapsed_seconds": round(elapsed, 3),
            "log": log_name,
            "status": ("PASS" if rc == 0 else "TIMEOUT" if rc == 124
                       else "ENV-SKIP" if _env_missing else "FAIL"),
        })
        return rc

    # High-signal command checks before pytest.
    if not args.skip_doctor:
        record("doctor", [sys.executable, "-m", "mamey", "doctor"], args.doctor_timeout, "doctor.log")

    py_targets = _existing(PY_COMPILE_TARGETS, root)
    if py_targets:
        record("py_compile", [sys.executable, "-m", "py_compile", *py_targets], 45.0, "py_compile.log")

    for rel in _existing(BASH_SYNTAX_TARGETS, root):
        record(f"bash_syntax:{rel}", ["bash", "-n", rel], 20.0, f"bash_syntax_{Path(rel).name}.log")

    tests = _existing(SURROGATE_PYTEST_FILES, root)
    if not tests:
        _write_text(out / "pytest_surrogate.log", "No surrogate pytest files found.\n")
        steps.append({"name": "pytest_surrogate", "returncode": 2, "elapsed_seconds": 0, "status": "ENV-SKIP", "log": "pytest_surrogate.log"})
    else:
        record("pytest_surrogate", [sys.executable, "-m", "pytest", "-q", *tests], args.pytest_timeout, "pytest_surrogate.log")

    # env-missing (e.g. pytest not installed) is ENV-SKIP, not FAIL — doctor treats these as optional deps.
    # v9.7.374 (audit lane): a step that TIMED OUT never finished, so it was never actually
    # verified — its real pass/fail is unknown, not "clean." Pre-fix this fell through the FAIL-only
    # check and the gate reported overall PASS/exit-0 even when e.g. the entire pytest_surrogate
    # subset (release-identity/version-sync/receipt-parity tests) hit the timeout and ran zero
    # assertions — live-reproduced with `--pytest-timeout 0.01`: step status TIMEOUT, overall
    # summary still said "status": "PASS", exit code 0. A TIMEOUT step must fail the gate too.
    status = "FAIL" if any(s.get("status") == "FAIL" for s in steps) or any(s.get("status") == "TIMEOUT" for s in steps) else "PASS"
    total_elapsed = round(sum(float(s["elapsed_seconds"]) for s in steps), 3)

    summary = {
        "schema": "chatgpt_surrogate_gate_v1",
        "status": status,
        "root": str(root),
        "total_elapsed_seconds_sum": total_elapsed,
        "pytest_file_count": len(tests),
        "pytest_files": tests,
        "steps": steps,
        "note": "Fast surrogate only; does not replace full partitioned pytest or real smoke runs before signing.",
    }
    _write_text(out / "surrogate_gate_summary.json", json.dumps(summary, indent=2, sort_keys=True) + "\n")

    with (out / "surrogate_gate_steps.csv").open("w", newline="", encoding="utf-8") as f:
        writer = _SafeDictWriter(f, fieldnames=["name", "status", "returncode", "elapsed_seconds", "log", "command"])
        writer.writeheader()
        writer.writerows(steps)

    md_lines = [
        "# ChatGPT surrogate gate report",
        "",
        f"Status: **{status}**",
        f"Pytest files: {len(tests)}",
        f"Step elapsed sum: {total_elapsed:.1f}s",
        "",
        "This is a fast, high-signal surrogate gate for capped ChatGPT review loops. It does not replace the full partitioned pytest suite before signing.",
        "",
        "| Step | Status | Seconds | Log |",
        "|---|---:|---:|---|",
    ]
    for step in steps:
        md_lines.append(f"| {step['name']} | {step['status']} | {step['elapsed_seconds']} | {step['log']} |")
    _write_text(out / "SURROGATE_GATE_REPORT.md", "\n".join(md_lines) + "\n")

    if args.json:
        emit(json.dumps(summary, indent=2, sort_keys=True))
    else:
        emit(f"ChatGPT surrogate gate: {status} ({len(tests)} pytest files, {total_elapsed:.1f}s step-sum)", f"Report: {out / 'SURROGATE_GATE_REPORT.md'}", sep="\n")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
