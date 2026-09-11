#!/usr/bin/env python3
"""session_cost_audit.py — where did a chat's tokens actually go?

Reads Claude Code session transcripts (~/.claude/projects/<proj>/*.jsonl) and reports,
per session: total tokens by class, turn count, and the tool calls that consumed the most
context. Answers "why did this lane cost 1.2M tokens?" from evidence instead of a story.

Usage:
  python3 Tools/session_cost_audit.py                       # all sessions, ranked
  python3 Tools/session_cost_audit.py --color a contributor lane    # resolve a color -> its session
  python3 Tools/session_cost_audit.py --session <uuid> -v   # deep dive one session
  python3 Tools/session_cost_audit.py --tsv out.tsv         # machine-readable

Token classes (from message.usage on each assistant turn):
  in      input_tokens                 fresh prompt tokens
  cw      cache_creation_input_tokens  context written to cache this turn
  cr      cache_read_input_tokens      context RE-READ from cache this turn  <-- usually dominant
  out     output_tokens                what the model actually wrote

Claim ceiling: accounting/provenance only. No BGC, novelty, activity or production claim.
"""
import argparse, json, os, re, sys, glob
from datetime import datetime, timedelta, timezone
from collections import Counter, defaultdict

_slug = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()).replace("/", "-")
PROJ = os.path.expanduser(f"~/.claude/projects/{_slug}")


