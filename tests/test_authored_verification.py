"""v9.7.192 — authored-output verification. Regression guard for two reported failures:
(1) a guide's gate ran on the SKELETON, so a green pass was reported over an empty template;
(2) a hand-built 5-section doc was titled "Mode B Card" though it had no §1-§30 structure.
These tests lock in that the authored verifier fails a blank guide and the naming guard refuses a
non-§ doc named Mode B."""
import os
import json
import re
import tempfile
from types import SimpleNamespace

import pytest

from mamey.bgc_guide import build_guide, render_markdown, verify_authored_guide
import mamey.authored_verify as authored_verify
from mamey.authored_verify import guard_deliverable_name

_PKG = "/data/mamey-local/work/strain_intake/runs_v184/AS-678/package"
_HAVE_PKG = os.path.isdir(_PKG)


def _write(text, suffix=".md"):
    fd, p = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    open(p, "w").write(text)
    return p


# ---- Item 1: authored-guide verifier reads the FINISHED file ----
@pytest.mark.skipif(not _HAVE_PKG, reason="AS-678 package not present in this env")
def test_blank_skeleton_fails_authored_verify():
    """The core reported failure: an unauthored skeleton must FAIL verify (it passes guide_quality_gate)."""
    skeleton = render_markdown(build_guide(_PKG, "BGC029"))
    p = _write(skeleton)
    try:
        ok, errors, _ = verify_authored_guide(p)
        assert ok is False
        assert any("residual" in e for e in errors)  # residual LAY slots caught
    finally:
        os.unlink(p)


@pytest.mark.skipif(not _HAVE_PKG, reason="AS-678 package not present in this env")
def test_authored_guide_passes():
    """A guide with every LAY slot filled with real prose passes."""
    md = render_markdown(build_guide(_PKG, "BGC029"))
    md = re.sub(r"<!-- LAY: plain-title -->", "the loading module", md)
    md = re.sub(r"<!-- LAY: one to three sentence plain-language summary for (\S+) -->",
                r"Gene \1 encodes an enzyme with a defined job in assembling the molecule; it is one "
                r"link in the pathway and its role is supported by the domains shown below.", md)
    md = re.sub(r"<!-- LAY: one-paragraph identity[^>]*-->", "This cluster builds a peptide. " * 15, md)
    md = re.sub(r"<!-- LAY: genes/proteins/domains[^>]*-->", "Genes are instructions. " * 12, md)
    md = re.sub(r"<!-- LAY: core biosynthetic logic[^>]*-->", "The logic is an assembly line. " * 12, md)
    md = re.sub(r"<!-- LAY: whole-picture read[^>]*-->", "Together this is a credible lead. " * 15, md)
    p = _write(md)
    try:
        ok, errors, _ = verify_authored_guide(p)
        assert ok is True, f"unexpected errors: {errors}"
    finally:
        os.unlink(p)


def test_missing_guide_file_fails():
    ok, errors, _ = verify_authored_guide("/nonexistent/guide.md")
    assert ok is False


# ---- Item 2: naming/write guard refuses a non-§ doc named Mode B ----
_FAKE_MODEB = """# AS-385 BGC021 Mode B Card
## 1 Engine summary
text
## 2 Interpretation
text
## 3 BLASTp evidence
## 4 Precursor peptides
## 5 Claim ceiling
"""


def test_naming_guard_refuses_handbuilt_modeb():
    p = _write(_FAKE_MODEB, suffix="_ModeB_Card.md")
    try:
        allowed, reasons = guard_deliverable_name(p)
        assert allowed is False
        assert reasons  # gives a reason
    finally:
        os.unlink(p)


def test_naming_guard_ignores_non_modeb_names():
    p = _write("just a prose summary", suffix="_summary.md")
    try:
        allowed, _ = guard_deliverable_name(p)
        assert allowed is True  # not claiming to be Mode B
    finally:
        os.unlink(p)


def test_naming_guard_missing_file_named_modeb_refused():
    allowed, reasons = guard_deliverable_name("/nope/AS-1_Mode_B_Card.md")
    assert allowed is False


# ---- v9.7.420 candidate: present-but-invalid package context is not optional absence ----
_COMPLETE_FIXTURE_ID = "TEST-001 / NODE_1 / region001 / BGC001"


def _context_package(tmp_path):
    package = tmp_path / "TEST-001" / "package"
    package.mkdir(parents=True)
    return package


def test_absent_optional_context_files_do_not_create_context_errors(tmp_path):
    ctx = authored_verify._bgc_context_from_package(_context_package(tmp_path), "BGC001")
    assert "_verification_context_findings" not in ctx


