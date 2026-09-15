"""Fixtures for tools/ratchet_delta.py — per-lane accounting against the repo-health ratchets.

A stub repo_health.py is written into each fixture tree, so these run in milliseconds and assert the
COMPARISON logic. The real counter is exercised separately by `_print_sites`, whose agreement with
repo_health is the tool's own runtime cross-check.
"""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / 'tools' / 'ratchet_delta.py'


def _load():
    spec = importlib.util.spec_from_file_location('ratchet_delta', TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _tree(root: Path, results, passed=True, scan_files=None):
    """A minimal tree carrying a stub repo_health.py that replays `results`."""
    (root / 'tools').mkdir(parents=True, exist_ok=True)
    (root / 'mamey').mkdir(parents=True, exist_ok=True)
    report = json.dumps({'root': str(root), 'strict': True, 'passed': passed,
                         'results': results, 'waived': []})
    (root / 'tools' / 'repo_health.py').write_text(
        'SCAN_DIRS = ("mamey", "tools")\n'
        'CLI_TOOL_EXCLUDE_DIRS = ("blastp_monitoring",)\n'
        'CLI_TOOL_EXCLUDE_FILES = {"front_door.py"}\n'
        'import sys\n'
        f'sys.stdout.write({report!r})\n')
    for name, body in (scan_files or {}).items():
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body)
    return root


def _r(name, detail, hits=(), status='OK'):
    return {'name': name, 'status': status, 'detail': detail, 'hits': list(hits), 'waived': False}


def test_an_unchanged_packet_reports_no_delta_and_exits_zero(tmp_path):
    mod = _load()
    res = [_r('silent_swallow', '147 `except ...: pass` (ceiling 147)', ['mamey/a.py:10'])]
    base = _tree(tmp_path / 'b', res)
    cand = _tree(tmp_path / 'c', res)
    lines = []
    assert mod.compare(str(base), str(cand), lines) == 0
    assert any('silent_swallow   147 -> 147  (=)' in x for x in lines)
    assert any('headroom 0' in x for x in lines)


def test_a_new_silent_swallow_site_is_named_not_just_counted(tmp_path):
    """With zero headroom the actionable question is always WHICH site is new."""
    mod = _load()
    base = _tree(tmp_path / 'b', [_r('silent_swallow', '147 `except ...: pass` (ceiling 147)',
                                     ['mamey/a.py:10'])])
    cand = _tree(tmp_path / 'c', [_r('silent_swallow', '148 `except ...: pass` (ceiling 147)',
                                     ['mamey/a.py:10', 'mamey/b.py:44'], status='WARN')],
                 passed=False)
    lines = []
    assert mod.compare(str(base), str(cand), lines) == 1
    assert any('NEW      mamey/b.py:44' in x for x in lines)
    assert any('BREACH' in x for x in lines)
    assert not any('mamey/a.py:10' in x and 'NEW' in x for x in lines)


def test_a_removed_site_is_reported_as_paydown(tmp_path):
    mod = _load()
    base = _tree(tmp_path / 'b', [_r('silent_swallow', '147 `except ...: pass` (ceiling 147)',
                                     ['mamey/a.py:10', 'mamey/b.py:44'])])
    cand = _tree(tmp_path / 'c', [_r('silent_swallow', '146 `except ...: pass` (ceiling 147)',
                                     ['mamey/a.py:10'])])
    lines = []
    assert mod.compare(str(base), str(cand), lines) == 0
    assert any('REMOVED  mamey/b.py:44' in x for x in lines)
    assert any('(-1)' in x for x in lines)


def test_turning_a_green_base_red_is_a_finding_even_without_a_ceiling_crossing(tmp_path):
    """print_calls sits ABOVE its ceiling under a waiver, so `tc > ceiling >= tb` never fires —
    the honest signal is the strict verdict flipping."""
    mod = _load()
    base = _tree(tmp_path / 'b', [_r('print_calls', '1323 direct terminal-emission calls (ceiling 1280)',
                                     status='WARN')], passed=True)
    cand = _tree(tmp_path / 'c', [_r('print_calls', '1324 direct terminal-emission calls (ceiling 1280)',
                                     status='WARN')], passed=False)
    lines = []
    assert mod.compare(str(base), str(cand), lines) == 1
    assert any('turns a green base red' in x for x in lines)
    assert any('print_calls      1323 -> 1324  (+1)' in x for x in lines)


def test_print_calls_attribution_is_supplied_because_repo_health_reports_none(tmp_path):
    """repo_health emits zero `hits` for print_calls; the metric with no waiver headroom is the one
    with no attribution, so the tool counts the sites itself."""
    mod = _load()
    src = 'def f():\n    print("a")\n'
    base = _tree(tmp_path / 'b', [_r('print_calls', '1 direct terminal-emission calls (ceiling 1280)')],
                 scan_files={'mamey/x.py': src})
    cand = _tree(tmp_path / 'c', [_r('print_calls', '2 direct terminal-emission calls (ceiling 1280)')],
                 scan_files={'mamey/x.py': src + 'def g():\n    print("b")\n'})
    lines = []
    mod.compare(str(base), str(cand), lines)
    assert any('NEW      mamey/x.py:4' in x for x in lines)


