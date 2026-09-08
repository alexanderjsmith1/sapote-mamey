#!/usr/bin/env python3
"""mamey good-guesses — the "Good Guesses" interpretive-priors report (FA7 prototype).

THE GAP THIS FILLS
------------------
A sealed package carries every evidence channel needed to form a disciplined interpretive
read of a notable BGC — the triage board (Arch_Capacity, Lead_tier_auto, AB/AF, KCB_top,
Misanchor_Flag, RGGMCI_support, CCTT_triggers, Primary_metab_flag, Standing_rule), the MIBiG
convergence tier + class-concordance (`*_3_mibig_convergence.csv`), and the reference-dark
profile (`*_3_mibig_profile.csv`: recognizable-gene fraction / interpretation class). What no
existing artifact does is SYNTHESIZE those channels, per notable BGC, into the single best
CLAIM-SAFE interpretive read: a class-level capacity hypothesis, a confidence band, the evidence
it rests on, and the experiment that would resolve it — WITHOUT crossing into structure/production
claims.

"Good Guesses" is that disciplined judgment layer. It is NOT a flat per-lead dump: each Good
Guess is TAGGED with the flavour(s) that make it worth a second look, and the report leads with
the most striking. The flavours are earned from real package signals, never asserted:

  * SOLID       — concordant MIBiG convergence (CONCORDANT) + committed core machinery
                  (recognizable-gene fraction) + specific dominance. The near-family calls.
  * RARE        — rare chemistry: CCTT warhead/class triggers (enediyne, phosphonate, thioamide,
                  halogenase, PTM tetramate…), uncommon product classes, low cohort prevalence.
  * REMARKABLE  — strong reference-dark novelty (high AB/AF capacity but NO family anchor — a
                  novelty PRIOR, not proof), multi-class committed hybrids, RG-GMCI split-pathway
                  rescues.
  * NOTABLE     — the engine surfacing something by correcting itself: a mis-anchor caught by a
                  guard, a standing-rule demotion, a strain-level capacity outlier.
  * INTERESTING — invites a second look but is lower-confidence (discordant-but-anchored,
                  unresolved concordance).

CLAIM SAFETY (critical, load-bearing — this is the point of the deliverable)
----------------------------------------------------------------------------
Every Good Guess is a CLASS-LEVEL biosynthetic-capacity hypothesis. It is explicitly hedged,
judgment is deferred, and it makes NO structure, product-identity, expression, production, or
bioactivity claim. Sequence similarity is relatedness, NOT identity. A reference-dark BGC's guess
is a "novelty PRIOR, not proof of a new compound." The confidence band rates how coherent the
CAPACITY read is, never how likely a compound is real. Wet-lab evidence is required for any
activity or structure statement — the "resolving experiment" names exactly what that evidence is.

This module READS already-scored package outputs and changes nothing: it is report-only and
NON-scoring. It never feeds AB/AF/novelty priors or the lead tier.

Usage:
    python mamey_run.py good-guesses [ROOT] [--out DIR] [--depth N] [--pdf] [--docx]
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
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from mamey.csv_safety import SafeDictWriter
from mamey.exact_identity import (
    ExactLocusIdentityError,
    NativeManifestBGCIdentity,
    exact_locus_display,
    exact_locus_from_mapping,
    exact_locus_from_native_inventory_row,
    validate_native_legacy_evidence_anchor,
)
from mamey.manifest_schema import F_STRAIN_ID, read_manifest_field
from mamey.reference_dark_prior import _has_mibig

# --------------------------------------------------------------------------- claim-safety
CLAIM_CEILING = (
    "Every Good Guess below is a CLASS-LEVEL biosynthetic-capacity hypothesis: explicitly hedged, "
    "judgment deferred, similarity not identity. No structure, product-identity, expression, "
    "production, or bioactivity claim is made. A reference-dark guess is a novelty PRIOR, not proof "
    "of a new compound. Wet-lab evidence is required for any activity or structure statement."
)
CLAIM_SAFETY_LINES = (
    "A Good Guess is a class-level capacity hypothesis synthesized from already-scored evidence "
    "channels — NOT a score, a structure call, or a bioactivity claim.",
    "The confidence band rates how coherent the CAPACITY read is (concordance + committed core + "
    "specificity), never how likely a compound is real or active.",
    "Reference-dark guesses are novelty PRIORS, not proof of a new compound. Similarity is "
    "pathway-family relatedness, not exact product identity.",
    "Judgment is deferred: the resolving experiment names the wet-lab evidence required before any "
    "activity or structure statement.",
)
CLAIM_SAFETY = " ".join(CLAIM_SAFETY_LINES)
# Short line stamped on every PDF page (fits the renderer footer at Helvetica 8).
PAGE_FOOTER = ("Good Guesses \u00b7 class-level capacity hypotheses \u00b7 judgment deferred \u00b7 "
               "similarity not identity \u00b7 not a structure/activity claim")

# --------------------------------------------------------------------------- vocab
CONFIDENCE = ("HIGH", "MEDIUM", "FRONTIER", "LOW")
FLAVOURS = ("SOLID", "REMARKABLE", "RARE", "NOTABLE", "INTERESTING")
# flavour ordering weight (lower sorts earlier when striking-scores tie)
_FLAVOUR_RANK = {f: i for i, f in enumerate(FLAVOURS)}

# CCTT / product tokens that mark rare chemistry (source-derived scan triggers + warheads).
_RARE_TOKENS = {
    "enediyne": "enediyne warhead",
    "ene_": "enediyne warhead",
    "-ene": "enediyne warhead",
    "phosphonate": "phosphonate (C\u2013P bond)",
    "pho_": "phosphonate (C\u2013P bond)",
    "thioamide": "thioamide",
    "tha_": "thioamide",
    "halogenase": "halogenase",
    "hal_": "halogenase",
    "ptm": "PoTeM / HSAF tetramate",
    "tetramate": "PoTeM / HSAF tetramate",
    "nucleoside": "nucleoside",
    "\u03b2-lactam": "\u03b2-lactam",
    "beta-lactam": "\u03b2-lactam",
}


@dataclass
class GoodGuess:
    strain: str
    bgc_id: str
    products: str
    arch_capacity: str
    lead_tier: str
    ab: float
    af: float
    novelty: float
    kcb: str
    concordance: str
    convergence_tier: str
    interpretation_class: str
    recog_fraction: float | None
    dominance_status: str
    misanchor: str
    standing_rule: str
    rggmci: str
    cctt: str
    primary_metab: str
    rggmci_high: bool = False   # a HIGH_RG_GMCI_RESCUE ranked pair involves this BGC
    # --- synthesized ---
    read: str = ""
    confidence: str = ""
    evidence_basis: str = ""
    resolving_experiment: str = ""
    flavours: list = field(default_factory=list)
    striking: float = 0.0
    dominant_mibig: str = ""  # profile anchor; appended to preserve positional callers
    exact_locus: str = ""  # canonical display from the triage-board authority


# --------------------------------------------------------------------------- readers
def _to_float(v) -> float:
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return 0.0


_KCB_NULLS = {"", "unresolved", "none", "n/a", "na", "-", "no hit", "no_hit", "no_hits"}


def _clean_kcb(v: str) -> str:
    v = (v or "").strip()
    return "" if v.lower() in _KCB_NULLS else v


def _load_csv(pkg: Path, pattern: str, *, unique: bool = False,
              required_columns: tuple[str, ...] = ()) -> list[dict]:
    """Read optional evidence or explicitly required, structurally valid CSV input."""
    try:
        files = list(pkg.glob(pattern))
        if not files or (unique and len(files) != 1):
            if required_columns:
                raise ValueError("missing or ambiguous required table")
            return []
        with files[0].open(newline="", encoding="utf-8",
                           errors="strict" if unique else "replace") as fh:
            reader = csv.DictReader(fh, strict=unique)
            headers = reader.fieldnames or []
            if required_columns and not set(required_columns).issubset(headers):
                raise ValueError("required columns are missing")
            if unique and len(headers) != len(set(headers)):
                raise ValueError("duplicate CSV columns")
            rows = list(reader)
            if unique and any(None in row or None in row.values() for row in rows):
                raise ValueError("CSV row width does not match header")
            return rows
    except Exception as exc:
        if required_columns:
            raise ValueError(f"REQUIRED_CSV_INVALID: {pattern}: {exc}") from exc
        return []


def _strain_of(pkg: Path) -> str:
    mani = pkg / "manifest.json"
    if not mani.is_file():
        raise ExactLocusIdentityError(f"MANIFEST_STRAIN_REQUIRED: missing {mani}")
    try:
        manifest = json.loads(mani.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ExactLocusIdentityError(f"MANIFEST_STRAIN_REQUIRED: unreadable {mani}") from exc
    if not isinstance(manifest, dict):
        raise ExactLocusIdentityError(f"MANIFEST_STRAIN_REQUIRED: object required in {mani}")
    strain = read_manifest_field(F_STRAIN_ID, manifest=manifest, default="")
    if not isinstance(strain, str) or not strain.strip():
        raise ExactLocusIdentityError(f"MANIFEST_STRAIN_REQUIRED: non-empty strain_id required in {mani}")
    return strain.strip()


_SOURCE_IDENTITY_FIELDS = (
    "strain", "strain_id", "Strain", "Strain_ID",
    "Full_Node_ID", "full_node_or_contig", "full_node", "Node_ID", "node_id", "node", "Contig", "contig",
    "antiSMASH_Region", "region", "Region",
)


def _board_identity(package_strain: str, row: dict) -> str | NativeManifestBGCIdentity:
    """Bind a reportable board row without conflating native display and join roles."""
    if "Node_ID" in row or "node_id" in row:
        return exact_locus_from_native_inventory_row(package_strain, row)
    return exact_locus_from_mapping(package_strain, row)


def _cross_bind_source_row(
    source: str,
    package_strain: str,
    row: dict,
    expected: str | NativeManifestBGCIdentity,
) -> None:
    """Reject a supplied profile/convergence locus that disagrees with its board locus.

    Older producer tables can supply only ``bgc_id``.  They remain alias-addressed
    until upgraded.  If any additional identity field is present, it is treated as
    an asserted identity and must be complete and equal to the authoritative board
    identity; no filename or shortened-node repair is attempted.
    """
    if not any(field in row for field in _SOURCE_IDENTITY_FIELDS):
        return
    if isinstance(expected, NativeManifestBGCIdentity):
        richer = {
            "strain_id", "Strain", "Strain_ID", "Full_Node_ID", "full_node_or_contig", "full_node",
            "Node_ID", "node_id", "node", "Contig", "antiSMASH_Region", "antismash_region",
            "Region", "BGC_ID", "bgc_alias", "BGC_alias",
        }
        if any(field in row for field in richer):
            if "Node_ID" in row:
                actual = exact_locus_from_native_inventory_row(package_strain, row).exact_locus
            else:
                actual = exact_locus_from_mapping(package_strain, row)
            if actual != expected.exact_locus:
                raise ExactLocusIdentityError(
                    f"{source} locus {actual!r} conflicts with triage-board locus {expected.exact_locus!r}"
                )
            return
        validate_native_legacy_evidence_anchor(package_strain, row, expected)
        return
    actual = exact_locus_from_mapping(package_strain, row)
    if actual != expected:
        raise ExactLocusIdentityError(
            f"{source} locus {actual!r} conflicts with triage-board locus {expected!r}"
        )


def _display_locus(g: GoodGuess) -> str:
    """Validate a stored canonical display before exposing any report surface."""
    parts = g.exact_locus.split(" / ")
    if len(parts) != 4:
        raise ExactLocusIdentityError("missing complete exact-locus display for Good Guess")
    display = exact_locus_display(*parts)
    if display != g.exact_locus or parts[0] != g.strain or parts[3] != g.bgc_id:
        raise ExactLocusIdentityError("Good Guess exact-locus display conflicts with its row identity")
    return display


def _json_row(g: GoodGuess) -> dict:
    row = dict(g.__dict__)
    row["exact_locus"] = _display_locus(g)
    return row


# --------------------------------------------------------------------------- synthesis
_NOTABLE_TIERS = {"exceptional", "high"}


def _is_notable(tier: str) -> bool:
    return (tier or "").strip().lower() in _NOTABLE_TIERS


# v9.7.371 fix: the interpretation_class vocabulary mibig_per_gene.py actually emits is
# {NO_MIBIG_PROTEIN_HITS, UNASSESSED_NO_QUERY_DENOMINATOR, KNOWN_ANCHORED,
# INTERPRETABLE_DARK_MATTER, PARTIAL_DARK_MATTER, TRUE_DARK_MATTER} -- "REFERENCE_SPARSE" and
# "REFERENCE_DARK" never occur in that column (apparent drift from an older/renamed tier
# vocabulary), so those two checks were dead code and only the "NO_MIBIG" substring ever fired.
# A BGC classed TRUE_DARK_MATTER or PARTIAL_DARK_MATTER (a real, common shape: some recognizable
# genes but well below the committed-core floor, no strong anchor) fell through both the ic check
# AND the recog_fraction<=0.001 fallback whenever its fraction was above 0.001 -- silently reading
# as NOT reference-dark and losing the REMARKABLE flavour / FRONTIER confidence framing this
# report exists to surface for exactly that case.
_REFERENCE_DARK_CLASSES = {"NO_MIBIG_PROTEIN_HITS", "TRUE_DARK_MATTER", "PARTIAL_DARK_MATTER"}


def _reference_dark(g: GoodGuess) -> bool:
    if g.recog_fraction is None:
        return False
    # Reuse the reference-dark owner's accession predicate; an anchored family
    # must not be described as having no characterized reference.
    if _has_mibig(g.kcb) or _has_mibig(g.dominant_mibig):
        return False
    ic = (g.interpretation_class or "").upper()
    if ic in _REFERENCE_DARK_CLASSES:
        return True
    return g.recog_fraction <= 0.001 and not g.kcb


def _committed_core(g: GoodGuess) -> bool:
    """A committed core is present when a meaningful fraction of genes are recognizable
    (family-anchored) — the proxy for 'the pathway's committed machinery is captured'."""
    return g.recog_fraction is not None and g.recog_fraction >= 0.35


