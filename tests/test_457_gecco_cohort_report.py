"""tools/gecco_cohort_report.py: GECCO calls listed and drawn beside antiSMASH regions, on synthetic data only.

One genome with two antiSMASH regions on two contigs. GECCO writes the contig names with its coverage rewrite
(cov_12.500000 -> cov_12.5), as it does for SPAdes names. Calls: one inside region001, one on the region002 contig but
outside the region, one on a contig with no region, and one on a contig whose node number is reused at another length."""
import csv
import importlib.util
import json
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("gcr", ROOT / "tools" / "gecco_cohort_report.py")
gcr = importlib.util.module_from_spec(spec); spec.loader.exec_module(gcr)

C1 = "NODE_1_length_9000_cov_12.500000"
C2 = "NODE_2_length_8000_cov_20.250000"


def region_gbk(contig, start, end, product, category, edge="False"):
    return (f"LOCUS       {contig[:16]}\nCOMMENT     ##antiSMASH-Data-START##\n            Orig. start  :: {start}\n"
            f"            Orig. end    :: {end}\n            ##antiSMASH-Data-END##\nFEATURES             Location/Qualifiers\n"
            f'     protocluster    1..{end - start}\n                     /category="{category}"\n'
            f'                     /product="{product}"\n     region          1..{end - start}\n'
            f'                     /contig_edge="{edge}"\n                     /product="{product}"\n//\n')


def gecco_row(seq, cid, start, end, typ, p, domains="PF00109;PF00109;PF02801"):
    return dict(sequence_id=seq, cluster_id=cid, start=start, end=end, average_p=p, max_p=p, type=typ,
                alkaloid_probability=0, nrp_probability=0, polyketide_probability=0.9, ripp_probability=0,
                saccharide_probability=0, terpene_probability=0, proteins="g1;g2;g3", domains=domains)


def kit(tmp_path, aliases=True):
    z = tmp_path / "S-1.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr(f"S-1/{C1}.region001.gbk", region_gbk(C1, 1000, 5000, "T1PKS", "PKS"))
        zf.writestr(f"S-1/{C2}.region002.gbk", region_gbk(C2, 0, 3000, "NRPS", "NRPS", edge="True"))
    rows = [gecco_row("NODE_1_length_9000_cov_12.5", "c1", 4000, 6000, "Polyketide", 0.99),
            gecco_row("NODE_2_length_8000_cov_20.25", "c2", 5001, 7000, "NRP", 0.95),
            gecco_row("NODE_7_length_3000_cov_9.0", "c3", 10, 2900, "Unknown", 0.85, domains=""),
            gecco_row("NODE_1_length_4000_cov_3.1", "c4", 100, 900, "RiPP", 0.9)]
    g = tmp_path / "S-1.clusters.tsv"
    with open(g, "w", newline="") as fh:
        w = csv.DictWriter(fh, list(rows[0]), delimiter="\t"); w.writeheader(); w.writerows(rows)
    (tmp_path / "genomes.tsv").write_text(f"strain\tgroup\tantismash_zip\tgecco_clusters\nS-1\tG1\t{z}\t{g}\n")
    (tmp_path / "names.tsv").write_text("accession\tname\nPF00109\tketoacyl-synt\nPF02801\tKetoacyl-synt_C\n")
    if aliases:
        (tmp_path / "aliases.tsv").write_text(f"strain\tcontig\tregion\tbgc_alias\nS-1\t{C1}\tregion001\tBGC001\n"
                                              f"S-1\t{C2}\tregion002\tBGC002\n")
    return tmp_path


def run(tmp_path, *extra):
    args = ["--genomes", str(tmp_path / "genomes.tsv"), "--pfam-names", str(tmp_path / "names.tsv"), "--out", str(tmp_path / "out")]
    return gcr.main(args + list(extra))


def calls(tmp_path):
    return {r["cluster_id"]: r for r in csv.DictReader(open(tmp_path / "out" / "gecco_calls.tsv"), delimiter="\t")}


def test_overlap_states_and_contig_joins(tmp_path):
    kit(tmp_path)
    assert run(tmp_path, "--aliases", str(tmp_path / "aliases.tsv"), "--no-figures") == 0
    c = calls(tmp_path)
    assert c["c1"]["state"] == "OVERLAPS_REGION" and c["c1"]["contig"] == C1
    assert c["c1"]["overlapping_regions"] == f"S-1 / {C1} / region001 / BGC001" and c["c1"]["overlapping_categories"] == "PKS"
    assert c["c2"]["state"] == "NO_REGION_OVERLAP" and c["c2"]["contig"] == C2   # joined by alias, outside the region
    assert c["c3"]["state"] == "NO_REGION_OVERLAP" and c["c3"]["contig_source"].startswith("as written by GECCO")
    # node 1 at another length is a different contig: never joined to region001's contig
    assert c["c4"]["state"] == "NO_REGION_OVERLAP" and c["c4"]["contig"] == "NODE_1_length_4000_cov_3.1"


