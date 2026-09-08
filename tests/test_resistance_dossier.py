"""Smoke + invariant tests for mamey.resistance_dossier (post-seal resistance writeups)."""
import os
import pytest
from mamey import resistance_dossier as rd


def _write(pkg, name, header, rows):
    with open(os.path.join(pkg, name), "w", encoding="utf-8") as fh:
        fh.write(",".join(header) + "\n")
        for r in rows:
            fh.write(",".join(str(x) for x in r) + "\n")


@pytest.fixture()
def sealed_pkg(tmp_path):
    pkg = tmp_path / "AS-TST" ; pkg.mkdir()
    p = str(pkg)
    # BGC001: has a beta-lactamase (strict resistance) + an ABC transporter
    # BGC002: only an ABC transporter (immunity only under the broad flag)
    _write(p, "AS-TST_2_inventory.csv",
           ["BGC_ID", "Products", "KCB_top", "Resistance_tier"],
           [["BGC001", "NRPS; PKS", "BGC0000001.1 | examplin | knownclusterblast #1",
             "T2_RESISTANCE_LIKE_SOURCE_DERIVED"],
            ["BGC002", "terpene", "", "T2_RESISTANCE_LIKE_SOURCE_DERIVED"]])
    _write(p, "AS-TST_domains.csv",
           ["bgc_id", "locus_tag", "domain", "pfam_acc"],
           [["BGC001", "ctg1_1", "Beta-lactamase", "PF00144"],
            ["BGC001", "ctg1_2", "PKS_KS", "PF00109"],
            ["BGC001", "ctg1_3", "ABC_tran", "PF00005"],
            ["BGC002", "ctg2_1", "Terpene_synth", "PF01397"],
            ["BGC002", "ctg2_2", "ABC2_membrane", "PF01061"]])
    _write(p, "AS-TST_3_mibig_per_gene.csv",
           ["query_gene", "mibig_compound", "mibig_accession", "pct_identity"],
           [["ctg1_2", "examplin", "BGC0000001", "72"]])
    return p


def test_strict_flags_only_resistance_marker(sealed_pkg, tmp_path):
    out = str(tmp_path / "out_strict")
    res = rd.run(sealed_pkg, out, immunity_transporters=False)
    # BGC001 has beta-lactamase -> dossier; BGC002 has only a transporter -> no dossier (strict)
    assert res["n_dossiers"] == 1
    md = open(os.path.join(out, "BGC001_resistance_dossier.md"), encoding="utf-8").read()
    assert "[RES]" in md and "Beta-lactamase" in md
    assert "[IMM]" not in md  # strict mode never emits immunity flags


def test_immunity_flag_broadens_to_transporters(sealed_pkg, tmp_path):
    out = str(tmp_path / "out_imm")
    res = rd.run(sealed_pkg, out, immunity_transporters=True)
    # now BGC002's transporter in a resistance-tier BGC also yields a dossier
    assert res["n_dossiers"] == 2
    md2 = open(os.path.join(out, "BGC002_resistance_dossier.md"), encoding="utf-8").read()
    assert "[IMM]" in md2


def test_claim_safety_language_present(sealed_pkg, tmp_path):
    out = str(tmp_path / "out_cs")
    rd.run(sealed_pkg, out)
    md = open(os.path.join(out, "BGC001_resistance_dossier.md"), encoding="utf-8").read()
    for phrase in ("similarity, not identity", "Judgment deferred", "does **not** prove"):
        assert phrase in md, phrase
    # never a bare production claim
    assert "produces " not in md.lower()


def test_curated_tsv_wins_over_incode_vocabulary(tmp_path):
    """Lactamase_B is 'resistance' in the curated TSV but not in the in-code fallback.

    Guards the undercount defect: without the curated vocabulary the strict resistance set
    silently loses every Lactamase_B-only BGC.
    """
    pkg = tmp_path / "AS-LB" ; pkg.mkdir() ; p = str(pkg)
    _write(p, "AS-LB_2_inventory.csv", ["BGC_ID", "Products", "KCB_top", "Resistance_tier"],
           [["BGC001", "NRPS", "", "T4"]])
    _write(p, "AS-LB_domains.csv", ["bgc_id", "locus_tag", "domain", "pfam_acc"],
           [["BGC001", "ctg1_1", "Lactamase_B", "PF00753"]])
    tsv = tmp_path / "domain_reference.tsv"
    tsv.write_text("domain\tpfam_acc\tcategory\tcontext\n"
                   "Lactamase_B\tPF00753.30\tresistance\tMetallo-beta-lactamase superfamily\n",
                   encoding="utf-8")

    # in-code fallback: Lactamase_B is not a resistance marker -> no dossier
    assert rd.run(p, str(tmp_path / "o1"))["n_dossiers"] == 0
    # curated TSV: it is -> dossier emitted, and the run reports the vocabulary it used
    res = rd.run(p, str(tmp_path / "o2"), domain_reference_tsv=str(tsv))
    assert res["n_dossiers"] == 1
    assert res["used_reference"] is True


def test_no_resistance_gene_no_dossier(tmp_path):
    pkg = tmp_path / "AS-CLEAN" ; pkg.mkdir(); p = str(pkg)
    _write(p, "AS-CLEAN_2_inventory.csv", ["BGC_ID", "Products", "KCB_top", "Resistance_tier"],
           [["BGC001", "terpene", "", "T4"]])
    _write(p, "AS-CLEAN_domains.csv", ["bgc_id", "locus_tag", "domain", "pfam_acc"],
           [["BGC001", "ctg1_1", "Terpene_synth", "PF01397"]])
    res = rd.run(p, str(tmp_path / "out"))
    assert res["n_dossiers"] == 0


# --- cross-BGC leakage bugfix + sibling-output policy (v9.7.348 repair) ---
def test_load_mibig_keys_by_bgc_and_gene_no_cross_bgc_leak(tmp_path):
    pkg = tmp_path / "AS-TST" ; pkg.mkdir()
    # a shared locus tag 'ctg1_5' carries a MIBiG hit under BGC001 ONLY
    _write(str(pkg), "AS-TST_3_mibig_per_gene.csv",
           ["bgc_id", "query_gene", "mibig_compound", "pct_identity"],
           [["BGC001", "ctg1_5", "vancomycin", "80"],
            ["BGC002", "ctg9_2", "erythromycin", "70"]])
    m = rd.load_mibig(str(pkg))
    assert m[("BGC001", "ctg1_5")][0]["compound"] == "vancomycin"
    assert m[("BGC002", "ctg9_2")][0]["compound"] == "erythromycin"
    # the shared locus tag must NOT leak into BGC002
    assert ("BGC002", "ctg1_5") not in m
    # rows without a bgc_id are dropped (never mis-attributed)
    assert all(isinstance(k, tuple) and k[0] for k in m)


def test_output_refuses_inside_sealed_package(tmp_path):
    pkg = tmp_path / "AS-TST" ; pkg.mkdir()
    with pytest.raises(ValueError, match="OUTSIDE the sealed package"):
        rd.run(str(pkg), out_dir=str(pkg / "resistance_dossiers"))


def test_output_defaults_to_sibling(sealed_pkg):
    res = rd.run(sealed_pkg)
    out = res["out_dir"]
    assert out.endswith("_resistance_dossiers")
    assert not out.startswith(os.path.abspath(sealed_pkg) + os.sep)   # sibling, not inside
    assert not os.path.exists(os.path.join(sealed_pkg, "resistance_dossiers"))  # package unmutated
