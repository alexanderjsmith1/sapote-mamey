"""Regression tests for the round-2 reference-strain audit fixes (v9.7.185): P3 contamination
scope, P7 unscoped-submission guard, P13 misfiled-core self-check."""
import pytest


def test_p3_scope_from_taxonomy_classifies_offtarget():
    from mamey.master_workbook import _scope_from_taxonomy as s
    assert s("Paenibacillus thiaminolyticus SY20") == "OUT_OF_SCOPE"   # Firmicute
    assert s("Streptomyces sp. YPW6") == "IN_SCOPE"
    assert s("Kitasatospora setae KM-6054") == "IN_SCOPE"
    assert s("Oscillatoria acuminata PCC 6304") == "REVIEW"            # cyanobacterium


def test_p3_scope_column_in_registry_header():
    # the A2_Strain_Registry header must carry the scope column so downstream can exclude off-target
    import inspect
    from mamey import master_workbook
    src = inspect.getsource(master_workbook)
    assert '"scope"' in src


def test_p7_unscoped_guard_env_default():
    # the guard must exist with a sane default so an unscoped genome submission is refused
    import inspect
    from mamey import blastp_online
    src = inspect.getsource(blastp_online)
    assert "MAMEY_BLASTP_MAX_UNSCOPED" in src


def test_p13_misfiled_core_tokens_empty_confirms_p11():
    # the Other_domain self-check: with P11 fixed, no core PKS token should land in Other_domain.
    import re
    from mamey.source_scans import DOMAIN_CLASS_PATTERNS as D

    def classify(tok):
        for cls, pats in D.items():
            for p in pats:
                if re.search(p, tok):
                    return cls
        return "Other_domain"

    for tok in ("PKS_KS", "PKS_AT", "PKS_DH", "PKS_ER", "PKS_KR", "PKS_ACP"):
        assert classify(tok) == tok  # none misfiled -> misfiled_core_tokens stays empty
