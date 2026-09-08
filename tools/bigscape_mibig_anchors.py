#!/usr/bin/env python3
"""Emit qualified per-run, per-cutoff MIBiG anchoring edges."""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse
import collections
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mamey.bigscape_namespace import (  # noqa: E402
    NamespaceError, atomic_write_text, build_family_identity, normalize_cutoff,
    normalize_run_id, public_error,
)

# v9.7.374 fix (AUDIT_374), PRESERVED THROUGH THE v9.7.405 NAMESPACE-GUARD REBASE — the
# upstream candidate deleted this rationale along with the code it explains, and the `re.I` below
# is load-bearing for a silent, system-wide failure. bigscape_prep.py names every staged GBK from
# the input zip/dir verbatim with NO case normalization, so a lowercase-named input ("AS-XXX.zip")
# stages GBKs prefixed "AS-XXX_...". Without re.I this regex misses, parse_strain() returns
# (None, locator), and the strain is silently dropped from this chat's anchoring TSV entirely.
# The un-normalized prefix is baked into the filenames consistently across chats, so EVERY
# parallel chat processing that strain hits the identical gap: the strain is never anchored
# anywhere, and bigscape_merge_anchors.py then marks every cross-strain family containing it
# NOVEL instead of KNOWN, system-wide. Same bug class as the audit_public_cut.py fix (v9.7.371);
# the sibling extractors have a generic fallback branch that softens it, this file has none.
# Claim-safety consequence: a dropped strain turns a KNOWN anchoring into a false NOVEL call.
#
# v9.7.409 fix (CLAUDE_409_mibig_anchor_locator): the v9.7.374 rationale above closed the
# case-normalization gap but left the shape of the identifiers hardwired. STRAIN only accepts the
# `AS-<n>`/`SID<n>` naming and LOCATOR only the SPAdes `NODE_<n>_length_..._cov_...` contig token, so
# this cohort's assemblies -- arbitrary strain ids over NCBI WGS-accession contigs, e.g.
# `RB68_WEGH01000001.1.region006.gbk` or `rif_AULB01000001.1.region001.gbk` -- match NEITHER regex:
# parse_strain() returns (None, base), build_rows() drops the record on `if strain:`, and the strain
# is never anchored. That is the identical silent-drop -> false NOVEL failure the comment warns about,
# for a different naming shape (missing != absent). Same fix class as CLAUDE_409_gcf_strain_match's
# parse_locator() NODE-only bug. Below: the NODE_ fast path is preserved byte-for-byte for AS-/SID
# inputs, a general `<strain>_<contig>.regionNN.gbk` fallback binds accession/arbitrary contigs, and a
# record that still cannot be bound is returned as UNBOUND so build_rows() can surface a typed WARNING
# instead of dropping it silently.
STRAIN = re.compile(r"^(AS-\d+|SID\d+)_", re.I)
LOCATOR = re.compile(r"_(NODE_.+)\.(region\d+)\.gbk$", re.I)
# General region-GBK shape: `<strain>_<contig>.region<NN>.gbk`, contig token unconstrained.
REGION_GBK = re.compile(r"^(?P<body>.+)\.(?P<region>region\d+)\.gbk$", re.I)


def is_mibig(path):
    return os.path.basename(path).upper().startswith("BGC")


def parse_strain(path):
    """Return (strain, locator). strain is None only when no strain/locator can be bound at all.

    Determinism: for `AS-`/`SID` strains over SPAdes `NODE_` contigs the result is byte-identical to
    v9.7.408; the general fallback runs only when the NODE_ regex misses.
    """
    base = os.path.basename(path)
    node = LOCATOR.search(base)
    if node:
        # Preserved SPAdes/NODE_ fast path. Prefer the blessed STRAIN capture; fall back to the
        # leading `_`-delimited token so a NODE_ contig under a non-AS/SID strain also binds.
        strain = STRAIN.match(base)
        return (strain.group(1) if strain else base.split("_", 1)[0],
                f"{node.group(1)}.{node.group(2)}")
    region = REGION_GBK.match(base)
    if region and "_" in region.group("body"):
        # `<strain>_<contig>` -> strain is the leading token, contig is the remainder verbatim
        # (an NCBI WGS accession like `WEGH01000001.1` is passed through unchanged).
        strain, contig = region.group("body").split("_", 1)
        if strain and contig:
            return strain, f"{contig}.{region.group('region')}"
    # Unbindable: not a `<strain>_<contig>.regionNN.gbk` record. Surfaced by build_rows(), not dropped.
    return None, base


