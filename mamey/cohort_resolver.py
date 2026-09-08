"""cohort_resolver.py — resolve a strain's cohort and actinomycete status (v9.7.44, F-7/B-1).

The cohort tag was keyed solely on the --strain ID prefix (AS->AS, SID->SID, else OTHER). Public SID
Streptomyces strains deposited under WGS accessions (e.g. --strain WWGG00000000, organism
"Streptomyces sp. SID-XXX") therefore landed in OTHER, and a non-actinomycete (e.g. Bacillus) entered the
set flagged only by the same quiet OTHER tag. This module resolves the embedded SID from the organism
string when the ID is an accession, and reports whether the organism genus is an actinomycete so a
non-actinomycete can be surfaced loudly.
"""
import re

# Genera that legitimately belong to an actinomycete-focused cohort (not exhaustive; "unknown" is benign).
# v9.7.81 P1: allowlist hardened — added genera documented in actinomycete literature
# that were falling to "unknown" because they were absent from ACTINO_GENERA.
# "unknown" is now a *review tag*, not a silent pass — see actino_status() docstring.
ACTINO_GENERA = {
    # Core Streptomycetales
    "streptomyces", "kitasatospora", "streptacidiphilus",
    # Pseudonocardiaceae
    "pseudonocardia", "amycolatopsis", "saccharopolyspora", "saccharomonospora",
    "actinosynnema", "kutzneria", "lentzea", "crossiella", "kibdelosporangium",
    "lechevalieria", "prauserella", "streptoalloteichus", "actinophytocola",
    # Micromonosporaceae
    "micromonospora", "actinoplanes", "catenulispora", "verrucosispora",
    "polymorphospora", "virgosporangium", "spirilliplanes",
    # Streptosporangiaceae
    "streptosporangium", "actinomadura", "nonomuraea", "planobispora",
    "planomonospora", "herbidospora",
    # Nocardiaceae / related
    "nocardia", "rhodococcus", "gordonia", "dietzia", "tsukamurella",
    "williamsia", "skermania",
    # Nocardioforma / Corynebacteriaceae
    "corynebacterium", "mycobacterium", "nocardiopsis", "kribbella",
    # Frankiales / Propionibacteriales
    "frankia", "propionibacterium", "acidothermus",
    # Micrococccales
    "micrococcus", "arthrobacter", "kocuria", "rothia",
    # Salinisporaceae / Glycomycetaceae
    "salinispora", "glycomyces",
    # Other documented BGC-producing actinomycetes
    "dactylosporangium", "asanoa", "spirillospora",
    "phytohabitans", "couchioplanes", "luedemannella",
}
# Genera that should NOT appear in an actinomycete cohort — fire a loud flag if seen.
NON_ACTINO_GENERA = {
    "bacillus", "paenibacillus", "escherichia", "pseudomonas", "burkholderia", "serratia",
    "photorhabdus", "xenorhabdus", "klebsiella", "staphylococcus", "lactobacillus", "clostridium",
    "vibrio", "enterococcus", "lysobacter", "myxococcus", "sorangium", "chromobacterium",
    "acinetobacter", "stenotrophomonas", "ralstonia", "cupriavidus", "sphingomonas", "bacteroides",
    # v9.7.86 P-9: non-actinomycete genera encountered in the cross-kingdom runs. Adding these so
    # the bldA/TTA scan correctly reports NOT_APPLICABLE (bldA control is actinomycete-specific;
    # on these organisms TTA codons are GC-content noise, not a developmental signal).
    # Firmicutes / Proteobacteria:
    "melissococcus", "wolbachia", "zymomonas", "gluconobacter", "snodgrassella", "gilliamella",
    "frischella", "bartonella", "pseudoalteromonas",
    # Endosymbionts / other bacteria from the bee/insect cohort:
    "symbiodolus", "candidatus",
    # Fungi (cross-kingdom runs: black yeasts, attine cultivar, model/endosymbiont fungi):
    "knufia", "leucocoprinus", "neurospora", "gemmata", "rhinocladiella", "aspergillus",
    "penicillium", "alternaria", "zymoseptoria", "saccharomyces", "candida", "fusarium",
    # v9.7.87 P-11: kingdom-level tokens. The bare-FASTA case carries no genus — the only
    # honest taxonomy a user can pass is "Fungi sp." / "fungal" / "Eukaryota". Without these,
    # actino_status returned "unknown" and the bldA guard's "unknown -> apply" rule produced a
    # false T4 on fungal genomes. A kingdom-only declaration that is clearly non-actinomycete
    # now resolves to non_actinomycete (it is never an actinomycete, which is a bacterial class).
    "fungi", "fungal", "eukaryota", "eukaryote", "eukarya", "archaea", "archaeon", "metazoa",
    "viridiplantae", "plant",
}

