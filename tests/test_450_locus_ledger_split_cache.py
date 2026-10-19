"""Synthetic current-ledger split admission; no searches, project data or rendering."""
import builtins
import csv
import gzip
from pathlib import Path

import pytest

from tests.test_449_locus_reading_pages import (lrp, fx, _gene, _ledger, _argv, S, C1, ID1, STEM1, STEM2)


OTHER = "FIXTURE_OTHER"


def _write_ledger(path, rows):
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "wt", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=lrp.LEDGER_COLUMNS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


@pytest.mark.parametrize("compressed", [False, True])
def test_current_split_does_not_admit_absent_strain_from_prior_flat_cache(tmp_path, compressed):
    cache = tmp_path / "cache"
    cache.mkdir()
    stale = cache / f"{S}.tsv"
    stale.write_bytes(b"prior saved ledger bytes must be retained\n")
    stale_before = stale.read_bytes()
    ledger = tmp_path / ("current.tsv.gz" if compressed else "current.tsv")
    _write_ledger(ledger, [_gene("current_only", C1, 1, strain=OTHER)])
    source_before = ledger.read_bytes()

    current = lrp.ledger_by_strain(ledger, None, cache)

    assert current != cache and current.parent == cache
    assert lrp._read_tsv(current / f"{S}.tsv") == [], "absence in current input must not reuse prior rows"
    assert [row["locus_tag"] for row in lrp._read_tsv(current / f"{OTHER}.tsv")] == ["current_only"]
    assert stale.read_bytes() == stale_before and ledger.read_bytes() == source_before


def test_repeated_split_keeps_prior_bytes_and_selects_only_current_rows(tmp_path):
    ledger, cache = tmp_path / "ledger.tsv", tmp_path / "cache"
    _write_ledger(ledger, [_gene("prior", C1, 1)])
    first = lrp.ledger_by_strain(ledger, None, cache)
    prior = first / f"{S}.tsv"
    prior_before = prior.read_bytes()
    _write_ledger(ledger, [_gene("current", C1, 2)])

    second = lrp.ledger_by_strain(ledger, None, cache)

    assert first != second and first.parent == second.parent == cache
    assert prior.read_bytes() == prior_before
    assert [row["locus_tag"] for row in lrp._read_tsv(second / f"{S}.tsv")] == ["current"]


def test_explicit_ledger_directory_is_returned_without_writing_split_cache(tmp_path):
    supplied = tmp_path / "supplied"
    supplied.mkdir()
    source = supplied / f"{S}.tsv"
    source.write_bytes(b"explicit per-strain evidence\n")
    cache = tmp_path / "unused_cache"

    assert lrp.ledger_by_strain(None, str(supplied), cache) == supplied
    assert source.read_bytes() == b"explicit per-strain evidence\n" and not cache.exists()


def test_split_cache_symlink_refusal_preserves_external_files(tmp_path):
    external = tmp_path / "external"
    external.mkdir()
    saved = external / f"{S}.tsv"
    saved.write_bytes(b"saved source evidence\n")
    cache = tmp_path / "cache"
    cache.symlink_to(external, target_is_directory=True)
    ledger = tmp_path / "ledger.tsv"
    _write_ledger(ledger, [_gene("current", C1, 1)])

    with pytest.raises(ValueError, match="PAGE_LEDGER_CACHE_PATH_REFUSED"):
        lrp.ledger_by_strain(ledger, None, cache)

    assert list(external.iterdir()) == [saved] and saved.read_bytes() == b"saved source evidence\n"


def _combined_arguments(inputs, out, ledger, bgc):
    argv = _argv(inputs, out, "--bgc", bgc)
    index = argv.index("--ledger-dir")
    argv[index:index + 2] = ["--ledger", str(ledger)]
    return argv


