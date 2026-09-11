from types import SimpleNamespace


def test_scan_lookup_marks_unreadable_scan_status_invalid():
    from mamey.output_checklist import _scan_lookup

    class Run:
        @property
        def scan_status(self):
            raise RuntimeError("scan status unavailable")

    scans, diagnostic = _scan_lookup(Run())
    assert scans == {}
    assert diagnostic == "INVALID_SCAN_STATUS: RuntimeError"


def test_checklist_keeps_invalid_manifest_visible(tmp_path):
    from mamey.output_checklist import write_output_checklist

    context = SimpleNamespace(strain_id="TEST-STRAIN")
    run = SimpleNamespace(context=context, bgcs=[], scan_status={}, source_scans=None)
    (tmp_path / "TEST-STRAIN_ANALYSIS_FORWARD.md").write_text("forward", encoding="utf-8")
    (tmp_path / "manifest.json").write_text("{not json", encoding="utf-8")

    csv_path, _ = write_output_checklist(run, tmp_path)
    text = csv_path.read_text(encoding="utf-8")
    assert "Compiled manifest for Sapote Mode B status" in text
    assert "BLOCKED_INVALID_MANIFEST: JSONDecodeError" in text


def test_compiled_report_marks_invalid_manifest_input(tmp_path):
    from mamey.compile_report import _cover, _read_manifests

    (tmp_path / "manifest.json").write_text("{not json", encoding="utf-8")
    details = _read_manifests(tmp_path)
    assert details["manifest_read_status"] == "INVALID_MANIFEST: JSONDecodeError"
    assert "Manifest input status: INVALID_MANIFEST: JSONDecodeError" in _cover(details)


def test_compiled_report_cover_accepts_legacy_metadata_without_status():
    from mamey.compile_report import _cover

    legacy = {"release": "", "strain_id": "TEST-STRAIN", "taxonomy": "unknown",
              "source": "unknown", "assembly_tier": "unknown", "interior_pct": None,
              "raw_bgcs": "?", "corrected_bgcs": "?", "mamey_version": "?",
              "bundle_version": "?"}
