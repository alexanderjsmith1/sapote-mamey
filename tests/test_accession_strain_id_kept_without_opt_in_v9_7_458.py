"""A single-region accession input keeps the accession as its output identity.

`run` used to rename an accession-shaped strain id after the identity guard had already
accepted it. With a genus in --taxonomy, `--strain KY089035.1` became the run folder
`Streptomyces_sp_KY089035_1`. With taxonomy "not verified" or empty, the genus was read from
the ZIP filename and the folder became `KY089035_1_zip_sp_KY089035_1`. That happened with or
without --allow-accession-strain-id.

Now the identity guard in `mamey.strain_identity` is the only place that decides the id:
- without --allow-accession-strain-id, an accession is refused when the archive names an
  organism, and kept as given (with a warning) when it does not;
- with the flag, the accession is kept as given;
- an id is never built from --taxonomy or from the ZIP filename.

The runs stop right after the run folder is named: the package lock is stubbed to refuse, so
`run_one_strain` returns PACKAGE_LOCKED before any extraction work.
"""
import json
import zipfile

import pytest

from mamey import cli

ACC = "KY089035.1"

GBK = """LOCUS       KY089035                20747 bp    DNA     linear   BCT 01-JAN-2020
DEFINITION  Streptomyces sp. test cluster.
SOURCE      {organism}
  ORGANISM  {organism}
            Bacteria; Actinomycetota; Actinomycetes; Streptomycetales;
            Streptomycetaceae; Streptomyces.
COMMENT     ##antiSMASH-Data-START##
            Version      :: 8.0.4
            ##antiSMASH-Data-END##
ORIGIN
//
"""


def _single_region_zip(tmp_path, organism):
    """A tiny single-region accession ZIP with the shape described on the troubleshooting page."""
    p = tmp_path / f"{ACC}.zip"
    with zipfile.ZipFile(p, "w") as zf:
        zf.writestr("KY089035.1.region001.gbk", GBK.format(organism=organism))
        zf.writestr("results.json", json.dumps({"strictness": "relaxed"}))
    return p


@pytest.fixture
def stop_after_naming(monkeypatch):
    monkeypatch.setenv("MAMEY_QUIET_STAGES", "1")
    monkeypatch.setattr(cli, "_acquire_package_lock", lambda *_a, **_k: None)


def _run_folders(outdir):
    return sorted(p.name for p in outdir.iterdir() if p.is_dir()) if outdir.exists() else []


# --- run_one_strain: the block that named the folder ------------------------------------------

@pytest.mark.parametrize("taxonomy", ["Streptomyces sp.", "Streptomyces griseus", "not verified", ""])
def test_run_one_strain_keeps_the_accession_folder(tmp_path, stop_after_naming, taxonomy):
    z = _single_region_zip(tmp_path, organism="Streptomyces sp.")
    out = tmp_path / "out"
    res = cli.run_one_strain(strain_id=ACC, display_name=ACC, input_zip=str(z), outdir=str(out), mode="gold",
                             taxonomy=taxonomy, source="public GenBank sequence")
    assert res["status"] == "PACKAGE_LOCKED"
    assert _run_folders(out) == [ACC]


def test_filename_is_never_an_id_source(tmp_path, stop_after_naming):
    z = _single_region_zip(tmp_path, organism=".")
    out = tmp_path / "out"
    cli.run_one_strain(strain_id=ACC, display_name=ACC, input_zip=str(z), outdir=str(out), mode="gold",
                       taxonomy="not verified", source="public GenBank sequence")
    folders = _run_folders(out)
    assert folders == [ACC]
    assert not any("_zip_" in f for f in folders)


def test_phase_environment_keeps_the_accession_in_the_manifest_context(tmp_path):
    pkg = tmp_path / "run" / "package"
    pkg.mkdir(parents=True)
    _timer, label_accession, _tax, _disp, context = cli._phase_environment(
        pkg, ACC, "gold", "off", "standard", str(tmp_path / f"{ACC}.zip"), "none",
        ACC, "Streptomyces sp.", "public GenBank sequence", None, None, tmp_path / "run")
    assert label_accession is True
    assert context.strain_id == ACC


# --- the `run` command, end to end through the real parser ------------------------------------

def _cli_run(tmp_path, organism, taxonomy, *extra):
    z = _single_region_zip(tmp_path, organism=organism)
    out = tmp_path / "out"
    argv = ["run", "--input-zip", str(z), "--outdir", str(out), "--source", "public GenBank sequence",
            "--mode", "gold", "--taxonomy", taxonomy, *extra]
    rc = cli.main(argv)
    return rc, _run_folders(out)


def test_a_without_flag_unreadable_organism_keeps_the_accession(tmp_path, stop_after_naming):
    # (a) The guard proceeds with a warning; --taxonomy must not rename the accession.
    _rc, folders = _cli_run(tmp_path, ".", "Streptomyces sp.", "--strain", ACC)
    assert folders == [ACC]


def test_a_without_flag_readable_organism_is_refused_before_any_write(tmp_path, stop_after_naming):
    # (a) Unchanged: the guard refuses and names the archive identity instead.
    rc, folders = _cli_run(tmp_path, "Streptomyces sp. ABC123", "Streptomyces sp.", "--strain", ACC)
    assert rc == 2
    assert folders == []


def test_a_strain_auto_takes_the_archive_identity(tmp_path, stop_after_naming):
    # Unchanged: --strain auto is the route to an organism-based identity.
    _rc, folders = _cli_run(tmp_path, "Streptomyces sp. ABC123", "Streptomyces sp.", "--strain", "auto")
    assert len(folders) == 1 and folders[0].startswith("Streptomyces")
    assert ACC not in folders[0] and "_zip_" not in folders[0]


def test_b_with_flag_and_genus_taxonomy_keeps_the_accession(tmp_path, stop_after_naming):
    # (b) The documented first-run command: the flag keeps the accession as the output identity.
    _rc, folders = _cli_run(tmp_path, "Streptomyces sp. ABC123", "Streptomyces sp.",
                            "--strain", ACC, "--allow-accession-strain-id")
    assert folders == [ACC]


@pytest.mark.parametrize("taxonomy", ["not verified", ""])
def test_c_with_flag_and_no_verified_taxonomy_never_uses_the_filename(tmp_path, stop_after_naming, taxonomy):
    # (c) No filename-built id such as KY089035_1_zip_sp_KY089035_1.
    _rc, folders = _cli_run(tmp_path, ".", taxonomy, "--strain", ACC, "--allow-accession-strain-id")
    assert folders == [ACC]
    assert not any("_zip_sp_" in f for f in folders)


# --- the page and the help say the same thing ---------------------------------------------------

def test_help_says_the_accession_is_kept_and_never_renamed():
    parser = cli.build_parser()
    run = next(a for a in parser._subparsers._group_actions[0].choices.values()
               if any(o.dest == "allow_accession_strain_id" for o in a._actions))
    action = next(o for o in run._actions if o.dest == "allow_accession_strain_id")
    text = " ".join(action.help.split())
    assert "kept as given" in text
    assert "--taxonomy" in text and "filename" in text


def test_page_matches_the_code():
    from pathlib import Path
    page = (Path(cli.__file__).resolve().parent.parent / "docs" / "troubleshooting"
            / "SINGLE_REGION_ACCESSION_INPUTS.md").read_text(encoding="utf-8")
    para = page.split("## Recommended first-run command", 1)[1].split("\n## ", 1)[0]
    flat = " ".join(para.split())
    assert "keeps the accession" in flat
    assert "never renames" in flat
    assert "--strain auto" in flat
