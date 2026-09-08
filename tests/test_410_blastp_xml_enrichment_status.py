"""v9.7.410 hostile audit — an alignment XML that parses to nothing must not be reported as
enrichment. Before: ``ingest_blastp`` returned ``enriched: True`` whenever the XML file *existed*,
so a classic BLAST XML1 download (``<Iteration>`` blocks, which the XML2 parser does not read)
left every description / sciname column blank with no signal at all.
"""
from __future__ import annotations

import warnings

import pytest

from mamey import blastp_ingest as bi
from tests.test_blastp_bgc_recovery_v97410 import CSV_BGC_LEADING, XML_FULL_TITLE, _master, _write

XML1_CLASSIC = """<?xml version="1.0"?>
<BlastOutput><BlastOutput_iterations><Iteration>
<Iteration_query-def>BGC008_ctg162_3 NODE_162</Iteration_query-def>
<Iteration_hits><Hit><Hit_accession>WP_401849909</Hit_accession><Hit_def>x</Hit_def></Hit></Iteration_hits>
</Iteration></BlastOutput_iterations></BlastOutput>
"""


def test_xml1_download_is_reported_empty_and_warned(tmp_path):
    csv = _write(tmp_path, "hits.csv", CSV_BGC_LEADING)
    xml = _write(tmp_path, "aln.xml", XML1_CLASSIC)
    status: dict = {}
    with pytest.warns(UserWarning, match="yielded 0 queries"):
        rows = bi.build_b5_rows("AS-TEST", csv, xml, top_n=10, enrich_status=status)
    assert rows and status == {"xml": "empty"}


def test_unparseable_xml_is_reported_error_and_warned(tmp_path):
    csv = _write(tmp_path, "hits.csv", CSV_BGC_LEADING)
    # Binary junk is text-scanned to nothing (status "empty"); an unreadable path raises inside the
    # parser and must surface as "error:<Type>" rather than vanish.
    junk = tmp_path / "junk.xml"
    junk.write_bytes(b"\xff\xfe not xml at all")
    status: dict = {}
    with pytest.warns(UserWarning, match="yielded 0 queries"):
        bi.build_b5_rows("AS-TEST", csv, junk, top_n=10, enrich_status=status)
    assert status == {"xml": "empty"}
    unreadable = tmp_path / "dir.xml"
    unreadable.mkdir()
    status = {}
    with pytest.warns(UserWarning, match="could not be parsed"):
        bi.build_b5_rows("AS-TEST", csv, unreadable, top_n=10, enrich_status=status)
    assert status["xml"].startswith("error:")


def test_ingest_summary_enriched_is_truthful(tmp_path):
    csv = _write(tmp_path, "hits.csv", CSV_BGC_LEADING)
    good = _write(tmp_path, "good.xml", XML_FULL_TITLE)
    bad = _write(tmp_path, "bad.xml", XML1_CLASSIC)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res_good = bi.ingest_blastp(_master(tmp_path), "AS-TEST", csv, good, top_n=10)
        res_bad = bi.ingest_blastp(_master(tmp_path), "AS-TEST", csv, bad, top_n=10)
        res_none = bi.ingest_blastp(_master(tmp_path), "AS-TEST", csv, None, top_n=10)
    assert (res_good["enriched"], res_good["xml_status"]) == (True, "ok")
    assert (res_bad["enriched"], res_bad["xml_status"]) == (False, "empty")
    assert (res_none["enriched"], res_none["xml_status"]) == (False, "absent")


def test_good_xml_does_not_warn(tmp_path):
    csv = _write(tmp_path, "hits.csv", CSV_BGC_LEADING)
    xml = _write(tmp_path, "aln.xml", XML_FULL_TITLE)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        bi.build_b5_rows("AS-TEST", csv, xml, top_n=10)
