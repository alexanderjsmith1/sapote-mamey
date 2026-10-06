"""v9.7.448: tools/check_tygs_coverage.py fails when a TYGS top-N type strain is neither in the panel nor logged (the neighbourhood-tree
silent-drop bug), and passes when each is accounted for, for both TYGS table formats."""
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("check_tygs_coverage", ROOT / "tools" / "check_tygs_coverage.py")
ctc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ctc)

TYGS = ("comp_type\tquery_genome\tsubject_genome\tdigital_ddh_d4\n"
        "U vs. T\t'AS-1.fna'\tStreptomyces alpha NRRL 1\t40\n"                                          # plain-text format
        "U vs. T\t<b>'AS-1.fna'</b> \t\"<I>Streptomyces</I> <I>beta</I> <a href=\"\"x\"\">DSM 2</a>\"\t30\n"  # HTML format
        "U vs. T\t'AS-1.fna'\tStreptomyces gamma JCM 3\t30\n"                                             # tied with the 2nd
        "U vs. T\t'AS-1.fna'\tStreptomyces delta JCM 4\t10\n")


def _setup(tmp, panel_names, issue_names):
    (tmp / "t.tsv").write_text(TYGS)
    d = tmp / "P" / "AS-1"; d.mkdir(parents=True)
    rows = "".join(f"GCF_{i}.1\t\t\t\t\t\t\t{n}\t\t\t\n" for i, n in enumerate(panel_names))
    (d / "PANEL_TREE.tsv").write_text("ncbi_accession\tsource\tbest_16S_identity\tblast_hits\torganism\tstrain\tncbi_type_material\t"
                                      "tygs_type_strain\ttygs_d4\tassembly_level\twhy\n" + rows)
    (d / "PANEL_ISSUES.tsv").write_text("source\titem\tdetail\n" + "".join(f"TYGS\t{n}\tx\n" for n in issue_names))
    return ["--tygs", str(tmp / "t.tsv"), "--panels-dir", str(tmp / "P"), "--strains", "AS-1:2", "--out", str(tmp / "o.tsv")]


def test_missing_unlogged_row_fails(tmp_path):
    args = _setup(tmp_path, ["Streptomyces alpha NRRL 1", "Streptomyces beta DSM 2"], [])   # gamma (tied 2nd) neither present nor logged
    assert ctc.main(args) == 1
    assert "MISSING_NOT_LOGGED" in (tmp_path / "o.tsv").read_text()


def test_every_row_accounted_for_passes(tmp_path):
    args = _setup(tmp_path, ["Streptomyces alpha NRRL 1; Streptomyces beta DSM 2"], ["Streptomyces gamma JCM 3"])
    assert ctc.main(args) == 0
    text = (tmp_path / "o.tsv").read_text()
    assert "delta" not in text          # outside the top 2 (plus ties)
    assert text.count("in_panel") == 2 and text.count("logged") == 1
