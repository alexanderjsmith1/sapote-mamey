#!/usr/bin/env python3
"""gen_release_manifest.py — regenerate the volatile fields of RELEASE_MANIFEST.md from live truth.

WHY THIS EXISTS (audit v9.7.95, P-A3 root cause). RELEASE_MANIFEST.md is hand-maintained: each release
bumps the header and the body rots. v9.7.95 shipped with a body still describing v9.7.57 (831 tests,
engine 1.9.64, build 20260619c) under a 9.7.95 header. This tool makes the volatile fields *derived*,
not typed: bundle/engine/stamp come from the same source-of-truth files sync_version reads, and the
test-count + gate fields come from the in-tier pytest summary the cut already produces.

It edits ONLY a fixed set of self-describing fields via anchored regexes; it never touches prose,
the four-tier table, the historical change snapshot, or any other content. Same UX as sync_version:

    python3 tools/gen_release_manifest.py --check        # report drift, exit 1 if any (CI/cut gate)
    python3 tools/gen_release_manifest.py --apply        # rewrite in place
    # optional, to refresh the test-count + gate-test fields too:
    python3 tools/gen_release_manifest.py --apply --pytest-log /tmp/_tier_pytest.log
    python3 tools/gen_release_manifest.py --apply --tests-passed 1409 --tests-skipped 91

Close-out contract (v9.7.405, learned the hard way): --fixed-point REFUSES a red pytest log, and
the definitive log is red *only* because the manifest-freshness tests fail until the manifest is
applied. So the sequence is: (1) run the suite alone; (2) `--fixed-point --tests-passed N
--tests-skipped M` with that run's measured counts as the seed (it converges by re-running the
manifest-reading subset); (3) run the suite once more, green, and bind that log with
`--apply --pytest-log`. Three runs, not one. Regenerate every generated surface (command catalog,
deliverables menu, tools inventory) AFTER sync_version, never before — they embed the version.

Truth sources (read, never written): mamey/__init__.py (engine), CITATION.cff (bundle), BUILD_STAMP.txt
(stamp). Run from the bundle root, or pass --root.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse
import datetime as dt
import pathlib
import re
import subprocess
import sys

TOOLS_DIR = pathlib.Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
from check_tier_parity import OPTIONAL_PROMOTION_TIERS, REQUIRED_TIERS, tier_of


def read_truth(root: pathlib.Path):
    init = (root / "mamey" / "__init__.py").read_text(encoding="utf-8")
    engine = re.search(r'__version__\s*=\s*"([^"]+)"', init).group(1)
    cff = (root / "CITATION.cff").read_text(encoding="utf-8")
    m = re.search(r"(?m)^\s*version:\s*['\"]?(\d+\.\d+\.\d+[a-z]?)", cff)
    if not m:
        raise ValueError(f"Cannot parse bundle version from CITATION.cff at {root / 'CITATION.cff'}")
    bundle = m.group(1)
    stamp = ""
    sp = root / "BUILD_STAMP.txt"
    if sp.exists():
        ms = re.search(r"(?m)^build=(.+)$", sp.read_text(encoding="utf-8"))
        stamp = ms.group(1).strip() if ms else ""
    return engine, bundle, stamp


def counts_from_log(log_path: pathlib.Path):
    """Parse a pytest summary line like '1409 passed, 91 skipped in 184s'.

    v9.7.250 — FAIL CLOSED on a red log. This function used to happily return
    ``(2906, 152)`` from a run whose summary read ``5 failed, 2906 passed`` and the
    caller would stamp those counts into the release manifest. A release manifest
    that records the pass count of a failing suite is worse than one that records
    nothing: it looks like evidence. Caught during the v9.7.250 cut, when the
    protocol's own step 7 was fed a log from step 4's first (red) run.
    """
    txt = log_path.read_text(encoding="utf-8", errors="ignore")

    red = []
    for kind in ("failed", "error", "errors"):
        m = re.search(rf"(\d+)\s+{kind}\b", txt)
        if m and int(m.group(1)) > 0:
            red.append(f"{m.group(1)} {kind}")
    if red:
        raise SystemExit(
            f"gen_release_manifest: refusing to read counts from a failing pytest log "
            f"({log_path}): {', '.join(red)}. Fix the suite, re-run it, and pass the green log. "
            f"A manifest that records the pass count of a red run looks like evidence."
        )

    # v9.7.410 hostile audit: counts come ONLY from pytest's own final summary line — the one that
    # ends `in <seconds>s` (optionally `(h:mm:ss)`), with or without the `=====` rule. Before this,
    # `(\d+)\s+passed` was searched over the whole file, so a log consisting of the prose
    # "Note: 7783 passed, 0 failed" was stamped into the manifest as a receipt-bound green run —
    # exactly the restatement the --pytest-log path exists to prevent. The LAST summary wins
    # (a log that captured a red run and then a green re-run is refused above anyway).
    summary = None
    for line in txt.splitlines():
        if _PYTEST_SUMMARY_RE.search(line):
            summary = line
    if summary is None:
        raise SystemExit(
            f"gen_release_manifest: {log_path} carries no pytest summary line "
            f"('N passed[, M skipped] in <seconds>s'); pass the complete log of a real run, not a note."
        )
    p = re.search(r"(\d+)\s+passed\b", summary)
    s = re.search(r"(\d+)\s+skipped\b", summary)
    return (int(p.group(1)) if p else None, int(s.group(1)) if s else 0)


# pytest's terminal summary: `7783 passed, 1013 skipped, 30 warnings in 324.57s (0:05:24)` under
# -q, or the same wrapped in `=====` rules without -q. `\bin\s+\d` anchors it to a real run.
_PYTEST_SUMMARY_RE = re.compile(r"\b\d+\s+passed\b.*\bin\s+\d+(?:\.\d+)?s\b")


def date_from_stamp(stamp: str) -> str:
    """Return the pinned YYYY-MM-DD cut date encoded by a build stamp.

    Accepted shape: `<YYYYMMDD>v<digits><one letter>` — e.g. `20260902v97405a`. A stamp such as
    `20200101a` (no `v<digits>`) is rejected on purpose; tests should build stamps with
    `tests/_fixtures.py::stamp()` rather than hand-writing them (v9.7.405 note).
    """
    match = re.fullmatch(r"(\d{8})v\d+[a-z]", stamp)
    if not match:
        raise ValueError(f"Cannot derive cut date from build stamp: {stamp!r}")
    return dt.datetime.strptime(match.group(1), "%Y%m%d").date().isoformat()


def release_tier_count(tier_zip_names=()):
    """Derive manifest prose from the parity gate's tier sets and supplied archives."""
    labels = {tier_of(name) for name in tier_zip_names}
    promotions = labels & OPTIONAL_PROMOTION_TIERS
    return len(REQUIRED_TIERS) + len(promotions)


