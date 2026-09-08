"""mode_b_quality_gate.py — structural depth enforcement for Mode B cards.

THE PROBLEM
-----------
The judgment layer can produce Mode B cards at vastly different depths.  A real
§1/§3/§5–§8 gene-grounded analysis runs 4,000–8,000 characters and names specific
genes, domains, and loci.  A template-fill summary runs 300–900 characters and
could be produced by string substitution.  Both pass through ``ingest-receipts``
identically — the pipeline cannot tell them apart.

THE FIX
-------
This module defines measurable depth criteria and returns a per-card quality
verdict: FULL, SHALLOW, or STUB.  The depth floor depends on the BGC's priority
tier (from the triage board rank):

  HIGH priority (top 10 by rank):  ≥12,000 chars for FULL
  MID  priority (ranks 11–25):     ≥11,000 chars for FULL
  LOW  priority (ranks 26+):       ≥10,000 chars for FULL

A card below its tier's floor but above 2,000 chars is SHALLOW (needs deepening).
A card below 2,000 chars is a STUB.

The gate does NOT block ingest — it records the quality tier alongside the card
so the gap is visible, not silent.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Thresholds (raised 2026-06-22, calibrated against real Mode B targets)
#
# Target depth by priority tier:
#   HIGH-priority BGCs (top 10):  12,000+ chars
#   MID-priority BGCs (11–25):    11,000+ chars
#   LOW-priority BGCs (26+):      10,000 chars  (v9.7.205: was 6,000; compressed to match FLOORS)
#   Single-gene FC fragments:     2,000–3,000 chars (genuine minimum)
# ---------------------------------------------------------------------------

# Per-card floors (v9.7.205): RAISED for the §1–§30 contract and re-centered on domain-level substance.
# A full Mode B card is now expected to be HEAVY on aSDomain-level detail (antiSMASH aSDomains + per-gene
# BLASTp where available), not prose. Calibration anchor: the real verified §30 card AS-XXX BGC007 is
# 36,623 chars / 61 domain·BLASTp mentions (density 1.7/1k). The old 9k/8k/6k floors were set for the
# retired §1–§10+§11–§20 (20-section) contract and are a fraction of a real §30 card.
#
# TIERS ARE COMPRESSED on purpose: the HIGH/MID/LOW rank spread previously dropped an important-but-
# fragmented BGC (low rank because it sits on a short/edge contig, NOT because it's less interesting) to
# a much lower floor. Compressing the spread (12k/11k/10k) keeps every non-fragment card held to a
# substantive bar regardless of rank. (A genuine boundary fragment still gets the FRAGMENT_FLOOR exemption
# below — that's assembly reality, not a downgrade of interest.)
#
# ⚠ PROVISIONAL CALIBRATION: these numbers are anchored on n=1 real §30 card + the Developer or User's directive. The
# per-BGC-class exemplar cards (1 good card per class, to be added under docs/reference/modeb_exemplars/)
# are the real calibration set — expect to revisit whether small classes (RiPP/terpene) need a
# class-specific floor once those land. Raising the floor makes MULTIPLE AUTHORING ROUNDS/BATCHES the
# norm: a domain-heavy card rarely completes in one pass — gather more BLASTp/aSDomain evidence rather
# than pad. NO PADDING: length must be backed by domain content (enforced by MIN_DOMAIN_DENSITY below).
FLOORS = {
    "HIGH": 12_000,
    "MID":  11_000,
    "LOW":  10_000,
}
FLOOR_STUB = 2_000             # below this = STUB regardless of tier (fragments exempt here)

MIN_GENE_MENTIONS = 12         # absolute floor of gene/domain-specific tokens for FULL (raised from 5)
# Anti-padding: domain·BLASTp mentions must SCALE with length, or a long card is prose padding, not a
# domain-heavy analysis. Require >= MIN_DOMAIN_DENSITY mentions per 1,000 chars. Conservative: the real
# AS-XXX BGC007 card is 1.7/1k, so a 1.0/1k floor passes genuine work and rejects padded length.
MIN_DOMAIN_DENSITY = 1.0       # gene/domain mentions per 1,000 chars (provisional; recalibrate vs exemplars)
MIN_SECTIONS = 4               # deep §1–§10 cards carry well over 4 markers; fragments exempt below STUB

# Sections that a full Mode B card must specifically contain (v9.7.112). §9 and §10 are the two that
# the judgment layer historically omitted; the gate now checks for their presence by number, so a card
# can no longer reach FULL by padding §1–§8 while skipping the activation/forensic analysis.
REQUIRED_SECTION_NUMBERS = (9, 10)

# Mandatory §11–§20 enrichment block (v9.7.112; floor raised v9.7.125 from 1,000 → 2,000).
# Each of §11–§20 is individually optional, but every card must carry >= MIN_ENRICHMENT_CHARS of
# combined §11–§20 content. Calibrated 2026-06-25 against a real authored AS-XXX batch (13 cards,
# all genuinely good non-padded §11–§20 sections): observed enrichment 2,045–7,297 chars (mean
# 3,809). The thinnest honest card was 2,045, so a 2,000 floor rejects thin enrichment without
# punishing real work; 2,500+ would reject honest cards (the padding-pressure line). The
# deterministic generators in mamey.enrichment_sections clear this floor from gene-table data.
MIN_ENRICHMENT_CHARS = 2_000

# Fragment-floor exemption (v9.7.114). A genuine boundary fragment (Edge or Full-contig) with very
# few CDS cannot honestly meet the flat 9k/8k/6k char floor — you can't write 9,000 chars about 3
# genes without padding, and compile_ready() would block the master PDF forever on such a card.
# So a boundary fragment below the CDS threshold gets a reduced char floor (it still owes §1–§10 and
# enrichment, just not the full-cluster char count).
#
# CRITICAL (per analysis-chat refinement): the exemption keys on edge_status AND cds — NOT cds alone.
# A 9-CDS *Interior* cluster is an intact small cluster, not a fragment; it still owes full depth.
# Only Edge / Full-contig clusters at/under the CDS threshold are relieved. Conservative by design:
# if edge_status is unknown/missing, NO exemption is granted (the cluster owes full depth).
FRAGMENT_CDS_MAX = 22          # boundary clusters with <= this many CDS may use the fragment floor
FRAGMENT_FLOOR = 2_500         # the reduced char floor for an exempt boundary fragment
_FRAGMENT_EDGE_STATUSES = {"edge", "full-contig", "full_contig", "fullcontig"}

# ---------------------------------------------------------------------------
# Priority tier assignment from triage board rank
# ---------------------------------------------------------------------------

def priority_tier(rank: int | None) -> str:
    """Map a triage board rank (1-based) to a priority tier."""
    if rank is None:
        return "LOW"           # unknown rank → apply the most lenient floor
    if rank <= 10:
        return "HIGH"
    if rank <= 25:
        return "MID"
    return "LOW"

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

# Locus tag patterns: XF36_04210, ctg1_00050, SSHG_01234, etc.
# Locus-tag patterns. Two real antiSMASH forms:
#   ctgN_M           — contig loci, ANY suffix width incl. single digit (ctg57_1, ctg6_186),
#                      optionally carrying a RiPP-precursor class suffix that antiSMASH appends to
#                      precursor genes (ctg42_21_lanthipeptide, ctg8_3_thioamitide).
#   PREFIX_NNNNN     — legacy long-suffix loci (XF36_04210, SSHG_01234).
# The RiPP suffix is matched STRUCTURALLY (_<lowercase word>), not against a hardcoded class list:
# antiSMASH 8 emits RiPP families beyond the original four (ranthipeptide, thioamitide, lipolanthine,
# microviridin, cyanobactin, ...) and a fixed list would silently drop them — the same lesson the
# extraction path already learned (see antismash_evidence.py _ripp_from_rec, v9.7.99, now data-driven).
# Verified safe: across 9,312 full-genome locus tags, antiSMASH emits NO non-RiPP _word suffix on a
# locus_tag, so the lowercase-word suffix cannot over-match a real tag. Validated 100% match / 0 FP
# across 5 genomes / 5 genera (Nocardia, Micromonospora, Streptomyces x2, Saccharopolyspora), 3,916 tags.
_RE_LOCUS = re.compile(
    r'\b(?:'
    r'ctg\d+_\d{1,6}(?:_[a-z][a-z_]*)?'
    r'|[A-Za-z]{2,8}\d*_\d{4,6}'
    r')\b'
)

# Domain/Pfam/TIGRFAM mentions
_RE_DOMAIN = re.compile(
    r'\b(?:'
    r'PF\d{4,5}'
    r'|TIGR\d{4,5}'
    r'|IPR\d{5,7}'
    r'|cd\d{4,5}'
    r'|[A-Z]{2,4}\s+domain'
    r'|condensation'
    r'|adenylation'
    r'|thiolation'
    r'|acyltransferase'
    r'|epimerization'
    r'|ketosynthase'
    r'|ketoreductase'
    r'|dehydratase'
    r'|methyltransferase'
    r'|aminotransferase'
    r'|halogenase'
    r'|epoxidase'
    r'|hydroxylase'
    r'|thioesterase'
    r'|cyclase'
    r'|aromatase'
    r')\b',
    re.IGNORECASE,
)

# Section headers
_RE_SECTION = re.compile(
    r'(?:§(?:10|[1-9])|Identity|Biosynthetic\s+Core|Pharmacology|Verdict|Priority'
    r'|Gene\s+neighborhood|Activation|Forensic)',
    re.IGNORECASE,
)

# Extracts the explicit §-numbers present in a card (10-first so "§10" parses whole, not "§1"+"0").
_RE_SECTION_NUM = re.compile(r'§(10|[1-9])(?!\d)')

def present_section_numbers(text: str) -> set[int]:
    """Return the set of explicit §-section numbers present in the card (1–10)."""
    return {int(m) for m in _RE_SECTION_NUM.findall(text)}


# §11–§20 enrichment block headers (20-first so "§20" parses whole, not "§2"+"0").
_RE_ENRICHMENT_HEAD = re.compile(r'§(?:20|1[1-9])\b')

def _enrichment_chars(text: str) -> tuple[int, int]:
    """Measure the §11–§20 enrichment block: from the first §11–§20 header to end of card.

    Returns (n_enrichment_section_headers, enrichment_char_count). If no §11–§20 header is
    present, the block is empty (0, 0).
    """
    heads = list(_RE_ENRICHMENT_HEAD.finditer(text))
    if not heads:
        return 0, 0
    first = heads[0].start()
    return len(heads), len(text) - first

# Amino acid counts: "NNN aa" or "N,NNN aa"
_RE_AA = re.compile(r'\b\d[\d,]*\s*aa\b')


# ---------------------------------------------------------------------------
# Quality verdict
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ModeB_QualityVerdict:
    """Result of evaluating a single Mode B card's depth."""
    bgc_id: str
    tier: str               # "FULL" | "SHALLOW" | "STUB"
    priority: str           # "HIGH" | "MID" | "LOW"
    char_count: int
    floor: int              # the char floor applied for this BGC's priority
    gene_mentions: int
    section_count: int
    aa_mentions: int
    message: str


