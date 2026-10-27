"""The evidence-disagreements audit write is create-exclusive.

The old code checked that the output was absent, then called write_text. A second run that
finished in between was silently overwritten. The audit now refuses to replace a file that
appears after the precheck, and a finished audit is never half-written.
"""
import json
import sys

import pytest


def test_audit_that_appears_after_the_precheck_is_not_overwritten(tmp_path, monkeypatch):
    from mamey import evidence_disagreements as ed
    from tests.test_evidence_disagreements import fixture_view
    selection = fixture_view(tmp_path)
    out = tmp_path / "audit.json"
    real = ed.Explorer.check_stable

    def other_run_finishes_first(self, *a, **k):
        if not out.exists():
            out.write_text("OTHER RUN")
        return real(self, *a, **k)

    monkeypatch.setattr(ed.Explorer, "check_stable", other_run_finishes_first)
    monkeypatch.setattr(sys, "argv", ["evidence_disagreements", "--selection", str(selection), "--audit", str(out)])
    with pytest.raises(SystemExit) as stop:
        ed.main()
    assert stop.value.code != 0
    assert out.read_text() == "OTHER RUN"
    assert [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp")] == []


def test_fresh_audit_is_written_complete(tmp_path, monkeypatch):
    from mamey import evidence_disagreements as ed
    from tests.test_evidence_disagreements import fixture_view
    selection = fixture_view(tmp_path)
    out = tmp_path / "audit.json"
    monkeypatch.setattr(sys, "argv", ["evidence_disagreements", "--selection", str(selection), "--audit", str(out)])
    ed.main()
    assert json.loads(out.read_text())["status"] == "SOURCE_BOUND_ENGINEERING_REVIEW_ONLY"
    assert [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp")] == []


def test_write_new_file_refuses_existing_and_dangling_symlink(tmp_path):
    from mamey.evidence_disagreements import write_new_file
    target = tmp_path / "a.json"
    write_new_file(target, "first")
    with pytest.raises(FileExistsError):
        write_new_file(target, "second")
    assert target.read_text() == "first"
    link = tmp_path / "dangling.json"
    link.symlink_to(tmp_path / "nowhere")
    with pytest.raises(FileExistsError):
        write_new_file(link, "x")
    assert not (tmp_path / "nowhere").exists()
    assert [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp")] == []