def tier_count_word(count):
    words = {4: "four", 5: "five"}
    try:
        return words[count]
    except KeyError as exc:
        raise ValueError(f"No release-manifest word for tier count {count}") from exc


def build_rules(engine, bundle, stamp, passed, skipped, tier_zip_names=()):
    """(label, compiled_pattern, replacement) — anchored to self-describing fields only."""
    cut_date = date_from_stamp(stamp)
    rules = [
        ("cut/build date",
         re.compile(r"(\*\*Cut/build date:\*\* )\d{4}-\d{2}-\d{2}"),
         rf"\g<1>{cut_date}"),
        ("header bundle version",
         re.compile(r"(\*\*Bundle version:\*\* `sapote-mamey-v)\d+\.\d+\.\d+[a-z]?(`)"),
         rf"\g<1>{bundle}\g<2>"),
        ("header engine",
         re.compile(r"(\*\*Engine:\*\* Mamey v)\d+\.\d+\.\d+[a-z]?"),
         rf"\g<1>{engine}"),
        ("header build stamp",
         re.compile(r"(\*\*Build stamp:\*\* )\S+"),
         rf"\g<1>{stamp}"),
        ("shared tier-count/build-stamp line",
         re.compile(r"All (?:four|five) tiers share build stamp `[^`]+`\."),
        f"All {tier_count_word(release_tier_count(tier_zip_names))} tiers share build stamp `{stamp}`."),
        ("sync_version row",
         re.compile(r"(\| `sync_version --check` \| PASS \(engine )\d+\.\d+\.\d+[a-z]?(, bundle )\d+\.\d+\.\d+[a-z]?(\) \|)"),
         rf"\g<1>{engine}\g<2>{bundle}\g<3>"),
        ("Gate 1 anchors",
         re.compile(r"(All tracked version anchors at v)\d+\.\d+\.\d+[a-z]?( / Mamey )\d+\.\d+\.\d+[a-z]?(\.)"),
         rf"\g<1>{bundle}\g<2>{engine}\g<3>"),
        ("Gate 2 anchor",
         re.compile(r"(`MAMEY_CHATGPT_EXECUTION_PROMPT.md` updated to v)\d+\.\d+\.\d+[a-z]?(\.)"),
         rf"\g<1>{bundle}\g<2>"),
        ("footer",
         re.compile(r"(\| Sapote-Mamey Bundle v)\d+\.\d+\.\d+[a-z]?( \|)"),
         rf"\g<1>{bundle}\g<2>"),
        ("generated date",
         re.compile(r"(\*Generated: )\d{4}-\d{2}-\d{2}( \| Sapote-Mamey Bundle v)"),
         rf"\g<1>{cut_date}\g<2>"),
    ]
    return rules


