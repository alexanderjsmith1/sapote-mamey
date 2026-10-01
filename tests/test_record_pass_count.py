"""Record-pass count invariant — the regression guard a package-write smoke test cannot provide.

The streaming/serialization smoke test asserts a package is *written*; it cannot see a silent
performance regression where the run parses the antiSMASH records more times than necessary
(output stays correct, the package still writes). Two such regressions were caught by hand with a
counter during development:

  * the double parse_antismash_evidence (status path + BGC-evidence-application path) — two full
    record passes per run; deduped by threading one evidence dict through both, and
  * the off-mode tigrfam fold briefly adding a wasted tigrfam pass via the BGC parser.

This test makes that counter permanent. _run_record_extractors is the single driver every record
extractor routes through, so counting its invocations counts record passes directly.

Invariant for a run on a single-contig input:
  * bounded -> exactly ONE pass, carrying all 7 handlers (the 2 tigrfam readers + the 5 json-evidence extractors)
  * off     -> exactly ONE pass, carrying ONLY the 2 tigrfam readers

The tigrfam channel has two readers of the same record: the tier-1 hits and, since v9.7.445, their report-only
competitors for the dominated-diagnostic report. Both ride the one pass; neither opens the JSON in off mode.

A second pass (dedup regression) or an extra off-mode pass (tigrfam-fold regression) fails here.
"""
import pathlib
import tempfile

import mamey.antismash_evidence as ae
from mamey.cli import run_one_strain

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
SYNTH = FIXTURES / "synthetic_single_contig_antismash.zip"


def _run_counting_passes(json_mode, monkeypatch, input_zip):
    """Run one strain and return the list of per-pass handler counts (one entry per record pass)."""
    handler_counts = []
    orig = ae._run_record_extractors

    def _counting(zip_path, handlers):
        h = list(handlers)
        handler_counts.append(len(h))
        return orig(zip_path, h)

    monkeypatch.setattr(ae, "_run_record_extractors", _counting)
    run_one_strain(
        strain_id="PASSCOUNT", display_name="PASSCOUNT",
        input_zip=str(input_zip), outdir=tempfile.mkdtemp(), mode="full",
        taxonomy="", source="", bioactivity="",
        master_path=None, json_mode=json_mode,
    )
    return handler_counts


def test_bounded_run_makes_one_record_pass(monkeypatch, synthetic_single_contig_full_locus_zip):
    counts = _run_counting_passes("bounded", monkeypatch, synthetic_single_contig_full_locus_zip)
    assert len(counts) == 1, f"expected ONE record pass in bounded mode, got {len(counts)}: {counts}"
    # tigrfam + tigrfam competitors (report-only) + nrps_pks + active_site + product_class + ripp + rrefinder
    assert counts[0] == 7, f"bounded pass should carry all 7 handlers, got {counts[0]}"


def test_off_run_makes_one_tigrfam_only_pass(monkeypatch, synthetic_single_contig_full_locus_zip):
    counts = _run_counting_passes("off", monkeypatch, synthetic_single_contig_full_locus_zip)
    assert len(counts) == 1, f"expected ONE record pass in off mode, got {len(counts)}: {counts}"
    # off mode: only the two tigrfam readers (the json-evidence extractors are gated off)
    assert counts[0] == 2, f"off-mode pass should carry only the 2 tigrfam readers, got {counts[0]}"
