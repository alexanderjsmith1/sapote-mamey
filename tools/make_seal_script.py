"""Prepare an owner-gated seal wrapper from hash-bound exact pytest identities.

This tool never runs pytest, collection, a seal, a release command or a subprocess.
Progress dots and reconstructed JUnit class/name pairs are not identity evidence.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shlex
import stat
import sys
import zipfile

from _release_partitions import validate_capture
from verify_external_validation_receipt import source_tree_sha256


class SealRefused(ValueError):
    """A required identity, binding or named disposition is missing or inconsistent."""


def require(condition, message):
    """Refuse before producing a candidate when a requirement is not met."""
    if not condition:
        raise SealRefused(message)


def canonical(value):
    """Use stable UTF-8 JSON for plans and comparison signatures."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def pin(path: Path, expected=None):
    """Bind a regular input in place without following a final symlink."""
    path = path.absolute()
    require(path.is_file() and not path.is_symlink(), "input is missing or nonregular: " + str(path))
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    measured = digest.hexdigest()
    require(expected is None or measured == expected, "input SHA-256 mismatch: " + str(path))
    return {"path": str(path), "sha256": measured, "bytes": path.stat().st_size}


def read_json(path: Path):
    """Reject duplicate JSON keys instead of silently replacing evidence fields."""
    def pairs(rows):
        result = {}
        for key, value in rows:
            require(key not in result, "duplicate JSON key: " + key)
            result[key] = value
        return result
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs)


def reference(value, parent: Path):
    """Resolve a required file reference and check its declared SHA-256."""
    require(isinstance(value, dict) and isinstance(value.get("path"), str)
            and bool(value["path"]), "missing file reference")
    require(isinstance(value.get("sha256"), str)
            and re.fullmatch("[0-9a-f]{64}", value["sha256"]), "missing reference SHA-256")
    path = Path(value["path"])
    return pin(path if path.is_absolute() else parent / path, value["sha256"])


def selection(arguments):
    """Remove only run-specific output/root operands, preserving selection and flags."""
    require(isinstance(arguments, list) and all(isinstance(a, str) for a in arguments),
            "invocation arguments are missing")
    result = []
    paths = {"--rootdir", "--release-evidence", "--basetemp", "--junitxml", "--junit-xml"}
    seen = set()
    index = 0
    while index < len(arguments):
        item = arguments[index]
        name = item.split("=", 1)[0]
        require(name != "--collect-only", "collect-only cannot establish execution")
        if name in paths:
            require(name not in seen, "duplicate run-specific invocation option")
            seen.add(name)
            if "=" in item:
                require(bool(item.split("=", 1)[1]), "empty invocation path")
            else:
                index += 1
                require(index < len(arguments) and bool(arguments[index]), "missing invocation operand")
        else:
            result.append(item)
        index += 1
    return result


