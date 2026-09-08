#!/usr/bin/env python3
"""save_transcript.py — export the live Claude Code session transcript (INCLUDING inner
monologue / thinking blocks) to a readable Markdown file in a color folder.

Continuity tool for the roster lane chat: STATE.md is my *summary*; this is the
ground-truth transcript with reasoning, so a post-compaction restart can see how a
decision was actually reached, not just its conclusion.

Each run writes two files into <color>/TRANSCRIPTS/:
  transcript_<session>_<YYYY-MM-DD_HHMM>.md   (timestamped snapshot, kept)
  transcript_latest.md                        (overwritten pointer to the newest)

Usage:
  python Tools/save_transcript.py                       # newest session -> the roster lane
  python Tools/save_transcript.py --color "Green Chat"  # different color folder
  python Tools/save_transcript.py --session <id>        # a specific session jsonl
  python Tools/save_transcript.py --max-result-chars 4000
"""
from __future__ import annotations
import argparse, json, os, sys, datetime as dt
from pathlib import Path

ROOT = Path(os.environ.get("SAPOTE_ROOT", os.environ.get("MAMEY_DATA_ROOT", os.getcwd())))
PROJECTS = Path(os.path.expanduser(os.environ.get("CLAUDE_PROJECTS_DIR", "~/.claude/projects")))


def chat_dir(root: Path, color: str) -> Path | None:
    """Which subdirectory of ROOT holds this color chat's own folder?

    $SAPOTE_CHAT_DIR wins if set -- explicit override, no discovery attempted. Otherwise,
    discover it structurally: check each direct subdirectory of ROOT for a `<color>/STATE.md`
    -- the per-chat continuity file every color chat maintains -- rather than hardcoding this
    project's own private workspace-folder name into shipped source. Candidates are deduped by
    `(st_dev, st_ino)` before counting, so a symlink alias to the same physical directory (set
    up for some other tool's hardcoded path expectation, as has happened live in this workspace)
    is not mistaken for a second, distinct candidate. Exactly one structural match is
    authoritative. Two or more genuinely distinct matches is an ambiguity this hook cannot
    resolve alone, so it refuses -- warns to stderr and returns None -- rather than silently
    picking the first sorted match. Falls back to the legacy `sessions` default only when
    nothing structural is found at all, so behavior when neither exists is unchanged from
    before.
    """
    env = os.environ.get("SAPOTE_CHAT_DIR")
    if env:
        return root / env
    try:
        seen: dict[tuple[int, int], Path] = {}
        for entry in sorted(root.iterdir()):
            if not entry.is_dir():
                continue
            if not (entry / color / "STATE.md").exists():
                continue
            st = entry.stat()
            seen.setdefault((st.st_dev, st.st_ino), entry)
        if len(seen) == 1:
            return next(iter(seen.values()))
        if len(seen) > 1:
            names = ", ".join(str(p) for p in seen.values())
            print(f"save_transcript: WARNING ambiguous chat dir for {color!r} -- "
                  f"{len(seen)} distinct candidates ({names}) -- refusing to guess, "
                  f"set $SAPOTE_CHAT_DIR to disambiguate", file=sys.stderr)
            return None
    except OSError:
        pass
    return root / "sessions"


