#!/usr/bin/env python3
"""comparison_map_pages.py: reference comparison maps in batches, on one kb scale, stacked onto pages.

A batch driver around tools/multi_reference_comparison.py (aligned layout). One spec row is one map: a query locus on
the top row and its best references below. The references of a row can be any mix of
  - public-genome antiSMASH regions, staged from a library INDEX.tsv by genus (the region-folder builder below),
    from extra antiSMASH zips, from folders of region GenBank files, or from single region files;
  - other isolate loci (compare_loci): one antiSMASH region each, named by BGC alias, always drawn;
  - MIBiG reference clusters (mibig): GenBank files, always drawn.
Pinned rows (compare_loci and mibig) are drawn whenever they match at least the discovery minimum of locus genes; the
`top` best other references fill the rest. Every map of a scale group is drawn at one width and one kb per inch, so a
kilobase is the same length on every map and page. Maps are then stacked onto pages in spec order.

Subcommands
  regions --index INDEX.tsv --genus G --out DIR [--library-root R] [--strictness loose] [--extra-zip Z ...]
          [--names NAMES.tsv]
      Stage one folder of antiSMASH region GenBank files for the public genomes of one genus. Each file is copied as
      <zip stem>__<file name>, and its ORGANISM line is set to the genome's row label, so the drawing gives one row per
      genome. Writes DIR/_genomes.tsv (zip, sha256, sha256_source, regions, row_label).
  run SPEC.tsv --out DIR [--library-index INDEX.tsv] [--mibig-dir D] [--mibig-names INDEX.json] [options]
      Draw every spec row, then the pages.

Spec columns (TSV, one row per map; '#' lines are comments; relative paths resolve against the spec's folder)
  map_id        required; the output folder name (letters, digits, '.', '_', '-')
  zip           required; antiSMASH result zip of the query locus
  label         required; the strain label the query locus is drawn and identified with
  bgc | rescue  one required; the BGC alias, or a <BGC>_vs_<ref> gap-rescue folder (adds its SUPPORTED partner contigs)
  genus         optional; stage that genus from --library-index (built once per run under DIR/_regions/<genus>/)
  ref_gbk_dirs  optional; ';'-separated folders of region GenBank files (for example from `regions`)
  ref_gbks      optional; ';'-separated region GenBank files
  extra_zips    optional; ';'-separated antiSMASH zips whose regions join the public references
  compare_loci  optional; ';'-separated isolate loci, each label|BGC|zip or label|BGC|zip|taxon (taxon is printed
                before the label, for example 'Nocardia sp.')
  mibig         optional; ';'-separated MIBiG GenBank files, or accessions found as <--mibig-dir>/<accession>.gbk
  top           optional; how many unpinned references to draw (default --top)
  gene_labels   optional; locus_tag/short_label TSV for gene labels, as multi_reference_comparison.py reads it
  page_group    optional; maps with one value are stacked onto their own pages (default: one group for the batch)

Outputs in DIR
  <map_id>/comparison.png/.pdf/.svg, CAPTION.md, references.tsv, pairs.tsv, receipt.json (from the drawing tool),
  rows.tsv (each drawn row: kind, pinned, name, identity), locus_pairs.tsv (global protein alignment of every matched
  pair between the query and each compare_loci row) and _references/ (the staged files, listed in _sources.tsv);
  pages/page_NN.png/.pdf with page_NN_CAPTION.md; MAPS.tsv (status per map); receipt.json (settings, inputs and
  outputs with SHA-256).

Similarity only: a matched gene is a best protein hit, not orthology, function or product. Nothing interpretive is
drawn on a map or page; captions go to CAPTION.md files.

Exit codes: 0 every map drawn; 1 one or more maps not drawn; 2 bad input.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import re
import shutil
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))

try:  # CSV formula-cell guard, as every tools/ writer (tests/test_410_tools_csv_writer_coverage.py)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # noqa: F401
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # noqa: F401

from mamey.logging_setup import get_logger as _get_logger  # noqa: E402
from mamey.figure_stamp import savefig_metadata, stamp_file  # noqa: E402

_OUT = _get_logger(__name__)

TOOL = "comparison_map_pages"
DRAWING_TOOL = "multi_reference_comparison"
EXIT_OK, EXIT_SOME_FAILED, EXIT_INPUT = 0, 1, 2
SPEC_COLUMNS = ("map_id", "zip", "label", "bgc", "rescue", "genus", "ref_gbk_dirs", "ref_gbks", "extra_zips",
                "compare_loci", "mibig", "top", "gene_labels", "page_group")
MAP_ID = re.compile(r"^[A-Za-z0-9._-]+$")
ALL_PINNED = 10 ** 6  # build() ranks every reference; the driver keeps the pinned rows and the top unpinned ones


class InputError(ValueError):
    """A refused input: a missing file or column, a malformed spec cell, or a locus that cannot be found."""


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _split(cell: str) -> list[str]:
    return [x.strip() for x in (cell or "").split(";") if x.strip()]


def _write_tsv(path: Path, header, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = _SafeWriter(fh, delimiter="\t", lineterminator="\n")
        w.writerow(list(header))
        w.writerows(rows)


def _read_tsv(path: Path) -> list[dict]:
    import csv
    lines = [x for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip() and not x.lstrip().startswith("#")]
    return list(csv.DictReader(lines, delimiter="\t"))


# ------------------------------------------------------------------------------------- region folder builder

_LEADING_RECORD = re.compile(r"^(?:[A-Z]{1,2}_)?[A-Z]{1,6}_?\d{5,}(?:\.\d+)?\s+")
_TRAILING_CONTIG = re.compile(r"\s+(Ga\d+_\d+|NODE_\S+|\S*contig\S*|\S*scaffold\S*|chromosome|DNA|genomic|genome|complete|whole)(\s.*)?$",
                              re.I)
_GENOME_ACC = re.compile(r"(?<![A-Za-z])([A-Z]{1,2}\d{5,8}|[A-Z]{4,6}\d{8,10}|GC[AF]_\d+)")


def clean_name(text: str) -> str:
    """A deposited name freed of a record accession in front and a contig token behind. antiSMASH run on FASTA input
    writes the first FASTA header as ORGANISM ('NZ_X01000001.1 Genus sp. M39 ABC_contig000001'); the name is the part
    between. The words are kept as deposited."""
    d = " ".join(text.split()).split(",")[0]
    d = _LEADING_RECORD.sub("", d)
    d = _TRAILING_CONTIG.sub("", d)
    return d.strip().rstrip(".").strip()


def label_of(texts: list[str]) -> str:
    """Row label of one genome from its region files: the most common ORGANISM line that is not '.', cleaned when it
    starts with a record accession; else the DEFINITION up to the first comma, cleaned the same way."""
    orgs = collections.Counter()
    for t in texts:
        m = re.search(r"^  ORGANISM +(.*)$", t, re.M)
        if m and m.group(1).strip() not in ("", "."):
            o = m.group(1).strip()
            orgs[clean_name(o) if _LEADING_RECORD.match(o + " ") else o] += 1
    orgs.pop("", None)
    if orgs:
        return orgs.most_common(1)[0][0]
    m = re.search(r"^DEFINITION +(.*?)(?=^\S)", texts[0], re.M | re.S) if texts else None
    name = clean_name(m.group(1)) if m else ""
    return name or "unnamed genome"


def set_organism(text: str, name: str) -> str:
    if not re.search(r"^  ORGANISM", text, re.M):
        raise InputError("region GenBank file has no ORGANISM line")
    return re.sub(r"^  ORGANISM +.*$", lambda _m: "  ORGANISM  " + name, text, count=1, flags=re.M)


def library_rows(index: Path, genus: str, strictness: str = "loose", library_root: Path | None = None) -> list[tuple]:
    """(zip path, sha256) for each distinct genome of one genus in a library INDEX.tsv (columns genus, strictness,
    sha256, library_path). library_path resolves against library_root, else the index's folder, else its parent."""
    rows, seen = [], set()
    roots = [library_root] if library_root else [index.parent, index.parent.parent]
    for r in _read_tsv(index):
        for c in ("genus", "strictness", "sha256", "library_path"):
            if c not in r:
                raise InputError(f"{index}: no '{c}' column")
        if r["genus"] == genus and r["strictness"] == strictness and r["sha256"] not in seen:
            seen.add(r["sha256"])
            p = Path(r["library_path"])
            if not p.is_absolute():
                p = next((root / p for root in roots if (root / p).exists()), roots[0] / p)
            rows.append((p, r["sha256"], "index"))
    return rows


