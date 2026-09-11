"""v9.7.408 — one door for agents, and the phylo tools run from anywhere (AMBER-409 F2/F3).

Behaviour-anchored: AGENTS.md and CLAUDE.md are the same door; `start` prints the happy path with
the live version and no stale literal; `phylo-autopilot` is a registered subcommand; and
phylo_place's OFFICIAL_DATA resolver finds the workspace from a nested cwd and says so loudly when
it cannot (the silent bare-label degrade was the field failure)."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_agents_and_claude_doors_are_one_file():
    a = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    c = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    assert a == c, "AGENTS.md and CLAUDE.md must be byte-identical: one door, two names"
    assert "python mamey_run.py start" in a
    assert "CURRENT_DOCS_INDEX.md" in a
    import re
    assert not re.search(r"\b9\.7\.\d{3}\b", a), "the door must not carry a version literal (it would go stale)"


def test_start_prints_live_version_and_happy_path():
    import mamey
    out = subprocess.run([sys.executable, str(ROOT / "mamey_run.py"), "start", "--no-doctor"],
                         cwd=str(ROOT), capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-500:]
    assert f"engine {mamey.__version__}" in out.stdout
    assert f"bundle {mamey.BUNDLE_VERSION}" in out.stdout
    for cmd in ("doctor", "inspect", "run --strain", "validate", "explain"):
        assert cmd in out.stdout, f"happy path missing `{cmd}`"


def test_phylo_autopilot_is_a_registered_subcommand():
    from mamey.cli import build_parser
    p = build_parser()
    ns = p.parse_args(["phylo-autopilot", "plan", "--help"])
    assert ns.tool_args == ["plan", "--help"]
    ns2 = p.parse_args(["start", "--no-doctor"])
    assert ns2.no_doctor is True


def _load_tool(name):
    import importlib.util as ilu
    spec = ilu.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    mod = ilu.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def test_phylo_place_finds_official_data_from_nested_cwd(tmp_path, monkeypatch):
    ws = tmp_path / "ws"; (ws / "OFFICIAL_DATA").mkdir(parents=True)
    (ws / "OFFICIAL_DATA" / "STRAIN_METADATA.tsv").write_text(
        "tip_label\thost_common\tlocation\tgenbank_accession\nAS-0001\tbee\tON\tXX000001\n", encoding="utf-8")
    nested = ws / "strain_data" / "_PLACEMENT" / "rare_genera"; nested.mkdir(parents=True)
    monkeypatch.delenv("SAPOTE_WORKSPACE_ROOT", raising=False); monkeypatch.delenv("SAPOTE_ROOT", raising=False)
    monkeypatch.chdir(nested)
    pp = _load_tool("phylo_place")
    assert pp.official_data_root() == str(ws)
    pp._AS_META = None
    meta = pp._as_meta()
    assert meta.get("AS-0001", {}).get("host") == "bee", "enriched labels must load from a nested cwd"


def test_phylo_place_is_loud_when_official_data_is_nowhere(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("SAPOTE_WORKSPACE_ROOT", raising=False); monkeypatch.delenv("SAPOTE_ROOT", raising=False)
    # a temp dir has no OFFICIAL_DATA above it, and the tool's own parents are the bundle (also none)
    monkeypatch.chdir(tmp_path)
    pp = _load_tool("phylo_place")
    if pp.official_data_root() is not None:
        pytest.skip("this checkout sits under a workspace with OFFICIAL_DATA; miss path not reachable here")
    pp._AS_META = None
    assert pp._as_meta() == {}
    err = capsys.readouterr().err
    assert "WARN phylo_place" in err and "BARE IDs" in err, "a silent degrade is the defect this guards"


def test_outgroup_registry_resolves_via_env_first(tmp_path, monkeypatch):
    ws = tmp_path / "ws"; (ws / "OFFICIAL_DATA").mkdir(parents=True)
    reg = ws / "OFFICIAL_DATA" / "OUTGROUP_REGISTRY.tsv"; reg.write_text("genus\toutgroup\n", encoding="utf-8")
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(ws)); monkeypatch.delenv("OUTGROUP_REGISTRY", raising=False)
    og = _load_tool("outgroup_registry")
    assert og.REGISTRY == str(reg)
