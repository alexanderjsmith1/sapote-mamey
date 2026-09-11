"""v9.7.372: finished cards require a complete channel-separated §4 BLASTp matrix."""
import mamey.modeb_structure_gate as G


ROSTER = ["ctg9_1", "ctg9_2"]
CTX = {"known_locus_tags": ROSTER, "require_complete_blastp_matrix": True}
GOOD = """## §4 Gene-by-gene interpretation

#### Complete channel-separated BLASTp matrix

| Gene | aa | NCBI nr accession + matched protein | nr id/pos/qcov | NCBI ClusteredNR accession + matched protein | ClusteredNR id/pos/qcov | local Swiss-Prot accession + matched protein | Swiss-Prot id/pos/qcov |
|---|---:|---|---|---|---|---|---|
| `ctg9_1` | 100 | WP_000001 — synthase [Streptomyces examplei] | 91.2% id / 95.0% sim / qcov 100.0% | no bound hit | no bound hit | P00001 — Reviewed synthase [Streptomyces examplei] | 42.0% id / 61.0% positives / query coverage 88.0% |
| `ctg9_2` | 200 | no bound hit | no bound hit | WP_000002 — transporter [Nocardia exemplaris] | 77.0% identity / 82.0% positives / qcov NR | no bound hit | no bound hit |

#### Source-derived architecture and bounded interpretation
| Gene | interpretation |
|---|---|
| `ctg9_1` | CONFIRM |
| `ctg9_2` | REFINE |
"""


def codes(md, ctx=CTX):
    return [x["code"] for x in G._section4_complete_blastp_matrix_findings(md, ctx)]


def test_complete_matrix_passes():
    assert codes(GOOD) == []


def test_finished_card_without_matrix_fails():
    md = "**Document state:** FINISHED_CURRENT_EVIDENCE\n## §4\n| Gene | nr |\n|---|---|\n| ctg9_1 | 91% |"
    assert codes(md, {"known_locus_tags": ROSTER}) == ["BLASTP_MATRIX_MISSING"]


def test_missing_canonical_gene_fails():
    line = "| `ctg9_2` | 200 | no bound hit | no bound hit | WP_000002 — transporter [Nocardia exemplaris] | 77.0% identity / 82.0% positives / qcov NR | no bound hit | no bound hit |\n"
    assert codes(GOOD.replace(line, "")) == ["BLASTP_MATRIX_ROSTER"]


def test_merged_channel_header_fails():
    bad = GOOD.replace("NCBI nr accession + matched protein | nr id/pos/qcov", "NCBI combined accession | combined metrics")
    assert codes(bad) == ["BLASTP_MATRIX_CHANNELS"]


def test_identity_without_similarity_and_coverage_fails():
    bad = GOOD.replace("91.2% id / 95.0% sim / qcov 100.0%", "91.2% id")
    assert codes(bad) == ["BLASTP_MATRIX_METRICS"]


def test_percentages_plus_bare_accession_in_one_cell_fail_named_match_contract():
    thin = GOOD.replace(
        "WP_000001 — synthase [Streptomyces examplei] | 91.2% id / 95.0% sim / qcov 100.0%",
        "WP_000001 | 91.2% id / 95.0% sim / qcov 100.0%",
    )
    assert codes(thin) == ["BLASTP_MATRIX_SUBJECTS"]


def test_percentage_without_paired_match_fails():
    bad = GOOD.replace(
        "WP_000001 — synthase [Streptomyces examplei] | 91.2% id / 95.0% sim / qcov 100.0%",
        "no bound hit | 91.2% id / 95.0% sim / qcov 100.0%",
    )
    assert codes(bad) == ["BLASTP_MATRIX_PAIRING"]


def test_named_match_without_organism_fails():
    bad = GOOD.replace("WP_000001 — synthase [Streptomyces examplei]", "WP_000001 — synthase")
    assert codes(bad) == ["BLASTP_MATRIX_SUBJECTS"]


def test_no_roster_cannot_certify_finished_matrix():
    assert codes(GOOD, {"require_complete_blastp_matrix": True}) == ["BLASTP_MATRIX_ROSTER_UNBOUND"]


def test_pending_is_not_a_finished_matrix_terminal_state():
    bad = GOOD.replace(
        "P00001 — Reviewed synthase [Streptomyces examplei] | 42.0% id / 61.0% positives / query coverage 88.0%",
        "pending | pending",
    )
    assert codes(bad) == ["BLASTP_MATRIX_PENDING_TERMINAL"]


def test_observed_no_significant_hit_is_a_complete_terminal_measurement():
    measured_no_hit = GOOD.replace(
        "P00001 — Reviewed synthase [Streptomyces examplei] | 42.0% id / 61.0% positives / query coverage 88.0%",
        "exact-sequence local search completed; no significant Swiss-Prot hit at E≤1e-3 | "
        "observed no-hit state; identity, BLAST positives and query coverage not applicable",
    )
    assert codes(measured_no_hit) == []


def test_observed_no_hit_pair_must_be_symmetric():
    asymmetric = GOOD.replace(
        "P00001 — Reviewed synthase [Streptomyces examplei]",
        "exact-sequence local search completed; no significant Swiss-Prot hit at E≤1e-3",
    )
    assert codes(asymmetric) == ["BLASTP_MATRIX_PAIRING"]


def test_count_first_query_coverage_is_accepted():
    count_first = GOOD.replace(
        "91.2% id / 95.0% sim / qcov 100.0%",
        "91.2% id / 95.0% sim / qcov 100/100 query residues covered (100.0% query coverage)",
    )
    assert codes(count_first) == []


def test_nonfinished_draft_is_not_forced_into_finished_profile():
    assert codes("## §4\nDraft evidence table", {}) == []
