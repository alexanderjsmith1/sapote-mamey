"""Evidence-dense, package-native locus maps (v8).

v8 restores the decision-relevant layers that the compact compile-report map
cannot carry safely on one arrow track:

* every exact locus tag is visible (dense loci use a leader-line label rail);
* one deterministic MIBiG comparator is selected from the sealed per-gene table;
* every comparator-selected gene has visible identity/coverage metrics;
* antiSMASH domain, HMM, module and motif evidence is summarized in a separate
  collision-managed panel and preserved in full in the companion CSV;
* PNG, SVG, rich CSV and a machine-readable preflight receipt are emitted.

The renderer is non-scoring. Similarity is navigation evidence, never exact
product identity, expression, production, activity, novelty or physical linkage.
All inputs are package-relative; no workspace path is serialized into outputs.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field
from hashlib import sha256
from pathlib import Path, PurePosixPath
from statistics import median
from typing import Any, Iterable, Mapping
import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import sys
import json
import math
import textwrap
import xml.etree.ElementTree as ET

try:
    import matplotlib
    matplotlib.use("Agg")
    matplotlib.rcParams["svg.hashsalt"] = "sapote-mamey-locus-map-v8"
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch, Polygon
    from matplotlib.ticker import FuncFormatter, MaxNLocator
    _HAVE_MPL = True
except ImportError as _e:  # pragma: no cover - optional dependency path
    _HAVE_MPL = False
    _MPL_ERR = str(_e)

from .locus_map import classify
from .kcb_locusmap import (
    BIOSYN,
    GRID,
    INK,
    MUTED,
    OTHER,
    PANEL,
    REGULATORY,
    SELECTED,
    TRANSPORT,
    _arrow_polygon,
)
# v9.7.410 (CLAUDE_410 savefig OOM sweep): clamp publication DPI under the Agg pixel
# ceiling before every raster write. See mamey/render_safe.py::safe_savefig_dpi.
from .render_safe import safe_savefig_dpi as _safe_dpi


SCHEMA_VERSION = "sapote-locus-map-v8-receipt-v1"
MAX_LABELS_PER_LANE = 80
CLAIM_CEILING = (
    "Comparator and per-gene values show similarity, not product identity. "
    "Domain/HMM/motif calls show biosynthetic capacity only. This figure does not establish "
    "expression, production, activity, novelty, a biological merge/split, or physical linkage. "
    "Judgment deferred."
)


class FigureReceiptMismatch(ValueError):
    """Typed refusal for a V8 receipt that does not bind its rendered triple."""

    code = "FIGURE_RECEIPT_MISMATCH"

    def __init__(self, details: Iterable[str]):
        self.details = tuple(details)
        super().__init__(f"{self.code}: {'; '.join(self.details)}")


@dataclass
class ComparatorGene:
    locus_tag: str
    subject_gene: str = ""
    pct_identity: float | None = None
    pct_coverage: float | None = None
    blast_score: float | None = None
    evalue: str = ""


@dataclass
class Comparator:
    accession: str = ""
    compound: str = ""
    genes: dict[str, ComparatorGene] = field(default_factory=dict)
    median_identity: float | None = None


@dataclass
class GeneRow:
    locus_tag: str
    order: int
    start: int
    end: int
    strand: int
    length_aa: int
    gene_functions: str
    role: str
    color: str
    is_core: bool
    domains: list[str] = field(default_factory=list)
    hmm: list[str] = field(default_factory=list)
    modules: list[str] = field(default_factory=list)
    motifs: list[str] = field(default_factory=list)


def _float(value: Any) -> float | None:
    try:
        text = str(value).strip()
        return float(text) if text else None
    except (TypeError, ValueError):
        return None


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return default


def _first(row: dict[str, Any], names: Iterable[str], default: str = "") -> str:
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return str(value).strip()
    return default


def _tokens(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        raw = [str(v).strip() for v in value]
    else:
        text = str(value).strip()
        if not text:
            return []
        for sep in (";", "|"):
            if sep in text:
                raw = [x.strip() for x in text.split(sep)]
                break
        else:
            raw = [text]
    out: list[str] = []
    seen: set[str] = set()
    for token in raw:
        if token and token not in seen:
            seen.add(token)
            out.append(token)
    return out


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def validate_locus_map_v8_receipt(
    receipt_path: Path | str,
    *,
    expected_bgc_id: str | None = None,
) -> dict[str, Any]:
    """Validate one V8 receipt and its package-local PNG/SVG/CSV outputs.

    The producer's receipt remains the sole serialized evidence object. This
    reader returns that object only after every binding and semantic check
    passes; otherwise it raises the typed ``FIGURE_RECEIPT_MISMATCH`` refusal.
    """
    path = Path(receipt_path)
    findings: list[str] = []
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="strict"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise FigureReceiptMismatch([f"receipt_unreadable={type(exc).__name__}"]) from exc
    if not isinstance(payload, dict):
        raise FigureReceiptMismatch(["receipt_not_object"])

    bgc_id = payload.get("bgc_id")
    if payload.get("schema_version") != SCHEMA_VERSION:
        findings.append("schema_version")
    if payload.get("renderer") != "v8":
        findings.append("renderer")
    if payload.get("status") != "READY":
        findings.append("status")
    if not isinstance(bgc_id, str) or not bgc_id:
        findings.append("bgc_id")
    if expected_bgc_id is not None and bgc_id != expected_bgc_id:
        findings.append("bgc_id_expected")
    if payload.get("claim_ceiling") != CLAIM_CEILING:
        findings.append("claim_ceiling")

    gene_count = payload.get("gene_count")
    comparator = payload.get("selected_comparator")
    comparator_count = comparator.get("supporting_exact_genes") if isinstance(comparator, dict) else None
    if not isinstance(gene_count, int) or gene_count <= 0:
        findings.append("gene_count")
    if payload.get("exact_labels_displayed") != gene_count:
        findings.append("exact_labels_displayed")
    if payload.get("exact_labels_suppressed") != 0:
        findings.append("exact_labels_suppressed")
    if not isinstance(comparator_count, int) or comparator_count < 0:
        findings.append("supporting_exact_genes")
    if payload.get("selected_genes_displayed_in_evidence_panel") != comparator_count:
        findings.append("selected_genes_displayed")
    if payload.get("full_evidence_preserved_in_csv") is not True:
        findings.append("full_evidence_preserved_in_csv")

    outputs = payload.get("outputs")
    integrity = payload.get("output_integrity")
    expected_names = {
        "png": f"{bgc_id}_locus_map.png",
        "svg": f"{bgc_id}_locus_map.svg",
        "csv": f"{bgc_id}_locus_map_data.csv",
    }
    resolved: dict[str, Path] = {}
    for kind, expected_name in expected_names.items():
        name = outputs.get(kind) if isinstance(outputs, dict) else None
        record = integrity.get(kind) if isinstance(integrity, dict) else None
        locator = PurePosixPath(name) if isinstance(name, str) else None
        if locator is None or locator.is_absolute() or len(locator.parts) != 1 or name != expected_name:
            findings.append(f"{kind}_locator")
            continue
        candidate = path.parent / name
        if candidate.is_symlink() or not candidate.is_file():
            findings.append(f"{kind}_missing_or_symlink")
            continue
        resolved[kind] = candidate
        if not isinstance(record, dict) or record.get("path") != name:
            findings.append(f"{kind}_integrity_record")
            continue
        if record.get("bytes") != candidate.stat().st_size:
            findings.append(f"{kind}_bytes")
        if record.get("sha256") != _sha(candidate):
            findings.append(f"{kind}_sha256")

    png_path = resolved.get("png")
    if png_path is not None and not png_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
        findings.append("png_signature")
    svg_path = resolved.get("svg")
    if svg_path is not None:
        try:
            if not ET.parse(svg_path).getroot().tag.endswith("svg"):
                findings.append("svg_root")
        except (OSError, ET.ParseError):
            findings.append("svg_parse")
    csv_path = resolved.get("csv")
    if csv_path is not None:
        try:
            rows = _read_csv(csv_path)
            if len(rows) != gene_count:
                findings.append("csv_gene_count")
            if any(row.get("label_displayed") != "YES" for row in rows):
                findings.append("csv_labels")
            selected_rows = [row for row in rows if row.get("selected_comparator") == "YES"]
            if len(selected_rows) != comparator_count:
                findings.append("csv_comparator_count")
            accession = comparator.get("accession") if isinstance(comparator, dict) else None
            if any(row.get("comparator_accession") != accession for row in selected_rows):
                findings.append("csv_comparator_accession")
        except (OSError, csv.Error, UnicodeError):
            findings.append("csv_parse")

    if findings:
        raise FigureReceiptMismatch(findings)
    return payload


def _gene_roster_from_csv(path: Path) -> list[dict[str, Any]]:
    """Return the exact ordered gene roster represented by the companion CSV."""
    rows = _read_csv(path)
    return [
        {"row": index, "locus_tag": str(row.get("locus_tag", "")), "order": _int(row.get("order"), -1)}
        for index, row in enumerate(rows, 1)
    ]


def _gene_roster_sha256(roster: list[dict[str, Any]]) -> str:
    payload = json.dumps(roster, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(payload.encode("utf-8")).hexdigest()


def validate_v8_gene_roster(receipt: Mapping[str, Any], csv_path: Path | str) -> list[str]:
    """Validate that a v8 receipt's hash-bound roster exactly matches its CSV."""
    path = Path(csv_path)
    if not path.is_file():
        return ["V8_CSV_ABSENT"]
    roster = _gene_roster_from_csv(path)
    binding = receipt.get("gene_roster")
    outputs = receipt.get("outputs")
    issues: list[str] = []
    if not isinstance(binding, Mapping):
        return ["V8_GENE_ROSTER_BINDING_ABSENT"]
    if not isinstance(outputs, Mapping) or outputs.get("csv_sha256") != _sha(path):
        issues.append("V8_CSV_HASH_MISMATCH")
    if binding.get("row_count") != len(roster):
        issues.append("V8_GENE_ROSTER_ROW_COUNT_MISMATCH")
    if binding.get("sha256") != _gene_roster_sha256(roster):
        issues.append("V8_GENE_ROSTER_HASH_MISMATCH")
    return issues


