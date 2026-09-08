from types import SimpleNamespace
from zipfile import ZipFile

from mamey.mibig_per_gene import (
    _convergence_tier,
    build_bgc_mibig_profile,
    build_mibig_convergence,
    parse_mibig_gene_map,
)
from mamey.length_weighted import (
    length_weighted_profile,
    nominal_length_profile,
    normalize_product_family,
    summary,
)


def test_mibig_parser_isolated_and_rank_uncapped(tmp_path):
    txt = """ClusterBlast scores for NODE_1\nTable of genes, locations, strands and annotations of query cluster:\nctg1_1\t1\t100\t+\nctg1_2\t101\t200\t+\n\nSignificant hits:\n1. BGC0000001.1\tone\n9. BGC0000009.1\tnine\n\nDetails:\n>>\n9. BGC0000009.1\nSource: nine\nType: PKS\nTable of Blast hits (query gene, subject gene, %identity, blast score, %coverage, e-value):\nctg1_2\tSUB9\t55\t900\t98\t1e-20\n"""
    p = tmp_path / "x.zip"
    with ZipFile(p, "w") as z:
        z.writestr("knownclusterblast/NODE_1_c1.txt", txt)
        z.writestr("clusterblast/NODE_1_c1.txt", txt.replace("SUB9", "GENERIC"))
    bgc = SimpleNamespace(bgc_id="BGC001", contig="NODE_1", region_number=1, kcb_top=None)
    out = parse_mibig_gene_map(p, [bgc])
    assert out["bgc_count"] == 1
    assert out["schema_version"] == "mibig_per_gene_v3"
    assert out["report_only_contract"] == "REPORT_ONLY_NO_SCORING"
    assert out["query_gene_counts"]["BGC001"] == 2
    assert out["recognizable_query_gene_counts"]["BGC001"] == 1
    assert out["per_gene_mibig"]["BGC001"][0]["reference_rank"] == 9
    assert out["per_gene_mibig"]["BGC001"][0]["subject_gene"] == "SUB9"


def test_mibig_parser_preserves_same_query_across_ranked_references(tmp_path):
    txt = """>>
1. BGC0000001.1
Source: one
Type: PKS
Table of Blast hits (query gene, subject gene, %identity, blast score, %coverage, e-value):
ctg1_1\tONE_A\t80\t1000\t99\t1e-50
ctg1_2\tONE_B\t70\t800\t95\t1e-40
>>
9. BGC0000009.1
Source: nine
Type: PKS
Table of Blast hits (query gene, subject gene, %identity, blast score, %coverage, e-value):
ctg1_1\tNINE_A\t60\t700\t90\t1e-30
"""
    path = tmp_path / "ranked.zip"
    with ZipFile(path, "w") as z:
        z.writestr("knownclusterblast/NODE_1_c1.txt", txt)
    bgc = SimpleNamespace(
        bgc_id="BGC001",
        contig="NODE_1",
        region_number=1,
        kcb_top="BGC0000001",
        products=["T1PKS"],
        edge_status="Interior",
    )
    out = parse_mibig_gene_map(path, [bgc])
    rows = out["per_gene_mibig"]["BGC001"]
    assert len(rows) == 3
    assert out["query_gene_counts"]["BGC001"] == 2
    assert out["recognizable_query_gene_counts"]["BGC001"] == 2
    assert {
        (row["query_gene"], row["mibig_accession"]) for row in rows
    } == {
        ("ctg1_1", "BGC0000001"),
        ("ctg1_2", "BGC0000001"),
        ("ctg1_1", "BGC0000009"),
    }
    convergence = build_mibig_convergence(
        out["per_gene_mibig"],
        out["query_gene_counts"],
        {"BGC001": {"products": ["T1PKS"], "edge_status": "Interior"}},
    )
    assert convergence[0]["mibig_accession"] == "BGC0000001"
    assert convergence[0]["distinct_query_genes"] == 2
    assert convergence[0]["class_concordance"] == "CONCORDANT"
    profile = build_bgc_mibig_profile(
        out["per_gene_mibig"],
        out["query_gene_counts"],
        {"BGC001": {"kcb_top": "BGC0000001"}},
        convergence,
    )
    assert profile["BGC001"]["recognizable_gene_count"] == 2
    assert profile["BGC001"]["dominant_mibig_accession"] == "BGC0000001"