def _specific(g: GoodGuess) -> bool:
    return (g.dominance_status or "").upper() in {"CLEAR_DOMINANT", "UNIQUE_DOMINANT"}


def _rare_hits(g: GoodGuess) -> list[str]:
    hay = f"{g.cctt} {g.products} {g.arch_capacity}".lower()
    hits = []
    for tok, label in _RARE_TOKENS.items():
        if tok in hay and label not in hits:
            hits.append(label)
    return hits


def _confidence(g: GoodGuess) -> tuple[str, str]:
    """Derive the confidence band from CONCORDANCE + committed core + specificity.
    Returns (band, one-line justification)."""
    if g.recog_fraction is None:
        return "LOW", "per-gene reference evidence NOT_MEASURED; restore the profile before interpretation"
    conc = (g.concordance or "").upper()
    ct = (g.convergence_tier or "").upper()
    strong_support = ct.startswith(("H3", "H4"))
    if _reference_dark(g):
        return "FRONTIER", ("reference-dark (no MIBiG family anchor / no committed recognizable "
                            "core) — a novelty prior, not a family call")
    if conc == "CONCORDANT" and strong_support and _committed_core(g):
        spec = " with specific dominant comparator" if _specific(g) else ""
        return "HIGH", (f"concordant convergence ({g.convergence_tier}) + committed core "
                        f"(recognizable-gene fraction {g.recog_fraction:.0%}){spec}")
    if conc == "CONCORDANT" and strong_support:
        return "MEDIUM", (f"concordant convergence ({g.convergence_tier}) but a thin committed core "
                          f"(recognizable-gene fraction {g.recog_fraction:.0%})")
    if conc == "DISCORDANT":
        return "MEDIUM", ("comparator class disagrees with the antiSMASH label "
                          "(CAUTION_CLASS_MISMATCH) — capacity read hedged to the shared machinery")
    if conc in {"UNRESOLVED", ""} and g.kcb:
        return "MEDIUM", "anchored to a KCB comparator but class concordance is unresolved"
    return "LOW", "weak/absent convergence support"


