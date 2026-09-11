"""mamey/kcb_locusmap.py — offline KnownClusterBlast / ClusterBlast comparative locus maps.

FEATURE (sign-off), non-scoring figure. Judgment deferred: this module renders evidence,
it never routes, promotes, or scores a BGC.

WHAT THIS IS
------------
A clinker-style comparative locus map, offline (matplotlib only — no DIAMOND / no clinker /
no network). Per BGC region it draws:

  * the **query** gene arrows on top, to genomic scale, colored by antiSMASH role
    (biosynthetic / transport / regulatory / other) read from the region GBK gene_functions
    when a raw antiSMASH ZIP is supplied, otherwise colored by KnownClusterBlast participation;
  * the **top-N MIBiG reference clusters** stacked beneath, each subject gene aligned under the
    query gene it pairs with;
  * **homology ribbons** linking paired genes, shaded by BLAST %identity.

The only required input is the antiSMASH `knownclusterblast/<contig>.txt` (or `clusterblast/…`)
file, which already carries the full gene pairing:

    Table of genes, locations, strands and annotations of query cluster:
        ctg106_3  1721  2669  -
    ...
    >>
    1. BGC0001211.5
    Source: albachelin
    Type: NRPS:Type I
    Table of Blast hits (query gene, subject gene, %identity, blast score, %coverage, e-value):
        ctg106_3  AMYAL_RS0130200  97  623  100.0  8.01e-229

STYLE PROVENANCE
----------------
Visual language is adopted from Codex's v4/v7 literature-atlas locus maps
(`Codex_v4_LOCUS_MAP_DEEPENED_2026-07-26/tools/build_locus_maps_v4.py`): the panel + genomic
kb axis, the strand-aware arrow polygon, the role palette (selected magenta / biosynthetic
green / transport blue / regulatory gold / other grey), and the explicit claim ceiling. The
new element here is the *comparative* stack (query over top-N references with homology ribbons),
which the atlas rendered query-only.

OUTPUTS (per region): `<stem>_kcb_locusmap.png`, `<stem>_kcb_locusmap.svg`, and a reproducible
`<stem>_kcb_locusmap_data.csv` sidecar (query_gene, ref_rank, ref_bgc, ref_compound,
subject_gene, pct_identity, pct_coverage, blast_score, evalue).

Everything degrades gracefully: no ZIP → parse a supplied txt; no matplotlib → clear message,
never a traceback; empty subject-coordinate tables (common in antiSMASH output) → subject genes
are aligned under their query partners.
"""
from __future__ import annotations

try:  # pragma: no cover - import shape depends on package vs direct-script use
    from .console import emit
except ImportError:  # direct execution: no parent package to resolve against.
    # v9.7.407: a bare-script run (documented for workbook_schema_check.py) has neither a
    # parent package NOR the bundle root on sys.path, so put the root there first.
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from mamey.console import emit

import argparse
import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
from .ziputil import regular_file_names
# v9.7.410 (CLAUDE_410 savefig OOM sweep): clamp publication DPI under the Agg pixel
# ceiling before every raster write. See mamey/render_safe.py::safe_savefig_dpi.
from .render_safe import safe_savefig_dpi as _safe_dpi

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon, Patch
    from matplotlib.lines import Line2D
    _HAVE_MPL = True
except ImportError as _e:  # figure deps are optional; clear message, not a traceback
    _HAVE_MPL = False
    _MPL_ERR = str(_e)


# --- palette (adopted from Codex v4 locus atlas) ------------------------------------------
INK = "#17212B"
MUTED = "#59636E"
PANEL = "#F4F7F6"
GRID = "#CAD4D1"
SELECTED = "#C02670"   # query gene participating in the selected (top) MIBiG comparison
BIOSYN = "#17785A"
TRANSPORT = "#2E6FA3"
REGULATORY = "#B7791F"
OTHER = "#9AA3AA"
REF_GENE = "#8794A0"   # reference subject gene body

ROLE_COLOR = {
    "SELECTED": SELECTED,
    "BIOSYNTHETIC": BIOSYN,
    "TRANSPORT": TRANSPORT,
    "REGULATORY": REGULATORY,
    "OTHER": OTHER,
}

CLAIM_CEILING = (
    "Ribbons show BLAST %identity (similarity, not identity of product). Colours mark "
    "antiSMASH feature classes and MIBiG-comparison genes. This is a class-level biosynthetic "
    "capacity hypothesis only — it does not establish product identity, expression, production, "
    "activity, novelty, or linkage beyond this region. Judgment deferred."
)


