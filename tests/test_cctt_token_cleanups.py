"""Token cleanups (N-05 source-level): stop spurious CCTT hits at the token, not just flag them.

Pinned from the cohort scan:
  - T43-PHO `phosphonate` matched "...ABC transporter..." (uptake, not synthesis); `pep mutase` /
    `phosphoenolpyruvate mutase` matched "isocitrate lyase/PEP-mutase FAMILY protein" (shared ICL fold).
  - T43-TET `glyceryl` matched "diacylglyceryl transferase" (lipoprotein/membrane processing).
The committed biosynthesis annotations must still fire.
"""
import re
from mamey.source_scans import CCTT_PATTERNS, CASSETTE_PATTERNS

PHO = CCTT_PATTERNS["T43-PHO_phosphonate"]
CAS_PHO = CASSETTE_PATTERNS["phosphonate"]
TET = CCTT_PATTERNS["T43-TET_tetronate_spirotetronate"]
CAS_TET = CASSETTE_PATTERNS["tetronate_spirotetronate"]
PYE = CCTT_PATTERNS["T43-PYE_polyene_macrolide"]
CAS_PYE = CASSETTE_PATTERNS["polyene_ptm_hsaf"]
NUC = CCTT_PATTERNS["T43-NUC_nucleoside"]
CAS_NUC = CASSETTE_PATTERNS["nucleoside"]
AMC = CCTT_PATTERNS["T43-AMC_aminocyclitol"]
CAS_AMC = CASSETTE_PATTERNS["aminoglycoside_aminocyclitol"]
LAN = CCTT_PATTERNS["T43-LAN_lanthipeptide"]
CAS_LAN = CASSETTE_PATTERNS["lanthipeptide"]

def _fires(pats, text):
    return any(re.search(p, text, re.I) for p in pats)

def test_pho_transporter_does_not_fire():
    assert not _fires(PHO, "2-aminoethylphosphonate ABC transporter substrate-binding protein")
    assert not _fires(PHO, "2-aminoethylphosphonate ABC transporter permease subunit")
    # BC2-408: the cassette twin (MMC-004) never received T43-PHO's own guards -- fixed here.
    assert not _fires(CAS_PHO, "2-aminoethylphosphonate ABC transporter substrate-binding protein")

def test_pho_family_fold_does_not_fire():
    assert not _fires(PHO, "isocitrate lyase/phosphoenolpyruvate mutase family protein")
    assert not _fires(PHO, "PEP mutase family protein")
    # GenBank wraps long /product values: the separator before 'family' may be a newline + indent, not a
    # single space. The lookahead must tolerate any whitespace join (this was a real miss on SID-XXX).
    assert not _fires(PHO, "isocitrate lyase/phosphoenolpyruvate mutase\n          family protein")
    assert not _fires(CAS_PHO, "isocitrate lyase/phosphoenolpyruvate mutase family protein")  # cassette twin fixed too

def test_pho_committed_biosynthesis_still_fires():
    assert _fires(PHO, "phosphoenolpyruvate mutase")
    assert _fires(PHO, "phosphonate biosynthesis protein")
    assert _fires(PHO, "PEP mutase")  # committed, no 'family' suffix
    assert _fires(CAS_PHO, "phosphoenolpyruvate mutase")
    assert _fires(CAS_PHO, "phosphonate biosynthesis protein")

def test_tet_diacylglyceryl_does_not_fire():
    assert not _fires(TET, "prolipoprotein diacylglyceryl transferase")
    assert not _fires(TET, "diacylglyceryl transferase")
    assert not _fires(CAS_TET, "prolipoprotein diacylglyceryl transferase")  # cassette twin fixed too

def test_tet_real_glyceryl_still_fires():
    assert _fires(TET, "glyceryl-S-ACP synthase")
    assert _fires(TET, "tetronate biosynthesis protein")
    assert _fires(TET, "FkbH-like glyceryl transferase")  # 'fkbh' + standalone 'glyceryl'


def test_pho_smcog_carboxyphosphonate_does_not_fire():
    # SMCOG1231 ("carboxyvinyl-carboxyphosphonate phosphorylmutase") tags the ICL superfamily — overwhelmingly
    # isocitrate lyase (primary metabolism). The bare `phosphonate` token matched the 'carboxyphosphonate'
    # substring and over-fired (84% of T43-PHO firings on the live cohort). Excluded via (?<!carboxy).
    assert not _fires(PHO, "biosynthetic-additional (smcogs) SMCOG1231: carboxyvinyl-carboxyphosphonate phosphorylmutase")
    assert not _fires(PHO, "carboxyphosphonate")
    assert not _fires(CAS_PHO, "biosynthetic-additional (smcogs) SMCOG1231: carboxyvinyl-carboxyphosphonate phosphorylmutase")
    assert not _fires(CAS_PHO, "carboxyphosphonate")

