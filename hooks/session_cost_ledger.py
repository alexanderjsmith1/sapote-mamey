#!/usr/bin/env python3
"""Stop hook — record this session's token spend so nobody ever has to guess again.

WHY: on 2026-08-10 the Developer or User stopped an analyst lane over a token count and no one — including
the lane's dispatcher — could say where the tokens went or how that lane compared to any
other. The transcripts existed; nothing read them. This appends one row per session per
stop to a ledger, so the comparison is always one `cat` away.

Writes: SAPOTE_CONTROL/SESSION_COST_LEDGER.tsv
Reads:  the session's own transcript (message.usage on each assistant turn)

Token classes: cache_read dominates long agentic sessions — every turn re-reads the whole
context, so cost is roughly (turn count x context size), not any single expensive call.
That is why "tokens per delivered file" is the number worth watching, not raw totals.

Deliberately advisory: it never blocks, never nags, and stays silent unless the session
crosses a threshold worth a human's attention.

Claim ceiling: process/accounting only. No BGC, novelty, activity or production claim.
"""
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # <repo>/.claude/hooks/x.py -> <repo>
LEDGER = os.path.join(ROOT, "SAPOTE_CONTROL", "SESSION_COST_LEDGER.tsv")

# Advisory thresholds. Chosen from the 2026-08-10 measurement, not invented: the efficient
# analyst lanes ran ~0.6M tokens per delivered analysis, the inefficient ones ~3.1-3.3M.
WARN_TOTAL = 500_000_000        # a very large session; worth a glance
WARN_PER_FILE = 3_000_000       # at/above the measured inefficient-lane rate


def identify(path):
    """Which color chat is this? By the STATE.md it writes — the shared
    .claude/current_chat_color marker is unreliable across concurrent chats.

    Pattern matches the v97395 fix already established and tested in
    Tools/session_cost_audit.py::identify() (same STATE.md-write-frequency method): the
    original pattern here required a literal "sessions/" immediately before the color name,
    which this project's real STATE.md write convention never produces — every ledger row
    for a real session recorded chat="?", defeating the ledger's own stated purpose of
    comparing one lane's cost to another's. Matching on the STATE.md-owning directory's own
    name, independent of its parent directory's name, fixes that and stays robust to a future
    rename.
    """
    pat = re.compile(rb"([A-Za-z][A-Za-z ]{2,20}?)/STATE\.md")
    c = Counter()
    try:
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 22), b""):
                for m in pat.finditer(chunk):
                    c[m.group(1).decode()] += 1
    except Exception:
        return "?"
    return c.most_common(1)[0][0] if c else "?"


def scan(path):
    tok = Counter()
    turns = 0
    agents = 0
    files = set()
    for line in open(path, errors="replace"):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        msg = rec.get("message") or {}
        if msg.get("role") != "assistant":
            continue
        u = msg.get("usage") or {}
        if u:
            turns += 1
            for k in ("input_tokens", "cache_creation_input_tokens",
                      "cache_read_input_tokens", "output_tokens"):
                tok[k] += u.get(k, 0) or 0
        for b in (msg.get("content") or []):
            if not isinstance(b, dict) or b.get("type") != "tool_use":
                continue
            if b.get("name") in ("Agent", "Task"):
                agents += 1
            elif b.get("name") in ("Write", "Edit", "NotebookEdit"):
                fp = (b.get("input") or {}).get("file_path")
                if fp:
                    files.add(fp)
    return tok, turns, agents, files


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    path = payload.get("transcript_path")
    sid = (payload.get("session_id") or "?")[:8]
    if not path or not os.path.exists(path):
        return 0

    try:
        tok, turns, agents, files = scan(path)
    except Exception:
        return 0
    if not turns:
        return 0

    total = sum(tok.values())
    nfiles = len(files)
    per_file = total // nfiles if nfiles else 0

    try:
        os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
        new = not os.path.exists(LEDGER)
        with open(LEDGER, "a") as fh:
            if new:
                fh.write("utc_timestamp\tsession\tchat\ttotal_tokens\tcache_read\t"
                         "cache_write\toutput\tturns\tagent_calls\tfiles_written\t"
                         "tokens_per_file\n")
            fh.write(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')}\t{sid}\t"
                     f"{identify(path)}\t{total}\t{tok['cache_read_input_tokens']}\t"
                     f"{tok['cache_creation_input_tokens']}\t{tok['output_tokens']}\t"
                     f"{turns}\t{agents}\t{nfiles}\t{per_file}\n")
    except Exception:
        return 0

    notes = []
    if agents:
        notes.append(f"{agents} subagent call(s) — their transcripts are NOT persisted, so "
                     f"that spend and reasoning cannot be audited later")
    if per_file and per_file >= WARN_PER_FILE:
        notes.append(f"{per_file/1e6:.1f}M tokens per file written — at or above the rate "
                     f"measured for the inefficient analyst lanes (~3.1-3.3M); the efficient "
                     f"lanes ran ~0.6M")
    if total >= WARN_TOTAL:
        notes.append(f"{total/1e6:.0f}M total tokens over {turns} turns — cache re-reads "
                     f"dominate long sessions, so consider a compaction/state save")

    if notes:
        print("SESSION COST (advisory, logged to SAPOTE_CONTROL/SESSION_COST_LEDGER.tsv):",
              file=sys.stderr)
        for n in notes:
            print(f"  - {n}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
