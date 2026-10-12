"""Read-only metric checks and transactional gappa graft generation.

The placement file, not a possibly older ref.tree, owns the graft backbone.
Split reference edges must be summed, never individually reset to whole edges.
"""
import io
import hashlib
import shutil
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
    paths = _query_pendant_path_records(graft, references)
    for name, (actual, segments) in paths.items():
        if not any(
            abs(actual - value) <= 0.0000051 * segments + 1e-12
            for value in queries[name]
        ):
            raise ValueError("GRAFT_INTEGRITY: query pendant differs from best placement")
    return {"status": "PASS", "reference_tips": len(references),
            "query_tips": len(queries), "authority": "jplace.tree",
            "scope": "reference topology and metric; best-placement pendants"}


def generate_checked_graft(gappa, jplace_path, outdir, env, *, exclusive=False):
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
        if exclusive:
            _copy_exclusive(candidates[0], target)
        else:
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
        best_weight = max(row[weight] for row in item["p"])
        best = [row for row in item["p"] if row[weight] == best_weight]
        values = [row[pendant] for row in best]
        if any(abs(value - values[0]) > 1e-12 for value in values[1:]):
            raise ValueError("AMBIGUOUS_BEST_PENDANT: tied maximum-LWR rows disagree")
        if abs(values[0] - PLACEHOLDER) < 1e-6:
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


def reestimate_pendants(graft_path, names, references, ref_aln, query_aln, model, raxml, env=None, *, evidence_dir=None):
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
            command = [raxml, "--evaluate", "--msa", str(td / "a.fasta"), "--tree", str(td / "t.nwk"),
                       "--model", str(model), "--opt-model", "off", "--opt-branches", "on", "--threads", "1",
                       "--prefix", str(td / "e"), "--redo"]
            executable_before = _executable_info(raxml)
            if not re.fullmatch(r"[0-9a-f]{64}", str(executable_before.get("sha256", ""))):
                raise ValueError("GRAFT_LENGTHS: evaluation executable identity unavailable before child")
            run = subprocess.run(command, capture_output=True, text=True, env=env)
            try:
                executable_after = _executable_info(raxml)
            except (OSError, ValueError) as exc:
                executable_after = {"state": "ERROR_AFTER_CHILD", "error_class": type(exc).__name__}
            executable_unchanged = executable_after == executable_before
            if evidence_dir is not None:
                record_dir = Path(evidence_dir) / hashlib.sha256(q.encode("utf-8")).hexdigest()
                record_dir.mkdir()
                _copy_exclusive(td / "t.nwk", record_dir / "input.newick")
                _write_json_exclusive(record_dir / "command.json", {
                    "query": q, "argv": command, "returncode": run.returncode,
                    "workdir_creation_path": str(td),
                    "alignment_sha256": _file_info(td / "a.fasta")["sha256"],
                    "model_creation_path": str(model),
                    "model_sha256": _file_info(model)["sha256"],
                    "threads": 1, "resource_environment": {
                        key: (env or os.environ).get(key, "NOT_RECORDED") for key in RESOURCE_KEYS},
                    "executable": executable_before, "executable_after": executable_after,
                    "executable_identity_state": "UNCHANGED" if executable_unchanged else "CHANGED_OR_UNAVAILABLE",
                })
                with (record_dir / "stdout.log").open("x", encoding="utf-8") as handle:
                    handle.write(run.stdout or "")
                with (record_dir / "stderr.log").open("x", encoding="utf-8") as handle:
                    handle.write(run.stderr or "")
                if (td / "e.raxml.bestTree").is_file():
                    _copy_exclusive(td / "e.raxml.bestTree", record_dir / "bestTree.newick")
            if not executable_unchanged:
                raise ValueError("GRAFT_LENGTHS: EVALUATION_EXECUTABLE_CHANGED_OR_UNAVAILABLE")
            if run.returncode:
                raise ValueError(f"GRAFT_LENGTHS: raxml-ng --evaluate failed for {q}")
            est = next(t.branch_length for t in Phylo.read(td / "e.raxml.bestTree", "newick").get_terminals()
                       if t.name == q)
            ll = next((l.split()[-1] for l in run.stdout.splitlines() if "final logLikelihood" in l), "")
        out[q] = (est, ll)
    return out


