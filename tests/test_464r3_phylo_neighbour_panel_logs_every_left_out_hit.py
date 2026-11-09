"""neighbour_panel_candidates: a mapped 16S hit left out at the --top-16s cap, a hit removed by
--exclude, and subjects with only short alignments each get a PANEL_ISSUES.tsv row."""
import csv
import importlib.util
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("npc_464r3", ROOT / "tools" / "neighbour_panel_candidates.py")
npc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(npc)


def _asm(acc, org, strain):
    return {"accession": acc, "organism": {"organism_name": org, "infraspecific_names": {"strain": strain}},
            "assembly_info": {"assembly_level": "Complete Genome", "assembly_status": "current"}}


def _run(tmp, *extra):
    asms = [_asm("GCF_100001.1", "Genus alpha", "S1"), _asm("GCF_100002.1", "Genus beta", "S2"),
            _asm("GCF_100003.1", "Genus own", "S3")]
    seqs = [{"assembly_accession": "GCF_100001.1", "genbank_accession": "CP100001.1"},
            {"assembly_accession": "GCF_100002.1", "genbank_accession": "CP100002.1"},
            {"assembly_accession": "GCF_100003.1", "genbank_accession": "CP100003.1"}]
    (tmp / "a.jsonl").write_text("\n".join(json.dumps(r) for r in asms) + "\n")
    (tmp / "s.jsonl").write_text("\n".join(json.dumps(r) for r in seqs) + "\n")
    (tmp / "b.tsv").write_text("\n".join([
        "Query_1\tCP100001.1\t99.50\t1450\t0\t0\t1\t1450\t1\t1450\t0.0\t2600",
        "Query_1\tCP100002.1\t98.00\t1400\t0\t0\t1\t1400\t1\t1400\t0.0\t2500",
        "Query_1\tCP100003.1\t100.0\t1500\t0\t0\t1\t1500\t1\t1500\t0.0\t2700",
        "Query_1\tCP100009.1\t99.00\t300\t0\t0\t1\t300\t1\t300\t0.0\t500"]) + "\n")
    (tmp / "ex.txt").write_text("GCF_100003.1\n")
    out = tmp / "out"
    assert npc.main(["--isolate", "ISOLATE_001", "--blast", str(tmp / "b.tsv"), "--assemblies", str(tmp / "a.jsonl"),
                     "--sequences", str(tmp / "s.jsonl"), "--exclude", str(tmp / "ex.txt"),
                     "--out-dir", str(out), *extra]) == 0
    panel = list(csv.DictReader(open(out / "PANEL_TREE.tsv"), delimiter="\t"))
    issues = list(csv.DictReader(open(out / "PANEL_ISSUES.tsv"), delimiter="\t"))
    return [r["ncbi_accession"] for r in panel], issues


def test_capped_excluded_and_short_hits_are_logged(tmp_path):
    panel, issues = _run(tmp_path, "--top-16s", "1")
    assert panel == ["GCF_100001.1"]
    by = {(i["source"], i["item"]): i for i in issues}
    assert ("16S_cap", "GCF_100002.1") in by and "--top-16s cap of 1" in by[("16S_cap", "GCF_100002.1")]["detail"]
    assert ("16S_excluded", "GCF_100003.1") in by
    assert ("16S_below_min_align", "1 subject sequences") in by


def test_no_cap_row_when_everything_fits(tmp_path):
    panel, issues = _run(tmp_path)
    assert sorted(panel) == ["GCF_100001.1", "GCF_100002.1"]
    assert not any(i["source"] == "16S_cap" for i in issues)
