"""test_bootstrap_transitive_no_retired_modes_v9_7_382.py — P0-9 transitive bootstrap guard.

Codex GitHub due-diligence: the front door routes an operator through a CHAIN of docs
(`CHATGPT_START_HERE.md` -> `docs/CHATGPT_EXECUTION_SLICE_*.md` -> ...). Scanning only the front-door
file misses a retired-mode instruction hiding two hops in — which is exactly how
`docs/CHATGPT_EXECUTION_SLICE_v97147.md` kept telling users to run `--mode smoke` / `--mode standard`
after the engine removed smoke (v9.7.161) and aliased standard->gold (v9.7.92).

This test computes the transitive closure of docs reachable from the bootstrap front door and asserts
none of them present a retired-mode RUN COMMAND. It deliberately matches an *invocation*
(`mamey run ... --mode smoke|standard`), NOT prose ABOUT the retired flags — a doc such as
`docs/PER_MODE_ARTIFACT_SET.md` that is explicitly flagged historical and only documents the flags'
removal is legitimate and must not trip the gate. Archival surfaces (batches/, troubleshooting/,
version-stamped docs, CHANGELOG) are excluded from the active-controller closure.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# The bootstrap front door (what an assistant/operator is told to open first).
SEED = [
    "CHATGPT_START_HERE.md", "CLAUDE_START_HERE.md", "000_READ_ME_FIRST_CHATGPT_CLAUDE.md",
    "CHATGPT_READ_ME_FIRST.md", "CHATGTP_READ_ME_FIRST.md",
]
# Archival / historical surfaces: legitimately reference retired modes in a history context.
_EXCL_DIR = ("docs/batches/", "docs/troubleshooting/", "docs/reference/", "docs/GUIDE/", "docs/archive/")
_EXCL_NAME = ("CHANGELOG.md", "RELEASES_LOG.md", "ISSUES_EXPERIENCED_DURING_DEVELOPMENT.md")
_EXCL_VERSIONED = re.compile(r"v9\.7\.\d+|_v9_7_\d+")

# a retired-mode RUN COMMAND (an actual invocation), not prose about the flag.
_RETIRED_RUNCMD = re.compile(
    r"(?:python[^\n]*\bmamey|\bmamey_run\.py|\bmamey)\b[^\n]*\brun\b[^\n]*--mode\s+(?:smoke|standard)")
_MD_REF = re.compile(r"`?((?:docs/)?[A-Za-z0-9_./-]+\.md)`?")


def _excluded(rel: str) -> bool:
    return rel.startswith(_EXCL_DIR) or Path(rel).name in _EXCL_NAME or bool(_EXCL_VERSIONED.search(rel))


def _reachable_active_docs() -> set[str]:
    seen: set[str] = set()
    frontier = [s for s in SEED if (ROOT / s).exists()]
    while frontier:
        cur = frontier.pop()
        if cur in seen or not (ROOT / cur).exists():
            continue
        seen.add(cur)
        for m in _MD_REF.findall((ROOT / cur).read_text(errors="ignore")):
            if (ROOT / m).exists() and not _excluded(m) and m not in seen:
                frontier.append(m)
    return seen


def test_front_door_seed_exists():
    # at least the two primary controllers must be present, or the bootstrap is broken
    present = [s for s in SEED if (ROOT / s).exists()]
    assert "CHATGPT_START_HERE.md" in present and "CLAUDE_START_HERE.md" in present


def test_no_retired_mode_run_command_in_active_chain():
    docs = _reachable_active_docs()
    assert len(docs) > 10, f"closure too small ({len(docs)}); bootstrap graph not traversed"
    offenders = {}
    for d in sorted(docs):
        hits = [ln.strip() for ln in (ROOT / d).read_text(errors="ignore").splitlines()
                if _RETIRED_RUNCMD.search(ln)]
        if hits:
            offenders[d] = hits
    assert not offenders, (
        "Retired-mode (--mode smoke/--mode standard) RUN COMMAND in an active bootstrap doc:\n" +
        "\n".join(f"  {d}: {h}" for d, h in offenders.items()) +
        "\nThe current engine accepts only --mode gold. Fix the controller, or mark the doc historical.")