def generate_length_restored_graft(graft_path, jplace_path, ref_tree_path, outdir, ref_aln=None, query_aln=None,
                                   model=None, raxml=None, env=None, *, evidence_dir=None, exclusive=False):
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
        estimates = reestimate_pendants(graft_path, names, references, ref_aln, query_aln, model, raxml, env,
                                        evidence_dir=evidence_dir)
        status = "RAXML_NG_EVALUATE"
    apply_pendant_estimates(graft, {k: v[0] for k, v in estimates.items()}, references)
    changed = restore_reference_edges(graft, ref, references)
    outdir = Path(outdir)
    target = outdir / (Path(graft_path).stem + ".lengths_restored.newick")
    if exclusive:
        with target.open("x", encoding="utf-8") as handle:
            Phylo.write(graft, handle, "newick", format_branch_length="%.17g", format_confidence="%.17g")
    else:
        Phylo.write(graft, target, "newick")
    with open(outdir / "BRANCH_LENGTH_RESTORE.tsv", "x" if exclusive else "w") as handle:
        handle.write("kind\tname\tepa_ng_value\trestored_value\tmethod\tlogLikelihood\n")
        handle.write(f"reference_edges\t{len(reset)} reset to default in jplace; {changed} changed\t{PLACEHOLDER}\t"
                     f"ref.tree length\tref.tree\t\n")
        for q in names:
            est, ll = estimates.get(q, ("", ""))
            handle.write(f"query_pendant\t{q}\t{PLACEHOLDER}\t{est}\t{status}\t{ll}\n")
    return str(target), len(reset), names, status


# A receipt is numerical evidence for the selected sources, not a biological
# confidence statement or an attestation against an adversarial Python process.
LENGTH_SCHEMA = "sapote.graft-length-evidence.v1"
RESOURCE_KEYS = ("OMP_NUM_THREADS", "OMP_THREAD_LIMIT", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                 "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")
SOURCE_ROLES = ("jplace", "reference_tree", "reference_alignment", "query_alignment",
                "model", "placement_provenance", "reference_provenance")


def _file_info(path):
    import stat
    path = Path(path)
    before = path.stat()
    if path.is_symlink() or not stat.S_ISREG(before.st_mode):
        raise ValueError("LENGTH_SOURCE_NOT_REGULAR")
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        opened = os.fstat(handle.fileno())
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            sha.update(chunk)
        after = os.fstat(handle.fileno())
    current = path.stat()
    identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
    if len({identity(s) for s in (before, opened, after, current)}) != 1:
        raise ValueError("LENGTH_SOURCE_CHANGED")
    return {"sha256": sha.hexdigest(), "size": current.st_size,
            "creation_path": str(path.absolute()),
            "physical_identity": list(identity(current))}


def _write_json_exclusive(path, value):
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def _copy_exclusive(source, target):
    before = _file_info(source)
    with Path(source).open("rb") as src, Path(target).open("xb") as dst:
        shutil.copyfileobj(src, dst, 1024 * 1024)
    if _file_info(source) != before or _file_info(target)["sha256"] != before["sha256"]:
        raise ValueError("LENGTH_SOURCE_CHANGED")


def _read_receipt(path):
    # Only the owned receipt/command JSON has a size bound; tree/alignment hashes stream.
    if any(part.is_symlink() for part in (Path(path), *Path(path).parents)):
        raise ValueError("LENGTH_RECEIPT_SYMLINK")
    before = _file_info(path)
    if before["size"] > 16 * 1024 * 1024:
        raise ValueError("LENGTH_RECEIPT_TOO_LARGE")
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("LENGTH_RECEIPT_INVALID") from exc
    if not isinstance(value, dict) or _file_info(path) != before:
        raise ValueError("LENGTH_RECEIPT_INVALID_OR_CHANGED")
    return value


