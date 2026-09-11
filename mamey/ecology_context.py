"""Source-bound ecological context for Mode B judgment.

This module is deliberately an evidence adapter, not an ecology interpreter.  It
normalizes the six ecology rows used by Sapote from already-computed Mamey scan
objects and preserves an explicit ``NOT_SCORED`` state whenever the relevant
stream is absent or unavailable.  The caller must provide the complete locus
identity; aliases are never sufficient.
"""
from __future__ import annotations

from typing import Any, Mapping

REGULATORS = (
    ("DasR", "Chitin -> GlcNAc de-repression of AB BGCs", ("DasR", "DasR_like_palindrome")),
    ("FuR/DmdR1", "Iron competition", ("FuR", "DmdR", "DmdR_iron_box_like", "Fur")),
    ("IolR", "Inositol/polyols", ("IolR", "IolR_like")),
    ("ANR", "Microaerobic zones", ("ANR", "ANR_FNR_like")),
    ("LexA", "Oxidative/ROS stress", ("LexA", "LexA_SOS_like")),
    ("GBL receptor", "Density/quorum signalling", ("GBL", "GBL_AdpA_like", "AdpA")),
)


def _identity(identity: Mapping[str, Any]) -> str:
    fields = ("strain", "node_or_contig", "region", "bgc_alias")
    values = [str(identity.get(k, "")).strip() for k in fields]
    if not all(values):
        raise ValueError("complete strain / node-or-contig / region / BGC alias identity is required")
    return " / ".join(values)


def _tokens(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        out: set[str] = set()
        for k, v in value.items():
            out.add(str(k).lower())
            out |= _tokens(v)
        return out
    if isinstance(value, (list, tuple, set)):
        out: set[str] = set()
        for v in value:
            out |= _tokens(v)
        return out
    return {str(value).lower()} if value not in (None, "") else set()


def build_bgc_ecology_context(
    identity: Mapping[str, Any],
    *,
    governed_locus_tags: list[str] | tuple[str, ...] = (),
    tfbs: Mapping[str, Any] | None = None,
    regulators: Mapping[str, Any] | None = None,
    chitinase: Mapping[str, Any] | None = None,
    cctt: Mapping[str, Any] | None = None,
    qs: Mapping[str, Any] | None = None,
    cross_habitat: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return locus-scoped ECO inputs suitable for a Mode B card.

    ``PRESENT`` means a source-bound hit names this exact BGC.  ``ABSENT`` is
    emitted only when the corresponding scan is present and complete but has no
    hit.  Missing/unreturned/unbound streams remain ``NOT_SCORED``.
    """
    locus = _identity(identity)
    streams = {"tfbs": tfbs, "regulators": regulators, "chitinase": chitinase, "cctt": cctt, "qs": qs}
    scan_available = bool(tfbs is not None)
    tfbs_hits = (tfbs or {}).get("hits", []) if isinstance(tfbs, Mapping) else []
    target = str(identity["bgc_alias"])
    governed = {str(x).strip() for x in governed_locus_tags if str(x).strip()}
    # A BGC alias is not a gene identifier. Prefer the SHA-bound governed roster;
    # alias matching is retained only for legacy scan fixtures that explicitly
    # encode the alias in target_locus.
    scoped = [h for h in tfbs_hits if (
        (governed and str(h.get("target_locus", "")) in governed)
        or (not governed and target.lower() in str(h.get("target_locus", "")).lower())
    )]
    token_blob = _tokens(scoped) | _tokens((regulators or {}).get(target, {}))
    token_text = " ".join(sorted(token_blob))
    rows = []
    for name, coupling, aliases in REGULATORS:
        hit = any(a.lower() in token_text for a in aliases)
        status = ("PRESENT" if hit else "ABSENT") if scan_available else "NOT_SCORED"
        rows.append({"regulator": name, "ecological_coupling": coupling, "signal_present": status,
                     "bgcs_coupled": [locus] if hit else []})
    return {
        "identity": {k: str(identity[k]) for k in ("strain", "node_or_contig", "region", "bgc_alias")},
        "complete_identity": locus,
        "tfbs_ecology_rows": rows,
        "source_stream_state": {k: ("AVAILABLE" if v is not None else "NOT_AVAILABLE") for k, v in streams.items()},
        "cross_habitat": cross_habitat if cross_habitat is not None else {"status": "NOT_SCORED"},
        "claim_safety": "Ecology rows are source-bound capacity/induction hypotheses; they do not establish expression, product identity, ecological function, or competitive outcome.",
    }
