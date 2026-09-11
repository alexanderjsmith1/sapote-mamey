"""test_lead_pages_no_hardcoded_root.py — H1 regression (v9.7.352).

lead_pages.py hardcoded `ROOT = "<author-workspace>"  # SAPOTE_WORKSPACE_ROOT` and derived `WCA`
from the code-tree root (a comment claimed it was WHOLE_COHORT_ANALYSIS_*), so the compound-
family / structure / ClusteredNR / nr channels resolved to the wrong base and blanked with NO
warning — even on the author's machine. Fix: env-configured resolution (no home literal) plus a
visible WARN per channel that cannot resolve (honest-blank). This pins both.
"""
import importlib
import os

import pytest


def _fresh(monkeypatch, **env):
    # reload lead_pages with a controlled environment so module-level resolution re-runs
    for k in ("MAMEY_DATA_ROOT", "MAMEY_COHORT_ANALYSIS_DIR"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    import mamey.lead_pages as lp
    return importlib.reload(lp)


def test_no_hardcoded_user_path_in_source():
    import mamey.lead_pages as lp
    src = open(lp.__file__, encoding="utf-8").read()
    assert "/Users/" not in src, "lead_pages.py must not contain an absolute /Users/... home path"


def test_unresolved_channels_emit_visible_warnings(monkeypatch):
    lp = _fresh(monkeypatch)  # no env -> nothing resolves
    warns = lp.data_channel_warnings()
    assert warns, "with no data root configured, absent channels must WARN (honest-blank)"
    blob = " ".join(warns).lower()
    assert "compound-family" in blob
    assert "clusterednr" in blob
    assert "nr divergence" in blob


def test_env_var_resolves_cohort_channel(tmp_path, monkeypatch):
    # stage a minimal cohort-analysis dir with a compound-family table
    cf_dir = tmp_path / "WHOLE_COHORT_ANALYSIS_2026-08-05" / "COMPOUND_FAMILIES"
    cf_dir.mkdir(parents=True)
    (cf_dir / "ANCHORED_BGC_COMPOUND_FAMILIES.tsv").write_text(
        "strain\tbgc_id\tanchor\tclass_concordance\nAS-1\tBGC001\tanchorX\tOK\n")
    (cf_dir / "ANCHOR_STRUCTURES.tsv").write_text(
        "anchor\tmatched_name\tinchikey\nanchorX\tfoomycin\tKEY123\n")

    lp = _fresh(monkeypatch, MAMEY_DATA_ROOT=str(tmp_path))
    # WCA resolved to the newest WHOLE_COHORT_ANALYSIS_* under the data root
    assert lp.WCA and os.path.isdir(lp.WCA)
    assert lp._CF.get(("AS-1", "BGC001")), "compound-family channel should populate from the env-resolved dir"
    # the compound-family channel is populated, so it must NOT warn for that channel
    assert not any("compound-family" in w for w in lp.data_channel_warnings())


@pytest.fixture(autouse=True)
def _restore_module():
    # leave lead_pages in its default (env-free) state for the rest of the suite
    yield
    import mamey.lead_pages as lp
    importlib.reload(lp)
