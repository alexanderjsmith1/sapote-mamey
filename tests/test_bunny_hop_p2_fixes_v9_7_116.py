"""v9.7.116: behavioral regression tests for the carded Bunny Hop P2 fixes (Sessions 18-22)."""
import sys
import tempfile
import os
import csv
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))


def test_check_antismash_profile_empty_fails_closed():
    """S20 P2: an empty packages root must fail closed (not vacuously pass), --warn-only softens."""
    import check_antismash_profile as C
    d = tempfile.mkdtemp()
    assert C.main([d]) == 1            # no manifests -> fail closed
    assert C.main([d, "--warn-only"]) == 0   # softened


def test_intake_harness_append_rows_deterministic_columns():
    """S19 P2: derived column order must be deterministic (sorted), not set-iteration order."""
    import intake_harness as I
    d = tempfile.mkdtemp()
    p = os.path.join(d, "ck.csv")
    I.append_rows(p, [{"zeta": 1, "alpha": 2, "mu": 3}])   # no header_order -> sorted
    hdr = next(csv.reader(open(p)))
    assert hdr == sorted(hdr) == ["alpha", "mu", "zeta"]


def test_intake_harness_append_rows_atomic_no_tmp_left():
    """The atomic write must not leave a .tmp sibling behind on success."""
    import intake_harness as I
    d = tempfile.mkdtemp()
    p = os.path.join(d, "ck.csv")
    I.append_rows(p, [{"a": 1, "b": 2}])
    assert not os.path.exists(p + ".tmp")
    assert os.path.exists(p)
