#!/usr/bin/env python3
"""Write a deterministic, qualified cross-strain BiG-SCAPE GCF table."""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse
import collections
import csv
import io
import os
import re
import sqlite3
import sys
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mamey.bigscape_namespace import (  # noqa: E402
    NamespaceError, atomic_write_text, build_family_identity, normalize_cutoff,
    normalize_run_id, public_error, strain_from_gbk_name,
)

LOCATOR = re.compile(r"_(NODE_.+)\.(region\d+)\.gbk$", re.I)


def parse(path):
    base = os.path.basename(path)
    # Directory names do not determine reference namespace.
    strain = strain_from_gbk_name(base)
    is_mibig = strain == "MIBiG"
    locator_match = LOCATOR.search(base)
    locator = f"{locator_match.group(1)}.{locator_match.group(2)}" if locator_match else base
    return strain, locator, is_mibig


def _dominant(counter):
    return sorted(counter.items(), key=lambda item: (-item[1], item[0]))[0][0]


# antiSMASH/BiG-SCAPE join hybrid products with "."; "-" and "_" occur inside a single product name
# (terpene-precursor, NRP-metallophore, fatty_acid), so parking splits on "." only.
HYBRID_SEPARATOR = "."
PARK_RULES = {
    "all-tokens": "park when every '.'-separated product in dominant_product equals a named product (case-insensitive)",
    "any-token": "park when any '.'-separated product in dominant_product equals a named product (case-insensitive)",
    "contains": "case-insensitive contains match on dominant_product",
}


def is_parked(product, tokens, mode="all-tokens"):
    text = (product or "").lower()
    if mode == "contains":
        return any(token in text for token in tokens)
    parts = [part for part in text.split(HYBRID_SEPARATOR) if part]
    hits = [part in tokens for part in parts]
    return bool(parts) and (all(hits) if mode == "all-tokens" else any(hits))


def load_labels(path):
    if not path:
        return {}
    result = {}
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.reader(handle, delimiter="\t"):
            if row and row[0] == "strain":
                continue
            if len(row) != 2 or not all(row) or row[0] in result:
                raise ValueError("LABELS_REFUSED: unique keys and exactly two nonempty columns required")
            result[row[0]] = row[1]
    return result


def build_rows(db, run_id, cutoff=None, min_strains=2, labels=None):
    selected_run = normalize_run_id(run_id)
    selected_cutoff = normalize_cutoff(cutoff) if cutoff is not None else None
    with sqlite3.connect(db) as connection:
        rows = connection.execute("""
          select fam.cutoff, fam.id, fam.bin_label, g.path, br.product, br.category, br.id
          from bgc_record_family rf
          join family fam on fam.id = rf.family_id
          join bgc_record br on br.id = rf.record_id
          join gbk g on g.id = br.gbk_id
          where fam.run_id = ?
          order by fam.cutoff, fam.id, br.id, g.path
        """, (selected_run,)).fetchall()
    families = collections.defaultdict(lambda: {
        "strains": set(), "locators": set(), "products": collections.Counter(),
        "bin": "", "mibig": False,
    })
    assignment = {}
    for raw_cutoff, family_id, bin_label, path, product, category, record_id in rows:
        identity = build_family_identity(selected_run, raw_cutoff, family_id)
        if selected_cutoff is not None and identity.normalized_cutoff != selected_cutoff:
            continue
        prior = assignment.get((record_id, identity.normalized_cutoff))
        if prior is not None and prior != identity.qualified_family_id:
            raise NamespaceError("DUPLICATE_CONFLICT", "one database record has conflicting family assignments")
        assignment[(record_id, identity.normalized_cutoff)] = identity.qualified_family_id
        strain, locator, is_mibig = parse(path)
        data = families[identity]
        if data["bin"] and data["bin"] != (bin_label or ""):
            raise NamespaceError("DUPLICATE_CONFLICT", "one family has conflicting bin labels")
        data["bin"] = bin_label or ""
        data["products"][product or category or "?"] += 1
        if is_mibig:
            data["mibig"] = True
        else:
            data["strains"].add(strain)
            data["locators"].add(f"{strain}:{locator}")
    output = []
    for identity, data in families.items():
        if len(data["strains"]) < min_strains:
            continue
        output.append({
            "cutoff": identity.normalized_cutoff, "family_id": identity.family_id,
            "run_id": str(identity.run_id), "normalized_cutoff": identity.normalized_cutoff,
            "qualified_family_id": identity.qualified_family_id,
            "gcf_namespace": identity.gcf_namespace,
            "n_strains": str(len(data["strains"])), "strains": ",".join(sorted(data["strains"])),
            "strain_labels": "; ".join(f"{labels[s]} ({s})" if labels and s in labels and labels[s] != s else s for s in sorted(data["strains"])),
            "n_members": str(len(data["locators"])), "bin": data["bin"],
            "dominant_product": _dominant(data["products"]),
            "contains_MIBiG": "yes" if data["mibig"] else "no",
            "members_locators": ";".join(sorted(data["locators"])),
        })
    return sorted(output, key=lambda row: (
        Decimal(row["normalized_cutoff"]), -int(row["n_strains"]),
        row["qualified_family_id"], row["members_locators"], row["dominant_product"], row["bin"],
    ))


