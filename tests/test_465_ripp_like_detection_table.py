"""Tests for mamey/ripp_like_detection.py and tools/ripp_like_detection_table.py."""
import csv
import importlib.util
import json
import zipfile
from pathlib import Path

import pytest

from mamey.ripp_like_detection import _ripp_like_from_rec, domain_summary, extract_ripp_like_triggers

TOOL = Path(__file__).resolve().parents[1] / "tools" / "ripp_like_detection_table.py"
spec = importlib.util.spec_from_file_location("rldt", TOOL)
rldt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rldt)


def cds(start, end, tag, fn=None, aa=100):
    q = {"locus_tag": [tag], "translation": ["M" * aa]}
    if fn:
        q["gene_functions"] = [f"biosynthetic (rule-based-clusters) RiPP-like: {d}" for d in fn]
        q["gene_kind"] = ["biosynthetic"]
    return {"type": "CDS", "location": f"[{start}:{end}](+)", "qualifiers": q}


def region(start, end, num, products):
    return {"type": "region", "location": f"[{start}:{end}](+)",
            "qualifiers": {"region_number": [str(num)], "product": products}}


def pc(start, end, core, num, product="RiPP-like", edge="False"):
    return {"type": "protocluster", "location": f"[{start}:{end}](+)",
            "qualifiers": {"product": [product], "core_location": [f"[{core[0]}:{core[1]}](+)"],
                           "protocluster_number": [str(num)], "contig_edge": [edge]}}


def records():
    r1 = {"id": "contigA", "features": [
        region(0, 30000, 1, ["RiPP-like"]), pc(0, 20000, (5000, 6000), 1),
        cds(5000, 6000, "a1", ["DUF692"]), cds(7000, 8000, "a2"),
        region(40000, 90000, 2, ["NRPS", "RiPP-like"]), pc(50000, 70000, (60000, 62000), 2, edge="True"),
        cds(60000, 61000, "a3", ["YcaO"]), cds(61000, 62000, "a4", ["TIGR03604"], aa=250),
        pc(40000, 48000, (41000, 42000), 3, product="NRPS"), cds(41000, 42000, "a5"),
    ]}
    r2 = {"id": "contigB", "features": [
        region(0, 20000, 1, ["RiPP-like"]), pc(0, 15000, (3000, 4000), 1), cds(9000, 9900, "b1", ["strepbact"]),
    ]}
    return [r1, r2]


def write_zip(path, recs):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("genome.json", json.dumps({"version": "8.0.4", "records": recs}))
    return path


def write_inventory(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["BGC_ID", "Contig", "antiSMASH_Region", "Products"]); w.writerows(rows)
    return path


def test_handler_reads_trigger_genes_inside_core():
    out = []
    for r in records():
        _ripp_like_from_rec(r, "genome.json", out)
    assert len(out) == 3                                       # the NRPS protocluster is not RiPP-like
    a, b, c = out
    assert (a["region"], a["trigger_domains"], a["trigger_locus_tags"], a["status"]) == ("region001", "DUF692", "a1", "TRIGGER_FOUND")
    assert a["region_is_ripp_like_only"] is True
    assert (b["region"], b["trigger_domains"], b["trigger_lengths_aa"]) == ("region002", "TIGR03604+YcaO", "100;250")
    assert b["region_is_ripp_like_only"] is False and b["contig_edge"] == "True"
    assert c["status"] == "TRIGGER_UNRESOLVED" and c["trigger_domains"] == ""   # trigger gene outside the core


def test_summary_keeps_unresolved_and_counts_context():
    out = []
    for r in records():
        _ripp_like_from_rec(r, "genome.json", out)
    s = {x["trigger_domains"]: x for x in domain_summary(out)}
    assert s["DUF692"]["protoclusters"] == 1 and s["DUF692"]["in_ripp_like_only_regions"] == 1
    assert s["TIGR03604+YcaO"]["on_contig_edge"] == 1
    assert s["TRIGGER_UNRESOLVED"]["protoclusters"] == 1


def test_extract_uses_shared_record_pass(tmp_path):
    rows, receipt = extract_ripp_like_triggers(write_zip(tmp_path / "g.zip", records()))
    assert len(rows) == 3
    assert receipt["files"][0]["status"] == "READ_COMPLETE" and receipt["files"][0]["records_seen"] == 2


def test_tool_binds_identity_and_holds_the_rest(tmp_path):
    z = write_zip(tmp_path / "g.zip", records())
    inv = write_inventory(tmp_path / "inv.csv", [("BGC001", "contigA", "region001", "RiPP-like"),
                                                  ("BGC002", "contigA", "region002", "NRPS;RiPP-like")])
    rows, summ = rldt.main(["--genome", "G1", str(z), str(inv), "--outdir", str(tmp_path / "o"), "--stem", "t"])
    by = {(r["contig"], r["region"]): r for r in rows}
    assert by[("contigA", "region001")]["identity"] == "G1 / contigA / region001 / BGC001"
    hold = by[("contigB", "region001")]
    assert hold["identity_status"] == "IDENTITY_HOLD" and hold["bgc_alias"] == "" and hold["identity"] == ""
    rec = json.loads((tmp_path / "o" / "t_receipt.json").read_text())
    assert rec["protoclusters"] == 3 and rec["identity_holds"] == 1 and rec["unresolved"] == 1
    assert rec["genomes"][0]["zip_sha256"] == rldt.sha(z)
    table = list(csv.DictReader(open(tmp_path / "o" / "t_protoclusters.tsv"), delimiter="\t"))
    assert [r["identity_status"] for r in table].count("BOUND") == 2


def test_duplicate_inventory_key_is_a_hold(tmp_path):
    z = write_zip(tmp_path / "g.zip", records())
    inv = write_inventory(tmp_path / "inv.csv", [("BGC001", "contigA", "region001", ""), ("BGC009", "contigA", "region001", "")])
    rows, _ = rldt.main(["--genome", "G1", str(z), str(inv), "--outdir", str(tmp_path / "o"), "--stem", "t"])
    assert next(r for r in rows if r["region"] == "region001" and r["contig"] == "contigA")["identity_status"] == "IDENTITY_HOLD"


def test_no_overwrite_and_bad_inputs(tmp_path):
    z = write_zip(tmp_path / "g.zip", records())
    inv = write_inventory(tmp_path / "inv.csv", [])
    args = ["--genome", "G1", str(z), str(inv), "--outdir", str(tmp_path / "o"), "--stem", "t"]
    rldt.main(args)
    with pytest.raises(SystemExit, match="refusing to overwrite"):
        rldt.main(args)
    with pytest.raises(SystemExit, match="distinct"):
        rldt.main(["--genome", "G1", str(z), str(inv), "--genome", "G1", str(z), str(inv),
                   "--outdir", str(tmp_path / "p"), "--stem", "t"])
    bad = tmp_path / "bad.csv"; bad.write_text("Contig,Region\n")
    with pytest.raises(SystemExit, match="needs columns"):
        rldt.main(["--genome", "G1", str(z), str(bad), "--outdir", str(tmp_path / "q"), "--stem", "t"])


def test_unreadable_json_stops_before_writing(tmp_path):
    z = tmp_path / "broken.zip"
    with zipfile.ZipFile(z, "w") as zz:
        zz.writestr("genome.json", "{not json")
    inv = write_inventory(tmp_path / "inv.csv", [])
    with pytest.raises(SystemExit, match="record pass incomplete"):
        rldt.main(["--genome", "G1", str(z), str(inv), "--outdir", str(tmp_path / "o"), "--stem", "t"])
    assert not (tmp_path / "o" / "t_protoclusters.tsv").exists()
