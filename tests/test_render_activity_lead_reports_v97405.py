"""tests/test_render_activity_lead_reports_v97405.py — synthetic-fixture coverage for
tools/render_activity_lead_reports.py.

No live data: every package, triage-board row, and gene row here is authored inline. This
module imports mamey.activity_lead_report / mamey.activity_lead_genes directly (the same real
production functions the renderer consumes) to build a real leads-dir, exactly like a real
`mamey activity-leads` + `mamey activity-lead-genes` run would, rather than hand-writing CSVs
that could silently drift from the real schema.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mamey.activity_lead_genes import run as genes_run  # noqa: E402
from mamey.activity_lead_report import run as leads_run  # noqa: E402


def _load_renderer():
    spec = importlib.util.spec_from_file_location(
        "render_activity_lead_reports_v97405_test",
        ROOT / "tools" / "render_activity_lead_reports.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


R = _load_renderer()

TRIAGE_FIELDS = [
    "BGC_ID", "Contig", "Node_ID", "antiSMASH_Region", "Products",
    "Boundary", "Lead_tier_auto", "Corrected_rank", "AB_auto", "AF_auto",
    "Novelty_auto", "KCB_top", "KCB_score", "CCTT_triggers",
    "Standing_rule", "Primary_metab_flag", "Misanchor_Flag", "Mobile_element_flag",
]


def _triage_row(alias, node, region, ab, af, *, products="NRPS; T1PKS",
                 boundary="Interior", corrected="1", novelty="40"):
    return {
        "BGC_ID": alias, "Contig": node, "Node_ID": node, "antiSMASH_Region": region,
        "Products": products, "Boundary": boundary, "Lead_tier_auto": "High",
        "Corrected_rank": corrected, "AB_auto": str(ab), "AF_auto": str(af),
        "Novelty_auto": novelty, "KCB_top": "BGC0000001 / navigation only", "KCB_score": "100",
        "CCTT_triggers": "", "Standing_rule": "", "Primary_metab_flag": "",
        "Misanchor_Flag": "", "Mobile_element_flag": "",
    }


def _gene_row(tag, start, domains, role="biosynthetic context", *, bgc_id="BGC010", contig="C1"):
    return {
        "bgc_id": bgc_id, "locus_tag": tag, "contig": contig, "bgc_start": "100",
        "bgc_end": "9000", "cds_start": str(start), "cds_end": str(start + 900), "strand": "+",
        "aa_length": "300", "product_qualifier": "", "gene_function_inference": role,
        "sec_met_domains": domains, "source_gbk": f"{contig}.region001.gbk",
    }


def _write_package(runs_dir: Path, strain: str, rows: list[dict], *, genome_bp, contigs, n50,
                    gene_rows: list[dict] | None = None):
    package = runs_dir / strain / "package"
    package.mkdir(parents=True)
    with (package / f"{strain}_4_triage_board.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=TRIAGE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    (package / "manifest.json").write_text(json.dumps({
        "strain_id": strain,
        "workflow_version": "Mamey vTEST",
        "assembly": {"genome_bp": genome_bp, "contigs": contigs, "n50": n50, "gc_pct": 70.0},
    }), encoding="utf-8")
    if gene_rows:
        with (package / f"{strain}_gene_by_gene_all_bgcs.csv").open(
            "w", newline="", encoding="utf-8"
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=list(gene_rows[0]))
            writer.writeheader()
            writer.writerows(gene_rows)
    return package


@pytest.fixture
def two_strain_cohort(tmp_path):
    """AS-901: good assembly, one strong NRPS lead with a bound gene anchor.
    AS-902: very poor assembly (mostly edge BGCs), a terpene lead, no gene table at all
    (activity-lead-genes must hold it, not crash)."""
    runs = tmp_path / "runs"
    _write_package(
        runs, "AS-901",
        [
            _triage_row("BGC010", "C1", "region001", 90, 20, boundary="Interior", novelty="15"),
            _triage_row("BGC011", "C1", "region002", 30, 85, products="RiPP; lanthipeptide",
                        boundary="Interior", novelty="60"),
        ],
        genome_bp=7_200_000, contigs=40, n50=250_000,
        gene_rows=[
            _gene_row("ctg1_1", 100, "AMP-binding; Condensation", bgc_id="BGC010", contig="C1"),
            _gene_row("ctg1_2", 1200, "methyltransferase", "tailoring", bgc_id="BGC010", contig="C1"),
        ],
    )
    _write_package(
        runs, "AS-902",
        [
            _triage_row("BGC020", "C2", "region001", 40, 30, products="terpene",
                        boundary="Edge", novelty="70"),
            _triage_row("BGC021", "C2", "region002", 20, 25, products="terpene",
                        boundary="Edge", novelty="80"),
        ],
        genome_bp=6_100_000, contigs=930, n50=2_800,
        # deliberately no gene table -- activity-lead-genes must hold these loci, not crash.
    )
    leads_dir = tmp_path / "leads"
    leads_meta = leads_run(str(runs), str(leads_dir), top_n=5)
    assert leads_meta["n_rows"] > 0
    genes_run(str(leads_dir / "PER_STRAIN_ACTIVITY_LEADS.csv"), str(leads_dir), top_n=5)
    return runs, leads_dir


def test_end_to_end_markdown_has_day5_shaped_sections(tmp_path, two_strain_cohort):
    runs, leads_dir = two_strain_cohort
    result = R.render(str(runs), str(leads_dir), str(tmp_path / "out" / "REPORT"),
                       top_n_targets=5, fmt="markdown")
    md = Path(result["markdown_path"]).read_text(encoding="utf-8")

    # Tier table (assembly-quality bar).
    assert "## Assembly-quality tiers" in md
    assert "| GOOD | ≥70% |" in md
    assert "| AS-901 " in md and "GOOD" in md
    assert "| AS-902 " in md and "VERY_POOR" in md

    # Cross-strain best-targets table.
    assert "## Cross-strain best targets" in md
    assert "| Rank | Strain | Tier | Best locus | Why it ranks here | Next experiment |" in md

    # Per-strain cards with Novelty + Layperson headline + Next experiment.
    assert "### AS-901" in md and "### AS-902" in md
    assert "Layperson headline" in md and "Next experiment" in md

    # Gene-anchor breakdown present for the strain WITH a gene table, absent claims for the one without.
    assert "ctg1_1" in md  # AS-901's bound gene anchor
    assert "Core catalytic architecture supports NRPS" in md

    # Mandatory claim-safety language, verbatim banner present at least twice (top + footer).
    assert md.count("Routing priors only.") >= 2
    assert "Similarity is not identity" in md
    assert "judgment" in md.lower()

    # No fabricated compound name or structural analogue anywhere in the document.
    for forbidden in ("migrastatin", "HSAF", "crocagin", "lomofungin"):
        assert forbidden not in md


def test_render_is_deterministic(tmp_path, two_strain_cohort):
    runs, leads_dir = two_strain_cohort
    a = R.render(str(runs), str(leads_dir), str(tmp_path / "a" / "REPORT"),
                 top_n_targets=5, fmt="markdown")
    b = R.render(str(runs), str(leads_dir), str(tmp_path / "b" / "REPORT"),
                 top_n_targets=5, fmt="markdown")
    assert Path(a["markdown_path"]).read_bytes() == Path(b["markdown_path"]).read_bytes()


def test_strain_without_gene_table_is_held_not_crashed(tmp_path, two_strain_cohort):
    runs, leads_dir = two_strain_cohort
    holds = list(csv.DictReader(
        (leads_dir / "ACTIVITY_LEAD_GENE_ANCHOR_HOLDS.csv").open(newline="", encoding="utf-8")
    ))
    assert any(row["strain"] == "AS-902" for row in holds)
    # The renderer must still complete cleanly and still show AS-902's routing leads (the gene
    # layer is an enrichment, not a precondition for the routing-board portion of the report).
    result = R.render(str(runs), str(leads_dir), str(tmp_path / "out" / "REPORT"),
                       top_n_targets=5, fmt="markdown")
    md = Path(result["markdown_path"]).read_text(encoding="utf-8")
    assert "BGC020" in md or "BGC021" in md


def test_format_markdown_explicit_never_writes_pdf(tmp_path, two_strain_cohort):
    runs, leads_dir = two_strain_cohort
    result = R.render(str(runs), str(leads_dir), str(tmp_path / "out" / "REPORT"),
                       top_n_targets=5, fmt="markdown")
    assert result["pdf_path"] is None
    assert result["pdf_skipped_reason"] == "format=markdown requested explicitly"
    assert not Path(str(tmp_path / "out" / "REPORT.pdf")).exists()


def test_format_pdf_produces_a_real_pdf_when_reportlab_present(tmp_path, two_strain_cohort):
    pytest.importorskip("reportlab")
    runs, leads_dir = two_strain_cohort
    result = R.render(str(runs), str(leads_dir), str(tmp_path / "out" / "REPORT"),
                       top_n_targets=5, fmt="pdf")
    assert result["pdf_path"] is not None
    pdf_bytes = Path(result["pdf_path"]).read_bytes()
    assert pdf_bytes.startswith(b"%PDF-")


@pytest.mark.parametrize(
    "products,expected",
    [
        ("NRPS; T1PKS", "NRPS"),
        ("terpene", "terpene"),
        ("RiPP; lanthipeptide-class-i", "RiPP"),
        ("phosphonate", "phosphonate"),
        ("totally-unrecognized-token", "totally-unrecognized-token"),
    ],
)
def test_primary_class_normalization(products, expected):
    assert R._primary_class(products) == expected


def test_assembly_tier_and_corrected_bgc_match_mamey_assembly_module(tmp_path):
    """No independent tier/threshold logic -- this renderer must produce the SAME numbers
    mamey.assembly's own functions would for the same interior/edge/full-contig counts."""
    from mamey.assembly import assembly_tier, corrected_bgc_count

    runs = tmp_path / "runs"
    _write_package(
        runs, "AS-903",
        [
            _triage_row("BGC030", "C1", "region001", 10, 10, boundary="Interior"),
            _triage_row("BGC031", "C1", "region002", 10, 10, boundary="Edge"),
            _triage_row("BGC032", "C1", "region003", 10, 10, boundary="Full-contig"),
            _triage_row("BGC033", "C1", "region004", 10, 10, boundary="Interior"),
        ],
        genome_bp=8_000_000, contigs=10, n50=500_000,
    )
    rows = R.load_assembly_rows(str(runs))
    row = rows["AS-903"]
    expected_pct = 100.0 * 2 / 4
    assert row["interior_pct"] == expected_pct
    assert row["tier"] == assembly_tier(expected_pct)
    assert row["corrected_bgc"] == corrected_bgc_count(2, 1, 1)
