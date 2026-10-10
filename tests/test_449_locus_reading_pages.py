"""tools/locus_reading_pages.py: one locus-reading page per antiSMASH region, every gene with every evidence layer.

A synthetic strain (AS-900, from tools/test_synthetic_ids.txt) with two regions: BGC001 has a gene-table pair whose
gap-rescue and split rows point to a short contig (NODE_5, shown whole) and a long one (NODE_7, matched CDS and 2 on each
side); BGC002 has no pair. The gap-rescue row names NODE_5 with its coverage string rewritten (cov_9.12345 for the
ledger's cov_9.012345), as some tables do. Page searches use stub hmmsearch and DIAMOND executables, or none.
"""
import csv
import gzip
import importlib.util
import json
import os
import re
import stat
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("locus_reading_pages", ROOT / "tools" / "locus_reading_pages.py")
lrp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lrp)

S = "AS-900"
C1, C2 = "NODE_1_length_60000_cov_10.0", "NODE_2_length_40000_cov_10.0"
C5, C7, C9 = "NODE_5_length_8000_cov_9.012345", "NODE_7_length_90000_cov_9.0", "NODE_9_length_50000_cov_9.0"
C5_REWRITTEN = "NODE_5_length_8000_cov_9.12345"   # the same contig, as a gap-rescue table may write it
ID1 = f"{S} / {C1} / region001 / BGC001"
STEM1, STEM2 = f"{S}_NODE1_r001_BGC001", f"{S}_NODE2_r001_BGC002"
CLAIMS = ("produces", "is a ", "novel compound")


def _gene(tag, contig, i, bgc="", **kw):
    g = {k: "" for k in lrp.LEDGER_COLUMNS}
    g.update(strain=S, locus_tag=tag, contig=contig, start=str(1000 * i), end=str(1000 * i + 900), strand="1", bgc=bgc,
             aa="300", as_gene_function="biosynthetic context" if bgc else "", L2b_bind="bound",
             mibig_queried="yes, no hit", L5_status="no_hit_under_filters", LG_gene_avg_p="0.5")
    g.update(kw)
    return g


def _ledger():
    rows = []
    for i in range(1, 13):                                   # NODE_1: region BGC001 is g5-g8
        kw = {}
        if i == 2:
            kw = {"L2b_bind": "NOT_SEARCHED"}                # outside the region, never Pfam-searched: †
        if i == 3:
            kw = {"mibig_queried": "no (outside regions)"}   # never MIBiG-searched: †
        if i == 4:
            kw = {"L5_status": "not_queried"}                # not yet against the reference genomes: ‡
        if 5 <= i <= 8:
            kw = {"as_gene_function": "core biosynthetic" if i == 6 else "biosynthetic context",
                  "L5_status": "hit", "L5_ref": "Streptomyces exemplar 1 | GCF_000000001.1", "L5_product": "ketosynthase",
                  "L5_pident": "61.0", "L5_region_call": "inside", "L5_ref_region": "r1 (T1PKS)",
                  "gene_map_rows": f"{S}_BGC001_alpha: abc{i} 70.0% [core]"}
        rows.append(_gene(f"g{i}", C1, i, "BGC001" if 5 <= i <= 8 else "", **kw))
    rows += [_gene(f"t{i}", C2, i, "BGC002" if i in (2, 3) else "") for i in range(1, 6)]
    rows += [_gene(f"n5_{i}", C5, i) for i in range(1, 4)]
    rows += [_gene(f"n7_{i}", C7, i) for i in range(1, 11)]
    rows += [_gene(f"n9_{i}", C9, i) for i in range(1, 4)]
    return rows


def _write_tsv(path, rows, cols=None):
    cols = cols or list(rows[0])
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, delimiter="\t", lineterminator="\n")   # test fixture input
        w.writeheader()
        w.writerows(rows)


def _write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")   # test fixture input
        w.writeheader()
        w.writerows(rows)


