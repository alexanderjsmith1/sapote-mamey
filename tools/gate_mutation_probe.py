#!/usr/bin/env python3
"""Reproducibly answer whether a named test detects a minimal protection mutation.

The tool copies the supplied source tree once per mutation, applies an exact one-occurrence
replacement, and invokes only the mutation's named tests.  It deliberately never changes the
source tree in place.  Rows with no declared test are reported as UNPAIRED, not silently green.
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


def run_one(root: Path, row: dict[str, str], logs: Path) -> dict[str, str]:
    tests = [item for item in row["tests"].split(";") if item]
    common = {"id": row["id"], "kind": row["kind"], "source": row["source"],
              "tests": ";".join(tests), "consequence": row["consequence"]}
    if not tests:
        return common | {"classification": "UNPAIRED", "mutation_status": "NOT_RUN",
                         "remediation": "HOLD_MUTATION_TABLE_ENTRY_REQUIRED", "exit_code": "", "log": ""}
    with tempfile.TemporaryDirectory(prefix="gate-mutation-") as work:
        copy = Path(work) / "tree"
        shutil.copytree(root, copy, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
        target = copy / row["source"]
        old, new = _unescape(row["old"]), _unescape(row["new"])
        text = target.read_text(encoding="utf-8")
        if text.count(old) != 1:
            return common | {"classification": "HOLD_MUTATION_NOT_UNIQUE", "mutation_status": "NOT_RUN",
                             "remediation": "HOLD_EXACT_MUTATION_DESIGN_REQUIRED",
                             "exit_code": "", "log": f"expected exactly one match, found {text.count(old)}"}
        target.write_text(text.replace(old, new, 1), encoding="utf-8")
        completed = subprocess.run([sys.executable, "-m", "pytest", "-q", *tests], cwd=copy,
                                   text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        log_name = row["id"].replace(":", "__").replace("/", "_").replace("\\", "_")
        log = logs / f"{log_name}.log"
        log.write_text(completed.stdout, encoding="utf-8")
        classification = "BITES" if completed.returncode else "VACUOUS"
        return common | {"classification": classification, "mutation_status": "APPLIED",
                         "remediation": "EXISTING_PAIRED_TEST" if classification == "BITES" else "PATCH_REQUIRED",
                         "exit_code": str(completed.returncode),
                         "log": str(log)}


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
    explicit = {row["id"] for row in table}
    # A mutation can name a human-readable guard while the AST inventory names its implementation.
    # Suppress only those exact duplicates; every other inventory entry remains a typed HOLD.
    explicit |= {
        "FUNC:mamey/rggmci.py:_product_class_gate", "FUNC:mamey/rggmci.py:_r1_drop_pair_gate",
        "FUNC:mamey/rggmci.py:_r2_strong_ref_gate", "FUNC:mamey/rggmci.py:_r3_noise_class_gate",
        "FUNC:mamey/rggmci.py:_apply_hub_degree_guard", "FUNC:mamey/rggmci.py:_geometry_gate",
        "VALIDATE:RGGMCI_GATE",
    }
    for item in inventory(root):
        if item["id"] not in explicit:
            results.append(item | {"tests": "", "consequence": "",
                                   "classification": "UNPAIRED", "mutation_status": "NOT_DESIGNED",
                                   "remediation": "HOLD_MUTATION_TABLE_ENTRY_REQUIRED",
                                   "exit_code": "", "log": ""})
    fields = ["id", "kind", "source", "tests", "consequence", "classification", "mutation_status", "remediation", "exit_code", "log"]
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
