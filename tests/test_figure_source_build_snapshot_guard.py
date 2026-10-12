"""Source-bundle builds require fresh output and exact parsed widget provenance.

Only synthetic saved inputs and fake hooks are used; no biological search or plotting.
"""
from __future__ import annotations

import hashlib
import json
import zipfile

import pytest

from mamey.interactive_figures import figure_source_bundle as fs


def _seed(tmp_path):
    package = tmp_path / "SYNTHETIC.zip"
    with zipfile.ZipFile(package, "w"):
        pass
    widget = tmp_path / "widget.json"
    widget.write_text(json.dumps({"strains": {"SYNTHETIC": {
        "package": package.name, "bgcRows": 0, "machineryGenes": 0,
        "governance": "GOVERNED", "classes": {}, "machinery": {},
    }}}), encoding="utf-8")
    return widget, package


def _tree(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


@pytest.mark.parametrize("prior_success", [False, True])
def test_existing_source_directory_is_refused_without_touching_prior_artifacts(tmp_path, monkeypatch, prior_success):
    widget, _ = _seed(tmp_path)
    out = tmp_path / "sources"
    out.mkdir()
    if prior_success:
        (out / "SOURCE_BUNDLE_RECEIPT.json").write_text('{"status": "PASS", "historical": true}\n')
        (out / "BGC_RECORDS.csv").write_text("old\nsource\n")
        (out / "unique_evidence.txt").write_bytes(b"retain exactly")
    before = _tree(out)
    def unexpected_package_read(*args, **kwargs):
        pytest.fail("existing destination must refuse before any package is read")
    monkeypatch.setattr(fs.zipfile, "ZipFile", unexpected_package_read)
    with pytest.raises(ValueError, match="FIGURE_SOURCE_OUTPUT_EXISTS"):
        fs.build_source_bundle(widget, tmp_path, out)
    assert _tree(out) == before


def test_existing_source_output_file_is_refused_without_overwrite(tmp_path):
    widget, _ = _seed(tmp_path)
    out = tmp_path / "sources"
    out.write_bytes(b"existing file")
    with pytest.raises(ValueError, match="FIGURE_SOURCE_OUTPUT_EXISTS"):
        fs.build_source_bundle(widget, tmp_path, out)
    assert out.read_bytes() == b"existing file"


def test_widget_drift_before_table_emission_refuses_without_csv_or_receipt(tmp_path, monkeypatch):
    widget, _ = _seed(tmp_path)
    def missing_member_after_drift(*args):
        widget.write_text('{"strains": {}, "changed": true}', encoding="utf-8")
        return None
    def unexpected_table(*args, **kwargs):
        pytest.fail("changed parsed widget must refuse before table writes")
    monkeypatch.setattr(fs, "_member", missing_member_after_drift)
    monkeypatch.setattr(fs, "_write_csv", unexpected_table)
    out = tmp_path / "sources"
    with pytest.raises(ValueError, match="FIGURE_SOURCE_WIDGET_CHANGED_DURING_BUILD"):
        fs.build_source_bundle(widget, tmp_path, out)
    assert _tree(out) == {}


def test_widget_drift_during_table_emission_cannot_commit_new_receipt(tmp_path, monkeypatch):
    widget, _ = _seed(tmp_path)
    write_csv = fs._write_csv
    emitted = []
    def write_then_drift(path, rows, fields=None):
        write_csv(path, rows, fields)
        emitted.append(path.name)
        if len(emitted) == 1:
            widget.write_text('{"strains": {}, "changed": true}', encoding="utf-8")
    monkeypatch.setattr(fs, "_write_csv", write_then_drift)
    out = tmp_path / "sources"
    with pytest.raises(ValueError, match="FIGURE_SOURCE_WIDGET_CHANGED_DURING_BUILD"):
        fs.build_source_bundle(widget, tmp_path, out)
    assert emitted
    assert not (out / "SOURCE_BUNDLE_RECEIPT.json").exists()


def test_fresh_source_receipt_hashes_the_exact_widget_bytes_and_keeps_missingness(tmp_path):
    widget, _ = _seed(tmp_path)
    original = widget.read_bytes()
    out = tmp_path / "sources"
    result = fs.build_source_bundle(widget, tmp_path, out)
    assert result["source"]["widget_sha256"] == hashlib.sha256(original).hexdigest()
    assert widget.read_bytes() == original
    # The empty saved ZIP has no required members: typed issues must remain.
    assert result["status"] == "PASS_WITH_ISSUES"
    assert result["missing_required_member_count"] == len(fs.REQUIRED_SUFFIXES)
    assert next(c for c in result["machine_checks"] if c["check_id"] == "REQUIRED_MEMBER_RESOLUTION")["status"] == "ISSUE"
    assert json.loads((out / "SOURCE_BUNDLE_RECEIPT.json").read_text()) == result


def test_missing_package_stays_hard_failure_in_new_source_bundle(tmp_path):
    widget, package = _seed(tmp_path)
    package.unlink()
    result = fs.build_source_bundle(widget, tmp_path, tmp_path / "sources")
    assert result["status"] == "FAIL"
    assert result["missing_packages"] == ["SYNTHETIC"]
    assert next(c for c in result["machine_checks"] if c["check_id"] == "PACKAGE_RESOLUTION")["status"] == "FAIL"
