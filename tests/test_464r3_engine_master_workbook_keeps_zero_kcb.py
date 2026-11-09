"""The master workbook's C4 top-lead KCB score keeps a recorded 0; only a missing score is blank.

`top_kcb_score` used `value or ""`, so a recorded KCB score of 0 was written as blank.
"""
import inspect

from mamey import master_workbook as mw


def test_zero_stays_zero_and_missing_is_blank():
    assert mw._kcb_cell(0) == 0
    assert mw._kcb_cell(0.0) == 0.0
    assert mw._kcb_cell(None) == ""
    assert mw._kcb_cell("nan") == ""
    assert mw._kcb_cell("NA") == ""
    assert mw._kcb_cell("37") == 37.0


def test_the_c4_row_uses_the_zero_safe_helper():
    source = inspect.getsource(mw)
    assert '"top_kcb_score": _kcb_cell(' in source
    assert "None) or \"\") if top_ab" not in source
