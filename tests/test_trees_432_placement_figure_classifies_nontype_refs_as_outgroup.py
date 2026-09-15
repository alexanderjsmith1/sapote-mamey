"""TREES_432 — placement figure classified every non-NR_ reference as an OUTGROUP.

`_render_tree` read the "genus" as the first alphabetic run of the labelmap string, and NCBI 16S
titles LEAD with the accession, so the modal "genus" was `NR` and every FJ_/MW_/PQ_/CP_ reference
was drawn grey and prefixed OUTGROUP. Now: OUTGROUP is a registry/labelmap ROLE (the bounded
`outgroup` token that outgroup_registry.get_16s writes), NR_ type-material references and other
references get their own roles, and the gate receives the exact outgroup tip identities. The
modal-organism-genus heuristic survives only as the fallback when no registry outgroup exists.
"""
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
_spec = importlib.util.spec_from_file_location("phylo_place_trees432_roles", ROOT / "tools" / "phylo_place.py")
pp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pp)

OG = "NR_000001_1_Actinoplanes_missouriensis_outgroup_for_Micromonospora"
LABELMAP = {
    "NR_179920_1_Micromonospora_deserti":
        "NR_179920.1 Micromonospora deserti strain YIM 12345 16S ribosomal RNA, partial sequence",
    "CP012345_1_Micromonospora_sp_XYZ":
        "CP012345.1 Micromonospora sp. XYZ 16S ribosomal RNA gene, partial sequence",
    "PQ361780_1_Micromonospora_taraxaci":
        "PQ361780.1 Micromonospora taraxaci strain TX-1 16S ribosomal RNA gene, partial sequence",
    OG: "NR_000001.1 Actinoplanes missouriensis strain DSM 43046 16S ribosomal RNA, partial sequence "
        "[outgroup for Micromonospora]",
    "AS-425": "AS-425",
}
# Shape of a build-ref backbone graft: rooted on the registry outgroup, pendant 0.0, the whole
# outgroup separation (0.10) on the ingroup stem.
TREE = ("(((AS-425:0.03,PQ361780_1_Micromonospora_taraxaci:0.03):0.04,"
        "(NR_179920_1_Micromonospora_deserti:0.04,CP012345_1_Micromonospora_sp_XYZ:0.04):0.04):0.10,"
        f"{OG}:0.0);")


@pytest.mark.parametrize("label", [
    "NR_179920.1 Micromonospora deserti strain YIM 12345 16S ribosomal RNA, partial sequence",
    "FJ830633.1 Micromonospora sp. SY10 16S ribosomal RNA gene, partial sequence",
    "PQ361780.1 Micromonospora taraxaci strain TX-1 16S ribosomal RNA gene",
    "NR_179920_1_Micromonospora_deserti_strain_YIM_12345",
    "OUTGROUP NR_000001.1 Micromonospora x",
])
def test_organism_genus_never_reads_the_accession_prefix(label):
    assert pp._organism_genus(label) == "Micromonospora"


def test_type_reference_is_the_nr_leading_identifier_only():
    assert pp._is_type_reference_label("NR_179920.1 Micromonospora deserti strain YIM 12345")
    assert not pp._is_type_reference_label("CP012345.1 Micromonospora sp. XYZ")
    assert not pp._is_type_reference_label("FJ830633.1 Micromonospora sp. SY10")
    assert not pp._is_type_reference_label("Micromonospora deserti (NR_179920.1)")  # not leading


def test_registry_token_is_the_only_outgroup_and_hint_is_exact_identity():
    tips = [SimpleNamespace(name=k) for k in LABELMAP if k != "AS-425"]
    og_tips, hint, source = pp._classify_outgroup_tips(tips, lambda n: LABELMAP.get(n, n))
    assert [x.name for x in og_tips] == [OG]
    assert hint == [OG] and source == "registry_outgroup_token"


def test_fallback_without_registry_token_uses_the_organism_genus():
    lm = {k: v.replace(" [outgroup for Micromonospora]", "") for k, v in LABELMAP.items()}
    lm["NR_000001_1_Actinoplanes_missouriensis"] = lm.pop(OG)
    tips = [SimpleNamespace(name=k) for k in lm if k != "AS-425"]
    og_tips, hint, source = pp._classify_outgroup_tips(tips, lambda n: lm.get(n, n))
    # NR_/CP/PQ Micromonospora references are all INGROUP; only the minority ORGANISM genus is outgroup
    assert [x.name for x in og_tips] == ["NR_000001_1_Actinoplanes_missouriensis"]
    assert hint == "Actinoplanes" and source == "modal_genus_heuristic"


def test_rendered_figure_roles_nr_type_cp_nontype_registry_outgroup(tmp_path, monkeypatch):
    pytest.importorskip("matplotlib"); pytest.importorskip("Bio")
    tree = tmp_path / "graft.newick"; tree.write_text(TREE)
    png = tmp_path / "Micromonospora_placement_tree.png"; svg = tmp_path / "Micromonospora_placement_tree.svg"
    hints = []
    monkeypatch.setattr(pp, "_graft_sane", lambda *a: (hints.append(a) or (True, "stub")))
    pp._render_tree(str(tree), LABELMAP, str(png), str(svg), "Micromonospora")
    receipt = json.loads(Path(str(svg) + ".labels.json").read_text())
    roles = receipt["roles"]
    assert roles["AS-425"] == "query"
    assert roles["NR_179920_1_Micromonospora_deserti"] == "reference_type"
    assert roles["CP012345_1_Micromonospora_sp_XYZ"] == "reference_nontype"
    assert roles["PQ361780_1_Micromonospora_taraxaci"] == "reference_nontype"
    assert roles[OG] == "outgroup"
    records = {r["tip_key"]: r for r in receipt["records"]}
    assert [k for k, r in records.items() if r["outgroup"]] == [OG]
    assert all(r["role"] == roles[k] for k, r in records.items())
    assert not any(r["label"].startswith("OUTGROUP") for k, r in records.items() if k != OG)
    assert receipt["role_basis"]["outgroup"] == "registry_outgroup_token"
    # the gate got the exact outgroup identity, on the display-rooted receipt tree
    (gated_path, hint), = hints
    assert hint == [OG]
    assert gated_path.endswith("Micromonospora_placement_tree.rooted_split.newick")
    assert Path(gated_path).is_file() and png.is_file()


def test_rendered_figure_passes_the_real_gate_with_registry_outgroup(tmp_path):
    pytest.importorskip("matplotlib"); pytest.importorskip("Bio")
    tree = tmp_path / "graft.newick"; tree.write_text(TREE)
    png = tmp_path / "Micromonospora_placement_tree.png"; svg = tmp_path / "Micromonospora_placement_tree.svg"
    pp._render_tree(str(tree), LABELMAP, str(png), str(svg), "Micromonospora")
    assert png.is_file()
