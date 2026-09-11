"""RAZZLE_417 — the ggtree producer put a FOLDER LABEL in publication tip labels, and read one
metadata table out of three.

Reproduced on the real Kribbella placement panel, 2026-09-08:
  * `AS-544 (Kribella, Moss, Ontario · Ontario)` — a misspelled genus + substrate + place crammed
    into the host field, and the location printed twice.
  * `AS-539` — rendered bare, though its deposited GenBank record carries accession PX726356,
    host "Moss", geo "Canada: Ontario".
"""
import importlib.util
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _mod():
    p = os.path.join(ROOT, "tools", "build_placement_ggtree_inputs.py")
    spec = importlib.util.spec_from_file_location("bpgi", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ---- host/location column precedence ----------------------------------------------------------

def test_curated_host_wins_over_the_raw_folder_string(tmp_path):
    """STRAIN_METADATA.tsv carries both; for `folder_parse` rows the raw column is a folder name."""
    m = _mod()
    t = tmp_path / "s.tsv"
    t.write_text(
        "tip_label\thost_common\tlocation\tgenbank_accession\thost_raw\tlocation_raw\tsource\n"
        "AS-544\tmoss\tOntario\tPX566632\tKribella, Moss, Ontario\tKribella, Moss, Ontario\tfolder_parse\n",
        encoding="utf-8")
    h = m._load_hosts(str(t))["AS-544"]
    assert h["host"] == "moss", "the curated host must win over the folder string"
    assert "Kribella" not in h["host"], "a misspelled genus from a folder name must never reach a label"


# ---- label construction -------------------------------------------------------------------------

def test_location_is_not_printed_twice():
    m = _mod()
    got = m._label_styles("AS-544", "Kribella, Moss, Ontario", "Ontario", "")["withloc"]
    assert got.count("Ontario") == 1, f"region duplicated: {got}"


def test_placeholder_values_are_not_rendered_as_findings():
    """"unknown" in a figure reads as a result; an absent parenthetical is the honest rendering."""
    m = _mod()
    assert m._label_styles("AS-958", "ant", "unknown", "")["withloc"] == "AS-958 [ant]"
    assert m._label_styles("AS-539", "", "", "")["full"] == "AS-539"     # never "AS-539 ( · )"


def test_every_style_is_available_and_ordered():
    m = _mod()
    st = m._label_styles("AS-727", "other bee", "Ontario", "PX565053")
    assert st["id"] == "AS-727"
    assert st["host"] == "AS-727 [other bee]"
    assert st["withloc"] == "AS-727 [other bee · Ontario] (PX565053)"
    assert st["full"] == "AS-727 [other bee · Ontario] (PX565053)"
    assert set(m.LABEL_STYLES) == {"id", "host", "noloc", "withloc", "full"}


# ---- reference / outgroup labels ----------------------------------------------------------------

def test_outgroup_label_is_not_a_doubled_genus_with_a_severed_accession():
    """v9.7.415 rendered this tip as "Nocardioides Nocardioides albus NR (outgroup)"."""
    m = _mod()
    tip = ("Nocardioides_Nocardioides_albus_NR_118893.1_outgroup_for_Kribbella_Nocardioides_albus_"
           "strain_DSM_43109_16S_ribosomal_RNA_partial_sequence")
    lab = m._ref_label(tip, "Kribbella")
    assert lab.count("Nocardioides") == 1, f"genus doubled: {lab}"
    assert "(NR_118893)" in lab, f"accession lost or severed: {lab}"
    assert not lab.rstrip().endswith("NR"), f"truncated mid-accession: {lab}"


def test_normal_reference_label_is_unchanged():
    """Guard the guard: the ordinary case must keep its existing shape."""
    m = _mod()
    lab = m._ref_label("NR_149213_1_Kribbella_soli_strain_FMN22_16S_ribosomal_RNA_partial_sequence",
                       "Kribbella")
    # v9.7.418 (accession fix): the accession now keeps its namespace underscore (NR_149213.1,
    # not NR149213.1) because that is the form a reader can paste into NCBI. The old concatenation
    # was a formatting error — it dropped the prefix separator.
    assert lab == "K. soli FMN22 (NR_149213)"


# ---- the multi-table join -----------------------------------------------------------------------

