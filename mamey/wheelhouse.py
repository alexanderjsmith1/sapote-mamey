"""wheelhouse.py — CLI for the Wheelhouse/ lab-data store (strains, scanners, validations).

The Wheelhouse is DATA, not pipeline code: a round-trippable folder of lab-specific knowledge
(strain registry, scanner registry, validation answer-keys, the pyHMMER scanner engine, reports).
It lives at bundle root and is excluded from the test suite. This module gives it light
lifecycle commands:

  mamey wheelhouse list                 — summarize strains + scanners + validations
  mamey wheelhouse clean [--apply]      — prune superseded scanner-registry versions + dup records
                                          (dry-run by default; --apply writes)
  mamey wheelhouse add-strain <json>    — merge a strain record into strains/strain_registry.json

Scanner semantics (from the pyHMMER scanner work): a raw HMM domain hit is NOT a scanner hit.
Each scanner carries a cluster-level GATE (per-region domain count / co-occurrence) that must
fire for the scanner to count. The engine (engine/pyhmmer_scanner_engine.py) builds the HMMs;
the gate rules live in the scanner registry. This module only manages the data, it does not
run scans (that needs the addon stack: pyhmmer + pyfamsa).
"""

from __future__ import annotations

from .logging_setup import get_logger

_log = get_logger(__name__)

import json
import os
from pathlib import Path


def _wh_root(bundle_root: Path) -> Path:
    return Path(bundle_root) / "Wheelhouse"


def _load_json(path: Path):
    with open(path) as fh:
        return json.load(fh)


def resolve_hmm_database(bundle_root: Path | None = None) -> dict:
    """Locate the best available Pfam HMM database across the three reference tiers, per the
    scanner three-tier model. Prefers the larger 148-family set (addon) when present, falls
    back to the 35-family core (bundle Wheelhouse). Returns {path, n_models_hint, tier, reason}.
    The engine degrades gracefully to whatever is present.

    Tiers:
      1. bundle Wheelhouse/hmm/scanner_pfam.hmm      — 35 core models (always in the bundle)
      2. addon sapote_addons/hmm/scanner_pfam_150.hmm — 148 empirical families (heavy, in the addon)
    """
    if bundle_root is None:
        bundle_root = Path(__file__).resolve().parent.parent
    here = Path(bundle_root).resolve()
    # An explicit override wins (set when the addon lives somewhere non-standard).
    env = os.environ.get("SM_HMM_DB")
    if env and os.path.exists(env):
        n = 148 if "150" in os.path.basename(env) else 35
        return {"path": env, "n_models_hint": n, "tier": "env-override", "reason": f"SM_HMM_DB={env}"}
    # Resolution order (predictable, self-contained-bundle-first):
    #   1. SM_HMM_DB env override
    #   2. bundle-local 148 (a bundle carrying its own large set is authoritative)
    #   3. addon 148 (documented side-by-side layout)
    #   4. bundle-local 35 core (always shipped)
    p = here / "Wheelhouse" / "hmm" / "scanner_pfam_150.hmm"
    if p.exists():
        return {"path": str(p.resolve()), "n_models_hint": 148, "tier": "wheelhouse-148",
                "reason": "using bundle-local 148-family HMM database"}
    # v9.7.187: the addon was renamed gemini_stack* -> sapote_addons*. Discover the HMM data by
    # globbing for any addon dir carrying hmm/scanner_pfam_150.hmm, so the fixed name doesn't matter
    # (mirrors the npatlas_resolver discovery). Old gemini_stack names still resolve for back-compat.
    _roots = (here.parent, here, here.parent.parent)
    for root in _roots:
        for sub in ("sapote_addons/hmm", "sm_addons/sapote_addons/hmm",
                    "gemini_stack/hmm", "sm_addons/gemini_stack/hmm"):
            p = root / sub / "scanner_pfam_150.hmm"
            if p.exists():
                return {"path": str(p.resolve()), "n_models_hint": 148, "tier": "addon-148",
                        "reason": "using addon-148 HMM database"}
    for root in _roots:
        try:
            for cand in list(root.glob("*addons*/hmm/scanner_pfam_150.hmm")) + \
                        list(root.glob("*stack*/hmm/scanner_pfam_150.hmm")) + \
                        list(root.glob("*/hmm/scanner_pfam_150.hmm")):
                if cand.exists():
                    return {"path": str(cand.resolve()), "n_models_hint": 148, "tier": "addon-148",
                            "reason": "using addon-148 HMM database"}
        except Exception:
            continue
    p = here / "Wheelhouse" / "hmm" / "scanner_pfam.hmm"
    if p.exists():
        return {"path": str(p.resolve()), "n_models_hint": 35, "tier": "wheelhouse-35",
                "reason": "using wheelhouse-35 core HMM database"}
    return {"path": None, "n_models_hint": 0, "tier": "none",
            "reason": "no Pfam HMM database found (attach the addon or check Wheelhouse/hmm/)"}


