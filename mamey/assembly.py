from __future__ import annotations
from .models import AssemblyMetrics

def n50(lengths: list[int]) -> int | None:
    if not lengths:
        return None
    total = sum(lengths)
    running = 0
    for length in sorted(lengths, reverse=True):
        running += length
        if running >= total / 2:
            return length
    return None

def gc_pct_from_sequences(seqs: list[str]) -> float | None:
    gc = 0
    total = 0
    for seq in seqs:
        s = seq.upper()
        gc += s.count("G") + s.count("C")
        total += sum(s.count(x) for x in "ACGT")
    return round(gc / total * 100.0, 3) if total else None

def metrics_from_sequences(seqs: dict[str, str]) -> AssemblyMetrics:
    lengths = [len(s) for s in seqs.values()]
    return AssemblyMetrics(sum(lengths), len(lengths), n50(lengths), gc_pct_from_sequences(list(seqs.values())), max(lengths) if lengths else None)


def _contig_gc(seq: str) -> float | None:
    s = seq.upper()
    acgt = sum(s.count(x) for x in "ACGT")
    return (s.count("G") + s.count("C")) / acgt * 100.0 if acgt else None


# AMBER-03-3: floor for a free-living actinomycete genome. The smallest complete
# actinomycete genomes are ~3.5 Mb (obligate symbionts aside); everything in this
# project's cohorts is 7-10 Mb. A record far below this is almost always a PARTIAL
# GenBank submission — one plasmid, one scaffold, one WGS record — not a small genome.
# Deliberately generous (3.0 Mb) so a genuinely small actinobacterium is not flagged.
ACTINOMYCETE_MIN_BP = 3_000_000
# a single record this far below the floor is a truncated/partial submission, not an assembly
PARTIAL_SUBMISSION_MAX_CONTIGS = 5


def assembly_sanity_check(seqs: dict[str, str], *, expected_gc: float | None = None,
                          expected_size_bp: tuple[int, int] | None = None,
                          min_genome_bp: int | None = ACTINOMYCETE_MIN_BP) -> dict:
    """PC-A2 (v9.7.101): non-blocking contamination / assembly-sanity check.

    Two VERY_POOR drafts passed as MAMEY_COMPLETE with no flag despite clear assembly
    pathology (bimodal GC, ~3-4 Mb foreign content) measurable from data already computed.
    This emits CONTAMINATION_SUSPECT / ASSEMBLY_SANITY WARNINGs when:
      (a) genome-wide GC deviates strongly from a taxon/expected prior (if one is given);
      (b) per-contig GC dispersion is high (sd above threshold — clean genomes ~1-2%, the
          contaminated drafts were 7-12%);
      (c) assembly size is outside an expected genus range (if one is given);
      (d) AMBER-03-3: assembly size is far below the actinomycete floor, with no prior
          needed — the partial-GenBank-submission case.

    Non-blocking by design: returns flags + the measured stats for the analyst to judge.
    expected_gc / expected_size_bp are optional taxon priors; when absent, the dispersion
    check and the (d) size-floor check (neither of which needs a prior) fire.

    (d) exists because the size check was UNREACHABLE in practice: run_one_strain calls
    this with no priors at all, so `expected_size_bp` was always None and the size branch
    never ran. Actinophytocola sp. NPDC049390 (1,462,829 bp, one contig) was therefore
    reported with 4 BGCs / 3.5 corrected and assembly_tier "GOOD", with ZERO warnings,
    next to congeners of 9.75 Mb / 34 BGCs and 7.38 Mb / 29 BGCs. Its BGC count is a
    property of a ~19%-complete submission, not a measurement of the organism.
    Pass min_genome_bp=None to disable (e.g. a deliberate plasmid/contig-level run).
    """
    flags: list[str] = []
    per_contig = {name: _contig_gc(s) for name, s in seqs.items() if s}
    gcs = [g for g in per_contig.values() if g is not None]
    weights = [len(seqs[n]) for n, g in per_contig.items() if g is not None]
    genome_bp = sum(len(s) for s in seqs.values())

    # (b) per-contig GC dispersion (length-weighted sd) — needs no prior
    gc_sd = None
    if len(gcs) >= 2:
        tot = sum(weights) or 1
        mean = sum(g * w for g, w in zip(gcs, weights)) / tot
        var = sum(w * (g - mean) ** 2 for g, w in zip(gcs, weights)) / tot
        gc_sd = var ** 0.5
        if gc_sd >= 5.0:  # clean genomes ~1-2%; contaminated drafts were 7-12%
            flags.append("CONTAMINATION_SUSPECT")

    # (a) genome-wide GC vs prior
    overall_gc = gc_pct_from_sequences(list(seqs.values()))
    if expected_gc is not None and overall_gc is not None and abs(overall_gc - expected_gc) >= 8.0:
        flags.append("ASSEMBLY_SANITY")

    # (c) size outside expected genus range
    if expected_size_bp is not None and genome_bp:
        lo, hi = expected_size_bp
        if genome_bp < lo or genome_bp > hi:
            flags.append("ASSEMBLY_SANITY")

    # (d) AMBER-03-3: no prior needed. A record far below the actinomycete floor is a
    # partial submission; its BGC count must not be read as a measurement of the organism.
    partial_submission = False
    if min_genome_bp and genome_bp and genome_bp < min_genome_bp:
        flags.append("PARTIAL_ASSEMBLY_SUSPECT")
        if len(seqs) <= PARTIAL_SUBMISSION_MAX_CONTIGS:
            # few records AND far too small = a truncated accession, not a fragmented draft
            partial_submission = True
            flags.append("PARTIAL_SUBMISSION_SUSPECT")

    return {
        "flags": sorted(set(flags)),
        "partial_submission_suspect": partial_submission,
        "min_genome_bp": min_genome_bp,
        "overall_gc": overall_gc,
        "per_contig_gc_sd": round(gc_sd, 2) if gc_sd is not None else None,
        "genome_bp": genome_bp,
        "n_contigs": len(seqs),
        "claim_safety": ("Non-blocking heuristic. High per-contig GC dispersion or a strong "
                         "GC/size deviation from a taxon prior suggests possible contamination or "
                         "co-assembly; a size far below the actinomycete floor suggests a partial "
                         "GenBank submission, whose BGC count is a property of the submission and "
                         "not of the organism; the analyst decides — extraction is unaffected."),
    }

