"""9.7.465: runs of one locus against different reference records are joined, never summed.

Fail-before on sealed 9.7.464: tools/gap_rescue_join_runs.py does not exist, and a run's receipt does not record the
genome or reference bytes it read, so two runs of one locus against two reference records could not be checked
against each other or read as one table. Pass-after: the join refuses runs
of different loci, genomes or a repeated reference, keeps each reference's own counts, names local proteins that are
the best match for genes of two references, and gap_directed_rescue's receipt carries inputs.zip_sha256.
"""
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
if "mamey" not in sys.modules:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ID = "S / NODE_1_length_9000_cov_10.0 / region001 / BGC001"
GENE_COLS = ["reference_gene", "name", "status", "best_identity_pct", "best_locus", "best_region_identity",
             "partner_verdict"]


def _run(tmp, name, ref, genes, core=ID, label="S", zip_sha=None, ref_sha=None):
    d = tmp / name
    d.mkdir()
    receipt = {"tool": "gap_directed_rescue", "label": label, "core": core, "reference": f"{ref}.gbk",
               "reference_name": ref.lower()}
    if zip_sha:
        receipt["inputs"] = {"zip": "S.zip", "zip_sha256": zip_sha, "reference": f"{ref}.gbk",
                             "reference_sha256": ref_sha or hashlib.sha256(ref.encode()).hexdigest()}
    (d / "gap_rescue_receipt.json").write_text(json.dumps(receipt))
    with open(d / "gap_rescue.tsv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=GENE_COLS, delimiter="\t")
        w.writeheader()
        for i, (gene, status, locus) in enumerate(genes, 1):
            w.writerow({"reference_gene": i, "name": gene, "status": status, "best_identity_pct": "80",
                        "best_locus": locus, "best_region_identity": core if status == "PRESENT_IN_CORE" else "",
                        "partner_verdict": ""})
    core_n = sum(1 for _g, s, _l in genes if s == "PRESENT_IN_CORE")
    (d / "gene_table_counts.tsv").write_text(f"reference_genes\tcore\n{len(genes)}\t{core_n}\n")
    return d


def _two(tmp, **kw):
    a = _run(tmp, "ref_a", "BGC0000001", [("aA", "PRESENT_IN_CORE", "c_1"), ("aB", "PRESENT_IN_CORE", "c_2")], **kw)
    b = _run(tmp, "ref_b", "BGC0000002", [("bA", "PRESENT_IN_CORE", "c_2"), ("bB", "MISSING_NOT_FOUND", "")])
    return a, b


def test_join_keeps_each_reference_and_names_shared_proteins(tmp_path):
    import gap_rescue_join_runs as J
    a, b = _two(tmp_path)
    (a / "gene_table.tsv").write_text("CDS\tReference gene\tLocation\n"
                                      "c_1\taA\tBGC001, NODE_1 (core); crosses the region edge (40% of the gene inside)\n"
                                      "c_2\taB\tBGC001, NODE_1 (core)\n")
    out = tmp_path / "out"
    assert J.main(["--run", str(a), "--run", str(b), "--out", str(out)]) == 0
    runs = list(csv.DictReader(open(out / "runs.tsv"), delimiter="\t"))
    assert [(r["reference"], r["core"], r["zip_sha256"]) for r in runs] == [
        ("BGC0000001", "2", "not recorded"), ("BGC0000002", "1", "not recorded")]
    genes = {g["reference_gene"]: g for g in csv.DictReader(open(out / "reference_genes.tsv"), delimiter="\t")}
    assert len(genes) == 4 and {g["identity"] for g in genes.values()} == {ID}
    assert genes["aB"]["also_best_for"] == "BGC0000002:bA"      # c_2 is the best protein for both
    assert genes["bA"]["also_best_for"] == "BGC0000001:aB"
    assert genes["aA"]["also_best_for"] == "" and genes["bB"]["best_locus"] == ""
    assert genes["aA"]["placement"] == "in the region" and genes["bB"]["placement"] == "not found in this assembly"
    assert genes["aA"]["gene_table_notes"] == "crosses the region edge (40% of the gene inside)"
    assert not any(re.search(r"\bBGC\d{3}\b", line.replace(ID, ""))       # no short locus label is copied
                   for line in (out / "reference_genes.tsv").read_text().splitlines()[1:])


@pytest.mark.parametrize("change,code", [
    ({"core": "S / NODE_2_length_9000_cov_10.0 / region001 / BGC002"}, "DIFFERENT_LOCUS"),
    ({"label": "T"}, "DIFFERENT_GENOME"),
])
def test_runs_of_another_locus_or_genome_are_refused(tmp_path, capsys, change, code):
    import gap_rescue_join_runs as J
    a = _run(tmp_path, "ref_a", "BGC0000001", [("aA", "PRESENT_IN_CORE", "c_1")])
    b = _run(tmp_path, "ref_b", "BGC0000002", [("bA", "PRESENT_IN_CORE", "c_1")], **change)
    out = tmp_path / "out"
    assert J.main(["--run", str(a), "--run", str(b), "--out", str(out)]) == 2
    assert code in capsys.readouterr().err and not out.exists()


def test_different_genome_bytes_and_a_repeated_reference_are_refused(tmp_path, capsys):
    import gap_rescue_join_runs as J
    a = _run(tmp_path, "ref_a", "BGC0000001", [("aA", "PRESENT_IN_CORE", "c_1")], zip_sha="a" * 64)
    b = _run(tmp_path, "ref_b", "BGC0000002", [("bA", "PRESENT_IN_CORE", "c_1")], zip_sha="b" * 64)
    assert J.main(["--run", str(a), "--run", str(b), "--out", str(tmp_path / "o1")]) == 2
    assert "DIFFERENT_GENOME" in capsys.readouterr().err
    c = _run(tmp_path, "ref_c", "BGC0000001", [("aA", "PRESENT_IN_CORE", "c_1")])
    assert J.main(["--run", str(a), "--run", str(c), "--out", str(tmp_path / "o2")]) == 2
    assert "SAME_REFERENCE_TWICE" in capsys.readouterr().err


def test_receipt_records_the_genome_and_reference_bytes(tmp_path, monkeypatch):
    D = pytest.importorskip("gap_directed_rescue")
    zip_path, ref = tmp_path / "S.zip", tmp_path / "BGC0000001.gbk"
    zip_path.write_bytes(b"zip bytes")
    ref.write_bytes(b"reference bytes")
    out = tmp_path / "run"

    def fake_analyse(label, prots, regions, core, reference, *args, **kwargs):
        out.mkdir()
        receipt = {"tool": "gap_directed_rescue", "label": label, "core": ID, "reference": Path(reference).name}
        (out / "gap_rescue_receipt.json").write_text(json.dumps(receipt))
        return receipt

    monkeypatch.setattr(D, "load_genome", lambda z, label: ({}, []))
    monkeypatch.setattr(D, "resolve_core", lambda regions, spec: {"identity": ID})
    monkeypatch.setattr(D, "choose_reference", lambda *a, **k: (ref, "ref", "given"))
    monkeypatch.setattr(D, "analyse_region", fake_analyse)
    monkeypatch.setattr(D, "summary_line", lambda receipt, o: "ok")
    monkeypatch.setattr(D, "assert_output_outside_bundle", lambda *a, **k: None)
    assert D.main(["--zip", str(zip_path), "--label", "S", "--core", "NODE_1.region001", "--reference", str(ref),
                   "--out", str(out), "--no-figure"]) == 0
    inputs = json.loads((out / "gap_rescue_receipt.json").read_text())["inputs"]
    import hashlib
    assert inputs["zip_sha256"] == hashlib.sha256(b"zip bytes").hexdigest()
    assert inputs["reference_sha256"] == hashlib.sha256(b"reference bytes").hexdigest()


# ---- review findings (fresh-agent attack, 9 Nov) ----
def test_same_reference_under_two_names_is_refused(tmp_path, capsys):
    import gap_rescue_join_runs as J
    a = _run(tmp_path, "ref_a", "BGC0000001", [("aA", "PRESENT_IN_CORE", "c_1")], zip_sha="a" * 64, ref_sha="e" * 64)
    b = _run(tmp_path, "ref_b", "BGC0000001_copy", [("aA", "PRESENT_IN_CORE", "c_1")], zip_sha="a" * 64,
             ref_sha="e" * 64)
    assert J.main(["--run", str(a), "--run", str(b), "--out", str(tmp_path / "o")]) == 2   # same reference_sha256
    assert "SAME_REFERENCE_TWICE" in capsys.readouterr().err
    c = _run(tmp_path, "ref_c", "BGC0000003", [("cA", "PRESENT_IN_CORE", "c_1")])
    d = tmp_path / "ref_d"
    d.mkdir()
    for f in ("gap_rescue.tsv", "gene_table_counts.tsv"):
        (d / f).write_bytes((c / f).read_bytes())
    rec = json.loads((c / "gap_rescue_receipt.json").read_text())
    rec["reference"] = "BGC0000003.gb"                                       # same stem, other suffix
    (d / "gap_rescue_receipt.json").write_text(json.dumps(rec))
    assert J.main(["--run", str(c), "--run", str(d), "--out", str(tmp_path / "o2")]) == 2
    assert "SAME_REFERENCE_TWICE" in capsys.readouterr().err


def test_genome_check_says_when_a_run_has_no_checksum(tmp_path):
    import gap_rescue_join_runs as J
    a = _run(tmp_path, "ref_a", "BGC0000001", [("aA", "PRESENT_IN_CORE", "c_1")], zip_sha="2" * 64)
    b = _run(tmp_path, "ref_b", "BGC0000002", [("bA", "PRESENT_IN_CORE", "c_1")])
    assert J.main(["--run", str(a), "--run", str(b), "--out", str(tmp_path / "o")]) == 0
    checks = {r["genome_check"] for r in csv.DictReader(open(tmp_path / "o" / "runs.tsv"), delimiter="\t")}
    assert checks == {"not checked: one or more runs recorded no ZIP checksum"}
    c = _run(tmp_path, "ref_c", "BGC0000003", [("cA", "PRESENT_IN_CORE", "c_1")], zip_sha="2" * 64)
    assert J.main(["--run", str(a), "--run", str(c), "--out", str(tmp_path / "o2")]) == 0
    assert {r["genome_check"] for r in csv.DictReader(open(tmp_path / "o2" / "runs.tsv"), delimiter="\t")} == {"checked"}


def test_notes_follow_row_order_not_gene_names(tmp_path, capsys):
    import gap_rescue_join_runs as J
    a = _run(tmp_path, "ref_a", "BGC0000001", [("", "PRESENT_IN_CORE", "c_1"), ("", "MISSING_FOUND_CLEAR", "c_9")])
    (a / "gene_table.tsv").write_text("CDS\tReference gene\tLocation\n"
                                      "c_1\t\tBGC001, NODE_1 (core); note of row one\n"
                                      "c_9\t\tNODE_1, same contig, outside the region; note of row two\n")
    b = _run(tmp_path, "ref_b", "BGC0000002", [("bA", "PRESENT_IN_CORE", "c_5")])
    assert J.main(["--run", str(a), "--run", str(b), "--out", str(tmp_path / "o")]) == 0
    genes = list(csv.DictReader(open(tmp_path / "o" / "reference_genes.tsv"), delimiter="\t"))
    assert [g["gene_table_notes"] for g in genes[:2]] == ["note of row one", "note of row two"]
    (a / "gene_table.tsv").write_text("CDS\tReference gene\tLocation\nc_1\tzzz\tBGC001, NODE_1 (core)\n")
    assert J.main(["--run", str(a), "--run", str(b), "--out", str(tmp_path / "o2")]) == 2
    assert "TABLE_MISMATCH" in capsys.readouterr().err


def test_bad_receipts_and_bad_out_exit_2_and_never_overwrite(tmp_path, capsys):
    import gap_rescue_join_runs as J
    a, b = _two(tmp_path)
    rec = json.loads((a / "gap_rescue_receipt.json").read_text())
    good = dict(rec)
    rec["inputs"] = None                                   # read as "not recorded", never a crash
    (a / "gap_rescue_receipt.json").write_text(json.dumps(rec))
    assert J.main(["--run", str(a), "--run", str(b), "--out", str(tmp_path / "o0")]) == 0
    rec["inputs"] = ["not", "an", "object"]
    (a / "gap_rescue_receipt.json").write_text(json.dumps(rec))
    assert J.main(["--run", str(a), "--run", str(b), "--out", str(tmp_path / "o")]) == 2
    (a / "gap_rescue_receipt.json").write_text("[]")
    assert J.main(["--run", str(a), "--run", str(b), "--out", str(tmp_path / "o")]) == 2
    (a / "gap_rescue_receipt.json").write_text(json.dumps(good))
    afile = tmp_path / "a_file"
    afile.write_text("x")
    assert J.main(["--run", str(a), "--run", str(b), "--out", str(afile)]) == 2
    out = tmp_path / "done"
    assert J.main(["--run", str(a), "--run", str(b), "--out", str(out)]) == 0
    before = (out / "runs.tsv").read_bytes()
    assert J.main(["--run", str(a), "--run", str(b), "--out", str(out)]) == 2
    assert "OUT_NOT_EMPTY" in capsys.readouterr().err and (out / "runs.tsv").read_bytes() == before


def test_all_regions_runs_record_their_inputs_too(tmp_path):
    D = pytest.importorskip("gap_directed_rescue")
    import inspect
    A = pytest.importorskip("gap_rescue_all_regions")
    gone = D.record_inputs(tmp_path / "no_such_run", {}, tmp_path / "gone.zip", tmp_path / "gone.gbk")["inputs"]
    assert {k: gone[k] for k in ("zip", "zip_sha256", "reference", "reference_sha256")} == {
        "zip": "gone.zip", "zip_sha256": "", "reference": "gone.gbk", "reference_sha256": ""}   # never a crash
    assert "record_inputs(" in inspect.getsource(A._run_all)
    out = tmp_path / "run"
    out.mkdir()
    zip_path, ref = tmp_path / "S.zip", tmp_path / "BGC0000001.gbk"
    zip_path.write_bytes(b"zip bytes")
    ref.write_bytes(b"reference bytes")
    receipt = D.record_inputs(out, {"core": ID}, zip_path, ref, zip_sha256="c" * 64)
    saved = json.loads((out / "gap_rescue_receipt.json").read_text())
    assert saved == receipt and saved["inputs"]["zip_sha256"] == "c" * 64
