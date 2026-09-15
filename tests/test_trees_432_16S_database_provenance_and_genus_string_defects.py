"""TREES_432_16S_database_provenance_and_genus_string_defects — (1) the fetch writes the record's
OWN metadata with a metadata_source label and replaces a harvested genus with the deposited
ORGANISM genus; (2) the builder splits glued 'Genusepithet' PDF titles and repairs stored ones;
(3) the read-only validator reports both defect classes on an existing store. No network."""
import io
import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import phylo_16s_build_db as build  # noqa: E402
import phylo_16s_fetch as fetch  # noqa: E402
import phylo_16s_validate_db as validate  # noqa: E402


def _rec(acc, definition, binomial, genus, source="pdf_candidate", designation="X", seq=None):
    return (acc.split(".")[0], acc, source, definition, binomial, genus, designation, "[]", None,
            seq, len(seq) if seq else None, None, "fixture", 0)


def _db(tmp_path, rows):
    db = tmp_path / "in.sqlite"
    with sqlite3.connect(db) as con:
        con.executescript(build.SCHEMA)
        for r in rows:
            build.upsert(con, [r], r[2])
    return db


def _gb(acc="MT760633.1", organism="Streptomyces zaomyceticus", seq="ACGT" * 150):
    from Bio import SeqIO
    from Bio.Seq import Seq
    from Bio.SeqRecord import SeqRecord
    from Bio.SeqFeature import SeqFeature, SimpleLocation
    rec = SeqRecord(Seq(seq), id=acc, name=acc.split(".")[0],
                    description=f"{organism} strain JCM 4864 16S ribosomal RNA gene, partial sequence")
    rec.annotations = {"molecule_type": "DNA", "accessions": [acc.split(".")[0]],
                       "sequence_version": int(acc.split(".")[1]), "organism": organism,
                       "taxonomy": ["Bacteria", "Actinomycetota"]}
    rec.features = [SeqFeature(SimpleLocation(0, len(seq)), type="source", qualifiers={
        "organism": [organism], "strain": ["JCM 4864"], "isolation_source": ["soil"],
        "geo_loc_name": ["Japan: Tokyo"]})]
    out = io.StringIO(); SeqIO.write(rec, out, "genbank"); return out.getvalue()


# ---- split rule -------------------------------------------------------------------------------
def test_split_requires_more_frequent_known_genus_and_long_epithet():
    known = {"Streptomyces": 50, "Streptomyceszaomyceticus": 3, "Kribbella": 4, "Nocardia": 9}
    assert build.split_concatenated_genus("Streptomyceszaomyceticus", known) == ("Streptomyces", "zaomyceticus")
    assert build.split_concatenated_genus("Kribbellakoreensis", known) == ("Kribbella", "koreensis")
    assert build.split_concatenated_genus("Streptomyces", known) == ("Streptomyces", "")
    assert build.split_concatenated_genus("Nocardiasp", known) == ("Nocardiasp", "")      # epithet < 4
    assert build.split_concatenated_genus("Nocardiopsis", {"Nocardia": 1, "Nocardiopsis": 9}) == ("Nocardiopsis", "")
    assert build.split_concatenated_genus("Micromonospora", known) == ("Micromonospora", "")  # no known prefix
    assert build.split_concatenated_genus("Streptomyceszaomyceticus", {"Streptomyces": 3, "Streptomyceszaomyceticus": 3}) \
        == ("Streptomyceszaomyceticus", "")   # equal frequency: not split (strictly more frequent required)
    assert build.split_concatenated_genus("", known) == ("", "")


def test_genuine_genus_more_frequent_than_prefix_is_kept():
    # 'Actinomadura' starts with 'Actino' but is the real genus and the more frequent string.
    assert build.split_concatenated_genus("Actinomadura", {"Actino": 1, "Actinomadura": 30}) == ("Actinomadura", "")