def corrected_bgc_count(interior: int, edge: int, full_contig: int) -> float:
    return round(interior + 0.5 * edge + 0.25 * full_contig, 2)

def assembly_tier(interior_pct: float | None) -> str:
    if interior_pct is None:
        return "UNKNOWN"
    if interior_pct >= 70:
        return "GOOD"
    if interior_pct >= 45:
        return "MODERATE"
    if interior_pct >= 20:
        return "POOR"
    return "VERY_POOR"


# ---------------------------------------------------------------------------
# Assembly CONTIGUITY quality + machine-generated caveat text  (AMBER-03-1)
# ---------------------------------------------------------------------------
# assembly_tier() above is derived from interior_pct — the fraction of BGCs that
# sit fully inside a contig. It answers "how trustworthy is the BGC inventory?",
# NOT "how contiguous is this assembly?". It is nevertheless named `assembly_tier`
# and printed immediately after contigs/N50 in the strain brief, so it reads as an
# assembly-quality statement: AS-XXX (7,296 contigs, N50 7,936 bp) carries
# assembly_tier "GOOD" in its manifest, brief and every cohort figure.
#
# The functions below answer the contiguity question from contigs/N50/genome size
# and emit a ready-to-paste caveat sentence, so a figure caption or a tree note can
# be GENERATED from the manifest instead of hand-typed. Hand-typed cohort numbers
# drift: a caption reading "4 of 25 assemblies exceed 6,000 contigs" was written
# against a cohort that is 47 strains (the "4" happened to still be right; the
# denominator was not).
#
# Claim-safety: this is an assembly-quality descriptor only. It never changes a
# score, a tier, a gate verdict or a product claim — it exists so a downstream
# figure is harder to get wrong.

# (tier, max_contigs, min_n50_bp) — the FIRST band where both hold wins.
FRAGMENTATION_BANDS: tuple[tuple[str, int, int], ...] = (
    ("CLOSED",       2, 1_000_000),
    ("CONTIGUOUS",  20,   500_000),
    ("DRAFT",      100,   100_000),
    ("FRAGMENTED", 1000,    10_000),
)
HIGHLY_FRAGMENTED_CONTIGS = 1000
# tiers whose numbers must not be presented without a caveat
CAVEAT_TIERS = frozenset({"FRAGMENTED", "HIGHLY_FRAGMENTED", "UNKNOWN"})


def fragmentation_tier(contigs: int | None, n50: int | None) -> str:
    """CLOSED | CONTIGUOUS | DRAFT | FRAGMENTED | HIGHLY_FRAGMENTED | UNKNOWN.

    Contiguity only. Deliberately independent of assembly_tier(interior_pct).
    """
    if not contigs or contigs <= 0:
        return "UNKNOWN"
    for tier, max_contigs, min_n50 in FRAGMENTATION_BANDS:
        if contigs <= max_contigs and (n50 or 0) >= min_n50:
            return tier
    return "HIGHLY_FRAGMENTED"


