#!/usr/bin/env python3
"""Experimental same-snapshot wrapper for one pinned tree-sanity gate.

Diagnostic only: an observed roster is not scientific acceptance or an audit
binding. Importing the trusted pinned gate also imports its unpinned dependencies.
"""
import argparse
import hashlib
import types
import io
import json
import math
import sys
from pathlib import Path

SUPPORTED_GATE_SHA256 = 'b84b7147eb83f91a02f8738e8ea54930d032e508acffdf777108723d1ed9e0e3'
MAX_TREE_BYTES = 8 * 1024 * 1024  # Optional diagnostic limit, not a universal tree limit.


def read_tree_snapshot(path):
    with Path(path).open('rb') as handle:
        raw = handle.read(MAX_TREE_BYTES + 1)
    if len(raw) > MAX_TREE_BYTES:
        raise ValueError('tree exceeds 8 MiB snapshot limit')
    return raw


def run(tree_path, gate_path, outgroups):
    try:
        gate_path = Path(gate_path).resolve(strict=True)
        gate_raw = gate_path.read_bytes()
        gate_hash = hashlib.sha256(gate_raw).hexdigest()
        if gate_hash != SUPPORTED_GATE_SHA256:
            raise ValueError('unsupported gate bytes')
        if any(not isinstance(x, str) or not x or x != x.strip() or ',' in x for x in outgroups):
            raise ValueError('outgroup arguments must be nonempty, trimmed and contain no comma')
        if len(set(outgroups)) != len(outgroups):
            raise ValueError('duplicate outgroup arguments')
        raw = read_tree_snapshot(tree_path)
        tree_hash = hashlib.sha256(raw).hexdigest()
        source = raw.decode('utf-8')
        # The native parser does not consume/check all trailing input. Require a
        # single complete Newick through an independent parser before reporting.
        from Bio import Phylo
        if not source.rstrip().endswith(';'):
            raise ValueError('Newick must end with a semicolon')
        try:
            independent = Phylo.read(io.StringIO(source), 'newick')
        except Exception as exc:
            raise ValueError('invalid or multiple Newick trees: ' + str(exc)) from exc
        independent_tips = [tip.name for tip in independent.get_terminals()]
        gate = types.ModuleType('_snapshot_pinned_gate')
        gate.__file__ = str(gate_path)
        # Execute the exact hashed source bytes. Its imports and interpreter are
        # trusted but not pinned; executing this code is not a sandbox.
        exec(compile(gate_raw, str(gate_path), 'exec'), gate.__dict__)
        # Native parser accepts a path; bind its open to this one byte snapshot.
        # The returned root is shared by recognition and the native check.
        gate.open = lambda _path: io.StringIO(source)
        root = gate.parse('<snapshot>')
        tips = [tip.name for tip in root.leaves()]
        if tips != independent_tips:
            raise ValueError('native and independent parsers disagree on ordered tip identities')
        def compare_nodes(native, other, is_root=False):
            if len(native.k) != len(other.clades):
                raise ValueError('native and independent parsers disagree on topology')
            if not is_root:
                length = other.branch_length
                if length is None or not math.isfinite(length) or length < 0:
                    raise ValueError('each non-root branch needs a finite nonnegative length')
                if native.l != length:
                    raise ValueError('native and independent parsers disagree on branch length')
            for left, right in zip(native.k, other.clades):
                compare_nodes(left, right)
        compare_nodes(root, independent.root, is_root=True)
        if len(tips) != len(set(tips)) or any(not t or t != t.strip() for t in tips):
            raise ValueError('tree tip identities must be nonempty, trimmed and unique')
        effective = outgroups or None
        recognized = sorted(t for t in tips if gate._is_outgroup_tip(t, effective))
        ok, report = gate.check(root, outgroup=effective)
        return {'schema': 'tree-sanity-snapshot-v1', 'status': 'OBSERVED',
                'tree_sha256': tree_hash, 'gate_sha256': gate_hash,
                'effective_outgroup_arguments': list(outgroups), 'tip_names': sorted(tips),
                'recognized_outgroup_tips': recognized, 'gate_pass': bool(ok), 'gate_report': report,
                'scope': 'Experimental snapshot: recognition and gate check use the same parsed root. Gate imports/dependencies and interpreter are trusted and not pinned; gate dependencies and filesystem paths are not race-protected. Topology, ordered tips and finite nonnegative non-root branch lengths are compared between parsers; complete parser equivalence is not established. No scientific validity or audit binding is asserted.'}
    except (OSError, UnicodeError, ValueError, ImportError, AttributeError, RecursionError) as exc:
        return {'schema': 'tree-sanity-snapshot-v1', 'status': 'ERROR', 'error': str(exc)}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--tree', required=True)
    ap.add_argument('--gate', required=True)
    ap.add_argument('--outgroup', action='append', default=[])
    args = ap.parse_args()
    result = run(args.tree, args.gate, args.outgroup)
    sys.stdout.write(json.dumps(result, indent=2) + "\n")
    return 0 if result['status'] == 'OBSERVED' and result['gate_pass'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
