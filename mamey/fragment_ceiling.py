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


# Typed guard states. UNKNOWN means a named backbone could trip the guard but the fragment
# metadata needed to decide (edge status, measured length) is absent or invalid. It is neither
# a pass (CLEAR) nor a trip (TRIPPED). Same vocabulary as mode_b FRAGMENT_CEILING_STATES.
CEILING_CLEAR = "CLEAR"
CEILING_TRIPPED = "TRIPPED"
CEILING_UNKNOWN = "UNKNOWN"
ADMITTED_EDGE_STATUSES = FRAGMENT_BOUNDARIES | {"Interior"}
UNVERIFIED_PREFIX = "METADATA_UNVERIFIED"


def _measured_kb(length_kb):
    """Finite positive length in kb, or None when the length is absent or invalid."""
    if length_kb is None or isinstance(length_kb, bool):
        return None
    try:
        kb = float(length_kb)
    except (TypeError, ValueError):
        return None
    if kb != kb or kb in (float("inf"), float("-inf")) or kb <= 0:
        return None
    return kb


def fragment_ceiling_state(product_name, edge_status, length_kb, reference_size_kb=None):
    """Return (state, reason) with state CLEAR, TRIPPED or UNKNOWN.

    The guard only applies when a large backbone is named: the matched reference is at or above
    the floor, or a curated large-backbone keyword is present. Then an absent or unadmitted edge
    status, or an absent, non-finite, zero or negative length on a fragment, gives UNKNOWN with a
    METADATA_UNVERIFIED reason instead of a silent no-trip.
    """
    name = str(product_name or "").lower()
    try:
        ref = float(reference_size_kb) if reference_size_kb else 0.0
    except (TypeError, ValueError):
        ref = 0.0
    by_reference = ref >= BACKBONE_MIN_KB
    by_keyword = any(kw in name for kw in LARGE_BACKBONE_KEYWORDS)
    if not (by_reference or by_keyword):
        return CEILING_CLEAR, None
    edge = str(edge_status).strip() if edge_status is not None else ""
    if edge not in ADMITTED_EDGE_STATUSES:
        return CEILING_UNKNOWN, (f"{UNVERIFIED_PREFIX}: edge status {edge_status!r} not admitted; "
                                 f"fragment ceiling not evaluated")
    if edge not in FRAGMENT_BOUNDARIES:
        return CEILING_CLEAR, None
    kb = _measured_kb(length_kb)
    if kb is None:
        return CEILING_UNKNOWN, (f"{UNVERIFIED_PREFIX}: cluster length {length_kb!r} is not a finite "
                                 f"positive measurement; fragment ceiling not evaluated")

    # (1) size-ratio path (preferred): the matched reference is itself a large backbone (>= floor),
    # and the observed fragment is below the floor -> it cannot encode the reference backbone.
    if by_reference and kb < BACKBONE_MIN_KB:
        first = name.split("/")[0] or "named"
        return CEILING_TRIPPED, (f"{kb:.1f}kb {edge_status} too small for the {ref:.0f}kb {first} reference cluster "
                                 f"(reference-size path; >= {BACKBONE_MIN_KB}kb required)")

    # (2) keyword fallback: no/short reference size available, but a curated large-backbone name is present.
    if by_keyword and kb < BACKBONE_MIN_KB:
        first = name.split("/")[0]
        return CEILING_TRIPPED, f"{kb:.1f}kb {edge_status} too small for {first} backbone (>= {BACKBONE_MIN_KB}kb required)"
    return CEILING_CLEAR, None


def fragment_claim_ceiling(product_name, edge_status, length_kb, reference_size_kb=None):
    """Return (should_downgrade: bool, reason: str|None).

    product_name      : closest_candidate_kcb_product (str)
    edge_status       : 'Interior' | 'Edge' | 'Full-contig'
    length_kb         : observed cluster length in kb (float)
    reference_size_kb : real size of the matched MIBiG reference cluster (kb), if known

    (False, None) is an evaluated no-trip. (False, 'METADATA_UNVERIFIED: ...') means the guard
    could not be evaluated; fragment_ceiling_state() gives the typed state.
    """
    state, reason = fragment_ceiling_state(product_name, edge_status, length_kb, reference_size_kb)
    return state == CEILING_TRIPPED, reason


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
    edge = getattr(bgc, "edge_status", None)   # missing edge metadata stays missing, not Full-contig
    kb = getattr(bgc, "length_kb", None)
    if callable(kb):
        kb = kb()
    elif kb is None and getattr(bgc, "start", None) is not None and getattr(bgc, "end", None) is not None:
        kb = round((bgc.end - bgc.start) / 1000, 2)
    ref_kb = reference_size_kb_for(getattr(bgc, "closest_mibig_accession", None))
    state, reason = fragment_ceiling_state(name, edge, kb, reference_size_kb=ref_kb)
    if state == CEILING_TRIPPED:
        bgc.product_claim_ceiling = DOWNGRADE_CEILING
        bgc.needs_manual_kcb_check = "yes"
        _append_note(bgc, f"FRAGMENT_CEILING: {reason}")
        return reason
    if state == CEILING_UNKNOWN:
        # Neither a pass nor a trip: keep the ceiling, hold for manual check, and record why.
        bgc.needs_manual_kcb_check = "yes"
        _append_note(bgc, f"FRAGMENT_CEILING_{reason}")
    return None


def _append_note(bgc, note):
    # bgc.notes may be a list or a str depending on the model; append type-safely.
    prev = getattr(bgc, "notes", None)
    if isinstance(prev, list):
        prev.append(note)
    elif prev:
        bgc.notes = f"{prev} | {note}"
    else:
        bgc.notes = note
