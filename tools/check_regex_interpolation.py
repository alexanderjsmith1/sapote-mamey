#!/usr/bin/env python3
"""check_regex_interpolation.py — fail closed on regex patterns that interpolate an
UNBOUND alternation.

WHY
---
Interpolating a constant that contains a top-level `|` into a larger regex WITHOUT wrapping it
in a group silently rebinds the pattern: regex alternation has the lowest precedence, so the
surrounding atoms attach to only the first/last branch. The pattern still compiles, still
matches *something*, and no test fails — the classic silent-coverage bug.

Two shipped instances of this exact class were found and fixed on 2026-08-31 (v9.7.395 pool):

  tools/modeb_card_guard.py     rf"{GEN} sp\\.? \\((...)-associated"  — GEN is a 15-genus
      alternation; the ` sp. (…` tail (and the eco capture group inside it) bound only to the
      LAST genus, silently disabling the ecology-fabrication check for the other 14. That is
      the guard written to catch the 2026-08-17 incident.
  (sibling class) tools/preflight_zip_hygiene.py — a token list applied with the wrong binding
      scope (full path vs basename). Not detectable by this AST check, but the same mechanical
      family: an interpolated token set whose binding was never pinned by a test.

WHAT IT DETECTS
---------------
For every f-string (and `+`-concatenation of string constants/names) in a scanned file:
  1. resolve each interpolated bare name to same-module string-constant assignment(s);
  2. if a resolved value contains a TOP-LEVEL `|` (outside groups/classes, unescaped),
     assemble the full pattern twice — value as-is, and value wrapped in `(?:...)` —
     and parse both with the stdlib regex parser;
  3. if the two parse trees differ, the alternation bleeds into the surrounding pattern:
     that is a finding. (If they are equal — e.g. the site already writes `({VAR})` — the
     binding is sound and nothing is flagged.)
A candidate is only considered regex-like if the assembled text contains a backslash escape
OR the composition is a direct argument to `re.compile/search/match/fullmatch/finditer/
findall/sub/subn/split`. This gate removes markdown-table / pipe-delimited-data f-strings
(measured on the live tree: 9 of 10 raw candidates were such non-regex strings; the tenth was
the real modeb_card_guard bug).

Known residuals (documented, not silent): `%`-formatting and `.format()` composition are not
modeled; names that resolve only across modules, through calls, or through `str.join()` are
counted as UNRESOLVED and reported in the summary rather than silently skipped; a backslash-free
regex passed indirectly (not a direct `re.*` argument) is below the gate.

USAGE
  python tools/check_regex_interpolation.py             # gate: exit 1 on any finding
  python tools/check_regex_interpolation.py --list      # report findings + coverage stats
  python tools/check_regex_interpolation.py --json
  python tools/check_regex_interpolation.py --root mamey tools
Exit 0 = clean. Exit 1 = finding(s). Exit 2 = usage error / missing root / empty scan
(a gate that scans nothing must not PASS — same contract as check_duplicate_dict_keys).
"""
from __future__ import annotations
import argparse
import ast
import json
import sys
from pathlib import Path

try:
    from re import _parser as _sre_parse   # py3.11+
except ImportError:                         # pragma: no cover
    import sre_parse as _sre_parse

# path -> why this site is tolerated. Ratchet: this list must only ever SHRINK.
ALLOWLIST: dict[str, str] = {}

SKIP_PARTS = {"__pycache__", "_vendor", ".git", "node_modules", "build", "dist"}
_RE_FUNCS = {"compile", "search", "match", "fullmatch", "finditer", "findall",
             "sub", "subn", "split"}


def top_level_alternation(s: str) -> bool:
    """True if `s` contains a `|` at group depth 0, outside a character class, unescaped."""
    depth = 0
    in_class = False
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\":
            i += 2
            continue
        if in_class:
            if c == "]":
                in_class = False
        elif c == "[":
            in_class = True
        elif c == "(":
            depth += 1
        elif c == ")":
            depth = max(0, depth - 1)
        elif c == "|" and depth == 0:
            return True
        i += 1
    return False


def _parses_differently(unwrapped: str, wrapped: str):
    """True if both parse as regexes AND their parse trees differ; False if equal;
    None if either does not parse (not a regex — no claim made)."""
    try:
        a = _sre_parse.parse(unwrapped)
        b = _sre_parse.parse(wrapped)
    except Exception:
        return None
    return repr(a) != repr(b)


def _collect_str_constants(tree) -> dict[str, set]:
    vals: dict[str, set] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    vals.setdefault(t.id, set()).add(node.value.value)
    return vals


