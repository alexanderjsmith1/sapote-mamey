"""Gap-crawl handoff (pack / return / merge) and the multi-panel splitter (v9.7.443). No network."""
import csv
import importlib.util
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

BUNDLE = Path(__file__).resolve().parents[1]
HANDOFF = BUNDLE / "tools/blastp_crawl/crawl_handoff.py"
SPLIT = BUNDLE / "tools/blastp_crawl/split_multi_panels.py"
SEQ = "MSTNPKPQRKTKRNTNRRPQDVKFPGGGQIVGGVYLLPRRGPRLGVRATRKTSERSQPRG"
COLS = ["strain", "bgc", "file", "rid", "rtoe", "submit_iso", "status", "fetch_iso", "note"]


def load():
    spec = importlib.util.spec_from_file_location("crawl_handoff_443", HANDOFF)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def workspace(tmp_path, n=1, genes=("g0", "g1", "g2")):
    br = tmp_path / "ws" / "Blastp RESULTS"
    q = br / f"_QUERIES_GAP_AS-{n}_K" / f"AS-{n}"
    for i, g in enumerate(genes):
        d = q / f"AS-{n}_gapK_p{i:04d}"
        d.mkdir(parents=True)
        (d / f"AS-{n}__gapK__{g}.faa").write_text(f">{g}\n{SEQ}\n")
    lane = br / f"_STRAINGAP_SINGLE_CLNR_GAP_AS{n}"
    lane.mkdir(parents=True)
    rel = f"AS-{n}/AS-{n}_gapK_p0000/AS-{n}__gapK__{genes[0]}.faa"
    write_ledger(lane / "_ledger.csv", [dict(strain=f"AS-{n}", bgc=f"AS-{n}_gapK_p0000", file=rel,
                 rid="R0", status="fetched", fetch_iso="2026-09-25 10:00:00")])
    (lane / "results").mkdir()
    (lane / "results" / "home.csv").write_text("home\n")
    return tmp_path / "ws"


def write_ledger(path, rows):
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in COLS})


def run(mod, monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["crawl_handoff.py", *argv])
    return mod.main()


def test_pack_return_merge_round_trip(tmp_path, monkeypatch):
    ws = workspace(tmp_path)
    mod = load()
    monkeypatch.setattr(mod, "runners_live", lambda: False)
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(ws))
    out = tmp_path / "out"
    out.mkdir()
    assert run(mod, monkeypatch, "pack", "--out", str(out), "--name", "H") == 0
    h = out / "H"
    for rel in ("tools/blastp_crawl/nr_rid_runner.py", "mamey/csv_safety.py", "mamey/path_safety.py",
                "hooks/block_blastp_overconcurrency.sh", "hooks/blastp_launch_probe.py",
                ".claude/settings.json", "START_HERE.md", "HANDOFF_MANIFEST.tsv", "run_lane.sh", "return.sh"):
        assert (h / rel).exists(), rel
    assert '"SAPOTE_BLASTP_MAX_LANES": "4"' in (h / ".claude/settings.json").read_text()
    assert (out / "H.zip").exists()
    home_marker = ws / "Blastp RESULTS/_STRAINGAP_SINGLE_CLNR_GAP_AS1/_HANDOFF_OUT.txt"
    assert home_marker.exists()
    assert not (h / "Blastp RESULTS/_STRAINGAP_SINGLE_CLNR_GAP_AS1/_HANDOFF_OUT.txt").exists()
    # The packed runner works on its own, with no bundle around it.
    env = dict(os.environ, SAPOTE_WORKSPACE_ROOT=str(h), RID_BASE="_STRAINGAP_SINGLE_CLNR_GAP_AS1",
               RID_QUERIES="_QUERIES_GAP_AS-1_K", RID_DATABASE="nr_cluster_seq")
    st = subprocess.run([sys.executable, str(h / "tools/blastp_crawl/nr_rid_runner.py"), "status"],
                        env=env, capture_output=True, text=True, cwd=h)
    assert st.returncode == 0 and "fetched=1" in st.stdout
    # The other machine fetches g1.
    lane = h / "Blastp RESULTS/_STRAINGAP_SINGLE_CLNR_GAP_AS1"
    rows = list(csv.DictReader((lane / "_ledger.csv").open()))
    rows.append(dict(strain="AS-1", bgc="AS-1_gapK_p0001", file="AS-1/AS-1_gapK_p0001/AS-1__gapK__g1.faa",
                     rid="R1", status="fetched", fetch_iso="2026-09-26 10:00:00"))
    write_ledger(lane / "_ledger.csv", rows)
    (lane / "results" / "away.csv").parent.mkdir(parents=True, exist_ok=True)
    (lane / "results" / "away.csv").write_text("away\n")
    (lane / "_run.log").write_text("[2026-09-26 10:00:00] READY g1\n")
    monkeypatch.chdir(h)
    back = tmp_path / "back"
    back.mkdir()
    assert run(mod, monkeypatch, "return", "--out", str(back)) == 0
    rz = next(back.glob("BLASTP_RETURN_*.zip"))
    home_lane = ws / "Blastp RESULTS/_STRAINGAP_SINGLE_CLNR_GAP_AS1"
    before = (home_lane / "_ledger.csv").read_bytes()
    assert run(mod, monkeypatch, "merge", str(rz)) == 0              # dry run writes nothing
    assert (home_lane / "_ledger.csv").read_bytes() == before
    assert not (home_lane / "results" / "away.csv").exists()
    assert run(mod, monkeypatch, "merge", str(rz), "--execute") == 0
    st = {r["file"].split("__")[-1]: r["status"] for r in csv.DictReader((home_lane / "_ledger.csv").open())}
    assert st == {"g0.faa": "fetched", "g1.faa": "fetched"}
    assert (home_lane / "results" / "away.csv").read_text() == "away\n"
    assert (home_lane / "results" / "home.csv").read_text() == "home\n"
    assert list(home_lane.glob("_ledger.csv.bak_premerge_*"))
    assert "merged from" in (home_lane / "_run.log").read_text()
    assert not home_marker.exists()                                   # merge clears the marker


