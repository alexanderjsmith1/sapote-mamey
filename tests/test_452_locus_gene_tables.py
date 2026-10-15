"""tools/gap_rescue_gene_table.py --window/--summary and load_gene_names(prefer_db, length_fallback)
(card .452 locus_gene_tables).

The genes in the window of a gap-rescue run, read from the strain side: every CDS on the core contig from the first to
the last matched gene, plus trim each side, with antiSMASH role and domains, the reference gene matched and the BLASTp
top-10 name bound by protein. An 8 pt print table refuses any text wider than its space. One summary table merges the
runs. The name loader's new options are opt-in; its default is unchanged. Synthetic data only.
"""
import csv
import importlib.util
import json
import sys
import zipfile
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")
Bio = pytest.importorskip("Bio")
from Bio import SeqIO  # noqa: E402
from Bio.Seq import Seq  # noqa: E402
from Bio.SeqFeature import FeatureLocation, SeqFeature  # noqa: E402
from Bio.SeqRecord import SeqRecord  # noqa: E402
from PIL import Image  # noqa: E402

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "tools"))


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gt = _load(HERE / "tools" / "gap_rescue_gene_table.py", "gap_rescue_gene_table_452w")
glm = _load(HERE / "tools" / "gap_rescue_locus_map.py", "gap_rescue_locus_map_452w")
CORE = "NODE_1_length_30000_cov_10.0"
IDENT = f"SYN-970 / {CORE} / region001 / BGC001"
# five genes on the core contig, one on another contig; genes 2 and 4 match reference genes
GENES = [(CORE, 1000, 2000, 1), (CORE, 2500, 4000, -1), (CORE, 6000, 7500, 1), (CORE, 9000, 10500, 1),
         (CORE, 16000, 17000, 1), ("NODE_2_length_9000_cov_9.0", 100, 900, 1)]


