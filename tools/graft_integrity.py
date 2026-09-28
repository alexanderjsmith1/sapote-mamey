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


# ---- v9.7.444: EPA-ng default branch lengths ------------------------------------------------------------------
# EPA-ng writes -ln 0.9 = 0.1053605157 where it has not estimated a length:
#   * in the jplace tree, on every reference branch that is exactly 0 in the refpkg ref.tree;
#   * as the best-placement pendant of some queries (reproduces with and without --no-heur).
# verify_graft() checks the graft against the jplace tree, so both defaults pass it. The functions below restore
# reference edges from ref.tree and re-estimate default pendants with RAxML-NG. The raw gappa graft is kept.
PLACEHOLDER = 0.1053605157


def _split_lengths(tree, references):
    """Unrooted reference split -> summed length (fragments and the two root-adjacent edges add up)."""
    out = {}
    for clade in tree.find_clades():
        if clade is tree.root:
            continue
        side = frozenset(t.name for t in clade.get_terminals()) & references
        other = references - side
        if not side or not other:
            continue
        key = min(tuple(sorted(side)), tuple(sorted(other)))
        out[key] = out.get(key, 0.0) + (clade.branch_length or 0.0)
    return out


def backbone_defaults(jplace_path, ref_tree_path):
    """Compare the jplace backbone with ref.tree. Returns (reset_to_default, other_differences) as split lists.

    Refuses when the two trees do not have the same reference tips and topology."""
    from Bio import Phylo
    with open(jplace_path) as handle:
        backbone = Phylo.read(io.StringIO(re.sub(r"\{\d+\}", "", json.load(handle)["tree"])), "newick")
    ref = Phylo.read(ref_tree_path, "newick")
    references = _tips(backbone)
    if _tips(ref) != references:
        raise ValueError("GRAFT_LENGTHS: ref.tree tips differ from the jplace backbone")
    a, b = _split_lengths(ref, references), _split_lengths(backbone, references)
    if a.keys() != b.keys():
        raise ValueError("GRAFT_LENGTHS: ref.tree topology differs from the jplace backbone")
    reset = [k for k in a if a[k] <= 1e-6 and abs(b[k] - PLACEHOLDER) < 1e-5]
    other = [k for k in a if k not in reset and abs(a[k] - b[k]) > 0.0000051 * 2 + 1e-12]
    return reset, other


def default_pendant_queries(jplace_path):
    """Query names whose best placement has the EPA-ng default pendant."""
    with open(jplace_path) as handle:
        data = json.load(handle)
    fields = data["fields"]
    weight, pendant = fields.index("like_weight_ratio"), fields.index("pendant_length")
    names = []
    for item in data["placements"]:
        best = max(item["p"], key=lambda row: row[weight])
        if abs(best[pendant] - PLACEHOLDER) < 1e-6:
            names += item["n"] if "n" in item else [pair[0] for pair in item["nm"]]
    return names


def restore_reference_edges(graft, ref_tree, references):
    """Scale each reference edge of a graft (the chain of segments between two reference nodes) to its ref.tree length.

    Where a query attaches along an edge keeps its proportion. Query-only branches are not touched. Returns the number of
    reference edges changed by more than 1e-4."""
    target = _split_lengths(ref_tree, references)
    parent = {c: p for p in graft.find_clades() for c in p.clades}

    def is_ref_node(clade):
        if clade.is_terminal():
            return clade.name in references
        return sum(any(t.name in references for t in k.get_terminals()) for k in clade.clades) >= 2
    chains = {}
    for node in graft.find_clades():
        if node is graft.root or not is_ref_node(node):
            continue
        chain, cur = [node], parent[node]
        while cur is not graft.root and not is_ref_node(cur):
            chain.append(cur)
            cur = parent[cur]
        side = frozenset(t.name for t in node.get_terminals()) & references
        key = min(tuple(sorted(side)), tuple(sorted(references - side)))
        chains.setdefault(key, []).extend(chain)
    changed = 0
    for key, segments in chains.items():
        if key not in target:
            raise ValueError("GRAFT_LENGTHS: graft reference split missing from ref.tree")
        have = sum(c.branch_length or 0.0 for c in segments)
        want = target[key]
        changed += abs(have - want) > 1e-4
        factor = want / have if have > 0 else 0.0
        for c in segments:
            c.branch_length = (c.branch_length or 0.0) * factor
    return changed


