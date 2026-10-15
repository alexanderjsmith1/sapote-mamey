#!/usr/bin/env python3
"""Which protein was searched: protein_sha256 for each (strain, gene, result file) of BLASTp results.

A BLASTp result names its query by locus tag, and locus tags are numbered per antiSMASH run, so the tag alone can point to a
different gene in another run of the same genome. This tool finds the query sequence each result file was searched with
and records its SHA-256 (mamey.protein_binding.protein_sha256), so a reader can bind the result to a gene by its protein.

How a result file finds its query, strongest evidence first (column binding_evidence):
  ledger_sha                    the result sits in a runner lane (<lane>/results/<strain>/<panel>/); the lane's _ledger.csv
                                row for (strain, panel) names the query file and its query_sha256; the copy in a _QUERIES*
                                folder beside the lane with those bytes is read.
  ledger_unchanged              as above for an older ledger without query_sha256: one copy exists, and it was last
                                modified before the row's submit time, so it is the file that was sent.
  saved_query_length_confirmed  no ledger: every saved query FASTA (any _QUERIES* or *STAGING* folder) holding this strain
                                and tag has the same protein, and its length equals the length the result file records.
  xml_query_length              no protein, but the lane's BLAST XML for the ledger row's RID (<lane>/xml/<RID>*.xml)
                                records the query length (query-len, or Iteration_query-len in the legacy format) for this
                                strain and tag. protein_sha256 stays empty; a reader binds by length (within 1 aa) only.
  xml_lane_one_length           the ledger has no row for the result folder (an older, rotated ledger), but every BLAST XML
                                in the lane's xml/ folder that searched this strain and tag records the same query length.
                                Length only, as above.
  none                          no evidence; protein_sha256 is empty. A reader may still bind by length (within 1 aa),
                                using query_aa_length when the result file records it.
The query FASTA headers in use are parsed by mamey.protein_binding.header_key.

Usage:
  python3 tools/blastp_query_index.py --root <workspace> --sources-from-table GENE_BLASTP_NAMES.tsv --out QUERY_INDEX.tsv
  python3 tools/blastp_query_index.py --root <workspace> --store <snapshot.sqlite> [--strain <strain> ...] --out QUERY_INDEX.tsv
  python3 tools/blastp_query_index.py --root <workspace> --annotate GENE_BLASTP_NAMES.tsv --index QUERY_INDEX.tsv \
          --out GENE_BLASTP_NAMES_WITH_SHA.tsv
The store is opened read-only; give it a snapshot. Nothing is overwritten.
"""
from __future__ import annotations

try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

import argparse
import csv
import datetime as dt
import glob
import json
import hashlib
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mamey.protein_binding import header_key, norm_strain, protein_sha256, read_fasta, tag_of  # noqa: E402

from mamey.extra_csv_manifest import csv_inputs, write_csv_manifest

COLS = ["strain", "gene", "source_file", "protein_sha256", "query_aa_length", "binding_evidence"]
# BLAST XML2 (<query-title>…<query-len>) and the legacy format (<Iteration_query-def>…<Iteration_query-len>)
_XML_QUERY = re.compile(r"<(?:query-title|Iteration_query-def)>([^<]*)</(?:query-title|Iteration_query-def)>\s*"
                        r"<(?:query-len|Iteration_query-len)>(\d+)</(?:query-len|Iteration_query-len)>")
RESULTS_ROOT = "Blastp RESULTS"


def _sha_file(p: Path) -> str:
    with open(p, "rb") as fh:
        return hashlib.file_digest(fh, "sha256").hexdigest()


def _when(iso: str):
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return dt.datetime.strptime((iso or "").strip(), fmt).timestamp()
        except ValueError:
            continue
    return None


