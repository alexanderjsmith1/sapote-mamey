#!/usr/bin/env python3
"""Create a reproducible display derivative; never edit the analysis inputs.

Only explicitly designated reference clades with a shared recorded taxon can
collapse. A display grouping is not evidence of species or ecological identity.
"""
from __future__ import annotations

import argparse
import copy
import csv
# Use the bundle's spreadsheet-safe writers for all tabular exports.
try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ModuleNotFoundError:
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

import hashlib
import io
import itertools
import json
import math
import os
from pathlib import Path
import re
import sys

from _console import emit
import logging
_LOG = logging.getLogger(__name__)

SCHEMA = "sapote.tree-display.v1"
QUERY_PATTERN = r"^(?:QUERY(?:_|$)|AS[_-]?\d)"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_meta(path):
    with Path(path).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle, delimiter="\t"))
    if not rows or len(set(rows[0])) != len(rows[0]) or not all(rows[0]):
        raise ValueError("METADATA_HEADER_INVALID")
    header = rows[0]
    if not {"tip", "label", "role"} <= set(header):
        raise ValueError("METADATA_REQUIRES_tip_label_role")
    # v9.7.417: `taxon` is REQUIRED, not optional. This module's own contract is "only explicitly
    # designated reference clades with a shared recorded taxon can collapse", and the eligibility
    # test reads `metadata[n].get("taxon", "")`. With the column absent that lookup returns "" for
    # every tip, so every candidate clade is rejected by the `"" in taxa` guard and the run
    # completes with exit 0, a signed receipt, and a ledger of nothing but RETAINED -- identical in
    # shape to a run where the sequences were genuinely too divergent to collapse. Measured on this
    # candidate with one alignment, one tree and one set of parameters, changing only the metadata:
    # with `taxon` -> 3 references collapse to 1; without it -> 0 collapse, exit 0, no warning.
    # `--max-nt` is a REQUIRED argument, so every invocation asks for collapsing and there is no
    # call that legitimately omits this column. Fail closed, like every other malformed-input case
    # in `read_meta`, rather than emit a display derivative that is silently a copy of its input.
    if "taxon" not in header:
        raise ValueError("METADATA_REQUIRES_taxon")
    if any(len(row) != len(header) for row in rows[1:]):
        raise ValueError("METADATA_ROW_WIDTH")
    body = [dict(zip(header, row)) for row in rows[1:]]
    if any(not r["tip"].strip() or not r["label"].strip() for r in body):
        raise ValueError("METADATA_EMPTY_ID_OR_LABEL")
    if len({r["tip"] for r in body}) != len(body):
        raise ValueError("DUPLICATE_METADATA_TIP")
    if any(r["role"] not in {"query", "reference", "outgroup"} for r in body):
        raise ValueError("ROLE_MUST_BE_query_reference_outgroup")
    for row in body:
        if re.search(QUERY_PATTERN, row["tip"], re.I) and row["role"] != "query":
            raise ValueError("QUERY_ROLE_CONFLICT")
        if "outgroup" in row["tip"].lower() and row["role"] != "outgroup":
            raise ValueError("OUTGROUP_ROLE_CONFLICT")
    return header, body


def read_fasta(path):
    seqs, key = {}, None
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith(">"):
            fields = line[1:].split()
            if not fields or fields[0] in seqs:
                raise ValueError("EMPTY_OR_DUPLICATE_FASTA_ID")
            key = fields[0]
            seqs[key] = ""
        else:
            if key is None:
                raise ValueError("FASTA_SEQUENCE_BEFORE_HEADER")
            seqs[key] += line.upper()
    if not seqs or not all(seqs.values()) or len({len(s) for s in seqs.values()}) != 1:
        raise ValueError("ALIGNMENT_EMPTY_OR_UNEQUAL_LENGTHS")
    if any(set(s) - set("ACGTRYSWKMBDHVN-?.") for s in seqs.values()):
        raise ValueError("ALIGNMENT_INVALID_DNA_SYMBOL")
    return seqs


def mismatches(a, b):
    if len(a) != len(b):
        raise ValueError("ALIGNMENT_UNEQUAL_LENGTHS")
    shared = [(x, y) for x, y in zip(a, b) if x in "ACGT" and y in "ACGT"]
    return sum(x != y for x, y in shared), len(shared)


