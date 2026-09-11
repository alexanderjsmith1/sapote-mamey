"""genus_reference.py — read-only access to shipped genus reference banks (v9.7.99).

The first bank is Nocardia: 7 public, published genomes run through Mamey 1.9.96, shipped under  # version-sync-ok (Nocardia bank provenance: scored at 1.9.96, a historical fact)
mamey/data/nocardia/ as a claim-safe comparative reference. This is Layer A of the specialization
plan — empirical genus baselines earned from cohort data, never seeded from memory.

Claim-safety (unchanged): these are capacity-level, KCB=similarity-not-identity, public reference rows.
A genus baseline sharpens priors and sensitivity; it never licenses "this BGC IS [compound]".

Version discipline: the reference rows are stamped with the engine that scored them (engine_version).
`assert_comparable_with(current_engine)` is the hook a comparative build uses to refuse pooling this
bank with a different-engine cohort — the class-prevalence baseline (counts) is engine-robust, but the
AB/AF *capacity scores* are engine-pinned and must be re-scored on a boundary bump before pooling.
"""
from __future__ import annotations
import csv
import json
from pathlib import Path

_DATA = Path(__file__).resolve().parent / "data" / "nocardia"
_REFERENCE = _DATA / "nocardia_reference.csv"
_PREVALENCE = _DATA / "nocardia_class_prevalence.csv"

# Classes excluded from comparative claims by standing rule (must already be release-flagged in the CSV;
def _registry_excluded_classes() -> frozenset:
    """Derive the comparative-exclusion class set from the rules registry (the SSOT).

    A class is comparative-excluded when its registry entry is ``status == "excluded"``
    or ``action == "drop"``. The registry keys decisions by free-text *patterns*, not by
    the ``bgc_class`` enum tokens used in the reference bank, so we bind the relevant
    registry IDs to their class tokens explicitly here. This keeps the *decision* in the
    registry (flip an entry's status there and it propagates) while making the
    pattern->token mapping auditable rather than a fragile regex match against enum values.

    Why this matters (v9.7.101, P3): the previous hardcoded set
    ``{saccharide, fatty_acid, NAPAA, hgle-ks}`` had drifted from the registry -- it
    excluded NAPAA (now registry-neutral) and hgle-ks (registry "noted/flag", not
    excluded). Deriving from the registry corrects both automatically.
    """
    # registry ID -> the bgc_class token(s) it governs in the reference bank
    _ID_TO_CLASS = {
        "SACCHARIDE": {"saccharide"},
        "PRIMARY-METABOLISM": {"fatty_acid"},
        # HGLE-KS-PREV-001 is registry "noted/flag" (NOT excluded) -- intentionally absent.
        # NAPAA is registry "neutral" -- intentionally absent.
        # BRYO-HGT-001 is retired/drop but is not a bgc_class token in the bank -- no binding.
    }
    excluded = set()
    try:
        reg = json.loads((Path(__file__).resolve().parent / "data" / "rules_registry.json").read_text(encoding="utf-8"))

        def _walk(o):
            if isinstance(o, dict):
                if "id" in o and ("status" in o or "action" in o):
                    if o.get("status") == "excluded" or o.get("action") == "drop":
                        excluded.update(_ID_TO_CLASS.get(o["id"], set()))
                for v in o.values():
                    _walk(v)
            elif isinstance(o, list):
                for v in o:
                    _walk(v)
        _walk(reg)
    except Exception:
        # Registry unreadable: fall back to the known-safe minimal set and proceed.
        return frozenset({"saccharide", "fatty_acid"})
    # Defensive floor: saccharide + fatty_acid are permanent primary-metabolism exclusions.
    excluded.update({"saccharide", "fatty_acid"})
    return frozenset(excluded)


# Derived from the rules-registry SSOT (was a hardcoded frozenset through v9.7.100; see
# _registry_excluded_classes for why the hardcode drifted). Defensive second filter so a
# consumer can't accidentally include an excluded class.
STANDING_EXCLUSIONS = _registry_excluded_classes()


def _read(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"genus reference bank file missing: {path}")
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_nocardia_reference(comparative_only: bool = True) -> list[dict]:
    """Return the Nocardia reference rows. comparative_only honors comparative_eligible + standing exclusions."""
    rows = _read(_REFERENCE)
    if comparative_only:
        rows = [r for r in rows
                if r.get("comparative_eligible") == "True"
                and r.get("bgc_class") not in STANDING_EXCLUSIONS]
    return rows


def nocardia_class_prevalence() -> list[dict]:
    """Layer-A baseline: per comparative-eligible class, how many of the cohort carry it (engine-robust)."""
    return _read(_PREVALENCE)


def genus_core_classes() -> list[str]:
    """Classes present in every strain of the cohort (claim as recurrent capacity, never shared product).

    The ``other`` residual bucket is excluded: it is a catch-all for unclassified loci, so its
    appearing in 7/7 strains reflects "every strain has *some* unclassified BGC", not a shared
    biosynthetic class. Reporting it as genus-core would be a false invariant (P16, v9.7.101).
    """
    _RESIDUAL = {"other"}
    return [r["bgc_class"] for r in nocardia_class_prevalence()
            if r.get("genus_core_7of7") == "True" and r["bgc_class"] not in _RESIDUAL]


def reference_engine_version() -> str:
    """The engine the bank was scored under (all rows share one; that uniformity is itself an invariant)."""
    versions = {r["engine_version"] for r in _read(_REFERENCE)}
    if len(versions) != 1:
        raise ValueError(f"Nocardia bank spans multiple engine versions {versions} — not a valid reference")
    return next(iter(versions))


def assert_comparable_with(current_engine: str) -> None:
    """Refuse to pool the bank's CAPACITY SCORES with a cohort scored under a different engine.

    Raises ValueError on a boundary mismatch. The class-prevalence baseline (counts) is engine-robust
    and is not gated by this; only AB/AF capacity-score pooling is. Mirrors cohort_scoring_version_gate.
    """
    ref = reference_engine_version()
    if ref != current_engine:
        raise ValueError(
            f"Nocardia reference bank was scored at engine {ref}, current engine is {current_engine}. "
            f"Class prevalence is still usable, but AB/AF capacity scores must be re-scored under "
            f"{current_engine} before comparative pooling (boundary bump → re-score)."
        )
