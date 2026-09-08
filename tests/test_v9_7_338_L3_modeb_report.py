"""v9.7.338 — L3 Mode-B / report / gate fixes (companion tests).

Covers, in one file, the five staged fixes:

  MB-01  §4 %id gate can finally bite — a Pfam-only §4 (gene table + BLASTp guidance prose, or
         CONFIRM sprinkled onto rows whose only digits are aa-length/coords) no longer reads as a
         BLASTp table, so EVIDENCE_GAP / BLASTP_ABSENT fire; a real bare-number-%id-under-a-%id-header
         table still passes.  [VERDICT-CHANGING]
  MB-02  narrative-slot SSOT — every openable SAPOTE marker is in SLOT_REGISTRY with a kind; the two
         deterministic-source slots (blastp_evidence, fermentation) are no longer mistaken for
         write-narrative sections.
  MB-03  claim-safety runs at compile time (not only at seal); the ecology/deep-dive section files are
         picked up by the claim-safety filename filter.
  MB-04  verify-modeb promotes BLASTP_ABSENT to ERROR when an authoritative package core count was
         available (so MB-01's restored signal actually gates); the honest DATA_REQUESTED path stays
         WARN.  [VERDICT-CHANGING]
  CONV-01 the convergence card prints the 0–100 capped coverage-interpretation, not raw >100%.
"""
import json
import types
from pathlib import Path

import pytest

import mamey.modeb_structure_gate as G
import mamey.compile_report as C
import mamey.claim_safety_gate as csg
import mamey.authored_verify as av
from mamey import modeb_cards
from mamey import judgment_store as js


# ── MB-01 ────────────────────────────────────────────────────────────────────

# The emitter's own unauthored §4: a claim-safe gene table (aa lengths, coordinates, TTA counts are
# all bare numbers) followed by the BLASTp-authoring GUIDANCE prose (which literally contains the words
# "BLASTp" and "CONFIRM / REFINE / OVERTURN"). This is what ships on every Pfam-only card.
_PFAM_ONLY_S4 = """## §4 Gene-by-gene interpretation

**Gene table** (observed, from `gene_context.jsonl`):

| Core | Locus tag | Node / contig | Start–End | Str | aa | sec_met domains | TTA | antiSMASH product |
|:---:|---|---|---|:---:|---:|---|---:|---|
| ● | `ctg13_108` | NODE_12 | 1,234–5,678 | + | 350 | PKS_KS | 2 | T1PKS |
| ● | `ctg13_109` | NODE_12 | 6,000–9,120 | − | 512 | AMP-binding | 0 | NRPS |

**Independent homology channel (REQUIRED):** author §4 AFTER the BLASTp panel exists. antiSMASH Pfam
calls are a hypothesis; reconcile each core against the BLASTp top hit (CONFIRM / REFINE / OVERTURN).
"""

# A Pfam-only §4 that CHEATS by writing a CONFIRM verdict into the table rows, but whose only numbers
# are aa lengths / coordinates — never a real percent identity. This is the residual bug MB-01 closes.
_PFAM_ONLY_FAKE_CONFIRM_S4 = """## §4 Gene-by-gene interpretation

| Core | Locus tag | aa | antiSMASH domains | note |
|:---:|---|---:|---|---|
| ● | ctg7_12 | 421 | PKS_KS | CONFIRM the modular PKS call |
| ● | ctg7_13 | 388 | PKS_KR | CONFIRM the reductive loop |
"""

# A genuine §4 grid: identity written as a BARE number under a "%id" (and "BLASTp") header — exactly
# how the shipped exemplars write it. This must keep passing or MB-01 has broken real cards.
_REAL_S4 = """## §4 Gene-by-gene evidence

| Locus | aa | antiSMASH domains | BLASTp top hit (nr) | %id | Reconciliation |
|---|---|---|---|---|---|
| ● ctg13_108 | 512 | Condensation | NRPS [Streptomyces sp.] | 71.4 | CONFIRM |
| ● ctg13_109 | 388 | AMP-binding | adenylation domain [Streptomyces sp.] | 64.2 | REFINE |
"""


def test_mb01_pfam_only_gene_table_is_not_a_blastp_table():
    """VERDICT-CHANGING: the emitter's own unauthored §4 must not satisfy the evidence gate."""
    assert G._has_blastp_table(_PFAM_ONLY_S4) is False


def test_mb01_pfam_only_flags_evidence_gap_and_blastp_absent():
    assert G._evidence_presence_findings(_PFAM_ONLY_S4)[0]["code"] == "EVIDENCE_GAP"
    codes = [f["code"] for f in G._section4_blastp_coverage_findings(_PFAM_ONLY_S4)]
    assert "BLASTP_ABSENT" in codes


