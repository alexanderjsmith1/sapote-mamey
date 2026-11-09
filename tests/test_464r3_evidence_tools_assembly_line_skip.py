"""The two assembly-line [SKIP] messages say what was checked, not that the package is absent."""
import importlib.util
from pathlib import Path

DT = Path(__file__).resolve().parents[1] / "deliverable_tools"


def _load(name):
    spec = importlib.util.spec_from_file_location(name + "_464r3", DT / f"{name}.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def test_missing_table_skip_does_not_claim_no_package(tmp_path, capsys):
    m = _load("assembly_line_pdf")
    assert m.build_pdf("EXAMPLE", str(tmp_path), str(tmp_path / "out")) is None
    text = capsys.readouterr().out
    assert "[SKIP]" in text and "no antismash_modules.csv" in text
    assert "The package may still exist" in text
    assert not (tmp_path / "out").exists()


def test_both_tools_carry_both_messages():
    for name in ("assembly_line_pdf", "assembly_line_widget"):
        src = (DT / f"{name}.py").read_text()
        assert "The package may still exist" in src
        assert "reports the module table only" in src
        assert "no NRPS/PKS assembly-line domains present\")" not in src
