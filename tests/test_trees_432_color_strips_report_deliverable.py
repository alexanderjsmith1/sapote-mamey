"""TREES_432 — the colour-strip placement figure is the required deliverable of `phylo_place.py report`.

build_placement_panel_inputs: a deposited value in a named bin wins; a reviewed collection value
fills a deposited gap; a documented deposited source outside every bin shows as "Other documented";
a tip with no geography from any admitted state is omitted and listed with its title; the registry
outgroup roots the tree and is dropped when it lacks a category; an owner ruling override beats the
owner table; a query with no owner row is omitted, never coloured by guess; the provenance table
names the state of every cell. phylo_place.report writes COLOR_STRIPS_NOT_RENDERED.txt with the
exact reason when the owner table or Rscript is missing, and never raises.
"""
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
pytest.importorskip("Bio")
_spec = importlib.util.spec_from_file_location("bpi_432", ROOT / "tools" / "build_placement_panel_inputs.py")
bpi = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bpi)

OG = "Outgenus_thermophila_ATCC_1_NR_000009_1_outgroup_for_Genus_Outgenus_thermophila_strain_ATCC_1_16S_ribosomal_RNA_partial_sequence"
TIPS = {
    "NR_000001_1_Genus_alpha_strain_A1_16S_ribosomal_RNA_partial_sequence": "NR_000001.1 Genus alpha strain A1 16S ribosomal RNA, partial sequence",
    "NR_000002_1_Genus_beta_strain_B2_16S_ribosomal_RNA_partial_sequence": "NR_000002.1 Genus beta strain B2 16S ribosomal RNA, partial sequence",
    "NR_000003_1_Genus_gamma_strain_C3_16S_ribosomal_RNA_partial_sequence": "NR_000003.1 Genus gamma strain C3 16S ribosomal RNA, partial sequence",
    "NR_000004_1_Genus_delta_strain_D4_16S_ribosomal_RNA_partial_sequence": "NR_000004.1 Genus delta strain D4 16S ribosomal RNA, partial sequence",
    "MZ000005_1_Genus_sp_strain_E5_16S_ribosomal_RNA_gene_partial_sequence": "MZ000005.1 Genus sp. strain E5 16S ribosomal RNA gene, partial sequence",
    "ZZ_101": "ZZ_101",
    "ZZ_102": "ZZ_102",
    OG: "NR_000009.1 Outgenus thermophila strain ATCC 1 16S ribosomal RNA, partial sequence [outgroup for Genus]",
}
NEWICK = ("(((NR_000001_1_Genus_alpha_strain_A1_16S_ribosomal_RNA_partial_sequence:0.01,ZZ_101:0.01):0.02,"
          "(NR_000002_1_Genus_beta_strain_B2_16S_ribosomal_RNA_partial_sequence:0.01,NR_000003_1_Genus_gamma_strain_C3_16S_ribosomal_RNA_partial_sequence:0.01):0.02,"
          "(NR_000004_1_Genus_delta_strain_D4_16S_ribosomal_RNA_partial_sequence:0.01,(MZ000005_1_Genus_sp_strain_E5_16S_ribosomal_RNA_gene_partial_sequence:0.01,ZZ_102:0.01):0.01):0.02):0.1,"
          f"{OG}:0.1);")
RES_COLS = "identifier\texact_accession\tisolation_source\thost\tlocation\tgeography\tevidence_url\tstrain_match_basis\tverification_status\tunresolved_issue\tisolation_source_provenance\tlocation_provenance\tchecked_biosample\ttype_material\n"


def _row(acc, src, host, loc):
    return f"x\t{acc}\t{src}\t{host}\t{loc}\t\thttps://example.org/{acc}\tstrain\tSTRAIN_CONFIRMED\t\tnuccore:/isolation_source\tnuccore:/country\t\t\n"


