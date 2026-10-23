"""tools/locus_protein_space_pages.py: protein-space pages of one locus as a bundle route (owner, 21 Oct, ruling 290; ruling 284
retired PCoA; V5.3 p331 "arrows pointing to 85 and 86 with no explanation"; p327 "the grey data points are hard to see").

Defaults: t-SNE and TriMap only, no point labels (a label is a protein-search name, never an index number), reference points
enlarged. Input derivation is tested on synthetic kits; drawing is the renderer's own, tested elsewhere."""
import importlib.util
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("lsp457", ROOT / "tools" / "locus_protein_space_pages.py")
lsp = importlib.util.module_from_spec(spec); spec.loader.exec_module(lsp)

ID = "S1 / NODE_1_length_9000_cov_9.5 / region001 / BGC001"
ORIGIN = "S1__NODE_1_length_9000_cov_9.5.region001.gbk"


def kit(tmp_path):
    z = tmp_path / "S1.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("S1/NODE_1_length_9000_cov_9.5.region001.gbk", "x")
        zf.writestr("S1/NODE_2_length_5000_cov_9.5.region001.gbk", "x")
    k = tmp_path / "kit"
    for s, rows in (("KS", [("p1", ORIGIN, "ctg1_3"), ("p2", ORIGIN, "ctg1_4"), ("r1", "R__x.region001.gbk", "r_1")]),
                    ("AT", [("r2", "R__x.region001.gbk", "r_2")]),          # no protein of the locus
                    ("C", [("p3", ORIGIN, "ctg1_9")])):                     # holds the locus, but no saved t-SNE
        d = k / f"out_{s}"; d.mkdir(parents=True, exist_ok=True)   # args() may build the kit twice in one test
        (d / f"PCOA_{s}.tsv").write_text("id\torigin\tlocus_tag\n" + "".join(f"{i}\t{o}\t{t}\n" for i, o, t in rows))
    (tmp_path / "kits.tsv").write_text("set\tkit\n" + "".join(f"{s}\t{k}\n" for s in ("KS", "AT", "C")))
    for s, lay in (("KS", "tsne"), ("KS", "trimap"), ("C", "trimap")):
        (tmp_path / f"{s}_{lay}.tsv").write_text("id\n")
    (tmp_path / "emb.tsv").write_text("set\tlayout\tpath\n" + "".join(f"{s}\t{lay}\t{tmp_path / f'{s}_{lay}.tsv'}\n"
                                                                     for s, lay in (("KS", "tsne"), ("KS", "trimap"), ("C", "trimap"))))
    (tmp_path / "cohort.tsv").write_text("strain\tcohort\nS1\tbee\nR\tpublic\n")
    (tmp_path / "names.tsv").write_text("locus_tag\tname\nctg1_3\tKS-like\n")
    return z


def args(tmp_path, **kw):
    a = lsp.argparse.Namespace(identity=ID, zip=str(kit(tmp_path)), kits=str(tmp_path / "kits.tsv"),
                               embeddings=str(tmp_path / "emb.tsv"), cohort_table=str(tmp_path / "cohort.tsv"),
                               layouts=["tsne", "trimap"], labels="none", gene_names=None)
    a.__dict__.update(kw)
    return a


def test_sets_cohort_and_drop_list(tmp_path):
    info = lsp.locus_inputs(args(tmp_path), tmp_path / "inputs")
    assert info["sets"] == ["KS"] and info["origin"] == ORIGIN
    assert ("C", "no saved tsne coordinates") in info["skipped"]
    assert (tmp_path / "inputs" / "COHORT.tsv").read_text() == "strain\tcohort\nS1\tlocus\nR\tpublic\n"
    assert (tmp_path / "inputs" / "DROP_OTHER_REGIONS.txt").read_text() == "S1__NODE_2_length_5000_cov_9.5.region001.gbk\n"
    assert info["labels"] == 0 and "__no_point_has_this_id__" in (tmp_path / "inputs" / "LABEL_IDS.tsv").read_text()   # no labels by default


def test_labels_are_names_never_numbers(tmp_path):
    info = lsp.locus_inputs(args(tmp_path, labels="names", gene_names=str(tmp_path / "names.tsv")), tmp_path / "inputs")
    assert info["labels"] == 1
    assert (tmp_path / "inputs" / "LABEL_IDS.tsv").read_text() == "id\ttext\np1\tKS-like\n"   # p2 has no name: not labeled


def test_refusals(tmp_path, capsys):
    with pytest.raises(ValueError, match="identity"):
        lsp.locus_inputs(args(tmp_path, identity="S1 / NODE_1"), tmp_path / "i1")
    with pytest.raises(ValueError, match="not a region file"):
        lsp.locus_inputs(args(tmp_path, identity="S1 / NODE_9_x / region001 / BGC009"), tmp_path / "i2")
    base = ["--identity", ID, "--zip", "z", "--kits", "k", "--embeddings", "e", "--cohort-table", "c", "--out", str(tmp_path / "o")]
    with pytest.raises(SystemExit):
        lsp.main(base + ["--layouts", "umap"])
    with pytest.raises(SystemExit):
        lsp.main(base + ["--labels", "names"])


def test_defaults_retire_pcoa_and_enlarge_reference_points():
    src = (ROOT / "tools" / "locus_protein_space_pages.py").read_text()
    assert 'default="tsne,trimap"' in src and "default=2.0" in src
    assert [lsp.grid_for(n) for n in (1, 2, 3, 5, 9)] == ["1x1", "2x1", "2x2", "3x2", "3x3"]
