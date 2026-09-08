#!/usr/bin/env python3
"""seal_sweep.py  (candidate patch F10)

Seal-time sweep for stale or contradictory prose, and for stale version citations, across the
doc surfaces a reader hits first. Two independent checks:

  1. Banned-phrase sweep — the same PROHIBITED_NEWEST_ENTRY_PHRASES set F6
     (tests/test_newest_changelog_composition_prose_v97406.py) defined for the newest CHANGELOG
     entry, reused here verbatim and applied to a wider surface: the newest CHANGELOG entry
     (bounded exactly as F6 bounds it — historical entries are evidence and are never scanned),
     plus every README*.md, *_START_HERE.md, and CURRENT_DOCS_INDEX.md at the bundle root
     (scanned in full — these are not versioned-entry documents, so there is no historical region
     to exempt).

  2. Version-citation check — every *_START_HERE.md must cite the current version recorded in
     BUILD_STAMP.txt (the literal "X.Y.Z" version string appears at least once in the file). A
     START_HERE file a reader opens first, silently still describing an old build, is exactly the
     stale-prose failure mode this sweep exists to catch — and this check is not hypothetical: run
     against the real v9.7.405 sealed tree, it finds FIGURES_START_HERE.md citing no "9.7.405"
     anywhere (see this patch's own card for the observed finding).

Typed findings only — list[dict], each {"path", "code", "detail"}; never a bare string. Report
mode (default) prints findings and always exits 0 — safe for a human to run and read. --check
flips only the exit code: 1 if any finding is present, 0 if clean; findings are printed either
way, so scripting on the exit code never has to also re-parse output to see why it failed.

  python tools/seal_sweep.py [--root PATH] [--check] [--json]

Independent of F7 (owner-governed release-tag work) — this sweeps prose and version citations
only, no release-tag logic.
"""
import argparse
import json
import re
import sys
from pathlib import Path

# Reused verbatim from F6 (tests/test_newest_changelog_composition_prose_v97406.py) — composition-
# only or contradictory prose that must never survive into a sealed newest-entry or front door.
PROHIBITED_PHRASES = (
    "CANDIDATE — not a seal",
    "absent by defined-symbol",
    "TO BE FILLED",
    "PENDING, not yet in this tree",
)

# F6's exact newest-entry header pattern, reused so the two tools agree on what "newest entry" means.
ENTRY_HEADER = re.compile(r"(?m)^# v\d+\.\d+\.\d+[^\n]*$")
VERSION_LINE = re.compile(r"(?m)^version\s*=\s*(\S+)\s*$")

DOC_SURFACE_GLOBS = ("README*.md", "*_START_HERE.md", "CURRENT_DOCS_INDEX.md")


def newest_changelog_entry(text):
    """F6's exact bounding logic, reused: only the first versioned entry is eligible to describe
    the tree being sealed; historical entries are evidence and are never scanned. Fails closed
    (raises) on malformed input, mirroring F6's own contract — callers here catch it and turn it
    into a typed finding rather than letting the sweep crash."""
    headers = list(ENTRY_HEADER.finditer(text))
    if not headers or headers[0].start() != 0:
        raise ValueError("CHANGELOG must start with a versioned '# vX.Y.Z' entry")
    end = headers[1].start() if len(headers) > 1 else len(text)
    return text[:end]


def _read_build_version(root):
    stamp = root / "BUILD_STAMP.txt"
    if not stamp.exists():
        return None
    m = VERSION_LINE.search(stamp.read_text(encoding="utf-8"))
    return m.group(1) if m else None


def sweep_changelog(root):
    """CHANGELOG.md, newest entry only. One typed BANNED_PHRASE finding per phrase found."""
    path = root / "CHANGELOG.md"
    if not path.exists():
        return [{"path": "CHANGELOG.md", "code": "MISSING_CHANGELOG",
                  "detail": "no CHANGELOG.md at bundle root"}]
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        entry = newest_changelog_entry(text)
    except ValueError as exc:
        return [{"path": "CHANGELOG.md", "code": "MALFORMED_CHANGELOG", "detail": str(exc)}]
    return [{"path": "CHANGELOG.md", "code": "BANNED_PHRASE",
              "detail": f"newest entry contains {phrase!r}"}
            for phrase in PROHIBITED_PHRASES if phrase in entry]


def sweep_doc_surface(root):
    """README*.md, *_START_HERE.md, CURRENT_DOCS_INDEX.md at bundle root — scanned in full (no
    bounded region; these are not versioned-entry documents), banned-phrase sweep only."""
    findings = []
    seen = set()
    for pattern in DOC_SURFACE_GLOBS:
        for path in sorted(root.glob(pattern)):
            if not path.is_file() or path in seen:
                continue
            seen.add(path)
            text = path.read_text(encoding="utf-8", errors="replace")
            for phrase in PROHIBITED_PHRASES:
                if phrase in text:
                    findings.append({"path": path.name, "code": "BANNED_PHRASE",
                                      "detail": f"contains {phrase!r}"})
    return findings


