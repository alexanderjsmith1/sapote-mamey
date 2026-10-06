"""Strip arrows that would be blank or grey take a family label and role colour from the gene-label table. A label is
admitted only when its contig, locus tag and protein-sequence hash match the genome the package was built from."""
import csv
import hashlib
import io
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import strain_slides as ss  # noqa: E402

SeqIO = pytest.importorskip("Bio.SeqIO")
from Bio.Seq import Seq  # noqa: E402
from Bio.SeqFeature import FeatureLocation, SeqFeature  # noqa: E402
from Bio.SeqRecord import SeqRecord  # noqa: E402

CONTIG = "NODE_1_length_900_cov_1.0"
AA = {"ctg1_1": "M" * 100, "ctg1_2": "MK" * 50, "ctg1_3": "MA" * 50}


def _D(tmp_path):
    rec = SeqRecord(Seq("ATG" * 300), id=CONTIG, name="t", description="t")
    rec.annotations["molecule_type"] = "DNA"
    rec.features = [SeqFeature(FeatureLocation(i * 300, i * 300 + 300, strand=1), type="CDS",
                               qualifiers={"locus_tag": [t], "translation": [a]}) for i, (t, a) in enumerate(AA.items())]
    buf = io.StringIO()
    SeqIO.write(rec, buf, "genbank")
    z = tmp_path / "input.zip"
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("genome.gbk", buf.getvalue())
    (tmp_path / "AS-XXX_proteins.faa").write_text("".join(f">{t}\n{a}\n" for t, a in AA.items()))
    return {"strain": "AS-XXX", "src": {"antismash_zip": str(z)}, "pkg": tmp_path,
            "cds": {t: {"contig": CONTIG, "length_aa": str(len(a))} for t, a in AA.items()}}


def _table(tmp_path, rows):
    p = tmp_path / "labels.tsv"
    cols = ["strain", "full_contig", "locus_tag", "aa_sha256", "protein_length_aa", "short_label", "role"]
    with p.open("w") as f:
        w = csv.DictWriter(f, fieldnames=cols, delimiter="\t")
        w.writeheader()
        for tag, lab, role, *over in rows:
            r = {"strain": "AS-XXX", "full_contig": CONTIG, "locus_tag": tag,
                 "aa_sha256": hashlib.sha256(AA.get(tag, "X").encode()).hexdigest(),
                 "protein_length_aa": str(len(AA.get(tag, "X"))), "short_label": lab, "role": role}
            r.update(over[0] if over else {})
            w.writerow(r)
    return p


def test_blank_arrows_take_the_table_label_and_role_colour(tmp_path):
    D = _D(tmp_path)
    D["glabel"] = ss.gene_labels(_table(tmp_path, [("ctg1_1", "P450", "tailoring"), ("ctg1_2", "TetR reg.", "regulation"),
                                                  ("ctg1_3", "", "unknown")]), D)
    lf, cf = ss.labelled(D, lambda g: "KS" if g["tag"] == "ctg1_2" else "", lambda g: "#C7CBD1")
    assert lf({"tag": "ctg1_1"}) == "P450" and cf({"tag": "ctg1_1"}) == "#F59E0B"
    assert lf({"tag": "ctg1_2"}) == "KS"  # the strip's own label wins
    assert cf({"tag": "ctg1_2"}) == "#15803D"
    assert lf({"tag": "ctg1_3"}) == "" and cf({"tag": "ctg1_3"}) == "#C7CBD1"  # unknown stays grey and blank


def test_same_length_other_protein_or_other_contig_is_not_admitted(tmp_path):
    D = _D(tmp_path)
    got = ss.gene_labels(_table(tmp_path, [("ctg1_1", "P450", "tailoring", {"aa_sha256": "a" * 64}),
                                          ("ctg1_2", "x", "core", {"full_contig": "NODE_9_length_900_cov_1.0"}),
                                          ("ctg1_3", "SDR", "tailoring")]), D)
    assert set(got) == {"ctg1_3"}


def test_a_coloured_arrow_keeps_its_colour(tmp_path):
    D = _D(tmp_path)
    D["glabel"] = ss.gene_labels(_table(tmp_path, [("ctg1_1", "P450", "tailoring")]), D)
    _, cf = ss.labelled(D, lambda g: "", lambda g: "#B91C1C")
    assert cf({"tag": "ctg1_1"}) == "#B91C1C"
