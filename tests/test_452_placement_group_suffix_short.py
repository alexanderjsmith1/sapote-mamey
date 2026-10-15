"""Representative display labels retain their own record text. Group members and measured bounds remain in the collapse ledger; the legacy suffix formatter remains available for compatible callers. Synthetic data only."""
import csv
import importlib.util
import io
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE / "tools"))
spec = importlib.util.spec_from_file_location("collapse_452g", HERE / "tools" / "collapse_near_identical.py")
cni = importlib.util.module_from_spec(spec); spec.loader.exec_module(cni)


def _build(tmp_path, r2):
    seq = "ACGT" * 200
    aln = tmp_path / "a.fa"; tree = tmp_path / "t.nwk"; meta = tmp_path / "m.tsv"
    aln.write_text(f">r1\n{seq}\n>r2\n{r2}\n>q\n{seq}\n>outgroup\n" + "TTGA" * 200 + "\n")
    tree.write_text("((r1:0,r2:0):0.1,(q:0.05,outgroup:0.5):0.1);")
    meta.write_text("tip\tlabel\trole\ttaxon\nr1\tSynus alpha SYN 1 (NR_000001.1)\treference\tSynus\n"
                    "r2\tSynus alpha SYN 2 (NR_000002.1)\treference\tSynus\nq\tSynus sp. SYN-970\tquery\tSynus\n"
                    "outgroup\tSynoutgroupia beta SYN 3\toutgroup\tSynoutgroupia\n")
    res = cni.build_display(aln, tree, meta, dict(max_nt=1, min_cols=100, protect=[], prune_outgroup=False,
                                                  group_label="representative"))
    rows = list(csv.DictReader(io.StringIO(res["metadata"].decode()), delimiter="\t"))
    return [r for r in rows if r["role"] == "reference"]


@pytest.mark.parametrize("mismatch", [0, 1])
def test_grouped_label_keeps_own_record_text(tmp_path, mismatch):
    seq = "ACGT" * 200
    refs = _build(tmp_path, "T" + seq[1:] if mismatch else seq)
    assert len(refs) == 1
    label = refs[0]["label"]
    assert label == "Synus alpha SYN 1 (NR_000001.1)"
    assert "identical" not in label and "grouped;" not in label


def test_no_grouping_leaves_labels_unchanged(tmp_path):
    seq = "ACGT" * 200
    refs = _build(tmp_path, "TTTT" + seq[4:20] + "GGGG" + seq[24:])      # 6 mismatches: above max_nt, not grouped
    assert [r["label"] for r in refs] == ["Synus alpha SYN 1 (NR_000001.1)", "Synus alpha SYN 2 (NR_000002.1)"]


def test_suffix_function_and_caption_rule():
    assert cni.group_suffix(3, 0, 1378) == "(+3; 0 nt over ≥1378 sites)"
    assert cni.group_suffix(2, 1, 600) == "(+2; ≤1 nt over ≥600 sites)"
    d = (HERE / "tools" / "placement_display.py").read_text()
    assert "supplementary grouping table" in d
