"""The GToTree version check must always leave a row in the preflight report.

Defect (sealed v9.7.414, tools/phylo_preflight.py:205-213): the version banner was read from
`.stdout` only, and `if m:` had NO `else`. If the banner failed to parse — it moves to stderr in
several GToTree builds and wrappers, and a nonzero `GToTree -v` prints nothing at all — the E2
branch fell through emitting nothing. Likewise, if GToTree was not on PATH the whole block was
skipped and no E2 row existed either.

Concrete wrong output: `phylo_preflight` prints its checklist and writes its JSON receipt with NO
E2 row. A reader (and the JSON consumer) sees a preflight carrying no version objection, which is
exactly what a PASSING version check looks like — and the run proceeds on, say, GToTree 1.8.16,
the version the project convention (>=1.8.19) exists to keep out. E2 is listed in the module
docstring as one of the checks this tool performs; an unrun check must be VISIBLE as unknown,
never absent.

Hermetic: `subprocess` is replaced inside the module object and `_which` is stubbed; GToTree is
never executed and nothing is written.
"""
import importlib.util
import os
import subprocess
import sys
import types

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(HERE, "..", "tools")
sys.path.insert(0, TOOLS)      # phylo_preflight imports its tools-local siblings (_wbio)


def _load():
    path = os.path.join(TOOLS, "phylo_preflight.py")
    spec = importlib.util.spec_from_file_location("phylo_preflight_v415", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _env(monkeypatch, tmp_path, mod):
    """Satisfy E1/E1b so the case under test is purely about E2."""
    hmm = tmp_path / "hmm"
    hmm.mkdir(exist_ok=True)
    (hmm / "Actinobacteria.hmm").write_text("fixture", encoding="utf-8")
    monkeypatch.setenv("GToTree_HMM_dir", str(hmm))


def _fake_subprocess(mod, monkeypatch, stdout="", stderr="", returncode=0):
    def run(cmd, *a, **k):
        return types.SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)
    monkeypatch.setattr(mod, "subprocess", types.SimpleNamespace(
        run=run, TimeoutExpired=subprocess.TimeoutExpired))


def _e2(rep):
    return [i for i in rep.items if i["check"] == "E2"]


def test_unparsable_banner_still_emits_an_explicit_unknown_row(monkeypatch, tmp_path):
    mod = _load()
    _env(monkeypatch, tmp_path, mod)
    monkeypatch.setattr(mod, "_which", lambda name: f"/fixture/{name}")
    _fake_subprocess(mod, monkeypatch, stdout="", stderr="", returncode=127)
    rep = mod.Report()
    mod.check_env(rep)
    rows = _e2(rep)
    assert len(rows) == 1, (
        "E2 vanished from the report: a preflight with no version row is indistinguishable "
        "from one whose version check passed")
    assert rows[0]["status"] in ("WARN", "FAIL")
    assert "UNKNOWN" in rows[0]["message"].upper()


def test_version_banner_on_stderr_is_read(monkeypatch, tmp_path):
    mod = _load()
    _env(monkeypatch, tmp_path, mod)
    monkeypatch.setattr(mod, "_which", lambda name: f"/fixture/{name}")
    _fake_subprocess(mod, monkeypatch, stdout="", stderr="GToTree v1.8.19\n", returncode=0)
    rep = mod.Report()
    mod.check_env(rep)
    rows = _e2(rep)
    assert len(rows) == 1 and rows[0]["status"] == "PASS", rows


def test_gtotree_absent_still_emits_a_not_measured_row(monkeypatch, tmp_path):
    mod = _load()
    _env(monkeypatch, tmp_path, mod)
    monkeypatch.setattr(mod, "_which", lambda name: None)
    _fake_subprocess(mod, monkeypatch, stdout="", stderr="", returncode=0)
    rep = mod.Report()
    mod.check_env(rep)
    rows = _e2(rep)
    assert len(rows) == 1, (
        "with GToTree off PATH the E2 row disappeared entirely; the >=1.8.19 convention must be "
        "reported as UNVERIFIED, not omitted")
    assert rows[0]["status"] in ("WARN", "FAIL")


def test_old_version_is_still_warned(monkeypatch, tmp_path):
    """Regression guard: the pre-existing 1.8.16 case is unchanged."""
    mod = _load()
    _env(monkeypatch, tmp_path, mod)
    monkeypatch.setattr(mod, "_which", lambda name: f"/fixture/{name}")
    _fake_subprocess(mod, monkeypatch, stdout="GToTree v1.8.16\n", returncode=0)
    rep = mod.Report()
    mod.check_env(rep)
    rows = _e2(rep)
    assert len(rows) == 1 and rows[0]["status"] == "WARN"
    assert "1.8.16" in rows[0]["message"]
