"""The bundled 16S family must resolve its workspace, not carry one.

DEFECT, measured 2026-09-08 by AST over the nine loose sources
(`Tools/build_16s_db.py`, `fetch_16s_records.py`, `esearch_16s_by_attribute.py`,
`rank_16s_records.py`, `panel_from_16s_db.py`, `extract_16s_from_genome.py`,
`audit_16s_merges.py`, plus `tip_label.py` and `outgroup_sanity_gate.py`):

    files carrying a personal-home workspace literal      7 of 9
    absolute-path module constants derived from it       19
    bare `print(` calls                                  43

A bundled tool cannot do this. `tests/test_workspace_path_portability.py` forbids the literal
outright ("publishing this exposes a username and private folder layout"), and on any machine
that is not the one the tools were written on every one of those 19 constants points at nothing.
The 43 bare prints are the second, quieter cost: `tools/repo_health.py` counts `print(` in
`mamey/` and `tools/` as a ratchet, measured at **1320 against a ceiling of 1280** on sealed
v9.7.413 — already over — so 43 more would deepen a breached ratchet for no reason.
`tools/_console.py` exists for exactly this and is a byte-identical pass-through of `print`.

The panel tool carried a fourth problem of the same family: an `except ImportError` fallback that
redefined `binomial`, `ref_label` and `query_label` inline, because the shared module lived
outside the tree. That fallback was a NINTH label writer — the precise defect `_tip_label.py` was
created to end, and its `ref_label` spelled the accession into the parentheses the type marker
uses. Bundled, the module is a sibling and the import cannot fail, so the fallback is gone.

Hermetic: reads the source of the shipped files and imports them with the environment pinned to
tmp_path. No network, no BLAST, no database.
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"

FAMILY = [
    "phylo_16s_build_db.py", "phylo_16s_fetch.py", "phylo_16s_esearch.py", "phylo_16s_rank.py",
    "phylo_16s_panel.py", "phylo_16s_from_genome.py", "phylo_16s_audit_merges.py",
    "_tip_label.py", "phylo_outgroup_gate.py",
]

# Any absolute path under somebody's home directory. Deliberately generic — this must fail for
# ANY operator's literal, not only the one that happened to be committed. It is written as a
# character class rather than a literal so this file does not itself trip the portability guard.
PERSONAL_ROOT = re.compile(r"/(?:Users|home)/[A-Za-z0-9._-]+/")

# A bare `print(` — `logger.print(...)` and `emit(` are not counted, matching
# tools/repo_health.check_print_calls.
BARE_PRINT = re.compile(r"(?<![\w.])print\(")


def _present() -> list[Path]:
    paths = [TOOLS / n for n in FAMILY]
    missing = [p.name for p in paths if not p.is_file()]
    assert not missing, f"the 16S family is not in tools/: missing {missing}"
    return paths


def _load(name: str):
    path = TOOLS / name
    spec = importlib.util.spec_from_file_location(f"_v415_{path.stem}", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_no_personal_home_path_in_the_bundled_16s_family():
    """7 of 9 carried one. A shipped tool that names an operator's home is broken everywhere else."""
    offenders = []
    for p in _present():
        for i, line in enumerate(p.read_text(errors="replace").splitlines(), 1):
            if PERSONAL_ROOT.search(line):
                offenders.append(f"{p.name}:{i}: {line.strip()[:90]}")
    assert not offenders, (
        "a hardcoded personal workspace path survives; resolve through _phylo16s.root() "
        "(SAPOTE_WORKSPACE_ROOT / SAPOTE_ROOT / mamey.workspace_root):\n" + "\n".join(offenders))


def test_the_root_actually_follows_the_environment(monkeypatch, tmp_path):
    """Not just 'no literal' — the constants must MOVE when the root moves."""
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.delenv("SAPOTE_16S_SQLITE", raising=False)
    monkeypatch.delenv("PHYLO_BLAST_PDF_HITS", raising=False)
    mod = _load("phylo_16s_rank.py")
    assert str(tmp_path) in mod.DB, f"DB did not follow the root: {mod.DB}"
    assert str(tmp_path) in mod.PDFHITS, f"PDFHITS did not follow the root: {mod.PDFHITS}"


