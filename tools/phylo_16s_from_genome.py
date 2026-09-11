"""Extract BLAST-supported candidate 16S spans with per-locus relative orientation.

HSP clustering is a heuristic. Orientation is relative to the selected reference
sequences, whose biological forward orientation must be established by the operator.
No motif-based orientation correction or strain/16S identity claim is made.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import logging
_LOG = logging.getLogger(__name__)
import _phylo16s as _p16

DB = _p16.refseq_16s_blastdb()
read_fasta = _p16.read_fasta


def rc(s):
    return s.translate(str.maketrans("ACGTRYSWKMBDHVNacgtryswkmbdhvn",
                                    "TGCAYRSWMKVHDBNtgcayrswmkvhdbn"))[::-1]


def merge(spans, gap=100):
    """Heuristically cluster nearby HSP spans; this does not locate gene boundaries."""
    out = []
    for s, e in sorted(spans):
        if out and s <= out[-1][1] + gap:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out


def extract(path, min_len, best, threads, evidence=None):
    if min_len <= 0 or threads <= 0:
        raise ValueError("min_len and threads must be positive")
    seqs = {h.split()[0]: s for h, s in read_fasta(path).items()}
    wd = _p16.space_free_workdir("phylo16s_extract_")
    try:
        p = _p16.run_checked(
            [_p16.blast_bin("blastn"), "-task", "blastn", "-db", _p16.stage_blastdb(DB, wd),
             "-query", _p16.stage_file(path, wd, "query.fna"),
             "-outfmt", "6 qseqid qstart qend sstart send pident length sseqid",
             "-max_target_seqs", "5", "-evalue", "1e-50", "-num_threads", str(threads)],
            "blastn (candidate 16S extraction)")
    finally:
        shutil.rmtree(wd)
    hits = {}
    for line in p.stdout.splitlines():
        f = line.split("\t")
        if len(f) != 8 or f[0] not in seqs:
            raise ValueError("malformed or unbound BLAST extraction row")
        q, qs, qe, ss, se = f[0], *map(int, f[1:5])
        pid, length = float(f[5]), int(f[6])
        if not math.isfinite(pid) or not 0 <= pid <= 100 or min(qs, qe, ss, se, length) <= 0:
            raise ValueError("invalid BLAST coordinates or identity")
        if max(qs, qe) > len(seqs[q]) or qs == qe or ss == se or not f[7]:
            raise ValueError("unsupported or out-of-bounds HSP")
        reverse = (qe - qs) * (se - ss) < 0
        hits.setdefault(q, []).append((min(qs, qe), max(qs, qe), reverse, pid, f[7], length))
    out, events = [], []
    for name, hsps in sorted(hits.items()):
        for lo, hi in merge([(h[0], h[1]) for h in hsps]):
            local = [h for h in hsps if h[0] >= lo and h[1] <= hi]
            orientations = {h[2] for h in local}
            if len(orientations) != 1:
                raise ValueError(f"orientation hold: conflicting HSP directions at {name}:{lo}-{hi}")
            if hi - lo + 1 < min_len:
                continue
            reverse = next(iter(orientations))
            sub = seqs[name][lo - 1:hi]
            if reverse:
                sub = rc(sub)
            top = sorted(local, key=lambda h: (-h[3], -h[5], h[4], h[0], h[1]))[0]
            out.append((name, lo, hi, len(sub), top[3], top[4], sub))
            events.append(dict(contig=name, start=lo, end=hi,
                               orientation_relative_to_reference="reverse" if reverse else "forward",
                               hsp_rows=local, span_basis="HSP cluster; gap at most 100 nt"))
    out.sort(key=lambda t: (-t[3], t[0], t[1], t[2]))
    if best:
        out = out[:1]
    if evidence is not None:
        keys = {(x[0], x[1], x[2]) for x in out}
        evidence.extend(x for x in events if (x['contig'], x['start'], x['end']) in keys)
    return out


def main(argv=None):
    global DB
    ap = argparse.ArgumentParser(allow_abbrev=False)
    ap.add_argument("genomes", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--blastdb", default=None)
    ap.add_argument("--min-len", type=int, default=1200)
    ap.add_argument("--best", action="store_true", help="longest candidate span per genome")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--label", default="")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    if a.min_len <= 0 or a.threads <= 0 or re.search(r"[^A-Za-z0-9_.-]", a.label):
        ap.error("positive limits and a filename-safe label are required")
    output = _p16.require_new_output(a.out)
    receipt = _p16.require_new_output(str(output) + ".receipt.json")
    inputs = [Path(g).resolve(strict=True) for g in a.genomes]
    if len(set(inputs)) != len(inputs):
        ap.error("duplicate genome input")
    input_hashes = [_p16.sha256_file(path) for path in inputs]
    if len(set(input_hashes)) != len(input_hashes):
        ap.error('duplicate genome content identity')
    for path in inputs:
        read_fasta(path)
    DB = _p16.refseq_16s_blastdb(a.blastdb)
    if a.dry_run:
        _LOG.info(f"DRY_RUN: validated {len(inputs)} FASTA inputs; BLAST not run; no outputs written")
        return 0
    reference_files = sorted(p for p in Path(DB).parent.glob(Path(DB).name + '.*') if p.is_file())
    if not reference_files:
        raise ValueError('reference database members unavailable for provenance')
    reference_members = [dict(name=p.name,sha256=_p16.sha256_file(p)) for p in reference_files]
    fasta, records = [], []
    for path, digest in zip(inputs,input_hashes):
        events = []
        got = extract(path, a.min_len, a.best, a.threads, events)
        if _p16.sha256_file(path) != digest:
            raise ValueError('genome input changed during extraction')
        for row in got:
            name, lo, hi, ln, pid, top, seq = row
            tag = f"{a.label}GENOME_{digest}|{name}|{lo}-{hi}"
            fasta.append(f">{tag} candidate_16S_span\n{seq}\n")
        records.append(dict(input_sha256=digest, input_name=path.name, candidates=events))
    text = "".join(fasta)
    details = dict(status="CANDIDATE_SPANS_NOT_GENE_VALIDATED", records=records,
                   fasta_sha256=hashlib.sha256(text.encode()).hexdigest(),
                   parameters=dict(min_len=a.min_len, best=a.best, threads=a.threads),
                   reference_members=reference_members)
    for path, member in zip(reference_files,reference_members):
        if _p16.sha256_file(path) != member['sha256']:
            raise ValueError('reference database changed during extraction')
    with output.open("x") as handle:
        handle.write(text)
    with receipt.open("x") as handle:
        json.dump(details, handle, indent=2)
    _LOG.info(f"{len(fasta)} candidate spans written; receipt {receipt}")
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    sys.exit(main())
