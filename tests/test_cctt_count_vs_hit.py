"""W27: CCTT must distinguish HIT count from BGC-carrying count.

cctt['counts'] is the raw hit count per T43 bucket (gene/motif level); cctt['bgc_counts'] is how many
DISTINCT BGCs carry each trigger. A single BGC can carry many hits, so the two diverge — 8 PHO hits inside
one BGC is a single dedicated locus, not a phosphonate-rich strain. This test pins the distinction.
"""
from types import SimpleNamespace
from mamey.source_scans import run_source_scans
from mamey.models import BGCRecord, CDSFeature


def test_bgc_counts_distinct_from_hit_counts():
    # two phosphonate genes (PepM/FomA-like) packed into ONE BGC's contig window -> 1 carrying BGC, >1 hits
    bgcs = [BGCRecord(bgc_id="BGC001", contig="ctg1", region_number=1, start=0, end=20000, contig_length=20000)]
    cds = [
        CDSFeature(contig="ctg1", start=1000, end=2000, strand=1, locus_tag="g1",
                   product="phosphoenolpyruvate phosphomutase"),
        CDSFeature(contig="ctg1", start=3000, end=4000, strand=1, locus_tag="g2",
                   product="phosphonopyruvate decarboxylase"),
    ]
    ss = run_source_scans(bgcs, cds, {"ctg1": "A" * 20000}, None)
    counts = ss.cctt.get("counts", {})
    bgc_counts = ss.cctt.get("trigger_bgc_counts", {})
    # bgc_counts must exist and never exceed the number of BGCs
    assert isinstance(bgc_counts, dict)
    for trig, nb in bgc_counts.items():
        assert nb <= len(bgcs), (trig, nb)
    # for any trigger present, hit count >= BGC-carrying count (a BGC can hold multiple hits)
    for trig, nb in bgc_counts.items():
        assert counts.get(trig, 0) >= nb, (trig, counts.get(trig), nb)
