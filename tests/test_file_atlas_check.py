"""Atlas freshness admission must be deterministic and leave checked trees untouched."""
import hashlib
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("file_atlas_check_owner", ROOT / "tools/file_atlas.py")
atlas = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(atlas)


def snapshot(root):
    return {str(p.relative_to(root)): (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
            for p in root.rglob("*") if p.is_file()}


@pytest.fixture
def tree(tmp_path, monkeypatch):
    for name in ("tools", "mamey", "docs", "tests"):
        (tmp_path / name).mkdir()
    (tmp_path / "tools/alpha.py").write_text('"""Fabricated atlas purpose."""\n')
    monkeypatch.setattr(atlas, "ROOT", tmp_path)
    return tmp_path


def generate(tree):
    return atlas.main(["--out", str(tree / "docs/FILE_ATLAS.csv"), "--md", str(tree / "docs/FILE_ATLAS.md")])


def test_current_defaults_and_second_generation_are_stable(tree):
    assert generate(tree) == 0
    before = snapshot(tree)
    assert atlas.main(["--check"]) == 0
    assert snapshot(tree) == before
    contents = {str(p.relative_to(tree)): p.read_bytes() for p in (tree / "docs").iterdir()}
    assert generate(tree) == 0
    assert contents == {str(p.relative_to(tree)): p.read_bytes() for p in (tree / "docs").iterdir()}


@pytest.mark.parametrize("change", ["csv", "markdown", "source", "membership", "test_reference"])
def test_stale_check_refuses_without_writing(tree, change):
    assert generate(tree) == 0
    targets = {"csv": "docs/FILE_ATLAS.csv", "markdown": "docs/FILE_ATLAS.md", "source": "tools/alpha.py", "membership": "mamey/beta.py", "test_reference": "tests/test_alpha.py"}
    target = tree / targets[change]
    target.write_text('"""alpha changed fabricated purpose."""\n')
    before = snapshot(tree)
    assert atlas.main(["--check"]) == 1
    assert snapshot(tree) == before


def test_missing_and_unreadable_outputs_create_nothing(tree):
    before = snapshot(tree)
    assert atlas.main(["--check", "--out", str(tree / "missing-parent/atlas.csv")]) == 1
    assert not (tree / "missing-parent").exists()
    assert atlas.main(["--check", "--md", str(tree / "docs")]) == 1
    assert snapshot(tree) == before


def test_explicit_single_output_has_explicit_scope(tree):
    assert generate(tree) == 0
    (tree / "docs/FILE_ATLAS.md").write_text("fabricated stale markdown")
    before = snapshot(tree)
    assert atlas.main(["--check", "--out", str(tree / "docs/FILE_ATLAS.csv")]) == 0
    assert atlas.main(["--check"]) == 1
    assert snapshot(tree) == before


@pytest.mark.parametrize("arguments", [["--check", "--orphans"], ["--check", "--out", "same", "--md", "same"]])
def test_invalid_modes_refuse_before_reading_or_writing(tree, arguments, monkeypatch):
    monkeypatch.setattr(atlas, "build", lambda: pytest.fail("invalid arguments must not build"))
    before = snapshot(tree)
    with pytest.raises(SystemExit) as error:
        atlas.main(arguments)
    assert error.value.code == 2
    assert snapshot(tree) == before



def test_generation_and_no_output_stdout_contract(tree, capsys):
    assert atlas.main([]) == 0
    assert capsys.readouterr().out == ""
    assert generate(tree) == 0
    assert capsys.readouterr().out == (
        f"wrote {tree / 'docs/FILE_ATLAS.csv'}\n"
        f"wrote {tree / 'docs/FILE_ATLAS.md'}\n"
    )


def test_successful_check_stdout_contract(tree, capsys):
    assert generate(tree) == 0
    capsys.readouterr()
    assert atlas.main(["--check"]) == 0
    assert capsys.readouterr().out == "FILE ATLAS CURRENT: 2 output(s), 1 source files\n"
    assert atlas.main(["--check", "--out", str(tree / "docs/FILE_ATLAS.csv")]) == 0
    assert capsys.readouterr().out == "FILE ATLAS CURRENT: 1 output(s), 1 source files\n"


@pytest.mark.parametrize("csv_state, md_state", [
    ("stale", "missing"),
    ("missing", "stale"),
    ("directory", "stale"),
    ("current", "stale"),
    ("stale", "current"),
])
def test_failed_check_stdout_preserves_output_order(tree, capsys, csv_state, md_state):
    assert generate(tree) == 0
    capsys.readouterr()
    paths = [tree / "docs/FILE_ATLAS.csv", tree / "docs/FILE_ATLAS.md"]
    expected = []
    for index, state in enumerate((csv_state, md_state)):
        if state == "stale":
            paths[index].write_text("fabricated stale output")
            expected.append(f"FILE ATLAS STALE: {paths[index]}; regenerate with tools/file_atlas.py --out <csv> --md <markdown>\n")
        elif state == "missing":
            paths[index] = tree / f"missing-output-{index}"
            expected.append(f"FILE ATLAS UNREADABLE: {paths[index]} (FileNotFoundError)\n")
        elif state == "directory":
            paths[index] = tree / "docs"
            expected.append(f"FILE ATLAS UNREADABLE: {paths[index]} (IsADirectoryError)\n")
    before = snapshot(tree)
    assert atlas.main(["--check", "--out", str(paths[0]), "--md", str(paths[1])]) == 1
    assert capsys.readouterr().out == "".join(expected)
    assert snapshot(tree) == before


def test_later_write_failure_retains_prior_success_stdout(tree, monkeypatch, capsys):
    csv_path = tree / "docs/FILE_ATLAS.csv"
    md_path = tree / "docs/FILE_ATLAS.md"
    original_write = Path.write_bytes

    def write_or_refuse(path, data):
        if path == md_path:
            raise OSError("fabricated second-output write refusal")
        return original_write(path, data)

    monkeypatch.setattr(Path, "write_bytes", write_or_refuse)
    with pytest.raises(OSError, match="fabricated second-output write refusal"):
        generate(tree)
    assert capsys.readouterr().out == f"wrote {csv_path}\n"
    assert csv_path.is_file() and not md_path.exists()


def test_orphan_stdout_contract(tree, capsys):
    assert atlas.main(["--orphans"]) == 0
    assert capsys.readouterr().out == (
        "1 orphan candidate(s) of 1 files (no importer, no CLI verb, no test naming them):\n"
        f"  {1:5d} loc  {'tools/alpha.py':44s} Fabricated atlas purpose.\n"
    )