def _fixture(tmp_path):
    (tmp_path / "tree.newick").write_text(NEWICK + "\n")
    (tmp_path / "labelmap.tsv").write_text("safe\toriginal\n" + "".join(f"{k}\t{v}\n" for k, v in TIPS.items()))
    (tmp_path / "resolved.tsv").write_text(RES_COLS
        + _row("NR_000001.1", "marine sponge", "", "Brazil")                       # deposited, named bins
        + _row("NR_000002.1", "Not recorded", "", "Not recorded")                   # nothing deposited -> reviewed fills it
        + _row("NR_000003.1", "laboratory culture of unspecified origin", "", "Italy: Lazio")  # documented, outside bins -> Other documented
        + _row("NR_000004.1", "soil", "", "Not recorded")                            # source only -> omitted (no geography)
        + _row("MZ000005.1", "Not recorded", "", "Not recorded")
        + _row("NR_000009.1", "Not recorded", "", "Not recorded"))                   # outgroup: root then drop
    (tmp_path / "reviewed.tsv").write_text("accession\tstrain\tisolation_source\tlocation\tsource_category\tgeography_category\tevidence_url\tnote\n"
        "NR_000002.1\tGenus beta B2\tforest soil\tChina, Beijing\tSoil\tAsia\thttps://collection.example/B2\tcatalogue\n")
    (tmp_path / "owner.tsv").write_text("tip\tlabel\tsample_id\trole\tsource_category\tgeography_category\tCandida\tMRSA\ttype_display\tlabel_original\n"
        "ZZ-101\tGenus sp. ZZ-101 [Bombus sp.; USA] (PX1.1)\tExp 1 #1\tquery\tBumblebee\tUS\t-\t+\t\tGenus sp. ZZ-101\n")
    (tmp_path / "override.tsv").write_text("tip\tlabel\tsample_id\tsource_category\tgeography_category\tCandida\tMRSA\tlabel_original\tprovenance\n"
        "ZZ-101\tGenus sp. ZZ-101 [Apis mellifera; USA] (PX1.1)\tExp 1 #1\tHoneybee\tUS\t-\t+\tGenus sp. ZZ-101\towner ruling\n")
    return tmp_path


def _build(tmp_path, extra=()):
    return bpi.main(["--genus", "Genus", "--tree", str(tmp_path / "tree.newick"), "--labelmap", str(tmp_path / "labelmap.tsv"),
                     "--resolved", str(tmp_path / "resolved.tsv"), "--reviewed", str(tmp_path / "reviewed.tsv"),
                     "--owner-table", str(tmp_path / "owner.tsv"), "--query-prefix", "ZZ", "--out", str(tmp_path / "out"), *extra])


def _tsv(p):
    lines = Path(p).read_text().splitlines()
    return [dict(zip(lines[0].split("\t"), ln.split("\t"))) for ln in lines[1:]]


def test_bins_and_rules():
    assert bpi.bin_source("marine sponge") == ("Marine-associated", True)
    assert bpi.bin_source("host: Apis mellifera") == ("Honeybee", True)
    assert bpi.bin_source("laboratory culture of unspecified origin") == ("Other documented", False)
    assert bpi.bin_source("tufacean surface in a catacomb") == ("Rock-associated", True)
    assert bpi.bin_source("Not recorded") == ("", False)
    assert bpi.bin_geo("USA: New Jersey") == "US" and bpi.bin_geo("Italy: Lazio") == "Europe" and bpi.bin_geo("unknown") == ""


