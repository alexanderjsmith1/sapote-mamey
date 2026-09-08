#!/usr/bin/env python3
"""check_md_links.py — verify that local file links in Markdown actually resolve on disk.

Recurring problem: file links handed to users don't open (un-encoded spaces/parens, or a path
that doesn't exist). This is the portable guard: it parses `[text](target)` links (and bare
`path:line` references) from a .md file, and for every LOCAL target checks that the file exists,
resolving the target relative to (a) the .md file's own directory and (b) the project root. It
also flags targets that contain RAW spaces or parens (which render dead in the terminal UI and
must be %20/%28/%29-encoded).

Exits non-zero if any local link is broken, so it can gate a hook / CI / a pre-send check.
http(s):, mailto:, and #anchors are ignored. stdlib only.

Usage:
  python3 tools/check_md_links.py FILE.md [FILE2.md ...]
  python3 tools/check_md_links.py --dir "some/folder"
"""
from __future__ import annotations
import argparse, os, re, sys
from urllib.parse import unquote

# v9.7.414: portable root. The workspace copy hardcoded one operator's absolute home path,
# which is both non-portable and a personal identifier the release audit forbids in shipped source.
# Resolution order mirrors hooks/md_link_check.sh so the hook and the tool agree on "the project":
# explicit env override, then the harness-supplied project dir, then the bundle's own parent, then
# cwd. A wrong root only costs a second resolution attempt -- check_file() tries the .md file's own
# directory first, so relative links resolve regardless.
def _project_root() -> str:
    for var in ("SAPOTE_WORKSPACE_ROOT", "SAPOTE_ROOT", "CLAUDE_PROJECT_DIR"):
        v = os.environ.get(var)
        if v and os.path.isdir(v):
            return v
    here = os.path.dirname(os.path.abspath(__file__))          # <bundle>/tools
    bundle = os.path.dirname(here)                             # <bundle>
    parent = os.path.dirname(bundle)                           # workspace holding the bundle
    return parent if os.path.isdir(parent) else os.getcwd()


PROJECT_ROOT = _project_root()
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")          # [text](target)
# also catch inline code paths like `some folder/foo.md` that look like real files
SKIP_PREFIX = ("http://", "https://", "mailto:", "#", "tel:", "data:")


def _is_local(target: str) -> bool:
    t = target.strip()
    return bool(t) and not t.startswith(SKIP_PREFIX)


def _strip_anchor_line(target: str) -> str:
    # drop #anchor and :line / :line:col suffixes for existence check
    t = target.split("#", 1)[0]
    t = re.sub(r":\d+(:\d+)?$", "", t)
    return t


def check_file(md_path: str) -> list[tuple[str, str]]:
    """Return list of (target, reason) problems."""
    problems: list[tuple[str, str]] = []
    md_dir = os.path.dirname(os.path.abspath(md_path))
    try:
        text = open(md_path, encoding="utf-8", errors="ignore").read()
    except OSError as e:
        return [("<file>", f"cannot read: {e}")]

    # Strip fenced code blocks and inline code spans so documentation EXAMPLES of links
    # (e.g. `[text](target)`) are not mistaken for real links.
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"`[^`]*`", "", text)

    for m in LINK_RE.finditer(text):
        raw = m.group(1).strip()
        if not _is_local(raw):
            continue
        # flag raw (un-encoded) spaces/parens BEFORE decoding
        if " " in raw or "(" in raw or ")" in raw:
            problems.append((raw, "un-encoded space/paren — will render dead; use %20/%28/%29"))
        target = _strip_anchor_line(unquote(raw))
        if target.startswith("/"):
            candidates = [target]
        else:
            candidates = [os.path.join(md_dir, target),
                          os.path.join(PROJECT_ROOT, target)]
        if not any(os.path.exists(c) for c in candidates):
            problems.append((raw, "target does not exist (checked file-dir + project-root)"))
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*")
    ap.add_argument("--dir", default=None, help="check every *.md in this folder")
    ap.add_argument("--quiet-if-clean", action="store_true")
    args = ap.parse_args(argv)

    targets = []
    if args.dir:
        for root, _, files in os.walk(args.dir):
            targets += [os.path.join(root, f) for f in files if f.endswith(".md")]
    targets += [f for f in args.files if f.endswith(".md")]
    targets = [t for t in targets if os.path.exists(t)]
    if not targets:
        ap.error("no .md files given")

    total = 0
    for md in targets:
        probs = check_file(md)
        if probs:
            total += len(probs)
            print(f"BROKEN LINKS in {md}:")
            for tgt, why in probs:
                print(f"  ✗ {tgt}\n      {why}")
    if total == 0 and not args.quiet_if_clean:
        print(f"OK — {len(targets)} file(s), all local links resolve.")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
