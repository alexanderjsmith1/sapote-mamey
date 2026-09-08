#!/usr/bin/env python3
"""render_activity_lead_reports.py — the Day-5-shaped activity-lead deliverable.

Consumes two ALREADY-SEALED, ALREADY-CLAIM-SAFE inputs and layers no new scoring on top of
either:

  1. ``--runs-dir``: sealed Mamey packages (``*_4_triage_board.csv`` + ``manifest.json`` per
     strain), read the same way :mod:`mamey.activity_lead_report` finds them
     (:func:`mamey.cohort_leads_ledger.find_triage_boards`). Used ONLY for assembly-quality
     bookkeeping (genome size, contig count, N50, and the corrected-BGC-count / interior-%
     tier table) -- the exact numbers CLAUDE.md's own gene-level guard and
     ``mamey/assembly.py``'s ``corrected_bgc_count()`` / ``assembly_tier()`` already define.
  2. ``--leads-dir``: the output directory of ``mamey activity-leads`` followed by
     ``mamey activity-lead-genes`` -- ``PER_STRAIN_ACTIVITY_LEADS.csv`` (the routing board) and
     ``ACTIVITY_LEAD_GENE_ANCHORS.csv`` / ``ACTIVITY_LEAD_GENE_LOGIC.csv`` (the up-to-five-gene
     class foundation for each admitted lead). Every lead this renderer prints is bound to its
     exact locus (``strain / full node-or-contig / region / bgc_alias``) exactly as
     ``activity_lead_report.py`` emitted it -- this renderer never recomputes or overrides a
     locus, a score, or a gene selection.

Shape (matches the Day-5 bar named in the 2026-09-02 cross-lane brief --
``Layperson_BGC_Guide_All27Strains_BertMode_May2026.pdf``): an assembly-quality tier table, a
cross-strain best-targets table, then one card per strain with a per-lead table carrying a
Novelty figure, a Layperson headline, and a Next-experiment suggestion. See
``docs/ACTIVITY_LEAD_REPORTS.md`` for the field-by-field honest comparison against that PDF --
this renderer does NOT fabricate compound names, structural analogues, or a MIBiG-similarity
percentage; none of those are present in the current engine's activity-lead surface, and
inventing them would be exactly the kind of unsupported specificity claim-safety forbids.

Deterministic: every list this script prints is sorted on an explicit key (strain name, axis,
rank, locus tag) before being written -- never on dict/glob iteration order. No timestamp or
run-specific value is embedded in the body text (the build-time stamp, if any, is confined to
one caption line, see ``--stamp``).

Output: always writes a Markdown file (the single source of truth for both the printed body and
the optional PDF). When ``reportlab`` is importable, also renders a vector/live-text PDF via the
bundle's own canonical Markdown-to-PDF renderer, :mod:`mamey.markdown_pdf` (the same renderer
:mod:`mamey.modeb_export` already uses for Mode B cards) -- this script does not implement its
own PDF layout. When ``reportlab`` is absent, the Markdown file is the deliverable; the script
exits 0 either way and says plainly on stdout which outputs were produced.

Claim-safety (mandatory, restated in the emitted document itself, not only here): every BGC
below is a class-level routing hypothesis. AF_auto/AB_auto and the gene anchors are routing
priors and class-explanatory genes, never a measured activity, a confirmed compound identity,
or evidence of expression. "Novelty" is the engine's own re-projected novelty score, not a
MIBiG-percent-identity figure. Missing evidence is a workflow gap, not a biological absence.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

import argparse
import csv
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from mamey.assembly import assembly_tier, corrected_bgc_count  # noqa: E402
from mamey.cohort_leads_ledger import find_triage_boards  # noqa: E402

try:
    import json as _json
except ImportError:  # pragma: no cover -- stdlib, always present
    _json = None  # type: ignore[assignment]


CLAIM_SAFETY_BANNER = (
    "Routing priors only. AF_auto/AB_auto are re-projected triage scores, not measured "
    "antibacterial or antifungal activity. Gene anchors show class-explanatory biosynthetic "
    "logic, not compound identity, production, or expression. Similarity is not identity; "
    "capacity is not production; missing evidence is a workflow gap, not a biological absence. "
    "Judgment on every hypothesis below is deferred to the Sapote (Tier 2/3) judgment layer."
)

TIER_TABLE_ROWS = [
    ("GOOD", "≥70%", "Low priority", "Raw ≈ corrected; BGC routing counts are reliable"),
    ("MODERATE", "45–69%", "Consider", "Minor correction needed; most interior BGCs are reliable"),
    ("POOR", "20–44%", "Recommended", "Corrected count only; edge/full-contig BGCs are unreliable"),
    ("VERY_POOR", "<20%", "Urgent", "Raw count is inflated; only interior BGCs are defensible"),
]

# Deterministic, class-level bench-method suggestions. Keyed by the normalized class token this
# script derives from the lead's own `Products` string (see `_primary_class`). Intentionally
# generic (no fabricated compound name or structure) -- the goal is a plausible NEXT ACTION a
# bench scientist could start from, not a claim about what the BGC actually makes.
NEXT_EXPERIMENT_BY_CLASS = {
    "NRPS": "Validate adenylation-domain substrate specificity and module completeness, then "
            "pair expression-linked LC-MS/MS with a matched antibacterial/antifungal panel.",
    "PKS": "Confirm module order and catalytic-domain completeness (KS/AT/ACP states), then "
           "profile expression-linked extracts by LC-MS/MS across the routed activity panel.",
    "RiPP": "Bind the precursor-to-maturation gene pair, verify expression, resolve the mature "
            "peptide by intact-mass/MS-MS, then test the routed activity panel.",
    "terpene": "Verify the product-forming cyclase/synthase, profile expression-linked "
               "metabolites, then run mechanism-neutral activity testing.",
    "siderophore": "Run a CAS (chrome azurol S) assay to confirm iron-chelating activity before "
                   "any antimicrobial-activity claim; siderophore capacity is not itself a "
                   "routing target.",
    "saccharide": "Confirm this is a specialized (non-housekeeping) saccharide cassette before "
                  "extraction; most saccharide hits are primary-metabolism glycosylation, not a "
                  "specialized product.",
    "beta-lactone": "Confirm the beta-lactone-forming step genetically, then pair expression-"
                    "linked extraction with a beta-lactone-sensitive activity panel.",
    "phosphonate": "Confirm the PEP-mutase / phosphonopyruvate step, then use 31P-NMR or "
                   "CID-fragmentation metabolomics to detect the C–P bond product.",
}
NEXT_EXPERIMENT_DEFAULT = (
    "Confirm the committed pathway step genetically and chemically, then test the routed "
    "phenotype against a matched negative control before any activity claim."
)

# Mirrors the class buckets `mamey.activity_lead_genes._norm_class` already uses for gene-vote
# normalization, so the class token printed here is the SAME vocabulary the gene-anchor layer
# reasons about -- not a second, independently-invented taxonomy.
_CLASS_TOKEN_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("NRPS", ("nrps", "nonribosomal")),
    ("PKS", ("pks", "polyketide")),
    ("RiPP", ("ripp", "lanth", "lasso", "thiopeptide", "linaridin", "cyanobactin")),
    ("terpene", ("terpene",)),
    ("siderophore", ("siderophore",)),
    ("saccharide", ("saccharide", "polysaccharide")),
    ("beta-lactone", ("betalactone", "beta-lactone")),
    ("phosphonate", ("phosphonate",)),
]


def _primary_class(products: str) -> str:
    """First recognizable class token in a lead's `Products` string, else the raw first token."""
    for token in (part.strip() for part in (products or "").split(";")):
        if not token:
            continue
        lowered = token.lower()
        for label, needles in _CLASS_TOKEN_RULES:
            if any(needle in lowered for needle in needles):
                return label
    first = (products or "").split(";")[0].strip()
    return first or "unresolved class"


