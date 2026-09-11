"""Read-only metric checks and transactional gappa graft generation.

The placement file, not a possibly older ref.tree, owns the graft backbone.
Split reference edges must be summed, never individually reset to whole edges.
"""
import io
import json
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile


def _tips(tree):
    names = [tip.name for tip in tree.get_terminals()]
    if any(not name for name in names) or len(set(names)) != len(names):
        raise ValueError("GRAFT_INTEGRITY: missing or duplicate tip names")
    return set(names)


def _metric(tree, references):
    """Unrooted reference splits; sum fragments after projecting out queries."""
    result = {}
    for clade in tree.find_clades(order="postorder"):
        length = clade.branch_length
        if length is None and clade is tree.root:
            length = 0.0
        if length is None or not math.isfinite(length) or length < 0:
            raise ValueError("GRAFT_INTEGRITY: missing, negative or nonfinite length")
        side = frozenset(t.name for t in clade.get_terminals()) & references
        other = references - side
        if not side or not other:
            continue
        key = min(tuple(sorted(side)), tuple(sorted(other)))
        total, count = result.get(key, (0.0, 0))
        result[key] = (total + length, count + 1)
    return result


def verify_graft(graft_path, jplace_path):
    """Verify reference topology/metric and best-placement query pendants; never write.

    Tolerance is a per-segment 0.0000051 allowance for five-decimal Newick
    serialization. This is numerical QA, not biological or placement validation.
    """
    from Bio import Phylo
    with open(jplace_path) as handle:
        data = json.load(handle)
    backbone = Phylo.read(io.StringIO(re.sub(r"\{\d+\}", "", data["tree"])), "newick")
    references = _tips(backbone)
    if len(references) < 2:
        raise ValueError("GRAFT_INTEGRITY: at least two references required")
    fields = data["fields"]
    weight = fields.index("like_weight_ratio")
    pendant = fields.index("pendant_length")
    queries = {}
    for item in data["placements"]:
        rows = item["p"]
        if not rows:
            raise ValueError("GRAFT_INTEGRITY: query has no placements")
        if any(not math.isfinite(row[weight]) or not 0 <= row[weight] <= 1 for row in rows):
            raise ValueError("GRAFT_INTEGRITY: invalid likelihood weights")
        best_weight = max(row[weight] for row in rows)
        lengths = [row[pendant] for row in rows if row[weight] == best_weight]
        if any(not math.isfinite(n) or n < 0 for n in lengths):
            raise ValueError("GRAFT_INTEGRITY: invalid pendant")
        if ("n" in item) == ("nm" in item):
            raise ValueError("GRAFT_INTEGRITY: require exactly one query-name field")
        names = item["n"] if "n" in item else [pair[0] for pair in item["nm"]]
        if not names:
            raise ValueError("GRAFT_INTEGRITY: unnamed query")
        for name in names:
            if not isinstance(name, str) or not name or name in references or name in queries:
                raise ValueError("GRAFT_INTEGRITY: duplicate or colliding query name")
            queries[name] = lengths
    graft = Phylo.read(graft_path, "newick")
    if _tips(graft) != references | set(queries):
        raise ValueError("GRAFT_INTEGRITY: graft tip inventory differs from jplace")
    expected, observed = _metric(backbone, references), _metric(graft, references)
    # Even a zero-length topology change is not silently accepted.
    if expected.keys() != observed.keys():
        raise ValueError("GRAFT_INTEGRITY: reference topology differs from jplace")
    for key, (length, _) in expected.items():
        actual, segments = observed[key]
        if abs(length - actual) > 0.0000051 * segments + 1e-12:
            raise ValueError("GRAFT_INTEGRITY: reference edge metric differs from jplace")
    for tip in graft.get_terminals():
        if tip.name in queries and not any(
            abs(tip.branch_length - value) <= 0.0000051 + 1e-12
            for value in queries[tip.name]
        ):
            raise ValueError("GRAFT_INTEGRITY: query pendant differs from best placement")
    return {"status": "PASS", "reference_tips": len(references),
            "query_tips": len(queries), "authority": "jplace.tree",
            "scope": "reference topology and metric; best-placement pendants"}


def generate_checked_graft(gappa, jplace_path, outdir, env):
    """Run in a fresh directory; promote only one checked graft, byte-for-byte."""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".graft-check-", dir=outdir) as staging:
        subprocess.run([gappa, "examine", "graft", "--jplace-path", str(jplace_path),
                        "--fully-resolve", "--out-dir", staging], env=env, check=True)
        candidates = list(Path(staging).glob("*.newick"))
        if len(candidates) != 1:
            raise ValueError("GRAFT_INTEGRITY: expected exactly one newly generated tree")
        verify_graft(candidates[0], jplace_path)
        target = outdir / candidates[0].name
        os.replace(candidates[0], target)
    return str(target)