def test_malformed_present_gene_table_is_a_structured_context_error(tmp_path):
    package = _context_package(tmp_path)
    (package / "TEST-001_3_gene_by_gene_all_bgcs.csv").write_text(
        "wrong_header,also_wrong\nvalue,value\n", encoding="utf-8")
    ctx = authored_verify._bgc_context_from_package(package, "BGC001")
    findings = ctx.get("_verification_context_findings", [])
    assert any(f["code"] == "VERIFICATION_CONTEXT_MALFORMED" for f in findings), (
        f"{_COMPLETE_FIXTURE_ID}: malformed authoritative context was silently treated as absent")
    assert all(str(package) not in f["message"] for f in findings)


def test_truncated_present_gene_table_row_is_malformed_context(tmp_path):
    package = _context_package(tmp_path)
    (package / "TEST-001_3_gene_by_gene_all_bgcs.csv").write_text(
        "locus_tag,bgc_id\nNODE_1_1\n", encoding="utf-8")
    ctx = authored_verify._bgc_context_from_package(package, "BGC001")
    findings = ctx.get("_verification_context_findings", [])
    assert any(f["code"] == "VERIFICATION_CONTEXT_MALFORMED" for f in findings), (
        f"{_COMPLETE_FIXTURE_ID}: truncated authoritative row was silently discarded")


def test_unreadable_present_cds_table_is_a_structured_context_error(tmp_path, monkeypatch):
    package = _context_package(tmp_path)
    cds = package / "TEST-001_cds_table.csv"
    cds.write_text("locus_tag\nNODE_1_1\n", encoding="utf-8")
    real_open = open

    def denied(path, *args, **kwargs):
        if os.fspath(path) == os.fspath(cds):
            raise PermissionError("fixture denied")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr("builtins.open", denied)
    ctx = authored_verify._bgc_context_from_package(package, "BGC001")
    findings = ctx.get("_verification_context_findings", [])
    assert any(f["code"] == "VERIFICATION_CONTEXT_UNREADABLE" for f in findings), (
        f"{_COMPLETE_FIXTURE_ID}: unreadable authoritative context was silently treated as absent")


def test_verify_modeb_fails_closed_on_malformed_present_context(tmp_path, monkeypatch):
    package = _context_package(tmp_path)
    (package / "TEST-001_3_gene_by_gene_all_bgcs.csv").write_text(
        "wrong_header,also_wrong\nvalue,value\n", encoding="utf-8")
    card = tmp_path / "TEST-001__NODE_1__region001__BGC001_ModeB.md"
    card.write_text(f"# {_COMPLETE_FIXTURE_ID}\n", encoding="utf-8")
    report = tmp_path / "verify.json"
    monkeypatch.setattr(authored_verify, "lint_card", lambda *_a, **_k: [])
    monkeypatch.setattr(authored_verify, "_coverage_unverified_reason", lambda *_a, **_k: None)
    args = SimpleNamespace(
        file=str(card), package=str(package), bgc="BGC001", no_strict_depth=False,
        interp=False, summary_only=True, report_json=str(report),
    )
    assert authored_verify.verify_modeb_command(args) == 1
    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["status"] == "FAIL"
    assert any(f["code"] == "VERIFICATION_CONTEXT_MALFORMED" for f in data["findings"])


def test_malformed_present_panel_manifest_is_not_treated_as_no_inventory(tmp_path):
    package = _context_package(tmp_path)
    panel_dir = package / "bgc_blastp_panel"
    panel_dir.mkdir()
    (panel_dir / "TEST-001_BGC_BLASTP_PANEL_selection_manifest.csv").write_text(
        "wrong_header,also_wrong\nvalue,value\n", encoding="utf-8")
    ctx = authored_verify._bgc_context_from_package(package, "BGC001")
    findings = ctx.get("_verification_context_findings", [])
    assert any(f["code"] == "VERIFICATION_CONTEXT_MALFORMED" for f in findings), (
        f"{_COMPLETE_FIXTURE_ID}: malformed panel inventory was silently treated as absent")


def test_valid_panel_manifest_remains_admitted_without_context_error(tmp_path):
    package = _context_package(tmp_path)
    panel_dir = package / "bgc_blastp_panel"
    panel_dir.mkdir()
    (panel_dir / "TEST-001_BGC_BLASTP_PANEL_selection_manifest.csv").write_text(
        "bgc_id,locus_tag\nBGC001,NODE_1_1\n", encoding="utf-8")
    ctx = authored_verify._bgc_context_from_package(package, "BGC001")
    assert ctx["panels_present"] == {"BGC001"}
    assert "_verification_context_findings" not in ctx


def test_malformed_present_manifest_json_is_structured_context_error(tmp_path):
    package = _context_package(tmp_path)
    (package / "manifest.json").write_text("{not-json", encoding="utf-8")
    ctx = authored_verify._bgc_context_from_package(package, "BGC001")
    findings = ctx.get("_verification_context_findings", [])
    assert any(f["code"] == "VERIFICATION_CONTEXT_MALFORMED" for f in findings), (
        f"{_COMPLETE_FIXTURE_ID}: malformed manifest was silently treated as absent")