@pytest.fixture
def fx(tmp_path):
    d = tmp_path / "in"
    pkg = d / "package"
    _write_csv(pkg / f"{S}_2_inventory.csv", [
        {"BGC_ID": "BGC001", "Contig": C1, "Region": "1", "Products": "T1PKS", "Boundary": "Interior", "Length_kb": "4.0",
         "KCB_top": "BGC0000001 | alpha", "KCB_proteins": "3"},
        {"BGC_ID": "BGC002", "Contig": C2, "Region": "1", "Products": "terpene", "Boundary": "Interior",
         "Length_kb": "2.0", "KCB_top": "", "KCB_proteins": ""}])
    _write_csv(pkg / f"{S}_3_mibig_convergence.csv", [
        {"bgc_id": "BGC001", "mibig_accession": "BGC0000001", "mibig_compound": "alpha", "distinct_query_genes": "4",
         "query_gene_count_total": "4", "median_pct_identity": "61.0"},
        {"bgc_id": "BGC001", "mibig_accession": "BGC0000002", "mibig_compound": "beta", "distinct_query_genes": "2",
         "query_gene_count_total": "4", "median_pct_identity": "40.0"}])
    _write_tsv(d / "ledger" / f"{S}.tsv", _ledger(), lrp.LEDGER_COLUMNS)
    pair = d / "maps" / f"{S}_BGC001_alpha"
    _write_tsv(d / "INVENTORY.tsv", [{
        "strain": S, "bgc": "BGC001", "pair": f"{S}_BGC001_alpha", "mibig": "BGC0000001", "reference_title": "alpha cluster",
        "in_core": "4", "reference_genes": "9", "core_proteins": "4", "found_clearly_elsewhere": "2",
        "found_ambiguously": "1", "not_found": "2", "set_aside": "0", "strength": "PARTIAL",
        "png": f"maps/{S}_BGC001_alpha/map_and_table.png"}])
    _write_tsv(pair / "gap_rescue.tsv", [
        {"name": "abc1", "status": "PRESENT_IN_CORE", "best_contig": C1, "best_locus": "g6"},
        {"name": "abc2", "status": "MISSING_FOUND_CLEAR", "best_contig": C5_REWRITTEN, "best_locus": "n5_2"},
        {"name": "abc3", "status": "MISSING_NOT_FOUND", "best_contig": C9, "best_locus": "n9_2"}])
    _write_tsv(pair / "gap_rescue_split_genes.tsv", [
        {"name": "abc4", "split_call": "CLEAR", "piece1_locus": "g7", "piece1_identity_pct": "64",
         "piece1_region_identity": ID1, "piece2_locus": "n7_5", "piece2_identity_pct": "58",
         "piece2_region_identity": f"{S} / {C7} (no antiSMASH region)", "whole_gene_rival_locus": "-",
         "whole_gene_rival_identity_pct": "0"}])
    _write_tsv(d / "gecco.tsv", [{"strain": S, "contig_full": C1, "type": "Polyketide", "start": "4000", "end": "9000",
                                  "average_p": "0.95", "relation": "INSIDE_REGION"}])
    (d / "mibig").mkdir()
    (d / "mibig" / "BGC0000001.json").write_text(json.dumps({
        "compounds": [{"name": "alpha", "bioactivities": [{"name": {"activity": "antibacterial"}, "observed": True}]}],
        "taxonomy": {"name": "Streptomyces exemplar"}}))
    return d


def _argv(d, out, *extra):
    return ["--out", str(out), "--package", f"{S}={d / 'package'}", "--ledger-dir", str(d / "ledger"),
            "--gene-table-inventory", str(d / "INVENTORY.tsv"), "--gene-table-root", str(d), "--gecco", str(d / "gecco.tsv"),
            "--mibig-json", str(d / "mibig"), *extra]


def _cds(page):
    return [ln.split("|")[1].strip() for ln in page.splitlines()
            if ln.startswith("| ") and not ln.startswith("| CDS") and not ln.startswith("| Reference gene")
            and not ln.startswith("| MIBiG ") and "|" in ln and not re.match(r"\| BGC\d{7}", ln)]


def _assessment(page):
    return page.split("## Assessment", 1)[1].split("*Built by", 1)[0]


