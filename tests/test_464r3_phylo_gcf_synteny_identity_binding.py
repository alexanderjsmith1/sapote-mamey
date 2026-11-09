"""render_gcf_synteny_tree binds a row to the package record only when contig and region both match.

A bound row whose recorded region disagrees with the staged filename is held, a Source_GBK basename
bound by two conflicting inventory rows is a duplicate-key hold, and an incomplete record is held.
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
_spec = importlib.util.spec_from_file_location("gcf_synteny_464r3", ROOT / "tools" / "render_gcf_synteny_tree.py")
gs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gs)

FILE = "STRN1_NODE_1_length_9000_cov_10.0.region001.gbk"
SRC = "NODE_1_length_9000_cov_10.0.region001.gbk"
HEAD = "BGC_ID,Contig,antiSMASH_Region,Source_GBK\n"


def _inv(tmp_path, name, rows):
    p = tmp_path / name
    p.write_text(HEAD + "".join(rows))
    return str(p)


def test_matching_record_binds_alias(tmp_path):
    bound = gs.load_identity([_inv(tmp_path, "a.csv", [f"BGC007,NODE_1_length_9000_cov_10.0,region001,{SRC}\n"])])
    r = gs.row_identity(FILE, bound)
    assert r["alias"] == "BGC007" and r["hold"] == ""


def test_region_mismatch_is_held(tmp_path):
    bound = gs.load_identity([_inv(tmp_path, "a.csv", [f"BGC007,NODE_1_length_9000_cov_10.0,region004,{SRC}\n"])])
    r = gs.row_identity(FILE, bound)
    assert r["alias"] == "" and r["label"].endswith(gs.HOLD)
    assert "region mismatch" in r["hold"]


def test_duplicate_conflicting_key_is_held_not_overwritten(tmp_path):
    a = _inv(tmp_path, "a.csv", [f"BGC007,NODE_1_length_9000_cov_10.0,region001,{SRC}\n"])
    b = _inv(tmp_path, "b.csv", [f"BGC099,NODE_1_length_9000_cov_10.0,region001,other/{SRC}\n"])
    r = gs.row_identity(FILE, gs.load_identity([a, b]))
    assert r["alias"] == "" and "duplicate Source_GBK key" in r["hold"]


def test_identical_repeat_is_not_a_conflict(tmp_path):
    row = f"BGC007,NODE_1_length_9000_cov_10.0,region001,{SRC}\n"
    r = gs.row_identity(FILE, gs.load_identity([_inv(tmp_path, "a.csv", [row, row])]))
    assert r["alias"] == "BGC007"


def test_record_without_region_or_contig_is_held(tmp_path):
    r = gs.row_identity(FILE, gs.load_identity([_inv(tmp_path, "a.csv", [f"BGC007,NODE_1_length_9000_cov_10.0,,{SRC}\n"])]))
    assert r["alias"] == "" and "no antiSMASH_Region" in r["hold"]
    r = gs.row_identity(FILE, gs.load_identity([_inv(tmp_path, "b.csv", [f"BGC007,,region001,{SRC}\n"])]))
    assert r["alias"] == "" and "no Contig" in r["hold"]
