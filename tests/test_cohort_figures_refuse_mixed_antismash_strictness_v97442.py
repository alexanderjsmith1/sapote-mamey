"""Cohort figures must not sum region/class counts across antiSMASH detection strictness."""
import json

import pytest

from mamey.figure_policy import FigurePolicyError
from mamey.interactive_figures.figure_set_renderer import _load_with_benchmarks
from mamey.interactive_figures.widget_data import _antismash_profile, antismash_profile_counts


def _payload(tmp_path, profiles, ack=None):
    strains = {}
    for i, prof in enumerate(profiles, start=1):
        rec = {"governance": "GOVERNED", "classes": {"NRPS": {"total": 3}}}
        if prof is not None:
            rec["antismashProfile"] = prof
        strains[f"AS-{i}"] = rec
    meta = {} if ack is None else {"antismashProfileMixAcknowledged": ack}
    path = tmp_path / "widget.json"
    path.write_text(json.dumps({"meta": meta, "strains": strains}), encoding="utf-8")
    return path


def test_single_profile_loads(tmp_path):
    _load_with_benchmarks(_payload(tmp_path, ["loose", "loose", "loose"]))


def test_payload_without_the_field_is_unchanged(tmp_path):
    _load_with_benchmarks(_payload(tmp_path, [None, None]))


def test_mixed_profiles_refuse_and_name_the_strains(tmp_path):
    with pytest.raises(FigurePolicyError) as err:
        _load_with_benchmarks(_payload(tmp_path, ["loose", "relaxed", "relaxed"]))
    assert err.value.code == "FIGURE_ANTISMASH_PROFILE_MIXED"
    assert "loose: 1 (AS-1)" in str(err.value) and "relaxed: 2" in str(err.value)


def test_partially_recorded_cohort_refuses(tmp_path):
    with pytest.raises(FigurePolicyError):
        _load_with_benchmarks(_payload(tmp_path, ["loose", None]))


def test_single_unknown_profile_refuses(tmp_path):
    with pytest.raises(FigurePolicyError):
        _load_with_benchmarks(_payload(tmp_path, ["unknown", "unknown"]))


def test_exact_acknowledgement_admits_the_mix(tmp_path):
    _load_with_benchmarks(_payload(tmp_path, ["loose", "relaxed"], ack={"loose": 1, "relaxed": 1}))


def test_stale_acknowledgement_refuses(tmp_path):
    with pytest.raises(FigurePolicyError, match="stale"):
        _load_with_benchmarks(_payload(tmp_path, ["loose", "relaxed", "relaxed"],
                                       ack={"loose": 1, "relaxed": 1}))


def test_profile_is_read_from_the_full_manifest(tmp_path):
    pkg = tmp_path / "package"
    pkg.mkdir()
    (pkg / "AS-9_manifest_short.json").write_text(json.dumps({"mamey_version": "1.9.169"}))
    assert _antismash_profile(pkg, "AS-9") == "unrecorded"
    (pkg / "manifest.json").write_text(json.dumps({"antismash_profile": "Loose"}))
    assert _antismash_profile(pkg, "AS-9") == "loose"
    (pkg / "manifest.json").write_text("{not json")
    assert _antismash_profile(pkg, "AS-9") == "unknown"


def test_profile_counts():
    recs = {"a": {"antismashProfile": "loose"}, "b": {}, "c": {"antismashProfile": "loose"}}
    assert antismash_profile_counts(recs, recs) == {"loose": 2, "unrecorded": 1}
