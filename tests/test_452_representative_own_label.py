import csv
import io
import json
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from tools.collapse_near_identical import build_display

@pytest.mark.parametrize("mismatches", [0, 1])
def test_representative_retains_own_label_and_all_group_evidence(tmp_path, mismatches):
    sequence = "ACGT" * 20
    second = "T" + sequence[1:] if mismatches else sequence
    alignment = tmp_path / "input.fa"
    tree = tmp_path / "input.nwk"
    metadata = tmp_path / "input.tsv"
    alignment.write_text(f">r1\n{sequence}\n>r2\n{second}\n>q\n{sequence}\n>outgroup\n" + "TTGA" * 20 + "\n")
    tree.write_text("((r1:0,r2:0):0.1,(q:0.1,outgroup:0.2):0.1);")
    label = "Syntheticus alpha SYN-1 (NR_000001.1)"
    metadata.write_text("tip\tlabel\trole\ttaxon\nr1\t" + label + "\treference\tSyntheticus alpha\nr2\tSyntheticus alpha SYN-2\treference\tSyntheticus alpha\nq\tSynthetic query\tquery\tSyntheticus\noutgroup\tSynthetic outgroup\toutgroup\tOtherus\n")
    before = [p.read_bytes() for p in (alignment, tree, metadata)]
    result = build_display(alignment, tree, metadata, dict(max_nt=1, min_cols=10, protect=[], prune_outgroup=False, group_label="representative"))
    rows = list(csv.DictReader(io.StringIO(result["metadata"].decode()), delimiter="\t"))
    representative = next(r for r in rows if r["tip"] == "r1")
    assert representative["label"] == label
    assert representative["display_members"] == "2"
    ledger = list(csv.DictReader(io.StringIO(result["ledger"].decode()), delimiter="\t"))
    grouped = [r for r in ledger if r["representative_tip"] == "r1"]
    assert {json.loads(r["original_metadata_json"])["label"] for r in grouped} == {label, "Syntheticus alpha SYN-2"}
    assert {r["max_pair_mismatches"] for r in grouped} == {str(mismatches)}
    assert {r["min_pair_shared_columns"] for r in grouped} == {"80"}
    assert [p.read_bytes() for p in (alignment, tree, metadata)] == before
