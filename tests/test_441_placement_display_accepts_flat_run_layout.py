"""v9.7.441 card 283f1f96 (Finding 7): placement_display accepts the flat layout phylo_place.py
writes (X/epa_result.newick) as well as the nested one it historically required (X/report/...)."""
import importlib.util, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location("placement_display", ROOT / "tools" / "placement_display.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod


def test_flat_layout(tmp_path):
    for f in ("epa_result.newick", "ref.aln.fasta", "query.aligned.fasta"):
        (tmp_path / f).write_text(">x\nA\n")
    src, refs, q = _load()._run_layout(tmp_path)
    assert (src, refs, q) == (tmp_path / "epa_result.newick", tmp_path / "ref.aln.fasta", tmp_path / "query.aligned.fasta")


def test_nested_layout_preferred(tmp_path):
    for d, f in (("report", "epa_result.newick"), ("refpkg", "ref.aln.fasta"), ("place", "query.aligned.fasta")):
        (tmp_path / d).mkdir(); (tmp_path / d / f).write_text(">x\nA\n")
    (tmp_path / "epa_result.newick").write_text(">flat\nA\n")
    src, refs, q = _load()._run_layout(tmp_path)
    assert src == tmp_path / "report/epa_result.newick" and refs == tmp_path / "refpkg/ref.aln.fasta"


def test_missing_still_named_by_first_candidate(tmp_path):
    src, refs, q = _load()._run_layout(tmp_path)
    assert src == tmp_path / "report/epa_result.newick" and not src.exists()
