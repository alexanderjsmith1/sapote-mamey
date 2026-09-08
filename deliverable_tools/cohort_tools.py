#!/usr/bin/env python3
"""cohort_tools — one front door for the Sapote-Mamey Multi-Cohort Comparison Toolkit.

A portable, stdlib-only launcher that (1) CATALOGS every tool in this folder by
category with a one-line description read from its docstring, (2) DISPATCHES to a
tool (`as_tools <tool> [args...]` runs it standalone), and (3) DOCTORS the shared
toolchain (`as_tools doctor`) — a small "registry of registries" that says where
python/pandoc/phylo/blast/bigscape actually live, because the #1 failure here is a
tool that exists but isn't on PATH (e.g. pandoc is at Tools/bin/pandoc, not bare).

Usage:
  python cohort_tools.py                 # list the tool catalog (default)
  python cohort_tools.py list            # same
  python cohort_tools.py doctor          # probe the shared toolchain + report paths
  python cohort_tools.py index           # (re)write TOOLS_INDEX.md
  python cohort_tools.py <tool> [args…]  # run a tool by name (with -h for its help)

Claim safety: these tools re-project already-produced Sapote-Mamey artifacts into
reader-side deliverables. Class-level capacity/context only; nothing here scores,
re-runs extraction, or upgrades a similarity signal to a claim. Judgment deferred.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import sys, os, re, subprocess, shutil, glob

HERE = os.path.dirname(os.path.abspath(__file__))
SELF = os.path.basename(__file__)

# name-keyword -> category, so the catalog reads by theme without moving files.
_CATEGORY_RULES = [
    (re.compile(r"roster|build_v[123]|strain_dossier|cohort_index"), "Rosters & dossiers"),
    (re.compile(r"blastp|ingest|enrich_|extract_|backfill|comprehensive"), "BLASTp / channel ingest"),
    (re.compile(r"novelty|as_sid|fair_"), "Cohort analysis (AS vs SID, novelty)"),
    (re.compile(r"tree|mlsa|phylo|genome_set"), "Phylogenomics & genome set"),
    (re.compile(r"widget"), "Interactive widgets"),
]

# The "registry of registries": capability -> (bare cmd, known project path, purpose).
# Paths are project-relative to the workspace root two levels up from a sealed bundle,
# but we also honor $SAPOTE_ROOT and a plain PATH probe so it stays portable.
_ROOT = os.environ.get("SAPOTE_ROOT", os.path.expanduser("~/sapote_workspace"))
_CAPABILITIES = [
    ("science python (matplotlib/pandas)", "python3", f"{_ROOT}/Tools/bin/python3", "figures, dataframes, these tools"),
    ("pandoc (md -> docx/pdf/html)",       "pandoc",  f"{_ROOT}/Tools/bin/pandoc",  "convert deliverable markdown to Word/PDF"),
    ("GToTree (organismal trees)",         "GToTree", f"{_ROOT}/tools/gtotree_env.sh", "source this env script first; then GToTree/iqtree3/fastANI"),
    ("IQ-TREE",                            "iqtree3", f"{_ROOT}/tools/gtotree_env.sh", "ML tree inference (via the phylo env)"),
    ("fastANI",                            "fastANI", f"{_ROOT}/tools/gtotree_env.sh", "nucleotide ANI (via the phylo env)"),
    ("BLASTp",                             "blastp",  f"{_ROOT}/Tools/blast",         "local/remote protein BLAST"),
    ("BiG-SCAPE",                          "bigscape",f"{_ROOT}/Tools/bigscape",      "GCF clustering (companion env)"),
]


def _tools() -> list[tuple[str, str]]:
    out = []
    for p in sorted(glob.glob(os.path.join(HERE, "*.py"))):
        name = os.path.basename(p)[:-3]
        if name == SELF[:-3]:
            continue
        out.append((name, _describe(p)))
    for p in sorted(glob.glob(os.path.join(HERE, "*.sh"))):
        out.append((os.path.basename(p), _describe(p)))
    return out


def _describe(path: str) -> str:
    """First meaningful line of the module docstring / leading comment."""
    try:
        txt = open(path, encoding="utf-8", errors="ignore").read()
    except OSError:
        return ""
    m = re.search(r'^\s*(?:#!.*\n)?\s*(?:"""|\'\'\')(.*?)(?:"""|\'\'\')', txt, re.S)
    if m:
        body = m.group(1).strip()
    else:  # shell / no docstring -> first non-shebang comment line
        body = ""
        for line in txt.splitlines():
            s = line.strip()
            if s.startswith("#!") or not s:
                continue
            if s.startswith("#"):
                body = s.lstrip("# ").strip(); break
            break
    # first line that reads like prose (skip imports / decorators / code / punctuation)
    first = ""
    for ln in body.splitlines():
        s = ln.strip()
        if not s or s.startswith(("from ", "import ", "@", ">", "(", "#!", "\"", "'", "-", "```")):
            continue
        if re.match(r'^[\w.\[\]]+\s*=', s) or s.endswith(":") or "->" in s[:40]:
            continue  # skip assignment / signature / code-ish lines
        first = s
        break
    # trim "name — " / "name: " prefixes for a clean column
    first = re.sub(r'^[\w./-]+\s*[—:-]\s*', '', first)
    return first[:96] or "(no docstring — run with -h)"


