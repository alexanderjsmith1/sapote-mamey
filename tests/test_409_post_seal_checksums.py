#!/usr/bin/env python3
"""TESTS — CLAUDE_409_post_seal_checksums (audit N1 injection / N2 swap+delete / N9 enforce).

Fail-before / pass-after for the three leaks the DEEP_AUDIT proved on the RB68 gold package:
  * N1  injection : a fabricated file dropped into an exempt post-seal subtree (mode_b/, …)
  * N2a swap      : a post-seal claim table swapped for fabricated content
  * N2b delete    : a post-seal deliverable (figure) removed
On a package sealed BEFORE this patch (no post_seal_checksums.txt) all three validate PASS
(the leak); on a package sealed by the PATCHED writer (post_seal_checksums.txt present) each is
caught -> checksum_integrity FAIL.

The mechanism under test is `mamey.validate.verify_checksums` (the function whose non-empty
return flips checksum_integrity to FAIL in validate_package). These tests exercise it directly on
a TINY synthetic sealed package, so they run in a fraction of a second and need neither the 104 MB
RB68 package nor pytest. The same behaviour was verified end-to-end on scratchpad copies of the
real RB68 package (see PATCH_CARD.md "Fail-before / pass-after").

Run against a bundle that HAS this patch applied:
    python TESTS_409_post_seal_checksums.py /path/to/patched/bundle_root
(bundle_root is the dir containing `mamey/`). Exit 0 = all pass.

The "fail-before" leg is encoded structurally: with NO post_seal_checksums.txt present, the SAME
injection/swap/delete is NOT flagged by verify_checksums (== the pre-patch behaviour, and the
backward-compat contract). With the manifest present, each IS flagged. One codebase demonstrates
both because absence-vs-presence of the manifest is exactly the pre/post-patch switch.
"""
import sys, os, shutil, tempfile, hashlib
from pathlib import Path


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _make_sealed_package(root: Path):
    """A minimal but faithful sealed package: one CORE file tracked in checksums_sha256.txt, plus
    post-seal DATA/deliverables in exempt subtrees (domain_level/, blastp_online/, mode_b absent)
    and a root figure + its *_fig_*_data.csv companion — the exact shapes the audit attacked."""
    root.mkdir(parents=True, exist_ok=True)
    # Core file (in the seal-first checksum set).
    core = root / "STR_2_inventory.csv"
    core.write_text("bgc_id,product\nBGC001,unknown\n", encoding="utf-8")
    # Post-seal exempt deliverables (NOT in checksums_sha256.txt — written after the core seal).
    (root / "domain_level").mkdir()
    (root / "domain_level" / "domain_safe_unsafe_claims.csv").write_text(
        "bgc_id,claim,safe\nBGC001,none asserted,TRUE\n", encoding="utf-8")
    (root / "blastp_online").mkdir()
    (root / "blastp_online" / "BGC001_online_blastp.csv").write_text(
        "gene,hit\nctg1_1,none\n", encoding="utf-8")
    (root / "STR_8a_fig_landscape.png").write_bytes(b"\x89PNG\r\n\x1a\n-real-figure-bytes-")
    (root / "STR_8d_fig_ab_ranked_data.csv").write_text("rank,score\n1,0.5\n", encoding="utf-8")
    # The core checksum manifest tracks ONLY the core file (seal-first snapshot).
    (root / "checksums_sha256.txt").write_text(f"{_sha(core)}  STR_2_inventory.csv\n", encoding="utf-8")