# resolving-experiment library, keyed by capacity class. First match wins.
def _resolving_experiment(g: GoodGuess) -> str:
    if g.recog_fraction is None:
        return "Restore and validate the per-gene MIBiG profile before selecting a resolving experiment."
    hay = f"{g.cctt} {g.products} {g.arch_capacity}".lower()
    misanchor = bool((g.misanchor or "").strip())
    if misanchor:
        return ("Re-anchor before any bench work: the mis-anchor guard flagged this call as "
                "similarity-only. Re-scan with the corrected anchor / a longer contig; do not "
                "screen against the retracted class.")
    if _reference_dark(g):
        return ("Test whether ANY product is made (novelty prior, not a compound): OSMAC / "
                "promoter-activation or heterologous expression + untargeted LC-MS/MS metabolomics; "
                "confirm the locus is captured (long-read closure if on a contig edge).")
    if "enediyne" in hay or "ene_" in hay or "-ene" in hay:
        return ("Enediyne warhead assay: Fe(II)/reductant-triggered double-strand DNA-cleavage "
                "(plasmid nicking) on crude extract + targeted confirmation of the PKSE/E-subunit "
                "warhead cassette; LC-MS for the chromophore.")
    if "phosphonate" in hay or "pho_" in hay:
        return ("Phosphonate confirmation: \u00b3\u00b9P-NMR of the crude extract for a C\u2013P "
                "signature + targeted PEP-mutase (pepM) expression/amplicon; the PepM Pfam sits in "
                "the ICL superfamily, so treat a lone hit as unconfirmed.")
    if "glycopeptide" in hay or "vancomycin" in hay or "balhi" in g.kcb.lower():
        return ("Antibacterial bioassay-guided fractionation (Gram-positive panel incl. MRSA) + "
                "LC-MS/MS aglycone/glycan profiling to test the glycopeptide capacity.")
    if any(t in hay for t in ("polyene", "candicidin", "hsaf", "ptm", "tetramate")) or g.af >= 60:
        return ("Antifungal bioassay-guided fractionation against Candida spp. + LC-MS/MS "
                "dereplication of the active fraction (strain-level activity \u2192 which locus is "
                "untested until fractionation links them).")
    if "thioamide" in hay or "tha_" in hay:
        return ("Thioamide confirmation: high-res MS for the +S/\u2212O mass shift on candidate "
                "peptides + targeted ycaO/tfuA thioamide-synthase expression.")
    if any(t in hay for t in ("ripp", "lanthipeptide", "lan_", "sactipeptide", "lasso")):
        return ("RiPP maturation check: MALDI-TOF / LC-MS of spent medium for the mature core "
                "mass (\u00b1 dehydration ladder) + targeted precursor-peptide gene; confirms the "
                "class beyond the maturation-enzyme signal.")
    if "metallophore" in hay or "siderophore" in hay or "nrp-metallophore" in hay:
        return ("Metallophore assay: chrome-azurol-S (CAS) plate/liquid assay for iron chelation + "
                "metal-titration LC-MS on the extract.")
    if "halogenase" in hay or "hal_" in hay:
        return ("Halogenation check: isotope-pattern LC-MS (Cl/Br signature) on the extract + "
                "targeted FADH\u2082-halogenase expression.")
    return ("Bioassay-guided fractionation on the target phenotype + LC-MS/MS dereplication; if on "
            "a contig edge, close the locus by long-read re-assembly first.")


