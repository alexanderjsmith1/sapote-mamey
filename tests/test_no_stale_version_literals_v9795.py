"""v9.7.95 AUDIT (P-A5): no stale self-describing engine-version literal anywhere in shipped code.

`make_public_tier.sh` carries a VERSION-SYNC GATE that fails a cut if any .py/.sh file contains a
self-describing literal of the form "(Sapote-)Mamey vX.Y.Z" / "pipeline vX.Y.Z" that does not equal
the engine __version__ (unless the line carries an explicit `version-sync-ok` marker). That gate only
ran at cut time. This test lifts the same rule into the standing suite so the drift is caught in dev/CI
the moment it is introduced — the cohort-wide complement to the per-file sync_version rules.

Scope intentionally mirrors the cut gate exactly to avoid false positives:
  - only .py and .sh files, excluding tests/ (which assert historical contract versions) and the gate's
    own source make_public_tier.sh;
  - only the "Mamey/pipeline vX.Y.Z" phrasing — bare CHANGELOG tokens like "v9.7.90" are NOT matched;
  - a `version-sync-ok` marker on the line is an explicit, auditable exemption for deliberate
    historical/compat references.
"""
from __future__ import annotations
import re
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
_VER = re.compile(r'(?:Sapote-)?(?:Mamey|pipeline)\s+v?(\d+\.\d+\.\d+)', re.IGNORECASE)


def _engine_version() -> str:
    init = (ROOT / "mamey" / "__init__.py").read_text(encoding="utf-8")
    return re.search(r'__version__\s*=\s*"([^"]+)"', init).group(1)


def test_no_stale_self_describing_version_literals():
    canon = _engine_version()
    stale = []
    unreadable = []
    for p in list(ROOT.rglob("*.py")) + list(ROOT.rglob("*.sh")):
        parts = p.relative_to(ROOT).parts
        if "tests" in parts or p.name == "make_public_tier.sh":
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            # v9.7.430 release-integrity: fail CLOSED. `errors="ignore"` already absorbs every decode
            # problem, so the only thing this handler can catch is an OSError — a file the scan could
            # not open. Swallowing it silently meant an unscannable file was reported drift-free: the
            # same "the guard saw nothing, so there is nothing" shape v9.7.409 closed in the
            # seal-coverage paths (tests/test_409_rglob_seal_coverage.py).
            unreadable.append(f"{p.relative_to(ROOT)}: {exc.__class__.__name__}: {exc}")
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if "version-sync-ok" in line:
                continue
            for hit in _VER.findall(line):
                if hit != canon:
                    stale.append(f"{p.relative_to(ROOT)}:{i}: claims v{hit} (engine is v{canon})")
    assert not unreadable, (
        "this guard could not read the following shipped files, so it cannot say they are free of "
        "stale version literals — fix the permissions or exclude them explicitly; do not let the "
        "scan pass by default:\n  " + "\n  ".join(unreadable))
    assert not stale, (
        "stale self-describing version literals (fix the literal, derive it from __version__, or append "
        "a 'version-sync-ok' marker if the reference is deliberately historical):\n  " + "\n  ".join(stale)
    )
