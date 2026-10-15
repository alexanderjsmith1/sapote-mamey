"""Domain-tree spec fields are typed: approval is a non-blank string, the outgroup declaration a real
boolean, and the tip floor a positive integer (P300-071)."""
import json

import pytest

from mamey import domain_tree as DT

BASE = {"domain_class": "PKS_KS", "gbk_dir": "x", "outdir": "y", "title": "t",
        "approved_by": "the owner", "allow_no_outgroup": True}


def _spec(tmp_path, **changes):
    p = tmp_path / "spec.json"
    p.write_text(json.dumps({**BASE, **changes}))
    return p


@pytest.mark.parametrize("value", [None, 0, False, "  "])
def test_approved_by_must_be_a_non_blank_string(tmp_path, value):
    with pytest.raises(DT.DomainTreeError, match="SPEC_INCOMPLETE.*approved_by"):
        DT.load_spec(_spec(tmp_path, approved_by=value))


@pytest.mark.parametrize("value", ["false", "0", 1, 0, None])
def test_allow_no_outgroup_must_be_a_json_boolean(tmp_path, value):
    with pytest.raises(DT.DomainTreeError, match="SPEC_INVALID_FIELD: allow_no_outgroup"):
        DT.load_spec(_spec(tmp_path, allow_no_outgroup=value))


@pytest.mark.parametrize("value", [0, -1, True, 2.5, "4", None])
def test_min_tips_must_be_a_positive_integer(tmp_path, value):
    with pytest.raises(DT.DomainTreeError, match="SPEC_INVALID_FIELD: min_tips"):
        DT.load_spec(_spec(tmp_path, min_tips=value))


def test_valid_spec_still_loads(tmp_path):
    spec = DT.load_spec(_spec(tmp_path, min_tips=6))
    assert spec["min_tips"] == 6 and spec["allow_no_outgroup"] is True
    spec = DT.load_spec(_spec(tmp_path, allow_no_outgroup=False, outgroup="Ref_OUT"))
    assert spec["min_tips"] == DT.MIN_TIPS and spec["allow_no_outgroup"] is False


def test_build_tree_refuses_a_null_approval_before_any_run(tmp_path):
    fa = tmp_path / "s.fasta"
    fa.write_text(">a\nMKV\n")
    calls = []
    for value in (None, 0, "  "):
        with pytest.raises(DT.DomainTreeError, match="APPROVAL_REQUIRED"):
            DT.build_tree(fa, tmp_path, approved_by=value, runner=lambda cmd, **kw: calls.append(cmd))
    assert calls == []


@pytest.mark.parametrize("value", [0, -3, True, 2.5])
def test_stage_domains_refuses_a_bad_tip_floor(tmp_path, value):
    with pytest.raises(DT.DomainTreeError, match="SPEC_INVALID_FIELD: min_tips"):
        DT.stage_domains([], "PKS_KS", tmp_path / "o", min_tips=value)
