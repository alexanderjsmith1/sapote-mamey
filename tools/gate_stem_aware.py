#!/usr/bin/env python3
"""Run the sibling tree gate, optionally on a verified display's analysis parent.

No bundle search or filename-derived authority. Missing machinery is a refusal.
The structural ingroup-stem exemption never waives terminal or other branches.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import sys

from _console import emit
import logging
_LOG = logging.getLogger(__name__)

from collapse_near_identical import (SCHEMA, binding, build_display, digest,
                                     read_meta, write_exclusive)


def _engine_gate():
    checker = Path(__file__).resolve().with_name("tree_sanity_check.py")
    if not checker.is_file():
        raise FileNotFoundError("GATE_UNAVAILABLE: sibling tree_sanity_check.py missing")
    return checker


def engine_module():
    spec = importlib.util.spec_from_file_location("bound_tree_checker", _engine_gate())
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("DUPLICATE_RECEIPT_KEY")
        result[key] = value
    return result


def verify_display(receipt_path, expected_sha256, tree, metadata, parent=None):
    receipt_path = Path(receipt_path).resolve()
    raw = receipt_path.read_bytes()
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256 or "") or digest(raw) != expected_sha256:
        raise ValueError("DISPLAY_RECEIPT_HASH_MISMATCH_OR_MISSING")
    receipt = json.loads(raw, object_pairs_hook=unique_object)
    if set(receipt) != {"schema", "authority", "inputs", "outputs", "parameters"} or receipt["schema"] != SCHEMA:
        raise ValueError("DISPLAY_RECEIPT_SCHEMA")
    if receipt["authority"] != "DISPLAY_ONLY_NOT_SCIENTIFIC_ACCEPTANCE":
        raise ValueError("DISPLAY_RECEIPT_AUTHORITY")
    resolved = {}
    for group, keys in (("inputs", {"alignment", "analysis_tree", "metadata"}),
                        ("outputs", {"tree", "metadata", "ledger"})):
        if set(receipt[group]) != keys:
            raise ValueError("DISPLAY_RECEIPT_BINDINGS")
        resolved[group] = {}
        for key, record in receipt[group].items():
            if not isinstance(record, dict) or set(record) != {"path", "sha256", "bytes"}:
                raise ValueError("DISPLAY_RECEIPT_RECORD_SCHEMA")
            locator = record["path"]
            if not isinstance(locator, str) or not locator or Path(locator).is_absolute():
                raise ValueError("DISPLAY_RECEIPT_REQUIRES_RELATIVE_LOCATOR")
            path = (receipt_path.parent / locator).resolve()
            if group == "outputs" and path.parent != receipt_path.parent:
                raise ValueError("DISPLAY_OUTPUT_OUTSIDE_RECEIPT_DIRECTORY")
            current = binding(path, receipt_path.parent)
            if current != record:
                raise ValueError(f"DISPLAY_BOUND_FILE_CHANGED: {group}.{key}")
            resolved[group][key] = path
    if resolved["outputs"]["tree"] != Path(tree).resolve() or resolved["outputs"]["metadata"] != Path(metadata).resolve():
        raise ValueError("DISPLAY_REQUEST_DOES_NOT_MATCH_RECEIPT")
    inputs = resolved["inputs"]
    if parent is not None and inputs["analysis_tree"] != Path(parent).resolve():
        raise ValueError("DISPLAY_PARENT_DOES_NOT_MATCH_RECEIPT")
    regenerated = build_display(inputs["alignment"], inputs["analysis_tree"], inputs["metadata"], receipt["parameters"])
    for key, data in regenerated.items():
        if data != resolved["outputs"][key].read_bytes():
            raise ValueError(f"DISPLAY_REPLAY_MISMATCH: {key}")
    return receipt, resolved


def gate(tree, *, abs_limit=0.25, factor=10.0, dominate=0.50, outgroup=None):
    engine = engine_module()
    root = engine.parse(tree)
    nodes = list(root.walk())
    tips = list(root.leaves())
    if len({t.name for t in tips}) != len(tips) or any(not t.name for t in tips):
        raise ValueError("GATE_DUPLICATE_OR_EMPTY_TREE_TIP")
    if any(not math.isfinite(n.l) or n.l < 0 for n in nodes):
        raise ValueError("GATE_INVALID_BRANCH_LENGTH")
    ok, report = engine.check(root, abs=abs_limit, factor=factor, dominate=dominate, outgroup=outgroup)
    if ok:
        return True, report
    # The engine's exact structured tree identifies the candidate stem. Printed
    # rounded branch lengths cannot identify a branch and are never compared.
    kinds = set(re.findall(r"^  \[([A-Z_]+)\]$", report, re.M))
    if kinds != {"DOMINATING_BRANCH"}:
        return False, report
    ingroup = {t.name for t in tips if not engine._is_outgroup_tip(t.name, outgroup)}
    outgroups = {t.name for t in tips} - ingroup
    stems = [n for n in root.k if n.k and {t.name for t in n.leaves()} == ingroup]
    if not outgroups or len(stems) != 1 or len(root.k) != 2:
        return False, report
    stem = stems[0]
    depths = {root: 0.0}
    for node in nodes:
        for child in node.k:
            depths[child] = depths[node] + child.l
    maxdepth = max(depths[t] for t in tips) or 1.0
    # If the engine reports only its longest branch, another dominating branch
    # can be masked. Confirm that no other non-outgroup branch exceeds the same
    # ceiling before exempting the root-adjacent ingroup stem.
    offenders = [n for n in nodes if not engine._all_leaves_outgroup(n, outgroup)
                 and n.l > dominate * maxdepth]
    if offenders != [stem]:
        return False, report
    return True, (report + f"\n  [stem-exemption] root-adjacent ingroup stem only: {stem.l:.17g}; "
                  f"{len(ingroup)} tips; all terminal and other branch checks retained."
                  "\n  PASS (structural ingroup-stem display exemption; judgment deferred)")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    ap.add_argument("tree")
    ap.add_argument("--metadata")
    ap.add_argument("--parent")
    ap.add_argument("--receipt")
    ap.add_argument("--receipt-sha256")
    ap.add_argument("--outgroup", action="append")
    ap.add_argument("--render-prefix", help="After rendering, bind existing PDF, PNG and session outputs")
    a = ap.parse_args(argv)
    try:
        checked_tree = Path(a.tree)
        receipt, resolved = None, None
        display_note = ""
        if a.receipt:
            if not a.metadata:
                raise ValueError("DISPLAY_METADATA_REQUIRED")
            receipt, resolved = verify_display(a.receipt, a.receipt_sha256, a.tree, a.metadata, a.parent)
            checked_tree = resolved["inputs"]["analysis_tree"]
            _, original = read_meta(resolved["inputs"]["metadata"])
            _, displayed = read_meta(resolved["outputs"]["metadata"])
            removed = sum(r["role"] == "outgroup" for r in original) if receipt["parameters"]["prune_outgroup"] else 0
            display_note = (f"DISPLAY_NOTE: Display derivative: {len(displayed)} of {len(original)} tips shown; "
                  f"{removed} outgroup tips pruned for display. Reference grouping uses pairwise "
                  f'<= {receipt["parameters"]["max_nt"]} mismatches over >= {receipt["parameters"]["min_cols"]} '
                  "shared A/C/G/T columns. All queries retained; member source records are in the ledger.")
        elif a.parent and Path(a.parent).resolve() != checked_tree.resolve():
            raise ValueError("A distinct analysis parent requires a hash-bound display receipt")
        elif a.receipt_sha256 or a.render_prefix:
            raise ValueError("DISPLAY_RECEIPT_REQUIRED")
        ok, report = gate(checked_tree, outgroup=a.outgroup)
        emit((display_note + "\n" if display_note else "") + report)
        if not ok:
            return 2
        if a.render_prefix:
            # Verify once more after graphics generation, before issuing a binding.
            verify_display(a.receipt, a.receipt_sha256, a.tree, a.metadata, a.parent)
            prefix = Path(a.render_prefix)
            target = Path(str(prefix) + ".render_receipt.json")
            outputs = {suffix: binding(Path(str(prefix) + suffix), target.parent.resolve())
                       for suffix in (".pdf", ".png", ".session.txt")}
            payload = {"schema": "sapote.tree-render.v1", "authority": "RENDER_ONLY_NOT_SCIENTIFIC_ACCEPTANCE",
                       "display_receipt": binding(Path(a.receipt), target.parent.resolve()),
                       "analysis_tree": binding(checked_tree, target.parent.resolve()),
                       "renderer": binding(Path(__file__).with_name("ggtree_rect_heatmap.R"), target.parent.resolve()),
                       "checker": binding(_engine_gate(), target.parent.resolve()),
                       "gate_wrapper": binding(Path(__file__), target.parent.resolve()),
                       "outputs": outputs, "gate_report": report}
            write_exclusive(target, (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode())
        return 0
    except FileNotFoundError as exc:
        _LOG.error(f"REFUSED [GATE_UNAVAILABLE]: {exc}")
        return 3
    except (ValueError, OSError, ImportError, TypeError, KeyError, IndexError) as exc:
        _LOG.error(f"REFUSED [TREE_DISPLAY_GATE]: {exc}")
        return 2


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    raise SystemExit(main())
