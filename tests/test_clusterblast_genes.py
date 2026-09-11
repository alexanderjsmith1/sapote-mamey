"""v9.7.100 P-CBG: ClusterBlast per-gene correspondence.

Pins that the FULL hit table (query gene, subject gene, %id, blast score, %coverage) is parsed and that
the per-gene best-hit aggregation picks the highest-blast-score reference gene per query CDS. Uses the
representative AS-XXX NODE_182 (BGC013) indolocarbazole hit rows.
"""
from mamey.clusterblast_genes import _parse_hit_rows, parse_clusterblast_gene_map


# Real first rows of the AT2433-A1 block from the AS-XXX NODE_182 KnownClusterBlast TXT.
AT2433_BLOCK = """
1. BGC0000809.3
Source: AT2433-A1
Type: other:other
Number of proteins with BLAST hits to this cluster: 8
Cumulative BLAST score: 3780.0

Table of genes, locations, strands and annotations of subject cluster:

Table of Blast hits (query gene, subject gene, %identity, blast score, %coverage, e-value):
ctg182_7\tABC02790.1\t51\t1008\t99.05498281786942\t0.0
ctg182_8\tABC02793.1\t61\t473\t100.0\t1.62e-167
"""


def test_full_hit_table_retains_all_columns():
    hits = _parse_hit_rows(AT2433_BLOCK)
    assert len(hits) == 2
    core = hits[0]
    assert core.query_gene == "ctg182_7"
    assert core.subject_gene == "ABC02790.1"
    assert core.pct_identity == 51.0
    assert core.blast_score == 1008.0
    assert round(core.pct_coverage) == 99      # %coverage retained (was discarded pre-P-CBG)
    assert core.evalue == "0.0"                 # e-value retained


def test_header_and_blank_rows_skipped():
    hits = _parse_hit_rows("Table of Blast hits (query gene, subject gene):\n\nnotarow\n")
    assert hits == []


class _B:
    def __init__(self, bgc_id, contig, region_number):
        self.bgc_id = bgc_id
        self.contig = contig
        self.region_number = region_number


def test_per_gene_best_hit_picks_highest_blast_score(tmp_path):
    import zipfile
    txt = ("ClusterBlast scores for NODE_182_length_13430_cov_62.880327\n\n"
           ">>\n1. BGC0000809.3\nSource: AT2433-A1\nType: other:other\n"
           "Number of proteins with BLAST hits to this cluster: 1\nCumulative BLAST score: 1008.0\n\n"
           "Table of Blast hits (query gene, subject gene, %identity, blast score, %coverage, e-value):\n"
           "ctg182_7\tABC02790.1\t51\t1008\t99.0\t0.0\n\n"
           ">>\n2. NZ_LAXD01000001\nSource: Carbonactinospora\nType: other\n"
           "Number of proteins with BLAST hits to this cluster: 1\nCumulative BLAST score: 1117.0\n\n"
           "Table of Blast hits (query gene, subject gene, %identity, blast score, %coverage, e-value):\n"
           "ctg182_7\tLI90_RS08865\t55\t1117\t99.0\t0.0\n")
    z = tmp_path / "as.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("knownclusterblast/NODE_182_length_13430_cov_62.880327_c1.txt", txt)
    bgcs = [_B("BGC013", "NODE_182_length_13430_cov_62.880327", 1)]
    out = parse_clusterblast_gene_map(str(z), bgcs, top_refs=5)
    assert out["status"] == "PASS"
    pg = out["per_gene_best_hit"]["BGC013"]
    assert len(pg) == 1
    # ctg182_7 appears in both references; best hit is the higher blast score (1117, Carbonactinospora).
    assert pg[0]["query_gene"] == "ctg182_7"
    assert pg[0]["blast_score"] == 1117.0
    assert pg[0]["subject_gene"] == "LI90_RS08865"


# ── DB-kind classification + functional complementarity (v9.7.100 P-CBDB) ────────────────
from mamey.rggmci import _classify_db_kind
from mamey.clusterblast_genes import (functional_profile_from_gene_context,
                                       rescue_functional_complementarity, _core_fraction)


def test_db_kind_classifier_order_matters():
    # 'knownclusterblast' and 'subclusterblast' both contain 'clusterblast' — order must disambiguate.
    assert _classify_db_kind("knownclusterblast/NODE_2_c1.txt") == "knownclusterblast"
    assert _classify_db_kind("subclusterblast/NODE_2_c1.txt") == "subclusterblast"
    assert _classify_db_kind("clusterblast/NODE_2_c1.txt") == "clusterblast"


def test_functional_profile_role_counts():
    gc = {"BGC01": [
        {"gene_kind": "biosynthetic", "gene_functions": "lanthipeptide", "sec_met_domains": ["LANC_like"]},
        {"gene_kind": "biosynthetic-additional", "gene_functions": "", "sec_met_domains": ["p450"]},
        {"gene_kind": "transport", "gene_functions": "ABC transporter", "sec_met_domains": []},
        {"gene_kind": "regulatory", "gene_functions": "TetR regulator", "sec_met_domains": []},
        {"gene_kind": "", "gene_functions": "", "sec_met_domains": []},
    ]}
    prof = functional_profile_from_gene_context(gc)["BGC01"]
    assert prof["core"] == 1
    assert prof["tailoring"] == 1
    assert prof["transport"] == 1
    assert prof["regulatory"] == 1
    assert prof["has_core"] is True


def test_complementary_needs_core_fraction_asymmetry():
    # Core-rich fragment (high core fraction) + accessory-dominated fragment (low) -> COMPLEMENTARY.
    core = {"core": 8, "tailoring": 1, "transport": 0, "regulatory": 1, "has_core": True,
            "roles_present": ["core", "tailoring", "regulatory"]}
    acc = {"core": 1, "tailoring": 8, "transport": 3, "regulatory": 2, "has_core": True,
           "roles_present": ["core", "tailoring", "transport", "regulatory"]}
    res = rescue_functional_complementarity(core, acc)
    assert res["functional_rescue_class"] == "COMPLEMENTARY"
    assert round(_core_fraction(acc), 2) <= 0.30


def test_both_core_rich_is_paralog_not_split():
    # Two core-rich fragments with similar fraction -> BOTH_CORE (paralog), not a split.
    a = {"core": 6, "tailoring": 3, "transport": 1, "regulatory": 1, "has_core": True, "roles_present": ["core"]}
    b = {"core": 7, "tailoring": 4, "transport": 1, "regulatory": 2, "has_core": True, "roles_present": ["core"]}
    res = rescue_functional_complementarity(a, b)
    assert res["functional_rescue_class"] == "BOTH_CORE"


def test_not_all_pairs_are_both_core():
    # Regression for the all-BOTH_CORE bug: a clearly asymmetric pair must NOT classify BOTH_CORE.
    core = {"core": 10, "tailoring": 1, "transport": 0, "regulatory": 0, "has_core": True, "roles_present": ["core"]}
    acc = {"core": 1, "tailoring": 12, "transport": 4, "regulatory": 3, "has_core": True, "roles_present": ["tailoring"]}
    assert rescue_functional_complementarity(core, acc)["functional_rescue_class"] != "BOTH_CORE"
