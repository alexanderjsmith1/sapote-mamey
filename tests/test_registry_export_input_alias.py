"""Synthetic registry export controls; no scientific registry is read."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools/export_registry_inventory_csv.py"


@pytest.mark.parametrize("mode", ["direct", "symlink", "hardlink", "existing", "new"])
def test_registry_export_preserves_source(tmp_path, mode):
    source = tmp_path / "registry.json"
    source.write_text(json.dumps([{"id": "SOFTWARE_ONLY", "name": "synthetic fixture"}]), encoding="utf-8")
    output = tmp_path / "output.csv"
    if mode == "direct":
        output = source
    elif mode == "symlink":
        output.symlink_to(source)
    elif mode == "hardlink":
        os.link(source, output)
    elif mode == "existing":
        output.write_bytes(b"previous generated output")
    before = source.read_bytes()
    result = subprocess.run([sys.executable, "-B", str(TOOL), "--registry", str(source), "--output", str(output)], capture_output=True, text=True)
    assert source.read_bytes() == before
    if mode in ("direct", "symlink", "hardlink"):
        assert result.returncode == 2
        assert "output must differ from the source JSON" in result.stderr
    else:
        assert result.returncode == 0, result.stderr
        assert output.read_text(encoding="utf-8").startswith("id,name,")
