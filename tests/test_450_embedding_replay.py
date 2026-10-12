"""Saved-coordinate contracts preserve rosters, values and explicit omissions."""
import csv
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from tools import _embedding_replay as replay


def fixture_manifest(tmp_path, *, method="trimap", exclusions="p2\n"):
    """Make a complete portable manifest with one deliberately excluded point."""
    coordinates = tmp_path / "coordinates.tsv"
    metadata = tmp_path / "metadata.tsv"
    excluded = tmp_path / "exclusions.txt"
    coordinates.write_text("id\tx\ty\np1\t1.25\t-2.5\np2\t3\t4\np3\t5\t6\n")
    metadata.write_text("id\tgroup\np1\tReference\np2\tStudy\np3\tStudy\n")
    excluded.write_text(exclusions)
    spec = {"schema": replay.SCHEMA, "method": method, "generation": "control-v1",
            "columns": {"id": "id", "x": "x", "y": "y", "group": "group"},
            "palette": {"Reference": "#666666", "Study": "#0072B2"},
            "group_order": ["Reference", "Study"],
            "expected_points": 2 if exclusions else 3}
    for label, path in [("coordinates", coordinates), ("metadata", metadata), ("exclusions", excluded)]:
        spec[label] = {"path": path.name, "sha256": replay.binding(path)["sha256"]}
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(spec))
    return manifest


def change_spec(manifest, update):
    """Change an owned fixture manifest for refusal tests."""
    spec = json.loads(manifest.read_text())
    update(spec)
    manifest.write_text(json.dumps(spec))


def change_input(manifest, label, value):
    """Make a new deliberately invalid input with a valid transport hash."""
    spec = json.loads(manifest.read_text())
    path = manifest.parent / spec[label]["path"]
    path.write_text(value)
    spec[label]["sha256"] = replay.binding(path)["sha256"]
    manifest.write_text(json.dumps(spec))


def fake_draw(plan, output):
    """Write a control artifact, never a claimed scientific figure."""
    path = output / "control.txt"
    path.write_text("control artifact")
    return [path]


@pytest.mark.parametrize("method", ["trimap", "tsne"])
def test_exact_points_and_exclusion_ledger(tmp_path, method):
    manifest = fixture_manifest(tmp_path, method=method)
    receipt = replay.run_replay(manifest, tmp_path / "output", draw=fake_draw)
    assert receipt["counts"] == {"input_rows": 3, "drawn_rows": 2, "excluded_rows": 1,
                                 "drawn_by_group": {"Reference": 1, "Study": 1}}
    rows = list(csv.DictReader((tmp_path / "output/POINTS.tsv").open(), delimiter="\t"))
    assert rows[0]["x"] == "1.25" and rows[0]["y"] == "-2.5"
    assert rows[1]["drawn"] == "False" and rows[1]["reason"] == "EXPLICIT_EXCLUSION"
    assert receipt["method"] == method and receipt["mode"] == "replot"
    for output in receipt["outputs"]:
        assert replay.binding(Path(output["path"])) == output


@pytest.mark.parametrize("label,value", [
    ("coordinates", "id\tx\ty\np1\t1\t2\np1\t3\t4\n"),
    ("coordinates", "id\tx\ty\np1\tnan\t2\np2\t3\t4\np3\t5\t6\n"),
    ("coordinates", "id\tx\ty\np1\tinf\t2\np2\t3\t4\np3\t5\t6\n"),
    ("coordinates", "id\tx\ty\np1\t1\t2\textra\np2\t3\t4\np3\t5\t6\n"),
    ("metadata", "id\tgroup\np1\tReference\np2\tStudy\n"),
    ("metadata", "id\tgroup\np1\tReference\np2\tStudy\np3\t\n"),
    ("exclusions", "unknown\n"), ("exclusions", "p2\np2\n"),
])
def test_invalid_data_refused_before_output(tmp_path, label, value):
    manifest = fixture_manifest(tmp_path)
    change_input(manifest, label, value)
    output = tmp_path / "output"
    with pytest.raises(replay.ReplayRefusal):
        replay.run_replay(manifest, output, draw=fake_draw)
    assert not output.exists()


@pytest.mark.parametrize("field,value", [("expected_points", 3), ("expected_points", True),
    ("method", "pcoa"), ("palette", {"Study": "#0072B2"}), ("unexpected", "ignored?"),
    ("group_order", ["Study", "Study"])])
def test_manifest_contract_refuses_mismatch(tmp_path, field, value):
    manifest = fixture_manifest(tmp_path)
    change_spec(manifest, lambda spec: spec.update({field: value}))
    with pytest.raises(replay.ReplayRefusal):
        replay.prepare_replay(manifest)


def test_hash_mismatch_refused(tmp_path):
    manifest = fixture_manifest(tmp_path)
    (tmp_path / "coordinates.tsv").write_text("changed")
    with pytest.raises(replay.ReplayRefusal, match="hash mismatch"):
        replay.prepare_replay(manifest)


def test_post_draw_drift_has_no_final_receipt(tmp_path):
    manifest = fixture_manifest(tmp_path)
    def drift(plan, output):
        artifacts = fake_draw(plan, output)
        (tmp_path / "coordinates.tsv").write_text("changed after validation")
        return artifacts
    with pytest.raises(replay.ReplayRefusal, match="changed during replay"):
        replay.run_replay(manifest, tmp_path / "output", draw=drift)
    assert not (tmp_path / "output/REPLAY_RECEIPT.json").exists()


