#!/usr/bin/env python3
"""Protein encoded in antiSMASH regions per genome: the input of the region protein figure (B03, region_protein_by_genus).

For each antiSMASH result ZIP (one detection strictness for all), every region GenBank is read: amino acids are the
summed lengths of the CDS /translation values in the region. A region is saccharide-only when every /product on its
region feature is "saccharide"; `amino_acids` leaves those regions out (the bee and moss Fig. 3B measure, batch 26
column aa_in_regions_excl_saccharide_only), and `amino_acids_all_regions` keeps them. A CDS without a translation is
counted in `missing_CDS_lengths`, which the figure tool refuses unless it is zero. Regions are found exactly as in
tools/region_table_one_setting.py. Counts describe the supplied assemblies only.
"""
import argparse
import re
import sys
import zipfile
from pathlib import Path

try:  # CSV formula-cell guard (mamey/csv_safety.py)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import os as _os
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

from mamey.antismash_input import VALID_STRICTNESS, detect_strictness
from mamey.ziputil import regular_file_names
from region_table_one_setting import PRODUCT, REGION_BLOCK, REGION_GBK, sha256, strain_of

CDS_BLOCK = re.compile(r"\n {5}CDS {13}.*?(?=\n {5}\S|\nORIGIN)", re.S)
TRANSLATION = re.compile(r'/translation="([^"]+)"')
COLUMNS = ["strain", "strictness", "regions", "saccharide_only_regions", "cds", "missing_CDS_lengths",
           "amino_acids_all_regions", "amino_acids", "zip_sha256"]


def totals(zf):
    regions = sacch = cds = missing = aa_all = aa = 0
    seen = set()
    for name in regular_file_names(zf):
        m = REGION_GBK.search(name)
        if not m:
            continue
        if Path(name).name in seen:
            raise ValueError(f"duplicate region filename in ZIP: {Path(name).name}")
        seen.add(Path(name).name)
        text = zf.read(name).decode(errors="ignore")
        block = REGION_BLOCK.search(text)
        products = set(PRODUCT.findall(block.group(0) if block else ""))
        if not products:
            raise ValueError(f"region without a product: {name}")
        only_sacch = products == {"saccharide"}
        region_aa = 0
        for c in CDS_BLOCK.finditer(text):
            cds += 1
            t = TRANSLATION.search(c.group(0))
            if t:
                region_aa += len(re.sub(r"\s", "", t.group(1)))
            else:
                missing += 1
        regions += 1
        sacch += only_sacch
        aa_all += region_aa
        aa += 0 if only_sacch else region_aa
    if not regions:
        raise ValueError("no antiSMASH region GenBank files")
    return dict(regions=regions, saccharide_only_regions=sacch, cds=cds, missing_CDS_lengths=missing,
                amino_acids_all_regions=aa_all, amino_acids=aa)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--zips", nargs="+", type=Path, required=True)
    ap.add_argument("--strictness", required=True, choices=sorted(VALID_STRICTNESS))
    ap.add_argument("--out", required=True, type=Path, help="new TSV")
    a = ap.parse_args(argv)
    if a.out.exists():
        raise FileExistsError(f"refusing to overwrite {a.out}")
    rows, problems, names = [], [], set()
    for z in a.zips:
        s = strain_of(z)
        if s in names:
            problems.append(f"{s}: two zips for one strain")
            continue
        names.add(s)
        try:
            with zipfile.ZipFile(z) as zf:
                got, evidence = detect_strictness(zf)
                t = totals(zf)
        except (ValueError, OSError, zipfile.BadZipFile) as exc:
            problems.append(f"{s}: {exc}")
            continue
        if got != a.strictness:
            problems.append(f"{s}: strictness {got} ({evidence}); table is {a.strictness}")
            continue
        rows.append(dict(strain=s, strictness=got, **t, zip_sha256=sha256(z)))
    if problems:
        sys.stderr.write("REGION_PROTEIN_TOTALS_REFUSED:\n  " + "\n  ".join(problems) + "\n")
        return 2
    with a.out.open("w", newline="", encoding="utf-8") as fh:
        w = _SafeDictWriter(fh, fieldnames=COLUMNS, delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    sys.stdout.write(f"{len(rows)} genomes, all {a.strictness} -> {a.out}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
