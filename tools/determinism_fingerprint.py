#!/usr/bin/env python3
"""Run and compare the shipped deterministic-extraction control inventory.

The harness extends ``mamey.packaging.repro_fingerprint``: it preserves that
science-output fingerprint, adds whole-package byte accounting, and reports
typed CSV changes only when a complete four-part locus identity is available.
It never changes a sealed package or interprets a score biologically.
"""
from __future__ import annotations

import argparse
import csv
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mamey import BUNDLE_VERSION, __version__
from mamey.exact_identity import (
    ExactLocusIdentityError, exact_locus_from_mapping,
    exact_locus_from_native_inventory_row, exact_locus_from_native_manifest_bgc,
)
from mamey.packaging import repro_fingerprint
from tools._safe_walk import safe_walk_files

DEFAULT_INVENTORY = ROOT / "mamey" / "data" / "determinism_inventory.json"
DEFAULT_BASELINE = ROOT / "mamey" / "data" / "determinism_fingerprint_406.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object required: {path}")
    return payload


def _discover_inputs() -> tuple[dict[str, str], list[str]]:
    found: dict[str, str] = {}
    unreadable: list[str] = []
    for base in (ROOT / "examples" / "test_data", ROOT / "tests"):
        paths, failures = safe_walk_files(base, skip_dirs=frozenset({"__pycache__", ".pytest_cache"}))
        unreadable.extend(failures)
        for path in paths:
            if path.is_file() and path.suffix.lower() in {".zip", ".gbk", ".gb", ".gbff"}:
                found[path.relative_to(ROOT).as_posix()] = sha256(path)
    master = ROOT / "examples" / "test_data" / "test_master.xlsx"
    if master.is_file():
        found[master.relative_to(ROOT).as_posix()] = sha256(master)
    reference = ROOT / "mamey" / "data" / "reference_bgc_library.json"
    if reference.is_file():
        found[reference.relative_to(ROOT).as_posix()] = sha256(reference)
    return found, sorted(unreadable)


def validate_inventory(spec: dict[str, Any]) -> dict[str, Any]:
    bindings = {row["input"]: row.get("input_sha256")
                for group in ("package_runs", "probes") for row in spec[group]}
    listed = set(bindings)
    discovered, unreadable = _discover_inputs()
    discovered_paths = set(discovered)
    missing_bindings = sorted(path for path, digest in bindings.items() if not digest)
    hash_mismatches = [
        {"input": path, "expected": bindings[path], "observed": discovered[path]}
        for path in sorted(listed & discovered_paths)
        if bindings[path] and bindings[path] != discovered[path]
    ]
    return {
        "discovered": sorted(discovered_paths),
        "discovered_sha256": discovered,
        "listed": sorted(listed),
        "unlisted": sorted(discovered_paths - listed),
        "missing": sorted(listed - discovered_paths),
        "missing_hash_bindings": missing_bindings,
        "hash_mismatches": hash_mismatches,
        "unreadable_directories": unreadable,
        "complete": discovered_paths == listed and not missing_bindings and not hash_mismatches and not unreadable,
    }


def _canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _normalize_runtime_json(value: Any) -> Any:
    volatile_keys = {
        "time", "mono_ns", "pid", "start_utc", "end_utc", "start_monotonic_ns",
        "end_monotonic_ns", "elapsed_seconds", "cpu_user_seconds", "cpu_system_seconds",
        "peak_rss_kb",
    }
    if isinstance(value, dict):
        return {key: (f"<volatile:{key}>" if key in volatile_keys else _normalize_runtime_json(item))
                for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_runtime_json(item) for item in value]
    return value


