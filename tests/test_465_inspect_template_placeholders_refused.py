"""`inspect` prints <Genus species> and <isolation source> for the user to edit; `run` must refuse them unedited."""
from mamey import cli
from mamey.cohort_resolver import is_placeholder_taxonomy, is_template_placeholder


def test_template_slots_are_placeholders():
    assert is_placeholder_taxonomy("<Genus species>")
    assert is_template_placeholder("<isolation source>")
    for real in ("Streptomyces sp.", "not verified", "leaf <litter> soil", "<", "<>"):
        assert not is_template_placeholder(real)
    assert not is_placeholder_taxonomy("Streptomyces sp.")


def _run(tmp_path, taxonomy, source):
    return cli.run_one_strain(strain_id="ABC-12", display_name="ABC-12", input_zip=str(tmp_path / "missing.zip"),
                              outdir=str(tmp_path / "runs"), mode="gold", taxonomy=taxonomy, source=source)


def test_run_refuses_unedited_taxonomy(tmp_path, capsys):
    r = _run(tmp_path, "<Genus species>", "soil")
    assert r == {"status": "TAXONOMY_PLACEHOLDER", "written": False}
    assert not (tmp_path / "runs").exists()


def test_run_refuses_unedited_source(tmp_path, capsys):
    r = _run(tmp_path, "Streptomyces sp.", "<isolation source>")
    assert r == {"status": "SOURCE_PLACEHOLDER", "written": False}
    assert "SOURCE_PLACEHOLDER" in capsys.readouterr().err
