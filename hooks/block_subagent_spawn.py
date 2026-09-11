#!/usr/bin/env python3
"""PreToolUse hook — DENY subagent spawning (Agent / Task) by default.

WHY (measured, 2026-08-10 — not a story this time):
  the Developer or User stopped the a contributor lane analyst lane over a token count they judged far too high.
  Nobody could say *why* it was high, because the subagents' transcripts do not exist
  anywhere on disk. The lane's own transcript survives; the 42 subagents it launched left
  only their final reports. That is the gap this hook closes.

  Measured across the six analyst lanes (Tools/session_cost_audit.py, same day):

    lane          main-thread tokens   analyses on disk   tokens/analysis   Agent calls
    Mango Tango          35.1M               62               0.57M              6
    Sea Green            24.5M               41               0.60M              4
    Wisteria             20.6M               13               1.58M             27
    a contributor lane                 38.6M               23               1.68M              2
    a contributor lane           86.4M               28               3.09M             42
    Cadet Blue           36.3M               11               3.30M             19

  The two cheapest lanes per delivered analysis are the two that barely delegated. The two
  dearest are two of the three heaviest delegators. Wisteria breaks the monotone (most
  Agent calls per file, middling cost), so delegation count alone does NOT explain lane
  cost — n=6, this is a strong association, not a proven mechanism. What IS certain:
  a subagent's token spend and reasoning are unrecoverable afterwards. You cannot audit
  what was never written down.

  the Developer or User, 2026-08-10: "subagents are supposed to be forbidden for workhorses" /
  "we have to fix this. Full Stop."  OUTPUT_SPEC §6 already said "do not spawn subagents";
  all six lanes did anyway. Prose is not enforcement. This is.

SCOPE — narrowed 2026-08-10 on the Developer or User's explicit wording, given twice:
  "subagents are supposed to be forbidden for workhorses" and, to the patch lane,
  "i meant no subagents for the workhorse chats."

  An earlier version of this hook denied EVERYONE. That was my over-reach, argued from Agent
  call counts (the phylogenomics lane 308, a contributor lane 238) that turned out to be LIFETIME totals set against
  a one-day window; in the same-day window those chats made ZERO calls. Retracted.

BEHAVIOUR
  DENY only for chats listed in SAPOTE_CONTROL/MAINTENANCE_LANES.tsv (the Mode-B analyst lanes).
  Builder/patch/phylo lanes are allowed. Identity is resolved from the session's own transcript
  by STATE.md write frequency — NOT .claude/current_chat_color, which is one shared file that
  concurrent chats overwrite (it read "Sea Green" while four other chats were live).
  A session id in .claude/SUBAGENT_ALLOWLIST.tsv (or the word ALL) overrides the ban.

  EVERY attempt — allowed or denied — is appended to SAPOTE_CONTROL/SUBAGENT_ATTEMPTS.tsv, so
  a permitted lane's delegation stays auditable even though its subagent transcripts are not.
  That log is the only trace such work leaves.

Claim ceiling: process/accounting guardrail only. No BGC, novelty, activity or production
claim is made or changed.
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # <repo>/.claude/hooks/x.py -> <repo>
ALLOWLIST = os.path.join(ROOT, ".claude", "SUBAGENT_ALLOWLIST.tsv")
LEDGER = os.path.join(ROOT, "SAPOTE_CONTROL", "SUBAGENT_ATTEMPTS.tsv")
ROSTER = os.path.join(ROOT, "SAPOTE_CONTROL", "MAINTENANCE_LANES.tsv")


def workhorse_names():
    """Colors/session-ids of the banned workhorse lanes. Empty roster = ban nobody."""
    out = set()
    try:
        with open(ROSTER) as fh:
            for line in fh:
                if line.startswith("#"):
                    continue
                first = line.split("\t")[0].strip()
                if first and first.lower() != "color":
                    out.add(first.lower())
    except FileNotFoundError:
        pass
    return out


def whoami(transcript_path, session_id):
    """Which chat is this? By STATE.md write frequency in its own transcript.

    Deliberately NOT .claude/current_chat_color: that is a single shared file which concurrent
    chats overwrite, and it was demonstrably mis-set (reading "Sea Green" for another chat)
    on the day this hook was written.

    Pattern matches the v97395 fix already established and tested in the sibling
    Tools/session_cost_audit.py::identify() (same STATE.md-write-frequency method): the
    original pattern here required a literal "sessions/" immediately before the color name,
    which this project's real STATE.md write convention never produces -- it matched a
    genuine write in essentially none of this project's actual session transcripts, silently
    disabling identity resolution (and therefore the workhorse ban itself) for every chat on
    the real convention. Matching on the STATE.md-owning directory's own name, independent of
    its parent directory's name, both fixes that and stays robust to a future rename.
    """
    if not transcript_path or not os.path.exists(transcript_path):
        return None
    pat = re.compile(rb"([A-Za-z][A-Za-z ]{2,20}?)/STATE\.md")
    counts = {}
    try:
        with open(transcript_path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 22), b""):
                for m in pat.finditer(chunk):
                    k = m.group(1).decode()
                    counts[k] = counts.get(k, 0) + 1
    except Exception:
        return None
    return max(counts, key=counts.get) if counts else None


def allowed(session_id):
    """the Developer or User-controlled allowlist. Missing/empty file means nobody is allowed."""
    try:
        with open(ALLOWLIST) as fh:
            for line in fh:
                tok = line.split("#", 1)[0].strip()
                if not tok:
                    continue
                if tok == "ALL" or (session_id and tok in session_id):
                    return True
    except FileNotFoundError:
        pass
    return False


def log(session_id, decision, subagent_type, desc, chat="?"):
    try:
        os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
        new = not os.path.exists(LEDGER)
        with open(LEDGER, "a") as fh:
            if new:
                fh.write("utc_timestamp\tsession_id\tchat\tdecision\tsubagent_type\tdescription\n")
            clean = " ".join(str(desc or "").split())[:160]
            fh.write(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')}\t"
                     f"{session_id}\t{chat}\t{decision}\t{subagent_type or '(default)'}\t{clean}\n")
    except Exception:
        pass  # a logging failure must never break the user's turn


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    if payload.get("tool_name") not in ("Agent", "Task"):
        return 0

    ti = payload.get("tool_input") or {}
    sid = payload.get("session_id") or "?"
    desc = ti.get("description") or ti.get("prompt", "")[:120]
    sub = ti.get("subagent_type")

    chat = whoami(payload.get("transcript_path"), sid) or "?"
    roster = workhorse_names()
    is_workhorse = chat.lower() in roster or (sid and sid.lower() in roster)

    if allowed(sid):
        log(sid, "ALLOW_allowlisted", sub, desc, chat)
        return 0

    if not is_workhorse:
        # Builder/patch/phylo lane: permitted, but LOGGED — a subagent's transcript is never
        # written to disk, so this row is the only trace the delegation leaves.
        log(sid, "ALLOW_not_workhorse", sub, desc, chat)
        return 0

    log(sid, "DENY_workhorse", sub, desc, chat)

    reason = (
        "BLOCKED — subagents are forbidden for WORKHORSE lanes, and this chat ("
        + chat + ") is on the workhorse roster.\n\n"
        "Standing rule (the Developer or User, 2026-08-10): \"i meant no subagents for the workhorse chats.\"\n\n"
        "WHY, measured rather than asserted: a subagent's transcript is NOT persisted "
        "anywhere on disk. When the Developer or User asked why one analyst lane had spent so many tokens, "
        "its 42 subagents had left only their final reports — the reasoning, the reads and "
        "the spend were unrecoverable. The lanes that read GBKs one at a time, in-session "
        "(Mango Tango, Sea Green), delivered an analysis for ~0.57-0.60M tokens; the two "
        "heaviest delegators cost ~3.1-3.3M per analysis, 5x more.\n\n"
        "DO THIS INSTEAD: read the region yourself, in this session. Read/Grep/Glob/Bash "
        "are all still available and all leave a record. Your accumulated strain context "
        "(assembly quality, PKS/NRPS families, RG-GMCI shape) is most of your speed by the "
        "fifth region on a strain — a subagent cannot carry it, so delegation pays tokens "
        "to throw away the thing that makes you fast.\n\n"
        "If you genuinely believe this task needs delegation: STOP and ask the Developer or User in chat, "
        "stating the task and why in-session reading will not do. the Developer or User grants exceptions by "
        "adding your session id to .claude/SUBAGENT_ALLOWLIST.tsv. "
        f"Your session id is {sid}.\n\n"
        "This attempt has been logged to SAPOTE_CONTROL/SUBAGENT_ATTEMPTS.tsv."
    )

    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
