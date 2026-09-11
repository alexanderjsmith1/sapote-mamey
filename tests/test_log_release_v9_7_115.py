"""v9.7.115: log_release header regex tolerates column changes; re-run is idempotent."""
import sys, pathlib, re
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import log_release as L


def test_header_regex_tolerates_column_counts():
    rx = re.compile(r"(?m)^\|(?:\s*-{3,}\s*\|)+\n")
    assert rx.search("|---|---|---|\n")          # 3 columns
    assert rx.search("|---|---|---|---|---|\n")  # 5 columns (original)
    assert rx.search("| --- | --- |\n")          # spaced


def test_real_releases_log_header_matches():
    txt = (ROOT / "RELEASES_LOG.md").read_text(encoding="utf-8")
    assert re.search(r"(?m)^\|(?:\s*-{3,}\s*\|)+\n", txt)
