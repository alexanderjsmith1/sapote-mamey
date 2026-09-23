import json

import pytest

from mamey import blastp_autoharness as ah


def _saved_state(package, *, strain="STRAIN_A", channel="nr"):
    state = ah.new_state(package, strain, [], channel=channel)
    state["n_submits"] = 3
    ah.save_state(package, state)
    return ah.state_path(package).read_bytes()


@pytest.mark.parametrize(
    ("field", "requested", "message"),
    [
        ("channel", "clustered_nr", "channel"),
        ("strain", "STRAIN_B", "strain"),
    ],
)
def test_resume_refuses_identity_mismatch_without_changing_state(
    tmp_path, monkeypatch, field, requested, message
):
    package = tmp_path / "package"
    before = _saved_state(package)
    monkeypatch.setattr(
        ah,
        "build_worklist",
        lambda *args, **kwargs: pytest.fail("mismatched state rebuilt a worklist"),
    )
    kwargs = {"strain": "STRAIN_A", "channel": "nr"}
    kwargs[field] = requested
    with pytest.raises(ValueError, match=message):
        ah.init_state(package, **kwargs, resume=True)
    assert ah.state_path(package).read_bytes() == before


def test_matching_resume_preserves_progress_and_updates_only_cadence(tmp_path):
    package = tmp_path / "package"
    _saved_state(package)
    resumed = ah.init_state(
        package,
        "STRAIN_A",
        channel="nr",
        submit_interval_s=901,
        ingest_interval_s=1802,
        resume=True,
    )
    assert resumed["n_submits"] == 3
    assert resumed["channel"] == "nr"
    assert resumed["strain"] == "STRAIN_A"
    assert resumed["submit_interval_s"] == 901
    assert resumed["ingest_interval_s"] == 1802


@pytest.mark.parametrize("missing", ["channel", "strain"])
def test_legacy_or_malformed_resume_without_identity_is_held(tmp_path, missing):
    package = tmp_path / "package"
    _saved_state(package)
    path = ah.state_path(package)
    state = json.loads(path.read_text())
    del state[missing]
    path.write_text(json.dumps(state))
    with pytest.raises(ValueError, match=missing):
        ah.init_state(package, "STRAIN_A", channel="nr", resume=True)


def test_resume_false_builds_requested_channel_instead_of_reusing_state(tmp_path, monkeypatch):
    package = tmp_path / "package"
    before = _saved_state(package)
    monkeypatch.setattr(ah, "build_worklist", lambda *args, **kwargs: [])
    fresh = ah.init_state(
        package,
        "STRAIN_B",
        channel="clustered_nr",
        resume=False,
    )
    assert fresh["strain"] == "STRAIN_B"
    assert fresh["channel"] == "clustered_nr"
    # init_state itself does not commit the replacement.
    assert ah.state_path(package).read_bytes() == before