def _read_line(g: GoodGuess) -> str:
    """The single best claim-safe capacity read."""
    cls = g.arch_capacity or g.products or "biosynthetic"
    if g.recog_fraction is None:
        return (f"The package reports {cls} class context; per-gene reference evidence is "
                "NOT_MEASURED. Family characterization and reference-dark status are unresolved.")
    if _reference_dark(g):
        return (f"Biosynthetic capacity for a {cls} product with NO characterized MIBiG family "
                f"anchor \u2014 a reference-dark novelty prior (AB {g.ab:.0f} / AF {g.af:.0f} / "
                f"novelty {g.novelty:.0f}), not proof of a new compound.")
    fam = f" resembling the {g.kcb} family" if g.kcb else ""
    conc = (g.concordance or "").upper()
    if conc == "CONCORDANT":
        return (f"Biosynthetic capacity consistent with a {cls} pathway{fam}; multi-gene "
                f"convergence is CONCORDANT with the antiSMASH class \u2014 a class-family read, "
                f"not a product-identity call.")
    if conc == "DISCORDANT":
        return (f"Biosynthetic capacity for a {cls} architecture, but the nearest MIBiG comparator "
                f"is a DIFFERENT class{fam}: read as shared machinery / possible hybrid, class held "
                f"open.")
    return (f"Biosynthetic capacity consistent with a {cls} pathway{fam}; class concordance "
            f"unresolved \u2014 a hedged class-level read.")


def _flavours_and_score(g: GoodGuess) -> tuple[list[str], float]:
    flavours: list[str] = []
    score = 0.0
    conc = (g.concordance or "").upper()
    ct = (g.convergence_tier or "").upper()
    strong = ct.startswith(("H3", "H4"))
    refdark = _reference_dark(g)
    rare = _rare_hits(g)
    multiclass = "multi-class hybrid" in (g.arch_capacity or "").lower()

    # SOLID — concordant + committed core (+ specific)
    if conc == "CONCORDANT" and strong and _committed_core(g):
        flavours.append("SOLID")
        score += 60 + (10 if _specific(g) else 0) + g.recog_fraction * 20

    # REMARKABLE — reference-dark high-capacity novelty, committed multi-class hybrid, RG-GMCI rescue
    if refdark and max(g.ab, g.af) >= 60:
        flavours.append("REMARKABLE")
        score += 45 + max(g.ab, g.af) * 0.15
    if multiclass and conc == "CONCORDANT" and "REMARKABLE" not in flavours:
        flavours.append("REMARKABLE")
        score += 30
    # RG-GMCI: only a genuine HIGH-confidence split-pathway RESCUE is remarkable, not mere
    # candidate-pair count (moderate/low pairs are noise for this purpose).
    if g.rggmci_high and "REMARKABLE" not in flavours:
        flavours.append("REMARKABLE")
        score += 24

    # RARE — rare chemistry triggers / warheads / uncommon classes
    if rare:
        flavours.append("RARE")
        score += 35 + 5 * len(rare)

    # NOTABLE — engine self-correction / mis-anchor caught / capacity outlier
    if (g.misanchor or "").strip():
        flavours.append("NOTABLE")
        score += 28
    if (g.standing_rule or "").strip():
        if "NOTABLE" not in flavours:
            flavours.append("NOTABLE")
        score += 20
    if g.af >= 80 or g.ab >= 90:
        if "NOTABLE" not in flavours:
            flavours.append("NOTABLE")
        score += 22

    # exceptional lead tier is intrinsically striking
    if (g.lead_tier or "").strip().lower() == "exceptional":
        score += 25

    # INTERESTING — lower-confidence second-look (nothing stronger fired)
    if not flavours:
        flavours.append("INTERESTING")
        score += 10 + max(g.ab, g.af) * 0.05

    # magnitude nudge so ties break by capacity
    score += (g.ab + g.af) * 0.03
    return flavours, score