def ensure_test_evidence_row(text: str, passed: int | None, skipped: int | None,
                             provenance: str = "receipt-bound log"):
    """Return text with one canonical full-suite evidence row, labelled by provenance.

    Older manifests have no test-count row at all. Merely warning about the
    absent row leaves the release unable to bind the final suite. Insert the
    row deterministically into the validation table, or replace the existing
    canonical row. A missing validation-table anchor is a hard error.
    """
    if passed is None:
        raise ValueError("A release manifest requires a parsed pytest passed count")
    skipped = 0 if skipped is None else skipped
    # v9.7.404: the row used to hardcode "receipt-bound log" even when the counts arrived
    # through --tests-passed/--tests-skipped, i.e. typed by a human with no log bound at all.
    # A release artifact must not describe the provenance of a number it does not have; the
    # house rule is that a metric travels with how it was obtained.
    canonical = (
        f"| Full pytest suite | PASS ({passed} passed, {skipped} skipped; "
        f"{provenance}) |"
    )
    row_pattern = re.compile(r"(?m)^\| Full pytest suite \|.*\|$")
    if row_pattern.search(text):
        return row_pattern.sub(canonical, text), canonical

    anchor_pattern = re.compile(
        r"(?m)^##\s+Validation status\s*\r?\n(?:\r?\n)*"
        r"\|\s*Gate\s*\|\s*Status\s*\|\r?\n"
        r"\|\s*:?-{3,}:?\s*\|\s*:?-{3,}:?\s*\|$"
    )
    matches = list(anchor_pattern.finditer(text))
    if len(matches) != 1:
        raise ValueError(
            "Cannot insert full-suite evidence: validation table anchor is missing or ambiguous"
        )
    match = matches[0]
    return text[:match.end()] + f"\n{canonical}" + text[match.end():], canonical


def discover_manifest_reading_tests(root: pathlib.Path) -> list[pathlib.Path]:
    """Every tests/test_*.py file that references the literal token RELEASE_MANIFEST -- i.e.
    reads or asserts against RELEASE_MANIFEST.md's own content, so an apply to that file can
    change what these tests observe. Discovered fresh each call (not a hardcoded list) so a
    consumer test added later is picked up automatically -- a hand-maintained list would be
    exactly the kind of hand-maintained drift this whole tool exists to eliminate."""
    tests_dir = root / "tests"
    out = []
    for p in sorted(tests_dir.rglob("test_*.py")):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "RELEASE_MANIFEST" in text:
            out.append(p)
    return out


