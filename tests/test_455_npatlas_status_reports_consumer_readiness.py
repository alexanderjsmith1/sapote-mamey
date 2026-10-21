"""NP Atlas status says whether the consumer can actually use what is provisioned.

`external_data.status()` marks NP Atlas provisioned when `np_atlas.json` exists. The consumer
(`npatlas_resolver`) never reads that file; it loads only the two normalized reference files. So a
raw download alone reads "provisioned" while the consumer finds nothing, and usable references
without the raw file read "not provisioned". `provisioned` keeps its old meaning (owner migration);
`consumer_ready` now reports what the consumer's own loader finds.
"""
import json

import mamey.npatlas_resolver as npr
from mamey import external_data


def _pin(monkeypatch, d):
    # MAMEY_DATA_ROOT is a second route to `provisioned`; clear it so the host cannot leak in.
    monkeypatch.delenv("MAMEY_DATA_ROOT", raising=False)
    monkeypatch.setenv("MAMEY_NPATLAS_DIR", str(d))
    monkeypatch.setattr(npr, "_npatlas_dirs", lambda: [d])


def test_raw_download_alone_is_not_consumer_ready(tmp_path, monkeypatch):
    (tmp_path / "np_atlas.json").write_text(json.dumps([{"compound_names": "x"}]))
    _pin(monkeypatch, tmp_path)
    s = external_data.status()["npatlas"]
    assert s["provisioned"] is True           # unchanged meaning: the raw sentinel is present
    assert s["consumer_ready"] is False
    assert s["consumer_references"] == []


def test_normalized_references_without_raw_file_are_consumer_ready(tmp_path, monkeypatch):
    ref = tmp_path / "all_actinobacteria_npatlas_ref.json"
    ref.write_text(json.dumps({"compounds": [{"name": "examplemycin"}, {"name": "othermycin"}]}))
    _pin(monkeypatch, tmp_path)
    s = external_data.status()["npatlas"]
    assert s["provisioned"] is False
    assert s["consumer_ready"] is True and s["consumer_named_compounds"] == 2


def test_malformed_reference_is_reported_not_skipped(tmp_path, monkeypatch):
    (tmp_path / "all_actinobacteria_npatlas_ref.json").write_text("{not json")
    _pin(monkeypatch, tmp_path)
    s = external_data.status()["npatlas"]
    assert s["consumer_ready"] is False and len(s["consumer_unreadable"]) == 1
