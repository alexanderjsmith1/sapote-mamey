"""Tests for mamey.compile_report — deterministic §13 report assembler.

Asserts the assembler (a) emits the §13 sections in the exact contractual order,
(b) fills deterministic sections from disk faithfully (no omissions, full cards),
(c) leaves only narrative sections as labelled Sapote slots, inlining any that were
pre-written, and (d) keeps the methods note claim-safe. Pure-read; no engine needed.
"""
import json
import struct
import subprocess
from types import SimpleNamespace
from pathlib import Path

import pytest

from mamey import compile_report as cr
from mamey import judgment_store as js


def _mk_pkg(tmp_path, *, cards=("BGC012", "BGC027"), with_layperson=True,
            release="PRIVATE", triage=True):
    pkg = tmp_path / "AS-XXX" / "package"
    (pkg / "judgment").mkdir(parents=True)
    (pkg / "manifest.json").write_text(json.dumps({
        "strain_id": "AS-XXX", "taxonomy": "Saccharopolyspora sp.",
        "source": "Apis honeybee / Ontario", "bundle_version": "9.7.148h",
        "release": release, "context": {"analysis_mode": "gold"}}))
    (pkg / "manifest_short.json").write_text(json.dumps({
        "strain_id": "AS-XXX", "mamey_version": "1.9.100", "status": "MAMEY_COMPLETE",
        "assembly_tier": "GOOD", "raw_bgcs": 51, "corrected_bgcs": 42.5,
        "interior_pct": 74, "mode": "gold", "n50": "412000", "contigs": "38"}))
    if triage:
        (pkg / "AS-XXX_4_triage_board.csv").write_text(
            "BGC_ID,contig/NODE,Class,Boundary,AB_auto,Corrected_rank\n"
            "BGC012,NODE_3,trans-AT PKS,Interior,0.91,1\n"
            "BGC027,NODE_7,NRPS,Interior,0.84,2\n"
            "BGC044,NODE_9,saccharide,Interior,0.30,18\n")
    # register + cards
    bgcs = {}
    for i in range(1, 52):
        bid = f"BGC{i:03d}"
        bgcs[bid] = {"status": "PENDING", "quality_tier": None}
    for bid in cards:
        bgcs[bid] = {"status": "COMPLETE", "quality_tier": "FULL",
                     "mode_b_file": f"judgment/AS-XXX_{bid}_mode_b.md"}
        (pkg / "judgment" / f"AS-XXX_{bid}_mode_b.md").write_text(
            f"## {bid} — card\n\nFull body for {bid}. " + "x" * 200 + "\n")
    (pkg / "AS-XXX_judgment_register.json").write_text(json.dumps({
        "schema_version": "1.0", "strain_id": "AS-XXX", "total_bgcs": 51,
        "complete_bgcs": len(cards), "bgcs": bgcs}))
    if with_layperson:
        (pkg / "judgment" / "AS-XXX_laypersons_section.md").write_text(
            "Plain-English layperson narrative written by Sapote.\n")
    return pkg


def test_sections_in_contractual_order(tmp_path):
    md = cr.build_report(_mk_pkg(tmp_path))
    order = ["# AS-XXX — Compiled Analysis Report", "# 2. Executive summary",
             "# 3. Layperson guide", "# 4. Assembly and strain summary",
             "# 5. Triage board", "# 6. Figures",
             "# 7. Cross-strain and ecological synthesis", "# 8. Priority lead deep-dives",
             "# 9. Complete Mode B cards", "# 10. BLASTP evidence summary",
             "# 11. Fermentation", "# 12. Wet-lab decision matrix",
             "# 13. Outstanding work", "# 14. Methods"]
    positions = [md.find(h) for h in order]
    assert all(p >= 0 for p in positions), "a required section is missing"
    assert positions == sorted(positions), "sections are out of contractual order"


def test_triage_board_includes_every_bgc(tmp_path):
    md = cr.build_report(_mk_pkg(tmp_path))
    for bid in ("BGC012", "BGC027", "BGC044"):  # incl. the downgraded saccharide
        assert bid in md, f"{bid} missing from triage board (no-omission rule)"
    assert "NODE_3" in md and "NODE_9" in md  # contig/node citation preserved


def test_mode_b_cards_included_in_full(tmp_path):
    pkg = _mk_pkg(tmp_path, cards=("BGC012", "BGC027"))
    md = cr.build_report(pkg)
    # full body (the 200-char filler) must be present, not a summary
    assert "x" * 200 in md
    assert md.count("— card") == 2