def stage_regions(zips: list[tuple], out: Path, names: dict | None = None) -> list[dict]:
    """Copy every <record>.regionNNN.gbk of each genome zip into out as <zip stem>__<file name>, with the ORGANISM
    line set to the genome's row label. A genome filed twice under two names (NZ_ prefix or not) is kept once, the
    first in sorted order. names maps a zip file name to a row label that replaces the one read from the files. Two
    genomes with one label are told apart by the accession in their file name. Returns the _genomes.tsv rows."""
    out.mkdir(parents=True, exist_ok=True)
    names = names or {}
    acc = lambda n: (_GENOME_ACC.search(n) or [None, n])[1]
    kept, dups = {}, []
    for p, sha, src in sorted(zips, key=lambda x: Path(x[0]).name):
        k = acc(Path(p).name)
        (dups.append(Path(p).name) if k in kept else kept.setdefault(k, (Path(p), sha, src)))
    tab, labels = [], {}
    for p, sha, src in kept.values():
        if not p.exists():
            tab.append({"zip": p.name, "sha256": sha, "sha256_source": src, "regions": "MISSING", "row_label": ""})
            continue
        files = {}
        with zipfile.ZipFile(p) as z:
            for nm in z.namelist():
                base = nm.rsplit("/", 1)[-1]
                if nm.startswith("__MACOSX") or base.startswith("._") or not re.search(r"\.region\d+\.gbk$", base):
                    continue
                files[re.sub(r"\s+", "_", p.stem) + "__" + re.sub(r"\s+", "_", base)] = z.read(nm).decode("utf-8", "replace")
        lab = names.get(p.name) or (label_of(list(files.values())) if files else "")
        labels[p.name] = (lab, files)
        tab.append({"zip": p.name, "sha256": sha, "sha256_source": src, "regions": str(len(files)), "row_label": lab})
    count = collections.Counter(v[0] for v in labels.values())
    for t in tab:
        if t["zip"] not in labels:
            continue
        lab, files = labels[t["zip"]]
        if count[lab] > 1:
            a = _GENOME_ACC.search(t["zip"])
            lab = f"{lab} {a.group(1) if a else t['zip'].removesuffix('.zip')}"
        for fn, txt in files.items():
            (out / fn).write_text(set_organism(txt, lab), encoding="utf-8")
        t["row_label"] = lab
    _write_tsv(out / "_genomes.tsv", ("zip", "sha256", "sha256_source", "regions", "row_label"),
               [[t[c] for c in ("zip", "sha256", "sha256_source", "regions", "row_label")] for t in tab])
    if dups:
        _OUT.info("same genome filed twice, second copy skipped: %s", "; ".join(dups))
    return tab


