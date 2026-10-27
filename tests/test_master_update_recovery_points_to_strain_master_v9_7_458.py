"""A failed master workbook update prints a recovery route that works.

The old line named `tools/ingest_package.py --package <pkg_dir> --master <path>`, and
ingest_package.py has no --master flag. The route is now the Strain Master inbox:
`strain-master submit` of the sealed package ZIP, then `verify` by a different --chat id, then
`apply`. This test stubs the failing update in a real bounded run, reads the printed line, parses
it with the real parser, and runs the submit, verify and apply against a fresh Strain Master.
"""
import json
import shlex

import pytest


def _recovery_lines(out: str) -> list[str]:
    lines = out.splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("recovery:"):
            return lines[i:i + 2]
    return []


@pytest.fixture
def failed_master_run(tmp_path, synthetic_single_contig_full_locus_zip, capsys):
    import openpyxl
    from mamey import master_workbook
    from mamey.cli import run_one_strain

    master = tmp_path / "master.xlsx"
    wb = openpyxl.Workbook()
    wb.save(master)

    def _boom(*_a, **_k):
        raise RuntimeError("stubbed master update failure")

    mp = pytest.MonkeyPatch()
    mp.setattr(master_workbook, "update_master_workbook", _boom)
    try:
        result = run_one_strain(
            strain_id="RECOV-1", display_name="RECOV-1",
            input_zip=str(synthetic_single_contig_full_locus_zip), outdir=str(tmp_path / "run"),
            mode="full", taxonomy="", source="", bioactivity="", json_mode="off",
            master_path=str(master),
        )
    finally:
        mp.undo()
    return result, capsys.readouterr().out


def test_printed_recovery_points_to_strain_master_and_runs(failed_master_run, tmp_path, monkeypatch):
    from pathlib import Path

    from mamey import strain_master as sm
    from mamey.cli import build_parser

    result, out = failed_master_run
    status = result["workbook_status"]["cumulative_master"]
    assert status["state"] == "FAILED"

    rec = _recovery_lines(out)
    assert rec, f"no recovery line printed:\n{out[-3000:]}"
    text = "\n".join(rec)
    assert "strain-master submit" in text
    assert not ("ingest_package.py --package" in text and "--master" in text)
    assert "verify" in rec[1] and "apply" in rec[1] and "different" in rec[1]
    assert "SAPOTE_STRAIN_MASTER" in rec[1]
    assert status["recovery_command"] == rec[0].split("recovery:", 1)[1].strip()

    # The printed submit command parses with the real parser and names the sealed ZIP.
    argv = shlex.split(rec[0].split("recovery:", 1)[1])
    assert argv[:3] == ["python", "mamey_run.py", "strain-master"]
    argv = [("tester-a" if a == "<your-id>" else a) for a in argv[2:]]
    assert not [a for a in argv if a.startswith("<")], argv
    parser = build_parser()
    root = tmp_path / "Strain Master"
    sm.init_master(str(root), name="Test master")
    monkeypatch.setenv("SAPOTE_STRAIN_MASTER", str(root))
    args = parser.parse_args(argv)
    assert args.action == "submit" and args.chat == "tester-a"
    assert len(args.files) == 1 and args.files[0] == result["package_zip"]
    assert Path(args.files[0]).is_file() and args.files[0].endswith("_Complete_Package.zip")

    # submit, verify by a different id, apply: the route the line names.
    sub = sm.submit([{"src": f, "what": args.what} for f in args.files], submitter=args.chat,
                    topic=args.topic, summary=args.summary, target=args.target)
    assert sub["status"] == "SUBMITTED"
    vargs = parser.parse_args(["strain-master", "verify", "--id", sub["id"], "--chat", "tester-b", "--accept",
                               "--checks", "2 ok: one file; 3 ok: strain id; 4 ok: no conflict; 6 ok: no claim"])
    assert sm.verify(vargs.id, verifier=vargs.chat, accept=True, checks=vargs.checks)["status"] == "ACCEPTED"
    aargs = parser.parse_args(["strain-master", "apply", "--id", sub["id"], "--chat", "tester-b"])
    applied = sm.apply_submission(aargs.id, chat=aargs.chat)
    assert json.dumps(applied)
    stored = root / "04 Gene clusters" / "Mamey packages" / Path(args.files[0]).name
    assert stored.is_file()


def test_ingest_package_has_no_master_flag():
    """Guard the premise: the old printed command could not run."""
    from pathlib import Path

    src = (Path(__file__).resolve().parents[1] / "tools" / "ingest_package.py").read_text(encoding="utf-8")
    assert '"--master"' not in src