def sweep_start_here_version_citation(root):
    """Every *_START_HERE.md at bundle root must cite the current BUILD_STAMP.txt version."""
    version = _read_build_version(root)
    if version is None:
        return [{"path": "BUILD_STAMP.txt", "code": "MISSING_BUILD_STAMP",
                  "detail": "no BUILD_STAMP.txt / no version= line at bundle root; "
                            "cannot check citation"}]
    findings = []
    for path in sorted(root.glob("*_START_HERE.md")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if version not in text:
            findings.append({"path": path.name, "code": "VERSION_STALE",
                              "detail": f"does not cite current version {version!r} "
                                        f"(from BUILD_STAMP.txt)"})
    return findings


# CLAUDE_409 — package path-scrub QA (DEEP_AUDIT3 F1/F2/F5). A sealed package handed to a
# collaborator must not embed the operator's absolute home-directory (<home>/<user>/) layout.
# Reuse the ONE detector in the tree that already recognises those paths — the PERSONAL regex
# in tools/public_release_audit.py — so the two stay in lockstep. Fall back to a byte-identical
# literal only if that module (which pulls in the mamey package) cannot be imported in a bare
# context, so this sweep still runs standalone.
_PKG_TEXT_SUFFIXES = (".json", ".md", ".txt", ".csv", ".tsv")


def _personal_path_regex():
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from public_release_audit import PERSONAL as _P
        return _P
    except Exception:
        # generic home-directory layouts only (built from parts so no literal path token ships in
        # this file); named workspaces come from public_release_audit.PERSONAL when importable.
        _roots = ("Users", "home")
        return re.compile("|".join(rf"/{r}/[^/]+/" for r in _roots))


def scan_package_personal_paths(package_dir):
    """Advisory scan of a sealed package's shipped text/JSON for embedded operator paths.

    Returns typed findings (list[dict] {"path","code","detail"}) — the detail names the file
    and line but never echoes the matched path itself, so the finding does not re-leak it.
    Advisory by design: this surfaces a package with operator paths BEFORE it is shared; it
    never runs inside (or blocks) a normal strain run.
    """
    root = Path(package_dir)
    regex = _personal_path_regex()
    findings = []
    if not root.is_dir():
        return [{"path": str(package_dir), "code": "PACKAGE_NOT_FOUND",
                 "detail": "not a directory; nothing scanned"}]
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        if path.suffix.lower() not in _PKG_TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        # PERSONAL's [^/]+ classes span newlines, so scan per line — matching how
        # public_release_audit.py applies the same regex.
        for lineno, line in enumerate(text.splitlines(), 1):
            if regex.search(line):
                rel = path.relative_to(root)
                findings.append({
                    "path": str(rel), "code": "PERSONAL_PATH_IN_PACKAGE",
                    "detail": f"line {lineno} embeds an operator path "
                              "(<home>/<user>/) — scrub before sharing"})
                break  # one finding per file is enough to flag it
    return findings


def run_sweep(root, package=None):
    """The full sweep, as a plain function so it is directly testable without shelling out.

    ``package`` (optional): also run the advisory package path-scrub (CLAUDE_409) over that
    sealed package directory, appending PERSONAL_PATH_IN_PACKAGE findings.
    """
    findings = []
    findings += sweep_changelog(root)
    findings += sweep_doc_surface(root)
    findings += sweep_start_here_version_citation(root)
    if package:
        findings += scan_package_personal_paths(package)
    return findings


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".", help="bundle root to sweep (default: cwd)")
    ap.add_argument("--package", default=None,
                     help="also advisory-scan this sealed package dir for embedded operator "
                          "paths (<home>/<user>/) before sharing (CLAUDE_409)")
    ap.add_argument("--check", action="store_true",
                     help="exit 1 if any finding is present (default: report only, exit 0)")
    ap.add_argument("--json", action="store_true", help="emit findings as JSON instead of lines")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    findings = run_sweep(root, package=args.package)

    if args.json:
        sys.stdout.write(json.dumps(findings, indent=2) + "\n")
    elif not findings:
        sys.stdout.write(
            "seal_sweep: clean — no banned phrases, no stale START_HERE version citations.\n")
    else:
        sys.stdout.write(f"seal_sweep: {len(findings)} finding(s)\n")
        for f in findings:
            sys.stdout.write(f"  [{f['code']}] {f['path']}: {f['detail']}\n")

    if args.check and findings:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
