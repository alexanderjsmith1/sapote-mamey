"""v9.7.396: determinism regression for emitted artifacts — set/dict iteration order must
never reach a sealed receipt, a published figure's contents, or a tree's rooting choice.

The engine's motto is "deterministic extraction, judgment deferred", and the project's
integrity model is checksum-based byte comparison rather than version control. Both break the
moment an emitted artifact's contents depend on `PYTHONHASHSEED`: two runs of the same input
produce byte-different receipts, and a checksum mismatch stops meaning "something changed".

Three observed instances on the sealed v9.7.395 tree, all reproduced across hash seeds:
  1. seal_package._gate_figure_references iterated a bare `set()` of figure references, and
     those findings are written verbatim into seal_findings.csv, seal_status.json,
     DEBUG_RECEIPT.md and figure_reference_validation.csv;
  2. cross_strain_figures built its heatmap token axis from a bare set union — Counter's
     most_common() is a STABLE sort, so tied tokens broke by randomised insertion order and a
     tie straddling the top-16 cut changed WHICH tokens the published figure showed;
  3. relabel_and_render picked the rooting outgroup with next() over a randomised dict, so an
     identical tree rooted on a different taxon between runs whenever more than one tip
     matched the hint.  Ambiguity now refuses before any intermediate or final output.

These tests pin the invariant rather than the instances: run the code under several
PYTHONHASHSEED values and require identical output.
"""
from __future__ import annotations

import os
import json
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SEEDS = ("0", "1", "2", "3", "4", "5")


def _under_seeds(code: str) -> list[str]:
    """Run `code` once per hash seed in a fresh interpreter; return the stdout of each."""
    outs = []
    for seed in SEEDS:
        env = {**os.environ, "PYTHONHASHSEED": seed}
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                           cwd=str(ROOT), env=env, timeout=120)
        assert r.returncode == 0, r.stderr[-2000:]
        outs.append(r.stdout)
    return outs


def test_seal_receipt_findings_are_order_stable(tmp_path):
    """The figure-reference gate's findings are emitted verbatim into four sealed artifacts.

    (Named without the word "figure": conftest classifies any node id containing it as slow,
    and this test renders nothing — it must stay in the fast partition.)
    """
    pkg = tmp_path / "package"
    pkg.mkdir()
    refs = [f"panel_{n}_fig.png" for n in
            ("alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel")]
    (pkg / "report.md").write_text("\n".join(f"![x]({r})" for r in refs), encoding="utf-8")
    code = (
        "import sys, json\n"
        f"sys.path.insert(0, {str(ROOT)!r})\n"
        "from mamey.seal_package import _gate_figure_references\n"
        "from pathlib import Path\n"
        f"res = _gate_figure_references(Path({str(pkg)!r}))\n"
        "print(json.dumps([f['detail'] for f in res.findings]))\n"
    )
    outs = _under_seeds(code)
    assert len(set(outs)) == 1, f"findings order varies with hash seed: {set(outs)}"


def test_cross_strain_axes_order_their_set_union():
    """The shipped heatmap axis builders must order their token union before counting.

    (Named without the word "figure" so conftest keeps it in the fast partition.)

    A source-level guard rather than a behavioural one: driving cross_strain_figures end to
    end needs a full cohort build, but the defect is entirely local — an unordered `set()`
    union feeding a Counter whose most_common() breaks ties by insertion order.
    """
    src = (ROOT / "mamey" / "cross_strain_figures.py").read_text(encoding="utf-8")
    unordered = [i for i, line in enumerate(src.splitlines(), 1)
                 if "set().union(" in line and "sorted(set().union(" not in line]
    assert not unordered, (
        "set().union(...) feeding a Counter axis must be wrapped in sorted() — tied tokens "
        f"otherwise shuffle in and out of the published figure (lines {unordered})")


def test_tied_token_axis_selection_is_stable_when_ordered():
    """Demonstrates why the guard above matters: an all-tied token population larger than the
    most_common() cut is exactly the condition under which insertion order decides which
    tokens a figure shows."""
    def axis(n_tokens: int, keep: int) -> list[str]:
        by_strain = defaultdict(Counter)
        for i in range(n_tokens):
            by_strain[f"S{i % 3}"][f"class_{i:02d}"] += 1
        union = set().union(*[set(c) for c in by_strain.values()] or [set()])
        totals = {k: sum(c[k] for c in by_strain.values()) for k in sorted(union)}
        return [k for k, _ in Counter(totals).most_common(keep)]

    first = axis(20, 16)
    assert len(first) == 16
    for _ in range(6):
        assert axis(20, 16) == first, "tied-token axis selection is not stable"