def test_pfam_names_and_counts(tmp_path):
    kit(tmp_path)
    assert run(tmp_path, "--no-figures") == 0
    assert calls(tmp_path)["c1"]["pfam_domains"] == "PF00109 (ketoacyl-synt) x2; PF02801 (Ketoacyl-synt_C)"


def test_alias_is_never_invented(tmp_path):
    kit(tmp_path, aliases=False)
    assert run(tmp_path, "--no-figures") == 0
    regs = list(csv.DictReader(open(tmp_path / "out" / "regions_with_gecco.tsv"), delimiter="\t"))
    assert {r["identity"] for r in regs} == {f"S-1 / {C1} / region001 / alias not supplied", f"S-1 / {C2} / region002 / alias not supplied"}


def test_summary_receipt_and_typed_list(tmp_path):
    kit(tmp_path)
    assert run(tmp_path, "--no-figures") == 0
    s = next(csv.DictReader(open(tmp_path / "out" / "summary_by_genome.tsv"), delimiter="\t"))
    assert (s["regions"], s["regions_with_gecco"], s["gecco_calls"], s["calls_in_regions"], s["calls_outside_regions"]) == ("2", "1", "4", "1", "3")
    r = json.loads((tmp_path / "out" / "receipt.json").read_text())
    assert r["calls"] == 4 and len(r["inputs_sha256"]) == 4
    listed = (tmp_path / "out" / "gecco_calls_outside_regions_typed.md").read_text()
    assert "/ c2 |" in listed and "/ c4 |" in listed and "/ c3 |" not in listed   # Unknown is not listed


def test_refusals(tmp_path):
    kit(tmp_path)
    (tmp_path / "out").mkdir()
    assert run(tmp_path) == 2                                   # an existing output folder is never reused
    (tmp_path / "out").rmdir()
    assert run(tmp_path, "--group-order", "G9") == 2            # the group order must name every group
    bad = tmp_path / "bad.tsv"; bad.write_text("x\ty\n1\t2\n")
    (tmp_path / "genomes.tsv").write_text(f"strain\tgroup\tantismash_zip\tgecco_clusters\nS-1\tG1\t{tmp_path / 'S-1.zip'}\t{bad}\n")
    assert run(tmp_path) == 2                                   # not a GECCO clusters table


def test_figures_meet_the_text_floor(tmp_path):
    pytest.importorskip("matplotlib"); pytest.importorskip("pypdf"); pytest.importorskip("PIL")
    kit(tmp_path)
    assert run(tmp_path, "--aliases", str(tmp_path / "aliases.tsv")) == 0
    out = tmp_path / "out"
    for folder, stem in (("calls_by_genome", "gecco_calls_by_genome"), ("type_vs_category", "gecco_type_vs_antismash_category")):
        for suffix in (".pdf", ".png", ".svg", "_plot_only.png", "_with_caption.png", "_CAPTION.md", "_data.tsv"):
            assert (out / folder / f"{stem}{suffix}").exists(), (folder, suffix)
    checks = json.loads((out / "receipt.json").read_text())["text_check"]
    assert checks and all(v["smallest_pt"] >= 7.95 for v in checks.values())


def test_isolate_against_references(tmp_path):
    pytest.importorskip("matplotlib"); pytest.importorskip("pypdf"); pytest.importorskip("PIL"); pytest.importorskip("numpy")
    kit(tmp_path)
    z, g = tmp_path / "S-1.zip", tmp_path / "S-1.clusters.tsv"
    lines = ["strain\tgroup\tantismash_zip\tgecco_clusters\tgenus\trole", f"S-1\tG1\t{z}\t{g}\tSynthetica\tisolate"]
    lines += [f"R-{k}\tpublic\t{z}\t{g}\tSynthetica\treference" for k in range(5)] + [f"X-1\tpublic\t{z}\t{g}\tSynthetica\tSID"]
    (tmp_path / "genomes.tsv").write_text("\n".join(lines) + "\n")
    assert run(tmp_path) == 0
    out = tmp_path / "out"
    assert (out / "calls_vs_references" / "gecco_calls_vs_references_with_caption.png").exists()
    pct = list(csv.DictReader(open(out / "calls_vs_references" / "isolate_percentiles.tsv"), delimiter="\t"))
    assert [(p["strain"], p["reference_genomes"], p["midrank_percentile"]) for p in pct if p["measure"] == "gecco_calls"] == [("S-1", "5", "50")]
    heat = list(csv.DictReader(open(out / "type_vs_category" / "gecco_type_vs_antismash_category_data.tsv"), delimiter="\t"))
    assert {h["set"] for h in heat} == {"Isolates", "Reference genomes"}       # SID genomes are in neither panel
    assert "Reference genomes per genus: *Synthetica* 5" in (out / "calls_vs_references" / "gecco_calls_vs_references_CAPTION.md").read_text()


def test_role_must_be_known(tmp_path):
    kit(tmp_path)
    z, g = tmp_path / "S-1.zip", tmp_path / "S-1.clusters.tsv"
    (tmp_path / "genomes.tsv").write_text(f"strain\tgroup\tantismash_zip\tgecco_clusters\trole\nS-1\tG1\t{z}\t{g}\tpublic\n")
    assert run(tmp_path) == 2
