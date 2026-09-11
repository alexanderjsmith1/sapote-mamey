"""Regression contracts found during real bee 16S production from v9.7.426."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import sqlite3

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))


def load(name):
    spec = importlib.util.spec_from_file_location(f"test_{name}", TOOLS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("raw, expected", [
    ("Bombus sp.", "bumblebee"),
    ("Apis mellifera", "honeybee"),
    ("Other Apidae (Andrena sp.)", "solitary bee"),
    ("Other Apidae (Unidentified)", "other bee"),
    ("Wasp", "wasp"),
    ("Atta sp.", "attine ant"),
    ("Acromyrmex echinator colony", "attine ant"),
    ("Myrmicocrypta sp. fungal garden", "attine ant"),
    ("Lower attine colony GB151025-06", "attine ant"),
])
def test_bee_isolation_sources_remain_distinct(raw, expected):
    metadata = load("_phylo_metadata")
    assert metadata.normalize_isolation_source(raw)["display_category"] == expected


def test_compact_publication_labels_use_one_grammar_and_keep_accessions():
    display = load("placement_display")
    rows = [
        dict(tip="AS_128", kind="query", as_id="AS-128", group="Streptomyces",
             host="Bombus sp.", region="New Jersey", accession="PV981676"),
        dict(tip="Streptomyces_sampsonii_ATCC_25495_NR_025870", kind="reference",
             group="Streptomyces",
             ref_label="S. sampsonii ATCC 25495 [rhizosphere soil · China] (NR_025870)",
             reference_habitat="rhizosphere soil", reference_country="China"),
    ]
    labels = [row["label"] for row in display.display_rows(rows, "compact")]
    assert labels[0] == "Streptomyces sp. AS-128 [bumblebee · New Jersey] (PV981676)"
    assert labels[1].startswith("Streptomyces sampsonii ATCC 25495 ")
    assert labels[1].endswith("(NR_025870)")
    assert all(".1)" not in label for label in labels)


def test_reference_definition_accession_prefix_is_removed_before_labeling(tmp_path):
    display = load("placement_display")
    db = tmp_path / "rrna.sqlite"
    with sqlite3.connect(db) as con:
        con.execute("CREATE TABLE record(acc_base TEXT, definition TEXT)")
        con.execute(
            "INSERT INTO record VALUES (?, ?)",
            ("MW444761", "MW444761.1 Micromonospora sp. strain AmelKG-G8 "
                         "16S ribosomal RNA gene, partial sequence"),
        )
    organisms = display._reference_organisms(db, load("build_placement_ggtree_inputs"))
    assert organisms["MW444761"] == "Micromonospora sp. strain AmelKG-G8"
    label = organisms["MW444761"] + " (MW444761)"
    assert label.startswith("Micromonospora ")
    assert label.count("MW444761") == 1


def test_explicit_genus_roster_can_replace_internal_cross_genus_group():
    display = load("placement_display")
    row = dict(tip="AS_210", kind="query", as_id="AS-210",
               group="combined_hymenoptera", host="Bombus sp.",
               region="New Jersey", accession="PX565015")
    row["group"] = "Micromonospora"  # operation performed from the genus roster in main()
    label = display.display_rows([row], "publication")[0]["label"]
    assert label == "Micromonospora sp. AS-210 [bumblebee · New Jersey] (PX565015)"


def test_publication_noloc_keeps_sources_and_accessions_but_omits_geography():
    display = load("placement_display")
    rows = [
        dict(tip="AS_128", kind="query", as_id="AS-128", group="Streptomyces",
             host="Bombus sp.", region="New Jersey", accession="PV981676.1"),
        dict(tip="Streptomyces_sampsonii_NR_025870", kind="reference",
             group="Streptomyces",
             ref_label="S. sampsonii [rhizosphere soil · China] (NR_025870)",
             ref_label_noloc="S. sampsonii [rhizosphere soil] (NR_025870)",
             reference_habitat="rhizosphere soil", reference_country="China"),
    ]
    labels = [row["label"] for row in display.display_rows(rows, "publication-noloc")]
    assert labels == [
        "Streptomyces sp. AS-128 [bumblebee] (PV981676)",
        "Streptomyces sampsonii [plant] (NR_025870)",
    ]
    assert all("New Jersey" not in label and "China" not in label for label in labels)


def test_country_name_inside_species_epithet_is_not_a_geography_leak():
    display = load("placement_display")
    row = dict(ref_label="S. venezuelae NBRC 12595 [soil · Venezuela] (NR_112510)",
               reference_habitat="soil", reference_country="Venezuela")
    assert display._without_location(row) == "S. venezuelae NBRC 12595 [soil] (NR_112510)"


def test_publication_noloc_normalizes_geographic_isolation_phrase():
    display = load("placement_display")
    row = dict(tip="Streptomyces_abyssalis_NR_109175", group="Streptomyces",
               ref_label="S. abyssalis YIM M 10400 [Northern South China Sea…] (NR_109175)",
               reference_habitat="Northern South China Sea abyssal sediment",
               reference_country="China")
    label = display.display_rows([row], "publication-noloc")[0]["label"]
    assert label == "Streptomyces abyssalis [soil] (NR_109175)"
    assert "China" not in label


@pytest.mark.parametrize("habitat, source, expected", [
    ("Highly mineralized stratal waters of the oil field", "", "water"),
    ("formation water from an oil reservoir", "", "water"),
    ("scab lesion of potato tuber", "scab lesion of potato tuber · host: Solanum tuberosum · Russia", "Solanum tuberosum"),
    ("potato tuber", "potato tuber · host: Solanum tuberosum · Russia", "Solanum tuberosum"),
    ("litter of bamboo (Sasa boreali) forest", "litter of bamboo (Sasa boreali) forest · host: Sasamorpha borealis · Russia", "bamboo"),
])
def test_publication_reference_sources_are_concise(habitat, source, expected):
    display = load("placement_display")
    row = dict(tip="Streptomyces_example_NR_112599", group="Streptomyces",
               reference_species="Streptomyces example", reference_habitat=habitat,
               reference_source=source, reference_country="Russia")
    rendered = display.display_rows([row], "publication")[0]
    assert rendered["label"] == f"Streptomyces example [{expected} · Russia] (NR_112599)"
    assert habitat not in rendered["label"]


def test_detailed_publication_variant_retains_deposited_source():
    display = load("placement_display")
    habitat = "Highly mineralized stratal waters of the oil field"
    row = dict(tip="Streptomyces_albiaxialis_NR_112599", group="Streptomyces",
               reference_species="Streptomyces albiaxialis", reference_habitat=habitat,
               reference_country="Russia")
    rendered = display.display_rows([row], "publication-detailed")[0]
    assert rendered["label"] == (
        "Streptomyces albiaxialis [Highly mineralized stratal waters of the oil field · Russia] "
        "(NR_112599)"
    )


def test_internal_label_adds_bound_experiment_and_sample_only_to_query():
    display = load("placement_display")
    rows = [
        dict(tip="AS_633", kind="query", as_id="AS-633", group="Streptomyces",
             host="Bombus sp.", region="New Jersey", accession="PX558893",
             experiment_id="Exp 55", sample_id="64"),
        dict(tip="Streptomyces_sampsonii_NR_025870", kind="reference", group="Streptomyces",
             ref_label="S. sampsonii ATCC 25495 [rhizosphere soil · China] (NR_025870)",
             reference_species="Streptomyces sampsonii",
             reference_habitat="rhizosphere soil", reference_country="China"),
    ]
    labels = [row["label"] for row in display.display_rows(rows, "internal")]
    assert labels == [
        "Streptomyces sp. AS-633 [bumblebee · New Jersey; Exp 55 #64] (PX558893)",
        "Streptomyces sampsonii [plant · China] (NR_025870)",
    ]


def test_multiple_reference_accessions_fail_admission_before_inference(tmp_path):
    place = load("phylo_place")
    ref = tmp_path / "bad.fasta"
    ref.write_text(
        ">NR_041207.1 Streptomyces example strain A >NR_112493.1 Streptomyces example strain B\n"
        + "ACGT" * 300 + "\n"
    )
    rejected = place.screen_reference_definitions(str(ref))
    assert rejected == [(rejected[0][0], "MULTIPLE_FASTA_DEFINITIONS_OR_ACCESSIONS")]


def test_query_alignment_failure_retains_external_diagnostic(tmp_path, monkeypatch):
    place = load("phylo_place")
    ref = tmp_path / "ref.fasta"
    query = tmp_path / "query.fasta"
    ref.write_text(">REF\nACGT\n")
    query.write_text(">AS_1\nACGT\n")

    def fail(_cmd, **kwargs):
        kwargs["stderr"].write("real mafft diagnostic\n")
        raise place.subprocess.CalledProcessError(7, _cmd)

    monkeypatch.setattr(place.subprocess, "check_call", fail)
    with pytest.raises(RuntimeError, match="QUERY_ALIGNMENT_FAILED.*query_alignment.stderr.log"):
        place._align_queries("mafft", "epa-ng", str(ref), str(query), str(tmp_path), True)
    assert "real mafft diagnostic" in (tmp_path / "query_alignment.stderr.log").read_text()


def test_identical_16s_from_distinct_isolates_is_retained(tmp_path):
    place = load("phylo_place")
    source = tmp_path / "queries.fasta"
    output = tmp_path / "dedup.fasta"
    source.write_text(">AS-150\nACGTACGT\n>AS-152\nACGTACGT\n")
    kept, dropped = place._dedup_queries(str(source), str(output))
    assert (kept, dropped) == (2, 0)
    assert output.read_text().count(">") == 2


def test_reference_culture_code_is_not_promoted_to_query():
    place = load("phylo_place")
    queries = {"AS_150_from_Andrena_PX558857"}
    assert place._tree_tip_matches_query("AS_150_from_Andrena_PX558857_2", queries)
    assert not place._tree_tip_matches_query(
        "Streptomyces_anthocyanicus_strain_AS_4_1594_NR_027222", queries
    )


def test_required_reference_table_preserves_exact_query_species_pairing(tmp_path):
    builder = load("build_placement_ggtree_inputs")
    table = tmp_path / "required.tsv"
    table.write_text(
        "strain\treference_species\n"
        "AS-128\tStreptomyces albovinaceus\n"
        "AS-150\tStreptomyces zingiberis\n"
    )
    assert builder._load_required_references(table) == {
        "AS-128": "Streptomyces albovinaceus",
        "AS-150": "Streptomyces zingiberis",
    }


def test_required_reference_table_refuses_conflicting_pairing(tmp_path):
    builder = load("build_placement_ggtree_inputs")
    table = tmp_path / "required.tsv"
    table.write_text(
        "strain\treference_species\n"
        "AS-128\tStreptomyces albovinaceus\n"
        "AS-128\tStreptomyces sampsonii\n"
    )
    with pytest.raises(ValueError, match="REQUIRED_REFERENCE_TABLE_CONFLICT"):
        builder._load_required_references(table)


def test_required_reference_missing_from_backbone_refuses_instead_of_using_nearest(tmp_path, monkeypatch, capsys):
    builder = load("build_placement_ggtree_inputs")
    graft = tmp_path / "graft.nwk"
    graft.write_text(
        "(AS_128_from_Bombus_PV981676:0.01,"
        "Streptomyces_sampsonii_NR_025436:0.001,"
        "Kitasatospora_setae_outgroup_NR_112082:0.2);\n"
    )
    required = tmp_path / "required.tsv"
    required.write_text(
        "strain\treference_species\n"
        "AS-128\tStreptomyces albovinaceus\n"
    )
    monkeypatch.setattr(sys, "argv", [
        "build_placement_ggtree_inputs.py",
        "--graft", str(graft),
        "--required-reference-table", str(required),
        "--out-prefix", str(tmp_path / "display"),
    ])
    with pytest.raises(SystemExit) as refused:
        builder.main()
    assert refused.value.code == 2
    assert "REQUIRED_REFERENCE_NOT_IN_BACKBONE" in capsys.readouterr().err


def test_display_refuses_duplicate_reference_species():
    display = load("placement_display")
    rows = [
        dict(tip="Streptomyces_microflavus_NR_043854", group="Streptomyces",
             reference_species="Streptomyces microflavus"),
        dict(tip="Streptomyces_microflavus_NR_103947", group="Streptomyces",
             reference_species="Streptomyces microflavus"),
    ]
    with pytest.raises(ValueError, match="DUPLICATE_REFERENCE_SPECIES"):
        display.display_rows(rows, "publication")


def test_reference_role_markers_are_explicit_in_publication_labels():
    display = load("placement_display")
    rows = [
        dict(tip="Streptomyces_sampsonii_NR_025870", group="Streptomyces",
             reference_species="Streptomyces sampsonii", reference_role="type_reference"),
        dict(tip="Streptomyces_sp._KGS_6_13_KU840406", group="Streptomyces",
             reference_species="Streptomyces sp.", reference_role="cultured_non_type_reference"),
    ]
    labels = [row["label"] for row in display.display_rows(rows, "publication")]
    assert labels == [
        "Streptomyces sampsonii [type strain] (NR_025870)",
        "Streptomyces sp. [cultured non-type] (KU840406)",
    ]


@pytest.mark.parametrize("taxon, role, error", [
    ("Nocardia sp.", "type_reference", "TYPE_REFERENCE_WITHOUT_EXPLICIT_NAMED_TARGET"),
    ("Nocardia alba", "cultured_non_type_reference", "CULTURED_NONTYPE_WITH_NAMED_SPECIES"),
])
def test_reference_metadata_refuses_role_taxon_mismatch(tmp_path, taxon, role, error):
    place = load("phylo_place")
    table = tmp_path / "reference_metadata.tsv"
    table.write_text(f"tip\ttaxon\trole\nref_1\t{taxon}\t{role}\n")
    with pytest.raises(ValueError, match=error):
        place._load_reference_identity_metadata(str(table), ["ref_1"])


def test_genus_sp_type_reference_is_admitted_with_explicit_named_target(tmp_path):
    place = load("phylo_place")
    table = tmp_path / "reference_metadata.tsv"
    table.write_text(
        "tip\ttaxon\trole\ttype_strain_of\ttype_evidence\n"
        "ref_1\tNocardia sp.\ttype_reference\tNocardia exemplaris\t"
        "GenBank source qualifier: type strain of Nocardia exemplaris\n"
    )
    rows = place._load_reference_identity_metadata(str(table), ["ref_1"])
    assert rows["ref_1"]["type_strain_of"] == "Nocardia exemplaris"


def test_publication_label_displays_explicit_type_strain_target():
    display = load("placement_display")
    row = dict(tip="Nocardia_sp_X123", group="Nocardia", reference_species="Nocardia sp.",
               reference_role="type_reference", type_strain_of="Nocardia exemplaris")
    label = display.display_rows([row], "publication")[0]["label"]
    assert "[type strain of Nocardia exemplaris]" in label


@pytest.mark.parametrize("raw, expected", [
    ("attine ant", "attine ant"),
    ("Moss", "moss"),
    ("Liverwort", "liverwort"),
])
def test_publication_query_labels_preserve_controlled_project_source(raw, expected):
    display = load("placement_display")
    row = dict(tip="AS_test", kind="query", as_id="AS-test", group="Streptomyces",
               host=raw, region="Canada", accession="PX000001")
    label = display.display_rows([row], "publication")[0]["label"]
    assert label == f"Streptomyces sp. AS-test [{expected} · Canada] (PX000001)"
