#!/usr/bin/env python3
"""locus_reading_pages.py: one locus-reading page per antiSMASH region, every gene with every evidence layer.

Reads only. Writes Markdown into a new output folder: one page per BGC, one combined file per strain and a build log.
Render a page or a combined file with Tools/render_md_pdf.sh (pandoc to HTML, then headless Chrome).

  python3 tools/locus_reading_pages.py --out <new folder> --package <STRAIN>=<package dir> [--package ...]
      (--ledger <ledger.tsv[.gz]> | --ledger-dir <dir of <strain>.tsv>)
      [--gene-table-inventory <INVENTORY.tsv> --gene-table-root <dir>] [--gecco <clusters.tsv>]
      [--mibig-json <dir of <BGC>.json>] [--mibig-proteins <dir with mibig_proteins.dmnd and .tsv>]
      [--proteomes <dir of <strain>.faa> --pfam <Pfam-A.hmm> --hmmsearch <bin> --diamond <bin>]
      [--assessments <dir>] [--refs <dir>] [--strains A,B] [--bgc BGC007] [--skip STRAIN=REASON] [--threads 4]

Inputs, one source each:
  regions and identity      the strain's Mamey package *_2_inventory.csv (BGC_ID, Contig, Region, Products, Boundary,
                            Length_kb, KCB_top, KCB_proteins)
  known-cluster convergence the package's *_3_mibig_convergence.csv
  every gene's layers       a gene annotation ledger: one row per CDS with the columns in LEDGER_COLUMNS
  gene tables and maps      a gene-table inventory (one row per pair; its png column is resolved against
                            --gene-table-root) and, beside each pair's map, gap_rescue.tsv and gap_rescue_split_genes.tsv
  GECCO clusters            a table with strain, contig_full, type, start, end, average_p, relation; contig_full is
                            matched to the ledger by the same exact-then-unique NODE_n_length_L rule as the gene tables;
                            an ambiguous name is a hold only when the cluster overlaps the page's region, else skipped
  MIBiG entries             MIBiG JSON records, one per BGC, for compound names, producer and recorded bioactivity
  hand assessments          <assessments>/<stem>.md, used in place of the automatic summary when present
  checked literature        <refs>/<stem>.tsv (pmid, citation, doi, reports), used when present
where <stem> is <strain>_<NODEn>_r<###>_<BGC>.

Rows shown per BGC: every CDS of the region, 3 flanking CDS on each side, and every CDS on any contig the gene table or
the split check points to (the whole contig up to 20 kb; otherwise the matched CDS and 2 on each side). Those contigs are
matched first to exact ledger contig names; NODE_n_length_L fallback is allowed only when unique, because some tables
rewrite the coverage part of SPAdes names. Ambiguous aliases remain an identity hold.
A protein the ledger never searched (L2b_bind NOT_SEARCHED, or mibig_queried "no ...") is searched for the pages, once per
strain: Pfam-A with hmmsearch --cut_ga, and MIBiG proteins with DIAMOND blastp --more-sensitive -k 25 -e 1e-5 (best bit
score). Results are cached in <out>/_page_searches/<strain>/ and marked † on the page; a cache made for a different
protein set, sequence, source database, tool or options is rebuilt. Only a hash-bound completion receipt admits reuse;
legacy or partial files are unverified and retained; new attempts use separate digest-keyed generations. Build attempts
  publish RUNNING/FAILED/VERIFIED (or NO_SEARCH_CONTEXT) separately, retaining prior receipts and binding only this attempt
  to its explicit output files. Fixed databases are
  hashed once per build and verified fully at its end. Without a proteome, Pfam file,
hmmsearch or DIAMOND, those cells read "not searched †" and the footnote says why.
Each gene-table bullet has a gene-kind line: the reference genes present in the core by MIBiG gene kind (gap_rescue.tsv
reference_gene_kind), and the biosynthetic count (core and additional), flagged when a STRONG table has fewer than half of
those in the core. A second known-cluster table counts the region's genes by the MIBiG cluster of each gene's best MIBiG
protein (ledger mibig_best_hit), because the KnownClusterBlast-based convergence table can miss clusters its database lacks.
Without a hand assessment, a page carries an automatic evidence summary: counts and calls only, no interpretation.

Rules: an output folder that already holds a build (BUILD_LOG.tsv) is refused, and so is an existing page (versions are
never overwritten); nothing is invented (a blank layer is marked ‡ or "no hit under the filters", never "none"); wording
stays at class level. A MIBiG or KnownClusterBlast match is similarity, not compound identity; a detected cluster is
capacity, not production.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path

try:  # CSV formula-cell guard, as every tools/ writer (tests/test_410_tools_csv_writer_coverage.py)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # noqa: F401
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # noqa: F401
from mamey.path_safety import assert_output_outside_bundle  # noqa: E402

from mamey.logging_setup import get_logger as _get_logger

_OUT = _get_logger(__name__)

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))
LEDGER_COLUMNS = ["strain", "locus_tag", "contig", "start", "end", "strand", "region", "bgc", "aa", "as_gene_function",
                  "L2b_bind", "L2b_pfam_domains", "mibig_best_hit", "mibig_gene", "mibig_identity", "mibig_queried",
                  "gene_map_rows", "card_family", "LG_gene_avg_p", "L5_status", "L5_ref", "L5_ref_is_SID", "L5_product",
                  "L5_pident", "L5_region_call", "L5_ref_region"]
CAVEAT = ("Locus reading. Every number comes from the named file. A MIBiG or KnownClusterBlast match is similarity, not "
          "compound identity; a detected cluster is capacity, not production. Judgment deferred.\n")
AUTO_HEAD = ("*Automatic evidence summary: counts and calls only. No hand assessment has been written for this locus yet; "
             "judgment deferred.*\n")
DAGGER_SEARCHED = ("† Searched for this page (the gene lies outside any antiSMASH region): Pfam-A, hmmsearch --cut_ga; MIBiG "
                   "proteins, DIAMOND blastp --more-sensitive, E ≤ 1e-5, best bit score.\n")
DOUBLE_DAGGER = "‡ Not yet searched against the reference genomes.\n"

short = lambda c: re.sub(r"_length_(\d+)_cov_([\d.]+)", lambda m: f" ({int(m.group(1)):,} bp, {float(m.group(2)):.0f}×)", c)
node_tag = lambda c: (re.match(r"(NODE_\d+)", c).group(1).replace("_", "") if c.startswith("NODE_")
                      else re.sub(r"[^A-Za-z0-9]", "", c)[:20])
clen = lambda c: int(m.group(1)) if (m := re.search(r"_length_(\d+)_", c)) else 10 ** 9


class MibigIndex:
    """Compound names, producer and recorded bioactivity per MIBiG accession, read from its JSON record."""

    def __init__(self, folder):
        self.folder = Path(folder) if folder else None
        self._cache = {}

    def __call__(self, acc):
        if acc in self._cache:
            return self._cache[acc]
        out = {"names": "?", "acts": [], "taxon": ""}
        p = self.folder / f"{acc}.json" if self.folder else None
        if p and p.exists():
            d = json.load(open(p))
            acts = []
            for x in d.get("compounds", []):
                for b in x.get("bioactivities", []):
                    n = b.get("name")
                    n = n.get("activity") if isinstance(n, dict) else n
                    acts.append(str(n) + ("" if b.get("observed", True) else " (not observed)"))
            out = {"names": "; ".join(x.get("name", "") for x in d.get("compounds", [])), "acts": sorted(set(acts)),
                   "taxon": d.get("taxonomy", {}).get("name", "")}
        self._cache[acc] = out
        return out


def ledger_by_strain(ledger, ledger_dir, cache):
    """Use --ledger-dir directly, or return a fresh retained split of the current --ledger."""
    if ledger_dir:
        return Path(ledger_dir)
    from contextlib import ExitStack

    if cache.is_symlink():
        raise ValueError("PAGE_LEDGER_CACHE_PATH_REFUSED")
    cache.mkdir(parents=True, exist_ok=True)
    # A later --bgc append may supply a ledger that omits an earlier strain.
    # Never let old per-strain files stand in for rows absent from this input.
    split = Path(tempfile.mkdtemp(prefix="split-", dir=cache))
    opener = gzip.open if str(ledger).endswith(".gz") else open
    fhs = {}
    with ExitStack() as outputs, opener(ledger, "rt") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            s = r.get("strain")
            if (not isinstance(s, str) or not s or s != s.strip() or s.startswith(".")
                    or any(c in s for c in ("/", "\\", "\x00", ":"))
                    or any(ord(c) < 32 or ord(c) == 127 for c in s) or Path(s).is_absolute()):
                raise ValueError(f"PAGE_LEDGER_STRAIN_PATH_REFUSED: {s!r}")
            if s not in fhs:
                fh = outputs.enter_context(open(split / f"{s}.tsv", "w", newline=""))
                w = _SafeWriter(fh, delimiter="\t", lineterminator="\n")
                w.writerow(LEDGER_COLUMNS)
                fhs[s] = (fh, w)
            fhs[s][1].writerow([r.get(k, "") for k in LEDGER_COLUMNS])
    return split


def _contig_candidates(ledger_contigs):
    """-> a function from a contig name in a supplied table to the ledger contigs it can mean: the exact name when the
    ledger has it, else every ledger contig with the same NODE_n_length_L alias (some tables rewrite the coverage
    suffix of SPAdes names; GECCO writes cov_9.12345 for cov_9.012345), else none."""
    key = lambda c: m.group(1) if (m := re.match(r"(NODE_\d+_length_\d+)_", c)) else c
    byk = defaultdict(list)
    for c in ledger_contigs:
        byk[key(c)].append(c)
    known = set(ledger_contigs)
    return lambda c: [c] if c in known else byk.get(key(c), [])


def contig_resolver(ledger_contigs):
    """-> a function from a contig name in a supplied table to the ledger's contig name.

    Exact full contig identity wins; the NODE_n_length_L alias is used when it names exactly one ledger contig. An alias
    naming two ledger contigs is an identity hold. A name with no match is returned unchanged."""
    candidates = _contig_candidates(list(ledger_contigs))

    def resolve(c):
        cs = candidates(c)
        if len(cs) > 1:
            raise ValueError(f"LOCUS_PAGE_CONTIG_IDENTITY_HOLD: {c} matches {', '.join(sorted(cs))}")
        return cs[0] if cs else c
    return resolve


def _overlaps(g, lo, hi) -> bool:
    """True when a GECCO row's span meets [lo, hi], or when its span cannot be read (it cannot be ruled out)."""
    try:
        return int(g["start"]) <= hi and int(g["end"]) >= lo
    except (KeyError, TypeError, ValueError):
        return True


