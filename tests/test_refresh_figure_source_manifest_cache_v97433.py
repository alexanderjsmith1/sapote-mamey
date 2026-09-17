import json
import shutil
import subprocess
import sys
from pathlib import Path


def test_source_manifest_ignores_transient_python_caches(tmp_path):
    source = Path(__file__).resolve().parents[1] / "tools/refresh_figure_source_manifest.py"
    script = tmp_path / source.name
    shutil.copyfile(source, script)
    (tmp_path / "tree.nwk").write_text("(A,B);\n")
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    bytecode = cache / "figure.cpython-314.pyc"
    bytecode.write_bytes(b"first")
    (tmp_path / "unused.pyo").write_bytes(b"first")

    def refresh():
        subprocess.run([sys.executable, str(script)], check=True, capture_output=True, text=True)
        return (tmp_path / "MANIFEST.json").read_bytes()

    first = refresh()
    listed = json.loads(first)["files"]
    assert "tree.nwk" in listed
    assert not any("__pycache__" in name or name.endswith((".pyc", ".pyo")) for name in listed)

    bytecode.write_bytes(b"different cache contents")
    (tmp_path / "unused.pyo").write_bytes(b"different cache contents")
    assert refresh() == first
