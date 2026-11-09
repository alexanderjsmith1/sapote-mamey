# Synthetic regression inputs only.
"""build_reconstruction binds each fragment to its own region GenBank and calls the census a region-file census.

Before: a `<prefix>*.region*.gbk` glob took the first match, so NODE_1 could read NODE_10's file or
another region on the same contig, and the report called the result "every CDS on each contig".
"""
from __future__ import annotations

import importlib.util
import json
import pathlib

_spec = importlib.util.spec_from_file_location(
    "build_reconstruction_464r3b",
    pathlib.Path(__file__).resolve().parent.parent / "tools" / "build_reconstruction.py")
br = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(br)


def _gbk(path, tag):
    path.write_text(f'LOCUS x\nFEATURES\n     CDS             1..300\n                     /locus_tag="{tag}"\n'
                    f'                     /product="hypothetical protein"\n//\n', encoding="utf-8")


def _setup(tmp_path, notes=None, region_number=2):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    gbk = tmp_path / "gbk"
    gbk.mkdir()
    cb = tmp_path / "cb"
    cb.mkdir()
    _gbk(gbk / "NODE_1.region001.gbk", "r1_gene")
    _gbk(gbk / "NODE_1.region002.gbk", "r2_gene")
    _gbk(gbk / "NODE_10.region001.gbk", "n10_gene")
    (pkg / "manifest.json").write_text(json.dumps({"bgcs": [
        {"bgc_id": "BGC002", "contig": "NODE_1", "products": ["NRPS"], "region_number": region_number,
         "notes": notes or []}]}), encoding="utf-8")
    return str(pkg), str(cb), str(gbk)


def _frag(tmp_path, **kw):
    pkg, cb, gbk = _setup(tmp_path, **kw)
    out = br.reconstruct(pkg, cb, gbk, ["BGC002"])
    frags = out[1]
    return frags[0]


def test_region_number_selects_the_right_file(tmp_path):
    f = _frag(tmp_path)
    assert f["gbk_file"] == "NODE_1.region002.gbk"
    assert [g["locus_tag"] for g in f["genes"]] == ["r2_gene"]


def test_exact_source_gbk_note_wins(tmp_path):
    f = _frag(tmp_path, notes=["source_gbk=/x/NODE_1.region001.gbk"], region_number=2)
    assert f["gbk_file"] == "NODE_1.region001.gbk" and f["gbk_status"] == "EXACT_SOURCE_GBK"


def test_several_candidates_without_a_match_are_held(tmp_path):
    f = _frag(tmp_path, region_number=None)
    assert f["gbk_status"] == "AMBIGUOUS" and f["genes"] == [] and f["gbk_file"] == ""


def test_prefix_does_not_match_a_longer_contig_name(tmp_path):
    path, status = br.select_region_gbk(str(tmp_path), None, "NODE_1", None)
    assert path is None
    gbk = tmp_path / "g"
    gbk.mkdir()
    _gbk(gbk / "NODE_10.region001.gbk", "n10")
    assert br.select_region_gbk(str(gbk), None, "NODE_1", 1) == (None, "NOT_FOUND")


def test_report_names_the_census_scope():
    cb = {"R": {"hits": [{"subject": "g1", "query": "q1", "pid": "80", "score": "100"}], "cum_score": 100, "type": "NRPS",
                "desc": "ref"}}
    held = {"bgc": "BGC002", "ctg": "ctg1", "cb": cb, "genes": [], "gbk_file": "", "gbk_status": "AMBIGUOUS",
            "products": "NRPS", "node": "NODE_1"}
    ok = dict(held, bgc="BGC003", ctg="ctg2", genes=[{"locus_tag": "q1", "label": "x"}],
              gbk_file="NODE_2.region001.gbk", gbk_status="REGION_NUMBER_MATCH")
    text = br.render("SYN", [held, ok], ["R"], "R")
    text = text if isinstance(text, str) else "\n".join(text)
    assert "every CDS on each contig" not in text.lower()
    assert "not necessarily the whole contig" in text
    assert "AMBIGUOUS" in text
