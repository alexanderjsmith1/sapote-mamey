"""test_misanchor_flag_column.py — STEP 1 (SM-P0-005): Misanchor_Flag column surface.

v9.7.123 renames the triage board CSV column "Misanchor" → "Misanchor_Flag" and
ensures it's consumed consistently by all downstream readers.

These tests pin:
  1. The column name in the triage_headers list is "Misanchor_Flag" (not "Misanchor").
  2. package_addons reads the renamed column correctly.
  3. The Part B prompt-block template is present in the system prompt.
"""
import csv
import re
import sys
from io import StringIO
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))


# ── 1. triage_headers column name ─────────────────────────────────────────────
def test_triage_headers_uses_misanchor_flag():
    """The triage board header list must use 'Misanchor_Flag', not bare 'Misanchor'."""
    cli_src = (_ROOT / "mamey" / "cli.py").read_text(encoding="utf-8")
    # Must contain the new name
    assert "\"Misanchor_Flag\"" in cli_src, \
        "cli.py triage_headers must contain 'Misanchor_Flag'"
    # Must NOT retain the old bare name as a header entry
    # (The string "Misanchor" still appears in comments and rationale strings — we
    # only forbid it as a standalone quoted header token in triage_headers.)
    # Parse the triage_headers list to check:
    m = re.search(r'triage_headers\s*=\s*\[([^\]]+)\]', cli_src, re.DOTALL)
    assert m, "Could not locate triage_headers list in cli.py"
    header_block = m.group(1)
    # Collect all quoted strings from the header list
    quoted = re.findall(r'"([^"]+)"', header_block)
    assert "Misanchor_Flag" in quoted, \
        f"'Misanchor_Flag' not in triage_headers: {quoted}"
    assert "Misanchor" not in quoted or "Misanchor_Flag" in quoted, \
        "Both 'Misanchor' and 'Misanchor_Flag' in triage_headers — rename not applied"
    # The bare "Misanchor" must not appear as a standalone column name
    standalone = [q for q in quoted if q == "Misanchor"]
    assert not standalone, \
        f"Old 'Misanchor' column still in triage_headers: {quoted}"


# ── 2. package_addons reads renamed column ─────────────────────────────────────
def test_package_addons_reads_misanchor_flag():
    """package_addons.py must read 'Misanchor_Flag', not 'Misanchor'."""
    src = (_ROOT / "mamey" / "package_addons.py").read_text(encoding="utf-8")
    assert 'row.get("Misanchor_Flag"' in src or "row.get('Misanchor_Flag'" in src, \
        "package_addons.py must read Misanchor_Flag column, not the old Misanchor"
    # Must NOT still use the old bare key
    assert 'row.get("Misanchor", "")' not in src, \
        "package_addons.py still reads old 'Misanchor' column — update to 'Misanchor_Flag'"


# ── 3. Part B warning block in system prompt ───────────────────────────────────
def test_misanchor_warning_block_in_prompt():
    """The system prompt must contain the standardised misanchor warning block."""
    prompt_path = _ROOT / "prompts" / "CLAUDE_SYSTEM_PROMPT.md"
    if not prompt_path.exists():
        pytest.skip("CLAUDE_SYSTEM_PROMPT.md not present in this tier")
    src = prompt_path.read_text(encoding="utf-8")
    # The block must contain the key identifiers from the spec
    assert "KCB anchor note" in src, \
        "Misanchor warning block missing 'KCB anchor note' in system prompt"
    assert "Misanchor_Flag" in src or "misanchor_flag" in src.lower(), \
        "Misanchor_Flag not referenced in system prompt misanchor block"
    assert "cite the *class*" in src.lower() or "cite the class" in src.lower(), \
        "Misanchor block must instruct to cite the class, not the anchor name"


# ── 4. Bunny Hop: old column name gone from CSV round-trip ────────────────────
def test_misanchor_flag_roundtrip_column_name():
    """CSV written with Misanchor_Flag must be readable by key 'Misanchor_Flag'."""
    # Simulate a minimal triage row with the renamed column
    headers = ["BGC_ID", "Misanchor_Flag", "AB_auto"]
    row_data = [["BGC001", "polyene_anchor_<4_PKS_KS(ks=1)", "55.0"]]
    buf = StringIO()
    w = csv.writer(buf)
    w.writerow(headers)
    w.writerows(row_data)
    buf.seek(0)
    rows = list(csv.DictReader(buf))
    assert rows[0]["Misanchor_Flag"] == "polyene_anchor_<4_PKS_KS(ks=1)"
    # Old key must not work (it won't exist as a column)
    assert "Misanchor" not in rows[0] or rows[0].get("Misanchor") is None


