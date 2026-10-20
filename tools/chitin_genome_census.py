#!/usr/bin/env python3
"""tools/chitin_genome_census.py -- whole-genome chitin/GlcNAc domain census, one row per genome.

WHY THIS EXISTS
    The bee paper's chitin panels (K01/K03) and the moss census of 13 Oct 2026 were counted with a
    census() function that lived outside the bundle (a cohort script importing a QC helper). This
    tool carries that method into the bundle unchanged, so a chitin count in a paper is produced by a
    sealed tool with its inputs as arguments.

METHOD (identical to the bee census)
    1. Proteins: every CDS /translation in the genome's whole-genome GenBank. For an antiSMASH result
       ZIP that is the largest .gbk that is not a per-region file and not the echoed input/ copy;
       a GenBank file can also be given directly. Translations are cleaned to letters, upper-cased,
       and a trailing stop removed.
    2. Search: HMMER `hmmsearch --cut_ga --tblout` against one HMM file holding exactly the 11 Pfam
       families below (each profile's own gathering threshold; no E-value is chosen here).
    3. Count: proteins per family (a protein hit by two families counts in both). The chitinolytic
       total is the sum of the 8 degradative/binding families. Glyco_hydro_16 is reported as
       fungal-glucan-active; Glyco_hydro_3 and Glucosamine_iso as catabolic context. Neither group
       is counted as chitinolytic capacity.

    Build the HMM from a local Pfam-A.hmm (never downloaded here):
        hmmfetch -f Pfam-A.hmm <(printf '%s\\n' PF02839 PF06483 PF08329 PF01182 PF00722 PF00704 \\
                                PF00182 PF00728 PF00933 PF03067 PF01522) > chitin_glcnac_11fam.hmm

CLAIM CEILING
    Domain presence is capacity, not activity, expression or an ecological claim. A zero means "not
    found in this assembly", never "absent from the organism"; pair counts with an assembly
    completeness measure before reading a zero. Judgment deferred.

REFUSALS
    A genome with no whole-genome GenBank or no CDS translations gets an error row with EMPTY counts
    (never 0) and the tool exits 2. An HMM file without exactly the 11 families, each with a GA line,
    is refused before any search.

Usage:
    chitin_genome_census.py --hmm chitin_glcnac_11fam.hmm --input STRAIN=antismash.zip [--input ...] --out census.tsv
    chitin_genome_census.py --hmm chitin_glcnac_11fam.hmm --manifest genomes.tsv --out census.tsv
        (manifest: tab-separated, columns strain_id and path; any other columns are copied to the output)
Writes <out> (TSV) and <out>.json (receipt: HMM sha256, HMMER version, rule, per-genome source sha256).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _console import emit  # noqa: E402
try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

TOOL_VERSION = "1.0.0"

DEGRADATIVE = ["Glyco_hydro_18", "Glyco_hydro_19", "Glyco_hydro_20", "CBM_5_12",
               "LPMO_10", "ChiC", "ChitinaseA_N", "Polysacc_deac_1"]
GLUCAN = ["Glyco_hydro_16"]
CONTEXT = ["Glyco_hydro_3", "Glucosamine_iso"]
ALL_FAMS = DEGRADATIVE + GLUCAN + CONTEXT
PFAM_ACC = {"CBM_5_12": "PF02839", "ChiC": "PF06483", "ChitinaseA_N": "PF08329",
            "Glucosamine_iso": "PF01182", "Glyco_hydro_16": "PF00722", "Glyco_hydro_18": "PF00704",
            "Glyco_hydro_19": "PF00182", "Glyco_hydro_20": "PF00728", "Glyco_hydro_3": "PF00933",
            "LPMO_10": "PF03067", "Polysacc_deac_1": "PF01522"}
MAX_LOCI = 20
RULE = ("Proteins = every CDS /translation of the whole-genome GenBank; hmmsearch --cut_ga --tblout "
        "against 11 Pfam families; count = proteins per family (a protein with two families counts in "
        "both); chitinolytic_domains_total = sum of the 8 degradative/binding families "
        f"({', '.join(DEGRADATIVE)}); Glyco_hydro_16, Glyco_hydro_3 and Glucosamine_iso are reported, "
        "not counted. Capacity only; a zero means not found in this assembly.")


class CensusInputError(RuntimeError):
    """Refuse instead of returning a count that could be read as a biological zero."""


# ---- input extraction (same logic as the bee census helper) -----------------------------------

def full_genome_gbk_member(zf: zipfile.ZipFile) -> str | None:
    """The whole-genome GenBank inside an antiSMASH result ZIP: the largest .gbk that is not a
    per-region file and not the echoed submission under input/."""
    best = None
    for n in zf.namelist():
        if not n.endswith(".gbk"):
            continue
        base = os.path.basename(n)
        if ".region" in base or n.startswith("input/") or "/input/" in n:
            continue
        info = zf.getinfo(n)
        if best is None or info.file_size > best[1]:
            best = (n, info.file_size)
    return best[0] if best else None


def parse_gbk(stream) -> tuple[list[int], list[tuple[str, str]]]:
    """Return (contig_lengths, [(locus_tag, protein_seq), ...]) from a GenBank stream.

    Only /translation blocks are read for protein sequence; contig lengths come from LOCUS lines.
    """
    lengths: list[int] = []
    prots: list[tuple[str, str]] = []
    locus = None
    trans: list[str] = []
    in_trans = False
    in_cds = False
    idx = 0

    def flush():
        nonlocal locus, trans, idx
        if trans:
            aa = re.sub(r"[^A-Za-z*]", "", "".join(trans)).upper().rstrip("*")
            if aa:
                idx += 1
                prots.append((locus or f"cds_{idx}", aa))
        locus, trans = None, []

    for raw in stream:
        line = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw
        if line.startswith("LOCUS"):
            parts = line.split()
            for i, p in enumerate(parts):
                if p == "bp" and i > 0:
                    try:
                        lengths.append(int(parts[i - 1]))
                    except ValueError:
                        break  # a non-numeric length field: no length is recorded for this hit
                    break
            continue
        if re.match(r"^     \S", line):
            if in_cds:
                flush()
            in_cds = line.startswith("     CDS ")
            in_trans = False
            continue
        if not in_cds or not line.startswith(" " * 21):
            continue
        s = line.strip()
        if s.startswith("/locus_tag="):
            locus = s.split("=", 1)[1].strip('"')
            continue
        if s.startswith("/translation="):
            body = s.split("=", 1)[1].lstrip('"')
            if body.endswith('"'):
                trans.append(body[:-1])
            else:
                trans.append(body)
                in_trans = True
            continue
        if in_trans:
            if s.endswith('"'):
                trans.append(s[:-1])
                in_trans = False
            else:
                trans.append(s)
    if in_cds:
        flush()
    return lengths, prots


def load_proteins(path: str) -> tuple[str, list[tuple[str, str]]]:
    """(GenBank member or file name, proteins) for an antiSMASH ZIP or a GenBank file."""
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as zf:
            member = full_genome_gbk_member(zf)
            if not member:
                raise CensusInputError("no whole-genome GenBank in the ZIP (only region or input/ files)")
            with zf.open(member) as fh:
                _, prots = parse_gbk(fh)
    else:
        member = os.path.basename(path)
        with open(path, "rb") as fh:
            _, prots = parse_gbk(fh)
    if not prots:
        raise CensusInputError("no CDS translations in the whole-genome GenBank")
    return member, prots


# ---- HMM and HMMER ------------------------------------------------------------------------------

def check_hmm(path: str) -> dict[str, str]:
    """Return {family: accession} after confirming the file holds exactly the 11 families, each with
    a GA line (needed by --cut_ga)."""
    names, accs, ga, cur = [], {}, set(), None
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith("NAME "):
                cur = line.split(None, 1)[1].strip()
                names.append(cur)
            elif line.startswith("ACC ") and cur:
                accs[cur] = line.split(None, 1)[1].strip()
            elif line.startswith("GA ") and cur:
                ga.add(cur)
    if sorted(names) != sorted(ALL_FAMS):
        missing = sorted(set(ALL_FAMS) - set(names))
        extra = sorted(set(names) - set(ALL_FAMS))
        dup = sorted({n for n in names if names.count(n) > 1})
        raise CensusInputError(f"HMM must hold exactly the 11 census families; missing={missing} "
                               f"extra={extra} duplicated={dup}")
    no_ga = sorted(set(ALL_FAMS) - ga)
    if no_ga:
        raise CensusInputError(f"HMM profiles without a GA line (needed by --cut_ga): {no_ga}")
    for fam, acc in accs.items():
        if not acc.startswith(PFAM_ACC[fam]):
            raise CensusInputError(f"{fam} has accession {acc}, expected {PFAM_ACC[fam]}.*")
    return accs


def hmmer_version(hmmsearch: str) -> str:
    r = subprocess.run([hmmsearch, "-h"], capture_output=True, text=True)
    m = re.search(r"HMMER\s+(\S+)", r.stdout)
    return m.group(1) if m else "unknown"


def search(hmmsearch: str, hmm: str, prots: list[tuple[str, str]], cpu: int) -> dict[str, list[str]]:
    """Run hmmsearch and return {family: [locus, ...]} (one entry per protein hit)."""
    hits: dict[str, list[str]] = {f: [] for f in ALL_FAMS}
    with tempfile.TemporaryDirectory(prefix="chitin_census_") as td:
        faa, tbl = os.path.join(td, "proteins.faa"), os.path.join(td, "hits.tbl")
        with open(faa, "w") as fh:
            for i, (lt, aa) in enumerate(prots):
                fh.write(f">{lt}_{i}\n{aa}\n")
        r = subprocess.run([hmmsearch, "--cut_ga", "--cpu", str(cpu), "--tblout", tbl, hmm, faa],
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        if r.returncode != 0:
            raise CensusInputError(f"hmmsearch failed (exit {r.returncode}): {r.stderr[:300]}")
        with open(tbl) as fh:
            for line in fh:
                if line.startswith("#"):
                    continue
                f = line.split()
                if len(f) > 2 and f[2] in hits:
                    hits[f[2]].append(re.sub(r"_\d+$", "", f[0]))
    return hits


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def census(strain: str, path: str, hmm: str, hmmsearch: str, cpu: int = 2) -> dict:
    rec = {"strain_id": strain, "source_path": path, "source_sha256": sha256(path)}
    try:
        member, prots = load_proteins(path)
        hits = search(hmmsearch, hmm, prots, cpu)
    except (CensusInputError, zipfile.BadZipFile, OSError) as exc:
        rec["error"] = str(exc)
        return rec
    rec["genbank_member"] = member
    rec["cds_searched"] = len(prots)
    for fam in ALL_FAMS:
        rec[fam] = len(hits[fam])
        rec[fam + "_loci"] = ";".join(hits[fam][:MAX_LOCI])
    rec["chitinolytic_domains_total"] = sum(rec[f] for f in DEGRADATIVE)
    rec["error"] = ""
    return rec


# ---- command line ---------------------------------------------------------------------------------

def read_inputs(pairs: list[str], manifest: str | None) -> tuple[list[dict], list[str]]:
    rows, extra_cols = [], []
    for p in pairs or []:
        if "=" not in p:
            raise CensusInputError(f"--input needs STRAIN=PATH, got {p!r}")
        s, path = p.split("=", 1)
        rows.append({"strain_id": s.strip(), "path": path.strip()})
    if manifest:
        with open(manifest, newline="") as fh:
            rd = csv.DictReader(fh, delimiter="\t")
            if not rd.fieldnames or not {"strain_id", "path"} <= set(rd.fieldnames):
                raise CensusInputError("manifest needs tab-separated columns strain_id and path")
            extra_cols = [c for c in rd.fieldnames if c not in ("strain_id", "path")]
            rows.extend(dict(r) for r in rd)
    if not rows:
        raise CensusInputError("no genomes given (use --input or --manifest)")
    ids = [r["strain_id"] for r in rows]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        raise CensusInputError(f"duplicate strain_id: {dup}")
    for r in rows:
        if not r["strain_id"] or not os.path.isfile(r["path"]):
            raise CensusInputError(f"missing strain_id or file: {r}")
    return rows, extra_cols


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--hmm", required=True, help="HMM file holding exactly the 11 census families")
    ap.add_argument("--input", action="append", metavar="STRAIN=PATH",
                    help="antiSMASH result ZIP or whole-genome GenBank; repeatable")
    ap.add_argument("--manifest", help="TSV with strain_id and path (+ any columns to carry through)")
    ap.add_argument("--out", required=True, help="output TSV file")
    ap.add_argument("--hmmsearch", default=shutil.which("hmmsearch"), help="hmmsearch binary")
    ap.add_argument("--cpu", type=int, default=2)
    a = ap.parse_args(argv)

    try:
        if not a.hmmsearch or not os.path.exists(a.hmmsearch):
            raise CensusInputError("hmmsearch not found; pass --hmmsearch (HMMER 3)")
        accs = check_hmm(a.hmm)
        inputs, extra_cols = read_inputs(a.input, a.manifest)
    except CensusInputError as exc:
        _report([f"REFUSED: {exc}"], failed=True)
        return 2

    rows, lines = [], []
    for r in inputs:
        rec = census(r["strain_id"], r["path"], a.hmm, a.hmmsearch, a.cpu)
        for c in extra_cols:
            rec[c] = r.get(c, "")
        rows.append(rec)
        lines.append(f"{rec['strain_id']}\tERROR\t{rec['error']}" if rec["error"] else
                     f"{rec['strain_id']}\tchitinolytic={rec['chitinolytic_domains_total']}\t"
                     f"cds={rec['cds_searched']}")

    cols = (["strain_id"] + extra_cols + ["chitinolytic_domains_total"] + ALL_FAMS +
            [f + "_loci" for f in ALL_FAMS] +
            ["cds_searched", "genbank_member", "source_path", "source_sha256", "error"])
    with open(a.out, "w", newline="") as fh:
        w = _SafeDictWriter(fh, fieldnames=cols, delimiter="\t", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    receipt = {
        "tool": "tools/chitin_genome_census.py", "tool_version": TOOL_VERSION,
        "computed_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hmm": os.path.abspath(a.hmm), "hmm_sha256": sha256(a.hmm), "hmm_accessions": accs,
        "hmmsearch": a.hmmsearch, "hmmer_version": hmmer_version(a.hmmsearch), "cpu": a.cpu,
        "rule": RULE, "families": {"degradative": DEGRADATIVE, "glucan": GLUCAN, "context": CONTEXT},
        "genomes": [{k: r.get(k, "") for k in ("strain_id", "source_path", "source_sha256",
                                                  "genbank_member", "cds_searched", "error")} for r in rows],
        "n_genomes": len(rows), "n_errors": sum(1 for r in rows if r["error"]),
    }
    with open(a.out + ".json", "w") as fh:
        json.dump(receipt, fh, indent=2)
    lines.append(f"wrote {a.out} ({len(rows)} genomes, {receipt['n_errors']} errors)")
    _report(lines, failed=bool(receipt["n_errors"]))
    return 2 if receipt["n_errors"] else 0


def _report(lines: list[str], failed: bool) -> None:
    """The tool's one terminal-emission site: refusals and per-genome errors go to stderr, results to stdout."""
    emit(*lines, sep="\n", file=sys.stderr if failed else sys.stdout)


if __name__ == "__main__":
    raise SystemExit(main())