def _package_file(pkg: Path, suffix: str) -> Path | None:
    matches = sorted(pkg.glob(f"*{suffix}"))
    return matches[0] if matches else None


def _read_csv(path: Path | None) -> list[dict[str, str]]:
    if path is None or not path.is_file():
        return []
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))
    except (OSError, csv.Error, UnicodeDecodeError):
        return []


def _role_class(blob: str, is_core: bool) -> tuple[str, str]:
    low = blob.lower()
    if "transport" in low or "abc transporter" in low or "mfs" in low:
        return "transport", TRANSPORT
    if "regulat" in low or "transcription" in low or "tetR".lower() in low:
        return "regulatory", REGULATORY
    if is_core or "biosynthetic" in low:
        return "biosynthetic", BIOSYN
    return "other", OTHER


def load_genes(package_dir: Path, bgc_id: str) -> tuple[list[GeneRow], Path | None]:
    """Load exact genes from the richest available current-run table.

    The normalized ``*_cds_table.csv`` is written with gene context before the
    in-run locus-map stage.  The richer all-BGC gene table is written later, so
    use it when present and otherwise fall back to the normalized table rather
    than treating a current run as gene-empty.
    """
    pkg = Path(package_dir)
    source = _package_file(pkg, "_gene_by_gene_all_bgcs.csv")
    if source is None:
        source = _package_file(pkg, "_cds_table.csv")
    rows = _read_csv(source)
    genes: list[GeneRow] = []
    for row in rows:
        if _first(row, ("bgc_id", "BGC_ID")) != bgc_id:
            continue
        locus = _first(row, ("locus_tag", "locus", "gene"))
        start_text = _first(row, ("gene_start", "start", "cds_start"))
        end_text = _first(row, ("gene_end", "end", "cds_end"))
        if not locus or not start_text or not end_text:
            continue
        try:
            start = int(float(start_text))
            end = int(float(end_text))
        except ValueError:
            continue
        if end < start:
            start, end = end, start
        strand_text = _first(row, ("strand", "Strand"), "+")
        strand = -1 if strand_text in {"-", "-1"} else 1
        domains = _tokens(_first(row, ("sec_met_domains", "aSDomains", "domain_annotations")))
        function = _first(
            row, ("gene_function_inference", "gene_functions", "product_qualifier", "product")
        )
        blob = " ".join(domains + [function]).strip()
        role_name, _palette_color, is_core = classify(blob)
        role, color = _role_class(blob + " " + role_name, bool(is_core))
        genes.append(GeneRow(
            locus_tag=locus,
            order=_int(row.get("order"), len(genes) + 1),
            start=start,
            end=end,
            strand=strand,
            length_aa=_int(_first(row, ("aa_length", "length_aa", "length"))),
            gene_functions=function,
            role=role,
            color=color,
            is_core=bool(is_core),
            domains=domains,
        ))
    genes.sort(key=lambda g: (g.start, g.end, g.locus_tag))
    for index, gene in enumerate(genes, 1):
        gene.order = index
    return genes, source


