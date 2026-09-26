import os
#!/usr/bin/env python3
"""PostToolUse provenance logger. Reads event session_id and tool-use JSON on stdin,
appends one row to the firehose TSV. Never blocks / never errors out loud.
argv: <log_path> [legacy_chat_fallback]."""
import sys, json, os, datetime, re

def main():
    log = sys.argv[1] if len(sys.argv) > 1 else ""
    fallback = sys.argv[2] if len(sys.argv) > 2 else "unattributed"
    root = (os.environ.get("SAPOTE_WORKSPACE_ROOT") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    try:
        d = json.load(sys.stdin)
    except Exception:
        return
    session_id = d.get("session_id")
    # The shared color marker can name another concurrent session. Prefer the
    # event's own id, and reject control characters before writing a TSV row.
    if session_id is None:
        chat = fallback
    elif isinstance(session_id, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", session_id):
        chat = session_id
    else:
        chat = "unattributed"
    tool = d.get("tool_name", "")
    if tool not in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        return
    ti = d.get("tool_input", {}) or {}
    fp = ti.get("file_path") or ti.get("notebook_path") or ""
    if not fp:
        return
    # Boundary-safe prefix check: bare `fp.startswith(root)` is a false positive for a sibling
    # path that merely shares root's string prefix with no path separator between them (e.g.
    # root=".../Workspace", fp=".../Workspace_archive/x.md") -- this project's workspaces
    # routinely have dated/versioned/archived sibling folder names, so that collision is a real
    # risk, not a hypothetical one. A false-positive match takes the relpath branch (meant only
    # for genuinely-inside paths) and logs a "../"-prefixed relative path for a file that is not
    # actually under root at all, defeating this branch's own intent of showing an unambiguous
    # absolute path for anything outside the workspace.
    root_norm = os.path.normpath(root)
    fp_norm = os.path.normpath(fp)
    inside_root = fp_norm == root_norm or fp_norm.startswith(root_norm + os.sep)
    rel = os.path.relpath(fp, root) if inside_root else fp
    try:
        os.makedirs(os.path.dirname(log), exist_ok=True)
        new = not os.path.exists(log)
        with open(log, "a") as f:
            if new:
                f.write("timestamp\ttool\tpath\tchat\n")
            f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}\t{tool}\t{rel}\t{chat}\n")
    except Exception:
        return

if __name__ == "__main__":
    main()