def apply_pendant_estimates(graft, estimates, references):
    """Set each estimated query's full pendant path to its estimate.

    gappa can give queries on one edge a shared stem. Within each query-only subtree the shared segments are scaled
    by the smallest target/current ratio, then each tip branch is set so its path equals its target. Queries not in
    `estimates` keep their current path. No branch becomes negative."""
    parent = {c: p for p in graft.find_clades() for c in p.clades}

    def query_only(clade):
        return all(t.name not in references for t in clade.get_terminals())
    roots = [c for c in graft.find_clades()
             if c is not graft.root and query_only(c) and not query_only(parent[c])]
    done = 0
    for r in roots:
        tips = r.get_terminals()
        if not any(t.name in estimates for t in tips):
            continue
        path = {t.name: sum(x.branch_length or 0.0 for x in [r] + r.get_path(t)) if t is not r
                else (r.branch_length or 0.0) for t in tips}
        for t in tips:
            if t.name in estimates and abs(path[t.name] - PLACEHOLDER) > 1e-5:
                raise ValueError(f"GRAFT_LENGTHS: {t.name} pendant path is not the EPA-ng default")
        target = {n: estimates.get(n, path[n]) for n in path}
        k = min((target[n] / path[n]) if path[n] > 0 else 1.0 for n in path)
        if r.is_terminal():
            r.branch_length = target[r.name]
        else:
            for c in [r] + [x for x in r.find_clades() if x is not r and not x.is_terminal()]:
                c.branch_length = (c.branch_length or 0.0) * k
            for t in tips:
                above = sum(x.branch_length or 0.0 for x in [r] + r.get_path(t)[:-1])
                t.branch_length = max(0.0, target[t.name] - above)
        done += sum(1 for t in tips if t.name in estimates)
    return done


def reestimate_pendants(graft_path, names, references, ref_aln, query_aln, model, raxml, env=None):
    """RAxML-NG --evaluate per query: reference tree plus that one query at its gappa position, topology and model
    fixed, branch lengths optimised. Returns {query: (estimate, logLikelihood)}."""
    from Bio import Phylo

    def fasta(path):
        seqs, name = {}, None
        for line in open(path):
            line = line.rstrip("\n")
            if line.startswith(">"):
                name = line[1:].split()[0]
                seqs[name] = []
            elif name:
                seqs[name].append(line)
        return {k: "".join(v) for k, v in seqs.items()}
    seqs = fasta(ref_aln)
    seqs.update({k: v for k, v in fasta(query_aln).items() if k not in seqs})
    out = {}
    for q in names:
        tree = Phylo.read(graft_path, "newick")
        for tip in list(tree.get_terminals()):
            if tip.name != q and tip.name not in references:
                tree.prune(tip)
        with tempfile.TemporaryDirectory(prefix=".pendant-") as td:
            td = Path(td)
            Phylo.write(tree, td / "t.nwk", "newick")
            with open(td / "a.fasta", "w") as handle:
                for tip in tree.get_terminals():
                    handle.write(f">{tip.name}\n{seqs[tip.name]}\n")
            run = subprocess.run([raxml, "--evaluate", "--msa", str(td / "a.fasta"), "--tree", str(td / "t.nwk"),
                                  "--model", str(model), "--opt-model", "off", "--opt-branches", "on", "--threads", "1",
                                  "--prefix", str(td / "e"), "--redo"], capture_output=True, text=True, env=env)
            if run.returncode:
                raise ValueError(f"GRAFT_LENGTHS: raxml-ng --evaluate failed for {q}")
            est = next(t.branch_length for t in Phylo.read(td / "e.raxml.bestTree", "newick").get_terminals()
                       if t.name == q)
            ll = next((l.split()[-1] for l in run.stdout.splitlines() if "final logLikelihood" in l), "")
        out[q] = (est, ll)
    return out


def generate_length_restored_graft(graft_path, jplace_path, ref_tree_path, outdir, ref_aln=None, query_aln=None,
                                   model=None, raxml=None, env=None):
    """Write <graft>.lengths_restored.newick and BRANCH_LENGTH_RESTORE.tsv next to it; return the restored path.

    Reference edges come from ref.tree. Default pendants are re-estimated with RAxML-NG when raxml, both
    alignments and the model are given. Otherwise they are listed in the ledger as NOT_REESTIMATED and stay at the
    default."""
    from Bio import Phylo
    reset, other = backbone_defaults(jplace_path, ref_tree_path)
    if other:
        raise ValueError(f"GRAFT_LENGTHS: {len(other)} reference edge(s) differ from ref.tree beyond the EPA-ng default")
    graft = Phylo.read(graft_path, "newick")
    ref = Phylo.read(ref_tree_path, "newick")
    references = _tips(ref)
    names = default_pendant_queries(jplace_path)
    estimates, status = {}, "NOT_REESTIMATED"
    if names and raxml and ref_aln and query_aln and model:
        estimates = reestimate_pendants(graft_path, names, references, ref_aln, query_aln, model, raxml, env)
        status = "RAXML_NG_EVALUATE"
    apply_pendant_estimates(graft, {k: v[0] for k, v in estimates.items()}, references)
    changed = restore_reference_edges(graft, ref, references)
    outdir = Path(outdir)
    target = outdir / (Path(graft_path).stem + ".lengths_restored.newick")
    Phylo.write(graft, target, "newick")
    with open(outdir / "BRANCH_LENGTH_RESTORE.tsv", "w") as handle:
        handle.write("kind\tname\tepa_ng_value\trestored_value\tmethod\tlogLikelihood\n")
        handle.write(f"reference_edges\t{len(reset)} reset to default in jplace; {changed} changed\t{PLACEHOLDER}\t"
                     f"ref.tree length\tref.tree\t\n")
        for q in names:
            est, ll = estimates.get(q, ("", ""))
            handle.write(f"query_pendant\t{q}\t{PLACEHOLDER}\t{est}\t{status}\t{ll}\n")
    return str(target), len(reset), names, status