def _category(name: str) -> str:
    for rx, cat in _CATEGORY_RULES:
        if rx.search(name):
            return cat
    return "Other"


def cmd_list(write_index: bool = False) -> int:
    tools = _tools()
    by_cat: dict[str, list[tuple[str, str]]] = {}
    for name, desc in tools:
        by_cat.setdefault(_category(name), []).append((name, desc))
    lines = ["Sapote-Mamey Multi-Cohort Comparison Toolkit — %d tools\n" % len(tools),
             "Run:  python cohort_tools.py <tool> [args]   (add -h for a tool's own help)\n"]
    for cat in sorted(by_cat):
        lines.append(f"\n== {cat} ==")
        for name, desc in sorted(by_cat[cat]):
            lines.append(f"  {name:34}  {desc}")
    text = "\n".join(lines)
    emit(text)
    if write_index:
        idx = os.path.join(HERE, "TOOLS_INDEX.md")
        with open(idx, "w", encoding="utf-8") as fh:
            fh.write("# TOOLS_INDEX — Sapote-Mamey Multi-Cohort Comparison Toolkit\n\n")
            fh.write("Auto-generated by `cohort_tools.py index`. %d tools.\n" % len(tools))
            for cat in sorted(by_cat):
                fh.write(f"\n## {cat}\n\n| tool | what it does |\n|---|---|\n")
                for name, desc in sorted(by_cat[cat]):
                    fh.write(f"| `{name}` | {desc} |\n")
        emit(f"\nwrote {idx}")
    return 0


def cmd_doctor() -> int:
    emit("as_tools doctor — shared toolchain (registry of registries)\n", f"  {'capability':38} {'status':10} where", sep="\n")
    for label, cmd, path, purpose in _CAPABILITIES:
        on_path = shutil.which(cmd)
        proj = os.path.exists(path)
        # The python3 trap: a bare `python3` on PATH is usually the Framework build
        # WITHOUT matplotlib/pandas — the science python is specifically the project one.
        prefer_project = cmd == "python3" and proj and on_path and os.path.realpath(on_path) != os.path.realpath(path)
        if prefer_project:
            status, where = "PROJECT*", path
        else:
            status = "PATH" if on_path else ("PROJECT" if proj else "MISSING")
            where = on_path or (path if proj else "(install / see Tools/CHAT_TOOLING.md)")
        emit(f"  {label:38} {status:10} {where}", f"  {'':38} {'':10} · {purpose}", sep="\n")
        if prefer_project:
            emit(f"  {'':38} {'':10} ! bare `python3` on PATH is {on_path} (Framework, no matplotlib) — use the project one")
    emit("\nNote: 'PROJECT' means it is NOT on your bare PATH but IS in the project toolchain —", "call it by the shown path, or source it (e.g. `source tools/gtotree_env.sh`).", sep="\n")
    return 0


def cmd_run(tool: str, args: list[str]) -> int:
    cand = os.path.join(HERE, tool if tool.endswith((".py", ".sh")) else tool + ".py")
    if not os.path.exists(cand):
        sh = os.path.join(HERE, tool if tool.endswith(".sh") else tool + ".sh")
        cand = sh if os.path.exists(sh) else cand
    if not os.path.exists(cand):
        emit(f"as_tools: no tool named '{tool}'. Run `python cohort_tools.py list`.", file=sys.stderr)
        return 2
    runner = [sys.executable, cand] if cand.endswith(".py") else ["bash", cand]
    return subprocess.call(runner + args)


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("list", "-l", "--list"):
        return cmd_list()
    if argv[0] in ("index",):
        return cmd_list(write_index=True)
    if argv[0] in ("doctor", "--doctor", "capabilities"):
        return cmd_doctor()
    if argv[0] in ("-h", "--help", "help"):
        emit(__doc__); return 0
    return cmd_run(argv[0], argv[1:])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
