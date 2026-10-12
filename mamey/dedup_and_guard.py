"""Prototypes for: (A) dedup-on-ingest, (B) hardened release guard, (C) fragment claim-ceiling."""
import re

# ---------- (A) DEDUP-ON-INGEST ----------
def dedup_b1_rows(rows, key=("strain","BGC_ID"), policy="last"):
    """Idempotent append: collapse duplicate primary keys. Returns (deduped, report)."""
    seen = {}
    order = []
    dup_keys = {}
    for r in rows:
        k = tuple(str(r.get(c,"")).strip() for c in key)
        if k in seen:
            dup_keys[k] = dup_keys.get(k, 1) + 1
            if policy == "last": seen[k] = r          # last wins
        else:
            seen[k] = r; order.append(k)
    deduped = [seen[k] for k in order]
    report = {"input_rows": len(rows), "output_rows": len(deduped),
              "removed": len(rows)-len(deduped),
              "duplicate_keys": {":".join(k): n for k,n in dup_keys.items()}}
    return deduped, report

# ---------- (B) HARDENED RELEASE GUARD ----------
# v9.7.81 P2: AS-regex canonical = optional hyphen (AS-XXX and AS-XXX both match)
AS_PATTERN      = re.compile(r'\bAS-?\d{2,}\b')
AJS_PATTERN     = re.compile(r'\bAJS-?\d+\b')   # v9.7.409 (BC hostile audit H1): \d{2,} let a single-digit AJS id bypass the non-overridable leak guard; the redactor already matched single digits
PENDING_PATTERN = re.compile(r'\bPENDING\b', re.I)
PUBLIC_PATTERN  = re.compile(r'^(SID\d+|PSEUDO|AGLAU|ACITR|AGRAE|MHUMI|SPHIL|SCLAV|SDROZ)$')

def derive_release(strain, private_registry=frozenset(), published_registry=None):
    """Default PRIVATE; an exact supplied public roster is explicit authority.

    Identifier shapes and historical cohort decisions never grant publication
    permission to new inputs. Hard private guards outrank any supplied roster.
    An omitted roster and an empty roster both yield PRIVATE.
    """
    s = str(strain)
    if _trips_private_guard(s, private_registry):
        return "PRIVATE"
    return "PUBLIC" if published_registry is not None and s in published_registry else "PRIVATE"


def _trips_private_guard(strain, private_registry=frozenset()):
    s = str(strain)
    return bool(AJS_PATTERN.search(s) or PENDING_PATTERN.search(s)
                or s in private_registry)


def resolve_release(strain, override=None, private_registry=frozenset(), published_registry=None):
    """Release tag with an optional operator override (the `--release` flag).

    Fail-safe default (override=None) is derive_release. An operator may assert PUBLIC on an UNRECOGNIZED
    shape (e.g. a named reference genome like 'Nocardia_fusca' or an NCBI accession that PUBLIC_PATTERN does
    not list) — but a PUBLIC override is REFUSED if the strain trips the private-identifier guard
    (AJS/PENDING/registry). That leak guard is not operator-bypassable. PRIVATE override is always honored
    (it is strictly more conservative). Returns (release, refused: bool) so the caller can warn on a refusal.

    v9.7.331: when an explicit `published_registry` is supplied, a PUBLIC override is ALSO refused for an
    AS strain not enumerated in it — the operator cannot blanket-force an unpublished AS strain public.
    v9.7.432: `None` (the default) means NOT CONFIGURED and leaves override behavior unchanged; any
    supplied set -- including an empty one -- arms the refusal, so an operator cannot force PUBLIC on
    an AS strain once the roster declares nothing published.
    """
    if override is None:
        return derive_release(strain, private_registry, published_registry), False
    o = str(override).strip().upper()
    if o == "PRIVATE":
        return "PRIVATE", False
    if o == "PUBLIC":
        if _trips_private_guard(strain, private_registry):
            return "PRIVATE", True   # guard wins; operator cannot force a private-identifier strain public
        if (published_registry is not None and AS_PATTERN.search(str(strain))
                and str(strain) not in published_registry):
            return "PRIVATE", True   # unpublished AS strain: not in the enumerated published allowlist
        return "PUBLIC", False
    # unknown override value -> ignore, fall back to derived (fail-safe)
    return derive_release(strain, private_registry, published_registry), False

def leak_audit(rows, *, public_strains=frozenset()):
    """Return private-shaped cells in PUBLIC rows.

    An own-strain self-reference is exempt only with separately supplied exact
    public authority, never because a row labels itself PUBLIC or matches a
    historical prefix. Hard private guards still win. This helper does not by
    itself establish that a live pipeline or export audit invoked it.
    """
    leaks = []
    for r in rows:
        if r.get("release") != "PUBLIC":
            continue
        own_strain = str(r.get("strain") or "")
        own_is_legit_public = (bool(own_strain) and own_strain in public_strains
                               and not _trips_private_guard(own_strain))
        for k, v in r.items():
            if not v:
                continue
            sv = str(v)
            if own_is_legit_public and sv == own_strain:
                continue  # the row correctly naming its own, independently-verified-PUBLIC strain
            if AS_PATTERN.search(sv) or AJS_PATTERN.search(sv) or PENDING_PATTERN.search(sv):
                leaks.append(f"{r.get('strain')}:{r.get('BGC_ID')}::{k}={v}")
    return leaks

# ---------- (C) FRAGMENT CLAIM-CEILING ----------
# LARGE_BACKBONE_KEYWORDS is the authoritative, expanded list in fragment_ceiling.py (38 entries).
# Import it here so dedup_and_guard stays in sync automatically.
from .fragment_ceiling import LARGE_BACKBONE_KEYWORDS as LARGE_BACKBONE
FRAGMENT_BOUNDARIES = {"Edge","Full-contig","FC"}
BACKBONE_MIN_KB = 45.0

def fragment_claim_ceiling(bgc):
    """If a large-backbone compound is named on a sub-45kb fragment, cap claim to class capacity.
    Returns (downgraded: bool, ceiling: str, reason: str|None)."""
    named = str(bgc.get("closest_candidate_kcb_product") or bgc.get("closest_product") or "").lower()
    boundary = str(bgc.get("edge_status") or bgc.get("boundary") or "")
    try:
        kb = (float(bgc.get("end",0)) - float(bgc.get("start",0)))/1000.0
    except (TypeError, ValueError):
        kb = float(bgc.get("length_kb") or 0)
    if any(kw in named for kw in LARGE_BACKBONE) and boundary in FRAGMENT_BOUNDARIES and 0 < kb < BACKBONE_MIN_KB:
        return True, "class_capacity_only", f"{kb:.1f}kb {boundary} too small for {named.split('/')[0]} backbone (>={BACKBONE_MIN_KB}kb)"
    return False, "", None
