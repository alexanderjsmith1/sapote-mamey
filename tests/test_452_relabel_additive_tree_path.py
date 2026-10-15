import runpy
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest

@pytest.mark.parametrize("name", ["source.nwk", "source"])
def test_relabeling_non_treefile_input_preserves_original(tmp_path, monkeypatch, name):
    source = tmp_path / name
    original = "(raw:0.1,reference_OUTGROUP:0.1);"
    source.write_text(original)
    genomes = tmp_path / "genomes"
    genomes.mkdir()
    (genomes / "raw.fna").write_text(">id Syntheticus sp. strain SYN-R\nACGT\n")
    commands = []
    def run(cmd, **kwargs):
        commands.append(cmd)
        return SimpleNamespace(returncode=0, stdout="", stderr="")
    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(sys, "argv", ["relabel_and_render", str(source), str(genomes), str(tmp_path / "out.png"), "synthetic", "OUTGROUP"])
    script = Path(__file__).resolve().parents[1] / "tools/relabel_and_render.py"
    with pytest.raises(SystemExit) as stopped:
        runpy.run_path(str(script), run_name="__main__")
    assert stopped.value.code == 0
    assert source.read_text() == original
    assert Path(commands[0][2]) != source
    assert Path(commands[0][2]).exists()
