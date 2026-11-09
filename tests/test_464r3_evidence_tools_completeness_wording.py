"""cluster_completeness: a zero denominator is a hold, and the output never claims orthology."""
import json
from tests.test_cluster_completeness import _load, _mk, A, B, C, D, E


def test_zero_denominator_is_unmeasured_not_complete(tmp_path, capsys):
    m = _load()
    _mk(tmp_path / "r1.gbk", [A]); _mk(tmp_path / "r2.gbk", [B]); _mk(tmp_path / "r3.gbk", [C])
    _mk(tmp_path / "q.gbk", [D])
    out = tmp_path / "out"
    assert m.main(["--query", f"q:{tmp_path / 'q.gbk'}", "--reference", f"r1:{tmp_path / 'r1.gbk'}",
                   "--reference", f"r2:{tmp_path / 'r2.gbk'}", "--reference", f"r3:{tmp_path / 'r3.gbk'}",
                   "--outdir", str(out)]) == 0
    rep = json.loads((out / "q_completeness.json").read_text())
    assert rep["n_cluster_genes"] == 0
    assert rep["completeness_pct"] is None
    assert rep["denominator_state"] == "UNMEASURED_NO_ELIGIBLE_REFERENCE_GENES"
    assert rep["tier"] == "unmeasured"
    assert "No reference cluster gene is missing" not in rep["interpretation"]
    assert "HOLD" in capsys.readouterr().out


def test_interpretation_does_not_claim_orthology_or_biology(tmp_path):
    m = _load()
    for name in ("r1", "r2"):
        _mk(tmp_path / f"{name}.gbk", [A, B, C, D, E])
    _mk(tmp_path / "q.gbk", [A, B, D, E])
    rep = m.assess(m._genes(tmp_path / "q.gbk"),
                   [(n, m._genes(tmp_path / f"{n}.gbk")) for n in ("r1", "r2")])
    text = m.interpret(rep, "q", "interior", ["r1", "r2"])
    assert "orthology" not in text.replace("not orthology", "")
    assert "genuine biological difference" not in text
    assert "reference-dependent similarity" in text
