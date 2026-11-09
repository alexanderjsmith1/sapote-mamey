"""Completed render-packet QA: an added SVG or caption that the receipt does not list is an error."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

PIL = pytest.importorskip("PIL")
from PIL import Image  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("render_qc_464r3", ROOT / "tools" / "figure_render_qc.py")
qc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qc)


def _packet(tmp_path):
    folder = tmp_path / "packet"; folder.mkdir()
    png = folder / "PAGE.png"
    Image.new("RGB", (60, 40), "white").save(png, dpi=(300, 300))
    (folder / "PAGE_CAPTION.md").write_text("Caption.\n")
    outputs = [dict(path=str(folder / p.name), bytes=p.stat().st_size,
                    sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(folder.iterdir())]
    (folder / "render_receipt.json").write_text(json.dumps(dict(
        completion_state="COMPLETE", artifact_root=str(folder), outputs=outputs)))
    return folder, png


def _errors(flags):
    return [text for level, text in flags if level == "error"]


def test_clean_packet_passes(tmp_path):
    folder, png = _packet(tmp_path)
    assert not _errors(qc.completed_packet_flags(png))


@pytest.mark.parametrize("name", ["EXTRA.svg", "sub/OTHER.png", "CAPTION_EXTRA.md", "EXTRA.pdf"])
def test_unlisted_member_is_an_error(tmp_path, name):
    folder, png = _packet(tmp_path)
    added = folder / name
    added.parent.mkdir(exist_ok=True)
    added.write_text("added after the receipt")
    errors = _errors(qc.completed_packet_flags(png))
    assert any("not in the completed roster" in e and name in e for e in errors), errors


def test_qa_output_folder_inside_packet_is_not_a_member(tmp_path):
    folder, png = _packet(tmp_path)
    qa = folder / "qa"; qa.mkdir()
    (qa / "preview.png").write_text("qa output")
    assert not _errors(qc.completed_packet_flags(png, qa_out=qa))
