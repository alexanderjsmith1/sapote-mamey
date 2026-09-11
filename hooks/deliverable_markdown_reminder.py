#!/usr/bin/env python3
"""deliverable_markdown_reminder.py — Stop-hook guardrail.

The obvious-but-skippable step: after you RUN Mamey (or analyze a region) you must WRITE the finding
as a markdown card INTO the current patch-chat folder — chat prose is not a deliverable, and the patch
folder is the only place Patch Chat looks (house rule: patch-chat-folder-is-only-place).

This hook makes the omission visible. It is advisory + non-blocking (like link_check.py / signoff_stop.sh):
silent when clean; on a gap it prints a short reminder to stderr and exits 0 (never blocks).

Heuristic (filesystem-only, no transcript parsing):
  - find Mamey run packages produced recently (default 120 min) under any sealed tree's runs/<STRAIN>/package
  - for each such STRAIN, check whether ANY *.md under the newest patch-chat folder mentions that STRAIN id
  - a recent run with no companion markdown in the patch folder -> remind to write the card
"""
import os, re, sys, glob, time

BASE = (os.environ.get("SAPOTE_WORKSPACE_ROOT") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
WINDOW_MIN = int(os.environ.get("DELIVERABLE_MD_WINDOW_MIN", "120"))
STRAIN_RE = re.compile(r"(AS-\d+|SID\d+)")


_VER_RE = re.compile(r"v(\d+)\.(\d+)\.(\d+)")


def _folder_version(path):
    """The (major, minor, patch) version tuple embedded in a candidate folder's own name, or
    None if it carries no parseable version. This is the folder's structural identity -- what
    it calls itself -- not an accident of the filesystem."""
    m = _VER_RE.search(os.path.basename(path))
    return tuple(int(g) for g in m.groups()) if m else None


def newest_patch_folder():
    """Locate the current patch-chat folder.

    v9.7.399 REDESIGN (Codex pool review, following the v9.7.398 mtime-based fix): picking
    "whichever candidate has the newest mtime" is not authority -- an unrelated filesystem
    operation (a backup, a sync, a `touch`, an editor save) can make an OLDER folder LOOK
    newest, silently misdirecting this reminder to the wrong patch pool with no signal that
    anything went wrong. Two real sources of authority are used instead, in order:

      1. $SAPOTE_PATCH_FOLDER, if set -- an explicit, operator-configured override (absolute,
         or relative to BASE). No discovery is attempted when this is set.
      2. Structural identity: every current-convention candidate folder names its own bundle
         version in its name (e.g. "... (v9.7.399)"); the single HIGHEST parsed version is
         authoritative, because a higher version number is definitionally newer -- unlike an
         mtime, it cannot be accidentally stale. Three naming styles have been used over time,
         oldest first: "Cuts for Next Patch of Sapote Mamey vX" and "Patches for next cut
         Sapote Mamey (vX)" (both legacy, kept for backward compatibility -- never narrow a
         scope check), "Patches for Sapote Mamey [Claude|Codex] (vX)" (current, in use since
         ~v9.7.385).

    If no candidate carries a parseable version, or two or more candidates tie at the same
    highest version (e.g. a Claude-owned and a Codex-owned pool at the same cut), this refuses
    rather than guessing -- prints a warning and returns None, so the reminder simply stays
    silent for that run instead of pointing at a folder it cannot actually justify.
    """
    explicit = os.environ.get("SAPOTE_PATCH_FOLDER")
    if explicit:
        p = explicit if os.path.isabs(explicit) else os.path.join(BASE, explicit)
        return p if os.path.isdir(p) else None

    cands = (glob.glob(os.path.join(BASE, "Patches for next cut Sapote Mamey*"))
             + glob.glob(os.path.join(BASE, "Cuts for Next Patch of Sapote Mamey*"))
             + glob.glob(os.path.join(BASE, "Patches for Sapote Mamey*")))
    cands = [c for c in cands if os.path.isdir(c)]
    versioned = [(c, _folder_version(c)) for c in cands]
    versioned = [(c, v) for c, v in versioned if v is not None]
    if not versioned:
        return None
    max_ver = max(v for _, v in versioned)
    winners = [c for c, v in versioned if v == max_ver]
    if len(winners) != 1:
        sys.stderr.write(
            "deliverable_markdown_reminder: ambiguous newest patch folder -- %d candidates "
            "tie at v%s: %s. Set $SAPOTE_PATCH_FOLDER to disambiguate.\n"
            % (len(winners), ".".join(map(str, max_ver)), winners))
        return None
    return winners[0]


def recent_run_strains(cutoff):
    """strain ids whose runs/<STRAIN>/package was touched since cutoff."""
    found = {}
    for pkg in glob.glob(os.path.join(BASE, "sapote-mamey-*", "runs", "*", "package")):
        if not os.path.isdir(pkg):
            continue
        strain = os.path.basename(os.path.dirname(pkg))
        if not STRAIN_RE.fullmatch(strain):
            continue
        if os.path.getmtime(pkg) >= cutoff:
            found[strain] = pkg
    return found


def main():
    pf = newest_patch_folder()
    if not pf:
        return 0
    cutoff = time.time() - WINDOW_MIN * 60
    runs = recent_run_strains(cutoff)
    if not runs:
        return 0
    # union of all strain ids mentioned in any .md under the patch folder
    mentioned = set()
    for md in glob.glob(os.path.join(pf, "**", "*.md"), recursive=True):
        try:
            mentioned |= set(STRAIN_RE.findall(open(md, errors="replace").read()))
        except OSError:
            pass
    gaps = [s for s in sorted(runs) if s not in mentioned]
    if gaps:
        sys.stderr.write(
            "⚠ DELIVERABLE-MD: recent Mamey run(s) with NO markdown card in the patch folder:\n"
            "  %s\n  → Write the finding as a .md INTO '%s' (clickable link + plain path); "
            "chat prose is not a deliverable and Patch Chat only reads that folder.\n"
            % (", ".join(gaps), os.path.basename(pf)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
