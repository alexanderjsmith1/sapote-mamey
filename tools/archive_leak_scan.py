#!/usr/bin/env python3
"""
archive_leak_scan.py — private-ID leak guard for the *contents* of committed archives.

WHY THIS EXISTS. The leak-audit chain has a coverage hole for archives:
  * redact_public_tier.py / the tree AS-mention inventory scan TEXT_EXT files only —
    `.zip`, `.docx`, `.pptx` are not in TEXT_EXT, so their readable contents are never scanned.
  * preflight_zip_hygiene.py DOES open zips, but only for cache/hygiene artifacts
    (.pytest_cache, __pycache__, .pyc, .DS_Store, large/hidden files) — it does not look at
    identifiers inside members.
  * audit_public_cut.py DOES hunt private IDs inside an archive, but only `.xlsx`, and only when
    manually pointed at one workbook (it decompresses xlsx via openpyxl; it is the merged-master
    Excel auditor).

So a real strain identifier (AS-###/AJS…/PENDING-…) or a held-cohort codename buried inside a
committed `.zip` fixture (antiSMASH result zips), a `.docx`/`.pptx` deliverable, or any nested
archive would pass every automated leak gate. That is exactly the class of leak audit_public_cut.py
was built to stop for xlsx (two real incidents: a full AS-### strain line, and the held-cohort
codename, both in prose a row-filter never touched). This tool generalizes that check to every
zip-family archive in the tree.

WHAT IT CHECKS (per readable member of every archive found under ROOT)
  1. Private identifiers — via the release-redaction SSOT `redact_public_tier.private_id_matches`
     (AS-/AJS-/PENDING- tokens; SID only with --include-sid; KNOWN_PUBLIC_AS carve-outs like
     enterocin AS-48 are excluded automatically, because the SSOT excludes them). Always checked,
     defense-in-depth, matching audit_public_cut.py's always-on static AS/AJS check — independent
     of the cut-time AS_SCRUB policy toggle.
  2. Held-cohort prose phrases — the "(AS held)" family (sibling pattern to audit_public_cut.py).
  3. Denylist terms — from tools/release_denylist.txt if present (same file audit_public_cut reads);
     absent file is fine.

Nested archives (a `.zip` inside a `.zip`, common for antiSMASH result bundles) are recursed into
up to --max-depth. Binary members (images, .pyc, fonts) are skipped; textual/XML members
(office-XML parts, .txt/.csv/.json/.gbk/.fasta/…) are decoded and scanned — office prose lives in
the zipped XML parts, which is precisely where the xlsx incidents hid.

USAGE
  python tools/archive_leak_scan.py [ROOT] [--include-sid] [--json] [--max-depth N]
      [--ext .zip,.xlsx,…] [--denylist tools/release_denylist.txt]

Exit 0 = CLEAN (no private-ID/held/denylist hit in any archive member). 1 = leak found. 2 = error.

This is a builder tool (no gate-registry row); pair it with test_archive_leak_scan.py.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

import argparse
import io
import json
import os
import re
import sys
import zipfile
from pathlib import Path

# --- private-ID SSOT: reuse the enforced redactor's definition so this can't drift ----------
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
try:
    from redact_public_tier import private_id_matches as _private_id_matches
except Exception as exc:  # pragma: no cover - the SSOT should always be present in-tier
    sys.stderr.write(f"archive_leak_scan: cannot import private-ID SSOT (redact_public_tier): {exc}\n")
    raise

# Sibling of audit_public_cut.py's HELD_PHRASES (kept local so this tool needs no openpyxl to
# scan a .zip; audit_public_cut.py hard-requires openpyxl at import).
HELD_PHRASES = re.compile(r"\(AS held\)|AS held|research \(AS\) tier|AS[\s_-]?tier held", re.I)

# Zip-family archive extensions (all are zip containers). tar/gz are out of scope for now.
DEFAULT_ARCHIVE_EXT = {".zip", ".xlsx", ".xlsm", ".xltx", ".docx", ".pptx", ".jar", ".whl"}

# Member extensions worth decoding as text. Office-XML parts are .xml/.rels; antiSMASH bundles
# carry .gbk/.json/.txt/.csv/.fasta/.gff. Everything else is treated as binary and skipped unless
# it decodes cleanly as mostly-printable text (extensionless members).
TEXT_MEMBER_EXT = {
    ".xml", ".rels", ".txt", ".csv", ".tsv", ".json", ".md", ".rst", ".html", ".htm",
    ".gbk", ".gb", ".gbff", ".genbank", ".fasta", ".fa", ".faa", ".fna", ".gff", ".gff3",
    ".cff", ".yaml", ".yml", ".toml", ".cfg", ".ini", ".log", ".tab", ".bed", ".nwk", ".newick",
}
# Members never worth decoding (fast skip).
BINARY_MEMBER_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".ico", ".pdf", ".pyc", ".pyo",
    ".so", ".dylib", ".dll", ".zip", ".gz", ".bz2", ".xz", ".7z", ".woff", ".woff2", ".ttf",
    ".otf", ".eot", ".xlsx", ".xlsm", ".docx", ".pptx", ".jar", ".whl", ".db", ".sqlite",
}


def _load_denylist(path: str | None) -> list[str]:
    p = Path(path) if path else (_HERE / "release_denylist.txt")
    terms: list[str] = []
    try:
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                t = line.strip()
                if t and not t.startswith("#"):
                    terms.append(t)
    except FileNotFoundError:
        # optional terms file absent -> scan proceeds with no extra private-ID terms
        terms = []
    return terms


def _looks_textual(name: str, raw: bytes) -> bool:
    """Decide whether a member is worth decoding+scanning as text."""
    ext = os.path.splitext(name)[1].lower()
    if ext in TEXT_MEMBER_EXT:
        return True
    if ext in BINARY_MEMBER_EXT:
        return False
    # Unknown/extensionless: sample the head; treat as text if it's mostly printable and has no NULs.
    head = raw[:4096]
    if b"\x00" in head:
        return False
    if not head:
        return False
    printable = sum(1 for b in head if 9 <= b <= 13 or 32 <= b <= 126 or b >= 128)
    return (printable / len(head)) >= 0.90


def _scan_text(text: str, *, as_only: bool, denylist: list[str]) -> list[dict]:
    """Run the three checks over one decoded member. Returns finding dicts (no location yet)."""
    found: list[dict] = []
    for tok in sorted(set(_private_id_matches(text, as_only=as_only))):
        # short snippet around first occurrence for the report
        i = text.find(tok)
        snip = text[max(0, i - 30): i + len(tok) + 30].replace("\n", " ")
        found.append({"kind": "private_identifier", "token": tok, "snippet": snip.strip()})
    if HELD_PHRASES.search(text):
        m = HELD_PHRASES.search(text)
        i = m.start()
        found.append({"kind": "held_phrase", "token": m.group(0),
                      "snippet": text[max(0, i - 20): i + 40].replace("\n", " ").strip()})
    low = text.lower()
    for term in denylist:
        if term.lower() in low:
            i = low.find(term.lower())
            found.append({"kind": "denylist_term", "token": term,
                          "snippet": text[max(0, i - 20): i + len(term) + 20].replace("\n", " ").strip()})
    return found


def scan_archive(path, *, as_only: bool = True, denylist: list[str] | None = None,
                 max_depth: int = 3) -> list[dict]:
    """Scan one archive file's readable members (recursing into nested archives).

    Returns a list of finding dicts: {archive, member, kind, token, snippet}. Empty = clean.
    Mirrors preflight_zip_hygiene.scan()'s shape (takes a path, returns structured findings).
    """
    denylist = denylist if denylist is not None else _load_denylist(None)
    findings: list[dict] = []
    try:
        data = Path(path).read_bytes()
    except Exception as exc:
        return [{"archive": str(path), "member": "", "kind": "read_error",
                 "token": type(exc).__name__, "snippet": str(exc)[:80]}]
    findings.extend(_scan_zip_bytes(data, str(path), as_only=as_only, denylist=denylist,
                                    depth=0, max_depth=max_depth))
    return findings


def _scan_zip_bytes(data: bytes, label: str, *, as_only: bool, denylist: list[str],
                    depth: int, max_depth: int) -> list[dict]:
    findings: list[dict] = []
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        return [{"archive": label, "member": "", "kind": "bad_zip",
                 "token": "BadZipFile", "snippet": "not a readable zip container"}]
    with zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = info.filename
            try:
                raw = zf.read(info)
            except Exception as exc:
                findings.append({"archive": label, "member": name, "kind": "member_read_error",
                                 "token": type(exc).__name__, "snippet": str(exc)[:80]})
                continue
            ext = os.path.splitext(name)[1].lower()
            # Recurse into nested archives.
            if ext in DEFAULT_ARCHIVE_EXT:
                if depth < max_depth:
                    findings.extend(_scan_zip_bytes(raw, f"{label}!{name}", as_only=as_only,
                                                    denylist=denylist, depth=depth + 1,
                                                    max_depth=max_depth))
                else:
                    # v9.7.395: previously fell through to _looks_textual(), which treats every
                    # DEFAULT_ARCHIVE_EXT extension as binary (they're all also listed in
                    # BINARY_MEMBER_EXT) and silently `continue`s -- a nested archive beyond
                    # --max-depth was skipped with ZERO signal that it was never scanned, so a
                    # real leak inside it would report as a clean scan. This tool exists
                    # specifically to close silent leak-audit coverage holes (see the module
                    # docstring); truncation must be visible, not silent.
                    findings.append({"archive": label, "member": name, "kind": "depth_limit_truncated",
                                     "token": "", "snippet": f"nested archive not scanned (depth "
                                     f"{depth + 1} exceeds --max-depth {max_depth}); increase "
                                     f"--max-depth to scan its contents"})
                continue
            if not _looks_textual(name, raw):
                continue
            text = raw.decode("utf-8", errors="ignore")
            for f in _scan_text(text, as_only=as_only, denylist=denylist):
                f2 = {"archive": label, "member": name}
                f2.update(f)
                findings.append(f2)
    return findings


def scan_tree(root, *, as_only: bool = True, archive_ext=None, denylist=None,
              max_depth: int = 3) -> tuple[list[dict], int]:
    """Walk ROOT for archive files and scan each. Returns (findings, archives_scanned)."""
    root = Path(root)
    archive_ext = archive_ext or DEFAULT_ARCHIVE_EXT
    denylist = denylist if denylist is not None else _load_denylist(None)
    findings: list[dict] = []
    n = 0
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        if "__pycache__" in p.parts:
            continue
        if p.suffix.lower() not in archive_ext:
            continue
        n += 1
        findings.extend(scan_archive(p, as_only=as_only, denylist=denylist, max_depth=max_depth))
    return findings, n


def _write_report(findings, n_archives, root, as_only):
    real = [f for f in findings if f["kind"] in ("private_identifier", "held_phrase", "denylist_term")]
    errs = [f for f in findings if f["kind"] not in ("private_identifier", "held_phrase", "denylist_term")]
    clean = not real
    emit(f"archive leak scan: {'CLEAN' if clean else 'LEAK'} "
          f"({n_archives} archive(s) under {root}; {len(real)} leak finding(s), "
          f"{len(errs)} read/parse note(s); as_only={as_only})")
    if real:
        by = {}
        for f in real:
            by.setdefault(f["kind"], []).append(f)
        for kind, items in by.items():
            emit(f"\n  {kind} ({len(items)}):")
            for it in items[:40]:
                emit(f"    {it['archive']}!{it['member']}: {it['token']}  «{it['snippet']}»")
            if len(items) > 40:
                emit(f"    … and {len(items) - 40} more")
    if errs:
        for it in errs[:10]:
            emit(f"  [note] {it['archive']}!{it.get('member','')}: {it['kind']} ({it['token']})")
    return clean


def main(argv=None):
    ap = argparse.ArgumentParser(description="Private-ID leak guard for archive contents "
                                             "(.zip/.xlsx/.docx/.pptx and nested archives).")
    ap.add_argument("root", nargs="?", default=".", help="tree to scan (default: .)")
    ap.add_argument("--include-sid", action="store_true",
                    help="also flag SID identifiers (as_only=False). Default: SID is public, not flagged.")
    ap.add_argument("--json", action="store_true", help="emit findings as JSON")
    ap.add_argument("--max-depth", type=int, default=3, help="nested-archive recursion cap (default 3)")
    ap.add_argument("--ext", help="comma-separated archive extensions to override the default set")
    ap.add_argument("--denylist", help="path to a denylist file (default: tools/release_denylist.txt)")
    args = ap.parse_args(argv)

    as_only = not args.include_sid
    archive_ext = ({e if e.startswith(".") else "." + e for e in args.ext.lower().split(",")}
                   if args.ext else DEFAULT_ARCHIVE_EXT)
    denylist = _load_denylist(args.denylist)

    findings, n = scan_tree(args.root, as_only=as_only, archive_ext=archive_ext,
                            denylist=denylist, max_depth=args.max_depth)
    real = [f for f in findings if f["kind"] in ("private_identifier", "held_phrase", "denylist_term")]

    if args.json:
        emit(json.dumps({"clean": not real, "archives_scanned": n, "findings": findings}, indent=2))
    else:
        _write_report(findings, n, args.root, as_only)
    return 1 if real else 0


if __name__ == "__main__":
    sys.exit(main())
