import hashlib
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "blastp_campaign_disclosure", ROOT / "tools" / "blastp_campaign.py"
)
assert SPEC and SPEC.loader
bc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bc)


def _batch(tmp_path):
    batches = tmp_path / "batches"
    batches.mkdir()
    (batches / "query.faa").write_text(
        ">GENERIC|node_1|gene=protein_a\nMAA\n"
        ">GENERIC|node_1|gene=protein_b\nMKKK\n"
    )
    return batches


def _args(tmp_path, **changes):
    values = dict(
        batches=str(_batch(tmp_path)),
        out=str(tmp_path / "run"),
        database="nr",
        hits=6,
        submit_gap=0,
        confirm_public_upload=False,
    )
    values.update(changes)
    return SimpleNamespace(**values)


def test_submit_without_acknowledgement_refuses_before_output_creation(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setattr(bc, "_post", lambda *args, **kwargs: pytest.fail("network reached"))
    args = _args(tmp_path)
    assert bc.cmd_submit(args) == 1
    assert not (tmp_path / "run").exists()
    text = capsys.readouterr().out
    assert "OUTBOUND SEQUENCE DISCLOSURE" in text and "REFUSING" in text


def test_receipt_binds_only_pending_sequences(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(bc, "_post", lambda *args, **kwargs: pytest.fail("network reached"))
    args = _args(tmp_path)
    bc.cmd_submit(args)
    expected = hashlib.sha256(
        b"GENERIC|node_1|protein_a\x00MAA\n"
        b"GENERIC|node_1|protein_b\x00MKKK\n"
    ).hexdigest()
    text = capsys.readouterr().out
    assert bc.NCBI in text and "2 protein(s), 7 aa" in text
    assert expected in text


def test_acknowledged_submit_prints_receipt_before_transport(tmp_path, monkeypatch, capsys):
    observed = {}

    def stop_at_transport(fields, timeout=45):
        observed["before"] = capsys.readouterr().out
        raise KeyboardInterrupt("stop before any real network")

    monkeypatch.setattr(bc, "_post", stop_at_transport)
    with pytest.raises(KeyboardInterrupt):
        bc.cmd_submit(_args(tmp_path, confirm_public_upload=True))
    assert "OUTBOUND SEQUENCE DISCLOSURE" in observed["before"]
    assert "sequence sha256" in observed["before"]


def test_submit_parser_requires_explicit_acknowledgement_flag(tmp_path, monkeypatch):
    batches = _batch(tmp_path)
    parser_args = ["submit", "--batches", str(batches), "--out", str(tmp_path / "run")]
    # Patch the command so parsing can be tested without writing or contacting the network.
    monkeypatch.setattr(bc, "cmd_submit", lambda args: int(args.confirm_public_upload))
    assert bc.main(parser_args) == 0
    assert bc.main([*parser_args, "--confirm-public-sequence-upload"]) == 1
