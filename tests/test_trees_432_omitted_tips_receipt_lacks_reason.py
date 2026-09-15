"""TREES_432: omitted_tips.tsv is a receipt with columns tip, name, reason; the reason grammar is
NO_DEPOSITED_SOURCE | NO_DEPOSITED_GEOGRAPHY | DUPLICATE_OF:<tip> | OWNER_RULE:<text>; the
compose/bind step refuses a prior tip that is neither staged nor receipted. (The colour-strip
renderers report the omitted count in their captions and point at the receipt; the old
supplement-table renderer was retired in favour of tools/render_tree_COLOR_STRIPS.R.)
"""
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))

import omitted_tips_receipt as otr  # noqa: E402
from trees_432_panel_fixture import make_panel  # noqa: E402

GOOD = [
    {"tip": "GCF_000000003.1", "name": "Genus gamma SH1", "reason": "NO_DEPOSITED_SOURCE"},
    {"tip": "GCF_000000004.1", "name": "Genus delta DSM 4", "reason": "NO_DEPOSITED_GEOGRAPHY"},
    {"tip": "GCF_000000006.1", "name": "Genus alpha DSM 1 (second assembly)", "reason": "DUPLICATE_OF:GCF_000000001.1"},
    {"tip": "GCF_000000007.1", "name": "Genus zeta K7", "reason": "OWNER_RULE:held geography Russia until ruling"},
]


def test_reason_grammar():
    for row in GOOD:
        assert otr.validate_reason(row["reason"]) == row["reason"]
    for bad in ("", "BLANK", "no_deposited_source", "DUPLICATE_OF:", "OWNER_RULE:", "QC_DROP"):
        with pytest.raises(otr.OmitReceiptError, match="OMIT_REASON_INVALID"):
            otr.validate_reason(bad)


def test_write_and_read_round_trip(tmp_path):
    path = otr.write_receipt(tmp_path / "omitted_tips.tsv", GOOD)
    text = path.read_text()
    assert text.splitlines()[0] == "tip\tname\treason"
    assert otr.read_receipt(path) == GOOD
    otr.append_receipt(path, {"tip": "X", "name": "Genus eta X", "reason": "NO_DEPOSITED_SOURCE"})
    assert len(otr.read_receipt(path)) == 5


def test_name_is_required_so_the_list_is_pasteable(tmp_path):
    with pytest.raises(otr.OmitReceiptError, match="OMIT_NAME_EMPTY"):
        otr.write_receipt(tmp_path / "o.tsv", [{"tip": "GCF_1", "name": "", "reason": "NO_DEPOSITED_SOURCE"}])


def test_bare_identifier_file_is_refused(tmp_path):
    legacy = tmp_path / "omitted_tips.txt"
    legacy.write_text("GCF_900091625.1\n")
    with pytest.raises(otr.OmitReceiptError, match="OMIT_RECEIPT_HEADER"):
        otr.read_receipt(legacy)


def test_compose_refusal_rule(tmp_path):
    prior = ["A", "B", "C", "D"]
    assert otr.unaccounted_tips(prior, ["A", "B"], [{"tip": "C", "name": "n", "reason": "NO_DEPOSITED_SOURCE"}]) == ["D"]
    assert otr.unaccounted_tips(prior, ["A", "B", "D"], [{"tip": "C", "name": "n", "reason": "NO_DEPOSITED_SOURCE"}]) == []


def test_cli_check_names_unaccounted_tips(tmp_path):
    prior = tmp_path / "prior_figure_metadata.tsv"
    prior.write_text("tip\tidentifier\trole\nA\tA\tQUERY\nGCF_2\tGCF_2\tREFERENCE\nGCF_3\tGCF_3\tREFERENCE\n")
    staged = tmp_path / "staged.txt"
    staged.write_text("A\n")
    receipt = tmp_path / "omitted_tips.tsv"
    subprocess.run([sys.executable, str(ROOT / "tools" / "omitted_tips_receipt.py"), "add", "--receipt", str(receipt),
                    "--tip", "GCF_2", "--name", "Genus two DSM 2", "--reason", "NO_DEPOSITED_GEOGRAPHY"], check=True)
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "omitted_tips_receipt.py"), "check", "--receipt", str(receipt),
                        "--prior", str(prior), "--staged", str(staged)], capture_output=True, text=True)
    assert r.returncode == 2 and "GCF_3" in r.stdout and "GCF_2" not in r.stdout.split(":")[-1]
    subprocess.run([sys.executable, str(ROOT / "tools" / "omitted_tips_receipt.py"), "add", "--receipt", str(receipt),
                    "--tip", "GCF_3", "--name", "Genus three DSM 3", "--reason", "DUPLICATE_OF:GCF_2"], check=True)
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "omitted_tips_receipt.py"), "check", "--receipt", str(receipt),
                        "--prior", str(prior), "--staged", str(staged)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout


def test_binder_refuses_receipted_tip_that_is_still_in_panel(tmp_path):
    panel = make_panel(tmp_path, "GTR-09-GENUS")
    receipt = otr.write_receipt(tmp_path / "omitted_tips.tsv",
                                [{"tip": "GCF_000000001.1", "name": "Genus alpha DSM 1", "reason": "NO_DEPOSITED_SOURCE"}])
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "bind_panel_metadata.py"), "--panel-dir", str(panel),
                        "--out-dir", str(tmp_path / "out"), "--omitted-tips", str(receipt)], capture_output=True, text=True)
    assert r.returncode != 0 and "OMIT_RECEIPT_CLASH" in (r.stdout + r.stderr)
