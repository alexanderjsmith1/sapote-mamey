#!/usr/bin/env python3
"""cut_audit.py — reproducible sealed-cut audit + card rebase-verify harness.

Codifies the manual workflow used to (a) adopt a sealed Sapote-Mamey cut as the working
version and (b) verify a staged patch card against it WITHOUT blaming the card for
environment/path noise. Two subcommands, stdlib-only.

    # 1) AUDIT a sealed cut (integrity + version + optional sealed-zip hash)
    python tools/cut_audit.py verify --tree <sealed_tree> \
        [--zip <cut.zip> --sha256 <SHA256SUMS.txt>]

    # 2) REBASE-VERIFY a staged card onto that cut, subtracting base failures
    python tools/cut_audit.py rebase-verify --base <sealed_tree> --card <card_dir> \
        [--full] [--python /path/to/python3] [--keep]

Two hard lessons this encodes:
  * COPY THE WHOLE TREE. A partial copy (e.g. excluding Wheelhouse/) makes tree-wide
    ratchet guards (dangling-path baselines) fail on missing references — not a card bug.
  * SUBTRACT BASE FROM PATCHED. Many tests are workspace/path-sensitive and fail from any
    copy location. Only failures PRESENT IN PATCHED BUT NOT IN BASE are attributable to the
    card. rebase-verify runs both trees the same way and reports the set difference.

Exit code: 0 = clean (verify passed / card introduced no NEW failures); 1 = problem.
Non-scoring, read-only w.r.t. the sealed tree (all work happens in a temp copy).
"""
from __future__ import annotations
import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

_FAIL_RE = re.compile(r"^(FAILED|ERROR)\s+(\S+)", re.M)


def _run(cmd, cwd=None, timeout=None):
    """Run a command; on timeout return rc=124 + partial output rather than raising, so a slow
    suite is reported as inconclusive instead of crashing the harness."""
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired as e:
        def _dec(x):
            return x.decode(errors="replace") if isinstance(x, (bytes, bytearray)) else (x or "")
        return 124, _dec(e.stdout) + _dec(e.stderr) + f"\n[cut_audit] TIMEOUT after {timeout}s"


def _pytest_failures(out: str) -> set[str]:
    """Extract the set of FAILED/ERROR node ids from a pytest -q run."""
    return {m.group(2) for m in _FAIL_RE.finditer(out)}


def _summary_line(out: str) -> str:
    for line in reversed(out.splitlines()):
        if "passed" in line or "failed" in line or "error" in line:
            return line.strip()
    return "(no pytest summary line found)"