def load_suite(path: Path, log: Path):
    """Admit a log/tree/capture wrapper and validate its complete native phase evidence."""
    wrapper_pin = pin(path)
    data = read_json(path)
    require(isinstance(data, dict) and data.get("schema") == "sapote-mamey.seal-suite-input.v1",
            "exact execution manifest required; progress dots/JUnit names are insufficient")
    log_pin = reference(data.get("log"), path.parent)
    require(Path(log_pin["path"]).resolve() == log.resolve(), "suite manifest names a different log")
    capture_pin = reference(data.get("capture"), path.parent)
    capture = read_json(Path(capture_pin["path"]))
    require(isinstance(capture, dict), "capture must be an object")
    validate_capture(capture)  # Native complete phase/count/subtest and freshness contract.
    require(type(capture.get("exit_code")) is int and capture["exit_code"] == 0,
            "suite exit must be an integer zero")
    grouped = {node: [] for node in capture["collected"]}
    for row in capture["phase_reports"]:
        grouped[row["nodeid"]].append(row)
    for row in capture["outcomes"]:
        phases = grouped[row["nodeid"]]
        require(row.get("reasons") == [p["reason"] for p in phases if p.get("reason")]
                and row.get("wasxfail") == [p["wasxfail"] for p in phases if p.get("wasxfail")],
                "main reason/xfail detail disagrees with phase evidence")
    tree = data.get("tree")
    require(isinstance(tree, dict) and isinstance(tree.get("path"), str)
            and isinstance(tree.get("sha256"), str), "suite tree binding missing")
    root = Path(tree["path"])
    root = (path.parent / root if not root.is_absolute() else root).resolve(strict=True)
    require(source_tree_sha256(root) == tree["sha256"], "suite tree changed")
    require(capture.get("rootpath") == str(root), "capture root differs from admitted tree")
    arguments = capture.get("invocation_args")
    require(isinstance(arguments, list), "invocation arguments are missing")
    evidence_operands = []
    for index, argument in enumerate(arguments):
        if argument == "--release-evidence":
            require(index + 1 < len(arguments), "missing capture output operand")
            evidence_operands.append(arguments[index + 1])
        elif isinstance(argument, str) and argument.startswith("--release-evidence="):
            evidence_operands.append(argument.split("=", 1)[1])
    require(len(evidence_operands) == 1 and Path(evidence_operands[0]).is_absolute()
            and Path(evidence_operands[0]).resolve() == Path(capture_pin["path"]).resolve(),
            "capture invocation does not bind its actual output")
    for bound in (wrapper_pin, log_pin, capture_pin):
        require(not Path(bound["path"]).resolve().is_relative_to(root),
                "suite evidence must be outside its source tree")
    # Collection-level skips omit unknown test identities: fail closed, even if both match.
    require(capture["collection_skips"] == [], "module collection skips leave ambiguous test identity")
    ini = capture.get("inifile")
    config = None
    if ini is not None:
        config_path = Path(ini)
        require(config_path.is_absolute() and config_path.resolve().is_relative_to(root),
                "pytest configuration is outside the suite tree")
        config = {"path": config_path.resolve().relative_to(root).as_posix(),
                  "sha256": pin(config_path)["sha256"]}
    result = {"manifest": wrapper_pin, "log": log_pin, "capture": capture_pin,
              "tree": {"path": str(root), "sha256": tree["sha256"]},
              "selection": selection(capture.get("invocation_args")),
              "pytest_version": capture.get("pytest_version"), "config": config}
    require(isinstance(result["pytest_version"], str) and result["pytest_version"],
            "pytest version is missing")
    return result, capture


def verify_archive(archive: Path, root: Path):
    """Compare every regular ZIP member with the actual extracted tree, without extraction."""
    names = set()
    with zipfile.ZipFile(archive) as zipped:
        for entry in zipped.infolist():
            name = entry.filename
            relative = PurePosixPath(name)
            require(name and "\\" not in name and not relative.is_absolute()
                    and ".." not in relative.parts and str(relative) == name.rstrip("/"),
                    "unsafe or noncanonical archive member")
            mode = entry.external_attr >> 16
            require(not stat.S_ISLNK(mode) and (entry.is_dir() or stat.S_IFMT(mode) in {0, stat.S_IFREG}),
                    "archive member is not a regular file/directory")
            if entry.is_dir():
                continue
            require(name not in names, "duplicate archive file")
            names.add(name)
            path = root / name
            require(path.is_file() and not path.is_symlink(), "extracted member missing or nonregular")
            digest = hashlib.sha256()
            with zipped.open(entry) as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
            require(pin(path)["sha256"] == digest.hexdigest(), "archive/extracted content differs: " + name)
            require(stat.S_IMODE(path.stat().st_mode) == (mode & 0o777 or 0o644),
                    "archive/extracted mode differs: " + name)
    observed = set()
    for path in root.rglob("*"):
        require(not path.is_symlink(), "extracted tree has a symlink")
        if path.is_file():
            observed.add(path.relative_to(root).as_posix())
        else:
            require(path.is_dir(), "extracted tree has a special entry")
    require(names and observed == names, "archive/extracted file census differs")


def outcome(row):
    """Retain skip/xfail detail alongside the observed main outcome."""
    require(set(row) >= {"nodeid", "outcome", "reasons", "wasxfail"}, "main outcome detail missing")
    require(isinstance(row["reasons"], list) and all(isinstance(r, str) for r in row["reasons"])
            and isinstance(row["wasxfail"], list) and all(isinstance(r, str) for r in row["wasxfail"]),
            "invalid outcome detail")
    return {key: row[key] for key in ("outcome", "reasons", "wasxfail")}


