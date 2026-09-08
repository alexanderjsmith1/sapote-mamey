"""antiSMASH --limit record-cap detection (v9.7.187). A truncated run scans only the largest N
records; BGCs on skipped records are silently absent while GC/contamination stats cover the whole
assembly — an incomplete scan presented as MAMEY_COMPLETE (AS-XXX silent-omission family, at the
whole-record level). The detector reads the archived .log for the --limit warning."""
import os
import tempfile
import zipfile

from mamey.parsers import antismash_record_limit_truncation

_TRUNC_LOG = (
    "INFO  Only analysing the first 1000 records (increase via --limit)\n"
    "INFO  Not annotating skipped record NODE_1001_length_1234_cov_5.6: "
    "skipping all but largest 1000 meaningful records (--limit)\n"
    "INFO  Not annotating skipped record NODE_1002_length_1200_cov_4.2: "
    "skipping all but largest 1000 meaningful records (--limit)\n"
)
_CLEAN_LOG = "INFO  antiSMASH complete. 112 records analysed.\n"

# --- Ground-truth fixtures (v9.7.188) --------------------------------------------------------
# Strings taken verbatim from the antiSMASH source, not hand-approximated:
#   * warning:  common/record_processing.py:435
#       logging.warning("Only analysing the first %d records (increase via --limit)", options.limit)
#   * skip str: common/record_processing.py:360
#       record.skip = f"skipping all but largest {maximum} meaningful records (--limit) "  # note trailing space
#   * skip log: main.py:521  ->  logging.debug("Not annotating skipped record %s: %s", record.id, record.skip)
# CRITICAL: the skip line is emitted at DEBUG level. A DEFAULT antiSMASH run does not write DEBUG to
# the .log, so on a normal truncated run ONLY the warning line is present — first_skipped/skipped_count
# are legitimately absent. The load-bearing signal (truncated=True) still fires from the warning alone.
_GT_DEFAULT_LOG = (  # default verbosity: warning only, no DEBUG skip lines (the common real case)
    "2026-07-03 10:00:01 INFO     antiSMASH version: 8.0.4\n"
    "2026-07-03 10:00:02 INFO     Parsing input file assembly.fasta\n"
    "2026-07-03 10:05:00 WARNING  Only analysing the first 1000 records (increase via --limit)\n"
    "2026-07-03 10:40:00 INFO     antiSMASH complete\n"
)
_GT_DEBUG_LOG = (  # --debug run: warning + the DEBUG skip lines, rendered exactly as "%s: %s"
    "2026-07-03 10:00:01 INFO     antiSMASH version: 8.0.4\n"
    "2026-07-03 10:05:00 WARNING  Only analysing the first 1000 records (increase via --limit)\n"
    "2026-07-03 10:06:00 DEBUG    Not annotating skipped record NODE_1001: "
    "skipping all but largest 1000 meaningful records (--limit) \n"
    "2026-07-03 10:06:01 DEBUG    Not annotating skipped record NODE_1002: "
    "skipping all but largest 1000 meaningful records (--limit) \n"
)


def _zip_with_log(text):
    fd, path = tempfile.mkstemp(suffix=".zip")
    os.close(fd)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("run.log", text)
    return path


def test_truncation_detected():
    z = _zip_with_log(_TRUNC_LOG)
    try:
        r = antismash_record_limit_truncation(z)
        assert r["truncated"] is True
        assert r["analysed"] == 1000
        assert r["first_skipped"] == "NODE_1001_length_1234_cov_5.6"
        assert r["skipped_count"] == 2
    finally:
        os.unlink(z)


def test_clean_log_no_truncation():
    z = _zip_with_log(_CLEAN_LOG)
    try:
        r = antismash_record_limit_truncation(z)
        assert r["truncated"] is False
        assert r["analysed"] is None
    finally:
        os.unlink(z)


def test_ground_truth_default_mode_warning_only():
    """Real default-verbosity run: only the WARNING line is written (skip lines are DEBUG-only).
    truncated MUST be True from the warning alone; detail fields are legitimately empty."""
    z = _zip_with_log(_GT_DEFAULT_LOG)
    try:
        r = antismash_record_limit_truncation(z)
        assert r["truncated"] is True          # load-bearing signal fires without any skip line
        assert r["analysed"] == 1000
        assert r["first_skipped"] is None       # no DEBUG skip lines in a default run
        assert r["skipped_count"] == 0
    finally:
        os.unlink(z)


def test_ground_truth_debug_mode_with_skip_lines():
    """--debug run: the DEBUG 'Not annotating skipped record <id>: <skip>' lines are present,
    rendered exactly as antiSMASH's '%s: %s' with the trailing-space skip string."""
    z = _zip_with_log(_GT_DEBUG_LOG)
    try:
        r = antismash_record_limit_truncation(z)
        assert r["truncated"] is True
        assert r["analysed"] == 1000
        assert r["first_skipped"] == "NODE_1001"   # bare record id, not NODE_..._length_..._cov_...
        assert r["skipped_count"] == 2
    finally:
        os.unlink(z)


def test_missing_log_graceful():
    # a zip with no .log must not raise
    fd, path = tempfile.mkstemp(suffix=".zip")
    os.close(fd)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("something.txt", "no log here")
    try:
        r = antismash_record_limit_truncation(path)
        assert r["truncated"] is False
    finally:
        os.unlink(path)