def evaluate_card(
    bgc_id: str,
    mode_b_md: str,
    rank: int | None = None,
    edge_status: str | None = None,
    cds_count: int | None = None,
) -> ModeB_QualityVerdict:
    """Evaluate the depth of a single Mode B card.

    Parameters
    ----------
    bgc_id : str
        The BGC identifier.
    mode_b_md : str
        The full Mode B markdown text.
    rank : int or None
        Triage board rank (1-based).  Determines the priority tier and
        therefore the character floor.  None → LOW (most lenient).
    edge_status : str or None
        The BGC's boundary status ("Interior" / "Edge" / "Full-contig"). Used with cds_count
        to grant the fragment-floor exemption. Unknown/None → no exemption (owes full depth).
    cds_count : int or None
        Number of CDS in the cluster. A boundary fragment (Edge/Full-contig) with
        cds_count <= FRAGMENT_CDS_MAX uses the reduced FRAGMENT_FLOOR. An Interior cluster
        of the same size is NOT exempt — an intact small cluster still owes its analysis.

    Returns a ModeB_QualityVerdict with tier FULL / SHALLOW / STUB.
    """
    # #24: arg-order guard. Passing the card text first (a natural mistake) silently returned a garbage
    # STUB. A real bgc_id is short and single-line; card text is long/multiline — reject the swap loudly.
    if "\n" in str(bgc_id) or len(str(bgc_id)) > 100:
        raise ValueError(
            "evaluate_card(bgc_id, mode_b_md, ...): first arg looks like card text, not a bgc_id "
            "(long/multiline). Args appear swapped — pass the BGC id first, the card markdown second.")
    text = mode_b_md.strip()
    n_chars = len(text)
    n_loci = len(_RE_LOCUS.findall(text))
    n_domains = len(_RE_DOMAIN.findall(text))
    n_gene = n_loci + n_domains
    n_sections = len(set(_RE_SECTION.findall(text)))
    n_aa = len(_RE_AA.findall(text))
    present_secs = present_section_numbers(text)
    missing_required = [n for n in REQUIRED_SECTION_NUMBERS if n not in present_secs]
    n_enrich_sec, enrich_chars = _enrichment_chars(text)
    enrichment_ok = enrich_chars >= MIN_ENRICHMENT_CHARS

    pri = priority_tier(rank)
    floor = FLOORS[pri]

    # Fragment-floor exemption (v9.7.114): a boundary fragment (Edge/Full-contig) at or under the CDS
    # threshold gets the reduced FRAGMENT_FLOOR. Keys on edge_status AND cds — an Interior small
    # cluster is NOT a fragment and keeps the full floor. Conservative: missing edge_status or
    # cds_count → no exemption. Never RAISES a floor; only lowers it for a genuine fragment.
    is_boundary = (edge_status or "").strip().lower() in _FRAGMENT_EDGE_STATUSES
    is_fragment = is_boundary and cds_count is not None and cds_count <= FRAGMENT_CDS_MAX
    if is_fragment and FRAGMENT_FLOOR < floor:
        floor = FRAGMENT_FLOOR

    # Anti-padding density: a FULL card's domain·BLASTp mentions must scale with its length (fragments,
    # judged below FLOOR_STUB, are exempt). density_floor is the minimum mentions for THIS card's length.
    density_floor = int((n_chars / 1000.0) * MIN_DOMAIN_DENSITY)
    density_ok = n_gene >= density_floor

    if n_chars < FLOOR_STUB:
        # Genuine single-ORF / full-contig fragments stay here and are NOT held to the §9/§10
        # requirement — a fragment has no neighborhood to do a full forensic sweep on (§10(D)
        # RG-GMCI is its key section, handled in the prose, not gated by length).
        tier = "STUB"
        msg = f"{n_chars:,} chars — stub (< {FLOOR_STUB:,} char floor)"
    elif (n_chars >= floor and n_gene >= MIN_GENE_MENTIONS and density_ok
          and n_sections >= MIN_SECTIONS and not missing_required and enrichment_ok):
        tier = "FULL"
        _floor_label = f"fragment floor ({floor:,})" if is_fragment else f"{pri} floor ({floor:,})"
        msg = (f"{n_chars:,} chars, {n_gene} gene/domain mentions ({n_gene/(n_chars/1000.0):.1f}/1k), "
               f"§1–§48 substance, §11–§20 enrichment {enrich_chars:,}c — meets {_floor_label}")
    else:
        tier = "SHALLOW"
        missing = []
        if n_chars < floor:
            _fl_label = "fragment" if is_fragment else pri
            missing.append(f"chars ({n_chars:,} < {floor:,} {_fl_label} floor)")
        if not density_ok:
            missing.append(f"domain density ({n_gene} mentions < {density_floor} needed for "
                           f"{n_chars:,} chars — looks padded; add aSDomain/BLASTp detail, don't pad prose)")
        if n_gene < MIN_GENE_MENTIONS:
            missing.append(f"gene mentions ({n_gene} < {MIN_GENE_MENTIONS})")
        if n_sections < MIN_SECTIONS:
            missing.append(f"sections ({n_sections} < {MIN_SECTIONS})")
        if missing_required:
            missing.append("missing " + ", ".join(f"§{n}" for n in missing_required))
        if not enrichment_ok:
            missing.append(f"§11–20 enrichment ({enrich_chars:,} < {MIN_ENRICHMENT_CHARS:,} "
                           "required; add an applicable enrichment section)")
        msg = f"{n_chars:,} chars — below {pri} depth floor: {'; '.join(missing)}"

    return ModeB_QualityVerdict(
        bgc_id=bgc_id,
        tier=tier,
        priority=pri,
        char_count=n_chars,
        floor=floor,
        gene_mentions=n_gene,
        section_count=n_sections,
        aa_mentions=n_aa,
        message=msg,
    )


def evaluate_batch(
    cards: list[dict],
    ranks: dict[str, int] | None = None,
) -> list[ModeB_QualityVerdict]:
    """Evaluate all cards in a receipt batch.

    Parameters
    ----------
    cards : list of dicts with bgc_id and mode_b_md
    ranks : optional dict mapping bgc_id → triage board rank
    """
    ranks = ranks or {}
    return [
        evaluate_card(
            c.get("bgc_id", "?"),
            c.get("mode_b_md", ""),
            rank=ranks.get(c.get("bgc_id", "?")),
        )
        for c in cards
        if (c.get("mode_b_md") or "").strip()
    ]


def summary_line(verdicts: list[ModeB_QualityVerdict]) -> str:
    """One-line summary: '14 FULL, 3 SHALLOW, 2 STUB'."""
    from collections import Counter
    counts = Counter(v.tier for v in verdicts)
    parts = []
    for tier in ("FULL", "SHALLOW", "STUB"):
        if counts[tier]:
            parts.append(f"{counts[tier]} {tier}")
    return ", ".join(parts) if parts else "0 cards"
