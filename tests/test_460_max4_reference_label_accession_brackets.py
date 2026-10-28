"""max4_tree_figure writes reference accessions in brackets, like bind_panel_metadata.

FIGURE_HOUSE_RULES rules 6 and 11 and TREE_FIGURE_GRAMMAR put the accession in brackets. The .459 card
fixed bind_panel_metadata.py; tools/max4_tree_figure.py::reference_row still wrote "(<accession>)".
"""
import argparse
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("max4_tree_figure_460", ROOT / "tools" / "max4_tree_figure.py")
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

ARGS = argparse.Namespace(source_from_host=False, country_part=False, outgroup=set())


def test_type_reference_label_uses_brackets_for_the_accession():
    rec = {"accession": "GCF_000000001.1", "organism": "Synthetica alpha", "strain": "DSM 1",
           "fromtype": mod.TYPE_TEXT, "isolation_source": "soil", "geo_loc_name": "Panama"}
    label = mod.reference_row(rec, ARGS)["label_concise"]
    assert label == "Synthetica alpha DSM 1 [Type] [GCF_000000001.1]"
    assert "(" not in label


def test_non_type_reference_label_uses_brackets_for_the_accession():
    rec = {"accession": "GCA_000000002.1", "organism": "Synthetica beta X2", "strain": "X2"}
    assert mod.reference_row(rec, ARGS)["label_concise"] == "Synthetica beta X2 [GCA_000000002.1]"
