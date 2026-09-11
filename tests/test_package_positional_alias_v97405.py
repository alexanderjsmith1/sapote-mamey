"""v9.7.405 — `--package` accepts a positional alias on every package-taking subcommand (WAC items 12/13/15)."""
from __future__ import annotations

import argparse

import pytest

from mamey import cli


def _parse(argv):
    parser = cli.build_parser()
    req = cli._install_package_positional_alias(parser)
    return parser.parse_args(argv), req


CMD = "render-figures"   # takes a required --package and declares no positional of its own


def test_positional_fills_package_and_flag_still_works(tmp_path):
    a, _ = _parse([CMD, str(tmp_path)])
    assert getattr(a, cli._PACKAGE_POSITIONAL) == str(tmp_path) and a.package is None  # main() copies it
    b, _ = _parse([CMD, "--package", str(tmp_path)])
    assert b.package == str(tmp_path) and getattr(b, cli._PACKAGE_POSITIONAL) is None


def test_subcommands_with_their_own_positional_are_left_alone():
    parser = cli.build_parser()
    req = cli._install_package_positional_alias(parser)
    assert "validate" not in req   # `validate <package_dir>` already has a positional; untouched


def test_every_package_subcommand_without_own_positionals_gained_the_alias():
    parser = cli.build_parser()
    req = cli._install_package_positional_alias(parser)
    assert CMD in req and req[CMD] is True and len(req) >= 15
    subs = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction)).choices
    for name in req:
        dests = [a.dest for a in subs[name]._actions]
        assert cli._PACKAGE_POSITIONAL in dests, name


def test_missing_package_errors_with_canonical_invocation(capsys):
    with pytest.raises(SystemExit) as e:
        cli.main([CMD])
    assert e.value.code == 2
    err = capsys.readouterr().err
    assert f"python mamey_run.py {CMD} --package <package_dir>" in err


def test_conflicting_spellings_are_refused(capsys, tmp_path):
    other = tmp_path / "other"; other.mkdir()
    with pytest.raises(SystemExit):
        cli.main([CMD, str(other), "--package", str(tmp_path)])
    assert "canonical invocation" in capsys.readouterr().err


# BC2-408: `test_every_package_subcommand_without_own_positionals_gained_the_alias` above only
# checks that `_PACKAGE_POSITIONAL` appears in each subcommand's `dests` -- it never actually
# parses a real positional invocation for anything but the one hardcoded CMD ("render-figures").
# That coverage gap hid a real bug: when --package lives inside a REQUIRED mutually-exclusive
# group (bigscape's --package/--runs-dir/--input-gbk-dir; blastp-availability's
# --runs-dir/--package), the OLD code added the positional as a bare top-level argument, which
# is not a member of that group -- so argparse's own "one of these is required" check never
# recognized the positional as satisfying it. Verified live pre-fix: `mamey bigscape <path>` and
# `mamey blastp-availability <path>` both refused with "one of the arguments ... is required"
# even though a package path WAS given positionally -- the v9.7.405 convergence silently never
# worked for these two commands. This test parses every affected subcommand end-to-end (not just
# checking a dest name exists), the general form the coverage gap needed.

def test_every_affected_subcommand_actually_accepts_a_bare_positional_end_to_end(tmp_path):
    parser = cli.build_parser()
    req = cli._install_package_positional_alias(parser)
    subs = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction)).choices
    for name in req:
        sub = subs[name]
        # only exercise a bare `<name> <path>` invocation on subcommands where --package (or its
        # containing mutually-exclusive group) is the ONLY required piece -- some subcommands
        # (e.g. ingest-blastp: --master/--strain/--hit-table) legitimately need more than a
        # package path and would fail for unrelated reasons, which is not this mechanism's bug
        # to catch.
        other_required = [a for a in sub._actions
                          if a.required and a.dest not in ("package", cli._PACKAGE_POSITIONAL)
                          and not any(a in g._group_actions
                                      for g in getattr(sub, "_mutually_exclusive_groups", ()))]
        if other_required:
            continue
        # a bare positional alone must parse without raising, for every subcommand this
        # mechanism claims to have wired up -- not just have the attribute present.
        args = parser.parse_args([name, str(tmp_path)])
        assert getattr(args, cli._PACKAGE_POSITIONAL) == str(tmp_path), name


def test_bigscape_and_blastp_availability_accept_positional_package(tmp_path):
    """The two commands whose --package lives in a required mutually-exclusive group."""
    for name in ("bigscape", "blastp-availability"):
        a, _ = _parse([name, str(tmp_path)])
        assert getattr(a, cli._PACKAGE_POSITIONAL) == str(tmp_path)
        assert a.package is None  # main() copies it in; the raw parse leaves it on the alias dest


def test_bigscape_positional_still_mutually_exclusive_with_runs_dir(tmp_path):
    parser = cli.build_parser()
    cli._install_package_positional_alias(parser)
    with pytest.raises(SystemExit):
        parser.parse_args(["bigscape", str(tmp_path), "--runs-dir", str(tmp_path)])


def test_bigscape_still_refuses_when_nothing_given():
    parser = cli.build_parser()
    cli._install_package_positional_alias(parser)
    with pytest.raises(SystemExit):
        parser.parse_args(["bigscape"])
