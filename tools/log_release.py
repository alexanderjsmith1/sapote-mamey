#!/usr/bin/env python3
"""log_release.py — append one row to RELEASES_LOG.md for the current build (idempotent).

WHY A SEPARATE TOOL (not make_public_tier.sh): the cut runs once PER TIER, and mutating the
source RELEASES_LOG.md mid-build would make the tiers cut after it diverge from the tiers cut
before it (a tier-parity break). Releases are logged ONCE, in build-prep, before any tier is cut.

Usage:  tools/log_release.py --stamp 20260620-(m)   [--tiers "CODE · CODE-analysis-free · SID · MERGED"]
        # version + headline are read from pyproject.toml + CHANGELOG.md; re-running is a no-op.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, pathlib, re, sys
import os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__))))
from _wbio import atomic_write_text

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _bundle_version():
    pp = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    return re.search(r'(?m)^\s*bundle_version\s*=\s*"([^"]+)"', pp).group(1)


def _changelog_headline():
    """First non-empty prose line under the top CHANGELOG entry, trimmed to a one-liner."""
    txt = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    lines = txt.splitlines()
    for i, l in enumerate(lines):
        if l.startswith("# v"):
            for l2 in lines[i + 1:]:
                s = l2.strip().lstrip("*").strip()
                if s:
                    return re.sub(r"\*\*", "", s)[:240]
    return "(headline unavailable)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stamp", required=True, help="build stamp, e.g. 20260620-(m)")
    ap.add_argument("--tiers", default="CODE · CODE-analysis-free · SID · MERGED")
    ap.add_argument("--leak-audit", default="0 AS (CODE/CAF/SID)")
    a = ap.parse_args()
    ver = _bundle_version()
    log = ROOT / "RELEASES_LOG.md"
    txt = log.read_text(encoding="utf-8")
    if f"| v{ver} |" in txt and a.stamp in txt:
        emit(f"RELEASES_LOG already has v{ver} @ {a.stamp} — no-op")
        return 0
    row = f"| {a.stamp} | v{ver} | {a.tiers} | {_changelog_headline()} | {a.leak_audit} |\n"
    # insert directly under the table header separator row (newest first)
    # v9.7.115: tolerate any column count (was hardcoded to exactly 5 `---` cells, which would
    # silently refuse to log if the table ever gained/lost a column).
    m = re.search(r"(?m)^\|(?:\s*-{3,}\s*\|)+\n", txt)
    if not m:
        emit("RELEASES_LOG.md table header not found; refusing to write.", file=sys.stderr)
        return 1
    txt = txt[: m.end()] + row + txt[m.end():]
    atomic_write_text(log, txt)
    emit(f"logged release row: v{ver} @ {a.stamp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
