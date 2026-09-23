#!/usr/bin/env python3
"""Reproducibly answer whether a named test detects a minimal protection mutation.

The tool copies the supplied source tree once per mutation, verifies a passing baseline, then
applies an exact one-occurrence replacement and invokes only the named tests. Only genuine
test failures count as mutation detection; collection errors and unexecuted tests remain holds.
It never changes the source tree in place. Rows with no declared test are reported as UNPAIRED.
"""
from __future__ import annotations

import argparse
import ast
import csv
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import json
import os
import xml.etree.ElementTree as ET
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def _unescape(value: str) -> str:
    return bytes(value, "utf-8").decode("unicode_escape")


def read_table(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t", quoting=csv.QUOTE_NONE))
    required = {"id", "kind", "source", "old", "new", "tests", "consequence"}
    if not rows or set(rows[0]) != required:
        raise ValueError(f"mutation table must have exactly {sorted(required)}")
    ids = [row["id"] for row in rows]
    if len(ids) != len(set(ids)) or any(not item for item in ids):
        raise ValueError("mutation IDs must be present and unique")
    return rows


def inventory(root: Path) -> list[dict[str, str]]:
    """Inventory the prompt-defined protection classes without claiming test pairing."""
    found: list[dict[str, str]] = []
    registry = root / "tools" / "gate_registry.tsv"
    for line in registry.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            tool, status, _reason = line.split("\t", 2)
            found.append({"id": f"REGISTRY:{tool}", "kind": f"gate-registry:{status}",
                          "source": "tools/gate_registry.tsv"})
    rules = json.loads((root / "mamey" / "data" / "rules_registry.json").read_text(encoding="utf-8"))
    for rule in rules["rules"]:
        found.append({"id": f"RULE:{rule['id']}", "kind": "standing-rule",
                      "source": "mamey/data/rules_registry.json"})
    sources = list((root / "mamey").rglob("*.py")) + list((root / "tools").rglob("*.py"))
    for source in sorted(
        path for path in sources
        if "__pycache__" not in path.parts and not path.is_symlink()
    ):
        try:
            tree = ast.parse(source.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
                node.name.endswith("_guard") or node.name.endswith("_gate") or node.name == "standing_rule_for"
            ):
                found.append({"id": f"FUNC:{source.relative_to(root)}:{node.name}", "kind": "function",
                              "source": str(source.relative_to(root))})
    for label in ("RGGMCI_GATE", "DEPTH_FLOOR"):
        found.append({"id": f"VALIDATE:{label}", "kind": "validate-gate", "source": "mamey/validate.py"})
    dedup: dict[str, dict[str, str]] = {row["id"]: row for row in found}
    return [dedup[key] for key in sorted(dedup)]


def _pytest_counts(path: Path) -> dict[str, int] | None:
    """Read actual test outcomes; process failure alone is not mutation evidence."""
    try:
        cases = list(ET.parse(path).getroot().iter("testcase"))
    except (OSError, ET.ParseError):
        return None
    return {
        "executed": sum(case.find("skipped") is None for case in cases),
        "failed": sum(case.find("failure") is not None for case in cases),
        "errors": sum(case.find("error") is not None for case in cases),
    }


def run_one(root: Path, row: dict[str, str], logs: Path) -> dict[str, str]:
    tests = [item for item in row["tests"].split(";") if item]
    common = {"id": row["id"], "kind": row["kind"], "source": row["source"],
              "tests": ";".join(tests), "consequence": row["consequence"]}
    def hold(code: str, note: str, *, applied: bool = False, exit_code: str = "", log: str = ""):
        return common | {"classification": code, "mutation_status": "APPLIED" if applied else "NOT_RUN",
                         "remediation": note, "exit_code": exit_code, "log": log}
    if not tests:
        return hold("UNPAIRED", "HOLD_MUTATION_TABLE_ENTRY_REQUIRED")
    source = Path(row["source"])
    if not row["source"].strip() or source.is_absolute() or ".." in source.parts:
        return hold("HOLD_UNSAFE_SOURCE", "source must be a relative file within the copied tree")
    with tempfile.TemporaryDirectory(prefix="gate-mutation-") as work:
        copy = Path(work) / "tree"
        shutil.copytree(root, copy, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
        target = copy / source
        if not target.resolve().is_relative_to(copy.resolve()) or not target.is_file():
            return hold("HOLD_UNSAFE_SOURCE", "source must resolve to a file within the copied tree")
        old, new = _unescape(row["old"]), _unescape(row["new"])
        text = target.read_text(encoding="utf-8")
        if text.count(old) != 1:
            return hold("HOLD_MUTATION_NOT_UNIQUE", "HOLD_EXACT_MUTATION_DESIGN_REQUIRED",
                        log=f"expected exactly one match, found {text.count(old)}")
        log_name = row["id"].replace(":", "__").replace("/", "_").replace("\\", "_")
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        def run(phase: str):
            junit = logs.resolve() / f"{log_name}.{phase}.xml"
            log = logs.resolve() / f"{log_name}.{phase}.log"
            # Remove only this run's prior report, so an interrupted invocation
            # cannot accidentally validate a stale result.
            junit.unlink(missing_ok=True)
            completed = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", f"--junitxml={junit}",
                 f"--basetemp={Path(work) / ('pytest-' + phase)}", *tests], cwd=copy,
                env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
            )
            log.write_text(completed.stdout, encoding="utf-8")
            return completed, log, _pytest_counts(junit)
        baseline, baseline_log, baseline_counts = run("baseline")
        common.update(baseline_exit_code=str(baseline.returncode), baseline_log=str(baseline_log))
        if baseline.returncode or baseline_counts is None or baseline_counts["failed"] or baseline_counts["errors"]:
            return hold("HOLD_BASELINE_FAILED", "repair baseline before interpreting a mutation",
                        exit_code=str(baseline.returncode), log=str(baseline_log))
        common["baseline_tests"] = str(baseline_counts["executed"])
        if not baseline_counts["executed"]:
            return hold("HOLD_NO_TESTS_EXECUTED", "baseline has no executed tests", log=str(baseline_log))
        target.write_text(text.replace(old, new, 1), encoding="utf-8")
        completed, log, counts = run("mutated")
        if counts is None or counts["errors"] or completed.returncode not in (0, 1):
            return hold("HOLD_MUTATION_EXECUTION_ERROR", "mutation did not produce interpretable test outcomes",
                        applied=True, exit_code=str(completed.returncode), log=str(log))
        common["mutation_tests"] = str(counts["executed"])
        if not counts["executed"]:
            return hold("HOLD_NO_TESTS_EXECUTED", "mutation has no executed tests", applied=True,
                        exit_code=str(completed.returncode), log=str(log))
        if completed.returncode == 1 and counts["failed"]:
            classification = "BITES"
        elif completed.returncode == 0 and not counts["failed"]:
            classification = "VACUOUS"
        else:
            return hold("HOLD_MUTATION_EXECUTION_ERROR", "exit status and test outcomes disagree",
                        applied=True, exit_code=str(completed.returncode), log=str(log))
        return common | {"classification": classification, "mutation_status": "APPLIED",
                         "remediation": "EXISTING_PAIRED_TEST" if classification == "BITES" else "PATCH_REQUIRED",
                         "exit_code": str(completed.returncode), "log": str(log)}


