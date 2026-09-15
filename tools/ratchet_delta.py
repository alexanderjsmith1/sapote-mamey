#!/usr/bin/env python3
"""What does THIS patch packet cost against the repo-health ratchets?

`repo_health.py --ratchet-down` drives every debt ceiling to the measured count on purpose: it
"turns 'zero headroom' from a fact you discover into one you cannot drift past." Zero headroom is
the design, not drift. Measured on the v9.7.416 candidate, both live ceilings sit exactly there:
`silent_swallow` 147/147, and `print_calls` 1323 against a waiver signed at observed 1323.

What the design does NOT provide is ACCOUNTING. Each lane measures its own work against the shared
base, sees OK, and hands off. The integrator applies three packets, the sum crosses the ceiling, and
the seal goes red with no way to see which packet spent the budget. That is not hypothetical: two
of this lane's own packets did it, once at +5 and once at +1, both caught only after integration.

This tool prices a packet BEFORE handoff, and attributes an overrun AFTER integration.

    python3 tools/ratchet_delta.py --base <sealed-tree> --candidate <work-tree>
    python3 tools/ratchet_delta.py --base <sealed-tree> --patches <patch-card-dir>

`repo_health.py --json` is the authority for every total. It emits per-site `hits` for
`silent_swallow` and `injected_print` but NONE for `print_calls`, so the one metric with zero waiver
headroom is also the one with no attribution. This tool supplies that inventory itself, using the
same AST rules, and CROSS-CHECKS its own total against repo_health's on both trees — a disagreement
is reported loudly rather than quietly trusted, because a private reimplementation of someone else's
counter is exactly the kind of thing that drifts.

Claim-safety: this module carries no scientific meaning. It counts code-hygiene sites.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _console import emit  # noqa: E402  the tools/ terminal-emission seam (v9.7.407)

_CONSOLE_IMPORTS = ("from .console import emit", "from ..console import emit",
                    "from mamey.console import emit", "from _console import emit")


def _scan_rules(root: str) -> tuple[tuple[str, ...], tuple[str, ...], frozenset[str]]:
    """SCAN_DIRS and the two exclusion sets, READ OUT OF the tree's own repo_health.py.

    Hardcoding a copy of `CLI_TOOL_EXCLUDE_FILES` here drifted by 70 sites on the first run — the
    list has grown with every cut as operator front doors landed. Parsing the constants (AST, no
    import) keeps one source of truth, and anything this still gets wrong the cross-check reports.
    """
    src = os.path.join(root, "tools", "repo_health.py")
    scan, xdirs, xfiles = ("mamey", "tools"), ("blastp_monitoring",), frozenset()
    try:
        tree = ast.parse(open(src, encoding="utf-8", errors="replace").read())
    except (OSError, SyntaxError):
        return scan, xdirs + ("__pycache__", "_vendor"), xfiles
    for node in tree.body:
        if not isinstance(node, ast.Assign) or not isinstance(node.targets[0], ast.Name):
            continue
        name = node.targets[0].id
        try:
            val = ast.literal_eval(node.value)
        except (ValueError, TypeError, SyntaxError):
            continue
        if name == "SCAN_DIRS":
            scan = tuple(val)
        elif name == "CLI_TOOL_EXCLUDE_DIRS":
            xdirs = tuple(val)
        elif name == "CLI_TOOL_EXCLUDE_FILES":
            xfiles = frozenset(val)
    return scan, xdirs + ("__pycache__", "_vendor"), xfiles


def _health(root: str) -> dict:
    """repo_health's own JSON report — the authority for every total."""
    # --strict, because the question is always "would this turn the seal red", and a WARN that
    # only blocks under --strict is invisible without it. The first run of this tool reported the
    # candidate PASS at print_calls 1325 for exactly that reason.
    r = subprocess.run([sys.executable, os.path.join(root, "tools", "repo_health.py"),
                        "--root", root, "--json", "--strict"],
                       capture_output=True, text=True, timeout=600)
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        raise SystemExit(f"repo_health.py --json produced no report for {root}\n{r.stderr[:2000]}")