# --- data model ---------------------------------------------------------------------------
@dataclass
class QueryGene:
    gene_id: str
    start: int
    end: int
    strand: str
    annotation: str = ""


@dataclass
class BlastPair:
    query_gene: str
    subject_gene: str
    pct_identity: float
    blast_score: float
    pct_coverage: float
    evalue: str


@dataclass
class RefHit:
    rank: int
    bgc_id: str
    compound: str
    ref_type: str = ""
    n_proteins: int = 0
    cumulative_score: float = 0.0
    pairs: list[BlastPair] = field(default_factory=list)

    @property
    def median_identity(self) -> float:
        vals = sorted(p.pct_identity for p in self.pairs)
        if not vals:
            return 0.0
        n = len(vals)
        return vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2.0


@dataclass
class KCBRegion:
    contig: str
    query_genes: list[QueryGene]
    hits: list[RefHit]
    source_file: str = ""


# --- parsing ------------------------------------------------------------------------------
def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value))
    except Exception:
        return default


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(str(value)))
    except Exception:
        return default


def parse_kcb_txt(text: str) -> KCBRegion:
    """Parse an antiSMASH knownclusterblast/clusterblast .txt into a KCBRegion.

    Robust to the empty 'subject cluster' gene table (typical) and to both KCB (has 'Source:'
    lines) and plain clusterblast files.
    """
    lines = text.splitlines()

    contig = ""
    for line in lines[:5]:
        m = re.match(r"ClusterBlast scores for (\S+)", line)
        if m:
            contig = m.group(1)
            break

    # --- query cluster gene table ---
    query_genes: list[QueryGene] = []
    in_query = False
    for line in lines:
        if line.startswith("Table of genes") and "query cluster" in line:
            in_query = True
            continue
        if in_query:
            if not line.strip():
                if query_genes:
                    break
                continue
            if line.startswith("Significant hits") or line.startswith(">>"):
                break
            parts = line.split("\t")
            if len(parts) < 4:
                parts = line.split()
            if len(parts) >= 4 and parts[0]:
                gid = parts[0].strip()
                start, end = _int(parts[1]), _int(parts[2])
                strand = "-" if str(parts[3]).strip() in {"-", "-1"} else "+"
                annotation = parts[4].strip() if len(parts) > 4 else ""
                query_genes.append(QueryGene(gid, min(start, end), max(start, end), strand, annotation))

    # --- significant-hit compound index (rank -> bgc, compound) ---
    compound_by_rank: dict[int, tuple[str, str]] = {}
    in_sig = False
    for line in lines:
        if line.startswith("Significant hits"):
            in_sig = True
            continue
        if in_sig:
            if line.startswith("Details") or line.startswith(">>"):
                break
            m = re.match(r"\s*(\d+)\.\s+(\S+)\s+(.*)$", line)
            if m:
                compound_by_rank[_int(m.group(1))] = (m.group(2).strip(), m.group(3).strip())

    # --- per-hit detail blocks ---
    hits: list[RefHit] = []
    blocks = re.split(r"\n>>\s*\n?", "\n" + text)
    for block in blocks:
        head = re.match(r"\s*(\d+)\.\s+(\S+)", block)
        if not head:
            continue
        rank = _int(head.group(1))
        bgc_id = head.group(2).strip()
        source = re.search(r"^Source:\s*(.+)$", block, re.MULTILINE)
        ref_type = re.search(r"^Type:\s*(.+)$", block, re.MULTILINE)
        nprot = re.search(r"Number of proteins with BLAST hits[^:]*:\s*(\d+)", block)
        cum = re.search(r"Cumulative BLAST score:\s*([\d.]+)", block)
        compound = source.group(1).strip() if source else compound_by_rank.get(rank, ("", ""))[1]

        pairs: list[BlastPair] = []
        in_hits = False
        for line in block.splitlines():
            if line.startswith("Table of Blast hits"):
                in_hits = True
                continue
            if in_hits:
                if not line.strip():
                    continue
                if line.startswith("Table of") or line.startswith(">>"):
                    break
                cols = line.split("\t")
                if len(cols) < 6:
                    cols = line.split()
                if len(cols) >= 6:
                    pairs.append(
                        BlastPair(
                            query_gene=cols[0].strip(),
                            subject_gene=cols[1].strip(),
                            pct_identity=_num(cols[2]),
                            blast_score=_num(cols[3]),
                            pct_coverage=min(100.0, _num(cols[4])),
                            evalue=cols[5].strip(),
                        )
                    )
        if pairs:
            hits.append(
                RefHit(
                    rank=rank,
                    bgc_id=bgc_id,
                    compound=compound,
                    ref_type=ref_type.group(1).strip() if ref_type else "",
                    n_proteins=_int(nprot.group(1)) if nprot else len(pairs),
                    cumulative_score=_num(cum.group(1)) if cum else 0.0,
                    pairs=pairs,
                )
            )
    hits.sort(key=lambda h: h.rank)
    return KCBRegion(contig=contig, query_genes=query_genes, hits=hits, source_file="")


