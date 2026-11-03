"""DREL-035: handoff --top-n never selects an engine-excluded row by its raw rank."""
from mamey.handoff import _top_n_bgcs


def _board(tmp_path, header, rows):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    lines = [",".join(header)] + [",".join(r) for r in rows]
    (pkg / "SYN-1_4_triage_board.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return pkg


def test_blank_corrected_rank_is_excluded_not_raw_ranked(tmp_path):
    pkg = _board(tmp_path, ["BGC_ID", "Rank", "Corrected_rank"],
                 [["BGC_EXCLUDED", "1", ""], ["BGC_LEAD", "2", "1"]])
    assert _top_n_bgcs(pkg, 1) == ["BGC_LEAD"]


def test_row_order_does_not_change_the_choice(tmp_path):
    pkg = _board(tmp_path, ["BGC_ID", "Rank", "Corrected_rank"],
                 [["BGC_LEAD", "2", "1"], ["BGC_EXCLUDED", "1", ""]])
    assert _top_n_bgcs(pkg, 1) == ["BGC_LEAD"]


def test_excluded_rows_never_fill_remaining_places(tmp_path):
    pkg = _board(tmp_path, ["BGC_ID", "Rank", "Corrected_rank"],
                 [["BGC_A", "1", "1"], ["BGC_X", "2", ""], ["BGC_B", "3", "2"]])
    assert _top_n_bgcs(pkg, 5) == ["BGC_A", "BGC_B"]


def test_all_excluded_selects_nothing(tmp_path):
    pkg = _board(tmp_path, ["BGC_ID", "Rank", "Corrected_rank"], [["BGC_X", "1", ""], ["BGC_Y", "2", ""]])
    assert _top_n_bgcs(pkg, 2) == []


def test_legacy_table_without_column_uses_raw_rank(tmp_path):
    pkg = _board(tmp_path, ["BGC_ID", "Rank"], [["BGC_B", "2"], ["BGC_A", "1"]])
    assert _top_n_bgcs(pkg, 1) == ["BGC_A"]