def _num(value: Any, default: float = 0.0) -> float:
    try:
        text = str(value).strip()
        return float(text) if text else default
    except (TypeError, ValueError):
        return default


def _read_manifest(package_dir: str) -> dict[str, Any]:
    path = os.path.join(package_dir, "manifest.json")
    try:
        with open(path, encoding="utf-8") as handle:
            return _json.load(handle)
    except (OSError, ValueError):
        return {}


def _strain_for(board: str, manifest: dict[str, Any]) -> str:
    # Mirrors mamey.activity_lead_report._strain_for exactly, so a strain name derived here
    # always matches the strain name activity_lead_report.py already put in the leads CSV.
    value = manifest.get("strain_id") or manifest.get("display_name")
    if value:
        return str(value).strip()
    return os.path.basename(board).replace("_4_triage_board.csv", "").strip()


def load_assembly_rows(runs_dir: str) -> dict[str, dict[str, Any]]:
    """One assembly-quality summary row per strain, built from every row in its FULL triage
    board (not the top-N-per-axis subset the activity-leads CSV carries) -- the tier table
    needs the true raw/interior/edge/full-contig counts across the whole board."""
    rows: dict[str, dict[str, Any]] = {}
    for board in find_triage_boards(runs_dir):
        package_dir = os.path.dirname(board)
        manifest = _read_manifest(package_dir)
        strain = _strain_for(board, manifest)
        if not strain:
            continue
        assembly = manifest.get("assembly") or {}
        boundary_counts = {"interior": 0, "edge": 0, "full-contig": 0, "other": 0}
        raw = 0
        try:
            with open(board, newline="", encoding="utf-8-sig") as handle:
                for source in csv.DictReader(handle):
                    raw += 1
                    boundary = (source.get("Boundary") or "").strip().lower()
                    if boundary in boundary_counts:
                        boundary_counts[boundary] += 1
                    else:
                        boundary_counts["other"] += 1
        except OSError:
            continue
        interior_pct = (100.0 * boundary_counts["interior"] / raw) if raw else None
        corrected = corrected_bgc_count(
            boundary_counts["interior"], boundary_counts["edge"], boundary_counts["full-contig"]
        ) if raw else 0.0
        rows[strain] = {
            "strain": strain,
            "genome_bp": assembly.get("genome_bp"),
            "contigs": assembly.get("contigs"),
            "n50": assembly.get("n50"),
            "raw_bgc": raw,
            "interior": boundary_counts["interior"],
            "edge": boundary_counts["edge"],
            "full_contig": boundary_counts["full-contig"],
            "interior_pct": interior_pct,
            "corrected_bgc": corrected,
            "tier": assembly_tier(interior_pct),
        }
    return rows


