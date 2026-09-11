"""Standing gate: no raw lambda-stub assignments onto module attributes in tests.

The corrupter class proven in the .398 round: ``SomeModule.attr = lambda …`` with no restore
leaks the stub to every later consumer in the pytest process. One instance
(test_audit230_fixes stubbing ``kcb_frontpage.read_frontpage``) silently broke
``test_raw_antismash_triage``'s e2e whenever an unrelated test's over-broad sys.modules purge
wasn't there to accidentally repair it. Use ``monkeypatch.setattr`` (auto-restored) or an
explicit save/``finally``-restore instead.

The scan is a source grep with a reviewed allowlist. Every allowlist entry carries its reason;
a NEW raw stub anywhere else fails this gate with the remedy in the message.
"""
from __future__ import annotations

import pathlib
import re

TESTS_DIR = pathlib.Path(__file__).resolve().parent

# module-attr lambda stub, excluding monkeypatch lines and local-variable false positives
_STUB_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\.[a-z_][A-Za-z0-9_]*\s*=\s*lambda\b")

# Reviewed-safe instances (file basename -> reason). Keep this SHORT; prefer fixing over listing.
ALLOWLIST = {
    # saves the original and restores in `finally` around every use — reviewed 2026-09-01
    "test_brief_nonblocking_v9752.py": "manual save/finally-restore discipline",
    # stubs attributes of a LOCAL types.ModuleType fake, not a shared real module
    "test_clinker_figure_cleanup_v9_7_383.py": "local ModuleType fake",
    # save/finally-restore added in the .398 round (this gate's sibling fix)
    "test_round_ledger_empty_preexisting_file_v97395.py": "manual save/finally-restore discipline",
}


def _scan():
    offenders = []
    for py in sorted(TESTS_DIR.rglob("test_*.py")):
        if py.name in ALLOWLIST or py.name == pathlib.Path(__file__).name:
            continue
        for i, line in enumerate(py.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if "monkeypatch" in line:
                continue
            if _STUB_RE.match(line):
                offenders.append(f"{py.relative_to(TESTS_DIR.parent)}:{i}: {line.strip()}")
    return offenders


def test_no_raw_module_stub_assignments_in_tests():
    offenders = _scan()
    assert not offenders, (
        "Raw lambda-stub assignment(s) onto module attributes found — these LEAK to every later "
        "test in the process (see the .398 kcb_frontpage incident). Use monkeypatch.setattr, or "
        "save the original and restore in `finally`, then either fix the line or (only with a "
        "written reason) extend the reviewed ALLOWLIST:\n  " + "\n  ".join(offenders)
    )