def test_a_counter_that_disagrees_with_repo_health_says_so_instead_of_being_trusted(tmp_path):
    mod = _load()
    base = _tree(tmp_path / 'b', [_r('print_calls', '999 direct terminal-emission calls (ceiling 1280)')],
                 scan_files={'mamey/x.py': 'print("a")\n'})
    cand = _tree(tmp_path / 'c', [_r('print_calls', '999 direct terminal-emission calls (ceiling 1280)')],
                 scan_files={'mamey/x.py': 'print("a")\n'})
    lines = []
    mod.compare(str(base), str(cand), lines)
    assert any('UNRELIABLE' in x for x in lines)


def test_the_exclusion_rules_are_read_from_the_target_tree_not_hardcoded(tmp_path):
    """Hardcoding a copy of CLI_TOOL_EXCLUDE_FILES drifted by 70 sites on the first run."""
    mod = _load()
    root = _tree(tmp_path / 'b', [], scan_files={
        'tools/front_door.py': 'print("receipt")\n',      # excluded by name, tools/ only
        'mamey/front_door.py': 'print("library debt")\n',  # same basename, must STAY counted
        'tools/blastp_monitoring/m.py': 'print("excluded dir")\n',
    })
    scan, xdirs, xfiles = mod._scan_rules(str(root))
    assert scan == ('mamey', 'tools') and 'front_door.py' in xfiles
    assert 'blastp_monitoring' in xdirs and '__pycache__' in xdirs
    sites = mod._print_sites(str(root))
    assert 'mamey/front_door.py:1' in sites
    assert not any(s.startswith('tools/front_door.py') for s in sites)
    assert not any('blastp_monitoring' in s for s in sites)


def test_a_patch_that_does_not_apply_refuses_instead_of_pricing_the_wrong_tree(tmp_path):
    mod = _load()
    base = _tree(tmp_path / 'b', [], scan_files={'mamey/x.py': 'print("a")\n'})
    pdir = tmp_path / 'patches'
    pdir.mkdir()
    (pdir / '001_bad.diff').write_text(
        '--- a/mamey/x.py\n+++ b/mamey/x.py\n@@ -1 +1 @@\n-print("NOT THE BASE")\n+print("b")\n')
    with pytest.raises(SystemExit) as e:
        mod._apply_patches(str(base), str(pdir), str(tmp_path / 'dest'))
    assert 'does not apply' in str(e.value)


def test_an_empty_patch_directory_refuses_rather_than_reporting_a_clean_zero(tmp_path):
    mod = _load()
    base = _tree(tmp_path / 'b', [])
    (tmp_path / 'empty').mkdir()
    with pytest.raises(SystemExit) as e:
        mod._apply_patches(str(base), str(tmp_path / 'empty'), str(tmp_path / 'dest'))
    assert 'no .diff' in str(e.value)


# --- v9.7.420: the private scanner drifted from the counter it reports on -------------------

def test_the_attribute_form_is_counted_like_repo_health_does(tmp_path):
    """Reported by the .420 candidate review: "private delta scanner misses qualified console calls".

    v9.7.418 taught `check_print_calls` to count `_console.emit(...)`. This scanner kept counting
    only the bare Name, so a file with one bare and two qualified calls reported ONE site against
    repo_health's THREE. The cross-check said the attribution was unreliable — which is honest, and
    still wrong.
    """
    mod = _load()
    root = _tree(tmp_path / 'b', [], scan_files={'mamey/probe.py':
        "import _console\nfrom _console import emit\n\n\ndef f():\n"
        "    emit('a')\n    _console.emit('b')\n    _console.emit('c')\n"})
    sites = [s for s in mod._print_sites(str(root)) if 'probe.py' in s]
    assert len(sites) == 3, f"expected 3 emission sites, counted {len(sites)}: {sites}"


def test_alias_resolution_is_delegated_to_the_target_tree(tmp_path):
    """One source of truth: the aliases come from the tree's own repo_health, not a private copy."""
    mod = _load()
    root = _tree(tmp_path / 'b', [], scan_files={'mamey/probe.py':
        "import _console as c\nfrom _console import emit\n\n\ndef f():\n    c.emit('x')\n"})
    assert len([s for s in mod._print_sites(str(root)) if 'probe.py' in s]) == 1


def test_an_unrelated_attribute_call_is_not_counted(tmp_path):
    mod = _load()
    root = _tree(tmp_path / 'b', [], scan_files={'mamey/probe.py':
        "import logging\nlog = logging.getLogger(__name__)\n\n\ndef f():\n    log.print('x')\n"})
    assert not [s for s in mod._print_sites(str(root)) if 'probe.py' in s]