def _best_gene_row(rows: list[dict[str, str]]) -> dict[str, str]:
    def key(row: dict[str, str]) -> tuple[float, float, float, str]:
        return (
            _float(row.get("blast_score")) or -1.0,
            _float(row.get("pct_identity")) or -1.0,
            _float(row.get("pct_coverage")) or -1.0,
            row.get("subject_gene", ""),
        )
    return max(rows, key=key)


def choose_comparator(package_dir: Path, bgc_id: str) -> tuple[Comparator, Path | None]:
    """Choose the comparator with most unique query genes, then median identity and rank."""
    pkg = Path(package_dir)
    source = _package_file(pkg, "_3_mibig_per_gene.csv")
    rows = [row for row in _read_csv(source) if _first(row, ("bgc_id", "BGC_ID")) == bgc_id]
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        accession = _first(row, ("mibig_accession", "reference", "ref_bgc"))
        if accession:
            grouped[(accession, row.get("mibig_compound", ""))].append(row)
    grouped = {
        key: grows for key, grows in grouped.items()
        if any(str(row.get("query_gene", "")).strip() for row in grows)
    }
    if not grouped:
        return Comparator(), source

    def group_key(item: tuple[tuple[str, str], list[dict[str, str]]]):
        (accession, _compound), grows = item
        unique = {row.get("query_gene", "") for row in grows if row.get("query_gene")}
        identities = [v for v in (_float(row.get("pct_identity")) for row in grows) if v is not None]
        ranks = [_int(row.get("reference_rank"), 10**9) for row in grows]
        return (-len(unique), -(median(identities) if identities else -1.0), min(ranks or [10**9]), accession)

    (accession, compound), selected_rows = min(grouped.items(), key=group_key)
    by_gene: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in selected_rows:
        gene = row.get("query_gene", "").strip()
        if gene:
            by_gene[gene].append(row)
    genes: dict[str, ComparatorGene] = {}
    for gene, grows in by_gene.items():
        row = _best_gene_row(grows)
        genes[gene] = ComparatorGene(
            locus_tag=gene,
            subject_gene=row.get("subject_gene", ""),
            pct_identity=_float(row.get("pct_identity")),
            pct_coverage=_float(row.get("pct_coverage")),
            blast_score=_float(row.get("blast_score")),
            evalue=row.get("evalue", ""),
        )
    identities = [g.pct_identity for g in genes.values() if g.pct_identity is not None]
    return Comparator(
        accession=accession,
        compound=compound,
        genes=genes,
        median_identity=median(identities) if identities else None,
    ), source