def _atom(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [("lit", node.value)]
    if isinstance(node, ast.Name):
        return [("name", node.id)]
    return [("other", None)]


def _flatten(node):
    """Composition -> [('lit', s) | ('name', id) | ('other', None)], or None."""
    if isinstance(node, ast.JoinedStr):
        parts = []
        for v in node.values:
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                parts.append(("lit", v.value))
            elif isinstance(v, ast.FormattedValue) and isinstance(v.value, ast.Name):
                parts.append(("name", v.value.id))
            else:
                parts.append(("other", None))
        return parts
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _flatten(node.left) or _atom(node.left)
        right = _flatten(node.right) or _atom(node.right)
        return left + right
    return None


def _direct_re_arg_nodes(tree) -> set:
    """(lineno, col) of nodes passed directly to a re.* function."""
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "re" \
                and node.func.attr in _RE_FUNCS and node.args:
            a = node.args[0]
            out.add((getattr(a, "lineno", 0), getattr(a, "col_offset", 0)))
    return out


def scan_file(path: Path, stats=None):
    """Yield finding dicts for unbound interpolated alternations in `path`."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return
    consts = _collect_str_constants(tree)
    re_args = _direct_re_arg_nodes(tree)
    seen = set()
    for node in ast.walk(tree):
        parts = _flatten(node)
        if not parts or all(k != "name" for k, _ in parts):
            continue
        loc = (getattr(node, "lineno", 0), getattr(node, "col_offset", 0))
        if loc in seen:
            continue
        seen.add(loc)
        if stats is not None:
            unresolved = sum(1 for k, v in parts
                             if k == "other" or (k == "name" and v not in consts))
            stats["unresolved_parts"] = stats.get("unresolved_parts", 0) + unresolved
        for idx, (kind, name) in enumerate(parts):
            if kind != "name" or name not in consts:
                continue
            for candidate in sorted(consts[name]):
                if not top_level_alternation(candidate):
                    continue
                unl, wrl = [], []
                resolvable = True
                for j, (k2, v2) in enumerate(parts):
                    if k2 == "lit":
                        unl.append(v2); wrl.append(v2)
                    elif k2 == "name" and v2 in consts:
                        sub = candidate if j == idx else sorted(consts[v2])[0]
                        unl.append(sub)
                        wrl.append("(?:" + sub + ")" if j == idx else sub)
                    else:
                        resolvable = False
                        break
                if not resolvable:
                    continue
                assembled = "".join(unl)
                # regex-context gate: backslash escape present, or direct re.* argument
                if "\\" not in assembled and loc not in re_args:
                    continue
                if _parses_differently(assembled, "".join(wrl)):
                    yield {"line": node.lineno, "var": name,
                           "value": candidate[:80] + ("..." if len(candidate) > 80 else ""),
                           "assembled": assembled[:120],
                           "fix": f"wrap the interpolation: (?:{{{name}}})"}


def collect(roots, stats=None):
    for root in roots:
        rp = Path(root)
        files = [rp] if rp.is_file() else sorted(rp.rglob("*.py"))
        for f in files:
            if any(part in SKIP_PARTS for part in f.parts):
                continue
            if stats is not None:
                stats["files"] = stats.get("files", 0) + 1
            for rec in scan_file(f, stats):
                rec["file"] = f.as_posix()
                yield rec


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Fail closed on regex patterns interpolating an unbound alternation.")
    ap.add_argument("--root", nargs="*", default=["mamey", "tools", "tests"])
    ap.add_argument("--strict", action="store_true", help="ignore the allowlist")
    ap.add_argument("--list", action="store_true", help="report findings + coverage stats")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    # A gate run that scans NOTHING must not PASS (same contract as check_duplicate_dict_keys).
    missing = [r for r in a.root if not Path(r).exists()]
    if missing:
        sys.stderr.write(f"regex-interpolation gate: ERROR — root(s) do not exist: "
                         f"{missing} (wrong working directory?)\n")
        return 2

    stats = {"files": 0, "unresolved_parts": 0}
    new, known = [], []
    for rec in collect(a.root, stats):
        if not a.strict and rec["file"] in ALLOWLIST:
            rec["allowlisted"] = ALLOWLIST[rec["file"]]
            known.append(rec)
        else:
            new.append(rec)

    if stats["files"] == 0:
        sys.stderr.write(f"regex-interpolation gate: ERROR — 0 python files found under "
                         f"root(s) {a.root}; refusing to PASS on an empty scan\n")
        return 2

    if a.json:
        sys.stdout.write(json.dumps({"new": new, "allowlisted": known,
                                     "files_scanned": stats["files"],
                                     "unresolved_interpolations": stats["unresolved_parts"]},
                                    indent=2) + "\n")
        return 1 if new else 0

    if a.list or known:
        for r in known:
            sys.stdout.write(f"  known  {r['file']}:{r['line']}  {{{r['var']}}}  ({r['allowlisted']})\n")
    for r in new:
        sys.stderr.write(f"  UNBOUND {r['file']}:{r['line']}  {{{r['var']}}} carries a top-level '|' "
                         f"but the surrounding pattern binds into its first/last branch only.\n"
                         f"          value: {r['value']!r}\n"
                         f"          fix:   {r['fix']}\n")

    if new:
        sys.stderr.write(f"\nregex-interpolation gate: FAIL ({len(new)} unbound alternation "
                         f"site(s)). Alternation has the lowest precedence — the surrounding "
                         f"atoms bind to a single branch, silently disabling the pattern for "
                         f"every other branch.\n")
        return 1
    sys.stdout.write(f"\nregex-interpolation gate: PASS ({len(known)} known site(s) "
                     f"allowlisted, 0 new; {stats['files']} file(s) scanned, "
                     f"{stats['unresolved_parts']} unresolved interpolation(s) outside "
                     f"static reach)\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