def test_rows_are_the_region_its_flanks_and_the_contigs_the_gene_table_points_to(fx, tmp_path):
    lrp.main(_argv(fx, tmp_path / "out"))
    p1 = (tmp_path / "out" / S / f"{STEM1}.md").read_text()
    rows = [r for r in _cds(p1) if re.fullmatch(r"g\d+|n\d_\d+|t\d", r)]
    assert rows == [f"g{i}" for i in range(2, 12)] + ["n5_1", "n5_2", "n5_3"] + [f"n7_{i}" for i in range(3, 8)], \
        "region g5-g8 with 3 flanks, NODE_5 (8 kb) whole, NODE_7 (90 kb) the split piece and 2 each side; not NODE_9"
    p2 = (tmp_path / "out" / S / f"{STEM2}.md").read_text()
    assert [r for r in _cds(p2) if re.fullmatch(r"t\d", r)] == ["t1", "t2", "t3", "t4", "t5"]


def test_select_rows_keeps_a_not_found_row_from_pulling_in_its_contig():
    genes = {c: [g for g in _ledger() if g["contig"] == c] for c in (C1, C9)}
    rows, order, extra = lrp.select_rows(genes, "BGC001", [{"pair": "p"}],
                                         {"p": [{"status": "MISSING_NOT_FOUND", "best_contig": C9, "best_locus": "n9_2"}]}, {})
    assert order == [C1] and not extra and all(r["contig"] == C1 for r in rows)


def test_title_carries_the_full_identity(fx, tmp_path):
    lrp.main(_argv(fx, tmp_path / "out"))
    p1 = (tmp_path / "out" / S / f"{STEM1}.md").read_text()
    assert f"# {ID1}: T1PKS" in p1.splitlines()
    log = list(csv.DictReader(open(tmp_path / "out" / "BUILD_LOG.tsv"), delimiter="\t"))
    assert {r["identity"] for r in log} == {ID1, f"{S} / {C2} / region001 / BGC002"}


def test_unsearched_layers_are_marked_and_footnoted_without_a_page_search(fx, tmp_path):
    lrp.main(_argv(fx, tmp_path / "out"))
    p1 = (tmp_path / "out" / S / f"{STEM1}.md").read_text()
    row = {r.split("|")[1].strip(): r for r in p1.splitlines() if r.startswith("| g")}
    assert "not searched †" in row["g2"] and "not searched †" in row["g3"], "never 'none' for a layer nobody searched"
    assert "| ‡ |" in row["g4"]
    assert "† Not searched for this page" in p1 and "page search not run" in p1
    assert lrp.DOUBLE_DAGGER.strip() in p1


def _stub(path, body):
    path.write_text("#!" + sys.executable + "\n" + body)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


def _search_kit(fx, tmp_path):
    """Stub hmmsearch and DIAMOND that log each call, plus the proteome, Pfam file and MIBiG protein set they need."""
    calls = tmp_path / "calls.txt"
    hmm = _stub(tmp_path / "hmmsearch", f"""import sys
open({str(calls)!r}, "a").write("hmmsearch\\n")
out = sys.argv[sys.argv.index("--domtblout") + 1]
cols = ["x"] * 23
for tag in ("g2", "g3"):
    cols[0], cols[3], cols[19], cols[20] = tag, "PKS_KS", "5", "250"
    open(out, "a").write(" ".join(cols) + "\\n")
""")
    dmd = _stub(tmp_path / "diamond", f"""import sys
open({str(calls)!r}, "a").write("diamond\\n")
out = sys.argv[sys.argv.index("-o") + 1]
open(out, "w").write("g3\\tBGC0000001|abcQ\\t72.0\\t300\\t300\\t300\\t100\\t100\\t1e-50\\t500\\n")
""")
    (fx / "faa").mkdir(exist_ok=True)
    (fx / "faa" / f"{S}.faa").write_text("".join(f">{S}|{t}|x\nMKV\n" for t in ("g2", "g3", "g9")))
    (fx / "mp").mkdir(exist_ok=True)
    (fx / "mp" / "mibig_proteins.dmnd").write_text("")
    (fx / "mp" / "mibig_proteins.tsv").write_text("id\tname\nBGC0000001|abcQ\tabcQ\n")
    (fx / "Pfam-A.hmm").write_text("")
    return calls, ["--proteomes", str(fx / "faa"), "--pfam", str(fx / "Pfam-A.hmm"), "--hmmsearch", str(hmm),
                   "--diamond", str(dmd), "--mibig-proteins", str(fx / "mp")]


