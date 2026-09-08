#!/usr/bin/env python3
"""Validate qualified anchor/base rows, then atomically classify base GCFs."""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse
import collections
import csv
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mamey.bigscape_namespace import (  # noqa: E402
    NamespaceError, atomic_write_text, load_membership_tsv, public_error,
)


def load_anchors(sources):
    anchors = collections.defaultdict(dict); total = 0
    for source in sources:
        rows = load_membership_tsv(
            source, key_fields=("qualified_family_id", "strain", "node_region", "mibig_accession")
        )
        for row in rows:
            locator = f"{row['strain']}:{row['node_region']}"
            accession = row["mibig_accession"]
            product = row.get("mibig_product", "")
            prior = anchors[locator].get(accession)
            if prior is not None and prior != product:
                raise NamespaceError("DUPLICATE_CONFLICT", "conflicting duplicate anchor products")
            anchors[locator][accession] = product; total += 1
    return anchors, total


def build_output(anchor_sources, base_source):
    anchors, total = load_anchors(anchor_sources)
    base_rows = load_membership_tsv(base_source, key_fields=("qualified_family_id",))
    output = []; known = novel = 0
    for row in base_rows:
        members = sorted(set(value for value in row.get("members_locators", "").split(";") if value))
        hit_accessions = {}; known_members = 0
        for member in members:
            if member in anchors:
                known_members += 1; hit_accessions.update(anchors[member])
        row = dict(row); row["status"] = "KNOWN" if hit_accessions else "NOVEL"
        row["n_members_known"] = str(known_members)
        row["mibig_matches"] = ";".join(sorted(hit_accessions))
        known += bool(hit_accessions); novel += not bool(hit_accessions); output.append(row)
    return output, total, known, novel


def render_rows(rows):
    if not rows:
        return ""
    fields = list(rows[0])
    stream = io.StringIO(newline=""); writer = _SafeDictWriter(stream, fieldnames=fields, delimiter="\t", lineterminator="\n")
    writer.writeheader(); writer.writerows(rows); return stream.getvalue()


def main(argv=None):
    parser = argparse.ArgumentParser(); parser.add_argument("--anchors", nargs="+", required=True)
    parser.add_argument("--base-cross-strain", required=True); parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        rows, total, known, novel = build_output(args.anchors, args.base_cross_strain)
        atomic_write_text(args.out, render_rows(rows))
    except NamespaceError as error:
        # v9.7.405: sys.stderr.write, not print() — a typed-refusal diagnostic, and the
        # print ratchet is at ceiling. Registering these front doors as EXCLUDED files
        # would have dropped their PRE-EXISTING prints from the count too: a lower
        # measure without paying anything.
        sys.stderr.write(public_error(error) + "\n"); return 2
    emit(f"merged {total} qualified anchoring edges; {known} KNOWN and {novel} NOVEL families")
    return 0


if __name__ == "__main__":
    sys.exit(main())