def compare(source, archive, dispositions):
    """Map by exact node ID; refuse incompatible coverage and unreviewed differences."""
    require(set(source["collected"]) == set(archive["collected"]), "incompatible collection identities")
    require(all("context" in r for r in source["subtests"] + archive["subtests"]),
            "subtest identity is ambiguous")
    for capture in (source, archive):
        identities = [(r["nodeid"], r["context"]) for r in capture["subtests"]]
        require(all(isinstance(context, str) and context for _, context in identities)
                and len(set(identities)) == len(identities), "duplicate or ambiguous subtest context")
    signature = lambda r: canonical({k: v for k, v in r.items() if k != "duration"})
    require(Counter(map(signature, source["subtests"])) == Counter(map(signature, archive["subtests"])),
            "subtest evidence differs; cannot explain by main-node alignment")
    a = {r["nodeid"]: outcome(r) for r in source["outcomes"]}
    b = {r["nodeid"]: outcome(r) for r in archive["outcomes"]}
    differences = [{"nodeid": n, "source": a[n], "archive": b[n]}
                   for n in sorted(a) if a[n] != b[n]]
    require(isinstance(dispositions, list) and all(isinstance(r, dict) for r in dispositions),
            "named differences must be an array of objects")
    supplied = {}
    for row in dispositions:
        require(set(row) == {"nodeid", "source", "archive", "explanation"}
                and isinstance(row["nodeid"], str) and isinstance(row["explanation"], str)
                and bool(row["explanation"].strip()), "invalid named difference")
        require(row["nodeid"] not in supplied, "duplicate named difference")
        supplied[row["nodeid"]] = row
    require(set(supplied) == {r["nodeid"] for r in differences}, "unexplained or stale named differences")
    for row in differences:
        declared = supplied[row["nodeid"]]
        require(all(declared[key] == row[key] for key in ("source", "archive")),
                "named difference does not match observed outcomes")
        row["explanation"] = declared["explanation"]
    return differences


def build_plan(*, cut_folder: Path, source_log: Path, archive_log: Path,
               source_evidence: Path, archive_evidence: Path, differences: Path,
               archive: Path, archive_sha256: str, owner_script: Path):
    """Read and bind all evidence without invoking the owner consumer."""
    cut = cut_folder.resolve(strict=True)
    require(cut.is_dir(), "cut folder is not a directory")
    require(re.fullmatch("[0-9a-f]{64}", archive_sha256 or ""), "archive SHA-256 is required")
    archive_pin = pin(archive, archive_sha256)
    require(Path(archive_pin["path"]).resolve().is_relative_to(cut), "archive is outside cut folder")
    source, source_capture = load_suite(source_evidence, source_log)
    extracted, archive_capture = load_suite(archive_evidence, archive_log)
    require(source["tree"]["path"] != extracted["tree"]["path"], "source and archive suite trees must differ")
    for key in ("selection", "pytest_version", "config"):
        require(source[key] == extracted[key], "incompatible suite " + key)
    require(not Path(archive_pin["path"]).resolve().is_relative_to(Path(extracted["tree"]["path"])),
            "archive must be outside extracted tree")
    verify_archive(Path(archive_pin["path"]), Path(extracted["tree"]["path"]))
    disposition_pin = pin(differences)
    named = compare(source_capture, archive_capture, read_json(differences))
    machinery = [pin(Path(__file__)), pin(Path(__file__).with_name("_release_partitions.py")),
                 pin(Path(__file__).with_name("_release_validation.py")),
                 pin(Path(__file__).with_name("verify_external_validation_receipt.py"))]
    return {"schema": "sapote-mamey.seal-script-plan.v1", "status": "PREPARED_OWNER_REVIEW",
            "cut_folder": str(cut), "source_suite": source, "archive_suite": extracted,
            "archive": archive_pin, "dispositions": disposition_pin, "named_differences": named,
            "owner_script": pin(owner_script), "machinery": machinery,
            "holds": ["No release, seal, publication or scientific acceptance is inferred",
                      "Explanations are operator dispositions, not independently established causes",
                      "Owner consumer safety and other release gates require their existing review"]}