def _seed_cache(out, tags, domain):
    ps = out / "_page_searches" / S
    ps.mkdir(parents=True)
    (ps / "proteins.faa").write_text("".join(f">{t}\nMKV\n" for t in tags))
    cols = ["x"] * 23
    cols[0], cols[3], cols[19], cols[20] = "g2", domain, "7", "70"
    (ps / "pfam.domtbl").write_text(" ".join(cols) + "\n")
    (ps / "mibig.tsv").write_text("")


def test_a_cache_for_another_protein_set_is_searched_again(fx, tmp_path):
    calls, kit = _search_kit(fx, tmp_path)
    out = tmp_path / "out"
    _seed_cache(out, ["g2"], "STALE_DOMAIN")          # made for a smaller set: g3 also needs a search now
    lrp.main(_argv(fx, out, *kit))                    # a folder without BUILD_LOG.tsv may be pre-seeded
    assert calls.read_text().split() == ["hmmsearch", "diamond"]
    p1 = (out / S / f"{STEM1}.md").read_text()
    assert "STALE_DOMAIN" not in p1 and "PKS_KS 5-250 †" in p1
    assert (out / "_page_searches" / S / "proteins.faa").read_text().count(">") == 2


def test_a_cache_for_the_same_protein_set_is_reused(fx, tmp_path):
    calls, kit = _search_kit(fx, tmp_path)
    out = tmp_path / "out"
    _seed_cache(out, ["g2", "g3"], "CACHED_DOMAIN")
    lrp.main(_argv(fx, out, *kit))
    assert not calls.exists(), "a cache for exactly the needed proteins is not searched again"
    assert "CACHED_DOMAIN 7-70 †" in (out / S / f"{STEM1}.md").read_text()


def test_a_contig_name_with_a_rewritten_coverage_string_still_shows_its_rows(fx, tmp_path):
    genes = {c: [g for g in _ledger() if g["contig"] == c] for c in (C1, C5)}
    rows, order, extra = lrp.select_rows(genes, "BGC001", [{"pair": "p"}], {"p": [
        {"status": "MISSING_FOUND_CLEAR", "best_contig": C5_REWRITTEN, "best_locus": "n5_2"},
        {"status": "PRESENT_IN_CORE", "best_contig": "NODE_1_length_60000_cov_10.00", "best_locus": "g6"}]}, {})
    assert order == [C1, C5], "the ledger's full name, and a rewritten core name is not an extra contig"
    assert [r["locus_tag"] for r in rows if r["contig"] == C5] == ["n5_1", "n5_2", "n5_3"]
    lrp.main(_argv(fx, tmp_path / "out"))
    p1 = (tmp_path / "out" / S / f"{STEM1}.md").read_text()
    assert all(f"| {t} |" in p1 for t in ("n5_1", "n5_2", "n5_3"))


