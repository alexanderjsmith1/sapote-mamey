#!/usr/bin/env python3
"""
audit_public_cut.py — workbook-aware public-cut leak guard for merged-master Excel deliverables.

WHY THIS EXISTS. `make_public_tier.sh` / `redact_public_tier.py` scrub the *code bundle's* text files
with grep/sed, but those tools cannot see inside an `.xlsx` — it is zipped XML, opaque to a text grep.
The merged-master PUBLIC cut is an `.xlsx`, so its provenance sheets (e.g. `00_MERGE_GUIDE`) have escaped
the leak audit. Twice a held-cohort reference survived the data-row filter into the public guide: first a
full `AS-XXX` strain line (named host + BGC count + source workbook), later the `BeeCohort_2026-06`
cohort codename ("AS held"). In both cases the *data* sheets were clean and a token grep over the rows
passed — the leak lived in prose the row-filter never touched. This tool closes that gap: it reaches
inside every sheet and every cell, audits data AND prose, reconciles against the PRIVATE master, and
optionally scrubs.

WHAT IT CHECKS
  1. Static research-strain tokens — `AS-###` (and `AS-##+`) and `AJS…`. Never allowed in a public cut.
     (`AS-\\d{3}` is hyphen-anchored, so the public KCB string `AL-KSAMP_AS10_SC01` does NOT trip it.)
  2. Denylist terms — read from `tools/release_denylist.txt` (e.g. , ).
  3. Derived held set (with --private) — held cohorts/strains = private − public. Asserts that NONE of
     them appear in the public workbook, in ANY cell, data or prose. This is what catches a held-cohort
     CODENAME or a carried-over strain line WITHOUT hardcoding either — the tool learns what to hunt for
     from what was actually held.
  4. Strain-roster completeness — every strain ID in a designated strain column (strain / strain_id /
     cohort_id / bgc_uid prefix) must be in the public roster (Strain_Master, or --roster). A stray held
     strain keyed into a coded sheet is caught here even if its token form is unusual.
  5. Reconciliation (with --private) — per-cohort BGC row-count diff = the held rows; the held cohort is
     absent from the public BGC_Master.

SID is PUBLIC in the data product (SID_public_2020 is a published NCBI cohort) and is NOT flagged here —
unlike the code tiers, where redact_public_tier.py scrubs SID example data. WAC and type-strain controls
are public too.

MODES
  default : audit-only. Writes a markdown report; exit 0 if CLEAN, non-zero if any leak survives.
  --scrub : genericize derived/known held-cohort codenames and strain lines in prose cells, write
            <input>_SCRUBBED.xlsx, then RE-AUDIT the result — refuses (non-zero) if it is not clean.

USAGE
  python tools/audit_public_cut.py PUBLIC.xlsx [--private PRIVATE.xlsx] [--roster strains.txt]
      [--held-replacement "the held research cohort"] [--scrub] [--out report.md]

Exit code 0 = CLEAN (safe to send w.r.t. these patterns). Non-zero = leak found / refused.
"""
import argparse
import os
import re
import sys
from pathlib import Path
from collections import Counter, defaultdict

try:
    import openpyxl
except ImportError:
    sys.stderr.write("audit_public_cut.py requires openpyxl (pip install openpyxl --break-system-packages)\n")
    sys.exit(2)

# --- static patterns (defense-in-depth; always checked) ----------------------
# v9.7.371 fix: RESEARCH_STRAIN/STRAIN_TOKEN (and the standalone-fallback PENDING- regex) lacked
# re.I even though AJS_STRAIN/HELD_PHRASES right beside them already carry it -- this tool's own
# docstring frames it as catching a held codename "in ANY cell, data or prose", so a lowercase/
# mixed-case strain token or held-cohort phrase (plausible casual authoring, e.g. a notes cell
# reading "AS-XXX held pending re-run") silently escaped this leak guard. Safety-positive only:
# can only catch MORE, never fewer, real tokens.
RESEARCH_STRAIN = re.compile(r"\bAS-\d{3,}", re.I)      # AS-XXX, AS-XXX, AS-XXX_Master_Workbook, …
AJS_STRAIN      = re.compile(r"\bAJS[-_]?\d+", re.I)
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from redact_public_tier import private_id_matches as _private_id_matches
except Exception:  # pragma: no cover - standalone fallback
    def _private_id_matches(text, as_only=True):
        out = RESEARCH_STRAIN.findall(text or "") + AJS_STRAIN.findall(text or "")
        out += re.findall(r"\bPENDING-[A-Z0-9]+", text or "", re.I)
        return out
