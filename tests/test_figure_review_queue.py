from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

import mamey.figure_review_queue as review_queue
from mamey.figure_review_queue import FigureReviewQueueError, build_review_queue
from mamey.interactive_figures.figure_set_renderer import render_tranche


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(root: Path, count: int = 3) -> Path:
    (root / "figures").mkdir(parents=True)
    (root / "text").mkdir()
    (root / "data").mkdir()
    figures = []
    for index in range(1, count + 1):
        fid = f"FS{index:03d}"
        image = root / "figures" / f"{fid}.svg"
        caption = root / "text" / f"{fid}.md"
        data = root / "data" / f"{fid}.csv"
        image.write_text(f'<svg xmlns="http://www.w3.org/2000/svg"><text>{fid}</text></svg>\n')
        caption.write_text(
            f"# {fid}\n\n## Caption\n\nDetailed traveling caption {index}.\n\n## Methods\n\nExact method {index}.\n"
        )
        data.write_text("group\tvalue\nA\t1\n")
        figures.append(
            {
                "figure_set_id": fid,
                "title": f"Figure {index}",
                "svg": f"figures/{fid}.svg",
                "caption_methods": f"text/{fid}.md",
                "data_csv": f"data/{fid}.csv",
                "svg_sha256": _sha(image),
                "text_sha256": _sha(caption),
                "data_sha256": _sha(data),
            }
        )
    manifest = root / "FIGURE_MANIFEST.json"
    manifest.write_text(json.dumps({"figures": figures}, indent=2) + "\n")
    return manifest


