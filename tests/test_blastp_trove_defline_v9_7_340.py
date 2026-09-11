"""TROVE-01 (v9.7.340): _gene_from_query must recover ctg<N>_<M> from a pipe-defline WITHOUT gene=,
not return the whole defline (which fragmented the per-gene merge in ingest-blastp-trove)."""
from mamey.blastp_ingest import _gene_from_query, ingest_blastp_trove, blastp_status


def test_gene_equals_fast_path_unchanged():
    # standard panels carry gene= — must be byte-identical to before the fix
    assert _gene_from_query("AS-705|BGC004|gene=ctg66_8|aa=420") == "ctg66_8"
    assert _gene_from_query("something|gene=ctg1_1|x") == "ctg1_1"


def test_pipe_defline_without_gene_recovers_locus():
    # the trove format ingest-blastp-trove introduces — the bug the card is about
    assert _gene_from_query("AS-421|BGC041|ctg66_8|3116") == "ctg66_8"
    assert _gene_from_query("AS-421 BGC041 ctg162_3 3116") == "ctg162_3"
    assert _gene_from_query("ctg9_12") == "ctg9_12"


def test_node_header_without_locus_returned_unchanged():
    # a NODE_..._length_..._cov_... header has no ctg<N>_<M>; must NOT be mis-parsed
    node = "NODE_5_length_204811_cov_34.08"
    assert _gene_from_query(node) == node


def test_trove_ingest_channel_and_status(tmp_path):
    # a minimal package + one-BGC trove: ingest tags the channel, status reports it
    pkg = tmp_path / "package"; pkg.mkdir()
    (pkg / "manifest.json").write_text('{"strain_id":"AS-999","taxonomy":"Streptomyces sp."}')
    (pkg / "AS-999_gene_context.jsonl").write_text(
        '{"bgc_id":"BGC001","cds":[{"locus_tag":"ctg1_1","aa_length":300}]}\n')
    trove = tmp_path / "trove" / "BGC001"; trove.mkdir(parents=True)
    (trove / "BGC001_top_hit_per_gene.csv").write_text(
        "strain,bgc_id,gene,subject_acc,subject_organism,pident,qcovs,evalue,bitscore,aa\n"
        "AS-999,BGC001,ctg1_1,WP_1,Streptomyces coelicolor,72.0,98,1e-40,150,300\n")
    res = ingest_blastp_trove(pkg, tmp_path / "trove", "nr")
    assert res["channel"] == "nr" and res["genes"] == 1
    st = blastp_status(pkg)
    assert st and st[0]["bgc"] == "BGC001" and "nr" in st[0]["channels"] and st[0]["armed"]


def test_channel_precedence_nr_beats_ebi(tmp_path):
    pkg = tmp_path / "package"; pkg.mkdir()
    (pkg / "manifest.json").write_text('{"strain_id":"AS-999"}')
    (pkg / "AS-999_gene_context.jsonl").write_text(
        '{"bgc_id":"BGC001","cds":[{"locus_tag":"ctg1_1","aa_length":300}]}\n')
    def _trove(dirn, org, pid):
        d = tmp_path / dirn / "BGC001"; d.mkdir(parents=True)
        (d / "BGC001_top_hit_per_gene.csv").write_text(
            f"strain,bgc_id,gene,aa_length,subject_organism,pident\n"
            f"AS-999,BGC001,ctg1_1,300,{org},{pid}\n")
        return tmp_path / dirn
    ingest_blastp_trove(pkg, _trove("ebi", "Org EBI", "50"), "ebi")
    ingest_blastp_trove(pkg, _trove("nr", "Org NR", "90"), "nr")   # higher precedence wins
    import csv
    row = next(csv.DictReader((pkg / "blastp_online" / "BGC001_online_blastp.csv").open()))
    assert row["channel"] == "nr" and row["blastp_organism"] == "Org NR"
