#!/usr/bin/env python3
"""sapote_hooks.py — organize, install, and verify the Sapote-Mamey guardrail hooks so the whole set
TRAVELS WITH THE BUNDLE and OPERATES in any workspace it lands in.

THE PROBLEM THIS SOLVES (2026-08-19, the Developer or User: "we are still struggling"):
  * The hooks in `.claude/hooks/` hardcode the authoring machine's absolute workspace root
    and `.claude/settings.json` wires every hook with an absolute path — so the guardrails do NOT travel
    to another root or machine.
  * The live hooks and the bundle's candidate copies DRIFT (a live fix is not mirrored to the bundle,
    and vice-versa) with nothing to detect it.
  * There is no single declarative REGISTRY of what hooks exist, on what event, deny vs warn, and why.

THE MODEL:
  * `HOOKS_MANIFEST.tsv` (beside this tool) is the single source of truth: one row per wired hook —
    event, matcher, runner (bash/python3/inline), hook file, type (deny|warn|context|log), scope,
    one-line purpose.
  * Wiring is PORTABLE: generated hook commands reference `$CLAUDE_PROJECT_DIR/.claude/hooks/<file>`
    (Claude Code exports CLAUDE_PROJECT_DIR to every hook), never an absolute machine path.
  * The bundle ships this folder (`sapote_hooks/` = tool + manifest + the hook files); landing in a
    workspace, `install --apply` copies the hooks into `.claude/hooks/` and writes portable wiring into
    `.claude/settings.json` (a timestamped backup is kept). `verify` detects drift + cruft + wiring gaps.

SUBCOMMANDS
  capture     read the live .claude/settings.json -> (re)build HOOKS_MANIFEST.tsv (type/purpose kept if
              a prior manifest exists; new rows get '?', to be annotated once).
  list        print the manifest grouped by event.
  verify      three checks: (1) every manifest hook file exists in .claude/hooks/; (2) every settings.json
              wired hook is in the manifest; (3) cruft (.bak*/__pycache__/_backup*) in .claude/hooks/;
              plus optional --bundle <dir> drift diff (live hook bytes vs bundle copy).
  install     write portable wiring to .claude/settings.json from the manifest (DRY-RUN unless --apply;
              --apply backs up settings.json first) and, with --bundle <dir>, copy bundle hook files into
              .claude/hooks/.

PORTABLE ROOT: $CLAUDE_PROJECT_DIR (falls back to $SAPOTE_ROOT, then a marker-walk to the dir holding
`.claude`). Nothing here needs an absolute path baked in.
"""
from __future__ import annotations
import argparse, json, os, re, sys, hashlib, shutil, time
from collections import OrderedDict

HERE = os.path.dirname(os.path.realpath(__file__))
MANIFEST = os.path.join(HERE, "HOOKS_MANIFEST.tsv")
ABS_ROOT_RE = re.compile(r'/Users/[^/]+/sapote_workspace')  # legacy hardcoded root to portabilize
PORTABLE_ROOT = "$CLAUDE_PROJECT_DIR"
HOOK_PATH_RE = re.compile(r'\.claude/hooks/([A-Za-z0-9_.\-]+)')
CRUFT_RE = re.compile(r'(\.bak|\.bak_|~$|__pycache__|_backup|\.orig|\.pyc$)')

def project_root():
    for env in ("CLAUDE_PROJECT_DIR", "SAPOTE_ROOT"):
        v = os.environ.get(env)
        if v and os.path.isdir(os.path.join(v, ".claude")):
            return os.path.realpath(v)
    d = HERE
    while True:
        if os.path.isdir(os.path.join(d, ".claude")):
            return d
        p = os.path.dirname(d)
        if p == d:
            sys.exit("could not locate project root (a dir containing .claude). Set CLAUDE_PROJECT_DIR.")
        d = p

