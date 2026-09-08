"""reference_dark — package-native reference-dark novelty re-projection.

Turns the per-gene multi-channel roster model (`roster_v2.build_gene_roster`) into a
per-BGC novelty synthesis and a novelty-first ranking. Reader-side, offline, non-scoring:
it only re-projects channel hits that are already in the sealed package. It never re-runs
antiSMASH, never re-BLASTs, and never changes an engine score, tier, or gate.

Why this exists
---------------
Anchor-based comparisons (KnownClusterBlast, MIBiG identity) systematically *understate*
novelty for rare-genus and fragmented genomes: the honest reference set is thin, so a
genuinely new cluster can still show a familiar top hit. The complementary, honest signal
is **reference-dark novelty**, measured against the broad nr protein space:

  * "confirmed reference-dark core" gene = a biosynthetic-core gene (a PKS/NRPS module or
    RiPP-machinery role) whose *best nr BLASTp hit* is < 60 % identity. The gene WAS
    compared against nr and the nearest known protein is still distant. This is the
    novelty-leaning evidence.

  * "core nr-todo" = a biosynthetic-core gene with **no nr hit recorded** — i.e. the nr
    channel has not been run for it yet. This is a **coverage gap, NOT novelty**. It is
    kept strictly separate from the confirmed count and never contributes to novelty;
    resolve it by running nr, not by inference.

Collapsing these two would inflate novelty on exactly the sparse-coverage genomes this
metric is meant to serve honestly, so the split is the whole point.

Claim ceiling
-------------
Every %id is homology — "capacity consistent with," never "produces." A low nr identity
is a *novelty-leaning* lead at class level, not a structural or bioactivity claim. A null
nr channel means NOT RUN, never a biological zero. MIBiG compound names are similarity
anchors, not independent confirmation. Ranking re-orders leads for a human reader;
judgment is deferred to Sapote.

Engine target: Mamey >= v1.9.119 / bundle v9.7.349. Author: Claude session 2026-08-03.
"""
from __future__ import annotations

import re
from collections import Counter
from statistics import median
from typing import Any

# nr best-hit identity at or below this is "reference-dark" (novelty-leaning).
from .convergence_band import REFERENCE_DARK_BELOW as DARK_PID_CUTOFF  # shared band contract (BB02); == 60.0, never a literal

# Class tokens that mark a *specialised* (secondary-metabolite) product. Products that are
# only saccharide/terpene/other primary-metabolism-adjacent classes are flagged
# non-specialised — surfaced with a denominator, never silently down-weighted.
_SPECIALISED_TOKENS = (
    "pks", "nrps", "nrp", "ripp", "lasso", "lanthi", "transat", "napaa",
    "siderophore", "nrp-metallophore",
)
_NONSPECIALISED_RE = re.compile(
    r"[\s;]*((saccharide|terpene|betalactone|other|butyrolactone|ectoine|melanin|hserlactone)[\s;]*)+",
    re.IGNORECASE,
)
# A biosynthetic-core gene: role_group tagged "biosynthetic core" by roster_v2, or a role
# string naming a PKS/NRPS module or RiPP machinery.
_CORE_ROLE_RE = re.compile(r"module|ripp", re.IGNORECASE)


def _is_core(gene: dict) -> bool:
    if "core" in (gene.get("role_group") or "").lower():
        return True
    return bool(_CORE_ROLE_RE.search(gene.get("role") or ""))


def _is_specialised(products: str) -> bool:
    p = (products or "").lower()
    if any(tok in p for tok in _SPECIALISED_TOKENS):
        return True
    if _NONSPECIALISED_RE.fullmatch(p):
        return False
    return True


def _nr_pid(gene: dict) -> float | None:
    """Best nr %id for a gene, or None when nr was not run for it (no fabricated zero)."""
    nr = (gene.get("channels") or {}).get("nr")
    if not nr:
        return None
    pid = nr.get("pid")
    return pid if isinstance(pid, (int, float)) else None


def _has_channel(gene: dict, channel: str) -> bool:
    return bool((gene.get("channels") or {}).get(channel))


def _median(values: list[float]) -> float | None:
    vals = [v for v in values if v is not None]
    return round(median(vals), 1) if vals else None


