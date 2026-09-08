"""v9.7.152: --chatgpt-safe renamed to --capped-session (assistant-neutral).

The old flags remain as deprecated aliases (same dest, same behavior, plus a
one-line deprecation notice). These tests pin:
  1. both spellings parse to the same dest,
  2. the capped-session profile fires identically under either spelling,
  3. the deprecation notice fires ONLY for the old alias.
"""
import sys
from mamey import cli


def _parse(argv):
    parser = cli.build_parser() if hasattr(cli, "build_parser") else None
    if parser is None:
        import pytest
        pytest.skip("build_parser not exposed")
    return parser.parse_args(argv)


def test_both_spellings_set_same_dest():
    base = ["run", "--strain", "T", "--input-zip", "x.zip", "--mode", "gold"]
    a_new = _parse(base + ["--capped-session"])
    a_old = _parse(base + ["--chatgpt-safe"])
    assert a_new.chatgpt_safe is True
    assert a_old.chatgpt_safe is True
    assert a_new.chatgpt_safe == a_old.chatgpt_safe


def test_followup_both_spellings():
    base = ["run", "--strain", "T", "--input-zip", "x.zip", "--mode", "gold"]
    a_new = _parse(base + ["--capped-session", "--capped-followup"])
    a_old = _parse(base + ["--chatgpt-safe", "--chatgpt-followup"])
    assert a_new.chatgpt_followup is True
    assert a_old.chatgpt_followup is True


def test_deprecation_notice_only_on_old_alias(capsys, monkeypatch):
    from argparse import Namespace
    # v9.7.160: gold no longer FATALs in a capped session, so run_command now proceeds into
    # run_one_strain — stub it so this test exercises only the alias-deprecation-notice branch.
    monkeypatch.setattr(cli, "run_one_strain", lambda **kw: {"status": "MAMEY_COMPLETE"})
    defaults = dict(
        strain="T", input_zip="x.zip", strains=None, mode="gold",
        chatgpt_safe=True, chatgpt_followup=False, brief="standard",
        json_evidence="bounded", require_workbook=False, locus_maps="auto",
        heartbeat_seconds=None, display_name=None, master=None, taxonomy=None,
        source=None, bioactivity="default", antismash_profile="unknown",
        release=None, metadata_csv=None, token_budget="standard", outdir="out",
    )

    # old alias present in argv -> notice fires
    monkeypatch.setattr(sys, "argv", ["mamey", "run", "--chatgpt-safe", "--mode", "gold"])
    cli.run_command(Namespace(**dict(defaults)))
    out = capsys.readouterr().out
    assert "deprecated" in out.lower()
    assert "--capped-session" in out

    # only new flag in argv -> no deprecation notice
    monkeypatch.setattr(sys, "argv", ["mamey", "run", "--capped-session", "--mode", "gold"])
    cli.run_command(Namespace(**dict(defaults)))
    out2 = capsys.readouterr().out
    assert "deprecated" not in out2.lower()
