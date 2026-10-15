"""A split-gene piece qualifies only when its open end faces the contig end where the rest of the gene would lie.

A forward piece's C-terminal end faces the contig's right end and its N-terminal end the left end; a reverse piece's
the opposite. The nearer contig end is not enough: a short piece near the far end points into the contig interior.
"""
from mamey.ref_completion import SPLIT_END_BP, _open_end_distance, split_genes

LEN = 100000
REF = [{"id": "g001", "i": 1, "name": "r1", "aa": "M" * 300}]


def _prot(contig, start, end, strand):
    return {"contig": contig, "start": start, "end": end, "strand": strand, "contig_len": LEN,
            "tag": f"{contig}_{start}", "shown": f"TST-1 / {contig}"}


def _hits():
    return [{"qseqid": "g001", "sseqid": "pa", "pident": "60", "bitscore": "200", "qstart": "1", "qend": "140",
             "qcovhsp": "46.7"},
            {"qseqid": "g001", "sseqid": "pb", "pident": "60", "bitscore": "200", "qstart": "151", "qend": "300",
             "qcovhsp": "50.0"}]


def _split(pa):
    # pb is a forward piece starting 100 bp from its contig's left end: its open N-terminal end faces that end
    prots = {"pa": pa, "pb": _prot("ctgB", 100, 550, 1)}
    rows, status = split_genes(REF, prots, [], _hits())
    assert status == "run"
    return rows


def test_facing_end_follows_strand_and_terminus():
    fwd, rev = _prot("c", 1000, 2000, 1), _prot("c", 1000, 2000, -1)
    assert _open_end_distance(fwd, "C") == LEN - 2000 and _open_end_distance(fwd, "N") == 1000
    assert _open_end_distance(rev, "C") == 1000 and _open_end_distance(rev, "N") == LEN - 2000


def test_unknown_strand_has_no_facing_end():
    assert _open_end_distance(_prot("c", 10, 250, 0), "C") is None
    assert _open_end_distance(_prot("c", 10, 250, None), "N") is None


def test_correctly_facing_pieces_still_split():
    rows = _split(_prot("ctgA", LEN - 500, LEN - 100, 1))        # forward, C-terminal end 100 bp from the right end
    assert len(rows) == 1 and rows[0]["split_call"] == "CLEAR"
    assert rows[0]["piece1_open_end_to_contig_end_bp"] == 100 and rows[0]["piece2_open_end_to_contig_end_bp"] == 100
    rows = _split(_prot("ctgA", 150, 600, -1))                    # reverse, C-terminal end 150 bp from the left end
    assert len(rows) == 1 and rows[0]["piece1_open_end_to_contig_end_bp"] == 150


def test_a_short_piece_near_the_wrong_end_is_not_a_split():
    # forward piece near the LEFT end: its open C-terminal end faces the right end, ~100 kb away
    assert _split(_prot("ctgA", 10, 250, 1)) == []
    # reverse piece near the RIGHT end: its open C-terminal end faces the left end
    assert _split(_prot("ctgA", LEN - SPLIT_END_BP - 200, LEN - SPLIT_END_BP, -1)) == []


def test_a_piece_with_unknown_strand_is_not_a_split():
    assert _split(_prot("ctgA", LEN - 500, LEN - 100, 0)) == []