def _attach_auxiliary(package_dir: Path, bgc_id: str, genes: list[GeneRow]) -> dict[str, Path]:
    pkg = Path(package_dir)
    by_gene = {gene.locus_tag: gene for gene in genes}
    specs = (
        ("_3_antismash_hmm.csv", "domain_name", "hmm"),
        ("_3_antismash_modules.csv", "domain", "modules"),
        ("_3_antismash_motifs.csv", "motif", "motifs"),
        ("_domains.csv", "domain", "hmm"),
    )
    used: dict[str, Path] = {}
    for suffix, value_col, target in specs:
        path = _package_file(pkg, suffix)
        if path is None:
            continue
        used[suffix] = path
        for row in _read_csv(path):
            if _first(row, ("bgc_id", "BGC_ID")) != bgc_id:
                continue
            locus = _first(row, ("locus_tag", "gene", "query_gene"))
            value = row.get(value_col, "").strip()
            gene = by_gene.get(locus)
            if gene is not None and value:
                collection: list[str] = getattr(gene, target)
                if value not in collection:
                    collection.append(value)
    return used


def _compact_evidence(gene: GeneRow, max_chars: int = 86) -> tuple[str, int]:
    prioritized: list[str] = []
    for prefix, values in (("M", gene.modules), ("H", gene.hmm), ("m", gene.motifs), ("D", gene.domains)):
        for value in values:
            token = f"{prefix}:{value}"
            if token not in prioritized:
                prioritized.append(token)
    if not prioritized:
        prioritized = [f"role:{gene.role}"]
    shown: list[str] = []
    used = 0
    for token in prioritized:
        addition = len(token) + (3 if shown else 0)
        if shown and used + addition > max_chars:
            break
        shown.append(token)
        used += addition
    hidden = len(prioritized) - len(shown)
    text = " · ".join(shown)
    if hidden:
        text += f" · +{hidden} more (CSV)"
    return text, hidden


def _display_name(text: str, max_chars: int = 78) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= max_chars else text[: max_chars - 1] + "…"


def _format_metric(value: float | None) -> str:
    return "—" if value is None else f"{value:.0f}%"


