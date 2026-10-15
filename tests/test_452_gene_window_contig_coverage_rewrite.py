"""The genes-in-the-window table finds the core contig when antiSMASH rewrote the coverage part of its name.

antiSMASH can write an assembler contig named NODE_7_length_9000_cov_54.074455 as NODE_7_length_9000_cov_54.74455 in
its GenBank record ids. The gap-rescue tables keep the original name. Synthetic SYN-971 data only.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import gap_rescue_gene_table as g  # noqa: E402

TABLE_CONTIG = "NODE_7_length_9000_cov_54.074455"
ZIP_CONTIG = "NODE_7_length_9000_cov_54.74455"
OTHER = "NODE_17_length_9000_cov_54.074455"


def _cds(contig, start, end):
    return {"contig": contig, "start": start, "end": end, "strand": "+", "aa": (end - start + 1) // 3,
            "role": "biosynthetic", "domains": "", "smcog": ""}


def _rows():
    return [{"name": "synA", "status": "PRESENT_IN_CORE", "best_locus": "syn7_2", "best_contig": TABLE_CONTIG,
             "best_identity_pct": "61.5"},
            {"name": "synB", "status": "PRESENT_IN_CORE", "best_locus": "syn7_3", "best_contig": TABLE_CONTIG,
             "best_identity_pct": "58.0"}]


def test_window_found_when_record_id_rewrites_coverage():
    # matched genes span 3001-6000, so the window is 1001-8000: syn7_1 and syn7_4 reach into it, syn7_0 and syn7_5 do not
    cds = {"syn7_0": _cds(ZIP_CONTIG, 1, 900), "syn7_1": _cds(ZIP_CONTIG, 1201, 2900),
           "syn7_2": _cds(ZIP_CONTIG, 3001, 4500), "syn7_3": _cds(ZIP_CONTIG, 4601, 6000),
           "syn7_4": _cds(ZIP_CONTIG, 7001, 7900), "syn7_5": _cds(ZIP_CONTIG, 8101, 8900),
           "syn17_1": _cds(OTHER, 3001, 4500)}
    out, facts = g.window_rows(_rows(), cds, f"SYN-971 / {TABLE_CONTIG} / region002 / BGC006", trim_bp=2000)
    tags = [r["locus_tag"] for r in out]
    assert tags == ["syn7_1", "syn7_2", "syn7_3", "syn7_4"]
    assert "syn17_1" not in tags  # a contig with another number stays out


def test_contig_key_keeps_other_names_whole():
    assert g._contig_key(ZIP_CONTIG) == g._contig_key(TABLE_CONTIG) == "NODE_7_length_9000"
    assert g._contig_key("scaffold_3") == "scaffold_3"
    assert g._contig_key("") == ""


def test_no_match_still_refused():
    cds = {"syn17_1": _cds(OTHER, 3001, 4500)}
    with pytest.raises(ValueError, match="GENE_WINDOW"):
        g.window_rows(_rows(), cds, f"SYN-971 / {TABLE_CONTIG} / region002 / BGC006")