def test_the_page_search_runs_once_per_strain_and_its_results_are_marked(fx, tmp_path):
    calls = tmp_path / "calls.txt"
    hmm = _stub(tmp_path / "hmmsearch", f"""import sys
open({str(calls)!r}, "a").write("hmmsearch\\n")
out = sys.argv[sys.argv.index("--domtblout") + 1]
cols = ["x"] * 23
for tag in ("g2", "g3"):
    cols[0], cols[3], cols[19], cols[20] = tag, "PKS_KS", "5", "250"
    open(out, "a").write(" ".join(cols) + "\\n")
""")
    dmd = _stub(tmp_path / "diamond", f"""import sys
open({str(calls)!r}, "a").write("diamond\\n")
out = sys.argv[sys.argv.index("-o") + 1]
open(out, "w").write("g3\\tBGC0000001|abcQ\\t72.0\\t300\\t300\\t300\\t100\\t100\\t1e-50\\t500\\n")
""")
    led = _ledger()                                   # both pages need a search: t1 flanks BGC002, never Pfam-searched
    next(g for g in led if g["locus_tag"] == "t1")["L2b_bind"] = "NOT_SEARCHED"
    _write_tsv(fx / "ledger" / f"{S}.tsv", led, lrp.LEDGER_COLUMNS)
    (fx / "faa").mkdir()
    (fx / "faa" / f"{S}.faa").write_text("".join(f">{S}|{t}|x\nMKV\n" for t in ("g2", "g3", "g9", "t1")))
    (fx / "mp").mkdir()
    (fx / "mp" / "mibig_proteins.dmnd").write_text("")
    (fx / "mp" / "mibig_proteins.tsv").write_text("id\tname\nBGC0000001|abcQ\tabcQ\n")
    (fx / "Pfam-A.hmm").write_text("")
    lrp.main(_argv(fx, tmp_path / "out", "--proteomes", str(fx / "faa"), "--pfam", str(fx / "Pfam-A.hmm"),
                   "--hmmsearch", str(hmm), "--diamond", str(dmd), "--mibig-proteins", str(fx / "mp")))
    assert calls.read_text().split() == ["hmmsearch", "diamond"], "one search per strain, not one per page"
    p1 = (tmp_path / "out" / S / f"{STEM1}.md").read_text()
    row = {r.split("|")[1].strip(): r for r in p1.splitlines() if r.startswith("| g")}
    assert "PKS_KS 5-250 †" in row["g2"]
    assert "abcQ (alpha, BGC0000001) 72% †" in row["g3"]
    assert lrp.DAGGER_SEARCHED.strip() in p1
    p2 = (tmp_path / "out" / S / f"{STEM2}.md").read_text()
    t1 = next(r for r in p2.splitlines() if r.startswith("| t1 |"))
    assert "| no domain at the gathering threshold † |" in t1, "searched, no Pfam domain"
    assert lrp.DAGGER_SEARCHED.strip() in p2
    assert (tmp_path / "out" / "_page_searches" / S / "proteins.faa").read_text().count(">") == 3


def test_the_automatic_summary_makes_no_compound_or_activity_claim(fx, tmp_path):
    lrp.main(_argv(fx, tmp_path / "out"))
    for stem in (STEM1, STEM2):
        a = _assessment((tmp_path / "out" / S / f"{stem}.md").read_text())
        assert "Automatic evidence summary: counts and calls only" in a
        for w in CLAIMS:
            assert w not in a.lower(), f"{stem}: '{w}' in the automatic summary"
    a1 = _assessment((tmp_path / "out" / S / f"{STEM1}.md").read_text())
    assert "4 genes in the region, 1 called core biosynthetic" in a1
    assert "the most genes matched to any MIBiG cluster is 4 of 4 (alpha)" in a1


def test_an_existing_output_or_page_is_never_overwritten(fx, tmp_path):
    out = tmp_path / "out"
    lrp.main(_argv(fx, out))
    before = (out / S / f"{STEM1}.md").read_bytes()
    with pytest.raises(SystemExit, match="never overwritten"):
        lrp.main(_argv(fx, out))
    with pytest.raises(SystemExit, match="never overwritten"):
        lrp.main(_argv(fx, out, "--bgc", "BGC001"))
    assert (out / S / f"{STEM1}.md").read_bytes() == before
    lrp.main(_argv(fx, tmp_path / "one", "--bgc", "BGC002"))       # --bgc may add a page that does not exist yet
    assert (tmp_path / "one" / S / f"{STEM2}.md").exists() and not (tmp_path / "one" / S / f"{STEM1}.md").exists()


