"""Regression (BLACK_CHERRY wave 20, base .384): the v9.7.384 INDIGO fix narrowed the bare
`except` INSIDE mamey/two_pathway.py::two_pathway_by_bgc() so a genuine read/parse failure now
propagates instead of being silently reported as a success receipt with bgcs_evaluated=0.

But mamey/cli.py::_write_package() calls two_pathway_by_bgc() from TWO places. Only the second
call (the "two_pathway_patch" phase, ~line 2126) records failures via _phase_receipt(...,
"ERROR", ...). The FIRST/early call (~line 2860, inside _write_package itself, run before the
fresh *_gene_by_gene_all_bgcs.csv is written) still had its own bare
`except Exception: _two_pathway = {}` with NO _phase_receipt and NO issue recorded at all --
silently re-swallowing the now-propagating exception with zero trace on disk. This is the exact
same failure class the .384 changelog entry claims to have closed, just relocated one call frame
up, and is realistically triggered by a stale/corrupt *_gene_by_gene_all_bgcs.csv left in
package_dir from a prior invocation -- a scenario the cli.py AUDIT_371 comment documents as
having actually happened (2 strains, test-harness re-run directories).

This test plants exactly that stale corrupt table before a real run_one_strain() call on the
project's own synthetic fixture, then asserts the failure is recorded on disk somewhere (an
issue string or a two_pathway-related ERROR phase receipt) -- not silently absorbed.
"""
import json
import pathlib

import pytest

from mamey.cli import run_one_strain

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
SYNTH = FIXTURES / "synthetic_single_contig_antismash.zip"


def test_stale_corrupt_gene_table_does_not_silently_vanish(
    tmp_path, synthetic_single_contig_full_locus_zip
):
    strain_id = "BCHERRY384"
    pkg_dir = tmp_path / strain_id / "package"
    pkg_dir.mkdir(parents=True, exist_ok=True)

    # Plant a stale, genuinely corrupt gene-by-gene table (invalid UTF-8), mirroring a leftover
    # file from a prior invocation of the same package_dir -- exactly the scenario the AUDIT_371
    # comment in cli.py names as the real-world trigger for the early two_pathway_by_bgc() call.
    stale = pkg_dir / f"{strain_id}_gene_by_gene_all_bgcs.csv"
    stale.write_bytes(b"bgc_id,cds_start,cds_end,sec_met_domains\n\xff\xfe\x00corrupt,1,2,PKS_KS\n")

    res = run_one_strain(
        strain_id=strain_id, display_name=strain_id,
        input_zip=str(synthetic_single_contig_full_locus_zip), outdir=str(tmp_path), mode="full",
        taxonomy="", source="", bioactivity="",
        master_path=None, json_mode="off",
    )

    issues = res.get("issues", [])
    issue_hit = any("two-pathway" in i.lower() or "two_pathway" in i.lower() for i in issues)

    receipts_path = pkg_dir / "run_phase_receipts.jsonl"
    receipt_hit = False
    if receipts_path.exists():
        for line in receipts_path.read_text().splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            if "two_pathway" in str(rec.get("phase", "")) and rec.get("status") == "ERROR":
                receipt_hit = True
                break

    assert issue_hit or receipt_hit, (
        "a genuinely corrupt stale gene-by-gene table was fed to the EARLY "
        "two_pathway_by_bgc() call inside _write_package(), yet the run recorded no issue "
        "string and no two_pathway ERROR phase receipt anywhere -- the failure vanished "
        "silently. issues=%r" % (issues,)
    )
