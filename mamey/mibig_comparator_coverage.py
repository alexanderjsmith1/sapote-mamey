"""Two-denominator comparator-coverage evidence layer (FA2).

Prototype reporting/evidence layer that *consumes* the already-emitted
per-gene MIBiG/KnownClusterBlast rows (`*_3_mibig_per_gene.csv`) and the
convergence rows (`*_3_mibig_convergence.csv`) and re-expresses each named
MIBiG comparator against **two** denominators instead of one:

1. matched genes / all physical locus genes; and
2. matched *defining-core* genes / all defining-core genes.

Motivation (Codex ``DEEP_SYNTHESIS_FINDINGS.md`` §1, §2, §31-33): a comparator
can accrue a high name-frequency purely from housekeeping support -- tandem ABC
transporters, regulators, or primary-metabolism genes -- while covering zero of
the locus's defining biosynthetic core.  AS-XXX BGC052 is the canonical failure
(7 KnownClusterBlast comparators supported only by `ctg53_12/13`: 2/18 total
genes, 0/5 defining alpha-glucan genes).  A single "matched / all genes"
fraction hides that; two denominators plus a collision flag surface it.

CONTRACT (this prototype): **report-only, non-scoring.**  This module MUST NOT
add or modify any AB/AF prior, triage tier, novelty routing, or gate outcome.
It emits a new reported table (`<STRAIN>_3b_comparator_coverage.csv`) and a
small JSON summary.  Every field is framed as *sequence / capacity evidence*,
never product identity, activity, expression, or production.

The one place a future scoring wire would attach is marked with
``SCORING_WIRE_HOOK`` below; wiring it is a separate, sign-off-gated change and
is deliberately not done here.  See ``FA2_HOOK.md``.

This file is intentionally standalone: it only reads emitted package CSVs, so it
does not import or perturb ``mibig_per_gene.py`` (owned by another change).
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

import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import json
import re
from math import ceil
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = "mibig_comparator_coverage_v1"
REPORT_ONLY_CONTRACT = "REPORT_ONLY_NO_SCORING"

# A per-gene MIBiG hit at or below this identity is not counted as recognizable
# support for a comparator (mirrors mibig_per_gene.RECOGNIZABLE_MIN_IDENTITY so
# the two layers agree on what "matched" means).
RECOGNIZABLE_MIN_IDENTITY = 30.0

# Fraction of OTHER cohort strains (focal strain excluded) ABOVE which a comparator
# is called promiscuous and flagged for de-weighting (advisory only in this
# prototype).  v9.7.410: the boundary is strict (``>``), the focal strain is
# excluded from numerator and denominator, and a minimum cohort size is required
# before promiscuity may be asserted at all.  Rationale: a comparator has a
# coverage row only if it appears in its own strain, so a raw K/N fraction is
# bounded below by 1/N; at N=2 the only values are 0.5 and 1.0 and a ``>= 0.5``
# cut labels EVERY comparator (strain-unique ones included) promiscuous.
COHORT_PREVALENCE_PROMISCUOUS_FRACTION = 0.50

# Minimum number of OTHER strains (denominator after focal exclusion) that must be
# present before prevalence is assessable.  With the focal strain in the cohort
# this is a cohort of N >= 4.  Below the floor the flag is
# ``NOT_ASSESSABLE_SMALL_COHORT`` -- never a promiscuity verdict.
COHORT_PREVALENCE_MIN_OTHER_STRAINS = 3

FLAG_PROMISCUOUS = "PROMISCUOUS_DE_WEIGHT"
FLAG_COHORT_TYPICAL = "COHORT_TYPICAL"
FLAG_NOT_ASSESSABLE = "NOT_ASSESSABLE_SMALL_COHORT"
FLAG_NOT_COMPUTED = "NOT_COMPUTED"

CLAIM_SAFETY = (
    "Two-denominator comparator coverage is protein-sequence / capacity evidence only: "
    "it measures how much of a locus's genes (and of its defining biosynthetic core) show "
    "recognizable similarity to a named MIBiG reference. It is NOT product identity, "
    "biosynthetic-pathway confirmation, expression, production, bioactivity, or novelty. "
    "A named comparator remains a class-level relatedness clue, not a compound assignment."
)

# ---------------------------------------------------------------------------
# Gene-role classification (antiSMASH gene_functions -> role)
# ---------------------------------------------------------------------------
# antiSMASH annotates each CDS with a gene_functions string whose leading token
# is the functional category.  We map those to compact roles.  The *defining
# core* is the set of rule-based-clusters "biosynthetic" genes (the genes that
# fire the cluster rule); "biosynthetic-additional" is tailoring, not core.

ROLE_CORE = "CORE_BIOSYNTHETIC"
ROLE_TAILORING = "TAILORING"
ROLE_TRANSPORT = "TRANSPORT"
ROLE_REGULATORY = "REGULATORY"
ROLE_RESISTANCE = "RESISTANCE"
ROLE_OTHER = "OTHER_GENERIC"
ROLE_UNKNOWN = "UNKNOWN"

# Roles that carry NO specialized-pathway defining signal.  A comparator whose
# matched genes fall entirely inside this set (and includes no core gene) is a
# collision / low-specificity call.
ACCESSORY_NONCORE_ROLES = frozenset(
    {ROLE_TRANSPORT, ROLE_REGULATORY, ROLE_RESISTANCE, ROLE_OTHER, ROLE_UNKNOWN}
)


def classify_gene_role(gene_functions: str | None, sec_met_domains: str | None = None) -> str:
    """Classify a query CDS into a compact biosynthetic role.

    Uses the antiSMASH ``gene_functions`` category token first, then falls back
    to ``sec_met_domains`` presence.  The defining-core signal is the
    rule-based-clusters "biosynthetic" (NOT "biosynthetic-additional") tag.
    """
    text = (gene_functions or "").lower()
    # A bare rule-based-clusters "biosynthetic (" token (NOT "biosynthetic-additional")
    # marks a defining-core gene; core wins whenever it co-occurs with other tokens.
    tokens = _biosynthetic_category_tokens(text)
    if "biosynthetic" in tokens:
        return ROLE_CORE
    if "biosynthetic-additional" in tokens:
        return ROLE_TAILORING
    if "transport" in tokens:
        return ROLE_TRANSPORT
    if "regulatory" in tokens:
        return ROLE_REGULATORY
    if "resistance" in tokens:
        return ROLE_RESISTANCE
    if "other" in tokens:
        return ROLE_OTHER
    # No gene_functions category. A CDS with sec_met domains but no category is
    # accessory-biosynthetic-ish; without either it is unknown/primary-metabolism.
    if (sec_met_domains or "").strip():
        return ROLE_TAILORING
    return ROLE_UNKNOWN


def _biosynthetic_category_tokens(lowered_text: str) -> set[str]:
    """Extract the set of antiSMASH category leading-tokens from a functions string.

    ``gene_functions`` may pack several tokens, e.g.
    ``"biosynthetic (rule-based-clusters) saccharide: RmlD_sub_bind
    biosynthetic-additional (...)"``.  We split on the category keywords and
    record which appear, distinguishing bare ``biosynthetic (`` (core) from
    ``biosynthetic-additional (`` (tailoring).
    """
    tokens: set[str] = set()
    if "biosynthetic-additional" in lowered_text:
        tokens.add("biosynthetic-additional")
    # Bare "biosynthetic (" not preceded by "-additional".
    for m in re.finditer(r"biosynthetic(-additional)?\s*\(", lowered_text):
        if not m.group(1):
            tokens.add("biosynthetic")
    if "transport" in lowered_text:
        tokens.add("transport")
    if "regulatory" in lowered_text:
        tokens.add("regulatory")
    if "resistance" in lowered_text:
        tokens.add("resistance")
    if re.search(r"\bother\s*\(", lowered_text):
        tokens.add("other")
    return tokens


# ---------------------------------------------------------------------------
# Locus gene inventory (from the emitted CDS table)
# ---------------------------------------------------------------------------
def load_locus_genes(cds_rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, str]]:
    """Build ``{bgc_id: {locus_tag: role}}`` from ``*_cds_table.csv`` rows.

    This is the authoritative *physical locus* inventory (all CDS in the BGC),
    which is the denominator base for the two coverage fractions.  If the CDS
    table is unavailable, callers pass ``None`` and the module falls back to the
    KnownClusterBlast query-gene set as an approximate locus denominator (see
    ``compute_comparator_coverage``).
    """
    inventory: dict[str, dict[str, str]] = {}
    for row in cds_rows:
        bid = str(row.get("bgc_id", "")).strip()
        tag = str(row.get("locus_tag", "")).strip()
        if not bid or not tag:
            continue
        role = classify_gene_role(row.get("gene_functions"), row.get("sec_met_domains"))
        inventory.setdefault(bid, {})[tag] = role
    return inventory


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------
def compute_comparator_coverage(
    per_gene_rows: Iterable[dict[str, Any]],
    locus_genes: dict[str, dict[str, str]] | None = None,
    convergence_rows: Iterable[dict[str, Any]] | None = None,
    cohort_prevalence: dict[str, dict[str, Any]] | None = None,
    min_identity: float = RECOGNIZABLE_MIN_IDENTITY,
    focal_strain: str | None = None,
    min_other_strains: int = COHORT_PREVALENCE_MIN_OTHER_STRAINS,
) -> dict[str, Any]:
    """Compute per (BGC, comparator) two-denominator coverage + flags.

    Parameters
    ----------
    per_gene_rows:
        Rows from ``*_3_mibig_per_gene.csv`` (bgc_id, query_gene, mibig_accession,
        mibig_compound, reference_type, pct_identity, ...).
    locus_genes:
        ``{bgc_id: {locus_tag: role}}`` from :func:`load_locus_genes`.  When
        ``None``, the physical-locus denominator degrades to the union of KCB
        query genes and the core denominator is reported as unavailable.
    convergence_rows:
        Optional ``*_3_mibig_convergence.csv`` rows; used only to recover
        ``query_gene_count_total`` when no CDS table is supplied.
    cohort_prevalence:
        Optional ``{mibig_accession: {"strains": K, "total": N, "fraction": f,
        "strain_ids": [...]}}`` from :func:`compute_cohort_prevalence`.
    focal_strain:
        Identifier of the strain whose package is being scored (the runs-dir
        folder name).  When it is among a comparator's ``strain_ids`` it is
        removed from both numerator and denominator, so prevalence measures
        recurrence in OTHER strains and a strain-unique comparator scores 0.
    min_other_strains:
        Minimum denominator (other strains) before promiscuity is assessable;
        below it the flag is ``NOT_ASSESSABLE_SMALL_COHORT``.

    Returns a dict with ``rows`` (one per BGC x comparator) and a ``summary``.
    NON-SCORING: nothing here feeds triage/novelty.
    """
    per_gene_rows = list(per_gene_rows)
    locus_genes = locus_genes or {}

    # Recover total-query-gene counts from convergence rows as a fallback locus
    # denominator when the CDS table is absent.
    conv_total: dict[str, int] = {}
    for row in convergence_rows or []:
        bid = str(row.get("bgc_id", "")).strip()
        try:
            conv_total[bid] = max(conv_total.get(bid, 0), int(float(row.get("query_gene_count_total") or 0)))
        except (TypeError, ValueError):
            continue

    # Group per-gene rows by BGC then comparator (mibig_accession).
    by_bgc: dict[str, list[dict[str, Any]]] = {}
    for row in per_gene_rows:
        bid = str(row.get("bgc_id", "")).strip()
        if bid:
            by_bgc.setdefault(bid, []).append(row)

    out_rows: list[dict[str, Any]] = []
    for bid, rows in sorted(by_bgc.items()):
        inv = locus_genes.get(bid, {})
        core_tags = {t for t, r in inv.items() if r == ROLE_CORE}
        all_core = len(core_tags)
        if inv:
            all_locus = len(inv)
            locus_denom_basis = "cds_table_physical_locus"
        else:
            # Fallback: union of KCB query genes for this BGC.
            all_locus = conv_total.get(bid, 0) or len(
                {str(r.get("query_gene", "")).strip() for r in rows if r.get("query_gene")}
            )
            locus_denom_basis = "kcb_query_gene_union_fallback"

        # Group by comparator.
        by_cmp: dict[str, list[dict[str, Any]]] = {}
        for r in rows:
            acc = str(r.get("mibig_accession") or r.get("reference") or "").strip()
            if acc:
                by_cmp.setdefault(acc, []).append(r)

        bgc_rows: list[dict[str, Any]] = []
        for acc, hits in by_cmp.items():
            # recognizable matched query genes for this comparator
            matched_tags = {
                str(h.get("query_gene", "")).strip()
                for h in hits
                if h.get("query_gene") and _num(h.get("pct_identity")) >= min_identity
            }
            matched_tags.discard("")
            matched_locus = len(matched_tags)

            # role breakdown of the matched genes
            role_counts = _role_breakdown(matched_tags, inv)
            matched_core = len(matched_tags & core_tags) if inv else None

            locus_coverage = round(matched_locus / all_locus, 4) if all_locus else 0.0
            if inv and all_core:
                core_coverage: float | None = round(matched_core / all_core, 4)
            elif inv:
                core_coverage = 0.0  # BGC has no defining-core genes annotated
            else:
                core_coverage = None  # unknown without CDS table

            collision_flag, collision_reason = _collision_flag(matched_core, role_counts, inv)

            rep = _representative_hit(hits)
            median_id = _median([h.get("pct_identity") for h in hits])
            bgc_rows.append(
                {
                    "bgc_id": bid,
                    "mibig_accession": acc,
                    "mibig_compound": rep.get("mibig_compound", ""),
                    "reference_type": rep.get("reference_type", ""),
                    "matched_locus_genes": matched_locus,
                    "all_locus_genes": all_locus,
                    "locus_coverage": locus_coverage,
                    "locus_denominator_basis": locus_denom_basis,
                    "matched_core_genes": matched_core if matched_core is not None else "",
                    "all_core_genes": all_core if inv else "",
                    "core_coverage": core_coverage if core_coverage is not None else "",
                    "matched_core_biosynthetic": role_counts[ROLE_CORE],
                    "matched_tailoring": role_counts[ROLE_TAILORING],
                    "matched_transport": role_counts[ROLE_TRANSPORT],
                    "matched_regulatory": role_counts[ROLE_REGULATORY],
                    "matched_resistance": role_counts[ROLE_RESISTANCE],
                    "matched_other_generic": role_counts[ROLE_OTHER],
                    "matched_unknown": role_counts[ROLE_UNKNOWN],
                    "collision_flag": collision_flag,
                    "collision_reason": collision_reason,
                    "median_pct_identity": median_id,
                    "best_reference_rank": _min_rank(hits),
                    "source_hit_count": len(hits),
                    "claim_safety": CLAIM_SAFETY,
                }
            )

        # within-BGC specificity across comparators (by recognizable matched genes)
        _stamp_within_bgc_specificity(bgc_rows)

        # cohort prevalence (optional de-weighting signal; routing prior, not identity)
        for r in bgc_rows:
            cp = (cohort_prevalence or {}).get(r["mibig_accession"])
            r.update(
                assess_cohort_prevalence(
                    cp, focal_strain=focal_strain, min_other_strains=min_other_strains
                )
            )

        out_rows.extend(bgc_rows)

    out_rows.sort(
        key=lambda r: (
            r["bgc_id"],
            -int(r["matched_locus_genes"]),
            -float(r["median_pct_identity"] or 0),
            r["mibig_accession"],
        )
    )
    summary = _summarize(out_rows)
    return {
        "schema_version": SCHEMA_VERSION,
        "report_only_contract": REPORT_ONLY_CONTRACT,
        "status": "PASS" if out_rows else "NULL_NO_COMPARATORS",
        "rows": out_rows,
        "summary": summary,
        "claim_safety": CLAIM_SAFETY,
        # SCORING_WIRE_HOOK: a future, sign-off-gated change could read
        # summary["collision_low_specificity"] / per-row collision_flag to
        # SUPPRESS (never boost) a comparator's contribution to an AB/AF prior,
        # gated by the existing mis-anchor / primary-metabolism guards and with
        # no double-counting of the KCB anchor. Not wired here. See FA2_HOOK.md.
    }


def _role_breakdown(matched_tags: set[str], inv: dict[str, str]) -> dict[str, int]:
    counts = {
        ROLE_CORE: 0,
        ROLE_TAILORING: 0,
        ROLE_TRANSPORT: 0,
        ROLE_REGULATORY: 0,
        ROLE_RESISTANCE: 0,
        ROLE_OTHER: 0,
        ROLE_UNKNOWN: 0,
    }
    for tag in matched_tags:
        role = inv.get(tag, ROLE_UNKNOWN)
        counts[role] = counts.get(role, 0) + 1
    return counts


def _collision_flag(
    matched_core: int | None, role_counts: dict[str, int], inv: dict[str, str]
) -> tuple[str, str]:
    """Return (flag, reason) for comparator specificity / promiscuity.

    - ``OK_HAS_CORE_SUPPORT``: matched at least one defining-core gene.
    - ``LOW_SPECIFICITY_ACCESSORY_ONLY``: zero core, and every matched gene is a
      transport/regulatory/resistance/other/unknown (primary-metabolism-like)
      gene -> the collision failure mode (AS-XXX BGC052 pattern).
    - ``NO_CORE_TAILORING_ONLY``: zero core but tailoring/accessory-biosynthetic
      support exists (softer; a family clue, not a product call).
    - ``UNRESOLVED_NO_CDS_ROLES``: no CDS role table, cannot judge core support.
    """
    if not inv:
        return "UNRESOLVED_NO_CDS_ROLES", "no CDS role inventory supplied for this BGC"
    if matched_core and matched_core > 0:
        return "OK_HAS_CORE_SUPPORT", f"matched {matched_core} defining-core gene(s)"
    total_matched = sum(role_counts.values())
    if total_matched == 0:
        return "UNRESOLVED_NO_MATCHED_GENES", "no recognizable matched genes"
    accessory = (
        role_counts[ROLE_TRANSPORT]
        + role_counts[ROLE_REGULATORY]
        + role_counts[ROLE_RESISTANCE]
        + role_counts[ROLE_OTHER]
        + role_counts[ROLE_UNKNOWN]
    )
    if role_counts[ROLE_TAILORING] == 0 and accessory == total_matched:
        return (
            "LOW_SPECIFICITY_ACCESSORY_ONLY",
            "0 defining-core genes; support is transport/regulatory/primary-metabolism only",
        )
    return (
        "NO_CORE_TAILORING_ONLY",
        "0 defining-core genes; support limited to tailoring/accessory biosynthetic genes",
    )


def _stamp_within_bgc_specificity(bgc_rows: list[dict[str, Any]]) -> None:
    """Classify each BGC by whether one comparator dominates recognizable support.

    Stamps a per-BGC ``within_bgc_specificity`` on every row of the BGC and a
    per-row ``is_bgc_dominant_comparator`` bool.  Labels:

    - ``UNIQUE``   : a single comparator (no competition).
    - ``CLEAR``    : top comparator leads the runner-up by >= max(2, 25%).
    - ``CO_DOMINANT``: two or more comparators tie for the most matched genes.
    - ``MIXED``    : an intermediate lead (present but below the CLEAR margin).
    """
    if not bgc_rows:
        return
    ranked = sorted(bgc_rows, key=lambda r: -int(r["matched_locus_genes"]))
    top = int(ranked[0]["matched_locus_genes"])
    runner = int(ranked[1]["matched_locus_genes"]) if len(ranked) > 1 else 0
    margin = top - runner
    if len(ranked) == 1:
        status = "UNIQUE"
    elif margin <= 0:
        status = "CO_DOMINANT"
    elif margin >= max(2, ceil(top * 0.25)):
        status = "CLEAR"
    else:
        status = "MIXED"
    top_count = top
    for r in bgc_rows:
        r["within_bgc_specificity"] = status
        r["is_bgc_dominant_comparator"] = int(r["matched_locus_genes"]) == top_count and top_count > 0


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    bgcs = {r["bgc_id"] for r in rows}
    low_spec = [r for r in rows if r["collision_flag"] == "LOW_SPECIFICITY_ACCESSORY_ONLY"]
    no_core = [r for r in rows if r["collision_flag"] == "NO_CORE_TAILORING_ONLY"]
    co_dom_bgcs = {r["bgc_id"] for r in rows if r.get("within_bgc_specificity") == "CO_DOMINANT"}
    unique_bgcs = {r["bgc_id"] for r in rows if r.get("within_bgc_specificity") == "UNIQUE"}
    clear_bgcs = {r["bgc_id"] for r in rows if r.get("within_bgc_specificity") == "CLEAR"}
    promiscuous = [r for r in rows if r.get("cohort_prevalence_flag") == FLAG_PROMISCUOUS]
    not_assessable = [r for r in rows if r.get("cohort_prevalence_flag") == FLAG_NOT_ASSESSABLE]
    return {
        "bgc_count": len(bgcs),
        "comparator_row_count": len(rows),
        "low_specificity_collision_count": len(low_spec),
        "no_core_tailoring_only_count": len(no_core),
        "co_dominant_bgc_count": len(co_dom_bgcs),
        "clear_dominant_bgc_count": len(clear_bgcs),
        "unique_bgc_count": len(unique_bgcs),
        "promiscuous_comparator_row_count": len(promiscuous),
        "prevalence_not_assessable_row_count": len(not_assessable),
        "prevalence_min_other_strains": COHORT_PREVALENCE_MIN_OTHER_STRAINS,
    }


# ---------------------------------------------------------------------------
# Cohort prevalence (optional)
# ---------------------------------------------------------------------------
def compute_cohort_prevalence(
    runs_dir: str | Path, *, diagnostics: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    """Scan a runs directory of sealed packages for comparator prevalence.

    Returns ``{mibig_accession: {"strains": K, "total": N, "fraction": K/N,
    "strain_ids": [sorted strain folder names carrying it]}}`` where K is the
    number of distinct strain packages in which the comparator appears at all in
    ``*_3_mibig_per_gene.csv``.  A comparator recurring in many OTHER strains is
    *promiscuous* (less diagnostic) -> advisory de-weight.  The raw ``fraction``
    is kept for provenance; the flag decision is made by
    :func:`assess_cohort_prevalence`, which excludes the focal strain and applies
    the cohort-size floor.
    """
    runs_dir = Path(runs_dir)
    strain_to_accs: dict[str, set[str]] = {}
    unassessed: dict[str, str] = {}
    # Explicit iteration surfaces discovery errors instead of silently presenting
    # an incomplete cohort as complete. Folder keys retain the existing API.
    for strain_dir in sorted(runs_dir.iterdir()):
        package = strain_dir / "package"
        if not package.is_dir():
            continue
        strain = strain_dir.name
        try:
            matches = sorted(p for p in package.iterdir()
                             if p.name.endswith("_3_mibig_per_gene.csv"))
            if len(matches) != 1:
                unassessed[strain] = "MISSING_OR_AMBIGUOUS_PROFILE"
                continue
            accs: set[str] = set()
            with open(matches[0], newline="", encoding="utf-8") as fh:
                reader = csv.DictReader(fh, strict=True)
                fields = reader.fieldnames
                if not fields or "mibig_accession" not in fields or len(set(fields)) != len(fields):
                    raise ValueError("Invalid comparator profile header")
                for row in reader:
                    if None in row or any(value is None for value in row.values()):
                        raise ValueError("Invalid comparator profile row width")
                    acc = str(row.get("mibig_accession") or "").strip()
                    if acc:
                        accs.add(acc)
            # Admit only after the entire file is read successfully. Header-only
            # CSVs remain observed zero-hit files, not claims of biological absence.
            strain_to_accs[strain] = accs
        except (OSError, UnicodeError, csv.Error, ValueError):
            unassessed[strain] = "UNREADABLE_OR_INVALID_PROFILE"
    if diagnostics is not None:
        diagnostics.update({
            "status": ("NO_ASSESSED_STRAINS" if not strain_to_accs else
                       "PARTIALLY_ASSESSED" if unassessed else "ASSESSED"),
            "assessed_strain_count": len(strain_to_accs),
            "assessed_strain_ids": sorted(strain_to_accs),
            "unassessed_strains": dict(sorted(unassessed.items())),
            "basis": "valid_per_gene_csv_observation_not_biological_absence",
        })
    total = len(strain_to_accs)
    carriers: dict[str, set[str]] = {}
    for strain, accs in strain_to_accs.items():
        for acc in accs:
            carriers.setdefault(acc, set()).add(strain)
    return {
        acc: {
            "strains": len(ids),
            "total": total,
            "fraction": (len(ids) / total if total else 0.0),
            "strain_ids": sorted(ids),
            "cohort_strain_ids": sorted(strain_to_accs),
            "unassessed_strains": dict(sorted(unassessed.items())),
        }
        for acc, ids in sorted(carriers.items())
    }


def assess_cohort_prevalence(
    cp: dict[str, Any] | None,
    focal_strain: str | None = None,
    min_other_strains: int = COHORT_PREVALENCE_MIN_OTHER_STRAINS,
    promiscuous_fraction: float = COHORT_PREVALENCE_PROMISCUOUS_FRACTION,
) -> dict[str, Any]:
    """Turn one comparator's prevalence record into the row's cohort columns.

    Deterministic, claim-safe gate (v9.7.410).  Prevalence is a routing prior
    about how diagnostic a reference is across the cohort, never an identity
    statement.  Three defects of the pre-.410 gate are closed here:

    1. **Focal strain excluded.**  When ``focal_strain`` is among the record's
       ``strain_ids`` it is dropped from numerator and denominator, so a
       strain-unique comparator scores ``0/(N-1)``, not ``1/N``.
    2. **Cohort-size floor.**  Fewer than ``min_other_strains`` other strains ->
       ``NOT_ASSESSABLE_SMALL_COHORT``; no promiscuity verdict is possible.
    3. **Strict boundary.**  Promiscuous only when the other-strain fraction is
       strictly greater than ``promiscuous_fraction``.

    Records without a focal identity may use validated raw counts. With a focal
    identity, its carrier membership proves inclusion; otherwise complete assessed
    cohort membership is required. Unknown membership is not assessed.
    """
    def unavailable(basis: str) -> dict[str, Any]:
        return {
            "cohort_strain_count": "",
            "cohort_total_strains": "",
            "cohort_prevalence": "",
            "cohort_prevalence_flag": FLAG_NOT_COMPUTED,
            "cohort_prevalence_basis": basis,
        }

    if not cp:
        return unavailable("")
    if not isinstance(cp, dict):
        return unavailable("invalid_cohort_record")
    strain_ids = cp.get("strain_ids")
    cohort_ids = cp.get("cohort_strain_ids")
    try:
        def count(value: Any) -> int:
            if isinstance(value, bool) or not isinstance(value, (int, str)):
                raise ValueError("Count must be an integer")
            result = int(value)
            if result < 0:
                raise ValueError("Negative count")
            return result
        strains, total = count(cp.get("strains")), count(cp.get("total"))
        if strains > total:
            raise ValueError("Carrier count exceeds cohort")
        for ids, expected in ((strain_ids, strains), (cohort_ids, total)):
            if ids is not None:
                if not isinstance(ids, (list, tuple, set)):
                    raise ValueError("Invalid membership list")
                if any(not isinstance(i, str) or not i.strip() for i in ids):
                    raise ValueError("Invalid member identity")
                if len(ids) != expected or len(set(ids)) != expected:
                    raise ValueError("Membership count mismatch")
        if cohort_ids is not None:
            if strain_ids is None or not set(strain_ids).issubset(cohort_ids):
                raise ValueError("Carrier absent from assessed cohort")
    except (TypeError, ValueError, OverflowError):
        return unavailable("invalid_cohort_record")
    if isinstance(cohort_ids, (list, tuple, set)) and focal_strain:
        other_strains = strains - int(focal_strain in (strain_ids or ()))
        other_total = total - int(focal_strain in cohort_ids)
        basis = ("other_strains_focal_excluded" if focal_strain in cohort_ids
                 else "other_strains_focal_not_in_assessed_cohort")
    elif isinstance(strain_ids, (list, tuple, set)) and focal_strain and focal_strain in strain_ids:
        other_strains = max(0, strains - 1)
        other_total = max(0, total - 1)
        basis = "other_strains_focal_excluded"
    elif focal_strain:
        return unavailable("focal_membership_unknown")
    else:
        other_strains, other_total = strains, total
        basis = "raw_cohort_fraction_focal_unknown"
    if other_total < max(1, int(min_other_strains)):
        flag = FLAG_NOT_ASSESSABLE
    else:
        fraction = other_strains / other_total
        flag = FLAG_PROMISCUOUS if fraction > promiscuous_fraction else FLAG_COHORT_TYPICAL
    return {
        "cohort_strain_count": other_strains,
        "cohort_total_strains": other_total,
        "cohort_prevalence": f"{other_strains}/{other_total}",
        "cohort_prevalence_flag": flag,
        "cohort_prevalence_basis": basis,
    }


# ---------------------------------------------------------------------------
# CSV / JSON emit
# ---------------------------------------------------------------------------
CSV_COLUMNS = [
    "bgc_id",
    "mibig_accession",
    "mibig_compound",
    "reference_type",
    "matched_locus_genes",
    "all_locus_genes",
    "locus_coverage",
    "locus_denominator_basis",
    "matched_core_genes",
    "all_core_genes",
    "core_coverage",
    "matched_core_biosynthetic",
    "matched_tailoring",
    "matched_transport",
    "matched_regulatory",
    "matched_resistance",
    "matched_other_generic",
    "matched_unknown",
    "collision_flag",
    "collision_reason",
    "within_bgc_specificity",
    "is_bgc_dominant_comparator",
    "cohort_prevalence",
    "cohort_strain_count",
    "cohort_total_strains",
    "cohort_prevalence_flag",
    "cohort_prevalence_basis",
    "median_pct_identity",
    "best_reference_rank",
    "source_hit_count",
    "claim_safety",
]


def _atomic_open(path: Path, *, newline: str | None = None):
    """Crash-safe streamed write: write to a sibling .tmp, os.replace() into place only on
    clean exit (matches mamey/packaging.py::_atomic_write_text / tools/_wbio.py::atomic_open).
    A killed/interrupted process leaves the prior file untouched instead of truncating it --
    this layer is re-run in place over an already-sealed package directory."""
    import contextlib
    import os as _os

    @contextlib.contextmanager
    def _cm():
        tmp = path.with_name(path.name + ".tmp")
        fh = open(tmp, "w", newline=newline, encoding="utf-8")
        try:
            yield fh
        except BaseException:
            fh.close()
            try:
                tmp.unlink()
            except OSError:
                pass
            raise
        else:
            fh.close()
            _os.replace(tmp, path)

    return _cm()


def write_csv(result: dict[str, Any], out_path: str | Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with _atomic_open(out_path, newline="") as fh:
        writer = _SafeDictWriter(fh, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in result["rows"]:
            writer.writerow(row)
    return out_path


def write_summary_json(result: dict[str, Any], out_path: str | Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": result["schema_version"],
        "report_only_contract": result["report_only_contract"],
        "status": result["status"],
        "summary": result["summary"],
        "claim_safety": result["claim_safety"],
    }
    with _atomic_open(out_path) as fh:
        json.dump(payload, fh, indent=2)
    return out_path


# ---------------------------------------------------------------------------
# Package-level convenience (used by the CLI hook / __main__)
# ---------------------------------------------------------------------------
def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def run_for_package(package_dir: str | Path, cohort_runs_dir: str | Path | None = None) -> dict[str, Any]:
    """Run the layer against a sealed package directory and write outputs.

    Discovers ``*_3_mibig_per_gene.csv``, ``*_3_mibig_convergence.csv`` and
    ``*_cds_table.csv`` by their strain prefix, emits
    ``<STRAIN>_3b_comparator_coverage.csv`` and
    ``<STRAIN>_3b_comparator_coverage_summary.json`` alongside them.
    """
    package_dir = Path(package_dir)
    per_gene_files = sorted(package_dir.glob("*_3_mibig_per_gene.csv"))
    if not per_gene_files:
        raise FileNotFoundError(f"no *_3_mibig_per_gene.csv under {package_dir}")
    per_gene_path = per_gene_files[0]
    strain = per_gene_path.name[: -len("_3_mibig_per_gene.csv")]

    per_gene_rows = _read_csv(per_gene_path)
    convergence_rows = _read_csv(package_dir / f"{strain}_3_mibig_convergence.csv")
    cds_rows = _read_csv(package_dir / f"{strain}_cds_table.csv")
    locus_genes = load_locus_genes(cds_rows) if cds_rows else None

    cohort_diagnostics: dict[str, Any] = {}
    cohort_prevalence = (
        compute_cohort_prevalence(cohort_runs_dir, diagnostics=cohort_diagnostics)
        if cohort_runs_dir else None
    )
    # Focal identity for the prevalence gate: the runs-dir folder that holds this
    # package (runs/<STRAIN>/package) when available, else the file-name prefix.
    focal_strain = strain
    if cohort_runs_dir and package_dir.name == "package":
        focal_strain = package_dir.parent.name

    result = compute_comparator_coverage(
        per_gene_rows,
        locus_genes=locus_genes,
        convergence_rows=convergence_rows,
        cohort_prevalence=cohort_prevalence,
        focal_strain=focal_strain,
    )
    if cohort_runs_dir:
        result["summary"]["cohort_evidence_admission"] = cohort_diagnostics
    csv_path = write_csv(result, package_dir / f"{strain}_3b_comparator_coverage.csv")
    json_path = write_summary_json(
        result, package_dir / f"{strain}_3b_comparator_coverage_summary.json"
    )
    result["_written"] = {"csv": str(csv_path), "summary_json": str(json_path), "strain": strain}
    return result


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _num(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _median(values: Iterable[Any]) -> float | None:
    vals = sorted(_num(v) for v in values if v not in (None, ""))
    if not vals:
        return None
    n = len(vals)
    return round(vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2, 3)


def _min_rank(hits: list[dict[str, Any]]) -> Any:
    ranks = []
    for h in hits:
        try:
            ranks.append(int(float(h.get("reference_rank"))))
        except (TypeError, ValueError):
            continue
    return min(ranks) if ranks else ""


def _representative_hit(hits: list[dict[str, Any]]) -> dict[str, Any]:
    return sorted(
        hits,
        key=lambda h: (int(float(h.get("reference_rank") or 999999)), -_num(h.get("blast_score"))),
    )[0]


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "FA2 two-denominator comparator coverage (report-only, non-scoring). "
            "Consumes a sealed package's per-gene MIBiG rows and emits "
            "<STRAIN>_3b_comparator_coverage.csv + summary JSON."
        )
    )
    parser.add_argument("package_dir", help="sealed package directory (contains *_3_mibig_per_gene.csv)")
    parser.add_argument(
        "--cohort-runs-dir",
        default=None,
        help="optional runs dir (*/package/*_3_mibig_per_gene.csv) for cohort comparator prevalence",
    )
    args = parser.parse_args(argv)
    result = run_for_package(args.package_dir, cohort_runs_dir=args.cohort_runs_dir)
    written = result["_written"]
    summary = result["summary"]
    emit(f"[FA2] strain={written['strain']} status={result['status']}", f"[FA2] wrote {written['csv']}", f"[FA2] wrote {written['summary_json']}", f"[FA2] summary: {json.dumps(summary)}", sep="\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