def test_high_density_convergence_tier_is_sequence_evidence_only():
    rows = []
    for index in range(12):
        rows.append({
            "bgc_id": "BGC001",
            "query_gene": f"q{index}",
            "subject_gene": f"s{index}",
            "mibig_accession": "BGC0000123",
            "mibig_compound": "reference family",
            "reference_type": "PKS",
            "reference_rank": 1,
            "pct_identity": 75,
            "pct_coverage": 95,
            "blast_score": 500,
        })
    convergence = build_mibig_convergence(
        {"BGC001": rows},
        {"BGC001": 12},
        {"BGC001": {"products": ["T1PKS"], "edge_status": "Interior"}},
    )
    assert convergence[0]["convergence_tier"] == "H1_HIGH_DENSITY"
    assert "not proof of exact product identity" in convergence[0]["claim_safety"]


def test_coverage_over_100_is_preserved_but_capped_for_interpretation(tmp_path):
    txt = """>>
1. BGC0000001.1
Source: one
Type: PKS
Table of Blast hits (query gene, subject gene, %identity, blast score, %coverage, e-value):
ctg1_1\tONE_A\t80\t1000\t103.5\t1e-50
"""
    path = tmp_path / "coverage.zip"
    with ZipFile(path, "w") as z:
        z.writestr("knownclusterblast/NODE_1_c1.txt", txt)
    bgc = SimpleNamespace(
        bgc_id="BGC001", contig="NODE_1", region_number=1,
        kcb_top="BGC0000001", products=["T1PKS"], edge_status="Interior",
    )
    parsed = parse_mibig_gene_map(path, [bgc])
    hit = parsed["per_gene_mibig"]["BGC001"][0]
    assert hit["pct_coverage"] == 103.5
    assert hit["pct_coverage_interpretation"] == 100.0
    assert hit["coverage_qc_flag"] == "SOURCE_GT100_CAPPED_FOR_INTERPRETATION"
    convergence = build_mibig_convergence(
        parsed["per_gene_mibig"], parsed["query_gene_counts"], {"BGC001": bgc}
    )
    assert convergence[0]["median_pct_coverage"] == 103.5
    assert convergence[0]["median_pct_coverage_interpretation"] == 100.0
    assert convergence[0]["coverage_qc_flag"] == "SOURCE_GT100_CAPPED_FOR_INTERPRETATION"


def test_convergence_reports_dominance_against_runner_up():
    rows = []
    for index in range(8):
        rows.append({
            "query_gene": f"q{index}", "subject_gene": f"a{index}",
            "mibig_accession": "BGC0000001", "mibig_compound": "family one",
            "reference_type": "PKS", "reference_rank": 1,
            "pct_identity": 75, "pct_coverage": 95, "blast_score": 500,
        })
    for index in range(3):
        rows.append({
            "query_gene": f"q{index}", "subject_gene": f"b{index}",
            "mibig_accession": "BGC0000002", "mibig_compound": "family two",
            "reference_type": "PKS", "reference_rank": 2,
            "pct_identity": 70, "pct_coverage": 90, "blast_score": 400,
        })
    convergence = build_mibig_convergence(
        {"BGC001": rows},
        {"BGC001": 10},
        {"BGC001": {"products": ["T1PKS"], "edge_status": "Interior"}},
    )
    assert convergence[0]["convergence_rank"] == 1
    assert convergence[0]["dominant_reference"] is True
    assert convergence[0]["dominance_status"] == "CLEAR_DOMINANT"
    assert convergence[0]["runner_up_mibig_accession"] == "BGC0000002"
    assert convergence[0]["runner_up_distinct_query_genes"] == 3
    assert convergence[0]["dominance_gene_margin"] == 5


def test_convergence_tier_thresholds_and_class_mismatch_precedence():
    assert _convergence_tier(12, 70, 80, 0.65, 3, "CONCORDANT") == "H1_HIGH_DENSITY"
    assert _convergence_tier(8, 55, 75, 0.40, 99, "CONCORDANT") == "H2_STRONG_FAMILY"
    assert _convergence_tier(4, 40, 60, 0.01, 99, "CONCORDANT") == "H3_MULTI_GENE"
    assert _convergence_tier(2, 35, 1, 0.01, 99, "CONCORDANT") == "H4_REPEATED_SUPPORT"
    assert _convergence_tier(1, 100, 100, 1.0, 1, "CONCORDANT") == "H5_SINGLE_OR_WEAK"
    assert _convergence_tier(20, 99, 99, 1.0, 1, "DISCORDANT") == "CAUTION_CLASS_MISMATCH"