def build_rows(db, run_id, cutoff):
    selected_run = normalize_run_id(run_id); selected_cutoff = normalize_cutoff(cutoff)
    with sqlite3.connect(db) as connection:
        source = connection.execute("""
          select fam.run_id,fam.cutoff,fam.id,g.path,br.product,br.category,br.id
          from bgc_record_family rf join family fam on fam.id=rf.family_id
          join bgc_record br on br.id=rf.record_id join gbk g on g.id=br.gbk_id
          where fam.run_id=? order by fam.cutoff,fam.id,br.id,g.path
        """, (selected_run,)).fetchall()
    families = collections.defaultdict(lambda: {"strains": set(), "mibig": set()})
    assignments = {}
    unbound = set()  # basenames of non-MIBiG records for which no strain/locator could be bound
    for stored_run, raw_cutoff, family_id, path, product, category, record_id in source:
        identity = build_family_identity(stored_run, raw_cutoff, family_id)
        if identity.normalized_cutoff != selected_cutoff:
            continue
        prior = assignments.get(record_id)
        if prior is not None and prior != identity.qualified_family_id:
            raise NamespaceError("DUPLICATE_CONFLICT", "one database record has conflicting family assignments")
        assignments[record_id] = identity.qualified_family_id
        if is_mibig(path):
            families[identity]["mibig"].add((os.path.splitext(os.path.basename(path))[0], product or category or ""))
        else:
            strain, locator = parse_strain(path)
            if strain:
                families[identity]["strains"].add((strain, locator))
            else:
                # Never drop silently: an un-anchored record whose absence would otherwise read as
                # novelty (missing != absent). Surface it as a typed, deterministic WARNING.
                unbound.add(os.path.basename(path))
    for name in sorted(unbound):
        sys.stderr.write(
            f"WARNING ANCHOR_LOCATOR_UNBOUND: {name} "
            "(no strain/locator could be bound; excluded from anchoring -- "
            "absence here is NOT evidence of novelty)\n"
        )
    output = []
    for identity, data in families.items():
        for strain, locator in sorted(data["strains"]):
            for accession, product in sorted(data["mibig"]):
                output.append({
                    "run_id": str(identity.run_id), "normalized_cutoff": identity.normalized_cutoff,
                    "family_id": identity.family_id, "qualified_family_id": identity.qualified_family_id,
                    "gcf_namespace": identity.gcf_namespace, "strain": strain, "node_region": locator,
                    "mibig_accession": accession, "mibig_product": product,
                })
    return sorted(output, key=lambda row: (
        row["qualified_family_id"], row["strain"], row["node_region"],
        row["mibig_accession"], row["mibig_product"],
    ))


def render_rows(rows):
    fields = ["run_id", "normalized_cutoff", "family_id", "qualified_family_id", "gcf_namespace",
              "strain", "node_region", "mibig_accession", "mibig_product"]
    return "\t".join(fields) + "\n" + "".join("\t".join(row[x] for x in fields) + "\n" for row in rows)


def main(argv=None):
    parser = argparse.ArgumentParser(); parser.add_argument("--db", required=True)
    parser.add_argument("--out", required=True); parser.add_argument("--run-id", required=True)
    parser.add_argument("--cutoff", required=True); args = parser.parse_args(argv)
    try:
        rows = build_rows(args.db, args.run_id, args.cutoff)
        atomic_write_text(args.out, render_rows(rows))
    except NamespaceError as error:
        # v9.7.405: sys.stderr.write, not print() — a typed-refusal diagnostic, and the
        # print ratchet is at ceiling. Registering these front doors as EXCLUDED files
        # would have dropped their PRE-EXISTING prints from the count too: a lower
        # measure without paying anything.
        sys.stderr.write(public_error(error) + "\n"); return 2
    emit(f"wrote {len(rows)} qualified anchoring edges")
    return 0


if __name__ == "__main__":
    sys.exit(main())