def test_a_hand_assessment_replaces_the_automatic_summary(fx, tmp_path):
    (fx / "assess").mkdir()
    (fx / "assess" / f"{STEM1}.md").write_text("**What the genes are.** A type I PKS module set.\n- KS and AT in g6.\n")
    lrp.main(_argv(fx, tmp_path / "out", "--assessments", str(fx / "assess")))
    a1 = _assessment((tmp_path / "out" / S / f"{STEM1}.md").read_text())
    assert "A type I PKS module set." in a1 and "Automatic evidence summary" not in a1
    a2 = _assessment((tmp_path / "out" / S / f"{STEM2}.md").read_text())
    assert "Automatic evidence summary" in a2, "a page without its own assessment keeps the automatic summary"
    log = {r["bgc"]: r for r in csv.DictReader(open(tmp_path / "out" / "BUILD_LOG.tsv"), delimiter="\t")}
    assert (log["BGC001"]["hand_assessment"], log["BGC002"]["hand_assessment"]) == ("yes", "no")


def test_a_gzipped_ledger_gives_the_same_pages_as_a_ledger_folder(fx, tmp_path):
    lrp.main(_argv(fx, tmp_path / "a"))
    rows = list(csv.DictReader(open(fx / "ledger" / f"{S}.tsv"), delimiter="\t"))
    with gzip.open(fx / "ledger.tsv.gz", "wt", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=lrp.LEDGER_COLUMNS, delimiter="\t", lineterminator="\n")   # fixture input
        w.writeheader()
        w.writerows(rows)
    argv = _argv(fx, tmp_path / "b")
    argv[argv.index("--ledger-dir"):argv.index("--ledger-dir") + 2] = ["--ledger", str(fx / "ledger.tsv.gz")]
    lrp.main(argv)
    a = (tmp_path / "a" / S / f"{STEM1}.md").read_text().replace("`a`", "`b`")
    assert a == (tmp_path / "b" / S / f"{STEM1}.md").read_text()


def test_a_skipped_strain_is_logged_with_its_reason(fx, tmp_path):
    lrp.main(_argv(fx, tmp_path / "out", "--skip", f"{S}=no package for the cleaned assembly yet"))
    log = list(csv.DictReader(open(tmp_path / "out" / "BUILD_LOG.tsv"), delimiter="\t"))
    assert [r["status"] for r in log] == ["SKIPPED: no package for the cleaned assembly yet"]
    assert not (tmp_path / "out" / S).exists()


def test_the_per_gene_mibig_table_names_a_top_cluster_missing_from_the_convergence_table(fx, tmp_path):
    led = _ledger()
    hits = {"g5": ("BGC0000009|gamA", "84.0"), "g6": ("BGC0000009|gamB", "100.0"), "g7": ("BGC0000009|gamC", "90.0"),
            "g8": ("BGC0000001|abcQ", "61.0")}
    for g in led:
        if g["locus_tag"] in hits:
            g["mibig_best_hit"], g["mibig_identity"] = hits[g["locus_tag"]]
    _write_tsv(fx / "ledger" / f"{S}.tsv", led, lrp.LEDGER_COLUMNS)
    (fx / "mibig" / "BGC0000009.json").write_text(json.dumps({"compounds": [{"name": "gamma"}],
                                                              "taxonomy": {"name": "Streptomyces exemplar"}}))
    lrp.main(_argv(fx, tmp_path / "out"))
    p1 = (tmp_path / "out" / S / f"{STEM1}.md").read_text()
    sec = p1.split("## Known clusters by the per-gene MIBiG column", 1)[1].split("## Assessment", 1)[0]
    assert p1.index("## Known clusters this locus resembles") < p1.index("## Known clusters by the per-gene MIBiG column")
    assert "| BGC0000009 | gamma | 3 of 4 | 84–100% |" in sec, "count of the region's 4 genes, and the identity range"
    assert "| BGC0000001 | alpha | 1 of 4 | 61–61% |" in sec
    assert sec.index("BGC0000009") < sec.index("BGC0000001")
    assert "The top cluster here is not in the KnownClusterBlast-based table above." in sec
    p2 = (tmp_path / "out" / S / f"{STEM2}.md").read_text()
    assert "per-gene MIBiG column" not in p2, "no section when no region gene has a MIBiG hit"