def render_rows(rows):
    fields = ["cutoff", "family_id", "run_id", "normalized_cutoff", "qualified_family_id",
              "gcf_namespace", "n_strains", "strains", "strain_labels", "n_members", "bin",
              "dominant_product", "contains_MIBiG", "members_locators"]
    from mamey.csv_safety import SafeDictWriter
    buffer = io.StringIO(newline="")
    writer = SafeDictWriter(buffer, fields, delimiter="\t", lineterminator="\n")
    writer.writeheader(); writer.writerows(rows)
    return buffer.getvalue()



def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--out", required=True, help="output TSV file, not a directory")
    parser.add_argument("--min-strains", type=int, default=2)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--cutoff", default=None, help="optional exact cutoff; otherwise emit every stored cutoff")
    parser.add_argument("--labels", help="TSV strain / label; exact keys retained")
    parser.add_argument("--exclude-products", default="", help="comma-separated case-insensitive label tokens; matches are written to <out>.PARKED.tsv")
    parser.add_argument("--exclude-match", choices=tuple(PARK_RULES), default="all-tokens",
                        help="all-tokens (default): park only when every product of a hybrid is named; any-token: "
                             "park when any product is named; contains: legacy substring match, so 'terpene' also "
                             "parks 'terpene-precursor'")
    args = parser.parse_args(argv)
    if os.path.isdir(args.out):
        parser.error("--out must be a TSV file, not a directory")
    try:
        rows = build_rows(args.db, args.run_id, args.cutoff, args.min_strains, load_labels(args.labels))
        tokens = [t.strip().lower() for t in args.exclude_products.split(",") if t.strip()]
        if tokens:
            parked, kept = [], []
            for row in rows:
                (parked if is_parked(row["dominant_product"], tokens, args.exclude_match) else kept).append(row)
            atomic_write_text(args.out + ".PARKED.tsv", render_rows(parked))
            atomic_write_text(args.out + ".FILTER.json", __import__("json").dumps({
                "rule": PARK_RULES[args.exclude_match], "match": args.exclude_match, "tokens": tokens,
                "kept_containing_a_token": sorted({row["dominant_product"] for row in kept
                                                   if any(t in row["dominant_product"].lower() for t in tokens)})[:5],
                "kept": len(kept), "parked": len(parked), "run_id": args.run_id, "cutoff": args.cutoff,
                "ceiling": "Explicit display/export scope; no biological absence claim"}, indent=2) + "\n")
            rows = kept
        atomic_write_text(args.out, render_rows(rows))
    except NamespaceError as error:
        # v9.7.405: sys.stderr.write, not print() — a typed-refusal diagnostic, and the
        # print ratchet is at ceiling. Registering these front doors as EXCLUDED files
        # would have dropped their PRE-EXISTING prints from the count too: a lower
        # measure without paying anything.
        sys.stderr.write(public_error(error) + "\n")
        return 2
    except (OSError, ValueError) as error:
        sys.stderr.write(f"CROSS_STRAIN_REFUSED: {error}\n")
        return 2
    emit(f"wrote {len(rows)} qualified cross-strain families")
    return 0


if __name__ == "__main__":
    sys.exit(main())
