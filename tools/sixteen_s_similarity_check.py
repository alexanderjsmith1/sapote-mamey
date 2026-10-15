#!/usr/bin/env python3
"""sixteen_s_similarity_check.py — do the deposited 16S similarity values reproduce from the sequences on file?

For each strain: align its 16S (FASTA) to every record of its deposited closest type-strain species in a local 16S BLAST
database (e.g. NCBI 16S RefSeq), take the best identity, and compare with the deposited similarity. Also report the nearest
record overall (hits covering >= 90% of the query, highest identity). Flags differences of >= --flag points.

Two identity readings are reported for each value:
- raw: BLAST pident, which counts every IUPAC ambiguity code (N, R, Y, ...) in either sequence as a mismatch;
- unambiguous: identity over the alignment columns where both sequences carry A, C, G, T or a gap
  (`_phylo16s.unambiguous_identity`). Partial Sanger reads often carry ambiguous calls; 27 in a 702 bp read lowers
  pident by about 3.8 points. Quote the unambiguous value against a species threshold, and give query_ambiguous_bp.
The nearest record is searched across every sequence in the database (-max_target_seqs = its record count), because
BLAST keeps the first N subjects in its own order, not the N most identical; a cap of 10 missed the nearest type strain
in large genera.

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
import argparse, csv, hashlib, json, re, shutil, subprocess, sys, tempfile
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



def _fmt(v) -> str:
    return f"{v:.2f}" if v is not None else ""


def _nearest_search(bb, query, db: str, n_targets: int, floor: float = 85.0) -> list[str]:
    """blastn against every record of the database. Hits below a raw identity floor are left out to keep the output
    small; if nothing passes the floor, the search runs again without it."""
    cmd = [bb("blastn"), "-task", "megablast", "-query", str(query), "-db", db, "-max_target_seqs", str(n_targets),
           "-outfmt", "6 pident length qlen bitscore stitle qseq sseq"]
    o = subprocess.run(cmd + ["-perc_identity", str(floor)], capture_output=True, text=True).stdout.split("\n")
    if not any(l.strip() for l in o):
        o = subprocess.run(cmd, capture_output=True, text=True).stdout.split("\n")
    return o


def _shared_phylo16s():
    """The shared 16S helpers (database lookup, BLAST binaries); see docs/LOCAL_16S_DATABASE.md."""
    here = str(Path(__file__).resolve().parent)
    if here not in sys.path:
        sys.path.insert(0, here)
    import _phylo16s
    return _phylo16s

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--fasta", required=True, type=Path); ap.add_argument("--table", required=True, type=Path)
    ap.add_argument("--db", default=None, help="16S RefSeq BLAST DB prefix (default: the shared lookup, docs/LOCAL_16S_DATABASE.md)")
    ap.add_argument("--blast-bin", default="")
    ap.add_argument("--out", required=True, type=Path); ap.add_argument("--flag", type=float, default=1.0)
    a = ap.parse_args(argv)
    _p16 = _shared_phylo16s()
    a.db = _p16.refseq_16s_blastdb(a.db)
    def _found(tool):  # PATH first, then the shared helper's known locations, else the bare name (as before)
        if shutil.which(tool):
            return shutil.which(tool)
        try:
            return _p16.blast_bin(tool)
        except SystemExit:
            return tool
    bb = (lambda t: str(Path(a.blast_bin) / t)) if a.blast_bin else _found
    seqs = read_fasta(a.fasta)
    rows = [r for r in csv.DictReader(open(a.table), delimiter="\t") if r["strain"] in seqs]
    titles = subprocess.run([bb("blastdbcmd"), "-db", a.db, "-entry", "all", "-outfmt", "%a\t%t"],
                            capture_output=True, text=True, check=True).stdout.splitlines()
    titles = [t.split("\t", 1) for t in titles if "\t" in t]
    n_targets = _p16.blastdb_sequence_count(a.db, bb("blastdbcmd")) or _p16.ALL_RECORDS_FALLBACK

    def _unamb(h, qi, pi):  # identity over unambiguous columns (qseq, sseq at qi, qi+1); pident if the row has no sequences
        if len(h) > qi + 1:
            v = _p16.unambiguous_identity(h[qi], h[qi + 1])[0]
            if v is not None:
                return v
        return float(h[pi])
    out = []
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        for r in rows:
            (td / "q.fa").write_text(f">{r['strain']}\n{seqs[r['strain']]}\n")
            sp = full_species(r.get("genus_16s", ""), r.get("closest_type_strain", ""))
            accs = [acc for acc, t in titles if t.startswith(sp + " ")]
            same = same_u = ""
            if accs:
                subprocess.run([bb("blastdbcmd"), "-db", a.db, "-entry", ",".join(accs), "-out", str(td / "s.fa")], check=True)
                o = subprocess.run([bb("blastn"), "-task", "megablast", "-query", str(td / "q.fa"), "-subject", str(td / "s.fa"),
                                    "-outfmt", "6 pident length bitscore qseq sseq"], capture_output=True, text=True).stdout.split("\n")
                hs = [l.split("\t") for l in o if l.strip()]
                if hs:
                    same = f"{float(max(hs, key=lambda x: float(x[2]))[0]):.2f}"
                    same_u = _fmt(max((_unamb(h, 3, 0) for h in hs), default=None))
            o = _nearest_search(bb, td / "q.fa", a.db, n_targets)
            hs = [l.split("\t") for l in o if l.strip()]
            good = [h for h in hs if int(h[1]) >= 0.9 * int(h[2])] or hs
            near = max(good, key=lambda h: (float(h[0]), float(h[3]))) if good else None
            near_u = max(good, key=lambda h: (_unamb(h, 5, 0), float(h[3]))) if good else None
            out.append(dict(strain=r["strain"], deposited_species=sp, deposited_similarity=r.get("similarity_percent", ""),
                            deposited_species_in_db=int(bool(accs)), identity_to_deposited_species=same,
                            nearest_identity=f"{float(near[0]):.2f}" if near else "", nearest_title=near[4] if near else "",
                            query_bp=len(seqs[r["strain"]]),
                            flag=int(flag(r.get("similarity_percent", ""), same, a.flag)),
                            query_ambiguous_bp=sum(1 for c in seqs[r["strain"]].upper() if c not in "ACGT"),
                            identity_to_deposited_species_unambiguous=same_u,
                            nearest_identity_unambiguous=_fmt(_unamb(near_u, 5, 0)) if near_u else "",
                            nearest_title_unambiguous=near_u[4] if near_u else ""))
    with open(a.out, "w", newline="") as h:
        w = _SafeDictWriter(h, fieldnames=list(out[0]), delimiter="\t", lineterminator="\n"); w.writeheader(); w.writerows(out)
    receipt = dict(tool="tools/sixteen_s_similarity_check.py", out=str(a.out), flag_points=a.flag,
                   fasta=str(a.fasta), fasta_sha256=hashlib.sha256(a.fasta.read_bytes()).hexdigest(),
                   table=str(a.table), table_sha256=hashlib.sha256(a.table.read_bytes()).hexdigest(),
                   strains_checked=len(out), max_target_seqs=n_targets,
                   identity_rule="raw = BLAST pident; unambiguous = columns where both sequences carry A/C/G/T or a gap",
                   **_p16.blastdb_receipt(a.db, bb("blastdbcmd")))
    Path(str(a.out) + ".receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    n = sum(r["flag"] for r in out)
    print(f"{len(out)} strains; deposited species in database for {sum(r['deposited_species_in_db'] for r in out)}; "
          f"{n} differ from the deposited value by >= {a.flag} point(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