def load_leads(leads_dir: str) -> list[dict[str, str]]:
    path = os.path.join(leads_dir, "PER_STRAIN_ACTIVITY_LEADS.csv")
    with open(path, newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def load_gene_layer(leads_dir: str) -> tuple[dict[str, list[dict[str, str]]], dict[str, dict[str, str]]]:
    """(anchors_by_locus, locus_summary_by_locus). Both empty (not an error) when the
    activity-lead-genes command has not been run for this leads-dir yet -- gene anchors are an
    enrichment layer, not a precondition for the routing-board portion of this report."""
    anchors_by_locus: dict[str, list[dict[str, str]]] = defaultdict(list)
    anchors_path = os.path.join(leads_dir, "ACTIVITY_LEAD_GENE_ANCHORS.csv")
    if os.path.isfile(anchors_path):
        with open(anchors_path, newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                anchors_by_locus[row.get("exact_locus", "")].append(row)
        for locus in anchors_by_locus:
            anchors_by_locus[locus].sort(key=lambda r: _num(r.get("gene_anchor_rank"), 0.0))

    summary_by_locus: dict[str, dict[str, str]] = {}
    logic_path = os.path.join(leads_dir, "ACTIVITY_LEAD_GENE_LOGIC.csv")
    if os.path.isfile(logic_path):
        with open(logic_path, newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                summary_by_locus[row.get("exact_locus", "")] = row
    return dict(anchors_by_locus), summary_by_locus


def _layperson_headline(lead: dict[str, str], gene_summary: dict[str, str] | None) -> str:
    """One deterministic, class-level sentence. Never a compound name or structural analogue --
    those are not present anywhere in the activity-lead or gene-anchor CSV surface, and
    inventing one here would be an unsupported specificity claim."""
    primary = _primary_class(lead.get("Products", ""))
    interp = lead.get("interpretability_tier", "").strip()
    if gene_summary:
        strength = gene_summary.get("gene_logic_strength", "").strip()
        strength_phrase = {
            "STRONG_GENE_LOGIC": "core catalytic machinery for this class is genetically secure",
            "MODERATE_GENE_LOGIC": "partial gene-level support for this class; a step remains unresolved",
            "WEAK_ACCESSORY_ONLY": "only accessory/context genes are secure; no class-defining core is bound",
            "UNRESOLVED_CLASS_FOUNDATION": "no gene-level foundation is bound for this class yet",
        }.get(strength, "gene-level foundation not yet evaluated")
    else:
        strength_phrase = "gene-level foundation not yet evaluated (run activity-lead-genes)"
    interp_phrase = (
        "no encoded exclusion or boundary warning" if interp == "STRONGER_ROUTING_CANDIDATE"
        else "conditional: " + (lead.get("interpretability_hold", "").strip() or "see hold")
    )
    return f"{primary} routing candidate; {strength_phrase}; {interp_phrase}."


def _why_it_ranks(strain: str, top_lead: dict[str, str], assembly_row: dict[str, Any] | None) -> str:
    primary = _primary_class(top_lead.get("Products", ""))
    axis = "antifungal" if top_lead.get("axis") == "antifungal" else "antibacterial"
    tier = (assembly_row or {}).get("tier", "UNKNOWN")
    tier_phrase = {
        "GOOD": "reliable assembly",
        "MODERATE": "assembly needs minor correction",
        "POOR": "assembly correction strongly recommended",
        "VERY_POOR": "assembly is unreliable; long-read sequencing urged",
        "UNKNOWN": "assembly quality not recorded",
    }.get(tier, "assembly quality not recorded")
    return (
        f"Top {axis} routing candidate is a {primary} locus at score "
        f"{_num(top_lead.get('axis_score')):.0f} ({top_lead.get('interpretability_tier', '')}); {tier_phrase}."
    )


def _next_experiment_for(products: str) -> str:
    return NEXT_EXPERIMENT_BY_CLASS.get(_primary_class(products), NEXT_EXPERIMENT_DEFAULT)


def _fmt_bp(value: Any) -> str:
    try:
        return f"{int(value):,} bp"
    except (TypeError, ValueError):
        return "not recorded"


def _fmt_mb(value: Any) -> str:
    try:
        return f"{int(value) / 1_000_000:.2f} Mb"
    except (TypeError, ValueError):
        return "not recorded"


def _fmt_pct(value: Any) -> str:
    return f"{value:.1f}%" if isinstance(value, (int, float)) else "n/a"


def _tier_rank(tier: str) -> int:
    return {"GOOD": 4, "MODERATE": 3, "POOR": 2, "VERY_POOR": 1, "UNKNOWN": 0}.get(tier, 0)


def build_markdown(
    assembly_rows: dict[str, dict[str, Any]],
    leads: list[dict[str, str]],
    anchors_by_locus: dict[str, list[dict[str, str]]],
    summary_by_locus: dict[str, dict[str, str]],
    *,
    top_n_targets: int,
    stamp: str,
) -> str:
    strains_with_leads = sorted({row["strain"] for row in leads}, key=str.casefold)
    leads_by_strain: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in leads:
        leads_by_strain[row["strain"]].append(row)
    for strain in leads_by_strain:
        leads_by_strain[strain].sort(
            key=lambda r: (r.get("axis", ""), _num(r.get("axis_rank_within_strain"), 0.0))
        )

    out: list[str] = []
    out.append("# Activity-Lead Report — Gene-Anchored AF/AB Routing Boards")
    out.append("")
    out.append(f"Cohort: {len(strains_with_leads)} strain(s) with an admitted routing lead, "
                f"{len(assembly_rows)} strain(s) with an assembly-quality record." +
                (f" Build: {stamp}." if stamp else ""))
    out.append("")
    out.append("> " + CLAIM_SAFETY_BANNER)
    out.append("")

    out.append("## Assembly-quality tiers")
    out.append("")
    out.append("Corrected BGC count = Interior + 0.5×Edge + 0.25×Full-contig "
                "(`mamey.assembly.corrected_bgc_count`). Interior % gates the tier.")
    out.append("")
    out.append("| Tier | Interior % | Long-read | Interpretation |")
    out.append("|---|---:|---|---|")
    for tier, pct, rec, note in TIER_TABLE_ROWS:
        out.append(f"| {tier} | {pct} | {rec} | {note} |")
    out.append("")
    out.append("| Strain | Genome | Contigs | N50 | Raw BGC | Corrected BGC | Interior % | Tier |")
    out.append("|---|---|---:|---:|---:|---:|---:|---|")
    for strain in sorted(assembly_rows, key=str.casefold):
        row = assembly_rows[strain]
        out.append(
            f"| {strain} | {_fmt_mb(row['genome_bp'])} | {row['contigs'] or 'n/a'} | "
            f"{row['n50'] or 'n/a'} | {row['raw_bgc']} | {row['corrected_bgc']:.2f} | "
            f"{_fmt_pct(row['interior_pct'])} | {row['tier']} |"
        )
    out.append("")

    out.append("## Cross-strain best targets")
    out.append("")
    out.append(f"Strains ranked by top routed score, tie-broken by assembly tier. "
                f"Top {top_n_targets} shown; every strain's full board is in its own card below.")
    out.append("")
    ranked: list[tuple[str, dict[str, str], dict[str, Any] | None]] = []
    for strain in strains_with_leads:
        rows = leads_by_strain[strain]
        top = max(rows, key=lambda r: _num(r.get("axis_score")))
        ranked.append((strain, top, assembly_rows.get(strain)))
    ranked.sort(
        key=lambda item: (
            -_num(item[1].get("axis_score")),
            -_tier_rank((item[2] or {}).get("tier", "UNKNOWN")),
            item[0].casefold(),
        )
    )
    out.append("| Rank | Strain | Tier | Best locus | Why it ranks here | Next experiment |")
    out.append("|---:|---|---|---|---|---|")
    for rank, (strain, top, assembly_row) in enumerate(ranked[:top_n_targets], start=1):
        out.append(
            f"| #{rank} | {strain} | {(assembly_row or {}).get('tier', 'UNKNOWN')} | "
            f"{top.get('bgc_alias', '')} | {_why_it_ranks(strain, top, assembly_row)} | "
            f"{_next_experiment_for(top.get('Products', ''))} |"
        )
    out.append("")

    out.append("## Per-strain cards")
    out.append("")
    for strain in strains_with_leads:
        assembly_row = assembly_rows.get(strain)
        out.append(f"### {strain}")
        out.append("")
        if assembly_row:
            out.append(
                f"{_fmt_mb(assembly_row['genome_bp'])} | {assembly_row['contigs'] or 'n/a'} ctgs | "
                f"Raw: {assembly_row['raw_bgc']} | Corrected: {assembly_row['corrected_bgc']:.2f} | "
                f"Interior: {_fmt_pct(assembly_row['interior_pct'])} | Assembly: {assembly_row['tier']}"
            )
        else:
            out.append("Assembly record not found in `--runs-dir` for this strain.")
        out.append("")
        out.append("| Axis+Rank | Locus | Class | Novelty | Layperson headline | Next experiment |")
        out.append("|---|---|---|---:|---|---|")
        for lead in leads_by_strain[strain]:
            exact = lead.get("exact_locus", "")
            gene_summary = summary_by_locus.get(exact)
            axis_label = "AF" if lead.get("axis") == "antifungal" else "AB"
            out.append(
                f"| {axis_label}{lead.get('axis_rank_within_strain', '')} | "
                f"{lead.get('bgc_alias', '')} | {_primary_class(lead.get('Products', ''))} | "
                f"{_num(lead.get('Novelty_auto')):.0f} | {_layperson_headline(lead, gene_summary)} | "
                f"{_next_experiment_for(lead.get('Products', ''))} |"
            )
        out.append("")
        for lead in leads_by_strain[strain]:
            exact = lead.get("exact_locus", "")
            anchors = anchors_by_locus.get(exact, [])
            if not anchors:
                continue
            axis_label = "AF" if lead.get("axis") == "antifungal" else "AB"
            out.append(f"#### {axis_label}{lead.get('axis_rank_within_strain', '')} — {exact}")
            out.append("")
            for anchor in anchors:
                out.append(
                    f"- {anchor.get('locus_tag', '')} — {anchor.get('evidence_tier', '')}: "
                    f"{anchor.get('logic', '')}"
                )
            out.append("")
        out.append(
            f"> Claim ceiling: {leads_by_strain[strain][0].get('claim_ceiling', '')}"
            if leads_by_strain[strain] else ""
        )
        out.append("")

    out.append("## Methods and claim-safety")
    out.append("")
    out.append(
        "Routing boards are re-projected from each sealed package's own `AB_auto`/`AF_auto` "
        "triage scores (`mamey.activity_lead_report`); no new score is computed here. Gene "
        "anchors are up to five class-explanatory genes per admitted locus "
        "(`mamey.activity_lead_genes`), bound by exact physical identity to the sealed "
        "per-gene table. Assembly-quality figures use `mamey.assembly.assembly_tier` and "
        "`mamey.assembly.corrected_bgc_count` against the strain's full triage board. This "
        "report changes no score, no gate verdict, and no claim-safety wording upstream of it."
    )
    out.append("")
    out.append("> " + CLAIM_SAFETY_BANNER)
    out.append("")
    return "\n".join(out)


def render(
    runs_dir: str,
    leads_dir: str,
    out_stem: str,
    *,
    top_n_targets: int = 15,
    fmt: str = "auto",
    stamp: str = "",
) -> dict[str, Any]:
    assembly_rows = load_assembly_rows(runs_dir)
    leads = load_leads(leads_dir)
    anchors_by_locus, summary_by_locus = load_gene_layer(leads_dir)
    markdown = build_markdown(
        assembly_rows, leads, anchors_by_locus, summary_by_locus,
        top_n_targets=top_n_targets, stamp=stamp,
    )

    out_path = Path(out_stem)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    md_path = out_path.with_suffix(".md")
    tmp = md_path.with_suffix(md_path.suffix + ".tmp")
    tmp.write_text(markdown, encoding="utf-8")
    os.replace(tmp, md_path)

    result: dict[str, Any] = {
        "markdown_path": str(md_path),
        "pdf_path": None,
        "pdf_skipped_reason": None,
        "n_strains_with_leads": len({row["strain"] for row in leads}),
        "n_strains_with_assembly": len(assembly_rows),
        "n_lead_rows": len(leads),
    }
    want_pdf = fmt in ("auto", "pdf")
    if not want_pdf:
        result["pdf_skipped_reason"] = "format=markdown requested explicitly"
    if want_pdf:
        try:
            from mamey.markdown_pdf import render as _render_pdf
        except ImportError:
            if fmt == "pdf":
                raise
            result["pdf_skipped_reason"] = "reportlab is not importable in this environment"
        else:
            pdf_path = out_path.with_suffix(".pdf")
            _render_pdf(
                str(md_path), str(pdf_path),
                title="Activity-Lead Report",
                subtitle="Gene-anchored AF/AB routing boards — class-level, judgment deferred",
            )
            result["pdf_path"] = str(pdf_path)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs-dir", required=True,
                         help="Root directory of sealed packages (same layout "
                              "mamey.cohort_leads_ledger.find_triage_boards expects).")
    parser.add_argument("--leads-dir", required=True,
                         help="Output directory of `mamey activity-leads` "
                              "(+ optionally `mamey activity-lead-genes`).")
    parser.add_argument("--out", default="activity_lead_reports/ACTIVITY_LEAD_REPORT",
                         help="Output path stem (no extension); .md always written, "
                              ".pdf written when reportlab is importable.")
    parser.add_argument("--top-n-targets", type=int, default=15,
                         help="Rows in the cross-strain best-targets table (default 15).")
    parser.add_argument("--format", choices=("auto", "pdf", "markdown"), default="auto",
                         help="auto: PDF if reportlab is importable, else Markdown only. "
                              "pdf: require reportlab (error if absent). "
                              "markdown: Markdown only, even if reportlab is available.")
    parser.add_argument("--stamp", default="",
                         help="Optional caption-only build label (e.g. a cut version string). "
                              "Never affects ranking or content, only the one summary line.")
    args = parser.parse_args(argv)

    result = render(
        args.runs_dir, args.leads_dir, args.out,
        top_n_targets=args.top_n_targets, fmt=args.format, stamp=args.stamp,
    )
    # v9.7.405 (lane 2, per the composer's ratchet request): print(...) -> sys.stdout.write(...) --
    # behaviour-identical (this IS the tool's own stdout receipt), but keeps this front door out
    # of the print-call ratchet count rather than needing a whole-file exclusion (the .404 A3
    # lesson: a file-level exclusion silently drops any PRE-EXISTING debt in that file from the
    # count too, not just its own new calls).
    sys.stdout.write(
        f"activity-lead-reports: {result['n_lead_rows']} lead row(s) across "
        f"{result['n_strains_with_leads']} strain(s) with leads, "
        f"{result['n_strains_with_assembly']} strain(s) with an assembly record.\n"
    )
    sys.stdout.write(f"  markdown: {result['markdown_path']}\n")
    if result["pdf_path"]:
        sys.stdout.write(f"  pdf:      {result['pdf_path']}\n")
    else:
        sys.stdout.write(
            f"  pdf:      not written ({result['pdf_skipped_reason']}; markdown is the deliverable)\n"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
