import hashlib

import pytest

from mamey import blastp_ebi


def _fasta(tmp_path):
    path = tmp_path / "query.faa"
    path.write_text(">protein_a\nMAA\n>protein_b\nMKKK\n")
    return str(path)


def test_valid_email_without_upload_ack_refuses_before_state_creation(
    tmp_path, monkeypatch, capsys
):
    state = tmp_path / "state.json"
    monkeypatch.setattr(blastp_ebi, "_post", lambda *args, **kwargs: pytest.fail("network reached"))
    with pytest.raises(ValueError, match="public.*upload|disclosure"):
        blastp_ebi.submit_ebi(
            _fasta(tmp_path), str(state), email="user@institution.edu"
        )
    assert not state.exists()
    text = capsys.readouterr().out
    assert "OUTBOUND SEQUENCE DISCLOSURE" in text
    assert blastp_ebi.BASE in text


def test_receipt_binds_exact_sequences(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(blastp_ebi, "_post", lambda *args, **kwargs: pytest.fail("network reached"))
    with pytest.raises(ValueError):
        blastp_ebi.submit_ebi(
            _fasta(tmp_path), str(tmp_path / "state.json"), email="user@institution.edu"
        )
    expected = hashlib.sha256(b"protein_a\x00MAA\nprotein_b\x00MKKK\n").hexdigest()
    text = capsys.readouterr().out
    assert "2 protein(s), 7 aa" in text and expected in text
    assert "uniprotkb_bacteria" in text


def test_acknowledged_receipt_precedes_transport(tmp_path, monkeypatch, capsys):
    observed = {}

    def stop_at_transport(*args, **kwargs):
        observed["before"] = capsys.readouterr().out
        raise KeyboardInterrupt("stop before real network")

    monkeypatch.setattr(blastp_ebi, "_post", stop_at_transport)
    with pytest.raises(KeyboardInterrupt):
        blastp_ebi.submit_ebi(
            _fasta(tmp_path),
            str(tmp_path / "state.json"),
            email="user@institution.edu",
            confirm_public_upload=True,
            throttle_sleep=lambda _: None,
        )
    assert "OUTBOUND SEQUENCE DISCLOSURE" in observed["before"]
    assert "sequence sha256" in observed["before"]


def test_ebi_parser_wires_upload_acknowledgement():
    from mamey.cli import build_parser

    parser = build_parser()
    planned = parser.parse_args(
        ["blastp-ebi", "--fasta", "query.faa", "--state", "state.json"]
    )
    assert not planned.confirm_public_upload
    live = parser.parse_args(
        [
            "blastp-ebi",
            "--fasta",
            "query.faa",
            "--state",
            "state.json",
            "--submit",
            "--confirm-public-sequence-upload",
        ]
    )
    assert live.submit and live.confirm_public_upload