def page_gecco(gecco_all, strain, order, ledger_contigs, region):
    """The GECCO rows of one page: this strain's clusters on the page's contigs (`order`), matched by _contig_candidates.
    Each returned row is a copy whose contig_full is the ledger's name; the supplied table is not changed.

    region is (core contig, first base, last base) of the page's own antiSMASH region. A cluster whose name could mean
    two ledger contigs is an identity hold only when one of them is the core contig and the cluster overlaps the region;
    any other such cluster is left off the page with a logged warning. Call it while planning, before pages are written."""
    candidates = _contig_candidates(list(ledger_contigs))
    core, lo, hi = region
    shown = set(order)
    out = []
    for g in gecco_all:
        if g["strain"] != strain:
            continue
        cs = candidates(g["contig_full"])
        if len(cs) == 1:
            if cs[0] in shown:
                out.append({**g, "contig_full": cs[0]})
        elif len(cs) > 1:
            if core in cs and _overlaps(g, lo, hi):
                raise ValueError(f"LOCUS_PAGE_CONTIG_IDENTITY_HOLD: GECCO {g['contig_full']} matches "
                                 f"{', '.join(sorted(cs))} and overlaps {core} {lo}-{hi}")
            _OUT.warning("GECCO cluster on %s skipped for the page of %s %s-%s: its name matches %s and it does not "
                         "overlap the region", g["contig_full"], core, lo, hi, ", ".join(sorted(cs)))
    return out


def select_rows(genes_by_contig, bgc, pairs, gr_by_pair, sp_by_pair):
    """-> (rows, contig order, extra contigs): the region's CDS with 3 flanking CDS on each side, then every contig the
    gene table or split check points to (whole contig up to 20 kb; else the matched CDS and 2 on each side)."""
    region = [g for gs in genes_by_contig.values() for g in gs if g["bgc"] == bgc]
    if not region:
        return [], [], {}
    core = region[0]["contig"]
    cg = genes_by_contig[core]
    idx = [i for i, g in enumerate(cg) if g["bgc"] == bgc]
    shown = {(core, i) for i in range(max(0, idx[0] - 3), min(len(cg), idx[-1] + 4))}
    extra = defaultdict(set)
    for p in pairs:
        for r in gr_by_pair.get(p["pair"], []):
            if r.get("best_contig") and r["status"] != "MISSING_NOT_FOUND" and r["best_contig"] != core:
                extra[r["best_contig"]].add(r.get("best_locus", ""))
        for r in sp_by_pair.get(p["pair"], []):
            for k, lk in (("piece1_region_identity", "piece1_locus"), ("piece2_region_identity", "piece2_locus")):
                m = re.search(r"/ (\S+)", r.get(k, ""))
                if m and m.group(1) != core:
                    extra[m.group(1)].add(r.get(lk, ""))
    resolve = contig_resolver(genes_by_contig)
    merged = defaultdict(set)
    for c, v in extra.items():
        resolved = resolve(c)
        if resolved != core:
            merged[resolved] |= v
    extra = merged
    for c, loci in extra.items():
        gs = genes_by_contig.get(c, [])
        if clen(c) <= 20000:
            shown |= {(c, i) for i in range(len(gs))}
        else:
            for i, g in enumerate(gs):
                if g["locus_tag"] in loci:
                    shown |= {(c, j) for j in range(max(0, i - 2), min(len(gs), i + 3))}
    order = [core] + sorted(extra)
    rows = [genes_by_contig[c][i] for c in order for i in sorted(j for cc, j in shown if cc == c)]
    return rows, order, extra


PAGE_SEARCH_SCHEMA = "sapote-mamey.locus-page-search.v1"
PAGE_SEARCH_OUTPUTS = ("proteins.faa", "pfam.domtbl", "mibig.tsv")
PAGE_SEARCH_PARAMETERS = {
    "hmmsearch": ["--cut_ga", "--noali"],
    "diamond": ["blastp", "--more-sensitive", "-k", "25", "-e", "1e-5"],
    "diamond_fields": ["qseqid", "sseqid", "pident", "length", "qlen", "slen", "qcovhsp", "scovhsp", "evalue", "bitscore"],
}


