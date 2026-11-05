"""A package with two triage boards fails the seal gates instead of reading the first.

`_triage_rows` and the compound-name loader both took the first `*_4_triage_board.csv` in sort
order. Two boards means two runs, or a stray copy, in one package, and the cards cannot be tied
to either one.
"""
from pathlib import Path

from mamey import judgment_store
from mamey import seal_package as seal_mod

HEADER = "BGC_ID,KCB_top,KCB_clusterblast\n"


def _pkg(tmp_path: Path, boards) -> Path:
    pkg = tmp_path / "package"
    pkg.mkdir()
    for name, row in boards:
        (pkg / name).write_text(HEADER + row + "\n", encoding="utf-8")
    return pkg


def test_two_boards_are_a_load_error(tmp_path):
    pkg = _pkg(tmp_path, [("A_4_triage_board.csv", "BGC001,BGC0000001.1 | alphamycin | kcb #1,"),
                          ("B_4_triage_board.csv", "BGC002,BGC0000002.1 | betamycin | kcb #1,")])
    rows, err = seal_mod._triage_rows(pkg)
    assert rows == {} and err.startswith("AMBIGUOUS_TRIAGE_BOARDS")
    gate = seal_mod._gate_locator(pkg, rows, err)
    assert gate.status == "FAIL" and "AMBIGUOUS_TRIAGE_BOARDS" in gate.detail
    errors = []
    assert judgment_store._strain_compound_names(pkg, errors) == set()
    assert errors and errors[0]["error_type"] == "AMBIGUOUS_TRIAGE_BOARDS"


def test_one_board_still_loads(tmp_path):
    pkg = _pkg(tmp_path, [("A_4_triage_board.csv", "BGC001,BGC0000001.1 | alphamycin | kcb #1,")])
    rows, err = seal_mod._triage_rows(pkg)
    assert err is None and set(rows) == {"BGC001"}
    assert "alphamycin" in judgment_store._strain_compound_names(pkg)
