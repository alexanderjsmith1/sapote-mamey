"""reference_panel_ledger: rows are per BGC, so the ZIP roster is reported separately.

Before: the guide said one row per ZIP, the tool printed only a total, and the filename-derived
strain in `identity` was not marked as unbound.
"""
import csv
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
_spec = importlib.util.spec_from_file_location("rpl_464r3", ROOT / "tools" / "reference_panel_ledger.py")
rpl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rpl)


def test_roster_line_counts_zero_region_and_skipped_zips(tmp_path, monkeypatch, capsys):
    src = tmp_path / "zips"
    src.mkdir()
    for name in ("multi.zip", "empty.zip", "broken.zip"):
        (src / name).write_bytes(b"x")

    def fake(path):
        name = pathlib.Path(path).name
        if name == "broken.zip":
            raise ValueError("not an archive")
        if name == "empty.zip":
            return []
        return [{"bgc_id": f"BGC00{i}", "contig": "ctg1", "region": f"region00{i}"} for i in (1, 2)]

    monkeypatch.setattr(rpl, "ledger_for_zip", fake)
    out = tmp_path / "ledger.csv"
    assert rpl.main([str(src), str(out)]) == 0
    text = capsys.readouterr().out
    assert "zip roster: 3 zip(s); 1 with BGC rows; 1 with no parsed region; 1 skipped" in text
    assert "no regions: empty.zip" in text
    rows = list(csv.DictReader(out.open()))
    assert len(rows) == 2 and {r["source_file"] for r in rows} == {"multi.zip"}
    assert {r["identity_strain_basis"] for r in rows} == {"zip_filename_stem_unbound"}