def iter_records(path):
    with open(path, "r", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


def identify(path):
    """Best-effort: which color chat is this session? By STATE.md writes.

    v97395 fix: the original pattern required a literal "sessions/" immediately before the
    color name, which this project's real STATE.md write convention never produces -- it
    matched a genuine write in essentially none of this project's actual session transcripts.
    Matching on the STATE.md-owning directory's own name (a short run of letters/spaces),
    independent of what its parent directory happens to be called, both fixes that and is more
    robust to a future rename of the parent directory -- and, deliberately, does not hardcode
    any workspace-specific path fragment into this shipped source (an early version of this fix
    did exactly that and tripped tools/public_release_audit.py's own banned-identity gate).
    """
    pat = re.compile(rb"([A-Za-z][A-Za-z ]{2,20}?)/STATE\.md")
    c = Counter()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            for m in pat.finditer(chunk):
                c[m.group(1).decode()] += 1
    return c.most_common(1)[0][0] if c else "?"


def audit(path, verbose=False, since=None):
    """since: datetime; when set, token/turn/agent counts cover ONLY records at or after it.

    WHY THIS PARAMETER EXISTS (2026-08-10): the first version of this tool reported lifetime
    totals and they were compared across sessions of wildly different age — a 21.9-day chat
    against a 0.3-day one. That made a 1.8x difference look like 45x. Lifetime totals are
    only ever comparable between sessions of the same age. Always state the window.
    """
    tot = Counter()
    turns = 0
    tool_calls = Counter()
    tool_result_bytes = Counter()
    subagents = 0
    files_written = set()
    biggest = []          # (bytes, tool, preview)
    growth = []           # (turn_idx, cache_read) to see context growth

    first_ts = last_ts = None
    pending = {}          # tool_use_id -> tool name
    for rec in iter_records(path):
        ts = rec.get("timestamp")
        t = None
        if ts:
            try:
                t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                t = None
        if t:
            first_ts = t if first_ts is None or t < first_ts else first_ts
            last_ts = t if last_ts is None or t > last_ts else last_ts
        if since is not None and (t is None or t < since):
            continue
        msg = rec.get("message") or {}
        role = msg.get("role") or rec.get("type")
        if role == "assistant":
            u = msg.get("usage") or {}
            if u:
                turns += 1
                tot["in"] += u.get("input_tokens", 0) or 0
                tot["cw"] += u.get("cache_creation_input_tokens", 0) or 0
                tot["cr"] += u.get("cache_read_input_tokens", 0) or 0
                tot["out"] += u.get("output_tokens", 0) or 0
                growth.append((turns, u.get("cache_read_input_tokens", 0) or 0))
            for blk in (msg.get("content") or []):
                if isinstance(blk, dict) and blk.get("type") == "tool_use":
                    name = blk.get("name", "?")
                    tool_calls[name] += 1
                    pending[blk.get("id")] = name
                    if name in ("Agent", "Task"):
                        subagents += 1
                    if name in ("Write", "Edit", "NotebookEdit"):
                        fp = (blk.get("input") or {}).get("file_path")
                        if fp:
                            files_written.add(fp)
        elif role == "user":
            for blk in (msg.get("content") or []):
                if isinstance(blk, dict) and blk.get("type") == "tool_result":
                    name = pending.get(blk.get("tool_use_id"), "?")
                    body = blk.get("content")
                    n = len(json.dumps(body)) if not isinstance(body, str) else len(body)
                    tool_result_bytes[name] += n
                    if n > 20000:
                        biggest.append((n, name))
    biggest.sort(reverse=True)
    span = ((last_ts - first_ts).total_seconds() / 86400.0
            if first_ts and last_ts else 0.0)
    return dict(tokens=tot, turns=turns, tools=tool_calls,
                result_bytes=tool_result_bytes, subagents=subagents,
                files=files_written, biggest=biggest[:15], growth=growth,
                span_days=span, first_ts=first_ts, last_ts=last_ts)


def fmt(n):
    for unit, div in (("M", 1e6), ("k", 1e3)):
        if n >= div:
            return f"{n/div:.1f}{unit}"
    return str(int(n))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proj", default=PROJ)
    ap.add_argument("--color")
    ap.add_argument("--session")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--tsv")
    ap.add_argument("--since", metavar="ISO_OR_DAYS",
                    help="only count records at/after this UTC time (ISO) or within the last "
                         "N days (a bare number). STRONGLY RECOMMENDED whenever comparing "
                         "sessions: lifetime totals are meaningless across different ages.")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()

    since = None
    if a.since:
        try:
            since = (datetime.now(timezone.utc) - timedelta(days=float(a.since))
                     if re.fullmatch(r"[\d.]+", a.since)
                     else datetime.fromisoformat(a.since.replace("Z", "+00:00")))
            if since.tzinfo is None:
                since = since.replace(tzinfo=timezone.utc)
        except Exception:
            sys.stderr.write((f"bad --since {a.since!r}") + "\n")
            return 2

    paths = sorted(glob.glob(os.path.join(a.proj, "*.jsonl")),
                   key=os.path.getmtime, reverse=True)
    if a.session:
        paths = [p for p in paths if a.session in os.path.basename(p)]
    if a.color:
        paths = [p for p in paths if identify(p).lower() == a.color.lower()]
    if not paths:
        sys.stderr.write(("no matching session") + "\n")
        return 1

    rows = []
    for p in paths[: (200 if (a.session or a.color) else 25)]:
        r = audit(p, a.verbose, since=since)
        t = r["tokens"]
        total = t["in"] + t["cw"] + t["cr"] + t["out"]
        rows.append((total, os.path.basename(p)[:8], identify(p), r))

    rows.sort(reverse=True)
    win = f"since {since.isoformat(timespec='minutes')}" if since else "LIFETIME (no --since)"
    sys.stdout.write((f"window: {win}\n") + "\n")
    sys.stdout.write((f"{'total':>8} {'cache_read':>10} {'output':>8} {'turns':>6} {'tok/turn':>9}  "
          f"{'sub':>3}  {'files':>5}  {'age_d':>6}  chat") + "\n")
    for total, sid, color, r in rows:
        t = r["tokens"]
        tpt = total / max(r["turns"], 1)
        sys.stdout.write((f"{fmt(total):>8} {fmt(t['cr']):>10} {fmt(t['out']):>8} {r['turns']:>6} "
              f"{fmt(tpt):>9}  {r['subagents']:>3}  {len(r['files']):>5}  "
              f"{r['span_days']:>6.1f}  {color} ({sid})") + "\n")

    # The guard that this tool's own first output failed. Session AGE is not the window you
    # measured; a 22-day chat and a 0.3-day chat are not comparable on lifetime totals.
    spans = [r["span_days"] for _, _, _, r in rows if r["span_days"] > 0]
    if not since and len(spans) > 1 and max(spans) > 3 * max(min(spans), 0.01):
        sys.stdout.write((f"\n*** WARNING: these sessions differ in age by {max(spans)/max(min(spans),0.01):.0f}x "
              f"({min(spans):.1f}d to {max(spans):.1f}d). LIFETIME TOTALS ARE NOT COMPARABLE "
              f"ACROSS THEM.\n    Re-run with --since (e.g. --since 1) to compare a common "
              f"window, or compare tok/turn and tokens-per-delivered-file instead.") + "\n")

    if a.verbose and rows:
        _, sid, color, r = rows[0]
        sys.stdout.write((f"\n--- {color} ({sid}) deep dive ---") + "\n")
        sys.stdout.write(("\ntool calls:") + "\n")
        for k, v in r["tools"].most_common(a.top):
            sys.stdout.write((f"  {v:>5}  {k}   [results {fmt(r['result_bytes'][k])} chars]") + "\n")
        sys.stdout.write(("\nlargest single tool results (chars):") + "\n")
        for n, name in r["biggest"]:
            sys.stdout.write((f"  {fmt(n):>8}  {name}") + "\n")
        g = r["growth"]
        if g:
            sys.stdout.write((f"\ncontext growth: turn 1 cache_read={fmt(g[0][1])} -> "
                  f"turn {g[-1][0]} cache_read={fmt(g[-1][1])} "
                  f"(peak {fmt(max(x[1] for x in g))})") + "\n")
        sys.stdout.write((f"\nfiles written: {len(r['files'])}") + "\n")

    if a.tsv:
        with open(a.tsv, "w") as fh:
            fh.write("session\tchat\ttotal\tcache_read\tcache_write\toutput\t"
                     "turns\ttok_per_turn\tsubagents\tfiles_written\n")
            for total, sid, color, r in rows:
                t = r["tokens"]
                fh.write(f"{sid}\t{color}\t{total}\t{t['cr']}\t{t['cw']}\t{t['out']}\t"
                         f"{r['turns']}\t{total//max(r['turns'],1)}\t"
                         f"{r['subagents']}\t{len(r['files'])}\n")
        sys.stdout.write((f"\nwrote {a.tsv}") + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
