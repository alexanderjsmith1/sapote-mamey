"""tools/blastp_identity_figures.py: the bee paper's two BLASTp identity figures, drawn from a genome table.

The owner, 12 Oct 2026: the moss BLASTp figure must be identical to the bee paper's, and the top-10 mean is the novelty
measure. The figures lived only as paper scripts; this card makes them one bundle tool. A tiny fixture redraws both layouts.
"""
import csv
import importlib.util
import json
import sqlite3
import statistics
import sys
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mamey.blastp_ingest import BLASTP_HITS_SCHEMA  # noqa: E402

spec = importlib.util.spec_from_file_location("blastp_identity_figures_451", ROOT / "tools/blastp_identity_figures.py")
bif = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bif)

DISK_RANKS = [95.0, 90.0, 85.0, 80.0, 75.0, 70.0, 65.0, 60.0, 55.0, 50.0]
CLNR_RANKS = [88.0, 86.0, 84.0, 82.0, 80.0, 78.0, 76.0, 74.0, 72.0, 70.0]
CSV_COLS = ["strain", "bgc_id", "gene", "aa_length", "role", "domains", "hit_rank", "subject_acc", "subject_organism",
            "subject_def", "pct_identity", "align_length", "query_coverage", "evalue", "bitscore", "pct_positives"]


def _csv(path, strain, gene, ranks):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_COLS); w.writeheader()
        for i, pid in enumerate(ranks, 1):
            w.writerow(dict.fromkeys(CSV_COLS, "") | {"strain": strain, "bgc_id": "B1", "gene": gene, "hit_rank": i,
                                                       "subject_acc": f"WP_{i}", "pct_identity": pid})


def _store(path, rows):
    con = sqlite3.connect(path)
    cols = ", ".join(f"{n} {t}{' NOT NULL' if nn else ''}" for n, t, nn in BLASTP_HITS_SCHEMA)
    con.execute(f"CREATE TABLE hits ({cols})")
    names = [c[0] for c in BLASTP_HITS_SCHEMA]
    for r in rows:
        full = dict.fromkeys(names) | {"workspace": "claude", "bgc_id": "B1", "provenance_suspect": 0} | r
        con.execute(f"INSERT INTO hits ({', '.join(names)}) VALUES ({', '.join('?' * len(names))})", [full[n] for n in names])
    con.commit(); con.close()


def _context(path, tags):
    path.parent.mkdir(parents=True, exist_ok=True)
    cds = [{"locus_tag": t, "gene_kind": "biosynthetic" if fn else "other", "gene_functions": fn} for t, fn in tags]
    path.write_text(json.dumps({"cds": cds}) + "\n")


@pytest.fixture
def world(tmp_path):
    root = tmp_path / "ws"
    # S1: ctg1_1 nr, store holds rank 1 only, the CSV on disk holds 10; ctg1_2 ClusteredNR, 10 ranks in the store;
    # ctg1_3 no hit. S2: ctg2_1 nr rank 1 only (no CSV on disk); ctg2_2 only in an extra (not ingested) CSV.
    _csv(root / "res/s1_nr.csv", "S1", "ctg1_1", DISK_RANKS)
    _csv(root / "lane/results/S2/p1/p1_blastp_top10_clustered.csv", "S2", "ctg2_2", CLNR_RANKS)
    rows = [dict(strain="S1", gene="ctg1_1", channel="ncbi_nr", hit_rank=1, pct_identity=95.0, source_file="res/s1_nr.csv")]
    rows += [dict(strain="S1", gene="ctg1_2", channel="ncbi_clustered_nr", hit_rank=i, pct_identity=p, source_file="res/s1_cl.csv")
             for i, p in enumerate(CLNR_RANKS, 1)]
    rows += [dict(strain="S2", gene="ctg2_1", channel="ncbi_nr", hit_rank=1, pct_identity=60.0, source_file="res/gone.csv")]
    _store(tmp_path / "snap.sqlite", rows)
    _context(root / "pk/S1.jsonl", [("ctg1_1", "biosynthetic (rule-based-clusters) T1PKS: PKS_KS"), ("ctg1_2", ""), ("ctg1_3", "")])
    _context(root / "pk/S2.jsonl", [("ctg2_1", "biosynthetic (rule-based-clusters) NRPS: Condensation"), ("ctg2_2", "")])
    g = tmp_path / "genomes.tsv"
    g.write_text("strain\tgenus\tblock\tgene_context\nS1\tKribbella\tIsolates\tpk/S1.jsonl\n"
                 "S2\tStreptomyces\tComparators\tpk/S2.jsonl\n")
    return dict(root=root, store=tmp_path / "snap.sqlite", genomes=g, tmp=tmp_path)