def verify(args) -> int:
    tree = os.path.abspath(args.tree)
    ok = True

    # 1. SOURCE_CHECKSUMS integrity
    sums = os.path.join(tree, "SOURCE_CHECKSUMS_SHA256.txt")
    if os.path.exists(sums):
        rc, out = _run(["shasum", "-a", "256", "-c", "SOURCE_CHECKSUMS_SHA256.txt"], cwd=tree)
        n_ok = out.count(": OK")
        n_bad = out.count("FAILED")
        sys.stdout.write((f"[checksums] {n_ok} OK, {n_bad} FAILED  -> {'PASS' if rc == 0 and n_bad == 0 else 'FAIL'}") + "\n")
        ok = ok and rc == 0 and n_bad == 0
    else:
        sys.stdout.write(("[checksums] SOURCE_CHECKSUMS_SHA256.txt not found -> SKIP") + "\n")

    # 2. version-sync drift gate
    vs = os.path.join(tree, "tools", "sync_version.py")
    if os.path.exists(vs):
        rc, out = _run([args.python, "tools/sync_version.py", "--check"], cwd=tree)
        _vline = (out.strip().splitlines() or ["(no output)"])[-1][:120]
        sys.stdout.write((f"[version ] {_vline}  -> {'PASS' if rc == 0 else 'FAIL'}") + "\n")
        ok = ok and rc == 0
    else:
        sys.stdout.write(("[version ] tools/sync_version.py not found -> SKIP") + "\n")

    # 3. sealed-zip hash (optional)
    if args.zip and args.sha256:
        want = None
        with open(args.sha256) as fh:
            for line in fh:
                parts = line.split()
                if parts and os.path.basename(args.zip) in line:
                    want = parts[0]
                    break
        if want:
            h = hashlib.sha256()
            with open(args.zip, "rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(chunk)
            got = h.hexdigest()
            match = (got == want)
            sys.stdout.write((f"[zip     ] {'OK' if match else 'MISMATCH'} {os.path.basename(args.zip)} -> {'PASS' if match else 'FAIL'}") + "\n")
            ok = ok and match
        else:
            sys.stdout.write((f"[zip     ] {os.path.basename(args.zip)} not listed in {args.sha256} -> FAIL") + "\n")
            ok = False

    sys.stdout.write((f"\nVERIFY: {'PASS' if ok else 'FAIL'}  ({tree})") + "\n")
    return 0 if ok else 1


def rebase_verify(args) -> int:
    base = os.path.abspath(args.base)
    card = os.path.abspath(args.card)
    work = tempfile.mkdtemp(prefix="cut_audit_")
    base_tree = os.path.join(work, "base")
    patch_tree = os.path.join(work, "patched")
    try:
        # WHOLE-TREE copies (do NOT exclude Wheelhouse — tree-wide guards need it)
        sys.stdout.write((f"[copy] rsync full base -> {base_tree}") + "\n")
        _run(["rsync", "-a", base + "/", base_tree + "/"])
        _run(["rsync", "-a", base_tree + "/", patch_tree + "/"])

        # apply every *.diff / *.patch in the card dir to the patched tree
        diffs = sorted(f for f in os.listdir(card) if f.endswith((".diff", ".patch")))
        for d in diffs:
            rc, out = _run(["patch", "-p1", "-i", os.path.join(card, d)], cwd=patch_tree)
            sys.stdout.write((f"[apply] {d}: {'OK' if rc == 0 else 'FAILED'}") + "\n")
            if rc != 0:
                sys.stdout.write((out[-800:]) + "\n")
                sys.stdout.write(("\nREBASE-VERIFY: FAIL (patch did not apply)") + "\n")
                return 1
        # copy any card test_*.py into tests/
        for f in os.listdir(card):
            if f.startswith("test_") and f.endswith(".py"):
                shutil.copy(os.path.join(card, f), os.path.join(patch_tree, "tests", f))
                shutil.copy(os.path.join(card, f), os.path.join(base_tree, "tests", f))
                sys.stdout.write((f"[test] staged {f} into both trees") + "\n")

        # Run the same scope both sides so the failure-set subtraction is apples-to-apples.
        # --tests limits scope (repeatable) for a faster targeted check; default is the full suite.
        # BC2-407: --run-slow is REQUIRED, not optional. conftest.py auto-skips any test whose
        # file name contains a _SLOW_FILE_HINTS substring (e.g. "figure") unless --run-slow is
        # passed -- CI's own full-suite job always adds it. Without it here, a card that touches
        # a figure/render/atlas-named test file gets "0 failures" on BOTH sides because every
        # test in that file was silently skipped, not because it passed -- a false PASS from the
        # tool whose entire job is to catch exactly this class of silent gap. --run-network is
        # deliberately NOT added: it requires live network, a materially different resource this
        # offline, read-only harness should never enable on its own.
        scope = args.tests if args.tests else ["tests/"]
        pytest_args = [args.python, "-m", "pytest", *scope, "-q", "-p", "no:cacheprovider", "--run-slow"]

        sys.stdout.write((f"[run] base suite ...") + "\n")
        base_rc, base_out = _run(pytest_args, cwd=base_tree, timeout=args.timeout)
        sys.stdout.write((f"      base:    {_summary_line(base_out)}") + "\n")
        sys.stdout.write((f"[run] patched suite ...") + "\n")
        patch_rc, patch_out = _run(pytest_args, cwd=patch_tree, timeout=args.timeout)
        sys.stdout.write((f"      patched: {_summary_line(patch_out)}") + "\n")
        timed_out = (base_rc == 124 or patch_rc == 124)
        if timed_out:
            sys.stdout.write((f"\n[warn] a suite hit --timeout ({args.timeout}s); failure sets are PARTIAL — "
                  "raise --timeout or narrow --tests. New failures below are still real; a clean "
                  "delta under timeout is INCONCLUSIVE, not PASS.") + "\n")

        base_f = _pytest_failures(base_out)
        patch_f = _pytest_failures(patch_out)
        new_f = patch_f - base_f
        fixed_f = base_f - patch_f

        sys.stdout.write((f"\n[delta] base failures={len(base_f)}  patched failures={len(patch_f)}") + "\n")
        if fixed_f:
            sys.stdout.write((f"[delta] {len(fixed_f)} failure(s) only in base (pre-existing/env, not the card's concern)") + "\n")
        if new_f:
            sys.stdout.write((f"[delta] {len(new_f)} NEW failure(s) introduced by the card:") + "\n")
            for n in sorted(new_f):
                sys.stdout.write((f"          + {n}") + "\n")
            sys.stdout.write(("\nREBASE-VERIFY: FAIL") + "\n")
            return 1
        if timed_out:
            sys.stdout.write(("\nREBASE-VERIFY: INCONCLUSIVE (0 new failures seen, but a suite timed out — "
                  "re-run with a larger --timeout or a narrower --tests scope to confirm)") + "\n")
            return 2
        sys.stdout.write(("\nREBASE-VERIFY: PASS (card introduces 0 new failures vs the same base)") + "\n")
        return 0
    finally:
        if args.keep:
            sys.stdout.write((f"[keep] work tree left at {work}") + "\n")
        else:
            shutil.rmtree(work, ignore_errors=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="cut_audit", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")

    v = sub.add_parser("verify", help="audit a sealed cut (checksums + version + optional zip hash)")
    v.add_argument("--tree", required=True, help="sealed CODE tree root")
    v.add_argument("--zip", default=None, help="sealed cut zip (optional)")
    v.add_argument("--sha256", default=None, help="SHA256SUMS.txt listing the zip (optional)")
    v.add_argument("--python", default=sys.executable, help="interpreter for tools/sync_version.py")
    v.set_defaults(func=verify)

    r = sub.add_parser("rebase-verify", help="apply a card to a full copy of the cut and subtract base failures")
    r.add_argument("--base", required=True, help="sealed CODE tree root (unchanged)")
    r.add_argument("--card", required=True, help="card dir holding *.diff/*.patch + test_*.py")
    r.add_argument("--tests", nargs="*", default=None,
                   help="limit pytest scope both sides (e.g. --tests tests/test_widget_deliverable_tools.py); "
                        "default = the full suite")
    r.add_argument("--python", default=sys.executable, help="interpreter with pytest")
    r.add_argument("--timeout", type=int, default=1800, help="per-suite timeout seconds")
    r.add_argument("--keep", action="store_true", help="keep the temp work trees")
    r.set_defaults(func=rebase_verify)

    args = ap.parse_args(argv)
    if not getattr(args, "func", None):
        ap.print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
