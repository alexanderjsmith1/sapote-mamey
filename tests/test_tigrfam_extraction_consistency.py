"""Consistency tripwire: every diagnostic TIGRFAM is either EXTRACTED or EXPLICITLY excepted.

Root cause this closes (investigation, v9.7.99): TIGRFAM hits arrive only via the JSON
antismash.detection.tigrfam module and are surfaced only if their accession is in
`DIAGNOSTIC_TIGRFAM`. Any TIGRFAM accession referenced elsewhere in the engine but absent from
that allowlist is SILENTLY DROPPED from gbk_pfam_hits — the exact failure mode behind the
v9.4.1-tigrfix defect and the v9.6.15-tigr8 follow-on (the 4-ID allowlist silently disabled the §8
combos). The fix flagged that the allowlist must be "kept in sync ... by hand" — this test removes
the "by hand."

Rule: every TIGR##### accession that appears anywhere in mamey/ must be EITHER in
`DIAGNOSTIC_TIGRFAM` (extracted) OR in `KNOWN_NOT_EXTRACTED` below (an explicit, reasoned exception).
A new diagnostic TIGRFAM added without wiring its extraction fails this test instead of silently
vanishing from strain evidence.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mamey.antismash_evidence import DIAGNOSTIC_TIGRFAM  # noqa: E402

# TIGRFAMs deliberately referenced but NOT extracted. Each needs a reason. Empty this as you resolve them.
KNOWN_NOT_EXTRACTED = {
    # architecture_first.py uses these for pathway classification, not extraction
    "TIGR02109",  # mycofactocin radical SAM — architecture_first marker, not Mamey extraction
    "TIGR03962",  # ranthipeptide — architecture_first marker, not Mamey extraction
    "TIGR00543",  # chorismate binding — architecture_first siderophore marker
    # singleton_filter.py references these as housekeeping-blocklist classification stems (v9.7.116),
    # never for extraction — they identify primary-metabolism families to DOWN-WEIGHT in the singleton
    # rarity metric, not diagnostic TIGRFAMs to surface.
    "TIGR00484",  # EF-G / translation elongation factor — housekeeping (translation)
    "TIGR00485",  # EF-G / translation elongation factor — housekeeping (translation)
    "TIGR01029",  # ribosomal protein — housekeeping (translation)
    "TIGR00981",  # ribosomal protein — housekeeping (translation)
    "TIGR00612",  # GcpE / HMBPP synthase — housekeeping (MEP isoprenoid, primary metabolism)
    "TIGR02094",  # glycogen / GlgE-pathway enzyme — housekeeping (central metabolism)
    "TIGR02100",  # pullulanase / α-glucan — housekeeping (central metabolism)
    "TIGR02456",  # glycogen / α-glucan enzyme — housekeeping (central metabolism)
    # BH-002 (v9.7.122): PQQ suppression via PRIMARY_METABOLISM_PATTERNS text scan.
    # TIGR03859 (PqqE radical SAM) is referenced as a _hay() regex target for cofactor_pqq
    # family detection — CDS annotation text matching, not antiSMASH TIGRFAM JSON extraction.
    # PQQ biosynthesis is primary metabolic cofactor; annotation arrives via sec_met_domains
    # (PqqD, PqqE) and named products, not the diagnostic TIGRFAM extraction path.
    "TIGR03859",  # PqqE radical SAM — PQQ cofactor PRIMARY_METABOLISM_PATTERNS text scan only
    # v9.7.130 — bgc_decomp.py domain classifier uses these TIGRFAMs as class-assignment
    # anchors in _CLASS_DOMAINS, not as antiSMASH extraction targets. They arrive via the
    # sec_met_domains column of the gene-by-gene CSV (antiSMASH annotation), not the
    # TIGRFAM JSON extraction path that DIAGNOSTIC_TIGRFAM covers.
    "TIGR03605",  # thioamitide biosynthesis protein — bgc_decomp classifier (thioamide class)
    "TIGR03882",  # thioamitide-specific TIGRFAM — bgc_decomp classifier (thioamide class)
    "TIGR03889",  # thioamitide — bgc_decomp classifier (thioamide class)
    "TIGR03888",  # thioamitide — bgc_decomp classifier (thioamide class)
    "TIGR03883",  # thioamitide — bgc_decomp classifier (thioamide class)
    "TIGR03886",  # thioamitide — bgc_decomp classifier (thioamide class)
    "TIGR03975",  # sactipeptide radical SAM — bgc_decomp classifier (RiPP class)
    "TIGR03988",  # ranthipeptide/sactipeptide — bgc_decomp classifier (RiPP class)
    # v9.7.330 — modeb_cards.py (Blue emit-modeb-cards) counts adenylation (A-)domains for the
    # architecture module tally via (AMP-binding | TIGR01733 | A-OX); a card-display module-count
    # marker, not an antiSMASH TIGRFAM JSON extraction target.
    "TIGR01733",  # adenylation domain (A-domain) — modeb_cards architecture module-count marker
    # v9.7.349 — widget_deliverable.py _REACTION_HINTS (Codex PATCH_008 gene-evidence widget) uses
    # TIGR04516 as one alternative in a glycosyltransferase display-hint regex on the post-seal widget;
    # a reader-side capacity label pattern, not an antiSMASH TIGRFAM JSON extraction target.
    "TIGR04516",  # glycosyltransferase — post-seal widget _REACTION_HINTS display-hint pattern
}


def _referenced_tigrfams():
    refs = {}
    for f in (ROOT / "mamey").glob("*.py"):
        for acc in set(re.findall(r"\b(TIGR\d{4,5})\b", f.read_text())):
            refs.setdefault(acc, set()).add(f.name)
    return refs


def test_every_referenced_tigrfam_is_extracted_or_excepted():
    refs = _referenced_tigrfams()
    extracted = set(DIAGNOSTIC_TIGRFAM)
    unaccounted = {a: sorted(fs) for a, fs in refs.items()
                   if a not in extracted and a not in KNOWN_NOT_EXTRACTED}
    assert not unaccounted, (
        "TIGRFAM accession(s) referenced in the engine but neither extracted (DIAGNOSTIC_TIGRFAM) "
        f"nor explicitly excepted: {unaccounted}. Wire extraction, or add a reasoned "
        "KNOWN_NOT_EXTRACTED entry — do not let it drop silently."
    )


def test_no_stale_exceptions():
    """An exception for a TIGRFAM no longer referenced anywhere is itself rot — drop it."""
    refs = set(_referenced_tigrfams())
    stale = [a for a in KNOWN_NOT_EXTRACTED if a not in refs]
    assert not stale, f"KNOWN_NOT_EXTRACTED has accessions no longer referenced: {stale}"


def test_excepted_accessions_are_not_also_extracted():
    """An accession can't be both excepted and extracted — that's a contradiction."""
    both = set(KNOWN_NOT_EXTRACTED) & set(DIAGNOSTIC_TIGRFAM)
    assert not both, f"accessions both excepted and extracted: {both}"

