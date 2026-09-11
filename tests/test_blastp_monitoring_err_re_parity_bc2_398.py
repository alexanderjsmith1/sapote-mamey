"""v9.7.398 — tools/blastp_monitoring/blastp_last_returns.py's own header docstring states
"Mirrors blastp_health.py's process/error anchoring" — verified live it did not. The two ERR_RE
patterns diverged bidirectionally:

  * blastp_health.py (the documented "ground-truth" tool, built to root-cause a real 2026-08-21
    incident) caught "UNKNOWN", "curl rc=", "expired" that blastp_last_returns.py missed;
  * blastp_last_returns.py caught a bare "rc=(?:16|56|6|7|18)" (no "curl" prefix) and "throttl"
    that blastp_health.py missed.

Both patterns now use the union of all 8 signatures. Since blastp_last_returns.py "doubles as a
gate" (its own docstring: "Exit code is 0 only when the last returns are usable AND there are no
failures"), the pre-fix gap meant a real curl timeout, an expired RID, or an UNKNOWN lane status
could report exit 0 (clean) from this tool while blastp_health.py correctly flagged DEGRADED for
the identical underlying log line — exactly the failure mode ("absence-of-fetches looked
identical to active-failure") blastp_health.py's own docstring says it exists to prevent.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_HERE = Path(__file__).resolve().parent.parent


def _load_err_re(rel_path: str):
    spec = importlib.util.spec_from_file_location("mod_bc2_398", _HERE / rel_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.ERR_RE


_LAST_RETURNS = "tools/blastp_monitoring/blastp_last_returns.py"
_HEALTH = "tools/blastp_monitoring/blastp_health.py"

# The real, concrete log lines the pre-fix divergence disagreed on.
_CASES = [
    "curl rc=28 connection timed out",
    "RID expired, resubmitting",
    "status=UNKNOWN for lane 12",
    "poll returned rc=16",             # bare rc=, no "curl" prefix
    "THROTTLE limit hit, pausing",     # no "backing off" co-occurring
]


def test_both_tools_now_agree_on_every_case():
    last_returns_re = _load_err_re(_LAST_RETURNS)
    health_re = _load_err_re(_HEALTH)
    for line in _CASES:
        lr = bool(last_returns_re.search(line))
        h = bool(health_re.search(line))
        assert lr and h, f"{line!r}: last_returns={lr}, health={h} — still disagree"


def test_shared_patterns_still_match_common_signals():
    last_returns_re = _load_err_re(_LAST_RETURNS)
    health_re = _load_err_re(_HEALTH)
    for line in ("submit failed: 503", "backing off 300s", "poll ERROR: malformed"):
        assert last_returns_re.search(line) and health_re.search(line)


def test_a_clean_log_line_matches_neither():
    last_returns_re = _load_err_re(_LAST_RETURNS)
    health_re = _load_err_re(_HEALTH)
    clean = "fetched 40 hits for AS-188 BGC012"
    assert not last_returns_re.search(clean)
    assert not health_re.search(clean)
