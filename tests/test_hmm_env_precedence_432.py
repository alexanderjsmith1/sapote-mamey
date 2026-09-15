"""v9.7.432 — `doctor` and the scanner must agree on whether the Pfam HMM is provisioned.

Defect: mamey/external_data.py registers the `hmm` dataset under MAMEY_HMM_DIR (and
$MAMEY_DATA_ROOT/hmm), and `mamey doctor` reports "External datasets provisioned ✓ (... hmm)"
from that registry. But mamey/wheelhouse.py:resolve_hmm_database — the resolver every scanner
path actually uses (raw_antismash_triage step 5, hmm_blastp_adjudicate.resolve_hmm_db) — read
only SM_HMM_DB and in-tree paths. An operator who followed docs/PUBLIC_RELEASE_GUIDE.md §5 and set
only MAMEY_HMM_DIR got a green doctor line and zero domain hits.

Contract after the fix:
  * resolve_hmm_database honours, in order: SM_HMM_DB (file) > MAMEY_HMM_DIR (dir) >
    $MAMEY_DATA_ROOT/hmm (dir) > bundle-local 148 > addon 148 > bundle-local 35 core.
  * external_data.resolve("hmm") (which powers doctor) delegates to that same resolver, so the
    two surfaces cannot disagree.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mamey import external_data as xd  # noqa: E402
from mamey import wheelhouse as wh  # noqa: E402

_ENV = ("SM_HMM_DB", "MAMEY_HMM_DIR", "MAMEY_DATA_ROOT")


@pytest.fixture
def clean_env(monkeypatch):
    for k in _ENV:
        monkeypatch.delenv(k, raising=False)
    return monkeypatch


@pytest.fixture
def empty_bundle(tmp_path):
    """A bundle root with no Wheelhouse/ and no addon anywhere under or beside it."""
    root = tmp_path / "bundle_root" / "bundle"
    root.mkdir(parents=True)
    return root


def _hmm_dir(tmp_path, name="scanner_pfam.hmm"):
    d = tmp_path / "operator_hmm"
    d.mkdir()
    (d / name).write_text("HMMER3/f fake\n")
    return d


# ---------------------------------------------------------------- resolver honours MAMEY_HMM_DIR

def test_mamey_hmm_dir_only_is_found_by_scanner_resolver(clean_env, tmp_path, empty_bundle):
    d = _hmm_dir(tmp_path)
    clean_env.setenv("MAMEY_HMM_DIR", str(d))
    r = wh.resolve_hmm_database(empty_bundle)
    assert r["tier"] != "none", r
    assert r["path"] == str((d / "scanner_pfam.hmm").resolve())
    assert r["n_models_hint"] == 35
    assert "MAMEY_HMM_DIR" in r["reason"]


def test_mamey_hmm_dir_prefers_150_over_core(clean_env, tmp_path, empty_bundle):
    d = _hmm_dir(tmp_path)
    (d / "scanner_pfam_150.hmm").write_text("HMMER3/f fake 150\n")
    clean_env.setenv("MAMEY_HMM_DIR", str(d))
    r = wh.resolve_hmm_database(empty_bundle)
    assert r["path"].endswith("scanner_pfam_150.hmm")
    assert r["n_models_hint"] == 148


def test_mamey_data_root_hmm_subdir_is_found(clean_env, tmp_path, empty_bundle):
    data_root = tmp_path / "data_root"
    (data_root / "hmm").mkdir(parents=True)
    (data_root / "hmm" / "scanner_pfam.hmm").write_text("x")
    clean_env.setenv("MAMEY_DATA_ROOT", str(data_root))
    r = wh.resolve_hmm_database(empty_bundle)
    assert r["path"] == str((data_root / "hmm" / "scanner_pfam.hmm").resolve())
    assert "MAMEY_DATA_ROOT" in r["reason"]


def test_sm_hmm_db_wins_when_both_are_set(clean_env, tmp_path, empty_bundle):
    d = _hmm_dir(tmp_path)
    explicit = tmp_path / "explicit" / "scanner_pfam_150.hmm"
    explicit.parent.mkdir()
    explicit.write_text("y")
    clean_env.setenv("MAMEY_HMM_DIR", str(d))
    clean_env.setenv("SM_HMM_DB", str(explicit))
    r = wh.resolve_hmm_database(empty_bundle)
    assert r["path"] == str(explicit)
    assert r["tier"] == "env-override"
    assert "SM_HMM_DB" in r["reason"]


def test_mamey_hmm_dir_pointing_at_empty_dir_does_not_count(clean_env, tmp_path, empty_bundle):
    d = tmp_path / "empty"
    d.mkdir()
    clean_env.setenv("MAMEY_HMM_DIR", str(d))
    r = wh.resolve_hmm_database(empty_bundle)
    assert r["tier"] == "none"


# ---------------------------------------------------------------- doctor report == resolver

def _agree(bundle_root):
    """Return (doctor_says_provisioned, resolver_says_found, doctor_path, resolver_path)."""
    st = xd.status()["hmm"]
    r = wh.resolve_hmm_database(bundle_root)
    return st["provisioned"], r["tier"] != "none", st["path"], r["path"]


@pytest.mark.parametrize("case", ["neither", "sm_hmm_db_only", "mamey_hmm_dir_only", "both"])
def test_doctor_report_and_resolver_agree(case, clean_env, tmp_path, empty_bundle):
    # Pin both surfaces to the same empty bundle so a stray addon on the dev machine can't
    # make one of them "provisioned" through the in-tree tiers.
    clean_env.setattr(xd, "_repo_root", lambda: empty_bundle)
    clean_env.setattr(wh, "_default_bundle_root", lambda: empty_bundle)
    d = _hmm_dir(tmp_path)
    explicit = tmp_path / "explicit" / "scanner_pfam_150.hmm"
    explicit.parent.mkdir()
    explicit.write_text("y")
    if case in ("sm_hmm_db_only", "both"):
        clean_env.setenv("SM_HMM_DB", str(explicit))
    if case in ("mamey_hmm_dir_only", "both"):
        clean_env.setenv("MAMEY_HMM_DIR", str(d))

    doctor_ok, resolver_ok, doctor_path, resolver_path = _agree(empty_bundle)
    assert doctor_ok == resolver_ok, (
        f"{case}: doctor says provisioned={doctor_ok} but the scanner resolver found={resolver_ok} "
        f"(doctor path={doctor_path!r}, resolver path={resolver_path!r})"
    )
    expected = case != "neither"
    assert doctor_ok is expected
    if expected:
        # doctor reports the directory holding the file the scanner will actually open.
        assert Path(resolver_path).parent == Path(doctor_path)


def test_doctor_command_lists_hmm_when_only_mamey_hmm_dir_is_set(clean_env, tmp_path, empty_bundle):
    from mamey import cli
    clean_env.setattr(xd, "_repo_root", lambda: empty_bundle)
    clean_env.setattr(wh, "_default_bundle_root", lambda: empty_bundle)
    clean_env.setenv("MAMEY_HMM_DIR", str(_hmm_dir(tmp_path)))
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = cli.doctor_command(argparse.Namespace())
    out = buf.getvalue()
    assert rc == 0
    assert "External datasets provisioned" in out
    prov_line = next(l for l in out.splitlines() if "External datasets provisioned" in l)
    assert "hmm" in prov_line, prov_line
    assert "External dataset 'hmm' not provisioned" not in out
    # And the scanner resolver, asked the same question in the same environment, agrees.
    assert wh.resolve_hmm_database()["tier"] != "none"
