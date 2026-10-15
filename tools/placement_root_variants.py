"""Bind strict gate verdicts to source-preserving root display variants."""
from __future__ import annotations

import hashlib
import io
import json
import math
from pathlib import Path


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _binding(path, directory):
    import os
    path = Path(path).resolve()
    return {"path": os.path.relpath(path, directory), "sha256": _sha(path),
            "bytes": path.stat().st_size}


def _split(path, outgroups):
    from Bio import Phylo
    from tools.phylo_place import _display_root_on_outgroup
    from tools.graft_integrity import _metric, _tips, _close_length
    tree = Phylo.read(path, "newick")
    tips = {tip.name: tip for tip in tree.get_terminals()}
    if len(tips) != len(tree.get_terminals()) or not all(tips):
        raise ValueError("ROOT_VARIANT_DUPLICATE_OR_EMPTY_TIP")
    if not outgroups or len(set(outgroups)) != len(outgroups) or set(outgroups) - set(tips):
        raise ValueError("ROOT_VARIANT_OUTGROUP_UNBOUND")
    if any(not math.isfinite(n.branch_length or 0.0) or (n.branch_length or 0.0) < 0
           for n in tree.find_clades()):
        raise ValueError("ROOT_VARIANT_INVALID_LENGTH")
    before = _metric(tree, _tips(tree))
    depths = tree.depths()
    maximum = max(depths.values()) or 1.0
    ingroup = set(tips) - set(outgroups)
    long_root = any({t.name for t in child.get_terminals()} == ingroup
                    and (child.branch_length or 0.0) > 0.5 * maximum
                    for child in tree.root.clades)
    rooting = _display_root_on_outgroup(tree, [tips[name] for name in outgroups])
    buffer = io.StringIO()
    Phylo.write(tree, buffer, "newick", format_branch_length="%.17g", format_confidence="%.17g")
    data = buffer.getvalue().encode()
    serialized = Phylo.read(io.StringIO(data.decode()), "newick")
    after = _metric(serialized, _tips(serialized))
    if before.keys() != after.keys() or any(not _close_length(after[k][0], v[0]) for k, v in before.items()):
        raise ValueError("ROOT_VARIANT_METRIC_DRIFT")
    return data, rooting, long_root


def prepare(source, prefix, outgroups, locked_accession=None):
    """Write both Newick variants and verdicts; acceptance requires the split gate.

    .452 locked_accession: the outgroup accession the registry LOCKS for this ingroup genus. Both gates
    then exempt the ingroup half of the root edge to that outgroup (tree_sanity_check
    locked_root_accession), and the receipt records it."""
    from tools.tree_sanity_check import check
    source, prefix = Path(source), Path(prefix)
    original = Path(str(prefix) + ".root_as_built.newick")
    split = Path(str(prefix) + ".rooted_split.newick")
    receipt = Path(str(prefix) + ".root_variants.json")
    if any(p.exists() for p in (original, split, receipt)):
        raise ValueError("ROOT_VARIANT_OUTPUT_EXISTS")
    data, rooting, long_root = _split(source, outgroups)
    original.write_bytes(source.read_bytes())
    split.write_bytes(data)
    ok_original, report_original = check(original, outgroup=outgroups, locked_root_accession=locked_accession)
    ok_split, report_split = check(split, outgroup=outgroups, locked_root_accession=locked_accession)
    payload = {"schema": "placement-root-variants-v1", "outgroup_tips": list(outgroups),
               "locked_outgroup_accession": locked_accession,
               "source": _binding(source, receipt.parent), "display_rooting": rooting,
               "long_root_branch": long_root, "accepted_variant": "display_rooted_split" if ok_split else None,
               "variants": {
                   "root_as_built": {"tree": _binding(original, receipt.parent), "gate_pass": ok_original,
                                     "gate_report": report_original, "accepted": False},
                   "display_rooted_split": {"tree": _binding(split, receipt.parent), "gate_pass": ok_split,
                                            "gate_report": report_split, "accepted": ok_split}}}
    receipt.write_text(json.dumps(payload, indent=2) + "\n")
    return split, receipt, payload


def verify_diagnostic(receipt_path, expected_sha256, original_parent):
    """Authorize only a bound root-as-built diagnostic; never change its FAIL verdict."""
    from tools.tree_sanity_check import check
    receipt_path = Path(receipt_path).resolve()
    if _sha(receipt_path) != expected_sha256:
        raise ValueError("ROOT_VARIANT_RECEIPT_HASH_MISMATCH")
    record = json.loads(receipt_path.read_text())
    if record.get("schema") != "placement-root-variants-v1":
        raise ValueError("ROOT_VARIANT_SCHEMA")
    variants = record["variants"]
    if set(variants) != {"root_as_built", "display_rooted_split"}:
        raise ValueError("ROOT_VARIANT_SCHEMA")
    source = (receipt_path.parent / record["source"]["path"]).resolve()
    if _binding(source, receipt_path.parent) != record["source"]:
        raise ValueError("ROOT_VARIANT_SOURCE_CHANGED")
    paths = {}
    for key, variant in variants.items():
        path = (receipt_path.parent / variant["tree"]["path"]).resolve()
        if _binding(path, receipt_path.parent) != variant["tree"]:
            raise ValueError("ROOT_VARIANT_CHANGED")
        paths[key] = path
    original = paths["root_as_built"]
    if source.read_bytes() != original.read_bytes():
        raise ValueError("ROOT_VARIANT_SOURCE_MISMATCH")
    if original != Path(original_parent).resolve():
        raise ValueError("ROOT_VARIANT_PARENT_MISMATCH")
    data, rooting, long_root = _split(original, record["outgroup_tips"])
    if data != paths["display_rooted_split"].read_bytes() or rooting != record["display_rooting"]:
        raise ValueError("ROOT_VARIANT_REPLAY_MISMATCH")
    locked = record.get("locked_outgroup_accession")
    passed, original_report = check(original, outgroup=record["outgroup_tips"], locked_root_accession=locked)
    split_passed, split_report = check(paths["display_rooted_split"], outgroup=record["outgroup_tips"],
                                       locked_root_accession=locked)
    import re
    failures = set(re.findall(r"^  \[([A-Z_]+)\]$", original_report, re.M))
    if not long_root or passed or failures != {"DOMINATING_BRANCH"} or not split_passed:
        raise ValueError("ROOT_VARIANT_NOT_ELIGIBLE_FOR_DIAGNOSTIC")
    if (variants["root_as_built"]["gate_pass"] is not False
            or variants["root_as_built"]["accepted"] is not False
            or variants["display_rooted_split"]["gate_pass"] is not True
            or variants["display_rooted_split"]["accepted"] is not True
            or record["long_root_branch"] is not True
            or variants["root_as_built"]["gate_report"] != original_report
            or variants["display_rooted_split"]["gate_report"] != split_report
            or record["accepted_variant"] != "display_rooted_split"):
        raise ValueError("ROOT_VARIANT_VERDICT_MISMATCH")
    return record, original_report, split_report