def test_mb01_fake_confirm_with_only_aa_numbers_is_not_covered():
    """A CONFIRM verdict beside aa-length/coord numbers (no %id column) must NOT count as covered."""
    assert G._has_blastp_table(_PFAM_ONLY_FAKE_CONFIRM_S4) is False
    codes = [f["code"] for f in G._section4_blastp_coverage_findings(_PFAM_ONLY_FAKE_CONFIRM_S4)]
    assert "BLASTP_ABSENT" in codes


def test_mb01_real_bare_number_pctid_under_header_still_passes():
    """Control: a real bare-number %id under a %id/BLASTp header must still read as evidence."""
    assert G._has_blastp_table(_REAL_S4) is True
    assert not ({"BLASTP_ABSENT", "BLASTP_THIN"}
                & {f["code"] for f in G._section4_blastp_coverage_findings(_REAL_S4)})


def test_mb01_explicit_percent_sign_form_passes():
    md = ("## §4\n| Locus | BLASTp | %id | Recon |\n|---|---|---|---|\n"
          "| ctg1_1 ● | PKS [Streptomyces] | 88.1% | CONFIRM |\n"
          "| ctg1_2 ● | NRPS [Streptomyces] | 77.0% | CONFIRM |\n## §5\n")
    assert G._has_blastp_table(md) is True


# ── MB-02 ────────────────────────────────────────────────────────────────────

def test_mb02_slot_registry_covers_every_emitted_marker():
    # build_report emits exactly these six SAPOTE markers.
    assert set(C.SLOT_REGISTRY) == {
        "executive_summary", "layperson_guide", "ecological_synthesis",
        "priority_deep_dives", "blastp_evidence", "fermentation"}


def test_mb02_narrative_slots_view_is_the_four_writable_ones():
    assert list(C.NARRATIVE_SLOTS) == [
        "executive_summary", "layperson_guide", "ecological_synthesis", "priority_deep_dives"]
    assert C.STRICT_NARRATIVE_KEYS == tuple(C.NARRATIVE_SLOTS)
    # historical (heading, filename, prompt) tuple shape preserved for downstream importers.
    h, fn, pr = C.NARRATIVE_SLOTS["executive_summary"]
    assert h.startswith("2.") and fn.endswith("_execsummary_section.md") and pr


def test_mb02_classify_open_slots_tags_kind_per_marker():
    md = ("<!-- SAPOTE:executive_summary --> <!-- SAPOTE:blastp_evidence --> "
          "<!-- SAPOTE:fermentation -->")
    kinds = {it["key"]: it["kind"] for it in C.classify_open_slots(md)}
    assert kinds["executive_summary"] == C.SLOT_KIND_NARRATIVE
    assert kinds["blastp_evidence"] == C.SLOT_KIND_DETERMINISTIC
    assert kinds["fermentation"] == C.SLOT_KIND_DETERMINISTIC
    assert all(it["remediation"] for it in C.classify_open_slots(md))


def test_mb02_write_narrative_rejects_deterministic_slots(tmp_path):
    pkg = tmp_path / "AS-XXX" / "package"
    pkg.mkdir(parents=True)
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": "AS-XXX"}))
    res = C.write_narrative(pkg, "blastp_evidence", "some text")
    assert res["status"] == "NOT_NARRATIVE" and res["kind"] == C.SLOT_KIND_DETERMINISTIC
    assert C.write_narrative(pkg, "bogus", "x")["status"] == "UNKNOWN_SECTION"


# ── MB-03 ────────────────────────────────────────────────────────────────────

def test_mb03_candidate_filter_catches_ecology_and_deepdive_sections():
    for name in ("AS-40_ecology_section.md", "AS-40_deepdives_section.md"):
        assert csg.CANDIDATE_NAME_RE.search(name), name


def _mk_min_pkg(tmp_path, card_body):
    pkg = tmp_path / "AS-XXX" / "package"
    (pkg / "judgment").mkdir(parents=True)
    (pkg / "manifest.json").write_text(json.dumps({
        "strain_id": "AS-XXX", "taxonomy": "Streptomyces sp.", "source": "bee",
        "bundle_version": "9.7.338", "release": "PRIVATE",
        "context": {"analysis_mode": "gold"}}))
    (pkg / "manifest_short.json").write_text(json.dumps({
        "strain_id": "AS-XXX", "mamey_version": "1.9.118", "assembly_tier": "GOOD",
        "raw_bgcs": 3, "corrected_bgcs": 3, "interior_pct": 70, "mode": "gold"}))
    (pkg / "AS-XXX_4_triage_board.csv").write_text(
        "BGC_ID,contig/NODE,Class,AB_auto,Corrected_rank\nBGC001,NODE_1,NRPS,0.9,1\n")
    (pkg / "judgment" / "AS-XXX_BGC001_mode_b.md").write_text(card_body)
    (pkg / "AS-XXX_judgment_register.json").write_text(json.dumps({
        "schema_version": "1.0", "strain_id": "AS-XXX", "total_bgcs": 1, "complete_bgcs": 1,
        "bgcs": {"BGC001": {"status": "COMPLETE", "quality_tier": "FULL",
                            "mode_b_file": "judgment/AS-XXX_BGC001_mode_b.md"}}}))
    return pkg


