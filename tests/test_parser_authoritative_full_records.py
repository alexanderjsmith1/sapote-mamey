"""Synthetic-only regression candidates; not executed during staging."""
import warnings
import zipfile

import pytest

from mamey import parsers


def gbk(cid="CONTIG_A.1", end=9, sequence="acgtacgtacgt"):
    # Twelve artificial bases; no real genome/translation fixture.
    return (f"LOCUS       {cid} {len(sequence)} bp DNA linear BCT 01-JAN-2000\n"
            "DEFINITION  Synthetic regression fixture.\n"
            f"ACCESSION   {cid}\nVERSION     {cid}\n"
            "FEATURES             Location/Qualifiers\n"
            f"     gene            1..{end}\n"
            '                     /locus_tag="SYNTH_001"\n'
            f"     CDS             1..{end}\n"
            '                     /locus_tag="SYNTH_001"\n'
            '                     /product="synthetic protein"\n'
            f"ORIGIN\n        1 {sequence}\n//\n")


@pytest.fixture(params=["shim", "bio"])
def backend(request, monkeypatch):
    if request.param == "shim":
        monkeypatch.setattr(parsers, "_require_seqio", lambda: None)
    else:
        seqio = pytest.importorskip("Bio.SeqIO")
        monkeypatch.setattr(parsers, "_require_seqio", lambda: seqio)


def archive(tmp_path, members):
    path = tmp_path / "synthetic.zip"
    with zipfile.ZipFile(path, "w") as zf:
        for name, text in members.items():
            zf.writestr(name, text)
    return path


def read(path, **kwargs):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        rows = parsers.read_genbank_records(path, **kwargs)
    return rows, [str(w.message) for w in caught]


def test_output_supersedes_matching_nested_input_and_reports(backend, tmp_path):
    path = archive(tmp_path, {"export/output.gbk": gbk(end=9),
                              "export/Input/original.gbk": gbk(end=12)})
    rows, diagnostics = read(path, exclude_regions=True)
    assert [name for name, _ in rows] == ["export/output.gbk"]
    assert sum("superseded" in message for message in diagnostics) == 1
    assert any("CONTIG_A.1" in message and "exact nucleotide equality" in message for message in diagnostics)
    cds = parsers.extract_cds_features(path)
    assert [(c.locus_tag, c.start, c.end) for c in cds] == [("SYNTH_001", 1, 9)]


def test_input_only_contig_retained_from_multi_record_member(backend, tmp_path):
    path = archive(tmp_path, {"output.gbk": gbk(),
                              "nested/input/original.gbk": gbk(end=12) + gbk("CONTIG_B.1")})
    rows, _ = read(path, exclude_regions=True)
    assert [(name, parsers._record_contig_id(rec)) for name, rec in rows] == [
        ("nested/input/original.gbk", "CONTIG_B.1"), ("output.gbk", "CONTIG_A.1")]


def test_input_only_archive_retained(backend, tmp_path):
    path = archive(tmp_path, {"input/original.gbk": gbk()})
    rows, diagnostics = read(path, exclude_regions=True)
    assert [name for name, _ in rows] == ["input/original.gbk"]
    assert not any("superseded" in message for message in diagnostics)


def test_failed_or_empty_output_keeps_input(backend, tmp_path):
    path = archive(tmp_path, {"output.gbk": "malformed, no GenBank record\n",
                              "input/original.gbk": gbk()})
    rows, diagnostics = read(path, exclude_regions=True)
    assert [name for name, _ in rows] == ["input/original.gbk"]
    assert any("yielded no records" in message for message in diagnostics)


def test_region_only_fallback_and_region_only_mode_unchanged(backend, tmp_path):
    path = archive(tmp_path, {"nested/contig.region001.gbk": gbk()})
    rows, _ = read(path, exclude_regions=True)
    assert [name for name, _ in rows] == ["nested/contig.region001.gbk"]
    rows, _ = read(path, region_only=True, exclude_regions=True)
    assert [name for name, _ in rows] == ["nested/contig.region001.gbk"]


def test_default_keeps_both_and_region_only_keeps_region(backend, tmp_path):
    path = archive(tmp_path, {"output.gbk": gbk(), "input/original.gbk": gbk(end=12),
                              "contig.region001.gbk": gbk()})
    rows, diagnostics = read(path)
    assert len(rows) == 3
    assert not any("superseded" in message for message in diagnostics)
    rows, _ = read(path, region_only=True)
    assert [name for name, _ in rows] == ["contig.region001.gbk"]


def test_multiple_output_versions_flagged_without_merging(backend, tmp_path):
    path = archive(tmp_path, {"a/output.gbk": gbk(), "b/output.gbk": gbk(end=12),
                              "input/original.gbk": gbk()})
    rows, diagnostics = read(path, exclude_regions=True)
    assert [name for name, _ in rows] == ["a/output.gbk", "b/output.gbk"]
    assert any("conflicting output records" in message for message in diagnostics)
    assert any("superseded" in message for message in diagnostics)


def test_input_substring_is_not_input_directory(backend, tmp_path):
    path = archive(tmp_path, {"input_assets/output.gbk": gbk(),
                              "input/original.gbk": gbk(end=12)})
    rows, _ = read(path, exclude_regions=True)
    assert [name for name, _ in rows] == ["input_assets/output.gbk"]


@pytest.mark.parametrize("output_sequence", ["tcgtacgtacgt", "acgtacgtacg"])
def test_sequence_or_length_mismatch_never_drops_input(backend, tmp_path, output_sequence):
    path = archive(tmp_path, {"output.gbk": gbk(sequence=output_sequence),
                              "input/original.gbk": gbk()})
    rows, diagnostics = read(path, exclude_regions=True)
    assert [name for name, _ in rows] == ["input/original.gbk", "output.gbk"]
    assert sum("unresolved sequence conflicts" in message for message in diagnostics) == 1
    assert not any("superseded" in message for message in diagnostics)


def test_uppercase_sequence_equality_allows_supersession(backend, tmp_path):
    path = archive(tmp_path, {"output.gbk": gbk(sequence="ACGTACGTACGT"),
                              "input/original.gbk": gbk()})
    rows, diagnostics = read(path, exclude_regions=True)
    assert [name for name, _ in rows] == ["output.gbk"]
    assert any("exact nucleotide equality" in message for message in diagnostics)


def test_one_matching_output_cannot_hide_conflicting_sibling(backend, tmp_path):
    path = archive(tmp_path, {"a/output.gbk": gbk(),
                              "b/output.gbk": gbk(sequence="tcgtacgtacgt"),
                              "input/original.gbk": gbk()})
    rows, diagnostics = read(path, exclude_regions=True)
    assert len(rows) == 3
    assert any("conflicting output records" in message for message in diagnostics)
    assert any("unresolved sequence conflicts" in message for message in diagnostics)
    assert not any("superseded" in message for message in diagnostics)


def test_many_supersessions_emit_one_bounded_summary(backend, tmp_path):
    output = "".join(gbk(f"SYNTH_{index}.1") for index in range(12))
    path = archive(tmp_path, {"output.gbk": output, "input/original.gbk": output})
    rows, diagnostics = read(path, exclude_regions=True)
    assert len(rows) == 12
    assert all(name == "output.gbk" for name, _ in rows)
    summaries = [message for message in diagnostics if "superseded" in message]
    assert len(summaries) == 1
    assert "12 archived input records" in summaries[0]
    assert "SYNTH_0.1" in summaries[0] and "SYNTH_2.1" in summaries[0]
    assert "SYNTH_3.1" not in summaries[0]
    assert len(summaries[0]) < 1000
