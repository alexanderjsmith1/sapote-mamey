"""Card 466 (ruling 234): multi-reference comparison, aligned layout. Locus contigs sit under the top reference genes
they match, reversed contigs are turned, unmatched reference genes leave a gap, and genomes with an empty ORGANISM line
get their own name."""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytest.importorskip("matplotlib")


def _load():
    sys.path.insert(0, str(ROOT / "tools"))
    spec = importlib.util.spec_from_file_location("mrc466", ROOT / "tools" / "multi_reference_comparison.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _gene(i, s, e, st):
    return {"i": i, "id": f"g{i:03d}", "start": s, "end": e, "strand": st, "name": f"r{i}"}


def _prot(contig, s, e, st):
    return {"contig": contig, "start": s, "end": e, "strand": st, "tag": None, "aa": "M", "kind": "biosynthetic"}


def _model():
    prots = {"a1": _prot("cA", 0, 1000, 1), "a2": _prot("cA", 1000, 2000, 1),
             "b1": _prot("cB", 0, 1000, -1), "b2": _prot("cB", 1000, 2000, -1),
             "c1": _prot("cC", 100, 1100, 1)}
    for q, p in prots.items():
        p["tag"] = q
    top = {"accession": "Top_region001", "display_id": "TOP00000000", "compound": "Genus alpha", "description": "", "also": [],
           "genes": [_gene(i, (i - 1) * 1000, i * 1000, 1) for i in range(1, 7)],
           # a1-a2 match genes 1-2; contig B matches 6 and 5 the other way round; genes 3 and 4 have no partner
           "pairs": [("a1", 1, 90.0, 500.0), ("a2", 2, 90.0, 400.0), ("b1", 6, 90.0, 450.0), ("b2", 5, 90.0, 350.0)]}
    second = {"accession": "Second_region002", "display_id": "SEC00000000", "compound": "Genus beta", "description": "",
              "also": [], "genes": [_gene(1, 0, 1000, -1), _gene(2, 1000, 2000, -1), _gene(3, 3000, 4000, -1)],
              # reversed against contig A (two shared genes, enough to carry the row); contig C matches only here
              "pairs": [("a1", 2, 80.0, 300.0), ("a2", 1, 80.0, 300.0), ("c1", 3, 70.0, 200.0)]}
    return {"label": "AS-1", "bgc": "BGC001", "prots": prots, "names": {},
            "segments": [("cA · BGC001", ["a1", "a2"]), ("cB · no region", ["b1", "b2"]), ("cC · no region", ["c1"])],
            "regions": [{"contig": "cA", "identity": "AS-1 / cA / region001 / BGC001"}],
            "source": "reference-genome antiSMASH regions", "refs": [top, second]}


def _mid(v):
    return (v[0] + v[1]) / 2


def test_each_locus_gene_sits_over_its_partner_in_the_top_reference():
    mrc = _load()
    m = _model()
    lay = mrc.aligned_layout(m)
    top = lay["top"]["place"]
    for q, i, *_ in m["refs"][0]["pairs"]:
        assert abs(_mid(lay["qx"][q]) - _mid(top[i])) <= 100, (q, i)
    seg = {r["heading"]: r for r in lay["segments"]}
    assert seg["cA · BGC001"]["orientation"] == 1
    assert seg["cB · no region"]["orientation"] == -1          # its matches run the other way: drawn reversed
    assert lay["qx"]["b1"][2] == 1                             # a minus-strand gene on a reversed contig points right
    # reference genes 3 and 4 have no partner: no locus gene is drawn over them
    gap = (top[3][0], top[4][1])
    assert not any(a < gap[1] and b > gap[0] for q, (a, b, _) in lay["qx"].items() if q[0] in "ab")


def test_other_rows_follow_the_locus_and_a_contig_without_a_top_match_is_placed_by_the_next_row():
    mrc = _load()
    m = _model()
    lay = mrc.aligned_layout(m)
    row = lay["rows"][0]
    assert row["orientation"] == -1 and row["pairs_used"] == 2
    for q, i in (("a1", 2), ("a2", 1)):
        assert abs(_mid(lay["qx"][q]) - _mid(row["place"][i])) <= 100
    c = next(r for r in lay["segments"] if r["heading"].startswith("cC"))
    assert c["placed_by_rank"] == 2 and c["anchored"]
    assert abs(_mid(lay["qx"]["c1"]) - _mid(row["place"][3])) <= 1


def test_one_shared_gene_cannot_carry_a_row():
    mrc = _load()
    m = _model()
    m["refs"][1]["pairs"] = [("a1", 2, 80.0, 300.0), ("c1", 3, 70.0, 200.0)]
    lay = mrc.aligned_layout(m)
    c = next(r for r in lay["segments"] if r["heading"].startswith("cC"))
    assert not c["anchored"]                                   # drawn at the right end, as deposited
    assert c["span_bp"][0] > max(v[1] for v in lay["top"]["place"].values())


def test_weighted_median_follows_the_big_genes():
    mrc = _load()
    assert mrc._wmedian([0, 0, 0, 100], [1, 1, 1, 10]) == 100
    assert mrc._wmedian([5, 1, 3], [1, 1, 1]) == 3


def test_drawing_writes_caption_file_and_keeps_text_at_8_pt(tmp_path):
    mrc = _load()
    m = _model()
    mrc.draw_aligned(m, mrc.aligned_layout(m), tmp_path, width_in=9.6, dpi=60)
    for f in ("comparison.png", "comparison.pdf", "comparison.svg", "CAPTION.md"):
        assert (tmp_path / f).exists()
    cap = (tmp_path / "CAPTION.md").read_text()
    assert "weighted by bitscore" in cap and "AS-1 / cA / region001 / BGC001" in cap
    assert m["aligned_layout"]["width_in"] == 9.6 and m["text_overlaps"] == []
    mrc.draw_aligned(m, mrc.aligned_layout(m), tmp_path / "narrow", width_in=6.5, dpi=60)


def test_empty_organism_line_falls_back_to_the_definition(tmp_path):
    mrc = _load()
    empty = tmp_path / "a.gbk"
    empty.write_text("LOCUS       x\nDEFINITION  Nocardia sp. X1 contig_12, whole genome shotgun\n            sequence.\n"
                     "SOURCE      .\n  ORGANISM  .\n            .\nFEATURES             Location/Qualifiers\n")
    named = tmp_path / "b.gbk"
    named.write_text("LOCUS       y\nDEFINITION  something.\n  ORGANISM  Nocardia alba\nFEATURES             Location/Qualifiers\n")
    assert mrc.organism(empty) == "Nocardia sp. X1"
    assert mrc.organism(named) == "Nocardia alba"