class QueryFinder:
    """Resolves the query proteins of result files under one workspace root."""

    def __init__(self, root: Path):
        self.root = root
        self.res = root / RESULTS_ROOT
        self._ledgers: dict[Path, dict] = {}
        self._saved: dict[tuple[str, str], Counter] | None = None
        self._lane_xml: dict[Path, dict] = {}
        self.query_roots = sorted(p for p in self.res.glob("_QUERIES*") if p.is_dir())

    def _ledger(self, lane: Path) -> dict:
        if lane not in self._ledgers:
            rows = defaultdict(list)
            led = lane / "_ledger.csv"
            if led.is_file():
                for r in csv.DictReader(open(led, newline="", encoding="utf-8", errors="replace")):
                    rows[(r.get("strain", ""), r.get("bgc", ""))].append(r)
            self._ledgers[lane] = rows
        return self._ledgers[lane]

    def _copies(self, rel: str) -> list[Path]:
        return [q / rel for q in self.query_roots if (q / rel).is_file()]

    def from_ledger(self, source_file: str) -> tuple[dict, str]:
        """-> ({(strain, tag): (sha, length)}, evidence) from the lane ledger, or ({}, reason)."""
        parts = Path(source_file).parts
        if "results" not in parts:
            return {}, "none"
        i = parts.index("results")
        if i + 2 >= len(parts):
            return {}, "none"
        lane = self.root.joinpath(*parts[:i])
        rows = self._ledger(lane).get((parts[i + 1], parts[i + 2]), [])
        out, evidence = {}, set()
        for r in rows:
            rel, want = r.get("file", ""), (r.get("query_sha256") or "").strip().lower()
            copies = self._copies(rel)
            pick, ev = None, None
            if want:
                hit = [p for p in copies if _sha_file(p) == want]
                pick, ev = (hit[0], "ledger_sha") if hit else (None, None)
            elif len(copies) == 1:
                sent = _when(r.get("submit_iso", ""))
                if sent is not None and copies[0].stat().st_mtime <= sent:
                    pick, ev = copies[0], "ledger_unchanged"
            if pick is None:
                continue
            evidence.add(ev)
            for head, seq in read_fasta(pick):
                s, t = header_key(head, norm_strain(r.get("strain", "")))
                out[(norm_strain(s), t)] = (protein_sha256(seq), len(seq.replace("*", "")))
        if not out:
            return {}, "none"
        return out, "ledger_sha" if evidence == {"ledger_sha"} else "ledger_unchanged"

    def lengths_from_xml(self, source_file: str) -> dict:
        """{(strain, tag): query length} from the lane's BLAST XML of every ledger row for this result folder."""
        parts = Path(source_file).parts
        if "results" not in parts or parts.index("results") + 2 >= len(parts):
            return {}
        i = parts.index("results")
        lane = self.root.joinpath(*parts[:i])
        out = {}
        for r in self._ledger(lane).get((parts[i + 1], parts[i + 2]), []):
            rid = (r.get("rid") or "").strip()
            if not rid:
                continue
            for x in sorted((lane / "xml").glob(f"{rid}*.xml")):
                try:
                    text = x.read_text(errors="replace")
                except OSError:
                    continue
                for title, qlen in _XML_QUERY.findall(text):
                    s, t = header_key(title.strip(), norm_strain(r.get("strain", "")))
                    out.setdefault((norm_strain(s), t), int(qlen))
        return out

    def lane_xml_lengths(self, source_file: str) -> dict:
        """{(strain, tag): length} for tags whose every XML in the lane's xml/ folder records one query length."""
        parts = Path(source_file).parts
        if "results" not in parts:
            return {}
        lane = self.root.joinpath(*parts[:parts.index("results")])
        if lane not in self._lane_xml:
            seen = defaultdict(set)
            for x in sorted((lane / "xml").glob("*.xml")):
                try:
                    text = x.read_text(errors="replace")
                except OSError:
                    continue
                for title, qlen in _XML_QUERY.findall(text):
                    s, t = header_key(title.strip())
                    seen[(norm_strain(s), t)].add(int(qlen))
            self._lane_xml[lane] = {k: next(iter(v)) for k, v in seen.items() if len(v) == 1}
        return self._lane_xml[lane]

    def saved(self) -> dict:
        """(strain, tag) -> Counter{(sha, length): copies} over every saved query FASTA."""
        if self._saved is None:
            self._saved = defaultdict(Counter)
            folders = [p for p in self.res.iterdir() if p.is_dir()
                       and ("QUERIES" in p.name.upper() or "STAGING" in p.name.upper())]
            for folder in folders:
                for f in glob.glob(str(folder / "**" / "*.faa"), recursive=True):
                    try:
                        recs = read_fasta(f)
                    except OSError:   # broken link
                        continue
                    strain_dir = Path(f).relative_to(folder).parts[0] if len(Path(f).relative_to(folder).parts) > 1 else ""
                    for head, seq in recs:
                        s, t = header_key(head, norm_strain(strain_dir))
                        sha = protein_sha256(seq)
                        if sha:
                            self._saved[(norm_strain(s), t)][(sha, len(seq.replace("*", "")))] += 1
        return self._saved