def test_pho_real_pep_mutase_domain_now_fires():
    # the true phosphonate signal is antiSMASH's sec_met_domain HMM hit "PEP_mutase" — previously MISSED
    # (underscore form caught by no token). Now caught by \bpep_mutase\b.
    assert _fires(PHO, "PEP_mutase (E-value: 5.3e-71, bitscore: 229.5, seeds: 69, tool: rule-based-clusters)")


# BC2-408: T43-PYE already guards "polyene" with (?<!aryl) (an APE-type pigment, not polyene-
# macrolide antifungal chemistry — the same confusion scoring.py's PIGMENT_NONLEAD_CLASSES
# guards against on the scoring axis). The cassette twin (polyene_ptm_hsaf, registry MMC-012,
# TIER_1_DIAGNOSTIC/HIGH, surfaced directly in the per-strain workbook's Cassette_Registry
# sheet) had the bare, unguarded token and was missing the same fix.

def test_pye_arylpolyene_does_not_fire():
    assert not _fires(PYE, "arylpolyene synthase, APE pathway protein")
    assert not _fires(CAS_PYE, "arylpolyene synthase, APE pathway protein")  # cassette twin fixed too

def test_pye_real_polyene_still_fires():
    assert _fires(PYE, "polyene macrolide biosynthesis")
    assert _fires(PYE, "natamycin biosynthesis protein")
    assert _fires(CAS_PYE, "polyene macrolide biosynthesis")
    assert _fires(CAS_PYE, "HSAF biosynthesis gene cluster")


# BC2-408 round 2: Alex flagged that the CASSETTE/CCTT sibling sweep was NOT finished (2 of ~15
# pairs checked at the time) and asked for one more pass. Checking the remaining true sibling
# pairs (a CASSETTE_PATTERNS entry with a semantically corresponding CCTT trigger) surfaced three
# more real gaps, verified live exactly like the PYE/PHO pair above.

def test_nuc_primary_metabolism_does_not_fire():
    # bare "nucleoside" (never in T43-NUC's own pattern set) matched universal housekeeping
    # enzymes with zero relation to nikkomycin/polyoxin-class peptidyl-nucleoside biosynthesis.
    assert not _fires(NUC, "nucleoside diphosphate kinase")
    assert not _fires(NUC, "purine nucleoside phosphorylase")
    assert not _fires(NUC, "nucleoside hydrolase")
    assert not _fires(CAS_NUC, "nucleoside diphosphate kinase")  # cassette twin fixed too
    assert not _fires(CAS_NUC, "purine nucleoside phosphorylase")

def test_nuc_real_peptidyl_nucleoside_still_fires():
    assert _fires(NUC, "nikkomycin biosynthesis protein NikJ")
    assert _fires(NUC, "peptidyl-nucleoside antibiotic")
    assert _fires(CAS_NUC, "nikkomycin biosynthesis protein NikJ")
    assert _fires(CAS_NUC, "polyoxin biosynthesis protein")


def test_amc_resistance_gene_does_not_fire():
    # bare "aminoglycoside" (never in T43-AMC's own pattern set) matched aminoglycoside-MODIFYING
    # resistance enzymes (self-protection/detox), not aminoglycoside biosynthesis.
    assert not _fires(AMC, "aminoglycoside phosphotransferase")
    assert not _fires(AMC, "aminoglycoside N-acetyltransferase")
    assert not _fires(CAS_AMC, "aminoglycoside phosphotransferase")  # cassette twin fixed too
    assert not _fires(CAS_AMC, "aminoglycoside 6-adenylyltransferase")

def test_amc_real_aminocyclitol_still_fires():
    assert _fires(AMC, "2-deoxy-scyllo-inosose synthase")
    assert _fires(AMC, "aminocyclitol biosynthesis protein DOIS")
    assert _fires(CAS_AMC, "2-deoxy-scyllo-inosose synthase")
    assert _fires(CAS_AMC, "aminocyclitol biosynthesis protein DOIS")


def test_lan_unanchored_substring_does_not_fire():
    # bare, unanchored lanc/lanm/lant/lanp matched pure substring coincidences with zero relation
    # to lanthipeptide biosynthesis -- this file's own UMED_PATTERNS docstring already diagnosed
    # this exact bug class for a different dict entry (LanT_C39_transporter_peptidase); the
    # CASSETTE_PATTERNS twin never received the same guard.
    assert not _fires(CAS_LAN, "atlantic salmon protein")
    assert not _fires(CAS_LAN, "planthopper")
    assert not _fires(CAS_LAN, "Lant_dehydr_N")  # real LanB domain, but not via a "lant" coincidence
    # T43-LAN's own \b-guarded lanc/lanm already reject these; confirm the sibling agrees.
    assert not _fires(LAN, "atlantic salmon protein")
    assert not _fires(LAN, "planthopper")

def test_lan_real_lanthipeptide_still_fires():
    assert _fires(LAN, "lanthipeptide class I")
    assert _fires(LAN, "lantibiotic biosynthesis protein LanC")
    assert _fires(CAS_LAN, "lanthipeptide class I")
    assert _fires(CAS_LAN, "LanM cyclase")
    assert _fires(CAS_LAN, "LanC-like protein")