def _page_stat(path):
    st = Path(path).stat()
    return [st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns]


def _page_sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _page_source_context(paths, context):
    """Hash fixed databases/tools once per build; each search checks their stat identities.

    A final full rehash is mandatory at build completion (or within a direct call).
    No executable version probe or optional tool installation is performed.
    """
    resolved = {name: str(Path(path).resolve()) for name, path in paths.items()}
    if context:
        if context["paths"] != resolved:
            raise ValueError("PAGE_SEARCH_SOURCE_CONTEXT_CHANGED")
        _page_verify_context(context)
        return context
    sources, stats = {}, {}
    work = {"full_file_reads": 0, "bytes_hashed": 0}
    for name, value in resolved.items():
        path = Path(value)
        if not path.is_file():
            if name != "mibig_names":
                raise ValueError(f"PAGE_SEARCH_SOURCE_MISSING: {name}")
            sources[name] = {"path": value, "state": "ABSENT"}
            stats[name] = None
            continue
        before = _page_stat(path)
        digest = _page_sha(path)
        if _page_stat(path) != before:
            raise ValueError(f"PAGE_SEARCH_SOURCE_CHANGED: {name}")
        sources[name] = {"path": value, "state": "PRESENT", "sha256": digest, "bytes": before[2]}
        stats[name] = before
        work["full_file_reads"] += 1
        work["bytes_hashed"] += before[2]
    context.update(paths=resolved, sources=sources, stats=stats, hashing_work=work)
    return context


def _page_verify_context(context, *, full=False):
    """Reject drift; do not refresh a binding to newly observed bytes or timestamps."""
    for name, record in context["sources"].items():
        path = Path(record["path"])
        if record["state"] == "ABSENT":
            if path.exists():
                raise ValueError(f"PAGE_SEARCH_SOURCE_CHANGED: {name}")
            continue
        if not path.is_file() or _page_stat(path) != context["stats"][name]:
            raise ValueError(f"PAGE_SEARCH_SOURCE_CHANGED: {name}")
        if full:
            digest = _page_sha(path)
            context["hashing_work"]["full_file_reads"] += 1
            context["hashing_work"]["bytes_hashed"] += record["bytes"]
            if digest != record["sha256"] or _page_stat(path) != context["stats"][name]:
                raise ValueError(f"PAGE_SEARCH_SOURCE_CHANGED: {name}")


def _page_queries(proteome, need):
    """Extract one exact nonempty AA sequence per requested tag, hashing consumed FASTA bytes."""
    seqs, current, digest = {}, None, hashlib.sha256()
    before = _page_stat(proteome)
    with Path(proteome).open("rb") as stream:
        for raw in stream:
            digest.update(raw)
            line = raw.decode("utf-8").strip()
            if line.startswith(">"):
                header = line[1:].split()
                token = header[0] if header else ""
                parts = token.split("|")
                tag = parts[1] if len(parts) > 1 else token
                current = tag if tag in need else None
                if current is not None:
                    if tag in seqs:
                        raise ValueError(f"PAGE_SEARCH_QUERY_DUPLICATE: {tag}")
                    seqs[tag] = ""
            elif current is not None:
                seqs[current] += "".join(line.split()).upper()
    if _page_stat(proteome) != before:
        raise ValueError("PAGE_SEARCH_SOURCE_CHANGED: proteome")
    missing = sorted(set(need) - set(seqs))
    if missing:
        raise ValueError("PAGE_SEARCH_QUERY_MISSING: " + ", ".join(missing))
    for tag, aa in seqs.items():
        if not aa or not re.fullmatch(r"[A-Z*]+", aa):
            raise ValueError(f"PAGE_SEARCH_QUERY_INVALID: {tag}")
    data = "".join(f">{tag}\n{seqs[tag]}\n" for tag in sorted(seqs)).encode("ascii")
    source = {"path": str(Path(proteome).resolve()), "sha256": digest.hexdigest(), "bytes": before[2]}
    return seqs, data, source, before


def _page_gene_sources(strain, need, seqs, gene_rows):
    """Bind physical ledger coordinates without inventing a ledger AA-sequence match."""
    if gene_rows is None:
        return {"state": "NOT_SUPPLIED", "rows": []}
    rows, physical = {}, {}
    for row in gene_rows:
        tag = row.get("locus_tag")
        if tag not in need:
            continue
        fields = ("strain", "locus_tag", "contig", "start", "end", "strand", "region", "bgc", "aa")
        record = {key: str(row.get(key) or "") for key in fields}
        if record["strain"] != strain or not record["contig"]:
            raise ValueError(f"PAGE_SEARCH_LEDGER_IDENTITY_HOLD: {tag}")
        try:
            start, end, length = int(record["start"]), int(record["end"]), int(record["aa"])
            if start < 0 or end <= start or length != len(seqs[tag]):
                raise ValueError
        except ValueError as exc:
            raise ValueError(f"PAGE_SEARCH_LEDGER_SEQUENCE_OR_COORDINATE_HOLD: {tag}") from exc
        key = tuple(record[k] for k in ("strain", "contig", "start", "end", "strand", "aa"))
        if tag in physical and physical[tag] != key:
            raise ValueError(f"PAGE_SEARCH_LEDGER_IDENTITY_HOLD: {tag}")
        physical[tag] = key
        rows[tuple(record.values())] = record
    if set(physical) != set(need):
        raise ValueError("PAGE_SEARCH_LEDGER_IDENTITY_HOLD: missing requested rows")
    return {"state": "COORDINATES_AND_LENGTH_BOUND; LEDGER_AA_SEQUENCE_HASH_UNAVAILABLE",
            "rows": [rows[key] for key in sorted(rows)]}


