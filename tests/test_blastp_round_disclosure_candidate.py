import hashlib
from types import SimpleNamespace

import pytest

from mamey import blastp_online


def _plan():
    batches = [[("protein_a", "MAA"), ("protein_b", "MKKK")]]
    return {
        "strain": "GENERIC",
        "round": 1,
        "full_bgcs": [],
        "sampled_bgcs": [],
        "n_proteins": 2,
        "n_batches": 1,
        "batches": batches,
        "plan": [],
    }


def _args(tmp_path, **changes):
    values = dict(
        package=str(tmp_path / "package"),
        outdir=str(tmp_path / "plan"),
        full_top=3,
        sample_per_bgc=1,
        round_num=1,
        run=False,
        confirm_public_upload=False,
        database="nr",
        evalue="1e-5",
    )
    values.update(changes)
    return SimpleNamespace(**values)


@pytest.fixture
def transport_spy(monkeypatch):
    calls = []

    def spy(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("network transport reached")

    monkeypatch.setattr(blastp_online, "plan_round", lambda *args, **kwargs: _plan())
    monkeypatch.setattr(blastp_online, "run_batches_online", spy)
    return calls


def test_default_round_is_plan_only(tmp_path, transport_spy, capsys):
    assert blastp_online.blastp_round_command(_args(tmp_path)) == 0
    assert transport_spy == []
    assert "DRY RUN" in capsys.readouterr().out


def test_run_without_acknowledgement_is_refused(tmp_path, transport_spy, capsys):
    assert blastp_online.blastp_round_command(_args(tmp_path, run=True)) == 1
    text = capsys.readouterr().out
    assert "OUTBOUND SEQUENCE DISCLOSURE" in text
    assert "REFUSING" in text
    assert transport_spy == []


def test_disclosure_binds_exact_planned_sequences(tmp_path, transport_spy, capsys):
    blastp_online.blastp_round_command(_args(tmp_path, run=True))
    expected = hashlib.sha256(b"protein_a\x00MAA\nprotein_b\x00MKKK\n").hexdigest()
    text = capsys.readouterr().out
    assert blastp_online.NCBI_URL in text
    assert "2 protein(s), 7 aa, in 1 batch(es)" in text
    assert expected in text


def test_both_flags_open_the_gate(tmp_path, transport_spy):
    with pytest.raises(AssertionError, match="network transport reached"):
        blastp_online.blastp_round_command(
            _args(tmp_path, run=True, confirm_public_upload=True)
        )


def test_round_parser_wires_acknowledgement_flag():
    from mamey.cli import build_parser

    parser = build_parser()
    planned = parser.parse_args(["blastp-round", "--package", "example"])
    assert not planned.run and not planned.confirm_public_upload
    live = parser.parse_args(
        [
            "blastp-round",
            "--package",
            "example",
            "--run",
            "--confirm-public-sequence-upload",
        ]
    )
    assert live.run and live.confirm_public_upload
