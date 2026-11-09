"""`blastp-status` refuses a non-package path cleanly and never claims a ClusterBlast fallback.

After EVIDENCE_TOOLS card 23, `blastp_status` raises for a path that is not a package; the CLI let
that become a traceback and exit 1. A BGC without an overlay was reported as "ClusterBlast
fallback", although a missing overlay is not evidence that ClusterBlast was used.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(*args):
    return subprocess.run([sys.executable, "mamey_run.py", "blastp-status", *args], cwd=ROOT,
                          capture_output=True, text=True, timeout=120)


def test_a_missing_package_is_refused_with_exit_2_and_one_line(tmp_path):
    res = _run("--package", str(tmp_path / "nope"))
    assert res.returncode == 2, res.stderr
    assert "Traceback" not in res.stderr
    assert [l for l in res.stderr.splitlines() if l.startswith("REFUSED: blastp-status")]


def test_no_overlay_is_not_called_a_clusterblast_fallback(tmp_path):
    pkg = tmp_path / "package"
    pkg.mkdir()
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": "EXAMPLE"}), encoding="utf-8")
    res = _run("--package", str(pkg))
    assert res.returncode == 0, res.stderr
    assert "ClusterBlast fallback" not in res.stdout
    assert "not assessed" in res.stdout


def test_help_no_longer_advertises_a_fallback_flag():
    out = subprocess.run([sys.executable, "mamey_run.py", "--help"], cwd=ROOT, capture_output=True,
                         text=True, timeout=120).stdout
    assert "flag ClusterBlast fallback" not in " ".join(out.split())