def portabilize_cmd(cmd):
    """Rewrite a hook command's legacy absolute root to $CLAUDE_PROJECT_DIR, QUOTE-AWARE. A single-quoted
    path must become DOUBLE-quoted or the env var will not expand (single quotes suppress $-expansion)."""
    # 1) single-quoted path containing the legacy root -> double-quoted with the env var
    cmd = re.sub(r"'(" + ABS_ROOT_RE.pattern + r")([^']*)'", r'"' + PORTABLE_ROOT + r'\2"', cmd)
    # 2) any remaining (double-quoted / unquoted) legacy root -> env var (already expands)
    cmd = ABS_ROOT_RE.sub(PORTABLE_ROOT, cmd)
    return cmd

def settings_path(root): return os.path.join(root, ".claude", "settings.json")
def hooks_dir(root):     return os.path.join(root, ".claude", "hooks")

def _runner_and_file(cmd):
    """Classify a hook command -> (runner, hook_file_or_INLINE)."""
    m = HOOK_PATH_RE.search(cmd)
    if not m:
        return ("inline", "INLINE")
    f = m.group(1)
    runner = "python3" if cmd.strip().startswith("python3") or ".py" in f else "bash"
    return (runner, f)

# ---------------------------------------------------------------- capture
def load_manifest():
    rows = []
    if os.path.exists(MANIFEST):
        with open(MANIFEST) as fh:
            hdr = fh.readline().rstrip("\n").split("\t")
            for line in fh:
                if not line.strip() or line.startswith("#"): continue
                rows.append(dict(zip(hdr, line.rstrip("\n").split("\t"))))
    return rows

COLS = ["event", "matcher", "runner", "hook", "type", "scope", "purpose"]

def cmd_capture(a):
    root = project_root()
    s = json.load(open(settings_path(root)))
    prior = {(r["event"], r["matcher"], r["hook"]): r for r in load_manifest()}
    out = []
    for event, groups in s.get("hooks", {}).items():
        for g in groups:
            matcher = g.get("matcher", "*") or "*"
            for hk in g.get("hooks", []):
                cmd = hk.get("command", "")
                runner, f = _runner_and_file(cmd)
                key = (event, matcher, f)
                p = prior.get(key, {})
                out.append({"event": event, "matcher": matcher, "runner": runner, "hook": f,
                            "type": p.get("type", "?"), "scope": p.get("scope", "bundle"),
                            "purpose": p.get("purpose", "?")})
    with open(MANIFEST, "w") as fh:
        fh.write("\t".join(COLS) + "\n")
        for r in out:
            fh.write("\t".join(str(r[c]) for c in COLS) + "\n")
    print(f"captured {len(out)} wired hooks -> {os.path.relpath(MANIFEST, root)}")
    unann = sum(1 for r in out if r["type"] == "?" or r["purpose"] == "?")
    if unann: print(f"  {unann} rows need type/purpose annotation (edit the TSV once).")

# ---------------------------------------------------------------- list
def cmd_list(a):
    rows = load_manifest()
    by_ev = OrderedDict()
    for r in rows: by_ev.setdefault(r["event"], []).append(r)
    for ev, rs in by_ev.items():
        print(f"\n{ev}:")
        for r in rs:
            print(f"  [{r['matcher']:<28}] {r['type']:<7} {r['hook']:<34} {r['purpose']}")