def wheelhouse_command(args) -> int:
    bundle_root = Path(__file__).resolve().parent.parent  # mamey/ -> bundle root
    wh = _wh_root(bundle_root)
    if not wh.exists():
        _log.warning(f"[wheelhouse] not found at {wh} — the Wheelhouse data store is missing from this bundle")
        return 1

    action = getattr(args, "wh_action", None)
    if action == "list":
        return _cmd_list(wh)
    if action == "clean":
        return _cmd_clean(wh, apply=getattr(args, "apply", False))
    if action == "add-strain":
        return _cmd_add_strain(wh, getattr(args, "strain_json", None))
    _log.warning("[wheelhouse] specify an action: list | clean | add-strain")
    return 1


def _cmd_list(wh: Path) -> int:
    strains = wh / "strains" / "strain_registry.json"
    scanners = sorted((wh / "scanners").glob("scanner_registry_v*.json"))
    vals = list((wh / "validations").glob("*.json"))
    if strains.exists():
        s = _load_json(strains)
        srec = s.get("strains", s)
        _log.info(f"[wheelhouse] strains: {len(srec)}")
    for sc in scanners:
        try:
            r = _load_json(sc)
            _log.info(f"[wheelhouse] {sc.name}: {r.get('n_scanners', '?')} scanners "
                  f"(registry {r.get('registry_version', '?')})")
        except Exception:
            _log.info(f"[wheelhouse] {sc.name}: (unreadable)")
    _log.info(f"[wheelhouse] validations: {len(vals)} ({', '.join(v.stem for v in vals)})")
    engine = wh / "engine" / "pyhmmer_scanner_engine.py"
    _log.info(f"[wheelhouse] scanner engine: {'present' if engine.exists() else 'MISSING'} "
          "(needs pyhmmer + pyfamsa from the gemini-stack addon to run)")
    hmm = wh / "hmm" / "scanner_pfam.hmm"
    if hmm.exists():
        sz = hmm.stat().st_size // 1024
        _log.info(f"[wheelhouse] Pfam HMM database (bundle): present ({sz} KB, 35 curated models with gathering cutoffs)")
    resolved = resolve_hmm_database(wh.parent)
    _log.info(f"[wheelhouse] active HMM tier: {resolved['tier']} "
          f"(~{resolved['n_models_hint']} models) — {resolved['reason']}")
    return 0


def _cmd_clean(wh: Path, apply: bool = False) -> int:
    """Prune superseded scanner-registry versions: keep the highest vN, flag older ones.
    Dry-run unless --apply. 'Clean the Wheelhouse' = drop stale/superseded records."""
    scanners = sorted((wh / "scanners").glob("scanner_registry_v*.json"))
    if len(scanners) <= 1:
        _log.info("[wheelhouse] nothing to prune (0-1 scanner registries)")
        return 0

    def _ver(p: Path) -> tuple:
        import re
        m = re.search(r"v(\d+)\.(\d+)", p.name)
        return (int(m.group(1)), int(m.group(2))) if m else (0, 0)

    latest = max(scanners, key=_ver)
    superseded = [p for p in scanners if p != latest]
    _log.info(f"[wheelhouse] latest scanner registry: {latest.name} (kept)")
    for p in superseded:
        _log.info(f"[wheelhouse] superseded: {p.name}" + ("  → removing" if apply else "  (dry-run; --apply to remove)"))
        if apply:
            p.unlink()
    if not apply and superseded:
        _log.info("[wheelhouse] dry-run only — re-run with --apply to prune")
    return 0


def _cmd_add_strain(wh: Path, strain_json: str | None) -> int:
    if not strain_json or not os.path.exists(strain_json):
        _log.warning(f"[wheelhouse] provide a valid strain JSON file (got: {strain_json})")
        return 1
    reg_path = wh / "strains" / "strain_registry.json"
    reg = _load_json(reg_path) if reg_path.exists() else {"strains": {}}
    new = _load_json(Path(strain_json))
    container = reg.get("strains", reg)
    # new record may be a single strain dict keyed by id, or {id: {...}}
    added = []
    if isinstance(new, dict) and "id" in new:
        container[new["id"]] = new
        added.append(new["id"])
    elif isinstance(new, dict):
        for k, v in new.items():
            container[k] = v
            added.append(k)
    if "strains" in reg:
        reg["strains"] = container
    else:
        reg = container
    with open(reg_path, "w") as fh:
        json.dump(reg, fh, indent=2)
    _log.info(f"[wheelhouse] added/updated strain(s): {', '.join(added)} → {reg_path}")
    return 0