def test_the_per_gene_note_follows_the_table_top_row():
    names = {"BGC0000001": "alpha", "BGC0000009": "gamma"}.get
    mibig = lambda acc: {"names": names(acc, "?")}
    conv = [{"mibig_accession": "BGC0000001"}]
    rows = [{"bgc": "BGC001", "mibig_best_hit": "BGC0000001|abcQ", "mibig_identity": "70"},
            {"bgc": "BGC001", "mibig_best_hit": "", "mibig_identity": ""},
            {"bgc": "", "mibig_best_hit": "BGC0000009|gamA", "mibig_identity": "99"}]   # a flank: not counted
    out = lrp.per_gene_clusters(rows, "BGC001", conv, mibig)
    assert "| BGC0000001 | alpha | 1 of 2 | 70–70% |" in out and not any("BGC0000009" in x for x in out)
    assert not any("not in the KnownClusterBlast" in x for x in out), "the top cluster is in the convergence table"
    tie = [rows[0], {"bgc": "BGC001", "mibig_best_hit": "BGC0000009|gamA", "mibig_identity": "95"}]
    out = lrp.per_gene_clusters(tie, "BGC001", conv, mibig)
    table = [x for x in out if x.startswith("| BGC")]
    assert table[0].startswith("| BGC0000009 "), "a tie on count goes to the higher identity"
    assert any("not in the KnownClusterBlast" in x for x in out), "the note is about the table's top row"
    assert not any("not in the KnownClusterBlast" in x for x in lrp.per_gene_clusters(tie, "BGC001", [], mibig)), \
        "no note when there is no convergence table"


def test_a_strong_table_with_few_biosynthetic_genes_in_the_core_is_flagged(fx, tmp_path):
    pair = fx / "maps" / f"{S}_BGC001_alpha"
    gr = [("abc1", "biosynthetic", "PRESENT_IN_CORE", C1, "g6"),
          ("abc2", "biosynthetic-additional", "MISSING_FOUND_CLEAR", C5_REWRITTEN, "n5_2"),
          ("abc3", "biosynthetic-additional", "MISSING_NOT_FOUND", C9, "n9_2"),
          ("abc4", "biosynthetic", "MISSING_FOUND_AMBIGUOUS", C7, "n7_5"),   # a CLEAR split with a piece in the core
          ("abc5", "biosynthetic", "MISSING_NOT_FOUND", C9, "n9_1"),
          ("o1", "other", "PRESENT_IN_CORE", C1, "g5"), ("o2", "other", "PRESENT_IN_CORE", C1, "g7"),
          ("o3", "other", "PRESENT_IN_CORE", C1, "g8"), ("r1", "regulatory", "MISSING_NOT_FOUND", C9, "n9_3")]
    _write_tsv(pair / "gap_rescue.tsv", [{"name": n, "reference_gene_kind": k, "status": s, "best_contig": c, "best_locus": lk}
                                         for n, k, s, c, lk in gr])
    inv = list(csv.DictReader(open(fx / "INVENTORY.tsv"), delimiter="\t"))
    for strength in ("STRONG", "PARTIAL"):
        inv[0]["strength"] = strength
        _write_tsv(fx / "INVENTORY.tsv", inv)
        lrp.main(_argv(fx, tmp_path / strength))
    line = {s: next(x for x in (tmp_path / s / S / f"{STEM1}.md").read_text().splitlines() if "By MIBiG gene kind" in x)
            for s in ("STRONG", "PARTIAL")}
    expect = ("  - By MIBiG gene kind, reference genes present in the core: biosynthetic 2 of 3; biosynthetic-additional 0 of 2; "
              "other 3 of 3; regulatory 0 of 1. Biosynthetic (core and additional): **2 of 5**")
    assert line["STRONG"] == expect + " — fewer than half, although the table is STRONG."
    assert line["PARTIAL"] == expect + ".", "the warning is for STRONG tables only"
    assert "By MIBiG gene kind" not in (tmp_path / "STRONG" / S / f"{STEM2}.md").read_text()


def test_the_tool_carries_no_workspace_path_or_strain_id():
    src = (ROOT / "tools" / "locus_reading_pages.py").read_text()
    assert not re.search(r"/Users/[^/\s]+/|/home/[^/\s]+/", src)
    assert not re.search(r"\bAS-\d+", src)
