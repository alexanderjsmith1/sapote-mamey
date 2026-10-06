import os
#!/usr/bin/env python3
"""chat_link_check.py — Stop-hook guardrail: every markdown link in the assistant's final
reply must point at an EXISTING FILE inside the workspace.

WHY (2026-08-20, the patch lane): the Developer or User clicked four links in one session that did not work. Audit
showed all targets existed — the links were DIRECTORY links (the client opens file links, not
folders) plus one misremembered filename. The percent-encoding rule lived only in memory
([percent-encode-file-links]) and the existing link_check.py checks WHERE_THINGS_LIVE
registration, not chat links. This hook closes the gap.

Flags, advisory + non-blocking (stderr; the session fixes its habit, nothing is refused):
  - MISSING     : the (percent-decoded) target does not exist on disk
  - DIRECTORY   : the target is a folder — link a file inside it, or give the path as plain text
  - OUTSIDE     : the target resolves outside the workspace root (e.g. the Codex tree) —
                  per the standing rule those are given as absolute plain-text paths, not links
  - UNENCODED   : the href contains a raw space / '(' / ')' — clients truncate at these

Skips http(s)/mailto/# anchors. FAIL-OPEN: an internal error stays silent (advisory guard).
"""
import json, os, re, sys, urllib.parse

ROOT = os.environ.get("SAPOTE_WORKSPACE_ROOT") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")  # broad: raw-space hrefs must be SEEN to be flagged


def last_assistant_text(transcript_path):
    text_parts = []
    try:
        with open(transcript_path, errors="replace") as fh:
            lines = fh.readlines()
    except Exception:
        return ""
    for line in reversed(lines):
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("type") != "assistant":
            continue
        msg = d.get("message") or {}
        for blk in (msg.get("content") or []):
            if isinstance(blk, dict) and blk.get("type") == "text":
                text_parts.append(blk.get("text") or "")
        if text_parts:
            return "\n".join(text_parts)
    return ""


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    text = last_assistant_text(data.get("transcript_path") or "")
    if not text:
        return 0
    problems = []
    for href in LINK_RE.findall(text):
        if href.startswith(("http://", "https://", "mailto:", "#")):
            continue
        if " " in href or "(" in href or ")" in href:
            problems.append(f"UNENCODED: {href}")
            continue
        decoded = urllib.parse.unquote(href)
        path = decoded if os.path.isabs(decoded) else os.path.join(ROOT, decoded)
        rp = os.path.realpath(path)
        if not rp.startswith(os.path.realpath(ROOT) + os.sep) and rp != os.path.realpath(ROOT):
            problems.append(f"OUTSIDE workspace (use absolute plain text, not a link): {decoded}")
        elif not os.path.exists(path):
            problems.append(f"MISSING: {decoded}")
        elif os.path.isdir(path):
            problems.append(f"DIRECTORY (link a file inside it, or plain-text the path): {decoded}")
    if problems:
        show = problems[:8]
        more = f" (+{len(problems)-8} more)" if len(problems) > 8 else ""
        sys.stderr.write(
            "⚠ CHAT-LINK CHECK — %d link problem(s) in your last reply%s:\n  %s\n"
            "  → Link only existing FILES inside the workspace (percent-encoded); directories and "
            "out-of-workspace paths go as plain text. Re-send corrected links to the user.\n"
            % (len(problems), more, "\n  ".join(show)))
        if not data.get("stop_hook_active"):
            return 2  # Stop exit 2: the reply is held and the message goes back to Claude, once (the host caps repeats)
    return 0



def _run_visible():
    """Hooks reference: stderr from a hook that exits 0 goes to the debug log only, and nobody sees it (audit F03).
    Run main() with stderr captured. An exit-2 result passes its text through on stderr, which the host feeds back
    to Claude. Any other result shows the text to the user as a systemMessage and exits 0."""
    import io
    buf, real = io.StringIO(), sys.stderr
    sys.stderr = buf
    try:
        rc = main()
    except Exception:
        rc = 0  # advisory: fail open
    finally:
        sys.stderr = real
    text = buf.getvalue().strip()
    if rc == 2:
        sys.stderr.write(text + "\n")
        return 2
    if text:
        print(json.dumps({"systemMessage": text}))
    return 0


if __name__ == "__main__":
    sys.exit(_run_visible())
