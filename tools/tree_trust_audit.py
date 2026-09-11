#!/usr/bin/env python3
"""Audit explicitly bound tree artifacts; results cover mechanical checks only.

Input JSON: {"trees": [{"tree": "tree.nwk", "metadata": "meta.tsv",
"render": "tree.png", "render_receipt": "render.json", "outgroups": ["reference"]}]}.
Relative paths resolve against the manifest. No discovery, newest-file selection,
registry mutation, scientific root validation or publication verdict is performed.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def _sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tips(path):
    from Bio import Phylo

    if not path.read_text().rstrip().endswith(";"):
        raise ValueError("Newick must end with a semicolon")
    names = [tip.name for tip in Phylo.read(str(path), "newick").get_terminals()]
    if len(names) < 2 or any(not name or not name.strip() for name in names):
        raise ValueError("Tree needs at least two nonempty tip identities")
    if len(set(names)) != len(names):
        raise ValueError("Duplicate tree tip identities")
    return names


def audit(entry, base, gate_path=None, timeout=300, tip_column="tip", label_column="label"):
    row = {"tree": entry.get("tree", ""), "checks": {},
           "scope": "mechanical only; rooting, taxonomy, rendering appearance and scientific acceptance unverified"}
    checks = row["checks"]

    def check(name, status, detail):
        checks[name] = {"status": status, "detail": detail}

    def bound(key):
        value = entry.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Explicit {key} path required")
        return Path(base) / value

    tips = None
    try:
        tree = bound("tree")
        tips = _tips(tree)
        row["tree_sha256"] = _sha(tree)
        check("tree", "PASS", f"{len(tips)} unique named tips")
    except (OSError, ValueError, ImportError) as exc:
        check("tree", "FAIL", str(exc))

    try:
        metadata = bound("metadata")
        with metadata.open(newline="") as fh:
            reader = csv.DictReader(fh, delimiter="\t")
            if not reader.fieldnames or not {tip_column, label_column}.issubset(reader.fieldnames):
                raise ValueError("Metadata requires configured tip and label columns")
            if len(reader.fieldnames) != len(set(reader.fieldnames)):
                raise ValueError("Duplicate metadata columns")
            records = list(reader)
        if any(None in r or any(v is None for v in r.values()) for r in records):
            raise ValueError("Metadata column width mismatch")
        ids = [r[tip_column] for r in records]
        if any(not key.strip() for key in ids) or len(ids) != len(set(ids)):
            raise ValueError("Metadata tip identities must be nonempty and unique")
        labels = {r[tip_column]: r[label_column] for r in records}
        if tips is None:
            check("metadata", "UNVERIFIED", "No valid tree for metadata join")
        else:
            missing = sorted(set(tips) - set(labels))
            extra = sorted(set(labels) - set(tips))
            bad = [t for t in tips if t in labels and (not labels[t].strip() or "unnamed" in labels[t].casefold())]
            check("metadata", "FAIL" if missing or extra or bad else "PASS",
                  json.dumps({"missing_tips": missing, "extra_metadata_tips": extra, "missing_labels": bad}))
        row["metadata_sha256"] = _sha(metadata)
    except (OSError, ValueError) as exc:
        check("metadata", "FAIL", str(exc))

    outgroups = entry.get("outgroups")
    if not isinstance(outgroups, list) or not outgroups:
        check("outgroup_membership", "UNVERIFIED", "Explicit outgroup tip identities required")
    elif any(not isinstance(t, str) or not t.strip() for t in outgroups) or len(set(outgroups)) != len(outgroups):
        check("outgroup_membership", "FAIL", "Outgroup identities must be nonempty unique strings")
    elif tips is None:
        check("outgroup_membership", "UNVERIFIED", "No valid tree")
    elif not set(outgroups).issubset(tips) or set(outgroups) == set(tips):
        check("outgroup_membership", "FAIL", "Declared outgroups must be an exact proper subset of tree tips")
    else:
        check("outgroup_membership", "PASS", "Declared tips present; biological outgroup suitability unverified")

    if gate_path is None or tips is None:
        check("gate", "UNVERIFIED", "Explicit gate script and valid tree required")
    else:
        try:
            gate = Path(gate_path).resolve(strict=True)
            before = _sha(gate)
            result = subprocess.run([sys.executable, str(gate), str(tree.resolve())],
                                    capture_output=True, text=True, timeout=timeout)
            row["gate_sha256"] = before
            row["gate_exit"] = result.returncode
            row["gate_stdout"] = result.stdout
            row["gate_stderr"] = result.stderr
            if before != _sha(gate) or row["tree_sha256"] != _sha(tree):
                check("gate", "FAIL", "Gate or tree changed during invocation")
            else:
                status = "PASS" if result.returncode == 0 else "FAIL" if result.returncode == 2 else "UNVERIFIED"
                check("gate", status, f"Configured gate exit {result.returncode}; gate scope remains limited")
        except (OSError, subprocess.TimeoutExpired) as exc:
            check("gate", "UNVERIFIED", f"{type(exc).__name__}: {exc}")

    try:
        render, receipt_path = bound("render"), bound("render_receipt")
        receipt = json.loads(receipt_path.read_text())
        if not isinstance(receipt, dict) or render.stat().st_size == 0:
            raise ValueError("Nonempty render and receipt object required")
        actual = {"tree_sha256": _sha(bound("tree")),
                  "metadata_sha256": _sha(bound("metadata")), "render_sha256": _sha(render)}
        row["render_sha256"] = actual["render_sha256"]
        row["render_receipt_sha256"] = _sha(receipt_path)
        if any(receipt.get(key) != value for key, value in actual.items()):
            check("render_binding", "FAIL", "Render receipt hash mismatch")
        elif any(row.get(key) != actual[key] for key in ("tree_sha256", "metadata_sha256")):
            check("render_binding", "FAIL", "Inputs changed or could not be audited")
        else:
            check("render_binding", "PASS", "Receipt binds exact bytes; appearance and execution provenance unverified")
    except (OSError, ValueError) as exc:
        check("render_binding", "UNVERIFIED", str(exc))

    statuses = {c["status"] for c in checks.values()}
    row["verdict"] = "FAIL" if "FAIL" in statuses else "UNVERIFIED" if "UNVERIFIED" in statuses else "MECHANICAL_PASS"
    return row


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--gate", type=Path, help="Exact Python gate script: 0 pass, 2 fail, other unverified")
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--tip-column", default="tip")
    parser.add_argument("--label-column", default="label")
    args = parser.parse_args(argv)
    try:
        if not 0 < args.timeout < float("inf"):
            raise ValueError("Timeout must be finite and positive")
        manifest = json.loads(args.manifest.read_text())
        entries = manifest["trees"]
        if not isinstance(entries, list) or not entries or any(not isinstance(e, dict) for e in entries):
            raise ValueError("Manifest trees must be a nonempty list of objects")
        rows = [audit(e, args.manifest.resolve().parent, args.gate, args.timeout,
                      args.tip_column, args.label_column) for e in entries]
        payload = {"scope": "mechanical evidence only; no scientific or publication approval", "trees": rows}
        # Exclusive creation prevents overwriting a prior audit or any input.
        with args.output.open("x") as fh:
            json.dump(payload, fh, indent=2, allow_nan=False)
            fh.write("\n")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        sys.stderr.write(f"REFUSED: {exc}\n")
        return 2
    return 0 if all(row["verdict"] == "MECHANICAL_PASS" for row in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
