from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


_CHILD = r'''
import json
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(root))

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt

from mamey.figure_save import save_figure

before = matplotlib.rcParams["svg.hashsalt"]
fig, ax = plt.subplots(figsize=(4, 3))
ax.plot([0, 1, 2], [2, 1, 3], marker="o", label="fixed data")
ax.set_title("Synthetic deterministic control")
ax.set_xlabel("fixed x")
ax.set_ylabel("fixed y")
ax.legend()
receipt = save_figure(
    fig,
    figure_id="synthetic_deterministic_control",
    out_stem=out / "synthetic_deterministic_control",
    renderer="separate_process_fixture",
    package_dir=out,
    provenance="local synthetic fixed data",
)
after = matplotlib.rcParams["svg.hashsalt"]
plt.close(fig)
print(json.dumps({"before": before, "after": after, "receipt": receipt}, sort_keys=True))
'''


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_root() -> Path:
    override = os.environ.get("SVG_SOURCE_ROOT")
    return Path(override).resolve() if override else Path(__file__).resolve().parents[1]


def _run(source_root: Path, output: Path) -> dict:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["MPLCONFIGDIR"] = str(output / "mplconfig")
    completed = subprocess.run(
        [sys.executable, "-c", _CHILD, str(source_root), str(output)],
        cwd=source_root,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def test_canonical_save_is_byte_stable_across_processes_without_rc_leak(tmp_path: Path) -> None:
    source_root = _source_root()
    left = tmp_path / "left"
    right = tmp_path / "right"
    left_result = _run(source_root, left)
    right_result = _run(source_root, right)

    left_svg = left / "synthetic_deterministic_control.svg"
    right_svg = right / "synthetic_deterministic_control.svg"
    left_png = left / "synthetic_deterministic_control.png"
    right_png = right / "synthetic_deterministic_control.png"

    assert left_result["before"] is None
    assert left_result["after"] is None
    assert right_result["before"] is None
    assert right_result["after"] is None
    assert left_svg.read_bytes() == right_svg.read_bytes()
    assert left_png.read_bytes() == right_png.read_bytes()
    assert "Synthetic deterministic control" in left_svg.read_text(encoding="utf-8")
    assert left_result["receipt"]["outputs"]["svg"]["sha256"] == _sha(left_svg)
    assert right_result["receipt"]["outputs"]["svg"]["sha256"] == _sha(right_svg)
    assert left_result["receipt"]["outputs"]["png"]["sha256"] == _sha(left_png)
    assert right_result["receipt"]["outputs"]["png"]["sha256"] == _sha(right_png)


def test_canonical_save_restores_caller_owned_hash_salt(tmp_path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    from mamey.figure_theme import save_figure_pair

    original = matplotlib.rcParams["svg.hashsalt"]
    with matplotlib.rc_context({"svg.hashsalt": "caller-owned"}):
        fig, ax = plt.subplots()
        ax.plot([0, 1], [0, 1])
        save_figure_pair(fig, tmp_path / "caller_owned")
        plt.close(fig)
        assert matplotlib.rcParams["svg.hashsalt"] == "caller-owned"
    assert matplotlib.rcParams["svg.hashsalt"] == original
