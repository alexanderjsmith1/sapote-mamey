"""Bundle copy of the ClusteredNR RID runner: held RIDs, pacing and query checks (v9.7.443).

NCBI and the clock are faked, so these tests make no network calls and take seconds."""
import argparse
import importlib.util
import time as real_time
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "tools/blastp_crawl/nr_rid_runner.py"
G28 = "MRAA" + "G" * 24
NORMAL = "MSTNPKPQRKTKRNTNRRPQDVKFPGGGQIVGGVYLLPRRGPRLGVRATRKTSERSQPRG"


class FakeClock:
    def __init__(self):
        self.now = 1_800_000_000.0

    def time(self):
        return self.now

    def sleep(self, s):
        self.now += s

    def strftime(self, fmt, t=None):
        return real_time.strftime(fmt, real_time.localtime(self.now if t is None else real_time.mktime(t)))

    def mktime(self, t):
        return real_time.mktime(t)

    def strptime(self, s, fmt):
        return real_time.strptime(s, fmt)


class FakeNCBI:
    """RIDs for files named in `never` stay WAITING; every other RID is READY after `ready_after` s."""
    def __init__(self, clock, never=(), ready_after=90):
        self.clock, self.never, self.ready_after = clock, set(never), ready_after
        self.rids, self.polls, self.submits = {}, {}, []

    def submit(self, text):
        gene = text.split("gene=")[1].split("|")[0].split()[0]
        rid = f"RID{len(self.submits):03d}"
        self.submits.append(gene)
        self.rids[rid] = (gene, self.clock.now)
        return rid, 30

    def status(self, rid):
        self.polls[rid] = self.polls.get(rid, 0) + 1
        gene, t0 = self.rids[rid]
        if gene in self.never:
            return "WAITING"
        return "READY" if self.clock.now - t0 >= self.ready_after else "WAITING"

    def fetch_xml2(self, rid):
        gene, _ = self.rids[rid]
        return (f"<Search><query-title>S|BGC1|gene={gene}</query-title><Hit><accession>WP_1</accession>"
                f"<sciname>x</sciname><title>t</title><bit-score>50</bit-score><evalue>1e-5</evalue>"
                f"<identity>9</identity><positive>9</positive><align-len>10</align-len></Hit></Search>")


def stage(tmp_path, genes, seqs=None):
    q = tmp_path / "Blastp RESULTS" / "_QUERIES_T" / "AS-1"
    for i, g in enumerate(genes):
        d = q / f"AS-1_p{i:04d}"
        d.mkdir(parents=True, exist_ok=True)
        seq = (seqs or {}).get(g, NORMAL)
        (d / f"AS-1__{g}.faa").write_text(f">AS-1|BGC1|gene={g}|aa={len(seq)}\n{seq}\n")