def _relabel_fixture(tmp_path, leaves):
    """Copy the tool beside a renderer spy, isolating selection from optional plot deps."""
    tool_dir = tmp_path / "tool"
    tool_dir.mkdir()
    tool = tool_dir / "relabel_and_render.py"
    shutil.copyfile(ROOT / "tools" / "relabel_and_render.py", tool)
    renderer = tool_dir / "render_clean_tree.py"
    renderer.write_text(
        "import pathlib, sys\n"
        "pathlib.Path(sys.argv[2]).write_bytes(b'rendered')\n"
        "pathlib.Path(sys.argv[2] + '.renderer-invoked').write_text(sys.argv[4])\n",
        encoding="utf-8")
    genomes = tmp_path / "genomes"
    genomes.mkdir()
    tree = tmp_path / "private analyst tree.treefile"
    tree.write_text("(" + ",".join(f"{leaf}:0.1" for leaf in leaves) + ");\n",
                    encoding="utf-8")
    output = tmp_path / "private final output.png"
    return tool, genomes, tree, output


def _run_relabel(tool, genomes, tree, output, selector=...):
    args = [sys.executable, str(tool), str(tree), str(genomes), str(output), "T1||T2"]
    if selector is not ...:
        args.append(selector)
    return subprocess.run(args, capture_output=True, text=True, timeout=120)


@pytest.mark.parametrize(
    ("selector", "expected_code", "expected_count"),
    [
        ("OUTGROUP", "OUTGROUP_SELECTOR_AMBIGUOUS", 2),
        ("absent-tip", "OUTGROUP_SELECTOR_NO_MATCH", 0),
        ("", "OUTGROUP_SELECTOR_EMPTY", 0),
    ],
)
def test_relabel_and_render_explicit_selector_refuses_without_any_output(
        tmp_path, selector, expected_code, expected_count):
    """Zero/multiple explicit matches are typed, path-redacted, pre-render refusals."""
    tool, genomes, tree, output = _relabel_fixture(
        tmp_path, ["A_OUTGROUP", "B_OUTGROUP", "AS-123"])
    r = _run_relabel(tool, genomes, tree, output, selector)
    refusal = json.loads(r.stderr)
    assert r.returncode == 2
    assert refusal == {
        "code": expected_code,
        "event": "OUTPUT_REFUSED",
        "match_count": expected_count,
        "path_disclosure": "REDACTED",
        "selector_mode": "EXPLICIT_SUBSTRING",
        "stage": "OUTGROUP_SELECTION",
    }
    assert str(tmp_path) not in r.stdout + r.stderr
    assert not output.exists()
    assert not Path(str(output) + ".renderer-invoked").exists()
    assert not tree.with_name("private analyst tree_relabeled.treefile").exists()


def test_relabel_and_render_role_suffix_fallback_requires_uniqueness(tmp_path):
    """Omitting a selector never turns multiple role-suffix tips into an implicit choice."""
    tool, genomes, tree, output = _relabel_fixture(
        tmp_path, ["A_OUTGROUP", "B_OUTGROUP", "AS-123"])
    r = _run_relabel(tool, genomes, tree, output)
    refusal = json.loads(r.stderr)
    assert r.returncode == 2
    assert refusal["code"] == "OUTGROUP_ROLE_SUFFIX_AMBIGUOUS"
    assert refusal["match_count"] == 2
    assert refusal["selector_mode"] == "ROLE_SUFFIX_FALLBACK"
    assert str(tmp_path) not in r.stdout + r.stderr
    assert not output.exists()
    assert not Path(str(output) + ".renderer-invoked").exists()


def test_relabel_and_render_explicit_unique_selector_invokes_renderer_once(tmp_path):
    """One explicit match is the only selector path that may reach downstream rendering."""
    tool, genomes, tree, output = _relabel_fixture(
        tmp_path, ["A_OUTGROUP", "B_OUTGROUP", "AS-123"])
    r = _run_relabel(tool, genomes, tree, output, "B_OUTGROUP")
    sentinel = Path(str(output) + ".renderer-invoked")
    assert r.returncode == 0, r.stderr
    assert output.read_bytes() == b"rendered"
    assert sentinel.read_text(encoding="utf-8") == "B_OUTGROUP"
    assert tree.with_name("private analyst tree_relabeled.treefile").is_file()


def test_no_bare_set_iteration_in_emitting_engine_paths():
    """Ratchet: the engine must not reintroduce bare `for x in set(...)` where the loop body
    feeds emitted output. Kept as an explicit allowlist so a new instance is a deliberate,
    reviewed decision rather than a silent regression."""
    import ast
    allow = {
        # order never reaches an artifact: every consumer of trigger_bgc_counts reads it by
        # key (external_adapters.py, cli.py), so the Counter's insertion order is not emitted.
        "mamey/source_scans.py",
    }

    def _is_bare_set_call(node) -> bool:
        return (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "set")

    offenders = []
    for py in sorted((ROOT / "mamey").rglob("*.py")):
        rel = py.relative_to(ROOT).as_posix()
        if "_vendor" in rel or rel in allow:
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:                       # not our invariant to enforce
            continue
        # Statement-level for-loops only: a generator inside sorted(...) is already ordered,
        # and matching it textually was itself a false positive of exactly this defect class.
        for node in ast.walk(tree):
            if isinstance(node, ast.For) and _is_bare_set_call(node.iter):
                offenders.append(f"{rel}:{node.lineno}")
    assert not offenders, ("bare set() iteration in engine code — wrap in sorted() if the "
                           f"result reaches output, or allowlist with a reason: {offenders}")