# ------------------------------------------------------------------------------------- pinned reference rows

def _mrc():
    import multi_reference_comparison as mrc  # noqa: PLC0415 - imports Biopython and matplotlib helpers on use
    return mrc


class GenomeCache:
    """One read of each antiSMASH zip (whole-genome CDS and region identities), shared by every map of the batch."""

    def __init__(self):
        self._g = {}

    def get(self, zip_path: Path, label: str):
        k = (str(Path(zip_path).resolve()), label)
        if k not in self._g:
            self._g[k] = _mrc().gdr.load_genome(Path(zip_path), label)
        return self._g[k]


def find_region(genome, bgc: str) -> dict:
    regions = genome[1]
    hit = [r for r in regions if r["identity"].endswith(f"/ {bgc}")]
    if len(hit) != 1:
        raise InputError(f"BGC alias {bgc}: {len(hit)} antiSMASH regions carry it")
    return hit[0]


def region_file_text(zip_path: Path, region: dict) -> tuple[str, str]:
    """(member name, text) of the antiSMASH region GenBank file of one region of a result zip, matched on region
    number and the record's contig name (the engine's naming rule)."""
    gdr = _mrc().gdr
    import io  # noqa: PLC0415
    want = f".region{region['n']:03d}.gbk"
    with zipfile.ZipFile(zip_path) as z:
        cands = [n for n in z.namelist() if n.endswith(want) and "__MACOSX" not in n and not n.rsplit("/", 1)[-1].startswith("._")]
        texts = {n: z.read(n).decode("utf-8", "replace") for n in cands}
    for n, t in texts.items():
        rec = next(gdr._seqio().parse(io.StringIO(t), "genbank"))
        if gdr.parsers._record_contig_id(rec) == region["contig"]:
            return n, t
    raise InputError(f"{Path(zip_path).name}: no {want} file for contig {region['contig']}")


def stage_compare_locus(spec: str, base: Path, out: Path, cache: GenomeCache) -> dict:
    """Write one isolate locus (label|BGC|zip[|taxon]) into the reference folder. Returns its row record."""
    parts = [x.strip() for x in spec.split("|")]
    if len(parts) not in (3, 4) or not all(parts[:3]):
        raise InputError(f"compare_loci entry {spec!r}: expected label|BGC|zip or label|BGC|zip|taxon")
    label, bgc, zp = parts[:3]
    taxon = parts[3] if len(parts) == 4 else ""
    zp = _path(zp, base)
    reg = find_region(cache.get(zp, label), bgc)
    member, text = region_file_text(zp, reg)
    stem = f"LOCUS__{re.sub(r'[^A-Za-z0-9.-]+', '_', label)}__{bgc}"
    name = " ".join(x for x in (taxon, label, bgc) if x)
    (out / f"{stem}.gbk").write_text(set_organism(text, name), encoding="utf-8")
    node = reg["contig"].split("_length")[0]
    return {"stem": stem, "kind": "isolate locus", "pinned": True, "name": name, "identity": reg["identity"],
            "display_id": f"{node} · region{reg['n']:03d}", "source": str(zp), "member": member, "sha256": sha256(zp)}


