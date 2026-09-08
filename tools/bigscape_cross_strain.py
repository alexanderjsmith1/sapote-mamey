#!/usr/bin/env python3
"""Write a deterministic, qualified cross-strain BiG-SCAPE GCF table."""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse
import collections
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
    is_mibig = "mibig" in path.lower() or base.upper().startswith("BGC")
    strain = "MIBiG" if is_mibig else strain_from_gbk_name(base)
    locator_match = LOCATOR.search(base)
    locator = f"{locator_match.group(1)}.{locator_match.group(2)}" if locator_match else base
    return strain, locator, is_mibig


def _dominant(counter):
    return sorted(counter.items(), key=lambda item: (-item[1], item[0]))[0][0]


def build_rows(db, run_id, cutoff=None, min_strains=2):
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
              "gcf_namespace", "n_strains", "strains", "n_members", "bin",
              "dominant_product", "contains_MIBiG", "members_locators"]
    return "\t".join(fields) + "\n" + "".join(
        "\t".join(row[field] for field in fields) + "\n" for row in rows
    )


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--min-strains", type=int, default=2)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--cutoff", default=None, help="optional exact cutoff; otherwise emit every stored cutoff")
    args = parser.parse_args(argv)
    try:
        rows = build_rows(args.db, args.run_id, args.cutoff, args.min_strains)
        atomic_write_text(args.out, render_rows(rows))
    except NamespaceError as error:
        # v9.7.405: sys.stderr.write, not print() — a typed-refusal diagnostic, and the
        # print ratchet is at ceiling. Registering these front doors as EXCLUDED files
        # would have dropped their PRE-EXISTING prints from the count too: a lower
        # measure without paying anything.
        sys.stderr.write(public_error(error) + "\n")
        return 2
    emit(f"wrote {len(rows)} qualified cross-strain families")
    return 0


if __name__ == "__main__":
    sys.exit(main())
