"""End-to-end smoke test: run_source_scans + triage on the real smoke ZIP, minus-strand CDS present.

Catches module-level breakage in the scan pipeline that unit fixtures miss — e.g. the v9.7.19
`reverse_complement` clobber, which 141 unit tests passed over because no fixture exercised scan_tfbs's
reverse-strand branch. Not gated on the registry; only skipped where the fixture ZIP is intentionally
stripped (the analysis-free tier). The shipped ZIP has no minus-strand CDS, so one is injected to force the
exact path that regressed.
"""
from __future__ import annotations
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mamey import parsers
from mamey.models import CDSFeature
from mamey.source_scans import run_source_scans
from mamey.scoring import triage_bgcs

ZIP = Path(__file__).resolve().parent.parent / "examples" / "test_data" / "smoke_antismash_small.zip"


@pytest.mark.skipif(not ZIP.exists(), reason="smoke_antismash_small.zip is stripped from the analysis-free tier")
def test_run_source_scans_end_to_end_with_minus_strand_cds():
    z = str(ZIP)
    bgcs = parsers.parse_bgcs_from_zip(z)
    cds = list(parsers.extract_cds_features(z))
    contigs = parsers.extract_contig_sequences(z)
    domains = parsers.extract_domain_features(z)
    # The shipped ZIP carries no minus-strand CDS; inject one on a real contig so scan_tfbs's reverse-strand
    # branch (reverse_complement) is exercised — the path the unit suite never covered.
    contig = next(iter(contigs))
    cds.append(CDSFeature(contig, 500, 1400, -1, "smoke_minus", "hypothetical protein", None, None, {}))

    ss = run_source_scans(bgcs, cds, contigs, domains)   # must not raise (covers reverse_complement, etc.)
    tr = triage_bgcs(bgcs, None, ss)
    assert isinstance(tr, list) and len(tr) == len(bgcs)
    assert ss.cctt.get("per_bgc") is not None             # the v9.7.19 per_bgc bridge is wired end-to-end


if __name__ == "__main__":
    test_run_source_scans_end_to_end_with_minus_strand_cds()
    print("end-to-end scan-pipeline smoke: pass")
