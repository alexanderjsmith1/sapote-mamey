"""verify-citations reports unchecked files and empty inputs as holds, never as a PASS."""
from argparse import Namespace

import mamey.bgc_citation_gate as gate
from mamey.cli import verify_citations_command

CLEAN = "PENDING-1 NODE_3_length_100_cov_2 region002 BGC012 carries a PKS.\n"
NODELESS = "PENDING-1 BGC012 carries a PKS.\n"


def _run(path, capsys):
    code = verify_citations_command(Namespace(path=str(path)))
    out = capsys.readouterr()
    return code, out.out, out.err


def test_empty_directory_is_a_no_input_hold(tmp_path, capsys):
    code, out, _ = _run(tmp_path, capsys)
    assert code == 2
    assert "HOLD_NO_INPUT" in out and "PASS" not in out


def test_unreadable_file_is_unchecked_not_pass(tmp_path, capsys):
    (tmp_path / "good.md").write_text(CLEAN, encoding="utf-8")
    (tmp_path / "folder.md").mkdir()  # a directory named *.md cannot be read as text
    code, out, err = _run(tmp_path, capsys)
    assert code == 2
    assert "HOLD_UNCHECKED" in out and "2 found, 1 checked, 1 unchecked" in out
    assert "[unchecked]" in err and "folder.md" in err


def test_gate_exception_is_unchecked_not_pass(tmp_path, capsys, monkeypatch):
    (tmp_path / "a.md").write_text(CLEAN, encoding="utf-8")

    def boom(_text):
        raise RuntimeError("gate failed")

    monkeypatch.setattr(gate, "gate_text", boom)
    code, out, err = _run(tmp_path, capsys)
    assert code == 2
    assert "1 found, 0 checked, 1 unchecked" in out and "gate failed" in err


def test_real_finding_still_fails_with_counts(tmp_path, capsys):
    (tmp_path / "a.md").write_text(CLEAN, encoding="utf-8")
    (tmp_path / "b.md").write_text(NODELESS, encoding="utf-8")
    (tmp_path / "c.md").mkdir()
    code, out, _ = _run(tmp_path, capsys)
    assert code == 1
    assert "FAIL — 1 node-less" in out and "3 found, 2 checked, 1 unchecked" in out


def test_clean_inputs_still_pass(tmp_path, capsys):
    (tmp_path / "a.md").write_text(CLEAN, encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.md").write_text(CLEAN, encoding="utf-8")
    code, out, _ = _run(tmp_path, capsys)
    assert code == 0
    assert "PASS" in out and "2 found, 2 checked, 0 unchecked" in out


def test_single_file_and_missing_path_unchanged(tmp_path, capsys):
    f = tmp_path / "one.md"
    f.write_text(CLEAN, encoding="utf-8")
    assert _run(f, capsys)[0] == 0
    code, _, err = _run(tmp_path / "absent.md", capsys)
    assert code == 2 and "no such path" in err