def test_append_omitting_requested_strain_logs_no_rows_instead_of_rendering_old_locus(fx, tmp_path, monkeypatch):
    def no_search(*_args, **_kwargs):
        pytest.fail("synthetic page build must not execute external searches")
    monkeypatch.setattr(lrp.subprocess, "run", no_search)
    ledger, out = tmp_path / "combined.tsv", tmp_path / "out"
    _write_ledger(ledger, _ledger())
    first = lrp.build(lrp.parse_args(_combined_arguments(fx, out, ledger, "BGC001")))
    assert first == [out / S / f"{STEM1}.md"]
    page_before = first[0].read_bytes()
    prior_split_files = {path: path.read_bytes() for path in (out / "_ledger_by_strain").rglob("*.tsv")}
    assert prior_split_files
    # This current source omits the requested fixture strain; old BGC002 is retained only in the prior split.
    _write_ledger(ledger, [_gene("other", C1, 1, strain=OTHER)])
    current_source = ledger.read_bytes()

    second = lrp.build(lrp.parse_args(_combined_arguments(fx, out, ledger, "BGC002")))

    assert second == []
    assert not (out / S / f"{STEM2}.md").exists()
    with (out / "BUILD_LOG.tsv").open() as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    last = rows[-1]
    assert last["strain"] == S and last["bgc"] == "BGC002" and last["status"] == "NO_LEDGER_ROWS"
    assert last["identity"] == f"{S} / NODE_2_length_40000_cov_10.0 / region001 / BGC002"
    assert last["rows"] == "0" and last["file"] == ""
    assert first[0].read_bytes() == page_before and ledger.read_bytes() == current_source
    assert {path: path.read_bytes() for path in prior_split_files} == prior_split_files
    assert ID1 in first[0].read_text(), "prior full four-part locus identity stays intact"



def _track_split_outputs(monkeypatch):
    real_open = builtins.open
    opened = []
    def track(path, mode="r", *args, **kwargs):
        stream = real_open(path, mode, *args, **kwargs)
        if "w" in mode:
            opened.append((Path(path), stream))
        return stream
    monkeypatch.setattr(lrp, "open", track, raising=False)
    return opened


@pytest.mark.parametrize("unsafe", ["", " ", ".", "..", ".hidden", "../../outside", "sub/strain",
                                     "sub\\strain", "/absolute", "C:\\absolute", "C:relative", "trailing ",
                                     "bad\nname", "bad\x00name", None])
def test_unsafe_strain_refuses_before_its_output_open_and_retains_sources(tmp_path, monkeypatch, unsafe):
    ledger, cache = tmp_path / "ledger.tsv", tmp_path / "cache"
    saved = tmp_path / "outside.tsv"
    saved.write_bytes(b"retained evidence outside the split\n")
    if unsafe is None:
        # A short physical CSV row makes DictReader return None for the strain value.
        ledger.write_text("locus_tag\tstrain\ngood\tAS-900\nbad\n")
    else:
        _write_ledger(ledger, [_gene("good", C1, 1), _gene("bad", C1, 2, strain=unsafe)])
    source_before, saved_before = ledger.read_bytes(), saved.read_bytes()
    opened = _track_split_outputs(monkeypatch)

    with pytest.raises(ValueError, match="PAGE_LEDGER_STRAIN_PATH_REFUSED"):
        lrp.ledger_by_strain(ledger, None, cache)

    assert [path.name for path, _ in opened] == [f"{S}.tsv"], "bad row must refuse before its output open"
    assert all(stream.closed for _, stream in opened), "partial valid-strain outputs must close on refusal"
    assert ledger.read_bytes() == source_before and saved.read_bytes() == saved_before
    assert {path.name for path in cache.rglob("*.tsv")} == {f"{S}.tsv"}


def test_split_output_handles_close_if_input_iteration_fails(tmp_path, monkeypatch):
    ledger, cache = tmp_path / "ledger.tsv", tmp_path / "cache"
    _write_ledger(ledger, [_gene("good", C1, 1)])
    source_before = ledger.read_bytes()
    real_reader = lrp.csv.DictReader
    def broken_reader(stream, **kwargs):
        yield from real_reader(stream, **kwargs)
        raise csv.Error("synthetic malformed ledger during iteration")
    monkeypatch.setattr(lrp.csv, "DictReader", broken_reader)
    opened = _track_split_outputs(monkeypatch)

    with pytest.raises(csv.Error, match="synthetic malformed ledger"):
        lrp.ledger_by_strain(ledger, None, cache)

    assert len(opened) == 1 and opened[0][1].closed
    assert opened[0][0].is_file(), "partial generated evidence remains retained"
    assert ledger.read_bytes() == source_before


def test_split_output_handle_closes_even_if_header_write_fails(tmp_path, monkeypatch):
    ledger, cache = tmp_path / "ledger.tsv", tmp_path / "cache"
    _write_ledger(ledger, [_gene("good", C1, 1)])
    source_before = ledger.read_bytes()
    class BrokenWriter:
        def writerow(self, _row):
            raise OSError("synthetic output header failure")
    monkeypatch.setattr(lrp, "_SafeWriter", lambda *_args, **_kwargs: BrokenWriter())
    opened = _track_split_outputs(monkeypatch)

    with pytest.raises(OSError, match="synthetic output header failure"):
        lrp.ledger_by_strain(ledger, None, cache)

    assert len(opened) == 1 and opened[0][1].closed
    assert ledger.read_bytes() == source_before