def _synthesize(g: GoodGuess) -> GoodGuess:
    g.read = _read_line(g)
    g.confidence, just = _confidence(g)
    g.resolving_experiment = _resolving_experiment(g)
    g.flavours, g.striking = _flavours_and_score(g)
    # evidence basis: the channels the read rests on
    bits = [f"tier={g.lead_tier}", f"AB/AF/nov={g.ab:.0f}/{g.af:.0f}/{g.novelty:.0f}"]
    if g.concordance:
        bits.append(f"concordance={g.concordance}")
    if g.convergence_tier:
        bits.append(f"conv={g.convergence_tier}")
    bits.append("recog-genes=NOT_MEASURED" if g.recog_fraction is None
                else f"recog-genes={g.recog_fraction:.0%}")
    if g.kcb:
        bits.append(f"KCB={g.kcb}")
    if g.cctt:
        bits.append(f"CCTT={g.cctt}")
    if (g.misanchor or "").strip():
        bits.append("mis-anchor guard fired")
    if (g.standing_rule or "").strip():
        bits.append(f"standing-rule={g.standing_rule}")
    rg = [p for p in (g.rggmci or "").split(";") if p.strip()]
    if g.rggmci_high:
        bits.append("RG-GMCI HIGH split-pathway rescue")
    elif rg:
        bits.append(f"RG-GMCI candidate pairs={len(rg)}")
    bits.append(f"[{just}]")
    g.evidence_basis = "; ".join(bits)
    return g


def _dominant_convergence_rows(pkg: Path, package_strain: str,
                               board_loci: dict[str, str | NativeManifestBGCIdentity]) -> dict[str, dict]:
    """Read the producer's dominant comparator, retaining first-row legacy fallback.

    mibig_per_gene.build_mibig_convergence marks rank 1 as dominant. A table has
    multiple references per locus, so a last-row-wins map selects a runner-up.
    Older tables may carry only the rank or neither selection column.
    """
    def is_dominant(row: dict) -> bool:
        return (str(row.get("dominant_reference", "")).strip().lower() == "true"
                or str(row.get("convergence_rank", "")).strip() == "1")

    selected: dict[str, dict] = {}
    for row in _load_csv(pkg, "*_3_mibig_convergence.csv"):
        bid = (row.get("bgc_id") or "").strip()
        if bid in board_loci:
            _cross_bind_source_row("convergence", package_strain, row, board_loci[bid])
        current = selected.get(bid)
        if current is None or (is_dominant(row) and not is_dominant(current)):
            selected[bid] = row
    return selected


def _profile_fraction(row: dict) -> float | None:
    """A missing, malformed or out-of-range measurement is not a measured zero."""
    if row.get("interpretation_class") == "UNASSESSED_NO_QUERY_DENOMINATOR":
        return None
    try:
        if row.get("query_gene_count") not in (None, ""):
            denominator = float(row["query_gene_count"])
            if not math.isfinite(denominator) or denominator <= 0 or not denominator.is_integer():
                return None
        value = float(row.get("recognizable_gene_fraction", ""))
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) and 0 <= value <= 1 else None


def _unique_profile_rows(pkg: Path) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    duplicates: set[str] = set()
    for row in _load_csv(pkg, "*_3_mibig_profile.csv", unique=True):
        bid = row.get("bgc_id", "")
        if bid in rows:
            duplicates.add(bid)
        rows[bid] = row
    for bid in duplicates:
        rows.pop(bid)
    return rows


