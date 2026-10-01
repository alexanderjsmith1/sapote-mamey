#!/usr/bin/env python3
"""sync_wiki_mirrors.py — keep wiki pages that copy a maintained doc identical to that doc.

Eight wiki pages were hand copies of docs pages. They drifted for dozens of cuts while sync_version kept their
version stamps current, so a "current to" stamp sat on months-old text: an install section for a June build,
`--break-system-packages`, a claim footer the figures no longer draw. Each is now a generated mirror: the source
text, links rewritten for wiki/, under a one-line banner. Edit the source, never the mirror.

    python3 tools/sync_wiki_mirrors.py --apply     # rewrite every mirror from its source
    python3 tools/sync_wiki_mirrors.py --check     # exit 1 if any mirror differs (a test runs this)

tools/sync_version.py gives each mirror its source's version rules, so a cut re-stamps both alike.
"""
from __future__ import annotations

import argparse
import logging
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = logging.getLogger("sync_wiki_mirrors")   # reports through logging: terminal emission sites are ratcheted

# wiki page -> its maintained source (CURRENT_DOCS_INDEX.md names the sources as the current docs)
MIRRORS = {
    "wiki/User-Manual.md": "docs/GUIDE/01_User_Manual.md",
    "wiki/Quick-Guide.md": "docs/GUIDE/02_Quick_Guide.md",
    "wiki/Concepts-Q-and-A.md": "docs/GUIDE/06_Concepts_QandA.md",
    "wiki/Glossary.md": "docs/GLOSSARY.md",
    "wiki/Prerequisites.md": "docs/PREREQUISITES.md",
    "wiki/Common-Mistakes.md": "docs/COMMON_MISTAKES.md",
    "wiki/External-Tools-and-Databases.md": "docs/EXTERNAL_TOOL_INVENTORY.md",
    "wiki/Phylogenetic-Placement.md": "docs/PHYLO_PLACEMENT_WORKFLOW.md",
}
BANNER = ("<!-- Mirror of {src}, made by tools/sync_wiki_mirrors.py. "
          "Edit the source, then run: python3 tools/sync_wiki_mirrors.py --apply -->\n")
LINK = re.compile(r"(\]\()([^)\s]+)(\))")


def _rewrite(target: str, src: str) -> str:
    """A link written for the source's folder, rewritten for wiki/; a link to another mirrored doc goes to its page."""
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target) or target.startswith("#"):
        return target                                    # a URL, mailto: or an anchor in the same page
    path, _, anchor = target.partition("#")
    resolved = os.path.normpath(os.path.join(os.path.dirname(src), path))
    page_of = {s: w for w, s in MIRRORS.items()}
    new = os.path.basename(page_of[resolved]) if resolved in page_of else os.path.relpath(resolved, "wiki")
    return new + ("#" + anchor if anchor else "")


def render(page: str) -> str:
    src = MIRRORS[page]
    out, fence = [], False
    for line in (ROOT / src).read_text(encoding="utf-8").splitlines(keepends=True):
        if line.lstrip().startswith("```"):
            fence = not fence
        out.append(line if fence else LINK.sub(lambda m: m.group(1) + _rewrite(m.group(2), src) + m.group(3), line))
    return BANNER.format(src=src) + "".join(out)


def stale_pages() -> list[str]:
    return [p for p in MIRRORS if not (ROOT / p).exists() or (ROOT / p).read_text(encoding="utf-8") != render(p)]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Keep wiki mirror pages identical to their maintained docs.")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--apply", action="store_true", help="rewrite every mirror from its source")
    mode.add_argument("--check", action="store_true", help="exit 1 if any mirror differs from its source")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    stale = stale_pages()
    if args.check:
        if stale:
            LOG.error("wiki mirrors out of sync: %s", ", ".join(stale))
        else:
            LOG.info("wiki mirrors in sync")
        return 1 if stale else 0
    for p in stale:
        (ROOT / p).write_text(render(p), encoding="utf-8")
    LOG.info("wiki mirrors: %d rewritten, %d already current", len(stale), len(MIRRORS) - len(stale))
    return 0


if __name__ == "__main__":
    sys.exit(main())
