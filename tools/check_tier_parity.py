#!/usr/bin/env python3
"""
check_tier_parity.py — fail-closed parity gate across the four release tiers.

Catches the drift class that shipped in v9.7.5 (CODE-analysis-free carried placeholder
cassette IDs + was missing the registry while MERGED was clean): a fix lands in one tree
but not in the cut tiers, and nothing notices until a user hits it.

For each tier zip it inspects: bundle version, cassette stable-ID inventory (count + any
placeholder), registry-inventory presence, the enforcement/manifest files, and marker count.
It then enforces:
  - VERSION parity: identical bundle version across all tiers
  - CASSETTE parity: identical real-ID count, ZERO placeholders (CAS-XXX/CASS-XXX/-XXX), in every tier
  - MARKER parity: identical marker count across tiers
  - MANIFEST parity: SESSION_START_MANIFEST.md, DELIVERABLE_MANIFEST_TEMPLATE.md,
    tools/check_deliverable_suite.py, tools/sapote_judgment_receipt.py present in EVERY tier
  - SET completeness: the four candidate tiers (merged, sid, code, clean) must each appear exactly
    once; an optional governance-gated public promotion is recognized and checked when present
  - REGISTRY presence: expected present in every recognized tier (merged, sid, code, clean, public) — the
    registry inventory is code-adjacent (0 strain IDs), so no tier strips it (see
    REGISTRY_EXPECTED below); flagged only when missing from a tier that should carry it

Usage:
  python tools/check_tier_parity.py --tiers-dir <dir-of-tier-zips> [--with-public] [--json]
  python tools/check_tier_parity.py --zips a.zip b.zip c.zip d.zip [--with-public] [--json]
Exit 0 = all tiers in parity, 1 = drift found.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, glob, json, os, re, shutil, sys, tempfile, zipfile
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # local repo root before mamey import
from mamey.ziputil import safe_extract_all

# v9.7.408: the tier vocabulary has one owner — tools/tier_vocabulary.py. Before that, renaming a
# tier meant editing this set, two case arms in make_public_tier.sh, the archive regex below, and
# prose in three docs, with no way to prove the sweep was complete.
from tier_vocabulary import (  # noqa: E402
    REQUIRED_TIERS as _VOCAB_REQUIRED_TIERS,
    OPTIONAL_PROMOTION_TIERS as _VOCAB_PROMOTION_TIERS,
    TIERS as _VOCAB_TIERS,
    HISTORICAL_LABELS as _VOCAB_HISTORICAL_LABELS,
)

REQUIRED_TIERS = set(_VOCAB_REQUIRED_TIERS)
OPTIONAL_PROMOTION_TIERS = set(_VOCAB_PROMOTION_TIERS)
REGISTRY_EXPECTED = REQUIRED_TIERS | OPTIONAL_PROMOTION_TIERS   # code-adjacent inventory ships in every tier
MANIFEST_FILES = ["SESSION_START_MANIFEST.md", "DELIVERABLE_MANIFEST_TEMPLATE.md",
                  "tools/check_deliverable_suite.py", "tools/sapote_judgment_receipt.py"]
PLACEHOLDER_RE = re.compile(r"(?:CASS?-XXX|MM[KC]-[A-Z]*-XXX|SM[KC]-[A-Z]*-XXX)")

# Labels are ordered longest-first so a prefix (CODE) cannot shadow a longer label (CODE-analysis-free).
# HISTORICAL_LABELS are included because bundles sealed up to v9.7.407 carry `-SID-public-`; this
# regex PARSES existing archives, so it must keep accepting retired labels. Producers name new
# archives from `tier_vocabulary.archive_label`, which never emits a historical label.
_ALL_ARCHIVE_LABELS = sorted(
    {t.label for t in _VOCAB_TIERS} | set(_VOCAB_HISTORICAL_LABELS),
    key=len, reverse=True,
)
TIER_ARCHIVE_RE = re.compile(
    r"^sapote-mamey-v(?P<version>\d+\.\d+\.\d+[a-z]?)-"
    r"(?P<tier>" + "|".join(re.escape(x) for x in _ALL_ARCHIVE_LABELS) + r")-"
    r"(?P<stamp>\d{8}v\d+[a-z])\.zip$",
    re.IGNORECASE,
)
# label (lowercased) -> canonical tier name. Built from the vocabulary so it cannot drift from it;
# historical labels resolve to the tier they now denote (SID-public -> cohort).
TIER_LABELS = {t.label.lower(): t.name for t in _VOCAB_TIERS}
TIER_LABELS.update({lbl.lower(): canon for lbl, canon in _VOCAB_HISTORICAL_LABELS.items()})


class TierArchiveNameError(ValueError):
    """A release archive name cannot be bound to exactly one governed tier."""

    def __init__(self, code, name):
        self.code = code
        self.name = name
        super().__init__(f"{code}: archive={name!r}")


def tier_of(name):
    """Return the tier from the complete governed release-archive filename."""
    basename = os.path.basename(name)
    match = TIER_ARCHIVE_RE.fullmatch(basename)
    if match:
        return TIER_LABELS[match.group("tier").lower()]
    lowered = basename.lower()
    tier_tokens = [token for token in TIER_LABELS if token in lowered]
    code = (
        "AMBIGUOUS_TIER_ARCHIVE_NAME"
        if len(tier_tokens) > 1
        else "UNRECOGNIZED_TIER_ARCHIVE_NAME"
    )
    raise TierArchiveNameError(code, basename)

def inspect(zpath):
    # v9.7.371 fix: was tempfile.mkdtemp() with no cleanup anywhere -- every call (main() invokes
    # this once per tier zip, typically 4 per run) leaked a full extracted copy of the sealed
    # bundle tree into the OS temp dir permanently. Wrap in try/finally so a repeated/automated
    # parity-gate run (e.g. wired into a pre-seal pipeline) doesn't silently accumulate multiple
    # unpacked bundle trees in /tmp.
    d = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(zpath) as z: safe_extract_all(z, d)  # fail-closed: reject ../ and absolute members
        # v9.7.371 fix: the old "for dd,_,ff in os.walk(d): ... root = dd; break" loop here was
        # dead code -- its result was immediately overwritten, unused, by the next.() line below.
        # Removed; the next() line already correctly (and more precisely -- it checks for a real
        # "mamey" SUBDIRECTORY, not just any dir entry named "mamey") locates the tree root.
        root = next((dp for dp,_,_ in os.walk(d) if os.path.isdir(os.path.join(dp,"mamey"))), d)
        def rd(p):
            fp = os.path.join(root, p)
            return open(fp, encoding="utf-8", errors="replace").read() if os.path.exists(fp) else None
        basename = os.path.basename(zpath)
        try:
            tier = tier_of(basename)
            tier_name_finding = None
        except TierArchiveNameError as exc:
            tier = "?"
            tier_name_finding = {"code": exc.code, "archive": basename, "message": str(exc)}
        info = {"tier": tier, "zip": basename, "tier_name_finding": tier_name_finding}
        # version
        cit = rd("CITATION.cff") or ""
        m = re.search(r"(?m)^version:\s*[\"']?([0-9][0-9.]+)", cit)
        info["version"] = m.group(1) if m else "?"
        # cassettes
        cass = (rd("mamey/mamey_cassettes.py") or "") + (rd("mamey/sapote_cassettes.py") or "")
        info["cassette_real_ids"] = len(set(re.findall(r"[MS]MC-[A-Z]*-?\d{3}", cass)))
        info["cassette_placeholders"] = len(PLACEHOLDER_RE.findall(cass))
        # markers
        mk = (rd("mamey/mamey_markers.py") or "") + (rd("mamey/sapote_markers.py") or "")
        info["marker_ids"] = len(set(re.findall(r"[MS]MK-[A-Z]+-\d+", mk)))
        # registry + manifests
        info["registry_present"] = os.path.exists(os.path.join(root, "registry_inventory_v1.9.4.json"))
        info["manifests_missing"] = [f for f in MANIFEST_FILES if not os.path.exists(os.path.join(root, f))]
        return info
    finally:
        shutil.rmtree(d, ignore_errors=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tiers-dir"); ap.add_argument("--zips", nargs="*"); ap.add_argument("--json", action="store_true"); ap.add_argument("--receipt-out", default=None)
    ap.add_argument("--with-public", action="store_true",
                    help="require exactly one governance-gated PUBLIC-RELEASE tier")
    a = ap.parse_args()
    zips = a.zips or (sorted(glob.glob(os.path.join(a.tiers_dir, "*.zip"))) if a.tiers_dir else [])
    if not zips: emit("no tier zips given", file=sys.stderr); sys.exit(2)
    tiers = [inspect(z) for z in zips]
    findings = []
    typed_findings = [t["tier_name_finding"] for t in tiers if t["tier_name_finding"]]
    # A parity comparison over an incomplete set is not a release-tier gate. The public promotion
    # is governance-gated and therefore optional here, but every ordinary candidate tier is
    # mandatory. Reject unknown and duplicate labels too: both make set identity ambiguous.
    labels = [t["tier"] for t in tiers]
    required_tiers = REQUIRED_TIERS | ({"public"} if a.with_public else set())
    missing = sorted(required_tiers - set(labels))
    if missing:
        findings.append(f"TIER set incomplete; missing required tier(s): {missing}")
    unknown = [t["zip"] for t in tiers if t["tier"] == "?"]
    if unknown:
        findings.append(f"TIER set contains unrecognized archive(s): {unknown}")
    duplicates = sorted(label for label in set(labels) if label != "?" and labels.count(label) > 1)
    if duplicates:
        findings.append(f"TIER set contains duplicate tier label(s): {duplicates}")
    # version parity
    vers = {t["version"] for t in tiers}
    if len(vers) > 1: findings.append(f"VERSION skew across tiers: {sorted(vers)}")
    # cassette parity
    real = {t["cassette_real_ids"] for t in tiers}
    if len(real) > 1: findings.append(f"CASSETTE real-ID count differs across tiers: " + ", ".join(f"{t['tier']}={t['cassette_real_ids']}" for t in tiers))
    for t in tiers:
        if t["cassette_placeholders"]: findings.append(f"{t['tier']}: {t['cassette_placeholders']} cassette PLACEHOLDER id(s) — fix did not propagate")
    # marker parity
    mk = {t["marker_ids"] for t in tiers}
    if len(mk) > 1: findings.append("MARKER count differs across tiers: " + ", ".join(f"{t['tier']}={t['marker_ids']}" for t in tiers))
    # manifests
    for t in tiers:
        if t["manifests_missing"]: findings.append(f"{t['tier']}: missing enforcement file(s): {t['manifests_missing']}")
    # registry expectation
    for t in tiers:
        exp = t["tier"] in REGISTRY_EXPECTED
        if exp and not t["registry_present"]: findings.append(f"{t['tier']}: registry_inventory MISSING (expected in this tier)")
    ok = not findings
    receipt = {"schema_version": "tier_parity_receipt_v1", "status": "PASS" if ok else "FAIL", "pass": ok, "required_tiers": sorted(required_tiers), "optional_promotion_tiers": sorted(OPTIONAL_PROMOTION_TIERS), "tiers": tiers, "findings": findings, "typed_findings": typed_findings}
    if a.receipt_out:
        outp = os.path.abspath(a.receipt_out)
        os.makedirs(os.path.dirname(outp) or ".", exist_ok=True)
        with open(outp, "w", encoding="utf-8") as fh:
            json.dump(receipt, fh, indent=2)
    if a.json:
        emit(json.dumps(receipt, indent=2))
    else:
        emit(f"Tier parity — {'PASS' if ok else 'FAIL'}  ({len(tiers)} tiers)")
        hdr = f"  {'tier':8} {'ver':8} {'cass':5} {'plc':4} {'mark':5} {'reg':4} manifests"
        emit(hdr)
        for t in tiers:
            emit(f"  {t['tier']:8} {t['version']:8} {t['cassette_real_ids']:<5} {t['cassette_placeholders']:<4} {t['marker_ids']:<5} {('Y' if t['registry_present'] else '-'):4} {'OK' if not t['manifests_missing'] else 'MISSING:'+','.join(t['manifests_missing'])}")
        for f in findings: emit(f"  ✗ {f}")
        if ok: emit("  ✓ version, cassette IDs, markers, manifests, and registry expectations all consistent")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
