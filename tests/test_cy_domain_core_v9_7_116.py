"""v9.7.116: Cy (Heterocyclization) domains are assembly-line core in the §3 census.

The s3_census_generator._role_of() core list omitted heterocyclization domains, so a BGC whose
assembly line is Cy-domain-driven (thiazoline/oxazoline NRPS) had those genes mis-bucketed as
non-core. antiSMASH emits the full "Heterocyclization" token alongside Cy1..Cy7 subtype tags; we
match the full name (distinctive, collision-safe). (Divergence flagged in the pks_investigation handoff
pks_investigation handoff.)
"""
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mamey.s3_census_generator import _role_of  # noqa: E402

_CORE = "assembly-line core (NRPS/PKS)"


def test_heterocyclization_is_core():
    assert _role_of(["Heterocyclization", "AMP-binding"]) == _CORE
    assert _role_of(["Heterocyclization"]) == _CORE


def test_standard_nrps_core_unchanged():
    assert _role_of(["Condensation", "AMP-binding", "PCP"]) == _CORE
    assert _role_of(["PKS_KS", "PKS_AT"]) == _CORE
