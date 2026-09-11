"""A reference tip label must carry its accession in parentheses, intact, and never fabricate one.

Regression for a defect measured in sealed v9.7.413 on 2026-09-08 in
`tools/build_placement_ggtree_inputs.py::_ref_label`. The function replaced underscores BEFORE
looking for the accession and then matched `^\\s*([A-Z]{2})\\s?(\\d+)(?:\\s+(\\d+))?\\s+`. Against the
tips this tool actually receives that match FAILS outright — `NR_151944.1_Micromonospora_ureilytica`
becomes `NR 151944.1 Micromonospora ureilytica`, the pattern takes `NR` then `151944` then demands
whitespace and meets `.` — so `acc` stayed empty and the whole string fell through as the label:

    sealed  ->  'NR 151944.1 Micromonospora ureilyt'
    fixed   ->  'M. ureilytica (NR_151944.1)'

Three things are wrong in that one string, and all three are visible on a published figure: the
accession is printed with a SPACE and outside the parentheses that this lane reserves for
accessions; the modal-genus abbreviation never fires because `toks[0]` is `NR` rather than the
genus, so the character budget the 34-char cut assumes is never freed; and the cut therefore lands
inside the epithet. Prefixes that are not exactly two letters — `NZ_CP108647.1`, `GCF_000372745.1`,
the two shapes NCBI and antiSMASH hand back most often — never matched at all.

The last case guards the OPPOSITE error. A pattern loose enough to catch every accession also reads
the culture-collection code `IFO_14684` as one and publishes it as an accession; earlier in this
lane the same class of looseness turned `IFO_14684` into "FO_14684" and `DSM_43827` into "SM_43827"
on real figures. A label may honestly carry no accession. It may never carry a wrong one.

Hermetic: loads the tool by path, calls one pure function, no network, no workspace, no I/O.
"""
import importlib.util
import re
import sys
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parent.parent / "tools" / "build_placement_ggtree_inputs.py"


def _ref_label():
    if not TOOL.exists():                       # pragma: no cover - environment guard
        pytest.skip(f"tool not present at {TOOL}")
    spec = importlib.util.spec_from_file_location("_ggtree_inputs_under_test", TOOL)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod._ref_label


@pytest.mark.parametrize("tip,modal,accession,epithet", [
    ("NR_151944.1_Micromonospora_ureilytica", "Micromonospora", "NR_151944.1", "ureilytica"),
    ("NR_112082.2_Kitasatospora_setae", "Kitasatospora", "NR_112082.2", "setae"),
    ("NZ_CP108647.1_Streptomyces_griseus", "Streptomyces", "NZ_CP108647.1", "griseus"),
    ("GCF_000372745.1_Embleya_scabrispora", "Embleya", "GCF_000372745.1", "scabrispora"),
    ("MW767829_Streptomyces_olivaceus", "Streptomyces", "MW767829", "olivaceus"),
])
def test_accession_is_parenthesised_and_the_epithet_survives(tip, modal, accession, epithet):
    label = _ref_label()(tip, modal)
    displayed_accession = accession.rsplit(".", 1)[0]
    assert f"({displayed_accession})" in label, (
        f"the accession must be inside parentheses; got {label!r}. Sealed v9.7.413 printed it "
        f"bare and space-separated because the match failed before it was ever extracted.")
    assert epithet in label, (
        f"the species epithet was severed; got {label!r}. The accession must not compete with the "
        f"name for the width budget.")


def test_no_accession_is_ever_printed_with_a_space():
    label = _ref_label()("NR_151944.1_Micromonospora_ureilytica", "Micromonospora")
    assert not re.search(r"\b(?:NR|NZ|NC|GCF|GCA|XR)\s+\d", label), (
        f"{label!r} contains a space-separated accession — not a token anyone can look up.")


def test_a_culture_collection_code_is_never_published_as_an_accession():
    for tip in ("IFO_14684_Streptomyces_griseus",
                "DSM_43827_Nocardioides_flavus",
                "ATCC_19285_Actinopolyspora_halophila"):
        label = _ref_label()(tip, "Streptomyces")
        assert "(" not in label, (
            f"{label!r} presents a culture-collection number as an accession. A fabricated "
            f"accession is strictly worse than no accession: it resolves to nothing, or to the "
            f"wrong record.")