def tsv_bytes(header, rows):
    buffer = io.StringIO(newline="")
    writer = _SafeDictWriter(buffer, fieldnames=header, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def build_display(aln, nwk, meta, parameters):
    from Bio import Phylo
    required = {"max_nt", "min_cols", "protect", "prune_outgroup"}
    # SEXTANT_421l: group_label is optional so every receipt written before it still verifies.
    if not required <= set(parameters) <= required | {"group_label"}:
        raise ValueError("PARAMETER_SCHEMA")
    group_label = parameters.get("group_label", "group")
    if group_label not in ("group", "representative"):
        raise ValueError("GROUP_LABEL_MUST_BE_group_OR_representative")
    max_nt, min_cols = parameters["max_nt"], parameters["min_cols"]
    if type(max_nt) is not int or max_nt < 0 or type(min_cols) is not int or min_cols < 1:
        raise ValueError("EXPLICIT_NONNEGATIVE_MISMATCH_AND_POSITIVE_SHARED_MINIMUM_REQUIRED")
    if type(parameters["prune_outgroup"]) is not bool or not isinstance(parameters["protect"], list):
        raise ValueError("PARAMETER_TYPES")
    seqs = read_fasta(aln)
    header, rows = read_meta(meta)
    metadata = {r["tip"]: r for r in rows}
    tree = Phylo.read(nwk, "newick")
    names = [t.name for t in tree.get_terminals()]
    if len(names) != len(set(names)) or any(not n for n in names):
        raise ValueError("DUPLICATE_OR_EMPTY_TREE_TIP")
    if set(names) != set(seqs) or set(names) != set(metadata):
        raise ValueError("TREE_ALIGNMENT_METADATA_SETS_DIFFER")
    for node in tree.find_clades():
        length = node.branch_length
        if node is tree.root and length is None:
            continue
        if length is None or not math.isfinite(length) or length < 0:
            raise ValueError("FINITE_NONNEGATIVE_BRANCH_LENGTHS_REQUIRED")
    protected = set(parameters["protect"])
    if not protected <= set(names):
        raise ValueError("PROTECTED_TIP_MISSING")
    protected |= {n for n in names if metadata[n]["role"] != "reference"}
    pairs = {}
    def distance(x, y):
        key = tuple(sorted((x, y)))
        if key not in pairs:
            pairs[key] = mismatches(seqs[x], seqs[y])
        return pairs[key]
    groups, assigned = [], set()
    # Preorder admits maximal eligible clades, then tests their descendants if
    # the larger clade fails. This avoids greedy sequence groups hiding a clade.
    for node in tree.get_nonterminals(order="preorder"):
        members = sorted(t.name for t in node.get_terminals())
        if len(members) < 2 or set(members) & (protected | assigned):
            continue
        taxa = {metadata[n].get("taxon", "").strip() for n in members}
        if len(taxa) != 1 or "" in taxa:
            continue
        comparisons = [distance(x, y) for x, y in itertools.combinations(members, 2)]
        if any(m > max_nt or shared < min_cols for m, shared in comparisons):
            continue
        rep = min(members, key=lambda n: (-sum(c in "ACGT" for c in seqs[n]), n))
        groups.append((rep, members, max(m for m, _ in comparisons), min(c for _, c in comparisons)))
        assigned.update(members)
    display = copy.deepcopy(tree)
    representatives = {n: n for n in names}
    group_info = {}
    for rep, members, max_pair, min_shared in groups:
        group_info[rep] = (members, max_pair, min_shared)
        for name in members:
            representatives[name] = rep
            if name != rep:
                display.prune(name)
    outgroups = {n for n in names if metadata[n]["role"] == "outgroup"}
    pruned = set()
    if parameters["prune_outgroup"]:
        if not outgroups or protected.intersection(parameters["protect"]).intersection(outgroups):
            raise ValueError("OUTGROUP_PRUNING_UNDECLARED_OR_PROTECTED")
        children = [{t.name for t in c.get_terminals()} for c in tree.root.clades]
        if len(children) != 2 or outgroups not in children:
            raise ValueError("OUTGROUP_MUST_BE_EXCLUSIVE_ROOT_SISTER_CLADE")
        for name in sorted(outgroups):
            display.prune(name)
            pruned.add(name)
    kept = {t.name for t in display.get_terminals()}
    if len(kept) < 2:
        raise ValueError("DISPLAY_REQUIRES_AT_LEAST_TWO_TIPS")
    if not {n for n in protected if n not in pruned} <= kept:
        raise ValueError("PROTECTED_TIP_LOST")
    display_rows = []
    extra = ["display_members", "display_source_scope"]
    if set(extra) & set(header):
        raise ValueError("INPUT_IS_ALREADY_DISPLAY_METADATA")
    for row in rows:
        name = row["tip"]
        if name not in kept:
            continue
        result = dict(row, display_members="1", display_source_scope="single_record")
        if name in group_info:
            members, max_pair, min_shared = group_info[name]
            # A representative's habitat, accession or type status is not a
            # shared property of a collapsed group. Raw rows remain in ledger.
            if group_label != "representative":
                for column in header:
                    if column not in {"tip", "role", "taxon", "label"}:
                        result[column] = ""
            if group_label == "representative":
                # The representative keeps its OWN category/source: they are that record's deposited
                # fields, not a claim about the members, which stay in the ledger.
                # SEXTANT_421l (Alex 2026-09-09): show the group as its representative -- a real record,
                # whose label and source fields are its own -- with the member count appended. The
                # members remain in the ledger. Bound here so the receipt covers the label.
                result["label"] = f'{row["label"]} (+{len(members) - 1} grouped; max {max_pair} nt differences; min {min_shared} shared sites)'
            else:
                result["label"] = (f'{row["taxon"]} {{{len(members)} reference isolates; '
                                   f'<={max_nt} nt; rep={name}}}')
            result["display_members"] = str(len(members))
            result["display_source_scope"] = "member_records_in_ledger"
        display_rows.append(result)
    ledger = []
    for name in sorted(names):
        rep = representatives[name]
        action = "OUTGROUP_PRUNED_FOR_DISPLAY" if name in pruned else (
            "COLLAPSED_MEMBER" if name != rep else "COLLAPSED_REPRESENTATIVE" if rep in group_info else "RETAINED")
        m, shared = distance(name, rep)
        info = group_info.get(rep)
        ledger.append(dict(tip=name, representative_tip=rep, action=action,
                           mismatches_to_representative=str(m), shared_columns=str(shared),
                           max_pair_mismatches=str(info[1]) if info else "",
                           min_pair_shared_columns=str(info[2]) if info else "",
                           original_metadata_json=json.dumps(metadata[name], sort_keys=True, ensure_ascii=True)))
    buffer = io.StringIO()
    # Bio.Phylo defaults to five decimals, which changes retained distances.
    Phylo.write(display, buffer, "newick", format_branch_length="%.17g", format_confidence="%.17g")
    return {"tree": buffer.getvalue().encode("utf-8"),
            "metadata": tsv_bytes(header + extra, display_rows),
            "ledger": tsv_bytes(list(ledger[0]), ledger)}


def binding(path, relative_to):
    path = Path(path).resolve()
    data = path.read_bytes()
    return {"path": os.path.relpath(path, relative_to), "sha256": digest(data), "bytes": len(data)}


def write_exclusive(path, data):
    path = Path(path)
    with path.open("xb") as handle:
        handle.write(data)


def create_display(aln, nwk, meta, prefix, parameters):
    prefix = Path(prefix)
    outputs = {"tree": Path(str(prefix) + "_display.nwk"),
               "metadata": Path(str(prefix) + "_display_meta.tsv"),
               "ledger": Path(str(prefix) + "_collapse_ledger.tsv")}
    receipt_path = Path(str(prefix) + "_display_receipt.json")
    inputs = {"alignment": Path(aln), "analysis_tree": Path(nwk), "metadata": Path(meta)}
    resolved = [p.resolve() for p in [*outputs.values(), receipt_path]]
    if len(set(resolved)) != len(resolved) or any(p.exists() or p.is_symlink() for p in [*outputs.values(), receipt_path]):
        raise ValueError("OUTPUT_EXISTS_OR_ALIASED")
    if set(resolved) & {p.resolve() for p in inputs.values()}:
        raise ValueError("OUTPUT_ALIASES_INPUT")
    before = {k: binding(p, receipt_path.parent.resolve()) for k, p in inputs.items()}
    data = build_display(aln, nwk, meta, parameters)
    if before != {k: binding(p, receipt_path.parent.resolve()) for k, p in inputs.items()}:
        raise ValueError("INPUT_CHANGED_DURING_BUILD")
    for key, path in outputs.items():
        write_exclusive(path, data[key])
    receipt = {"schema": SCHEMA, "authority": "DISPLAY_ONLY_NOT_SCIENTIFIC_ACCEPTANCE",
               "inputs": before, "parameters": parameters,
               "outputs": {k: binding(p, receipt_path.parent.resolve()) for k, p in outputs.items()}}
    write_exclusive(receipt_path, (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    return receipt_path, digest(receipt_path.read_bytes())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    ap.add_argument("aln"); ap.add_argument("nwk"); ap.add_argument("meta")
    ap.add_argument("--max-nt", type=int, required=True)
    ap.add_argument("--min-cols", type=int, required=True)
    ap.add_argument("--protect", action="append", default=[], help="Exact additional tip to retain; repeatable")
    ap.add_argument("--prune-outgroup", action="store_true")
    ap.add_argument("--group-label", choices=["group", "representative"], default="group",
                    help="how a collapsed clade is labelled: a group summary, or its representative record with group size and measured pairwise bounds")
    ap.add_argument("--out-prefix", required=True)
    a = ap.parse_args(argv)
    try:
        path, sha = create_display(a.aln, a.nwk, a.meta, a.out_prefix,
                                  dict(max_nt=a.max_nt, min_cols=a.min_cols, protect=a.protect,
                                       prune_outgroup=a.prune_outgroup,
                                       **({"group_label": a.group_label} if a.group_label != "group" else {})))
        emit(f"DISPLAY_RECEIPT {path}\nDISPLAY_RECEIPT_SHA256 {sha}")
        return 0
    except (ValueError, OSError, ImportError) as exc:
        _LOG.error(f"REFUSED [TREE_DISPLAY]: {exc}")
        return 2


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    raise SystemExit(main())