def test_binomial_corroboration_blocks_real_taxa():
    # Nostocoides is a real genus; the frequency rule alone would split it as Nostoc + oides.
    known = {"Nostoc": 40, "Nostocoides": 5, "Streptomyces": 50, "Streptomyceszaomyceticus": 3}
    binoms = {"Streptomyces zaomyceticus", "Nostoc commune"}
    assert build.split_concatenated_genus("Nostocoides", known) == ("Nostoc", "oides")            # candidate only
    assert build.split_concatenated_genus("Nostocoides", known, binoms) == ("Nostocoides", "")    # not corroborated
    assert build.split_concatenated_genus("Streptomyceszaomyceticus", known, binoms) == ("Streptomyces", "zaomyceticus")


# ---- builder: PDF ingest and repair pass ----------------------------------------------------------
def test_pdf_ingest_splits_glued_title_when_genus_is_known(tmp_path, monkeypatch):
    hits = tmp_path / "hits.tsv"
    hits.write_text("strain\taccession\tpct_identity\tsubject\tsubject_len\n"
                    "AS-1\tMT760633.1\t99.1\tStreptomyceszaomyceticus strain JCM 4864\t1450\n"
                    "AS-1\tKF667497.1\t99.7\tActinomadurabarringtoniae strain GKU 128\t1400\n"
                    "AS-1\tAB000001.1\t98.0\tNovelgenusnobody strain Q\t1400\n", encoding="utf-8")
    monkeypatch.setattr(build, "PDFHITS", str(hits))
    con = sqlite3.connect(":memory:"); con.executescript(build.SCHEMA)
    # RefSeq (ingested first) knows the genera and 'Streptomyces zaomyceticus'; it does NOT know
    # 'Actinomadura barringtoniae', so that PDF title stays as harvested until the fetch.
    for i, (binom, genus) in enumerate([("Streptomyces zaomyceticus", "Streptomyces"), ("Streptomyces lividans", "Streptomyces"),
                                        ("Actinomadura madurae", "Actinomadura"), ("Actinomadura rubra", "Actinomadura")]):
        build.upsert(con, [_rec(f"NR_00000{i}.1", f"{binom} strain S{i} 16S", binom, genus, "refseq_type", f"S{i}")],
                     "refseq_type")
    assert build.ingest_pdf_candidates(con) == (3, 3)
    got = dict(con.execute("SELECT acc_base, genus||'|'||binomial FROM record WHERE source='pdf_candidate'"))
    assert got["MT760633"] == "Streptomyces|Streptomyces zaomyceticus"
    assert got["KF667497"].startswith("Actinomadurabarringtoniae|")      # candidate, uncorroborated: untouched
    assert got["AB000001"].startswith("Novelgenusnobody|")               # unknown prefix: untouched
    repairs = dict(con.execute("SELECT strain_uid, value FROM strain_meta WHERE key='title_repair'"))
    assert repairs == {"REC:MT760633": "Streptomyceszaomyceticus -> Streptomyces zaomyceticus"}