def test_empty_explicit_exclusions_and_relocation(tmp_path):
    import shutil
    original = tmp_path / "original"
    original.mkdir()
    manifest = fixture_manifest(original, exclusions="")
    before = replay.prepare_replay(manifest)
    relocated = tmp_path / "relocated"
    shutil.copytree(original, relocated)
    after = replay.prepare_replay(relocated / "manifest.json")
    assert before["points"] == after["points"]
    assert before["membership_sha256"] == after["membership_sha256"]


def test_occupied_output_preserved(tmp_path):
    manifest = fixture_manifest(tmp_path)
    output = tmp_path / "output"
    output.mkdir()
    protected = output / "keep.txt"
    protected.write_text("keep")
    with pytest.raises(replay.ReplayRefusal, match="new or empty"):
        replay.run_replay(manifest, output, draw=fake_draw)
    assert protected.read_text() == "keep"


def test_real_matplotlib_outputs_and_plain_axes(tmp_path):
    from mamey.figure_policy import svg_visible_text
    manifest = fixture_manifest(tmp_path)
    receipt = replay.run_replay(manifest, tmp_path / "output")
    text = " ".join(svg_visible_text((tmp_path / "output/embedding.svg").read_text()))
    assert "TriMap" in text and "nan" not in text and "%" not in text
    assert text.index("Reference") < text.index("Study")
    assert len(receipt["outputs"]) == 4 and receipt["renderer"] == "matplotlib"


def test_cli_validate_only_needs_no_output_or_fitting_library(tmp_path):
    manifest = fixture_manifest(tmp_path)
    source = Path(replay.__file__).resolve().parents[1]
    completed = subprocess.run([sys.executable, str(source / "tools/protein_embedding_replay.py"),
                               "--manifest", str(manifest), "--validate-only"],
                              cwd=tmp_path, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    assert "drawn_rows" in completed.stdout


def replace_second_read(monkeypatch, target, replacement):
    """Swap a valid payload only while its second read is open, then restore it."""
    previous = target.read_bytes()
    original_open = Path.open
    state = {"reads": 0, "swapped": False}
    @contextmanager
    def swapped(args, kwargs):
        target.write_bytes(replacement)
        try:
            with original_open(target, *args, **kwargs) as stream:
                yield stream
        finally:
            target.write_bytes(previous)
    def guarded_open(path, *args, **kwargs):
        mode = args[0] if args else kwargs.get("mode", "r")
        if path == target and "r" in mode:
            state["reads"] += 1
            if state["reads"] == 2:
                state["swapped"] = True
                return swapped(args, kwargs)
        return original_open(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", guarded_open)
    return state, previous


@pytest.mark.parametrize("label,replacement", [
    ("coordinates", b"id\tx\ty\np1\t99\t-2.5\np2\t3\t4\np3\t5\t6\n"),
    ("metadata", b"id\tgroup\np1\tStudy\np2\tStudy\np3\tReference\n"),
    ("exclusions", b"p3\n"),
])
def test_replace_read_restore_refused_before_output(tmp_path, monkeypatch, label, replacement):
    manifest = fixture_manifest(tmp_path)
    spec = json.loads(manifest.read_text())
    target = manifest.parent / spec[label]["path"]
    state, previous = replace_second_read(monkeypatch, target, replacement)
    output = tmp_path / "output"
    with pytest.raises(replay.ReplayRefusal, match="consumed input hash mismatch"):
        replay.run_replay(manifest, output, draw=fake_draw)
    assert state["swapped"] is True
    assert target.read_bytes() == previous
    assert not output.exists()


def test_manifest_binding_and_parse_use_one_snapshot(tmp_path, monkeypatch):
    manifest = fixture_manifest(tmp_path)
    original = manifest.read_bytes()
    alternative = json.loads(original)
    alternative["method"] = "tsne"
    state, _ = replace_second_read(monkeypatch, manifest, json.dumps(alternative).encode())
    plan = replay.prepare_replay(manifest)
    assert plan["spec"]["method"] == "trimap"
    assert plan["inputs"]["manifest"]["sha256"] == hashlib.sha256(original).hexdigest()
    assert plan["inputs"]["manifest"]["bytes"] == len(original)
    assert state["swapped"] is False


@pytest.mark.parametrize("separator", ["\u0085", "\u2028", "\u2029", "\r\n", "\n"])
def test_snapshot_tsv_preserves_physical_csv_line_parsing(tmp_path, separator):
    table = tmp_path / "physical_lines.tsv"
    raw = ("\ufeffid\tx\ty\tnotes\r\np1\t1\t2\t\"left" + separator
           + "right\"\r\np2\t3\t4\tplain\r\n").encode("utf-8")
    table.write_bytes(raw)
    with table.open(newline="", encoding="utf-8-sig") as stream:
        legacy = list(csv.DictReader(stream, delimiter="\t"))
    expected = {row["id"]: row for row in legacy}
    assert replay.rows_by_id(table, "id", ["id", "x", "y"]) == expected
    assert replay.rows_by_id(table, "id", ["id", "x", "y"],
                             expected_sha256=hashlib.sha256(raw).hexdigest()) == expected


def test_snapshot_hash_and_size_are_from_exact_consumed_bytes(tmp_path, monkeypatch):
    path = tmp_path / "snapshot.tsv"
    path.write_bytes(b"original on disk")
    original_read = Path.read_bytes
    consumed = b"different consumed bytes"
    def substituted(target):
        return consumed if target == path else original_read(target)
    monkeypatch.setattr(Path, "read_bytes", substituted)
    raw, record = replay.read_snapshot(path)
    assert raw == consumed
    assert record == {"path": str(path.resolve()), "bytes": len(consumed),
                      "sha256": hashlib.sha256(consumed).hexdigest()}
    with pytest.raises(replay.ReplayRefusal, match="consumed input hash mismatch"):
        replay.read_snapshot(path, expected_sha256=hashlib.sha256(b"original on disk").hexdigest())
