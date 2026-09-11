"""Regression test — v97395 tick 21: round_ledger.py writes a headerless row when the ledger
CSV already exists as an empty (0-byte) file.

`new = not led.exists()` treats "the file exists" as proof it already has a header. A 0-byte
pre-existing ledger (a pre-created placeholder, or a prior invocation of this very tool
interrupted between opening the file in append mode and writing its row -- both realistic given
this tool's own docstring: "a drop-in for the multi-round authoring loop... across the 6+ rounds
and across chats") produces a data row with NO header at all. Any downstream `csv.DictReader`
would then treat that first data row's values as the column names, silently corrupting every
subsequent read -- defeating the tool's own stated purpose ("a durable, greppable trail").
"""
import csv
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

import round_ledger as m


def _run(tmp_path, card_text="fake card body", ledger_preexists_empty=True):
    card = tmp_path / "card.md"
    card.write_text(card_text, encoding="utf-8")
    ledger = tmp_path / "round_ledger.csv"
    if ledger_preexists_empty:
        ledger.write_text("", encoding="utf-8")

    # save/restore, never a bare permanent stub: round_ledger is a shared sys.modules
    # entry, and a leaked fake-OK run_gate would false-green any later in-process caller
    # (the raw-stub leak class diagnosed in the .398 round — see test_audit230_fixes).
    orig_run_gate = m.run_gate
    m.run_gate = lambda c, p, b: ("OK", 0, "fake OK (0 warning(s))")
    argv = [
        "round_ledger.py", str(card), "--package", "PKG", "--bgc", "BGC025",
        "--round", "1", "--ledger", str(ledger),
    ]
    old_argv = sys.argv
    sys.argv = argv
    try:
        m.main()
    finally:
        sys.argv = old_argv
        m.run_gate = orig_run_gate
    return ledger


def test_preexisting_empty_ledger_still_gets_a_header_v97395(tmp_path):
    ledger = _run(tmp_path, ledger_preexists_empty=True)
    first_line = ledger.read_text(encoding="utf-8").splitlines()[0]
    assert first_line.split(",")[0] == "round", (
        f"ledger's first line is a DATA row, not a header: {first_line!r} -- a downstream "
        "csv.DictReader would treat round-1's own data as column names"
    )


def test_ledger_readable_with_dictreader_after_preexisting_empty_file_v97395(tmp_path):
    ledger = _run(tmp_path, ledger_preexists_empty=True)
    rows = list(csv.DictReader(ledger.open(encoding="utf-8")))
    assert len(rows) == 1
    assert rows[0]["bgc"] == "BGC025"
    assert rows[0]["gate_status"] == "OK"


def test_brand_new_ledger_path_still_gets_a_header_no_regression_v97395(tmp_path):
    ledger = _run(tmp_path, ledger_preexists_empty=False)
    first_line = ledger.read_text(encoding="utf-8").splitlines()[0]
    assert first_line.split(",")[0] == "round"
