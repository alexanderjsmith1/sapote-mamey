#!/usr/bin/env python3
"""Local names for antiSMASH region genes, for the grey (unmatched) genes of a gap-rescue locus map.

Usage:
  gene_local_names.py --input LABEL=PATH [--input LABEL=PATH ...] --swissprot swissprot.dmnd \
      --mibig-proteins DIR --out DIR [--skip-named TABLE.tsv ...] [--diamond diamond] [--threads 4]

PATH is an antiSMASH result zip, one region GenBank file, or a folder of region GenBank files. LABEL is the strain name
the locus map is drawn under (gap-rescue --label); it must not contain "|".

Every CDS with a translation in the region GenBank files is collected. A gene that a --skip-named table already names
(an NCBI nr table, say) is not searched again; rows bind to genes by protein, as the locus map binds them
(mamey.protein_binding). The rest are searched with DIAMOND blastp (--sensitive, top 10 hits, e-value 1e-5) against
Swiss-Prot and against the MIBiG protein set (DIR/mibig_proteins.dmnd, names from DIR/mibig_proteins.tsv). Each gene
takes the database whose top hit has the higher bitscore. Its name is the commonest cleaned name among that database's
top 10 hits. A MIBiG protein with no product text gives no name; its id is kept as top_hit_def.

Outputs in --out: QUERIES.faa, DIAMOND_SwissProt.tsv, DIAMOND_MIBiG.tsv, GENE_LOCAL_NAMES.tsv and
GENE_LOCAL_NAMES_COUNTS.md. GENE_LOCAL_NAMES.tsv has the columns of the NCBI gene-name table plus protein_sha256, so
gap-rescue --gene-names reads both, NCBI table first. A finished search is reused while QUERIES.faa is unchanged.
Names are similarity, not function; db says which database a name came from.
"""
from __future__ import annotations

import argparse
import collections
import csv
import io
import re
import shutil
import statistics
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from mamey.console import emit  # noqa: E402
from mamey.csv_safety import SafeDictWriter  # noqa: E402
from mamey.protein_binding import bind_name_rows, protein_sha256  # noqa: E402

DATABASES = ("Swiss-Prot", "MIBiG")
TOP_N = 10
EVALUE = "1e-5"
COLUMNS = ["strain", "bgc_id", "gene", "aa_length", "protein_sha256", "db", "n_hits", "top_hit_identity",
           "top10_mean_identity", "top10_consensus_name", "consensus_share", "function_class",
           "function_class_ambiguous", "top_hit_def", "top_hit_organism", "source", "source_file"]
REGION_GBK = re.compile(r"region\d+\.gbk$")

# Function classes: the same keyword rules as the NCBI gene-name table, so both tables fill the locus map alike
# (gap_rescue_locus_map.CLASS_FILL). Keywords on a name, not evidence of function.
FAMILIES = {
    "PKS": r"polyketide|ketosynthase|beta-ketoacyl|acyl carrier|acyltransferase domain|\bKS\b|type I PKS|chain length factor",
    "NRPS": r"non-ribosomal|nonribosomal|peptide synthetase|adenylation|condensation domain|thioesterase",
    "methyltransferase": r"methyltransferase|methylase",
    "glycosyltransferase": r"glycosyltransferase|glycosyl transferase",
    "P450": r"cytochrome p450|p450",
    "oxidoreductase": r"oxidoreductase|dehydrogenase|reductase|oxidase|monooxygenase|dioxygenase|hydroxylase|epimerase",
    "aminotransferase": r"aminotransferase|transaminase",
    "transporter": r"transporter|abc |permease|efflux|mfs|major facilitator|atp-binding",
    "regulator": r"regulator|transcription|sarp|luxr|tetr|marr|gntr|sigma|two-component|histidine kinase|response",
    "sugar": r"dtdp|ndp|glucose|nucleotidyl|sugar|hexose|deoxy",
    "halogenase": r"halogenase",
    "hydrolase": r"hydrolase|esterase|lipase|peptidase|protease|amidase",
    "kinase": r"kinase",
    "synthase_other": r"synthase|synthetase|ligase|cyclase",
}
HOUSEKEEPING = re.compile(r"\barg[a-z]?\b|arginin|ornithine|topoisomerase|helicase|ribosom|trna|rrna|pyrophosphat|"
                          r"dna polymerase|gyrase|recombinase|excisonase|integrase|transposase|chaperone|elongation factor|"
                          r"glutamine synthetase|ribonuclease|uroporphyrinogen|complex i subunit|nadh dehydrogenase|"
                          r"sulfate adenylyltransferase|rna polymerase|cell division|adenine glycosylase|rhamnose isomerase")
