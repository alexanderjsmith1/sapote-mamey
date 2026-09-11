from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "compile_figure_owner_review.py"
HEADER = "figure_set_id\tdecision\towner_comment\trequested_changes\ttarget_use\n"


def _manifest(path: Path, ids=("F01", "F02", "F03")) -> Path:
    payload = {
        "schema_version": "figure_set_manifest_v1",
        "figures": [
            {
                "figure_set_id": figure_id,
                "title": f"Figure {figure_id}",
                "svg": f"figures/{figure_id}.svg",
                "data_csv": f"data/{figure_id}.csv",
                "caption_methods": f"text/{figure_id}.md",
            }
            for figure_id in ids
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _run(tmp_path: Path, decision_text: str, *, manifest: Path | None = None, name="out"):
    manifest = manifest or _manifest(tmp_path / "manifest.json")
    decisions = tmp_path / f"decisions-{name}.tsv"
    decisions.write_text(decision_text, encoding="utf-8")
    out = tmp_path / name
    result = subprocess.run(
        [sys.executable, str(TOOL), "--manifest", str(manifest), "--decisions", str(decisions), "--outdir", str(out)],
        text=True, capture_output=True, check=False,
    )
    return result, out


def test_compiles_decisions_and_preserves_unreviewed(tmp_path):
    text = HEADER + "F01\tKEEP\tUseful\t\tmain paper\nF02\tREDESIGN\tNeeds filtering\tUse within-genus preset\tappendix\n"
    result, out = _run(tmp_path, text)
    assert result.returncode == 0, result.stderr
    payload = json.loads((out / "OWNER_REVIEW_PLAN.json").read_text())
    assert payload["counts"] == {"DROP": 0, "HOLD": 0, "KEEP": 1, "REDESIGN": 1, "UNREVIEWED": 1}
    assert payload["publication_selection_performed"] is False
    assert [row["decision"] for row in payload["figures"]] == ["KEEP", "REDESIGN", "UNREVIEWED"]
    assert all(str(tmp_path) not in (out / name).read_text() for name in ("OWNER_REVIEW_PLAN.json", "OWNER_REVIEW_PLAN.tsv", "OWNER_REVIEW_SUMMARY.md"))


def test_output_is_deterministic(tmp_path):
    text = HEADER + "F01\tDROP\tNot informative\t\tinternal review\n"
    first, out1 = _run(tmp_path, text, name="out1")
    second, out2 = _run(tmp_path, text, name="out2")
    assert first.returncode == second.returncode == 0
    for name in ("OWNER_REVIEW_PLAN.json", "OWNER_REVIEW_PLAN.tsv", "OWNER_REVIEW_SUMMARY.md"):
        assert (out1 / name).read_bytes() == (out2 / name).read_bytes()


def test_unknown_id_refuses_without_output(tmp_path):
    result, out = _run(tmp_path, HEADER + "F99\tKEEP\t\t\t\n")
    assert result.returncode == 2
    assert "DECISIONS_FIGURE_ID_UNKNOWN" in result.stderr
    assert not out.exists()


def test_duplicate_decision_refuses_without_output(tmp_path):
    result, out = _run(tmp_path, HEADER + "F01\tKEEP\t\t\t\nF01\tKEEP\t\t\t\n")
    assert result.returncode == 2
    assert "DECISIONS_FIGURE_ID_DUPLICATE" in result.stderr
    assert not out.exists()


def test_duplicate_manifest_id_refuses_without_output(tmp_path):
    manifest = _manifest(tmp_path / "manifest.json", ids=("F01", "F01"))
    result, out = _run(tmp_path, HEADER + "F01\tKEEP\t\t\t\n", manifest=manifest)
    assert result.returncode == 2
    assert "MANIFEST_FIGURE_ID_DUPLICATE" in result.stderr
    assert not out.exists()


def test_invalid_decision_refuses_without_output(tmp_path):
    result, out = _run(tmp_path, HEADER + "F01\tACCEPT\t\t\t\n")
    assert result.returncode == 2
    assert "DECISIONS_VALUE_INVALID" in result.stderr
    assert not out.exists()


def test_redesign_requires_comment_and_requested_changes(tmp_path):
    result, out = _run(tmp_path, HEADER + "F01\tREDESIGN\t\t\t\n")
    assert result.returncode == 2
    assert "DECISIONS_COMMENT_REQUIRED" in result.stderr
    assert not out.exists()
    result, out = _run(tmp_path, HEADER + "F01\tREDESIGN\tNeeds work\t\t\n", name="out2")
    assert result.returncode == 2
    assert "DECISIONS_CHANGES_REQUIRED" in result.stderr
    assert not out.exists()


def test_header_is_exact_and_width_is_uniform(tmp_path):
    result, out = _run(tmp_path, "decision\tfigure_set_id\nKEEP\tF01\n")
    assert result.returncode == 2
    assert "DECISIONS_HEADER_INVALID" in result.stderr
    assert not out.exists()


def test_unsafe_manifest_locator_refuses(tmp_path):
    manifest = _manifest(tmp_path / "manifest.json")
    payload = json.loads(manifest.read_text())
    payload["figures"][0]["svg"] = str(tmp_path / "private.svg")
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    result, out = _run(tmp_path, HEADER + "F01\tKEEP\t\t\t\n", manifest=manifest)
    assert result.returncode == 2
    assert "MANIFEST_LOCATOR_UNSAFE" in result.stderr
    assert not out.exists()


def test_existing_output_refuses_without_mutation(tmp_path):
    manifest = _manifest(tmp_path / "manifest.json")
    decisions = tmp_path / "decisions.tsv"
    decisions.write_text(HEADER + "F01\tKEEP\t\t\t\n", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    sentinel = out / "sentinel.txt"
    sentinel.write_text("unchanged", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(TOOL), "--manifest", str(manifest), "--decisions", str(decisions), "--outdir", str(out)],
        text=True, capture_output=True, check=False,
    )
    assert result.returncode == 2
    assert "OUTPUT_EXISTS" in result.stderr
    assert sentinel.read_text() == "unchanged"
    assert list(out.iterdir()) == [sentinel]


def test_tsv_output_is_rectangular(tmp_path):
    text = HEADER + 'F01\tKEEP\t"Useful | with note"\t\tmain paper\n'
    result, out = _run(tmp_path, text)
    assert result.returncode == 0, result.stderr
    with (out / "OWNER_REVIEW_PLAN.tsv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle, delimiter="\t"))
    assert {len(row) for row in rows} == {9}
