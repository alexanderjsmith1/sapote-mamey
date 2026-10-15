"""The reciprocal test searches each find's own aligned stretch, even when two reference genes hit one protein.

Before, the stretch was stored under the protein id alone, so the last reference gene's stretch replaced the others
and every row on that protein was judged on it.
"""
from mamey.ref_completion import partner_checks

CORE = {"contig": "ctgA", "start": 0, "end": 5000}
AA = ("ACDEFGHIKLMNPQRSTVWY" * 20)            # 400 aa
FIRST, SECOND = AA[0:150], AA[200:400]          # the stretches reference genes 1 and 2 aligned to


def _prots():
    return {"pA": {"contig": "ctgA", "start": 100, "end": 1000, "contig_len": 50000, "aa": "M" * 300},
            "q1": {"contig": "ctgB", "start": 200, "end": 1400, "contig_len": 60000, "aa": AA}}


def _rows():
    return [{"reference_gene": 1, "status": "MISSING_FOUND_CLEAR", "best_protein": "q1", "best_contig": "ctgB"},
            {"reference_gene": 2, "status": "MISSING_FOUND_CLEAR", "best_protein": "q1", "best_contig": "ctgB"}]


def _hits():
    return [{"qseqid": "g001", "sseqid": "q1", "pident": 60.0, "qcovhsp": 90.0, "bitscore": 300.0,
             "sstart": "1", "send": "150"},
            {"qseqid": "g002", "sseqid": "q1", "pident": 55.0, "qcovhsp": 90.0, "bitscore": 250.0,
             "sstart": "400", "send": "201"}]


def _search(seen):
    """The first stretch is best in the reference's own cluster; the second belongs to another family."""
    def search(query_fasta, _db, **_kw):
        name, hits = None, []
        for line in open(query_fasta).read().splitlines():
            if line.startswith(">"):
                name = line[1:].split()[0]
                continue
            seen[name] = line
            if line == FIRST:
                hits += [{"qseqid": name, "sseqid": "BGC0000001|1", "bitscore": "200", "pident": "70"}]
            else:
                hits += [{"qseqid": name, "sseqid": "BGC0000002|4", "bitscore": "200", "pident": "70"},
                         {"qseqid": name, "sseqid": "BGC0000001|2", "bitscore": "20", "pident": "31"}]
        return {"ok": True, "hits": hits, "reason": "ok (test)"}
    return search


def test_each_row_is_judged_on_its_own_stretch():
    rows, seen = _rows(), {}
    status = partner_checks(rows, _prots(), _hits(), CORE, "BGC0000001", mibig_db="test.dmnd", search=_search(seen))
    assert status["reciprocal_mibig"] == "run"
    assert sorted(seen.values()) == sorted([FIRST, SECOND])          # both stretches were searched
    assert rows[0]["reciprocal_best_mibig"] == "BGC0000001" and rows[0]["reciprocal_family_ratio"] == 1.0
    assert rows[0]["partner_verdict"] != "PARALOG_FAMILY"
    assert rows[1]["reciprocal_best_mibig"] == "BGC0000002" and rows[1]["reciprocal_family_ratio"] == 0.1
    assert rows[1]["partner_verdict"] == "PARALOG_FAMILY"


def test_identical_stretches_share_one_query():
    rows, seen = _rows(), {}
    hits = _hits()
    hits[1].update(sstart="150", send="1")
    partner_checks(rows, _prots(), hits, CORE, "BGC0000001", mibig_db="test.dmnd", search=_search(seen))
    assert list(seen.values()) == [FIRST]
    assert rows[0]["reciprocal_best_mibig"] == rows[1]["reciprocal_best_mibig"] == "BGC0000001"