def _run_pytest_subset(files: list[pathlib.Path], root: pathlib.Path) -> tuple[int, int, int, str]:
    """Run exactly these test files with pytest -q; return (passed, skipped, failed, raw_output).
    `failed` sums reported 'failed' and 'error' counts -- either means the subset is not green."""
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"] + [str(f) for f in files]
    proc = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True)
    out = (proc.stdout or "") + (proc.stderr or "")
    failed_m = re.search(r"(\d+)\s+failed", out)
    error_m = re.search(r"(\d+)\s+error", out)
    passed_m = re.search(r"(\d+)\s+passed", out)
    skipped_m = re.search(r"(\d+)\s+skipped", out)
    failed = (int(failed_m.group(1)) if failed_m else 0) + (int(error_m.group(1)) if error_m else 0)
    passed = int(passed_m.group(1)) if passed_m else 0
    skipped = int(skipped_m.group(1)) if skipped_m else 0
    # Only pytest exit 1 denotes completed test failures usable in the
    # pre/post manifest comparison. Interrupts, usage errors, and no collection
    # are execution failures, regardless of summary-looking text in stdout.
    if proc.returncode not in (0, 1):
        raise SystemExit(f"gen_release_manifest: pytest execution failed (exit {proc.returncode})"
                         f"\n{_tail_lines(out)}")
    if not (passed + skipped + failed):
        raise SystemExit("gen_release_manifest: pytest reported no test outcomes")
    if proc.returncode == 1 and not failed:
        raise SystemExit("gen_release_manifest: pytest failed without a failure summary")
    if proc.returncode == 0 and failed:
        raise SystemExit("gen_release_manifest: pytest exit code conflicts with failure summary")
    return passed, skipped, failed, out


def apply_manifest_with_counts(root: pathlib.Path, passed: int, skipped: int,
                               provenance: str, tier_zip_names=()) -> tuple[bool, str]:
    """Write RELEASE_MANIFEST.md's derived fields for (passed, skipped, provenance).

    Shares the exact same primitives main()'s --apply branch uses (read_truth,
    ensure_test_evidence_row, build_rules) so this can never drift from --apply's own
    behaviour -- it is an additional caller of those functions, not a second implementation.
    Returns (changed, message). Raises SystemExit if RELEASE_MANIFEST.md is missing, matching
    main()'s own fail-closed posture.
    """
    manifest = root / "RELEASE_MANIFEST.md"
    if not manifest.exists():
        raise SystemExit(f"gen_release_manifest: no RELEASE_MANIFEST.md at {root}")
    engine, bundle, stamp = read_truth(root)
    text = manifest.read_text(encoding="utf-8")
    test_bound_text, _canonical_test_row = ensure_test_evidence_row(text, passed, skipped, provenance)
    rules = build_rules(engine, bundle, stamp, passed, skipped, tier_zip_names)
    new_text = test_bound_text
    for _label, pat, repl in rules:
        new_text = pat.sub(lambda m: m.expand(repl), new_text)
    if new_text != text:
        tmp = manifest.with_suffix(".md.tmp")
        tmp.write_text(new_text, encoding="utf-8")
        import os
        os.replace(str(tmp), str(manifest))
        return True, (f"patched RELEASE_MANIFEST.md — engine {engine}, bundle {bundle}, "
                      f"stamp {stamp}, tests {passed}p/{skipped}s")
    return False, "RELEASE_MANIFEST.md already current; no change."


