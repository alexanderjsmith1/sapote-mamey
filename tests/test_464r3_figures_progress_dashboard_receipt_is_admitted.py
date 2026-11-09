"""Progress dashboard: the receipt path is admitted with the artwork and CSV; nothing existing is replaced."""
from datetime import datetime, timedelta, timezone

import pytest

pytest.importorskip("matplotlib")

from mamey.interactive_figures.progress_dashboard import (  # noqa: E402
    ProgressDashboardRefusal,
    ProgressEvent,
    render_progress_dashboard,
)

NOW = datetime(2026, 9, 3, 12, tzinfo=timezone.utc)


def _render(package, stem):
    return render_progress_dashboard(
        [ProgressEvent("Figure renders", NOW - timedelta(hours=2), 4)], now=NOW,
        windows_hours=(24,), title="Synthetic", unit_label="units",
        out_stem=stem, package_dir=package, provenance="synthetic")


def test_symlinked_receipt_is_refused_before_any_write(tmp_path):
    package = tmp_path / "package"; (package / "figures").mkdir(parents=True)
    outside = tmp_path / "outside.json"; outside.write_text("keep")
    (package / "figures" / "progress_receipt.json").symlink_to(outside)
    with pytest.raises(ProgressDashboardRefusal, match="PROGRESS_OUTPUT_OUTSIDE_PACKAGE"):
        _render(package, package / "figures" / "progress")
    assert outside.read_text() == "keep"
    assert not (package / "figures" / "progress.csv").exists()


def test_existing_receipt_is_not_replaced(tmp_path):
    package = tmp_path / "package"; (package / "figures").mkdir(parents=True)
    receipt = package / "figures" / "progress_receipt.json"; receipt.write_text("earlier receipt")
    with pytest.raises(ProgressDashboardRefusal, match="PROGRESS_OUTPUT_NOT_FRESH"):
        _render(package, package / "figures" / "progress")
    assert receipt.read_text() == "earlier receipt"
    assert not (package / "figures" / "progress.csv").exists()


def test_fresh_stem_writes_all_four(tmp_path):
    package = tmp_path / "package"; package.mkdir()
    result = _render(package, package / "figures" / "progress")
    assert result["status"] == "CANDIDATE_RENDERED"
    for name in ("progress.png", "progress.svg", "progress.csv", "progress_receipt.json"):
        assert (package / "figures" / name).exists(), name