def _executable_info(command):
    path = shutil.which(str(command))
    return dict(_file_info(Path(path).resolve(strict=True)), invocation=str(command)) if path else {"state": "NOT_RECORDED"}


def _query_pendant_path_records(tree, references):
    """Full query-only paths plus their serialization segment counts."""
    parent = {child: node for node in tree.find_clades() for child in node.clades}
    result = {}
    for tip in tree.get_terminals():
        if tip.name in references:
            continue
        length, segments, node = 0.0, 0, tip
        while node is not tree.root and not ({t.name for t in node.get_terminals()} & references):
            value = node.branch_length
            if value is None or not math.isfinite(value) or value < 0:
                raise ValueError("GRAFT_LENGTHS: invalid query-only path")
            length += value
            segments += 1
            node = parent[node]
        result[tip.name] = (length, segments)
    return result


def query_pendant_paths(tree, references):
    """Full query-only path lengths, including a shared query stem."""
    return {name: value[0] for name, value in _query_pendant_path_records(tree, references).items()}


def _close_length(actual, expected):
    if not math.isfinite(actual) or not math.isfinite(expected):
        return False
    if expected == 0:
        return actual == 0
    return math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12)


def _topology(tree):
    return sorted(((tuple(sorted(t.name for t in node.get_terminals())), node.name, repr(node.confidence))
                   for node in tree.find_clades()), key=lambda item: json.dumps(item))


def _fasta_records(path):
    records, name = {}, None
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line.startswith(">"):
                parts = line[1:].split()
                if not parts or parts[0] in records:
                    raise ValueError("LENGTH_ALIGNMENT_DUPLICATE_OR_EMPTY_ID")
                name = parts[0]
                records[name] = ""
            elif line:
                if name is None:
                    raise ValueError("LENGTH_ALIGNMENT_INVALID")
                records[name] += line
    if not records or any(not seq for seq in records.values()):
        raise ValueError("LENGTH_ALIGNMENT_EMPTY")
    return records


def _source_records(sources):
    if set(sources) != set(SOURCE_ROLES):
        raise ValueError("LENGTH_SOURCE_ROSTER_INVALID")
    result, identities = {}, set()
    for role in SOURCE_ROLES:
        path = sources[role]
        if path is None:
            result[role] = {"state": "NOT_RECORDED"}
            continue
        path = Path(path)
        if any(part.is_symlink() for part in (path, *path.parents)):
            raise ValueError("LENGTH_SOURCE_SYMLINK")
        if not path.exists():
            result[role] = {"state": "MISSING"}
            continue
        record = _file_info(path)
        physical = tuple(record["physical_identity"][:2])
        if physical in identities:
            raise ValueError("LENGTH_SOURCE_ALIAS")
        identities.add(physical)
        result[role] = dict(record, state="BOUND")
    return result


def _same_sources(before, after, *, physical=False):
    if not isinstance(before, dict) or set(before) != set(SOURCE_ROLES):
        raise ValueError("LENGTH_RECEIPT_SOURCE_ROSTER_INVALID")
    for role in SOURCE_ROLES:
        if not isinstance(before[role], dict) or not isinstance(after[role], dict):
            raise ValueError("LENGTH_RECEIPT_SOURCE_ROSTER_INVALID")
        keys = ("state", "sha256", "size") + (("physical_identity",) if physical else ())
        if any(before[role].get(key) != after[role].get(key) for key in keys):
            raise ValueError("LENGTH_SOURCE_CHANGED_OR_UNBOUND")


def _output_records(root):
    records = {}
    for path in sorted(Path(root).rglob("*")):
        if path.is_symlink():
            raise ValueError("LENGTH_OUTPUT_SYMLINK")
        if path.is_dir():
            continue
        rel = path.relative_to(root).as_posix()
        if rel == "receipt.json":
            continue
        info = _file_info(path)
        records[rel] = {key: info[key] for key in ("sha256", "size")}
    return records


