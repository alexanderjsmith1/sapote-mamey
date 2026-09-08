"""Re-folded guard tests for mamey/render_brief.py.

v9.7.141 pytest hygiene: the full synthetic package run is an integration fixture
and is intentionally executed once per module to keep the full suite feasible in
ChatGPT/tool-capped sessions.
"""
import os, glob, pathlib
import pytest
from mamey.cli import run_one_strain
from mamey import render_brief as RB

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
SYNTH = FIXTURES / "synthetic_single_contig_antismash.zip"


@pytest.fixture(scope="module")
def pkg_dir(tmp_path_factory, synthetic_single_contig_full_locus_zip):
    outdir = tmp_path_factory.mktemp("render_brief_pkg")
    res = run_one_strain(
        strain_id="BRIEF", display_name="BRIEF", input_zip=str(synthetic_single_contig_full_locus_zip), outdir=str(outdir),
        mode="full", taxonomy="", source="", bioactivity="", master_path=None, json_mode="bounded",
    )
    assert res["status"] in {"PASS", "MAMEY_COMPLETE", "MAMEY_COMPLETE_WITH_ISSUES"} or str(res.get("validator_status","")).startswith("PASS"), res
    man = glob.glob(os.path.join(str(outdir), "**", "manifest.json"), recursive=True)
    assert man, "no manifest written"
    return os.path.dirname(man[0])


def test_num_coercion():
    assert RB._num("3.5") == 3.5
    assert RB._num("") == 0.0
    assert RB._num("n/a") == 0.0
    assert RB._num(None) == 0.0


def test_release_status_private_for_as_strain():
    assert RB._release_status({"strain_id": "AS-SYNTH"}) == "PRIVATE"
    assert RB._release_status({"strain_id": "X", "display_name": "Streptomyces sp. AS-SYNTH"}) == "PRIVATE"


def test_release_status_public_default_and_passthrough():
    assert RB._release_status({"strain_id": "SID-XXX"}) == "SID-public"
    assert RB._release_status({"strain_id": "SID-XXX", "release": "PUBLIC"}) == "PUBLIC"


def test_load_facts_contract(pkg_dir):
    facts = RB.load_facts(pkg_dir)
    assert "manifest" in facts and "rows" in facts
    assert facts["release"] in ("PRIVATE", "SID-public", "PUBLIC")
    if facts["rows"]:
        r0 = facts["rows"][0]
        for k in ("rank", "bgc_id", "contig", "products", "boundary", "arch", "ab", "af", "novelty"):
            assert k in r0, k


def test_load_facts_tolerates_w9_header(pkg_dir):
    # W9 renamed Arch_Conf->Class_Conf; load_facts must still resolve Arch/Arch_Capacity (it never read Arch_Conf)
    board = glob.glob(os.path.join(pkg_dir, "*_4_triage_board.csv"))[0]
    header = open(board).readline()
    assert "Arch" in header and "Class_Conf" in header and "Arch_Conf" not in header
    facts = RB.load_facts(pkg_dir)  # must not raise on the renamed header
    assert isinstance(facts["rows"], list)


def test_render_brief_writes_pdf(pkg_dir):
    out = RB.render_brief(pkg_dir, tier="standard")
    # render_brief returns the PDF path (or writes into the package); assert a PDF exists either way
    pdfs = glob.glob(os.path.join(pkg_dir, "*.pdf")) + ([out] if out and str(out).endswith(".pdf") else [])
    assert any(os.path.exists(p) for p in pdfs), f"no brief PDF produced (returned {out})"
