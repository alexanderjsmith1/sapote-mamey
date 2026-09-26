"""Canonical observation rows may not hide cells beyond the bound header."""

import csv

import pytest

from mamey import bioassay_figure_factory as factory


@pytest.mark.parametrize("suffix,delimiter", [(".csv", ","), (".tsv", "\t")])
def test_extra_observation_cell_is_refused(tmp_path, suffix, delimiter):
    source = tmp_path / ("observations" + suffix)
    with source.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter=delimiter)
        writer.writerow(factory.FIELDS)
        writer.writerow(["" for _ in factory.FIELDS] + ["untracked assay value"])
    with pytest.raises(factory.BioassayFigureHold, match="BIOASSAY_SCHEMA_HOLD"):
        factory._read(source)