try:
    from _wbio import atomic_save, atomic_write_text
except ImportError as exc:  # pragma: no cover - broken/incomplete bundle
    raise RuntimeError(
        "audit_public_cut.py requires the bundled tools/_wbio.py; refusing to write "
        "a public-cut workbook or audit report without atomic output support"
    ) from exc
HELD_PHRASES    = re.compile(r"\(AS held\)|AS held|research \(AS\) tier|AS[\s_-]?tier held", re.I)
# strain-ID forms enumerated from designated strain columns
STRAIN_TOKEN    = re.compile(r"\b(SID\d{1,5}|WAC\d{3,6}|AS-\d{3,}|AJS[-_]?\d+)\b", re.I)
STRAIN_COLS     = {"strain", "strain_id", "cohort_id", "bgc_uid"}
COHORT_COLS     = {"cohort_id", "cohort", "release"}
DENYLIST_PATH   = os.path.join(os.path.dirname(__file__), "release_denylist.txt")


def _load_denylist():
    terms = []
    try:
        with open(DENYLIST_PATH, encoding="utf-8") as fh:
            for line in fh:
                t = line.strip()
                if t and not t.startswith("#"):
                    terms.append(t)
    except FileNotFoundError:
        pass
    return terms


def _held_tokens(held_cohorts, held_strains):
    """Full held identifiers PLUS their distinctive alphabetic stems, so a prose mention of the bare
    codename prefix (e.g. 'BeeCohort' from cohort_id 'BeeCohort_2026-06') is hunted too, not just the
    exact cohort_id. Stems shorter than 5 chars or non-alphabetic are skipped (avoids matching generic
    fragments like 'AS' or year digits; AS-### strain tokens are covered by RESEARCH_STRAIN anyway)."""
    toks = set(held_cohorts) | set(held_strains)
    for ident in list(toks):
        for part in re.split(r"[_\-\s()|]+", ident):
            if len(part) >= 5 and part.isalpha():
                toks.add(part)
    return sorted(toks, key=len, reverse=True)