def _run(w, out, *extra):
    return bif.main(["--genomes", str(w["genomes"]), "--store", str(w["store"]), "--root", str(w["root"]), "--out", str(out),
                     "--extra-csv", "lane/results/*/*/*_blastp_top10_clustered.csv", "--binding", "locus_tag", *extra])


def _values(out):
    return {(r["strain"], r["gene"], r["channel"]): r for r in csv.DictReader(open(out / "GENE_VALUES.tsv"), delimiter="\t")}


def test_both_layouts_are_drawn_stamped_and_numbered(world):
    out = world["tmp"] / "out"
    assert _run(world, out) == 0
    for stem in ("BLASTP_IDENTITY_BY_GENOME", "BLASTP_IDENTITY_BY_CLASS"):
        png = out / f"{stem}.png"
        assert png.stat().st_size > 1000 and (out / f"{stem}.pdf").exists() and (out / f"{stem}_numbers.tsv").exists()
        assert b"Sapote-Mamey blastp_identity_figures" in png.read_bytes()
    info = json.loads((out / "RUN_INFO.json").read_text())
    assert info["genes_with_value"] == 4 and info["measure"] == "top10" and info["extra_csvs"] == 1


def test_top10_mean_reads_missing_ranks_from_the_csv_on_disk(world):
    out = world["tmp"] / "out"
    _run(world, out)
    v = _values(out)
    assert float(v[("S1", "ctg1_1", "ncbi_nr")]["top10_mean_identity"]) == pytest.approx(statistics.mean(DISK_RANKS))
    assert v[("S1", "ctg1_1", "ncbi_nr")]["ranks_from_disk"] == "yes" and v[("S1", "ctg1_1", "ncbi_nr")]["hits_used"] == "10"
    assert v[("S2", "ctg2_1", "ncbi_nr")]["hits_used"] == "1"          # no CSV on disk: the store's rank 1 is all there is
    assert float(v[("S2", "ctg2_2", "ncbi_clustered_nr")]["top10_mean_identity"]) == pytest.approx(statistics.mean(CLNR_RANKS))
    rows = [r for r in csv.reader(open(out / "BLASTP_IDENTITY_BY_GENOME_numbers.tsv"), delimiter="\t") if r and r[0] != "block"
            and not r[0].startswith("#")]
    s1 = next(r for r in rows if r[1] == "S1")
    assert s1[3] == "2" and s1[4] == "3"                                 # 2 of 3 region genes have a value


def test_top1_and_single_database_options(world):
    out1, out2 = world["tmp"] / "top1", world["tmp"] / "nr"
    _run(world, out1, "--measure", "top1")
    _run(world, out2, "--db", "nr")
    g1 = {r[1]: r for r in csv.reader(open(out1 / "BLASTP_IDENTITY_BY_GENOME_numbers.tsv"), delimiter="\t") if len(r) > 5}
    assert g1["S1"][5] == "91.5"                                         # true median of 95 (nr top hit) and 88 (ClusteredNR)
    v = _values(out2)
    assert all(k[2] == "ncbi_nr" for k in v) and len(v) == 2


def test_class_figure_counts_core_genes_by_their_own_rule(world):
    out = world["tmp"] / "out"
    _run(world, out)
    rows = {(r[0], r[1]): r for r in csv.reader(open(out / "BLASTP_IDENTITY_BY_CLASS_numbers.tsv"), delimiter="\t")}
    assert rows[("PKS", "S1")][3:5] == ["1", "1"] and rows[("NRPS", "S2")][3:5] == ["1", "1"]
    assert bif.gene_classes("biosynthetic (rule-based-clusters) lanthipeptide-class-i: LanB") == {"RiPP"}


def test_existing_outputs_are_never_overwritten(world):
    out = world["tmp"] / "out"
    _run(world, out)
    with pytest.raises(SystemExit):
        _run(world, out)


def test_colours_come_from_the_bundle_palette_file():
    d = json.loads(bif.PALETTE.read_text())
    assert bif.genus_colours()["Streptomyces"] == d["default"]["Streptomyces"]
    assert bif.genus_colours("moss")["Streptomyces"] == d["sets"]["moss"]["Streptomyces"]
    assert bif.genus_colours()["Peterkaempfera"] == "#16504C"
    assert bif.genus_colours()["No such genus"] == d["fallback"]
    with pytest.raises(SystemExit):
        bif.genus_colours("no-such-set")
    src = (ROOT / "tools/blastp_identity_figures.py").read_text()
    assert "GENUS_COLOURS" not in src and "colours.get(" not in src
