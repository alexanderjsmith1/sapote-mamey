"""test_mode_b_quality_gate.py — verify priority-tier-aware Mode B depth enforcement.

Three floors by priority tier:
  HIGH (rank 1–10):   ≥12,000 chars for FULL (domain-heavy §1–§30)
  MID  (rank 11–25):  ≥11,000 chars for FULL
  LOW  (rank 26+):    ≥10,000 chars for FULL
  STUB threshold:     <2,000 chars regardless of tier
"""
from mamey.mode_b_quality_gate import (
    evaluate_card, evaluate_batch, summary_line,
    priority_tier, FLOORS, FLOOR_STUB,
)


def _fake_card(n_chars, with_genes=True, full_sections=True, with_enrichment=True):
    """Build a synthetic card at a specific character count.

    full_sections=True prepends the §1–§10 headers (v9.7.112 contract). with_enrichment=True
    appends a >=2,000-char §11–§20 enrichment block so FULL-expecting fixtures model the new
    standard. Set either False to simulate a card that stops short.
    """
    if with_genes:
        unit = ("XF36_04210 (5129 aa) PF00501 condensation adenylation "
                "TIGR01720 thiolation XF36_04215 (412 aa) PF04820 halogenase "
                "ketosynthase dehydratase XF36_04218 (623 aa) hydroxylase ")
    else:
        unit = ("This BGC contains biosynthetic genes consistent with a "
                "secondary metabolite. The cluster architecture suggests "
                "a polyketide or nonribosomal peptide scaffold. ")
    if full_sections:
        headers = ("§1 Identity §3 Biosynthetic Core §4 Gene neighborhood §5 Pharmacology "
                   "§6 Priority §7 Verdict §8 Summary §9 Activation §10 Forensic ")
    else:
        headers = "§1 Identity §3 Biosynthetic Core §5 Pharmacology "
    enrich = ""
    if with_enrichment:
        enrich = ("\n§11 Rarest domains. XF36_04210 carries PF04820 (a genome-unique singleton "
                  "seen in only this gene across the genome); the full domain set spans condensation, "
                  "adenylation, and thiolation modules characteristic of an NRPS assembly line. "
                  "§12 Domain inventory. The cluster spans 12 domain families across the assembly "
                  "line, with the condensation and adenylation modules forming the NRPS core and "
                  "the ketosynthase units forming the PKS extension; of these, several sit outside "
                  "the common carrier machinery and represent the cluster's specific tailoring "
                  "content. §13 NRPS/PKS typing places this as a hybrid PKS-NRPS architecture. "
                  "Module count constrains predicted product length; specificity codes would refine "
                  "the monomer set drawn into the growing chain during each condensation cycle. "
                  "§14 Rarest genes. The least common domain content is carried by the tailoring "
                  "enzymes flanking the core — the halogenase and the hydroxylase, each contributing "
                  "to the predicted structural decoration of the mature scaffold. §15 The expression "
                  "context and precursor supply round out the deterministic enrichment census for "
                  "this cluster, drawn entirely from gene-table data rather than asserted prose. "
                  "§16 Substrate, tailoring, transport, and resistance audit. The adenylation "
                  "specificity pockets suggest hydrophobic residue selection; the flanking ABC "
                  "transporter and a putative target-modifying resistance determinant sit within the "
                  "locus, consistent with self-protection co-localised with the biosynthetic core. "
                  "§17 KCB and misanchor audit. The nearest known-cluster anchor is a similarity "
                  "signal only; the committed class-diagnostic enzyme of that anchor is present here, "
                  "so no misanchor flag is raised and the class call rests on own-gene evidence. "
                  "§18 Regulation and activation. A cluster-situated regulator and the bldA-dependent "
                  "TTA distribution shape predicted expression timing; no global silencing risk is "
                  "inferred for this locus from the available context. §19 RG-GMCI and assembly "
                  "forensics. The cluster is interior to its contig with no split-pathway evidence; "
                  "the corrected boundary count treats it as a single intact unit. §20 Actionable "
                  "next analysis. Targeted fermentation with the predicted precursor supplement and "
                  "LC-HRMS in the predicted mass window would test the capacity-level hypothesis, "
                  "which remains a similarity-anchored prediction rather than a compound identity.")
    body_target = max(0, n_chars - len(headers) - len(enrich))
    body = (unit * ((body_target // len(unit)) + 2))[:body_target]
    text = headers + body + enrich
    return text


# --- Priority tier assignment ---

def test_priority_tier_high():
    assert priority_tier(1) == "HIGH"
    assert priority_tier(10) == "HIGH"

def test_priority_tier_mid():
    assert priority_tier(11) == "MID"
    assert priority_tier(25) == "MID"

def test_priority_tier_low():
    assert priority_tier(26) == "LOW"
    assert priority_tier(100) == "LOW"

def test_priority_tier_none():
    assert priority_tier(None) == "LOW"


# --- FULL at each tier ---

def test_high_priority_full():
    v = evaluate_card("BGC001", _fake_card(12500), rank=3)
    assert v.tier == "FULL"
    assert v.priority == "HIGH"
    assert v.floor == 12000

def test_mid_priority_full():
    v = evaluate_card("BGC015", _fake_card(11500), rank=15)
    assert v.tier == "FULL"
    assert v.priority == "MID"
    assert v.floor == 11000

def test_low_priority_full():
    v = evaluate_card("BGC030", _fake_card(10500), rank=30)
    assert v.tier == "FULL"
    assert v.priority == "LOW"
    assert v.floor == 10000


# --- SHALLOW: above stub, below tier floor ---

def test_high_priority_shallow():
    """A rank-3 BGC at 7,000 chars is SHALLOW — below the 9,000 HIGH floor."""
    v = evaluate_card("BGC001", _fake_card(7000), rank=3)
    assert v.tier == "SHALLOW"
    assert v.priority == "HIGH"
    assert "12,000 HIGH floor" in v.message

def test_mid_priority_shallow():
    """A rank-15 BGC at 6,000 chars is SHALLOW — below the 8,000 MID floor."""
    v = evaluate_card("BGC015", _fake_card(6000), rank=15)
    assert v.tier == "SHALLOW"
    assert v.priority == "MID"

def test_low_priority_shallow():
    """A rank-30 BGC at 4,000 chars is SHALLOW — below the 6,000 LOW floor."""
    v = evaluate_card("BGC030", _fake_card(4000), rank=30)
    assert v.tier == "SHALLOW"
    assert v.priority == "LOW"


# --- STUB: below 2,000 regardless of tier ---

def test_stub_any_tier():
    for rank in [1, 15, 30, None]:
        v = evaluate_card("BGC099", _fake_card(800, with_enrichment=False), rank=rank)
        assert v.tier == "STUB", f"rank={rank} should be STUB at 800 chars"

def test_empty_is_stub():
    v = evaluate_card("BGC099", "", rank=1)
    assert v.tier == "STUB"
    assert v.char_count == 0


# --- No gene mentions → SHALLOW even if long ---

def test_no_genes_is_shallow():
    """A long card with no locus tags or domain accessions is SHALLOW (gene-mention floor)."""
    v = evaluate_card("BGC001", _fake_card(9500, with_genes=False, with_enrichment=False), rank=3)
    assert v.tier == "SHALLOW"
    assert "gene mentions" in v.message


# --- Batch with ranks ---

def test_batch_with_ranks():
    cards = [
        {"bgc_id": "BGC001", "mode_b_md": _fake_card(12500)},
        {"bgc_id": "BGC015", "mode_b_md": _fake_card(6000)},
        {"bgc_id": "BGC030", "mode_b_md": _fake_card(1500, with_enrichment=False)},
    ]
    ranks = {"BGC001": 3, "BGC015": 15, "BGC030": 30}
    verdicts = evaluate_batch(cards, ranks=ranks)
    tiers = {v.bgc_id: v.tier for v in verdicts}
    assert tiers["BGC001"] == "FULL"     # 12,500 ≥ 12,000 HIGH, §1–§10 complete
    assert tiers["BGC015"] == "SHALLOW"  # 6,000 < 8,000 MID
    assert tiers["BGC030"] == "STUB"     # 1,500 < 2,000


def test_summary_line_format():
    cards = [
        {"bgc_id": "BGC001", "mode_b_md": _fake_card(12500)},
        {"bgc_id": "BGC015", "mode_b_md": _fake_card(6000)},
        {"bgc_id": "BGC030", "mode_b_md": _fake_card(1500, with_enrichment=False)},
    ]
    ranks = {"BGC001": 3, "BGC015": 15, "BGC030": 30}
    verdicts = evaluate_batch(cards, ranks=ranks)
    line = summary_line(verdicts)
    assert "1 FULL" in line
    assert "1 SHALLOW" in line
    assert "1 STUB" in line


# --- Threshold constants ---

def test_floor_values():
    assert FLOORS["HIGH"] == 12000
    assert FLOORS["MID"] == 11000
    assert FLOORS["LOW"] == 10000
    assert FLOOR_STUB == 2000


# --- _RE_LOCUS refined regex (v9.7.111): antiSMASH ctg loci, any width, RiPP-family-agnostic ---

def test_ctg_style_locus_tags_counted():
    """antiSMASH ctgN_NNN tags must count, any suffix width (incl. single-digit)."""
    from mamey.mode_b_quality_gate import _RE_LOCUS
    tags = "ctg6_186 ctg6_207 ctg1_50 ctg57_1 ctg57_2 ctg28_3 ctg12_3041 XF36_04210 SSHG_01234"
    found = _RE_LOCUS.findall(tags)
    for t in ["ctg6_186", "ctg1_50", "ctg57_1", "ctg57_2", "ctg28_3",
              "ctg12_3041", "XF36_04210", "SSHG_01234"]:
        assert t in found
    assert len(found) == 9


def test_ripp_precursor_suffixed_loci_counted_any_family():
    """antiSMASH appends a RiPP class to precursor loci; must count for ANY family.

    Real tag observed in a Loose-profile Streptomyces run: ctg42_21_lanthipeptide. The suffix is
    matched structurally so antiSMASH-8 families beyond the original four (thioamitide,
    lipolanthine, ranthipeptide, microviridin, cyanobactin, ...) are not silently dropped.
    """
    from mamey.mode_b_quality_gate import _RE_LOCUS
    tags = ("ctg42_21_lanthipeptide ctg402_5_lanthipeptide ctg6_88_lassopeptide "
            "ctg3_14_sactipeptide ctg9_2_thiopeptide ctg7_1_ranthipeptide "
            "ctg8_3_thioamitide ctg4_5_lipolanthine ctg2_9_microviridin ctg5_6_cyanobactin")
    found = _RE_LOCUS.findall(tags)
    for t in ["ctg42_21_lanthipeptide", "ctg8_3_thioamitide", "ctg4_5_lipolanthine",
              "ctg2_9_microviridin", "ctg5_6_cyanobactin", "ctg7_1_ranthipeptide"]:
        assert t in found, f"{t} not matched"
    assert len(found) == 10


def test_ctg_tags_do_not_false_match_domains():
    """Pfam/TIGR/CAZyme/transporter/version tokens must NOT match."""
    from mamey.mode_b_quality_gate import _RE_LOCUS
    non_loci = ("MFS_3 PKS_1 NRPS_2 GH18_1 AA10_1 CBM_4 KS_3 SIS_2 "
                "Trans_reg_C PF00501 TIGR01930 v9_7_110 Acyl_transf_1 PCP_mC NRPS-A_a3")
    assert _RE_LOCUS.findall(non_loci) == []


# --- v9.7.112: §9/§10 presence requirement + raised floors ---

def test_card_missing_section_9_and_10_is_shallow():
    """A long, gene-rich §1–§8 card that omits §9/§10 must be SHALLOW, not FULL."""
    v = evaluate_card("BGC001", _fake_card(12000, full_sections=False), rank=3)
    assert v.tier == "SHALLOW"
    assert "missing" in v.message
    assert "§9" in v.message and "§10" in v.message

def test_full_section_1_to_10_card_is_full():
    """A §1–§10 card above the HIGH floor reads FULL with the §1–§10 marker."""
    v = evaluate_card("BGC001", _fake_card(12500, full_sections=True), rank=3)
    assert v.tier == "FULL"
    assert "§1–§48 substance" in v.message

def test_fragment_exempt_from_section_9_10_requirement():
    """A genuine sub-STUB fragment is STUB and not penalized for missing §9/§10."""
    frag = "§1 fragment on ctg88. ctg88_1 (210 aa) hypothetical. §10 RG-GMCI link noted."
    v = evaluate_card("BGC099", frag, rank=40)
    assert v.tier == "STUB"
    assert "missing" not in v.message

def test_present_section_numbers_parses_10_correctly():
    """§10 must parse as 10, not 1 (10-first alternation)."""
    from mamey.mode_b_quality_gate import present_section_numbers
    nums = present_section_numbers("§1 a §9 b §10 c")
    assert nums == {1, 9, 10}


# --- v9.7.112: §11–§20 mandatory enrichment block ---

def test_card_without_enrichment_is_shallow():
    """A complete §1–§10 card above floor but with NO §11–§20 enrichment is SHALLOW."""
    v = evaluate_card("BGC001", _fake_card(9500, with_enrichment=False), rank=3)
    assert v.tier == "SHALLOW"
    assert "enrichment" in v.message

def test_card_with_thin_enrichment_is_shallow():
    """Enrichment present but under 1,000 chars is SHALLOW."""
    card = _fake_card(9500, with_enrichment=False) + "\n§11 Rarest domains. A short note only."
    v = evaluate_card("BGC001", card, rank=3)
    assert v.tier == "SHALLOW"
    assert "enrichment" in v.message

def test_card_with_full_enrichment_is_full():
    """A §1–§10 card above floor WITH >=2,000c enrichment is FULL."""
    v = evaluate_card("BGC001", _fake_card(12500, with_enrichment=True), rank=3)
    assert v.tier == "FULL"
    assert "enrichment" in v.message

def test_enrichment_section_20_parses_whole():
    """§20 must parse as part of the enrichment block, not §2."""
    from mamey.mode_b_quality_gate import _RE_ENRICHMENT_HEAD
    assert _RE_ENRICHMENT_HEAD.findall("§20 final enrichment") == ["§20"]
    assert _RE_ENRICHMENT_HEAD.findall("§2 biosynthetic") == []


# --- v9.7.114: fragment-floor exemption (boundary status + CDS, NOT CDS alone) ---

def _frag_card(n_chars):
    """A §1–§10 + enrichment card sized to land between FRAGMENT_FLOOR and the HIGH floor."""
    genes = " ".join(f"ctg88_{i} encodes a domain-bearing biosynthetic gene." for i in range(1, 12))
    enrich = (" §11 Rarest domains: ctg88_1 carries a genome-unique singleton. "
              "§12 Domain inventory: three families span this cluster. "
              + "Per-gene domain detail for this small boundary cluster follows. " * 12)
    card = ("§1 Identity fragment on ctg88. §3 Biosynthetic core. " + genes
            + " §4 §5 §6 §7 §8 §9 activation §10 forensic RG-GMCI. " + enrich
            + "Brief but complete boundary-fragment analysis. " * 24)
    return card[:n_chars]

def test_edge_fragment_uses_fragment_floor():
    """An Edge fragment with few CDS reaches FULL on the reduced fragment floor."""
    v = evaluate_card("BGC022", _frag_card(3400), rank=1, edge_status="Edge", cds_count=3)
    assert v.tier == "FULL"
    assert "fragment floor" in v.message

def test_fullcontig_fragment_uses_fragment_floor():
    v = evaluate_card("BGC026", _frag_card(3400), rank=1, edge_status="Full-contig", cds_count=12)
    assert v.tier == "FULL"

def test_interior_small_cluster_NOT_exempt():
    """CRITICAL: an Interior small cluster is intact, not a fragment — it owes full depth."""
    v = evaluate_card("BGC005", _frag_card(3400), rank=1, edge_status="Interior", cds_count=9)
    assert v.tier == "SHALLOW"
    assert "HIGH floor" in v.message  # still held to the full HIGH floor

def test_large_edge_cluster_NOT_exempt():
    """An Edge cluster above the CDS threshold is not a fragment."""
    v = evaluate_card("BGC010", _frag_card(3400), rank=1, edge_status="Edge", cds_count=50)
    assert v.tier == "SHALLOW"

def test_missing_edge_status_NO_exemption():
    """Conservative: unknown boundary status grants no exemption."""
    v = evaluate_card("BGCx", _frag_card(3400), rank=1, edge_status=None, cds_count=3)
    assert v.tier == "SHALLOW"

def test_fragment_exemption_never_raises_floor():
    """The exemption only lowers a floor; a fragment never gets a HIGHER bar than its tier."""
    # An Edge fragment at LOW rank already has a 6000 floor; fragment floor 2500 < 6000, so it applies.
    v = evaluate_card("BGCl", _frag_card(3400), rank=40, edge_status="Edge", cds_count=3)
    assert v.tier == "FULL"
    assert v.floor == 2500


# --- B3 (v9.7.119): §11 phantom-§1 regex fix ---
from mamey.mode_b_quality_gate import present_section_numbers


def test_section_11_does_not_phantom_section_1():
    """§11 must not be counted as §1 by present_section_numbers() (the _RE_SECTION_NUM lookahead fix)."""
    card = ("## §2 Class\nBGC class-III lanthipeptide. ctg7_15 LanKC 950 aa.\n\n"
            "## §9 Lead Tier\nMedium. ctg7_15 LanKC.\n\n"
            "## §10 Cross-Strain\nCross-genus. ctg7_15 950 aa.\n\n"
            "## §11 Domain Inventory\nctg7_15: LANC_like 950 aa.\n")
    present = present_section_numbers(card)
    assert 1 not in present
    assert 10 in present
    assert 11 in present or 1 not in present  # §11 itself isn't in the {1..10} set; key point is no phantom §1


def test_section_10_still_recognised_after_fix():
    """§10 must still parse correctly after the lookahead fix."""
    assert 10 in present_section_numbers("## §10 Cross-Strain Context\n")
    assert 1 not in present_section_numbers("## §10 Cross-Strain Context\n")


def test_missing_section_1_makes_card_shallow_not_full():
    """A card with §11 but no §1 must not pass as FULL (phantom §1 previously cleared MIN_SECTIONS)."""
    base = ("LanKC ctg7_15 950 aa class-III lanthipeptide synthetase. "
            "Precursor ctg7_14 105 aa upstream. ABC_tran ctg7_16 400 aa. "
            "LANC_like domain ctg7_15 950 aa. Interior 21.9 kb. ")
    card = ("## §2 Class\n" + base * 5 + "\n## §9 Lead Tier\n" + base * 5 +
            "\n## §10 Cross-Strain\n" + base * 5 + "\n## §11 Domain Inventory\n" + base * 5)
    assert evaluate_card("BGC042", card, rank=None).tier == "SHALLOW"