def stage_mibig(entry: str, base: Path, out: Path, mibig_dir: Path | None, mibig_names: Path | None) -> dict:
    p = Path(entry)
    if p.suffix.lower() not in (".gbk", ".gb", ".genbank"):
        if not mibig_dir:
            raise InputError(f"mibig entry {entry!r} is an accession; give --mibig-dir")
        p = mibig_dir / f"{entry}.gbk"
    else:
        p = _path(entry, base)
    if not p.exists():
        raise InputError(f"MIBiG file not found: {p}")
    acc = re.sub(r"\.\d+$", "", p.stem)
    stem = f"MIBiG__{acc}"
    shutil.copyfile(p, out / f"{stem}.gbk")
    compound = _mrc().rlc.compound_name(acc, str(mibig_names)) if mibig_names else ""
    org = _mrc().organism(out / f"{stem}.gbk")
    return {"stem": stem, "kind": "MIBiG reference", "pinned": True, "name": org or acc, "identity": acc,
            "display_id": f"MIBiG {acc}" + (f", {compound}" if compound else ""), "source": str(p), "member": "",
            "sha256": sha256(p)}


def _path(cell: str, base: Path) -> Path:
    p = Path(os.path.expanduser(cell))
    return p if p.is_absolute() else base / p


def _link(src: Path, dst_dir: Path, rows: list, kind: str) -> None:
    dst = dst_dir / src.name
    if dst.exists() or dst.is_symlink():
        if sha256(dst) != sha256(src):
            raise InputError(f"two different reference files are named {src.name}")
        return
    try:
        dst.symlink_to(src.resolve())
    except OSError:
        shutil.copyfile(src, dst)
    rows.append({"stem": src.stem, "kind": kind, "pinned": False, "name": "", "identity": src.stem, "display_id": "",
                 "source": str(src.resolve()), "member": "", "sha256": sha256(src)})


def stage_references(row: dict, base: Path, out: Path, ctx: dict) -> list[dict]:
    """The reference folder of one map: public regions, then the pinned isolate loci and MIBiG clusters."""
    ref = out / "_references"
    if ref.exists():
        shutil.rmtree(ref)
    ref.mkdir(parents=True)
    staged = []
    folders = [_path(d, base) for d in _split(row.get("ref_gbk_dirs", ""))]
    if row.get("genus"):
        folders.append(ctx["genus_folder"](row["genus"].strip()))
    zips = [_path(z, base) for z in _split(row.get("extra_zips", ""))]
    if zips:
        extra = out / "_extra_regions"
        if extra.exists():
            shutil.rmtree(extra)
        stage_regions([(z, sha256(z), "computed") for z in zips], extra)
        folders.append(extra)
    for d in folders:
        if not d.is_dir():
            raise InputError(f"reference folder not found: {d}")
        for g in sorted(d.glob("*.gbk")):
            _link(g, ref, staged, "public region")
    for g in _split(row.get("ref_gbks", "")):
        p = _path(g, base)
        if not p.exists():
            raise InputError(f"reference file not found: {p}")
        _link(p, ref, staged, "public region")
    for c in _split(row.get("compare_loci", "")):
        staged.append(stage_compare_locus(c, base, ref, ctx["genomes"]))
    for e in _split(row.get("mibig", "")):
        staged.append(stage_mibig(e, base, ref, ctx["mibig_dir"], ctx["mibig_names"]))
    _write_tsv(ref / "_sources.tsv", ("file_stem", "kind", "pinned", "source", "zip_member", "sha256"),
               [[s["stem"], s["kind"], "yes" if s["pinned"] else "no", s["source"], s["member"], s["sha256"]] for s in staged])
    return staged


def select_refs(refs: list[dict], pinned: set, top: int) -> tuple[list[dict], list[str]]:
    """Keep rank order; every pinned row stays, unpinned rows fill up to `top`. Returns (kept, pinned stems missing)."""
    kept, n = [], 0
    for r in refs:
        if r["accession"] in pinned:
            kept.append(r)
        elif n < top:
            kept.append(r)
            n += 1
    drawn = {r["accession"] for r in kept}
    return kept, sorted(pinned - drawn)


# ------------------------------------------------------------------------------------- pair alignment

def global_pair(a: str, b: str, aligner=None, matrix=None) -> dict:
    """Needleman-Wunsch, BLOSUM62, gap open 11 / extend 1: identity and positives over the alignment length, gap
    columns, and identity over the shorter protein."""
    from Bio.Align import PairwiseAligner, substitution_matrices  # noqa: PLC0415
    matrix = matrix or substitution_matrices.load("BLOSUM62")
    if aligner is None:
        aligner = PairwiseAligner()
        aligner.substitution_matrix, aligner.open_gap_score, aligner.extend_gap_score, aligner.mode = matrix, -11, -1, "global"
    known = set(matrix.alphabet)
    a, b = ("".join(c if c in known else "X" for c in s.upper().rstrip("*")) for s in (a, b))  # U, O and the like score as X
    aln = aligner.align(a, b)[0]
    x, y = str(aln[0]), str(aln[1])
    ident = sum(1 for p, q in zip(x, y) if p == q and p != "-")
    pos = sum(1 for p, q in zip(x, y) if p != "-" and q != "-" and matrix[p][q] > 0)
    gaps = sum(1 for p, q in zip(x, y) if p == "-" or q == "-")
    n = len(x)
    return {"identity_pct": round(100 * ident / n, 1), "positives_pct": round(100 * pos / n, 1), "alignment_length": n,
            "gap_columns": gaps, "identity_over_shorter_pct": round(100 * ident / min(len(a), len(b)), 1)}


