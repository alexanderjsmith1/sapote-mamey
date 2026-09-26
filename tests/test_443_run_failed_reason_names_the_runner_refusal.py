"""A batch input the runner refuses must report the refusal, not the refusal's last line.

`tools/intake_harness.py` launches each input through `mamey_run.py`, which can refuse before the
engine starts. Its refusal messages open with a named token (`STALE_BYTECODE_REFUSED: ...`) and close
with a remediation or with "Nothing has been deleted for you." `_run_failed_reason()` looked for an
`ERROR` line and otherwise returned the LAST line, so a refused batch printed
`RUN_FAILED (rc=2) -- Nothing has been deleted for you.` for every input.

Same hermetic seam as test_440_run_failed_reason_surfaces_engine_error.py: the helper's own source is
extracted and exec'd, so neither `mamey` nor `_console` has to import.
"""
import re
from pathlib import Path

BUNDLE = Path(__file__).resolve().parents[1]
HARNESS = BUNDLE / "tools" / "intake_harness.py"
RUNNER = BUNDLE / "mamey_run.py"


def _load_run_failed_reason():
    source = HARNESS.read_text(encoding="utf-8")
    match = re.search(r"def _run_failed_reason\(.*?\n\n\ndef ", source, re.S)
    assert match, "_run_failed_reason() not found in tools/intake_harness.py"
    func_source = source[match.start():match.end()].rsplit("\n\n\ndef ", 1)[0]
    ns = {}
    exec(compile(func_source, str(HARNESS), "exec"), ns)
    return ns["_run_failed_reason"]


STALE = (
    "STALE_BYTECODE_REFUSED: __version__: source='1.9.170', imported='1.9.169'\n"
    "  package: /bundle/mamey/__init__.py\n"
    "  A cached .pyc compiled from a different cut is being reused. The cut writes a fixed\n"
    "  Remediation: remove the stale caches under this bundle, e.g.\n"
    "    find '/bundle' -name __pycache__ -type d -prune -exec rm -rf {} +\n"
    "  Nothing has been deleted for you.\n"
)

FOREIGN = (
    "FOREIGN_BYTECODE_REFUSED: __pycache__ under this bundle was compiled from a different cut.\n"
    "  cache was built by : version=9.7.442 build=20260924v97442a\n"
    "  this tree is       : version=9.7.443 build=20260926v97443a\n"
    "  Remediation: re-run with --purge-bytecode, or:\n"
    "  Nothing has been deleted for you.\n"
)


def test_a_stale_bytecode_refusal_is_reported_by_name():
    reason = _load_run_failed_reason()(STALE)
    assert reason.startswith(" -- STALE_BYTECODE_REFUSED:"), reason
    assert "Nothing has been deleted" not in reason


def test_any_named_runner_refusal_is_reported_by_name():
    reason = _load_run_failed_reason()(FOREIGN)
    assert reason.startswith(" -- FOREIGN_BYTECODE_REFUSED:"), reason


def test_the_engines_own_error_line_still_wins():
    log = "ERROR: TAXONOMY_PLACEHOLDER: supply taxonomy\n" + STALE
    assert _load_run_failed_reason()(log).startswith(" -- ERROR: TAXONOMY_PLACEHOLDER")


def test_prose_that_merely_mentions_a_refusal_is_not_mistaken_for_one():
    log = "note: see STALE_BYTECODE_REFUSED in the docs\nRuntimeError: boom\n"
    assert _load_run_failed_reason()(log) == " -- RuntimeError: boom"


def test_the_shipped_runner_still_opens_its_refusal_with_the_token_this_reads():
    """Producer side: if the runner's message format changes, this helper goes blind again."""
    assert 'STALE_BYTECODE_REFUSED: ' in RUNNER.read_text(encoding="utf-8")
