from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


_PATH = Path(__file__).resolve().parents[1] / "tools" / "ani_caption_check.py"
_SPEC = importlib.util.spec_from_file_location("ani_caption_check", _PATH)
assert _SPEC and _SPEC.loader
ani = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(ani)


def _receipt(path: Path, source: Path, metric: str, **extra) -> Path:
    payload = {"metric": metric, "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(), **extra}
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


@pytest.mark.parametrize("value", [94.0, 95.0, 96.0])
def test_nucleotide_ani_boundary_is_inclusive(tmp_path: Path, value: float) -> None:
    caption = tmp_path / "caption.md"
    caption.write_text(f"Genome comparison: nucleotide ANI = {value:.1f}%.", encoding="utf-8")
    result = ani.check_caption_or_table(caption, _receipt(tmp_path / "receipt.json", caption, "nucleotide_ANI"))
    assert result["status"] == "BOUNDARY"
    assert result["boundary_values_pct"] == [value]


def test_core_scg_aai_table_is_not_relabelled_as_ani(tmp_path: Path) -> None:
    table = tmp_path / "identity.tsv"
    table.write_text("metric\tidentity_pct\ncore_SCG_AAI\t93.2\n", encoding="utf-8")
    result = ani.check_caption_or_table(table, _receipt(tmp_path / "receipt.json", table, "core_SCG_AAI"))
    assert result["metric"] == "core_SCG_AAI"
    assert result["display_label"] == "AAI"
    assert result["status"] == "NON_BOUNDARY"


def test_receipt_metric_conflict_and_stale_input_fail_closed(tmp_path: Path) -> None:
    caption = tmp_path / "caption.txt"
    caption.write_text("Core SCG AAI was 95.1%.", encoding="utf-8")
    receipt = _receipt(tmp_path / "receipt.json", caption, "nucleotide_ANI")
    with pytest.raises(ani.CaptionMetricError, match="ANI_AAI_LABEL_CONFLICT"):
        ani.check_caption_or_table(caption, receipt)
    caption.write_text("Nucleotide ANI was 95.1% after editing.", encoding="utf-8")
    with pytest.raises(ani.CaptionMetricError, match="ANI_INPUT_HASH_MISMATCH"):
        ani.check_caption_or_table(caption, receipt)