def test_valid_minimal_manifest_remains_nonfailing_context(tmp_path):
    package = _context_package(tmp_path)
    (package / "manifest.json").write_text('{"bgcs": []}\n', encoding="utf-8")
    ctx = authored_verify._bgc_context_from_package(package, "BGC001")
    assert "_verification_context_findings" not in ctx


def test_malformed_present_gene_context_jsonl_is_structured_context_error(tmp_path):
    package = _context_package(tmp_path)
    (package / "TEST-001_gene_context.jsonl").write_text(
        '{"schema_version":"gene_context/1.0"}\n{not-json\n', encoding="utf-8")
    ctx = authored_verify._bgc_context_from_package(package, "BGC001")
    findings = ctx.get("_verification_context_findings", [])
    assert any(f["code"] == "VERIFICATION_CONTEXT_MALFORMED" for f in findings), (
        f"{_COMPLETE_FIXTURE_ID}: malformed gene context was silently skipped")


def test_valid_gene_context_jsonl_binds_cds_and_tta_without_context_error(tmp_path):
    package = _context_package(tmp_path)
    (package / "TEST-001_gene_context.jsonl").write_text(
        '{"schema_version":"gene_context/1.0"}\n'
        '{"bgc_id":"BGC001","cds":[{"locus_tag":"NODE_1_1","tta_codons":1}]}\n',
        encoding="utf-8")
    ctx = authored_verify._bgc_context_from_package(package, "BGC001")
    assert ctx["cds_count"] == 1
    assert ctx["tta_by_gene"] == {"node_1_1": 1}
    assert "_verification_context_findings" not in ctx


def _write_round1_context_source(package, source_kind, *, malformed):
    if source_kind == "panel":
        panel_dir = package / "bgc_blastp_panel"
        panel_dir.mkdir()
        path = panel_dir / "TEST-001_BGC_BLASTP_PANEL_selection_manifest.csv"
        path.write_text(
            "wrong_header\nvalue\n" if malformed else "bgc_id\nBGC001\n",
            encoding="utf-8")
    elif source_kind == "manifest":
        path = package / "manifest.json"
        path.write_text("{not-json" if malformed else '{"bgcs": []}\n', encoding="utf-8")
    else:
        path = package / "TEST-001_gene_context.jsonl"
        path.write_text(
            "{not-json\n" if malformed else
            '{"bgc_id":"BGC001","cds":[{"locus_tag":"NODE_1_1"}]}\n',
            encoding="utf-8")


@pytest.mark.parametrize("source_kind", ["panel", "manifest", "gene_context"])
def test_present_malformed_round1_context_reaches_verify_modeb_report(
        tmp_path, monkeypatch, source_kind):
    package = _context_package(tmp_path)
    _write_round1_context_source(package, source_kind, malformed=True)
    card = tmp_path / "TEST-001__NODE_1__region001__BGC001_ModeB.md"
    card.write_text(f"# {_COMPLETE_FIXTURE_ID}\n", encoding="utf-8")
    report = tmp_path / f"{source_kind}_verify.json"
    monkeypatch.setattr(authored_verify, "lint_card", lambda *_a, **_k: [])
    monkeypatch.setattr(authored_verify, "_coverage_unverified_reason", lambda *_a, **_k: None)
    args = SimpleNamespace(
        file=str(card), package=str(package), bgc="BGC001", no_strict_depth=False,
        interp=False, summary_only=True, report_json=str(report),
    )
    assert authored_verify.verify_modeb_command(args) == 1, (
        f"{_COMPLETE_FIXTURE_ID}: {source_kind} corruption did not reach the CLI boundary")
    data = json.loads(report.read_text(encoding="utf-8"))
    assert any(f["code"] == "VERIFICATION_CONTEXT_MALFORMED" for f in data["findings"])


@pytest.mark.parametrize("source_kind", ["panel", "manifest", "gene_context"])
def test_valid_round1_context_preserves_real_structural_refusal(
        tmp_path, monkeypatch, source_kind):
    package = _context_package(tmp_path)
    _write_round1_context_source(package, source_kind, malformed=False)
    card = tmp_path / "TEST-001__NODE_1__region001__BGC001_ModeB.md"
    card.write_text(f"# {_COMPLETE_FIXTURE_ID}\n", encoding="utf-8")
    monkeypatch.setattr(authored_verify, "lint_card", lambda *_a, **_k: [{
        "severity": "ERROR", "code": "STRUCTURAL_REFUSAL", "section": 1,
        "message": "generic fixture remains structurally refused",
    }])
    monkeypatch.setattr(authored_verify, "_coverage_unverified_reason", lambda *_a, **_k: None)
    args = SimpleNamespace(
        file=str(card), package=str(package), bgc="BGC001", no_strict_depth=False,
        interp=False, summary_only=True, report_json=None,
    )
    assert authored_verify.verify_modeb_command(args) == 1