# --------------------------------------------------------------------------- package scan
def _scan_package(pkg: Path) -> list[GoodGuess]:
    board = _load_csv(pkg, "*_4_triage_board.csv", unique=True,
                      required_columns=("BGC_ID", "Lead_tier_auto"))
    strain = _strain_of(pkg)
    if not board:
        return []
    notable_board = [r for r in board if _is_notable(r.get("Lead_tier_auto", ""))]
    board_loci: dict[str, str | NativeManifestBGCIdentity] = {}
    physical_loci: set[tuple[str, str, str]] = set()
    for row_number, row in enumerate(notable_board, start=2):
        bid = (row.get("BGC_ID") or "").strip()
        identity = _board_identity(strain, row)
        if bid in board_loci:
            raise ExactLocusIdentityError(
                f"triage board repeats an alias before evidence association at row {row_number}"
            )
        if isinstance(identity, NativeManifestBGCIdentity):
            physical = (identity.strain, identity.full_contig, identity.region)
        else:
            parts = identity.split(" / ")
            if len(parts) != 4:
                raise ExactLocusIdentityError("triage board generic identity is not complete")
            physical = (parts[0], parts[1], parts[2])
        if physical in physical_loci:
            raise ExactLocusIdentityError("triage board repeats physical locus before evidence association")
        physical_loci.add(physical)
        board_loci[bid] = identity
    conv = _dominant_convergence_rows(pkg, strain, board_loci)
    prof = _unique_profile_rows(pkg)
    # BGCs implicated in a genuine HIGH-confidence RG-GMCI split-pathway rescue pair.
    rg_high: set[str] = set()
    for pr in _load_csv(pkg, "*_4A_RGGMCI_ranked_pairs.csv"):
        if "HIGH" in (pr.get("rggmci_confidence") or "").upper():
            for k in ("bgc_a", "bgc_b"):
                v = (pr.get(k) or "").strip()
                if v:
                    rg_high.add(v)
    out: list[GoodGuess] = []
    for r in notable_board:
        bid = (r.get("BGC_ID") or "").strip()
        c = conv.get(bid, {})
        p = prof.get(bid, {})
        identity = board_loci[bid]
        exact = identity.exact_locus if isinstance(identity, NativeManifestBGCIdentity) else identity
        if p:
            _cross_bind_source_row("profile", strain, p, identity)
        g = GoodGuess(
            strain=strain,
            bgc_id=bid,
            products=(r.get("Products") or "").strip(),
            arch_capacity=(r.get("Arch_Capacity") or "").strip(),
            lead_tier=(r.get("Lead_tier_auto") or "").strip(),
            ab=_to_float(r.get("AB_auto")),
            af=_to_float(r.get("AF_auto")),
            novelty=_to_float(r.get("Novelty_auto")),
            kcb=_clean_kcb(r.get("KCB_top", "")),
            # concordance: triage board column is often empty; convergence CSV is authoritative.
            concordance=((r.get("Concordance") or "").strip()
                         or (c.get("class_concordance") or "").strip()),
            convergence_tier=(c.get("convergence_tier") or "").strip(),
            interpretation_class=(p.get("interpretation_class") or "").strip(),
            dominant_mibig=(p.get("dominant_mibig_accession") or "").strip(),
            recog_fraction=_profile_fraction(p),
            dominance_status=(c.get("dominance_status") or "").strip(),
            misanchor=(r.get("Misanchor_Flag") or "").strip(),
            standing_rule=(r.get("Standing_rule") or "").strip(),
            rggmci=(r.get("RGGMCI_support") or "").strip(),
            cctt=(r.get("CCTT_triggers") or "").strip(),
            primary_metab=(r.get("Primary_metab_flag") or "").strip(),
            rggmci_high=bid in rg_high,
            exact_locus=exact,
        )
        out.append(_synthesize(g))
    return out


def _find_packages(root: Path, depth: int) -> list[Path]:
    root = Path(root)
    if (root / "manifest.json").is_file():
        return [root]
    # An explicit package-like root without its manifest must fail through the
    # governed manifest path rather than become a silent empty report.
    if root.is_dir() and any(root.glob("*_4_triage_board.csv")):
        return [root]
    out = []
    for f in root.rglob("manifest.json"):
        rel = len(f.relative_to(root).parts)
        if rel <= depth + 1:
            out.append(f.parent)
    return sorted(set(out))


def build_guesses(pkgs: list[Path]) -> list[GoodGuess]:
    rows: list[GoodGuess] = []
    for pkg in pkgs:
        rows.extend(_scan_package(pkg))
    rows.sort(key=lambda g: (-g.striking, _FLAVOUR_RANK.get(g.flavours[0], 9),
                             g.strain, g.bgc_id))
    return rows


# --------------------------------------------------------------------------- markdown
def _flavour_badges(flavours: list[str]) -> str:
    return " ".join(f"**{f}**" for f in flavours)


def _md_escape(s: str) -> str:
    return (s or "").replace("|", "\\|").replace("\n", " ")


def render_markdown(rows: list[GoodGuess]) -> str:
    displays = {id(g): _display_locus(g) for g in rows}
    strains = sorted({g.strain for g in rows})
    L = ["# Good Guesses \u2014 claim-safe interpretive priors", ""]
    L.append("> **Claim ceiling.** " + CLAIM_CEILING)
    L.append("")
    L.append(f"**{len(rows)} Good Guesses across {len(strains)} strain(s)** "
             f"({', '.join(strains)}). Each is the single best claim-safe read of a notable "
             f"(Exceptional/High) lead, tagged by flavour and ordered most-striking first.")
    L.append("")
    # flavour legend
    L.append("### Flavour legend")
    L.append("")
    L.append("- **SOLID** \u2014 concordant MIBiG convergence + committed core machinery + specific comparator.")
    L.append("- **RARE** \u2014 rare chemistry: CCTT warhead/class triggers (enediyne, phosphonate, thioamide, halogenase, PTM tetramate\u2026).")
    L.append("- **REMARKABLE** \u2014 strong reference-dark novelty prior, committed multi-class hybrid, or RG-GMCI split-pathway rescue.")
    L.append("- **NOTABLE** \u2014 the engine self-correcting: a mis-anchor caught, a standing-rule demotion, a capacity outlier.")
    L.append("- **INTERESTING** \u2014 invites a second look but is lower-confidence.")
    L.append("")
    # ranked table
    L.append("## Ranked Good Guesses")
    L.append("")
    L.append("| # | Exact locus | Flavour | The Good Guess (class-level capacity hypothesis) "
             "| Confidence | Evidence basis | Resolving experiment |")
    L.append("|---:|---|---|---|:--:|---|---|")
    for i, g in enumerate(rows, 1):
        L.append("| {n} | {locus} | {fl} | {rd} | {cf} | {ev} | {rx} |".format(
            n=i, locus=_md_escape(displays[id(g)]),
            fl=_flavour_badges(g.flavours), rd=_md_escape(g.read),
            cf=g.confidence, ev=_md_escape(g.evidence_basis),
            rx=_md_escape(g.resolving_experiment)))
    L.append("")
    # per-flavour highlight sections (lead with the most striking in each)
    for fl in FLAVOURS:
        picks = [g for g in rows if fl in g.flavours]
        if not picks:
            continue
        L.append(f"## {fl} \u2014 {len(picks)} guess(es)")
        L.append("")
        for g in picks:
            L.append(f"### {displays[id(g)]}  ({g.confidence})")
            L.append("")
            L.append(f"- **Read:** {g.read}")
            L.append(f"- **Flavours:** {', '.join(g.flavours)}")
            L.append(f"- **Evidence basis:** {g.evidence_basis}")
            L.append(f"- **Resolving experiment:** {g.resolving_experiment}")
            L.append("")
    L.append("---")
    L.append("")
    L.append("### Claim-safety")
    L.append("")
    for ln in CLAIM_SAFETY_LINES:
        L.append(f"- {ln}")
    L.append("")
    L.append("*Good Guesses is report-only and NON-scoring: it reads already-scored package "
             "outputs and changes nothing. Class-level capacity hypotheses; judgment deferred; "
             "no structure/activity claim.*")
    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------- CSV