def test_the_database_path_is_overridable_by_one_variable(monkeypatch, tmp_path):
    """An operator must be able to pin the store without reproducing the folder layout."""
    pinned = tmp_path / "elsewhere" / "rrna16s.sqlite"
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("SAPOTE_16S_SQLITE", str(pinned))
    mod = _load("phylo_16s_build_db.py")
    assert mod.DB == str(pinned), mod.DB


def test_no_bare_print_in_the_bundled_16s_family():
    """43 across the nine sources, into a print_calls ratchet already at 1320/1280."""
    counts = {p.name: len(BARE_PRINT.findall(p.read_text(errors="replace"))) for p in _present()}
    over = {k: v for k, v in counts.items() if v}
    assert not over, (
        f"{sum(over.values())} bare print( call(s) in {len(over)} file(s): {over}. "
        f"Use `from _console import emit` — it is a pass-through of print, so stdout is "
        f"byte-identical and repo_health's print_calls ratchet does not move.")


def test_the_panel_imports_the_shared_label_module_instead_of_redefining_it():
    """The `except ImportError` fallback was a ninth tip-label writer inside the panel writer."""
    src = (TOOLS / "phylo_16s_panel.py").read_text(errors="replace")
    assert "from _tip_label import" in src, (
        "the panel must import the shared label module, not carry its own copy")
    assert "except ImportError" not in src, (
        "the fallback label writers are still here. `_tip_label.py` exists because eight separate "
        "writers produced four different accession defects in one day; a ninth defeats it.")
    for fn in ("def binomial(", "def ref_label(", "def query_label("):
        assert fn not in src, f"{fn.strip('def (')} is redefined locally in the panel writer"


def test_every_bundled_16s_tool_parses():
    """REGRESSION GUARD (passes on both trees): a portability pass that breaks a script is worse
    than the path it removed — the same assertion tests/test_workspace_path_portability.py makes
    of deliverable_tools/."""
    bad = []
    for p in _present() + [TOOLS / "_phylo16s.py"]:
        if not p.is_file():
            continue
        try:
            compile(p.read_text(encoding="utf-8"), str(p), "exec")
        except SyntaxError as exc:
            bad.append(f"{p.name}: {exc}")
    assert not bad, "syntax errors after the portability pass:\n" + "\n".join(bad)


@pytest.mark.parametrize("name", ["_tip_label.py", "phylo_outgroup_gate.py"])
def test_the_pure_helpers_import_with_no_workspace_at_all(monkeypatch, tmp_path, name):
    """REGRESSION GUARD (passes on both trees). These two touch no path and no external tool, so
    they must load with the root pointing at an EMPTY directory — which is what a fresh install
    looks like, and the state in which the rest of the family correctly refuses."""
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(tmp_path))
    mod = _load(name)
    assert mod.__doc__


def test_the_shipped_label_helper_is_the_current_one(monkeypatch, tmp_path):
    """REGRESSION GUARD (passes on both trees): the version landed here must be the one carrying
    `species_from_tip()` and `outgroup_label()`, not an older copy.

    `species_from_tip` is why this matters. `build_cohort_trees_v2.py` derived a reference label
    with `binomial(tip.replace("_", " "))`, which rewrites the ACCESSION as well, so
    `NR_151944.1_Micromonospora_ureilytica` became `NR 151944.1 Micromonospora ureilytica`, the
    leading-accession strip stopped matching, and the function returned "". Measured 2026-09-08
    across `September 7 2026/COHORT_TREES_2026-09/`: **8,508 of 8,508 reference rows in all 30
    panels published as `(unnamed) (NR_151944.1)`** — including the 20 *Candidatus* Streptomyces
    philanthi biovar tips, the described beewolf symbionts, which are the most relevant
    comparators a bee panel can carry.
    """
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(tmp_path))
    mod = _load("_tip_label.py")
    assert hasattr(mod, "species_from_tip"), (
        "the bundled copy predates species_from_tip(); shipping the older one re-opens the "
        "(unnamed) defect the module was extended to close")
    assert hasattr(mod, "outgroup_label")
    assert mod.species_from_tip("NR_151944.1_Micromonospora_ureilytica") == (
        "Micromonospora ureilytica", "NR_151944.1")
    assert mod.query_label("QUERY_A", "plant", "NR_151944.1") == "QUERY_A [plant] (NR_151944.1)"
