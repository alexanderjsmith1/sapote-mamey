"""The gap-rescue-to-locus-map adapter: one correspondence per AS gene, real gene names only, long references cropped,
and text kept out of the ribbon space (top row above, bottom row below, middle row heading on the left)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import rescue_locus_comparison as rlc  # noqa: E402


def _g(i, s, e, group="", label=""):
    return {"id": f"g{i}", "label": label, "start": s, "end": e, "strand": 1, "aa_sha256": "0" * 64, "group": group}


def _spec(ref_len=10000, partners=False):
    core = {"id": "core", "kind": "bgc", "orientation": 1, "anchor_gene": "g1",
            "genes": [_g(1, 0, 900, "G1", "KS"), _g(2, 1000, 1900, "G2", "")]}
    ref = {"id": "ref", "kind": "reference", "orientation": 1, "anchor_gene": "g1", "label": "MIBiG X",
           "genes": [_g(i, i * 1000, i * 1000 + 900, "G1" if i == 1 else "G2" if i == 2 else "") for i in range(1, ref_len // 1000)]}
    tracks = [core, ref]
    if partners:
        tracks.append({"id": "p1", "kind": "bgc", "orientation": 1, "anchor_gene": "g9", "genes": [_g(9, 0, 900, "", "")]})
    links = [{"a": ["core", "g1"], "b": ["ref", "g1"], "identity_pct": 75.0, "evidence": "x"},
             {"a": ["core", "g2"], "b": ["ref", "g2"], "identity_pct": 61.4, "evidence": "x"}]
    return {"tracks": tracks, "links": links, "display": {"width_in": 13}}


def test_short_gene_names_only():
    assert rlc.short_gene_name("phzB") == "phzB" and rlc.short_gene_name("ccrA") == "ccrA"
    assert rlc.short_gene_name("D581_RS0125600") == "" and rlc.short_gene_name("AIE47503.1") == ""


def test_long_reference_is_cropped_and_short_one_is_not():
    s = _spec(ref_len=60000)
    assert rlc.crop_long_reference(s) is True
    ids = [g["id"] for g in s["tracks"][1]["genes"]]
    assert ids[0] == "g1" and len(ids) <= 2 + 3 + 1  # first..last matched gene plus up to 3 flanking genes
    assert rlc.crop_long_reference(_spec(ref_len=4000)) is False


def test_sides_put_text_outside_the_ribbons_and_identity_on_as_labels():
    s = _spec(partners=True)
    rlc.sides(s["tracks"], s["links"])
    core, ref, p1 = s["tracks"]
    assert core["label_side"] == "above" and p1["label_side"] == "below"
    assert ref["label_side"] == "none" and ref["heading_side"] == "left"
    assert core["genes"][0]["label"] == "KS 75%" and core["genes"][1]["label"] == "61%"
    s2 = _spec()
    rlc.sides(s2["tracks"], s2["links"])
    assert s2["tracks"][1]["label_side"] == "below"  # two rows: the reference is the bottom row
