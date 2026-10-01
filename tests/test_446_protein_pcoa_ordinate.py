"""tools/protein_pcoa_ordinate.py: extraction of the antiSMASH domain and secmet sets, the classical PCoA, refusals, and (with
DIAMOND) a kit the renderer and explorer can read. Synthetic strains only (tools/test_synthetic_ids.txt)."""
import csv
import importlib.util
import itertools
import json
import shutil
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("protein_pcoa_ordinate", ROOT / "tools" / "protein_pcoa_ordinate.py")
ppo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ppo)

KS1 = "MSEPIAIVGMACRLPGGVDSPESLWRLLAEGRDAVSEVPADRWDADALYDPDPDAPGKSYTRWGGFLDGVDGFDAAFFGISPREAAAMDPQQRLLLEVAWEALEDAGIAPDSLRGSRTGVFVGASSSDYAELLGRTGAGSDGYLGLGNAASVAAGRISYVLGLRGPSLSVDTACSSSLVAVHLACQSLRSGECDLALAGGVNLMLSPLTFVAFSKARALSPDGRCKAFSADADGYGRGEGAGVVVLKRLSDARRDGDRILAVVRGSAVNQDGASNGLTAPNGPAQQRVIRQALANAGLRPDQVDYVEAHGTGTRLGDPIEAGALAAVFGPHRPADRPLLLGSVKTNIGHLEAAAGIAGLIKVVLALRHGVLPPTLHLTEPNPYLDLDGSRLRLVTEPRPWPAGGRARRAGVSSFGFGGTNAHVVLEE"
KS2 = KS1.replace("VAWEALEDAG", "VAWEALQDAG").replace("GLRGPS", "GLKGPS")
LANC = "MTLLDRAREALLAAGDRPLGLLDGHAGVALALAELARETGDARWRDLALELLERAAEAADGSGGLLHGHLGVAAALLAAARALGDPRWLDLGRRAVTRLLAAASEGGAGDGTGTGTDLAHGRAGLLLGLLALHDAGPDAAARAAARRLLDAL"
OTHER = "MKKLLIAAGAGFAGALVAGPAQAAEVTSPADA"


def region_gbk(record, ks_seqs, lanc=False, product="T1PKS"):
    feats = [f"     region          1..9000\n                     /product=\"{product}\""]
    pos = 1
    for k, s in enumerate(ks_seqs, 1):
        feats.append(f"     CDS             {pos}..{pos + 1499}\n                     /locus_tag=\"{record}_{k}\"\n"
                     f"                     /translation=\"{s}\"")
        feats.append(f"     aSDomain        {pos}..{pos + 1199}\n                     /aSDomain=\"PKS_KS\"\n"
                     f"                     /aSTool=\"nrps_pks_domains\"\n                     /domain_subtypes=\"Modular-KS\"\n"
                     f"                     /locus_tag=\"{record}_{k}\"\n                     /translation=\"{s}\"")
        pos += 1500
    if lanc:
        feats.append(f"     CDS             {pos}..{pos + 500}\n                     /locus_tag=\"{record}_lanc\"\n"
                     f"                     /sec_met_domain=\"LANC_like (E-value: 1e-40, bitscore: 130, seeds: 10)\"\n"
                     f"                     /translation=\"{LANC}\"")
    feats.append(f"     CDS             8000..8099\n                     /locus_tag=\"{record}_x\"\n                     /translation=\"{OTHER}\"")
    seq = "a" * 9000
    origin = "\n".join(f"{i + 1:>9} {seq[i:i + 60]}" for i in range(0, 9000, 60))
    return (f"LOCUS       {record}  9000 bp    DNA     linear   UNK 01-JAN-1980\nDEFINITION  test.\n"
            f"FEATURES             Location/Qualifiers\n" + "\n".join(feats) + f"\nORIGIN\n{origin}\n//\n")