def test_prewritten_narrative_is_inlined_not_slotted(tmp_path):
    md = cr.build_report(_mk_pkg(tmp_path, with_layperson=True))
    assert "Plain-English layperson narrative written by Sapote." in md
    assert "SAPOTE:layperson_guide" not in md  # inlined, not a slot


def test_missing_narrative_left_as_labelled_slot(tmp_path):
    md = cr.build_report(_mk_pkg(tmp_path, with_layperson=False))
    assert "<!-- SAPOTE:layperson_guide -->" in md
    slots = cr.open_slots(md)
    assert "executive_summary" in slots
    assert "layperson_guide" in slots  # now a slot, since not on disk


def test_open_slots_reports_remaining_prose(tmp_path):
    md = cr.build_report(_mk_pkg(tmp_path, with_layperson=True), generate_figures=False)
    slots = cr.open_slots(md)
    # layperson inlined; §12 is deterministic; §10 has no store here -> falls back to a slot.
    # v9.7.344: `fermentation` is now a deterministic-source slot (fills from a genus/class bench
    # draft), so it no longer appears as an open narrative slot. Remaining generative slots:
    assert set(slots) == {"executive_summary", "ecological_synthesis",
                          "priority_deep_dives", "blastp_evidence"}


def test_private_tag_surfaced_on_cover(tmp_path):
    md = cr.build_report(_mk_pkg(tmp_path, release="PRIVATE"))
    assert "**PRIVATE**" in md.split("# 2.")[0]  # in the cover block


def test_pandoc_toc_frontmatter_not_handwritten(tmp_path):
    md = cr.build_report(_mk_pkg(tmp_path))
    assert md.startswith("---\n")
    assert "toc: true" in md.split("---", 2)[1]
    # must NOT contain a hand-written TOC block (the page-number-drift failure mode)
    assert "Table of Contents" not in md


def test_methods_note_is_claim_safe(tmp_path):
    md = cr.build_report(_mk_pkg(tmp_path))
    methods = md.split("# 14. Methods")[1]
    assert "capacity consistent with" in methods
    assert "similarity, not identity" in methods.lower()
    assert "extract-level" in methods
    assert "produces" not in methods.lower()  # no identity/production language


def test_degrades_without_triage_csv(tmp_path):
    md = cr.build_report(_mk_pkg(tmp_path, triage=False))
    assert "triage board CSV not found" in md  # honest blank, not fabricated table


# ── items added v9.7.148h-2: deterministic §10/§12, --strict, figure-gen ────────

def _add_blastp_store(pkg, rows=True):
    d = pkg / "blastp_evidence_store" / "cumulative"
    d.mkdir(parents=True)
    body = ("strain,bgc_id,round_ids,query_count,top_titles,best_pct_identity,"
            "best_query_coverage,tier_a_count,tier_b_count,tier_c_count,tier_d_count,"
            "current_claim_level,recommended_next_action,claim_safety\n")
    if rows:
        body += "AS-XXX,BGC012,R1,8,lydicamycin biosynthesis,79,94,3,2,1,2,class-consistent,fermentation,capacity-only\n"
    (d / "BLASTP_BGC_summary_all_rounds.csv").write_text(body)


def _real_triage(pkg):
    (pkg / "AS-XXX_4_triage_board.csv").write_text(
        "Rank,BGC_ID,Contig,Node_ID,antiSMASH_Region,AB_auto,AF_auto,Novelty_auto,"
        "Lead_tier_auto,KCB_top,Standing_rule,Corrected_rank,Primary_metab_flag\n"
        "1,BGC012,NODE_3,NODE_3,r001,0.91,0.77,HIGH,A,lydicamycin (79%),,1,\n"
        "2,BGC027,NODE_7,NODE_7,r001,0.84,0.40,MED,B,none,,2,\n"
        "18,BGC044,NODE_9,NODE_9,r001,0.30,0.10,LOW,E,streptomycin,saccharide,18,\n")


def test_blastp_section_is_deterministic_table_from_store(tmp_path):
    pkg = _mk_pkg(tmp_path)
    _add_blastp_store(pkg, rows=True)
    md = cr.build_report(pkg, generate_figures=False)
    sec = md.split("# 10.")[1].split("# 11.")[0]
    assert "BGC012" in sec and "lydicamycin biosynthesis" in sec
    assert "79" in sec
    assert "similarity, not identity" in sec.lower()
    assert "SAPOTE:blastp_evidence" not in sec  # filled, not a slot


