"""test_claim_safety_auto_derive_v9_7_153.py — Part-2 Finding 3.

The `mamey claim-safety` CLI previously called `lint_claim_safety_report()` with no
`compound_names`, permanently locking every command-line invocation onto the heuristic
path the module's own comments describe as the weaker fallback. On a real report this
produced 244 findings (~241 false positives); supplying the real compound names dropped
it to 3. Fix: `--package <dir>` auto-derives the compound-name set from the package's own
`KCB_top` triage-board candidates and uses the robust path by default; `--compound-names`
remains as an explicit override; a bare invocation with neither still works (heuristic)
but now prints a one-line notice rather than silently using the weaker path.

Fixtures use synthetic AS-TEST data only.
"""
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tools"))

import claim_safety_linter as csl
from mamey import cli


# ── derive_compound_names_from_package ──────────────────────────────────────────

def _mk_triage(tmp_path, rows):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    lines = ["BGC_ID,KCB_top,Boundary"]
    lines.extend(rows)
    (pkg / "AS-TEST_4_triage_board.csv").write_text("\n".join(lines) + "\n")
    return pkg


def test_derives_compound_names_from_pipe_delimited_kcb_top(tmp_path):
    pkg = _mk_triage(tmp_path, [
        "BGC001,BGC0000123.4 | coelibactin | knownclusterblast #1,Interior",
        "BGC002,BGC0000456.7 | bacillibactin | knownclusterblast #1,Interior",
    ])
    names = csl.derive_compound_names_from_package(pkg)
    assert names == {"coelibactin", "bacillibactin"}


def test_skips_raw_non_pipe_self_hit_lines(tmp_path):
    """A raw clusterblast self-hit line (no MIBiG reference resolved) has no pipe
    structure — must be skipped, not guessed at, since a wrong name in the candidate
    set would silently suppress a genuine overclaim finding."""
    pkg = _mk_triage(tmp_path, [
        "BGC001,some raw self-hit description with no pipes at all,Edge",
    ])
    assert csl.derive_compound_names_from_package(pkg) == set()


def test_skips_unresolved_tokens(tmp_path):
    pkg = _mk_triage(tmp_path, [
        "BGC001,UNRESOLVED | UNRESOLVED | knownclusterblast #1,Edge",
        "BGC002,,Full-contig",
    ])
    assert csl.derive_compound_names_from_package(pkg) == set()


def test_missing_triage_board_returns_empty_not_error(tmp_path):
    pkg = tmp_path / "empty_pkg"
    pkg.mkdir()
    assert csl.derive_compound_names_from_package(pkg) == set()


def test_mixed_resolved_and_unresolved_rows(tmp_path):
    pkg = _mk_triage(tmp_path, [
        "BGC001,BGC0000123.4 | coelibactin | knownclusterblast #1,Interior",
        "BGC002,raw self-hit no pipes,Edge",
        "BGC003,UNRESOLVED | UNRESOLVED | knownclusterblast #1,Edge",
        "BGC004,,Full-contig",
    ])
    assert csl.derive_compound_names_from_package(pkg) == {"coelibactin"}


# ── CLI routing: --package / --compound-names / bare fallback ──────────────────

def _write_report(tmp_path, text):
    p = tmp_path / "report.md"
    p.write_text(text)
    return p


_FALSE_POSITIVE_PRONE_TEXT = (
    "Coverage 77x is adequate for assembly depth and supports confident calls.\n"
    "True cluster size is larger than 53.9 kb based on edge-truncation analysis.\n"
)
_REAL_IDENTITY_CLAIM = "BGC001 is coelibactin based on 96.3% BLASTP identity across 6 hits.\n"


class _Args:
    def __init__(self, **kw):
        self.path = None
        self.card_id = ""
        self.section = ""
        self.misanchor_flag = ""
        self.package = None
        self.compound_names = None
        self.report = None
        self.mode = "warn"
        self.json = False
        self.__dict__.update(kw)


def test_package_auto_derivation_reduces_false_positives(tmp_path, capsys):
    """The headline regression: --package must drop the false-positive-prone
    sentences relative to the bare heuristic, on the same input text."""
    pkg = _mk_triage(tmp_path, [
        "BGC001,BGC0000123.4 | coelibactin | knownclusterblast #1,Interior",
    ])
    report = _write_report(tmp_path, _FALSE_POSITIVE_PRONE_TEXT + _REAL_IDENTITY_CLAIM)

    rc = cli.claim_safety_command(_Args(path=str(report), package=str(pkg)))
    out = capsys.readouterr()
    assert rc == 0
    assert "auto-derived 1 compound name" in out.out
    assert "robust check path" in out.out
    # only the genuine identity claim should fire, not the two capacity-only sentences
    assert "1 finding" in out.out


def test_bare_invocation_falls_back_to_heuristic_with_notice(tmp_path, capsys):
    report = _write_report(tmp_path, _FALSE_POSITIVE_PRONE_TEXT + _REAL_IDENTITY_CLAIM)
    rc = cli.claim_safety_command(_Args(path=str(report)))
    out = capsys.readouterr()
    assert rc == 0
    assert "bare-name heuristic" in out.err
    assert "--package" in out.err and "--compound-names" in out.err
    # heuristic path is more permissive — all three sentences are expected to fire
    assert "3 finding" in out.out


def test_explicit_compound_names_overrides_and_needs_no_notice(tmp_path, capsys):
    """An explicit --compound-names supplier already did the right thing —
    no nagging notice should print."""
    report = _write_report(tmp_path, _FALSE_POSITIVE_PRONE_TEXT + _REAL_IDENTITY_CLAIM)
    rc = cli.claim_safety_command(
        _Args(path=str(report), compound_names="coelibactin"))
    out = capsys.readouterr()
    assert rc == 0
    assert "bare-name heuristic" not in out.err
    assert "1 finding" in out.out


def test_explicit_compound_names_takes_precedence_over_package(tmp_path, capsys):
    """If both are given, the explicit override wins — it's the more deliberate,
    more specific signal."""
    pkg = _mk_triage(tmp_path, [
        "BGC001,BGC0000123.4 | bacillibactin | knownclusterblast #1,Interior",
    ])
    report = _write_report(tmp_path, _REAL_IDENTITY_CLAIM)  # mentions "coelibactin"
    rc = cli.claim_safety_command(_Args(
        path=str(report), package=str(pkg), compound_names="coelibactin"))
    out = capsys.readouterr()
    assert rc == 0
    # auto-derive notice must NOT print — the explicit override took precedence
    assert "auto-derived" not in out.out


def test_package_with_no_derivable_names_falls_back_with_distinct_notice(tmp_path, capsys):
    """--package given but the triage board is missing/empty: distinct from the
    bare-invocation case — the person DID try to use the robust path, so the
    notice should say so, not just repeat the generic bare-invocation message."""
    empty_pkg = tmp_path / "empty_pkg"
    empty_pkg.mkdir()
    report = _write_report(tmp_path, _REAL_IDENTITY_CLAIM)
    rc = cli.claim_safety_command(_Args(path=str(report), package=str(empty_pkg)))
    out = capsys.readouterr()
    assert rc == 0
    assert "no compound names could be derived" in out.err
    assert str(empty_pkg) in out.err


def test_claim_safety_cli_has_package_and_compound_names_flags():
    """Parser-level smoke test: both new flags exist and route to the right dest."""
    parser = cli.build_parser()
    args = parser.parse_args([
        "claim-safety", "some.md", "--package", "/tmp/pkg",
        "--compound-names", "a,b,c",
    ])
    assert args.package == "/tmp/pkg"
    assert args.compound_names == "a,b,c"
