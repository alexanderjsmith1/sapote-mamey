#!/usr/bin/env python3
"""repo_health.py — one-command repo-health gate for the Sapote-Mamey bundle.

Stdlib-only (ast, pathlib, re, argparse, json, sys) so it runs on a core-only or air-gapped
install without the science stack. Run from the bundle root:

    python tools/repo_health.py            # human summary; exit 1 if any hard check FAILs
    python tools/repo_health.py --strict   # promote WARNs to FAILs
    python tools/repo_health.py --json      # machine-readable report to stdout

Checks (hard = can FAIL and set exit 1; soft = WARN only unless --strict):
  [hard] syntax          — every .py under mamey/ and tools/ parses
  [hard] collisions      — delegates to the wired gate tools/check_duplicate_dict_keys.py
                           (duplicate dict-key detection across mamey/tools/tests, with its ratchet).
                           repo_health does NOT reimplement this — it runs the real gate.
  [hard] placeholder_keys— no dict literal key in mamey/tools is a scrub placeholder (contains 'XXX');
                           catches LONE placeholder keys (dead lookups) the collision gate won't flag
  [hard] manifest_drift  — every path MODULE_MANIFEST.txt lists still exists on disk
  [soft] silent_swallow  — count of `except ...: pass` in mamey/ and tools/ (silently swallowed errors)
  [soft] bare_except     — count of bare `except:` in mamey/ and tools/
  [soft] print_calls     — count of print( in mamey/ and tools/ (should migrate to logging)
  [info] docstring_cov   — function docstring coverage in mamey/ (reported, never gates)
  [info] onboarding_docs — count of root READ_ME/START_HERE files (sprawl signal)

This is the reproducible form of the v9.7.30x "50 best / 50 worst" audit's mechanical findings.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ---- config -----------------------------------------------------------------
SCAN_DIRS = ("mamey", "tools")
PRINT_WARN_THRESHOLD = 1280  # v9.7.410 cut, 2026-09-06: 1277 -> 1280 (measured) -- UP, flagged for the owner: +1 tools/gen_figure_r_manifest.py, +1 tools/check_patch_lane.py (two new tool entry points, one emit each), +1 mamey/cli.py ingest-blastp fail-loud WARNING (deliberate, replaces a silent 0-BGC bind); no consecutive single-arg emit pairs remain to merge (measured by AST)  # ratchet-down 2026-09-06: 1278 -> 1277 (measured)  # ratchet-down 2026-09-05: 1289 -> 1278 (measured)  # v9.7.408 close-out, second paydown: 101 more consecutive single-arg emits merged (sep="\n", byte-identical); the 5 new emissions from `start`/`phylo-autopilot` are absorbed. Ceilings only go down.
                             # emissions merged byte-identically with sep="\n"; merge requires the
                             # statement to stand ALONE on its line -- a single-line compound statement
                             # shares the indent of a bare one and is NOT in the same block)  # ratchet-down 2026-09-02: 1623 -> 1622 (measured)  # ratchet-down 2026-09-02: 1624 -> 1623 (measured)   # RATCHETED DOWN 2026-09-02 (v9.7.405) from 1629: the .405 composition
                              # added 26 prints (22 in four tools/ front doors now EXCLUDED BY
                              # DESIGN below; 10 real ones in mamey/ CLI mains), paid for by
                              # deleting the 15-print duplicate __main__ self-test in
                              # mamey/architecture_first.py. 1624 is the measured truth after that.
                              # Prior: 1629 (.404) — RATCHETED DOWN 2026-09-02 (v9.7.404) from 1635 — and this is a
                              # ratchet DOWN, not another rebaseline. The 1635 figure was never
                              # the number of print calls: the metric was a TEXT regex, so six
                              # mentions of the call token in comments and docstrings were being
                              # counted as debt. check_print_calls now counts real calls from the
                              # AST, and 1629 is the measured truth. Prior ceilings 1632 (.381)
                              # and 1635 (.392b) were debt REBASELINED; this one is debt
                              # RE-MEASURED. Ratchet down, never raise.
                              #
                              # Where the remaining debt lives (measured at .404, AST, excluding
                              # tools/ operator front doors): 721 in mamey/ across 89 files, of
                              # which mamey/cli.py 235, package_inspector.py 72,
                              # mode_b_receipt.py 61, compile_report.py 27, blastp_online.py 25.
                              # Converting those is a separate, individually verifiable task — a
                              # mass edit inside a cut candidate is exactly the kind of change
                              # that looks like a fix and is not.
BARE_EXCEPT_WARN_THRESHOLD = 0
# baseline 110 at v9.7.307; ceiling stops growth, not approval. The .323..332 drift to 115 was
# SWEPT back to 110 (v9.7.333 hygiene, closing .332 intake-receipt F1): 4 loop parse-guards
# `except (ValueError|Exception): pass` -> `continue` (collection_figures.py x3, cohort_figures.py x1,
# all behavior-identical) + 1 reviewed-intentional handler marked `...` (master_workbook.py NP-Atlas
# optional). Hold the line at 110 — do not raise without a sweep.
SILENT_SWALLOW_CEILING = 82  # combined ratchet-down 2026-09-09: 145 -> 125 (measured)  # ratchet-down 2026-09-09: 147 -> 145 (measured)  # ratchet-down 2026-09-07: 148 -> 147 (measured)  # ratchet-down 2026-09-05: 149 -> 148 (measured)  # ratchet-down 2026-09-05: 151 -> 149 (measured)  # ratchet-down 2026-09-04: 152 -> 151 (measured)  # ratchet-down 2026-09-03: 153 -> 152 (measured)  # ratchet-down 2026-09-02: 154 -> 153 (measured)   # REBASELINED 2026-08-26 (v9.7.381) to the measured count — DEBT
                          # REBASELINED, NOT REDUCED. No-regression ceiling; ratchet down, never raise.
PLACEHOLDER_RE = re.compile(r"XXX")


@dataclass
class Result:
    name: str
    status: str            # "OK" | "WARN" | "FAIL" | "INFO"
    detail: str = ""
    hits: list = field(default_factory=list)


def _repo_root(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    here = Path(__file__).resolve()
    # tools/repo_health.py -> repo root is the parent of tools/
    return here.parent.parent


# Operator CLI tools whose stdout IS the deliverable (dashboards, plot generators, run launchers), not the
# library debt the print_calls metric targets ("migrate to logging"). Excluded from the .py hygiene scan
# BY DESIGN — a status dashboard is supposed to print. Explicit + named so nothing else can hide here.
# (v9.7.382: the blastp-monitoring fleet + phylo preflight/postflight/render launchers were folded in.)
CLI_TOOL_EXCLUDE_DIRS = ("blastp_monitoring",)
CLI_TOOL_EXCLUDE_FILES = {"render_all.py", "phylo_preflight.py", "phylo_postflight.py",
                          "phylo_place.py",
                          "relabel_and_render.py", "render_clean_tree.py",
                          "validate_portfolio_registry.py",
                          "blastp_channel_triage.py",
                          # v9.7.407: six operator front doors landed with the .407 composition
                          # (CODEX-407 contract-map/determinism/registry/gate-probe lanes + AMBER-407).
                          # Each one's stdout IS its receipt — a JSON/TSV register, a census row, or a
                          # typed PASS/FAIL line — so they are EXCLUDED BY DESIGN, not library debt.
                          # tools/-only by path (the .404 A3 basename-collision fix still applies).
                          # v9.7.408: tier_vocabulary is a library with a small inspection CLI;
                          # all 9 of its emit calls live in _main() and print the tier table,
                          # which IS that command's deliverable.
                          "tier_vocabulary.py",
                          # v9.7.408: phylo_autopilot is an operator front door (AMBER-408): its stdout
                          # is the routing tally and reference-genera list a user reads BEFORE spending
                          # compute — the deliverable itself. tools/-only by path.
                          "phylo_autopilot.py",
                          "check_manifest_contract.py", "determinism_fingerprint.py",
                          "gate_mutation_probe.py", "parked_card_audit.py",
                          "scan_marker_census.py", "scan_registry_parity.py",
                          # v9.7.405: four Codex operator front doors landed with the .405 composition.
                          # Each one's stdout IS its receipt (JSON/TSV register or a typed refusal
                          # line) — the blastp_channel_triage family — so they are EXCLUDED BY DESIGN,
                          # not counted as library debt. Every one lives in tools/ only (basename
                          # collision with a mamey/ module checked at registration: none).
                          "generated_surface_ownership.py",
                          "reference_bgc_structural_validator.py",
                          "compile_figure_owner_review.py",
                          "build_owner_kept_figure_inputs.py",
                          # v9.7.405: lead-propagation front door (stdout = receipt JSON).
                          "lead_propagation_gate.py",
                          # v9.7.405: alias-history front door (stdout = history JSON receipt).
                          "bgc_alias_history.py"}
# v9.7.403: tools/blastp_channel_triage.py is an operator front door whose stdout IS the
# deliverable (the triage receipt JSON on stdout, the error line on stderr) — the same family as
# the phylo launchers above, so it is EXCLUDED BY DESIGN rather than counted as library debt.
# NOTE (latent, deliberately not redesigned here): this set matches on BASENAME across every
# SCAN_DIR, so naming a tools/ front door also excludes any mamey/ module with the same file
# name. mamey/blastp_channel_triage.py emits nothing to stdout today (verified at .403 staging),
# so nothing is being hidden — but a basename-scoped exclusion is a hole waiting for a collision.
# Second latent note: check_print_calls below is a TEXT regex, so a comment or docstring that
# merely names the call token is counted as one. Keep prose in this file clear of it.
# Making the exclusion path-scoped is a separate candidate, not a composer delta.
# v97395: phylo_place.py is the direct sibling of phylo_preflight.py/phylo_postflight.py in the
# same operator-CLI-launcher family (its stdout is the placement receipt/log, not a hygiene
# concern) but was never added when those two were. Reached independently by two lanes this cut
# cycle -- an independent composition audit and Codex's CODEX_395_COMBINED_REPO_HEALTH_CLI_OUTPUT_
# CLASSIFICATION_REPAIR.patch both landed on the identical fix; this is that convergent fix,
# staged standalone so it doesn't require pulling in Codex's separately-staged, larger
# gene-first-portability patch that their combined diff was bundled with.


def _py_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for d in SCAN_DIRS:
        base = root / d
        if base.is_dir():
            out += [p for p in base.rglob("*.py")
                    if "__pycache__" not in p.parts and "_vendor" not in p.parts
                    and not any(x in p.parts for x in CLI_TOOL_EXCLUDE_DIRS)
                    # v9.7.404 (A3): was `p.name not in CLI_TOOL_EXCLUDE_FILES` — a BASENAME match
                    # across every SCAN_DIR, so naming a tools/ operator front door also silently
                    # excluded any mamey/ library module with the same file name. That collision is
                    # not hypothetical: v9.7.403 shipped BOTH tools/blastp_channel_triage.py (an
                    # operator front door whose stdout is the deliverable) and
                    # mamey/blastp_channel_triage.py (a library module that must stay scanned).
                    # Nothing was hidden at the time — the library module emits nothing to stdout —
                    # but the exclusion was one `print(` away from concealing real debt. The set is
                    # now scoped to tools/ only, which is the only place an operator front door lives.
                    and not (p.parent == root / "tools" and p.name in CLI_TOOL_EXCLUDE_FILES)]
    return out


# ---- checks -----------------------------------------------------------------
def check_syntax(files: list[Path], root: Path) -> tuple[Result, dict[Path, ast.AST]]:
    trees: dict[Path, ast.AST] = {}
    bad = []
    for p in files:
        try:
            trees[p] = ast.parse(p.read_text())
        except SyntaxError as e:
            bad.append(f"{p.relative_to(root)}:{e.lineno}: {e.msg}")
    if bad:
        return Result("syntax", "FAIL", f"{len(bad)} file(s) fail to parse", bad), trees
    return Result("syntax", "OK", f"{len(files)} files parse"), trees


def check_collisions_gate(root: Path) -> Result:
    """Delegate duplicate-dict-key detection to the wired gate rather than reimplementing it."""
    import subprocess
    gate = root / "tools" / "check_duplicate_dict_keys.py"
    if not gate.is_file():
        return Result("collisions", "WARN", "tools/check_duplicate_dict_keys.py not found")
    try:
        r = subprocess.run([sys.executable, str(gate), "--strict"],
                           capture_output=True, text=True, cwd=str(root), timeout=120)
    except Exception as e:  # noqa: BLE001 - surface any invocation failure as a WARN
        return Result("collisions", "WARN", f"gate did not run: {e}")
    if r.returncode == 0:
        return Result("collisions", "OK", "wired dup-key gate --strict: PASS")
    hits = [ln for ln in (r.stdout + r.stderr).splitlines() if ln.strip()]
    return Result("collisions", "FAIL", "wired dup-key gate --strict: FAIL", hits)


def check_placeholder_keys(trees: dict[Path, ast.AST], root: Path) -> Result:
    hits = []
    for p, tree in trees.items():
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                for k in node.keys:
                    if isinstance(k, ast.Constant) and isinstance(k.value, str) and PLACEHOLDER_RE.search(k.value):
                        hits.append(f"{p.relative_to(root)}:{k.lineno}: placeholder dict key {k.value!r}")
    if hits:
        return Result("placeholder_keys", "FAIL", f"{len(hits)} placeholder dict key(s)", hits)
    return Result("placeholder_keys", "OK", "no placeholder dict keys")


def check_manifest_drift(root: Path) -> Result:
    man = root / "MODULE_MANIFEST.txt"
    if not man.is_file():
        return Result("manifest_drift", "WARN", "MODULE_MANIFEST.txt not found")
    listed = set(re.findall(r"((?:mamey|tools)/[\w/]+\.py)", man.read_text()))
    missing = sorted(x for x in listed if not (root / x).is_file())
    if missing:
        return Result("manifest_drift", "FAIL",
                      f"{len(missing)} manifest path(s) missing on disk", missing)
    return Result("manifest_drift", "OK", f"{len(listed)} listed paths all present")


def check_silent_swallow(trees: dict[Path, ast.AST], root: Path) -> Result:
    """`except ...: pass` — a caught exception silently discarded. Baseline is a ceiling, not
    approval: 110 exist at v9.7.307; this stops the count from growing while they're triaged."""
    hits = []
    for p, tree in trees.items():
        for n in ast.walk(tree):
            if isinstance(n, ast.ExceptHandler) and len(n.body) == 1 and isinstance(n.body[0], ast.Pass):
                hits.append(f"{p.relative_to(root)}:{n.lineno}")
    status = "OK" if len(hits) <= SILENT_SWALLOW_CEILING else "WARN"
    return Result("silent_swallow", status,
                  f"{len(hits)} `except ...: pass` (ceiling {SILENT_SWALLOW_CEILING})", hits)


