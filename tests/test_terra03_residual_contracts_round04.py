"""Exhaustive residual-contract controls for Terra 03 figure surfaces.

Fixtures are generic and exercise only mechanical provenance, missingness, and
observability behavior. They do not make scientific or release judgments.
"""
from __future__ import annotations

import hashlib
import json

import pytest

from mamey import cohort_figures
from mamey.cohort_figures import _load_manifest_short
from mamey.render_all_figures import _resolve_source_zip, render_all


class _BrokenLayoutEngine:
    def set(self, **_kwargs):
        raise RuntimeError("generic layout API mismatch")


class _FigureWithBrokenLayout:
    def get_layout_engine(self):
        return _BrokenLayoutEngine()


def test_layout_engine_incompatibility_is_observable_but_save_continues(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(cohort_figures, "save_figure", lambda *args, **kwargs: calls.append((args, kwargs)))

    with pytest.warns(RuntimeWarning, match="LAYOUT_ENGINE_RECT_UNAVAILABLE"):
        cohort_figures._save_pair(_FigureWithBrokenLayout(), tmp_path / "generic.png")

    assert len(calls) == 1


def _full_manifest(**overrides):
    payload = {
        "taxonomy": "Example genus",
        "bgc_counts": {"assembly_tier": "GOOD", "raw": 4, "corrected": 3.5},
    }
    payload.update(overrides)
    return payload


def test_missing_both_manifests_refuses_instead_of_inventing_zero(tmp_path):
    with pytest.raises(FileNotFoundError, match="MANIFEST_METADATA_UNAVAILABLE"):
        _load_manifest_short(str(tmp_path), "GENERIC-01")


def test_corrupt_short_warns_then_uses_valid_full_manifest(tmp_path):
    (tmp_path / "manifest_short.json").write_text("{broken", encoding="utf-8")
    (tmp_path / "manifest.json").write_text(json.dumps(_full_manifest()), encoding="utf-8")

    with pytest.warns(RuntimeWarning, match="MANIFEST_SHORT_UNREADABLE_FALLBACK"):
        observed = _load_manifest_short(str(tmp_path), "GENERIC-01")

    assert observed["raw_bgcs"] == 4
    assert observed["corrected_bgcs"] == 3.5
    assert observed["assembly_tier"] == "GOOD"


def test_corrupt_full_manifest_surfaces_when_compact_is_unavailable(tmp_path):
    (tmp_path / "manifest.json").write_text("{broken", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        _load_manifest_short(str(tmp_path), "GENERIC-01")


def test_incomplete_compact_manifest_refuses_missing_figure_fields(tmp_path):
    (tmp_path / "manifest_short.json").write_text(
        json.dumps({"raw_bgcs": 4, "assembly_tier": "GOOD"}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="MANIFEST_FIGURE_FIELDS_MISSING.*corrected_bgcs"):
        _load_manifest_short(str(tmp_path), "GENERIC-01")


def _write_source_manifest(pkg, source_locator, digest):
    (pkg / "manifest.json").write_text(
        json.dumps({"input_zip": source_locator, "input_zip_sha256": digest}),
        encoding="utf-8",
    )


def test_source_zip_uses_manifest_digest_and_portable_basename_fallback(tmp_path):
    pkg = tmp_path / "package"
    pkg.mkdir()
    source = tmp_path / "generic-input.zip"
    source.write_bytes(b"generic source bytes")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    _write_source_manifest(pkg, "/retired/machine/generic-input.zip", digest)

    assert _resolve_source_zip(pkg) == str(source)


def test_source_zip_digest_mismatch_refuses(tmp_path):
    pkg = tmp_path / "package"
    pkg.mkdir()
    source = tmp_path / "generic-input.zip"
    source.write_bytes(b"changed bytes")
    _write_source_manifest(pkg, "/retired/machine/generic-input.zip", "0" * 64)

    with pytest.raises(ValueError, match="SOURCE_ZIP_DIGEST_MISMATCH"):
        _resolve_source_zip(pkg)


def test_source_zip_without_digest_refuses_unbound_input(tmp_path):
    pkg = tmp_path / "package"
    pkg.mkdir()
    source = tmp_path / "generic-input.zip"
    source.write_bytes(b"generic source bytes")
    (pkg / "manifest.json").write_text(
        json.dumps({"input_zip": str(source)}), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="SOURCE_ZIP_DIGEST_UNBOUND"):
        _resolve_source_zip(pkg)


def test_corrupt_source_manifest_surfaces(tmp_path):
    pkg = tmp_path / "package"
    pkg.mkdir()
    (pkg / "manifest.json").write_text("{broken", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        _resolve_source_zip(pkg)


def test_unavailable_declared_source_routes_to_limited_mode_sentinel(tmp_path):
    pkg = tmp_path / "package"
    pkg.mkdir()
    _write_source_manifest(pkg, "/retired/machine/unavailable.zip", "0" * 64)
    assert _resolve_source_zip(pkg) is None


def test_render_all_refuses_corrupt_manifest_before_dispatch(tmp_path):
    (tmp_path / "manifest.json").write_text("{broken", encoding="utf-8")
    result = render_all(tmp_path, include=[])
    assert result["ok"] is False
    assert result["sets"] == {}
    assert "manifest.json unreadable" in result["error"]


def test_missing_explicit_source_zip_refuses(tmp_path):
    pkg = tmp_path / "package"
    pkg.mkdir()
    (pkg / "manifest.json").write_text("{}", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="EXPLICIT_SOURCE_ZIP_UNAVAILABLE"):
        _resolve_source_zip(pkg, str(tmp_path / "absent.zip"))
