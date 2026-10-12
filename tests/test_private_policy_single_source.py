"""Core hard refusals and metadata-based figure privacy have distinct roles."""

from tests._synthetic_identity_fixture import synthetic_namespace_id
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_unbound_figure_identity_is_private_even_when_public_looking():
    from mamey.cohort_figures import is_private
    for sid in ("AS-" + "987654", "SID987654", "public_reference", "AJS-" + "987654"):
        assert is_private(sid)
    rows = {"public_reference": {"privacy": {"effective_release": "PUBLIC"}}}
    assert not is_private("public_reference", rows)


def test_unbound_release_and_figure_defaults_agree():
    from mamey.dedup_and_guard import derive_release
    from mamey.cohort_figures import is_private
    for sid in ("AS-" + "987654", "SID987654", "public_reference"):
        assert (derive_release(sid) == "PRIVATE") == is_private(sid)


def test_intake_guard_preserves_explicit_public_independently_of_figure_default(monkeypatch):
    import sys
    monkeypatch.setitem(sys.modules, "mamey.cohort_figures", None)
    spec = importlib.util.spec_from_file_location("intake_guard_policy_test", ROOT / "tools/intake_harness.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert not module._is_private("public_reference")
    assert not module._is_private("AS-" + "987654")
    assert module._is_private("AJS-" + "987654")
    assert module._is_private((synthetic_namespace_id('PENDING', width=None, case_index=917, separator=True)))
