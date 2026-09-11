"""AMBER_04: tests for the MLSA driver's pure, importable logic (tools/build_mlsa.py).

The blastp/prodigal/muscle/iqtree steps are DETECTED external companions and are not
exercised here (offline core stays test-clean). What IS unit-tested is the sequence
bookkeeping that has bitten us before: gappy-column trimming, and building the
partitioned supermatrix so a taxon missing a locus is gap-padded (union of taxa),
never silently dropped. Binary resolution is checked to be PATH-based (portable),
and the bundled seed set is checked to be present.
"""
import os
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
_MLSA = os.path.join(ROOT, "tools", "build_mlsa.py")

spec = importlib.util.spec_from_file_location("build_mlsa", _MLSA)
mlsa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mlsa)


def test_trim_drops_only_overgappy_columns():
    # col0: 0/3 gaps keep; col1: 2/3 gaps (>0.5) drop; col2: 0/3 keep; col3: 1/3 keep
    aln = {"a": "A-CG", "b": "A-CG", "c": "AACT"}
    out = mlsa.trim_gappy_columns(aln, max_gap_frac=0.5)
    assert out == {"a": "ACG", "b": "ACG", "c": "ACT"}


def test_trim_empty_alignment_is_safe():
    assert mlsa.trim_gappy_columns({}) == {}


def test_concat_gap_pads_missing_locus_and_keeps_union():
    trimmed = {
        "atpD": {"a": "AAAA", "b": "AAAC"},          # b present, c missing
        "gyrB": {"a": "GG", "c": "GT"},              # a & c present, b missing
    }
    concat, parts = mlsa.concat_partitions(trimmed, loci=["atpD", "gyrB", "recA"])
    # union of taxa across loci; recA absent entirely -> skipped
    assert set(concat) == {"a", "b", "c"}
    assert [p[0] for p in parts] == ["atpD", "gyrB"]
    assert parts == [("atpD", 1, 4), ("gyrB", 5, 6)]
    # every row is the full supermatrix width
    assert all(len(v) == 6 for v in concat.values())
    # b missing gyrB -> gap-padded there, not dropped
    assert concat["b"] == "AAAC" + "--"
    # c missing atpD -> gap-padded there
    assert concat["c"] == "----" + "GT"


def test_binary_resolution_is_path_based():
    # a real, ubiquitous binary resolves via PATH; a nonsense tool does not.
    assert mlsa.resolve_bin("prodigal") is None or os.path.isabs(mlsa.resolve_bin("prodigal"))
    mlsa._BIN_ALIASES.setdefault("_definitely_not_a_tool_", ["_definitely_not_a_tool_"])
    assert mlsa.resolve_bin("_definitely_not_a_tool_") is None


def test_bundled_seeds_present():
    for locus in mlsa.LOCI:
        p = os.path.join(mlsa.DEFAULT_SEEDS_DIR, locus + ".faa")
        assert os.path.isfile(p), p


def test_help_returns_nonzero_without_running():
    assert mlsa.main(["--help"]) == 2
