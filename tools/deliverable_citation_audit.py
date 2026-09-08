#!/usr/bin/env python3
"""deliverable_citation_audit.py — pre-delivery §15 citation + provenance gate for FINISHED deliverables.

The missing step between authoring a deliverable and shipping it. `verify-modeb` (via
`mamey.modeb_structure_gate._citation_findings`) already checks node/region citation, but three
gaps leave the actual shipping incident unguarded:

  1. It is DELIBERATELY WEAK. Per the v9.7.209 refinement in that gate, a BGC is considered fine
     "as long as it is cited with a locator *somewhere* in the card" — so `BGC039/BGC027's tier`
     scattered through prose passes. That is correct for a single §1-§30 card, but it is NOT the
     §15 rule for a compiled report.
  2. It runs ONLY on §1-§30 Mode B cards. The compiled deliverables where the incident actually
     happened — Lay Guide, Synopsis, Chapter, exclusion tables, lead-tier tables, fermentation
     guidance — never pass through `verify-modeb` at all.
  3. The strict every-mention regex the compiled-report rule needs (`_BARE_BGC_RE` in
     `modeb_structure_gate.py`) is DEFINED BUT NEVER CALLED. The rule text (execution slice §15,
     restated at CHATGPT_EXECUTION_SLICE §15 "compiled report") tells the author to run the scan
     BY HAND: "search for bare BGC\\d{3} patterns not followed by NODE_ or `· r\\d+` within the same
     clause. Fix every hit. In a compiled report this is non-trivial — budget time for it."

That hand-scan is what this tool automates. The documented incident it targets: 324 bare BGC-ID
instances in one compiled report (all in exclusion lists, lead-tier tables, cross-references,
fermentation guidance). It runs over one file or a whole directory of finished .md/.txt, applies
the §15 rule WITH its documented exceptions (tables carry the locator in an adjacent column; TOC
entries may abbreviate), tags provenance presence, and — because BGC numbering drifts across
sources — flags ID collisions (the same BGC number bound to conflicting node/region locators).

WHAT IT IS FOR (honest scope): a CITATION + PROVENANCE + COLLISION reviewer over finished text.
It does NOT read the sealed package, recompute boundaries, run BLASTp, or judge product class —
that is `bgc_reconcile.py` (pre-authoring) and the engine. It reads the words that will ship and
answers one question: does every BGC in this document carry its address, is provenance tagged, and
do the addresses agree with themselves. It reuses the engine's own citation/provenance regex shapes
(see `_ENGINE_CONSISTENCY` in the tests) so "located" here means what "located" means in the gate.

CLAIM DISCIPLINE (hard):
  - Every finding is a CITATION-HYGIENE prompt, never a science verdict and never a phenotype.
  - The tool reports only whether the address/provenance/collision hygiene holds; it never edits
    the science, re-derives a locator, or invents a node/region that is not already in the text.
  - Quoted offending tokens are shown inside backticks (code context), never as prose claims, so
    the rendered report itself passes claim-safety self-lint.

Severity model:
  BLOCK (ERROR)  — a bare BGC mention in a PROSE clause with no node/region locator in that clause;
                   a genuine ID COLLISION (one BGC number → two different node/region addresses in
                   the same strain scope). These are the §15 shipping violations.
  WATCH (WARN)   — a bare BGC mention inside a table row that carries no locator anywhere in the row;
                   a `SID-XXX BGCddd` cross-strain-table mention with no locator (a recognized
                   cross-strain idiom that still drifts from §15); a file with BGC mentions but no
                   provenance tag at all; an unscoped (GLOBAL) collision that may be legitimate
                   cross-strain reuse.
  INFO           — a hyphen/slash prose cross-reference (`BGC039-specific`, `BGC039/BGC027`) with no
                   in-clause locator (the engine's own gate treats these as prose, not citations —
                   surfaced so the author can decide, not to force a fix); a TOC-line abbreviation.

Exit: with --strict, exits 1 if any BLOCK finding exists (bare-prose or real collision). Mirrors
`bgc_reconcile.py --strict`, so this drops into a pre-delivery gate the same way.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

import argparse
import json
import os
import re
import sys
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from _wbio import atomic_write_text

# ── Regexes — kept LOCAL for standalone robustness, but asserted consistent with the engine's
#    `mamey.modeb_structure_gate` shapes in tests/test_deliverable_citation_audit.py::test_engine_consistency
#    so they cannot silently drift from what "located"/"provenance" mean in verify-modeb. ──────────

# Any BGC id token: BGC + exactly three digits, not glued to another word char.
_ANY_BGC_RE = re.compile(r"\bBGC(\d{3})\b", re.IGNORECASE)
# v9.7.395: was case-sensitive, so a lowercase/mixed-case citation ("bgc039") produced ZERO
# findings at all -- not even NO_PROVENANCE_TAGS -- completely bypassing this file's own BLOCK-
# severity BARE_IN_PROSE §15 shipping gate. Same bypass class already fixed at .383/.384 in
# bgc_citation_gate.py / sapote_hooks/bgc_citation_node_guard.py, and this session in the sibling
# modeb_structure_gate.py MISSING_LOCATOR check -- this is the fourth instance found, and per
# this file's own docstring the one this tool exists specifically to catch ("the actual shipping
# incident" a §1-§30-only check misses), so a case-insensitivity gap here is the most consequential
# instance of the four.

# A node/region LOCATOR token, in any of the forms the project uses. This is what makes an id "located".
#   NODE_1_length_20000_cov_50 · region001  |  NODE_32 · r001  |  ctg58_45  |  region001  |  · r001
_LOCATOR_TOKEN_RE = re.compile(
    r"(?:NODE_\d+\w*"          # SPAdes node, optionally with _length…_cov…
    r"|\bctg\d+(?:_\d+)?\b"    # antiSMASH ctg locus / ctgN
    r"|·\s*r\d+"              # abbreviated · r001
    r"|·\s*region\s*\d+"      # · region001
    r"|\bregion0*\d+\b)",      # bare region001 / region1
    re.IGNORECASE)

# BGCddd IMMEDIATELY followed by a locator parenthetical — the canonical inline citation.
# Mirrors _LOCATOR_BGC_RE in modeb_structure_gate.py (BGC(\d{3})\s*\((?:NODE|NODE_|ctg|[^)]*·)).
_LOCATOR_INLINE_RE = re.compile(r"\bBGC(\d{3})\s*\((?:NODE|NODE_|ctg|region|[^)]*·)", re.IGNORECASE)

# Cross-strain abbreviation form used in DAPR / cohort lead tables: "SID-XXX BGC050", "AS-XXX BGC008".
_SID_PREFIXED_RE = re.compile(r"(?:SID-\w+|AS-\d+)\s+BGC\d{3}", re.IGNORECASE)

# Provenance vocabulary — identical set to modeb_structure_gate._PROVENANCE_RE.
_PROVENANCE_RE = re.compile(
    r"store-backed|store backed|reconstructed|corpus|derived|"
    r"observed|inferred|computed|assumed",
    re.IGNORECASE)

# Clause delimiters for the "within the same clause" test (NOT comma — a comma commonly separates a
# BGC id from a shared trailing locator, and the canonical citation puts the locator on the id anyway).
_CLAUSE_SPLIT_RE = re.compile(r"[.;:—]")

# Strain-scope token for collision scoping, from a mention prefix or a filename.
_STRAIN_TOKEN_RE = re.compile(r"(SID-\w+|AS-\d+)", re.IGNORECASE)

# A markdown table separator row: |---|:--:|  etc.
_TABLE_SEP_RE = re.compile(r"^\s*\|?[\s:|-]+\|?\s*$")


# ── line classification ──────────────────────────────────────────────────────────────────────────

def _classify_lines(text: str):
    """Yield (lineno, raw_line, kind) with kind in {code, heading, table_sep, table_row, toc, prose}.
    Fenced code blocks are marked 'code' and skipped by the scanner. A crude but reliable TOC region
    detector: lines under a heading whose title contains 'contents' until the next heading."""
    in_fence = False
    in_toc = False
    for i, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            yield i, line, "code"
            continue
        if in_fence:
            yield i, line, "code"
            continue
        if stripped.startswith("#"):
            in_toc = "contents" in stripped.lower() or "table of contents" in stripped.lower()
            yield i, line, "heading"
            continue
        if _TABLE_SEP_RE.match(line) and "|" in line and "-" in line:
            yield i, line, "table_sep"
            continue
        if in_toc and stripped:
            yield i, line, "toc"
            continue
        if "|" in line and line.count("|") >= 2:
            yield i, line, "table_row"
            continue
        yield i, line, "prose"


def _clause_of(line: str, pos: int) -> str:
    """Return the clause (delimited by . ; : —) of `line` that contains character index `pos`."""
    starts = [0] + [m.end() for m in _CLAUSE_SPLIT_RE.finditer(line)]
    ends = [m.start() for m in _CLAUSE_SPLIT_RE.finditer(line)] + [len(line)]
    for s, e in zip(starts, ends):
        if s <= pos <= e:
            return line[s:e]
    return line


# region number in any project form: `· region001`, `region1`, `· r001`, `r5`
_REGION_RE = re.compile(r"(?:·\s*region\s*|·\s*r|\bregion\s*|\br)0*(\d+)", re.IGNORECASE)
# accession-style contig token: NZ_KB898221.1 / CP012345.1 / GCF_000009.1 / ARIN00000000
_ACCESSION_RE = re.compile(r"\b([A-Za-z]{2,}_[A-Za-z0-9]+(?:\.\d+)?|[A-Za-z]{1,3}\d{5,}(?:\.\d+)?)\b")


def _norm_locator(text_window: str):
    """Extract a normalized (node, region) address from a text window, or None.
    Handles SPAdes NODE_x, antiSMASH ctgN, AND accession contigs (NZ_…, CP…, GCF_…) — the last is
    the case a smoke fixture misses and a real NCBI genome exposes. 'NODE_1_length…·region001'
    -> ('NODE_1','1'); 'NZ_KB898221.1 region002' -> ('NZ_KB898221.1','2')."""
    region = None
    mr = _REGION_RE.search(text_window)
    if mr:
        region = mr.group(1).lstrip("0") or "0"
    node = None
    mn = re.search(r"\bNODE_(\d+)", text_window, re.IGNORECASE)
    if mn:
        node = f"NODE_{mn.group(1)}"
    else:
        mc = re.search(r"\bctg(\d+)", text_window, re.IGNORECASE)
        if mc:
            node = f"ctg{mc.group(1)}"
        else:
            ma = _ACCESSION_RE.search(text_window)
            if ma:
                node = ma.group(1)
    if node is None and region is None:
        return None
    return (node, region)


# ── collision address-binding (inline forms only — never row/co-mention scoped) ───────────────────
# Two directions the project uses:  Form A prose  `BGCddd (locator)`  ·  Form B board  `locator (BGCddd)`.
# Binding ONLY from these (plus a single-id clause guard in scan_text) is what stops a co-mention like
# `BGC002+BGC022` in BGC022's row from binding BGC002 to BGC022's address (the accession-genome bug).
_BIND_A_RE = re.compile(r"\bBGC(\d{3})\s*\(([^)]{0,80})\)", re.IGNORECASE)  # v9.7.395: same fix
_BIND_B_RE = re.compile(r"([^|()\n]{1,70}?(?:region|·\s*r)\s*0*\d+)\s*\(BGC(\d{3})\)", re.IGNORECASE)


def _extract_bindings(text: str, source: str):
    """Return unambiguous (bgc_num, (node,region), source, line) address bindings for the collision pass."""
    out = []
    for m in _BIND_A_RE.finditer(text):
        loc = _norm_locator(m.group(2))
        if loc:
            out.append((m.group(1), loc, source, text.count("\n", 0, m.start()) + 1))
    for m in _BIND_B_RE.finditer(text):
        loc = _norm_locator(m.group(1))
        if loc:
            out.append((m.group(2), loc, source, text.count("\n", 0, m.start()) + 1))
    return out


_IMAGE_RE = re.compile(r"^\s*!\[")                                     # markdown image embed
_CAPTION_RE = re.compile(r"^\s*\*?\s*(figure|fig\.?|table)\b", re.IGNORECASE)  # figure/table caption
_FIELD_RE = re.compile(r"^\s*(?:[-*]\s*)?\*\*[^*]+:\*\*")              # **Key:** value field line


# ── core scan ──────────────────────────────────────────────────────────────────────────────────

def scan_text(text: str, source: str = "<text>"):
    """Return (findings, located, prov_finding) for one document.
    findings: list of dicts {severity, code, file, line, token, context, note}.
    located: list of (bgc_num, norm_locator, file, line) — inline + single-id-clause bindings only."""
    findings = []
    has_bgc = False
    has_provenance = bool(_PROVENANCE_RE.search(text))

    lines = list(_classify_lines(text))

    def _lookahead_locator(idx: int, span: int = 3) -> bool:
        """True if a locator token appears in the next `span` non-blank lines (field-block layout:
        `**BGC:** BGC040` followed by `**Node / contig:** NZ_…` / `**antiSMASH region:** region001`)."""
        seen = 0
        for j in range(idx + 1, min(len(lines), idx + 1 + span * 2)):
            nxt = lines[j][1]
            if not nxt.strip():
                continue
            if _LOCATOR_TOKEN_RE.search(nxt) or _ACCESSION_RE.search(nxt):
                return True
            seen += 1
            if seen >= span:
                break
        return False

    for idx, (lineno, line, kind) in enumerate(lines):
        if kind in ("code", "table_sep", "heading"):
            continue
        if _IMAGE_RE.match(line):                    # image embed — alt text is a filename, not a citation
            continue

        is_caption = bool(_CAPTION_RE.match(line))
        is_field = bool(_FIELD_RE.match(line))
        field_covered = is_field and _lookahead_locator(idx)
        row_has_locator = bool(_LOCATOR_TOKEN_RE.search(line) or _ACCESSION_RE.search(line)) \
            if kind in ("table_row", "toc") else False

        line_ids = set(_ANY_BGC_RE.findall(line))

        for m in _ANY_BGC_RE.finditer(line):
            has_bgc = True
            num = m.group(1)
            start = m.start()

            # canonical inline citation?  BGCddd (NODE… · r…) — anchored at the id's start.
            if _LOCATOR_INLINE_RE.match(line, start):
                continue

            after = line[m.end(): m.end() + 1]
            # `/` and `+` join cross-references / RGGMCI pairings (BGC039/BGC027, BGC031+BGC040) on
            # either side; `-` only as a suffix (BGC039-specific).
            is_cross_ref = after in ("-", "/", "+") or (start >= 1 and line[start - 1] in ("/", "+"))
            before = line[max(0, start - 8):start]
            is_sid = bool(_SID_PREFIXED_RE.search(before + line[start:m.end()]))

            clause = _clause_of(line, start)
            clause_ids = set(_ANY_BGC_RE.findall(clause))
            clause_located = bool(_LOCATOR_TOKEN_RE.search(clause) or _ACCESSION_RE.search(clause))

            # covered by a locator in the same clause (prose variant of the citation)
            if clause_located and not is_sid:
                continue
            # covered by a field-block locator two lines down (§1 identity block)
            if field_covered and not is_sid:
                continue

            ctx = clause.strip()[:120]

            if is_caption:
                findings.append(dict(
                    severity="INFO", code="CAPTION_NO_LOCATOR", file=source, line=lineno,
                    token=f"BGC{num}", context=ctx,
                    note="figure/table caption references a bare id; captions may abbreviate but "
                         "carrying `· NODE_x`/accession keeps them §15-consistent."))
                continue

            if kind == "table_row":
                if row_has_locator:
                    continue
                findings.append(dict(
                    severity="WATCH", code="BARE_IN_TABLE", file=source, line=lineno,
                    token=f"BGC{num}", context=ctx,
                    note="table row cites the id with no node/region anywhere in the row; add a "
                         "Node/Region column value or inline `(NODE_x · rNNN)`."))
                continue

            if kind == "toc":
                findings.append(dict(
                    severity="INFO", code="BARE_IN_TOC", file=source, line=lineno,
                    token=f"BGC{num}", context=ctx,
                    note="TOC entry may abbreviate but should carry at least `· NODE_x` (§15)."))
                continue

            if is_sid:
                findings.append(dict(
                    severity="WATCH", code="SID_PREFIXED_NO_LOCATOR", file=source, line=lineno,
                    token=f"BGC{num}", context=ctx,
                    note="cross-strain `SID-XXX BGCddd` form with no node/region; recognized "
                         "cohort-table idiom but §15 still wants the address."))
                continue

            if is_cross_ref:
                findings.append(dict(
                    severity="INFO", code="CROSSREF_NO_LOCATOR", file=source, line=lineno,
                    token=f"BGC{num}", context=ctx,
                    note="hyphen/slash prose cross-reference; the engine gate treats these as prose, "
                         "not citations — fix only if this is a first/primary mention."))
                continue

            findings.append(dict(
                severity="BLOCK", code="BARE_IN_PROSE", file=source, line=lineno,
                token=f"BGC{num}", context=ctx,
                note="bare BGC id in a prose clause with no node/region in the same clause — the §15 "
                     "shipping violation. Write `BGC{n} (NODE_x · rNNN)`.".replace("{n}", num)))

    # collision index: inline Form A/B bindings, plus single-BGC clause/row bindings (unambiguous only)
    located = _extract_bindings(text, source)
    for lineno, line, kind in lines:
        if kind in ("code", "table_sep") or _IMAGE_RE.match(line):
            continue
        ids = set(_ANY_BGC_RE.findall(line))
        if len(ids) == 1 and (_LOCATOR_TOKEN_RE.search(line) or _ACCESSION_RE.search(line)):
            loc = _norm_locator(line)
            if loc:
                located.append((next(iter(ids)), loc, source, lineno))
    # dedup identical (num, loc, source, line) bindings (Form-A + single-id pass can both fire)
    located = list(dict.fromkeys(located))

    prov_finding = None
    if has_bgc and not has_provenance:
        prov_finding = dict(
            severity="WATCH", code="NO_PROVENANCE_TAGS", file=source, line=0,
            token="", context="",
            note="document cites BGCs but carries no provenance tag (store-backed / reconstructed / "
                 "corpus; observed / inferred / computed / assumed). Tag the evidence basis.")
    return findings, located, prov_finding


# ── collision pass ──────────────────────────────────────────────────────────────────────────────

def _strain_scope(source: str, located_entry) -> str:
    """Scope a located id to a strain so cross-strain reuse of BGCddd is not a false collision.
    Prefer a SID-/AS- token in the filename; fall back to the leading filename token; else GLOBAL."""
    base = os.path.basename(source)
    m = _STRAIN_TOKEN_RE.search(base)
    if m:
        return m.group(1).upper()
    # leading token before first underscore/space, if it looks like an id
    lead = re.split(r"[_\s.]", base, 1)[0]
    if re.match(r"^[A-Za-z]+-?\d+$", lead):
        return lead.upper()
    return "GLOBAL"


def find_collisions(all_located):
    """all_located: list of (bgc_num, (node,region), source, line).
    A collision = same (scope, bgc_num) bound to CONFLICTING addresses. A None component is a
    wildcard, not a distinct address — `(NZ_1, None)` and `(NZ_1, 5)` describe the same contig with
    one citation omitting the region, which is NOT a collision. The conflict test: within a group,
    >1 distinct non-None NODE, OR >1 distinct non-None REGION. GLOBAL-scoped collisions (no strain
    token in the filenames) are downgraded to WATCH — they may be legitimate cross-strain reuse."""
    by_key = {}
    for num, loc, source, line in all_located:
        scope = _strain_scope(source, (num, loc, source, line))
        by_key.setdefault((scope, num), {}).setdefault(loc, []).append((source, line))

    findings = []
    for (scope, num), addr_map in sorted(by_key.items()):
        addrs = sorted(addr_map.keys(), key=lambda x: (x[0] or "", x[1] or ""))
        nodes = {n for n, r in addrs if n}
        regions = {r for n, r in addrs if r}
        if len(nodes) <= 1 and len(regions) <= 1:
            continue  # no conflicting non-None node or region — one address (partials tolerated)
        # keep only the addresses that participate in the conflict for the report
        conflicting = [loc for loc in addrs if (loc[0] in nodes and len(nodes) > 1)
                       or (loc[1] in regions and len(regions) > 1)]
        sev = "BLOCK" if scope != "GLOBAL" else "WATCH"
        code = "ID_COLLISION" if scope != "GLOBAL" else "ID_COLLISION_UNSCOPED"
        where = []
        for loc in conflicting:
            node, region = loc
            addr_str = f"{node or '?'}·r{region or '?'}"
            locs = "; ".join(f"{os.path.basename(s)}:{ln}" for s, ln in addr_map[loc][:4])
            where.append(f"`{addr_str}` [{locs}]")
        findings.append(dict(
            severity=sev, code=code, file=scope, line=0,
            token=f"BGC{num}", context=" vs ".join(where),
            note=(f"BGC{num} is bound to conflicting node/region addresses within scope "
                  f"{scope}. Reconcile the numbering before delivery (an id must map to one address "
                  f"per strain)." if scope != "GLOBAL"
                  else f"BGC{num} maps to conflicting addresses across files with no strain scope in "
                       f"their names — may be legitimate cross-strain reuse; confirm scoping.")))
    return findings


# ── render ──────────────────────────────────────────────────────────────────────────────────────

_SEV_ORDER = {"BLOCK": 0, "WATCH": 1, "INFO": 2}


def render_md(all_findings, per_file_counts, collisions, files):
    lines = []
    lines.append("# Pre-delivery citation & provenance audit")
    lines.append("")
    lines.append("*§15 node/region every-mention scan + provenance-tag check + BGC-id collision "
                 "check over finished deliverables. Every finding flags a citation-hygiene issue, "
                 "never a science verdict. Offending ids appear in `backticks` (code context).*")
    lines.append("")

    n_block = sum(1 for f in all_findings + collisions if f["severity"] == "BLOCK")
    n_watch = sum(1 for f in all_findings + collisions if f["severity"] == "WATCH")
    n_info = sum(1 for f in all_findings + collisions if f["severity"] == "INFO")
    lines.append(f"**Scanned {len(files)} file(s).** "
                 f"BLOCK: {n_block} · WATCH: {n_watch} · INFO: {n_info}")
    lines.append("")

    # per-file receipts table
    lines.append("## Per-file receipts")
    lines.append("")
    lines.append("| File | BGC mentions | located | BARE prose (BLOCK) | table/SID/other | provenance |")
    lines.append("|---|--:|--:|--:|--:|---|")
    for f in files:
        c = per_file_counts.get(f, {})
        prov = c.get("provenance", "—")
        lines.append(
            f"| `{os.path.basename(f)}` | {c.get('mentions', 0)} | {c.get('located', 0)} "
            f"| {c.get('block', 0)} | {c.get('watch', 0) + c.get('info', 0)} | {prov} |")
    lines.append("")

    if collisions:
        lines.append("## ID collisions (numbering drift across the set)")
        lines.append("")
        for f in sorted(collisions, key=lambda x: _SEV_ORDER[x["severity"]]):
            lines.append(f"- **[{f['severity']}] {f['code']}** — {f['token']}: {f['context']}")
            lines.append(f"  - {f['note']}")
        lines.append("")

    # fix-list, sorted by severity then file then line
    actionable = [f for f in all_findings if f["severity"] in ("BLOCK", "WATCH", "INFO")]
    if actionable:
        lines.append("## Fix-list")
        lines.append("")
        for f in sorted(actionable, key=lambda x: (_SEV_ORDER[x["severity"]],
                                                   x["file"], x["line"])):
            loc = f"{os.path.basename(f['file'])}:{f['line']}" if f["line"] else os.path.basename(f["file"])
            ctx = f" — “{f['context']}”" if f["context"] else ""
            lines.append(f"- **[{f['severity']}] {f['code']}** `{loc}` `{f['token']}`{ctx}")
            lines.append(f"  - {f['note']}")
        lines.append("")

    if not actionable and not collisions:
        lines.append("_No citation, provenance, or collision findings — the set is §15-clean._")
        lines.append("")

    lines.append("---")
    lines.append("*Scope: this tool reads finished text only. It never edits the science, "
                 "re-derives a locator, or invents a node/region not already present. "
                 "Pre-authoring channel reconciliation is `tools/bgc_reconcile.py`; per-card "
                 "structure/depth is `mamey verify-modeb`.*")
    return "\n".join(lines)


# ── self-lint (mirror bgc_reconcile) ─────────────────────────────────────────────────────────────

def _self_lint(rendered: str):
    """The rendered report must not itself read as an overclaim. Reuse the project linter if importable."""
    try:
        sys.path.insert(0, _HERE)
        from claim_safety_linter import lint_claim_safety  # type: ignore
    except Exception:
        return []
    return lint_claim_safety(rendered)


# ── driver ──────────────────────────────────────────────────────────────────────────────────────

def _iter_paths(inputs):
    for p in inputs:
        pp = Path(p)
        if pp.is_dir():
            for f in sorted(pp.rglob("*")):
                if f.suffix.lower() in (".md", ".markdown", ".txt") and f.is_file():
                    yield f
        elif pp.is_file():
            yield pp


def audit(inputs):
    files = [str(f) for f in _iter_paths(inputs)]
    all_findings = []
    all_located = []
    per_file_counts = {}
    for f in files:
        try:
            text = Path(f).read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            per_file_counts[f] = {"error": str(e)}
            continue
        findings, located, prov = scan_text(text, source=f)
        if prov:
            findings.append(prov)
        mentions = len(_ANY_BGC_RE.findall(text))
        per_file_counts[f] = dict(
            mentions=mentions,
            located=len(located),
            block=sum(1 for x in findings if x["severity"] == "BLOCK"),
            watch=sum(1 for x in findings if x["severity"] == "WATCH"),
            info=sum(1 for x in findings if x["severity"] == "INFO"),
            provenance=("tagged" if not any(x["code"] == "NO_PROVENANCE_TAGS" for x in findings)
                        and mentions else ("MISSING" if mentions else "—")),
        )
        all_findings.extend(findings)
        all_located.extend(located)
    collisions = find_collisions(all_located)
    return files, all_findings, all_located, per_file_counts, collisions


def main():
    ap = argparse.ArgumentParser(
        description="Pre-delivery §15 citation + provenance + collision gate for finished deliverables.")
    ap.add_argument("inputs", nargs="+", help="one or more finished .md/.txt files, or directories")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of markdown")
    ap.add_argument("--out", default=None, help="write to path instead of stdout")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 if any BLOCK finding (bare-prose citation or real ID collision)")
    a = ap.parse_args()

    files, findings, located, counts, collisions = audit(a.inputs)

    n_block = sum(1 for f in findings + collisions if f["severity"] == "BLOCK")

    if a.json:
        out = json.dumps({
            "files": [os.path.basename(f) for f in files],
            "summary": {
                "n_files": len(files),
                "n_block": n_block,
                "n_watch": sum(1 for f in findings + collisions if f["severity"] == "WATCH"),
                "n_info": sum(1 for f in findings + collisions if f["severity"] == "INFO"),
            },
            "findings": findings,
            "collisions": collisions,
            "per_file": {os.path.basename(k): v for k, v in counts.items()},
        }, indent=2)
    else:
        out = render_md(findings, counts, collisions, files)
        problems = _self_lint(out)
        if problems:
            emit("# INTERNAL claim-safety self-lint tripped (this is a bug in "
                  "deliverable_citation_audit):", file=sys.stderr)
            for p in problems:
                emit(f"#   {p}", file=sys.stderr)

    if a.out:
        atomic_write_text(a.out, out)
        emit(f"wrote {a.out}")
    else:
        emit(out)

    if a.strict and n_block > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