def run_fixed_point(root: pathlib.Path, seed_passed: int, seed_skipped: int, provenance: str,
                    max_iterations: int = 5, tier_zip_names=()) -> tuple[int, int, int]:
    """Converge the manifest's test-count row against its own manifest-reading test subset.

    Both lanes did this by hand at .404: apply the manifest with a measured full-suite count,
    then discover that applying it flips one or more of the tests that themselves read
    RELEASE_MANIFEST.md (a stamp/version/anchor check that was failing against the STALE
    manifest and now passes against the freshly-applied one) -- so the measured count under-
    stated the true post-apply pass total by exactly the number of such flips. This function
    automates that dance: run the manifest-reading subset BEFORE applying (baseline), apply
    with the current candidate count, run the same subset AFTER applying, and adjust the
    candidate count by the subset's own pass/skip delta (attributable entirely to the apply,
    since nothing else in the tree changed between the two subset runs). Repeat until the
    delta is zero -- a fixed point -- or `max_iterations` is exhausted.

    Fails closed exactly like the rest of this tool, but asymmetrically by design: a pre-apply
    failure in the subset is EXPECTED (a freshness check failing against the stale manifest is
    the drift this tool exists to fix, and it is already reflected in the lower pre-apply passed
    count) and is not refused -- but a subset failure that PERSISTS after the apply is refused
    (raises SystemExit): the apply is supposed to make every manifest-reading check pass, so a
    still-red post-apply subset means something is genuinely broken in the applied content, not
    merely uncounted, and must not be silently absorbed into a "corrected" count. Also refuses if
    no manifest-reading test files are discovered at all (nothing to converge against).

    Returns (final_passed, final_skipped, iterations_used).
    """
    consumer_files = discover_manifest_reading_tests(root)
    if not consumer_files:
        raise SystemExit(
            "gen_release_manifest --fixed-point: no RELEASE_MANIFEST-consuming test files "
            "discovered under tests/ -- refusing (nothing to converge against)"
        )
    passed, skipped = seed_passed, seed_skipped
    for iteration in range(1, max_iterations + 1):
        # A pre-apply failure here is EXPECTED, not refused: a manifest-consumer test failing
        # against a stale manifest (e.g. a version/stamp freshness check) is exactly the drift
        # this tool exists to fix, and pytest's own "N passed" already excludes it -- so
        # base_passed is already correctly lower, and the post-apply delta below captures the
        # fix automatically. Only a still-failing (or newly-failing) subset AFTER the apply is
        # refused: that means the apply itself did not do what it claims.
        base_passed, base_skipped, _base_failed, _base_out = _run_pytest_subset(consumer_files, root)
        apply_manifest_with_counts(root, passed, skipped, provenance, tier_zip_names)
        after_passed, after_skipped, after_failed, after_out = _run_pytest_subset(consumer_files, root)
        if after_failed:
            raise SystemExit(
                f"gen_release_manifest --fixed-point: {after_failed} manifest-consumer test(s) "
                f"failing AFTER apply (iteration {iteration}) -- refusing:\n{_tail_lines(after_out)}"
            )
        delta_passed = after_passed - base_passed
        delta_skipped = after_skipped - base_skipped
        if delta_passed == 0 and delta_skipped == 0:
            return passed, skipped, iteration
        passed += delta_passed
        skipped += delta_skipped
    raise SystemExit(
        f"gen_release_manifest --fixed-point: did not converge after {max_iterations} "
        f"iteration(s) (last delta {delta_passed:+d} passed / {delta_skipped:+d} skipped) -- "
        f"a manifest-reading test's pass/skip status is not stabilizing; fix that test's flakiness "
        f"before trusting a --fixed-point count"
    )


