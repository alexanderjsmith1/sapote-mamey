"""build_figure_review_queue: a caption or decision file that is not UTF-8 is a typed exit-2 refusal."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "build_figure_review_queue.py"


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _root(tmp_path, caption_bytes):
    root = tmp_path / "atlas"
    (root / "figures").mkdir(parents=True)
    (root / "text").mkdir()
    image = root / "figures" / "FS001.svg"
    image.write_text('<svg xmlns="http://www.w3.org/2000/svg"><text>FS001</text></svg>\n')
    caption = root / "text" / "FS001.md"
    caption.write_bytes(caption_bytes)
    manifest = root / "FIGURE_MANIFEST.json"
    manifest.write_text(json.dumps({"figures": [{
        "figure_set_id": "FS001", "title": "Figure 1", "svg": "figures/FS001.svg",
        "caption_methods": "text/FS001.md", "svg_sha256": _sha(image), "text_sha256": _sha(caption),
    }]}))
    return root, manifest


def _run(*args):
    return subprocess.run([sys.executable, str(TOOL), *map(str, args)], capture_output=True, text=True)


def test_invalid_utf8_caption_is_refused_with_exit_2(tmp_path):
    root, manifest = _root(tmp_path, b"# FS001\n\n\xff\xfe caption\n")
    out = root / "owner_review"
    result = _run("--manifest", manifest, "--figure-root", root, "--outdir", out)
    assert result.returncode == 2, result.stderr
    assert json.loads(result.stderr.strip().splitlines()[-1])["code"] == "FIGURE_REVIEW_CAPTION_UNREADABLE"
    assert "Traceback" not in result.stderr
    assert not out.exists()


def test_invalid_utf8_decisions_file_is_refused_with_exit_2(tmp_path):
    root, manifest = _root(tmp_path, b"# FS001\n\nCaption.\n")
    decisions = root / "decisions.tsv"
    decisions.write_bytes(b"figure_id\tdecision\tdecision_note\nFS001\tKEEP\t\xff\n")
    out = root / "owner_review"
    result = _run("--manifest", manifest, "--figure-root", root, "--outdir", out, "--decisions", decisions)
    assert result.returncode == 2, result.stderr
    assert json.loads(result.stderr.strip().splitlines()[-1])["code"] == "FIGURE_REVIEW_DECISIONS_UNREADABLE"
    assert not out.exists()
