"""A Swiss-Prot top-10 table has up to ten rows per gene. ingest-blastp-trove kept the LAST row, so the
overlay showed rank 10 as the gene's hit. Within one source file the lowest hit_rank must win; without a
rank column the first row (BLAST's best-first order) wins."""
import csv

from mamey.blastp_ingest import ingest_blastp_trove

HEAD = ("strain,bgc_id,gene,aa_length,role,domains,hit_rank,subject_acc,subject_organism,subject_def,"
        "pct_identity,align_length,query_coverage,evalue,bitscore,pct_positives,subject_db\n")


def _package(tmp_path):
    pkg = tmp_path / "package"; pkg.mkdir()
    (pkg / "manifest.json").write_text('{"strain_id":"AS-999","taxonomy":"Streptomyces sp."}')
    (pkg / "AS-999_gene_context.jsonl").write_text(
        '{"bgc_id":"BGC001","cds":[{"locus_tag":"ctg1_1","aa_length":300}]}\n')
    return pkg


def _row(rank, acc, pid):
    return (f"AS-999,BGC001,ctg1_1,300,core,,{rank},{acc},Bacillus subtilis,enzyme {acc},{pid},290,97,"
            f"1e-{60 - rank},{200 - rank},50,swissprot\n")


def _overlay(pkg):
    return list(csv.DictReader((pkg / "blastp_online" / "BGC001_online_blastp.csv").open()))


def test_rank_one_wins_over_later_rows(tmp_path):
    pkg = _package(tmp_path)
    d = tmp_path / "trove" / "BGC001"; d.mkdir(parents=True)
    (d / "BGC001_blastp_top10_local.csv").write_text(HEAD + "".join(_row(k, f"P{k:05d}", 60 - k) for k in range(1, 11)))
    ingest_blastp_trove(pkg, tmp_path / "trove", "swissprot")
    rows = _overlay(pkg)
    assert len(rows) == 1 and rows[0]["blastp_accession"] == "P00001"


def test_rank_one_wins_when_rows_arrive_out_of_order(tmp_path):
    pkg = _package(tmp_path)
    d = tmp_path / "trove" / "BGC001"; d.mkdir(parents=True)
    (d / "BGC001_blastp_top10_local.csv").write_text(HEAD + _row(3, "P00003", 40) + _row(1, "P00001", 55) + _row(2, "P00002", 50))
    ingest_blastp_trove(pkg, tmp_path / "trove", "swissprot")
    assert _overlay(pkg)[0]["blastp_accession"] == "P00001"


def test_without_a_rank_column_the_first_row_wins(tmp_path):
    pkg = _package(tmp_path)
    d = tmp_path / "trove" / "BGC001"; d.mkdir(parents=True)
    (d / "BGC001_top_hit_per_gene.csv").write_text(
        "strain,bgc_id,gene,aa_length,subject_acc,subject_organism,pident\n"
        "AS-999,BGC001,ctg1_1,300,WP_FIRST,Bacillus subtilis,80\n"
        "AS-999,BGC001,ctg1_1,300,WP_SECOND,Bacillus subtilis,70\n")
    ingest_blastp_trove(pkg, tmp_path / "trove", "nr")
    assert _overlay(pkg)[0]["blastp_accession"] == "WP_FIRST"