def test_mb03_compile_report_lints_its_own_output(tmp_path, capsys):
    """A compiled report whose Mode-B card overclaims is caught at compile time (not only at seal).

    v9.7.409 (CLAUDE narrative-gates): a claim-safety finding now BLOCKS by default (rc 3, nothing
    written) — previously it was warning-only and the report shipped at rc 0. The warn-and-ship path
    is now reachable ONLY via --allow-claim-safety-warnings (see the companion test below).
    """
    pkg = _mk_min_pkg(tmp_path, "## BGC001\n\nThis pathway produces erythromycin in culture.\n")
    args = types.SimpleNamespace(package_dir=str(pkg), out=None, no_figures=True,
                                 toc_depth=1, strict=False, pdf=False,
                                 allow_claim_safety_warnings=False)
    rc = C.compile_report_command(args)
    err = capsys.readouterr().err
    assert rc == 3  # default: blocked, nothing written
    assert "claim-safety" in err and "erythromycin" in err
    assert not (pkg / "AS-XXX_compiled_report.md").exists(), \
        "default claim-safety refusal must write nothing"


def test_mb03_allow_flag_restores_warn_and_ship(tmp_path, capsys):
    """--allow-claim-safety-warnings restores the pre-.409 warn-and-ship behaviour for a draft."""
    pkg = _mk_min_pkg(tmp_path, "## BGC001\n\nThis pathway produces erythromycin in culture.\n")
    args = types.SimpleNamespace(package_dir=str(pkg), out=None, no_figures=True,
                                 toc_depth=1, strict=False, pdf=False,
                                 allow_claim_safety_warnings=True)
    rc = C.compile_report_command(args)
    err = capsys.readouterr().err
    assert rc == 0  # explicitly attested draft: written, but warned
    assert "claim-safety" in err and "erythromycin" in err
    assert (pkg / "AS-XXX_compiled_report.md").exists()


def test_mb03_strict_overrides_allow_flag(tmp_path, capsys):
    """--strict is not overridable by --allow-claim-safety-warnings: a strict compile never ships
    past claim-safety findings (rc 3, nothing written) even when the allow flag is also set."""
    pkg = _mk_min_pkg(tmp_path, "## BGC001\n\nThis pathway produces erythromycin in culture.\n")
    strain = "AS-XXX"
    for key in C.NARRATIVE_SLOTS:
        (pkg / "judgment" / C.narrative_filename(key, strain)).write_text(
            "Biosynthetic capacity consistent with this class; product identity requires isolation.\n")
    js._fermentation_path(pkg).write_text("Media: ISP2. Timepoints: 3/5/7 d. Extraction: EtOAc.\n")
    (pkg / "BLASTP_BGC_summary_all_rounds.csv").write_text(
        "bgc_id,top_titles,best_pct_identity,best_query_coverage,current_claim_level,"
        "recommended_next_action\nBGC001,NRPS [Streptomyces],71.0,88,class-level,isolate\n")
    args = types.SimpleNamespace(package_dir=str(pkg), out=None, no_figures=True,
                                 toc_depth=1, strict=True, pdf=False,
                                 allow_claim_safety_warnings=True)
    out_path = pkg / "AS-XXX_compiled_report.md"
    rc = C.compile_report_command(args)
    err = capsys.readouterr().err
    assert rc == 3, err
    assert not out_path.exists(), "strict must block claim-safety findings even with the allow flag"


def test_mb03_strict_refuses_on_claim_safety(tmp_path, capsys):
    """--strict with a clean slot set but an overclaim in the body refuses (rc 3, nothing written)."""
    pkg = _mk_min_pkg(tmp_path, "## BGC001\n\nThis pathway produces erythromycin in culture.\n")
    # fill every openable slot so the slot gate (which precedes claim-safety) does not fire first.
    strain = "AS-XXX"
    for key in C.NARRATIVE_SLOTS:
        (pkg / "judgment" / C.narrative_filename(key, strain)).write_text(
            "Biosynthetic capacity consistent with this class; product identity requires isolation.\n")
    js._fermentation_path(pkg).write_text("Media: ISP2. Timepoints: 3/5/7 d. Extraction: EtOAc.\n")
    (pkg / "BLASTP_BGC_summary_all_rounds.csv").write_text(
        "bgc_id,top_titles,best_pct_identity,best_query_coverage,current_claim_level,"
        "recommended_next_action\nBGC001,NRPS [Streptomyces],71.0,88,class-level,isolate\n")
    args = types.SimpleNamespace(package_dir=str(pkg), out=None, no_figures=True,
                                 toc_depth=1, strict=True, pdf=False)
    out_path = pkg / "AS-XXX_compiled_report.md"
    rc = C.compile_report_command(args)
    err = capsys.readouterr().err
    assert rc == 3, err
    assert not out_path.exists(), "strict claim-safety refusal must write nothing"