def find_kcb_files_in_zip(zip_path: Path) -> list[str]:
    """Return knownclusterblast (preferred) then clusterblast txt members inside a raw ZIP."""
    with zipfile.ZipFile(zip_path) as zf:
        names = regular_file_names(zf)
    kcb = sorted(n for n in names if "knownclusterblast/" in n.lower() and n.endswith(".txt")
                 and "clusters.txt" not in n.lower())
    cb = sorted(n for n in names if "clusterblast/" in n.lower() and "knownclusterblast" not in n.lower()
                and n.endswith(".txt") and "clusters.txt" not in n.lower())
    return kcb + cb


def _match_member(members: list[str], contig: str) -> Optional[str]:
    if not contig:
        return members[0] if members else None
    key = contig.lower()
    exact = [m for m in members if Path(m).name.lower().startswith(key + "_")
             or Path(m).name.lower() == key + ".txt"]
    if exact:
        return exact[0]
    loose = [m for m in members if key in m.lower()]
    return loose[0] if loose else None


def read_kcb_from_zip(zip_path: Path, contig: str = "") -> KCBRegion:
    members = find_kcb_files_in_zip(zip_path)
    if not members:
        raise FileNotFoundError(f"No knownclusterblast/clusterblast txt in {zip_path}")
    member = _match_member(members, contig)
    if member is None:
        raise KeyError(f"No knownclusterblast file matching '{contig}' in {zip_path}")
    with zipfile.ZipFile(zip_path) as zf:
        text = zf.read(member).decode("utf-8", errors="replace")
    region = parse_kcb_txt(text)
    region.source_file = f"{zip_path.name}::{member}"
    if not region.contig:
        region.contig = Path(member).name.split("_length")[0]
    return region


# --- optional GBK role coloring -----------------------------------------------------------
def _classify_role(gene_functions: str, gene_kind: str, product: str) -> str:
    text = " ".join((gene_functions, gene_kind, product)).lower()
    if "biosynthetic" in text:
        return "BIOSYNTHETIC"
    if "transport" in text or "abc transporter" in text:
        return "TRANSPORT"
    if "regulat" in text or "transcription" in text:
        return "REGULATORY"
    return "OTHER"


def load_gbk_roles(zip_path: Path, query_gene_ids: set[str]) -> dict[str, str]:
    """Best-effort: scan region GBKs in the ZIP for the query locus_tags and classify roles
    from gene_functions/gene_kind/product. Returns {} on any failure (never raises)."""
    roles: dict[str, str] = {}
    if not query_gene_ids:
        return roles
    try:
        with zipfile.ZipFile(zip_path) as zf:
            gbks = [n for n in regular_file_names(zf) if n.lower().endswith((".gbk", ".gb"))]
            probe = next(iter(query_gene_ids))
            probe_b = f'/locus_tag="{probe}"'.encode()
            for name in gbks:
                data = zf.read(name)
                if probe_b not in data:
                    continue
                roles.update(_roles_from_gbk_text(data.decode("utf-8", errors="replace"), query_gene_ids))
                if query_gene_ids.issubset(roles.keys()):
                    break
    except Exception:
        return {}
    return roles