def _hits(count, identity=40):
    return [
        {
            "query_gene": f"q{index}",
            "subject_gene": f"s{index}",
            "mibig_accession": "BGC0000001",
            "pct_identity": identity,
            "blast_score": 100 - index,
        }
        for index in range(count)
    ]


def test_mibig_profile_dark_matter_classes_and_denominators():
    bgcs = {
        "BGC001": {"kcb_top": ""},
        "BGC002": {"kcb_top": ""},
        "BGC003": {"kcb_top": ""},
        "BGC004": {"kcb_top": "BGC0000001.1 | reference"},
        "BGC005": {"kcb_top": ""},
        "BGC006": {"kcb_top": ""},
    }
    profiles = build_bgc_mibig_profile(
        {
            "BGC001": _hits(2),
            "BGC002": _hits(3),
            "BGC003": _hits(5),
            # MPG-01 (v9.7.338): an anchored region now needs frac >= 0.20 to stay KNOWN_ANCHORED,
            # so give BGC004 enough recognizable genes (3/10) to keep that call meaningful.
            "BGC004": _hits(3),
            "BGC006": _hits(1, identity=29),
        },
        {
            "BGC001": 10,
            "BGC002": 10,
            "BGC003": 10,
            "BGC004": 10,
            "BGC005": 10,
            "BGC006": 10,
        },
        bgcs,
    )
    assert profiles["BGC001"]["interpretation_class"] == "TRUE_DARK_MATTER"
    assert profiles["BGC002"]["interpretation_class"] == "PARTIAL_DARK_MATTER"
    assert profiles["BGC003"]["interpretation_class"] == "INTERPRETABLE_DARK_MATTER"
    assert profiles["BGC004"]["interpretation_class"] == "KNOWN_ANCHORED"
    assert profiles["BGC005"]["interpretation_class"] == "NO_MIBIG_PROTEIN_HITS"
    assert profiles["BGC006"]["recognizable_gene_count"] == 0
    assert profiles["BGC003"]["recognizable_gene_fraction"] == 0.5
    assert profiles["BGC003"]["recognizable_min_pct_identity"] == 30.0


def test_length_weighted_is_additive_and_boundary_stratified():
    bgcs = [SimpleNamespace(bgc_id="BGC001", contig="N1", start=0, end=3000, products=["NRPS"], edge_status="Full-contig"),
            SimpleNamespace(bgc_id="BGC002", contig="N2", start=0, end=30000, products=["NRPS"], edge_status="Interior")]
    rows = length_weighted_profile(bgcs)
    s = summary(rows)
    assert s["raw_regions"] == 2
    assert s["length_weighted_capacity_equivalents"] == 1.1
    assert s["full_contig_weighted"] == 0.1
    assert all(row["metric_status"] == "TRIAL_ONLY_NO_SCORING" for row in rows)


def test_length_weighted_normalizes_common_antismash_aliases():
    expected = {
        "lanthipeptide-class-i": "RiPP",
        "lanthipeptide-class-iv": "RiPP",
        "RiPP-like": "RiPP",
        "NRP-metallophore": "NRPS",
        "PKS-like": "PKS",
        "redox-cofactor": "REDOX_COFACTOR",
    }
    for product, family in expected.items():
        assert normalize_product_family(product)[0] == family
    profile = nominal_length_profile(["lanthipeptide-class-ii", "PKS-like"])
    assert profile["nominal_bp"] == 30_000
    assert profile["nominal_basis_family"] == "PKS"


def test_length_weighted_uses_inclusive_coordinates_and_reports_defaults():
    bgcs = [
        SimpleNamespace(
            bgc_id="BGC001", contig="N1", start=1, end=30_000,
            products=["unknown-new-class"], edge_status="Interior",
        )
    ]
    rows = length_weighted_profile(bgcs)
    assert rows[0]["length_bp"] == 30_000
    assert rows[0]["nominal_mapping_status"] == "DEFAULT_UNMAPPED"
    assert summary(rows)["default_nominal_regions"] == 1