def _iter_cells(path):
    """Yield (sheet, row_idx, col_idx, header, value) for every non-empty string/num cell."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    for ws in wb.worksheets:
        rows = ws.iter_rows(values_only=True)
        try:
            header = [str(c).strip() if c is not None else "" for c in next(rows)]
        except StopIteration:
            continue
        # header row itself counts as row 1
        for ci, h in enumerate(header):
            if h:
                yield ws.title, 1, ci, h, h
        for ri, row in enumerate(rows, start=2):
            for ci, c in enumerate(row):
                if c is None:
                    continue
                head = header[ci] if ci < len(header) else f"col{ci}"
                yield ws.title, ri, ci, head, c
    wb.close()


# v9.7.374 fix: the real merged-master producer (tools/merge_workbooks.py, SHEET_DEFAULT) writes
# "B1_BGC_Master" + a hardcoded "A2_Strain_Registry" registry sheet -- the same naming convention
# mamey/master_workbook.py's CANONICAL_V1_HEADERS uses for the per-strain workbook, and the same
# tolerance tools/build_id_resolver.py already applies when reading a BGC sheet ("BGC_Master",
# "C1_BGC_Master", "BGC_Inventory"). This module's reconciliation reader only ever looked for the
# bare "BGC_Master"/"Strain_Master" names its own test fixtures use, which do not match any real
# producer in this codebase. Confirmed live: run against a workbook shaped like the actual
# merge_workbooks.py output, every reconciliation check below silently examines zero rows and
# reports a vacuous ALL-CLEAR (schema_identical=True, public_subset_private=True,
# delta_is_held_only=True, held_cohorts=[]) regardless of what the workbook actually contains --
# and the tool's own headline feature (deriving a held-cohort codename to hunt for in prose, e.g.
# the "BeeCohort_2026-06" incident cited in this file's own docstring) goes completely inert, so a
# bare held-cohort stem leaked into public prose is reported CLEAN. Trying multiple candidate names
# is the same defensive pattern build_id_resolver.py already uses for this exact ambiguity.
BGC_SHEET_NAMES = ("BGC_Master", "B1_BGC_Master", "C1_BGC_Master", "BGC_Inventory")
STRAIN_SHEET_NAMES = ("Strain_Master", "A2_Strain_Registry", "Strain_Registry")


def _find_sheet(wb, names):
    return next((wb[n] for n in names if n in wb.sheetnames), None)


def workbook_schema_findings(path, role="public"):
    """Fail closed when a purported merged-master lacks the sheets this audit governs.

    Before this check, a workbook with neither a recognized BGC-master nor strain-roster
    sheet could produce empty counters on both sides of the reconciliation and therefore a
    vacuous CLEAN result.  Cell-token scanning is still useful, but it cannot establish public
    roster completeness or public/private row parity without these two governed schemas.
    """
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        findings = []
        if _find_sheet(wb, BGC_SHEET_NAMES) is None:
            findings.append({
                "kind": "required_bgc_sheet_missing",
                "where": role,
                "detail": "none of " + ", ".join(BGC_SHEET_NAMES),
            })
        if _find_sheet(wb, STRAIN_SHEET_NAMES) is None:
            findings.append({
                "kind": "required_strain_sheet_missing",
                "where": role,
                "detail": "none of " + ", ".join(STRAIN_SHEET_NAMES),
            })
        return findings
    finally:
        wb.close()


def _cohorts_and_strains(path):
    """Return (cohort->bgc_row_count, set(strain_ids)) from a workbook's BGC-master + strain-roster
    sheets (see BGC_SHEET_NAMES / STRAIN_SHEET_NAMES for the accepted sheet-name aliases)."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    coh = Counter()
    strains = set()
    ws = _find_sheet(wb, BGC_SHEET_NAMES)
    if ws is not None:
        rows = ws.iter_rows(values_only=True)
        hdr = [str(c).strip() if c is not None else "" for c in next(rows)]
        ci = hdr.index("cohort_id") if "cohort_id" in hdr else (hdr.index("cohort") if "cohort" in hdr else None)
        for row in rows:
            if all(c is None for c in row):
                continue
            if ci is not None and row[ci] is not None:
                coh[str(row[ci]).strip()] += 1
    ws = _find_sheet(wb, STRAIN_SHEET_NAMES)
    if ws is not None:
        rows = ws.iter_rows(values_only=True)
        hdr = [str(c).strip() if c is not None else "" for c in next(rows)]
        si = hdr.index("strain") if "strain" in hdr else 1
        for row in rows:
            if si < len(row) and row[si] is not None:
                v = str(row[si]).strip()
                if v and v.upper() != "TOTAL":
                    strains.add(v)
    wb.close()
    return coh, strains


