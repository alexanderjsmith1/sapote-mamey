#!/usr/bin/env python3
"""sapote_version_guard.py — UserPromptSubmit hook: force the CURRENT Sapote-Mamey version + the
'don't trust stale on-disk cards' rule into context BEFORE EVERY interaction.

Why this exists: a session once authored 'corrections' to Mode-B cards read from mode_b_v9.7.339/
(an OLD engine) and asserted defects that the CURRENT engine had already fixed — wasting the user's
and Codex's time. This guard fires on every user prompt so the current version and the verify-not-stale
rule are always in view.

Fast + safe: resolves the newest bundle by directory name, reads its __version__, prints one compact
additionalContext block. Never blocks (always exit 0); on any error it stays silent.
"""
import os, re, sys, glob, json

ROOT = os.environ.get("CLAUDE_PROJECT_DIR") or os.environ.get("SAPOTE_WORKSPACE_ROOT") or os.environ.get("SAPOTE_ROOT", os.getcwd())

def _ver_tuple(name):
    m = re.search(r"v(\d+)\.(\d+)\.(\d+)", name)
    return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)

def _newest_bundle():
    cands = []
    for pat in ("sapote-mamey-v*-CODE-*", "Sapote_Mamey_v*", "Sapote Mamey v*"):
        cands += [d for d in glob.glob(os.path.join(ROOT, pat)) if os.path.isdir(d)]
    if not cands:
        return None
    # highest version; on a tie prefer a *-CODE-* tree (the code, not the doc bundle)
    cands.sort(key=lambda d: (_ver_tuple(os.path.basename(d)), "-CODE-" in os.path.basename(d)))
    return cands[-1]

def _engine_version(bundle):
    init = os.path.join(bundle, "mamey", "__init__.py")
    try:
        txt = open(init, errors="replace").read()
        m = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", txt)
        return m.group(1) if m else "?"
    except Exception:
        return "?"

def main():
    try:
        bundle = _newest_bundle()
        if not bundle:
            return 0
        b = os.path.basename(bundle)
        eng = _engine_version(bundle)
        msg = (
            "SAPOTE-MAMEY VERSION GUARD (read before responding). "
            f"CURRENT working engine = {b} (mamey __version__ {eng}). "
            "HARD RULE: on-disk Mode-B cards, deliverables, and folders may be from an OLDER engine "
            "(e.g. mode_b_v9.7.339/). Do NOT assert a defect, author a 'correction', or build a card "
            "from a stale card's content — first VERIFY against the CURRENT engine (mamey/modeb_*.py, "
            "mamey/antismash_evidence.py, mamey/modeb_class_checklist.py) or regenerate the card with "
            "the current engine. Before Mode-B / patch / audit / BLASTp / clade work, read the current "
            f"bundle's CURRENT_DOCS_INDEX.md (in {b}) as the authority for what is current. "
            "When in doubt about the version, check memory current-working-version."
        )
        out = {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": msg}}
        sys.stdout.write(json.dumps(out))
    except Exception:
        pass
    return 0

if __name__ == "__main__":
    sys.exit(main())