def check_bare_except(files: list[Path], root: Path) -> Result:
    hits = []
    for p in files:
        for i, line in enumerate(p.read_text().splitlines(), 1):
            if re.match(r"\s*except\s*:", line):
                hits.append(f"{p.relative_to(root)}:{i}")
    status = "OK" if len(hits) <= BARE_EXCEPT_WARN_THRESHOLD else "WARN"
    return Result("bare_except", status, f"{len(hits)} bare `except:`", hits)


def _console_imports(nodes):
    out = {}
    for node in nodes:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in ("_console", "mamey.console"):
                    out[alias.asname or alias.name.split(".")[0]] = alias.name if alias.asname else alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "console" and node.module == "mamey":
                    out[alias.asname or alias.name] = "mamey.console"
                elif alias.name == "_console" and not node.module:
                    out[alias.asname or alias.name] = "_console"
    return out


def _console_aliases(tree):
    return frozenset(_console_imports(tree.body))


def _count_console_attributes(tree):
    """Count known module-qualified emitters with lexical imports and local shadowing."""
    scopes = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)
    def flat(nodes):
        for node in nodes:
            yield node
            if not isinstance(node, scopes):
                yield from flat(ast.iter_child_nodes(node))
    def dotted(node):
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            parent = dotted(node.value)
            return parent + "." + node.attr if parent else ""
        return ""
    def count(scope, inherited):
        body = scope.body if isinstance(scope.body, list) else [scope.body]
        nodes = list(flat(body)); aliases = dict(inherited)
        if isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            bound = {n.id for n in nodes if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
            args = scope.args
            bound.update(a.arg for a in [*args.posonlyargs, *args.args, *args.kwonlyargs])
            bound.update(a.arg for a in (args.vararg, args.kwarg) if a)
            for name in bound:
                aliases.pop(name, None)
        # An assignment shadows an imported module. Treat ambiguous reassignments conservatively.
        assigned = {n.id for n in nodes if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
        aliases.update(_console_imports(nodes))
        for name in assigned:
            aliases.pop(name, None)
        total = 0
        for node in nodes:
            if isinstance(node, scopes):
                total += count(node, aliases)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                symbol = dotted(node.func); head, _, tail = symbol.partition(".")
                target = aliases.get(head, "") + "." + tail
                if target in {"_console.emit", "_console.print", "mamey.console.emit", "mamey.console.print"}:
                    total += 1
        return total
    return count(tree, {})


def check_print_calls(files: list[Path], root: Path) -> Result:
    """Count real calls to the builtin, from the AST.

    v9.7.404 (A4): this was `re.findall(r"\\bprint\\s*\\(", text)` over the whole file — a text
    scan, so a COMMENT or DOCSTRING that merely named the call token incremented the metric. That
    is not a hypothetical: writing the v9.7.403 composer delta, a comment explaining the exclusion
    list pushed the count over its own ceiling and turned the gate red for prose. At a
    zero-headroom ceiling that is a live foot-gun, and worse, it means the number the gate defends
    was never the number of print calls. The AST counts calls; a mention in prose is prose.

    Only `print(...)` where `print` is a bare Name is counted — an attribute call such as
    `logger.print(...)` is a different function and never was library debt. Verified at .404 that
    no aliasing, shadowing, `builtins.` qualification or `partial(print, ...)` occurs anywhere in
    mamey/ or tools/, so the Name check is not narrower than the old text scan for anything that
    actually exists here.

    INJECTED-PRINT SITES ARE OUTSIDE THIS METRIC BY DESIGN — 3 known at .404, where `print` is
    passed as a callable rather than called: mamey/render_brief.py:718 and mamey/cli.py:3280
    (`logger=print`), tools/cluster_discovery.py:108 (`log=print` default arg). They DO emit at
    runtime, via the callee. Neither this counter nor the text scan it replaced has ever seen
    them — there is no `print(` token at the injection point — so this is a PRE-EXISTING blind
    spot of both metrics, not a regression introduced by the AST switch, and it does not move the
    ceiling in the unsafe direction. They are a different kind of debt (dependency-injected
    output) and should be tracked separately rather than chased into this count.
    """
    total = 0
    for p in files:
        try:
            tree = ast.parse(p.read_text())
        except SyntaxError:            # already reported by check_syntax; do not double-fail here
            continue
        # v9.7.407: count the EMISSION SITE, not the spelling. The package gained two
        # pass-through emitters (mamey/console.py::emit, tools/_console.py::emit) that forward
        # *args/**kwargs to builtins.print unchanged. Centralising the seam is real architecture
        # -- one place to add --quiet or a capture buffer -- but it does not remove a single
        # emission site, and a counter that only knew the token `print` would have read 2 and
        # silently stopped defending anything. Both names count; the emitter definitions
        # themselves call `builtins.print`, an Attribute call, so they are not double-counted.
        text = p.read_text()
        # Only count `emit` where it is THIS package's terminal emitter, i.e. the file imports it
        # from mamey.console / tools/_console. An unrelated local `emit()` is a different function.
        uses_console = ("from .console import emit" in text or "from ..console import emit" in text
                        or "from mamey.console import emit" in text or "from _console import emit" in text)
        emitters = ("print", "emit") if uses_console else ("print",)
        total += _count_console_attributes(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name) and node.func.id in emitters:
                total += 1
    status = "OK" if total <= PRINT_WARN_THRESHOLD else "WARN"
    return Result("print_calls", status, f"{total} direct terminal-emission calls (ceiling {PRINT_WARN_THRESHOLD})")


INJECTED_PRINT_CEILING = 3   # v9.7.405: the three known sites (render_brief.py, cli.py `logger=print`,
                             # cluster_discovery.py `log=print`). Separate metric, separate ceiling —
                             # the blind spot of check_print_calls is now MEASURED, not footnoted.


def check_injected_print(trees: dict[Path, ast.AST], root: Path) -> Result:
    """Count `print` passed as a VALUE (argument, keyword, default) rather than called.

    These sites emit at runtime through the callee and are invisible to check_print_calls by
    design (no `print(` token at the injection point). v9.7.405 (proposals item 7): counted
    separately with its own ceiling so the debt is tracked instead of narrated in a docstring.
    """
    hits: list[str] = []
    for p, tree in trees.items():
        for node in ast.walk(tree):
            names: list[ast.AST] = []
            if isinstance(node, ast.Call):
                names += [a for a in node.args if isinstance(a, ast.Name)]
                names += [k.value for k in node.keywords if isinstance(k.value, ast.Name)]
            elif isinstance(node, ast.arguments):
                names += [d for d in (node.defaults + node.kw_defaults) if isinstance(d, ast.Name)]
            for n in names:
                # v9.7.407: the emitter rename means an injected output callable can now be
                # spelled `emit` (mamey/render_brief.py, mamey/cli.py `logger=`). Same debt, same
                # runtime behaviour -- count both spellings or the ceiling stops defending it.
                if n.id in ("print", "emit"):
                    hits.append(f"{p.relative_to(root)}:{n.lineno}")
    status = "OK" if len(hits) <= INJECTED_PRINT_CEILING else "WARN"
    return Result("injected_print", status,
                  f"{len(hits)} injected `print` value(s) (ceiling {INJECTED_PRINT_CEILING})", hits)


def check_docstring_cov(trees: dict[Path, ast.AST], root: Path) -> Result:
    funcs = documented = 0
    for p, tree in trees.items():
        if (root / "mamey") not in p.parents:
            continue
        for n in ast.walk(tree):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                funcs += 1
                if ast.get_docstring(n):
                    documented += 1
    pct = (100 * documented // funcs) if funcs else 0
    return Result("docstring_cov", "INFO", f"mamey/ function docstrings: {documented}/{funcs} ({pct}%)")


def check_waiver_slack(root: Path) -> Result:
    """Report how much regression each signed waiver would silently absorb.

    v9.7.412 (BLIZZARD_BLUE-412). A waiver is signed as a SNAPSHOT of debt that exists at
    signing time -- "observed = 1620, I accept it". `observed` legitimately sits ABOVE the
    ceiling; that is the whole point, and this check does not treat it as an error.

    The hazard appears only AFTER the debt is paid down. The ratchet moves down (its own
    source comment: "Ceilings only go down"), the signed `observed` stays frozen, and the
    same number silently becomes a LICENCE TO REGRESS back to it. `_waiver_covers` still
    returns True anywhere below `observed`, so the regression is waived rather than failed --
    and because the metric currently reads OK, nothing in the report mentions the waiver at
    all. Measured on sealed v9.7.411: silent_swallow absorbs 1 count, print_calls absorbs 340.

    This check does NOT change coverage semantics -- narrowing them could break a legitimate
    in-flight waiver. It only makes the absorption visible, because "silent" was the defect.
    INFO, not WARN: surfacing owner-signed drift must not block a cut on its own.
    """
    waivers = load_waivers(root / _WAIVER_DEFAULT_NAME)
    hits: list[str] = []
    inactive: list[str] = []
    for metric, w in sorted(waivers.items()):
        ceiling = _ratchet_ceiling(metric)
        if ceiling is None or not isinstance(w.get("observed"), int):
            continue
        slack = int(w["observed"]) - int(ceiling)
        if slack > 0:
            if not _waiver_covers(w, int(ceiling) + 1):
                inactive.append(f"{metric}: inactive signing ceiling; grants no regression coverage")
                continue
            hits.append(f"{metric}: signed observed={w['observed']} vs enforced ceiling={ceiling}"
                        f" -> would waive up to {slack} count(s) of NEW regression")
    if not hits and not inactive:
        return Result("waiver_slack", "OK", "no signed waiver sits above its enforced ceiling")
    return Result("waiver_slack", "INFO",
                  f"{len(hits)} signed waiver(s) would absorb regression above the current ceiling; "
                  f"{len(inactive)} inactive waiver(s)",
                  hits + inactive)


def check_onboarding_docs(root: Path) -> Result:
    docs = sorted(p.name for p in root.glob("*")
                  if p.is_file() and re.search(r"read.?me|start.?here", p.name, re.I))
    return Result("onboarding_docs", "INFO", f"{len(docs)} root onboarding docs", docs)


# ---- driver -----------------------------------------------------------------
def run(root: Path) -> list[Result]:
    files = _py_files(root)
    syntax, trees = check_syntax(files, root)
    results = [syntax]
    if syntax.status != "FAIL":
        results += [
            check_collisions_gate(root),
            check_placeholder_keys(trees, root),
            check_manifest_drift(root),
            check_silent_swallow(trees, root),
            check_bare_except(files, root),
            check_print_calls(files, root),
            check_injected_print(trees, root),
            check_docstring_cov(trees, root),
            check_waiver_slack(root),
            check_onboarding_docs(root),
        ]
    return results


_WAIVER_SCHEMA = "sapote.strict_health_waiver/1"
_WAIVER_DEFAULT_NAME = "STRICT_HEALTH_WAIVER.json"


def _metric_count(r: "Result") -> int | None:
    """Current numeric value of a metric (len(hits) for hit-based checks, else the leading int)."""
    if r.hits:
        return len(r.hits)
    m = re.match(r"\s*(\d+)", r.detail)
    return int(m.group(1)) if m else None


def load_waivers(path: Path | None) -> dict[str, dict]:
    """NC-005: load the machine-readable, signed strict-health waiver.

    A waiver entry WAIVES a strict WARN (never a FAIL) only when it is fully signed
    (metric + owner + reason + a numeric `observed`) AND the current count has not drifted above
    the signed `observed`. It documents an explicit, owned exception — it does NOT raise the ceiling.
    """
    if path is None or not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if data.get("schema_version") != _WAIVER_SCHEMA:
        return {}
    out: dict[str, dict] = {}
    for w in data.get("waivers", []):
        metric = str(w.get("metric") or "").strip()
        owner = str(w.get("owner") or "").strip()
        reason = str(w.get("reason") or "").strip()
        observed = w.get("observed")
        if metric and owner and reason and isinstance(observed, int):
            out[metric] = w
    return out


def _ratchet_ceiling(metric: str) -> int | None:
    """Currently enforced ceiling for a ratcheted metric, or None if it is not ratcheted."""
    const = _RATCHETS.get(metric)
    return globals().get(const) if const else None


def _waiver_covers(waiver: dict, current: int | None) -> bool:
    """Does this signed waiver still cover the current count?

    v9.7.412 (BLIZZARD_BLUE-412): adds the OPTIONAL `ceiling_at_signing` field.

    The original rule was `current <= observed`. That is correct while the ceiling holds still,
    and inverts once the ceiling is ratcheted DOWN beneath a frozen `observed`: the same number
    that documented EXISTING debt silently becomes a licence to REGRESS back to it. Measured on
    sealed v9.7.411 -- print_calls ceiling 1280 vs signed observed 1620, a 340-count band in
    which a regression is waived rather than failed, on a metric whose own source comment reads
    "Ceilings only go down."

    The fix is not to narrow coverage arithmetically -- that would break a legitimate in-flight
    waiver. It is to make the waiver STOP APPLYING when the ground it was signed against moves.
    When `ceiling_at_signing` is present it must equal the currently enforced ceiling; if the
    ceiling has changed in either direction the waiver no longer applies and must be re-signed.
    That forces exactly the conscious owner decision the waiver's own `_note` says the mechanism
    exists to force, instead of letting a stale signature quietly widen.

    Backward compatible: a waiver without `ceiling_at_signing` keeps the legacy rule, so no
    existing signed file changes behaviour on the day this lands. `check_waiver_slack` reports
    the slack such a legacy waiver still carries.
    """
    if current is None or current > int(waiver["observed"]):
        return False
    # v9.7.414 (BLIZZARD_BLUE-414): read the signing ceiling from the field the schema ALREADY
    # has. Every waiver entry carries `ceiling` -- the enforced ceiling at signing time. The
    # v9.7.412 `ceiling_at_signing` field I added duplicated it, and because nothing adopted the
    # new field it has had ZERO effect: both live waivers still carry `ceiling_at_signing: None`.
    # Using the existing `ceiling` needs no schema change and no adoption step, and it fires on
    # the already-signed file today: print_calls signed ceiling 1300 vs enforced 1280;
    # silent_swallow signed ceiling 110 vs enforced 147.
    signed_ceiling = waiver.get("ceiling_at_signing")
    if not isinstance(signed_ceiling, int):
        signed_ceiling = waiver.get("ceiling")
    if isinstance(signed_ceiling, int):
        now = _ratchet_ceiling(str(waiver.get("metric") or ""))
        if now is not None and int(signed_ceiling) != int(now):
            return False  # ground moved since signing -> re-sign, do not silently extend
    return True


_RATCHETS = {  # metric name -> constant name in this file
    "print_calls": "PRINT_WARN_THRESHOLD",
    "silent_swallow": "SILENT_SWALLOW_CEILING",
    "injected_print": "INJECTED_PRINT_CEILING",
}


def ratchet_down(results: list) -> int:
    """Lower each ratchet constant to its measured value when measured < ceiling. Never raises.

    Rewrites ONLY the integer literal after `NAME = ` (the trailing comment survives) and appends
    a dated audit trail comment. Exit 0 always; prints one line per metric.
    """
    import datetime as _dt
    me = Path(__file__)
    src = me.read_text()
    changed = []
    for r in results:
        const = _RATCHETS.get(r.name)
        if not const:
            continue
        m = re.match(r"(\d+)", r.detail)
        if not m:
            continue
        measured = int(m.group(1))
        cur = re.search(rf"(?m)^{const} = (\d+)", src)
        if not cur:
            continue
        ceiling = int(cur.group(1))
        if measured < ceiling:
            src = re.sub(rf"(?m)^{const} = \d+",
                         f"{const} = {measured}", src, count=1)
            src = src.replace(f"{const} = {measured}",
                              f"{const} = {measured}  # ratchet-down {_dt.date.today().isoformat()}: {ceiling} -> {measured} (measured)", 1)
            changed.append((r.name, ceiling, measured))
            sys.stdout.write(str(f"ratchet-down {r.name}: {ceiling} -> {measured}") + "\n")
        else:
            sys.stdout.write(str(f"ratchet-hold {r.name}: measured {measured}, ceiling {ceiling} (no change)") + "\n")
    if changed:
        me.write_text(src)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Sapote-Mamey repo-health gate")
    ap.add_argument("--root", default=None, help="bundle root (default: parent of tools/)")
    ap.add_argument("--strict", action="store_true", help="promote WARN to FAIL")
    ap.add_argument("--json", action="store_true", help="emit JSON report")
    ap.add_argument("--ratchet-down", action="store_true",
                    help="v9.7.405: when a measured debt count is BELOW its ceiling, rewrite that ceiling "
                         "constant in this file to the measured value (never upward) and report the delta. "
                         "Turns 'zero headroom' from a fact you discover into one you cannot drift past.")
    ap.add_argument("--waiver", default=None,
                    help=f"path to a signed strict-health waiver JSON (default: <root>/{_WAIVER_DEFAULT_NAME})")
    ap.add_argument("--candidate-census", metavar="DIR", default=None,
                    help="v9.7.405: OPT-IN, standalone -- run tools/candidate_census.py against "
                         "DIR (pyc/__pycache__/.pytest_cache/.DS_Store debris) and print its JSON "
                         "receipt. Excluded by design from the run()/--strict/--ratchet-down "
                         "sweep and from every ratchet constant below: this flag short-circuits "
                         "before any of that runs, so it can never move a ratchet ceiling.")
    args = ap.parse_args(argv)

    root = _repo_root(args.root)
    if args.candidate_census is not None:
        import importlib.util as _ilu
        _spec = _ilu.spec_from_file_location(
            "candidate_census", Path(__file__).resolve().parent / "candidate_census.py")
        _cc = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_cc)
        return _cc.main([args.candidate_census])

    results = run(root)
    if args.ratchet_down:
        return ratchet_down(results)

    waiver_path = Path(args.waiver) if args.waiver else (root / _WAIVER_DEFAULT_NAME)
    waivers = load_waivers(waiver_path) if args.strict else {}

    failed: list[Result] = []
    waived: list[tuple[Result, dict]] = []
    for r in results:
        is_fail = r.status == "FAIL"
        is_strict_warn = args.strict and r.status == "WARN"
        if not (is_fail or is_strict_warn):
            continue
        w = waivers.get(r.name)
        # only a strict WARN can be waived — a hard FAIL is never waivable
        if is_strict_warn and w is not None and _waiver_covers(w, _metric_count(r)):
            waived.append((r, w))
        else:
            failed.append(r)

    waived_names = {r.name for r, _ in waived}
    if args.json:
        sys.stdout.write((json.dumps({
            "root": str(root),
            "strict": args.strict,
            "passed": not failed,
            "results": [{"name": r.name, "status": r.status, "detail": r.detail, "hits": r.hits,
                         "waived": r.name in waived_names}
                        for r in results],
            "waived": [{"metric": r.name, "observed_now": _metric_count(r),
                        "signed_observed": w.get("observed"), "ceiling": w.get("ceiling"),
                        "owner": w.get("owner"), "reason": w.get("reason")}
                       for r, w in waived],
        }, indent=2)) + "\n")
    else:
        icon = {"OK": "✓", "WARN": "!", "FAIL": "✗", "INFO": "·"}
        sys.stdout.write((f"repo-health: {root}") + "\n")
        for r in results:
            tag = " (WAIVED)" if r.name in waived_names else ""
            sys.stdout.write((f"  {icon.get(r.status, '?')} [{r.status:4}] {r.name:16} {r.detail}{tag}") + "\n")
            for h in r.hits[:20]:
                sys.stdout.write((f"        - {h}") + "\n")
            if len(r.hits) > 20:
                sys.stdout.write((f"        … and {len(r.hits) - 20} more") + "\n")
        for r, w in waived:
            sys.stdout.write((f"  · WAIVED {r.name}: signed observed {w.get('observed')} ceiling {w.get('ceiling')} "
                  f"— {w.get('owner')}: {w.get('reason')}") + "\n")
        sys.stdout.write((f"\n{'FAIL' if failed else 'PASS'}: "
              f"{len(failed)} blocking issue(s)" if failed else "PASS: no blocking issues") + "\n")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