def test_repair_pass_splits_stored_genus_only_when_definition_agrees():
    con = sqlite3.connect(":memory:"); con.executescript(build.SCHEMA)
    rows = [_rec("NR_000001.1", "Kribbella flavida strain A 16S", "Kribbella flavida", "Kribbella",
                 "refseq_type", "A"),
            _rec("NR_000003.1", "Kribbella alba strain C 16S", "Kribbella alba", "Kribbella",
                 "refseq_type", "C"),
            _rec("NR_000004.1", "Kribbella solani strain D 16S", "Kribbella solani", "Kribbella",
                 "refseq_type", "D"),
            _rec("AY253865.1", "Kribbella koreensis strain LM161 16S", "Kribbellakoreensis",
                 "Kribbellakoreensis", designation="LM161"),
            _rec("AY000009.1", "Hongia koreensis strain Z 16S", "Kribbellakoreensis",
                 "Kribbellakoreensis", designation="Z"),
            # a real genus that the frequency rule would split (Nostoc + oides): no corroboration -> held
            _rec("NR_000020.1", "Nostoc commune strain N1 16S", "Nostoc commune", "Nostoc", "refseq_type", "N1"),
            _rec("NR_000021.1", "Nostoc punctiforme strain N2 16S", "Nostoc punctiforme", "Nostoc", "refseq_type", "N2"),
            _rec("NR_000022.1", "Nostocoides limicola strain N3 16S", "Nostocoides limicola", "Nostocoides",
                 "refseq_type", "N3")]
    for r in rows:
        build.upsert(con, [r], r[2])
    assert build.repair_concatenated_genus(con) == (1, 2)
    assert con.execute("SELECT genus, binomial FROM record WHERE acc_base='AY253865'").fetchone() == \
        ("Kribbella", "Kribbella koreensis")
    assert con.execute("SELECT genus FROM record WHERE acc_base='AY000009'").fetchone() == ("Kribbellakoreensis",)
    assert con.execute("SELECT genus FROM record WHERE acc_base='NR_000022'").fetchone() == ("Nostocoides",)
    assert con.execute("SELECT value, source FROM strain_meta WHERE strain_uid='REC:AY253865'").fetchone() == \
        ("Kribbellakoreensis|Kribbellakoreensis -> Kribbella|Kribbella koreensis", "concatenated_genus_split")


# ---- fetch: own-record provenance and deposited genus ------------------------------------------
def test_fetch_labels_own_metadata_and_replaces_harvested_genus(tmp_path, monkeypatch):
    db = _db(tmp_path, [_rec("MT760633.1", "Streptomyceszaomyceticus strain JCM 4864",
                             "Streptomyceszaomyceticus", "Streptomyceszaomyceticus")])
    monkeypatch.setattr(fetch, "fetch_batch", lambda ids: _gb())
    monkeypatch.setattr(fetch.time, "sleep", lambda x: None)
    out = tmp_path / "out.sqlite"
    assert fetch.main(["--db", str(db), "--out-db", str(out), "--no-cache"]) == 0
    with sqlite3.connect(out) as con:
        row = con.execute("SELECT genus, binomial, metadata_source, isolation_source, geo_loc_name "
                          "FROM record WHERE acc_base='MT760633'").fetchone()
    assert row == ("Streptomyces", "Streptomyces zaomyceticus", "record_source_feature:MT760633.1",
                   "soil", "Japan: Tokyo")


def test_organism_binomial_never_guesses():
    assert fetch.organism_binomial("Streptomyces zaomyceticus") == ("Streptomyces zaomyceticus", "Streptomyces")
    assert fetch.organism_binomial("Micromonospora sp. LHW63014") == ("Micromonospora sp.", "Micromonospora")
    assert fetch.organism_binomial("[Clostridium] cellulosi") == ("", "")
    assert fetch.organism_binomial("uncultured bacterium") == ("", "")
    assert fetch.organism_binomial(None) == ("", "")


def test_ensure_columns_adds_metadata_source():
    con = sqlite3.connect(":memory:"); con.executescript(build.SCHEMA)
    fetch.ensure_columns(con)
    assert "metadata_source" in {r[1] for r in con.execute("PRAGMA table_info(record)")}


