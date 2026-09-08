#!/usr/bin/env python3
"""Validate portable strain privacy and evidence registries without running Mamey."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mamey.evidence_registry import EvidenceRegistryError, validate_evidence_registry
from mamey.privacy_profile import PrivacyProfileError, load_privacy_profile

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--privacy-profile", required=True)
    parser.add_argument("--evidence-registry", required=True)
    args = parser.parse_args(argv)
    try:
        profile = load_privacy_profile(args.privacy_profile)
        evidence = validate_evidence_registry(args.evidence_registry, profile=profile)
    except (PrivacyProfileError, EvidenceRegistryError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"status": "PASS", "profile_id": profile.profile_id, "tier_count": len(profile.tiers), "exact_strain_assignments": len(profile.assignments), "evidence": evidence}, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
