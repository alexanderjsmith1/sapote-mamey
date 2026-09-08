"""mamey.pathway_believability — per-LOCUS committed-step believability prior (FA4 prototype).

A claim-safe, NON-RANKING "is this class call structurally coherent?" prior. antiSMASH fires a class
rule (and Mamey a CCTT trigger) on a single diagnostic hit, but many classes have a hard *committed
step* whose gateway Pfam is degenerate, so the label over-calls. This module returns a tiered read of
one LOCUS (a list of CDS dicts) against the known enzymology of the class:

    HIGH    : gateway (good hit) + committed pull + >=1 downstream (tailoring/TIGR/assembly)
    MEDIUM  : gateway (good hit) + partial corroboration (committed pull OR >=2 associated markers)
    LOW     : gateway only / weak, no committed pull, <=1 associated marker  -> named-FP risk
    SUSPECT : class flagged by antiSMASH/CCTT but NO gateway enzyme captured
    NONE    : neither gateway nor class flag -> not a candidate for this class

Worked example (shipped): PHOSPHONATE. PEP --(PEP mutase, PepM: the committed C-P bond)-->
phosphonopyruvate --(phosphonopyruvate decarboxylase, a TPP enzyme: the committed pull)--> ... .
A lone/weak PepM with no downstream context is the principal false positive: the PepM Pfam sits in
the isocitrate-lyase (ICL) superfamily and also matches primary-metabolism enzymes (carboxyPEP
mutase, methylisocitrate lyase). This prior returns LOW there instead of a confident phosphonate
call — defeating the ICL-superfamily over-call.

RELATIONSHIP TO `mamey.class_believability` (reconciliation, no duplication):
  * `class_believability` is the PACKAGE/COHORT driver: it reads a sealed package's
    `*_gene_context.jsonl` + inventory, runs LOCAL (per-BGC) and POOLED (per-strain) passes, and
    emits the `class-believability` subcommand's CSV/JSON.
  * THIS module is the IO-FREE, per-LOCUS entry point: give it a plain list of CDS dicts and it
    returns a tier. It is what a Mode-B card author, a §-level checklist, or a unit test calls when
    it has a locus in hand and no package on disk.
  * There is ONE source of truth for the marker sets and tier logic: this module DELEGATES to
    `class_believability.REGISTRY` / `scan_bgc` / `classify`. Adding a validated class there makes
    it available here automatically.

CLAIM-SAFETY / NON-RANKING CONTRACT: the returned `believability_tier` is advisory. It is a
capacity-level coherence prior, NOT a score. It MUST NOT feed AB/AF/novelty priors or the lead tier;
`BelievabilityResult.non_ranking` is `True` to make that contract explicit at the call site.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

from . import class_believability as _cb

# Re-export the tier vocabulary so callers don't reach into class_believability.
TIERS = ("HIGH", "MEDIUM", "LOW", "SUSPECT", "NONE")


@dataclass(frozen=True)
class BelievabilityResult:
    """One locus's committed-step read for one class. Advisory / non-ranking."""
    cls: str
    believability_tier: str          # one of TIERS
    reason: str
    evidence: dict = field(default_factory=dict)
    non_ranking: bool = True         # hard contract: never feeds AB/AF/novelty/lead tier

    @property
    def tier(self) -> str:           # convenience alias
        return self.believability_tier


def available_classes() -> list[str]:
    """Validated classes shipped in the shared registry (currently: phosphonate)."""
    return sorted(_cb.REGISTRY)


def _module(cls: str) -> "_cb.ClassModule":
    try:
        return _cb.REGISTRY[cls]
    except KeyError:
        raise ValueError(
            f"no validated believability module for class {cls!r}; "
            f"available: {available_classes()} (add it to class_believability.REGISTRY first)"
        )


def classify_locus(cds_list: Sequence[Mapping], cls: str = "phosphonate") -> BelievabilityResult:
    """Read one locus (list of CDS dicts: locus_tag / sec_met_domains / product / gene_functions)
    against class `cls` and return its non-ranking believability tier + evidence.

    Delegates the marker scan and tier logic to `class_believability` so the phosphonate (and any
    future) rule lives in exactly one place. Boundary/assembly status is NOT considered here — a
    genuine gateway on a contig edge is still a genuine gateway (fragment-surfacing principle)."""
    mod = _module(cls)
    m = _cb.scan_bgc(list(cds_list), mod)
    tier, reason = _cb.classify(m, mod)
    evidence = {
        "gateway": m["gateway"],
        "gateway_loci": m["gateway_loci"],
        "gateway_bitscore": m["gateway_bitscore"],
        "committed": m["committed"],
        "tigr": m["tigr"],
        "warhead_count": m["warhead_count"],
        "assembly": m["assembly"],
        "engine_flag": m["engine_flag"],
        "n_cds": m["n_cds"],
        "fp_superfamily": mod.fp_superfamily,
    }
    return BelievabilityResult(cls=mod.name, believability_tier=tier, reason=reason, evidence=evidence)


def believability_tier(cds_list: Sequence[Mapping], cls: str = "phosphonate") -> str:
    """Convenience: just the tier string (one of TIERS) for a locus under class `cls`."""
    return classify_locus(cds_list, cls).believability_tier
