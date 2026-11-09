"""The progress dashboard refuses an out-of-package destination before writing its CSV."""
from datetime import datetime, timedelta, timezone

import pytest

from mamey.interactive_figures.progress_dashboard import (
    ProgressDashboardRefusal,
    ProgressEvent,
    render_progress_dashboard,
)


def test_outside_destination_writes_nothing(tmp_path):
    now = datetime(2026, 9, 3, 12, tzinfo=timezone.utc)
    package, outside = tmp_path / "package", tmp_path / "outside"
    package.mkdir()
    with pytest.raises(ProgressDashboardRefusal, match="PROGRESS_OUTPUT_OUTSIDE_PACKAGE"):
        render_progress_dashboard(
            [ProgressEvent("Figure renders", now - timedelta(hours=2), 4)], now=now,
            windows_hours=(24,), title="Synthetic", unit_label="units",
            out_stem=outside / "figures/progress", package_dir=package, provenance="synthetic")
    assert not outside.exists()