# Accept an optional hyphen or space between the SID prefix and the number so that the
# hyphenated public form used in this module's own docstring example
# ("Streptomyces sp. SID-XXX") resolves identically to the space- or run-together WGS form.
_SID_RE = re.compile(r"\bSID[-\s]?(\d+)\b", re.I)
# v9.7.81 P2 F2/PC-03: canonical AS-regex — hyphen is OPTIONAL (AS-XXX and AS-XXX both match).
# All three matchers (cohort_resolver, dedup_and_guard, cli) are aligned on this choice.
# v9.7.402 (W402-35 round 3): tightened to exact-anchor matching. This pattern previously
# admitted a second, unrelated two-letter-prefix shape as an alternate branch, which meant any
# identifier beginning with that other prefix was swept into cohort "AS" even though it shares
# no relationship to this project's actinomycete cohort. The engine-shipped matcher here now
# recognizes ONLY the exact "AS" prefix (optionally hyphenated, followed by a digit) -- no other
# prefix, however similar in shape, is treated as this project's private cohort. Cohort/study
# membership for any non-"AS" identifier is never inferred from its prefix; it is either resolved
# to the public SID/OTHER routing buckets below (see resolve_cohort()'s membership_authority
# field) or, for genuine scientific cohort membership, must come from an external, digest-bound
# roster this module does not implement.
_AS_RE = re.compile(r"^AS-?\d", re.I)

# Marker value for resolve_cohort()'s "membership_authority" field, matching the
# ROUTING_ONLY_* naming convention already used elsewhere in this codebase (e.g.
# source_availability.py's claim_effect/claim_state fields) for a result that is a generic
# routing/diagnostic bucket, not confirmed scientific cohort/study membership. A caller must not
# treat cohort=="OTHER" as resolved membership for a study denominator, prevalence, enrichment,
# or publication-facing group label -- only an external, digest-bound membership manifest (not
# yet implemented anywhere in this engine) may authorize that.
_ROUTING_ONLY = "ROUTING_ONLY_NOT_SCIENTIFIC_COHORT_MEMBERSHIP"


def derive_strain_id(current_label: str, organism: str = "", filename: str = "") -> tuple[str, str]:
    """v9.7.229 naming convention: strain ID = `Genus_species_Designation`, filesystem-safe, sourced
    from the actual organism record — NEVER an LLM-invented abbreviation. Returns (id, note).

    Priority:
      1. antiSMASH record ORGANISM (`organism`) when it yields a real genus (+ species/sp.); the
         designation is kept from the current label (culture/SID/WAC/NPDC number or accession).
      2. organism tokens from the uploaded filename, when the record lacks taxonomy.
      3. never invent — if neither yields a genus, keep the current label + a note to supply --strain.
    """
    import re as _re

    # Never rewrite an already-canonical designation (AS-cohort, or an already-derived Genus_species_*).
    lab0 = (current_label or "").strip()
    if _re.match(r"^AS-\d+$", lab0) or _re.match(r"^[A-Z][a-z]+_[a-z]+_", lab0):
        return current_label, ""
    def _safe(s):
        s = _re.sub(r"\bsubsp\.?\b", "", s or "", flags=_re.I)
        s = s.replace(".", " ").replace("-", " ")
        return _re.sub(r"_+", "_", _re.sub(r"\s+", "_", s.strip())).strip("_")

    def _binomial(org):
        s = (org or "").strip()
        if not s or not s[:1].isalpha():
            return ""
        toks = s.split()
        genus = toks[0]
        if not genus[:1].isupper():
            return ""
        species = toks[1] if len(toks) > 1 and toks[1][:1].islower() else "sp"
        return f"{genus} {species}"

    def _designation(label, org):
        # the culture/collection tag: strip a leading binomial off the label if present, else the label
        lab = (label or "").strip()
        # organism may already carry the strain tag as trailing tokens (e.g. "Salinispora arenicola CNX814")
        otoks = (org or "").split()
        if len(otoks) > 2:
            tail = "_".join(otoks[2:])
            if tail:
                return _safe(tail)
        return _safe(lab)

    binom = _binomial(organism) or _binomial(filename.replace("_", " "))
    if not binom:
        return current_label, ("label kept — no genus in ORGANISM or filename; supply --strain <Genus_species_Designation>")
    desig = _designation(current_label, organism)
    derived = _safe(f"{binom} {desig}") if desig else _safe(binom)
    if derived == _safe(current_label):
        return current_label, ""
    return derived, (f"strain ID derived from the organism record: '{current_label}' -> '{derived}' "
                     f"(convention: Genus_species_Designation, not an LLM abbreviation)")


