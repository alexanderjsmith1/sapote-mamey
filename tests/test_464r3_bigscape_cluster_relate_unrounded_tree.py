"""cluster_relate builds the tree from unrounded distances; rounding is display-only in the CSV."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = {("A", "B"): 0.30004, ("A", "C"): 0.29996, ("B", "C"): 0.9}


def _load(monkeypatch):
    spec = importlib.util.spec_from_file_location("_cr_464r3", ROOT / "tools" / "cluster_relate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "_genes", lambda path: [Path(path).stem])
    monkeypatch.setattr(module, "_aligner", lambda: None)

    def fake(left, right, al, min_id):
        key = tuple(sorted((left[0], right[0])))
        dist = DIST[key]
        return 1, 0.5, 1 - dist, dist
    monkeypatch.setattr(module, "_one_to_one_result", fake)
    return module


def test_near_tie_is_not_created_by_rounding(monkeypatch, tmp_path):
    module = _load(monkeypatch)
    labels = ["A", "B", "C"]
    _, D, _, _ = module.pairwise_distances(labels, [f"{x}.gbk" for x in labels], metric="one_to_one_v1")
    assert D[0][1] == 0.30004 and D[0][2] == 0.29996
    newick = module.upgma_newick(labels, D)
    # A and C are the closer pair once rounding no longer forces a tie with A-B.
    assert "(A:0.1500,C:0.1500)" in newick
    assert "(A:0.1500,B:0.1500)" not in newick


def test_csv_still_rounds_and_contract_states_precision(monkeypatch, tmp_path):
    module = _load(monkeypatch)
    monkeypatch.setattr(module, "make_dendrogram", lambda labels, D, outdir, title: str(Path(outdir) / "dendrogram.png")
                        if (Path(outdir) / "dendrogram.png").write_bytes(b"png") else "")
    out = tmp_path / "out"
    assert module.main(["--metric", "one_to_one_v1", "--gbk", "A:A.gbk", "--gbk", "B:B.gbk",
                        "--gbk", "C:C.gbk", "--outdir", str(out)]) == 0
    rows = (out / "distance_matrix.csv").read_text().splitlines()
    assert rows[1] == "A,0.0,0.3,0.3"
    contract = json.loads((out / "comparison_contract.json").read_text())
    assert "unrounded" in contract["distance_precision"]
    assert "input order" in contract["upgma_tie_policy"]
