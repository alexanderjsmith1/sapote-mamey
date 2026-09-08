"""Tetronate cassette-completeness gate (v9.7.183) — the tetronate cassette-completeness patch.

FkbH is necessary-not-sufficient for a tetronate; the ring needs a FabH/KSIII closure enzyme (or a
Diels-Alderase for the spiro sub-class) co-located with the FkbH+ACP pair. The gate grades the
T43-TET trigger instead of firing it on FkbH alone — the same partial-evidence-as-identity fix §8
(KCB coverage) and §4 (BLASTp reconcile) apply elsewhere."""
from mamey.antismash_evidence import tetronate_cassette_completeness as tcc


def test_bgc010_starter_only_is_the_ground_truth():
    # Tetronate case: FkbH + ACP present, no KSIII anywhere reachable -> STARTER_ONLY (tips to tetramate)
    r = tcc(["FkbH", "PP-binding", "PKS_KS"], partner_domains=["PKS_KS"])
    assert r["grade"] == "TET_CASSETTE_STARTER_ONLY"
    assert r["has_starter"] and not r["has_ksiii"] and not r["has_spiro"]


def test_complete_when_ksiii_colocated():
    assert tcc(["FkbH", "PP-binding", "fabH"])["grade"] == "TET_CASSETTE_COMPLETE"
    # also complete when the KSIII is in an RGGMCI partner
    assert tcc(["FkbH", "PP-binding"], partner_domains=["ACP_syn_III"])["grade"] == "TET_CASSETTE_COMPLETE"


def test_spiro_when_diels_alderase_present():
    assert tcc(["FkbH", "Diels_aldr"])["grade"] == "TET_CASSETTE_SPIRO"


def test_indeterminate_when_edge_truncated():
    assert tcc(["FkbH", "PP-binding"], edge_truncated=True)["grade"] == "TET_CASSETTE_INDETERMINATE"


def test_no_starter_should_not_fire():
    assert tcc(["PKS_KS", "AMP-binding"])["grade"] == "TET_NO_STARTER"


def test_ksiii_markers_are_in_the_domain_table():
    from mamey.antismash_evidence import DIAGNOSTIC_SEC_MET_DOMAINS as D
    for k in ("fabH", "ACP_syn_III", "ksIII"):
        assert k in D


# --- v9.7.194: co-fire precedence wiring (grader wired into apply_cctt_vetoes) ---
def _bgc(bgc_id, products, start, end, contig="NODE_1"):
    from types import SimpleNamespace
    return SimpleNamespace(bgc_id=bgc_id, products=products, contig=contig,
                           start=start, end=end, region_number=1, kcb_top="",
                           mibig_hits=[], closest_candidate_kcb_product="")


def _cds(contig, start, end, text):
    from types import SimpleNamespace
    return SimpleNamespace(contig=contig, start=start, end=end, strand=1,
                           product=text, locus_tag="ctg1", qualifiers={"sec_met_domain": [text]})


def test_ptm_tet_cofire_spiro_gives_tetronate_precedence():
    """When PTM+TET co-fire and a Diels-Alderase (spiro closure) is in-region, the annotation must
    give spirotetronate precedence — not the PTM KCB call. This is the spirotetronate-precedence case."""
    from mamey.source_scans import apply_cctt_vetoes
    bgc = _bgc("BGC020", ["NRPS", "T1PKS"], 1000, 60000)
    # CDS carrying FkbH + Diels-Alderase domain text in-region
    cds_list = [_cds("NODE_1", 2000, 3000, "FkbH glyceryl-ACP"),
                _cds("NODE_1", 4000, 5000, "Diels_aldr ring closure"),
                _cds("NODE_1", 6000, 7000, "PP-binding ACP")]
    cctt = {"bgc_coupling": {"BGC020": ["T43-PTM_hsaf_tetramate",
                                        "T43-TET_tetronate_spirotetronate"]}}
    out = apply_cctt_vetoes(cctt, [bgc], cds_list)
    prec = out.get("ptm_tet_precedence", {}).get("BGC020")
    assert prec is not None, "co-fire precedence annotation missing"
    assert prec["grade"] == "TET_CASSETTE_SPIRO"
    assert "precedence" in prec["note"].lower()


def test_ptm_tet_cofire_starter_only_keeps_ptm():
    """FkbH present but no ring-closure enzyme: tetronate is starter-only, PTM retains precedence.
    Guards against the report's over-broad 'FkbH present -> raise tetronate' suggestion."""
    from mamey.source_scans import apply_cctt_vetoes
    bgc = _bgc("BGC099", ["NRPS", "T1PKS"], 1000, 60000)
    cds_list = [_cds("NODE_1", 2000, 3000, "FkbH glyceryl starter"),
                _cds("NODE_1", 6000, 7000, "PP-binding ACP")]
    cctt = {"bgc_coupling": {"BGC099": ["T43-PTM_hsaf_tetramate",
                                        "T43-TET_tetronate_spirotetronate"]}}
    out = apply_cctt_vetoes(cctt, [bgc], cds_list)
    prec = out.get("ptm_tet_precedence", {}).get("BGC099")
    assert prec is not None
    assert prec["grade"] == "TET_CASSETTE_STARTER_ONLY"
    assert "ptm call retains precedence" in prec["note"].lower()
