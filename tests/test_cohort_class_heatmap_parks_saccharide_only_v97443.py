"""The genome class heatmap parks saccharide only.

Owner ruling (2026-09-24): figures that count antiSMASH product classes per genome park
saccharide only; fatty acid, terpene and ectoine are shown. BiG-SCAPE family figures and the
genus reference bank keep their own, longer lists, so the heatmap must not inherit
`genus_reference.STANDING_EXCLUSIONS`.
"""
from mamey.cohort_class_heatmap import _EXCLUDED_CLASSES, build_class_matrix
from mamey.genus_reference import STANDING_EXCLUSIONS

ROWS = [
    {"strain": "REF-1", "NRPS": 3, "fatty_acid": 1, "terpene": 2, "ectoine": 1, "saccharide": 4, "NAPAA": 1},
    {"strain": "REF-2", "NRPS": 1, "fatty_acid": 0, "terpene": 1, "ectoine": 0, "saccharide": 2, "NAPAA": 0},
]


def test_heatmap_parks_saccharide_only():
    assert _EXCLUDED_CLASSES == {"saccharide"}


def test_fatty_acid_is_drawn_and_saccharide_is_parked():
    strains, classes, matrix = build_class_matrix(ROWS)
    assert strains == ["REF-1", "REF-2"]
    assert "saccharide" not in classes
    for shown in ("fatty_acid", "terpene", "ectoine", "NAPAA"):
        assert shown in classes
    col = classes.index("fatty_acid")
    assert [row[col] for row in matrix] == [1, 0]  # the observed zero stays a zero


def test_genus_bank_keeps_its_own_list():
    assert "fatty_acid" in STANDING_EXCLUSIONS


def test_subtitle_names_what_is_parked():
    from pathlib import Path
    import mamey.cohort_class_heatmap as m
    src = Path(m.__file__).read_text(encoding="utf-8")
    assert "standing comparative exclusions removed" not in src
    assert "saccharide parked" in src