def locus_pair_rows(m: dict, rows: list[dict]) -> list[list]:
    out = []
    for info in rows:
        if info["kind"] != "isolate locus":
            continue
        r = next((x for x in m["refs"] if x["accession"] == info["stem"]), None)
        if not r:
            continue
        genes = {g["i"]: g for g in r["genes"]}
        for q, i, pid, bits in sorted(r["pairs"], key=lambda x: m["prots"][x[0]]["start"]):
            p, g = m["prots"][q], genes[i]
            al = global_pair(p["aa"], g["aa"])
            out.append([info["identity"], p["tag"], len(p["aa"].rstrip("*")), g["name"], len(g["aa"].rstrip("*")),
                        f"{pid:.1f}", f"{bits:.0f}", al["identity_pct"], al["positives_pct"], al["alignment_length"],
                        al["gap_columns"], al["identity_over_shorter_pct"]])
    return out


LOCUS_PAIR_HEADER = ("compared_locus", "query_locus_tag", "query_aa", "compared_gene", "compared_aa",
                     "diamond_identity_pct", "diamond_bitscore", "global_identity_pct", "global_positives_pct",
                     "alignment_length", "gap_columns", "identity_over_shorter_pct")


# ------------------------------------------------------------------------------------- pages

def stack_pages(maps: list[tuple[str, Path]], height_in: float, gap_in: float, dpi: int) -> list[list[tuple[str, Path]]]:
    """Greedy: maps in order, a new page when the next would pass height_in. A map taller than a page is alone."""
    from matplotlib import image as mpimg  # noqa: PLC0415
    pages, cur, h = [], [], 0.0
    for mid, png in maps:
        hh = mpimg.imread(png).shape[0] / dpi
        need = hh + (gap_in if cur else 0)
        if cur and h + need > height_in:
            pages.append(cur)
            cur, h, need = [], 0.0, hh
        if hh > height_in:
            _OUT.warning("%s is %.2f in tall, more than a page (%.2f in); it gets a page of its own", mid, hh, height_in)
        cur.append((mid, png))
        h += need
    if cur:
        pages.append(cur)
    return pages


def draw_page(items: list[tuple[str, Path]], out_stem: Path, gap_in: float, dpi: int) -> list[Path]:
    """One page: the map PNGs one under another, left-aligned, pixel for pixel (no resampling). PNG and PDF."""
    import matplotlib  # noqa: PLC0415
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # noqa: PLC0415
    from matplotlib import image as mpimg  # noqa: PLC0415
    imgs = [mpimg.imread(p) for _, p in items]
    gap = round(gap_in * dpi)
    wpx = max(i.shape[1] for i in imgs)
    hpx = sum(i.shape[0] for i in imgs) + gap * (len(imgs) - 1)
    fig = plt.figure(figsize=((wpx + .25) / dpi, (hpx + .25) / dpi), dpi=dpi)  # Agg truncates the pixel size
    fig.patch.set_facecolor("white")
    y = hpx
    for im in imgs:
        y -= im.shape[0]
        fig.figimage(im, xo=0, yo=y, origin="upper")
        y -= gap
    written = []
    out_stem.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        f = out_stem.with_suffix(f".{ext}")
        fig.savefig(f, dpi=dpi, metadata=savefig_metadata(f, TOOL), facecolor="white")
        written.append(f)
    plt.close(fig)
    return written


# ------------------------------------------------------------------------------------- the batch

def read_spec(spec: Path) -> list[dict]:
    rows = _read_tsv(spec)
    if not rows:
        raise InputError(f"{spec}: no rows")
    unknown = sorted(set(rows[0]) - set(SPEC_COLUMNS))
    if unknown:
        raise InputError(f"{spec}: unknown columns {unknown}; known: {', '.join(SPEC_COLUMNS)}")
    ids = set()
    for k, r in enumerate(rows, 1):
        r = {c: (r.get(c) or "").strip() for c in SPEC_COLUMNS}
        rows[k - 1] = r
        for c in ("map_id", "zip", "label"):
            if not r[c]:
                raise InputError(f"{spec} row {k}: '{c}' is empty")
        if not MAP_ID.match(r["map_id"]) or r["map_id"] in ids or r["map_id"] in ("pages", "_regions"):
            raise InputError(f"{spec} row {k}: map_id {r['map_id']!r} is not a unique folder name")
        ids.add(r["map_id"])
        if bool(r["bgc"]) == bool(r["rescue"]):
            raise InputError(f"{spec} row {k}: give exactly one of bgc and rescue")
        if r["top"] and not r["top"].isdigit():
            raise InputError(f"{spec} row {k}: top {r['top']!r} is not a whole number")
    return rows


