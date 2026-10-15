"""tools/blastp_tag_position_audit.py keys BLASTp rows whose tag is a position inside a region, and holds the rest.

Synthetic antiSMASH ZIP: one contig, two region files. Every protein length is distinct except one deliberate tie, so
each binding rule is exercised once. The inputs are never changed.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("blastp_tag_position_audit", ROOT / "tools/blastp_tag_position_audit.py")
tool = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tool)

LENGTHS = {"ctg1_1": 101, "ctg1_2": 102, "ctg1_3": 110, "ctg1_4": 104, "ctg1_5": 105, "ctg1_6": 110, "ctg1_7": 107,
           "ctg1_8": 108}


def _gbk(name, tags):
    length = 900 * (len(LENGTHS) + 1)
    lines = [f"LOCUS       {name:<16}{length:>12} bp    DNA     linear   UNK 01-JAN-1980",
             f"DEFINITION  synthetic {name}.", f"ACCESSION   {name}", f"VERSION     {name}",
             "FEATURES             Location/Qualifiers"]
    for tag in tags:
        i = int(tag.split("_")[1])
        lines += [f"     CDS             {900 * i + 1}..{900 * i + 330}", f'                     /locus_tag="{tag}"',
                  f'                     /translation="{"M" + "A" * (LENGTHS[tag] - 1)}"']
    lines.append("ORIGIN")
    for start in range(0, length, 60):
        chunk = "a" * min(60, length - start)
        lines.append(f"{start + 1:>9} " + " ".join(chunk[j:j + 10] for j in range(0, len(chunk), 10)))
    return "\n".join(lines + ["//"]) + "\n"


@pytest.fixture
def inputs(tmp_path):
    z = tmp_path / "SYN.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("SYN.gbk", _gbk("NODE_1", list(LENGTHS)))
        zf.writestr("NODE_1.region001.gbk", _gbk("NODE_1", ["ctg1_3", "ctg1_4", "ctg1_5"]))
        zf.writestr("NODE_1.region002.gbk", _gbk("NODE_1", ["ctg1_6", "ctg1_7", "ctg1_8"]))
    rows = tmp_path / "hits.csv"
    with open(rows, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["strain", "bgc_id", "gene", "aa_length", "pct_identity"])
        w.writerows([["SYN-1", "BGC001", "ctg1_4", "104", "90"],    # the tag is right
                     ["SYN-1", "BGC001", "ctg1_2", "104", "88"],    # 2nd CDS of region001 is ctg1_4 (104 aa)
                     ["SYN-1", "BGC001", "ctg1_1", "110", "70"],    # 1st CDS of both regions is 110 aa
                     ["SYN-1", "BGC001", "ctg1_3", "999", "60"],    # nothing that long
                     ["SYN-1", "BGC001", "ctg1_5", "", "50"],       # no recorded length
                     ["SYN-1", "BGC001", "gene=x", "104", "40"]])   # not a ctgN_M tag
    inv = tmp_path / "SYN-1_2_inventory.csv"
    with open(inv, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["BGC_ID", "Contig", "antiSMASH_Region"])
        w.writerows([["BGC010", "NODE_1", "region001"], ["BGC011", "NODE_1", "region002"]])
    return z, rows, inv


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def test_each_rule_binds_or_holds_and_inputs_are_untouched(inputs, tmp_path):
    z, rows, inv = inputs
    before = [_sha(p) for p in inputs]
    out = tmp_path / "keyed.tsv"
    assert tool.main(["--antismash-zip", str(z), "--rows", str(rows), "--inventory", str(inv), "--out", str(out)]) == 0
    got = {r["source_gene"]: r for r in csv.DictReader(open(out), delimiter="\t")}
    assert {g: r["binding"] for g, r in got.items()} == {
        "ctg1_4": "TAG_OK", "ctg1_2": "REGION_POSITION", "ctg1_1": "AMBIGUOUS", "ctg1_3": "NO_FIT",
        "ctg1_5": "NO_LENGTH", "gene=x": "TAG_UNPARSED"}
    moved = got["ctg1_2"]
    assert (moved["locus_tag"], moved["contig"], moved["region"], moved["bgc_alias"]) == \
        ("ctg1_4", "NODE_1", "region001", "BGC010")
    assert moved["protein_sha256"] == hashlib.sha256(("M" + "A" * 103).encode()).hexdigest()
    assert got["ctg1_4"]["bgc_alias"] == "BGC010" and got["ctg1_4"]["source_bgc"] == "BGC001"
    assert all(not got[g]["locus_tag"] for g in ("ctg1_1", "ctg1_3", "ctg1_5", "gene=x"))
    assert [_sha(p) for p in inputs] == before


def test_an_existing_output_is_refused(inputs, tmp_path):
    z, rows, _inv = inputs
    out = tmp_path / "keyed.tsv"
    out.write_text("keep me\n")
    with pytest.raises(SystemExit):
        tool.main(["--antismash-zip", str(z), "--rows", str(rows), "--out", str(out)])
    assert out.read_text() == "keep me\n"


def test_rows_without_gene_and_length_columns_are_refused(inputs, tmp_path):
    z, _rows, _inv = inputs
    bad = tmp_path / "bad.csv"
    bad.write_text("strain,locus\nSYN-1,ctg1_4\n")
    with pytest.raises(SystemExit):
        tool.main(["--antismash-zip", str(z), "--rows", str(bad), "--out", str(tmp_path / "o.tsv")])
    assert not (tmp_path / "o.tsv").exists()