# ---------------------------------------------------------------- verify
def _verify_tree(tree, gate_mode):
    """Self-contained integrity check of a STANDALONE bundle tree (no .claude needed): every manifest hook
    present in <tree>/hooks/, no non-portable hook (hardcodes the workspace root with ZERO env-var
    fallback), no cruft. This is the correct SEAL-TIME check — it validates the artifact being shipped,
    not the live workspace (so it does not false-alarm on live-vs-bundle differences)."""
    tree = os.path.realpath(tree)
    man = os.path.join(tree, "sapote_hooks", "HOOKS_MANIFEST.tsv")
    hd = os.path.join(tree, "hooks")
    if not os.path.isdir(hd) or not os.path.exists(man):
        print(f"  TREE-INVALID: expected {man} and {hd}/ to exist"); sys.exit(1)
    rows = []
    with open(man) as fh:
        hdr = fh.readline().rstrip("\n").split("\t")
        for line in fh:
            if line.strip() and not line.startswith("#"):
                rows.append(dict(zip(hdr, line.rstrip("\n").split("\t"))))
    gate = 0; advisory = 0
    for r in rows:
        if r.get("hook") in ("INLINE", None): continue
        if r.get("scope") == "workspace": continue          # workspace-only hooks are not bundle-shipped
        if not os.path.exists(os.path.join(hd, r["hook"])):
            print(f"  MISSING: bundle-scoped manifest hook not in tree hooks/: {r['hook']}"); gate += 1
    for name in sorted(os.listdir(hd)):
        if CRUFT_RE.search(name):
            print(f"  CRUFT: hooks/{name}"); advisory += 1; continue
        if not (name.endswith(".sh") or name.endswith(".py")): continue
        text = open(os.path.join(hd, name), encoding="utf-8", errors="replace").read()
        if ABS_ROOT_RE.search(text):
            has_env = ("CLAUDE_PROJECT_DIR" in text) or ("SAPOTE_WORKSPACE_ROOT" in text)
            bare = any(ABS_ROOT_RE.search(ln) and not ln.lstrip().startswith("#")
                       for ln in text.splitlines())
            if bare and not has_env:
                print(f"  NON-PORTABLE: hooks/{name} hardcodes the workspace root with no env-var fallback")
                gate += 1
    total = gate + advisory
    print(f"\nverify --tree: {gate} gate + {advisory} advisory = {total} problem(s)"
          + (" (gate mode: cruft advisory)" if gate_mode else "") + ("" if total else "  CLEAN."))
    sys.exit(1 if (gate if gate_mode else total) else 0)

def cmd_verify(a):
    if getattr(a, "tree", ""):
        return _verify_tree(a.tree, a.gate)
    # GATE problems = bundle-integrity (missing/unmanifested/non-portable/broken/drift): fail a seal.
    # ADVISORY = workspace cruft (.bak/__pycache__/_backup): printed but never fails --gate (never bundled).
    root = project_root(); hd = hooks_dir(root)
    rows = load_manifest()
    gate = 0; advisory = 0
    # (1) manifest hook files present
    for r in rows:
        if r["hook"] == "INLINE": continue
        if not os.path.exists(os.path.join(hd, r["hook"])):
            print(f"  MISSING: manifest hook not in .claude/hooks/: {r['hook']}"); gate += 1
    # (2) wired-but-unmanifested
    s = json.load(open(settings_path(root)))
    wired = set()
    for event, groups in s.get("hooks", {}).items():
        for g in groups:
            for hk in g.get("hooks", []):
                _, f = _runner_and_file(hk.get("command", ""))
                wired.add((event, f))
    man = {(r["event"], r["hook"]) for r in rows}
    for ev, f in sorted(wired - man):
        if f == "INLINE": continue
        print(f"  UNMANIFESTED: settings.json wires {f} on {ev} but it's not in the manifest"); gate += 1
    # (3) cruft (advisory)
    for name in sorted(os.listdir(hd)):
        if CRUFT_RE.search(name):
            print(f"  CRUFT: .claude/hooks/{name} (strip before bundling)"); advisory += 1
    # (3b) absolute-root wiring (portability)
    raw = open(settings_path(root)).read()
    n_abs = len(ABS_ROOT_RE.findall(raw))
    if n_abs:
        print(f"  NON-PORTABLE: settings.json has {n_abs} absolute-root hook paths "
              f"(run `install --apply` to rewrite as {PORTABLE_ROOT}).")
        gate += 1
    n_broken = raw.count("'" + PORTABLE_ROOT)  # single-quoted env var will NOT expand
    if n_broken:
        print(f"  BROKEN-PORTABLE: {n_broken} single-quoted {PORTABLE_ROOT} path(s) — single quotes "
              "suppress expansion; must be double-quoted. Re-run `install --apply`.")
        gate += 1
    # (4) drift vs bundle
    if a.bundle:
        bdir = a.bundle if os.path.isabs(a.bundle) else os.path.join(root, a.bundle)
        for r in rows:
            if r["hook"] == "INLINE": continue
            live = os.path.join(hd, r["hook"]); bun = os.path.join(bdir, r["hook"])
            if os.path.exists(live) and os.path.exists(bun):
                if _sha(live) != _sha(bun):
                    print(f"  DRIFT: {r['hook']} differs between live and bundle ({a.bundle})"); gate += 1
            elif os.path.exists(live) and not os.path.exists(bun):
                print(f"  DRIFT: {r['hook']} present live but MISSING in bundle ({a.bundle})"); gate += 1
    total = gate + advisory
    tag = " (gate mode: cruft is advisory)" if a.gate else ""
    print(f"\nverify: {gate} gate + {advisory} advisory = {total} problem(s){tag}." +
          ("" if total else "  CLEAN."))
    fail = gate if a.gate else total
    sys.exit(1 if fail else 0)

