"""FA4 (extended in AMBER_04): tests for the analysis sign-off gate (tools/signoff_check.py).

The gate is advisory (always exits 0); these tests exercise the OBJECTIVE checks:
  * a clean, well-labelled tree with support + a marked outgroup passes with no issues;
  * a tree with a planted non-target contaminant tip (E. coli) and NO branch-support
    values is flagged (the two catches the sign-off gate exists to mechanise);
  * the CLI wrapper runs on a real Newick file and exits 0 regardless.
AMBER_04 adds coverage for the four checks folded in from the Amber phylogeny session:
  MAG/unclassified bin tips, >1 _OUTGROUP tip, an _OUTGROUP whose genus is also in the
  ingroup (not a true outgroup), and the same assembly present as both GCA and GCF.
"""
import os
import sys
import subprocess
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
_SIGNOFF = os.path.join(ROOT, "tools", "signoff_check.py")

spec = importlib.util.spec_from_file_location("signoff_check", _SIGNOFF)
signoff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(signoff)

# A clean tree: marked outgroup, strain designations, internal-node support values (e.g. 98/95).
CLEAN = ("(((Streptomyces_griseus_DSM40236:0.01,Streptomyces_coelicolor_A3_2:0.01)98:0.02,"
         "Streptomyces_venezuelae_ATCC10712:0.03)95:0.02,"
         "Kitasatospora_setae_KM6054_OUTGROUP:0.10)100:0.0);")

# Planted problems: an E. coli contaminant tip AND no internal-node support labels at all.
CONTAMINATED = ("((Streptomyces_griseus_DSM40236:0.01,Escherichia_coli_K12:0.9):0.02,"
                "Streptomyces_venezuelae_ATCC10712:0.03,"
                "Kitasatospora_setae_KM6054_OUTGROUP:0.10);")

# A MAG / GTDB placeholder sitting in an actinomycete tree (the CAJCJE01_sp963818685 catch).
MAG_TREE = ("(((Pseudonocardia_autotrophica_DSM43083:0.01,"
            "CAJCJE01_sp963818685:0.2)90:0.02,"
            "Pseudonocardia_dioxanivorans_CB1190:0.03)95:0.02,"
            "Actinosynnema_mirum_DSM43827_OUTGROUP:0.10)100:0.0);")

# Two _OUTGROUP tips, one of which shares a genus with the ingroup (mislabelled), plus a
# GCA/GCF twin of the same assembly. All four AMBER_04 checks fire on this one tree.
MULTI = ("((((Nocardia_farcinica_IFM10152:0.01,"
         "Nocardia_farcinica_GCA_000009565.1:0.01)90:0.02,"
         "Nocardia_brasiliensis_HUJEG1_GCF_000009565.1:0.03)95:0.02,"
         "Nocardia_cyriacigeorgica_GUH2_OUTGROUP:0.05)80:0.02,"
         "Rhodococcus_jostii_RHA1_OUTGROUP:0.10)100:0.0);")


def test_clean_tree_passes_objective_checks():
    tips, issues, notes = signoff.check_tree_text(CLEAN)
    assert len(tips) == 4
    assert issues == [], issues  # no objective problems


def test_contaminant_and_missing_support_flagged():
    tips, issues, notes = signoff.check_tree_text(CONTAMINATED)
    blob = " ".join(issues)
    assert "ROGUE" in blob and "coli" in blob.lower()          # planted contaminant tip
    assert any("support" in i for i in issues)                  # no branch-support values


def test_mag_bin_tip_flagged():
    tips, issues, notes = signoff.check_tree_text(MAG_TREE)
    assert any("MAG" in i for i in issues), issues             # unclassified bin as tip


def test_multiple_and_mislabelled_outgroup_flagged():
    tips, issues, notes = signoff.check_tree_text(MULTI)
    blob = " ".join(issues)
    assert "tagged _OUTGROUP (expected 1)" in blob            # >1 outgroup
    assert "not a true outgroup" in blob                       # ingroup genus tagged outgroup
    assert "GCA and GCF" in blob                               # duplicate genome (twin accession)


def test_cli_runs_and_exits_zero(tmp_path):
    f = tmp_path / "demo.treefile"
    f.write_text(CONTAMINATED, encoding="utf-8")
    r = subprocess.run([sys.executable, _SIGNOFF, str(f)],
                       capture_output=True, text=True)
    assert r.returncode == 0                                    # advisory: never blocks
    assert "signoff_check" in r.stdout
    assert "ROGUE" in r.stdout                                  # still reports the issue
