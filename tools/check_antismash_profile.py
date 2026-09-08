#!/usr/bin/env python3
"""
check_antismash_profile.py — cross-profile pooling guard.

Reads antismash_profile from each strain's manifest.json (the run handoff object) and refuses to
certify a cohort for comparative/ecological claims when strains were run under DIFFERENT antiSMASH
hmmdetection profiles, or when any profile is 'unknown'. Detection strictness changes which marginal
clusters are called, so pooling across profiles silently confounds cross-habitat counts.

Usage: check_antismash_profile.py <packages_root> [--warn-only]
  Scans <packages_root> for manifest.json files.
Exit: 0 = one known profile across all strains; 1 = mixed or any unknown (unless --warn-only).
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, json, sys
from pathlib import Path

def collect(root: Path) -> dict:
    # v9.7.374: an unreadable/corrupt manifest.json (truncated write, disk-full, interrupted run)
    # used to `continue` silently -- the strain vanished from the pool entirely instead of failing
    # closed, so a genuinely mixed-profile cohort could certify OK if the one manifest that would
    # have exposed the mismatch happened to be the corrupt one. Record it as "unknown" (its parent
    # dir name as the strain key) so it flows through the existing mixed/unknown fail-closed path
    # instead of disappearing.
    out = {}
    for mp in sorted(root.rglob("manifest.json")):
        try:
            d = json.loads(mp.read_text(encoding="utf-8"))
        except Exception as exc:
            strain = mp.parent.name
            out[strain] = "unknown"
            emit(f"  WARNING: unreadable manifest {mp} ({type(exc).__name__}: {exc}) -- treated as unknown",
                  file=sys.stderr)
            continue
        strain = d.get("strain") or d.get("strain_id") or mp.parent.name
        out[strain] = d.get("antismash_profile", "unknown")
    return out

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Cross-profile pooling guard.")
    ap.add_argument("root"); ap.add_argument("--warn-only", action="store_true")
    a = ap.parse_args(argv)
    profiles = collect(Path(a.root))
    if not profiles:
        # v9.7.116: empty input fails closed, not a vacuous pass. A pooling guard that finds zero
        # manifests almost always means a wrong path, and returning 0 (safe-to-pool) is the wrong
        # default — mirrors the cohort_scoring_version_gate empty-fail fix. --warn-only still softens.
        emit(f"  no manifest.json found under {a.root} — cannot certify a cohort that isn't there",
              file=sys.stderr)
        return 0 if a.warn_only else 1
    for s in sorted(profiles): emit(f"  {s:<18} {profiles[s]}")
    distinct = sorted(set(profiles.values()))
    unknown = [s for s, p in profiles.items() if p == "unknown"]
    mixed = len([p for p in distinct if p != "unknown"]) > 1
    if not mixed and not unknown:
        emit(f"OK  single profile across {len(profiles)} strain(s): {distinct[0]}"); return 0
    parts = []
    if mixed: parts.append(f"MIXED antiSMASH profiles {distinct}")
    if unknown: parts.append(f"UNKNOWN for {len(unknown)} strain(s): {unknown[:8]}")
    emit("UNSAFE TO POOL — " + " ; ".join(parts), file=sys.stderr)
    return 0 if a.warn_only else 1

if __name__ == "__main__": raise SystemExit(main())
