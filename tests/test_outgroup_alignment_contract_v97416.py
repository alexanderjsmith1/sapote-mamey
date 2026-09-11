import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("outgroup416", Path(__file__).resolve().parents[1] / "tools/phylo_outgroup_gate.py")
G = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(G)


def write(tmp_path, text):
    p = tmp_path / "alignment.fasta"
    p.write_text(text)
    return p


def test_duplicate_identifier_refuses(tmp_path):
    rc, text = G.check(write(tmp_path, ">a\nAAAA\n>a\nAAAA\n"), min_cols=1)
    assert rc == 3 and "duplicate" in text


def test_unequal_lengths_refuse(tmp_path):
    rc, text = G.check(write(tmp_path, ">a\nAAAA\n>b\nAAA\n"), min_cols=1)
    assert rc == 3 and "equal length" in text


def test_ambiguity_is_missing_not_a_match():
    assert G.ident("NR-?", "NR-?") == (None, 0)
    assert G.ident("ACGN", "ACGA") == (100.0, 3)


def test_incomplete_overlap_cannot_pass(tmp_path):
    p = write(tmp_path, ">OUTGROUP_v1\nCCCC\n>a\nAAAA\n>b\nAAAA\n>c\nNNNA\n")
    assert G.check(p, min_cols=3)[0] == 3


def test_complete_screen_does_not_claim_root_validation(tmp_path):
    p = write(tmp_path, ">OUTGROUP_v1\nCCCC\n>a\nAAAA\n>b\nAAAA\n>c\nAAAA\n")
    rc, text = G.check(p, min_cols=4)
    assert rc == 0 and "rooting is not validated" in text
    assert G.check(p, min_cols=4, sample=1)[0] == 3