def _roles_from_gbk_text(text: str, wanted: set[str]) -> dict[str, str]:
    roles: dict[str, str] = {}
    cur_locus = ""
    cur_kind: list[str] = []
    cur_func: list[str] = []
    cur_prod: list[str] = []

    def flush():
        if cur_locus and cur_locus in wanted:
            roles[cur_locus] = _classify_role(" ".join(cur_func), " ".join(cur_kind), " ".join(cur_prod))

    in_features = False
    for line in text.splitlines():
        if line.startswith("FEATURES"):
            in_features = True
            continue
        if line.startswith("ORIGIN"):
            break
        if not in_features:
            continue
        if re.match(r"^ {5}CDS\s", line):
            flush()
            cur_locus, cur_kind, cur_func, cur_prod = "", [], [], []
            continue
        m = re.match(r'^ {21}/locus_tag="?([^"]+)"?', line)
        if m:
            cur_locus = m.group(1).strip()
            continue
        m = re.match(r'^ {21}/gene_kind="?([^"]+)"?', line)
        if m:
            cur_kind.append(m.group(1))
            continue
        m = re.match(r'^ {21}/gene_functions="?(.*)$', line)
        if m:
            cur_func.append(m.group(1).rstrip('"'))
            continue
        m = re.match(r'^ {21}/product="?(.*)$', line)
        if m:
            cur_prod.append(m.group(1).rstrip('"'))
    flush()
    return roles


# --- rendering ----------------------------------------------------------------------------
def _arrow_polygon(x0: float, x1: float, y: float, h: float, strand: str, tip_frac: float = 0.4):
    """Strand-aware gene arrow as a list of (x, y) vertices (data coords), Codex-atlas shape."""
    x0, x1 = min(x0, x1), max(x0, x1)
    span = x1 - x0
    tip = min(span, span * tip_frac)
    b = h / 2.0
    if strand == "-":
        return [(x1, y - b), (x0 + tip, y - b), (x0, y), (x0 + tip, y + b), (x1, y + b)]
    return [(x0, y - b), (x1 - tip, y - b), (x1, y), (x1 - tip, y + b), (x0, y + b)]


def _identity_color(pct: float):
    """Sequential green shading by %identity (30->100), matching the atlas green family."""
    frac = max(0.0, min(1.0, (pct - 30.0) / 70.0))
    # interpolate PANEL-ish grey-green -> deep BIOSYN green
    c0 = (0.86, 0.93, 0.90)
    c1 = (0.09, 0.47, 0.35)
    return tuple(c0[i] + (c1[i] - c0[i]) * frac for i in range(3))


