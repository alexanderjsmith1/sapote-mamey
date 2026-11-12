"""mode-b must hold on a triage board that cannot name each card's contig.

With the Contig column removed it used to exit 0 and write Assembly_Locator " region002".
With no leads it printed the path of a CSV it never wrote.
"""
import inspect

from mamey import chatgpt_commands as CC


def test_board_checks():
    hold = CC._mode_b_board_hold
    assert hold([], []) == "the board is empty (no header row)"
    assert "Contig" in hold(["BGC_ID", "Products"], [{"BGC_ID": "BGC001"}])
    assert "blank Contig" in hold(["BGC_ID", "Contig"], [{"BGC_ID": "BGC001", "Contig": " "}])
    assert "blank BGC_ID" in hold(["BGC_ID", "Contig"], [{"BGC_ID": "", "Contig": "NODE_1"}])
    assert hold(["BGC_ID", "Contig"], [{"BGC_ID": "BGC001", "Contig": "NODE_1"}]) == ""
    assert hold(["BGC_ID", "Contig"], []) == ""   # a header-only board is not an identity problem


def test_mode_b_checks_the_board_before_writing():
    src = inspect.getsource(CC.mode_b_command)
    assert src.index("_mode_b_board_hold(") < src.index("outdir.mkdir(parents=True, exist_ok=True)")
    assert "IDENTITY_HOLD:" in src


def test_mode_b_does_not_print_an_unwritten_csv_path():
    src = inspect.getsource(CC.mode_b_command)
    assert "Mode B CSV: not written (no leads on the triage board)" in src
