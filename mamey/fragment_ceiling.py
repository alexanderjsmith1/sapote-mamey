"""
fragment_ceiling.py — engine-side fragment claim-ceiling for Mamey.

Wires into antismash_evidence.py immediately AFTER the MIBiG-reference ceiling is set
(currently line ~1031). If a large-backbone compound is named on a sub-45kb Edge/FC
fragment, the product-level ceiling is downgraded to class-capacity, because the fragment
physically cannot encode the backbone. This prevents product-level over-calls (teicoplanin,
UK-68,597, friulimicin, nystatin, enduracidin on truncated fragments) at extraction time.

Designed to be conservative: only trips on a curated large-backbone keyword set, only on
fragments (Edge/Full-contig), only below the size floor. Interior clusters and small
non-backbone compounds (e.g. lanthipeptides) never trip.
"""

# Curated large multi-module NRPS/PKS backbones. A <45kb fragment cannot encode these.
LARGE_BACKBONE_KEYWORDS = (
    # glycopeptides
    "teicoplanin", "vancomycin", "balhimycin", "uk-68", "a-47934", "a47934",
    "chloroeremomycin", "ristocetin", "complestatin", "kistamicin",
    # lipo-glyco / Ca-dependent lipopeptides
    "enduracidin", "ramoplanin", "friulimicin", "daptomycin", "a54145", "cda1", "cda2", "cda3", "cda4", "calcium-dependent antibiotic",
    "skyllamycin",
    # large polyene / modular PKS macrolides
    "nystatin", "amphotericin", "candicidin", "pimaricin", "rapamycin", "fk506",
    "niddamycin", "nanchangmycin", "avermectin", "rimocidin", "filipin",
    "stambomycin", "lydicamycin", "notonesomycin", "clethramycin", "linearmycin",
    # large NRPS lipopeptides
    "stenothricin",
)
FRAGMENT_BOUNDARIES = frozenset({"Edge", "Full-contig", "FC"})
BACKBONE_MIN_KB = 45.0
DOWNGRADE_CEILING = "class-capacity only (fragment too small for named backbone; do not use product name)"


# ---- size-ratio path: read the MATCHED reference cluster's real size instead of a curated keyword list ----
# The MIBiG reference index carries a real per-cluster size_kb (size_kb_is_proxy=False). Any reference cluster
# at/above the backbone floor that is named on a sub-floor Edge/FC fragment cannot be encoded by that fragment
# — regardless of whether the compound is in LARGE_BACKBONE_KEYWORDS. This generalises the keyword list and
# self-maintains. The keyword list remains a fallback for when no reference size is available.
import os as _os
import json as _json


def _loadj(p):   # B1: context-managed json load (no leaked handle); +utf-8 (B2)
    with open(p, encoding="utf-8") as _f:
        return _json.load(_f)


_REFERENCE_SIZES = None  # lazy {accession_stem: size_kb}


def _load_reference_sizes():
    global _REFERENCE_SIZES
    if _REFERENCE_SIZES is not None:
        return _REFERENCE_SIZES
    sizes = {}
    # v9.7.371 fix: was hardcoded to mamey/data/mibig/ (the pre-v9.7.362 in-tree path) only. The
    # external-data reform (external_data.py) moved MIBiG provisioning to a user-supplied dataset
    # resolved via MAMEY_MIBIG_DIR / $MAMEY_DATA_ROOT/mibig / the legacy in-tree path (in that
    # order) -- but this module was never updated to use it, unlike its sibling
    # mibig_neighborhoods_api.py, which does. Since mamey/data/mibig/ is never shipped post-reform,
    # this module's PREFERRED, more-accurate size-ratio path was permanently unreachable for any
    # operator who correctly provisions MIBiG data the documented way (MAMEY_MIBIG_DIR /
    # MAMEY_DATA_ROOT) rather than the superseded in-tree location -- it silently fell back to the
    # less-accurate keyword-only matching path every time, indistinguishable from "no MIBiG data
    # provisioned at all".
    try:
        from . import external_data as _xd
        base_path = _xd.resolve("mibig")
    except Exception:
        base_path = None
    if base_path is None:
        # No MIBiG dataset provisioned by any resolution order -- legitimate degrade, not an error.
        _REFERENCE_SIZES = sizes
        return sizes
    base = str(base_path)
    for fn in ("mibig_reference_index.bacterial.json", "mibig_reference_index.fungal.json"):
        fp = _os.path.join(base, fn)
        try:
            idx = _loadj(fp)
        except Exception as exc:
            # A provisioned dataset that fails to load (corrupt/malformed) IS worth a breadcrumb --
            # unlike the file simply not existing, which the resolve()-returns-None branch above
            # already handles as an expected, silent degrade.
            from . import degradation as _degradation
            _degradation.record("fragment_ceiling._load_reference_sizes.parse", exc, file=fp)
            continue
        for e in idx.get("entries", []):
            acc = str(e.get("accession") or "").split(".")[0]   # BGC0000440.5 -> BGC0000440
            sig = e.get("architecture_signature") or {}
            sz = sig.get("size_kb")
            if acc and isinstance(sz, (int, float)) and not sig.get("size_kb_is_proxy", False):
                sizes[acc] = float(sz)
    _REFERENCE_SIZES = sizes
    return sizes


