#!/usr/bin/env python3
"""tools/pks_piece_map.py -- where along each large reference PKS protein do one genome's protein pieces sit?

WHY THIS EXISTS
    A modular PKS repeats near-identical modules, so a short-read assembly breaks a 30 kb gene into contig-length
    pieces. A check of one draft isolate against the nystatin-like PKS (MIBiG BGC0000116) mapped every piece
    onto the reference's antiSMASH modules and found the pieces tiling each protein end to end, in reference order,
    with gaps only at contig ends. That map was made outside the bundle; this tool carries it in, with a call that says
    when the order of the pieces can and cannot be read from the matches.

INPUT
    --reference-gbk F   a reference cluster GenBank carrying antiSMASH aSDomain / aSModule features (a MIBiG record).
    --genome G          the strain's antiSMASH result ZIP (its whole-genome GenBank) or a whole-genome .gbk.
    --label S           the strain label written in the outputs.

METHOD
    Reference proteins: every CDS /translation of at least --min-ref-length (1,500) aa. Modules: the aSModule features,
    each spanning its domains' protein_start..protein_end on that protein. Genome proteins: every CDS /translation of the
    whole-genome GenBank, with contig, contig length and coordinates.
    DIAMOND blastp, reference proteins as queries, genome proteins as the database (FASTA): --more-sensitive
    --evalue 1e-10 --max-target-seqs 0 --max-hsps 0 (every HSP). A piece is one HSP at >= --min-identity (85) %.
    Lower-identity hits are usually the genome's other PKS modules matching by family resemblance; they are left out of
    the map, but the best identity of any HSP per module is still reported.
    Per reference protein, pieces in reference order. Call:
      TILED        consecutive pieces overlap by <= --max-overlap (10) aa and none lies inside another: the order of the
                   pieces along the gene can be read from the matches.
      OVERLAPPING  otherwise: pieces match several places (module resemblance); the order cannot be read from the
                   matches. Use tools/ks_module_placement.py (KS phylogeny against the reference modules).
      NO_PIECES    no HSP at the identity threshold.
    Gaps (reference stretches with no piece) are listed with whether the pieces on each side end within 100 bp of a
    contig end. A contig carrying the end of one reference protein and the start of the next is listed as a junction.

OUTPUT (--out DIR, must not exist)
    PKS_PIECES.tsv (one row per piece), PKS_PIECE_MAP.tsv (one row per reference module), PKS_PROTEIN_CALLS.tsv,
    PKS_GAPS.tsv, PKS_JUNCTIONS.tsv, PKS_PIECE_MAP.txt (text tracks, 100 columns per protein), RECEIPT.json.

Homology and assembly position only: no contigs are joined, and no claim that the pieces form one locus or that the
strain makes the compound. Long reads or PCR across the breaks test linkage.
Refusals (exit 2): a missing input, no whole-genome GenBank, no reference protein >= the length cut, no aSModule
features, DIAMOND missing (never replaced), --out existing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
from mamey._gbk_shim import parse_genbank_text  # noqa: E402
from mamey.ref_completion import whole_genome_gbk_name  # noqa: E402
try:  # CSV formula-cell guard, as every tools/ writer (tests/test_410_tools_csv_writer_coverage.py)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

__version__ = "1.0.0"
_LOG = logging.getLogger("pks_piece_map")   # operator messages go through logging (repo_health print_calls)
EDGE_BP = 100
MODULE_CHARS = "123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


class Refusal(Exception):
    pass


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def q1(f, key, default=""):
    v = f.qualifiers.get(key)
    return v[0] if v else default


def genome_text(path):
    if str(path).endswith(".zip"):
        with zipfile.ZipFile(path) as zf:
            name = whole_genome_gbk_name(zf)
            if not name:
                raise Refusal(f"no whole-genome GenBank in {path}")
            return zf.read(name).decode("utf-8", "replace"), name
    return Path(path).read_text(encoding="utf-8", errors="replace"), os.path.basename(path)


def reference_model(path, min_len):
    proteins, domains, modules = {}, {}, defaultdict(list)
    records = parse_genbank_text(Path(path).read_text(encoding="utf-8", errors="replace"))
    feats = [f for r in records for f in r.features]
    for f in feats:
        if f.type == "CDS":
            aa = q1(f, "translation").replace(" ", "")
            if len(aa) >= min_len:
                name = q1(f, "gene") or q1(f, "locus_tag") or q1(f, "protein_id")
                proteins[name] = dict(aa=aa, locus_tag=q1(f, "locus_tag"), gene=q1(f, "gene"), protein_id=q1(f, "protein_id"))
        elif f.type == "aSDomain" and q1(f, "protein_start"):
            domains[q1(f, "domain_id")] = (q1(f, "locus_tag"), int(q1(f, "protein_start")) + 1, int(q1(f, "protein_end")), q1(f, "aSDomain"))
    tag_to_name = {}
    for name, p in proteins.items():
        for k in (p["locus_tag"], p["gene"], name):
            if k: tag_to_name[k] = name
    for f in feats:
        if f.type != "aSModule":
            continue
        ds = [domains[d] for d in f.qualifiers.get("domains", []) if d in domains]
        if ds and ds[0][0] in tag_to_name:
            ds.sort(key=lambda d: d[1])
            modules[tag_to_name[ds[0][0]]].append(dict(start=ds[0][1], end=max(d[2] for d in ds),
                                                       domains="-".join(d[3].replace("PKS_", "") for d in ds),
                                                       complete="yes" if "complete" in f.qualifiers else "no"))
    for name in modules:
        modules[name].sort(key=lambda m: m["start"])
    return proteins, modules


def genome_proteins(text):
    out = {}
    for rec in parse_genbank_text(text):
        L = len(rec.seq)
        for i, f in enumerate(x for x in rec.features if x.type == "CDS"):
            aa = q1(f, "translation").replace(" ", "")
            if not aa:
                continue
            tag = q1(f, "locus_tag") or q1(f, "protein_id") or f"cds{i}"
            out[f"P{len(out) + 1:06d}"] = dict(aa=aa, locus_tag=tag, contig=rec.id, contig_len=L, start=f.location.start + 1,
                                               end=f.location.end, strand="+" if f.location.strand == 1 else "-",
                                               to_start=f.location.start, to_end=L - f.location.end)
    return out


def union(iv):
    iv = sorted(iv); tot = 0
    if not iv:
        return 0
    cs, ce = iv[0]
    for a, b in iv[1:]:
        if a > ce + 1: tot += ce - cs + 1; cs, ce = a, b
        else: ce = max(ce, b)
    return tot + ce - cs + 1


def write_tsv(path, rows, cols):
    with open(path, "w", newline="") as fh:
        w = _SafeDictWriter(fh, fieldnames=cols, delimiter="\t", lineterminator="\n", extrasaction="ignore")
        w.writeheader(); w.writerows(rows)


def call_protein(pieces, max_overlap):
    if not pieces:
        return "NO_PIECES", 0
    worst = 0
    for a, b in zip(pieces, pieces[1:]):
        if b["ref_end"] <= a["ref_end"]:
            return "OVERLAPPING", max(worst, b["ref_end"] - b["ref_start"] + 1)
        worst = max(worst, a["ref_end"] - b["ref_start"] + 1)
    return ("TILED" if worst <= max_overlap else "OVERLAPPING"), max(worst, 0)


def run(a):
    for p in (a.reference_gbk, a.genome):
        if not os.path.isfile(p):
            raise Refusal(f"input missing: {p}")
    if os.path.exists(a.out):
        raise Refusal(f"--out exists: {a.out}")
    dmd = a.diamond or shutil.which("diamond")
    if not dmd or not os.path.isfile(dmd):
        raise Refusal("DIAMOND not found (--diamond or PATH); it is never replaced")
    proteins, modules = reference_model(a.reference_gbk, a.min_ref_length)
    if not proteins:
        raise Refusal(f"no reference CDS of >= {a.min_ref_length} aa in {a.reference_gbk}")
    if not any(modules.values()):
        raise Refusal("the reference GenBank has no aSModule features on its large proteins (antiSMASH annotation needed)")
    text, member = genome_text(a.genome)
    gp = genome_proteins(text)
    if not gp:
        raise Refusal("no CDS translations in the genome GenBank")
    os.makedirs(a.out)
    work = tempfile.mkdtemp(prefix="pks-piece-map-", dir=a.out)
    qf, df = os.path.join(work, "ref.faa"), os.path.join(work, "genome.faa")
    with open(qf, "w") as fh:
        fh.writelines(f">{n}\n{p['aa']}\n" for n, p in proteins.items())
    with open(df, "w") as fh:
        fh.writelines(f">{i}\n{p['aa']}\n" for i, p in gp.items())
    cmd = [dmd, "blastp", "-q", qf, "-d", df, "--more-sensitive", "--evalue", "1e-10", "--max-target-seqs", "0", "--max-hsps", "0",
           "--threads", str(a.threads), "--quiet", "--outfmt", "6", "qseqid", "sseqid", "pident", "length", "qstart", "qend",
           "sstart", "send", "evalue", "bitscore"]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise Refusal(f"DIAMOND failed (rc {p.returncode}): {p.stderr.strip()[:300]}")
    version = subprocess.run([dmd, "version"], capture_output=True, text=True).stdout.strip()
    for x in (qf, df):
        os.remove(x)
    os.rmdir(work)
    pieces, best_any = defaultdict(list), defaultdict(float)
    for line in p.stdout.splitlines():
        q, s, pid, _ln, qs, qe, ss, se, ev, bs = line.split("\t")
        if q not in proteins or s not in gp:
            continue
        qs, qe, pid = int(qs), int(qe), float(pid)
        for i, m in enumerate(modules[q]):
            if qs <= m["end"] and qe >= m["start"]:
                best_any[(q, i)] = max(best_any[(q, i)], pid)
        if pid < a.min_identity:
            continue
        g = gp[s]
        pieces[q].append(dict(ref_protein=q, ref_len_aa=len(proteins[q]["aa"]), ref_start=qs, ref_end=qe, identity_pct=f"{pid:.1f}",
                              genome_locus_tag=g["locus_tag"], genome_aa_start=int(ss), genome_aa_end=int(se), genome_protein_len=len(g["aa"]),
                              contig=g["contig"], contig_len_bp=g["contig_len"], cds_start=g["start"], cds_end=g["end"], strand=g["strand"],
                              bp_to_contig_start=g["to_start"], bp_to_contig_end=g["to_end"],
                              at_contig_end="yes" if min(g["to_start"], g["to_end"]) <= EDGE_BP else "no"))
    prow, mrow, crow, grow, jrow = [], [], [], [], []
    txt = [f"{a.label} pieces along each large protein of {os.path.basename(a.reference_gbk)} (identity >= {a.min_identity:g} %); "
           "100 columns = whole reference protein", "'=' piece; module row: module number (1-9, then letters); '.' between modules", ""]
    for name in proteins:
        P = sorted(pieces[name], key=lambda x: (x["ref_start"], -x["ref_end"])); L = len(proteins[name]["aa"])
        col = lambda x: min(99, (x - 1) * 100 // L)
        call, worst = call_protein(P, a.max_overlap)
        cov = union([(x["ref_start"], x["ref_end"]) for x in P])
        crow.append(dict(ref_protein=name, ref_len_aa=L, modules=len(modules[name]), pieces=len(P), contigs=len({x["contig"] for x in P}),
                         ref_covered_pct=f"{100 * cov / L:.0f}", largest_overlap_aa=worst, call=call,
                         note=("order of pieces readable from the matches" if call == "TILED" else
                               "order not readable from the matches; see tools/ks_module_placement.py" if call == "OVERLAPPING" else "")))
        ml = ["."] * 100
        for i, m in enumerate(modules[name]):
            for x in range(col(m["start"]), col(m["end"]) + 1): ml[x] = MODULE_CHARS[i % len(MODULE_CHARS)]
        txt += [f"{name}  ({L} aa; {len(modules[name])} modules; {len(P)} pieces; {call}; covered {100 * cov / L:.0f} %)",
                f"  {'modules':<34}|{''.join(ml)}|"]
        for n_, x in enumerate(P, 1):
            t = [" "] * 100
            for c in range(col(x["ref_start"]), col(x["ref_end"]) + 1): t[c] = "="
            x["piece"] = f"{name}.{n_}"; prow.append(x)
            txt.append(f"  {(x['contig'][:20] + ' ' + x['genome_locus_tag'][:9] + ' ' + x['identity_pct'] + '%'):<34}|{''.join(t)}|")
        txt.append("")
        end = 0; prev = None
        for x in P:
            if x["ref_start"] > end + 1:
                grow.append(dict(ref_protein=name, gap_start=end + 1, gap_end=x["ref_start"] - 1, gap_aa=x["ref_start"] - 1 - end,
                                 piece_before=prev["piece"] if prev else "", before_at_contig_end=prev["at_contig_end"] if prev else "",
                                 piece_after=x["piece"], after_at_contig_end=x["at_contig_end"]))
            if x["ref_end"] > end: end, prev = x["ref_end"], x
        if P and end < L:
            grow.append(dict(ref_protein=name, gap_start=end + 1, gap_end=L, gap_aa=L - end, piece_before=prev["piece"],
                             before_at_contig_end=prev["at_contig_end"], piece_after="", after_at_contig_end=""))
        for i, m in enumerate(modules[name]):
            ov = [x for x in P if x["ref_start"] <= m["end"] and x["ref_end"] >= m["start"]]
            mc = union([(max(x["ref_start"], m["start"]), min(x["ref_end"], m["end"])) for x in ov])
            mrow.append(dict(ref_protein=name, module=i + 1, ref_aa_start=m["start"], ref_aa_end=m["end"], domains=m["domains"],
                             antismash_complete=m["complete"], module_covered_pct=f"{100 * mc / (m['end'] - m['start'] + 1):.0f}",
                             n_pieces=len(ov), contigs=len({x["contig"] for x in ov}),
                             pieces="; ".join(f"{x['piece']} {x['contig']} {x['genome_locus_tag']} {x['identity_pct']}%" for x in ov),
                             best_identity_any_hsp_pct=f"{best_any[(name, i)]:.1f}"))
    names = list(proteins)
    by_contig = defaultdict(set)
    for x in prow:
        by_contig[x["contig"]].add(x["ref_protein"])
    for c, prots in sorted(by_contig.items()):
        if len(prots) > 1:
            jrow.append(dict(contig=c, reference_proteins=" + ".join(sorted(prots, key=names.index)),
                             pieces="; ".join(x["piece"] for x in prow if x["contig"] == c)))
    PCOLS = ["piece", "ref_protein", "ref_len_aa", "ref_start", "ref_end", "identity_pct", "genome_locus_tag", "genome_aa_start",
             "genome_aa_end", "genome_protein_len", "contig", "contig_len_bp", "cds_start", "cds_end", "strand", "bp_to_contig_start",
             "bp_to_contig_end", "at_contig_end"]
    write_tsv(os.path.join(a.out, "PKS_PIECES.tsv"), prow, PCOLS)
    write_tsv(os.path.join(a.out, "PKS_PIECE_MAP.tsv"), mrow, list(mrow[0]) if mrow else ["ref_protein"])
    write_tsv(os.path.join(a.out, "PKS_PROTEIN_CALLS.tsv"), crow, list(crow[0]))
    write_tsv(os.path.join(a.out, "PKS_GAPS.tsv"), grow, ["ref_protein", "gap_start", "gap_end", "gap_aa", "piece_before",
                                                          "before_at_contig_end", "piece_after", "after_at_contig_end"])
    write_tsv(os.path.join(a.out, "PKS_JUNCTIONS.tsv"), jrow, ["contig", "reference_proteins", "pieces"])
    with open(os.path.join(a.out, "PKS_PIECE_MAP.txt"), "w") as fh:
        fh.write("\n".join(txt) + "\n")
    receipt = dict(tool="pks_piece_map", version=__version__, utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   label=a.label, reference=dict(path=a.reference_gbk, sha256=sha256(a.reference_gbk), proteins=len(proteins),
                   modules=sum(len(v) for v in modules.values())), genome=dict(path=a.genome, sha256=sha256(a.genome), member=member,
                   proteins=len(gp)), diamond=version, rule=dict(min_identity=a.min_identity, min_ref_length=a.min_ref_length,
                   max_overlap=a.max_overlap, evalue=1e-10, mode="--more-sensitive --max-hsps 0", contig_end_bp=EDGE_BP),
                   calls={r["ref_protein"]: r["call"] for r in crow}, pieces=len(prow))
    with open(os.path.join(a.out, "RECEIPT.json"), "w") as fh:
        json.dump(receipt, fh, indent=1)
    return receipt


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--reference-gbk", required=True); ap.add_argument("--genome", required=True)
    ap.add_argument("--label", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--diamond"); ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--min-identity", type=float, default=85.0); ap.add_argument("--min-ref-length", type=int, default=1500)
    ap.add_argument("--max-overlap", type=int, default=10)
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        r = run(a)
    except Refusal as exc:
        _LOG.error("REFUSED: %s", exc)
        return 2
    _LOG.info("%s: %d pieces; %s -> %s", a.label, r["pieces"], ", ".join(f"{k} {v}" for k, v in r["calls"].items()), a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
