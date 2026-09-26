"""A rulings row with an untracked value must not pass the exact schema."""

import csv

import pytest

from mamey import bioassay_figure_factory as factory


def test_extra_ruling_cell_is_refused_instead_of_discarded(tmp_path):
    path = tmp_path / "rulings.tsv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(factory.RULING_FIELDS)
        writer.writerow(["R1", "plate-1", "A01", "SYN-1", "material_type",
                         "CRUDE_EXTRACT", "FLASH_FRACTION", "source plate map", "owner",
                         "untracked trailing value"])

    with pytest.raises(factory.BioassayFigureHold, match="BIOASSAY_RULING_SCHEMA_HOLD"):
        factory.read_rulings(path)