def recheck_plan(path: Path, expected_sha256: str):
    """Recompute the exact plan at owner execution time; changed evidence refuses."""
    pin(path, expected_sha256)
    plan = read_json(path)
    require(isinstance(plan, dict) and plan.get("schema") == "sapote-mamey.seal-script-plan.v1", "invalid plan")
    for item in plan.get("machinery", []):
        pin(Path(item["path"]), item["sha256"])
    current = build_plan(cut_folder=Path(plan["cut_folder"]),
        source_log=Path(plan["source_suite"]["log"]["path"]),
        archive_log=Path(plan["archive_suite"]["log"]["path"]),
        source_evidence=Path(plan["source_suite"]["manifest"]["path"]),
        archive_evidence=Path(plan["archive_suite"]["manifest"]["path"]),
        differences=Path(plan["dispositions"]["path"]), archive=Path(plan["archive"]["path"]),
        archive_sha256=plan["archive"]["sha256"], owner_script=Path(plan["owner_script"]["path"]))
    require(current == plan, "plan inputs, trees, machinery or named differences changed")
    return plan


def emit_candidate(plan, output: Path):
    """Create a fresh review directory with a nonexecutable wrapper and pinned plan."""
    output = output.absolute()
    # Keep outputs outside source evidence and cut records; no mutation of inputs.
    for root in (Path(plan["cut_folder"]), Path(plan["source_suite"]["tree"]["path"]),
                 Path(plan["archive_suite"]["tree"]["path"])):
        require(not output.resolve().is_relative_to(root), "candidate output overlaps bound evidence")
    require(output.parent.is_dir(), "candidate parent directory must already exist")
    require(not output.exists() and not output.is_symlink(), "candidate output is occupied")
    output.mkdir()
    plan_path = output / "PLAN.json"
    with plan_path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(plan, indent=2, sort_keys=True) + "\n")
    digest = pin(plan_path)["sha256"]
    q = shlex.quote
    lines = ["#!/usr/bin/env bash", "# PREPARED owner-review wrapper. No seal has run.",
             "# Review the pinned owner consumer and every PLAN.json disposition first.",
             "set -euo pipefail", "[ \"${SAPOTE_OWNER_SEAL_APPROVED:-}\" = " + q(digest) + " ] || {",
             "  echo 'REFUSED: explicit owner approval for this exact plan is required' >&2; exit 2; }",
             q(str(Path(sys.executable).absolute())) + " " + q(str(Path(__file__).absolute()))
             + " --verify-plan " + q(str(plan_path)) + " --plan-sha256 " + q(digest),
             "# Each named node/outcome/reason is rechecked by the exact pinned plan above.",
             "exec /bin/bash " + q(plan["owner_script"]["path"]), ""]
    wrapper = output / "SEAL_CANDIDATE.sh"
    with wrapper.open("x", encoding="utf-8") as stream:
        stream.write("\n".join(lines))
    wrapper.chmod(0o600)
    return {"plan": pin(plan_path), "script": pin(wrapper), "status": "PREPARED_OWNER_REVIEW"}


def main(argv=None):
    """Parse generation or evidence-only recheck; no execution operation exists."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-plan", type=Path)
    parser.add_argument("--plan-sha256")
    for name in ("cut-folder", "source-log", "archive-log", "source-evidence", "archive-evidence",
                 "differences", "archive", "owner-script", "output"):
        parser.add_argument("--" + name, type=Path)
    parser.add_argument("--archive-sha256")
    args = parser.parse_args(argv)
    try:
        if args.verify_plan is not None:
            require(re.fullmatch("[0-9a-f]{64}", args.plan_sha256 or ""), "plan SHA-256 required")
            require(all(getattr(args, name) is None for name in
                ("cut_folder", "source_log", "archive_log", "source_evidence", "archive_evidence",
                 "differences", "archive", "owner_script", "output", "archive_sha256")),
                "verify-plan cannot be combined with generation arguments")
            recheck_plan(args.verify_plan, args.plan_sha256)
            sys.stdout.write("SEAL PLAN: evidence rechecked; owner and release holds remain\n")
        else:
            require(args.plan_sha256 is None, "plan-sha256 requires verify-plan")
            values = vars(args).copy()
            values.pop("verify_plan"); values.pop("plan_sha256")
            require(all(v is not None for v in values.values()), "all generation inputs are required")
            output = values.pop("output")
            result = emit_candidate(build_plan(**values), output)
            sys.stdout.write(json.dumps(result, sort_keys=True) + "\n")
        return 0
    except (ValueError, OSError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        sys.stderr.write("SEAL PLAN: REFUSED: " + str(exc) + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
