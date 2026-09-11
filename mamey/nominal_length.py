"""mamey/nominal_length.py — BGC length reporting + nominal-length normalization (DRAFT v9.7.104).

WHY. In VERY_POOR / POOR assemblies, most BGC regions are Edge or Full-contig fragments: the antiSMASH
span under-estimates the true cluster size because the cluster runs off the end of a short contig. Reporting
the raw span in kb is still useful, but it is hard to read "11 kb" without a yardstick. This module adds an
OPTIONAL nominal-length normalization: for a fragment whose class matches a known reference cluster, it reports
the observed span as a fraction of that reference's NOMINAL length (e.g. "11.0 kb ≈ 34% of the ~32 kb
polyoxin-class nominal length").

CLAIM-SAFETY (this is the whole reason it's a guarded module, not a bare ratio):
  * "recovery fraction" is span ÷ nominal, NOT "fraction of the strain's true cluster present". The nominal
    length is a REFERENCE cluster's length; the strain's real cluster may be larger or smaller. The output is
    a yardstick for triage, never a completeness claim about the strain.
  * Every nominal entry carries a `confidence` and `confirmed` flag. The polyoxin/nucleoside entry seeded here
    is marked confirmed=False ("unconfirmed polyoxin-class reference") — it is a plausible yardstick from one
    characterised cluster (EU158805.1, S. cacaoi polyoxin), not a validated class constant.
  * A fragment longer than its nominal reference is reported as ">100% (exceeds nominal; reference may be
    smaller than this cluster)", never silently clipped — an over-100% value is itself information.
  * Interior (non-fragment) BGCs are reported in kb only; nominal normalization is for Edge/Full-contig
    fragments where the span is known to be a truncation.

Deterministic; no LLM; capacity-level language only.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class NominalReference:
    """A nominal cluster length for a compound class, with provenance and confidence."""
    label: str                 # human label, e.g. "polyoxin-class (nucleoside)"
    nominal_kb: float          # nominal full-cluster length in kb
    classes: tuple             # antiSMASH product tokens this applies to (lowercased)
    source_accession: str      # the reference cluster the nominal came from
    confidence: str            # HIGH / MODERATE / LOW
    confirmed: bool = False    # False = unconfirmed yardstick, not a validated class constant
    note: str = ""
    members: tuple = ()        # accessions the nominal is derived from (provenance for the yardstick)
    nominal_range_kb: tuple = ()  # (min_kb, max_kb) observed across members; () when single-member


# Seed registry. Lengths are antiSMASH-region spans of characterised reference clusters, used as
# yardsticks only. Add entries as references are run; keep confirmed=False until a class length is
# validated across multiple members.
NOMINAL_REFERENCES: tuple = (
    NominalReference(
        label="polyoxin-class (nucleoside / peptidyl-nucleoside)",
        nominal_kb=30.0,                         # 2-member mean of antiSMASH region spans (27.9, 32.0)
        classes=("nucleoside", "polyoxin", "peptidyl-nucleoside"),
        source_accession="EU158805.1; JN674503.1",
        confidence="MODERATE",
        confirmed=False,
        members=("EU158805.1", "JN674503.1"),
        nominal_range_kb=(27.9, 32.0),
        note="Unconfirmed polyoxin-class reference from TWO characterised polyoxin clusters: "
             "EU158805.1 (S. cacaoi/asoensis, region 32.0 kb) and JN674503.1 (S. aureochromogenes, "
             "region 27.9 kb); both KCB polyoxin A/H = BGC0000877. Nominal = 2-member mean 30.0 kb "
             "(observed range 27.9-32.0 kb, ~14% spread; full GenBank records 43.2-46.1 kb). Yardstick for "
             "nucleoside/peptidyl-nucleoside fragments (e.g. nikkomycin-type leads). STILL UNCONFIRMED: n=2, "
             "both polyoxin (not nikkomycin or the wider peptidyl-nucleoside class), both from the same "
             "(Deng/Bai) lineage. Promote to confirmed only when validated across independent class members.",
    ),
)


def _ref_for_products(products) -> "NominalReference | None":
    """Return the first nominal reference whose classes intersect the BGC's product tokens."""
    toks = {str(p).strip().lower() for p in (products or [])}
    # also split semicolon/space-joined product strings
    extra = set()
    for t in list(toks):
        for piece in t.replace(";", " ").split():
            extra.add(piece)
    toks |= extra
    for ref in NOMINAL_REFERENCES:
        if toks & set(ref.classes):
            return ref
    return None


def length_kb_of(bgc) -> float:
    """BGC span in kb from start/end (works on dict rows or BGCRecord-like objects)."""
    def g(k):
        return bgc.get(k) if hasattr(bgc, "get") else getattr(bgc, k, None)
    lk = g("length_kb")
    if lk is not None:
        try:
            return round(float(lk), 2)
        except (TypeError, ValueError):
            pass
    s, e = g("start"), g("end")
    try:
        return round(max(0, int(e) - int(s)) / 1000, 2)
    except (TypeError, ValueError):
        return 0.0


def measure_bgc(bgc) -> dict:
    """Length measurement for one BGC, with optional nominal normalization for fragments.

    Returns a dict with: bgc_id, node, length_kb, boundary, and (when a nominal reference matches AND
    the BGC is a fragment) nominal_kb, recovery_pct, recovery_label, reference, reference_confirmed.
    """
    def g(k):
        return bgc.get(k) if hasattr(bgc, "get") else getattr(bgc, k, None)

    boundary = str(g("edge_status") or g("boundary") or g("Boundary") or "").strip() or "unknown"
    lk = length_kb_of(bgc)
    out = {
        "bgc_id": g("bgc_id") or g("BGC_ID") or "?",
        "node": g("node_id") or g("contig") or g("Node_ID") or g("Contig") or "",
        "length_kb": lk,
        "boundary": boundary,
        "nominal_kb": None,
        "recovery_pct": None,
        "recovery_label": f"{lk:.1f} kb",
        "reference": None,
        "reference_confirmed": None,
    }

    is_fragment = boundary.lower() in ("edge", "full-contig", "full_contig", "fc")
    ref = _ref_for_products(g("products") or g("Products") or [])
    if ref and is_fragment and lk > 0:
        frac = lk / ref.nominal_kb
        out["nominal_kb"] = ref.nominal_kb
        out["reference"] = ref.label
        out["reference_confirmed"] = ref.confirmed
        if frac > 1.0:
            out["recovery_pct"] = round(100 * frac, 1)
            out["recovery_label"] = (
                f"{lk:.1f} kb · >100% of ~{ref.nominal_kb:.0f} kb {ref.label} nominal "
                f"(exceeds nominal; reference may be smaller than this cluster)"
                + ("" if ref.confirmed else " [unconfirmed ref]")
            )
        else:
            out["recovery_pct"] = round(100 * frac, 1)
            out["recovery_label"] = (
                f"{lk:.1f} kb ≈ {out['recovery_pct']:.0f}% of ~{ref.nominal_kb:.0f} kb {ref.label} nominal "
                f"(yardstick, not a completeness claim)"
                + ("" if ref.confirmed else " [unconfirmed ref]")
            )
    return out


def measure_bgcs(bgcs) -> list:
    """Measure a list of BGCs. Always reports kb; adds nominal normalization where a reference matches."""
    return [measure_bgc(b) for b in (bgcs or [])]