_CSV_FIELDS = ("exact_locus", "strain", "bgc_id", "flavours", "confidence", "read", "evidence_basis",
               "resolving_experiment", "lead_tier", "ab", "af", "novelty", "concordance",
               "convergence_tier", "interpretation_class", "recognizable_gene_fraction",
               "dominance_status", "kcb", "cctt", "striking")


def _write_csv(rows: list[GoodGuess], path: Path) -> None:
    displays = [(g, _display_locus(g)) for g in rows]
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = SafeDictWriter(fh, fieldnames=list(_CSV_FIELDS))
        w.writeheader()
        for g, exact in displays:
            w.writerow({
                "exact_locus": exact, "strain": g.strain, "bgc_id": g.bgc_id,
                "flavours": "|".join(g.flavours),
                "confidence": g.confidence, "read": g.read, "evidence_basis": g.evidence_basis,
                "resolving_experiment": g.resolving_experiment, "lead_tier": g.lead_tier,
                "ab": g.ab, "af": g.af, "novelty": g.novelty, "concordance": g.concordance,
                "convergence_tier": g.convergence_tier,
                "interpretation_class": g.interpretation_class,
                "recognizable_gene_fraction": g.recog_fraction,
                "dominance_status": g.dominance_status, "kcb": g.kcb, "cctt": g.cctt,
                "striking": round(g.striking, 2),
            })


# --------------------------------------------------------------------------- docx (graceful)
def render_docx(rows: list[GoodGuess], path: Path) -> dict:
    """Emit GOOD_GUESSES.docx. Degrades gracefully (status SKIPPED_NO_DOCX) if python-docx
    is not installed — the .md/.pdf still ship."""
    displays = {id(g): _display_locus(g) for g in rows}
    try:
        from docx import Document
        from docx.shared import Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
    except Exception as e:  # noqa: BLE001
        return {"status": "SKIPPED_NO_DOCX", "path": None, "detail": str(e)}
    try:
        doc = Document()
        h = doc.add_heading("Good Guesses \u2014 claim-safe interpretive priors", level=0)
        p = doc.add_paragraph()
        run = p.add_run("Claim ceiling. " + CLAIM_CEILING)
        run.italic = True
        run.font.size = Pt(9)
        strains = sorted({g.strain for g in rows})
        doc.add_paragraph(
            f"{len(rows)} Good Guesses across {len(strains)} strain(s): {', '.join(strains)}. "
            f"Each is the single best claim-safe read of a notable (Exceptional/High) lead, "
            f"tagged by flavour and ordered most-striking first.")
        doc.add_heading("Ranked Good Guesses", level=1)
        cols = ["#", "Exact locus", "Flavour", "The Good Guess", "Conf.",
                "Evidence basis", "Resolving experiment"]
        table = doc.add_table(rows=1, cols=len(cols))
        try:
            table.style = "Light Grid Accent 1"
        except Exception:
            pass
        for j, c in enumerate(cols):
            cell = table.rows[0].cells[j]
            cell.text = c
            for pr in cell.paragraphs:
                for rn in pr.runs:
                    rn.font.bold = True
                    rn.font.size = Pt(8)
        for i, g in enumerate(rows, 1):
            cells = table.add_row().cells
            vals = [str(i), displays[id(g)], " ".join(g.flavours), g.read,
                    g.confidence, g.evidence_basis, g.resolving_experiment]
            for j, v in enumerate(vals):
                cells[j].text = v
                for pr in cells[j].paragraphs:
                    for rn in pr.runs:
                        rn.font.size = Pt(7.5)
        # per-flavour sections
        for fl in FLAVOURS:
            picks = [g for g in rows if fl in g.flavours]
            if not picks:
                continue
            doc.add_heading(f"{fl} \u2014 {len(picks)} guess(es)", level=1)
            for g in picks:
                doc.add_heading(f"{displays[id(g)]}  ({g.confidence})", level=2)
                for label, val in (("Read", g.read), ("Flavours", ", ".join(g.flavours)),
                                   ("Evidence basis", g.evidence_basis),
                                   ("Resolving experiment", g.resolving_experiment)):
                    para = doc.add_paragraph(style="List Bullet")
                    r1 = para.add_run(f"{label}: ")
                    r1.bold = True
                    para.add_run(val)
        doc.add_heading("Claim-safety", level=1)
        for ln in CLAIM_SAFETY_LINES:
            para = doc.add_paragraph(ln, style="List Bullet")
            for rn in para.runs:
                rn.font.size = Pt(9)
        foot = doc.add_paragraph()
        fr = foot.add_run(PAGE_FOOTER)
        fr.italic = True
        fr.font.size = Pt(8)
        fr.font.color.rgb = RGBColor(0x55, 0x55, 0x66)
        foot.alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.save(str(path))
        return {"status": "WRITTEN", "path": str(path)}
    except Exception as e:  # noqa: BLE001
        return {"status": "ERROR", "path": None, "detail": str(e)}


