"""Card attine_452_tree_pool_candida_strip: placement-tree activity strips can pool the Candida readings into one column.

The owner ruled (13 Oct) for one merged Candida panel, and the attine bioassay figure already pools Candida on one axis.
The placement tree drew one strip per Candida species instead. With the layout key tree_pool_candida (true for the
attine profile, so the paper figure needs no hand option) the loader returns one '*Candida*' column plus MRSA. The
pooled state is the strongest recorded state: a positive in any species is positive, then a tested negative, then not
tested, then blank. No state is converted into another. Synthetic data only.
"""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("placement_activity_452p", HERE / "tools" / "_placement_activity.py")
act = importlib.util.module_from_spec(spec); spec.loader.exec_module(act)


def _long(tmp_path):
    rows = [("SYN-970", "C. albicans", "90"), ("SYN-970", "C. auris", "10"), ("SYN-970", "MRSA", "5"),
            ("SYN-971", "C. albicans", "20"), ("SYN-971", "C. auris", "30"), ("SYN-971", "MRSA", "95"),
            ("SYN-972", "C. albicans", "n.t."), ("SYN-972", "C. auris", ""), ("SYN-972", "MRSA", "n.t."),
            ("SYN-973", "C. albicans", "+"), ("SYN-973", "C. auris", "−"), ("SYN-973", "MRSA", "−"),
            ("SYN-974", "C. albicans", ""), ("SYN-974", "C. auris", ""), ("SYN-974", "MRSA", ""),
            ("SYN-975", "Candida (species not named)", "85"), ("SYN-975", "C. albicans", "10"),
            ("SYN-975", "C. auris", "n.t."), ("SYN-975", "MRSA", "n.t.")]
    p = tmp_path / "long.tsv"
    p.write_text("strain\torganism\tmaterial\tbest_pct\n" + "".join(f"{s}\t{o}\tCrude extract\t{v}\n" for s, o, v in rows))
    return p


def test_pooled_column_takes_the_strongest_state_and_never_coerces(tmp_path):
    res, strips = act.load(_long(tmp_path), pool=True)
    assert [s["label"] for s in strips] == ["*Candida*", "MRSA"]
    c = {sid: row["*Candida*"] for sid, row in res.items()}
    assert c["SYN-970"] == "strong (≥80%)"          # one species active
    assert c["SYN-971"] == "tested, below 80%"       # both tested below 80
    assert c["SYN-972"] == "n.t."                    # not tested beats blank, never becomes negative
    assert c["SYN-973"] == "+"                       # a + in any species stays +
    assert c["SYN-974"] == ""                        # blank stays blank
    assert c["SYN-975"] == "strong (≥80%)"          # the species-not-recorded reading counts
    assert res["SYN-971"]["MRSA"] == "strong (≥80%)" and res["SYN-972"]["MRSA"] == "n.t."
    assert all("C. albicans" not in row for row in res.values())


def test_without_pooling_the_species_strips_are_unchanged(tmp_path):
    res, strips = act.load(_long(tmp_path))
    assert [s["label"] for s in strips] == ["C. albicans", "C. auris", "C. albicans or C. auris (not recorded)", "MRSA"]
    assert res["SYN-970"]["C. auris"] == "tested, below 80%"


def test_the_attine_layout_pools_and_moss_does_not():
    prof = json.loads((HERE / "mamey" / "data" / "bioassay_layouts.json").read_text())
    assert prof["attine"]["tree_pool_candida"] is True
    assert "tree_pool_candida" not in prof["moss"]
    assert act.profile("attine")["tree_pool_candida"] is True


def test_the_renderer_explains_the_pooled_column():
    d = (HERE / "tools" / "placement_display.py").read_text()
    assert 'get("tree_pool_candida", False)' in d and "a positive in any one is shown as positive" in d
