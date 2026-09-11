"""v9.7.418 (GOLDENROD): exactly one outgroup gate ships — the superseded sibling must not.

Eggplant's .417 audit (§3.3): `outgroup_sanity_gate.py` and `phylo_outgroup_gate.py` are the SAME
distance-screen tool under two names; only `phylo_outgroup_gate.py` landed in the seal (verified:
`load`/`ident`/`check` trio is unique to it). The superseded `.416`-queue `outgroup_sanity_gate.py`
diff still reports `git apply --check` rc=0, so it "looks like a clean win" and applying it would ship
a SECOND copy of the one tool. No shipped test catches that today. This is that guard.

Filesystem/structure only — no scan, score, gate logic, or biological claim. Judgment deferred.
"""
import pathlib

TOOLS = pathlib.Path(__file__).resolve().parents[1] / "tools"


def _outgroup_gate_files(tools_dir: pathlib.Path):
    """Every tool whose basename looks like an outgroup gate (`*outgroup*gate*.py`)."""
    return sorted(p.name for p in tools_dir.glob("*outgroup*gate*.py"))


def test_exactly_one_outgroup_gate_ships():
    got = _outgroup_gate_files(TOOLS)
    assert got == ["phylo_outgroup_gate.py"], (
        "exactly one outgroup gate must ship; the superseded `outgroup_sanity_gate.py` is the same "
        f"tool renamed and must not land as a second copy. Found in tools/: {got}")


def test_superseded_sanity_gate_name_is_not_a_live_tool():
    assert not (TOOLS / "outgroup_sanity_gate.py").exists(), (
        "outgroup_sanity_gate.py is the pre-bundle loose name of phylo_outgroup_gate.py; it must not "
        "reappear as a shipped tool")


def test_guard_fires_on_a_duplicate(tmp_path):
    """Negative control: the detector must actually catch a second gate under the old name."""
    t = tmp_path / "tools"
    t.mkdir()
    (t / "phylo_outgroup_gate.py").write_text("def check():\n    return 0\n", encoding="utf-8")
    assert _outgroup_gate_files(t) == ["phylo_outgroup_gate.py"]
    (t / "outgroup_sanity_gate.py").write_text("def check():\n    return 0\n", encoding="utf-8")
    got = _outgroup_gate_files(t)
    assert got == ["outgroup_sanity_gate.py", "phylo_outgroup_gate.py"]
    # the production assertion above would fail on this two-file set — the guard is not vacuous:
    assert got != ["phylo_outgroup_gate.py"]