def normalize_taxonomy(taxonomy: str) -> str:
    """F-6: the AS GBKs deposit `ORGANISM  .` (no genus), so an organism string lifted from them is the literal
    ".". A taxonomy with no leading alphabetic genus token is normalized to the safe placeholder "sp." (genus
    unresolved) so "." never propagates into organism / genus / cohort / display. A real binomial is returned
    unchanged."""
    s = (taxonomy or "").strip()
    return s if re.match(r"[A-Za-z]", s) else "sp."


def _genus(organism: str) -> str:
    s = (organism or "").strip()
    # v9.7.187 P3 fix: a lineage string (";" or "," delimited, e.g.
    # "Bacteria;Actinomycetota;...;Streptomyces") carries the genus in its LAST
    # populated rank, not the first token. Detect a delimited lineage and take
    # the terminal field before falling back to first-token binomial parsing.
    if ";" in s or "," in s:
        fields = [f.strip() for f in re.split(r"[;,]", s) if f.strip()]
        if fields:
            s = fields[-1]
    parts = s.split()
    if parts and parts[0].lower() in ("candidatus", "uncultured"):
        parts = parts[1:]
    return parts[0].lower() if parts else ""


def actino_status(organism: str) -> str:
    """'actinomycete' / 'non_actinomycete' / 'unknown' from the organism genus.

    v9.7.81: "unknown" is a REVIEW tag — the genus is not in the allowlist OR denylist.
    It does NOT mean the strain is non-actinomycete; it means human review is warranted.
    Callers should surface "unknown" loudly (e.g. in the intake issue_log) rather than
    silently accepting it as a pass.
    """
    g = _genus(organism)
    if g in NON_ACTINO_GENERA:
        return "non_actinomycete"
    if g in ACTINO_GENERA:
        return "actinomycete"
    return "unknown"


def resolve_cohort(strain_id: str, organism: str = "") -> dict:
    """Resolve {cohort, actino_status, resolved_sid, note, membership_authority} for a strain.

    cohort vocabulary is unchanged ({AS, SID, OTHER}) so downstream consumers are unaffected; the fix is
    that WGS-accession-labelled SID strains now resolve to SID via the organism string.

    v9.7.402 (W402-35 round 3): added `membership_authority`. `cohort` alone conflates a generic
    routing/diagnostic bucket with confirmed scientific cohort/study membership -- a caller
    checking only `cohort` cannot tell "resolved, publicly-known SID" from "unrecognized prefix,
    parked in OTHER pending real classification." `membership_authority` is `None` for AS/SID
    (this module's existing, unchanged prefix/accession resolution -- not reopened by this fix)
    and `_ROUTING_ONLY` for OTHER, so a denominator-bearing consumer has an explicit, typed signal
    that OTHER is not itself scientific cohort membership. Real external-manifest-backed
    membership (Layer C in the Mode-B gene-first v2 three-layer model) is deliberately not
    implemented here -- this field only marks the boundary, it does not resolve the harder
    question.
    """
    sid = (strain_id or "").strip()
    org = (organism or "").strip()
    up = sid.upper()
    st = actino_status(org)
    if _AS_RE.match(up):
        return {"cohort": "AS", "actino_status": st, "resolved_sid": None, "note": None,
                "membership_authority": None}
    if up.startswith("SID"):
        return {"cohort": "SID", "actino_status": st, "resolved_sid": sid, "note": None,
                "membership_authority": None}
    m = _SID_RE.search(org)
    if m:
        rsid = f"SID{m.group(1)}"
        return {"cohort": "SID", "actino_status": st, "resolved_sid": rsid,
                "note": f"accession '{sid}' resolved to public {rsid} via organism string '{org}'",
                "membership_authority": None}
    note = None
    if st == "non_actinomycete":
        note = (f"organism '{org}' is a non-actinomycete ({_genus(org)}) — off-target for an "
                f"actinomycete cohort; review before including in cross-strain comparison")
    return {"cohort": "OTHER", "actino_status": st, "resolved_sid": None, "note": note,
            "membership_authority": _ROUTING_ONLY}