def _bgc_uids(path):
    """(header_tuple, list_of_bgc_uids) for a workbook's BGC-master sheet (BGC_SHEET_NAMES)."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    header, uids = (), []
    ws = _find_sheet(wb, BGC_SHEET_NAMES)
    if ws is not None:
        rows = ws.iter_rows(values_only=True)
        hdr = [str(c).strip() if c is not None else "" for c in next(rows)]
        header = tuple(hdr)
        ui = hdr.index("bgc_uid") if "bgc_uid" in hdr else None
        for row in rows:
            if ui is not None and row[ui] is not None:
                uids.append(str(row[ui]))
    wb.close()
    return header, uids


def merge_invariants(public, private):
    """Doc-6 #2: the four checks an auditor otherwise reconstructs by hand. Returns a dict + a list of
    invariant-violation findings (schema drift, dup keys, public⊄private, delta≠held-only)."""
    findings = workbook_schema_findings(public, "public")
    findings.extend(workbook_schema_findings(private, "private"))
    pub_hdr, pub_uids = _bgc_uids(public)
    prv_hdr, prv_uids = _bgc_uids(private)
    pub_coh, _ = _cohorts_and_strains(public)
    prv_coh, _ = _cohorts_and_strains(private)
    pub_set, prv_set = set(pub_uids), set(prv_uids)

    schema_ok = bool(pub_hdr and prv_hdr and pub_hdr == prv_hdr)
    if not schema_ok:
        findings.append({"kind": "schema_drift", "where": "BGC_Master",
                         "detail": "public/private column set or order differ"})
    pub_dups = len(pub_uids) - len(pub_set)
    prv_dups = len(prv_uids) - len(prv_set)
    if pub_dups or prv_dups:
        findings.append({"kind": "bgc_uid_not_unique", "where": "BGC_Master",
                         "detail": f"public dups={pub_dups}, private dups={prv_dups}"})
    public_not_in_private = pub_set - prv_set
    if public_not_in_private:
        findings.append({"kind": "public_not_subset_private", "where": "BGC_Master",
                         "detail": f"{len(public_not_in_private)} public bgc_uid(s) absent from private"})
    held = set(prv_coh) - set(pub_coh)
    recon = []
    delta_ok = True
    for c in sorted(set(prv_coh) | set(pub_coh)):
        pub_n, prv_n = pub_coh.get(c, 0), prv_coh.get(c, 0)
        d = prv_n - pub_n
        recon.append((c, pub_n, prv_n, d))
        if d != 0 and c not in held:
            delta_ok = False
    if not delta_ok:
        findings.append({"kind": "delta_not_held_only", "where": "BGC_Master",
                         "detail": "a non-held cohort differs between public and private"})
    inv = {"schema_identical": schema_ok, "pub_rows": len(pub_uids), "prv_rows": len(prv_uids),
           "pub_unique": len(pub_set), "prv_unique": len(prv_set),
           "public_subset_private": len(public_not_in_private) == 0,
           "reconciliation": recon, "held_cohorts": sorted(held), "delta_is_held_only": delta_ok}
    return inv, findings


def release_invariant(public):
    """Doc-6 #4: independent assertion that every row carrying a `release` column is `public`
    (or blank). Catches a row mis-tagged at cohort level that cohort-filtering missed."""
    findings = []
    wb = openpyxl.load_workbook(public, read_only=True, data_only=True)
    checked = 0
    for ws in wb.worksheets:
        rows = ws.iter_rows(values_only=True)
        try:
            hdr = [str(c).strip().lower() if c is not None else "" for c in next(rows)]
        except StopIteration:
            continue
        if "release" not in hdr:
            continue
        ri_idx = hdr.index("release")
        for ri, row in enumerate(rows, start=2):
            if ri_idx < len(row) and row[ri_idx] is not None:
                val = str(row[ri_idx]).strip().lower()
                checked += 1
                if val and val != "public":
                    findings.append({"kind": "release_not_public", "where": f"{ws.title} r{ri}",
                                     "detail": f"release={val!r}"})
    wb.close()
    return checked, findings


def audit(public, private=None, roster=None):
    """Run the full audit. Return (findings: list[dict], context: dict)."""
    # merge_invariants performs the two-workbook schema check below; audit-only mode
    # still needs an explicit public schema check here.
    findings = [] if private else workbook_schema_findings(public, "public")
    denylist = _load_denylist()

    # public roster
    pub_coh, pub_strains = _cohorts_and_strains(public)
    if roster:
        with open(roster, encoding="utf-8") as fh:
            pub_strains |= {l.strip() for l in fh if l.strip()}

    # derived held set from private (the strongest signal)
    held_cohorts, held_strains = set(), set()
    recon = None
    if private:
        prv_coh, prv_strains = _cohorts_and_strains(private)
        held_cohorts = set(prv_coh) - set(pub_coh)
        held_strains = prv_strains - pub_strains
        recon = {"public": dict(pub_coh), "private": dict(prv_coh),
                 "held_cohorts": sorted(held_cohorts),
                 "held_rows": {c: prv_coh[c] for c in held_cohorts}}
        # any held cohort still present in public BGC rows?
        for c in held_cohorts:
            if c in pub_coh:
                findings.append({"kind": "held_cohort_in_public_data", "where": "BGC_Master",
                                 "detail": f"held cohort {c!r} still has {pub_coh[c]} public rows"})

    # derived held tokens to hunt for (full identifiers + distinctive stems), escaped for regex
    held_tokens = _held_tokens(held_cohorts, held_strains)
    # v9.7.371 fix: was case-sensitive -- this derived regex is exactly the mechanism this
    # tool's own docstring describes as catching a held codename "in ANY cell, data or prose";
    # without re.I a codename typed in different casing than held_tokens' own source records
    # silently escaped the sweep below.
    held_re = re.compile("|".join(re.escape(t) for t in held_tokens), re.I) if held_tokens else None

    # full cell sweep
    for sheet, ri, ci, head, val in _iter_cells(public):
        s = val if isinstance(val, str) else str(val)
        priv_hits = _private_id_matches(s, as_only=True)
        if priv_hits:
            findings.append({"kind": "private_identifier_token", "where": f"{sheet} r{ri}",
                             "detail": f"{';'.join(sorted(set(priv_hits)))} in {s[:90]!r}"})
        if HELD_PHRASES.search(s):
            findings.append({"kind": "held_phrase", "where": f"{sheet} r{ri}", "detail": s[:90]})
        if held_re and held_re.search(s):
            findings.append({"kind": "derived_held_token", "where": f"{sheet} r{ri}", "detail": s[:90]})
        for term in denylist:
            if term.lower() in s.lower():
                findings.append({"kind": "denylist_term", "where": f"{sheet} r{ri}",
                                 "detail": f"{term!r} in {s[:70]!r}"})
        # strain-roster completeness (designated strain columns only — avoids KCB-string FPs)
        if head in STRAIN_COLS:
            for m in STRAIN_TOKEN.findall(s):
                base = m.split("|")[0] if "|" in s else m
                if m.startswith(("AS-", "AJS")):
                    findings.append({"kind": "held_strain_in_roster_col", "where": f"{sheet} r{ri} [{head}]",
                                     "detail": m})
                elif pub_strains and m not in pub_strains and not m.startswith(("SID", "WAC")):
                    findings.append({"kind": "strain_not_in_public_roster", "where": f"{sheet} r{ri} [{head}]",
                                     "detail": m})

    # Doc-6 #4: independent per-row release-flag invariant (every public row must be release=public)
    rel_checked, rel_findings = release_invariant(public)
    findings.extend(rel_findings)

    # Doc-6 #2: merge-invariant log (schema identity, uid uniqueness, public⊆private, cohort recon)
    invariants = None
    if private:
        invariants, inv_findings = merge_invariants(public, private)
        findings.extend(inv_findings)

    context = {"public_cohorts": dict(pub_coh), "public_strain_count": len(pub_strains),
               "held_cohorts": sorted(held_cohorts), "held_strains_sample": sorted(held_strains)[:10],
               "denylist": denylist, "reconciliation": recon,
               "release_rows_checked": rel_checked, "invariants": invariants}
    return findings, context


def scrub(public, out, private=None, replacement="the held research cohort"):
    """Genericize derived/known held-cohort codenames & strain lines in prose, write `out`."""
    held_cohorts, held_strains = set(), set()
    if private:
        prv_coh, prv_strains = _cohorts_and_strains(private)
        pub_coh, pub_strains = _cohorts_and_strains(public)
        held_cohorts = set(prv_coh) - set(pub_coh)
        held_strains = prv_strains - pub_strains
    tokens = _held_tokens(held_cohorts, held_strains)
    pats = [re.compile(re.escape(t)) for t in tokens]
    pats.append(HELD_PHRASES)
    pats.append(RESEARCH_STRAIN)
    pats.append(AJS_STRAIN)
    # collapse runs of the replacement string (with adjacent punctuation) into one, so stacked
    # substitutions like 'BeeCohort_2026-06(AS held)' don't yield a doubled replacement.
    dedupe = re.compile(r"(?:" + re.escape(replacement) + r")(?:\W*" + re.escape(replacement) + r")+")

    wb = openpyxl.load_workbook(public)
    n = 0
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str):
                    new = cell.value
                    for p in pats:
                        new = p.sub(replacement, new)
                    new = dedupe.sub(replacement, new)
                    if new != cell.value:
                        cell.value = new
                        n += 1
    # v9.7.371 fix: was a direct wb.save(out) -- scrub() writes the genericized PUBLIC-tier
    # deliverable itself; an interrupted write here (crash, kill, disk full) leaves a corrupted/
    # partial .xlsx at the destination with no signal anything went wrong. atomic_save (already
    # this codebase's established fix for the same class of bug, e.g. tools/_wbio.py's own
    # consumers) writes to a sibling .tmp and os.replace()s it into place instead.
    atomic_save(wb, out)
    return n


def write_report(findings, context, public, out_path):
    clean = len(findings) == 0
    lines = []
    lines.append(f"# Public-cut leak audit — {os.path.basename(public)}")
    lines.append("")
    lines.append(f"*workbook-aware (all sheets, all cells incl. provenance prose) · "
                 f"tools/audit_public_cut.py*")
    lines.append("")
    lines.append(f"## Verdict: {'**CLEAN** — safe to send w.r.t. these patterns ✓' if clean else '**LEAK — do not send** ✗'}")
    lines.append("")
    if context.get("reconciliation"):
        r = context["reconciliation"]
        lines.append("## Reconciliation (public vs private)")
        lines.append(f"- public cohorts: {r['public']}")
        lines.append(f"- private cohorts: {r['private']}")
        lines.append(f"- held (private−public): {r['held_cohorts']} — rows: {r['held_rows']}")
        lines.append("")
    inv = context.get("invariants")
    if inv:
        lines.append("## Merge invariants")
        lines.append(f"- schema identical (public vs private BGC_Master): "
                     f"{'YES ✓' if inv['schema_identical'] else 'NO ✗'}")
        lines.append(f"- bgc_uid unique: public {inv['pub_unique']}/{inv['pub_rows']}, "
                     f"private {inv['prv_unique']}/{inv['prv_rows']} "
                     f"{'✓' if inv['pub_unique']==inv['pub_rows'] and inv['prv_unique']==inv['prv_rows'] else '✗'}")
        lines.append(f"- public ⊆ private: {'YES ✓' if inv['public_subset_private'] else 'NO ✗'}")
        lines.append(f"- delta is held-cohort-only: {'YES ✓' if inv['delta_is_held_only'] else 'NO ✗'}")
        lines.append("")
        lines.append("| Cohort | Public | Private | Δ |")
        lines.append("|---|---:|---:|---:|")
        for c, pn, vn, d in inv["reconciliation"]:
            held = " (held)" if c in inv["held_cohorts"] else ""
            lines.append(f"| {c}{held} | {pn} | {vn} | {d} |")
        lines.append("")
    if context.get("release_rows_checked") is not None:
        rel_bad = sum(1 for f in findings if f["kind"] == "release_not_public")
        lines.append(f"## Release-flag invariant")
        lines.append(f"- rows carrying a `release` column checked: {context['release_rows_checked']} — "
                     f"non-`public` values: {rel_bad} {'✓' if rel_bad==0 else '✗'}")
        lines.append("")
    if not clean:
        by = defaultdict(list)
        for f in findings:
            by[f["kind"]].append(f)
        lines.append("## Findings")
        for kind, items in by.items():
            lines.append(f"\n### {kind} ({len(items)})")
            for it in items[:30]:
                lines.append(f"- `{it['where']}`: {it['detail']}")
            if len(items) > 30:
                lines.append(f"- … and {len(items)-30} more")
    else:
        lines.append("No research-strain tokens (`AS-###`/`AJS`), no derived held-cohort tokens, no "
                     "held-phrase prose, no denylist terms, and every strain ID is in the public roster.")
    lines.append("")
    lines.append("## Scope")
    lines.append(f"- public cohorts: {context['public_cohorts']}")
    lines.append(f"- public roster size: {context['public_strain_count']}")
    if context["held_cohorts"]:
        lines.append(f"- held cohorts hunted for: {context['held_cohorts']}")
    atomic_write_text(out_path, "\n".join(lines) + "\n")
    return clean


def main(argv=None):
    ap = argparse.ArgumentParser(description="Workbook-aware public-cut leak guard.")
    ap.add_argument("public", help="public .xlsx to audit")
    ap.add_argument("--private", help="private .xlsx — derive the held set + reconcile")
    ap.add_argument("--roster", help="optional newline-delimited allowed public strain IDs")
    ap.add_argument("--scrub", action="store_true", help="write scrubbed .xlsx and re-audit")
    ap.add_argument("--scrub-out", help="path for the scrubbed .xlsx (default: <input>_SCRUBBED.xlsx)")
    ap.add_argument("--held-replacement", default="the held research cohort")
    ap.add_argument("--out", help="markdown report path (default: <input>_leak_audit.md)")
    args = ap.parse_args(argv)

    target = args.public
    if args.scrub:
        out_xlsx = args.scrub_out or (os.path.splitext(args.public)[0] + "_SCRUBBED.xlsx")
        n = scrub(args.public, out_xlsx, private=args.private, replacement=args.held_replacement)
        sys.stderr.write(f"scrubbed {n} cell(s) -> {out_xlsx}\n")
        target = out_xlsx

    findings, context = audit(target, private=args.private, roster=args.roster)
    out_md = args.out or (os.path.splitext(target)[0] + "_leak_audit.md")
    clean = write_report(findings, context, target, out_md)
    sys.stderr.write(f"report -> {out_md}\n")
    sys.stderr.write(f"VERDICT: {'CLEAN' if clean else 'LEAK (' + str(len(findings)) + ' finding(s))'}\n")
    return 0 if clean else 1


if __name__ == "__main__":
    sys.exit(main())
