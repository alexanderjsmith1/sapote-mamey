"""v9.7.156 — Bug 2: n50/contigs fall back to manifest.json["assembly"].

Vintage packages (pre-v9.7.148c) never wrote n50/contigs into
manifest_short.json; the values live in manifest.json["assembly"]. The reader
now falls back there rather than emitting a bare "?".
See PATCH_CHAT_MEMO 2026-06-30 Bug 2.
"""
import json
from pathlib import Path
from mamey.compile_report import _read_manifests


def test_n50_and_contigs_fall_back_to_manifest_assembly_dict(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({"assembly": {"n50": 288422, "contigs": 286}}))
    (tmp_path / "manifest_short.json").write_text(json.dumps({"strain_id": "AS-TEST"}))
    m = _read_manifests(tmp_path)
    assert m["n50"] == 288422
    assert m["contigs"] == 286


def test_n50_and_contigs_prefer_manifest_short_when_both_present(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({"assembly": {"n50": 288422, "contigs": 286}}))
    (tmp_path / "manifest_short.json").write_text(json.dumps({"strain_id": "AS-TEST", "n50": 412000, "contigs": 99}))
    m = _read_manifests(tmp_path)
    assert m["n50"] == 412000
    assert m["contigs"] == 99


def test_n50_contigs_bare_question_mark_when_neither_source_has_them(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({"assembly": {}}))
    (tmp_path / "manifest_short.json").write_text(json.dumps({"strain_id": "AS-TEST"}))
    m = _read_manifests(tmp_path)
    assert m["n50"] == "?" and m["contigs"] == "?"
