#!/usr/bin/env python3
"""Does each BLASTp row's gene tag name the protein that was searched? An audit that never edits its inputs.

BLASTp result rows name the query by locus tag and record the query length (aa_length). In some result sets the tag is
the gene's 1-based position inside its antiSMASH region, written with the contig prefix (`ctg16_18` for the 18th CDS of
a region on contig 16), not the contig-wide locus tag. Joining such rows by tag attaches the hit to another gene.

For every row with a gene tag this tool writes one keyed row:
  TAG_OK             the tag is a CDS of the genome and its protein length equals the recorded length
  REGION_POSITION    the tag is not that, but exactly one region on the tag's contig has, at that position, a CDS whose
                     length equals the recorded length; the row is keyed to that CDS
  held rows          NO_LENGTH (no usable recorded length), AMBIGUOUS (more than one region fits), NO_FIT (no rule
                     fits; another assembly or gene calling is the usual cause), TAG_UNPARSED (not a ctgN_M tag)
Bound rows carry the canonical locus tag, the full contig, the region, the BGC alias from the package inventory when one
is given (bound by contig and region, never by an old BGC number), and the protein's SHA-256.

The region order comes from each region GenBank file in the antiSMASH result ZIP. The genome-wide GenBank file also
lists a CDS that only overlaps a region edge, so its order is off by one at region starts.

Usage:
  python3 tools/blastp_tag_position_audit.py --antismash-zip <strain>.zip --rows <results.csv> [--rows ...] \
      [--inventory <strain>_2_inventory.csv] --out <keyed.tsv>
Rows need columns gene and aa_length; strain and bgc_id are copied through when present. The output must not exist.
REGION_POSITION is an inference from position and length; adopting keyed rows as evidence is the owner's decision.
"""
from __future__ import annotations

import os as _os, sys as _sys  # bundle-root path guard (see tests/test_tool_front_doors.py)
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

import argparse
import csv
import io
import re
import zipfile
from collections import Counter
from pathlib import Path

from mamey.csv_safety import SafeDictWriter
from mamey.path_safety import assert_output_outside_bundle
from mamey.protein_binding import protein_sha256

COLS = ["source_file", "source_row", "strain", "source_bgc", "source_gene", "aa_length", "binding",
        "locus_tag", "contig", "region", "bgc_alias", "protein_sha256"]
_TAG = re.compile(r"(ctg\d+)_(\d+)$")


def _records(zf: zipfile.ZipFile, name: str):
    try:
        from Bio import SeqIO
    except ImportError:  # the bundle's GenBank shim covers antiSMASH region files without biopython
        from mamey._gbk_shim import SeqIO
    return list(SeqIO.parse(io.StringIO(zf.read(name).decode("utf-8", "replace")), "genbank"))


def _is_member(name: str, region: bool) -> bool:
    base = name.rsplit("/", 1)[-1]
    if not name.endswith(".gbk") or "__MACOSX" in name or base.startswith("._") or name.startswith("input/"):
        return False
    return (".region" in base) == region


def load_genome(zip_path: Path) -> tuple[dict, dict]:
    """({locus tag: (contig, aa length, protein)}, {(ctg prefix, region file): [locus tags in file order]})."""
    with zipfile.ZipFile(zip_path) as zf:
        tops = [i for i in zf.infolist() if _is_member(i.filename, region=False)]
        if not tops:
            raise SystemExit(f"no genome GenBank file in {zip_path}")
        top = max(tops, key=lambda i: i.file_size).filename
        cds = {}
        for rec in _records(zf, top):
            for f in rec.features:
                if f.type == "CDS":
                    tag = f.qualifiers.get("locus_tag", [""])[0]
                    aa = f.qualifiers.get("translation", [""])[0]
                    cds[tag] = (rec.id, len(aa), aa)
        regions = {}
        for name in sorted(n for n in zf.namelist() if _is_member(n, region=True)):
            recs = _records(zf, name)
            tags = [f.qualifiers.get("locus_tag", [""])[0] for r in recs for f in r.features if f.type == "CDS"]
            m = _TAG.match(tags[0]) if tags else None
            if m:
                regions[(m.group(1), name)] = tags
    return cds, regions


