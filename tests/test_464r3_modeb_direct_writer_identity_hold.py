"""record_mode_b fails closed on identity (.464 ruling, DN-87).

The direct writer used to write the card, the reader notes and a register row even
when the card's four-part identity was missing or conflicted with the package. Now
it raises ModeBIdentityHold (exit_code 2), names the component, and writes nothing.
"""
import csv
import json

import pytest

from mamey.judgment_store import ModeBIdentityHold, init_register, record_mode_b

ROW = ["1", "BGC001", "CP000001.1", "CP000001.1", "region001", "NRPS", ""]


def _pkg(tmp_path, with_triage=True):
    (tmp_path / "manifest.json").write_text(json.dumps({"strain_id": "PUBLIC-1", "mode": "gold", "bgcs": []}))
    init_register(tmp_path, "PUBLIC-1", ["BGC001"])
    if with_triage:
        with open(tmp_path / "PUBLIC-1_4_triage_board.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["Rank", "BGC_ID", "Node_ID", "Contig", "antiSMASH_Region", "Products", "Misanchor_Flag"])
            w.writerow(ROW)
    return tmp_path


def _written(pkg):
    reg = json.loads(next(pkg.glob("*_judgment_register.json")).read_text())
    return (sorted(p.name for p in pkg.rglob("*_mode_b.md")),
            sorted(p.name for p in pkg.rglob("*_laypersons_section.md")),
            reg["bgcs"]["BGC001"]["status"])


@pytest.mark.parametrize("header,component", [
    ("# Mode B — OTHER-9 / CP000001.1 / region001 / BGC001", "strain"),
    ("# Mode B — PUBLIC-1 / CP999999.1 / region001 / BGC001", "full contig"),
    ("# Mode B — PUBLIC-1 / CP000001.1 / region007 / BGC001", "region"),
])
def test_conflicting_component_is_named_and_nothing_written(tmp_path, header, component):
    pkg = _pkg(tmp_path)
    before = _written(pkg)
    with pytest.raises(ModeBIdentityHold) as hold:
        record_mode_b(pkg, "BGC001", header + "\n§1 capacity text.", layperson_paragraph="Lay note.")
    assert hold.value.exit_code == 2
    assert component in hold.value.components
    assert "No card was written" in str(hold.value)
    assert before[:2] == ([], [])
    assert _written(pkg) == before  # no card, no reader note, register row unchanged


def test_missing_identity_header_is_held(tmp_path):
    pkg = _pkg(tmp_path)
    with pytest.raises(ModeBIdentityHold) as hold:
        record_mode_b(pkg, "BGC001", "## §1 Identity\nNo four-part header here.")
    assert hold.value.refusal_reason == "ZERO_EXACT_IDENTITIES"
    assert not list(pkg.rglob("*_mode_b.md"))


def test_alias_without_triage_row_is_held(tmp_path):
    pkg = _pkg(tmp_path, with_triage=False)
    with pytest.raises(ModeBIdentityHold) as hold:
        record_mode_b(pkg, "BGC001", "# Mode B — PUBLIC-1 / CP000001.1 / region001 / BGC001\n§1 text.")
    assert hold.value.refusal_reason == "NO_TRIAGE_ROW"
    assert not list(pkg.rglob("*_mode_b.md"))


def test_matching_identity_is_written(tmp_path):
    pkg = _pkg(tmp_path)
    result = record_mode_b(pkg, "BGC001", "# Mode B — PUBLIC-1 / CP000001.1 / region001 / BGC001\n§1 text.")
    assert result["verdict"]["locator"]["status"] == "PASS" and result["path"].exists()
