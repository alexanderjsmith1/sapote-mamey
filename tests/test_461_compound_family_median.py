"""Arithmetic rollup fixtures; no compound identification or activity inference."""
import csv
import json

import pytest

from mamey import compound_family_report as report


@pytest.mark.parametrize("values,expected", [
    ([0, 10], 5),
    ([0, 2, 8, 10], 5),
    ([2, 5, 10], 5),
    ([7], 7),
    ([], None),
])
def test_rollup_uses_median_of_all_retained_values(tmp_path, monkeypatch, values, expected):
    package = tmp_path / "package"
    package.mkdir()
    (package / "manifest.json").write_text(json.dumps({"strain": "engineering_fixture"}))
    board = package / "engineering_fixture_4_triage_board.csv"
    fields = ["BGC_ID", "Node/Contig", "Region", "KCB_top", "AF_auto", "AB_auto"]
    with board.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index, value in enumerate(values, 1):
            writer.writerow({"BGC_ID": f"BGC{index:03d}", "Node/Contig": "software_contig",
                "Region": f"region{index:03d}", "KCB_top": "software_anchor",
                "AF_auto": value, "AB_auto": value * 2})
    monkeypatch.setattr(report, "EXCLUDE_STRAINS", set())
    monkeypatch.setattr(report, "load_rules", lambda: [(["software_anchor"], ("software_family", "other", "arithmetic fixture"))])
    monkeypatch.setattr(report, "_extract_anchor", lambda value: value)
    result = report.run(package, out_dir=tmp_path / "output", with_structures=False)
    assert result["rows"] == len(values)
    output = tmp_path / "output/COMPOUND_FAMILIES/COMPOUND_FAMILY_ROLLUP.tsv"
    with output.open() as handle:
        rows = list(csv.DictReader((line for line in handle if not line.startswith("#")), delimiter="\t"))
    if expected is None:
        assert rows == []
    else:
        assert len(rows) == 1
        assert float(rows[0]["median_AF_prior"]) == expected
        assert float(rows[0]["median_AB_prior"]) == expected * 2
