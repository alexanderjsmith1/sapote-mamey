"""Fail-before / pass-after for CLAUDE_409_provenance_anchors.

Doctrine: every citable per-BGC delivery row must carry a durable locus anchor
(strain / node-or-contig / region), because BGC### is a non-portable internal id.
tools/check_provenance_columns.py enforces that. This lane has two halves:

  (1) CHECKER — two recognition defects that manufactured false failures:
      * Defect A: a leading `# provenance,...` banner line was taken by csv.DictReader
        as the header row, hiding the real `contig,region` header one line below.
      * Defect B: the project's OWN canonical split-locus column names
        (`full_node_or_contig`, `exact_locus`, `region_key`, `node/contig`,
        `contig_a/contig_b`, `region_number`) were not in CONTIG_COLS/REGION_COLS,
        so the gate flagged its most doctrine-faithful tables.

  (2) EMITTERS — the per-strain package CSV export block (mamey/cli.py) and the flat
      per-gene / per-detail writers (gene_context.py, gene_by_gene.py) shipped a bare
      `bgc_id` with no strain/region. This test asserts the OLD export shape FAILS the
      gate and the NEW anchored shape PASSES.

Run against the tree under test (set MAMEY_BUNDLE, or run from inside the patched bundle):
    MAMEY_BUNDLE=/path/to/bundle pytest test_409_provenance_anchors.py

Pristine v9.7.408 -> the Defect-A/Defect-B tests FAIL (false "missing anchor"); the
anchored-export test PASSES either way (it is the fix's target shape). Patched -> all pass.
"""
import importlib.util
import os
import sys
from pathlib import Path

import pytest


# --------------------------------------------------------------- load the checker under test
def _find_checker() -> Path:
    env = os.environ.get("MAMEY_BUNDLE")
    candidates = []
    if env:
        candidates.append(Path(env) / "tools" / "check_provenance_columns.py")
    # walk up from cwd and from this file, looking for the bundle's tools/ copy
    for base in (Path.cwd(), Path(__file__).resolve().parent):
        for up in [base, *base.parents]:
            candidates.append(up / "tools" / "check_provenance_columns.py")
    for c in candidates:
        if c.is_file():
            return c
    raise RuntimeError(
        "check_provenance_columns.py not found — set MAMEY_BUNDLE to the patched bundle root"
    )


_CHECKER_PATH = _find_checker()
# the checker inserts its own dir on sys.path (for `from _console import emit`); mirror that
sys.path.insert(0, str(_CHECKER_PATH.parent))
_spec = importlib.util.spec_from_file_location("check_provenance_columns_under_test", _CHECKER_PATH)
cpc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cpc)


def _check(tmp_path, name: str, text: str) -> list:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return cpc.check_file(p)


# =============================================================== EMITTER shape (old -> new)
def test_old_bare_bgc_id_export_fails(tmp_path):
    """The shape the pre-patch cli.py per-gene export wrote: bare bgc_id, no anchor.
    The gate must FAIL it (this is the real bug the lane fixes at the source)."""
    csv_text = "bgc_id,query_gene,subject_gene,pct_identity\nBGC001,ctg1_5,mibigX,88.0\n"
    problems = _check(tmp_path, "AS-40_4A2_ClusterBlast_per_gene.csv", csv_text)
    assert problems, "a bare-bgc_id per-gene export must fail the provenance gate"
    joined = " ".join(problems)
    assert "strain" in joined and "region" in joined


def test_new_anchored_export_passes(tmp_path):
    """The shape the patched emitters write: strain, assembly_locator, contig, region, bgc_id, ..."""
    csv_text = (
        "strain,assembly_locator,contig,region,bgc_id,query_gene,pct_identity\n"
        "AS-40,NODE_402 region001 (BGC001),NODE_402,region001,BGC001,ctg1_5,88.0\n"
    )
    assert _check(tmp_path, "AS-40_4A2_ClusterBlast_per_gene.csv", csv_text) == []


def test_new_cds_table_shape_passes(tmp_path):
    """gene_context.py _cds_table after the patch: strain/assembly_locator/region + bgc_id,contig."""
    csv_text = (
        "strain,assembly_locator,region,bgc_id,contig,locus_tag,order\n"
        "AS-40,NODE_1 region002 (BGC002),region002,BGC002,NODE_1,ctg1_11,1\n"
    )
    assert _check(tmp_path, "AS-40_cds_table.csv", csv_text) == []


# =============================================================== CHECKER Defect A (banner)
def test_defect_a_banner_hidden_header_passes(tmp_path):
    """A figure-data CSV whose FIRST line is a `# provenance,...` banner. The real header
    (`rank,bgc_id,contig,region`) sits on line 2. Pristine .408: the banner is read as the
    header and all three anchors 'go missing' (RED). Patched: banner skipped -> passes."""
    # The banner is padded to the table's real width so that, on pristine .408, the BGC### cell
    # still lands in a NAMED (banner-derived) column and the table is detected as per-BGC — making
    # pristine FAIL all three anchors (RED). Patched skips the banner and reads the true header.
    csv_text = (
        "# provenance,Mamey deterministic extraction,class-level hypothesis,only,--\n"
        "strain,rank,bgc_id,contig,region\n"
        "AS-40,1,BGC001,NODE_402,region001\n"
    )
    problems = _check(tmp_path, "AS-40_8a_fig_domain_data.csv", csv_text)
    assert problems == [], f"banner-led CSV should pass once the banner is skipped; got {problems}"


def test_defect_a_still_needs_a_bgc_id_column(tmp_path):
    """Guard: skipping the banner must not swallow a genuinely anchorless table."""
    csv_text = (
        "# provenance,banner\n"
        "bgc_id,query_gene\n"
        "BGC001,ctg1_5\n"
    )
    problems = _check(tmp_path, "AS-40_bad_after_banner.csv", csv_text)
    assert problems, "a real bare-bgc_id table behind a banner must still fail"


# =============================================================== CHECKER Defect B (synonyms)
def test_defect_b_activity_lead_split_columns_pass(tmp_path):
    """The activity-lead gold-standard shape: strain, exact_locus, full_node_or_contig, region,
    bgc_alias. Pristine .408: full_node_or_contig is not a recognised contig synonym -> RED."""
    csv_text = (
        "strain,exact_locus,full_node_or_contig,region,bgc_alias\n"
        "AS-40,AULB01000055.1 region001,AULB01000055.1,region001,BGC044\n"
    )
    assert _check(tmp_path, "ACTIVITY_LEAD_GENE_ANCHORS.csv", csv_text) == []


def test_defect_b_region_key_hmm_shape_passes(tmp_path):
    """antismash_hmm carries `region_key` (not `region`). Once region_key is a REGION synonym and
    the anchor columns are added by the emitter, the table passes."""
    csv_text = (
        "strain,assembly_locator,contig,region_key,bgc_id,domain_name\n"
        "AS-40,NODE_1 region001 (BGC001),NODE_1,NODE_1_r1,BGC001,PKS_KS\n"
    )
    assert _check(tmp_path, "AS-40_3_antismash_hmm.csv", csv_text) == []


def test_defect_b_cohort_roster_node_contig_passes(tmp_path):
    """Cohort roster uses a `node/contig` column plus `region`."""
    csv_text = (
        "strain,node/contig,region,bgc_id\n"
        "AS-40,NODE_9,region003,BGC009\n"
    )
    assert _check(tmp_path, "G15_rare_bgc_roster_data.csv", csv_text) == []


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