# --------------------------------------------------------------------------- pdf (reuse renderer)
def render_pdf(md_path: Path, pdf_path: Path, pkg_hint: Path | None = None) -> dict:
    """Render GOOD_GUESSES.pdf by REUSING the sanctioned colorful reportlab renderer
    (tools/render_deliverable_pdf.py, the same primary path compile_report._render_compiled_pdf
    drives via md_to_pdf.sh). We call it in-process so it uses THIS interpreter's reportlab
    (Tools/bin/python3), and monkeypatch its footer to the per-page claim-safety line. Falls back
    to compile_report._render_compiled_pdf (pandoc/xelatex) if reportlab is unavailable."""
    import importlib.util
    tools_renderer = (Path(__file__).resolve().parents[1] / "tools" / "render_deliverable_pdf.py")
    if tools_renderer.exists():
        try:
            spec = importlib.util.spec_from_file_location("_gg_render_pdf", str(tools_renderer))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            # per-page claim-safety footer, reusing the renderer's own footer hook
            mod._footer_line = lambda: PAGE_FOOTER  # type: ignore[attr-defined]
            mod.render(str(md_path), str(pdf_path),
                       title="Good Guesses \u2014 claim-safe interpretive priors",
                       subtitle="Class-level capacity hypotheses \u00b7 judgment deferred")
            if pdf_path.exists() and pdf_path.stat().st_size > 0:
                return {"status": "WRITTEN", "path": str(pdf_path),
                        "engine": "render_deliverable_pdf (reportlab, in-process)"}
        except Exception as e:  # noqa: BLE001
            last = str(e)
        else:
            last = "renderer produced no file"
    else:
        last = "tools/render_deliverable_pdf.py absent"
    # fallback: the compile_report sanctioned path (pandoc/xelatex)
    try:
        from . import compile_report as _cr
        md = md_path.read_text(encoding="utf-8")
        res = _cr._render_compiled_pdf(md, pdf_path, pkg_hint or md_path.parent)
        if res.get("status") == "WRITTEN":
            return res
        return {"status": res.get("status", "RENDER_FAILED"),
                "path": None, "detail": f"reportlab: {last}; fallback: {res.get('detail', '')}"}
    except Exception as e:  # noqa: BLE001
        return {"status": "RENDER_FAILED", "path": None,
                "detail": f"reportlab: {last}; fallback import failed: {e}"}


# --------------------------------------------------------------------------- run / CLI
def run(root: str | Path = ".", out_dir: str | Path | None = None, depth: int = 3,
        pdf: bool = False, docx: bool = False) -> dict:
    root = Path(root)
    pkgs = _find_packages(root, depth)
    rows = build_guesses(pkgs)
    md = render_markdown(rows)
    strains = sorted({g.strain for g in rows})
    flavour_counts = {fl: sum(1 for g in rows if fl in g.flavours) for fl in FLAVOURS}
    result = {
        "packages": len(pkgs),
        "guesses": len(rows),
        "strains": strains,
        "flavour_counts": flavour_counts,
        "markdown": md,
        "rows": [_json_row(g) for g in rows],
        "claim_ceiling": CLAIM_CEILING,
        "claim_safety": CLAIM_SAFETY,
    }
    if out_dir:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        md_path = out / "GOOD_GUESSES.md"
        csv_path = out / "GOOD_GUESSES.csv"
        md_path.write_text(md, encoding="utf-8")
        _write_csv(rows, csv_path)
        result["md_path"] = str(md_path)
        result["csv_path"] = str(csv_path)
        result["out_dir"] = str(out)
        if docx:
            result["docx"] = render_docx(rows, out / "GOOD_GUESSES.docx")
        if pdf:
            result["pdf"] = render_pdf(md_path, out / "GOOD_GUESSES.pdf",
                                       pkg_hint=(pkgs[0] if pkgs else None))
    return result


def good_guesses_command(args) -> int:
    res = run(getattr(args, "root", ".") or ".",
              out_dir=getattr(args, "out", None),
              depth=getattr(args, "depth", 3),
              pdf=getattr(args, "pdf", False),
              docx=getattr(args, "docx", False))
    if res.get("out_dir"):
        fc = res["flavour_counts"]
        emit(f"good-guesses: {res['packages']} package(s) -> {res['guesses']} guess(es) "
              f"across {len(res['strains'])} strain(s) "
              f"[{', '.join(f'{k}={v}' for k, v in fc.items() if v)}] -> {res['out_dir']}")
        for key in ("docx", "pdf"):
            if key in res:
                st = res[key]
                emit(f"  {key}: {st.get('status')}"
                      + (f" -> {st.get('path')}" if st.get("path") else
                         f" ({st.get('detail', '')})"))
    else:
        emit(res["markdown"])
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Good Guesses \u2014 claim-safe interpretive-priors report (report-only, non-scoring)")
    ap.add_argument("root", nargs="?", default=".",
                    help="workspace / runs / package dir to scan (default: current dir)")
    ap.add_argument("--out", metavar="DIR", help="write GOOD_GUESSES.md/.csv/.docx/.pdf here")
    ap.add_argument("--depth", type=int, default=3, help="max recursion depth (default 3)")
    ap.add_argument("--pdf", action="store_true", help="also render GOOD_GUESSES.pdf")
    ap.add_argument("--docx", action="store_true", help="also render GOOD_GUESSES.docx")
    return good_guesses_command(ap.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