HOUSEKEEPING_EXTRA = re.compile(r"\bclp[a-z]?\b|clp protease|chaperon|heat shock|\bgroel\b|\bdnak\b|\bftsh\b")
HYPO = re.compile(r"hypothetical|unknown|uncharacterized|duf\d|^nbc\d|^orf\d|conserved protein")
RESISTANCE = re.compile(r"resistance|beta-lactamase|aminoglycoside|bleomycin|vancomycin|streptogramin|immunity protein|"
                        r"rrna methyltransferase erm|23s rrna .*methyltransferase")
CORE_EXTRA = re.compile(r"aromatase|lanthionine|lantibiotic|lanthipeptide|terpene synthase|terpene cyclase|ycao|"
                        r"squalene|phytoene|radical sam")
# names shared by fatty-acid synthesis and type II PKS genes (FabG, ACP, KAS): class unclear, flagged, not resolved
FATTY = re.compile(r"\bfab[a-z]\b|fatty acid|3-oxoacyl|acyl carrier protein|beta-ketoacyl-(\[?acyl-carrier|\[?acp)|"
                   r"ketoacyl-acp|enoyl-\[?acp")
TRANSPORT_WORDS = re.compile(r"abc|transporter|transport system|permease|efflux|mfs|major facilitator|atp-binding cassette")
CORE_FAM = {"PKS", "NRPS", "synthase_other"}
TAILORING_FAM = {"methyltransferase", "glycosyltransferase", "P450", "oxidoreductase", "aminotransferase", "sugar",
                 "halogenase", "hydrolase", "kinase"}


def clean_name(d: str) -> str:
    """A hit description -> a name: no trailing [organism], MULTISPECIES prefix, RecName tag or accession."""
    d = re.sub(r"\s*\[[^\[\]]*\]\s*$", "", d or "")     # the trailing [organism] only; keep [acyl-carrier-protein] etc.
    d = re.sub(r"^\s*MULTISPECIES:\s*", "", d, flags=re.I)
    d = re.sub(r"^\s*(RecName: Full=|[A-Z]{2}_\d+\.\d+\s+)", "", d)
    return re.sub(r"\s+", " ", d).strip(" ;,")


def function_class(name: str) -> str:
    t = (name or "").lower()
    if not t or HYPO.search(t):
        return "hypothetical"
    if RESISTANCE.search(t):
        return "resistance"
    if HOUSEKEEPING.search(t) or HOUSEKEEPING_EXTRA.search(t):
        return "housekeeping"
    fam = {k for k, rx in FAMILIES.items() if re.search(rx, t, flags=re.I)}
    if "transporter" in fam and not TRANSPORT_WORDS.search(t):
        fam.discard("transporter")             # "atp-binding" alone (Clp protease, kinases, ParA) is not a transporter
    if fam & CORE_FAM or CORE_EXTRA.search(t):
        return "biosynthetic core"
    if "regulator" in fam:
        return "regulator"
    if "transporter" in fam:
        return "transport"
    if fam & TAILORING_FAM:
        return "tailoring"
    return "other"


def ambiguous(name: str) -> str:
    """yes when a name matches the fatty-acid words, or both the housekeeping and the core words. Not resolved here."""
    t = (name or "").lower()
    core = bool({k for k, rx in FAMILIES.items() if re.search(rx, t, flags=re.I)} & CORE_FAM) or bool(CORE_EXTRA.search(t))
    return "yes" if t and (FATTY.search(t) or (HOUSEKEEPING.search(t) and core)) else "no"


def swissprot_title(title: str) -> tuple[str, str]:
    """A Swiss-Prot hit title -> (protein name, organism). Reads NCBI titles ("P1.1 RecName: Full=X; AltName: ...
    [Organism]") and UniProt titles ("sp|P1|X_ORG X OS=Organism OX=... GN=...")."""
    m = re.search(r"RecName: Full=([^;\[]+)", title)
    if m:
        org = re.search(r"\[([^\[\]]+)\]\s*$", title)
        return m.group(1).strip(), org.group(1).strip() if org else ""
    rest = title.split(" ", 1)[1] if " " in title else ""
    org = re.search(r"\sOS=(.+?)(?:\s+[A-Z]{2}=|$)", rest)
    return re.split(r"\s+[A-Z]{2}=", rest, maxsplit=1)[0].strip(), org.group(1).strip() if org else ""


