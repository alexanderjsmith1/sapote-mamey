"""AS-48 public-NP carve-out (v9.7.97).

The redactor's AS-NNN pattern collides with the public bacteriocin name 'enterocin AS-48'
(MIBiG BGC0000489). Before the carve-out it corrupted 'enterocin AS-48' -> 'enterocin AS-XXX'
in the shipped MIBiG reference index. These tests pin the carve-out and guard against
over-redaction (AS-48 only) and under-redaction (every real cohort/private ID still scrubbed).

NOTE: all AS-/AJS- literals below are synthetic (AS-901/902/903, AJS-001) or public-NP/boundary
tokens (AS-48, AS-480) on tools/test_synthetic_ids.txt — no real cohort strain appears here.
"""
import sys
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import redact_public_tier as R  # noqa: E402


def test_as48_is_not_redacted():
    assert R.redact_text("enterocin AS-48 (BGC0000489)", as_only=True) == "enterocin AS-48 (BGC0000489)"


@pytest.mark.parametrize("synthetic_id", ["AS-901", "AS-902", "AS-903", "AJS-001"])
def test_real_form_ids_still_redacted(synthetic_id):
    out = R.redact_text(f"strain {synthetic_id} here", as_only=True)
    assert "XXX" in out and synthetic_id not in out, f"{synthetic_id} not redacted: {out!r}"


def test_as48_boundary_is_exact():
    # only the exact token AS-48 is exempt; AS-480 (and AS-48N generally) is NOT
    assert R.redact_text("AS-480", as_only=True) == "AS-XXX"
    assert R.redact_text("AS-48 vs AS-480", as_only=True) == "AS-48 vs AS-XXX"


def test_private_count_excludes_as48():
    assert R._private_as_count("AS-48 and AS-901 and AS-902") == 2


def test_mibig_index_not_corrupted():
    """The shipped MIBiG reference index must say 'enterocin AS-48', never the redacted form."""
    import sys as _sys; _sys.path.insert(0, str(ROOT))
    from mamey import external_data as _xd
    _d = _xd.resolve("mibig")
    if _d is None:
        pytest.skip("MIBiG not provisioned (v9.7.362: user-provisioned, see docs/EXTERNAL_DATA.md)")
    idx = (_d / "mibig_reference_index.bacterial.json").read_text()
    assert "enterocin AS-48" in idx
    assert "enterocin AS-" + "XXX" not in idx, "MIBiG index carries a redaction-corrupted compound name"