def render_region(
    region: KCBRegion,
    out_dir: Path,
    stem: str,
    top_n: int = 6,
    roles: Optional[dict[str, str]] = None,
    strain_id: str = "",
    bgc_id: str = "",
    products: str = "",
) -> dict[str, Any]:
    """Render one comparative locus map (PNG + SVG) and its data CSV. Returns a metrics dict."""
    if not _HAVE_MPL:
        raise RuntimeError(
            f"kcb-locusmap needs matplotlib (install the figures extra). Import error: {_MPL_ERR}"
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    roles = roles or {}
    hits = region.hits[:top_n]
    qgenes = region.query_genes

    # genomic scale from query genes
    if qgenes:
        qmin = min(g.start for g in qgenes)
        qmax = max(g.end for g in qgenes)
    else:
        qmin, qmax = 0, 1
    span = max(1, qmax - qmin)
    pad = span * 0.03

    # centre x of each query gene (for aligning subject genes beneath)
    q_by_id = {g.gene_id: g for g in qgenes}
    genes_with_hits = {p.query_gene for h in hits for p in h.pairs}
    anchor_hit_genes = {p.query_gene for p in hits[0].pairs} if hits else set()

    fig_h = 2.4 + 1.15 * len(hits)
    fig, ax = plt.subplots(figsize=(13.2, fig_h), dpi=200)

    track_gap = 1.55
    arrow_h = 0.42
    y_query = (len(hits)) * track_gap
    ax.set_xlim(qmin - pad, qmax + pad)
    ax.set_ylim(-1.0, y_query + 1.05)
    ax.axis("off")

    # panel background
    ax.add_patch(Polygon(
        [(qmin - pad, -0.95), (qmax + pad, -0.95), (qmax + pad, y_query + 0.72), (qmin - pad, y_query + 0.72)],
        closed=True, facecolor=PANEL, edgecolor=GRID, linewidth=1.0, zorder=0))

    # --- query track ---
    # v9.7.371 fix: the first branch was tautological whenever roles is empty (the common case --
    # always true for render_from_text/--kcb-txt calls, and whenever load_gbk_roles can't resolve
    # the query locus tags) -- roles.get(x, "OTHER") trivially equals "OTHER" when roles is {},
    # collapsing the condition to just `g.gene_id in genes_with_hits`. That colored EVERY gene
    # matching ANY shown reference SELECTED (magenta), making the else branch's intended
    # anchor-vs-secondary-reference distinction (SELECTED vs BIOSYNTHETIC) unreachable --
    # over-representing how many genes support the TOP MIBiG comparison on a claim-safety-
    # relevant figure. The else branch below already handles the `not roles` case correctly.
    for g in qgenes:
        if roles:
            role = "SELECTED" if g.gene_id in anchor_hit_genes else roles.get(g.gene_id, "OTHER")
        else:
            role = ("SELECTED" if g.gene_id in anchor_hit_genes
                    else "BIOSYNTHETIC" if g.gene_id in genes_with_hits else "OTHER")
        color = ROLE_COLOR.get(role, OTHER)
        ax.add_patch(Polygon(_arrow_polygon(g.start, g.end, y_query, arrow_h, g.strand),
                             closed=True, facecolor=color, edgecolor="white", linewidth=0.7, zorder=3))
    ax.text(qmin - pad, y_query + 0.62,
            f"QUERY  {region.contig}", fontsize=9, fontweight="bold", color=INK, va="bottom")

    # --- reference tracks + homology ribbons ---
    for i, hit in enumerate(hits):
        y_ref = (len(hits) - 1 - i) * track_gap
        # label (comfortably above/below the arrow lane)
        comp = hit.compound if len(hit.compound) <= 40 else hit.compound[:37] + "..."
        ax.text(qmin - pad, y_ref + 0.40,
                f"{hit.rank:>2}. {hit.bgc_id}  {comp}",
                fontsize=7.8, fontweight="bold", color=INK, va="bottom")
        ax.text(qmin - pad, y_ref - 0.42,
                f"{len(hit.pairs)} genes | median {hit.median_identity:.0f}% id",
                fontsize=6.6, color=MUTED, va="top")
        for p in hit.pairs:
            qg = q_by_id.get(p.query_gene)
            if qg is None:
                continue
            cx = (qg.start + qg.end) / 2.0
            w = max(span * 0.012, (qg.end - qg.start))
            sx0, sx1 = cx - w / 2.0, cx + w / 2.0
            col = _identity_color(p.pct_identity)
            # homology ribbon (trapezoid) query-bottom -> subject-top
            ax.add_patch(Polygon(
                [(qg.start, y_query - arrow_h / 2.0), (qg.end, y_query - arrow_h / 2.0),
                 (sx1, y_ref + arrow_h / 2.0), (sx0, y_ref + arrow_h / 2.0)],
                closed=True, facecolor=col, edgecolor="none",
                alpha=0.28 + 0.42 * max(0.0, min(1.0, (p.pct_identity - 30) / 70)), zorder=1))
            # subject gene arrow (aligned beneath its query partner)
            ax.add_patch(Polygon(_arrow_polygon(sx0, sx1, y_ref, arrow_h, qg.strand),
                                 closed=True, facecolor=col, edgecolor=INK, linewidth=0.5, zorder=3))
            ax.text(cx, y_ref, f"{p.pct_identity:.0f}", fontsize=5.6, color="white",
                    ha="center", va="center", zorder=4)

    # --- title / legend / caption ---
    title = f"KnownClusterBlast comparative locus map"
    ident = " ".join(x for x in [strain_id, bgc_id] if x) or region.contig
    if products:
        ident += f" | {products}"
    fig.suptitle(f"{title} — {ident}", fontsize=12.5, fontweight="bold", color=INK, y=0.995)

    legend_handles = [
        Patch(facecolor=SELECTED, label="Selected MIBiG-comparison gene"),
        Patch(facecolor=BIOSYN, label="Biosynthetic CDS"),
        Patch(facecolor=TRANSPORT, label="Transport"),
        Patch(facecolor=REGULATORY, label="Regulatory"),
        Patch(facecolor=OTHER, label="Other CDS"),
        Line2D([0], [0], color=_identity_color(90), lw=6, label="Homology ribbon (shaded by %identity)"),
    ]
    ax.legend(handles=legend_handles, loc="upper center", bbox_to_anchor=(0.5, -0.02),
              ncol=3, fontsize=7, frameon=False, handlelength=1.6)

    fig.text(0.5, 0.005, CLAIM_CEILING, ha="center", va="bottom", fontsize=6.2,
             color=MUTED, wrap=True)
    fig.subplots_adjust(left=0.16, right=0.99, top=0.90, bottom=0.16)

    png = out_dir / f"{stem}_kcb_locusmap.png"
    svg = out_dir / f"{stem}_kcb_locusmap.svg"
    fig.savefig(png, dpi=_safe_dpi(fig, 200))
    fig.savefig(svg)
    plt.close(fig)

    csv_path = out_dir / f"{stem}_kcb_locusmap_data.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        w = _SafeWriter(fh)
        w.writerow(["query_gene", "ref_rank", "ref_bgc", "ref_compound",
                    "subject_gene", "pct_identity", "pct_coverage", "blast_score", "evalue"])
        for hit in hits:
            for p in hit.pairs:
                w.writerow([p.query_gene, hit.rank, hit.bgc_id, hit.compound,
                            p.subject_gene, f"{p.pct_identity:.1f}", f"{p.pct_coverage:.1f}",
                            f"{p.blast_score:.0f}", p.evalue])

    return {
        "png": str(png),
        "svg": str(svg),
        "csv": str(csv_path),
        "contig": region.contig,
        "query_genes": len(qgenes),
        "reference_clusters": len(hits),
        "gene_pairs": sum(len(h.pairs) for h in hits),
        "top_anchor": hits[0].bgc_id if hits else "",
        "top_anchor_compound": hits[0].compound if hits else "",
    }


def render_from_zip(
    zip_path: Path,
    contig: str,
    out_dir: Path,
    top_n: int = 6,
    strain_id: str = "",
    bgc_id: str = "",
    products: str = "",
    stem: str = "",
) -> dict[str, Any]:
    region = read_kcb_from_zip(zip_path, contig)
    roles = load_gbk_roles(zip_path, {g.gene_id for g in region.query_genes})
    stem = stem or (bgc_id or region.contig or contig or "region")
    return render_region(region, out_dir, stem, top_n=top_n, roles=roles,
                         strain_id=strain_id, bgc_id=bgc_id, products=products)


def render_from_text(
    text: str,
    out_dir: Path,
    stem: str = "region",
    top_n: int = 6,
    strain_id: str = "",
    bgc_id: str = "",
    products: str = "",
) -> dict[str, Any]:
    region = parse_kcb_txt(text)
    return render_region(region, out_dir, stem, top_n=top_n,
                         strain_id=strain_id, bgc_id=bgc_id, products=products)


# --- CLI (standalone; wired into `figures` via KCB_LOCUSMAP_HOOK.md, no cli.py edit) -------
def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mamey.kcb_locusmap",
        description="Offline KnownClusterBlast/ClusterBlast comparative locus map (matplotlib).")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--zip", type=Path, help="Raw antiSMASH ZIP (reads knownclusterblast/*.txt).")
    src.add_argument("--kcb-txt", type=Path, help="A single knownclusterblast/clusterblast .txt file.")
    p.add_argument("--contig", default="", help="Contig/region key, e.g. NODE_106 (ZIP mode).")
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--top-n", type=int, default=6)
    p.add_argument("--strain-id", default="")
    p.add_argument("--bgc-id", default="")
    p.add_argument("--products", default="")
    p.add_argument("--stem", default="")
    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if not _HAVE_MPL:
        emit(f"[kcb-locusmap] matplotlib unavailable: {_MPL_ERR}\n"
              f"Install the figures extra:  pip install -e '.[all]'")
        return 2
    if args.zip:
        metrics = render_from_zip(
            args.zip, args.contig, args.out_dir, top_n=args.top_n,
            strain_id=args.strain_id, bgc_id=args.bgc_id, products=args.products, stem=args.stem)
    else:
        text = args.kcb_txt.read_text(encoding="utf-8", errors="replace")
        stem = args.stem or args.kcb_txt.stem
        metrics = render_from_text(
            text, args.out_dir, stem=stem, top_n=args.top_n,
            strain_id=args.strain_id, bgc_id=args.bgc_id, products=args.products)
    emit(f"[kcb-locusmap] {metrics['png']}", f"  contig={metrics['contig']} query_genes={metrics['query_genes']} refs={metrics['reference_clusters']} pairs={metrics['gene_pairs']} anchor={metrics['top_anchor']} ({metrics['top_anchor_compound']})", sep="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