def _region_texts(path: Path):
    """-> [(region file stem, GenBank text)] from an antiSMASH zip, one GenBank file or a folder of them."""
    if path.is_dir():
        files = sorted(p for p in path.iterdir() if REGION_GBK.search(p.name)) or sorted(path.glob("*.gbk"))
        return [(p.name[:-4], p.read_text(errors="replace")) for p in files]
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            return [(Path(n).name[:-4], z.read(n).decode("utf-8", "replace"))
                    for n in sorted(z.namelist()) if REGION_GBK.search(n)]
    return [(path.name.rsplit(".", 1)[0], path.read_text(errors="replace"))]


def region_cds(path: Path) -> dict[str, tuple[str, str]]:
    """-> {locus tag: (region file stem, protein)} for every CDS with a locus tag and a translation. A tag seen in two
    region files keeps its first region."""
    try:
        from Bio import SeqIO
    except ImportError:
        from mamey._gbk_shim import SeqIO
    out: dict[str, tuple[str, str]] = {}
    for stem, text in _region_texts(path):
        for rec in SeqIO.parse(io.StringIO(text), "genbank"):
            for ft in rec.features:
                q = ft.qualifiers
                if ft.type == "CDS" and q.get("translation") and q.get("locus_tag"):
                    out.setdefault(q["locus_tag"][0], (stem, "".join(q["translation"][0].split())))
    return out


def already_named(tables, label: str, cds: dict) -> set[str]:
    """Tags of this label's genes that a --skip-named table names, bound by protein as the locus map binds them."""
    rows = []
    for t in tables or []:
        with open(t, newline="") as fh:
            rows += [r for r in csv.DictReader(fh, delimiter="\t")
                     if r.get("strain") == label and (r.get("top10_consensus_name") or "").strip()]
    bound, _, _ = bind_name_rows(rows, {tag: aa for tag, (_, aa) in cds.items()})
    return set(bound)


def read_hits(tsv: Path, db: str, mibig_products: dict) -> dict:
    """DIAMOND tabular (qseqid sseqid pident bitscore stitle) -> {query: [(bitscore, identity, name, def, organism)]}."""
    hits = collections.defaultdict(list)
    with open(tsv) as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t", 4)
            if len(parts) < 4:
                continue
            q, sid, pid, bit = parts[:4]
            title = parts[4] if len(parts) > 4 else sid
            if db == "Swiss-Prot":
                name, org = swissprot_title(title)
                hit_def = name
            else:
                name, org = mibig_products.get(sid, ""), ""
                hit_def = name or sid
            hits[q].append((float(bit), float(pid), clean_name(name), hit_def, org))
    return hits


def name_row(label: str, tag: str, stem: str, aa: str, hits_by_db: dict) -> dict | None:
    """One gene -> its GENE_LOCAL_NAMES row, or None when neither database has a hit."""
    best = None
    for db in DATABASES:
        h = sorted(hits_by_db.get(db, {}).get(f"{label}|{tag}", []), key=lambda x: (-x[0], -x[1]))[:TOP_N]
        if h and (best is None or h[0][0] > best[1][0][0]):
            best = (db, h)
    if best is None:
        return None
    db, h = best
    names = [x[2] for x in h if x[2]]
    cons, k = collections.Counter(names).most_common(1)[0] if names else ("", 0)
    src = f"DIAMOND_{db.replace('-', '')}.tsv"
    return {"strain": label, "bgc_id": stem, "gene": tag, "aa_length": len(aa), "protein_sha256": protein_sha256(aa),
            "db": db, "n_hits": len(h), "top_hit_identity": f"{h[0][1]:.1f}",
            "top10_mean_identity": f"{statistics.mean(x[1] for x in h):.1f}", "top10_consensus_name": cons,
            "consensus_share": f"{k} of {len(h)}", "function_class": function_class(cons),
            "function_class_ambiguous": ambiguous(cons), "top_hit_def": h[0][3], "top_hit_organism": h[0][4],
            "source": f"local DIAMOND {db}", "source_file": src}