def _bound_output(root, relative):
    if not isinstance(relative, str) or not relative:
        raise ValueError("LENGTH_OUTPUT_PATH_INVALID")
    rel = Path(relative)
    if rel.is_absolute() or any(part in ("..", ".") for part in rel.parts):
        raise ValueError("LENGTH_OUTPUT_PATH_INVALID")
    path = Path(root) / rel
    for part in (path, *path.parents):
        if part == Path(root).parent:
            break
        if part.is_symlink():
            raise ValueError("LENGTH_OUTPUT_SYMLINK")
    return path


def _evaluation_estimates(root, names, sources, raw):
    """Read retained real evaluation outputs; independently bind per-query inputs."""
    from Bio import Phylo
    reference = Phylo.read(sources["reference_tree"], "newick")
    refs = _tips(reference)
    estimates = {}
    if not names:
        if (Path(root) / "evaluation").exists() and any((Path(root) / "evaluation").iterdir()):
            raise ValueError("LENGTH_UNEXPECTED_EVALUATION")
        return estimates
    seqs = _fasta_records(sources["reference_alignment"])
    query_seqs = _fasta_records(sources["query_alignment"])
    if set(seqs) & set(query_seqs):
        raise ValueError("LENGTH_ALIGNMENT_ID_COLLISION")
    seqs.update(query_seqs)
    if len({len(seq) for seq in seqs.values()}) != 1:
        raise ValueError("LENGTH_ALIGNMENT_WIDTH_MISMATCH")
    expected_dirs = {hashlib.sha256(name.encode("utf-8")).hexdigest() for name in names}
    evalroot = Path(root) / "evaluation"
    if {path.name for path in evalroot.iterdir()} != expected_dirs:
        raise ValueError("LENGTH_EVALUATION_ROSTER_MISMATCH")
    for name in names:
        record = evalroot / hashlib.sha256(name.encode("utf-8")).hexdigest()
        command = _read_receipt(record / "command.json")
        if (command.get("query") != name or command.get("returncode") != 0 or
                command.get("threads") != 1 or
                command.get("resource_environment") != {key: "1" for key in RESOURCE_KEYS}):
            raise ValueError("LENGTH_EVALUATION_CONTEXT_INVALID")
        executable = command.get("executable")
        if not isinstance(executable, dict) or not re.fullmatch(r"[0-9a-f]{64}", str(executable.get("sha256", ""))):
            raise ValueError("LENGTH_EVALUATION_EXECUTABLE_UNBOUND")
        if command.get("executable_identity_state") != "UNCHANGED" or command.get("executable_after") != executable:
            raise ValueError("LENGTH_EVALUATION_EXECUTABLE_CHANGED_OR_UNAVAILABLE")
        argv = command.get("argv")
        if not isinstance(argv, list) or not all(isinstance(arg, str) for arg in argv):
            raise ValueError("LENGTH_EVALUATION_COMMAND_INVALID")
        expected_flags = {"--evaluate", "--msa", "--tree", "--model", "--opt-model", "--opt-branches", "--threads", "--prefix", "--redo"}
        if {arg for arg in argv if arg.startswith("--")} != expected_flags or len(argv) != 17:
            raise ValueError("LENGTH_EVALUATION_COMMAND_INVALID")
        workdir = command.get("workdir_creation_path")
        if not isinstance(workdir, str):
            raise ValueError("LENGTH_EVALUATION_COMMAND_INVALID")
        expected_argv = [executable.get("invocation"), "--evaluate", "--msa", str(Path(workdir) / "a.fasta"),
                         "--tree", str(Path(workdir) / "t.nwk"), "--model", command.get("model_creation_path"),
                         "--opt-model", "off", "--opt-branches", "on", "--threads", "1",
                         "--prefix", str(Path(workdir) / "e"), "--redo"]
        if argv != expected_argv:
            raise ValueError("LENGTH_EVALUATION_COMMAND_INVALID")
        required = {"--evaluate": None, "--opt-model": "off", "--opt-branches": "on", "--threads": "1"}
        for flag, expected in required.items():
            if argv.count(flag) != 1 or (expected is not None and
                    (argv.index(flag) + 1 >= len(argv) or argv[argv.index(flag)+1] != expected)):
                raise ValueError("LENGTH_EVALUATION_COMMAND_INVALID")
        if "--model" not in argv or argv[argv.index("--model")+1] != command.get("model_creation_path"):
            raise ValueError("LENGTH_EVALUATION_MODEL_UNBOUND")
        if command.get("model_sha256") != _file_info(sources["model"])["sha256"]:
            raise ValueError("LENGTH_EVALUATION_MODEL_UNBOUND")
        tree = Phylo.read(raw, "newick")
        for tip in list(tree.get_terminals()):
            if tip.name != name and tip.name not in refs:
                tree.prune(tip)
        stream = io.StringIO()
        Phylo.write(tree, stream, "newick")
        if (record / "input.newick").read_text(encoding="utf-8") != stream.getvalue():
            raise ValueError("LENGTH_EVALUATION_TREE_UNBOUND")
        msa = "".join(f">{tip.name}\n{seqs[tip.name]}\n" for tip in tree.get_terminals())
        if hashlib.sha256(msa.encode("utf-8")).hexdigest() != command.get("alignment_sha256"):
            raise ValueError("LENGTH_EVALUATION_ALIGNMENT_UNBOUND")
        best = Phylo.read(record / "bestTree.newick", "newick")
        if _tips(best) != refs | {name} or set(_metric(best, _tips(best))) != set(_metric(tree, _tips(tree))):
            raise ValueError("LENGTH_EVALUATION_TOPOLOGY_INVALID")
        _metric(best, refs)
        estimate = next(t.branch_length for t in best.get_terminals() if t.name == name)
        if estimate is None or not math.isfinite(estimate) or estimate < 0:
            raise ValueError("LENGTH_EVALUATION_ESTIMATE_INVALID")
        estimates[name] = estimate
    return estimates