def shared_scales(spans: dict, groups: dict, mode: str, plot_w_in: float, kb_per_in: float | None,
                  scale_kb: float | None) -> dict:
    """{map_id: (kb_per_in, scale bar kb)}. mode 'batch': one scale for every map; 'group': one per page_group;
    'none': each map fills the width (kb_per_in None). An explicit kb_per_in or scale_kb wins."""
    mrc = _mrc()
    out = {}
    if mode == "none":
        return {k: (kb_per_in, scale_kb) for k in spans}
    by = collections.defaultdict(list)
    for k in spans:
        by["" if mode == "batch" else groups.get(k, "")].append(k)
    for ks in by.values():
        widest = max((spans[k][1] - spans[k][0]) / 1000 for k in ks)
        kpi = kb_per_in or widest * 1.0201 / plot_w_in  # the 1% pad each side that draw_aligned keeps
        sb = scale_kb or mrc.scale_bar_kb(widest)
        for k in ks:
            out[k] = (kpi, sb)
    return out


def run(a) -> int:
    mrc = _mrc()
    spec = Path(a.spec).resolve()
    base = spec.parent
    out = Path(a.out).resolve()
    rows = read_spec(spec)
    out.mkdir(parents=True, exist_ok=True)
    genomes = GenomeCache()
    genus_dirs = {}

    def genus_folder(genus):
        if not a.library_index:
            raise InputError(f"genus {genus!r} needs --library-index")
        if genus not in genus_dirs:
            d = out / "_regions" / re.sub(r"[^A-Za-z0-9._-]+", "_", genus)
            tab = stage_regions(library_rows(Path(a.library_index), genus, a.strictness,
                                             Path(a.library_root) if a.library_root else None), d)
            _OUT.info("%s: %d genome zips, %d regions, %d missing", genus, len(tab),
                      sum(int(t["regions"]) for t in tab if t["regions"].isdigit()), sum(t["regions"] == "MISSING" for t in tab))
            genus_dirs[genus] = d
        return genus_dirs[genus]

    ctx = {"genus_folder": genus_folder, "genomes": genomes, "mibig_dir": Path(a.mibig_dir) if a.mibig_dir else None,
           "mibig_names": Path(a.mibig_names) if a.mibig_names else None}
    built, status = {}, {}
    for r in rows:
        mid = r["map_id"]
        mdir = out / mid
        try:
            staged = stage_references(r, base, mdir, ctx)
            pinned = {s["stem"]: s for s in staged if s["pinned"]}
            zp = _path(r["zip"], base)
            rescue = _path(r["rescue"], base) if r["rescue"] else None
            m = mrc.build(zp, r["label"], rescue, None, None, gene_labels=str(_path(r["gene_labels"], base)) if r["gene_labels"] else None,
                          top=ALL_PINNED, genome=genomes.get(zp, r["label"]), ref_gbk_dir=str(mdir / "_references"),
                          bgc=r["bgc"] or None)
            m["refs"], missing = select_refs(m["refs"], set(pinned), int(r["top"] or a.top))
            for ref in m["refs"]:
                if ref["accession"] in pinned:
                    ref["display_id"] = pinned[ref["accession"]]["display_id"]
            kinds = [k for k in ("isolate locus", "MIBiG reference") if any(
                pinned[x["accession"]]["kind"] == k for x in m["refs"] if x["accession"] in pinned)]
            if kinds:  # the caption names what the rows are
                m["source"] = "reference regions (" + ", ".join(["public-genome antiSMASH regions"] + [
                    {"isolate locus": "loci of other isolates", "MIBiG reference": "MIBiG clusters"}[k] for k in kinds]) + ")"
            skipped = dict(m.get("skipped", []))
            missing_why = {s: skipped.get(s, f"fewer than the discovery minimum of matched locus genes") for s in missing}
            for s, why in missing_why.items():
                _OUT.warning("%s: pinned row %s not drawn (%s)", mid, s, why)
            if not m["refs"]:
                status[mid] = ("not drawn", "no reference matches two or more locus genes", missing_why)
                continue
            lay = mrc.aligned_layout(m)
            built[mid] = (r, m, lay, staged, missing_why)
        except (Exception, SystemExit) as exc:  # noqa: BLE001 - one bad row (a loader may exit) goes to MAPS.tsv; the batch goes on
            status[mid] = ("not drawn", f"{type(exc).__name__}: {exc}", {})
            _OUT.error("%s: %s", mid, exc)
    plot_w = a.width_in - sum(mrc.PLOT_MARGINS_IN)
    spans = {k: mrc.aligned_span_bp(v[2]) for k, v in built.items()}
    scales = shared_scales(spans, {k: v[0]["page_group"] for k, v in built.items()}, a.shared_scale, plot_w,
                           a.kb_per_in, a.scale_bar_kb)
    drawn = []
    for r in rows:
        mid = r["map_id"]
        if mid not in built:
            continue
        _, m, lay, staged, missing_why = built[mid]
        mdir = out / mid
        kpi, sb = scales[mid]
        try:
            mrc.draw_aligned(m, lay, mdir, width_in=a.width_in, dpi=a.dpi, italic_binomial=a.italic_binomial,
                             kb_per_in=kpi, scale_kb=sb)
            mrc.write(m, mdir)
        except ValueError as exc:
            status[mid] = ("not drawn", f"drawing refused: {exc}", missing_why)
            _OUT.error("%s: %s", mid, exc)
            continue
        for ext in ("png", "pdf", "svg"):
            stamp_file(mdir / f"comparison.{ext}", DRAWING_TOOL)
        info = {s["stem"]: s for s in staged}
        row_tab, n_q = [], sum(len(qs) for _, qs in m["segments"])
        for k, ref in enumerate(m["refs"], 1):
            s = info.get(ref["accession"], {"kind": "public region", "pinned": False, "identity": ref["accession"]})
            row_tab.append([k + 1, ref["accession"], s["kind"], "yes" if s["pinned"] else "no", ref["compound"],
                            ref["display_id"], s["identity"], len(ref["pairs"]), n_q])
        _write_tsv(mdir / "rows.tsv", ("drawn_row", "file_stem", "kind", "pinned", "name", "bracket_label", "identity",
                                       "locus_genes_matched", "locus_genes"), row_tab)
        drawn_info = [info[x["accession"]] for x in m["refs"] if x["accession"] in info]
        if a.align_pairs and any(s["kind"] == "isolate locus" for s in drawn_info):
            _write_tsv(mdir / "locus_pairs.tsv", LOCUS_PAIR_HEADER, locus_pair_rows(m, drawn_info))
        extra = []
        loci = [s for s in drawn_info if s["kind"] == "isolate locus"]
        mib = [s for s in drawn_info if s["kind"] == "MIBiG reference"]
        if loci:
            extra.append("Rows from other isolates, each its antiSMASH region only: " + "; ".join(s["identity"] for s in loci) + ".")
        if mib:
            extra.append("MIBiG reference rows: " + "; ".join(s["display_id"] for s in mib) + ".")
        if missing_why:
            extra.append("Requested rows not drawn: " + "; ".join(f"{k} ({v})" for k, v in missing_why.items()) + ".")
        if a.shared_scale != "none":
            extra.append(f"Maps of this set share one scale: {kpi:.3g} kb per inch at {a.width_in:g} in wide.")
        if extra:
            with open(mdir / "CAPTION.md", "a", encoding="utf-8") as fh:
                fh.write("\n" + " ".join(extra) + "\n")
        status[mid] = ("drawn", f"{len(m['refs'])} rows", missing_why)
        drawn.append(mid)
    # pages
    page_rows, page_files = [], []
    if not a.no_pages and drawn:
        by = collections.OrderedDict()
        for r in rows:
            if r["map_id"] in drawn:
                by.setdefault(r["page_group"], []).append((r["map_id"], out / r["map_id"] / "comparison.png"))
        n = 0
        for grp, maps in by.items():
            for items in stack_pages(maps, a.page_height_in, a.page_gap_in, a.dpi):
                n += 1
                stem = out / "pages" / f"page_{n:02d}"
                page_files += draw_page(items, stem, a.page_gap_in, a.dpi)
                cap = [f"# Page {n}\n", "Maps from top to bottom.\n"]
                for k, (mid, _) in enumerate(items, 1):
                    cap.append(f"\n## {k}. {mid}\n\n" + (out / mid / "CAPTION.md").read_text(encoding="utf-8").split("\n", 2)[-1].strip() + "\n")
                    page_rows.append((mid, n, k, grp))
                Path(f"{stem}_CAPTION.md").write_text("".join(cap), encoding="utf-8")
                page_files.append(Path(f"{stem}_CAPTION.md"))
    page_of = {mid: (p, k) for mid, p, k, _ in page_rows}
    _write_tsv(out / "MAPS.tsv", ("map_id", "status", "detail", "pinned_not_drawn", "kb_per_in", "scale_bar_kb", "page", "position"),
               [[r["map_id"], status[r["map_id"]][0], status[r["map_id"]][1],
                 "; ".join(f"{k} ({v})" for k, v in status[r["map_id"]][2].items()),
                 f"{scales[r['map_id']][0]:.4g}" if r["map_id"] in drawn and scales[r["map_id"]][0] else "",
                 f"{scales[r['map_id']][1]:g}" if r["map_id"] in drawn and scales[r["map_id"]][1] else "",
                 page_of.get(r["map_id"], ("", ""))[0], page_of.get(r["map_id"], ("", ""))[1]] for r in rows])
    write_receipt(a, spec, rows, out, drawn, page_files)
    _OUT.info("%d of %d maps drawn, %d pages; %s", len(drawn), len(rows), len({p for _, p, _, _ in page_rows}), out / "MAPS.tsv")
    return EXIT_OK if len(drawn) == len(rows) else EXIT_SOME_FAILED


