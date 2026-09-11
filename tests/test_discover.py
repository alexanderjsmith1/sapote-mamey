"""Regression coverage for `mamey discover` (workspace-orientation subcommand).

Builds throwaway package fixtures in tmp_path (a dir with a manifest_short.json is a package),
then asserts the coverage grid, the engine-drift/stale detection, and the next-action ranker.
Pure stdlib fixtures; no sealed packages or network needed.
"""
import json
from mamey import discover


def _mk_pkg(root, strain, engine, *, figures=False, mode_b=False, blastp=False,
            worklist=False, report=False, gate="MAMEY_COMPLETE", release="PUBLIC",
            tier="GOOD", raw=10, corr=8.0):
    pkg = root / strain / "package"
    pkg.mkdir(parents=True)
    (pkg / "manifest_short.json").write_text(json.dumps({
        "strain_id": strain, "mamey_version": engine, "release": release,
        "status": "MAMEY_COMPLETE", "assembly_tier": tier,
        "raw_bgcs": raw, "corrected_bgcs": corr}))
    (pkg / "gate_validation.json").write_text(json.dumps({"status": gate}))
    (pkg / "gold_mode_receipt.json").write_text(json.dumps({"mode": "gold"}))
    if figures:
        (pkg / "gold_figures").mkdir()
    if mode_b:
        (pkg / "modeb_verdicts.csv").write_text("bgc,verdict\nBGC001,green\n")  # header + 1 data row
    if blastp:
        (pkg / "bgc_blastp_panel").mkdir()
    if worklist:
        (pkg / f"{strain}_5b_manual_blastp_worklist.csv").write_text("bgc\n")
    if report:
        (pkg / f"{strain}_compiled_report.md").write_text("# report\n")
    return pkg


def test_finds_packages_and_coverage_grid(tmp_path):
    _mk_pkg(tmp_path, "AS-001", "1.9.111", figures=True, mode_b=True, blastp=True, report=True)
    _mk_pkg(tmp_path, "AS-002", "1.9.111", worklist=True)  # blastp pending; nothing else
    rep = discover.run(tmp_path, max_depth=6)
    pkgs = {p["strain"]: p for p in rep["packages"]}
    assert set(pkgs) == {"AS-001", "AS-002"}
    # fully-covered package
    a1 = pkgs["AS-001"]["caps"]
    assert a1["figures"] and a1["mode_b"] and a1["blastp"] and a1["report"]
    # worklist-only package: BLASTp pending (⧗), not ingested; no figures/mode-b
    a2 = pkgs["AS-002"]["caps"]
    assert a2["blastp_worklist_only"] and not a2["blastp"]
    assert not a2["figures"] and not a2["mode_b"]
    # next-action ranker surfaces the pending BLASTp worklist
    assert any("ingest-blastp" in a for a in rep["next_actions"])
    # counts are reported (not just present/absent)
    assert pkgs["AS-001"]["counts"]["mode_b"] == 1   # one verdict row written by the fixture
    assert pkgs["AS-002"]["counts"]["mode_b"] == 0


def test_stale_detection_uses_newest_engine_as_reference(tmp_path):
    _mk_pkg(tmp_path, "AS-100", "1.9.111", figures=True, mode_b=True, blastp=True, report=True)
    _mk_pkg(tmp_path, "AS-101", "1.9.112", figures=True, mode_b=True, blastp=True, report=True)
    rep = discover.run(tmp_path, max_depth=6)
    assert rep["engine_ref"] == "1.9.112"
    stale = {p["strain"]: p["stale"] for p in rep["packages"]}
    assert stale["AS-100"] is True   # older engine -> re-run candidate
    assert stale["AS-101"] is False  # newest -> current
    assert any("engine drift" in a for a in rep["next_actions"])


def test_current_override_marks_all_stale(tmp_path):
    _mk_pkg(tmp_path, "AS-200", "1.9.111", figures=True, mode_b=True, blastp=True, report=True)
    rep = discover.run(tmp_path, max_depth=6, current="1.9.200")
    assert rep["engine_ref"] == "1.9.200"
    assert all(p["stale"] for p in rep["packages"])


# NB: name avoids the conftest slow-hint substrings ("figure"/"cohort_fig") — this test is
# instant (no rendering) and belongs in the fast partition.
def test_multi_package_suggests_cohort_deck(tmp_path):
    for s in ("AS-300", "AS-301"):
        _mk_pkg(tmp_path, s, "1.9.111", figures=True, mode_b=True, blastp=True, report=True)
    rep = discover.run(tmp_path, max_depth=6)
    assert any("cohort-figures" in a for a in rep["next_actions"])


def test_empty_root_is_safe(tmp_path):
    rep = discover.run(tmp_path, max_depth=6)
    assert rep["packages"] == []
    assert rep["engine_ref"] is None
    assert rep["next_actions"]  # never empty
    # v9.7.334: an empty scan must NOT claim completeness (vacuous truth) — it must
    # tell the operator nothing was found, not that everything is done.
    joined = " ".join(rep["next_actions"]).lower()
    assert "no packages found" in joined
    assert "look complete" not in joined
