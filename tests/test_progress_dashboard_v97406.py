from datetime import datetime, timedelta, timezone

import pytest

from mamey.interactive_figures.progress_dashboard import (
    ProgressDashboardRefusal,
    ProgressEvent,
    render_progress_dashboard,
)


def test_generic_progress_dashboard_uses_actual_units_and_shared_receipt(tmp_path):
    now = datetime(2026, 9, 3, 12, tzinfo=timezone.utc)
    events = [
        ProgressEvent("Figure renders", now - timedelta(hours=2), 4),
        ProgressEvent("Figure renders", now - timedelta(hours=25), 3),
        ProgressEvent("Package audits", now - timedelta(hours=1), 10),
        ProgressEvent("Package audits", now - timedelta(hours=70), 5),
    ]
    receipt = render_progress_dashboard(
        events, now=now, windows_hours=(24, 96), title="Synthetic governed work progress",
        unit_label="work units", out_stem=tmp_path / "figures/progress",
        package_dir=tmp_path, provenance="synthetic test events",
    )
    assert receipt["totals"]["Figure renders"] == {"24": 4.0, "96": 7.0}
    assert receipt["totals"]["Package audits"] == {"24": 10.0, "96": 15.0}
    assert receipt["layout_qa"]["status"] == "PASS"
    assert (tmp_path / "figures/progress.png").is_file()
    assert (tmp_path / "figures/progress.svg").is_file()
    assert (tmp_path / "figures/progress.csv").is_file()
    assert (tmp_path / "figures/progress_receipt.json").is_file()
    assert (tmp_path / "figure_receipts.jsonl").is_file()


@pytest.mark.parametrize("units", [-1, float("nan"), float("inf")])
def test_invalid_actual_unit_weight_refuses(tmp_path, units):
    now = datetime(2026, 9, 3, 12, tzinfo=timezone.utc)
    with pytest.raises(ProgressDashboardRefusal, match="PROGRESS_UNITS_INVALID"):
        render_progress_dashboard(
            [ProgressEvent("lane", now, units)], now=now, windows_hours=(24,),
            title="x", unit_label="records", out_stem=tmp_path / "x",
            package_dir=tmp_path, provenance="synthetic",
        )


def test_timezone_mismatch_refuses(tmp_path):
    now = datetime(2026, 9, 3, 12, tzinfo=timezone.utc)
    with pytest.raises(ProgressDashboardRefusal, match="PROGRESS_TIMEZONE_MISMATCH"):
        render_progress_dashboard(
            [ProgressEvent("lane", datetime(2026, 9, 3, 11), 1)], now=now,
            windows_hours=(24,), title="x", unit_label="records",
            out_stem=tmp_path / "x", package_dir=tmp_path, provenance="synthetic",
        )