def result_genes(root: Path, source_file: str) -> dict:
    """(strain, gene key, tag) -> recorded query length ('' if none) from a result CSV on disk."""
    out = {}
    p = root / source_file
    if not (p.is_file() and p.suffix == ".csv"):
        return out
    with open(p, newline="", encoding="utf-8", errors="replace") as fh:
        for r in csv.DictReader(fh):
            s, g = (r.get("strain") or "").strip(), (r.get("gene") or "").strip().split("|")[-1]
            if s and g:
                key = (s, g, tag_of(g))
                if not out.get(key):
                    out[key] = (r.get("aa_length") or r.get("query_length") or "").strip()
    return out


def index_sources(root: Path, sources: dict) -> list[dict]:
    """sources: {source_file: {(strain, gene): recorded length}} -> index rows."""
    qf = QueryFinder(root)
    rows = []
    for src in sorted(sources):
        genes = dict(sources[src])
        for (s, g, _t), L in result_genes(root, src).items():
            genes.setdefault((s, g), L)
            if not genes[(s, g)]:
                genes[(s, g)] = L
        ledger, ev = qf.from_ledger(src)
        xml_len = None
        for (s, g), rec_len in sorted(genes.items()):
            key = (norm_strain(s), tag_of(g))
            sha, qlen, how = "", rec_len, "none"
            if key in ledger:
                sha, qlen = ledger[key]
                how = ev
            else:
                cands = qf.saved().get(key, Counter())
                if len(cands) == 1:
                    (c_sha, c_len), = cands
                    try:
                        if rec_len and int(float(rec_len)) == c_len:
                            sha, how = c_sha, "saved_query_length_confirmed"
                    except ValueError:
                        # The recorded length cannot be compared, so the saved query is not bound; say so in the row
                        # instead of leaving "none" (.452: the last `except ...: pass` in tools/).
                        how = "recorded_length_unreadable"
            if not sha and not qlen:
                if xml_len is None:
                    xml_len = qf.lengths_from_xml(src)
                if key in xml_len:
                    qlen, how = str(xml_len[key]), "xml_query_length"
                elif key in qf.lane_xml_lengths(src):
                    qlen, how = str(qf.lane_xml_lengths(src)[key]), "xml_lane_one_length"
            rows.append({"strain": s, "gene": g, "source_file": src, "protein_sha256": sha,
                         "query_aa_length": qlen, "binding_evidence": how})
    return rows


def sources_from_table(path: Path) -> dict:
    out = defaultdict(dict)
    for r in csv.DictReader(open(path, newline="", encoding="utf-8"), delimiter="\t"):
        if r.get("source_file"):
            out[r["source_file"]][(r["strain"], r["gene"])] = (r.get("aa_length") or "").strip()
    return out


def sources_from_store(store: Path, strains) -> dict:
    from mamey.blastp_ingest import open_blastp_hits_store
    con = open_blastp_hits_store(store, writable=False)
    q = "select strain, gene, source_file, aa_length from hits where channel in ('ncbi_nr','ncbi_clustered_nr')"
    args = ()
    if strains:
        q += " and strain in (%s)" % ",".join("?" * len(strains))
        args = tuple(strains)
    out = defaultdict(dict)
    for s, g, src, L in con.execute(q, args):
        k = (s, (g or "").split("|")[-1])
        if not out[src].get(k):
            out[src][k] = "" if L is None else str(L)
    con.close()
    return out