def test_precedence_omission_outgroup_and_provenance(tmp_path):
    built = _build(_fixture(tmp_path))
    out = Path(built["dir"])
    md = {r["tip"]: r for r in _tsv(out / "metadata.tsv")}
    assert built["kept"] == 4 and built["omitted"] == 4
    a1 = next(k for k in md if k.startswith("NR_000001")); assert md[a1]["source_category"] == "Marine-associated" and md[a1]["geography_category"] == "South America"
    b2 = next(k for k in md if k.startswith("NR_000002")); assert md[b2]["source_category"] == "Soil" and md[b2]["geography_category"] == "Asia"
    c3 = next(k for k in md if k.startswith("NR_000003")); assert md[c3]["source_category"] == "Other documented" and md[c3]["geography_category"] == "Europe"
    assert md[a1]["label"] == "Genus alpha A1 [Type; Marine-associated; South America] (NR_000001.1)" and md[a1]["type_display"] == "Type"
    assert md["ZZ_101"]["role"] == "query" and md["ZZ_101"]["MRSA"] == "+" and md["ZZ_101"]["source_category"] == "Bumblebee"
    om = {r["tip"]: r for r in _tsv(out / "OMITTED_TIPS.tsv")}
    assert any(k.startswith("NR_000004") for k in om) and "no deposited or reviewed geography" in next(v for k, v in om.items() if k.startswith("NR_000004"))["reason"]
    assert om["ZZ_102"]["reason"].startswith("query row absent")
    assert om[OG]["record_title"].startswith("NR_000009.1 Outgenus thermophila") and "used for rooting, then dropped" in om[OG]["reason"]
    assert (out / "outgroup.txt").read_text().strip() == OG                       # roots the tree ...
    assert OG in (out / "exclude_tips.txt").read_text().splitlines()               # ... and is then dropped
    prov = {(r["tip"], r["field"]): r for r in _tsv(out / "METADATA_PROVENANCE.tsv")}
    assert prov[(a1, "source")]["provenance"].startswith("DEPOSITED") and prov[(a1, "source")]["verbatim"] == "marine sponge"
    assert prov[(b2, "source")]["provenance"] == "COLLECTION_OR_LITERATURE" and prov[(b2, "source")]["evidence_url"] == "https://collection.example/B2"
    assert "outside named bins" in prov[(c3, "source")]["provenance"]
    assert prov[("ZZ_101", "source")]["provenance"] == "OWNER_REGISTRY"


def test_owner_ruling_override_wins(tmp_path):
    built = _build(_fixture(tmp_path), extra=["--query-override", str(tmp_path / "override.tsv")])
    md = {r["tip"]: r for r in _tsv(Path(built["dir"]) / "metadata.tsv")}
    assert md["ZZ_101"]["source_category"] == "Honeybee" and "Apis mellifera" in md["ZZ_101"]["label"]
    prov = {(r["tip"], r["field"]): r for r in _tsv(Path(built["dir"]) / "METADATA_PROVENANCE.tsv")}
    assert prov[("ZZ_101", "source")]["provenance"] == "OWNER_RULING" and prov[("ZZ_101", "source")]["verbatim"] == "owner ruling"


def _pp():
    spec = importlib.util.spec_from_file_location("phylo_place_cs_432", ROOT / "tools" / "phylo_place.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def test_report_hook_writes_reason_without_owner_table(tmp_path):
    pp = _pp(); _fixture(tmp_path)
    a = SimpleNamespace(owner_table=[], owner_table_original=[], reference_metadata=[], reviewed=[], query_override=[], query_prefix="ZZ", rscript="Rscript")
    assert pp._color_strips_deliverable(a, str(tmp_path), "Genus", str(tmp_path / "tree.newick"), str(tmp_path / "labelmap.tsv")) is None
    note = (tmp_path / "color_strips" / "COLOR_STRIPS_NOT_RENDERED.txt").read_text()
    assert "no --owner-table" in note


def test_report_hook_builds_inputs_and_names_missing_rscript(tmp_path, monkeypatch):
    pp = _pp(); _fixture(tmp_path)
    monkeypatch.setattr(pp, "_which", lambda *args, **kw: None)
    import shutil
    monkeypatch.setattr(shutil, "which", lambda *args, **kw: None)
    a = SimpleNamespace(owner_table=[str(tmp_path / "owner.tsv")], owner_table_original=[], reference_metadata=[str(tmp_path / "resolved.tsv")],
                        reviewed=[str(tmp_path / "reviewed.tsv")], query_override=[], query_prefix="ZZ", rscript="Rscript-not-here")
    built = pp._color_strips_deliverable(a, str(tmp_path), "Genus", str(tmp_path / "tree.newick"), str(tmp_path / "labelmap.tsv"))
    assert built and built["kept"] == 4
    panel = tmp_path / "color_strips" / "Genus"
    assert (panel / "metadata.tsv").is_file() and (panel / "render_placement_COLOR_STRIPS.R").is_file()
    assert "Rscript not found" in (tmp_path / "color_strips" / "COLOR_STRIPS_NOT_RENDERED.txt").read_text()