def load_inventory(path: Path | None) -> dict:
    """{(full contig, regionNNN): BGC alias} from a package *_2_inventory.csv."""
    if not path:
        return {}
    with open(path, newline="", encoding="utf-8") as fh:
        return {(r["Contig"], r["antiSMASH_Region"]): r["BGC_ID"] for r in csv.DictReader(fh)
                if r.get("Contig") and r.get("antiSMASH_Region") and r.get("BGC_ID")}


def _region_of(name: str) -> str:
    m = re.search(r"\.(region\d{3})\.gbk$", name)
    return m.group(1) if m else ""


def key_row(gene: str, aa_text: str, cds: dict, regions: dict) -> tuple[str, str, str]:
    """(binding, canonical locus tag, region file) for one row."""
    m = _TAG.match((gene or "").strip())
    if not m:
        return "TAG_UNPARSED", "", ""
    try:
        aa = int(float(aa_text))
    except (TypeError, ValueError):
        aa = 0
    if aa <= 0:
        return "NO_LENGTH", "", ""
    if gene in cds and cds[gene][1] == aa:
        reg = next((n for (c, n), tags in regions.items() if c == m.group(1) and gene in tags), "")
        return "TAG_OK", gene, reg
    k = int(m.group(2))
    fits = [(tags[k - 1], n) for (c, n), tags in regions.items()
            if c == m.group(1) and 0 < k <= len(tags) and cds.get(tags[k - 1], ("", -1))[1] == aa]
    if len(fits) == 1:
        return "REGION_POSITION", fits[0][0], fits[0][1]
    return ("AMBIGUOUS", "", "") if fits else ("NO_FIT", "", "")


def audit(zip_path: Path, row_files: list[Path], inventory: Path | None) -> tuple[list[dict], Counter]:
    cds, regions = load_genome(zip_path)
    alias = load_inventory(inventory)
    out, counts = [], Counter()
    for src in row_files:
        with open(src, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            if not reader.fieldnames or not {"gene", "aa_length"} <= set(reader.fieldnames):
                raise SystemExit(f"{src}: rows need columns gene and aa_length")
            for i, r in enumerate(reader, 2):
                binding, tag, reg_file = key_row(r.get("gene", ""), r.get("aa_length", ""), cds, regions)
                counts[binding] += 1
                contig = cds[tag][0] if tag else ""
                region = _region_of(reg_file)
                out.append({"source_file": str(src), "source_row": i, "strain": r.get("strain", ""),
                            "source_bgc": r.get("bgc_id", ""), "source_gene": r.get("gene", ""),
                            "aa_length": r.get("aa_length", ""), "binding": binding, "locus_tag": tag,
                            "contig": contig, "region": region, "bgc_alias": alias.get((contig, region), ""),
                            "protein_sha256": protein_sha256(cds[tag][2]) if tag else ""})
    return out, counts


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--antismash-zip", type=Path, required=True, help="the genome's antiSMASH result ZIP")
    ap.add_argument("--rows", type=Path, action="append", required=True, help="BLASTp result CSV (repeatable)")
    ap.add_argument("--inventory", type=Path, help="package *_2_inventory.csv, to name the current BGC alias")
    ap.add_argument("--out", type=Path, required=True, help="keyed TSV to write (must not exist)")
    a = ap.parse_args(argv)
    if a.out.exists() or a.out.is_symlink():
        raise SystemExit(f"refusing to overwrite {a.out}")
    assert_output_outside_bundle(a.out, __file__)
    rows, counts = audit(a.antismash_zip, a.rows, a.inventory)
    with open(a.out, "x", newline="", encoding="utf-8") as fh:
        w = SafeDictWriter(fh, fieldnames=COLS, delimiter="\t")
        w.writeheader()
        w.writerows(rows)
    # one summary line on stdout (sys.stdout.write keeps the print_calls ratchet flat)
    _sys.stdout.write(f"{len(rows)} rows -> {a.out}: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