def load(tmp_path, monkeypatch, never=()):
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("RID_DATABASE", "nr_cluster_seq")
    monkeypatch.setenv("RID_QUERIES", "_QUERIES_T")
    monkeypatch.setenv("RID_BASE", "_LANE_T")
    spec = importlib.util.spec_from_file_location("rid_runner_443", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    clock = FakeClock()
    ncbi = FakeNCBI(clock, never=never)
    monkeypatch.setattr(mod, "time", clock)
    monkeypatch.setattr(mod, "submit", ncbi.submit)
    monkeypatch.setattr(mod, "status", ncbi.status)
    monkeypatch.setattr(mod, "fetch_xml2", ncbi.fetch_xml2)
    return mod, clock, ncbi


def args(**kw):
    base = dict(hours=12.0, sleep=300.0, limit=0, max_inflight=1, hold_after=3600.0, max_held=4,
                max_wait=129600.0, min_aa=20, max_aa=1000, max_one_residue=0.6, allow_mixed_tree=False,
                ignore_handoff=False)
    base.update(kw)
    return argparse.Namespace(**base)


def statuses(mod):
    return {Path(k).name: r["status"] for k, r in mod.load_ledger().items()}


def test_poll_interval_backs_off_with_age_and_errors():
    spec = importlib.util.spec_from_file_location("rid_runner_443_pi", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.poll_interval(30) == 60
    assert mod.poll_interval(900) == 300
    assert mod.poll_interval(7200) == 900
    assert mod.poll_interval(30, errors=2) == 240
    assert mod.poll_interval(7200, errors=5) == 1800


def test_held_rid_frees_its_slot_and_is_checked_rarely(tmp_path, monkeypatch):
    stage(tmp_path, ["g0", "g1", "g2", "g3", "g4"])
    mod, clock, ncbi = load(tmp_path, monkeypatch, never={"g0"})
    assert mod.cmd_run(args(hours=10.0, max_inflight=1)) == 0
    st = statuses(mod)
    # One slot, and g0 never returns: before v9.7.443 the lane would sit blocked for 10 h.
    assert [st[f"AS-1__g{i}.faa"] for i in range(1, 5)] == ["fetched"] * 4
    assert st["AS-1__g0.faa"] == "submitted"
    assert ncbi.submits.count("g0") == 1
    g0_rid = next(r for r, (g, _) in ncbi.rids.items() if g == "g0")
    assert ncbi.polls[g0_rid] <= 60          # ~600 at one check a minute


def test_rid_past_max_wait_becomes_unsure_and_is_never_resubmitted(tmp_path, monkeypatch):
    stage(tmp_path, ["g0", "g1"])
    mod, clock, ncbi = load(tmp_path, monkeypatch, never={"g0"})
    mod.cmd_run(args(hours=3.0, max_wait=7200.0))
    assert statuses(mod)["AS-1__g0.faa"] == "unsure"
    mod.cmd_run(args(hours=1.0, max_wait=7200.0))   # a restart must not resubmit it either
    assert ncbi.submits.count("g0") == 1
    assert statuses(mod)["AS-1__g1.faa"] == "fetched"


def test_poll_errors_keep_the_rid_and_stretch_the_gap(tmp_path, monkeypatch):
    stage(tmp_path, ["g0"])
    mod, clock, ncbi = load(tmp_path, monkeypatch)
    calls = {"n": 0}
    real_status = ncbi.status

    def flaky(rid):
        calls["n"] += 1
        if calls["n"] <= 6:
            raise RuntimeError("curl rc=52: ")
        return real_status(rid)
    monkeypatch.setattr(mod, "status", flaky)
    mod.cmd_run(args(hours=6.0))
    assert statuses(mod)["AS-1__g0.faa"] == "fetched"
    assert ncbi.submits == ["g0"]            # no retire-and-resubmit after poll errors


def test_unsearchable_and_giant_queries_are_parked_before_submit(tmp_path, monkeypatch):
    stage(tmp_path, ["gly", "big", "short", "ok"],
          seqs={"gly": G28, "big": "M" + "ACDEFGHIKLMNPQRSTVWY" * 60, "short": "MKTAYIAK"})
    mod, clock, ncbi = load(tmp_path, monkeypatch)
    mod.cmd_run(args(hours=2.0))
    st = statuses(mod)
    assert st["AS-1__gly.faa"] == st["AS-1__big.faa"] == st["AS-1__short.faa"] == "submit_failed_parked"
    assert st["AS-1__ok.faa"] == "fetched"
    assert ncbi.submits == ["ok"]
    notes = {Path(k).name: r["note"] for k, r in mod.load_ledger().items()}
    assert "low complexity" in notes["AS-1__gly.faa"] and ">=1000aa" in notes["AS-1__big.faa"]


def test_mixed_or_duplicated_query_tree_is_refused(tmp_path, monkeypatch):
    stage(tmp_path, ["g0", "g1"])
    panel = tmp_path / "Blastp RESULTS/_QUERIES_T/AS-1/AS-1_p0099/AS-1_panel.faa"
    panel.parent.mkdir(parents=True)
    panel.write_text(f">AS-1|BGC1|gene=g0|aa=60\n{NORMAL}\n>AS-1|BGC1|gene=g9|aa=60\n{NORMAL}\n")
    mod, clock, ncbi = load(tmp_path, monkeypatch)
    assert mod.cmd_run(args(hours=1.0)) == 2
    assert ncbi.submits == []
    log = (tmp_path / "Blastp RESULTS/_LANE_T/_run.log").read_text()
    assert "mixes single-protein and multi-protein" in log and "staged in both" in log


def test_hourly_rate_line_is_logged(tmp_path, monkeypatch):
    stage(tmp_path, ["g0", "g1"])
    mod, clock, ncbi = load(tmp_path, monkeypatch, never={"g0"})
    mod.cmd_run(args(hours=2.5))
    log = (tmp_path / "Blastp RESULTS/_LANE_T/_run.log").read_text()
    assert "RATE last hour:" in log and "held" in log


def test_run_from_the_bundle_without_a_workspace_refuses_before_writing(monkeypatch):
    bundle = SCRIPT.parents[2]
    monkeypatch.delenv("SAPOTE_WORKSPACE_ROOT", raising=False)
    monkeypatch.chdir(bundle)
    monkeypatch.setenv("RID_BASE", "_LANE_REFUSE_TEST")
    spec = importlib.util.spec_from_file_location("rid_runner_443_refuse", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr("sys.argv", ["nr_rid_runner.py", "run", "--hours", "0.001"])
    from mamey.path_safety import OutputInsideBundle
    with pytest.raises(OutputInsideBundle):
        mod.main()
    assert not (bundle / "Blastp RESULTS" / "_LANE_REFUSE_TEST").exists()


def test_a_handed_off_lane_refuses_to_run(tmp_path, monkeypatch):
    stage(tmp_path, ["g0"])
    mod, clock, ncbi = load(tmp_path, monkeypatch)
    lane = tmp_path / "Blastp RESULTS" / "_LANE_T"
    lane.mkdir(parents=True)
    (lane / "_HANDOFF_OUT.txt").write_text("handed off in H\n")
    assert mod.cmd_run(args(hours=1.0)) == 3
    assert ncbi.submits == []
    assert mod.cmd_run(args(hours=1.0, ignore_handoff=True)) == 0
    assert ncbi.submits == ["g0"]


def test_pid_file_exists_only_while_the_lane_runs(tmp_path, monkeypatch):
    stage(tmp_path, ["g0"])
    mod, clock, ncbi = load(tmp_path, monkeypatch)
    pid = tmp_path / "Blastp RESULTS" / "_LANE_T" / "_runner.pid"
    seen = []
    real_submit = ncbi.submit
    def spy(text):
        seen.append(pid.exists())
        return real_submit(text)
    monkeypatch.setattr(mod, "submit", spy)
    mod.cmd_run(args(hours=1.0))
    assert seen == [True] and not pid.exists()
