#!/usr/bin/env python3
r"""
redact_public_tier.py — CAS-safe SID + AS strain-identifier redaction for PUBLIC bundle tiers.

  - SID strains:  \bSID\d+\b               -> SID-XXX
  - AS  strains:  (?<![A-Za-z])AS-\d{2,4}  -> AS-XXX
    (hyphenated + anchor-free: catches underscore-wrapped ..._AS-NNN_BGC05, but NOT dashless public
     KCB substrings like AL-KSAMP_AS10_SC01, and NOT CAS-/MCAS- cassette stable-IDs.)

For .py files the rewrite is tokenize-aware: only COMMENT, STRING and FSTRING_MIDDLE spans are
touched, never code
identifiers or numeric literals, so a tree-wide walk is safe by construction (closes the --all-py
foot-gun). Non-.py text files are scrubbed whole. CAS stable-IDs are guarded (abort on any change).
Run on PUBLIC tiers only; the MERGED-PRIVATE scaffold legitimately retains strain IDs.

v9.7.156 (PI decision, the Developer or User Smith, 2026-06-30): the AS-series privacy guard is
RETIRED — all AS strains are publicly disclosed (16S on GenBank associating strain/genus/host).
The AS-ID patterns below are RETAINED but INACTIVE for enforcement (the leak audit that consumed
them is now WARN, not FAIL; see make_public_tier.sh AS_GUARD_RETIRED). They are kept deliberately
because the tooling is reusable if a future private cohort needs the same redaction. SID redaction
is unaffected and remains active.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, io, json, os, re, sys, tokenize
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wbio import atomic_write_text  # v9.7.371 fix: this tool rewrites source files in place;
# route through the same crash-safe helper build_id_resolver.py/build_master.py already use in
# this directory, instead of a direct write_text() that can leave a truncated file mid-redaction.

# v9.7.371 fix: SID_RE/AS_RE/PENDING_RE/PRIVATE_ID_RE/_KEYED_ID below were case-sensitive. Per this
# file's own docstring, SID redaction "is unaffected and remains active" (the AS-series guard is
# retired-but-kept per the v9.7.156 PI decision, and AJS-/PENDING- remain actively private per
# project convention) -- a lowercase/mixed-case SID or AJS/PENDING token (plausible casual
# authoring, e.g. a comment or f-string reading a bare SID or PENDING token) survived redaction
# untouched into a PUBLIC tier. Adding re.IGNORECASE is safety-positive only: it can only catch
# MORE tokens that should be redacted, never fewer, and the substitution output (_as_sub / the
# fixed "SID-XXX"/"AS-XXX"/"PENDING-XXX" replacements) is already canonical-cased regardless of
# input case, so this cannot corrupt anything CAS_RE/KNOWN_PUBLIC_AS already guard. Note
# re.IGNORECASE also extends existing [A-Z0-9] character classes to match lowercase automatically
# (Python re semantics), so no character-class edits are needed alongside the flag.
SID_RE = re.compile(r"\bSID\d+\b", re.IGNORECASE)
# v9.7.88: AS_RE catches our cohort IDs in three forms without false-matching public data:
#   - AS-NNN / AJS-NNN  (hyphenated, 2-4 digits) — the canonical form
#   - ASNNNN            (DASHLESS, 3-4 digits)    — e.g. a dashless 3-digit id; this is how one reached a public
#                                                   tier (the old hyphen-only regex missed it)
# It deliberately does NOT match dashless AJS (AJS327 is a public MIBiG organism), 2-digit dashless
# (AS15 is public), CAS-/MCAS- cassette IDs, or LAS-NNN (the trailing AS-NNN is a compound-name tail).
# v9.7.236: AJS split out from the shared A(?:JS|S)- alternation. The `\d{2,}` floor was written
# for the 1-digit AS-N carve-out (prose like "AS-1"), but it silently applied to AJS too, so a
# single-digit AJS id escaped redaction. AJS is unconditionally private (see
# mamey.cohort_figures.is_private) and has no 1-digit prose collision, so it takes \d+.
# Latent, not live: no AJS-<1 digit> strain exists in the current registry. All other carve-outs
# unchanged: AS-1, dashless AS15, dashless AJS327, LAS-/CAS-, and AS-48 via KNOWN_PUBLIC_AS.
# v9.7.410 hostile audit: the hyphen in the canonical form was a literal ASCII `-`, so an id written
# with a non-breaking hyphen (U+2011, what Word and many editors insert), an en/em dash, a soft
# hyphen or zero-width char next to the hyphen, or the HTML entity `&#45;` survived the scrub
# unchanged (AJS followed by U+2011 and digits — AJS is unconditionally private). `_ID_SEP` is one hyphen-like separator
# (any of the Unicode dashes or its entity) optionally wrapped in invisible characters. The
# dashless forms and every carve-out (AS-1, AS15, AJS327, LAS-/CAS-, AS-48) are unchanged.
_ID_SEP = (r"(?:[­​‌‍⁠﻿]*"
           r"(?:[\-‐‑‒–—−]|&#(?:45|8208|8209|8210|8211|8212|8722);|&minus;|&ndash;|&mdash;)"
           r"[­​‌‍⁠﻿]*)")
AS_RE  = re.compile(r"(?<![A-Za-z])(?:AJS" + _ID_SEP + r"\d+|AS" + _ID_SEP + r"\d{2,}|AS\d{3,})", re.IGNORECASE)
# v9.7.115: digit ranges widened from {2,4}/{3,4} to {2,}/{3,} so a 5+-digit cohort ID redacts as a
# WHOLE token (the old {2,4} left 'AS-XXX' -> 'AS-XXX1', and 'AS-XXX' escaped entirely). Cohort is
# currently 3-digit, so this was a latent edge, not a live leak — but the SSOT should never leave a
# partial ID. Carve-outs unchanged: AS-48 (KNOWN_PUBLIC_AS), 1-digit AS-N, LAS-/CAS-, dashless AJS/AS15.
CAS_RE = re.compile(r"\b[MS]MC-\d+\b")
PENDING_RE = re.compile(r"\bPENDING-(?!XXX\b)[A-Z0-9]+", re.IGNORECASE)
PRIVATE_ID_RE = re.compile(
    r"(?<![A-Za-z])(?:AJS" + _ID_SEP + r"\d+|AS" + _ID_SEP + r"\d{2,}|AS\d{3,})|\bPENDING-(?!XXX\b)[A-Z0-9]+",
    re.IGNORECASE)
# v9.7.97: known PUBLIC natural-product names that collide with the cohort AS-NNN form. AS-48 is the
# bacteriocin enterocin AS-48 (MIBiG BGC0000489), public reference data — NOT a strain. No cohort or
# private strain is AS-48 (cohort uses AS-3xx/4xx/6xx/7xx), so exempting the exact token is leak-safe.
# Without this, the redactor corrupted "enterocin AS-48" -> "enterocin AS-XXX" in the shipped MIBiG index.
# Extend ONLY with verified public NP names that can never be a private strain ID.
KNOWN_PUBLIC_AS = {
    "AS-48",   # enterocin AS-48, a public natural-product name
    "AJS327",  # public MIBiG organism token retained in its validation-fixture filename
}
TEST_FILE_REF_RE = re.compile(r"\btest_[A-Za-z0-9_.-]+\.py\b", re.IGNORECASE)


def _inside_test_file_reference(text: str, start: int, end: int) -> bool:
    """True when an identifier is part of a shipped synthetic-test filename reference.

    Test files themselves are preserved so the in-tier suite remains executable. Their exact
    filenames may also appear in changelogs, inventories, and guides; rewriting only the prose
    reference creates a dangling locator without removing any private scientific content.
    """
    return any(m.start() <= start and end <= m.end() for m in TEST_FILE_REF_RE.finditer(text or ""))

def _as_sub(m):
    tok = m.group(0)
    return tok if tok in KNOWN_PUBLIC_AS else "AS-XXX"

def private_id_matches(t: str, *, as_only: bool = True) -> list[str]:
    """Return private/public-cut-prohibited identifiers using the release redaction SSOT.

    Includes AS-/AJS-style private strain tokens and PENDING-* placeholders. KNOWN_PUBLIC_AS
    natural-product carve-outs such as enterocin AS-48 are excluded. When as_only=False,
    SID identifiers are included too.
    """
    hits = []
    for m in PRIVATE_ID_RE.finditer(t or ""):
        tok = m.group(0)
        if tok not in KNOWN_PUBLIC_AS and not _inside_test_file_reference(t, m.start(), m.end()):
            hits.append(tok)
    if not as_only:
        hits += SID_RE.findall(t or "")
    return hits

def _private_as_count(t):
    """AS/PENDING matches that are genuine private-ID candidates (excludes KNOWN_PUBLIC_AS)."""
    return len(private_id_matches(t, as_only=True))
DEFAULT_FILES = ["mamey/source_scans.py", "mamey/master_workbook.py"]
TEXT_EXT = {".md",".csv",".cff",".txt",".json",".sh",".yaml",".yml",".toml",".cfg",".ini",".rst",".html"}
WHITELIST = {"SOURCE_CHECKSUMS_SHA256.txt", "TIER_MANIFEST.txt", "BUNDLE_FINGERPRINT.txt",
             # v9.7.88: the synthetic-ID allowlist must keep its literal synthetic AS-NNN entries
             # — redacting them to AS-XXX would break the test-leak guard that reads this file.
             "test_synthetic_ids.txt"}

def redact_text(t: str, as_only: bool=False) -> str:
    # as_only: scrub private AS-/AJS-/PENDING- IDs only; SID is public (Chevrette 2019) and is
    # legitimately retained in the code/sid tiers, so the sid-tier cut passes as_only=True.
    if not as_only:
        t = SID_RE.sub("SID-XXX", t)
    t = AS_RE.sub(
        lambda m: m.group(0) if _inside_test_file_reference(t, m.start(), m.end()) else _as_sub(m),
        t,
    )
    return PENDING_RE.sub("PENDING-XXX", t)

def redact_py(text: str, as_only: bool=False) -> str:
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (tokenize.TokenError, IndentationError):
        return redact_text(text, as_only)
    lines = text.splitlines(keepends=True); off=[0]
    for ln in lines: off.append(off[-1]+len(ln))
    pos = lambda r,c: off[r-1]+c
    edits=[]
    for tk in toks:
        # v9.7.251: Python 3.12+ splits f-strings into FSTRING_START / FSTRING_MIDDLE / FSTRING_END,
        # none of which is tokenize.STRING. A private ID inside an f-string literal was therefore
        # invisible to this redactor — a silent leak vector. Found by scrubbing the CODE tier and
        # measuring the residual: tools/build_cohort_precompute.py:90 kept "AS-XXX/AS-XXX" in an
        # f-string WARN message. FSTRING_MIDDLE carries only the literal text, never the {expr} parts,
        # so rewriting it cannot touch code.
        _FSTR = {getattr(tokenize, n) for n in ("FSTRING_MIDDLE",) if hasattr(tokenize, n)}
        if tk.type in (tokenize.COMMENT, tokenize.STRING) or tk.type in _FSTR:
            s,e = pos(*tk.start), pos(*tk.end); seg=text[s:e]; red=redact_text(seg, as_only)
            if red!=seg: edits.append((s,e,red))
    if not edits: return text
    out,last=[],0
    for s,e,red in sorted(edits): out.append(text[last:s]); out.append(red); last=e
    out.append(text[last:]); return "".join(out)

def _cas(t): return Counter(CAS_RE.findall(t))

def redact_file(path: Path, check_only=False, as_only=False) -> dict:
    # v9.7.371 fix: errors="ignore" silently DROPS any non-UTF-8 bytes on read. Since this
    # function conditionally overwrites the file in place a few lines below (after==before check),
    # a file containing even one stray non-UTF-8 byte would be silently rewritten with that byte
    # permanently removed -- a silent, irreversible content corruption during a leak-scrub pass
    # meant to prepare a PUBLIC release, not to mangle source content. Fail loudly instead: let a
    # genuine decode error surface (the tree-walk caller can then skip/report the file) rather than
    # quietly deleting bytes and writing back a corrupted file.
    before = path.read_text(encoding="utf-8")
    # JSON registries keyed by strain ID need key-collision-safe redaction: masking every
    # AS-number to "AS-XXX" collapses distinct object keys (last-write-wins, silent data loss —
    # hostile audit F1). For these, redact on the parsed structure and disambiguate colliding
    # masked keys (AS-XXX-1, AS-XXX-2, ...) so every record survives.
    if path.suffix == ".json" and _is_keyed_registry(before):
        after = _redact_json_registry(before, as_only)
    else:
        after = redact_py(before, as_only) if path.suffix==".py" else redact_text(before, as_only)
    cb,ca=_cas(before),_cas(after)
    if cb!=ca: raise AssertionError(f"{path}: redaction altered CAS stable-IDs. Refusing to write.")
    if as_only:
        n=_private_as_count(before)
    else:
        n=len(SID_RE.findall(before))+_private_as_count(before)
    # v9.7.371 fix: was a direct write_text() in-place overwrite of the SOURCE file, no
    # temp+replace step -- an interrupted write during a tree-wide redaction pass (this tool's
    # whole job) leaves a truncated file on disk with no signal besides a possibly-missed exit
    # code, and the tree's redaction state becomes silently inconsistent.
    if not check_only and after!=before: atomic_write_text(path, after)
    return {"file":str(path),"ids_redacted":n,"cas_preserved":sum(cb.values()),"changed":after!=before}


_KEYED_ID = re.compile(r"^(?:AJS-?\d+|AS-?\d{2,}|SID\d+|PENDING-[A-Z0-9]+)$", re.IGNORECASE)


def _is_keyed_registry(text: str) -> bool:
    """True if this looks like a JSON object with a top-level 'strains' (or similar) dict keyed
    by strain IDs — the structure vulnerable to AS-key collapse."""
    try:
        d = json.loads(text)
    except Exception:
        return False
    if not isinstance(d, dict):
        return False
    inner = d.get("strains", d)
    return isinstance(inner, dict) and any(_KEYED_ID.match(str(k)) for k in inner)


def _redact_json_registry(text: str, as_only: bool) -> str:
    """Redact a strain-keyed JSON registry without collapsing keys: mask each AS-key, and if
    two masked keys collide, append -1/-2/... to keep every record. Values are redacted with
    the normal text redactor. Recomputes n_strains to match the surviving record count."""
    d = json.loads(text)
    container_is_wrapped = isinstance(d, dict) and "strains" in d and isinstance(d["strains"], dict)
    strains = d["strains"] if container_is_wrapped else d
    new_strains = {}
    seen = {}
    for k, v in strains.items():
        # mask ANY private ID in the key (AS-numbers AND others like AS-XXX), matching the
        # plain redactor's coverage; then disambiguate collisions so records aren't collapsed.
        mk = redact_text(str(k), as_only).strip()
        if mk in seen:
            seen[mk] += 1
            mk = f"{mk}-{seen[mk]}"
        else:
            seen[mk] = 0
            if mk in new_strains:
                seen[mk] = 1
                mk = f"{mk}-1"
        vred = json.loads(redact_text(json.dumps(v), as_only))
        new_strains[mk] = vred
    if container_is_wrapped:
        d["strains"] = new_strains
        if "n_strains" in d:
            d["n_strains"] = len(new_strains)  # F1: recompute, never trust the stale field
        # v9.7.371 fix: this blanket safety-net pass was dead (`if False else d`, a classic
        # forgotten debug-disable -- nobody writes that pattern intentionally). The comment "keys
        # already handled" is true only for the strains dict's OWN keys/values (handled above);
        # any OTHER top-level key holding a nested dict/list (e.g. a "generated_by": {"source_files":
        # [...], "note": "..."} metadata block) carried private IDs straight through untouched --
        # confirmed live: a nested `generated_by.note` mentioning "AS-XXX" survived a full
        # _redact_json_registry() pass unredacted. Re-enabling this call is safe: redact_text() is
        # idempotent on already-masked tokens (e.g. "AS-XXX" contains no digits, so it can't
        # re-match AS_RE), and it operates on arbitrary JSON text exactly as it already does for
        # .py/.md files elsewhere in this module -- verified live this still preserves the
        # disambiguated "AS-XXX"/"AS-XXX-1" strains keys unchanged.
        d = json.loads(redact_text(json.dumps(d), as_only))
        # redact any remaining top-level string values (redundant with the pass above, kept as a
        # second explicit safety net for the common case)
        for tk, tv in list(d.items()):
            if isinstance(tv, str):
                d[tk] = redact_text(tv, as_only)
        out = d
    else:
        out = new_strains
    return json.dumps(out, indent=2)

def verify_cassettes_import(tree: Path) -> bool:
    import importlib; sys.path.insert(0,str(tree))
    for mod in ("mamey.mamey_cassettes","mamey.sapote_cassettes"):
        if mod in sys.modules: importlib.reload(sys.modules[mod])
        else: importlib.import_module(mod)
    return True

def audit_paths(tree: Path) -> list[str]:
    """v9.7.251: this redactor rewrites CONTENT, never PATHS. A scrubbed tier shipped
    `docs/reference/AS-XXX_AS-XXX_over_merge_decomposition.csv` — every row inside redacted, the strain
    IDs still in the filename, and repeated verbatim in TIER_MANIFEST.txt (which is a file list).
    Content-only scrubbing cannot see this. Report it; renaming is a human decision because references
    must move with the file."""
    import re as _re
    # BC2-AP-01 (v9.7.395): this pattern lacked re.IGNORECASE even though AS_RE (the near-identical
    # content-scrubbing pattern nine lines above, in this same file) has it. This function's own
    # docstring and the CHANGELOG.md v9.7.251 entry it cites both frame it as closing exactly the
    # "content-only scrubbing cannot see this" gap for a private strain ID leaked into a FILENAME —
    # but a lowercase/mixed-case filename (e.g. "as-705_notes_backup.csv", plausible casual
    # authoring or an OS that lowercases on copy) silently escaped this specific detector while an
    # uppercase file with the identical strain ID was correctly caught. Reproduced: a tree with both
    # "AS-705_....csv" and "as-705_...backup.csv" only flagged the uppercase one.
    pat = _re.compile(r"(?<![A-Za-z])(?:AJS-?\d+|AS-\d{2,}|AS\d{3,})", _re.IGNORECASE)
    known_public_upper = {k.upper() for k in KNOWN_PUBLIC_AS}
    hits = []
    for p in sorted(tree.rglob("*")):
        if not p.is_file() or "__pycache__" in p.parts:
            continue
        if "tests" in p.parts:
            continue
        m = pat.search(p.name)
        # case-insensitive KNOWN_PUBLIC_AS membership too, so the re.IGNORECASE widening above
        # cannot newly false-positive on a differently-cased mention of a carve-out like "AS-48"
        # (enterocin, a peptide name, not a strain) or "AJS327".
        if m and m.group(0).upper() not in known_public_upper:
            hits.append(str(p.relative_to(tree)))
    return hits


def _walk(tree: Path):
    """Yield non-test documentation/configuration text for release-time redaction.

    Python is intentionally excluded. Its strings may be executable data rather than prose;
    genericizing those values belongs in reviewed source patches with behavioral tests.
    """
    for p in sorted(tree.rglob("*")):
        if p.is_file() and p.suffix.lower() in TEXT_EXT and p.name not in WHITELIST and "__pycache__" not in p.parts and "tests" not in p.parts:
            yield p

def main(argv=None):
    ap=argparse.ArgumentParser(description="CAS-safe SID+AS redaction for public bundle tiers.")
    ap.add_argument("--tree",required=True); ap.add_argument("--files",nargs="*",default=None)
    ap.add_argument("--walk",action="store_true",help="walk whole tree (default when --files absent)")
    ap.add_argument("--all-py",action="store_true",help="(legacy) walk every *.py; now AST-safe")
    ap.add_argument("--check-only",action="store_true")
    ap.add_argument("--as-only",action="store_true",help="count/verify only private AS IDs (SID stays — it's public)")
    a=ap.parse_args(argv); tree=Path(a.tree).resolve()
    if a.files is not None: targets=[tree/r for r in a.files]
    elif a.all_py: targets=[p for p in tree.rglob("*.py") if "__pycache__" not in p.parts]
    else: targets=list(_walk(tree))
    total=0
    for p in targets:
        if not p.exists(): emit(f"  [skip] {p} (absent)"); continue
        r=redact_file(p,check_only=a.check_only,as_only=a.as_only); total+=r["ids_redacted"]
        if r["changed"] or r["ids_redacted"]:
            emit(f"  [{'check' if a.check_only else 'redact'}] {p.relative_to(tree)} -> {r['ids_redacted']} ID(s)")
    try:
        verify_cassettes_import(tree)
        emit(f"  [ok] cassettes import cleanly; {total} strain ID(s) {'found' if a.check_only else 'redacted'}, CAS intact")
    except Exception as e:
        emit(f"  [FAIL] cassette import broke: {e}"); return 1
    # In check-only mode, surviving strain IDs are a gate failure (nonzero exit) so this can be
    # wired into make_public_tier.sh as an independent verification of the inline scrub.
    if a.check_only and total > 0:
        emit(f"  [FAIL] {total} strain ID(s) survive in this tree — public cut would leak")
        return 2
    return 0

if __name__=="__main__": raise SystemExit(main())