def _page_parse_outputs(folder, seqs, payloads=None):
    """Parse completed output only; unknown tags or impossible query coordinates refuse."""
    pf, mb = defaultdict(list), {}
    payloads = payloads if payloads is not None else {name: (folder / name).read_bytes() for name in PAGE_SEARCH_OUTPUTS}
    for line in payloads["pfam.domtbl"].decode("utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        f = line.split()
        try:
            if len(f) < 22 or f[0] not in seqs or int(f[2]) != len(seqs[f[0]]):
                raise ValueError
            start, end = int(f[19]), int(f[20])
            if not 1 <= start <= end <= len(seqs[f[0]]):
                raise ValueError
        except (ValueError, IndexError) as exc:
            raise ValueError("PAGE_SEARCH_PFAM_OUTPUT_INVALID") from exc
        pf[f[0]].append((start, f"{f[3]} {start}-{end}"))
    for line in payloads["mibig.tsv"].decode("utf-8").splitlines():
        if not line.strip():
            continue
        f = line.rstrip("\r\n").split("\t")
        try:
            if len(f) != 10 or f[0] not in seqs or not f[1] or int(f[4]) != len(seqs[f[0]]):
                raise ValueError
            subject = f[1].split("|")
            if len(subject) < 2 or not subject[0] or not subject[1]:
                raise ValueError  # the page reader consumes accession|protein identifiers
            values = [float(f[i]) for i in (2, 6, 7, 8, 9)]
            if (not all(math.isfinite(v) for v in values) or not all(0 <= v <= 100 for v in values[:3])
                    or any(v < 0 for v in values[3:]) or int(f[3]) <= 0 or int(f[5]) <= 0):
                raise ValueError
        except (ValueError, IndexError) as exc:
            raise ValueError("PAGE_SEARCH_MIBIG_OUTPUT_INVALID") from exc
        if f[0] not in mb or float(f[9]) > float(mb[f[0]][9]):
            mb[f[0]] = f
    return pf, mb

def _page_cache(folder, binding, data, seqs):
    """Legacy, interrupted, corrupt and differently bound caches are never evidence of no hit."""
    try:
        if (folder / "PAGE_SEARCH_FAILURE.json").exists():
            return None
        receipt = json.loads((folder / "PAGE_SEARCH_RECEIPT.json").read_bytes())
        if receipt.get("schema_version") != PAGE_SEARCH_SCHEMA or receipt.get("status") != "COMPLETE":
            return None
        payloads = {name: (folder / name).read_bytes() for name in PAGE_SEARCH_OUTPUTS}
        if receipt.get("binding") != binding or payloads["proteins.faa"] != data:
            return None
        if receipt.get("completed_searches") != ["hmmsearch", "diamond"]:
            return None
        outputs = receipt.get("outputs")
        if not isinstance(outputs, dict) or set(outputs) != set(PAGE_SEARCH_OUTPUTS):
            return None
        for name in PAGE_SEARCH_OUTPUTS:
            if (outputs[name].get("sha256") != hashlib.sha256(payloads[name]).hexdigest()
                    or outputs[name].get("bytes") != len(payloads[name])):
                return None
        return _page_parse_outputs(folder, seqs, payloads)
    except (OSError, ValueError, TypeError, AttributeError, KeyError):
        return None


def _page_atomic_json(path, value):
    """Publish the completion marker atomically, after all bound files are installed."""
    fd, temporary = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def page_search(strain, need, out, opts, *, source_context=None, gene_rows=None, consumed_mibig_names=None):
    """Pfam/MIBiG for requested proteins, reusing only fully bound completed evidence.

    A build shares one fixed-source hash context across strains, checks stat drift at
    search boundaries and fully verifies it once at build completion. Direct calls
    perform that final verification here. No missing tool triggers a fallback search.
    """
    pf, mb = defaultdict(list), {}
    if not need:
        return pf, mb, ""
    proteome = Path(opts.proteomes) / f"{strain}.faa" if opts.proteomes else None
    pfam = Path(opts.pfam) if opts.pfam else None
    mibig_db = Path(opts.mibig_proteins) / "mibig_proteins.dmnd" if opts.mibig_proteins else None
    hmm = shutil.which(opts.hmmsearch) if opts.hmmsearch else None
    diamond = shutil.which(opts.diamond) if opts.diamond else None
    missing = [name for name, available in (("proteome", proteome and proteome.is_file()),
               ("Pfam file", pfam and pfam.is_file()), ("hmmsearch", hmm), ("DIAMOND", diamond),
               ("MIBiG protein set", mibig_db and mibig_db.is_file())) if not available]
    if missing:
        return pf, mb, "not run: no " + ", no ".join(missing) + " given"
    proteome, pfam, mibig_db = proteome.resolve(), pfam.resolve(), mibig_db.resolve()
    hmm, diamond = str(Path(hmm).resolve()), str(Path(diamond).resolve())
    own_context = source_context is None
    context = {} if own_context else source_context
    paths = {"pfam": pfam, "mibig_db": mibig_db, "mibig_names": Path(opts.mibig_proteins) / "mibig_proteins.tsv",
             "hmmsearch": hmm, "diamond": diamond, "producer": Path(__file__)}
    try:
        seqs, data, proteome_source, proteome_stat = _page_queries(proteome, need)
        gene_sources = _page_gene_sources(strain, need, seqs, gene_rows)
    except (ValueError, UnicodeError) as exc:
        return pf, mb, "not run: " + str(exc)
    _page_source_context(paths, context)
    if consumed_mibig_names is not None and consumed_mibig_names != context["sources"]["mibig_names"]:
        raise ValueError("PAGE_SEARCH_SOURCE_CHANGED: consumed_mibig_names")
    binding = {"strain": strain, "requested": sorted(need), "query_sha256": hashlib.sha256(data).hexdigest(),
               "queries": [{"locus_tag": tag, "aa": len(seqs[tag]), "aa_sha256": hashlib.sha256(seqs[tag].encode()).hexdigest()}
                           for tag in sorted(seqs)], "proteome": proteome_source, "gene_sources": gene_sources,
               "shared_sources": context["sources"], "parameters": PAGE_SEARCH_PARAMETERS, "threads": int(opts.threads)}
    cache_root = Path(out) / "_page_searches"
    ps = cache_root / strain

    def verify_inputs():
        _page_verify_context(context, full=own_context)
        if _page_stat(proteome) != proteome_stat or _page_sha(proteome) != proteome_source["sha256"]:
            raise ValueError("PAGE_SEARCH_SOURCE_CHANGED: proteome")

    binding_digest = hashlib.sha256(json.dumps(binding, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def publish_current(folder):
        _page_atomic_json(ps / "CURRENT.json", {"generation": folder.relative_to(ps).as_posix(),
                                               "binding_sha256": binding_digest,
                                               "receipt_sha256": _page_sha(folder / "PAGE_SEARCH_RECEIPT.json")})

    generations = ps / "generations"
    generation_root = generations / binding_digest
    for parent in (cache_root, ps, generations, generation_root):
        if parent.is_symlink():
            raise ValueError("PAGE_SEARCH_CACHE_PATH_REFUSED")
    if generation_root.is_dir():
        for candidate in sorted(generation_root.iterdir(), reverse=True):
            if not candidate.is_dir() or candidate.is_symlink():
                continue
            cached = _page_cache(candidate, binding, data, seqs)
            if cached is not None:
                verify_inputs()
                publish_current(candidate)
                return *cached, ""
    generation_root.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f"attempt-{time.time_ns()}-", dir=generation_root))
    try:
        faa, dt, mt = (stage / name for name in PAGE_SEARCH_OUTPUTS)
        faa.write_bytes(data)
        commands = [
            [str(hmm), "--cut_ga", "--cpu", str(opts.threads), "--noali", "-o", os.devnull,
             "--domtblout", str(dt), str(pfam), str(faa)],
            [str(diamond), "blastp", "--more-sensitive", "-k", "25", "-e", "1e-5", "--threads", str(opts.threads),
             "-q", str(faa), "-d", str(mibig_db), "-o", str(mt), "-f", "6", *PAGE_SEARCH_PARAMETERS["diamond_fields"]],
        ]
        subprocess.run(commands[0], check=True)
        subprocess.run(commands[1], check=True, capture_output=True)
        payloads = {name: (stage / name).read_bytes() for name in PAGE_SEARCH_OUTPUTS}
        result = _page_parse_outputs(stage, seqs, payloads)
        verify_inputs()
        outputs = {name: {"sha256": hashlib.sha256(payloads[name]).hexdigest(), "bytes": len(payloads[name])}
                   for name in PAGE_SEARCH_OUTPUTS}
        if any(_page_sha(stage / name) != outputs[name]["sha256"] for name in PAGE_SEARCH_OUTPUTS):
            raise ValueError("PAGE_SEARCH_OUTPUT_CHANGED")
        receipt = {"schema_version": PAGE_SEARCH_SCHEMA, "status": "COMPLETE", "binding": binding,
                   "outputs": outputs, "commands": commands, "completed_searches": ["hmmsearch", "diamond"],
                   "empty_outputs_mean": "No hit under these recorded filters only after both successful commands",
                   "hashing_work": {"shared_sources_so_far": dict(context["hashing_work"]),
                                    "proteome_full_reads": 2, "proteome_bytes_hashed": 2 * proteome_source["bytes"]}}
        _page_atomic_json(stage / "PAGE_SEARCH_RECEIPT.json", receipt)
        _page_atomic_json(ps / "CURRENT.json", {"generation": stage.relative_to(ps).as_posix(),
                                              "binding_sha256": binding_digest,
                                              "receipt_sha256": _page_sha(stage / "PAGE_SEARCH_RECEIPT.json")})
    except BaseException as exc:
        # Failed output is retained as evidence, never admitted as a completed search.
        try:
            _page_atomic_json(stage / "PAGE_SEARCH_FAILURE.json", {"status": "FAILED", "binding": binding,
                              "error_type": type(exc).__name__, "error": str(exc)[:2000]})
        except OSError as receipt_error:
            _OUT.warning("Could not record page-search failure in %s: %s", stage, receipt_error)
        raise
    return *result, ""


def cells(r, pair_names, pf, mb, mnames, mibig, searched):
    """One table row for one CDS, and the marks it carries (†, ‡)."""
    flags = set()
    p = ("; ".join(f"{d.split()[1]} {d.split()[2]}" for d in r["L2b_pfam_domains"].split(" | ") if d)
         if r["L2b_pfam_domains"] else "")
    if r["L2b_bind"] == "NOT_SEARCHED":
        found = "; ".join(x for _, x in sorted(pf.get(r["locus_tag"], [])))
        p = ((found or "no domain at the gathering threshold") if searched else "not searched") + " †"
        flags.add("†")
    m = ""
    if r["mibig_best_hit"]:
        acc = r["mibig_best_hit"].split("|")[0]
        m = (f"{r['mibig_gene'] or r['mibig_best_hit'].split('|')[1]} ({mibig(acc)['names'][:40]}, {acc}) "
             f"{float(r['mibig_identity']):.0f}%")
    elif r["mibig_queried"].startswith("yes, no"):
        m = "no hit under the filters"
    elif r["mibig_queried"].startswith("no"):
        flags.add("†")
        h = mb.get(r["locus_tag"])
        if not searched:
            m = "not searched †"
        elif h:
            acc = h[1].split("|")[0]
            g = mnames.get(h[1], {})
            m = f"{g.get('name') or h[1].split('|')[1]} ({mibig(acc)['names'][:40]}, {acc}) {float(h[2]):.0f}% †"
        else:
            m = "no hit under the filters †"
    l5 = ""
    if r["L5_status"] == "hit":
        org = r["L5_ref"].split(" | ")[0].rsplit(" ", 1)[0]
        where = {"inside": "in a region", "outside": "outside regions", "edge_overlap": "at a region edge",
                 "mixed": "mixed (ties)"}.get(r["L5_region_call"], r["L5_region_call"])
        cls = re.search(r"\(([^()]*)\)$", r["L5_ref_region"]) if r["L5_ref_region"] else None
        l5 = (f"{r['L5_product']} (*{org}*{', SID' if r['L5_ref_is_SID'] == 'yes' else ''}) {float(r['L5_pident']):.0f}%, "
              f"{where}{' (' + cls.group(1) + ')' if cls else ''}")
    elif r["L5_status"] == "no_hit_under_filters":
        l5 = "no hit under the filters"
    elif r["L5_status"] == "not_queried":
        l5 = "‡"
        flags.add("‡")
    calls = [g.split(": ", 1)[1].split(" [")[0] for g in (r["gene_map_rows"] or "").split(" || ")
             if any(g.startswith(n + ":") for n in pair_names)]
    notes = [f"CARD {r['card_family']}"] if r["card_family"] else []
    if r["bgc"] in ("", "-"):
        notes.append("outside the region")
    saved_p = r.get("LG_gene_avg_p")
    raw_p = "" if saved_p is None else str(saved_p).strip()
    try:
        value = float(raw_p)
        avg_p = f"{value:.2f}" if math.isfinite(value) and 0 <= value <= 1 else "source value invalid"
    except ValueError:
        avg_p = "not available" if not raw_p else "source value invalid"
    row = (f"| {r['locus_tag']} | {r['aa']} | {r['as_gene_function'] or '–'} | {p} | {m} | {l5} | {'; '.join(calls)} | "
           f"{avg_p} | {'; '.join(notes)} |")
    return row, flags


def auto_summary(rows, bgc, arow, conv, pairs, gecco, *, gene_table_provided=True, gecco_provided=True):
    """Counts and calls only: no interpretation, no compound or activity claim."""
    reg = [r for r in rows if r["bgc"] == bgc]
    core = sum(1 for r in reg if r["as_gene_function"].startswith("core"))
    l5 = [r for r in reg if r["L5_status"] == "hit"]
    l5in = sum(1 for r in l5 if r["L5_region_call"] == "inside")
    orgs = defaultdict(int)
    for r in l5:
        if r["L5_region_call"] == "inside":
            orgs[r["L5_ref"].split(" | ")[0].rsplit(" ", 1)[0]] += 1
    top_org = max(orgs.items(), key=lambda x: x[1]) if orgs else None
    S = [AUTO_HEAD,
         f"- antiSMASH class {arow['Products']}; {len(reg)} genes in the region, {core} called core biosynthetic; "
         f"boundary {arow['Boundary']}."]
    if conv:
        top = conv[0]
        ties = [c for c in conv if c["distinct_query_genes"] == top["distinct_query_genes"]]
        S.append(f"- Known clusters: the most genes matched to any MIBiG cluster is {top['distinct_query_genes']} of "
                 f"{top['query_gene_count_total']} ({', '.join(sorted({c['mibig_compound'] for c in ties}))[:160]}), "
                 f"median identity {float(top['median_pct_identity']):.0f}%"
                 f"{'; ' + str(len(ties)) + ' clusters tie' if len(ties) > 1 else ''}.")
    else:
        S.append("- Known clusters: no MIBiG cluster shares genes with this region in the package's convergence table.")
    if l5:
        S.append(f"- Reference genomes: {len(l5)} of {len(reg)} region genes have a closest public protein; {l5in} of those "
                 f"lie inside an antiSMASH region of their own genome"
                 + (f"; the most frequent genome among those is *{top_org[0]}* ({top_org[1]} genes)." if top_org else "."))
    for p in pairs:
        S.append(f"- Gene table ({p['mibig']}, {p['reference_title']}): {p['in_core']} of {p['reference_genes']} reference "
                 f"genes in the core; strength {p['strength']}.")
    if not pairs:
        S.append("- Gene table: no pair for this locus is recorded in the supplied inventory."
                 if gene_table_provided else
                 "- Gene table: NOT_PROVIDED; comparison evidence was not supplied.")
    S.append("- GECCO: " + ("; ".join(g["relation"].replace("_", " ").lower() + " (" + g["type"] + ", p "
                                      + format(float(g["average_p"]), ".2f") + ")" for g in gecco)
                            or ("no cluster for the region contig is recorded in the supplied table"
                                if gecco_provided else
                                "NOT_PROVIDED; comparison evidence was not supplied")) + ".")
    return "\n".join(S) + "\n"


def gene_kind_line(p, gr, sp, bgc):
    """The gene-table pair's reference genes present in the core, by MIBiG gene kind (gap_rescue.tsv
    reference_gene_kind). A reference whose borders include housekeeping genes ("other") can reach STRONG on those alone,
    so the biosynthetic count is given too. Present in the core = status PRESENT_IN_CORE, or a CLEAR split with a piece
    in this region (a shown split counts once, as core when a piece is in the core region), as in the table's own count."""
    if not gr:
        return ""
    def piece_here(s):
        return any((m := re.search(r"/ (BGC\d+)\s*$", s.get(k, ""))) and m.group(1) == bgc
                   for k in ("piece1_region_identity", "piece2_region_identity"))
    split_core = {s["name"] for s in sp if s.get("split_call") == "CLEAR" and piece_here(s)}
    kinds = defaultdict(lambda: [0, 0])
    for x in gr:
        k = x.get("reference_gene_kind") or "unknown"
        kinds[k][1] += 1
        kinds[k][0] += x.get("status") == "PRESENT_IN_CORE" or x.get("name") in split_core
    bc = sum(kinds[k][0] for k in ("biosynthetic", "biosynthetic-additional") if k in kinds)
    bt = sum(kinds[k][1] for k in ("biosynthetic", "biosynthetic-additional") if k in kinds)
    parts = "; ".join(f"{k} {v[0]} of {v[1]}" for k, v in sorted(kinds.items()))
    return (f"  - By MIBiG gene kind, reference genes present in the core: {parts}. Biosynthetic (core and additional): "
            f"**{bc} of {bt}**" + (" — fewer than half, although the table is STRONG."
                                   if p["strength"] == "STRONG" and bt and bc / bt < 0.5 else "."))


def per_gene_clusters(rows, bgc, conv, mibig):
    """Region genes counted by the MIBiG cluster of each gene's single best MIBiG protein (ledger mibig_best_hit). The
    convergence table comes from antiSMASH's KnownClusterBlast database, which can lack clusters, so it can miss the
    per-gene best match. -> Markdown lines, or [] when no region gene has a MIBiG hit."""
    per = defaultdict(list)
    for r in rows:
        if r["bgc"] == bgc and r["mibig_best_hit"]:
            per[r["mibig_best_hit"].split("|")[0]].append(float(r["mibig_identity"]))
    if not per:
        return []
    nreg = sum(1 for r in rows if r["bgc"] == bgc)
    top = sorted(per.items(), key=lambda x: (-len(x[1]), -max(x[1])))
    L = ["## Known clusters by the per-gene MIBiG column\n\nEach region gene's single best MIBiG protein (the ledger's "
         "MIBiG column), counted by cluster. This can differ from the table above, whose source is antiSMASH's "
         "KnownClusterBlast database.\n\n| MIBiG | Compound | Region genes whose best hit is here | Identity range |\n"
         "|---|---|--:|---|"]
    for acc, ids in top[:6]:
        L.append(f"| {acc} | {mibig(acc)['names'][:60]} | {len(ids)} of {nreg} | {min(ids):.0f}–{max(ids):.0f}% |")
    if conv and top[0][0] not in {c["mibig_accession"] for c in conv}:
        L.append("\nThe top cluster here is not in the KnownClusterBlast-based table above.")
    L.append("")
    return L


def _page_mibig_names(path):
    """Bind precisely the bytes decoded by the page names reader, including absence."""
    if path is None:
        return {}, None
    path = Path(path).resolve()
    source = {"path": str(path), "state": "ABSENT"}
    if not path.is_file():
        return {}, source
    before = _page_stat(path)
    payload = path.read_bytes()
    if _page_stat(path) != before:
        raise ValueError("PAGE_SEARCH_SOURCE_CHANGED: consumed_mibig_names")
    source.update(state="PRESENT", sha256=hashlib.sha256(payload).hexdigest(), bytes=len(payload))
    rows = csv.DictReader(io.StringIO(payload.decode("utf-8")), delimiter="\t")
    return {row["id"]: row for row in rows}, source


def _read_tsv(path):
    return list(csv.DictReader(open(path), delimiter="\t")) if path and Path(path).exists() else []


def _pairs(opts):
    """Gene-table pairs by (strain, bgc), and each pair's gap-rescue and split-gene rows, read beside its map."""
    by, gr, sp = defaultdict(list), {}, {}
    if not opts.gene_table_inventory:
        return by, gr, sp
    root = Path(opts.gene_table_root) if opts.gene_table_root else Path(opts.gene_table_inventory).parent
    for r in _read_tsv(opts.gene_table_inventory):
        r = dict(r)
        png = Path(r.get("png", ""))
        r["_png"] = png if png.is_absolute() else root / png
        by[(r["strain"], r["bgc"])].append(r)
        gr[r["pair"]] = _read_tsv(r["_png"].parent / "gap_rescue.tsv")
        sp[r["pair"]] = _read_tsv(r["_png"].parent / "gap_rescue_split_genes.tsv")
    return by, gr, sp


def _page_run_outputs(out, paths):
    """Bind explicit outputs touched by this attempt; never scan the output tree."""
    records = []
    for path in dict.fromkeys(paths):
        record = {"path": Path(path).relative_to(out).as_posix()}
        try:
            payload = Path(path).read_bytes()
            record.update(state="PRESENT", sha256=hashlib.sha256(payload).hexdigest(), bytes=len(payload))
        except OSError as exc:
            record.update(state="MISSING_OR_UNREADABLE", error_type=type(exc).__name__)
        records.append(record)
    return records


def _page_begin_run(out):
    """Invalidate current-looking success before writes, retaining every prior receipt."""
    root = out / "_page_searches"
    attempts = root / "run_attempts"
    current = root / "SOURCE_BINDING_RUN_RECEIPT.json"
    if any(path.is_symlink() for path in (root, attempts, current)):
        raise ValueError("PAGE_SEARCH_CACHE_PATH_REFUSED")
    attempts.mkdir(parents=True, exist_ok=True)
    attempt = Path(tempfile.mkdtemp(prefix=f"attempt-{time.time_ns()}-", dir=attempts))
    previous = current.read_bytes() if current.is_file() else None
    if previous is not None:
        (attempt / "PREVIOUS_CURRENT.json").write_bytes(previous)
    run = {"out": out, "attempt": attempt, "current": current,
           "previous_current_sha256": hashlib.sha256(previous).hexdigest() if previous is not None else None}
    _page_finish_run(run, "RUNNING", {}, [])
    return run


def _page_finish_run(run, status, context, output_paths, error=None):
    """Publish an immutable status record, then atomically select it as current."""
    out, attempt = run["out"], run["attempt"]
    record = {"schema_version": "sapote-mamey.locus-page-run.v1", "status": status,
              "attempt": attempt.relative_to(out).as_posix(),
              "scope": "Fixed page-search sources and explicit page/combined/log outputs touched by this attempt; "
                       "not whole-build scientific validation or acceptance",
              "source_validation": ("FINAL_HASH_VERIFIED" if status == "VERIFIED" else
                                    "NO_SEARCH_CONTEXT" if status == "NO_SEARCH_CONTEXT" else "NOT_VERIFIED"),
              "sources": context.get("sources", {}), "hashing_work": context.get("hashing_work", {}),
              "outputs": _page_run_outputs(out, output_paths),
              "output_scope": "Full saved bytes at attempt end; an appended shared BUILD_LOG may include prior rows",
              "previous_current_sha256": run["previous_current_sha256"],
              "validation_limits": "No file locking; prior ledger annotation layers and scientific claims are not revalidated"}
    if status in ("VERIFIED", "NO_SEARCH_CONTEXT") and any(item["state"] != "PRESENT" for item in record["outputs"]):
        raise ValueError("PAGE_SEARCH_RUN_OUTPUT_BINDING_FAILED")
    if error is not None:
        record["error"] = {"type": type(error).__name__, "message": str(error)[:2000]}
    destination = attempt / (status + ".json")
    if destination.exists():
        raise ValueError("PAGE_SEARCH_RUN_STATUS_EXISTS")
    _page_atomic_json(destination, record)
    _page_atomic_json(run["current"], {**record, "record_path": destination.relative_to(out).as_posix(),
                                       "record_sha256": _page_sha(destination)})


def _page_require_optional_tables(opts):
    """A supplied table is input evidence, never an implicit empty result."""
    for field, flag in (("gene_table_inventory", "--gene-table-inventory"), ("gecco", "--gecco")):
        path = getattr(opts, field, None)
        if path is not None and not Path(path).is_file():
            raise ValueError(f"PAGE_OPTIONAL_INPUT_NOT_FILE: {flag}: {path}")


def build(opts):
    out = assert_output_outside_bundle(Path(opts.out), __file__)
    _page_require_optional_tables(opts)
    if (out / "BUILD_LOG.tsv").exists() and not opts.bgc:
        raise SystemExit(f"{out} already holds a build; versions are never overwritten")
    out.mkdir(parents=True, exist_ok=True)
    run = _page_begin_run(out)
    context, built, output_paths = {}, [], []
    try:
        _build_pages(opts, out, context, built, output_paths)
        if context:
            _page_verify_context(context, full=True)
        _page_finish_run(run, "VERIFIED" if context else "NO_SEARCH_CONTEXT", context, output_paths)
        return built
    except BaseException as exc:
        try:
            _page_finish_run(run, "FAILED", context, output_paths, error=exc)
        except OSError as receipt_error:
            # RUNNING already replaced any prior current VERIFIED marker before page writes.
            _OUT.warning("Could not record failed locus-page attempt in %s: %s", run["attempt"], receipt_error)
        raise


def _build_pages(opts, out, search_context, built, output_paths):
    packages = dict(x.split("=", 1) for x in opts.package)
    skips = dict(x.split("=", 1) for x in opts.skip)
    led = ledger_by_strain(opts.ledger, opts.ledger_dir, out / "_ledger_by_strain")
    pairs_by, gr_by_pair, sp_by_pair = _pairs(opts)
    gecco_all = _read_tsv(opts.gecco)
    mibig = MibigIndex(opts.mibig_json)
    mnames, consumed_mibig_names = _page_mibig_names(
        Path(opts.mibig_proteins) / "mibig_proteins.tsv" if opts.mibig_proteins else None)
    strains = opts.strains.split(",") if opts.strains else sorted(packages)
    log_path = out / "BUILD_LOG.tsv"
    new_log = not log_path.exists()
    output_paths.append(log_path)
    log = open(log_path, "a", newline="")
    try:
        lw = _SafeWriter(log, delimiter="\t", lineterminator="\n")
        if new_log:
            lw.writerow(["strain", "bgc", "identity", "status", "rows", "gene_table_pairs", "hand_assessment", "file"])
        for strain in strains:
            if strain in skips:
                lw.writerow([strain, "", "", f"SKIPPED: {skips[strain]}", "", "", "", ""])
                continue
            t0 = time.time()
            pkg = Path(packages[strain])
            regions = list(csv.DictReader(open(next(pkg.glob("*_2_inventory.csv")))))
            conv_all = defaultdict(list)
            conv_file = next(pkg.glob("*_3_mibig_convergence.csv"), None)
            for r in (csv.DictReader(open(conv_file)) if conv_file else []):
                conv_all[r["bgc_id"]].append(r)
            genes = defaultdict(list)
            for r in _read_tsv(led / f"{strain}.tsv"):
                genes[r["contig"]].append(r)
            for gs in genes.values():
                gs.sort(key=lambda g: int(g["start"]))
            plan, gecco_by_bgc = [], {}
            for arow in regions:
                bgc = arow["BGC_ID"]
                if opts.bgc and bgc != opts.bgc:
                    continue
                pairs = pairs_by.get((strain, bgc), [])
                rows, order, _ = select_rows(genes, bgc, pairs, gr_by_pair, sp_by_pair)
                if rows:   # GECCO identity holds fire here, before any page of the strain is written
                    span = [int(g["start"]) for g in genes.get(order[0], []) if g["bgc"] == bgc] + \
                           [int(g["end"]) for g in genes.get(order[0], []) if g["bgc"] == bgc]
                    gecco_by_bgc[bgc] = page_gecco(gecco_all, strain, order, list(genes),
                                                   (order[0], min(span), max(span)))
                plan.append((arow, bgc, pairs, rows, order))
            need = {r["locus_tag"] for *_, rows, _ in plan for r in rows
                    if r["L2b_bind"] == "NOT_SEARCHED" or r["mibig_queried"].startswith("no")}
            search_rows = [r for *_, rows, _ in plan for r in rows if r["locus_tag"] in need]
            pf, mb, not_run = page_search(strain, need, out, opts, source_context=search_context, gene_rows=search_rows,
                                         consumed_mibig_names=consumed_mibig_names)
            (out / strain).mkdir(exist_ok=True)
            combined = []
            for arow, bgc, pairs, rows, order in plan:
                core = arow["Contig"]
                reg = int(arow.get("Region") or 1)
                ident = f"{strain} / {core} / region{reg:03d} / {bgc}"
                stem = f"{strain}_{node_tag(core)}_r{reg:03d}_{bgc}"
                page = out / strain / f"{stem}.md"
                if page.exists():
                    raise SystemExit(f"{page} exists; versions are never overwritten")
                if not rows:
                    lw.writerow([strain, bgc, ident, "NO_LEDGER_ROWS", 0, len(pairs), "", ""])
                    continue
                gecco = gecco_by_bgc[bgc]
                conv = sorted(conv_all.get(bgc, []), key=lambda r: (-int(r["distinct_query_genes"]),
                                                                    -float(r["median_pct_identity"] or 0)))
                kcb = arow.get("KCB_top", "")
                L = ['<style>table{font-size:8.5pt} td,th{padding:2px 4px}</style>\n', f"# {ident}: {arow['Products']}\n",
                     CAVEAT, "## At a glance\n",
                     f"- **Region:** {ident}, {arow['Length_kb']} kb, boundary {arow['Boundary']}, antiSMASH class "
                     f"**{arow['Products']}**.",
                     (f"- **KnownClusterBlast top hit:** {kcb.split(' | ')[0]}"
                      f"{' (' + kcb.split(' | ')[1] + ')' if ' | ' in kcb else ''}, {arow.get('KCB_proteins', '')} proteins."
                      if kcb else "- **KnownClusterBlast:** no hit.")]
                for p in pairs:
                    L.append(f"- **Gene table ({p['mibig']}, {p['reference_title']}):** {p['in_core']} of {p['reference_genes']} "
                             f"reference genes in the core, on {p['core_proteins']} distinct proteins; "
                             f"{p['found_clearly_elsewhere']} found clearly elsewhere; {p['found_ambiguously']} ambiguous; "
                             f"{p['not_found']} not found; {p['set_aside']} set aside. Strength **{p['strength']}**.")
                    kind = gene_kind_line(p, gr_by_pair.get(p["pair"], []), sp_by_pair.get(p["pair"], []), bgc)
                    if kind:
                        L.append(kind)
                if not pairs:
                    L.append("- **Gene table:** no pair for this locus is recorded in the supplied inventory."
                             if opts.gene_table_inventory else
                             "- **Gene table:** NOT_PROVIDED; comparison evidence was not supplied.")
                for g in gecco:
                    L.append(f"- **GECCO:** {g['type']} cluster on {short(g['contig_full'])}, {g['start']}–{g['end']}, average p "
                             f"{float(g['average_p']):.3f}, {g['relation'].replace('_', ' ').lower()}.")
                if not gecco:
                    L.append("- **GECCO:** no cluster for these contigs is recorded in the supplied table."
                             if opts.gecco else
                             "- **GECCO:** NOT_PROVIDED; comparison evidence was not supplied.")
                L.append("")
                for p in pairs:
                    L.append(f'<img src="{p["_png"]}" style="width:100%">\n')
                L.append("## Every gene, every layer\n")
                L.append("Rows: every CDS of the region, 3 flanking CDS on each side, and the contigs the gene table or split "
                         "check points to. Pfam = full Pfam-A (gathering thresholds). MIBiG best = highest-bit-score MIBiG "
                         "protein. Closest reference-genome protein = highest-bit-score protein among the reference genomes, "
                         "its GenBank product, and whether it lies in an antiSMASH region of its own genome (class in "
                         "brackets). GECCO p = per-gene probability.\n")
                L.append("| CDS | aa | antiSMASH role | Pfam domains (envelope) | MIBiG best hit | Closest reference-genome "
                         "protein | Gene-table call | GECCO p | Notes |")
                L.append("|---|--:|---|---|---|---|---|--:|---|")
                flags = set()
                for r in rows:
                    line, f = cells(r, [p["pair"] for p in pairs], pf, mb, mnames, mibig, not not_run)
                    L.append(line)
                    flags |= f
                L.append("")
                if "†" in flags:
                    L.append(DAGGER_SEARCHED if not not_run else
                             f"† Not searched for this page (the gene lies outside any antiSMASH region): page search {not_run}.\n")
                if "‡" in flags:
                    L.append(DOUBLE_DAGGER)
                L.append("Contigs: " + "; ".join(short(c) for c in order) + ".\n")
                sps = [s for p in pairs for s in sp_by_pair.get(p["pair"], [])]
                if sps:
                    L.append("**Split-gene checks:**\n\n| Reference gene | Call | Piece 1 | Piece 2 | Whole-gene rival |\n"
                             "|---|---|---|---|---|")
                    for s in sps:
                        L.append(f"| {s['name']} | {s['split_call']} | {s['piece1_locus']} {s['piece1_identity_pct']}% | "
                                 f"{s['piece2_locus']} {s['piece2_identity_pct']}% | {s.get('whole_gene_rival_locus', '')} "
                                 f"{s.get('whole_gene_rival_identity_pct', '')}% |")
                    L.append("\nA split is drawn only when CLEAR, and never overrides a core call.\n")
                if conv:
                    L.append("## Known clusters this locus resembles\n\n| MIBiG | Compound | Producer | Genes matched | Median "
                             "identity | MIBiG bioactivity (as recorded) |\n|---|---|---|--:|--:|---|")
                    for c in conv[:6]:
                        m = mibig(c["mibig_accession"])
                        L.append(f"| {c['mibig_accession']} | {c['mibig_compound'][:60]} | {m['taxon']} | "
                                 f"{c['distinct_query_genes']} of {c['query_gene_count_total']} | "
                                 f"{float(c['median_pct_identity'] or 0):.0f}% | {', '.join(m['acts']) or 'none recorded'} |")
                    L.append("\nBackground on reference compounds, not a claim about this strain.\n")
                L += per_gene_clusters(rows, bgc, conv, mibig)
                hand = Path(opts.assessments) / f"{stem}.md" if opts.assessments else None
                L.append("## Assessment\n")
                if hand and hand.exists():
                    txt, prev = [], ""
                    for line in hand.read_text().strip().splitlines():
                        if line.lstrip().startswith("- ") and prev.strip() and not prev.lstrip().startswith("- "):
                            txt.append("")
                        txt.append(line)
                        prev = line
                    L.append("\n".join(txt) + "\n")
                else:
                    L.append(auto_summary(rows, bgc, arow, conv, pairs, gecco,
                                          gene_table_provided=bool(opts.gene_table_inventory),
                                          gecco_provided=bool(opts.gecco)))
                refs = Path(opts.refs) / f"{stem}.tsv" if opts.refs else None
                if refs and refs.exists():
                    L.append("## Literature (checked at PubMed)\n")
                    for r in _read_tsv(refs):
                        L.append(f"- {r['citation']} doi:{r['doi']} (PMID {r['pmid']}). {r['reports']}")
                    L.append("")
                L.append(f"*Built by `locus_reading_pages.py` into `{out.name}`.*\n")
                text = "\n".join(L)
                output_paths.append(page)
                page.write_text(text)
                combined.append(text)
                built.append(page)
                lw.writerow([strain, bgc, ident, "OK", len(rows), len(pairs), "yes" if hand and hand.exists() else "no",
                             f"{strain}/{stem}.md"])
            if combined and not opts.bgc:
                combined_path = out / f"{strain}_ALL_BGCS.md"
                output_paths.append(combined_path)
                combined_path.write_text('\n\n<div style="page-break-after: always"></div>\n\n'.join(combined))
            log.flush()
            _OUT.info(f"{strain}: {len(combined)} pages, {len(need)} proteins searched"
                  f"{' (page search ' + not_run + ')' if not_run else ''}, {time.time() - t0:.0f} s")
    finally:
        log.close()


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", required=True, help="a new output folder (refused if it already holds a build, unless --bgc adds one page)")
    ap.add_argument("--package", action="append", default=[], required=True, metavar="STRAIN=DIR",
                    help="a strain's Mamey package folder; repeat per strain")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--ledger", help="gene annotation ledger, TSV or TSV.gz, one row per CDS with a strain column")
    g.add_argument("--ledger-dir", help="a folder of per-strain ledger TSVs named <strain>.tsv")
    ap.add_argument("--gene-table-inventory", help="gene-table inventory TSV (one row per pair)")
    ap.add_argument("--gene-table-root", help="folder the inventory's png paths are relative to (default: its folder)")
    ap.add_argument("--gecco", help="GECCO cluster table TSV")
    ap.add_argument("--mibig-json", help="folder of MIBiG JSON records, <BGC>.json")
    ap.add_argument("--mibig-proteins", help="folder with mibig_proteins.dmnd and mibig_proteins.tsv")
    ap.add_argument("--proteomes", help="folder of whole-proteome FASTA, <strain>.faa")
    ap.add_argument("--pfam", help="Pfam-A HMM file")
    ap.add_argument("--hmmsearch", help="hmmsearch binary")
    ap.add_argument("--diamond", help="DIAMOND binary")
    ap.add_argument("--assessments", help="folder of hand assessments, <stem>.md")
    ap.add_argument("--refs", help="folder of checked literature, <stem>.tsv")
    ap.add_argument("--strains", help="comma-separated strains to build (default: every --package)")
    ap.add_argument("--bgc", help="build one BGC only, into an existing folder (an existing page is still refused)")
    ap.add_argument("--skip", action="append", default=[], metavar="STRAIN=REASON", help="skip a strain; logged")
    ap.add_argument("--threads", type=int, default=4, help="threads for hmmsearch and DIAMOND (default 4)")
    return ap.parse_args(argv)


def main(argv=None):
    build(parse_args(argv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
