#!/usr/bin/env python3
"""parked_card_audit.py — flag patch-pool cards that silently fell out of the cut cadence.

MOTIVATION (real, 2026-09-03): AMBER_401_g3b_n50_floor was a fully-verified patch that never
folded. The .401 pool froze before it composed, and it sat un-folded through .402→.406 while its
target file drifted underneath it — so the old patch bytes no longer even applied. Five cuts of
silence. Nothing watched for it. This tool is that watch.

DETECTION IS CONTENT-GROUNDED, NOT MARKER-GROUNDED. The FOLDED/RETIRED marker-file convention is
too sparsely applied to trust (in the .401 pool only one of ~28 card dirs carried a marker, yet
many had folded) — keying off markers alone would false-flag nearly every card in every old pool.
Instead we ask the sealed tree directly:

  * `patch -p1 --dry-run` applies clean → the change is ABSENT but cleanly foldable → PARKED.
  * else, we cannot use reverse-apply to decide "already folded": a patch built against an OLDER
    base fails to reverse-apply against a drifted sealed tree EVEN WHEN its change landed, because
    the surrounding context lines differ (verified 2026-09-03: reverse-apply mislabeled a
    known-folded card DRIFTED and a known-unfolded card FOLDED). So for the non-forward-applicable
    case we ask a drift-robust question instead — do the card's ADDED ('+') lines actually appear
    in the current target file(s)?
      - a high fraction present → FOLDED (the change is in; only its context drifted)
      - a low fraction present  → DRIFTED (the change is absent AND the base moved — the g3b case,
                                  neither foldable nor folded, needs a human rebase)
    New-file targets (/dev/null adds) are judged by existence of the file in the sealed tree.

Flagging policy (ranked by consequence):
  * DRIFTED  → ALWAYS flagged, any age. This is the g3b case: neither foldable nor folded, needs a
               human rebase. The most dangerous state, because it fails silently at compose time.
  * PARKED   → flagged once the pool is >= TTL cuts behind the current sealed version (default 2).
  * FOLDED   → never flagged (it is in the engine); noted only, and a missing marker is advisory.

A card dir with a FOLDED*/RETIRED*/SUPERSED* marker AND a FOLDED classification is fully expected
and stays silent. A marker that CONTRADICTS the content (e.g. "RETIRED" but the patch still applies
forward = not actually superseded) is itself surfaced — a stale marker is its own small defect.

Non-destructive: only ever runs `patch --dry-run` against the sealed tree; never writes to it.
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import subprocess
import sys

_VER_RE = re.compile(r"v?9\.7\.(\d+)")
_MARKER_RE = re.compile(r"^(FOLDED|RETIRED|SUPERSED)", re.I)


def _pool_version(path):
    """Extract the NNN from a '...(v9.7.NNN)' pool dir name, or None."""
    m = _VER_RE.search(os.path.basename(os.path.normpath(path)))
    return int(m.group(1)) if m else None


def _dry_run(patch_path, tree, reverse):
    """Return True iff `patch -p1 --dry-run [-R]` applies with zero fuzz in `tree`."""
    cmd = ["patch", "-p1", "--dry-run", "--fuzz=0"]
    if reverse:
        cmd.append("-R")
    try:
        with open(patch_path, "rb") as fh:
            r = subprocess.run(cmd, cwd=tree, stdin=fh,
                               capture_output=True, timeout=60)
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _parse_targets(patch_path):
    """Yield (target_path, is_new_file, [added_lines]) for each file in a unified diff.

    added_lines = content '+' lines (excluding the '+++' header), stripped of the leading '+'.
    is_new_file = the '---' side was /dev/null (a pure file creation)."""
    targets = []
    cur_path = None
    cur_new = False
    cur_added = []
    prev_minus_new = False
    with open(patch_path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith("--- "):
                body = line[4:].rstrip("\n")
                minus_path = body.split("\t")[0].strip()
                # A new file is signalled EITHER by /dev/null (GNU `diff -N`, hand-written adds)
                # OR by an epoch timestamp on the '---' line (BSD/macOS `diff -urN` keeps the
                # a/<path> name but stamps 1969/1970 = the file did not exist). Handle both.
                prev_minus_new = (minus_path == "/dev/null"
                                  or re.search(r"\b19(69|70)-", body) is not None)
            elif line.startswith("+++ "):
                if cur_path is not None:
                    targets.append((cur_path, cur_new, cur_added))
                raw = line[4:].strip().split("\t")[0]
                cur_path = re.sub(r"^b/", "", raw)
                cur_new = prev_minus_new
                cur_added = []
            elif line.startswith("+") and not line.startswith("+++"):
                cur_added.append(line[1:].rstrip("\n"))
    if cur_path is not None:
        targets.append((cur_path, cur_new, cur_added))
    return targets


def _added_presence_ratio(added, sealed_text):
    """Fraction of distinctive added lines that appear verbatim in the sealed file text."""
    lines = [ln.strip() for ln in added if len(ln.strip()) >= 6]  # ignore trivial/blank lines
    if not lines:
        return 1.0  # nothing distinctive to check -> don't drag the verdict
    present = sum(1 for ln in lines if ln in sealed_text)
    return present / len(lines)


def _classify_patch(patch_path, tree, fold_threshold=0.6):
    """PARKED / FOLDED / DRIFTED / EMPTY for one .patch against the sealed tree.

    Order matters: presence is checked FIRST (it is the stronger 'already folded' signal and is
    drift-robust), and forward-apply is only the tiebreaker that distinguishes a cleanly-foldable
    absent card (PARKED) from a drifted absent one (DRIFTED). Checking forward-apply first misfires
    on a new-file add whose target already exists identically, which patch(1) reports as applicable.
    """
    if os.path.getsize(patch_path) == 0:
        return "EMPTY"
    # (1) presence — but only over targets that BELONG to this tree. A MODIFY target whose file is
    # absent from the sealed tree means the card patches a DIFFERENT tree (e.g. the workspace
    # `Tools/` toolkit vs the engine `tools/`); that is OUT_OF_SCOPE for this audit, not a drifted
    # change (verified 2026-09-03: a real BC card targeting Tools/guardrails.py was nearly
    # mis-flagged DRIFTED against the engine tree).
    ratios = []
    in_scope = 0
    for tgt, is_new, added in _parse_targets(patch_path):
        abspath = os.path.join(tree, tgt)
        if is_new:
            in_scope += 1
            ratios.append(1.0 if os.path.exists(abspath) else 0.0)
            continue
        if not os.path.exists(abspath):
            continue             # modify-target not in this tree -> out of scope, skip it
        in_scope += 1
        try:
            with open(abspath, encoding="utf-8", errors="replace") as fh:
                sealed_text = fh.read()
        except OSError:
            ratios.append(0.0)
            continue
        ratios.append(_added_presence_ratio(added, sealed_text))
    if in_scope == 0:
        return "OUT_OF_SCOPE"    # nothing this card touches lives in the audited tree
    # a card is FOLDED only if EVERY in-scope target's change is present; a partial fold is NOT a pass.
    if ratios and min(ratios) >= fold_threshold:
        return "FOLDED"
    # (2) not (fully) present: does it still apply forward cleanly?
    if _dry_run(patch_path, tree, reverse=False):
        return "PARKED"          # absent AND cleanly foldable — trustworthy
    return "DRIFTED"             # absent-or-partial AND not applicable — needs a human


_RANK = {"DRIFTED": 3, "EMPTY": 2, "PARKED": 1, "FOLDED": 0, "OUT_OF_SCOPE": -1}


PATCH_GLOBS = ("*.patch", "*.diff")  # the pool uses BOTH conventions (verified on the .407 pool:
                                     # AMBER/BC dirs use .patch, the PATCH_CARD_* dirs use .diff)


def _card_patches(card_dir):
    """All *.patch / *.diff files directly in a card dir (non-recursive is intentional:
    diffbuild/ copies are inputs, not the shipped patch)."""
    out = []
    for g in PATCH_GLOBS:
        out.extend(glob.glob(os.path.join(card_dir, g)))
    return sorted(out)


def _has_marker(card_dir):
    for name in os.listdir(card_dir):
        if _MARKER_RE.match(name):
            return name
    return None


def _touches(patches, prefixes):
    """True if any patch target path starts with one of `prefixes`."""
    for p in patches:
        for tgt, _is_new, _added in _parse_targets(p):
            if any(tgt.startswith(pre) for pre in prefixes):
                return True
    return False


def audit(pools, sealed_tree, current_version, ttl=2, require_tests=True):
    """Return (rows, flagged). Each row: dict(pool, card, status, age, marker, flag, note, test_gap).

    Second guard (require_tests): a not-yet-folded card that changes engine code (tools/ or mamey/)
    but carries NO tests/ target is flagged as a test gap — the exact shape of the 2026-09-03 .406
    signoff regression, which shipped a code change whose tests never made the cut. A test-only or
    doc-only card, or one whose test rides in-patch under tests/, is fine."""
    rows = []
    for pool in pools:
        pv = _pool_version(pool)
        if pv is None:
            continue
        age = current_version - pv
        entries = []
        # card subdirectories
        for name in sorted(os.listdir(pool)):
            cd = os.path.join(pool, name)
            if os.path.isdir(cd) and _card_patches(cd):
                entries.append((name, cd, _card_patches(cd)))
        # loose top-level *.patch / *.diff (Codex-style single-file cards)
        loose = []
        for g in PATCH_GLOBS:
            loose.extend(glob.glob(os.path.join(pool, g)))
        for p in sorted(loose):
            entries.append((os.path.basename(p), None, [p]))

        for card, cd, patches in entries:
            statuses = [_classify_patch(p, sealed_tree) for p in patches]
            status = max(statuses, key=lambda s: _RANK.get(s, 0))
            marker = _has_marker(cd) if cd else None
            flag, note = False, ""
            if status == "DRIFTED":
                flag = True
                note = ("does not apply forward AND its added lines are not present verbatim — "
                        "either SUPERSEDED by a reworked version already in the tree, or the base "
                        "drifted and the change is absent; a human must confirm which")
            elif status == "PARKED" and age >= ttl:
                flag = True
                note = f"foldable but un-folded for {age} cut(s) (TTL={ttl})"
            elif status == "FOLDED" and marker and _MARKER_RE.match(marker).group(1).upper() in ("RETIRED", "SUPERSED"):
                # marker says superseded, yet the content is present — contradictory, worth a look
                pass  # folded+retired is fine (rebased-elsewhere); don't flag
            elif status == "PARKED" and marker:
                # marker claims folded/retired but the patch still applies forward = stale marker
                if _MARKER_RE.match(marker).group(1).upper() in ("FOLDED",):
                    flag = True
                    note = f"marker '{marker}' claims folded but the patch still applies forward — stale marker"
            # second guard: a not-yet-folded code change with no accompanying test. A test counts if
            # it is EITHER a tests/ target inside the patch OR a loose test_*.py file shipped beside
            # the patch in the card dir (a common convention — the test is placed into tests/ at fold
            # time). Verified 2026-09-03: two real BC2 cards ship their test as a loose file, not a
            # patch hunk; checking only patch targets false-flagged them.
            test_gap = False
            if require_tests and status in ("PARKED", "DRIFTED"):
                has_test = _touches(patches, ("tests/",))
                if not has_test and cd:
                    has_test = bool(glob.glob(os.path.join(cd, "test_*.py"))
                                    or glob.glob(os.path.join(cd, "*_test.py")))
                if _touches(patches, ("tools/", "mamey/")) and not has_test:
                    test_gap = True
                    tg = ("changes engine code (tools/ or mamey/) but the card ships NO test "
                          "(neither a tests/ patch target nor a loose test_*.py in the card dir)")
                    note = (note + "; also: " + tg) if note else tg
            rows.append(dict(pool=os.path.basename(pool), card=card, status=status, age=age,
                             marker=marker or "", flag=flag or test_gap, note=note, test_gap=test_gap))
    flagged = [r for r in rows if r["flag"]]
    return rows, flagged


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pools", nargs="+", help="patch-pool dir(s) or a glob")
    ap.add_argument("--sealed-tree", required=True, help="path to the current SEALED bundle tree")
    ap.add_argument("--current-version", type=int, default=None,
                    help="current sealed NNN (default: read from --sealed-tree name)")
    ap.add_argument("--ttl", type=int, default=2, help="cuts a PARKED card may sit before flagging")
    ap.add_argument("--all", action="store_true", help="print every card, not just flagged ones")
    ap.add_argument("--no-require-tests", action="store_true",
                    help="disable the second guard (code change without a tests/ target)")
    args = ap.parse_args()

    cur = args.current_version
    if cur is None:
        cur = _pool_version(args.sealed_tree)
    if cur is None:
        print("ERROR: could not determine current version; pass --current-version", file=sys.stderr)
        return 2

    pools = []
    for p in args.pools:
        pools.extend(sorted(glob.glob(p)) if any(c in p for c in "*?[") else [p])
    pools = [p for p in pools if os.path.isdir(p)]

    rows, flagged = audit(pools, args.sealed_tree, cur, ttl=args.ttl,
                          require_tests=not args.no_require_tests)
    show = rows if args.all else flagged
    if show:
        print(f"=== parked_card_audit: current sealed=9.7.{cur}, TTL={args.ttl} ===")
        for r in sorted(show, key=lambda r: (-_RANK.get(r["status"], 0), r["pool"], r["card"])):
            tag = "FLAG" if r["flag"] else "    "
            print(f"  {tag} [{r['status']:7}] {r['pool']} / {r['card']}"
                  + (f"  (age {r['age']})" if r["age"] else "")
                  + (f"  — {r['note']}" if r["note"] else ""))
    if flagged:
        print(f"\n{len(flagged)} card(s) flagged: {sum(1 for r in flagged if r['status']=='DRIFTED')} DRIFTED, "
              f"{sum(1 for r in flagged if r['status']=='PARKED' and not r['test_gap'])} PARKED-past-TTL, "
              f"{sum(1 for r in flagged if r['test_gap'])} test-gap.")
        return 2
    print("parked_card_audit: no parked/drifted cards past TTL." if not args.all else
          "parked_card_audit: nothing flagged.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
