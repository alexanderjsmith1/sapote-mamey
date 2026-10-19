"""Cold imports and explicit monitor entry points; synthetic inputs, no renderer.

The dependency stubs isolate import effects. Explicit helper-route controls use
the real shipped sibling over tiny CSV/FASTA fixtures and stop before rendering.
"""
import builtins
import csv
import datetime
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import types

import pytest


ROOT = Path(__file__).resolve().parents[1]
CONTEXT_ROOT = ROOT
PLOTS = ("plot_crawl_12h_15min", "plot_crawl_cumulative", "plot_usable_6h")
RELATIVE = ("tools/phylo_postflight.py",) + tuple(
    f"tools/blastp_monitoring/{name}.py" for name in PLOTS)


@pytest.fixture
def import_source_root():
    """Normally the bundle; a tiny owner overlay can supply read-only context."""
    return CONTEXT_ROOT


COLD_CHILD = r'''
import builtins, importlib.util, json, os, runpy, subprocess, sys, types
from pathlib import Path
path, phase, workspace, output = sys.argv[1:]
# Simulate the resolver's already-admitted canonical code roots. No root derived
# from an operator data directory may subsequently enter the leading block.
tools = str(Path(path).parents[1] if 'blastp_monitoring' in path else Path(path).parent)
bundle = str(Path(tools).parent)
sys.path[:0] = [tools, bundle]
wbio = types.ModuleType('_wbio')
def forbidden(*args, **kwargs):
    raise AssertionError('operational action during import/help')
wbio.atomic_dump_json_owned = forbidden
preflight = types.ModuleType('phylo_preflight')
preflight.TAXA = {'Sentinel': {'rank': 'genus'}}
preflight.FAMILY_LEVEL = {}
def rank_of(value):
    return None
preflight.rank_of = rank_of
sys.modules.update(_wbio=wbio, phylo_preflight=preflight)
os.environ.update(SAPOTE_WORKSPACE_ROOT=workspace,
                  SAPOTE_BLASTP_PLOT_DIR=output, MAMEY_DATA_ROOT=workspace)
sys.argv = [path, '--hours'] if phase == 'import' else [path, '--help']
before = (os.getcwd(), dict(os.environ), list(sys.path))
real_import = builtins.__import__
def guarded_import(name, *args, **kwargs):
    if name == 'matplotlib' or name.startswith('matplotlib.'):
        raise AssertionError('Matplotlib initialized during import/help')
    return real_import(name, *args, **kwargs)
builtins.__import__ = guarded_import
os.chdir = forbidden
subprocess.Popen = forbidden
def audit(event, args):
    if event in ('os.system', 'os.posix_spawn', 'subprocess.Popen') or event.startswith('socket.connect'):
        forbidden()
    if event == 'exec' and str(args[0].co_filename).endswith('plot_crawl_recent.py'):
        raise AssertionError('plot helper executed during import/help')
sys.addaudithook(audit)
if phase == 'import':
    spec = importlib.util.spec_from_file_location('cold_target', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if path.endswith('phylo_postflight.py'):
        assert module.TAXA is preflight.TAXA
        assert module.ROOT == workspace
else:
    try:
        runpy.run_path(path, run_name='__main__')
    except SystemExit as exc:
        assert exc.code == 0, exc.code
    else:
        raise AssertionError('help did not exit')
assert before == (os.getcwd(), dict(os.environ), list(sys.path)), 'import/help mutated caller state'
assert not Path(output).exists(), 'import/help created an output directory'
print('COLD_CONTROL_PASS')
'''


@pytest.mark.parametrize("relative", RELATIVE)
@pytest.mark.parametrize("phase", ("import", "help"))
def test_fresh_foreign_cwd_import_and_help_are_inert(relative, phase, tmp_path):
    caller = tmp_path / "foreign caller"
    caller.mkdir()
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-B", "-c", COLD_CHILD,
         str(ROOT / relative), phase, str(tmp_path / "missing operator root"),
         str(tmp_path / "missing plot output")],
        cwd=caller, text=True, capture_output=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "COLD_CONTROL_PASS" in result.stdout
    if phase == "help":
        assert "usage:" in result.stdout.lower()