def _format_coverage(value: float | None) -> str:
    """Preserve source-reported coverage; mark values above 100 instead of capping."""
    if value is None:
        return "— cov"
    marker = "*" if value > 100 else ""
    return f"{value:.0f}% cov{marker}"


def _label_lane_count(gene_count: int) -> int:
    """Return enough lanes to keep each exact-label rail within its tested density."""
    return max(1, math.ceil(gene_count / MAX_LABELS_PER_LANE))


def _draw_label_rail(ax, genes: list[GeneRow], minx: float, maxx: float) -> int:
    """Draw every exact tag across adaptive, vertically separated label lanes."""
    n = len(genes)
    if not n:
        return 1
    lanes = _label_lane_count(n)
    span = max(maxx - minx, 1.0)
    left = minx + span * 0.01
    right = maxx - span * 0.01
    step = 0.0 if n == 1 else (right - left) / (n - 1)
    for index, gene in enumerate(genes):
        slot = left + step * index
        mid = (gene.start + gene.end) / 2.0
        lane = index % lanes
        baseline = -0.53 - lane * 0.82
        ax.plot([mid, slot], [0.28, baseline + 0.07], color="#8A949C", lw=0.5, zorder=1)
        ax.text(slot, baseline, gene.locus_tag, ha="center", va="top", rotation=90,
                fontsize=6.6, fontweight="bold", color=INK, clip_on=False)
    return lanes


def _draw_map_axis(ax, genes: list[GeneRow], comparator: Comparator, title: str) -> int:
    minx = min(g.start for g in genes)
    maxx = max(g.end for g in genes)
    span = max(maxx - minx, 1)
    pad = max(span * 0.035, 300.0)
    ax.set_facecolor(PANEL)
    ax.axhline(0.55, color="#65727A", lw=0.75, zorder=0)
    for gene in genes:
        selected = gene.locus_tag in comparator.genes
        color = SELECTED if selected else gene.color
        patch = Polygon(
            _arrow_polygon(gene.start, gene.end, 0.55, 0.38, "+" if gene.strand == 1 else "-",
                            tip_frac=0.28),
            closed=True, facecolor=color, edgecolor="#1B1F23", linewidth=1.1, zorder=3,
        )
        patch.set_joinstyle("round")
        patch.set_capstyle("round")
        ax.add_patch(patch)
    label_lanes = _draw_label_rail(ax, genes, minx, maxx)
    ax.set_xlim(minx - pad, maxx + pad)
    ax.set_ylim(-1.25 - (label_lanes - 1) * 0.82, 1.18)
    ax.set_yticks([])
    ax.xaxis.set_major_locator(MaxNLocator(nbins=6, prune="both"))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x/1000:.1f} kb"))
    ax.tick_params(axis="x", labelsize=7.2, pad=3)
    ax.set_title(title, fontsize=10.3, fontweight="bold", color=INK,
                 loc="left", pad=7, y=1.075)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    return label_lanes


def _draw_evidence_axis(ax, genes: list[GeneRow], comparator: Comparator) -> tuple[int, int]:
    ax.axis("off")
    selected = [gene for gene in genes if gene.locus_tag in comparator.genes]
    if not selected:
        ax.text(0.01, 0.93, "Comparator per-gene evidence", fontsize=10.5,
                fontweight="bold", color=INK, transform=ax.transAxes)
        ax.text(0.01, 0.76, "No package-bound MIBiG comparator rows for this locus.",
                fontsize=8.5, color=MUTED, transform=ax.transAxes)
        return 0, 0

    ax.text(0.01, 0.97,
            f"Selected comparator per-gene evidence — {len(selected)} exact genes",
            fontsize=10.5, fontweight="bold", color=INK, transform=ax.transAxes)
    columns = 2 if len(selected) > 10 else 1
    rows_per_col = math.ceil(len(selected) / columns)
    top = 0.89
    bottom = 0.05
    row_h = (top - bottom) / max(rows_per_col, 1)
    hidden_total = 0
    for index, gene in enumerate(selected):
        col = index // rows_per_col
        row = index % rows_per_col
        x = 0.01 + col * 0.5
        y = top - row * row_h
        metric = comparator.genes[gene.locus_tag]
        ax.text(x, y, gene.locus_tag, fontsize=7.8, fontweight="bold", color=SELECTED,
                va="top", transform=ax.transAxes)
        ax.text(x + 0.115, y,
                f"{_format_metric(metric.pct_identity)} id / {_format_coverage(metric.pct_coverage)}",
                fontsize=7.3, color=INK, va="top", transform=ax.transAxes)
        evidence, hidden = _compact_evidence(gene)
        hidden_total += hidden
        wrapped = textwrap.fill(evidence, width=74 if columns == 2 else 150,
                                break_long_words=False, break_on_hyphens=False)
        ax.text(x + 0.115, y - min(0.040, row_h * 0.42), wrapped, fontsize=6.2,
                color=MUTED, va="top", linespacing=1.05, transform=ax.transAxes)
        ax.plot([x, x + 0.47], [y - row_h * 0.78, y - row_h * 0.78],
                color="#E1E6E4", lw=0.35, transform=ax.transAxes, clip_on=False)
    if any(
        comparator.genes[gene.locus_tag].pct_coverage is not None
        and comparator.genes[gene.locus_tag].pct_coverage > 100
        for gene in selected
    ):
        ax.text(0.99, 0.01, "* source-reported coverage shown uncapped", fontsize=6.2,
                color=MUTED, ha="right", va="bottom", transform=ax.transAxes)
    return len(selected), hidden_total


