"""cohort_enzyme_catalog BLASTp binding: protein hashes use the shared normalization, a name match that the query index
contradicts is held, identical proteins under two names are not a conflict, and the shown hit comes from the same
file as the value. Synthetic fixtures only."""
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cohort_enzyme_catalog as cec  # noqa: E402
from test_465_cohort_enzyme_catalog import cohort, read  # noqa: E402,F401

HEAD = "strain,gene,hit_rank,subject_acc,subject_organism,subject_def,pct_identity\n"
QI = "strain\tgene\tsource_file\tprotein_sha256\tquery_aa_length\tbinding_evidence\n"
GV = "strain\tgene\tchannel\ttop1_identity\ttop10_mean_identity\thits_used\tranks_from_disk\tsource_file\n"


def sha(s):
    return hashlib.sha256(s.upper().rstrip("*").encode()).hexdigest()


def faa_seq(root, strain, tag):
    rec = [r for r in (root / strain / "package" / f"{strain}_proteins.faa").read_text().split(">") if r.startswith(tag)]
    return "".join(rec[0].splitlines()[1:])


def genes(root, out):
    return {r["locus_tag"]: r for r in read(root / out / "ENZYME_GENES.tsv")}


def test_lowercase_and_stop_codon_fasta_still_binds_by_sequence(cohort):
    root, gt, gv = cohort
    faa = root / "X-2" / "package" / "X-2_proteins.faa"
    seq = faa_seq(root, "X-2", "b2")
    faa.write_text(faa.read_text().replace(seq, seq.lower() + "*"))
    (root / "res" / "old.csv").write_text(HEAD + "X-2,old_7,1,WP_OLD,Streptomyces sp. O,old hit,93\n")
    (root / "gv.tsv").write_text(GV + "X-2\tb2\tncbi_clustered_nr\t93\t91.0\t10\t\tres/old.csv\n")
    (root / "qi.tsv").write_text(QI + f"X-2\told_7\tres/old.csv\t{sha(seq)}\t9\tledger_sha\n")
    cec.build(gt, root, root / "o", root / "gv.tsv", query_index=root / "qi.tsv")
    assert genes(root, "o")["b2"]["top_hit_acc"] == "WP_OLD"


def test_a_name_match_contradicted_by_the_index_is_held(cohort):
    root, gt, gv = cohort
    # the file's query "b2" is indexed as another protein: an old assembly reused the tag
    (root / "res" / "b2.csv").write_text(HEAD + "X-2,b2,1,WP_WRONG,Other sp.,x,99\n")
    (root / "gv.tsv").write_text(GV + "X-2\tb2\tncbi_clustered_nr\t99\t98.0\t10\t\tres/b2.csv\n")
    (root / "qi.tsv").write_text(QI + f"X-2\tb2\tres/b2.csv\t{sha('MOTHERPROTEIN')}\t13\tledger_sha\n")
    info = cec.build(gt, root, root / "o", root / "gv.tsv", query_index=root / "qi.tsv")
    g = genes(root, "o")["b2"]
    assert (g["blastp_top10_mean"], g["top_hit_acc"]) == ("", "") and "different protein" in g["blastp_hold"]
    assert info["blastp_rows_dropped_index_conflict"] == 1


def test_sequence_evidence_wins_over_a_reused_tag(cohort):
    root, gt, gv = cohort
    seq = faa_seq(root, "X-2", "b2")
    (root / "res" / "two.csv").write_text(HEAD + "X-2,b2,1,WP_TARGET,T sp.,t,90\nX-2,OTHER,1,WP_OTHER,O sp.,o,80\n")
    (root / "gv.tsv").write_text(GV + "X-2\tb2\tncbi_clustered_nr\t90\t88.0\t10\t\tres/two.csv\n")
    (root / "qi.tsv").write_text(QI + f"X-2\tOTHER\tres/two.csv\t{sha(seq)}\t9\tledger_sha\n")
    info = cec.build(gt, root, root / "o", root / "gv.tsv", query_index=root / "qi.tsv")
    # the file's query OTHER carries this gene's protein; its tag b2 names another protein in the file
    assert genes(root, "o")["b2"]["top_hit_acc"] == "WP_OTHER" and info["genes_bound_by_sequence_alias"] == 1


def test_identical_proteins_under_two_names_are_not_a_conflict(cohort):
    root, gt, gv = cohort
    seq = faa_seq(root, "X-2", "b2")
    (root / "res" / "dup.csv").write_text(HEAD + "X-2,b1,1,WP_DUP,D sp.,d,99\nX-2,b2,1,WP_DUP,D sp.,d,99\n")
    (root / "gv.tsv").write_text(GV + "X-2\tb2\tncbi_clustered_nr\t99\t97.0\t10\t\tres/dup.csv\n")
    # both names indexed with the same sequence; read_query_index keeps only the first name per hash
    (root / "qi.tsv").write_text(QI + f"X-2\tb1\tres/dup.csv\t{sha(seq)}\t9\tledger_sha\n"
                                      f"X-2\tb2\tres/dup.csv\t{sha(seq)}\t9\tledger_sha\n")
    info = cec.build(gt, root, root / "o", root / "gv.tsv", query_index=root / "qi.tsv")
    g = genes(root, "o")["b2"]
    assert (g["blastp_top10_mean"], g["top_hit_acc"], g["blastp_hold"]) == ("97.0", "WP_DUP", "")
    assert info["blastp_rows_dropped_index_conflict"] == 0


def test_value_and_hit_come_from_the_same_file(cohort):
    root, gt, gv = cohort
    (root / "res" / "low.csv").write_text(HEAD + "X-2,b2,1,WP_LOW,L sp.,l,70\n")
    (root / "gv.tsv").write_text(GV + "X-2\tb2\tncbi_nr\t95\t94.0\t10\t\tres/missing.csv\n"
                                      "X-2\tb2\tncbi_clustered_nr\t70\t65.0\t10\t\tres/low.csv\n")
    cec.build(gt, root, root / "o", root / "gv.tsv")
    g = genes(root, "o")["b2"]
    # the highest value's file is unreadable, so no hit is shown beside it; the lower file's hit is not borrowed
    assert (g["blastp_top10_mean"], g["top_hit_acc"]) == ("94.0", "")