def test_blastp_section_falls_back_to_slot_without_store(tmp_path):
    md = cr.build_report(_mk_pkg(tmp_path), generate_figures=False)
    assert "<!-- SAPOTE:blastp_evidence -->" in md  # no store -> honest slot


def test_decision_matrix_derived_with_node_labels(tmp_path):
    pkg = _mk_pkg(tmp_path)
    _real_triage(pkg)
    md = cr.build_report(pkg, generate_figures=False)
    sec = md.split("# 12.")[1]
    # §15: node+region label, never bare
    assert "BGC012 (NODE_3 · r001)" in sec
    # strong top-rank lead -> PRIORITY ISO
    assert "PRIORITY ISO" in sec
    # saccharide -> EXCL by standing rule
    assert "EXCL" in sec
    assert "saccharide" in sec.lower()


def test_decision_excludes_standing_rule_and_primary_metab(tmp_path):
    assert cr._decision_for({"Standing_rule": "saccharide", "Corrected_rank": "5"})[0] == "EXCL"
    assert cr._decision_for({"Primary_metab_flag": "1", "Corrected_rank": "5"})[0] == "EXCL"
    assert cr._decision_for({"Downgrade": "NAPAA", "Corrected_rank": "5"})[0] == "EXCL"


def test_decision_tiers_calibrated(tmp_path):
    # strong top-rank -> PRIORITY ISO
    assert cr._decision_for({"AB_auto": "0.9", "Corrected_rank": "1", "Novelty_auto": "MED"})[0] == "PRIORITY ISO"
    # top-rank novel but moderate score -> PRIORITY ISO via novelty branch
    assert cr._decision_for({"AB_auto": "0.55", "Corrected_rank": "3", "Novelty_auto": "HIGH"})[0] == "PRIORITY ISO"
    # high score but NOT top-rank -> HIGH SEQ, not PRIORITY ISO
    assert cr._decision_for({"AB_auto": "0.85", "Corrected_rank": "9", "Novelty_auto": "MED"})[0] == "HIGH SEQ"
    # moderate -> MEDIUM ACT
    assert cr._decision_for({"AB_auto": "0.45", "Corrected_rank": "12"})[0] == "MEDIUM ACT"
    # low -> LOW
    assert cr._decision_for({"AB_auto": "0.2", "Corrected_rank": "20"})[0] == "LOW"


def test_strict_blocks_when_slots_open(tmp_path):
    pkg = _mk_pkg(tmp_path, with_layperson=False)
    md = cr.build_report(pkg, generate_figures=False)
    assert cr.open_slots(md)  # there ARE open slots
    # simulate the CLI gate decision
    class A: package_dir = str(pkg); out = str(tmp_path / "r.md"); strict = True; no_figures = True
    rc = cr.compile_report_command(A())
    assert rc == 2
    assert not (tmp_path / "r.md").exists()  # nothing written


def test_strict_passes_when_all_narrative_on_disk(tmp_path):
    pkg = _mk_pkg(tmp_path, with_layperson=True)
    _add_blastp_store(pkg, rows=True)  # §10 filled
    jd = pkg / "judgment"
    for fn in ("AS-XXX_execsummary_section.md", "AS-XXX_ecology_section.md",
               "AS-XXX_deepdives_section.md", "AS-XXX_fermentation_section.md"):
        (jd / fn).write_text("prose\n")
    md = cr.build_report(pkg, generate_figures=False)
    assert cr.open_slots(md) == []  # all narrative present
    class A: package_dir = str(pkg); out = str(tmp_path / "ok.md"); strict = True; no_figures = True
    rc = cr.compile_report_command(A())
    assert rc == 0
    assert (tmp_path / "ok.md").exists()


def test_figure_generation_is_nonblocking(tmp_path):
    # no matplotlib / no source -> must not raise, must leave an honest note
    pkg = _mk_pkg(tmp_path)
    md = cr.build_report(pkg, generate_figures=True)
    sec = md.split("# 6. Figures")[1].split("# 7.")[0]
    assert "No figures" in sec or "generated" in sec  # honest outcome, no crash


