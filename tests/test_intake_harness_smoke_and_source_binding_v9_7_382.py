"""intake_harness P1-3/P1-4 (v9.7.382): no retired smoke mode; own repo root bound before mamey import."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tools" / "intake_harness.py"


def test_parser_rejects_retired_smoke_mode():
    # the REAL harness parser must not accept --mode smoke (removed at v9.7.161)
    r = subprocess.run([sys.executable, str(HARNESS), "--mode", "smoke",
                        "--batch-report", "x", "y"],
                       capture_output=True, text=True)
    assert r.returncode != 0
    assert "invalid choice: 'smoke'" in r.stderr


def test_gold_is_the_default_mode():
    r = subprocess.run([sys.executable, str(HARNESS), "--help"], capture_output=True, text=True)
    assert r.returncode == 0
    flat = r.stdout.replace(" ", "").replace("\n", "")
    assert "{standard,gold}" in flat and "smoke" not in flat.split("--mode")[1][:40]


def test_harness_binds_own_root_under_hostile_pythonpath(tmp_path):
    # a fake 'mamey' on PYTHONPATH must NOT shadow the real engine: the harness prepends its own root.
    fake = tmp_path / "fake_site"
    (fake / "mamey").mkdir(parents=True)
    (fake / "mamey" / "__init__.py").write_text("SENTINEL = 'HOSTILE'\n")
    probe = (
        "import importlib.util, os, sys\n"
        f"spec = importlib.util.spec_from_file_location('intake_harness', r'{HARNESS}')\n"
        "m = importlib.util.module_from_spec(spec)\n"
        "try:\n    spec.loader.exec_module(m)\n"
        "except SystemExit:\n    pass\n"
        "import mamey\n"
        f"assert os.path.abspath(r'{ROOT}') in os.path.abspath(mamey.__file__), mamey.__file__\n"
        "assert not hasattr(mamey, 'SENTINEL'), 'hostile mamey shadowed the engine'\n"
        "print('OK')\n"
    )
    env = dict(os.environ, PYTHONPATH=str(fake))
    r = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, env=env)
    assert r.returncode == 0 and "OK" in r.stdout, r.stderr