def render_bgc_v8(
    package_dir: Path | str,
    bgc_id: str,
    *,
    out_dir: Path | str | None = None,
    strain_id: str = "",
    node: str = "",
    region: str = "",
    products: str = "",
) -> dict[str, Any]:
    """Render one package-bound v8 map and return its receipt dictionary."""
    if not _HAVE_MPL:
        raise RuntimeError(f"locus map v8 needs matplotlib: {_MPL_ERR}")
    pkg = Path(package_dir)
    out = Path(out_dir) if out_dir is not None else pkg / "locus_maps"
    out.mkdir(parents=True, exist_ok=True)
    genes, gene_source = load_genes(pkg, bgc_id)
    if not genes:
        raise ValueError(f"no exact gene rows for {bgc_id}")
    comparator, comparator_source = choose_comparator(pkg, bgc_id)
    auxiliary = _attach_auxiliary(pkg, bgc_id, genes)

    triage = _package_file(pkg, "_4_triage_board.csv")
    triage_row = next(
        (row for row in _read_csv(triage) if _first(row, ("BGC_ID", "bgc_id")) == bgc_id),
        {},
    )

    if not strain_id:
        for manifest_name in ("manifest_short.json", "manifest.json"):
            manifest_path = pkg / manifest_name
            if manifest_path.is_file():
                try:
                    strain_id = str(json.loads(manifest_path.read_text()).get("strain_id", ""))
                except (OSError, json.JSONDecodeError) as exc:
                    # A malformed manifest must not decide the figure's identity silently:
                    # name the degradation, then try the next manifest / caller-supplied id.
                    sys.stderr.write(
                        f"locus_map_v8: could not read strain_id from {manifest_name} "
                        f"({type(exc).__name__}: {exc})\n")
                if strain_id:
                    break

    node = node or _first(triage_row, ("Contig", "Node_ID", "Node"))
    region = region or _first(triage_row, ("antiSMASH_Region", "Region", "region"))
    missing_identity = [
        name for name, value in (
            ("strain", strain_id), ("full node-or-contig", node),
            ("region", region), ("BGC alias", bgc_id),
        ) if not str(value).strip()
    ]
    if missing_identity:
        raise ValueError(
            "complete locus identity unavailable: " + ", ".join(missing_identity)
        )

    n_selected = len([g for g in genes if g.locus_tag in comparator.genes])
    rows_per_col = math.ceil(max(n_selected, 1) / (2 if n_selected > 10 else 1))
    planned_label_lanes = _label_lane_count(len(genes))
    fig_h = max(8.8, 5.6 + rows_per_col * 0.34 + (planned_label_lanes - 1) * 0.9)
    fig = plt.figure(figsize=(16.0, fig_h), dpi=180, facecolor="white")
    grid = fig.add_gridspec(
        2, 1,
        height_ratios=[3.0 + (planned_label_lanes - 1) * 0.9, max(3.8, rows_per_col * 0.33)],
        hspace=0.12,
    )
    map_ax = fig.add_subplot(grid[0])
    evidence_ax = fig.add_subplot(grid[1])

    ident = f"{strain_id} / {node} / {region} / {bgc_id}"
    if products:
        ident += f" · {products}"
    comparator_line = "Comparator: not available in sealed package"
    if comparator.accession:
        med = "—" if comparator.median_identity is None else f"{comparator.median_identity:.1f}%"
        comparator_line = (
            f"Comparator: {comparator.accession} ({_display_name(comparator.compound)}) · "
            f"{len(comparator.genes)} supporting exact genes · median {med} identity"
        )
    label_lanes = _draw_map_axis(map_ax, genes, comparator, ident)
    map_ax.text(0.0, 1.02, comparator_line, transform=map_ax.transAxes,
                fontsize=8.3, color=MUTED, va="bottom")
    selected_displayed, hidden_tokens = _draw_evidence_axis(evidence_ax, genes, comparator)

    legend = []
    if comparator.genes:
        legend.append(Patch(facecolor=SELECTED, label="Selected comparator gene"))
    role_legend = (
        ("biosynthetic", BIOSYN, "Biosynthetic CDS"),
        ("transport", TRANSPORT, "Transport"),
        ("regulatory", REGULATORY, "Regulatory"),
        ("other", OTHER, "Other/context CDS"),
    )
    for role, color, label in role_legend:
        if any(g.role == role and g.locus_tag not in comparator.genes for g in genes):
            legend.append(Patch(facecolor=color, label=label))
    legend.append(Line2D([0], [0], color="#8A949C", lw=0.8, label="Exact-label leader"))
    fig.legend(handles=legend, loc="upper center", bbox_to_anchor=(0.5, 0.955),
               ncol=6, frameon=False, fontsize=7.4)
    fig.suptitle("Sapote-Mamey locus map v8 — evidence-dense exact-locus view",
                 fontsize=14.0, fontweight="bold", color=INK, y=0.995)
    fig.text(0.5, 0.012, CLAIM_CEILING, ha="center", va="bottom",
             fontsize=6.5, color=MUTED, wrap=True)
    fig.subplots_adjust(left=0.055, right=0.985, top=0.91, bottom=0.075)

    png = out / f"{bgc_id}_locus_map.png"
    svg = out / f"{bgc_id}_locus_map.svg"
    csv_path = out / f"{bgc_id}_locus_map_data.csv"
    receipt_path = out / f"{bgc_id}_locus_map_v8_receipt.json"
    fig.savefig(png, dpi=_safe_dpi(fig, 180), metadata={"Software": "Sapote-Mamey locus map v8"})
    fig.savefig(svg, metadata={"Date": None, "Creator": "Sapote-Mamey locus map v8"})
    plt.close(fig)

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        fields = [
            "panel", "locus_tag", "order", "start", "end", "strand", "length_aa", "role",
            "gene_functions", "label_displayed", "selected_comparator", "comparator_accession",
            "comparator_compound", "subject_gene", "pct_identity", "pct_coverage", "blast_score",
            "evalue", "domain_tokens", "hmm_tokens", "module_tokens", "motif_tokens",
            "displayed_evidence_summary",
        ]
        writer = _SafeDictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for gene in genes:
            metric = comparator.genes.get(gene.locus_tag)
            summary, _hidden = _compact_evidence(gene)
            writer.writerow({
                "panel": ident,
                "locus_tag": gene.locus_tag,
                "order": gene.order,
                "start": gene.start,
                "end": gene.end,
                "strand": "+" if gene.strand == 1 else "-",
                "length_aa": gene.length_aa,
                "role": gene.role,
                "gene_functions": gene.gene_functions,
                "label_displayed": "YES",
                "selected_comparator": "YES" if metric else "NO",
                "comparator_accession": comparator.accession if metric else "",
                "comparator_compound": comparator.compound if metric else "",
                "subject_gene": metric.subject_gene if metric else "",
                "pct_identity": "" if not metric or metric.pct_identity is None else f"{metric.pct_identity:.3f}",
                "pct_coverage": "" if not metric or metric.pct_coverage is None else f"{metric.pct_coverage:.3f}",
                "blast_score": "" if not metric or metric.blast_score is None else f"{metric.blast_score:.3f}",
                "evalue": metric.evalue if metric else "",
                "domain_tokens": "; ".join(gene.domains),
                "hmm_tokens": "; ".join(gene.hmm),
                "module_tokens": "; ".join(gene.modules),
                "motif_tokens": "; ".join(gene.motifs),
                "displayed_evidence_summary": summary if metric else "",
            })

    gene_roster = _gene_roster_from_csv(csv_path)

    source_paths = [path for path in [gene_source, comparator_source, *auxiliary.values()] if path]
    sources = [
        {"path": path.relative_to(pkg).as_posix(), "sha256": _sha(path), "bytes": path.stat().st_size}
        for path in sorted(set(source_paths))
    ]
    comparator_bound = len(comparator.genes)
    status = (
        "READY" if len(genes) > 0 and selected_displayed == comparator_bound
        else "NEEDS_REVIEW"
    )
    receipt: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "renderer": "v8",
        "status": status,
        "bgc_id": bgc_id,
        "gene_count": len(genes),
        "exact_labels_displayed": len(genes),
        "exact_labels_suppressed": 0,
        "label_layout": {
            "strategy": "adaptive_multi_lane",
            "lane_count": label_lanes,
            "max_labels_per_lane": MAX_LABELS_PER_LANE,
        },
        "exact_locus_identity": {
            "strain": strain_id,
            "full_node_or_contig": node,
            "region": region,
            "bgc_alias": bgc_id,
            "display": ident,
        },
        "selected_comparator": {
            "accession": comparator.accession,
            "compound": comparator.compound,
            "supporting_exact_genes": comparator_bound,
            "median_identity": comparator.median_identity,
        },
        "selected_genes_displayed_in_evidence_panel": selected_displayed,
        "coverage_display_policy": "RAW_UNCAPPED_SOURCE_REPORTED; values over 100% marked with *",
        "coverage_values_over_100": sum(
            gene.pct_coverage is not None and gene.pct_coverage > 100
            for gene in comparator.genes.values()
        ),
        "evidence_summary_hidden_token_count": hidden_tokens,
        "full_evidence_preserved_in_csv": True,
        "outputs": {
            "png": png.name,
            "svg": svg.name,
            "csv": csv_path.name,
            "csv_sha256": _sha(csv_path),
        },
        "gene_roster": {
            "source": csv_path.name,
            "row_count": len(gene_roster),
            "sha256": _gene_roster_sha256(gene_roster),
            "identity_fields": ["row", "locus_tag", "order"],
        },
        "output_integrity": {
            kind: {"path": output.name, "sha256": _sha(output), "bytes": output.stat().st_size}
            for kind, output in (("png", png), ("svg", svg), ("csv", csv_path))
        },
        "sources": sources,
        "claim_ceiling": CLAIM_CEILING,
    }
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    validate_locus_map_v8_receipt(receipt_path, expected_bgc_id=bgc_id)
    return receipt


