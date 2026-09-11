"""Fail-before / pass-after for CLAUDE_409_mibig_anchor_locator.

Bug: tools/bigscape_mibig_anchors.py hardwired the identifier SHAPE. STRAIN only accepts
`AS-<n>`/`SID<n>` and LOCATOR only the SPAdes `NODE_<n>_length_..._cov_...` contig token, so this
cohort's assemblies -- arbitrary strain ids over NCBI WGS-accession contigs, e.g.
`RB68_WEGH01000001.1.region006.gbk` and `rif_AULB01000001.1.region001.gbk` -- matched NEITHER regex.
parse_strain() returned (None, base), build_rows() dropped the record on `if strain:`, and the strain
was never anchored. Because bigscape_merge_anchors then reads absence as novelty, a dropped record
turns a KNOWN anchoring into a FALSE NOVEL call (missing != absent) -- and it happened SILENTLY.

The fix: (1) generalise parse_strain to bind any `<strain>_<contig>.regionNN.gbk` name while keeping
the AS-/SID + NODE_ path byte-identical; (2) any record that still cannot be bound is surfaced by
build_rows() as a typed, deterministic `WARNING ANCHOR_LOCATOR_UNBOUND: ...` on stderr, never dropped
in silence.

Run against the tree under test (the module inserts tools/ and the repo root on sys.path itself):
    pytest test_409_mibig_anchor_locator.py
Pristine .408 -> the RB68/rif accession tests FAIL (strain is None) and the WARNING test FAILS
(nothing on stderr). Patched -> all pass.
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # tree root, if run from lane
from tools import bigscape_mibig_anchors as A  # noqa: E402  (point sys.path at the tree under test)


# --------------------------------------------------------------------------- parse_strain (core fix)

def test_rb68_wgs_accession_contig_now_binds():
    # THE FIX: NCBI WGS-accession contig under an arbitrary strain id must bind, not return None.
    strain, locator = A.parse_strain("/x/RB68_WEGH01000001.1.region006.gbk")
    assert strain == "RB68"                       # pristine .408 -> None  (RED)
    assert locator == "WEGH01000001.1.region006"  # pristine .408 -> whole basename


def test_rif_wgs_accession_contig_now_binds():
    strain, locator = A.parse_strain("/x/rif_AULB01000001.1.region001.gbk")
    assert strain == "rif"                         # pristine .408 -> None  (RED)
    assert locator == "AULB01000001.1.region001"


def test_spades_node_contig_unchanged():
    # Regression guard: AS-/SID over SPAdes NODE_ contigs is byte-identical to v9.7.408.
    strain, locator = A.parse_strain("/x/AS-40_NODE_402_length_4883_cov_73.020183.region001.gbk")
    assert strain == "AS-40"
    assert locator == "NODE_402_length_4883_cov_73.020183.region001"
    s2, l2 = A.parse_strain("/x/SID12_NODE_7_length_100_cov_5.5.region003.gbk")
    assert s2 == "SID12"
    assert l2 == "NODE_7_length_100_cov_5.5.region003"


def test_unbindable_record_returns_none():
    # A name with no `<strain>_<contig>.regionNN.gbk` shape cannot bind -> (None, base).
    strain, locator = A.parse_strain("/x/contig-no-region.gbk")
    assert strain is None
    assert locator == "contig-no-region.gbk"


# ----------------------------------------------------- build_rows: bind RB68 + surface UNBOUND WARNING

def _seed_db(path):
    """Minimal schema matching build_rows' SQL: one family (run 1, cutoff 0.5) with a MIBiG ref,
    an RB68 accession record (must now anchor), and one genuinely unbindable record."""
    con = sqlite3.connect(path)
    con.executescript(
        """
        create table family (id text, run_id integer, cutoff real);
        create table gbk (id integer, path text);
        create table bgc_record (id integer, gbk_id integer, product text, category text);
        create table bgc_record_family (family_id text, record_id integer);
        insert into family values ('1', 1, 0.5);
        insert into gbk values (1, '/d/BGC0001234.gbk'),
                               (2, '/d/RB68_WEGH01000001.1.region006.gbk'),
                               (3, '/d/mystery-contig-no-region.gbk');
        insert into bgc_record values (1, 1, 'NRPS', ''),
                                      (2, 2, 'T1PKS', ''),
                                      (3, 3, 'terpene', '');
        insert into bgc_record_family values ('1', 1), ('1', 2), ('1', 3);
        """
    )
    con.commit()
    con.close()


def test_build_rows_anchors_accession_and_warns_on_unbound(tmp_path, capsys):
    db = str(tmp_path / "anchors.db")
    _seed_db(db)

    rows = A.build_rows(db, 1, "0.5")

    # The RB68 accession record now anchors against the MIBiG ref (pristine .408: 0 rows -> false NOVEL).
    assert any(r["strain"] == "RB68" and r["node_region"] == "WEGH01000001.1.region006"
               and r["mibig_accession"] == "BGC0001234" for r in rows)

    # The unbindable record is SURFACED, not dropped silently.
    err = capsys.readouterr().err
    assert "WARNING ANCHOR_LOCATOR_UNBOUND: mystery-contig-no-region.gbk" in err  # pristine .408: absent (RED)
    assert "NOT evidence of novelty" in err
