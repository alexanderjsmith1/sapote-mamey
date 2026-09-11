"""v9.7.47 (B-10) — ingest_package.infer_cohort must inherit the B-1 cohort resolution.

The run resolves WGS-accession-labelled public strains to SID via the embedded SID in the organism string
(cohort_resolver). The merge tool's infer_cohort previously used a bare ID-prefix and banked them as REF,
so the run and the bank disagreed on cohort label. infer_cohort now consults the resolver first and keeps
its finer TYPE/REF split only for genuine OTHER organisms.
"""
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
from ingest_package import infer_cohort  # noqa: E402


def test_wgs_accession_resolves_to_sid():
    # accession ID, but the organism carries the embedded SID -> SID (not REF)
    assert infer_cohort("WWGG00000000", "Streptomyces sp. SID8375") == "SID"
    assert infer_cohort("JAAGLM000000000", "Streptomyces sp. SID10815") == "SID"


def test_sid_prefix_still_sid():
    assert infer_cohort("SID8374", "Streptomyces sp.") == "SID"


def test_as_prefix_resolves_to_as():
    assert infer_cohort("AS-1", "Pseudonocardia sp.") == "AS"


def test_type_strain_marker_preserved():
    # genuine external type strain (no embedded SID) keeps the TYPE classification
    assert infer_cohort("GCA_000", "Streptomyces sp. ATCC 12345") == "TYPE"
    assert infer_cohort("GCA_001", "Amycolatopsis orientalis NRRL 2450") == "TYPE"


def test_plain_external_is_ref():
    assert infer_cohort("XYZ001", "Amycolatopsis sp.") == "REF"


def test_resolver_runtime_error_is_not_silently_reclassified(monkeypatch):
    """A loaded resolver failure is a real defect, not evidence for prefix fallback."""
    def fail_resolver(_sid, _taxonomy):
        raise RuntimeError("resolver execution failed")

    monkeypatch.setitem(
        sys.modules,
        "mamey.cohort_resolver",
        types.SimpleNamespace(resolve_cohort=fail_resolver),
    )
    with pytest.raises(RuntimeError, match="resolver execution failed"):
        infer_cohort("WWGG00000000", "Streptomyces sp. SID8375")
