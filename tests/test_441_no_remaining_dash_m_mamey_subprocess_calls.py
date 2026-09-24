"""No production code should launch the engine via ``-m mamey`` in a subprocess.

The stray workspace-root mamey/ (v1.9.154, bundle 9.7.418) shadows the bundle
(v1.9.169, bundle 9.7.440) when cwd is the workspace root. 88fdad06 fixed the
intake harness; this test covers the three remaining callers AND prevents any
new caller from reintroducing the pattern.

Four callers total (before this fix):
  tools/intake_harness.py          (fixed by 88fdad06)
  tools/run_chatgpt_surrogate_gate.py  (fixed here)
  tools/cohort_blastp_driver.py    (fixed here, 2 call sites)
  mamey/deliverable_queue.py       (fixed here)
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# Tests/ are exempt — they run from inside the bundle and the shadow does not
# reach them. Comments and docstrings are also fine.
_PROD_GLOBS = ["tools/*.py", "mamey/**/*.py", "deliverable_tools/*.py", "scripts/*.py"]
_DASH_M_RE = re.compile(
    r"""sys\.executable\s*,\s*['"]-m['"]\s*,\s*['"]mamey""",
    re.DOTALL,
)


def _is_in_string_or_comment(source: str, match_start: int) -> bool:
    """Heuristic: if the match is inside a triple-quoted string or after #, skip it."""
    line_start = source.rfind("\n", 0, match_start) + 1
    line = source[line_start : source.find("\n", match_start)]
    stripped = line.lstrip()
    if stripped.startswith("#"):
        return True
    before = source[:match_start]
    triple_double = before.count('"""')
    triple_single = before.count("'''")
    if triple_double % 2 == 1 or triple_single % 2 == 1:
        return True
    return False


def _collect_violations() -> list[str]:
    violations = []
    for pattern in _PROD_GLOBS:
        for path in sorted(ROOT.glob(pattern)):
            if path.name.startswith("test_") or "__pycache__" in str(path):
                continue
            try:
                src = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for m in _DASH_M_RE.finditer(src):
                if not _is_in_string_or_comment(src, m.start()):
                    rel = path.relative_to(ROOT)
                    lineno = src[:m.start()].count("\n") + 1
                    violations.append(f"{rel}:{lineno}")
    return violations


def test_no_dash_m_mamey_subprocess_in_production_code():
    violations = _collect_violations()
    assert violations == [], (
        f"Production code still launches the engine via `-m mamey` in a subprocess. "
        f"Use mamey_run.py instead (cwd-shadow risk). Violations:\n"
        + "\n".join(f"  {v}" for v in violations)
    )


@pytest.mark.parametrize("tool,runner_literal", [
    ("tools/run_chatgpt_surrogate_gate.py", "mamey_run.py"),
    ("tools/cohort_blastp_driver.py", "_BUNDLE_RUNNER"),
    ("mamey/deliverable_queue.py", "_RUNNER"),
])
def test_callers_use_bundle_pinned_runner(tool, runner_literal):
    src = (ROOT / tool).read_text()
    assert runner_literal in src, f"{tool} should reference {runner_literal}"


def test_intake_harness_already_fixed_by_88fdad06():
    src = (ROOT / "tools/intake_harness.py").read_text()
    assert 'mamey_run.py' in src or "-m" not in src[src.index("run_monitored"):], (
        "intake_harness.py should use mamey_run.py (88fdad06 fix)"
    )
