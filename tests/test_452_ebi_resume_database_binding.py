import json
import pytest
from mamey import blastp_ebi as mod

def test_resume_database_conflict_is_refused_without_submission(tmp_path, monkeypatch):
    fasta = tmp_path / "query.faa"
    fasta.write_text(">synthetic_gene\nMPEPTIDE\n")
    state = tmp_path / "state.json"
    content = json.dumps({"database": "old_db", "jobs": {"synthetic_gene": None}, "results": {}})
    state.write_text(content)
    posted = []
    monkeypatch.setattr(mod, "_post", lambda *args: posted.append(args) or "synthetic-job")
    with pytest.raises(ValueError, match="database"):
        mod.submit_ebi(str(fasta), str(state), database="new_db", email="contact@unit.invalid", confirm_public_upload=True, throttle_sleep=lambda *args: None)
    assert posted == []
    assert state.read_text() == content