def main(bundle_root: str) -> int:
    sys.path.insert(0, bundle_root)
    from mamey.validate import verify_checksums
    from mamey.packaging import write_post_seal_checksums, is_post_seal_covered

    tmp = Path(tempfile.mkdtemp(prefix="psc_tests_"))
    failures = []

    def check(name, cond, detail=""):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  -- {detail}" if detail and not cond else ""))
        if not cond:
            failures.append(name)

    def fresh(sub):
        p = tmp / sub
        shutil.rmtree(p, ignore_errors=True)
        _make_sealed_package(p)
        return p

    def has(errs, needle):
        return any(needle in e for e in errs)

    # ---- FAIL-BEFORE: no post_seal_checksums.txt => the three attacks are NOT caught (leak) ----
    print("FAIL-BEFORE (no post_seal_checksums.txt — pre-patch / backward-compatible posture):")
    p = fresh("fb_inject"); (p / "mode_b").mkdir()
    (p / "mode_b" / "BGC999_mode_b.md").write_text("fabricated: produces penicillin\n", encoding="utf-8")
    check("injection NOT flagged without manifest (leak reproduced)",
          not has(verify_checksums(p), "post_seal") and not has(verify_checksums(p), "injected"))
    p = fresh("fb_swap")
    (p / "domain_level" / "domain_safe_unsafe_claims.csv").write_text(
        "bgc_id,claim,safe\nBGC001,makes vancomycin,TRUE\n", encoding="utf-8")
    check("swap NOT flagged without manifest (leak reproduced)", verify_checksums(p) == [])
    p = fresh("fb_delete"); (p / "STR_8a_fig_landscape.png").unlink()
    check("delete NOT flagged without manifest (leak reproduced)", verify_checksums(p) == [])

    # ---- PASS-AFTER: sealed by the patched writer => each attack caught ----
    print("PASS-AFTER (post_seal_checksums.txt written by the patched sealer):")
    base = fresh("pa_base")
    res = write_post_seal_checksums(base)
    check("sealer emitted post_seal_checksums.txt", (base / "post_seal_checksums.txt").exists(),
          "no manifest written")
    check("covered set includes the post-seal deliverables (not the core/mutable)",
          res["n_files"] >= 4 and "STR_2_inventory.csv" not in res["files"])
    check("legit sealed package still verifies clean", verify_checksums(base) == [],
          str(verify_checksums(base)))

    # injection
    p = tmp / "pa_inject"; shutil.rmtree(p, ignore_errors=True); shutil.copytree(base, p)
    (p / "mode_b").mkdir(); (p / "mode_b" / "BGC999_mode_b.md").write_text("fabricated\n", encoding="utf-8")
    check("INJECTION caught (mode_b/BGC999_mode_b.md)", has(verify_checksums(p), "injected file present"))

    # swap
    p = tmp / "pa_swap"; shutil.rmtree(p, ignore_errors=True); shutil.copytree(base, p)
    (p / "domain_level" / "domain_safe_unsafe_claims.csv").write_text(
        "bgc_id,claim,safe\nBGC001,makes vancomycin,TRUE\n", encoding="utf-8")
    check("SWAP caught (domain_level claim table)", has(verify_checksums(p), "post-seal checksum mismatch"))

    # delete
    p = tmp / "pa_delete"; shutil.rmtree(p, ignore_errors=True); shutil.copytree(base, p)
    (p / "STR_8a_fig_landscape.png").unlink()
    check("DELETE caught (figure removed)", has(verify_checksums(p), "post-seal file deleted"))

    # ---- Boundary: genuinely-mutable receipts / regenerated reports are NOT covered ----
    print("BOUNDARY (mutable receipts & regenerated reports stay changeable):")
    for nm in ("manifest.json", "package_status.json", "gate_validation.json",
               "STR_compiled_report.md", "STR_SAPOTE_WORKFLOW_LEDGER.md", "STR_cnbu.json",
               "STR_judgment_register.json", "post_seal_checksums.txt", "locus_maps/M_locus_map.png"):
        check(f"not covered: {nm}", is_post_seal_covered(nm) is False)
    for nm in ("mode_b/c.md", "domain_level/t.csv", "blastp_online/b.csv", "guide/g.md",
               "figures/f.png", "STR_8a_fig_landscape.png", "STR_8d_fig_ab_ranked_data.csv",
               "locus_maps/M_locus_map_data.csv", "locus_maps/M_v8_receipt.json"):
        check(f"covered: {nm}", is_post_seal_covered(nm) is True)

    shutil.rmtree(tmp, ignore_errors=True)
    print()
    if failures:
        print(f"RESULT: {len(failures)} FAILED -> {failures}")
        return 1
    print("RESULT: ALL PASSED")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        print("usage: python TESTS_409_post_seal_checksums.py <patched_bundle_root>")
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