def _load(path):
    spec = importlib.util.spec_from_file_location("owner_import_control", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _plot(name):
    return _load(ROOT / "tools/blastp_monitoring" / f"{name}.py")


@pytest.mark.parametrize("name", PLOTS)
def test_output_guard_precedes_dependency_and_workspace_operations(
        name, tmp_path, monkeypatch, import_source_root):
    module = _plot(name)
    # Use the real unchanged containment implementation with a synthetic bundle.
    safety = _load(import_source_root / "mamey/path_safety.py")
    package = types.ModuleType("mamey")
    package.__path__ = []
    monkeypatch.setitem(sys.modules, "mamey", package)
    monkeypatch.setitem(sys.modules, "mamey.path_safety", safety)
    code = tmp_path / "synthetic code"
    code.mkdir()
    (code / "BUILD_STAMP.txt").write_text("synthetic marker\n")
    monkeypatch.setattr(module, "__file__", str(code / "tools/blastp_monitoring" / f"{name}.py"))
    monkeypatch.setattr(module, "OUT", str(code / "refused output"))
    monkeypatch.setattr(sys, "path", list(sys.path))
    attempts = []
    original = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name.startswith("matplotlib"):
            attempts.append(name)
            raise AssertionError("dependency initialized before output refusal")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    monkeypatch.setattr(module.os, "chdir", lambda *_: pytest.fail("workspace changed before refusal"))
    with pytest.raises(SystemExit, match="OUTPUT_INSIDE_BUNDLE"):
        module.main([])
    assert attempts == []
    assert not Path(module.OUT).exists()


@pytest.mark.parametrize("argv, expected", [([], 12), (["--hours", "6"], 6),
    (["--hours=3"], 3), (["--legacy-ignored-option", "value"], 12)])
def test_hours_are_parsed_only_on_explicit_main(argv, expected, monkeypatch):
    module = _plot(PLOTS[0])

    class GuardReached(Exception):
        pass

    def stop(path):
        assert path == module.OUT
        assert module.HOURS == expected
        raise GuardReached

    monkeypatch.setattr(module, "_refuse_output_inside_bundle", stop)
    with pytest.raises(GuardReached):
        module.main(argv)


@pytest.mark.parametrize("argv", (["--hours"], ["--hours=invalid"]))
def test_invalid_hours_refuse_before_operational_calls(argv, monkeypatch):
    module = _plot(PLOTS[0])
    monkeypatch.setattr(module, "_refuse_output_inside_bundle",
                        lambda *_: pytest.fail("invalid argv reached output/data operation"))
    with pytest.raises(SystemExit) as exc:
        module.main(argv)
    assert exc.value.code == 2


@pytest.mark.parametrize("name", PLOTS)
def test_explicit_main_uses_shipped_sibling_with_operator_roots(
        name, tmp_path, monkeypatch, import_source_root):
    code = tmp_path / "relocated code/tools/blastp_monitoring"
    code.mkdir(parents=True)
    target = code / f"{name}.py"
    target.write_bytes((ROOT / "tools/blastp_monitoring" / target.name).read_bytes())
    sibling = code / "plot_crawl_recent.py"
    sibling.write_bytes((import_source_root / "tools/blastp_monitoring" / sibling.name).read_bytes())
    workspace = tmp_path / "operator workspace with spaces"
    queries = workspace / "Blastp RESULTS/_QUERIES_SYNTHETIC"
    queries.mkdir(parents=True)
    (queries / "synthetic.faa").write_text(">SYNTHETIC_ONE\nA\n>SYNTHETIC_TWO\nA\n")
    lane = workspace / "Blastp RESULTS/SYNTHETIC_CLNR_LANE"
    lane.mkdir()
    with (lane / "_ledger.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["status", "fetch_iso", "note", "file"])
        writer.writeheader()
        writer.writerow({"status": "fetched", "fetch_iso": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                         "note": "2 rows", "file": "synthetic.faa"})
    output = tmp_path / "operator output"
    output.mkdir()
    (output / "plot_crawl_recent.py").write_text("raise AssertionError('output directory code executed')\n")
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(workspace))
    monkeypatch.setenv("SAPOTE_BLASTP_PLOT_DIR", str(output))
    module = _load(target)
    assert module.ROOT == str(workspace)
    assert module.OUT == str(output / "crawl_plots")
    if hasattr(module, "BR"):
        assert module.BR == str(workspace / "Blastp RESULTS")
    monkeypatch.setattr(module, "_refuse_output_inside_bundle", lambda *_: None)
    monkeypatch.chdir(tmp_path)  # registers restoration after main's explicit chdir
    loaded = []
    original = importlib.util.module_from_spec

    def record(spec):
        result = original(spec)
        loaded.append(result)
        return result

    monkeypatch.setattr(importlib.util, "module_from_spec", record)
    mpl = types.ModuleType("matplotlib")
    pyplot = types.ModuleType("matplotlib.pyplot")
    backend = []
    mpl.use = backend.append
    mpl.pyplot = pyplot

    class BeforeRender(Exception):
        pass

    def refuse_render(*args, **kwargs):
        raise BeforeRender

    pyplot.subplots = refuse_render
    monkeypatch.setitem(sys.modules, "matplotlib", mpl)
    monkeypatch.setitem(sys.modules, "matplotlib.pyplot", pyplot)
    with pytest.raises(BeforeRender):
        module.main([])
    assert Path.cwd() == workspace
    assert len(loaded) == 1 and Path(loaded[0].__file__) == sibling
    assert backend == ["Agg", "Agg"]
    assert loaded[0].query_proteins("synthetic.faa") == 2
    fetches = loaded[0].load_fetches()
    assert len(fetches) == 1 and fetches[0][1:] == (2, "ClusteredNR", lane.name)
    assert not (output / "crawl_plots").exists()


class _Clock(datetime.datetime):
    @classmethod
    def now(cls):
        return cls(2026, 1, 2, 12, 0)


def _clock(module, monkeypatch):
    monkeypatch.setattr(module, "datetime", types.SimpleNamespace(
        datetime=_Clock, timedelta=datetime.timedelta))


def test_cumulative_helpers_keep_channel_totals_and_window_boundary(monkeypatch):
    module = _plot(PLOTS[1])
    _clock(module, monkeypatch)
    now = _Clock.now()
    rows = [(now - datetime.timedelta(minutes=61), 2, "nr", "a"),
            (now - datetime.timedelta(minutes=60), 3, "ClusteredNR", "b"),
            (now, 5, "nr", "a")]
    times, total, nr, cl = module.cumulative(rows)
    assert times == [r[0] for r in rows]
    assert (total, nr, cl) == ([2, 5, 10], [2, 2, 7], [0, 3, 3])
    assert module.slope_last(rows, 60) == (8, 8 / 60)
    assert module.cumulative([]) == ([], [], [], [])


def test_cumulative_panel_rezeros_window_without_a_renderer(monkeypatch):
    module = _plot(PLOTS[1])
    _clock(module, monkeypatch)
    calls = []

    class Axes:
        def step(self, times, values, **kwargs):
            calls.append((times, values, kwargs))

        def get_xticklabels(self):
            return []

        def __getattr__(self, name):
            return lambda *args, **kwargs: None

    now = _Clock.now()
    module.panel(Axes(), [(now - datetime.timedelta(hours=25), 10, "nr", "a"),
                         (now, 3, "ClusteredNR", "b")], "synthetic", since_hours=24)
    assert [call[1] for call in calls] == [[3], [0], [3]]
    assert all(call[2]["where"] == "post" for call in calls)
    module.panel(Axes(), [], "empty")
    assert len(calls) == 3


def test_live_lane_helper_counts_processes_without_spawning(monkeypatch):
    module = _plot(PLOTS[0])
    commands = ("/fake/python3 nr_rid_runner.py run --lane=synthetic\n"
                "python nr_rid_runner.py run\n"
                "zsh -c python nr_rid_runner.py run\n"
                "caffeinate python nr_rid_runner.py run\n"
                "python unrelated.py run\n"
                "python nr_rid_runner.py run grep\n")
    calls = []

    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))
        return types.SimpleNamespace(stdout=commands)

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    assert module.live_lanes() == 2
    assert calls[0][0] == ["ps", "-eo", "command"]

    def fail(*args, **kwargs):
        raise OSError("synthetic unavailable process list")

    monkeypatch.setattr(module.subprocess, "run", fail)
    assert module.live_lanes() is None