def run_diamond(diamond: str, faa: Path, db: Path, tsv: Path, threads: int) -> None:
    if tsv.exists() and tsv.stat().st_mtime >= faa.stat().st_mtime:   # a finished search of the same queries
        return
    part = tsv.with_name(tsv.name + ".part")
    subprocess.run([diamond, "blastp", "-q", str(faa), "-d", str(db), "-o", str(part), "--sensitive",
                    "-k", str(TOP_N), "-e", EVALUE, "-p", str(threads), "--quiet",
                    "-f", "6", "qseqid", "sseqid", "pident", "bitscore", "stitle"], check=True)
    part.replace(tsv)


def parse_input(spec: str) -> tuple[str, Path]:
    label, sep, path = spec.partition("=")
    if not sep or not label or "|" in label:
        raise SystemExit(f"--input wants LABEL=PATH with no '|' in LABEL: {spec!r}")
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"--input path not found: {p}")
    return label, p


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--input", action="append", required=True, metavar="LABEL=PATH",
                    help="strain label and its antiSMASH zip, region GenBank file or folder; repeat per genome")
    ap.add_argument("--swissprot", type=Path, required=True, help="Swiss-Prot DIAMOND database (.dmnd)")
    ap.add_argument("--mibig-proteins", type=Path, required=True,
                    help="folder holding mibig_proteins.dmnd and mibig_proteins.tsv")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--skip-named", type=Path, nargs="*", default=[],
                    help="gene-name tables (NCBI first) whose genes are not searched again")
    ap.add_argument("--diamond", default="diamond", help="DIAMOND executable (default: diamond on PATH)")
    ap.add_argument("--threads", type=int, default=4)
    a = ap.parse_args(argv)

    diamond = shutil.which(a.diamond)
    mibig_db, mibig_tsv = a.mibig_proteins / "mibig_proteins.dmnd", a.mibig_proteins / "mibig_proteins.tsv"
    missing = [n for n, ok in (("DIAMOND", diamond), ("Swiss-Prot database", a.swissprot.is_file()),
                               ("MIBiG protein set", mibig_db.is_file() and mibig_tsv.is_file())) if not ok]
    if missing:
        emit("not run: no " + ", no ".join(missing), file=sys.stderr)
        return 2
    inputs = [parse_input(s) for s in a.input]
    labels = [lab for lab, _ in inputs]
    if len(set(labels)) != len(labels):
        raise SystemExit("each --input LABEL must be distinct")
    a.out.mkdir(parents=True, exist_ok=True)

    genes, total, skipped = {}, {}, {}
    for label, path in inputs:
        cds = region_cds(path)
        skip = already_named(a.skip_named, label, cds)
        total[label], skipped[label] = len(cds), len(skip)
        for tag, (stem, aa) in cds.items():
            if tag not in skip:
                genes[(label, tag)] = (stem, aa)
    faa = a.out / "QUERIES.faa"
    text = "".join(f">{lab}|{tag}\n{aa}\n" for (lab, tag), (_, aa) in genes.items())
    if not faa.exists() or faa.read_text() != text:   # unchanged queries keep their finished searches
        faa.write_text(text)

    mibig_products = {}
    with open(mibig_tsv, newline="") as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            mibig_products[r["id"]] = (r.get("product") or "").strip()
    hits_by_db = {}
    for db, path in (("Swiss-Prot", a.swissprot), ("MIBiG", mibig_db)):
        tsv = a.out / f"DIAMOND_{db.replace('-', '')}.tsv"
        if genes:
            run_diamond(diamond, faa, path, tsv, a.threads)
            hits_by_db[db] = read_hits(tsv, db, mibig_products)

    rows = [r for (lab, tag), (stem, aa) in genes.items() if (r := name_row(lab, tag, stem, aa, hits_by_db))]
    with open(a.out / "GENE_LOCAL_NAMES.tsv", "w", newline="") as fh:
        w = SafeDictWriter(fh, fieldnames=COLUMNS, delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    named = collections.Counter(r["strain"] for r in rows)
    searched = collections.Counter(lab for lab, _ in genes)
    lines = ["| Strain | Region CDS | Named before | Searched here | Named here | Still unnamed |",
             "|---|--:|--:|--:|--:|--:|"]
    lines += [f"| {lab} | {total[lab]} | {skipped[lab]} | {searched[lab]} | {named[lab]} | {searched[lab] - named[lab]} |"
              for lab in labels]
    (a.out / "GENE_LOCAL_NAMES_COUNTS.md").write_text("\n".join(lines) + "\n")
    emit("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