def test_merge_holds_a_lane_that_changed_at_home(tmp_path, monkeypatch):
    ws = workspace(tmp_path)
    mod = load()
    monkeypatch.setattr(mod, "runners_live", lambda: False)
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(ws))
    out = tmp_path / "out"
    out.mkdir()
    run(mod, monkeypatch, "pack", "--out", str(out), "--name", "H")
    monkeypatch.chdir(out / "H")
    run(mod, monkeypatch, "return", "--out", str(tmp_path))
    rz = next(tmp_path.glob("BLASTP_RETURN_*.zip"))
    home_led = ws / "Blastp RESULTS/_STRAINGAP_SINGLE_CLNR_GAP_AS1/_ledger.csv"
    home_led.write_text(home_led.read_text() + "AS-1,x,AS-1/x.faa,R9,,,submitted,,\n")   # home kept running
    changed = home_led.read_bytes()
    assert run(mod, monkeypatch, "merge", str(rz), "--execute") == 1
    assert home_led.read_bytes() == changed


def test_pack_refuses_while_lanes_run_and_inside_the_bundle(tmp_path, monkeypatch):
    ws = workspace(tmp_path)
    mod = load()
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(ws))
    monkeypatch.setattr(mod, "runners_live", lambda: True)
    with pytest.raises(SystemExit):
        run(mod, monkeypatch, "pack", "--out", str(tmp_path))
    monkeypatch.setattr(mod, "runners_live", lambda: False)
    from mamey.path_safety import OutputInsideBundle
    with pytest.raises(OutputInsideBundle):
        run(mod, monkeypatch, "pack", "--out", str(BUNDLE / "tools"))
    assert not list((BUNDLE / "tools").glob("BLASTP_HANDOFF_*"))


def test_split_multi_panels_skips_genes_already_single(tmp_path):
    br = tmp_path / "Blastp RESULTS"
    strain = br / "_QUERIES_GAP_AS-1_K" / "AS-1"
    (strain / "AS-1_gapK_p0001").mkdir(parents=True)
    (strain / "AS-1_gapK_p0001" / "AS-1__gapK__a.faa").write_text(f">a\n{SEQ}\n")
    (strain / "_gap").mkdir()
    (strain / "_gap" / "AS-1_gapK_p010.faa").write_text(f">a\n{SEQ}\n>b\n{SEQ}\n>c\n{SEQ}\n")
    env = dict(os.environ, SAPOTE_WORKSPACE_ROOT=str(tmp_path))
    dry = subprocess.run([sys.executable, str(SPLIT)], env=env, capture_output=True, text=True)
    assert dry.returncode in (0, None) and "DRY RUN" in dry.stdout
    assert (strain / "_gap").exists()
    wet = subprocess.run([sys.executable, str(SPLIT), "--execute"], env=env, capture_output=True, text=True)
    assert "1 already staged singly" in wet.stdout
    singles = sorted(p.name for p in strain.rglob("*.faa"))
    assert singles == ["AS-1__gapK__a.faa", "AS-1__gapK__b.faa", "AS-1__gapK__c.faa"]
    assert (br / "_SUPERSEDED_MULTI_PANELS" / "AS-1" / "AS-1_gapK_p010.faa").exists()


def test_packed_run_lane_works_without_an_execute_bit(tmp_path, monkeypatch):
    """The bundle ships every .sh without an execute bit and runs them with bash; the packed
    wrapper must do the same, or a handoff lane dies with exit 126 before the runner starts."""
    ws = workspace(tmp_path)
    mod = load()
    monkeypatch.setattr(mod, "runners_live", lambda: False)
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(ws))
    out = tmp_path / "out"
    out.mkdir()
    run(mod, monkeypatch, "pack", "--out", str(out), "--name", "H")
    inner = out / "H" / "tools/blastp_crawl/run_lane.sh"
    inner.chmod(0o644)
    # No strain given: run_lane.sh itself must run and refuse with its own usage error (exit 1).
    p = subprocess.run([str(out / "H" / "run_lane.sh")], capture_output=True, text=True)
    assert p.returncode == 1, (p.returncode, p.stderr)
    assert "give a strain" in p.stderr