def _canonical_file_bytes(path: Path, package: Path, memo: dict[Path, bytes]) -> bytes:
    path = path.resolve()
    if path in memo:
        return memo[path]
    name = path.name
    raw = path.read_bytes()
    canonical = raw
    if name.endswith("_judgment_register.json"):
        payload = json.loads(raw)
        if "mamey_init_timestamp" in payload:
            payload["mamey_init_timestamp"] = "<volatile:mamey_init_timestamp>"
        canonical = _canonical_json_bytes(payload)
    elif name.endswith("_timing_breakdown.json"):
        canonical = _canonical_json_bytes(_normalize_runtime_json(json.loads(raw)))
    elif name.endswith("_timing_breakdown.csv"):
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
        rows = list(reader)
        for row in rows:
            row["elapsed_seconds"] = "<volatile:elapsed_seconds>"
        stream = io.StringIO(newline="")
        writer = _SafeDictWriter(stream, fieldnames=reader.fieldnames or [], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        canonical = stream.getvalue().encode("utf-8")
    elif name.endswith("_timing_breakdown.md"):
        text = raw.decode("utf-8")
        text = re.sub(r"^Start: .*?  \|  Elapsed: \*\*.*?\*\*$",
                      "Start: <volatile:start_utc>  |  Elapsed: **<volatile:elapsed_seconds>**",
                      text, flags=re.MULTILINE)
        text = re.sub(r"^Peak RSS: .*? KB  \|  CPU user: .*?s  sys: .*?s$",
                      "Peak RSS: <volatile:peak_rss_kb> KB  |  CPU user: <volatile:cpu_user_seconds>s  sys: <volatile:cpu_system_seconds>s",
                      text, flags=re.MULTILINE)
        text = re.sub(r"^(\| [^|]+ \|) [0-9.]+ (\| (?:COMPLETE|PASS|FAIL|SKIP|SKIPPED) \|)",
                      r"\1 <volatile:elapsed_seconds> \2", text, flags=re.MULTILINE)
        text = re.sub(r"^\*\*Phase sum:\*\* .*?$", "**Phase sum:** <volatile:runtime_totals>",
                      text, flags=re.MULTILINE)
        canonical = text.encode("utf-8")
    elif name == "run_phase_receipts.jsonl":
        rows = [_normalize_runtime_json(json.loads(line)) for line in raw.decode("utf-8").splitlines() if line.strip()]
        for row in rows:
            if row.get("phase") == "zip_package" and row.get("status") == "END" and "bytes" in row:
                row["bytes"] = "<volatile:compressed_zip_bytes>"
        canonical = b"".join(_canonical_json_bytes(row) for row in rows)
    elif name == "manifest.json":
        payload = json.loads(raw)
        for item in payload.get("files", []):
            relative = item.get("path")
            child = (package / relative).resolve() if relative else None
            if child and child != path and child.is_file() and (child == package or package in child.parents):
                child_bytes = _canonical_file_bytes(child, package, memo)
                item["sha256"] = hashlib.sha256(child_bytes).hexdigest()
                item["bytes"] = len(child_bytes)
        canonical = _canonical_json_bytes(payload)
    elif name == "checksums_sha256.txt":
        lines = []
        for line in raw.decode("utf-8").splitlines():
            parts = line.split(None, 1)
            if len(parts) != 2:
                lines.append(line)
                continue
            relative = parts[1].strip().lstrip("*")
            child = (package / relative).resolve()
            if child != path and child.is_file() and (child == package or package in child.parents):
                digest = hashlib.sha256(_canonical_file_bytes(child, package, memo)).hexdigest()
                lines.append(f"{digest}  {relative}")
            else:
                lines.append(line)
        canonical = ("\n".join(lines) + "\n").encode("utf-8")
    memo[path] = canonical
    return canonical


def _package_files(package: Path) -> tuple[dict[str, str], dict[str, str]]:
    raw: dict[str, str] = {}
    canonical: dict[str, str] = {}
    memo: dict[Path, bytes] = {}
    for path in sorted(package.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(package).as_posix()
        raw[relative] = sha256(path)
        canonical[relative] = hashlib.sha256(_canonical_file_bytes(path, package.resolve(), memo)).hexdigest()
    return raw, canonical


def _manifest_strain(package: Path) -> str:
    manifest = _load_json(package / "manifest.json")
    strain = str(manifest.get("strain_id") or manifest.get("strain") or "").strip()
    if not strain:
        raise ValueError(f"manifest strain missing: {package}")
    return strain


def _identity(row: dict[str, str], strain: str, *, native_inventory: bool = False,
              native_manifest: bool = False) -> str | None:
    try:
        if native_inventory:
            return exact_locus_from_native_inventory_row(strain, row).exact_locus
        if native_manifest:
            return exact_locus_from_native_manifest_bgc(strain, row).exact_locus
        return exact_locus_from_mapping(strain, row)
    except ExactLocusIdentityError:
        return None


_ROW_KEY_PREFIX = "csv-row-v1:"


def _csv_cell_key(file_name: str, identity: str, source_row: int | None) -> str:
    """Keep legacy single-locus keys and encode source-row identity separately."""
    if source_row is None and "|" not in file_name and not file_name.startswith(_ROW_KEY_PREFIX):
        return f"{file_name}|{identity}"
    return _ROW_KEY_PREFIX + json.dumps([file_name, identity, source_row], separators=(",", ":"))


def _decode_csv_cell_key(key: str) -> tuple[str, str, int | None]:
    if not key.startswith(_ROW_KEY_PREFIX):
        file_name, identity = key.split("|", 1)
        return file_name, identity, None
    value = json.loads(key[len(_ROW_KEY_PREFIX):])
    if (not isinstance(value, list) or len(value) != 3
            or not isinstance(value[0], str) or not isinstance(value[1], str)
            or (value[2] is not None and (type(value[2]) is not int or value[2] < 2))):
        raise ValueError("invalid typed CSV source-row key")
    return value[0], value[1], value[2]


def _csv_cells(package: Path) -> tuple[dict[str, dict[str, str]], list[dict[str, str]]]:
    strain = _manifest_strain(package)
    cells: dict[str, dict[str, str]] = {}
    holds: list[dict[str, str]] = []
    for path in sorted(package.glob("*.csv")):
        single_locus_rows = path.name.endswith((
            "_2_inventory.csv", "_2b_bgc_crosswalk.csv", "_4_triage_board.csv", "_4B_two_model_decomp.csv",
            "_4c_AB_lead_board.csv", "_4c_AF_lead_board.csv",
        ))
        alias_keys: dict[str, str] = {}
        physical_keys: dict[str, str] = {}
        refused_keys: set[str] = set()
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fields = reader.fieldnames or []
            identity_table = single_locus_rows or bool({"BGC_ID", "bgc_id"}.intersection(fields))
            if identity_table and (not fields or any(not field.strip() for field in fields)
                                      or len(fields) != len(set(fields))):
                holds.append({"file": path.name, "row": "1",
                              "reason": "missing, empty or duplicate identity-table CSV header"})
                continue
            native_inventory = single_locus_rows and {"Contig", "Node_ID"}.issubset(fields)
            native_manifest = path.name.endswith(("_2b_bgc_crosswalk.csv", "_4B_two_model_decomp.csv")) and "node_id" in fields
            for index, row in enumerate(reader, start=2):
                if identity_table and (None in row or any(value is None for value in row.values())):
                    holds.append({"file": path.name, "row": str(index),
                                  "reason": "identity-table CSV row width differs from its header"})
                    continue
                alias = (row.get("BGC_ID") or row.get("bgc_id") or "").strip()
                if not alias and not identity_table:
                    continue
                identity = _identity(row, strain, native_inventory=native_inventory,
                                     native_manifest=native_manifest)
                if identity is None:
                    holds.append({"file": path.name, "row": str(index),
                                  "reason": "complete strain / node-or-contig / region / BGC alias unavailable"})
                    continue
                key = _csv_cell_key(path.name, identity, None if single_locus_rows else index)
                if single_locus_rows:
                    physical = identity.rsplit(" / ", 1)[0]
                    conflicts = {prior for prior in (alias_keys.get(alias), physical_keys.get(physical)) if prior is not None}
                    alias_keys[alias] = key
                    physical_keys[physical] = key
                    if conflicts or key in refused_keys:
                        refused_keys.update(conflicts | {key})
                        for prior in refused_keys:
                            cells.pop(prior, None)
                        holds.append({"file": path.name, "row": str(index),
                                      "reason": "duplicate or ambiguous single-locus CSV identity"})
                        continue
                cells[key] = {column: value or "" for column, value in row.items() if column is not None}
    return cells, holds


def fingerprint_pair(case_id: str, left: Path, right: Path, volatile: Any = None) -> dict[str, Any]:
    left_raw, left_files = _package_files(left)
    right_raw, right_files = _package_files(right)
    names = sorted(set(left_files) | set(right_files))
    raw_differences = [name for name in names if left_raw.get(name) != right_raw.get(name)]
    byte_differences = [name for name in names if left_files.get(name) != right_files.get(name)]
    volatile_only = sorted(set(raw_differences) - set(byte_differences))
    left_cells, left_holds = _csv_cells(left)
    right_cells, right_holds = _csv_cells(right)
    typed = []
    for key in sorted(set(left_cells) | set(right_cells)):
        before, after = left_cells.get(key, {}), right_cells.get(key, {})
        file_name, identity, source_row = _decode_csv_cell_key(key)
        for column in sorted(set(before) | set(after)):
            if before.get(column, "") != after.get(column, ""):
                typed.append({"file": file_name, "identity": identity, "column": column,
                              **({"source_row": source_row} if source_row is not None else {}),
                              "left": before.get(column, ""), "right": after.get(column, "")})
    science_left, science_right = repro_fingerprint(left), repro_fingerprint(right)
    return {
        "case_id": case_id,
        "left_package": left.name,
        "right_package": right.name,
        "science_fingerprint": science_left,
        "science_fingerprint_match": science_left["fingerprint"] == science_right["fingerprint"],
        "canonical_outputs": left_files,
        "raw_outputs": left_raw,
        "files_total": len(names),
        "raw_files_identical": len(names) - len(raw_differences),
        "raw_byte_differences": raw_differences,
        "non_timestamp_files_total": len(names),
        "non_timestamp_files_identical": len(names) - len(byte_differences),
        "non_timestamp_byte_parity": not byte_differences,
        "byte_differences": byte_differences,
        "volatile_field_only_differences": volatile_only,
        "volatile_field_policy": volatile or {},
        "typed_bgc_cell_differences": typed,
        "identity_holds": left_holds + right_holds,
        "canonical_csv_cells": left_cells,
    }


def _run(command: list[str], cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=False)


def _pair_status(result: dict[str, Any]) -> str:
    if not result["non_timestamp_byte_parity"]:
        return "FAIL_PARITY"
    if result["identity_holds"]:
        return "HOLD_IDENTITY"
    return "PASS"


def _run_package_case(case: dict[str, Any], root: Path, volatile: dict[str, list[str]]) -> dict[str, Any]:
    case_root = root / case["id"]
    input_path = case["input"]
    preparation = None
    if case.get("fixture_preparation") is not None:
        from zipfile import BadZipFile
        try:
            from tools.fixture_inputs import (
                prepare_single_contig_fixture, prepare_full_locus_single_contig_fixture,
            )
            preparers = {
                "single_contig_stored_fasta_v1": prepare_single_contig_fixture,
                "single_contig_full_locus_runtime_v1": prepare_full_locus_single_contig_fixture,
            }
            if case["fixture_preparation"] not in preparers:
                raise ValueError("unknown governed fixture preparation")
            case_root.mkdir(parents=True, exist_ok=True)
            prepared_path = case_root / "admitted_synthetic_input.zip"
            preparation = preparers[case["fixture_preparation"]](ROOT / case["input"], prepared_path)
            input_path = str(prepared_path.resolve())
        except (OSError, ValueError, BadZipFile) as exc:
            return {"case_id": case["id"], "status": "RUN_FAILED", "runs": [],
                    "input": case["input"],
                    "fixture_preparation": {"status": "FAILED",
                        "policy": case["fixture_preparation"],
                        "error_type": type(exc).__name__},
                    "error": f"input preparation failed: {type(exc).__name__}: {exc}"}
    env = dict(os.environ)
    env["MPLCONFIGDIR"] = str(root / "mpl-cache")
    exits = []
    packages = []
    for label in ("A", "B"):
        out = case_root / label
        command = [sys.executable, "mamey_run.py", "run", "--strain", case["strain"],
                   "--input-zip", input_path, "--taxonomy", "Synthetic sp.", "--source", "fixture",
                   "--mode", case["mode"], "--outdir", str(out), *case["flags"]]
        completed = _run(command, ROOT, env)
        case_root.mkdir(parents=True, exist_ok=True)
        run = {"label": label, "exit_code": completed.returncode}
        for stream in ("stdout", "stderr"):
            content = getattr(completed, stream)
            encoded = content.encode("utf-8")
            log_path = case_root / f"{label}.{stream}.log"
            log_path.write_bytes(encoded)
            run[f"{stream}_sha256"] = hashlib.sha256(encoded).hexdigest()
            run[f"{stream}_log"] = log_path.relative_to(root).as_posix()
            run[f"{stream}_tail"] = content[-1000:]
        exits.append(run)
        package = out / case["strain"] / "package"
        if completed.returncode != 0 or not package.is_dir():
            return {"case_id": case["id"], "status": "RUN_FAILED", "runs": exits,
                    "fixture_preparation": preparation,
                    "error": "stdout:\n" + completed.stdout[-1000:] +
                             "\nstderr:\n" + completed.stderr[-1000:]}
        packages.append(package)
    result = fingerprint_pair(case["id"], packages[0], packages[1], volatile)
    result.update({"status": _pair_status(result),
                   "input": case["input"], "input_sha256": sha256(ROOT / case["input"]),
                   "mode": case["mode"], "flags": case["flags"], "runs": exits,
                   "fixture_preparation": preparation})
    return result


def _run_probe(case: dict[str, Any], root: Path) -> dict[str, Any]:
    env = dict(os.environ)
    outputs = []
    for label in ("A", "B"):
        command = [sys.executable, *case["command"]]
        if case["kind"] == "calibration":
            target = root / case["id"] / f"{label}.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            command += ["--out", str(target)]
        completed = _run(command, ROOT, env)
        if case["kind"] == "calibration" and completed.returncode == 0:
            content = target.read_bytes()
        else:
            content = (completed.stdout + completed.stderr).encode()
        canonical = content
        if case["kind"] == "pytest":
            canonical = re.sub(rb" in [0-9]+(?:\.[0-9]+)?s", b" in <elapsed>", content)
        outputs.append({"exit_code": completed.returncode,
                        "raw_sha256": hashlib.sha256(content).hexdigest(),
                        "sha256": hashlib.sha256(canonical).hexdigest()})
    expected_exit = int(case.get("expected_exit_code", 0))
    parity = outputs[0]["sha256"] == outputs[1]["sha256"]
    expected = all(run["exit_code"] == expected_exit for run in outputs)
    return {"case_id": case["id"], "status": "PASS" if parity and expected else "FAIL",
            "input": case["input"], "input_sha256": sha256(ROOT / case["input"]),
            "runner_kind": case["kind"], "expected_exit_code": expected_exit,
            "expected_outcome": case.get("expected_outcome", "EXPECTED_SUCCESS"),
            "runs": outputs, "byte_parity": parity}


def run_inventory(spec_path: Path, work_root: Path) -> dict[str, Any]:
    spec = _load_json(spec_path)
    coverage = validate_inventory(spec)
    if not coverage["complete"]:
        raise ValueError(f"inventory coverage incomplete: {coverage}")
    work_root.mkdir(parents=True, exist_ok=True)
    inputs = {}
    for case in spec["package_runs"]:
        inputs[case["id"]] = _run_package_case(case, work_root, spec.get("legitimate_volatile_fields", {}))
    for case in spec["probes"]:
        inputs[case["id"]] = _run_probe(case, work_root)
    return {"schema_version": "mamey_determinism_fingerprint_v3",
            "bundle_version": BUNDLE_VERSION, "engine_version": __version__,
            "inventory_sha256": sha256(spec_path), "inventory_coverage": coverage,
            "inputs": inputs}


def report_ok(report: dict[str, Any]) -> bool:
    coverage = report.get("inventory_coverage") or {}
    if not coverage.get("complete", False):
        return False
    for row in report.get("inputs", {}).values():
        if row.get("status") != "PASS":
            return False
        if row.get("non_timestamp_byte_parity") is False or row.get("science_fingerprint_match") is False:
            return False
        if row.get("byte_parity") is False or row.get("typed_bgc_cell_differences"):
            return False
        if row.get("identity_holds"):
            return False
    return True


def compare_reports(current: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    changes = []
    for field in ("schema_version", "bundle_version", "engine_version", "inventory_sha256"):
        if current.get(field) != baseline.get(field):
            changes.append({"input": "<report>", "file": None, "identity": None, "column": field,
                            "baseline": baseline.get(field), "current": current.get(field)})
    if current.get("inventory_coverage") != baseline.get("inventory_coverage"):
        changes.append({"input": "<report>", "file": None, "identity": None,
                        "column": "inventory_coverage", "baseline": baseline.get("inventory_coverage"),
                        "current": current.get("inventory_coverage")})
    for case_id in sorted(set(current.get("inputs", {})) | set(baseline.get("inputs", {}))):
        now = current.get("inputs", {}).get(case_id, {})
        old = baseline.get("inputs", {}).get(case_id, {})
        for field in ("status", "input_sha256", "mode", "flags", "runner_kind", "expected_exit_code",
                      "expected_outcome", "byte_parity", "non_timestamp_byte_parity", "science_fingerprint_match"):
            if now.get(field) != old.get(field):
                changes.append({"input": case_id, "file": None, "identity": None, "column": field,
                                "baseline": old.get(field), "current": now.get(field)})
        old_files, new_files = old.get("canonical_outputs", {}), now.get("canonical_outputs", {})
        for name in sorted(set(old_files) | set(new_files)):
            if old_files.get(name) != new_files.get(name):
                changes.append({"input": case_id, "file": name, "identity": None, "column": None,
                                "baseline": old_files.get(name), "current": new_files.get(name)})
        old_cells, new_cells = old.get("canonical_csv_cells", {}), now.get("canonical_csv_cells", {})
        for key in sorted(set(old_cells) | set(new_cells)):
            file_name, identity, source_row = _decode_csv_cell_key(key)
            before, after = old_cells.get(key, {}), new_cells.get(key, {})
            for column in sorted(set(before) | set(after)):
                if before.get(column, "") != after.get(column, ""):
                    changes.append({"input": case_id, "file": file_name, "identity": identity,
                                    **({"source_row": source_row} if source_row is not None else {}),
                                    "column": column, "baseline": before.get(column, ""),
                                    "current": after.get(column, "")})
        for delta in now.get("typed_bgc_cell_differences", []):
            changes.append({"input": case_id, "file": delta.get("file"), "identity": delta.get("identity"),
                            "column": delta.get("column"),
                            **({"source_row": delta["source_row"]} if "source_row" in delta else {}),
                            "baseline": delta.get("left"),
                            "current": delta.get("right"), "source": "current_pair_internal_difference"})
        if now.get("status") != "PASS" and not any(
            row.get("input") == case_id and row.get("column") == "current_internal_status" for row in changes
        ):
            changes.append({"input": case_id, "file": None, "identity": None,
                            "column": "current_internal_status", "baseline": "PASS", "current": now.get("status")})
    current_ok = report_ok(current)
    return {"schema_version": "mamey_determinism_compare_v4",
            "match": not changes and current_ok, "current_report_ok": current_ok, "changes": changes}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--work-root", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--compare", type=Path, help="baseline fingerprint JSON")
    parser.add_argument("--package-pair", nargs=3, action="append", metavar=("ID", "LEFT", "RIGHT"),
                        help="fingerprint an existing package pair instead of executing the inventory")
    parser.add_argument("--include-probes", action="store_true",
                        help="with --package-pair, also execute every non-package probe twice")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    spec = _load_json(args.inventory)
    if args.package_pair:
        by_id = {case["id"]: case for case in spec["package_runs"]}
        inputs = {}
        for case_id, left, right in args.package_pair:
            result = fingerprint_pair(case_id, Path(left), Path(right), spec.get("legitimate_volatile_fields", {}))
            case = by_id.get(case_id)
            result["status"] = _pair_status(result)
            if case:
                result.update({"input": case["input"], "input_sha256": sha256(ROOT / case["input"]),
                               "mode": case["mode"], "flags": case["flags"]})
            inputs[case_id] = result
        if args.include_probes:
            work_root = args.work_root or Path(tempfile.mkdtemp(prefix="mamey-determinism-probes-"))
            work_root.mkdir(parents=True, exist_ok=True)
            for case in spec["probes"]:
                inputs[case["id"]] = _run_probe(case, work_root)
        report = {"schema_version": "mamey_determinism_fingerprint_v3",
                  "bundle_version": BUNDLE_VERSION, "engine_version": __version__,
                  "inventory_sha256": sha256(args.inventory), "inventory_coverage": validate_inventory(spec),
                  "inputs": inputs}
    else:
        if args.work_root:
            report = run_inventory(args.inventory, args.work_root)
        else:
            with tempfile.TemporaryDirectory(prefix="mamey-determinism-") as temp:
                report = run_inventory(args.inventory, Path(temp))
    payload: dict[str, Any] = report
    return_code = 0 if report_ok(report) else 1
    if args.compare:
        comparison = compare_reports(report, _load_json(args.compare))
        payload = {"report": report, "comparison": comparison}
        return_code = 0 if comparison["match"] and report_ok(report) else 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