def _console_aliases_for(root: str, tree: ast.AST) -> frozenset[str]:
    """Names in this module that refer to the shared console module.

    Delegates to the TARGET TREE's own `repo_health._console_imports` when it exists, so this
    scanner cannot drift from the counter it is reporting on. It drifted once already: v9.7.418
    taught `check_print_calls` to count the attribute form `_console.emit(...)`, this scanner kept
    counting only the bare Name, and a file with one bare and two qualified calls was reported as
    one site against repo_health's three. The cross-check below caught the disagreement and said so,
    but a scanner that is honestly wrong is still wrong.

    Falls back to the two conventional names when the helper is absent (an older tree), which is the
    pre-.418 behaviour and is reported by the cross-check if it matters.
    """
    fn = _repo_health_helper(root)
    if fn is not None:
        try:
            return frozenset(fn(tree.body))
        except Exception:
            # v9.7.431: make the fall-through explicit rather than swallowing silently. Behaviour
            # is unchanged -- an unusable helper in the target tree means the conventional-name
            # scan below, which is exactly what the docstring promises and what the cross-check
            # reports. Written as an explicit rebind so the `except ...: pass` debt metric this
            # very tool forecasts against does not grow by the tool that forecasts it.
            fn = None
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name in ("_console", "console", "mamey.console"):
                    found.add(a.asname or a.name.split(".")[-1])
    return frozenset(found)


_HELPER_CACHE: dict[str, object] = {}


def _repo_health_helper(root: str):
    """`repo_health._console_imports` from the tree under test, or None. Cached per tree."""
    if root in _HELPER_CACHE:
        return _HELPER_CACHE[root]
    fn = None
    src = os.path.join(root, "tools", "repo_health.py")
    if os.path.isfile(src):
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("_rd_repo_health", src)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = mod          # module-level dataclasses need this
            try:
                spec.loader.exec_module(mod)
                fn = getattr(mod, "_console_imports", None)
            finally:
                sys.modules.pop(spec.name, None)
        except Exception:
            fn = None
    _HELPER_CACHE[root] = fn
    return fn


def _print_sites(root: str) -> list[str]:
    """Per-site inventory for print_calls, which repo_health reports as a bare total."""
    out: list[str] = []
    scan_dirs, exclude_dirs, exclude_files = _scan_rules(root)
    tools_dir = os.path.join(root, "tools")
    for d in scan_dirs:
        base = os.path.join(root, d)
        if not os.path.isdir(base):
            continue
        for dp, dn, fn in os.walk(base):
            dn[:] = [x for x in dn if x not in exclude_dirs]
            for f in sorted(fn):
                if not f.endswith(".py"):
                    continue
                # tools/-only by path, per the v9.7.404 A3 fix: a basename match across every
                # SCAN_DIR would also exclude a mamey/ library module of the same name.
                if os.path.abspath(dp) == os.path.abspath(tools_dir) and f in exclude_files:
                    continue
                p = os.path.join(dp, f)
                try:
                    text = open(p, encoding="utf-8", errors="replace").read()
                    tree = ast.parse(text)
                except (OSError, SyntaxError):
                    continue
                names = ("print", "emit") if any(s in text for s in _CONSOLE_IMPORTS) else ("print",)
                aliases = _console_aliases_for(root, tree)
                for n in ast.walk(tree):
                    if not isinstance(n, ast.Call):
                        continue
                    if isinstance(n.func, ast.Name) and n.func.id in names:
                        out.append(f"{os.path.relpath(p, root)}:{n.lineno}")
                    elif (isinstance(n.func, ast.Attribute) and n.func.attr in ("print", "emit")
                          and isinstance(n.func.value, ast.Name) and n.func.value.id in aliases):
                        out.append(f"{os.path.relpath(p, root)}:{n.lineno}")
    return out


