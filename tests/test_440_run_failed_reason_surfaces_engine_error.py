"""RUN_FAILED used to print only `rc=N`. `run_monitored()` already captures the engine's combined
stdout+stderr (`log`), including its own `ERROR: <code>: <detail>` line (mamey/cli.py's
metadata-refusal path, e.g. TAXONOMY_PLACEHOLDER) -- it was one field away and never surfaced. This
pins `_run_failed_reason()`, which extracts a short, useful line from `log` for the operator's
stdout only. Does not touch the checkpoint CSV schema (_MET_HDR) or any row shape -- verified by
grep below that the RUN_FAILED met_rows dict is unchanged.

Hermetic: extracts the helper's source directly (regex + exec), the same seam-testing approach as
9C92D456's taxonomy-fallback test, so this does not need `_console`/`mamey` importable.
"""
import re
import sys
from pathlib import Path

BUNDLE = Path(__file__).resolve().parents[1]
HARNESS = BUNDLE / "tools" / "intake_harness.py"


def _load_run_failed_reason():
    source = HARNESS.read_text(encoding="utf-8")
    match = re.search(r"def _run_failed_reason\(.*?\n\n\ndef ", source, re.S)
    assert match, "_run_failed_reason() not found in tools/intake_harness.py"
    func_source = source[match.start():match.end()].rsplit("\n\n\ndef ", 1)[0]
    ns = {}
    exec(compile(func_source, str(HARNESS), "exec"), ns)
    return ns["_run_failed_reason"]


def test_extracts_the_engines_own_error_line():
    reason = _load_run_failed_reason()
    log = (
        "ERROR: TAXONOMY_PLACEHOLDER: supply taxonomy bound to the source record, "
        "or explicitly use 'not verified' if unresolved.\n"
        '{"status": "TAXONOMY_PLACEHOLDER", "written": false}\n'
    )
    result = reason(log)
    assert result.startswith(" -- ERROR: TAXONOMY_PLACEHOLDER")
    assert "written" not in result  # prefers the ERROR line over the trailing JSON line


def test_falls_back_to_last_nonempty_line_when_no_error_prefix():
    reason = _load_run_failed_reason()
    log = "Loading antiSMASH results...\nProcessing region 1 of 3...\nRuntimeError: boom\n"
    assert reason(log) == " -- RuntimeError: boom"


def test_empty_log_yields_empty_string_not_a_crash():
    reason = _load_run_failed_reason()
    assert reason("") == ""
    assert reason(None) == ""


def test_long_line_is_truncated_not_unbounded():
    reason = _load_run_failed_reason()
    log = "ERROR: " + ("x" * 500)
    result = reason(log)
    assert result.endswith("...")
    assert len(result) < 200


def test_run_failed_emit_call_uses_the_helper():
    source = HARNESS.read_text(encoding="utf-8")
    assert 'RUN_FAILED (rc={rc}){_run_failed_reason(log)}' in source


def test_met_rows_run_failed_shape_is_unchanged():
    """This patch must not touch the checkpoint CSV schema -- only the stdout emit() line."""
    source = HARNESS.read_text(encoding="utf-8")
    match = re.search(
        r'met_rows\.append\(\{"strain": name, "batch": a\.batch_label, "status": "RUN_FAILED",\s*'
        r'"engine_wall_s": wall, "engine_peak_mb": mem, "rescue_wall_s": "", "n_regions": ""\}\)',
        source,
    )
    assert match, "RUN_FAILED met_rows dict shape changed -- this patch should not touch it"