def _numeric_length_qa(root, selected, sources):
    from Bio import Phylo
    raw = _bound_output(root, selected["raw"])
    restored = _bound_output(root, selected["restored"])
    verify_graft(raw, sources["jplace"])
    names = default_pendant_queries(sources["jplace"])
    reset, other = backbone_defaults(sources["jplace"], sources["reference_tree"])
    if other:
        raise ValueError("LENGTH_REFERENCE_DIFFERS_BEYOND_DEFAULT")
    ref = Phylo.read(sources["reference_tree"], "newick")
    references = _tips(ref)
    _metric(ref, references)
    original = Phylo.read(raw, "newick")
    final = Phylo.read(restored, "newick")
    if _tips(final) != _tips(original) or _topology(final) != _topology(original):
        raise ValueError("LENGTH_RESTORED_TOPOLOGY_CHANGED")
    expected, observed = _metric(ref, references), _metric(final, references)
    if expected.keys() != observed.keys() or any(
            not _close_length(observed[key][0], val[0]) for key, val in expected.items()):
        raise ValueError("LENGTH_RESTORED_REFERENCE_METRIC_INVALID")
    expected_outputs = {selected["raw"], selected["restored"], selected["ledger"]}
    for name in names:
        prefix = "evaluation/" + hashlib.sha256(name.encode("utf-8")).hexdigest() + "/"
        expected_outputs.update(prefix + filename for filename in
                                ("input.newick", "bestTree.newick", "command.json", "stdout.log", "stderr.log"))
    if set(_output_records(root)) != expected_outputs:
        raise ValueError("LENGTH_OUTPUT_ROSTER_INVALID")
    estimates = _evaluation_estimates(root, names, sources, raw)
    oldpaths, paths = query_pendant_paths(original, references), query_pendant_paths(final, references)
    targets = {name: estimates.get(name, value) for name, value in oldpaths.items()}
    if any(not _close_length(paths[name], value) for name, value in targets.items()):
        raise ValueError("LENGTH_RESTORED_QUERY_METRIC_INVALID")
    # Independently reconstruct the ledger from retained evidence, rather than trusting its method labels.
    import csv
    with _bound_output(root, selected["ledger"]).open(newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    reference_rows = [row for row in rows if row["kind"] == "reference_edges"]
    rawmetric = _metric(original, references)
    changed = sum(abs(rawmetric[key][0] - val[0]) > 1e-4 for key, val in expected.items())
    expected_reference = {"kind": "reference_edges", "name": f"{len(reset)} reset to default in jplace; {changed} changed",
                          "epa_ng_value": str(PLACEHOLDER), "restored_value": "ref.tree length", "method": "ref.tree", "logLikelihood": ""}
    if reference_rows != [expected_reference] or len(rows) != len(names) + 1:
        raise ValueError("LENGTH_LEDGER_REFERENCE_INVALID")
    queryrows = [row for row in rows if row["kind"] == "query_pendant"]
    if len(queryrows) != len(names) or {row["name"] for row in queryrows} != set(names):
        raise ValueError("LENGTH_LEDGER_ROSTER_INVALID")
    for row in queryrows:
        evaluation = Path(root) / "evaluation" / hashlib.sha256(row["name"].encode("utf-8")).hexdigest()
        stdout = (evaluation / "stdout.log").read_text(encoding="utf-8")
        ll = next((line.split()[-1] for line in stdout.splitlines() if "final logLikelihood" in line), "")
        if row["epa_ng_value"] != str(PLACEHOLDER) or row["logLikelihood"] != ll:
            raise ValueError("LENGTH_LEDGER_CONTEXT_INVALID")
        if row["method"] != "RAXML_NG_EVALUATE" or not _close_length(float(row["restored_value"]), estimates[row["name"]]):
            raise ValueError("LENGTH_LEDGER_ESTIMATE_INVALID")
    return {"status": "PASS_LENGTH_QA", "reference_tips": len(references),
            "query_tips": len(paths), "default_queries_reestimated": sorted(names),
            "scope": "reference projected split metrics and full query pendant paths; unchanged graft topology",
            "biological_validation": False, "tolerance": {"relative": 1e-12, "absolute": 1e-12}}


def _layout_binding(sources, report):
    jp, ref = Path(sources["jplace"]).absolute(), Path(sources["reference_tree"]).absolute().parent
    report = Path(report).absolute()
    expected = {"reference_alignment": ref / "ref.aln.fasta",
                "query_alignment": jp.parent / "query.aligned.fasta",
                "placement_provenance": jp.parent / "_provenance.json",
                "reference_provenance": ref / "_provenance.json"}
    if any(path is not None and Path(path).absolute() != expected[role]
           for role, path in sources.items() if role in expected):
        return {"state": "DISPLAY_LAYOUT_UNBOUND"}
    if sources["model"] is not None and (Path(sources["model"]).absolute().parent != ref or
            Path(sources["model"]).name not in {"ref.bestModel", "ref.raxml.raxml.bestModel"}):
        return {"state": "DISPLAY_LAYOUT_UNBOUND"}
    if jp.name != "epa_result.jplace":
        return {"state": "DISPLAY_LAYOUT_UNBOUND"}
    if report.name == "report" and jp.parent == report.parent / "place" and ref == report.parent / "refpkg":
        return {"state": "BOUND", "kind": "nested", "reference_root": "refpkg"}
    if jp.parent == report:
        choices = {report / "refpkg": "refpkg", report: ".", report.parent / "refpkg": "../refpkg"}
        if ref in choices:
            return {"state": "BOUND", "kind": "flat", "reference_root": choices[ref]}
    return {"state": "DISPLAY_LAYOUT_UNBOUND"}


def produce_graft_length_evidence(sources, output_root, gappa, raxml=None, env=None):
    """Create a fresh evidence child; retain failed attempts, never refresh older receipts."""
    before = _source_records(sources)
    root = Path(output_root) / "graft_length_evidence"
    if any(part.is_symlink() for part in (root, *root.parents)):
        raise ValueError("LENGTH_OUTPUT_SYMLINK")
    if root.exists() or root.is_symlink():
        raise ValueError("LENGTH_EVIDENCE_EXISTS")
    root.mkdir(parents=True, exist_ok=False)
    record = {"schema": LENGTH_SCHEMA, "state": "HOLD_LENGTH_QA", "sources": before,
              "layout": _layout_binding(sources, output_root), "selected": {}, "qa": None}
    try:
        if any(before[role]["state"] != "BOUND" for role in ("jplace", "reference_tree")):
            raise ValueError("LENGTH_REFERENCE_OR_JPLACE_MISSING")
        raw = generate_checked_graft(gappa, sources["jplace"], root, env, exclusive=True)
        names = default_pendant_queries(sources["jplace"])
        if names and (not raxml or any(before[role]["state"] != "BOUND" for role in
                                      ("reference_alignment", "query_alignment", "model"))):
            raise ValueError("LENGTH_DEFAULT_PENDANT_NOT_REESTIMATED")
        evaldir = root / "evaluation"
        evaldir.mkdir()
        evalenv = dict(os.environ if env is None else env, **{key: "1" for key in RESOURCE_KEYS})
        restored, _, _, _ = generate_length_restored_graft(
            raw, sources["jplace"], sources["reference_tree"], root,
            ref_aln=sources["reference_alignment"], query_aln=sources["query_alignment"],
            model=sources["model"], raxml=raxml, env=evalenv, evidence_dir=evaldir, exclusive=True)
        record["selected"] = {"raw": Path(raw).name, "restored": Path(restored).name,
                              "ledger": "BRANCH_LENGTH_RESTORE.tsv"}
        record["qa"] = _numeric_length_qa(root, record["selected"], sources)
        _same_sources(before, _source_records(sources), physical=True)
        record["state"] = "PASS_LENGTH_QA"
    except (ValueError, OSError, KeyError, IndexError, TypeError, subprocess.SubprocessError) as exc:
        record["reason"] = f"{type(exc).__name__}: {exc}"
    record["outputs"] = _output_records(root)
    _write_json_exclusive(root / "receipt.json", record)
    if record["state"] == "PASS_LENGTH_QA":
        return admit_graft_length_evidence(root / "receipt.json", sources)
    return {"state": record["state"], "receipt": str(root / "receipt.json"),
            "reason": record.get("reason"), "selected": None}


def admit_graft_length_evidence(receipt_path, expected_sources):
    """Read-only re-admission: rehash exact sources/closure and recompute numerical QA."""
    receipt_path = Path(receipt_path)
    if any(part.is_symlink() for part in (receipt_path, *receipt_path.parents)):
        raise ValueError("LENGTH_OUTPUT_SYMLINK")
    record = _read_receipt(receipt_path)
    if record.get("schema") != LENGTH_SCHEMA or record.get("state") != "PASS_LENGTH_QA":
        raise ValueError("LENGTH_RECEIPT_MISSING_OR_HOLD")
    before = _source_records(expected_sources)
    saved = record.get("sources")
    if not isinstance(saved, dict) or set(saved) != set(SOURCE_ROLES):
        raise ValueError("LENGTH_RECEIPT_SOURCE_ROSTER_INVALID")
    _same_sources(saved, before)
    root = receipt_path.parent
    if record.get("outputs") != _output_records(root):
        raise ValueError("LENGTH_RECEIPT_OUTPUT_CHANGED")
    selected = record.get("selected")
    if not isinstance(selected, dict) or set(selected) != {"raw", "restored", "ledger"}:
        raise ValueError("LENGTH_RECEIPT_SELECTION_INVALID")
    try:
        qa = _numeric_length_qa(root, selected, expected_sources)
    except (KeyError, IndexError, TypeError, StopIteration) as exc:
        raise ValueError("LENGTH_EVIDENCE_MALFORMED") from exc
    if qa != record.get("qa"):
        raise ValueError("LENGTH_RECEIPT_QA_CHANGED")
    _same_sources(before, _source_records(expected_sources), physical=True)
    if record["outputs"] != _output_records(root):
        raise ValueError("LENGTH_RECEIPT_OUTPUT_CHANGED")
    return {"state": "PASS_LENGTH_QA", "receipt": str(receipt_path),
            "receipt_sha256": _file_info(receipt_path)["sha256"], "qa": qa,
            "selected": {key: str(_bound_output(root, value)) for key, value in selected.items()},
            "sources": {key: str(value) if value is not None else None for key, value in expected_sources.items()},
            "layout": record.get("layout"), "outputs": record["outputs"]}


def admit_placement_run(run):
    """Portable admission uses a fixed layout contract, never historical absolute paths."""
    run = Path(run).resolve(strict=True)
    candidates = [run / "graft_length_evidence" / "receipt.json",
                  run / "report" / "graft_length_evidence" / "receipt.json"]
    found = [path for path in candidates if path.exists() or path.is_symlink()]
    if len(found) != 1:
        raise ValueError("DISPLAY_LENGTH_RECEIPT_MISSING_OR_COMPETING")
    receipt = _read_receipt(found[0])
    layout = receipt.get("layout")
    if not isinstance(layout, dict) or layout.get("state") != "BOUND":
        raise ValueError("DISPLAY_LAYOUT_UNBOUND")
    kind = layout.get("kind")
    refrel = layout.get("reference_root")
    if not isinstance(kind, str) or not isinstance(refrel, str):
        raise ValueError("DISPLAY_LAYOUT_UNBOUND")
    if (kind == "nested" and refrel == "refpkg" and found[0] == candidates[1]):
        place, ref = run / "place", run / "refpkg"
    elif (kind == "flat" and refrel in {"refpkg", ".", "../refpkg"} and found[0] == candidates[0]):
        place, ref = run, run / refrel
    else:
        raise ValueError("DISPLAY_LAYOUT_UNBOUND")
    sources = {"jplace": place / "epa_result.jplace", "reference_tree": ref / "ref.tree",
               "reference_alignment": ref / "ref.aln.fasta", "query_alignment": place / "query.aligned.fasta",
               "model": None, "placement_provenance": place / "_provenance.json",
               "reference_provenance": ref / "_provenance.json"}
    saved = receipt.get("sources", {})
    if not isinstance(saved, dict) or set(saved) != set(SOURCE_ROLES):
        raise ValueError("LENGTH_RECEIPT_SOURCE_ROSTER_INVALID")
    for role in SOURCE_ROLES:
        record = saved.get(role)
        if not isinstance(record, dict):
            raise ValueError("LENGTH_RECEIPT_SOURCE_ROSTER_INVALID")
        if role == "model" and record.get("state") == "BOUND":
            creation_path = record.get("creation_path")
            if not isinstance(creation_path, str):
                raise ValueError("DISPLAY_MODEL_LAYOUT_UNBOUND")
            basename = Path(creation_path).name
            if basename not in {"ref.bestModel", "ref.raxml.raxml.bestModel"}:
                raise ValueError("DISPLAY_MODEL_LAYOUT_UNBOUND")
            sources[role] = ref / basename
        elif record.get("state") == "NOT_RECORDED":
            sources[role] = None
    result = admit_graft_length_evidence(found[0], sources)
    if any(result["sources"][role] is None or saved[role].get("state") != "BOUND"
           for role in ("reference_alignment", "query_alignment")):
        raise ValueError("DISPLAY_ALIGNMENT_UNBOUND")
    return result