def write_receipt(a, spec: Path, rows: list, out: Path, drawn: list, page_files: list) -> None:
    inputs = {str(spec): sha256(spec)}
    for r in rows:
        z = _path(r["zip"], spec.parent)
        if z.exists():
            inputs[str(z)] = sha256(z)
    for f in (a.library_index, a.mibig_names):
        if f and Path(f).exists():
            inputs[str(Path(f).resolve())] = sha256(f)
    outputs = {}
    for mid in drawn:
        for f in sorted((out / mid).iterdir()):
            if f.is_file():
                outputs[str(f.relative_to(out))] = sha256(f)
        src = out / mid / "_references" / "_sources.tsv"
        outputs[str(src.relative_to(out))] = sha256(src)
    for f in page_files + [out / "MAPS.tsv"]:
        outputs[str(Path(f).relative_to(out))] = sha256(f)
    rec = {"schema": "comparison-map-pages-v1", "tool": f"tools/{TOOL}.py", "drawing_tool": f"tools/{DRAWING_TOOL}.py",
           "settings": {"top": a.top, "width_in": a.width_in, "dpi": a.dpi, "italic_binomial": a.italic_binomial,
                        "shared_scale": a.shared_scale, "kb_per_in": a.kb_per_in, "scale_bar_kb": a.scale_bar_kb,
                        "page_height_in": a.page_height_in, "page_gap_in": a.page_gap_in, "pages": not a.no_pages,
                        "align_pairs": a.align_pairs, "strictness": a.strictness,
                        "pair_alignment": "global, BLOSUM62, gap open 11, extend 1"},
           "inputs_sha256": inputs, "outputs_sha256": outputs,
           "reference_files": "each map's _references/_sources.tsv lists every staged file with its source and SHA-256"}
    (out / "receipt.json").write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8")


