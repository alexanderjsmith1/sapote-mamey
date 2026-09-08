"""inventory_audit default-home + loud-refusal regression (v9.7.397 bypass-audit finding 3).

The old default boards glob hardcoded the ``mamey_packages/`` home; with that home absent
(as on the current estate) a defaults run silently audited ZERO boards and exited 0 with a
"reviewed 0" report. Repaired: the default walks the package homes (``mamey_packages``,
``Mamey Complete*``, plus ``MAMEY_PACKAGE_HOMES`` env globs) and a zero-match run REFUSES
loudly (typed JSON on stderr, exit 2) instead of writing an empty report.

Strain IDs are synthetic and runtime-constructed; fixtures live in tmp_path only.
"""
from __future__ import annotations

import csv
import importlib.util
import os

# Load the deliverable_tools CLI module by file path (mirrors the roster_v2 freshness test).
_SPEC = importlib.util.spec_from_file_location(
    "deliverable_tools_inventory_audit",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "deliverable_tools", "inventory_audit.py"),
)
inventory_audit = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(inventory_audit)

STRAIN = "AS-" + str(9900 + 3)
BOARD_COLS = ["BGC_ID", "Lead_tier_auto", "Products", "AB_auto", "AF_auto", "Novelty_auto"]


def _write_board(home_dir):
    d = os.path.join(home_dir, STRAIN, "package")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, STRAIN + "_4_triage_board.csv")
    with open(p, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(BOARD_COLS)
        w.writerow(["BGC001", "Inventory", "saccharide", "1", "1", "Low"])
    return p


def test_zero_boards_refuses_loudly(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.delenv("MAMEY_PACKAGE_HOMES", raising=False)
    rc = inventory_audit.main(["--out", str(tmp_path)])
    assert rc == 2, "empty estate must refuse, not write a 'reviewed 0' report (got rc=%r)" % rc
    err = capsys.readouterr().err
    assert "INVENTORY_AUDIT_NO_BOARDS" in err
    assert not [f for f in os.listdir(tmp_path) if f.endswith((".md", ".tsv"))], \
        "no report files may be written on refusal"


def test_default_finds_versionless_package_home(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.delenv("MAMEY_PACKAGE_HOMES", raising=False)
    _write_board(os.path.join(str(tmp_path), "Mamey Complete"))
    out = tmp_path / "out"
    out.mkdir()
    rc = inventory_audit.main(["--out", str(out)])
    assert rc == 0, "board in a 'Mamey Complete*' home must be found by the default"
    assert "reviewed 1 Inventory rows" in capsys.readouterr().out, \
        "the board must actually be AUDITED, not skipped by an empty default glob"


def test_env_homes_extend_the_default(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("MAMEY_PACKAGE_HOMES", "CUSTOM HOME")
    _write_board(os.path.join(str(tmp_path), "CUSTOM HOME"))
    out = tmp_path / "out"
    out.mkdir()
    rc = inventory_audit.main(["--out", str(out)])
    assert rc == 0, "MAMEY_PACKAGE_HOMES home must be searched by the default"
    assert "reviewed 1 Inventory rows" in capsys.readouterr().out


def test_explicit_glob_still_wins(tmp_path, monkeypatch):
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(tmp_path))
    board = _write_board(os.path.join(str(tmp_path), "elsewhere"))
    out = tmp_path / "out"
    out.mkdir()
    rc = inventory_audit.main(["--boards-glob", board, "--out", str(out)])
    assert rc == 0