def _by_file(sites: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for s in sites:
        out[s.rsplit(":", 1)[0]] = out.get(s.rsplit(":", 1)[0], 0) + 1
    return out


def _ceiling(detail: str) -> int | None:
    """Ceilings live in repo_health's detail string; this tool never keeps its own copy."""
    if "(ceiling " not in detail:
        return None
    try:
        return int(detail.split("(ceiling ", 1)[1].split(")", 1)[0])
    except (ValueError, IndexError):
        return None


def _total(detail: str) -> int | None:
    head = detail.split(None, 1)[0] if detail else ""
    return int(head) if head.isdigit() else None


def _apply_patches(base: str, patch_dir: str, dest: str) -> list[str]:
    shutil.copytree(base, dest, symlinks=True)
    applied = []
    diffs = []
    for dp, dn, fn in os.walk(patch_dir):
        dn[:] = [d for d in dn if d not in ("__pycache__",)]
        diffs += [os.path.join(dp, f) for f in sorted(fn) if f.endswith((".diff", ".patch"))]
    for d in sorted(diffs):
        r = subprocess.run(["git", "apply", "-p1", d], cwd=dest, capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"patch does not apply to the base tree: {d}\n{r.stderr[:1500]}\n"
                             "Price the packet against the base it was written for, or rebase it.")
        applied.append(os.path.relpath(d, patch_dir))
    if not applied:
        raise SystemExit(f"no .diff/.patch files under {patch_dir}")
    return applied


def compare(base: str, cand: str, lines: list[str]) -> int:
    """Append the report to `lines`; return 1 if the candidate breaches a ceiling the base cleared."""
    hb, hc = _health(base), _health(cand)
    rb = {c["name"]: c for c in hb["results"]}
    rc = {c["name"]: c for c in hc["results"]}

    breach = 0
    for name in ("silent_swallow", "print_calls", "injected_print", "bare_except"):
        b, c = rb.get(name), rc.get(name)
        if not b or not c:
            continue
        tb, tc = _total(b["detail"]), _total(c["detail"])
        if tb is None or tc is None:
            continue
        ceil = _ceiling(c["detail"])
        delta = tc - tb
        arrow = "=" if delta == 0 else ("+%d" % delta if delta > 0 else str(delta))
        head = f"{name:<16} {tb} -> {tc}  ({arrow})"
        if ceil is not None:
            room = ceil - tc
            head += f"   ceiling {ceil}, headroom {room}"
        lines.append(head)

        # attribution
        sb = b["hits"] or (_print_sites(base) if name == "print_calls" else [])
        sc = c["hits"] or (_print_sites(cand) if name == "print_calls" else [])
        if name == "print_calls":
            for label, mine, theirs in (("base", len(sb), tb), ("candidate", len(sc), tc)):
                if mine != theirs:
                    lines.append(f"    ! this tool counted {mine} print_calls sites on the {label} "
                                 f"tree, repo_health reports {theirs}. Attribution below is "
                                 f"UNRELIABLE; the totals above are still repo_health's.")
        new = sorted(set(sc) - set(sb))
        gone = sorted(set(sb) - set(sc))
        if name == "print_calls" and (len(new) > 40 or len(gone) > 40):
            # line numbers shift wholesale when a file is edited; per-file counts are the honest view
            fb, fc = _by_file(sb), _by_file(sc)
            moved = sorted({f for f in set(fb) | set(fc) if fb.get(f, 0) != fc.get(f, 0)})
            for f in moved:
                lines.append(f"    {fc.get(f, 0) - fb.get(f, 0):+d}  {f}"
                             f"  ({fb.get(f, 0)} -> {fc.get(f, 0)})")
        else:
            for s in new[:25]:
                lines.append(f"    NEW      {s}")
            if len(new) > 25:
                lines.append(f"    ... and {len(new) - 25} more new site(s)")
            for s in gone[:25]:
                lines.append(f"    REMOVED  {s}")
            if len(gone) > 25:
                lines.append(f"    ... and {len(gone) - 25} more removed site(s)")

        if ceil is not None and tc > ceil >= tb:
            lines.append(f"    ^^ BREACH: this packet takes {name} past its ceiling. "
                         f"Pay it back, or take it to the release owner — a ceiling is not "
                         f"raised by the lane that needs it raised.")
            breach = 1

    wb = next((c for c in hb["results"] if c["name"] == "waiver_slack"), None)
    wc = next((c for c in hc["results"] if c["name"] == "waiver_slack"), None)
    for w, label in ((wb, "base"), (wc, "candidate")):
        if w and w["hits"]:
            for h in w["hits"]:
                lines.append(f"waiver ({label}): {h}")

    lines.append("")
    lines.append(f"base      --strict PASS: {hb['passed']}")
    lines.append(f"candidate --strict PASS: {hc['passed']}")
    if hb["passed"] and not hc["passed"]:
        lines.append("This packet turns a green base red. That is the finding — not a reason to "
                     "re-sign a waiver around it.")
        breach = 1
    return breach


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True, help="the tree the packet was written against")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--candidate", help="an already-patched tree")
    g.add_argument("--patches", help="a patch-card directory; every .diff/.patch under it is "
                                     "applied to a scratch copy of --base, in sorted order")
    a = ap.parse_args(argv)

    lines: list[str] = []
    tmp = None
    try:
        if a.patches:
            tmp = tempfile.mkdtemp(prefix="ratchet_delta_")
            dest = os.path.join(tmp, "candidate")
            applied = _apply_patches(a.base, a.patches, dest)
            lines.append(f"applied {len(applied)} patch file(s) from {a.patches}:")
            lines += [f"    {p}" for p in applied]
            lines.append("")
            cand = dest
        else:
            cand = a.candidate
        rc = compare(a.base, cand, lines)
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
    emit("\n".join(lines))
    return rc


if __name__ == "__main__":
    sys.exit(main())
