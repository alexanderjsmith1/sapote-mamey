"""cnbu.py — Class-Normalized BGC Units (v9.7.72).

CNBU = observed_region_length_kb / expected_complete_length_kb_for_primary_class

Purpose: a single BGC contributes up to 1.0 CNBU when it matches the expected size
for its class, more than 1.0 if it is unusually large (capped at CAP), and less if
it is a fragment. Summing CNBU across a strain gives a class-normalized biosynthetic
capacity estimate that is less biased by the presence of many small (e.g. terpene)
or unusually large (e.g. transAT-PKS) clusters.

CNBU does NOT replace the corrected BGC count. It is an optional supplement.

Claim-safety: CNBU is a structural-length metric derived from assembly data and class
reference priors. It does not imply that any compound is produced.

Class priors are curated from MIBiG representative cluster lengths. When a class has
no prior (UNKNOWN_PRIOR), a warning is emitted and that BGC is reported separately.
The calculation proceeds without the unknown BGC rather than failing.
"""
from __future__ import annotations

from typing import Any

# Reference expected complete cluster lengths (kb) per antiSMASH product-class label.
# Conservative lower-bound estimates; classes with wide ranges use the interquartile median.
CLASS_PRIORS_KB: dict[str, float] = {
    "NRPS":                    60.0,
    "NRPS-like":               40.0,
    "PKS":                     50.0,
    "PKS-like":                35.0,
    "T1PKS":                   50.0,
    "T2PKS":                   35.0,
    "T3PKS":                   10.0,
    "transAT-PKS":             85.0,
    "hr-t2pks":                38.0,
    "RiPP":                    12.0,
    "lassopeptide":            14.0,
    "lanthipeptide-class-i":   12.0,
    "lanthipeptide-class-ii":  16.0,
    "lanthipeptide-class-iii": 14.0,
    "lanthipeptide-class-iv":  16.0,
    "azole-containing-RiPP":   16.0,
    "thiopeptide":             30.0,
    "RiPP-like":               10.0,
    "terpene":                 15.0,
    "terpene-precursor":       10.0,
    "NI-siderophore":          20.0,
    "NRP-metallophore":        25.0,
    "saccharide":              30.0,
    "halogenated":             25.0,
    "phosphonate":             18.0,
    "betalactone":             20.0,
    "fatty_acid":              20.0,
    "butyrolactone":            8.0,
    "NAPAA":                   40.0,
    "hglE-KS":                 30.0,
    "ectoine":                  8.0,
    "melanin":                  6.0,
    "nucleoside":              12.0,
    "indole":                  10.0,
    "furan":                    8.0,
    "phenazine":               15.0,
    # "other" intentionally absent — unknown prior
}

UNKNOWN_PRIOR_LABEL = "UNKNOWN_PRIOR"
DEFAULT_CAP = 1.25   # max CNBU contribution per BGC


def _primary_class(products: list[str] | str | None) -> str:
    """Return the first non-trivial product-class token."""
    if isinstance(products, str):
        products = [p.strip() for p in products.split(";") if p.strip()]
    if not products:
        return "other"
    # Prefer specific classes over 'other'/'PKS'/'NRPS' generics when available
    for p in products:
        if p.lower() not in ("other", ""):
            return p.strip()
    return "other"


def compute_cnbu(
    bgcs: list[dict[str, Any]],
    *,
    cap: float = DEFAULT_CAP,
    priors: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Compute CNBU for a list of BGC dicts.

    Each BGC dict must have:
        length_kb:  float or str — observed region length in kb
        products:   str or list  — antiSMASH product class tokens

    Returns:
        {
          "total_cnbu":   float,
          "n_bgcs":       int,
          "n_unknown":    int,
          "unknown_bgcs": [{"bgc_id": ..., "products": ...}, ...],
          "per_bgc":      [{bgc_id, length_kb, primary_class, prior_kb, cnbu, capped}, ...],
          "warnings":     [str, ...],
          "claim_safety": str,
        }
    """
    priors = priors or CLASS_PRIORS_KB
    # v9.7.371 fix: CLASS_PRIORS_KB keys are mixed/upper-case ("NRPS", "T1PKS", ...) but the real
    # antiSMASH product tokens stored on a BGCRecord (parsers.py::_feature_products, confirmed
    # against class_architecture.py's canonical lowercase _REAL_CLASSES set) are lowercase
    # ("nrps", "t1pks", ...). _primary_class() returns the token unchanged, so the exact-case
    # `priors.get(cls)` lookup below silently missed almost every real BGC class, dropping it to
    # UNKNOWN_PRIOR and excluding it from total_cnbu -- the sibling length_weighted.py solves the
    # identical problem with an explicit alias table; this mirrors that with a case-insensitive
    # index instead (no change to the canonical CLASS_PRIORS_KB keys themselves).
    _priors_ci = {k.lower(): v for k, v in priors.items()}
    per_bgc = []
    unknown_bgcs = []
    warnings: list[str] = []
    total = 0.0

    for b in bgcs:
        bgc_id = str(b.get("bgc_id") or b.get("BGC_ID") or "UNKNOWN")
        try:
            length_kb = float(b.get("length_kb") or 0)
        except (TypeError, ValueError):
            length_kb = 0.0
        cls = _primary_class(b.get("products"))
        prior = priors.get(cls)
        if prior is None:
            prior = _priors_ci.get(cls.lower())

        if prior is None:
            unknown_bgcs.append({"bgc_id": bgc_id, "products": cls})
            per_bgc.append({
                "bgc_id": bgc_id, "length_kb": length_kb,
                "primary_class": cls, "prior_kb": UNKNOWN_PRIOR_LABEL,
                "cnbu": UNKNOWN_PRIOR_LABEL, "capped": False,
            })
            continue

        raw_cnbu = length_kb / prior if prior > 0 else 0.0
        capped = raw_cnbu > cap
        cnbu = min(raw_cnbu, cap)
        total += cnbu
        per_bgc.append({
            "bgc_id": bgc_id, "length_kb": length_kb,
            "primary_class": cls, "prior_kb": prior,
            "cnbu": round(cnbu, 3), "capped": capped,
        })

    if unknown_bgcs:
        warnings.append(
            f"{len(unknown_bgcs)} BGC(s) with no class prior (UNKNOWN_PRIOR) excluded "
            f"from CNBU total: " +
            ", ".join(f"{u['bgc_id']} ({u['products']})" for u in unknown_bgcs[:5]) +
            ("…" if len(unknown_bgcs) > 5 else "")
        )

    return {
        "total_cnbu": round(total, 2),
        "n_bgcs": len(bgcs),
        "n_known": len(bgcs) - len(unknown_bgcs),
        "n_unknown": len(unknown_bgcs),
        "cap": cap,
        "unknown_bgcs": unknown_bgcs,
        "per_bgc": per_bgc,
        "warnings": warnings,
        "claim_safety": (
            "CNBU is a structural-length metric (region_kb / expected_class_kb). "
            "It does not imply compound production or bioactivity. "
            "Class priors are reference medians from MIBiG; values are capped at "
            f"{cap} per BGC. UNKNOWN_PRIOR BGCs are excluded from the total."
        ),
    }


def cnbu_from_inventory_csv(inventory_csv_path: str, **kwargs) -> dict[str, Any]:
    """Convenience wrapper: read a Mamey _2_inventory.csv and compute CNBU."""
    import csv
    with open(inventory_csv_path, newline="", encoding="utf-8") as f:
        bgcs = list(csv.DictReader(f))
    return compute_cnbu(bgcs, **kwargs)