def test_health_and_error_helpers_on_tiny_synthetic_ledgers(tmp_path, monkeypatch):
    module = _plot(PLOTS[0])
    _clock(module, monkeypatch)
    lane = tmp_path / "SYNTHETIC_LANE"
    lane.mkdir()
    monkeypatch.setattr(module, "BR", str(tmp_path))
    with (lane / "_ledger.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["status", "submit_iso", "fetch_iso", "note"])
        writer.writeheader()
        writer.writerows([
            {"status": "submitted", "submit_iso": "2026-01-02 10:00:00"},
            {"status": "submitted", "submit_iso": "2026-01-01 10:00:00"},
            {"status": "fetched", "fetch_iso": "2026-01-02 11:30:00", "note": "3 rows"},
            {"status": "fetched", "fetch_iso": "2026-01-02 11:00:00", "note": "0 rows"},
            {"status": "fetched", "fetch_iso": "2026-01-01 11:00:00", "note": "4 rows"},
            {"status": "fetched", "fetch_iso": "invalid", "note": "3 rows"}])
    now = _Clock.now()
    assert module.health(now - datetime.timedelta(hours=1), now) == (
        _Clock(2026, 1, 2, 11, 30), 1, 1, 1)
    (lane / "_run.log").write_text(
        "[2026-01-02 11:40:00] submit failed; poll ERROR\n"
        "[2026-01-02 11:30:00] curl rc=18\n"
        "[2026-01-02 10:00:00] backing off\n"
        "[2026-99-02 11:40:00] throttled\n"
        "poll ERROR without timestamp\n")
    assert module.recent_errors(30) == (1, 1)


@pytest.mark.parametrize("mode", ("environment", "exact_cwd", "no_parent_search"))
def test_phylo_data_root_and_sibling_contract_preserved(mode, tmp_path, monkeypatch):
    root = tmp_path / "data with spaces"
    child = root / "nested caller"
    child.mkdir(parents=True)
    table = root / "strain_data/_ANTISMASH_CANONICAL/STRAIN_METADATA_CONSOLIDATED.tsv"
    table.parent.mkdir(parents=True)
    table.write_text("strain\ttaxonomy\nSYN-001\tStreptomyces syntheticus\n")
    monkeypatch.delenv("MAMEY_DATA_ROOT", raising=False)
    monkeypatch.chdir(root if mode == "exact_cwd" else child)
    if mode == "environment":
        monkeypatch.setenv("MAMEY_DATA_ROOT", str(root))
    wbio = types.ModuleType("_wbio")
    monkeypatch.setattr(wbio, "atomic_dump_json_owned",
                        lambda *args, **kwargs: pytest.fail("unexpected write"), raising=False)
    pre = types.ModuleType("phylo_preflight")
    monkeypatch.setattr(pre, "TAXA", {"sentinel": 1}, raising=False)
    monkeypatch.setattr(pre, "FAMILY_LEVEL", {}, raising=False)
    monkeypatch.setattr(pre, "rank_of", lambda value: None, raising=False)
    monkeypatch.setitem(sys.modules, "_wbio", wbio)
    monkeypatch.setitem(sys.modules, "phylo_preflight", pre)
    monkeypatch.setattr(sys, "path", list(sys.path))
    module = _load(ROOT / RELATIVE[0])
    assert module.TAXA is pre.TAXA
    expected = ROOT if mode == "no_parent_search" else root
    assert module.ROOT == str(expected)
    assert str(expected / "Tools") not in sys.path
    if mode != "no_parent_search":
        assert module.load_tax() == {"SYN-001": "Streptomyces syntheticus"}


def test_phylo_cold_import_with_real_shipped_siblings(tmp_path, import_source_root):
    """Exercise actual taxonomy/writer imports without importing the whole engine."""
    program = r'''
import builtins, importlib.util, os, sys, types
from pathlib import Path
target, context, workspace = map(Path, sys.argv[1:])
sys.path[:0] = [str(target.parent), str(target.parent.parent),
               str(context / 'tools'), str(context)]
# Admit only the actual shipped package directory for this tiny sibling closure.
package = types.ModuleType('mamey'); package.__path__ = [str(context / 'mamey')]
sys.modules['mamey'] = package
for key in ('OUTGROUP_REGISTRY', 'SAPOTE_ROOT'):
    os.environ.pop(key, None)
os.environ.update(MAMEY_DATA_ROOT=str(workspace), SAPOTE_WORKSPACE_ROOT=str(workspace))
sys.argv = ['foreign parent', '--hours']
original = builtins.__import__
def blocked_import(name, *args, **kwargs):
    if name.startswith('matplotlib'):
        raise AssertionError('unexpected plotting import')
    return original(name, *args, **kwargs)
builtins.__import__ = blocked_import
def refuse(*args, **kwargs):
    raise AssertionError('operational action during tiny cold import')
os.chdir = refuse
def audit(event, args):
    if event in ('subprocess.Popen', 'os.system', 'os.posix_spawn') or event.startswith('socket.connect'):
        refuse()
sys.addaudithook(audit)
import _wbio, phylo_preflight
assert Path(_wbio.__file__) == context / 'tools/_wbio.py'
assert Path(phylo_preflight.__file__) == context / 'tools/phylo_preflight.py'
before = (os.getcwd(), dict(os.environ), list(sys.path))
spec = importlib.util.spec_from_file_location('tiny_real_phylo', target)
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
assert module.TAXA is phylo_preflight.TAXA and module.TAXA
assert module.rank_of is phylo_preflight.rank_of
assert module._atomic_write_json is _wbio.atomic_dump_json_owned
assert module.ROOT == str(workspace)
assert before == (os.getcwd(), dict(os.environ), list(sys.path))
print('REAL_SIBLING_CONTROL_PASS')
'''
    child = subprocess.run([sys.executable, "-I", "-S", "-B", "-c", program,
        str(ROOT / RELATIVE[0]), str(import_source_root), str(tmp_path / "missing data root")],
        cwd=tmp_path, text=True, capture_output=True, timeout=15)
    assert child.returncode == 0, child.stdout + child.stderr
    assert "REAL_SIBLING_CONTROL_PASS" in child.stdout
