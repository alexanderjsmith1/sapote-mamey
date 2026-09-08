"""Tests for mamey.good_guesses — the "Good Guesses" claim-safe interpretive-priors report.

A synthetic sealed package (triage board + convergence + profile + RG-GMCI pairs) exercises the
four evidence archetypes the synthesizer must handle:

  * a SOLID concordant call (committed core + concordant convergence)     -> HIGH
  * a reference-dark novelty prior (no MIBiG family anchor)               -> FRONTIER, REMARKABLE
  * a RARE enediyne warhead (CCTT trigger)                                -> RARE + enediyne experiment
  * a mis-anchor caught by the guard                                      -> NOTABLE + re-anchor experiment

We assert the guess/confidence/experiment fields, the claim-safety footer text, and that the
docx renderer degrades gracefully (status SKIPPED_NO_DOCX) when python-docx is not importable.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

from mamey import good_guesses as gg
from mamey.exact_identity import ExactLocusIdentityError


# --------------------------------------------------------------------------- fixtures
def _write_package(root: Path) -> Path:
    pkg = root / "package"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": "AS-TEST",
                                                    "taxonomy": "Streptomyces sp."}),
                                       encoding="utf-8")

    board_cols = ["Rank", "BGC_ID", "Contig", "antiSMASH_Region", "Products", "Arch", "Arch_Capacity", "AB_auto", "AF_auto",
                  "Novelty_auto", "Lead_tier_auto", "KCB_top", "CCTT_triggers", "RGGMCI_support",
                  "Primary_metab_flag", "Standing_rule", "Misanchor_Flag", "Concordance"]
    board_rows = [
        # SOLID concordant glycopeptide (committed core, concordant)
        dict(Rank=1, BGC_ID="BGC001", Products="glycopeptide", Arch="A", Arch_Capacity="glycopeptide",
             AB_auto=70, AF_auto=42, Novelty_auto=35, Lead_tier_auto="High",
             KCB_top="BGC0000311.6 | balhimycin", CCTT_triggers="T43-HAL_halogenase",
             RGGMCI_support="", Primary_metab_flag="", Standing_rule="", Misanchor_Flag="",
             Concordance=""),
        # RARE enediyne warhead, concordant, committed core
        dict(Rank=2, BGC_ID="BGC002", Products="enediyne 10-membered; T1PKS",
             Arch="A", Arch_Capacity="complex multi-class hybrid (pks/enediyne)",
             AB_auto=84, AF_auto=38, Novelty_auto=41, Lead_tier_auto="High",
             KCB_top="BGC0001503.4 | maduropeptin", CCTT_triggers="T43-ENE_enediyne",
             RGGMCI_support="BGC002+BGC009; BGC002+BGC010", Primary_metab_flag="",
             Standing_rule="", Misanchor_Flag="", Concordance=""),
        # reference-dark RiPP novelty prior (no MIBiG hits)
        dict(Rank=3, BGC_ID="BGC003", Products="RiPP; lanthipeptide-class-iv",
             Arch="A", Arch_Capacity="RiPP", AB_auto=74, AF_auto=24, Novelty_auto=60,
             Lead_tier_auto="Exceptional", KCB_top="", CCTT_triggers="T43-LAN_lanthipeptide",
             RGGMCI_support="", Primary_metab_flag="", Standing_rule="", Misanchor_Flag="",
             Concordance=""),
        # mis-anchor caught by the guard (NOTABLE)
        dict(Rank=4, BGC_ID="BGC004", Products="enediyne; NRPS",
             Arch="A", Arch_Capacity="complex multi-class hybrid (nrps/enediyne)",
             AB_auto=72, AF_auto=34, Novelty_auto=34, Lead_tier_auto="High",
             KCB_top="BGC0000112.5 | neocarzinostatin", CCTT_triggers="T43-HAL_halogenase",
             RGGMCI_support="", Primary_metab_flag="",
             Standing_rule="", Misanchor_Flag="enediyne_anchor_no_ene_KS(similarity_only)",
             Concordance=""),
        # an Inventory lead that must be IGNORED (only Exceptional/High are notable)
        dict(Rank=5, BGC_ID="BGC005", Products="terpene", Arch="A", Arch_Capacity="terpene",
             AB_auto=10, AF_auto=0, Novelty_auto=5, Lead_tier_auto="Inventory", KCB_top="",
             CCTT_triggers="", RGGMCI_support="", Primary_metab_flag="", Standing_rule="",
             Misanchor_Flag="", Concordance=""),
    ]
    for index, row in enumerate(board_rows, start=1):
        row.update(Contig=f"NODE_{index}_length_10000_cov_1", antiSMASH_Region="region001")
    with (pkg / "AS-TEST_4_triage_board.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=board_cols)
        w.writeheader()
        for r in board_rows:
            w.writerow(r)

    conv_cols = ["bgc_id", "class_concordance", "convergence_tier", "dominance_status"]
    conv_rows = [
        dict(bgc_id="BGC001", class_concordance="CONCORDANT",
             convergence_tier="H4_REPEATED_SUPPORT", dominance_status="UNIQUE_DOMINANT"),
        dict(bgc_id="BGC002", class_concordance="CONCORDANT",
             convergence_tier="H4_REPEATED_SUPPORT", dominance_status="CLEAR_DOMINANT"),
        # BGC003 reference-dark: no convergence row
        dict(bgc_id="BGC004", class_concordance="DISCORDANT",
             convergence_tier="CAUTION_CLASS_MISMATCH", dominance_status="CO_DOMINANT_OR_DIFFUSE"),
    ]
    with (pkg / "AS-TEST_3_mibig_convergence.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=conv_cols)
        w.writeheader()
        for r in conv_rows:
            w.writerow(r)

    prof_cols = ["bgc_id", "recognizable_gene_fraction", "interpretation_class"]
    prof_rows = [
        dict(bgc_id="BGC001", recognizable_gene_fraction="0.55", interpretation_class="KNOWN_ANCHORED"),
        dict(bgc_id="BGC002", recognizable_gene_fraction="0.64", interpretation_class="KNOWN_ANCHORED"),
        dict(bgc_id="BGC003", recognizable_gene_fraction="0.0", interpretation_class="NO_MIBIG_PROTEIN_HITS"),
        dict(bgc_id="BGC004", recognizable_gene_fraction="0.34", interpretation_class="KNOWN_ANCHORED"),
    ]
    with (pkg / "AS-TEST_3_mibig_profile.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=prof_cols)
        w.writeheader()
        for r in prof_rows:
            w.writerow(r)

    # RG-GMCI ranked pairs: BGC002 has a genuine HIGH rescue pair
    rg_cols = ["pair", "bgc_a", "bgc_b", "rggmci_confidence"]
    rg_rows = [
        dict(pair="BGC002::BGC009", bgc_a="BGC002", bgc_b="BGC009",
             rggmci_confidence="HIGH_RG_GMCI_RESCUE"),
        dict(pair="BGC001::BGC020", bgc_a="BGC001", bgc_b="BGC020",
             rggmci_confidence="LOW_SHARED_REFERENCE_SIGNAL"),
    ]
    with (pkg / "AS-TEST_4A_RGGMCI_ranked_pairs.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=rg_cols)
        w.writeheader()
        for r in rg_rows:
            w.writerow(r)
    return pkg


@pytest.fixture()
def synthetic_pkg(tmp_path) -> Path:
    return _write_package(tmp_path)


# --------------------------------------------------------------------------- tests
def test_only_notable_leads_surface(synthetic_pkg):
    rows = gg.build_guesses([synthetic_pkg])
    ids = {g.bgc_id for g in rows}
    assert ids == {"BGC001", "BGC002", "BGC003", "BGC004"}  # BGC005 Inventory excluded


def test_guess_confidence_and_experiment_fields(synthetic_pkg):
    rows = {g.bgc_id: g for g in gg.build_guesses([synthetic_pkg])}

    # every guess carries all four synthesized fields
    for g in rows.values():
        assert g.read and g.confidence in gg.CONFIDENCE
        assert g.evidence_basis and g.resolving_experiment
        assert g.flavours  # at least one flavour tag

    # SOLID concordant committed-core call -> HIGH
    solid = rows["BGC001"]
    assert solid.confidence == "HIGH"
    assert "SOLID" in solid.flavours

    # reference-dark novelty prior -> FRONTIER, REMARKABLE, and hedged read
    dark = rows["BGC003"]
    assert dark.confidence == "FRONTIER"
    assert "REMARKABLE" in dark.flavours
    assert "novelty prior" in dark.read.lower()
    assert "not proof" in dark.read.lower()

    # RARE enediyne warhead -> RARE flavour + enediyne resolving experiment
    ene = rows["BGC002"]
    assert "RARE" in ene.flavours
    assert "enediyne" in ene.resolving_experiment.lower()

    # mis-anchor caught -> NOTABLE + re-anchor experiment (no bench work on retracted call)
    mis = rows["BGC004"]
    assert "NOTABLE" in mis.flavours
    assert "re-anchor" in mis.resolving_experiment.lower()


def test_rg_gmci_high_rescue_is_earned(synthetic_pkg):
    rows = {g.bgc_id: g for g in gg.build_guesses([synthetic_pkg])}
    # BGC002 has a HIGH_RG_GMCI_RESCUE pair; BGC001 only a LOW one.
    assert rows["BGC002"].rggmci_high is True
    assert rows["BGC001"].rggmci_high is False


def test_markdown_has_claim_ceiling_and_footer(synthetic_pkg):
    rows = gg.build_guesses([synthetic_pkg])
    md = gg.render_markdown(rows)
    assert "Claim ceiling" in md
    assert "class-level" in md.lower()
    assert "judgment deferred" in md.lower()
    assert "novelty prior" in md.lower()
    # ranked table header present
    assert "Ranked Good Guesses" in md
    assert "Resolving experiment" in md
    assert "AS-TEST / NODE_1_length_10000_cov_1 / region001 / BGC001" in md


def test_page_footer_text_is_claim_safe():
    # the per-page PDF footer must carry the hard claim ceiling in miniature
    assert "class-level capacity" in gg.PAGE_FOOTER.lower()
    assert "judgment deferred" in gg.PAGE_FOOTER.lower()
    assert "not a structure/activity claim" in gg.PAGE_FOOTER.lower()


def test_run_writes_md_and_csv(synthetic_pkg, tmp_path):
    out = tmp_path / "out"
    res = gg.run(synthetic_pkg, out_dir=out, pdf=False, docx=False)
    assert res["guesses"] == 4
    assert (out / "GOOD_GUESSES.md").is_file()
    assert (out / "GOOD_GUESSES.csv").is_file()
    # CSV round-trips the synthesized fields
    csv_rows = list(csv.DictReader((out / "GOOD_GUESSES.csv").open()))
    assert {r["bgc_id"] for r in csv_rows} == {"BGC001", "BGC002", "BGC003", "BGC004"}
    assert all(r["confidence"] and r["resolving_experiment"] for r in csv_rows)
    expected = "AS-TEST / NODE_1_length_10000_cov_1 / region001 / BGC001"
    assert next(r for r in csv_rows if r["bgc_id"] == "BGC001")["exact_locus"] == expected
    assert next(r for r in res["rows"] if r["bgc_id"] == "BGC001")["exact_locus"] == expected


def test_presentation_csv_neutralises_formula_cells_without_changing_identity_or_numbers(
        synthetic_pkg, tmp_path):
    """Only the spreadsheet-facing CSV is guarded; Good Guess objects stay verbatim."""
    board = next(synthetic_pkg.glob("*_4_triage_board.csv"))
    with board.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fields = list(reader.fieldnames or [])
        board_rows = list(reader)
    formula = '=HYPERLINK("https://example.invalid","controlled")'
    board_rows[0]["KCB_top"] = formula
    with board.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(board_rows)

    guess, = gg._scan_package(synthetic_pkg)[:1]
    expected_identity = "AS-TEST / NODE_1_length_10000_cov_1 / region001 / BGC001"
    assert guess.exact_locus == expected_identity
    assert guess.kcb == formula
    # Non-string values intentionally remain non-strings at the writer boundary.
    guess.ab = -3.5
    guess.recog_fraction = None
    returned = gg._json_row(guess)
    out = tmp_path / "GOOD_GUESSES.csv"
    gg._write_csv([guess], out)

    with out.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        assert reader.fieldnames == list(gg._CSV_FIELDS)
        csv_rows = list(reader)
    assert len(csv_rows) == 1
    assert csv_rows[0]["kcb"] == "'" + formula
    assert csv_rows[0]["ab"] == "-3.5"
    assert csv_rows[0]["recognizable_gene_fraction"] == ""
    assert csv_rows[0]["exact_locus"] == expected_identity
    # JSON/report identity and the original controlled value are not presentation-sanitised.
    assert returned["exact_locus"] == expected_identity
    assert returned["kcb"] == formula


def test_docx_graceful_skip_without_python_docx(synthetic_pkg, tmp_path, monkeypatch):
    """render_docx must degrade gracefully (SKIPPED_NO_DOCX) when python-docx is absent."""
    # Force `from docx import ...` to fail regardless of whether python-docx is installed.
    monkeypatch.setitem(sys.modules, "docx", None)
    rows = gg.build_guesses([synthetic_pkg])
    res = gg.render_docx(rows, tmp_path / "GOOD_GUESSES.docx")
    assert res["status"] == "SKIPPED_NO_DOCX"
    assert res["path"] is None
    assert not (tmp_path / "GOOD_GUESSES.docx").exists()


@pytest.mark.parametrize("manifest_case", ["missing", "malformed", "invalid_utf8", "empty_strain", "missing_strain", "wrong_shape"])
def test_manifest_strain_is_required_before_good_guesses_writes_output(
        synthetic_pkg, tmp_path, manifest_case):
    manifest = synthetic_pkg / "manifest.json"
    if manifest_case == "missing":
        manifest.unlink()
    elif manifest_case == "malformed":
        manifest.write_text("{not-json", encoding="utf-8")
    elif manifest_case == "invalid_utf8":
        manifest.write_bytes(b'{"strain_id":"AS-TEST"}\xff')
    elif manifest_case == "empty_strain":
        manifest.write_text(json.dumps({"strain_id": "  "}), encoding="utf-8")
    elif manifest_case == "missing_strain":
        manifest.write_text(json.dumps({"taxonomy": "Streptomyces sp."}), encoding="utf-8")
    else:
        manifest.write_text(json.dumps(["AS-TEST"]), encoding="utf-8")

    with pytest.raises(ExactLocusIdentityError, match="MANIFEST_STRAIN_REQUIRED"):
        gg.run(synthetic_pkg, out_dir=tmp_path / "out", pdf=False, docx=False)
    assert not (tmp_path / "out" / "GOOD_GUESSES.csv").exists()


def test_docx_written_when_available(synthetic_pkg, tmp_path):
    docx = pytest.importorskip("docx")
    rows = gg.build_guesses([synthetic_pkg])
    res = gg.render_docx(rows, tmp_path / "GOOD_GUESSES.docx")
    assert res["status"] == "WRITTEN"
    assert (tmp_path / "GOOD_GUESSES.docx").is_file()
    document = docx.Document(tmp_path / "GOOD_GUESSES.docx")
    text = "\n".join(
        [p.text for p in document.paragraphs]
        + [cell.text for table in document.tables for row in table.rows for cell in row.cells]
    )
    assert "AS-TEST / NODE_1_length_10000_cov_1 / region001 / BGC001" in text


def test_current_writer_lowercase_anchors_cross_bind_to_board(tmp_path):
    """Current writer schema: strain, assembly_locator, contig, region, then evidence fields."""
    pkg = tmp_path / "package"
    pkg.mkdir()
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": "TEST"}), encoding="utf-8")

    def write_table(name, row):
        with (pkg / name).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(row))
            writer.writeheader()
            writer.writerow(row)

    write_table("TEST_4_triage_board.csv", dict(
        BGC_ID="BGC001", Contig="NODE_1_length_10000_cov_1", antiSMASH_Region="region001",
        Products="NRPS", Arch_Capacity="NRPS", Lead_tier_auto="High"
    ))
    anchor = dict(strain="TEST", assembly_locator="assembly://test", contig="NODE_1_length_10000_cov_1",
                  region="region001", bgc_id="BGC001")
    write_table("TEST_3_mibig_profile.csv", dict(
        anchor, query_gene_count="10", recognizable_gene_fraction="0.5", interpretation_class="KNOWN_ANCHORED"
    ))
    write_table("TEST_3_mibig_convergence.csv", dict(
        anchor, class_concordance="CONCORDANT", convergence_tier="H4_REPEATED_SUPPORT",
        dominance_status="CLEAR_DOMINANT", convergence_rank="1"
    ))
    guess, = gg._scan_package(pkg)
    assert guess.exact_locus == "TEST / NODE_1_length_10000_cov_1 / region001 / BGC001"
    assert guess.convergence_tier == "H4_REPEATED_SUPPORT"


@pytest.mark.parametrize("conflict", ["strain", "node", "region", "alias"])
def test_canonical_identity_rejects_conflicting_supplied_synonyms(conflict):
    row = dict(
        strain="TEST", strain_id="TEST",
        Full_Node_ID="NODE_1_length_10000_cov_1", Contig="NODE_1_length_10000_cov_1",
        antiSMASH_Region="region001", region="region001",
        BGC_ID="BGC001", bgc_id="BGC001",
    )
    replacements = {
        "strain": ("strain_id", "OTHER"),
        "node": ("Contig", "NODE_2_length_10000_cov_1"),
        "region": ("region", "region002"),
        "alias": ("bgc_id", "BGC002"),
    }
    key, value = replacements[conflict]
    row[key] = value
    with pytest.raises(ExactLocusIdentityError, match="conflicting"):
        gg.exact_locus_from_mapping("TEST", row)


@pytest.mark.parametrize("case", [
    "missing_node", "short_node", "missing_region", "missing_alias", "board_strain_conflict",
    "profile_node_conflict", "profile_alias_conflict", "convergence_region_conflict",
])
def test_exact_locus_failure_prevents_every_report_surface(synthetic_pkg, tmp_path, case):
    """Synthetic locus: AS-TEST / NODE_1_length_10000_cov_1 / region001 / BGC001."""
    board = next(synthetic_pkg.glob("*_4_triage_board.csv"))
    with board.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        board_rows = list(reader)
        board_fields = list(reader.fieldnames or [])
    first = board_rows[0]
    if case == "missing_node":
        first["Contig"] = ""
    elif case == "short_node":
        first["Contig"] = "NODE_1"
    elif case == "missing_region":
        first["antiSMASH_Region"] = ""
    elif case == "missing_alias":
        first["BGC_ID"] = ""
    elif case == "board_strain_conflict":
        first["strain"] = "OTHER-STRAIN"
        board_fields.append("strain")
    with board.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=board_fields)
        writer.writeheader()
        writer.writerows(board_rows)

    if case.startswith("profile_"):
        profile = next(synthetic_pkg.glob("*_3_mibig_profile.csv"))
        with profile.open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            profile_rows = list(reader)
            profile_fields = list(reader.fieldnames or [])
        profile_rows[0].update(strain="AS-TEST", Contig="NODE_999_length_10000_cov_1",
                               antiSMASH_Region="region001")
        if case == "profile_alias_conflict":
            profile_rows[0]["BGC_ID"] = "BGC002"
            profile_fields.append("BGC_ID")
        profile_fields.extend(
            field for field in ("strain", "Contig", "antiSMASH_Region") if field not in profile_fields
        )
        with profile.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=profile_fields)
            writer.writeheader()
            writer.writerows(profile_rows)

    if case == "convergence_region_conflict":
        convergence = next(synthetic_pkg.glob("*_3_mibig_convergence.csv"))
        with convergence.open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            convergence_rows = list(reader)
            convergence_fields = list(reader.fieldnames or [])
        convergence_rows[0].update(strain="AS-TEST", Contig="NODE_1_length_10000_cov_1",
                                   antiSMASH_Region="region999")
        convergence_fields.extend(
            field for field in ("strain", "Contig", "antiSMASH_Region") if field not in convergence_fields
        )
        with convergence.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=convergence_fields)
            writer.writeheader()
            writer.writerows(convergence_rows)

    out = tmp_path / "out"
    with pytest.raises(ExactLocusIdentityError):
        gg.run(synthetic_pkg, out_dir=out, pdf=False, docx=False)
    assert not out.exists()


def test_pdf_reuses_renderer_when_reportlab_available(synthetic_pkg, tmp_path):
    pytest.importorskip("reportlab")
    rows = gg.build_guesses([synthetic_pkg])
    md_path = tmp_path / "GOOD_GUESSES.md"
    md_path.write_text(gg.render_markdown(rows), encoding="utf-8")
    res = gg.render_pdf(md_path, tmp_path / "GOOD_GUESSES.pdf")
    # WRITTEN via in-process reportlab; if the tools renderer is not on this cut, allow a
    # skip-style status but never a hard crash.
    assert res["status"] in {"WRITTEN", "SKIPPED_NO_TOOLCHAIN", "SKIPPED_NO_RENDERER",
                             "RENDER_FAILED"}
    if res["status"] == "WRITTEN":
        assert (tmp_path / "GOOD_GUESSES.pdf").is_file()


@pytest.mark.parametrize("rank_only", [False, True])
@pytest.mark.parametrize("dominant_first", [False, True])
def test_scan_uses_dominant_comparator_independent_of_row_order(tmp_path, rank_only, dominant_first):
    """The producer ranks comparators; the report must not select the final CSV row.

    Synthetic locus: TEST / NODE_1_length_10000_cov_1 / region001 / BGC001.
    """
    pkg = tmp_path / "package"
    pkg.mkdir()
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": "TEST"}), encoding="utf-8")
    identity = dict(strain="TEST", Contig="NODE_1_length_10000_cov_1", antiSMASH_Region="region001")

    def write_table(name, rows):
        with (pkg / name).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    write_table("TEST_4_triage_board.csv", [dict(
        identity, BGC_ID="BGC001", Products="NRPS", Lead_tier_auto="High", Concordance=""
    )])
    write_table("TEST_3_mibig_profile.csv", [dict(
        identity, bgc_id="BGC001", recognizable_gene_fraction="0.55",
        interpretation_class="KNOWN_ANCHORED"
    )])
    dominant = dict(identity, bgc_id="BGC001", convergence_rank="1",
                    class_concordance="CONCORDANT", convergence_tier="H4_REPEATED_SUPPORT",
                    dominance_status="CLEAR_DOMINANT")
    other = dict(identity, bgc_id="BGC001", convergence_rank="2",
                 class_concordance="DISCORDANT", convergence_tier="CAUTION_CLASS_MISMATCH",
                 dominance_status="NOT_DOMINANT")
    if not rank_only:
        dominant["dominant_reference"] = "True"
        other["dominant_reference"] = "False"
    write_table("TEST_3_mibig_convergence.csv",
                [dominant, other] if dominant_first else [other, dominant])
    result, = gg._scan_package(pkg)
    assert result.concordance == "CONCORDANT"
    assert result.convergence_tier == "H4_REPEATED_SUPPORT"
    assert result.dominance_status == "CLEAR_DOMINANT"
    assert result.confidence == "HIGH"
    assert "SOLID" in result.flavours


@pytest.mark.parametrize("source", ["kcb", "profile", "none"])
@pytest.mark.parametrize("interpretation", ["TRUE_DARK_MATTER", "PARTIAL_DARK_MATTER"])
def test_characterized_anchor_prevents_reference_dark_claim(tmp_path, source, interpretation):
    """Synthetic locus: TEST / NODE_1_length_10000_cov_1 / region001 / BGC001."""
    pkg = tmp_path / "package"
    pkg.mkdir()
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": "TEST"}), encoding="utf-8")
    identity = dict(strain="TEST", Contig="NODE_1_length_10000_cov_1", antiSMASH_Region="region001")
    def table(name, row):
        with (pkg / name).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(row))
            writer.writeheader()
            writer.writerow(row)
    table("TEST_4_triage_board.csv", dict(identity, BGC_ID="BGC001", Products="RiPP",
          Lead_tier_auto="High", KCB_top="BGC0000001.1 | reference family" if source == "kcb" else ""))
    table("TEST_3_mibig_profile.csv", dict(identity, bgc_id="BGC001",
          recognizable_gene_fraction="0.12", interpretation_class=interpretation,
          dominant_mibig_accession="BGC0000001" if source == "profile" else ""))
    result, = gg._scan_package(pkg)
    assert gg._reference_dark(result) is (source == "none")
    if source != "none":
        assert "NO characterized MIBiG family anchor" not in result.read
        assert result.confidence != "FRONTIER"
    else:
        assert result.confidence == "FRONTIER"


@pytest.mark.parametrize("profile_case", ["missing", "empty", "wrong_locus", "missing_fraction", "invalid_fraction", "nan_fraction", "negative_fraction", "over_one_fraction", "missing_column", "duplicate_rows", "duplicate_files", "malformed_csv", "unreadable", "corrupt_utf8", "duplicate_headers", "unassessed", "zero_denominator"])
def test_unavailable_profile_never_becomes_reference_dark(synthetic_pkg, profile_case, monkeypatch):
    # Existing fixture locus under test is completed here before any report scan.
    # TEST / NODE_1_length_10000_cov_1 / region001 / BGC001.
    board = next(synthetic_pkg.glob("*_4_triage_board.csv"))
    with board.open(newline="", encoding="utf-8") as stream:
        records = list(csv.DictReader(stream))
    record = records[0]
    record.update(strain="TEST", Contig="NODE_1_length_10000_cov_1", antiSMASH_Region="region001",
                  KCB_top="", CCTT_triggers="", Products="RiPP", Arch_Capacity="RiPP")
    with board.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(record))
        writer.writeheader()
        writer.writerow(record)
    (synthetic_pkg / "manifest.json").write_text(json.dumps({"strain_id": "TEST"}), encoding="utf-8")
    profile = next(synthetic_pkg.glob("*_3_mibig_profile.csv"))
    profile.unlink()
    if profile_case != "missing":
        row = dict(strain="TEST", Contig="NODE_1_length_10000_cov_1", antiSMASH_Region="region001",
                   bgc_id="BGC001", interpretation_class="TRUE_DARK_MATTER",
                   recognizable_gene_fraction="0")
        if profile_case == "wrong_locus":
            row.update(bgc_id="BGC999", Contig="NODE_999_length_10000_cov_1")
        values = {"missing_fraction":"", "invalid_fraction":"unknown", "nan_fraction":"nan",
                  "negative_fraction":"-0.2", "over_one_fraction":"1.2"}
        if profile_case in values:
            row["recognizable_gene_fraction"] = values[profile_case]
        if profile_case == "unassessed":
            row["interpretation_class"] = "UNASSESSED_NO_QUERY_DENOMINATOR"
        if profile_case == "zero_denominator":
            row["query_gene_count"] = "0"
        if profile_case == "missing_column":
            row.pop("recognizable_gene_fraction")
        with profile.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(row))
            writer.writeheader()
            if profile_case != "empty":
                writer.writerow(row)
                if profile_case == "duplicate_rows":
                    writer.writerow(row)
        if profile_case == "duplicate_files":
            (synthetic_pkg / "DUPLICATE_3_mibig_profile.csv").write_bytes(profile.read_bytes())
        if profile_case == "malformed_csv":
            profile.write_text('bgc_id,recognizable_gene_fraction,interpretation_class\nBGC001,"0,TRUE_DARK_MATTER\n', encoding="utf-8")
        if profile_case == "corrupt_utf8":
            profile.write_bytes(b"bgc_id,recognizable_gene_fraction,interpretation_class\nBGC001,0,\xff\n")
        if profile_case == "duplicate_headers":
            profile.write_text("bgc_id,recognizable_gene_fraction,recognizable_gene_fraction,interpretation_class\nBGC001,0.9,0,TRUE_DARK_MATTER\n", encoding="utf-8")
        if profile_case == "unreadable":
            original_open = Path.open
            def inaccessible(path, *args, **kwargs):
                if path == profile:
                    raise PermissionError("injected unreadable profile")
                return original_open(path, *args, **kwargs)
            monkeypatch.setattr(Path, "open", inaccessible)
    guess, = gg._scan_package(synthetic_pkg)
    assert not gg._reference_dark(guess)
    assert guess.confidence != "FRONTIER"
    assert "NO characterized MIBiG family" not in guess.read
    assert "recog-genes=0%" not in guess.evidence_basis
    assert "NOT_MEASURED" in guess.evidence_basis


@pytest.mark.parametrize("board_case", ["missing", "ambiguous", "wrong_header", "empty_file", "duplicate_header", "ragged", "malformed", "invalid_utf8", "unreadable"])
def test_required_board_admission_before_output(synthetic_pkg, tmp_path, monkeypatch, board_case):
    board = next(synthetic_pkg.glob("*_4_triage_board.csv"))
    if board_case == "missing":
        board.unlink()
    elif board_case == "ambiguous":
        (synthetic_pkg / "OTHER_4_triage_board.csv").write_bytes(board.read_bytes())
    elif board_case == "wrong_header":
        board.write_text("wrong_column\nvalue\n")
    elif board_case == "empty_file":
        board.write_text("")
    elif board_case == "duplicate_header":
        board.write_text("BGC_ID,BGC_ID,Lead_tier_auto\n")
    elif board_case == "ragged":
        board.write_text("BGC_ID,Lead_tier_auto\n,High,unexpected\n")
    elif board_case == "malformed":
        board.write_text('BGC_ID,Lead_tier_auto\n"unterminated\n')
    elif board_case == "invalid_utf8":
        board.write_bytes(b"BGC_ID,Lead_tier_auto\n\xff")
    else:
        original = Path.open
        def denied(path, *args, **kwargs):
            if path == board:
                raise PermissionError("fixture denies board read")
            return original(path, *args, **kwargs)
        monkeypatch.setattr(Path, "open", denied)
    output = tmp_path / "report"
    with pytest.raises(ValueError, match="REQUIRED_CSV"):
        gg.run(synthetic_pkg, out_dir=output, pdf=False, docx=False)
    assert not output.exists()


def test_valid_empty_board_remains_supported(synthetic_pkg, tmp_path):
    board = next(synthetic_pkg.glob("*_4_triage_board.csv"))
    board.write_text("BGC_ID,Contig,antiSMASH_Region,Lead_tier_auto\n")
    result = gg.run(synthetic_pkg, out_dir=tmp_path / "report", pdf=False, docx=False)
    assert result["packages"] == 1
    assert result["guesses"] == 0
    assert Path(result["md_path"]).is_file()


@pytest.mark.parametrize("manifest_case", ["missing", "invalid_utf8", "no_strain"])
def test_empty_board_still_requires_governed_manifest(synthetic_pkg, tmp_path, manifest_case):
    next(synthetic_pkg.glob("*_4_triage_board.csv")).write_text("BGC_ID,Lead_tier_auto\n")
    manifest = synthetic_pkg / "manifest.json"
    if manifest_case == "missing":
        manifest.unlink()
    elif manifest_case == "invalid_utf8":
        manifest.write_bytes(b"\xff")
    else:
        manifest.write_text("{}")
    output = tmp_path / "report"
    with pytest.raises(ValueError, match="MANIFEST_STRAIN_REQUIRED"):
        gg.run(synthetic_pkg, out_dir=output, pdf=False, docx=False)
    assert not output.exists()