def annotate(table: Path, index: Path, out: Path) -> Counter:
    idx = {(r["strain"], r["gene"], r["source_file"]): r
           for r in csv.DictReader(open(index, newline="", encoding="utf-8"), delimiter="\t")}
    with open(table, newline="", encoding="utf-8") as fh:
        rd = csv.DictReader(fh, delimiter="\t")
        cols = list(rd.fieldnames or []) + [c for c in ("protein_sha256", "query_aa_length", "binding_evidence")
                                             if c not in (rd.fieldnames or [])]
        rows = list(rd)
    tally = Counter()
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = _SafeDictWriter(fh, fieldnames=cols, delimiter="\t", lineterminator="\n")
        w.writeheader()
        for r in rows:
            hit = idx.get((r.get("strain", ""), r.get("gene", ""), r.get("source_file", "")))
            r["protein_sha256"] = hit["protein_sha256"] if hit else ""
            r["query_aa_length"] = (hit["query_aa_length"] if hit else "") or r.get("aa_length", "")
            r["binding_evidence"] = hit["binding_evidence"] if hit else "none"
            tally[r["binding_evidence"]] += 1
            w.writerow(r)
    return tally


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", type=Path, required=True, help="workspace root the source paths are relative to")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--sources-from-table", type=Path, help="a name table with strain, gene, source_file (and aa_length)")
    ap.add_argument("--store", type=Path, help="a read-only snapshot of the BLASTp store")
    ap.add_argument("--strain", action="append", default=[], help="with --store: only these strains")
    ap.add_argument("--extra-csv", action="append", default=[], help="glob of result CSVs (relative to --root)")
    ap.add_argument("--annotate", type=Path, help="a name table to copy with protein_sha256 added (needs --index)")
    ap.add_argument("--index", type=Path, help="with --annotate: an index this tool wrote")
    ap.add_argument("--extra-csv-list", type=Path, help="checked path/sha256/bytes TSV; exclusive with --extra-csv")
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit(f"{a.out} exists; nothing overwritten")
    root = a.root.resolve()
    try:
        extra_records, input_list_sha = csv_inputs(root, a.extra_csv, a.extra_csv_list)
    except (OSError, ValueError) as exc:
        ap.error(str(exc))
    receipt_dir = a.out.with_name(a.out.name + ".provenance")
    if receipt_dir.exists():
        ap.error(f"{receipt_dir} exists; nothing overwritten")
    def receipt():
        receipt_dir.mkdir()
        digest = write_csv_manifest(receipt_dir / "EXTRA_CSV_FILES.tsv", extra_records)
        info = {"extra_csv_manifest_sha256": digest, "extra_csv_list_sha256": input_list_sha,
                "extra_csvs": len(extra_records), "output": str(a.out)}
        (receipt_dir / "RUN_INFO.json").write_text(json.dumps(info, indent=2) + "\n")
    if a.annotate:
        if not a.index:
            raise SystemExit("--annotate needs --index")
        print(dict(annotate(a.annotate, a.index, a.out)))
        receipt()
        return 0
    sources = defaultdict(dict)
    if a.sources_from_table:
        for k, v in sources_from_table(a.sources_from_table).items():
            sources[k].update(v)
    if a.store:
        for k, v in sources_from_store(a.store, a.strain).items():
            sources[k].update(v)
    for record in extra_records:
        sources[record["path"]]
    if not sources:
        raise SystemExit("no sources: give --sources-from-table, --store or --extra-csv")
    rows = index_sources(root, sources)
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = _SafeDictWriter(fh, fieldnames=COLS, delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    receipt()
    print(dict(Counter(r["binding_evidence"] for r in rows)), f"{len(rows)} rows ->", a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
