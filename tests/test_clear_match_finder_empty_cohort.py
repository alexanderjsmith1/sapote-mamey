"""Regression test for the empty-cohort guard in tools/clear_match_finder.py.

Before the guard: a package whose _cds_table.csv has no data rows makes `genes`
(and `bgcs`, `matching_counts`) empty, and analyze() aborts at the first row-0
index (`genes[0]`) with an opaque `IndexError`. The ALL_MIBIG_HITS writer one
step earlier is already empty-guarded; these sibling writers were not.

After the guard: analyze() raises a clear ValueError naming the cause, and a
mixed cohort (one empty package + one real package) still ranks the real one.

Place this file in tests/ alongside test_clear_match_finder_v97434.py.
"""
import csv
import importlib.util
import json
from pathlib import Path

import pytest

MODULE = Path(__file__).parents[1] / "tools" / "clear_match_finder.py"
spec = importlib.util.spec_from_file_location("clear_match_finder", MODULE)
cm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cm)

_CDS = ["strain", "contig", "region", "bgc_id", "locus_tag", "order",
        "product", "sec_met_domains", "gene_functions"]
_HITS = ["bgc_id", "query_gene", "subject_gene", "mibig_accession", "mibig_compound",
         "reference_type", "pct_identity", "pct_coverage", "pct_coverage_interpretation",
         "coverage_qc_flag", "blast_score", "evalue", "reference_rank", "source_file"]


def _pkg(root, name, cds_rows):
    pkg = root / "runs" / name / "package"
    pkg.mkdir(parents=True)
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": name}))
    with (pkg / f"{name}_cds_table.csv").open("w", newline="") as h:
        w = csv.DictWriter(h, _CDS)
        w.writeheader()
        w.writerows(cds_rows)
    with (pkg / f"{name}_3_mibig_per_gene.csv").open("w", newline="") as h:
        csv.DictWriter(h, _HITS).writeheader()   # no hits needed for this test
    return pkg


def test_empty_cohort_raises_clear_error_not_indexerror(tmp_path):
    """A CDS-less package must yield a diagnostic ValueError, never a raw IndexError."""
    empty = _pkg(tmp_path, "EDGE-1", [])
    with pytest.raises(ValueError) as exc:
        cm.analyze([empty], tmp_path / "out")
    assert "no CDS rows" in str(exc.value)


def test_mixed_cohort_survives_one_empty_package(tmp_path):
    """One empty package must not abort ranking of the packages that do have CDS."""
    empty = _pkg(tmp_path, "EDGE-2", [])
    good = _pkg(tmp_path, "GOOD-1", [
        {"strain": "GOOD-1", "contig": "NODE_1_length_1000_cov_10.0", "region": "region001",
         "bgc_id": "BGC001", "locus_tag": "g1", "order": 1, "product": "x",
         "sec_met_domains": "", "gene_functions": ""},
    ])
    receipt = cm.analyze([empty, good], tmp_path / "out")
    assert receipt["status"] == "COMPLETE"
    assert receipt["strains"] == 1        # only GOOD-1 contributes
    assert receipt["cds_rows"] == 1
