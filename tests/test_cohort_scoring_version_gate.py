"""Cohort scoring-version gate logic (DRAFT, v9.7.99). Unit-level; the build hook comes post-re-score."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
import pytest
from cohort_scoring_version_gate import (
    parse_engine_version, assert_uniform_scoring_engine, CohortVersionError)


def test_parse_engine_version():
    assert parse_engine_version("Mamey v1.9.96") == "1.9.96"
    assert parse_engine_version("v1.9.96") == "1.9.96"
    assert parse_engine_version("") is None


def test_uniform_cohort_passes():
    assert_uniform_scoring_engine({"AS-901": "Mamey v1.9.96", "AS-902": "Mamey v1.9.96"}, "1.9.96")


def test_mixed_versions_refuse():
    with pytest.raises(CohortVersionError) as e:
        assert_uniform_scoring_engine({"AS-901": "Mamey v1.9.96", "AS-902": "Mamey v1.9.91"}, "1.9.96")
    assert "AS-902=1.9.91" in str(e.value)


def test_unstamped_strain_refuses():
    with pytest.raises(CohortVersionError) as e:
        assert_uniform_scoring_engine({"AS-901": "Mamey v1.9.96", "AS-902": ""}, "1.9.96")
    assert "no recorded engine version" in str(e.value)


def test_empty_cohort_fails_closed():
    """v9.7.115: an empty cohort is a failure, not a vacuous pass (a fail-closed gate that says OK
    on zero strains has almost certainly been given a bad path)."""
    with pytest.raises(CohortVersionError):
        assert_uniform_scoring_engine({}, "1.9.98")


def test_unstamped_strain_is_failure():
    """A strain with no recorded engine version can't be certified — it must fail."""
    with pytest.raises(CohortVersionError):
        assert_uniform_scoring_engine({"S1": "Mamey v1.9.98", "S2": ""}, "1.9.98")


def test_offender_strain_named_in_error():
    """A strain scored under a different engine is named in the raised error."""
    with pytest.raises(CohortVersionError) as ei:
        assert_uniform_scoring_engine({"S1": "Mamey v1.9.98", "S2": "Mamey v1.9.84"}, "1.9.98")
    assert "S2" in str(ei.value)
