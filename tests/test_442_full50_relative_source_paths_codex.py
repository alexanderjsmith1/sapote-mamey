"""The full50 wrapper runs the engine in bundle cwd, so input paths need caller binding."""

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_full50_forwards_caller_relative_inputs_as_absolute(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "full50_relative_paths", ROOT / "tools" / "emit_modeb_template_full50.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "mamey_run.py").write_text("")
    (tmp_path / "package").mkdir()
    for dirname in ("cohort", "references", "regions"):
        (tmp_path / dirname).mkdir()
    (tmp_path / "metadata.tsv").write_text("strain\tgenus\n")
    (tmp_path / "venv" / "bin").mkdir(parents=True)
    (tmp_path / "venv" / "bin" / "python").write_text("")
    monkeypatch.chdir(tmp_path)
    seen = {}

    def fake_build(bundle_arg, python, package_arg, bgc, source_args):
        seen.update(bundle=bundle_arg, python=python, package=package_arg, sources=source_args)
        return "", {"section_count": 50}

    monkeypatch.setattr(module, "build", fake_build)
    assert module.main(["--bundle", "bundle", "--package", "package",
                        "--python", "./venv/bin/python", "--bgc", "BGC001",
                        "--out", "rendered.md", "--cohort-dir", "cohort",
                        "--reference-dir", "references", "--strain-metadata", "metadata.tsv",
                        "--bigscape-regions-dir", "regions"]) == 0
    assert seen["bundle"] == bundle
    assert seen["python"] == str(tmp_path / "venv" / "bin" / "python")
    assert seen["package"] == tmp_path / "package"
    assert seen["sources"] == [
        "--cohort-dir", str(tmp_path / "cohort"),
        "--reference-dir", str(tmp_path / "references"),
        "--strain-metadata", str(tmp_path / "metadata.tsv"),
        "--bigscape-regions-dir", str(tmp_path / "regions")]
