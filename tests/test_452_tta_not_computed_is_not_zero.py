"""A CDS without a nucleotide sequence has an uncomputed TTA count, not zero TTA codons."""
import csv
from types import SimpleNamespace

from mamey.gene_context import build_gene_context, write_gene_context


def _cds(locus, nt):
    return SimpleNamespace(contig="NODE_1", start=100, end=399, strand=1, locus_tag=locus,
                           product="p", translation="M" * 99, nucleotide_seq=nt, qualifiers={})


BGCS = [SimpleNamespace(bgc_id="BGC001", contig="NODE_1", start=1, end=5000)]


def _rows(*cds):
    return {r["locus_tag"]: r for r in build_gene_context(BGCS, list(cds))["bgcs"]["BGC001"]}


def test_absent_or_empty_nucleotide_is_not_computed():
    rows = _rows(_cds("a", None), _cds("b", ""))
    for locus in ("a", "b"):
        assert rows[locus]["tta_codons"] is None
        assert rows[locus]["has_nucleotide"] is False


def test_completed_zero_and_positive_counts_unchanged():
    rows = _rows(_cds("z", "ATGCTGGGG"), _cds("p", "TTAGGGTTA"), _cds("f", "GTTAAA"))
    assert rows["z"]["tta_codons"] == 0 and rows["z"]["has_nucleotide"] is True
    assert rows["p"]["tta_codons"] == 2
    assert rows["f"]["tta_codons"] == 0  # in-frame scan only, as before


def test_cds_table_writes_blank_for_not_computed(tmp_path):
    out = write_gene_context(tmp_path, "S1", BGCS, [_cds("a", None), _cds("z", "ATG")])
    assert out["status"] == "WRITTEN", out
    with open(tmp_path / "S1_cds_table.csv", newline="", encoding="utf-8") as fh:
        by_locus = {r["locus_tag"]: r for r in csv.DictReader(fh)}
    assert by_locus["a"]["tta_codons"] == ""
    assert by_locus["z"]["tta_codons"] == "0"


def test_authored_verify_does_not_bind_uncomputed_tta(tmp_path):
    import mamey.authored_verify as authored_verify
    package = tmp_path / "TEST-001" / "package"
    package.mkdir(parents=True)
    (package / "TEST-001_gene_context.jsonl").write_text(
        '{"schema_version":"gene_context/1.0"}\n'
        '{"bgc_id":"BGC001","cds":[{"locus_tag":"NODE_1_1","tta_codons":null},'
        '{"locus_tag":"NODE_1_2","tta_codons":0},{"locus_tag":"NODE_1_3"}]}\n',
        encoding="utf-8")
    ctx = authored_verify._bgc_context_from_package(package, "BGC001")
    assert ctx["cds_count"] == 3
    assert ctx["tta_by_gene"] == {"node_1_2": 0, "node_1_3": 0}
