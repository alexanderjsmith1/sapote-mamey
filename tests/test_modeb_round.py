"""v9.7.194 — modeb-round orchestrator: emit + scaffold-verify + stateful worklist.
Guards the contract: N triage cards emitted, each scaffold-verified (structure only, not depth),
worklist written with correct per-BGC states. A broken skeleton must be flagged SCAFFOLD_INVALID."""
import json
import os

import pytest

from mamey.modeb_round import _scaffold_ok, run_round, S_TRIAGE, S_SCAFFOLD_BAD

_PKG = "/data/mamey-local/work/strain_intake/runs_v184/AS-421/package"
_HAVE = os.path.isdir(_PKG) and os.path.exists(os.path.join(_PKG, "manifest.json"))


def test_scaffold_ok_passes_valid_skeleton():
    tmpl = os.path.join(_PKG, "mode_b_templates", "BGC041_template.md")
    if not os.path.exists(tmpl):
        pytest.skip("AS-421 template not present")
    ok, errs = _scaffold_ok(open(tmpl).read())
    assert ok is True and errs == []


def test_scaffold_ok_fails_broken_skeleton():
    """A 5-section doc without §1–§30 headings must fail — the gate is not a rubber stamp."""
    bad = "# Fake\n## 1 Summary\nx\n## 2 Notes\ny\n"
    ok, errs = _scaffold_ok(bad)
    assert ok is False
    assert errs  # gives a reason


@pytest.mark.skipif(not _HAVE, reason="AS-421 package not present")
def test_run_round_emits_and_states():
    r = run_round(_PKG, top_n=10, scope="top")
    assert r["ok"] is True
    assert r["emitted_n"] == 10
    assert len(r["entries"]) == 10
    # all emitted skeletons should be valid scaffolds (TRIAGE), none SCAFFOLD_INVALID on a real run
    states = {e["authoring_state"] for e in r["entries"]}
    assert S_TRIAGE in states
    assert r["scaffold_invalid_n"] == 0
    # worklist file written
    wl = os.path.join(_PKG, "modeb_round_worklist.json")
    assert os.path.exists(wl)
    w = json.load(open(wl))
    assert w["schema_version"] == "modeb-round-worklist-1.0"
    # every entry starts unauthored
    assert all(e["authored_card"] is None for e in w["entries"])


# --- v9.7.195: quality_gate checklist surfaced in the emitted skeleton header ---
def test_emitted_skeleton_carries_quality_gate_checklist():
    """The authoring bar (contract quality_gate) must appear in the emitted skeleton so an author
    reads it before filling — closing the gap where the bar was buried in the contract JSON."""
    import json
    from mamey.modeb_template_emitter import _header_block
    from mamey.modeb_structure_gate import load_contract
    contract = load_contract()
    qg = contract.get("quality_gate") or []
    if not qg:
        import pytest; pytest.skip("contract has no quality_gate block")
    facts = {"bgc_id": "BGC001", "node": "NODE_1", "strain_id": "TEST", "products": "NRPS"}
    header = _header_block(facts, contract)
    assert "AUTHORING BAR" in header
    # every checklist item is present in the header
    for item in qg:
        assert item in header, f"quality_gate item missing from header: {item[:40]}"


def test_run_round_no_nameerror_without_precompute(tmp_path):
    """v9.7.226 regression guard (hermetic, no strain fixture): run_round must not
    raise NameError. Pre-fix, line 63 referenced an out-of-scope `args`, so EVERY
    call crashed; the only run_round test was skipif-gated on a hardcoded dev path
    and never ran in CI. run_round on an empty dir must RETURN a dict, not raise."""
    r = run_round(tmp_path, top_n=3, scope="top")
    assert isinstance(r, dict)
    assert r.get("ok") is False


def test_run_round_threads_precompute_dir(tmp_path, monkeypatch):
    """v9.7.226: the --from-precompute value must reach emit_batch."""
    import mamey.modeb_template_emitter as _emit
    seen = {}
    def _fake_emit_batch(pkg, scope="top", top_n=10, precompute_dir=None):
        seen["precompute_dir"] = precompute_dir
        return {"skipped_reason": "stub"}
    monkeypatch.setattr(_emit, "emit_batch", _fake_emit_batch)
    run_round(tmp_path, top_n=3, scope="top", precompute_dir="/cohort/xyz")
    assert seen["precompute_dir"] == "/cohort/xyz"
