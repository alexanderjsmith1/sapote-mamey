"""Reference-guided completion in the standalone package: the tier without a database, the split rules, and
`rggmci build-mibig-db`. Made-up ids only."""
import json
from pathlib import Path

import pytest

from rggmci.cli import main
from rggmci.ref_completion import complete, is_mobile_gene, mark_recurrent_splits


def test_without_a_database_every_pair_says_so(tmp_path, monkeypatch):
    monkeypatch.delenv("RGGMCI_MIBIG_DB", raising=False)
    res = {"ranked_pairs": [{"pair": "BGC001+BGC002", "bgc_a": "BGC001", "bgc_b": "BGC002"}]}
    complete(res, Path(tmp_path, "TST-1.zip"), [], {}, set(), mibig_db=None)
    assert res["reference_completion"]["completion_tier"] == "NO_MIBIG_PROTEINS"
    assert res["ranked_pairs"][0]["completion_tier"] == "NO_MIBIG_PROTEINS"


def test_split_rules():
    comp = {"BGC9999001": ["testomycin"], "BGC9999002": ["otheromycin"]}
    real = [{"reference": "BGC9999001", "_core_bgc": "BGC001", "_pieces": ("q1", "q2"),
             "_piece_bgcs": {"BGC001", "BGC002"}, "split_call": "CLEAR"},
            {"reference": "BGC9999002", "_core_bgc": "BGC002", "_pieces": ("q1", "q2"),
             "_piece_bgcs": {"BGC001", "BGC002"}, "split_call": "CLEAR"}]
    assert mark_recurrent_splits(real, comp) == 0
    assert is_mobile_gene({"product": "transposase"}) and not is_mobile_gene({"product": "kinase"})


def _mibig_gbk(folder: Path) -> Path:
    """One made-up MIBiG cluster, BGC9999001, 3,000 bp with two proteins."""
    folder.mkdir()
    cds = [("1..900", "tstA", "synthase", "M" + "ACDEFGHIKL" * 29 + "AC"),
           ("1001..1600", "tstB", "kinase", "M" + "PQRSTVWY" * 24 + "PQRSTVW")]
    lines = ["LOCUS       BGC9999001 3000 bp    DNA     linear   BCT 01-JAN-2000",
             "DEFINITION  Streptomyces sp. TST-9 testomycin cluster.", "ACCESSION   BGC9999001",
             "VERSION     BGC9999001", "FEATURES             Location/Qualifiers"]
    for loc, gene, product, aa in cds:
        lines += [f"     CDS             {loc}", f'                     /gene="{gene}"',
                  f'                     /product="{product}"', f'                     /translation="{aa}"']
    (folder / "BGC9999001.gbk").write_text("\n".join(lines + ["//"]) + "\n")
    return folder


def test_build_mibig_db_from_the_command_line_without_diamond(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("RGGMCI_DIAMOND", raising=False)
    monkeypatch.setenv("PATH", str(tmp_path))          # no DIAMOND: the FASTA and the tables only
    assert main(["build-mibig-db", str(_mibig_gbk(tmp_path / "gbk")), str(tmp_path / "db")]) == 0
    assert "1 clusters, 2 proteins" in capsys.readouterr().out
    manifest = json.loads((tmp_path / "db" / "MANIFEST.json").read_text())
    assert (manifest["clusters"], manifest["proteins"], manifest["diamond_db"]) == (1, 2, "")
    assert (tmp_path / "db" / "mibig_proteins.faa").read_text().count(">BGC9999001|") == 2
    clusters = (tmp_path / "db" / "mibig_clusters.tsv").read_text().splitlines()
    assert clusters[0].split("\t")[-1] == "length_bp" and clusters[1].split("\t")[-1] == "3000"


def test_build_mibig_db_help_names_rggmci(capsys):
    with pytest.raises(SystemExit):
        main(["build-mibig-db", "--help"])
    assert "usage: rggmci build-mibig-db" in capsys.readouterr().out