def _tail_lines(text: str, lines: int = 20) -> str:
    return "\n".join(text.strip().splitlines()[-lines:])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".", help="bundle root (default: cwd)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="report drift; exit 1 if any field is stale")
    g.add_argument("--apply", action="store_true", help="rewrite RELEASE_MANIFEST.md in place")
    g.add_argument("--fixed-point", action="store_true",
                   help="apply, then converge the count against the manifest-reading test "
                        "subset's own pre/post-apply delta (see run_fixed_point docstring); "
                        "requires --pytest-log or --tests-passed/--tests-skipped, same as --apply")
    ap.add_argument("--pytest-log", help="pytest summary log to read pass/skip counts from")
    ap.add_argument("--tests-passed", type=int, help="explicit passed count (overrides --pytest-log)")
    ap.add_argument("--tests-skipped", type=int, help="explicit skipped count (overrides --pytest-log)")
    ap.add_argument("--max-iterations", type=int, default=5,
                    help="--fixed-point only: convergence iteration ceiling (default: 5)")
    ap.add_argument(
        "--tier-zips", nargs="*", default=(), metavar="ZIP",
        help="release tier archives; include PUBLIC-RELEASE only when that promotion exists",
    )
    args = ap.parse_args(argv)

    root = pathlib.Path(args.root).resolve()
    manifest = root / "RELEASE_MANIFEST.md"
    if not manifest.exists():
        emit(f"gen_release_manifest: no RELEASE_MANIFEST.md at {root}", file=sys.stderr)
        return 2

    if args.fixed_point:
        passed, skipped = args.tests_passed, args.tests_skipped
        provenance = "operator-supplied counts, no log bound"
        if args.pytest_log and (passed is None or skipped is None):
            lp, ls = counts_from_log(pathlib.Path(args.pytest_log))
            provenance = ("receipt-bound log" if passed is None and skipped is None
                          else "receipt-bound log, partly operator-supplied")
            passed = passed if passed is not None else lp
            skipped = skipped if skipped is not None else ls
        if passed is None:
            sys.stderr.write(
                "gen_release_manifest --fixed-point: requires --pytest-log or --tests-passed "
                "(a seed measured count) -- refusing to converge from nothing\n")
            return 2
        try:
            final_passed, final_skipped, _iters = run_fixed_point(
                root, passed, skipped, provenance, max_iterations=args.max_iterations,
                tier_zip_names=args.tier_zips)
        except SystemExit as exc:
            sys.stderr.write(str(exc) + "\n")
            return 1
        sys.stdout.write(f"converged: {final_passed} passed\n")
        return 0

    engine, bundle, stamp = read_truth(root)
    passed, skipped = args.tests_passed, args.tests_skipped
    # v9.7.404: record HOW the counts were obtained, not just what they were. A count read from
    # a pytest log is receipt-bound and re-checkable; a count typed on the command line is an
    # operator assertion. Both are legitimate at cut time — describing the second as the first
    # is not, and the row is read later as if it were evidence.
    provenance = "operator-supplied counts, no log bound"
    if args.pytest_log and (passed is None or skipped is None):
        lp, ls = counts_from_log(pathlib.Path(args.pytest_log))
        provenance = ("receipt-bound log" if passed is None and skipped is None
                      else "receipt-bound log, partly operator-supplied")
        passed = passed if passed is not None else lp
        skipped = skipped if skipped is not None else ls

    text = manifest.read_text(encoding="utf-8")
    # A normal source-tree ``--check`` runs before the final suite and therefore
    # has no receipt counts yet. Validate every other derived field without
    # fabricating or requiring the cut-only row. Once the row exists, a no-log
    # check preserves it unchanged. ``--apply`` remains fail-closed: it may add
    # or refresh the row only from explicit counts or a green pytest log.
    if args.check and passed is None:
        test_bound_text, canonical_test_row = text, ""
    else:
        try:
            test_bound_text, canonical_test_row = ensure_test_evidence_row(text, passed, skipped, provenance)
        except ValueError as exc:
            emit(f"gen_release_manifest: {exc}", file=sys.stderr)
            return 2
    rules = build_rules(engine, bundle, stamp, passed, skipped, args.tier_zips)

    drift, new_text = [], test_bound_text
    if test_bound_text != text:
        drift.append(("full pytest suite evidence", "missing or stale", canonical_test_row))
    zero_match = []  # v9.7.116: a rule that matches nothing means its manifest line was reworded/removed
    for label, pat, repl in rules:
        n_hits = 0
        def _sub(m):
            nonlocal n_hits
            n_hits += 1
            cur = m.group(0)
            new = m.expand(repl)
            if cur != new:
                drift.append((label, cur.strip(), new.strip()))
            return new
        new_text = pat.sub(_sub, new_text)
        if n_hits == 0:
            zero_match.append(label)
    if zero_match:
        msg = ("RELEASE_MANIFEST sync rule matched ZERO times (line reworded/removed; "
               "the field is no longer kept in sync): " + ", ".join(zero_match))
        if args.check:
            emit(msg, file=sys.stderr)
            return 1
        emit("WARNING — " + msg, file=sys.stderr)

    if args.check:
        if drift:
            emit("RELEASE_MANIFEST drift (run --apply):")
            for label, cur, new in drift:
                emit(f"  [{label}]\n    - {cur}\n    + {new}")
            return 1
        emit(f"RELEASE_MANIFEST OK  (engine {engine}, bundle {bundle}, stamp {stamp})")
        return 0

    if new_text != text:
        tmp = manifest.with_suffix(".md.tmp")
        tmp.write_text(new_text, encoding="utf-8")
        import os
        os.replace(str(tmp), str(manifest))
        emit(f"patched RELEASE_MANIFEST.md — engine {engine}, bundle {bundle}, stamp {stamp}"
              + (f", tests {passed}p/{skipped}s" if passed is not None else ""))
    else:
        emit("RELEASE_MANIFEST.md already current; no change.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
