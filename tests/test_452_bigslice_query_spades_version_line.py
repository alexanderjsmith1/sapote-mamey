"""Synthetic coverage-token regression: retain the complete LOCUS identifier when a VERSION
field drops a zero after the coverage decimal point. Unrelated accession mismatches stay refused.
"""
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("bigslice_query_452", Path(__file__).resolve().parents[1] / "tools/bigslice_query.py")
bq = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bq)

FULL = "NODE_1_length_9000_cov_12.0034"
SHORT = "NODE_1_length_9000_cov_12.34"


def gbk(tmp_path, locus, version, name="r.gbk"):
    seq = "a" * 3000
    origin = "\n".join(f"{i + 1:>9} {seq[i:i + 60]}" for i in range(0, 3000, 60))
    p = tmp_path / name
    p.write_text(f"LOCUS       {locus} 3000 bp    DNA     linear   UNK 01-JAN-1980\nDEFINITION  {locus}.\n"
                 f"ACCESSION   {locus.rsplit('.', 1)[0]}\nVERSION     {version}\nFEATURES             Location/Qualifiers\n"
                 f"     region          101..2900\n                     /region_number=\"1\"\n"
                 f"ORIGIN\n{origin}\n//\n")
    return p


def test_spades_region_with_antismash_version_line_is_admitted(tmp_path):
    assert bq.region_header(gbk(tmp_path, FULL, SHORT), FULL, "region001") == 2800


def test_exact_version_line_is_still_admitted(tmp_path):
    assert bq.region_header(gbk(tmp_path, FULL, FULL), FULL, "region001") == 2800


@pytest.mark.parametrize("locus,version", [
    ("NODE_1_length_9000_cov_12.34", SHORT),          # LOCUS does not name the full contig
    (FULL, "NODE_1_length_9000_cov_12.28268"),           # VERSION differs by more than the dropped 0
    (FULL, "NODE_2_length_9000_cov_12.34"),           # another contig's VERSION
])
def test_other_version_mismatches_still_refuse(tmp_path, locus, version):
    with pytest.raises(bq.AdapterError) as err:
        bq.region_header(gbk(tmp_path, locus, version), FULL, "region001")
    assert err.value.code == "GBK_REGION_UNSUPPORTED"
