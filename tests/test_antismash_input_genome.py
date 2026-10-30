"""tools/antismash_input_genome.py: the genome an antiSMASH run was given is kept under input/ in its result ZIP."""
import csv
import importlib.util
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("antismash_input_genome", ROOT / "tools/antismash_input_genome.py")
aig = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(aig)

GBK = """LOCUS       ctg1                      12 bp    DNA     linear   UNK 01-JAN-2026
FEATURES             Location/Qualifiers
ORIGIN
        1 acgtacgtac gt
//
"""


def _zip(path, members):
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in members.items():
            zf.writestr(name, data)
    return path


def _manifest(out):
    with open(out / "MANIFEST.tsv", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def test_fasta_and_genbank_inputs_become_fasta(tmp_path):
    a = _zip(tmp_path / "S1.zip", {"input/WW00.fna": ">c1\nACGT\n>c2\nGG\n", "S1.gbk": "x",
                                   "input/._WW00.fna": "junk", "__MACOSX/input/WW00.fna": "junk"})
    b = _zip(tmp_path / "S2.zip", {"input/WW01.gbk": GBK, "regions.js": ""})
    out = tmp_path / "out"
    assert aig.main(["--zip", str(a), "--zip", str(b), "--out", str(out)]) == 0
    assert (out / "S1.fasta").read_text() == ">c1\nACGT\n>c2\nGG\n"
    assert (out / "S2.fasta").read_text() == ">ctg1\nACGTACGTACGT\n"
    rows = _manifest(out)
    assert [(r["name"], r["input_format"], r["contigs"], r["total_bp"]) for r in rows] == \
        [("S1", "fasta", "2", "6"), ("S2", "genbank", "1", "12")]
    assert all(len(r["fasta_sha256"]) == 64 for r in rows)


def test_long_sequences_wrap_at_80_columns(tmp_path):
    a = _zip(tmp_path / "S5.zip", {"input/g.fna": ">c\n" + "A" * 170 + "\n"})
    out = tmp_path / "out"
    assert aig.main(["--zip", str(a), "--out", str(out)]) == 0
    assert [len(line) for line in (out / "S5.fasta").read_text().splitlines()] == [2, 80, 80, 10]


def test_missing_or_ambiguous_input_is_reported_and_nothing_is_overwritten(tmp_path):
    _zip(tmp_path / "S3.zip", {"S3.gbk": GBK})
    _zip(tmp_path / "S6.zip", {"input/a.fna": ">c\nAC\n", "input/b.gbk": GBK})
    out = tmp_path / "out"
    out.mkdir()
    (out / "S4.fasta").write_text("keep\n")
    _zip(tmp_path / "S4.zip", {"input/x.fna": ">c\nAC\n"})
    assert aig.main(["--zips-dir", str(tmp_path), "--out", str(out)]) == 1
    assert (out / "S4.fasta").read_text() == "keep\n"
    assert not (out / "S3.fasta").exists() and not (out / "S6.fasta").exists()
    notes = {r["name"]: r["note"] for r in _manifest(out)}
    assert notes == {"S3": "no input/ genome file", "S4": "exists; not overwritten",
                     "S6": "2 input/ genome files"}


def test_without_biopython_the_shim_and_a_plain_reader_give_the_same_fasta(tmp_path, monkeypatch):
    """The GBK shim rule: a tool that reads GenBank must still work where Biopython is absent."""
    import builtins
    real = builtins.__import__

    def no_bio(name, *args, **kwargs):
        if name == "Bio" or name.startswith("Bio."):
            raise ImportError("Biopython hidden for this test")
        return real(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_bio)
    a = _zip(tmp_path / "S1.zip", {"input/WW00.fna": ">c1 a description\nacgt\n>c2\nGG\n"})
    b = _zip(tmp_path / "S2.zip", {"input/WW01.gbk": GBK})
    out = tmp_path / "out"
    assert aig.main(["--zip", str(a), "--zip", str(b), "--out", str(out)]) == 0
    assert (out / "S1.fasta").read_text() == ">c1\nACGT\n>c2\nGG\n"
    assert (out / "S2.fasta").read_text() == ">ctg1\nACGTACGTACGT\n"


def test_companion_files_points_to_the_zip_before_asking_for_genomes():
    text = (ROOT / "docs" / "COMPANION_FILES.md").read_text(encoding="utf-8")
    assert "tools/antismash_input_genome.py" in text
    assert "original ZIPs" in text or "antiSMASH ZIPs" in text


def test_a_sequence_less_record_is_not_written_as_a_genome(tmp_path):
    no_seq = "LOCUS       ctg9                      50 bp    DNA     linear   UNK 01-JAN-2026\n//\n"
    a = _zip(tmp_path / "S7.zip", {"input/g.gbk": no_seq})
    out = tmp_path / "out"
    assert aig.main(["--zip", str(a), "--out", str(out)]) == 1
    assert not (out / "S7.fasta").exists()
    assert _manifest(out)[0]["fasta_sha256"] == ""