def _ranked_targets(package_dir: Path, top_n: int) -> list[dict[str, str]]:
    triage = _package_file(Path(package_dir), "_4_triage_board.csv")
    rows = _read_csv(triage)
    def rank(row: dict[str, str]) -> tuple[float, str]:
        value = _float(row.get("Corrected_rank") or row.get("Rank"))
        return (value if value is not None else 10**9, row.get("BGC_ID", ""))
    return sorted(rows, key=rank)[:top_n]


def render_for_compile_report_v8(
    package_dir: Path | str,
    top_n: int = 5,
    *,
    out_subdir: str = "locus_maps",
    fmt: str = "svg",
) -> dict[str, Any]:
    """Compatibility adapter for compile-report and render-all-figures.

    v8 always emits both PNG and SVG; ``fmt`` is accepted for API compatibility.
    """
    del fmt
    pkg = Path(package_dir)
    out = pkg / out_subdir
    out.mkdir(parents=True, exist_ok=True)
    gene_source = _package_file(pkg, "_gene_by_gene_all_bgcs.csv")
    if gene_source is None:
        return {"out": str(out), "rendered": [], "skipped": {},
                "skipped_reason": "no gene_by_gene_all_bgcs.csv in package", "renderer": "v8"}
    triage = _package_file(pkg, "_4_triage_board.csv")
    if triage is None:
        return {"out": str(out), "rendered": [], "skipped": {},
                "skipped_reason": "no triage board CSV in package", "renderer": "v8"}
    rendered: list[str] = []
    skipped: dict[str, str] = {}
    for row in _ranked_targets(pkg, top_n):
        bgc_id = _first(row, ("BGC_ID", "bgc_id"))
        if not bgc_id:
            continue
        try:
            render_bgc_v8(
                pkg, bgc_id, out_dir=out,
                node=_first(row, ("Contig", "Node_ID", "Node")),
                region=_first(row, ("antiSMASH_Region", "Region", "region")),
                products=row.get("Products", ""),
            )
            rendered.append(bgc_id)
        except Exception as exc:  # non-blocking figure path
            skipped[bgc_id] = f"{type(exc).__name__}: {exc}"
    return {"out": str(out), "rendered": rendered, "skipped": skipped,
            "skipped_reason": None, "renderer": "v8"}


__all__ = [
    "Comparator",
    "FigureReceiptMismatch",
    "GeneRow",
    "SCHEMA_VERSION",
    "MAX_LABELS_PER_LANE",
    "choose_comparator",
    "load_genes",
    "render_bgc_v8",
    "render_for_compile_report_v8",
    "validate_locus_map_v8_receipt",
]
