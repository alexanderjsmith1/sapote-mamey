"""v9.7.227: the blastp-ebi subparser must define --hits — .218 threaded hits=a.hits into submit_ebi
but never added the arg, so `mamey blastp-ebi --submit` raised AttributeError. CLI-path test (not a
proxy), so this bug class is caught in CI."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

def test_blastp_ebi_subparser_defines_hits():
    from mamey.cli import build_parser
    p = build_parser()
    ns = p.parse_args(["blastp-ebi", "--fasta", "x.faa", "--state", "s.json", "--hits", "10"])
    assert getattr(ns, "hits", None) == 10          # arg exists and binds
    ns2 = p.parse_args(["blastp-ebi", "--fasta", "x.faa", "--state", "s.json"])
    assert getattr(ns2, "hits", None) == 6           # default present (no AttributeError downstream)

def test_snap_alignments_still_maps_6_to_valid_enum():
    from mamey.blastp_ebi import _snap_alignments, _EBI_ALIGN_ENUM
    assert _snap_alignments(6) == "10" and int(_snap_alignments(6)) in _EBI_ALIGN_ENUM