def newest_jsonl() -> Path | None:
    js = sorted(PROJECTS.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    return js[0] if js else None


def resolve_jsonl(color: str, session: str | None) -> tuple[Path | None, str]:
    """Pick the right transcript. Priority: explicit --session > color-folder `.session_id`
    pin > newest. Newest-mtime is UNSAFE here — multiple color chats write concurrently, so
    it often points at a neighbor's session. The pin file is the reliable anchor."""
    if session:
        return PROJECTS / f"{session}.jsonl", "explicit"
    cdir = chat_dir(ROOT, color)
    if cdir is not None:
        pin = cdir / color / ".session_id"
        if pin.exists():
            sid = pin.read_text().strip()
            p = PROJECTS / f"{sid}.jsonl"
            if p.exists():
                return p, "pinned"
            print(f"save_transcript: WARNING pinned session {sid} has no jsonl — falling back to newest")
    return newest_jsonl(), "newest(fallback)"


def _trunc(s: str, n: int) -> str:
    s = s if isinstance(s, str) else json.dumps(s, ensure_ascii=False)
    return s if len(s) <= n else s[:n] + f"\n…[truncated {len(s)-n} chars]…"


def render(jsonl: Path, max_result_chars: int) -> tuple[str, dict]:
    lines = jsonl.read_text(errors="replace").splitlines()
    out: list[str] = []
    stats = {"user": 0, "assistant": 0, "thinking_blocks": 0, "tool_uses": 0, "events": 0}
    out.append(f"# Transcript (with inner monologue) — {jsonl.stem}\n")
    out.append(f"*Exported {dt.datetime.now():%Y-%m-%d %H:%M} · {len(lines)} events · "
               f"source `{jsonl.name}`*\n")
    out.append("> Full session ground truth including 🧠 thinking blocks. Class-level "
               "hypotheses / judgment deferred — same claim-safety as every deliverable.\n")
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        try:
            ev = json.loads(ln)
        except Exception:
            continue
        stats["events"] += 1
        typ = ev.get("type")
        msg = ev.get("message") or {}
        ts = ev.get("timestamp", "")
        tstr = ""
        if ts:
            try:
                tstr = dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%H:%M:%S")
            except Exception:
                tstr = str(ts)[:19]
        role = msg.get("role") or typ
        content = msg.get("content")
        if typ == "summary":
            out.append(f"\n---\n### 📎 [compaction summary]\n\n{_trunc(ev.get('summary',''), max_result_chars)}\n")
            continue
        if role not in ("user", "assistant"):
            continue
        stats[role] = stats.get(role, 0) + 1
        out.append(f"\n---\n## {'🧑 USER' if role=='user' else '🤖 ASSISTANT'}  ·  {tstr}\n")
        if isinstance(content, str):
            out.append(content + "\n")
            continue
        if not isinstance(content, list):
            out.append(_trunc(content, max_result_chars) + "\n")
            continue
        for blk in content:
            if not isinstance(blk, dict):
                out.append(str(blk) + "\n"); continue
            bt = blk.get("type")
            if bt == "text":
                out.append(blk.get("text", "") + "\n")
            elif bt == "thinking":
                stats["thinking_blocks"] += 1
                th = blk.get("thinking", "")
                out.append("> 🧠 **inner monologue**\n>\n" +
                           "\n".join("> " + l for l in th.splitlines()) + "\n")
            elif bt == "tool_use":
                stats["tool_uses"] += 1
                nm = blk.get("name", "?")
                inp = _trunc(blk.get("input", {}), 1200)
                out.append(f"**🛠 tool_use → `{nm}`**\n\n```json\n{inp}\n```\n")
            elif bt == "tool_result":
                c = blk.get("content", "")
                if isinstance(c, list):
                    c = "\n".join(x.get("text", "") if isinstance(x, dict) else str(x) for x in c)
                out.append(f"**↩ tool_result**\n\n```\n{_trunc(c, max_result_chars)}\n```\n")
            elif bt == "image":
                out.append("*[image omitted]*\n")
            else:
                out.append(_trunc(blk, 800) + "\n")
    return "\n".join(out), stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--color", default="the roster lane")
    ap.add_argument("--session", default=None, help="session id (jsonl stem); default = newest")
    ap.add_argument("--max-result-chars", type=int, default=3000)
    a = ap.parse_args()
    jsonl, how = resolve_jsonl(a.color, a.session)
    if not jsonl or not jsonl.exists():
        print(f"save_transcript: no jsonl found ({jsonl})"); return 1
    print(f"save_transcript: source = {jsonl.name} [{how}]")
    cdir = chat_dir(ROOT, a.color)
    if cdir is None:
        print(f"save_transcript: cannot determine chat dir for color {a.color!r} -- "
              f"ambiguous discovery (see warning above); set $SAPOTE_CHAT_DIR to disambiguate",
              file=sys.stderr)
        return 1
    outdir = cdir / a.color / "TRANSCRIPTS"
    outdir.mkdir(parents=True, exist_ok=True)
    body, stats = render(jsonl, a.max_result_chars)
    stamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M")
    snap = outdir / f"transcript_{jsonl.stem}_{stamp}.md"
    latest = outdir / "transcript_latest.md"
    snap.write_text(body)
    latest.write_text(body)
    kb = len(body.encode()) / 1024
    print(f"save_transcript: wrote {snap.name} ({kb:.0f} KB) + transcript_latest.md")
    print(f"  {stats['events']} events | {stats['assistant']} assistant / {stats['user']} user "
          f"| {stats['thinking_blocks']} thinking blocks | {stats['tool_uses']} tool_uses")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