def regions_cmd(a) -> int:
    names = {r["zip"]: r["row_label"] for r in _read_tsv(Path(a.names))} if a.names else {}
    zips = library_rows(Path(a.index), a.genus, a.strictness, Path(a.library_root) if a.library_root else None)
    zips += [(Path(z), sha256(z), "computed") for z in a.extra_zip or []]
    tab = stage_regions(zips, Path(a.out), names)
    _OUT.info("%s: %d genome zips, %d regions, %d missing", a.genus, len(tab),
              sum(int(t["regions"]) for t in tab if t["regions"].isdigit()), sum(t["regions"] == "MISSING" for t in tab))
    return EXIT_OK


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog="See the module docstring for the spec columns and outputs.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("regions", help="stage one genus's public antiSMASH regions as a folder")
    g.add_argument("--index", required=True, help="library INDEX.tsv (genus, strictness, sha256, library_path)")
    g.add_argument("--genus", required=True)
    g.add_argument("--out", required=True)
    g.add_argument("--library-root", help="folder library_path resolves against (default: the index's folder, then its parent)")
    g.add_argument("--strictness", default="loose")
    g.add_argument("--extra-zip", action="append", help="another antiSMASH zip to stage with the genus (repeatable)")
    g.add_argument("--names", help="TSV with zip and row_label columns: deposited names that replace the label read from the files")
    r = sub.add_parser("run", help="draw every spec row on one kb scale and stack the pages", description=__doc__,
                       formatter_class=argparse.RawDescriptionHelpFormatter)
    r.add_argument("spec")
    r.add_argument("--out", required=True)
    r.add_argument("--library-index", help="library INDEX.tsv for the spec's genus column")
    r.add_argument("--library-root")
    r.add_argument("--strictness", default="loose")
    r.add_argument("--mibig-dir", help="folder of MIBiG GenBank files for accessions in the mibig column")
    r.add_argument("--mibig-names", help="MIBiG index JSON: adds the compound name to MIBiG row labels")
    r.add_argument("--top", type=int, default=6, help="unpinned references per map (default 6)")
    r.add_argument("--width-in", type=float, default=9.6, help="map width (default 9.6 landscape; 6.5 portrait)")
    r.add_argument("--dpi", type=int, default=300)
    r.add_argument("--italic-binomial", action="store_true", help="genus and species of a row name in italics")
    r.add_argument("--shared-scale", choices=("batch", "group", "none"), default="batch",
                   help="one kb scale for the whole batch (default), one per page_group, or each map fills its width")
    r.add_argument("--kb-per-in", type=float, help="fix the shared scale instead of fitting the widest map")
    r.add_argument("--scale-bar-kb", type=float, help="fix the scale bar length")
    r.add_argument("--page-height-in", type=float, default=6.5, help="page height maps are stacked into (default 6.5)")
    r.add_argument("--page-gap-in", type=float, default=.15)
    r.add_argument("--no-pages", action="store_true")
    r.add_argument("--no-align-pairs", dest="align_pairs", action="store_false",
                   help="skip locus_pairs.tsv (global alignment of query and compared-locus protein pairs)")
    a = ap.parse_args(argv)
    try:
        return regions_cmd(a) if a.cmd == "regions" else run(a)
    except InputError as exc:
        _OUT.error("refused: %s", exc)
        return EXIT_INPUT


if __name__ == "__main__":
    sys.exit(main())
