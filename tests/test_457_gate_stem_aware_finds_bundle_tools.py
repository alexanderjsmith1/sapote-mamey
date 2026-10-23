"""tools/gate_stem_aware.py imports `tools.placement_root_variants` lazily. The R renderer runs it as a script from any directory,
and on GitHub CI (.456) the `mamey` package was installed but the bundle's `tools` package was not importable:
'No module named tools'. The script must put the bundle root on sys.path itself."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_lazy_tools_import_works_when_mamey_is_installed_but_tools_is_not(tmp_path):
    site = tmp_path / "site"
    site.mkdir()
    (site / "mamey").symlink_to(ROOT / "mamey")   # like `pip install -e .`: mamey importable, tools not
    code = (
        "import runpy, sys\n"
        f"sys.path.insert(0, {str(ROOT / 'tools')!r})\n"   # what launching the file as a script does
        f"runpy.run_path({str(ROOT / 'tools' / 'gate_stem_aware.py')!r}, run_name='gate_stem_aware_probe')\n"
        "from tools.placement_root_variants import verify_diagnostic\n"
        "print('OK', callable(verify_diagnostic))\n")
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env.update(PYTHONPATH=str(site), PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, env=env, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "OK True" in r.stdout