@pytest.fixture
def inputs(tmp_path):
    iso = tmp_path / "iso/Streptomyces"; iso.mkdir(parents=True)
    (iso / "AS-900__NODE_1_length_9000_cov_5.0.region001.gbk").write_text(region_gbk("NODE_1", [KS1], lanc=True))
    (iso / "AS-901__NODE_2_length_9000_cov_5.0.region001.gbk").write_text(region_gbk("NODE_2", [KS2]))
    ref = tmp_path / "ref/Streptomyces"; ref.mkdir(parents=True)
    (ref / "Ref_one__NZ_1.region001.gbk").write_text(region_gbk("NZ_1", [KS1, KS2], lanc=True))
    mib = tmp_path / "mibig"; mib.mkdir()
    (mib / "BGC0000001.gbk").write_text(region_gbk("BGC0000001", [KS1]))
    (tmp_path / "cohort.tsv").write_text("strain\tcohort\nAS-900\tgroup_a\nAS-901\tgroup_b\n")
    return tmp_path


def extract(t):
    return ppo.main(["extract", "--kit", str(t / "kit"), "--input", f"isolate={t / 'iso'}", "--input", f"reference={t / 'ref'}",
                     "--input", f"MIBiG={t / 'mibig'}", "--cohort-table", str(t / "cohort.tsv")])


def test_extract_sets_genus_and_cohort(inputs):
    assert extract(inputs) == 0
    ks = list(csv.DictReader(open(inputs / "kit/KS_META.tsv"), delimiter="\t"))
    assert [(r["source"], r["strain"], r["group"], r["genus"], r["subtype"]) for r in ks] == [
        ("isolate", "AS-900", "group_a", "Streptomyces", "Modular-KS"), ("isolate", "AS-901", "group_b", "Streptomyces", "Modular-KS"),
        ("reference_held", "Ref_one", "reference_held", "Streptomyces", "Modular-KS"),
        ("reference_held", "Ref_one", "reference_held", "Streptomyces", "Modular-KS"),
        ("MIBiG", "BGC0000001", "MIBiG", "", "Modular-KS")]
    lanc = list(csv.DictReader(open(inputs / "kit/LANC_META.tsv"), delimiter="\t"))
    assert sorted(r["strain"] for r in lanc) == ["AS-900", "Ref_one"]
    receipt = json.loads((inputs / "kit/EXTRACT_RECEIPT.json").read_text())
    assert receipt["cds_by_source"] == {"isolate": 5, "reference_held": 4, "MIBiG": 2}
    assert extract(inputs) == 2                                  # never overwrites its outputs


def test_extract_refuses_an_unknown_source(inputs):
    assert ppo.main(["extract", "--kit", str(inputs / "k2"), "--input", f"public={inputs / 'ref'}"]) == 2


def test_classical_pcoa_recovers_a_known_layout():
    pts = np.array([[0, 0], [3, 0], [0, 4], [3, 4], [1.5, 2]], float)
    D = np.sqrt(((pts[:, None] - pts[None]) ** 2).sum(-1)).astype(np.float32)
    X, pct = ppo.classical_pcoa(D.copy(), k=3)
    for i, j in itertools.combinations(range(5), 2):
        assert np.linalg.norm(X[i, :2] - X[j, :2]) == pytest.approx(np.linalg.norm(pts[i] - pts[j]), abs=1e-3)
    assert pct[0] >= pct[1] and abs(sum(pct[:2]) - 100) < 1e-3
    X2, _ = ppo.classical_pcoa(D.copy(), k=3)
    assert np.allclose(X, X2)                                    # fixed axis signs: reruns give the same picture


@pytest.mark.skipif(not shutil.which("diamond"), reason="DIAMOND not on PATH")
def test_ordinate_and_nearest_write_a_renderable_kit(inputs):
    extract(inputs)
    assert ppo.main(["ordinate", "--kit", str(inputs / "kit"), "--set", "KS", "--threads", "1"]) == 0
    rows = list(csv.DictReader(open(inputs / "kit/out_KS/PCOA_KS.tsv"), delimiter="\t"))
    assert sum(r["source"] == "isolate" for r in rows) == 2      # cohort points are never clustered away
    assert {"PC1", "PC2", "PC3", "n_represented", "origin", "locus_tag"} <= set(rows[0])
    run = json.loads((inputs / "kit/out_KS/RUN_KS.json").read_text())
    assert run["isolate_sequences"] == 2 and run["mibig_sequences"] == 1 and len(run["pct_axes"]) == 3
    assert ppo.main(["nearest", "--kit", str(inputs / "kit"), "--set", "KS", "--threads", "1"]) == 0
    near = {r["strain"]: r for r in csv.DictReader(open(inputs / "kit/out_KS/NEAREST_KS.tsv"), delimiter="\t")}
    assert float(near["AS-900"]["nearest_pident"]) == 100.0      # identical to the reference and MIBiG KS
    assert float(near["AS-901"]["nearest_pident"]) == 100.0
    assert not list((inputs / "kit/out_KS").glob("*.faa"))     # working files removed


