"""Guard: per-strain workbook sheet names must never exceed Excel's 31-character limit.

openpyxl does NOT raise when a sheet name exceeds 31 chars — it warns and writes a sheet that
Excel cannot open, and two over-long codes can silently collide and overwrite each other. This
test pins _sheet_code so the longest "{code}{suffix}" sheet name stays within the limit, even for
a pathologically long strain id. Regression guard for the v9.7.57 sheet-name overflow (P2).
"""
from mamey.master_workbook import _sheet_code

# The longest suffix appended to a strain code anywhere in master_workbook.py.
LONGEST_SUFFIX = "_Lead_Propagation"  # 17 chars
EXCEL_SHEET_NAME_LIMIT = 31

# All suffixes that get appended as f"{code}{suffix}" — keep in sync if new sheets are added.
ALL_SUFFIXES = ["_Lead_Propagation", "_Missingness", "_Summary", "_Triage"]


def test_sheet_code_plus_longest_suffix_within_excel_limit():
    pathological = "X" * 200  # a strain id whose last token is absurdly long
    code = _sheet_code(pathological)
    for suffix in ALL_SUFFIXES:
        name = f"{code}{suffix}"
        assert len(name) <= EXCEL_SHEET_NAME_LIMIT, (
            f"sheet name {name!r} is {len(name)} chars (> {EXCEL_SHEET_NAME_LIMIT}); "
            f"code={code!r} ({len(code)} chars) + suffix={suffix!r}"
        )


def test_sheet_code_unchanged_for_short_ids():
    # Real-world short codes pass through untouched. Avoid embedding raw SID####/AS-### literals
    # here: the analysis-free tier's release scrub rewrites them (SID8375 -> SID-XXX), which would
    # change what this test asserts in the staged tree. Use anonymization-stable examples.
    for strain_id, expected in [
        ("Actinomadura_rubrisoli_H3C3", "H3C3"),
        ("Streptomyces_sp_K375", "K375"),
        ("WW-PENDING_BGC", "BGC"),
    ]:
        assert _sheet_code(strain_id) == expected


def test_sheet_code_cap_is_exactly_14():
    # 31 - len("_Lead_Propagation") = 14
    assert _sheet_code("Z" * 50) == "Z" * 14
