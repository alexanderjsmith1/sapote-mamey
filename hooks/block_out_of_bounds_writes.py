import os
#!/usr/bin/env python3
"""PreToolUse GUARDRAIL — DENY any write outside the allowed roots.

WHY (2026-08-18, the roster lane): Claude wrote deliverable files into a sibling agent's
workspace (the Codex workspace) — OUTSIDE this project root. That is an instruction/house-rule
boundary (shared-corpus boundary; the Codex workspace is read-only to
this chat) that had NO enforced hook. This hook makes it impossible: every Write/Edit/MultiEdit/
NotebookEdit whose target resolves outside the allowlist is DENIED, and Bash write-ops whose TARGET is
an out-of-bounds path are DENIED as defense-in-depth.

ALLOWED write roots (everything else is denied):
  * the workspace root ($SAPOTE_WORKSPACE_ROOT / $CLAUDE_PROJECT_DIR, defaulting to this project)
  * ~/.claude                                (Claude config + this session's memory files)
  * /private/tmp, /tmp, /var/folders         (scratch / OS temp)

READS are never blocked. For Bash, only the WRITE TARGET is inspected (redirect target; cp/mv/rsync/ln/
install destination; mkdir/touch/rmdir/truncate/sed -i/dd targets). A command that merely *mentions* an
out-of-bounds path — e.g. writing a log line that quotes it, or `cp <codex-file> ./local` (read source)
— is ALLOWED, because the write target is in-bounds. Heredoc bodies are ignored (never a target).

FAIL-CLOSED: any internal error DENIES (a broken hard-boundary guard must not fail open).
Deny = stdout JSON permissionDecision:deny, exit 0 (same contract as block_sealed_tree_edits.sh).
"""
import sys, json, os, re, shlex

ALLOWED_ROOTS_RAW = [
    (os.environ.get("SAPOTE_WORKSPACE_ROOT") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()),
    os.path.expanduser("~/.claude"),
    "/private/tmp",
    "/tmp",
    "/var/folders",
    "/dev",  # shell plumbing: >/dev/null, 2>/dev/null, /dev/stdout, etc. (not a workspace)
]

def _deny(reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason}}))
    sys.exit(0)

def _fail_closed(detail):
    _deny("GUARDRAIL INTERNAL ERROR in block_out_of_bounds_writes.py — failing CLOSED "
          f"({detail}). The hook broke, not your command. Fix the hook, then retry.")

def _real(p):
    try:
        return os.path.realpath(p)
    except Exception:
        return p

def _allowed_roots():
    return [_real(r) for r in ALLOWED_ROOTS_RAW]

def _under_allowed(abspath, roots):
    rp = _real(abspath)
    return any(rp == root or rp.startswith(root + os.sep) for root in roots)

def _resolve(path, cwd):
    if not os.path.isabs(path):
        path = os.path.join(cwd, path)
    return path

def _looks_like_path(tok):
    # a token worth checking as a filesystem target
    return ("/" in tok) or tok not in ("", ".", "..")

# commands whose DESTINATION is the last path argument
DEST_LAST = {"cp", "mv", "rsync", "install", "ln"}
# commands where every non-flag path arg is a write target
ALL_ARGS = {"mkdir", "touch", "rmdir", "truncate"}

def bash_write_targets(cmd):
    """Return the list of path tokens that this command would WRITE to. Heredoc bodies ignored."""
    head = cmd.split("<<", 1)[0] if "<<" in cmd else cmd  # heredoc body is content, never a target
    # split on shell separators so each simple command is handled on its own
    segments = re.split(r"(?:&&|\|\||[;|&]|\n)", head)
    targets = []
    redir = re.compile(r'^(?:[0-9]*|&)?(?:>>?|>\|)(.*)$')  # >  >>  >|  2>  &>  (glued or not)
    for seg in segments:
        try:
            toks = shlex.split(seg, posix=True)
        except Exception:
            toks = seg.split()
        if not toks:
            continue
        # 1) redirections anywhere in the segment
        i = 0
        while i < len(toks):
            m = redir.match(toks[i])
            if m:
                tgt = m.group(1)
                if tgt:
                    targets.append(tgt)
                elif i + 1 < len(toks):
                    targets.append(toks[i + 1]); i += 1
            i += 1
        # 2) file-writing commands
        # strip leading env-assignments / sudo
        argv = [t for t in toks if not re.match(r'^\w+=', t)]
        if not argv:
            continue
        cmd0 = os.path.basename(argv[0])
        rest = [t for t in argv[1:] if not t.startswith("-") and not redir.match(t)]
        if cmd0 in DEST_LAST and rest:
            targets.append(rest[-1])
        elif cmd0 in ALL_ARGS:
            targets.extend(rest)
        elif cmd0 == "sed" and any(a == "-i" or a.startswith("-i") for a in argv[1:]):
            targets.extend(rest)
        elif cmd0 == "tee":
            targets.extend(rest)
        elif cmd0 == "dd":
            for t in argv[1:]:
                if t.startswith("of="):
                    targets.append(t[3:])
    return [t for t in targets if _looks_like_path(t)]

def main():
    try:
        data = json.load(sys.stdin)
    except Exception as e:
        _fail_closed(f"stdin parse: {e}")
    try:
        tool = data.get("tool_name", "") or ""
        ti = data.get("tool_input", {}) or {}
        cwd = data.get("cwd") or os.getcwd() or ALLOWED_ROOTS_RAW[0]
        roots = _allowed_roots()

        if tool in ("Write", "Edit", "MultiEdit"):
            path = ti.get("file_path", "") or ""
            if path and not _under_allowed(_resolve(path, cwd), roots):
                _deny(
                    f"BLOCKED by out-of-bounds guardrail: writing to '{path}' is OUTSIDE the allowed "
                    "roots. Deliverables go in THIS project only — your own chat folder is "
                    "'sessions/the roster lane/'. Never write into another agent's workspace "
                    "(e.g. the Codex workspace) or anywhere outside the workspace root "
                    f"('{ALLOWED_ROOTS_RAW[0]}'). Produce the file here and hand off the "
                    "path; the other chat/agent pulls it. See memory: shared-tool-and-corpus-boundary, "
                    "patch-chat-folder-is-only-place.")
            return 0

        if tool == "NotebookEdit":
            path = ti.get("notebook_path", "") or ti.get("file_path", "") or ""
            if path and not _under_allowed(_resolve(path, cwd), roots):
                _deny(f"BLOCKED by out-of-bounds guardrail: editing notebook '{path}' is OUTSIDE the "
                      "allowed roots (this project + .claude + tmp). Work inside "
                      f"'{ALLOWED_ROOTS_RAW[0]}' only.")
            return 0

        if tool == "Bash":
            cmd = ti.get("command", "") or ""
            bad = [t for t in bash_write_targets(cmd) if not _under_allowed(_resolve(t, cwd), roots)]
            if bad:
                _deny(
                    "BLOCKED by out-of-bounds guardrail: this Bash command WRITES to a path outside "
                    f"this project: {bad[:4]}. Never write into another agent's workspace (e.g. "
                    "the Codex workspace) or outside the workspace root "
                    f"('{ALLOWED_ROOTS_RAW[0]}'). Reading such a path is fine; only the "
                    "write target is blocked. Produce the file in this project and hand off the path. "
                    "See memory: shared-tool-and-corpus-boundary.")
            return 0

        return 0
    except SystemExit:
        raise
    except Exception as e:
        _fail_closed(f"main: {e}")

if __name__ == "__main__":
    main()
