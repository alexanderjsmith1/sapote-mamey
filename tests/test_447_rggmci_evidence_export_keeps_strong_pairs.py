"""RG-GMCI's evidence export keeps every row of a HIGH pair first, and says how many rows it left out.

Found 2026-10-03 in a split-link review: the engine kept the first 5,000 evidence rows in reference order, so in
AS-815 all 17 reviewed HIGH pairs had incomplete supporting references in the export (one had 8 saved of 25 ranked),
while their scores counted every reference. The summary's adjacency and identity counts were taken from the cut list.
"""
from mamey import rggmci
from mamey.models import BGCRecord


def _bgc(bid, edge="Full-contig"):
    return BGCRecord(bgc_id=bid, contig=f"ctg{bid}", region_number=1, start=1, end=9000, contig_length=9000,
                     products=["NRPS"], edge_status=edge, source_gbk="")


def _ref(bgc_id, ref, subjects, nprot=None):
    return {"bgc_id": bgc_id, "contig": f"ctg{bgc_id}", "region_number": 1, "region_key": f"ctg{bgc_id}_c1",
            "ref": ref, "source": ref, "reference_type": "nrps", "rank": 1, "nprot": nprot or len(subjects),
            "cumulative_score": 1000.0, "mean_identity": 60.0, "interval_start": None, "interval_end": None,
            "source_file": f"knownclusterblast/ctg{bgc_id}_c1.txt", "subjects": tuple(subjects),
            "db_kind": "knownclusterblast"}


NOISY = [f"N{k:02d}" for k in range(24)]
BGCS = [_bgc(b) for b in ["A", "B"] + NOISY]
# twelve weak pairs, one shared single-gene reference each, come first in reference order; the A+B references last
NOISE = [_ref(b, f"BGC9{k:06d}", ["x1"], nprot=1) for k in range(12) for b in NOISY[2 * k:2 * k + 2]]
STRONG = [_ref(b, f"BGC00000{k:02d}", genes) for k in range(6)
          for b, genes in (("A", ["g1", "g2", "g3", "g4"]), ("B", ["g5", "g6", "g7", "g8"]))]
REFMAP = {"reference_records": NOISE + STRONG}


def _rows(out, pair):
    return [r for r in out["evidence_rows"] if r["pair"] == pair]


def test_strong_pair_rows_survive_the_cap(monkeypatch):
    full = rggmci.compute_rggmci(BGCS, REFMAP)
    ab = next(p for p in full["ranked_pairs"] if p["pair"] == "A+B")
    assert ab["rggmci_confidence"] == "HIGH_RG_GMCI_RESCUE"
    assert len(_rows(full, "A+B")) == 6 and full["rggmci_summary"]["evidence_rows_not_exported"] == 0
    monkeypatch.setattr(rggmci, "RGGMCI_MAX_EVIDENCE_ROWS", 8)
    cut = rggmci.compute_rggmci(BGCS, REFMAP)
    assert len(_rows(cut, "A+B")) == 6  # all of the strong pair's references
    assert len(cut["evidence_rows"]) == 8
    s = cut["rggmci_summary"]
    assert s["evidence_rows_total"] == len(full["evidence_rows"]) == 18
    assert s["evidence_rows_not_exported"] == 10
    assert "evidence rows exported 8/18" in cut["summary_line"]


def test_summary_counts_use_every_row(monkeypatch):
    full = rggmci.compute_rggmci(BGCS, REFMAP)
    monkeypatch.setattr(rggmci, "RGGMCI_MAX_EVIDENCE_ROWS", 8)
    cut = rggmci.compute_rggmci(BGCS, REFMAP)
    for k in ("adjacency_basis_counts", "identity_rows_populated", "pairs_total"):
        assert cut["rggmci_summary"][k] == full["rggmci_summary"][k]


def test_high_rows_are_kept_even_past_the_cap(monkeypatch):
    monkeypatch.setattr(rggmci, "RGGMCI_MAX_EVIDENCE_ROWS", 2)
    cut = rggmci.compute_rggmci(BGCS, REFMAP)
    assert len(_rows(cut, "A+B")) == 6 and len(cut["evidence_rows"]) == 6