def _queue(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def test_builds_paginated_queue_without_copying_images(tmp_path):
    root = tmp_path / "atlas"
    manifest = _fixture(root)
    decisions = root / "OWNER_DECISIONS.tsv"
    decisions.write_text(
        "figure_id\tdecision\tdecision_note\nFS001\tKEEP\tUseful domain summary\n"
    )
    receipt = build_review_queue(
        manifest, root, root / "owner_review", decisions=decisions, page_size=2
    )
    out = root / "owner_review"
    assert receipt["status"] == "PASS"
    assert receipt["figure_count"] == 3
    assert receipt["page_count"] == 2
    assert receipt["images_copied"] == 0
    assert receipt["decision_source"]["locator"] == "OWNER_DECISIONS.tsv"
    assert receipt["decision_source"]["sha256"] == _sha(decisions)
    assert not list(out.rglob("*.svg"))
    assert len(list((out / "pages").glob("*.html"))) == 2
    rows = _queue(out / "FIGURE_REVIEW_QUEUE.tsv")
    assert rows[0]["decision"] == "KEEP"
    assert rows[0]["decision_note"] == "Useful domain summary"
    assert rows[1]["decision"] == "UNREVIEWED"
    page = (out / "pages" / "PAGE_001.html").read_text()
    assert "Detailed traveling caption 1" in page
    assert "../../figures/FS001.svg" in page


def test_rerender_is_byte_deterministic(tmp_path):
    hashes = []
    for name in ("first", "second"):
        root = tmp_path / name / "atlas"
        manifest = _fixture(root)
        out = root / "owner_review"
        build_review_queue(manifest, root, out, page_size=2)
        hashes.append({p.relative_to(out).as_posix(): _sha(p) for p in out.rglob("*") if p.is_file()})
    assert hashes[0] == hashes[1]


def test_hash_mismatch_refuses_before_output(tmp_path):
    root = tmp_path / "atlas"
    manifest = _fixture(root)
    payload = json.loads(manifest.read_text())
    payload["figures"][0]["svg_sha256"] = "0" * 64
    manifest.write_text(json.dumps(payload))
    out = root / "owner_review"
    with pytest.raises(FigureReviewQueueError, match="FIGURE_REVIEW_HASH_MISMATCH"):
        build_review_queue(manifest, root, out)
    assert not out.exists()


@pytest.mark.parametrize("digest_field", ("svg_sha256", "text_sha256", "data_sha256"))
def test_missing_referenced_artifact_hash_refuses_before_output(tmp_path, digest_field):
    root = tmp_path / "atlas"
    manifest = _fixture(root)
    payload = json.loads(manifest.read_text())
    payload["figures"][0].pop(digest_field)
    manifest.write_text(json.dumps(payload))
    out = root / "owner_review"

    with pytest.raises(
        FigureReviewQueueError,
        match="FIGURE_REVIEW_HASH_REQUIRED",
    ):
        build_review_queue(manifest, root, out)

    assert not out.exists()


@pytest.mark.parametrize("bad", ("../outside.svg", "/tmp/outside.svg", "figures\\bad.svg"))
def test_nonportable_locator_refuses_before_output(tmp_path, bad):
    root = tmp_path / "atlas"
    manifest = _fixture(root)
    payload = json.loads(manifest.read_text())
    payload["figures"][0]["svg"] = bad
    manifest.write_text(json.dumps(payload))
    out = root / "owner_review"
    with pytest.raises(FigureReviewQueueError, match="FIGURE_REVIEW_LOCATOR_INVALID"):
        build_review_queue(manifest, root, out)
    assert not out.exists()


def test_orphan_decision_refuses_before_output(tmp_path):
    root = tmp_path / "atlas"
    manifest = _fixture(root)
    decisions = root / "OWNER_DECISIONS.tsv"
    decisions.write_text("figure_id\tdecision\tdecision_note\nFS999\tKEEP\tUnknown\n")
    out = root / "owner_review"
    with pytest.raises(FigureReviewQueueError, match="FIGURE_REVIEW_DECISION_ORPHAN"):
        build_review_queue(manifest, root, out, decisions=decisions)
    assert not out.exists()


def test_existing_output_is_never_replaced(tmp_path):
    root = tmp_path / "atlas"
    manifest = _fixture(root)
    out = root / "owner_review"
    out.mkdir()
    marker = out / "owner-note.txt"
    marker.write_text("preserve")
    with pytest.raises(FigureReviewQueueError, match="FIGURE_REVIEW_OUTPUT_EXISTS"):
        build_review_queue(manifest, root, out)
    assert marker.read_text() == "preserve"


def test_destination_created_at_publish_is_not_replaced(tmp_path, monkeypatch):
    """A competing empty directory created after the precheck retains its inode."""
    root = tmp_path / "atlas"
    manifest = _fixture(root)
    out = root / "owner_review"
    original_publish = review_queue._publish_stage_noreplace
    competing: dict[str, int] = {}

    def create_competitor_then_publish(stage: Path, destination: Path) -> None:
        destination.mkdir()
        competing["inode"] = destination.stat().st_ino
        original_publish(stage, destination)

    monkeypatch.setattr(
        review_queue, "_publish_stage_noreplace", create_competitor_then_publish
    )
    with pytest.raises(FigureReviewQueueError, match="FIGURE_REVIEW_OUTPUT_EXISTS"):
        build_review_queue(manifest, root, out)

    assert out.is_dir()
    assert out.stat().st_ino == competing["inode"]
    assert list(out.iterdir()) == []
    assert not list(root.glob(".owner_review.stage-*"))


def test_missing_nested_output_parent_is_typed_redacted_cli_refusal(tmp_path):
    root = tmp_path / "private analyst atlas"
    manifest = _fixture(root)
    missing_parent = root / "private new parent"
    out = missing_parent / "review"
    tool = Path(__file__).resolve().parents[1] / "tools" / "build_figure_review_queue.py"

    result = subprocess.run(
        [
            sys.executable,
            str(tool),
            "--manifest",
            str(manifest),
            "--figure-root",
            str(root),
            "--outdir",
            str(out),
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 2
    assert json.loads(result.stderr) == {
        "status": "REFUSED",
        "code": "FIGURE_REVIEW_OUTPUT_PARENT_UNAVAILABLE",
    }
    assert result.stdout == ""
    assert str(tmp_path) not in result.stdout + result.stderr
    assert "Traceback" not in result.stdout + result.stderr
    assert not missing_parent.exists()


def test_decision_register_must_remain_inside_figure_root(tmp_path):
    root = tmp_path / "atlas"
    manifest = _fixture(root)
    decisions = tmp_path / "outside.tsv"
    decisions.write_text("figure_id\tdecision\tdecision_note\nFS001\tKEEP\tok\n")
    out = root / "owner_review"
    with pytest.raises(FigureReviewQueueError, match="FIGURE_REVIEW_DECISIONS_OUTSIDE_ROOT"):
        build_review_queue(manifest, root, out, decisions=decisions)
    assert not out.exists()


def test_consumes_current_twenty_figure_renderer_manifest(tmp_path):
    strains = {}
    for index, sid in enumerate(("SYN-1", "SYN-2", "SYN-3", "SYN-4"), 1):
        strains[sid] = {
            "governance": "GOVERNED",
            "bgcRows": 10 + index,
            "uniquePhysicalGenes": 1000 + index * 50,
            "machineryGenes": 300 + index * 15,
            "classes": {
                "PKS": {"total": 5 + index, "edge": index, "full": 3, "interior": 1},
                "NRPS": {"total": 4 + index, "edge": 1, "full": 2, "interior": 1},
                "RiPP": {"total": 2 + index, "edge": 1, "full": 1, "interior": index - 1},
            },
            "machinery": {
                "Biosynthetic core": [200 + index, 300 + index, 1200 + index],
                "Biosynthetic additional": [250 + index, 350 + index],
                "Resistance": [400 + index],
                "Transport": [300 + index],
                "Regulatory": [150 + index],
            },
            "hostContext": {"group": ("BEE", "ATTINE_ANT", "MOSS", "WASP")[index - 1]},
        }
    source = tmp_path / "widget.json"
    source.write_text(json.dumps({"meta": {"sourceRelease": "synthetic"}, "strains": strains}))
    atlas = tmp_path / "atlas"
    render_receipt = render_tranche(source, atlas)
    assert render_receipt["implemented_count"] == 20

    review = build_review_queue(
        atlas / "FIGURE_MANIFEST.json", atlas, atlas / "owner_review", page_size=7
    )
    assert review["figure_count"] == 20
    assert review["page_count"] == 3
    assert review["images_copied"] == 0
    assert not list((atlas / "owner_review").rglob("*.svg"))
    page = (atlas / "owner_review" / "pages" / "PAGE_001.html").read_text()
    assert "Traveling caption and methods" in page
    assert "Figure question" in page
