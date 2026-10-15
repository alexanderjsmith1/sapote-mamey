"""Card attine_452_ledger_identity_columns: tools/reference_panel_ledger.py writes each BGC's region, its four-part
identity (genome / contig / region / BGC alias, all from the engine's parse of one ZIP) and the KnownClusterBlast MIBiG
accession and protein-hit count, so a per-BGC supplementary table never shows a bare alias. Fixture ZIP only."""
import csv
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
FIX = HERE / "tests" / "fixtures" / "domain_level_minimal_antismash.zip"


def test_identity_region_and_kcb_columns(tmp_path):
    src = tmp_path / "zips"
    src.mkdir()
    shutil.copy(FIX, src / "SYN-970.zip")
    out = tmp_path / "ledger.csv"
    subprocess.run([sys.executable, str(HERE / "tools" / "reference_panel_ledger.py"), str(src), str(out)], check=True,
                   cwd=HERE, capture_output=True)
    rows = list(csv.DictReader(out.open()))
    assert rows
    cols = list(rows[0])
    assert cols[:5] == ["source_file", "identity", "bgc_id", "contig", "region"]
    assert {"obs_kcb_mibig_accession", "obs_kcb_protein_hits"} <= set(cols)
    for r in rows:
        assert r["identity"] == f"SYN-970 / {r['contig']} / {r['region']} / {r['bgc_id']}"
        assert r["region"].startswith("region") and r["bgc_id"].startswith("BGC")