def _asm_fields(metrics) -> dict:
    """Accept an AssemblyMetrics or a manifest['assembly'] dict, uniformly."""
    if isinstance(metrics, dict):
        return metrics
    return {"genome_bp": getattr(metrics, "genome_bp", None),
            "contigs": getattr(metrics, "contigs", None),
            "n50": getattr(metrics, "n50", None),
            "gc_pct": getattr(metrics, "gc_pct", None),
            "largest_contig": getattr(metrics, "largest_contig", None)}


def assembly_caveat_sentence(tier: str, contigs: int | None, n50: int | None,
                             label: str | None = None) -> str:
    """One ready-to-paste sentence, or '' when no caveat is required."""
    who = f"{label}: " if label else ""
    n_txt = f"{contigs:,}" if contigs else "an unrecorded number of"
    n50_txt = f"{n50:,} bp" if n50 else "unrecorded"
    if tier == "UNKNOWN":
        return (f"{who}assembly contiguity was not recorded; BGC counts and "
                f"phylogenomic branch lengths for this genome are unverified and "
                f"should be reported as floors, not measurements.")
    if tier in ("FRAGMENTED", "HIGHLY_FRAGMENTED"):
        strength = "highly fragmented" if tier == "HIGHLY_FRAGMENTED" else "fragmented"
        return (f"{who}{strength} draft assembly ({n_txt} contigs, N50 {n50_txt}). "
                f"BGC counts are a floor, not a measurement, and branch lengths from "
                f"this genome are not trustworthy even where the tip position holds.")
    return ""


def assembly_quality(metrics) -> dict:
    """Machine-readable assembly-quality block for the manifest.

    Returns fragmentation_tier + caveat_required + a generated caveat sentence,
    so captions are generated from the table rather than typed alongside it.
    """
    a = _asm_fields(metrics)
    contigs, n50 = a.get("contigs"), a.get("n50")
    tier = fragmentation_tier(contigs, n50)
    return {
        "fragmentation_tier": tier,
        "contigs": contigs,
        "n50": n50,
        "genome_bp": a.get("genome_bp"),
        "largest_contig": a.get("largest_contig"),
        "caveat_required": tier in CAVEAT_TIERS,
        "caveat": assembly_caveat_sentence(tier, contigs, n50),
        "basis": ("contigs/N50 contiguity bands; independent of bgc_counts.assembly_tier, "
                  "which is derived from interior_pct (BGC boundary status) and is NOT an "
                  "assembly-contiguity statement."),
    }


def cohort_assembly_caveat(records) -> dict:
    """Cohort-level caveat, generated — the sentence that keeps being hand-typed.

    `records` is an iterable of (label, metrics), where metrics is an
    AssemblyMetrics or a manifest['assembly'] dict. Returns counts, the per-tier
    census and a ready-to-paste caption sentence. Order of the named strains is
    deterministic (contig count descending, then label).
    """
    rows = []
    for label, metrics in records:
        a = _asm_fields(metrics)
        rows.append((str(label), a.get("contigs"), a.get("n50"),
                     fragmentation_tier(a.get("contigs"), a.get("n50"))))
    total = len(rows)
    tier_counts: dict[str, int] = {}
    for _, _, _, t in rows:
        tier_counts[t] = tier_counts.get(t, 0) + 1
    flagged = sorted([r for r in rows if r[3] in CAVEAT_TIERS],
                     key=lambda r: (-(r[1] or 0), r[0]))
    if not total:
        caption = "No assemblies supplied; no assembly-quality caveat can be generated."
    elif not flagged:
        caption = (f"Assembly quality: all {total} assemblies are DRAFT or better "
                   f"(≤{FRAGMENTATION_BANDS[-2][1]:,} contigs, N50 "
                   f"≥{FRAGMENTATION_BANDS[-2][2]:,} bp); no fragmentation caveat applies.")
    else:
        named = "; ".join(f"{lab} {c:,}" for lab, c, _, _ in flagged[:5] if c)
        more = f"; and {len(flagged) - 5} more" if len(flagged) > 5 else ""
        caption = (
            f"Assembly quality: {len(flagged)} of {total} assemblies are FRAGMENTED or worse "
            f"(>{FRAGMENTATION_BANDS[-1][1]:,} contigs or N50 <{FRAGMENTATION_BANDS[-1][2]:,} bp)"
            + (f" — most fragmented: {named}{more}" if named else "")
            + ". For these, BGC counts are floors and branch lengths are not trustworthy; "
              "the tip position may still hold."
        )
    return {
        "n_assemblies": total,
        "n_caveat_required": len(flagged),
        "tier_counts": dict(sorted(tier_counts.items())),
        "flagged": [{"label": lab, "contigs": c, "n50": n, "fragmentation_tier": t}
                    for lab, c, n, t in flagged],
        "caption": caption,
    }
