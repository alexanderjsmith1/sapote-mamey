#!/usr/bin/env python3
"""sixteen_s_similarity_check.py — do the deposited 16S similarity values reproduce from the sequences on file?

For each strain: align its 16S (FASTA) to every record of its deposited closest type-strain species in a local 16S BLAST
database (e.g. NCBI 16S RefSeq), take the best identity, and compare with the deposited similarity. Also report the nearest
record overall (hits covering >= 90% of the query, highest identity). Flags differences of >= --flag points.

Why: on 2026-09-24, 11 of 133 bee/wasp isolates whose deposited closest species is in NCBI 16S RefSeq did not reproduce by
>= 1 point (e.g. deposited 100% to S. xylanilyticus, 96.3% recomputed; deposited 95.0% to S. gloriosae, 100% recomputed).
The 16S figures plot deposited values as-deposited, so the check is a report for the owner, not a correction.

Input table (TSV) columns: strain, genus_16s ("Streptomyces sp."), closest_type_strain ("S. griseus" or full name),
similarity_percent. FASTA headers must contain the strain id.
Usage:
  python tools/sixteen_s_similarity_check.py --fasta q.fa --table t.tsv --db PATH/16S_ribosomal_RNA --blast-bin DIR --out out.tsv
blastn/blastdbcmd (BLAST+) must be available; paths with spaces break BLAST, so the tool works in a temporary folder.
"""
from __future__ import annotations
import argparse, csv, re, shutil, subprocess, sys, tempfile
from pathlib import Path
try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run from a foreign cwd
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter


def full_species(genus_16s: str, closest: str) -> str:
    """'Streptomyces sp.' + 'S. griseus' -> 'Streptomyces griseus'; a full name is kept."""
    gen = genus_16s.replace(" sp.", "").strip()
    m = re.match(r"^([A-Z])\.\s*(\S+)", closest.strip())
    if m and gen.startswith(m.group(1)):
        return f"{gen} {m.group(2)}"
    return closest.strip()


def flag(deposited: str, recomputed: str, points: float) -> bool:
    try:
        return abs(float(deposited) - float(recomputed)) >= points
    except ValueError:
        return False


def read_fasta(p: Path) -> dict[str, str]:
    seqs, cur = {}, None
    for line in open(p):
        if line.startswith(">"):
            m = re.search(r"(AS-\d+|\S+)", line[1:]); cur = m.group(1); seqs[cur] = ""
        elif cur:
            seqs[cur] += line.strip()
    return seqs


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--fasta", required=True, type=Path); ap.add_argument("--table", required=True, type=Path)
    ap.add_argument("--db", required=True); ap.add_argument("--blast-bin", default="")
    ap.add_argument("--out", required=True, type=Path); ap.add_argument("--flag", type=float, default=1.0)
    a = ap.parse_args(argv)
    bb = (lambda t: str(Path(a.blast_bin) / t)) if a.blast_bin else (lambda t: shutil.which(t) or t)
    seqs = read_fasta(a.fasta)
    rows = [r for r in csv.DictReader(open(a.table), delimiter="\t") if r["strain"] in seqs]
    titles = subprocess.run([bb("blastdbcmd"), "-db", a.db, "-entry", "all", "-outfmt", "%a\t%t"],
                            capture_output=True, text=True, check=True).stdout.splitlines()
    titles = [t.split("\t", 1) for t in titles if "\t" in t]
    out = []
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        for r in rows:
            (td / "q.fa").write_text(f">{r['strain']}\n{seqs[r['strain']]}\n")
            sp = full_species(r.get("genus_16s", ""), r.get("closest_type_strain", ""))
            accs = [acc for acc, t in titles if t.startswith(sp + " ")]
            same = ""
            if accs:
                subprocess.run([bb("blastdbcmd"), "-db", a.db, "-entry", ",".join(accs), "-out", str(td / "s.fa")], check=True)
                o = subprocess.run([bb("blastn"), "-task", "megablast", "-query", str(td / "q.fa"), "-subject", str(td / "s.fa"),
                                    "-outfmt", "6 pident length bitscore"], capture_output=True, text=True).stdout.split("\n")
                hs = [l.split("\t") for l in o if l.strip()]
                if hs:
                    same = f"{float(max(hs, key=lambda x: float(x[2]))[0]):.2f}"
            o = subprocess.run([bb("blastn"), "-task", "megablast", "-query", str(td / "q.fa"), "-db", a.db, "-max_target_seqs", "10",
                                "-outfmt", "6 pident length qlen bitscore stitle"], capture_output=True, text=True).stdout.split("\n")
            hs = [l.split("\t") for l in o if l.strip()]
            good = [h for h in hs if int(h[1]) >= 0.9 * int(h[2])] or hs
            near = max(good, key=lambda h: (float(h[0]), float(h[3]))) if good else None
            out.append(dict(strain=r["strain"], deposited_species=sp, deposited_similarity=r.get("similarity_percent", ""),
                            deposited_species_in_db=int(bool(accs)), identity_to_deposited_species=same,
                            nearest_identity=f"{float(near[0]):.2f}" if near else "", nearest_title=near[4] if near else "",
                            query_bp=len(seqs[r["strain"]]),
                            flag=int(flag(r.get("similarity_percent", ""), same, a.flag))))
    with open(a.out, "w", newline="") as h:
        w = _SafeDictWriter(h, fieldnames=list(out[0]), delimiter="\t", lineterminator="\n"); w.writeheader(); w.writerows(out)
    n = sum(r["flag"] for r in out)
    print(f"{len(out)} strains; deposited species in database for {sum(r['deposited_species_in_db'] for r in out)}; "
          f"{n} differ from the deposited value by >= {a.flag} point(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
