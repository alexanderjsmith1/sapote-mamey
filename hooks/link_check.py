#!/usr/bin/env python3
"""link_check.py — Stop-hook guardrail: flag deliverable folders under the workspace
subdirectory that owns `WHERE_THINGS_LIVE.md` that are NOT registered in that index.

Advisory + non-blocking (like signoff_stop.sh): silent when everything is linked; on orphans it
prints a short reminder so the session registers them (link + one-line) instead of scattering
undiscoverable folders. Enforces the FILE-HOME + CHECK-BEFORE-CREATE rules by making orphaning visible.

A "deliverable hub" = a top-level dir under the index-owning root whose name starts with `_`
(module/analysis hub) OR that carries a top-level *SYNTHESIS*.md / *REPORT*.md / README.md.
Per-strain `AS-XXX/` dirs and `_WORD_DOCS` are excluded (they're covered by the per-strain
convention, not the index).
"""
import os, re, sys, glob

WORKSPACE = os.environ.get("SAPOTE_WORKSPACE_ROOT") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


def deliverable_hub_root(workspace):
    """The single root of authority for deliverable-hub discovery.

    v9.7.399 REDESIGN (Codex pool review): the prior design (v9.7.398) aggregated findings
    across EVERY workspace subdirectory that owned a WHERE_THINGS_LIVE.md, plus an always-on
    legacy fallback -- silently combining results from what could be multiple, genuinely
    distinct indexes with no signal that the scope was ambiguous. Structural discovery must
    resolve to exactly one root or refuse, not aggregate.

    Priority:
      1. $SAPOTE_DELIVERABLE_ROOT, if set -- an explicit, operator-configured override
         (absolute, or relative to `workspace`). No discovery attempted when set.
      2. Structural identity: the workspace subdirectory that owns WHERE_THINGS_LIVE.md (per
         that index's own Rule 1, deliverable hubs live directly under it). If EXACTLY ONE
         such subdirectory exists, it is authoritative. If two or more exist, this is a
         genuine ambiguity this hook cannot resolve on its own -- refuse (None, warn) rather
         than silently combining two potentially-unrelated indexes.
      3. If no subdirectory owns the index at all (a differently-laid-out workspace), fall
         back to the legacy bare 'strain_data/' path -- kept ONLY as a last-resort when the
         modern structural signal finds nothing, never combined with a genuine structural
         match.
      4. Otherwise, refuse (None) -- nothing to check.
    """
    explicit = os.environ.get("SAPOTE_DELIVERABLE_ROOT")
    if explicit:
        p = explicit if os.path.isabs(explicit) else os.path.join(workspace, explicit)
        return p if os.path.isdir(p) else None

    # Dedup by (st_dev, st_ino) -- the same physical directory reached via a symlink alias
    # (e.g. a workaround symlink pointing a legacy path name at the real canonical folder,
    # confirmed to exist live in this workspace) must count as ONE candidate, not two,
    # matching the identical (st_dev, st_ino) dedup precedent already established in
    # mamey/strain_data_home.py's own resolver for the same class of duplicate-path problem.
    structural = []
    seen_inodes = set()
    try:
        for entry in sorted(os.listdir(workspace)):
            p = os.path.join(workspace, entry)
            if not (os.path.isdir(p) and os.path.exists(os.path.join(p, "WHERE_THINGS_LIVE.md"))):
                continue
            try:
                st = os.stat(p)
                key = (st.st_dev, st.st_ino)
            except OSError:
                key = None
            if key is not None and key in seen_inodes:
                continue
            if key is not None:
                seen_inodes.add(key)
            structural.append(p)
    except OSError:
        pass

    if len(structural) == 1:
        return structural[0]
    if len(structural) > 1:
        sys.stderr.write(
            "link_check: ambiguous deliverable-hub root -- %d distinct-inode subdirectories "
            "each own a WHERE_THINGS_LIVE.md: %s. Set $SAPOTE_DELIVERABLE_ROOT to disambiguate.\n"
            % (len(structural), structural))
        return None

    legacy = os.path.join(workspace, "strain_data")
    if os.path.isdir(legacy) and os.path.exists(os.path.join(legacy, "WHERE_THINGS_LIVE.md")):
        return legacy
    return None


DELIVERABLE_HUB_ROOT = deliverable_hub_root(WORKSPACE)

def is_deliverable_hub(path):
    b = os.path.basename(path)
    if re.match(r"AS-\d+$", b) or b in ("_WORD_DOCS", "__pycache__", "_queue_test") or b.startswith("."):
        return False
    if b.startswith("_"):
        return True
    # a folder with a top-level synthesis/report/readme is a deliverable
    for pat in ("*SYNTHESIS*.md", "*REPORT*.md", "README.md", "*SURVEY*.md"):
        if glob.glob(os.path.join(path, pat)):
            return True
    return False

def main():
    root = DELIVERABLE_HUB_ROOT
    if not root:
        return 0
    index = os.path.join(root, "WHERE_THINGS_LIVE.md")
    if not os.path.isdir(root) or not os.path.exists(index):
        return 0
    index_text = open(index, errors="replace").read()
    orphans = []
    for name in sorted(os.listdir(root)):
        p = os.path.join(root, name)
        if not os.path.isdir(p) or not is_deliverable_hub(p):
            continue
        if name not in index_text:                      # basename not referenced anywhere in the index
            orphans.append(name)
    if orphans:
        show = orphans[:12]
        more = f" (+{len(orphans)-12} more)" if len(orphans) > 12 else ""
        sys.stderr.write(
            "⚠ LINK-CHECK: %d deliverable folder(s) are NOT linked in "
            "WHERE_THINGS_LIVE.md:\n  %s%s\n  → Register each (one-line + %%-encoded link) so it is "
            "discoverable; do not leave orphaned deliverables.\n" % (len(orphans), ", ".join(show), more))
    return 0

if __name__ == "__main__":
    sys.exit(main())