def _zip(tmp_path):
    recs = {}
    for i, (contig, s, e, strand) in enumerate(GENES, 1):
        rec = recs.setdefault(contig, SeqRecord(Seq("A" * 30000), id=contig, name=contig[:16], description=contig,
                                                annotations={"molecule_type": "DNA"}))
        q = {"locus_tag": [f"ctg_{i}"], "translation": ["M" * ((e - s) // 3)]}
        if i == 2:
            q.update(gene_kind=["biosynthetic"],
                     sec_met_domain=["PKS_KS (E-value: 2.1e-50, bitscore: 160.0, seeds: 10, tool: rule-based-clusters)"],
                     NRPS_PKS=["Domain: PKS_AT (120-400). E-value: 3.4e-40. Score: 120.0. Matches aSDomain: x"],
                     gene_functions=["biosynthetic (smcogs) SMCOG1022: Beta-ketoacyl synthase"])
        rec.features.append(SeqFeature(FeatureLocation(s, e, strand=strand), type="CDS", qualifiers=q))
    recs[CORE].features.append(SeqFeature(FeatureLocation(500, 12000), type="region",
                                          qualifiers={"region_number": ["1"], "product": ["T1PKS", "NRPS"]}))
    gbk = tmp_path / "SYN-970.gbk"
    SeqIO.write(list(recs.values()), gbk, "genbank")
    zp = tmp_path / "SYN-970.zip"
    with zipfile.ZipFile(zp, "w") as z:
        z.write(gbk, "SYN-970.gbk")
    return zp


def _run(tmp_path):
    run = tmp_path / "SYN-970_BGC001_synthetic"
    run.mkdir()
    (run / "gap_rescue_receipt.json").write_text(json.dumps(
        {"core": IDENT, "reference": "BGC0000000.gbk", "reference_name": "synthetic", "label": "SYN-970"}))
    cols = ["reference_gene", "name", "status", "best_identity_pct", "best_protein", "best_locus", "partner_verdict"]
    rows = [["1", "synA", "PRESENT_IN_CORE", "81.4", "p2", "ctg_2", ""],
            ["2", "synB", "MISSING_FOUND_CLEAR", "66.6", "p4", "ctg_4", "SUPPORTED"],
            ["3", "synC", "MISSING_FOUND_CLEAR", "50.0", "p6", "ctg_6", "SINGLE_GENE"],
            ["4", "synD", "MISSING_NOT_FOUND", "", "", "", ""]]
    with open(run / "gap_rescue.tsv", "w", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(cols); w.writerows(rows)
    return run


def test_genome_cds_reads_roles_domains_and_products(tmp_path):
    cds, products = gt.genome_cds(_zip(tmp_path))
    assert cds["ctg_2"]["domains"] == "PKS_KS (2.1e-50); PKS_AT (3.4e-40)"
    assert cds["ctg_2"]["role"] == "biosynthetic" and cds["ctg_2"]["smcog"] == "Beta-ketoacyl synthase"
    assert cds["ctg_2"]["strand"] == "−" and cds["ctg_1"]["start"] == 1001 and cds["ctg_1"]["aa"] == 333
    assert products[(CORE, 1)] == "T1PKS; NRPS"


def test_window_is_matched_core_genes_plus_trim(tmp_path):
    cds, _ = gt.genome_cds(_zip(tmp_path))
    rows = list(csv.DictReader(open(_run(tmp_path) / "gap_rescue.tsv"), delimiter="\t"))
    names = {"ctg_2": {"top10_consensus_name": "beta-ketoacyl synthase", "db": "nr", "top10_mean_identity": "71.5",
                       "consensus_share": "9 of 10"}}
    table, facts = gt.window_rows(rows, cds, IDENT, names, trim_bp=2000)
    # matched on the core contig: ctg_2 (2501-4000) and ctg_4 (9001-10500); window 501..12500 takes ctg_1..ctg_4,
    # not ctg_5 (16001-17000) and not ctg_6 (other contig, matched elsewhere)
    assert [r["locus_tag"] for r in table] == ["ctg_1", "ctg_2", "ctg_3", "ctg_4"]
    assert (facts["window_start"], facts["window_end"]) == (501, 12500)
    assert table[1]["reference_gene_match"] == "synA 81%" and table[3]["reference_gene_match"] == "synB 67%"
    assert table[1]["BLASTp_name"] == "beta-ketoacyl synthase" and table[0]["BLASTp_name"] == ""
    assert list(table[0]) == gt.WINDOW_COLS and facts["genes_matched_in_window"] == 2
    with pytest.raises(ValueError, match="GENE_WINDOW"):
        gt.window_rows(rows, cds, "SYN-970 / NODE_9_length_1_cov_1.0 / region001 / BGC009", {})


def test_name_loader_options_are_opt_in(tmp_path):
    tsv = tmp_path / "names.tsv"
    cols = ["strain", "gene", "db", "top10_consensus_name", "aa_length", "query_aa_length", "protein_sha256"]
    rows = [["SYN-970", "ctg_1", "ClusteredNR", "cluster name", "", "333", ""],
            ["SYN-970", "ctg_1", "nr", "nr name", "", "333", ""],
            ["SYN-970", "ctg_2", "nr", "wrong length", "", "900", ""]]
    with open(tsv, "w", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n"); w.writerow(cols); w.writerows(rows)
    prots = {"p1": {"tag": "ctg_1", "aa": "M" * 333}, "p2": {"tag": "ctg_2", "aa": "M" * 500}}
    default = glm.load_gene_names(tsv, "SYN-970", prots)
    assert len(default) == 0 and default.names_unbound == 3          # no checksum, no aa_length: nothing binds
    opt = glm.load_gene_names(tsv, "SYN-970", prots, prefer_db=("nr",), length_fallback="query_aa_length")
    assert opt["ctg_1"]["top10_consensus_name"] == "nr name"          # nr wins over ClusteredNR
    assert "ctg_2" not in opt                                        # 900 aa searched, 500 aa in the genome
    only_len = glm.load_gene_names(tsv, "SYN-970", prots, length_fallback="query_aa_length")
    assert only_len["ctg_1"]["top10_consensus_name"] == "cluster name"   # file order without prefer_db


def test_write_window_table_and_summary(tmp_path):
    zp, run = _zip(tmp_path), _run(tmp_path)
    res = gt.write_window_table(tmp_path / "out", run, zp, {}, 2000, "SYN-970")
    assert res["rows"] == 4
    s = res["summary"]
    assert s["identity"] == IDENT and s["antiSMASH_product"] == "T1PKS; NRPS" and s["reference"] == "BGC0000000"
    assert (s["reference_genes"], s["in_region"], s["found_clearly_elsewhere"], s["supported_elsewhere"]) == (4, 1, 2, 1)
    assert s["median_identity_in_region"] == "81.4"
    png = tmp_path / "out" / "gene_window_table.png"
    assert png.is_file() and Image.open(png).info.get("Software", "").startswith("Sapote-Mamey")
    assert Image.open(png).width == 3000                              # 10 in at 300 dpi
    import matplotlib
    with matplotlib.rc_context({"savefig.bbox": "tight", "savefig.pad_inches": 0.35}):   # a global tight save
        gt.write_window_table(tmp_path / "tight", run, zp, {}, 2000, "SYN-970")
    assert Image.open(tmp_path / "tight" / "gene_window_table.png").width == 3000
    assert (tmp_path / "out" / "gene_window_table.pdf").is_file()
    gt.write_window_table(tmp_path / "out2", run, zp, {}, 2000, "SYN-970", draw=False)
    n = gt.merge_summaries([tmp_path / "out", tmp_path / "out2"], tmp_path / "summary.tsv")
    merged = list(csv.DictReader(open(tmp_path / "summary.tsv"), delimiter="\t"))
    assert n == 2 and list(merged[0]) == gt.SUMMARY_COLS


def test_print_table_refuses_text_wider_than_its_space(tmp_path, monkeypatch):
    zp, run = _zip(tmp_path), _run(tmp_path)
    monkeypatch.setattr(gt, "CHAR_IN", 0.01)   # wrap far too loosely: the measured cells overflow
    with pytest.raises(ValueError, match="GENE_WINDOW_PRINT"):
        gt.write_window_table(tmp_path / "out", run, zp, {}, 2000, "SYN-970")


def test_cli_window_and_summary(tmp_path):
    zp, run = _zip(tmp_path), _run(tmp_path)
    assert gt.main(["--window", "--run", str(run), "--zip", str(zp), "--out", str(tmp_path / "w"), "--no-print"]) == 0
    assert (tmp_path / "w" / "gene_window_table.tsv").is_file()
    assert not (tmp_path / "w" / "gene_window_table.pdf").exists()
    assert gt.main(["--summary", str(tmp_path / "w"), "--out", str(tmp_path / "all.tsv")]) == 0
    with pytest.raises(SystemExit, match="needs --run and --zip"):
        gt.main(["--window", "--out", str(tmp_path / "x")])
    with pytest.raises(SystemExit):   # the reference-side table keeps its own required arguments
        gt.main(["--run", str(run)])