def function_mutation_id(root: Path, row: dict[str, str]) -> str | None:
    """Bind a unique replacement to its innermost containing function, never by name alone."""
    source = Path(row["source"])
    if not row.get("tests") or source.is_absolute() or ".." in source.parts or source.suffix != ".py":
        return None
    target = root / source
    if target.is_symlink() or not target.resolve().is_relative_to(root.resolve()):
        return None
    try:
        text = target.read_text(encoding="utf-8")
        tree = ast.parse(text)
        old = _unescape(row["old"])
    except (OSError, SyntaxError, UnicodeError):
        return None
    if not old.strip() or text.count(old) != 1:
        return None
    offset = text.index(old)
    start = text.count("\n", 0, offset + len(old) - len(old.lstrip())) + 1
    end = text.count("\n", 0, offset + len(old.rstrip()) - 1) + 1
    functions = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    enclosing = [n for n in functions if n.lineno <= start and end <= n.end_lineno]
    if not enclosing:
        return None
    node = min(enclosing, key=lambda n: n.end_lineno - n.lineno)
    # The existing inventory ID cannot distinguish repeated method/function names in one file.
    if sum(n.name == node.name for n in functions) != 1:
        return None
    return f"FUNC:{source.as_posix()}:{node.name}"


def inventory_results(root: Path, table: list[dict[str, str]], results: list[dict[str, str]],
                      discovered: list[dict[str, str]]) -> list[dict[str, str]]:
    """Keep aliases visible with their measured outcome; pairing is not exhaustive coverage."""
    explicit = {row["id"] for row in table}
    by_id = {row["id"]: row for row in results}
    bindings: dict[str, list[dict[str, str]]] = {}
    for row in table:
        function_id = function_mutation_id(root, row)
        if function_id and row["id"] in by_id:
            bindings.setdefault(function_id, []).append(by_id[row["id"]])
    extra = []
    for item in discovered:
        if item["id"] in explicit:
            continue
        paired = bindings.get(item["id"], [])
        if paired:
            classes = sorted({r["classification"] for r in paired})
            outcome = "BITES" if "BITES" in classes else ";".join(classes)
            extra.append(item | {"tests": ";".join(sorted({r["tests"] for r in paired})),
                "consequence": "Function contains the bound mutation; not exhaustive function coverage",
                "classification": "PAIRED_" + outcome, "mutation_status": "SEE_PAIRED_RESULT",
                "remediation": "REVIEW_PAIRED_MUTATION_EVIDENCE", "exit_code": "", "log": "",
                "paired_mutation_ids": ";".join(sorted(r["id"] for r in paired))})
        else:
            extra.append(item | {"tests": "", "consequence": "", "classification": "UNPAIRED",
                "mutation_status": "NOT_DESIGNED", "remediation": "HOLD_MUTATION_TABLE_ENTRY_REQUIRED",
                "exit_code": "", "log": "", "paired_mutation_ids": ""})
    return extra


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--mutation-table", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    if not (root / "mamey" / "validate.py").is_file():
        raise SystemExit("--source-root must be a Sapote-Mamey source tree")
    table = read_table(args.mutation_table)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    logs = args.output.parent / "probe_logs"
    logs.mkdir(exist_ok=True)
    results = [run_one(root, row, logs) for row in table]
    results.extend(inventory_results(root, table, results, inventory(root)))
    fields = ["id", "kind", "source", "tests", "consequence", "classification", "mutation_status", "remediation", "exit_code", "log", "baseline_exit_code", "baseline_log", "baseline_tests", "mutation_tests", "paired_mutation_ids"]
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        handle.write(f"# generated_at_utc={datetime.now(timezone.utc).isoformat()}\n")
        writer = _SafeDictWriter(handle, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(sorted(results, key=lambda item: item["id"]))
    counts: dict[str, int] = {}
    for row in results:
        counts[row["classification"]] = counts.get(row["classification"], 0) + 1
    print(json.dumps({"rows": len(results), "counts": counts, "result": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