def _sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()

# ---------------------------------------------------------------- install (portabilize wiring)
def cmd_install(a):
    root = project_root(); sp = settings_path(root)
    s = json.load(open(sp))
    changed = 0
    for event, groups in s.get("hooks", {}).items():
        for g in groups:
            for hk in g.get("hooks", []):
                new = portabilize_cmd(hk.get("command", ""))
                if new != hk["command"]:
                    hk["command"] = new; changed += 1
    # optional: copy bundle hook files into .claude/hooks/
    copied = 0
    if a.bundle:
        bdir = a.bundle if os.path.isabs(a.bundle) else os.path.join(root, a.bundle)
        hd = hooks_dir(root); os.makedirs(hd, exist_ok=True)
        for r in load_manifest():
            if r["hook"] == "INLINE": continue
            src = os.path.join(bdir, r["hook"])
            if os.path.exists(src):
                if a.apply: shutil.copy2(src, os.path.join(hd, r["hook"]))
                copied += 1
    if not a.apply:
        print(f"DRY-RUN: would portabilize {changed} absolute hook path(s) -> {PORTABLE_ROOT}"
              + (f", copy {copied} bundle hook file(s) into .claude/hooks/" if a.bundle else "")
              + ".\n  Re-run with --apply to write (settings.json backed up first).")
        return
    bak = sp + ".bak_" + time.strftime("%Y%m%d_%H%M%S")
    shutil.copy2(sp, bak)
    json.dump(s, open(sp, "w"), indent=2)
    print(f"APPLIED: {changed} paths portabilized"
          + (f", {copied} hook files copied from bundle" if a.bundle else "")
          + f". Backup: {os.path.relpath(bak, root)}")

def main(argv=None):
    ap = argparse.ArgumentParser(description="Organize/install/verify Sapote-Mamey guardrail hooks.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("capture").set_defaults(fn=cmd_capture)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    v = sub.add_parser("verify"); v.add_argument("--bundle", default="")
    v.add_argument("--gate", action="store_true", help="fail only on bundle-integrity problems (cruft advisory)")
    v.add_argument("--tree", default="", help="check a STANDALONE bundle tree (self-contained; no .claude needed)")
    v.set_defaults(fn=cmd_verify)
    i = sub.add_parser("install"); i.add_argument("--apply", action="store_true")
    i.add_argument("--bundle", default=""); i.set_defaults(fn=cmd_install)
    a = ap.parse_args(argv); a.fn(a)

if __name__ == "__main__":
    main()