def reference_size_kb_for(accession):
    """Real cluster size (kb) for a MIBiG accession, or None. Version-suffix tolerant."""
    if not accession:
        return None
    return _load_reference_sizes().get(str(accession).split(".")[0])


def fragment_claim_ceiling(product_name, edge_status, length_kb, reference_size_kb=None):
    """Return (should_downgrade: bool, reason: str|None).

    product_name      : closest_candidate_kcb_product (str)
    edge_status       : 'Interior' | 'Edge' | 'Full-contig'
    length_kb         : observed cluster length in kb (float)
    reference_size_kb : real size of the matched MIBiG reference cluster (kb), if known
    """
    name = str(product_name or "").lower()
    try:
        kb = float(length_kb or 0)
    except (TypeError, ValueError):
        kb = 0.0
    frag = str(edge_status) in FRAGMENT_BOUNDARIES

    # (1) size-ratio path (preferred): the matched reference is itself a large backbone (>= floor),
    # and the observed fragment is below the floor -> it cannot encode the reference backbone.
    try:
        ref = float(reference_size_kb) if reference_size_kb else 0.0
    except (TypeError, ValueError):
        ref = 0.0
    if ref >= BACKBONE_MIN_KB and frag and 0 < kb < BACKBONE_MIN_KB:
        first = name.split("/")[0] or "named"
        return True, (f"{kb:.1f}kb {edge_status} too small for the {ref:.0f}kb {first} reference cluster "
                      f"(reference-size path; >= {BACKBONE_MIN_KB}kb required)")

    # (2) keyword fallback: no/short reference size available, but a curated large-backbone name is present.
    if (any(kw in name for kw in LARGE_BACKBONE_KEYWORDS) and frag and 0 < kb < BACKBONE_MIN_KB):
        first = name.split("/")[0]
        return True, f"{kb:.1f}kb {edge_status} too small for {first} backbone (>= {BACKBONE_MIN_KB}kb required)"
    return False, None


def apply_to_bgc(bgc):
    """Mutate a BGCRecord in place if the fragment ceiling trips. Returns the reason or None.

    Call AFTER the MIBiG-reference block sets product_claim_ceiling. Sets:
      - product_claim_ceiling -> DOWNGRADE_CEILING
      - needs_manual_kcb_check -> 'yes'
    and stamps a note. Leaves the named product/accession intact for provenance, but the
    ceiling now forbids product-level use.
    """
    name = getattr(bgc, "closest_candidate_kcb_product", "") or ""
    if (not name) or name == "UNRESOLVED":
        name = getattr(bgc, "kcb_top", "") or ""   # source-derived path keeps the product in kcb_top
    edge = getattr(bgc, "edge_status", "Full-contig")
    kb = getattr(bgc, "length_kb", None)
    kb = kb() if callable(kb) else (kb if kb is not None else round((getattr(bgc,"end",0)-getattr(bgc,"start",0))/1000, 2))
    ref_kb = reference_size_kb_for(getattr(bgc, "closest_mibig_accession", None))
    trip, reason = fragment_claim_ceiling(name, edge, kb, reference_size_kb=ref_kb)
    if trip:
        bgc.product_claim_ceiling = DOWNGRADE_CEILING
        bgc.needs_manual_kcb_check = "yes"
        # bgc.notes may be a list or a str depending on the model; append type-safely.
        note = f"FRAGMENT_CEILING: {reason}"
        prev = getattr(bgc, "notes", None)
        if isinstance(prev, list):
            prev.append(note)
        elif prev:
            bgc.notes = f"{prev} | {note}"
        else:
            bgc.notes = note
        return reason
    return None
