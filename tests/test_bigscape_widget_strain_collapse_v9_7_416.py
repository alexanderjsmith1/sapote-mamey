"""AMBER_417 — the BiG-SCAPE cohort widgets must not collapse two distinct references onto one row.

deliverable_tools/_bigscape_data.strain_of() derived a reference label from the first three organism
words (`" ".join(organism.split()[:3])`). For `Genus sp. <COLLECTION> <NUMBER>` names the 4th token IS
the strain designator, so two distinct references collapsed to one label -- e.g.

    "Streptomyces sp. WAC 01529"  ->  "Streptomyces sp. WAC"
    "Streptomyces sp. WAC 06738"  ->  "Streptomyces sp. WAC"

In the strain x GCF matrix widget those two organisms are then drawn as ONE row and their GCF
portfolios merge. The fix routes the reference label through the engine's single resolver
strain_from_gbk_name (used by the four BiG-SCAPE->Mamey tools), which keeps the full strain from the
BiG-SCAPE input filename. A "."-organism record additionally leaked an accession fragment.

AS/SID labels are resolved earlier in strain_of and are unaffected. Hermetic (no DB fixture).

Run:  pytest tests/test_bigscape_widget_strain_collapse_v9_7_416.py
"""
import importlib
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (_ROOT, os.path.join(_ROOT, "deliverable_tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

D = importlib.import_module("_bigscape_data")


def _label(path, organism):
    return D.strain_of(path, organism)[0]


def test_two_distinct_wac_references_do_not_collapse():
    p1 = "/x/gbk_input/Streptomyces sp. WAC 01529_NZ_CP012345.1.region001.gbk"
    p2 = "/x/gbk_input/Streptomyces sp. WAC 06738_NZ_CP029618.1.region041.gbk"
    l1 = _label(p1, "Streptomyces sp. WAC 01529")
    l2 = _label(p2, "Streptomyces sp. WAC 06738")
    assert l1 != l2, f"distinct references collapsed to one label: {l1!r}"
    assert l1 == "Streptomyces sp. WAC 01529", l1
    assert l2 == "Streptomyces sp. WAC 06738", l2


def test_dot_organism_reference_does_not_leak_accession():
    # organism == "." forced the [:40]-of-filename fallback, which kept the accession fragment
    p = "/x/gbk_input/Micromonospora sp. WMMA1998_CP114911.1.region015.gbk"
    label = _label(p, ".")
    assert label == "Micromonospora sp. WMMA1998", label


def test_as_and_sid_labels_unchanged():
    # the AS/SID branches run before the reference branch and must be untouched by the fix
    assert D.strain_of("/x/AS-696_NODE_25_length_90404_cov_51.797192.region001.gbk", "") == ("AS-696", "AS")
    assert D.strain_of("/x/SID8384_NODE_1_length_1000_cov_5.0.region001.gbk", "")[0] == "SID8384"
    assert D.strain_of("/x/SID8384_NODE_1_length_1000_cov_5.0.region001.gbk", "")[1] == "SID"
