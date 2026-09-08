"""EBI submission safety (v9.7.382): valid email required, 30-record cap, active-job refusal.

All tests are HERMETIC — no network. The validation paths raise before any request; the one
success path monkeypatches the module _post so nothing is submitted.
"""
import json
import pytest
from mamey import blastp_ebi


def _fasta(tmp_path, n):
    p = tmp_path / "q.faa"
    p.write_text("".join(f">lt{i}\nMKAAA\n" for i in range(n)))
    return str(p)


def test_missing_email_refused(tmp_path):
    with pytest.raises(ValueError, match="requires a valid contact email"):
        blastp_ebi.submit_ebi(_fasta(tmp_path, 2), str(tmp_path / "s.json"), email=None)


def test_placeholder_email_refused(tmp_path):
    with pytest.raises(ValueError, match="placeholder"):
        blastp_ebi.submit_ebi(_fasta(tmp_path, 2), str(tmp_path / "s.json"),
                              email="sapote-mamey@example.org")


def test_invalid_email_refused(tmp_path):
    with pytest.raises(ValueError, match="not a valid email"):
        blastp_ebi.submit_ebi(_fasta(tmp_path, 2), str(tmp_path / "s.json"), email="not-an-email")


def test_over_30_records_refused(tmp_path):
    with pytest.raises(ValueError, match="30 jobs per transaction"):
        blastp_ebi.submit_ebi(_fasta(tmp_path, 31), str(tmp_path / "s.json"),
                              email="user@institution.edu")


def test_active_jobs_block_new_transaction(tmp_path):
    state = tmp_path / "s.json"
    state.write_text(json.dumps({
        "fasta": "x", "database": "uniprotkb_bacteria", "transport": "EBI",
        "jobs": {"lt0": "ebi-job-123"}, "results": {"lt0": None},
    }))
    with pytest.raises(ValueError, match="already submitted and not yet\\s+harvested"):
        blastp_ebi.submit_ebi(_fasta(tmp_path, 2), str(state), email="user@institution.edu")


def test_valid_bounded_submission(tmp_path, monkeypatch):
    calls = []
    def fake_post(kind, payload):
        calls.append(payload["email"])
        return "ebi-job-" + payload["sequence"].split("\n")[0].lstrip(">")
    monkeypatch.setattr(blastp_ebi, "_post", fake_post)
    d = blastp_ebi.submit_ebi(_fasta(tmp_path, 2), str(tmp_path / "s.json"),
                              email="user@institution.edu", throttle_sleep=lambda _s: None)
    assert sum(1 for j in d["jobs"].values() if j and not str(j).startswith("ERR")) == 2
    assert calls == ["user@institution.edu", "user@institution.edu"]  # real email, never a placeholder