# ---- validator: read-only, both classes --------------------------------------------------------
@pytest.fixture
def defective_store(tmp_path):
    db = tmp_path / "store.sqlite"
    with sqlite3.connect(db) as con:
        con.executescript(build.SCHEMA)
        fetch.ensure_columns(con)
        rows = [_rec("NR_024839.1", "Saccharopolyspora spinosa strain DSM 44228 16S", "Saccharopolyspora spinosa",
                     "Saccharopolyspora", "refseq_type", "DSM 44228"),
                _rec("NR_000010.1", "Saccharopolyspora erythraea strain E 16S", "Saccharopolyspora erythraea",
                     "Saccharopolyspora", "refseq_type", "E"),
                _rec("NR_000011.1", "Saccharopolyspora hirsuta strain H 16S", "Saccharopolyspora hirsuta",
                     "Saccharopolyspora", "refseq_type", "H"),
                _rec("MT760633.1", "Saccharopolyspora gregorii strain G 16S", "Saccharopolysporagregorii",
                     "Saccharopolysporagregorii", designation="G"),
                _rec("MT760634.1", "Saccharopolyspora gregorii strain G2 16S", "Saccharopolysporagregorii",
                     "Saccharopolysporagregorii", designation="G2")]
        for r in rows:
            build.upsert(con, [r], r[2])
        con.execute("UPDATE record SET country='China', geo_loc_name='China: Shanghai', isolation_source='soil', "
                    "metadata_source='genome_type_material' WHERE acc_base='NR_024839'")
        con.execute("UPDATE record SET country='Japan', metadata_source='record_source_feature:NR_000010.1' "
                    "WHERE acc_base='NR_000010'")
        con.execute("UPDATE record SET host='moss' WHERE acc_base='NR_000011'")   # metadata, no provenance
    return db


def test_validator_reports_both_classes_read_only(defective_store, tmp_path, capsys):
    before = defective_store.read_bytes()
    out_dir = tmp_path / "report"
    rc = validate.main(["--db", str(defective_store), "--out-dir", str(out_dir)])
    assert rc == 1
    assert defective_store.read_bytes() == before
    report = json.loads((out_dir / "16s_validate_report.json").read_text())
    g = report["genome_joined"]
    assert g["genome_joined_rows"] == 1 and g["provenance_unknown_rows"] == 1 and g["rows_with_metadata"] == 3
    assert g["by_source"] == [{"source": "refseq_type", "metadata_source": "genome_type_material", "n": 1}]
    c = report["concatenated_genus"]
    assert c["concatenated_strings"] == 1 and c["affected_records"] == 2 and c["definition_agrees"] == 2
    assert c["corroborated_strings"] == 1 and c["review_needed_strings"] == 0
    tsv = (out_dir / "16s_validate_concatenated_genus.tsv").read_text().splitlines()
    row = dict(zip(tsv[0].split("\t"), tsv[1].split("\t")))
    assert (row["genus_as_stored"], row["split_genus"], row["epithet"], row["status"]) == \
        ("Saccharopolysporagregorii", "Saccharopolyspora", "gregorii", "CORROBORATED")
    joined = (out_dir / "16s_validate_genome_joined.tsv").read_text().splitlines()
    assert joined[1].startswith("NR_024839\tNR_024839.1\trefseq_type\tSaccharopolyspora spinosa\tgenome_type_material")
    assert "defects_present: True" in capsys.readouterr().out


def test_validator_clean_store_exits_zero(tmp_path):
    db = _db(tmp_path, [_rec("NR_000001.1", "Kribbella flavida strain A 16S", "Kribbella flavida",
                             "Kribbella", "refseq_type", "A")])
    with sqlite3.connect(db) as con:
        fetch.ensure_columns(con)
    report, g_rows, c_rows = validate.validate(str(db))
    assert (g_rows, c_rows, report["defects_present"]) == ([], [], False)
    assert validate.main(["--db", str(db)]) == 0


def test_validator_missing_metadata_source_column_is_a_defect(tmp_path):
    db = _db(tmp_path, [_rec("NR_000001.1", "Kribbella flavida strain A 16S", "Kribbella flavida",
                             "Kribbella", "refseq_type", "A")])
    report, _, _ = validate.validate(str(db))
    assert report["genome_joined"]["metadata_source_column_present"] is False
    assert report["defects_present"] is True


def test_validator_missing_db_is_usage_error(tmp_path):
    assert validate.main(["--db", str(tmp_path / "nope.sqlite")]) == 2
