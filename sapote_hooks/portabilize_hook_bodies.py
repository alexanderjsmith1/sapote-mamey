#!/usr/bin/env python3
"""portabilize_hook_bodies.py — convert each hook's INTERNAL hardcoded root to a portable
$CLAUDE_PROJECT_DIR reference WITH THE OLD ABSOLUTE PATH AS FALLBACK, so behavior on the current machine
is byte-identical while the hook now also works under any root the bundle lands in.

Behavior-preserving by construction: every rewrite is `env-var OR old-absolute`, so if CLAUDE_PROJECT_DIR
is unset the value is exactly what it was. Operates on COPIES in <lane>/hooks_portable/ (never live), and
syntax-checks every output (bash -n / py_compile). Refs that live only in COMMENTS or MESSAGE strings are
left as-is (cosmetic) and reported. The security hook block_out_of_bounds_writes.py is special-cased
(inject CLAUDE_PROJECT_DIR into its allowlist rather than rewriting message text).

USAGE: python3 portabilize_hook_bodies.py           # writes copies + a report
"""
import os, re, subprocess, sys

ROOT = (os.environ.get("SAPOTE_WORKSPACE_ROOT") or os.environ.get("CLAUDE_PROJECT_DIR") or "/Users/<user>/<workspace>")
HOOKS = os.path.join(ROOT, ".claude", "hooks")
OUT = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "hooks_portable")
OUT = os.path.normpath(OUT)
# DETECTION PATTERN (exempted in test_workspace_path_portability): this tool's job is to FIND the
# bare literal in hook bodies and rewrite it behind ${SAPOTE_WORKSPACE_ROOT:-...}, so the pattern
# itself must stay literal — parametrising it would disable the rewrite.
ABS = "/Users/<user>/<workspace>"

def transform_bash(text):
    changed = 0; left = 0; out = []
    for ln in text.splitlines(keepends=True):
        stripped = ln.lstrip()
        if ABS not in ln:
            out.append(ln); continue
        if stripped.startswith("#"):        # comment — cosmetic, leave
            left += 1; out.append(ln); continue
        # already-env fallback:  ${SAPOTE_WORKSPACE_ROOT:-<ABS>}  -> prefer CLAUDE_PROJECT_DIR first
        if "${SAPOTE_WORKSPACE_ROOT:-" + ABS + "}" in ln:
            ln = ln.replace("${SAPOTE_WORKSPACE_ROOT:-" + ABS + "}",
                            "${CLAUDE_PROJECT_DIR:-${SAPOTE_WORKSPACE_ROOT:-" + ABS + "}}")
            changed += 1; out.append(ln); continue
        # Any abs literal on a non-comment bash line (VAR="<ABS>..." or a "<ABS>/..." command arg):
        # wrapping with ${CLAUDE_PROJECT_DIR:-<ABS>} is valid in every bash double-quoted context and
        # preserves the value when the env var is unset.
        ln = ln.replace(ABS, "${CLAUDE_PROJECT_DIR:-" + ABS + "}")
        changed += 1; out.append(ln)
    return "".join(out), changed, left

def transform_python(text, fname):
    changed = 0; left = 0; out = []
    # special-case the security hook: add CLAUDE_PROJECT_DIR into the allowlist list literal
    special = (fname == "block_out_of_bounds_writes.py")
    for ln in text.splitlines(keepends=True):
        if ABS not in ln:
            out.append(ln); continue
        stripped = ln.lstrip()
        if stripped.startswith("#"):
            left += 1; out.append(ln); continue
        # simple assignment: VAR = "<ABS>"  or  VAR = "<ABS>/sub"
        m = re.match(r'^(\s*)([A-Za-z_]\w*)\s*=\s*"(' + re.escape(ABS) + r')(/[^"]*)?"\s*$', ln)
        if m:
            indent, var, _, sub = m.groups()
            base = f'os.environ.get("CLAUDE_PROJECT_DIR", "{ABS}")'
            rhs = base if not sub else f'os.path.join({base}, "{sub.lstrip("/")}")'
            out.append(f'{indent}{var} = {rhs}\n'); changed += 1; continue
        # argparse default="<ABS>/sub"
        m = re.search(r'default="(' + re.escape(ABS) + r')(/[^"]*)?"', ln)
        if m and "add_argument" in ln:
            sub = m.group(2) or ""
            base = f'os.environ.get("CLAUDE_PROJECT_DIR", "{ABS}")'
            rep = base if not sub else f'os.path.join({base}, "{sub.lstrip("/")}")'
            ln = ln[:m.start()] + "default=" + rep + ln[m.end():]
            out.append(ln); changed += 1; continue
        # allowlist list item in the security hook:  "<ABS>",
        if special and re.match(r'^\s*"' + re.escape(ABS) + r'"\s*,\s*$', ln):
            indent = ln[:len(ln) - len(ln.lstrip())]
            out.append(f'{indent}os.environ.get("CLAUDE_PROJECT_DIR", "{ABS}"),\n'); changed += 1; continue
        left += 1; out.append(ln)           # message string / other — leave (cosmetic)
    body = "".join(out)
    if changed and "import os" not in body:
        body = "import os\n" + body
    return body, changed, left

def syntax_ok(path):
    if path.endswith(".sh"):
        return subprocess.run(["bash", "-n", path], capture_output=True).returncode == 0
    return subprocess.run([sys.executable, "-m", "py_compile", path], capture_output=True).returncode == 0

def main():
    os.makedirs(OUT, exist_ok=True)
    files = sorted(f for f in os.listdir(HOOKS)
                   if (f.endswith(".sh") or f.endswith(".py")) and ".bak" not in f)
    report = []
    for f in files:
        src = os.path.join(HOOKS, f)
        text = open(src, encoding="utf-8", errors="replace").read()
        if ABS not in text:
            continue
        if f.endswith(".sh"):
            body, ch, left = transform_bash(text)
        else:
            body, ch, left = transform_python(text, f)
        if ch == 0:
            report.append((f, "no-op(all-cosmetic)", left, "-")); continue
        dst = os.path.join(OUT, f)
        open(dst, "w", encoding="utf-8").write(body)
        os.chmod(dst, os.stat(src).st_mode)
        ok = "SYNTAX_OK" if syntax_ok(dst) else "SYNTAX_FAIL"
        report.append((f, f"{ch} rewritten", left, ok))
    print(f"portabilized copies -> {OUT}\n")
    print(f"{'hook':38} {'rewrites':22} {'cosmetic-left':13} check")
    for f, ch, left, ok in report:
        print(f"{f:38} {ch:22} {left:<13} {ok}")
    fails = [f for f, _, _, ok in report if ok == "SYNTAX_FAIL"]
    print(f"\n{len(report)} files transformed; syntax failures: {fails or 'none'}")

if __name__ == "__main__":
    main()