def synthesize_bgc(bgc: dict) -> dict:
    """Per-BGC reference-dark synthesis. Confirmed core-dark and core nr-todo are separate."""
    genes = bgc.get("genes") or []
    n = len(genes)

    nr_pids = [p for p in (_nr_pid(g) for g in genes) if p is not None]
    mibig_pids = [
        c["pid"] for g in genes
        if (c := (g.get("channels") or {}).get("mibig")) and c.get("pid") is not None
    ]

    # reference-dark = compared against nr, best hit still distant
    dark = [g for g in genes if (p := _nr_pid(g)) is not None and p < DARK_PID_CUTOFF]
    no_nr = [g for g in genes if not _has_channel(g, "nr")]
    no_mibig = [g for g in genes if not _has_channel(g, "mibig")]

    core = [g for g in genes if _is_core(g)]
    core_dark = [g for g in core if (p := _nr_pid(g)) is not None and p < DARK_PID_CUTOFF]
    core_nr_todo = [g for g in core if not _has_channel(g, "nr")]  # coverage gap, NOT novelty

    compounds = [
        c["compound"] for g in genes
        if (c := (g.get("channels") or {}).get("mibig")) and c.get("compound")
    ]
    dominant, recurrence = ("—", 0)
    if compounds:
        dominant, recurrence = Counter(compounds).most_common(1)[0]
    coherent = bool(compounds) and recurrence >= 0.6 * len(compounds)

    return {
        "bgc_id": bgc.get("bgc_id", ""),
        "products": bgc.get("products", ""),
        "boundary": bgc.get("boundary", ""),
        "genes": n,
        "nr_hits": len(nr_pids),
        "nr_median_pid": _median(nr_pids),
        "mibig_hits": len(mibig_pids),
        "reference_dark": len(dark),
        "no_nr": len(no_nr),
        "no_mibig": len(no_mibig),
        "no_mibig_fraction": round(len(no_mibig) / n, 3) if n else 0.0,
        "core": len(core),
        # the honesty split:
        "confirmed_core_dark": len(core_dark),   # novelty-leaning evidence
        "core_nr_todo": len(core_nr_todo),       # coverage gap, resolve by running nr
        "dominant_mibig_compound": dominant,
        "dominant_mibig_recurrence": recurrence,
        "coherent_family": coherent,
        "specialised": _is_specialised(bgc.get("products", "")),
    }


def novelty_score(s: dict) -> float:
    """Novelty-leaning rank key. Confirmed core reference-dark weighs most; core nr-todo is a
    COVERAGE gap and deliberately contributes nothing. Non-specialised classes are nudged
    down but still surfaced with their denominators, never dropped."""
    core = s["core"] or 1
    n = s["genes"] or 1
    return (
        s["confirmed_core_dark"] * 3.0
        + (s["confirmed_core_dark"] / core) * 2.0
        + s["no_mibig_fraction"]
        + (1.0 if s["specialised"] else -1.0)
        + (s["reference_dark"] / n)
    )


def novelty_ranking(gene_roster: dict) -> list[dict]:
    """Rank a strain's BGCs by reference-dark novelty.

    Input: the `roster_v2.build_gene_roster` model
        {strain, channels_present, bgcs:[{bgc_id, products, boundary,
          genes:[{role, role_group, channels:{nr:{pid}|null, mibig:..., ...}}]}]}

    Output: one dict per BGC (only BGCs with genes), sorted best-novelty first, each carrying
    the full synthesis plus:
        rank                 1-based novelty rank
        novelty_score        the ranking key (re-projection, not an engine score)
        strain               carried through for convenience

    Ordering: confirmed core reference-dark count, then no-MIBiG fraction, then specialised
    class (all folded into `novelty_score`, with confirmed_core_dark / no_mibig_fraction /
    specialised as explicit tie-breakers so ties are deterministic).
    """
    strain = gene_roster.get("strain", "")
    syntheses = [
        synthesize_bgc(b) for b in gene_roster.get("bgcs", []) if b.get("genes")
    ]
    for s in syntheses:
        s["novelty_score"] = round(novelty_score(s), 4)
        s["strain"] = strain

    syntheses.sort(
        key=lambda s: (
            -s["novelty_score"],
            -s["confirmed_core_dark"],
            -s["no_mibig_fraction"],
            0 if s["specialised"] else 1,
            s["bgc_id"],
        )
    )
    for rank, s in enumerate(syntheses, 1):
        s["rank"] = rank
    return syntheses


def novelty_rows(gene_roster: dict) -> tuple[list[str], list[list[Any]]]:
    """Flat (header, rows) table for a small package-native CSV (render-widgets side-car).

    Column meaning is explicit so the file is self-documenting: `confirmed_core_dark` is the
    novelty-leaning count; `core_nr_todo` is a coverage gap kept separate, never novelty."""
    header = [
        "rank", "strain", "bgc_id", "products", "specialised",
        "confirmed_core_dark", "core", "core_nr_todo",
        "reference_dark", "genes", "nr_hits", "nr_median_pid",
        "no_mibig", "no_mibig_fraction",
        "dominant_mibig_compound", "dominant_mibig_recurrence", "coherent_family",
        "novelty_score",
    ]
    rows = [[s[k] for k in header] for s in novelty_ranking(gene_roster)]
    return header, rows