# ── MB-04 ────────────────────────────────────────────────────────────────────

def _verify_args(tmp_path, body="# card\n"):
    f = tmp_path / "AS-XXX_BGC001_mode_b.md"
    f.write_text(body)
    return types.SimpleNamespace(file=str(f), package=None, bgc=None, no_strict_depth=True)


def test_mb04_blastp_absent_is_error_when_package_core_count_present(tmp_path, monkeypatch):
    """VERDICT-CHANGING: verify-modeb must FAIL on a Pfam-only §4 when a real core count was available."""
    finding = {"severity": "WARN", "code": "BLASTP_ABSENT", "section": 4, "message": "pfam only"}
    monkeypatch.setattr(av, "lint_card", lambda *a, **k: [dict(finding)])
    monkeypatch.setattr(av, "_bgc_context_from_package", lambda *a, **k: {"n_core_genes": 6})
    rc = av.verify_modeb_command(_verify_args(tmp_path))
    assert rc == 1, "BLASTP_ABSENT must promote to ERROR (FAIL) when a package core count exists"


def test_mb04_blastp_absent_stays_warn_without_package_core_count(tmp_path, monkeypatch):
    finding = {"severity": "WARN", "code": "BLASTP_ABSENT", "section": 4, "message": "pfam only"}
    monkeypatch.setattr(av, "lint_card", lambda *a, **k: [dict(finding)])
    monkeypatch.setattr(av, "_bgc_context_from_package", lambda *a, **k: None)
    rc = av.verify_modeb_command(_verify_args(tmp_path))
    assert rc == 0, "card-only run (no core count) keeps BLASTP_ABSENT as an honest WARN"


def test_mb04_data_requested_stays_warn_even_with_core_count(tmp_path, monkeypatch):
    finding = {"severity": "WARN", "code": "DATA_REQUESTED", "section": 4, "message": "requested"}
    monkeypatch.setattr(av, "lint_card", lambda *a, **k: [dict(finding)])
    monkeypatch.setattr(av, "_bgc_context_from_package", lambda *a, **k: {"n_core_genes": 6})
    rc = av.verify_modeb_command(_verify_args(tmp_path))
    assert rc == 0, "the honest DATA_REQUESTED path must remain a WARN, not an ERROR"


# ── CONV-01 ──────────────────────────────────────────────────────────────────

class _Rec:
    bgc = "BGC001"; cls = "phenazine"; contig = "NODE_1"; len_kb = 30.0
    is_edge = False; ab = 10; af = 20; novelty = 5; lead_tier = "Medium"; kcb_top = ""


def _render_conv(conv_rows):
    dd = {"BGC001": {"genes": {}, "domains": []}}
    return modeb_cards.card("AS-TEST", _Rec(), dd, {}, [], {}, {}, {}, {}, {},
                            conv=conv_rows, conv_layer=True)


def test_conv01_card_prints_capped_interpretation_not_raw_over_100():
    row = {"convergence_rank": "1", "mibig_compound": "streptophenazine B",
           "mibig_accession": "BGC0002010", "convergence_tier": "H2_STRONG_FAMILY",
           "distinct_query_genes": "25", "recognizable_gene_share": "0.625",
           "median_pct_identity": "74.0", "median_pct_coverage": "102.9",
           "median_pct_coverage_interpretation": "100.0",
           "class_concordance": "CONCORDANT", "dominance_status": "CLEAR_DOMINANT"}
    md = _render_conv([row])
    assert "74.0/100.0" in md, "convergence row must print the capped 0–100 coverage"
    assert "102.9" not in md, "raw >100% coverage must not be printed"


def test_conv01_falls_back_to_raw_when_interpretation_absent():
    row = {"convergence_rank": "1", "mibig_compound": "x", "mibig_accession": "BGC0",
           "convergence_tier": "H2_STRONG_FAMILY", "distinct_query_genes": "9",
           "recognizable_gene_share": "0.5", "median_pct_identity": "74.0",
           "median_pct_coverage": "88.0",  # no interpretation field
           "class_concordance": "CONCORDANT", "dominance_status": "CLEAR_DOMINANT"}
    md = _render_conv([row])
    assert "74.0/88.0" in md