def test_bundle_version_present_passes_through(tmp_path):
    """v9.7.153 (Part-2 Finding 6): a manifest WITH bundle_version is unaffected
    by the fallback — the recorded value is used verbatim, not overridden."""
    pkg = _mk_pkg(tmp_path)  # fixture's manifest.json has bundle_version: "9.7.148h"
    md = cr.build_report(pkg)
    assert "9.7.148h" in md  # the fixture's real recorded bundle_version, untouched
    assert "(compiler; not recorded at run time)" not in md  # fallback must NOT fire


def test_bundle_version_missing_falls_back_to_active_bundle_not_bare_question_mark(tmp_path):
    """v9.7.153 (Part-2 Finding 6): a legacy manifest with no bundle_version field
    must no longer render a bare, unexplained '?'. It should fall back to the
    bundle actually doing the compiling, labelled as such."""
    pkg = _mk_pkg(tmp_path)
    man_path = pkg / "manifest.json"
    man = json.loads(man_path.read_text())
    del man["bundle_version"]  # simulate a pre-bundle_version-field legacy manifest
    man_path.write_text(json.dumps(man))

    md = cr.build_report(pkg)
    from mamey import BUNDLE_VERSION
    assert BUNDLE_VERSION in md
    assert "(compiler; not recorded at run time)" in md


def test_pdf_preparation_rejects_upscaled_low_resolution_raster(tmp_path):
    png = tmp_path / "screen-thumbnail.png"
    png.write_bytes(
        b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", 800, 600)
    )
    md = "![generic heatmap](screen-thumbnail.png)\n"
    with pytest.raises(ValueError, match="FIGURE_EFFECTIVE_DPI_INSUFFICIENT"):
        cr._prepare_publication_artwork(md, tmp_path, profile="DOUBLE_COLUMN")
    assert not list(tmp_path.glob("*.render.md"))


def test_pdf_preparation_preserves_suitable_vector_artwork(tmp_path, monkeypatch):
    svg = tmp_path / "tree.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="360">'
        '<path d="M0 0 L10 10"/><text x="2" y="8">generic tip</text></svg>',
        encoding="utf-8",
    )

    def fake_svg_to_pdf(source, destination):
        return True

    monkeypatch.setattr(cr, "_svg_to_pdf", fake_svg_to_pdf)
    gated, receipt = cr._prepare_publication_artwork(
        "![generic tree](tree.svg)\n", tmp_path, profile="SINGLE_COLUMN"
    )
    assert "tree.svg.vector.pdf" in gated
    assert "tree.svg.publication.png" not in gated
    assert receipt["vector_preserved"] == 1
    assert receipt["publication_raster_fallbacks"] == 0
    assert receipt["artwork_receipts"][0]["live_text"] is True


def test_embedded_pdf_qa_requires_embedded_fonts_and_surviving_plot_text(monkeypatch, tmp_path):
    monkeypatch.setattr("shutil.which", lambda executable: f"/fixture/{executable}")

    def completed(command, **kwargs):
        if command[0] == "pdffonts":
            return SimpleNamespace(stdout="header\nrule\nFixtureFont Type1 Unicode yes no yes 1 0\n")
        if command[0] == "pdftotext":
            return SimpleNamespace(stdout="generic tip label\n")
        raise AssertionError(command)

    monkeypatch.setattr(subprocess, "run", completed)
    receipt = cr._verify_compiled_pdf_artwork(
        tmp_path / "not-created.pdf",
        {"vector_preserved": 1, "artwork_receipts": [{
            "artwork_type": "VECTOR_SVG", "live_text_probes": ["generic tip label"],
        }]},
    )
    assert receipt["vector_fonts"] == "EMBEDDED"
    assert receipt["live_text_probe"] == "VERIFIED"


def test_embedded_pdf_qa_rejects_low_effective_raster_dpi(monkeypatch, tmp_path):
    monkeypatch.setattr("shutil.which", lambda executable: f"/fixture/{executable}")
    listing = "header\nrule\n1 0 image 800 600 rgb 3 8 image no 1 0 111 111 10K 1%\n"
    monkeypatch.setattr(subprocess, "run", lambda command, **kwargs: SimpleNamespace(stdout=listing))
    with pytest.raises(ValueError, match="FIGURE_EMBED_EFFECTIVE_DPI_INSUFFICIENT"):
        cr._verify_compiled_pdf_artwork(
            tmp_path / "not-created.pdf",
            {"vector_preserved": 0, "artwork_receipts": [{"artwork_type": "RASTER_PNG"}]},
        )