def test_ordinate_refuses_without_diamond(inputs, monkeypatch):
    extract(inputs)
    monkeypatch.setattr(ppo.shutil, "which", lambda name: None)
    assert ppo.main(["ordinate", "--kit", str(inputs / "kit"), "--set", "KS"]) == 2


def _hmm_file(path, name, seq):
    pyhmmer = pytest.importorskip("pyhmmer")
    from pyhmmer.easel import Alphabet, TextSequence
    from pyhmmer.plan7 import Background, Builder
    alpha = Alphabet.amino()
    hmm, _, _ = Builder(alpha).build(TextSequence(name=name.encode(), sequence=seq).digitize(alpha), Background(alpha))
    hmm.name = name.encode()
    hmm.cutoffs.gathering = (50.0, 50.0)
    with open(path, "wb") as fh:
        hmm.write(fh)


def test_pfam_sets_use_gathering_thresholds(inputs):
    extract(inputs)
    hmm = inputs / "sets.hmm"
    with open(hmm, "wb") as fh:
        pass
    parts = []
    for name in sorted({p for ps in ppo.PFAM_SETS.values() for p in ps}):
        f = inputs / f"{name}.hmm"
        _hmm_file(f, name, KS1 if name == "p450" else OTHER * 3)
        parts.append(f.read_bytes())
    hmm.write_bytes(b"".join(parts))
    assert ppo.main(["pfam", "--kit", str(inputs / "kit"), "--hmm", str(hmm), "--threads", "1"]) == 0
    p450 = list(csv.DictReader(open(inputs / "kit/P450_META.tsv"), delimiter="\t"))
    assert sorted(r["strain"] for r in p450) == ["AS-900", "AS-901", "BGC0000001", "Ref_one", "Ref_one"]   # KS-like CDS hit
    assert all(r["subtype"] == "p450" for r in p450)
    # a library without the named families is refused
    one = inputs / "one.hmm"; _hmm_file(one, "SomethingElse", KS1)
    assert ppo.main(["pfam", "--kit", str(inputs / "kit2"), "--hmm", str(one)]) == 2


@pytest.mark.skipif(not shutil.which("diamond"), reason="DIAMOND not on PATH")
def test_card_families_become_res_sets(inputs):
    extract(inputs)
    (inputs / "card.faa").write_text(f">gb|X1.1|ARO:3000001|TestPump [synthetic]\n{KS1}\n")
    (inputs / "aro.tsv").write_text("ARO Accession\tAMR Gene Family\nARO:3000001\ttest efflux family\n")
    assert ppo.main(["card", "--kit", str(inputs / "kit"), "--card-fasta", str(inputs / "card.faa"), "--aro-index",
                     str(inputs / "aro.tsv"), "--min-cohort", "2", "--threads", "1"]) == 0
    sets = list(csv.DictReader(open(inputs / "kit/RES_SETS.tsv"), delimiter="\t"))
    assert sets == [{"set": "RES01", "amr_gene_family": "test efflux family", "proteins": "5", "isolate_proteins": "2"}]


def test_a_folder_of_result_zips_names_each_genome_by_its_zip(inputs):
    import zipfile
    dl = inputs / "downloads/round1"; dl.mkdir(parents=True)
    with zipfile.ZipFile(dl / "GCF_000001.1.zip", "w") as z:
        z.writestr("GCF_000001.1/NZ_X.region001.gbk", region_gbk("NZ_X", [KS2]))
    (inputs / "genus.tsv").write_text("strain\tgenus\nGCF_000001.1\tStreptomyces\n")
    assert ppo.main(["extract", "--kit", str(inputs / "kz"), "--input", f"reference={inputs / 'downloads'}",
                     "--genus-table", str(inputs / "genus.tsv")]) == 0
    ks = list(csv.DictReader(open(inputs / "kz/KS_META.tsv"), delimiter="\t"))
    assert [(r["strain"], r["genus"], r["origin"]) for r in ks] == [("GCF_000001.1", "Streptomyces", "GCF_000001.1:NZ_X.region001.gbk")]
