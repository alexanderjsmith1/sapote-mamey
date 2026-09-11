"""source_provenance.py — how strongly is this strain's isolation source evidenced?

AMBER-03-2. `--source` is a free string. A host read off a folder name and a host
traced to a deposited GenBank record produced byte-identical manifests, so nothing
downstream could tell them apart — and a figure caption that says "bee-associated"
looks equally authoritative either way.

This is the analysis sign-off gate's item 7 ("a plotted strain's host must trace to
the authoritative strain table / GenBank accession, not a folder or notebook label;
flag PI-word-only provenance") made machine-readable.

Descriptive only: nothing here touches a score, a tier, a gate verdict or a product
claim. It records what is known about the provenance and emits the claim-safety
sentence a caption must carry when the host is not traced to a record.
"""
from __future__ import annotations

# ordered strongest -> weakest
SOURCE_PROVENANCE_LEVELS: tuple[str, ...] = ("accession", "table", "filename", "asserted")

#: the fail-safe default — an operator who says nothing has asserted, not traced
DEFAULT_SOURCE_PROVENANCE = "asserted"

#: levels that do NOT trace to an authoritative record, and therefore need a caveat
UNTRACED_LEVELS = frozenset({"filename", "asserted"})

_DESCRIPTIONS = {
    "accession": "traced to a deposited record (GenBank /isolation_source, /host, or BioSample)",
    "table": "traced to the authoritative strain table (an accession-bearing row)",
    "filename": "inferred from a file or folder label; NOT traced to any record",
    "asserted": "supplied by a person with no on-disk trace",
}

NOT_SUPPLIED = ("not supplied", "", "none", "unknown", "n/a", "na")


def normalize_source_provenance(value: str | None) -> str:
    """Fail safe: anything unrecognized becomes the weakest level, never the strongest."""
    v = (value or "").strip().lower()
    return v if v in SOURCE_PROVENANCE_LEVELS else DEFAULT_SOURCE_PROVENANCE


def describe_source_provenance(level: str | None) -> str:
    return _DESCRIPTIONS[normalize_source_provenance(level)]


def source_is_traced(level: str | None) -> bool:
    """True only for levels that trace to an authoritative record."""
    return normalize_source_provenance(level) not in UNTRACED_LEVELS


def source_provenance_note(source: str | None, level: str | None) -> str:
    """The claim-safety sentence for this strain's isolation source.

    Never empty — an untraced host and a traced host must both be stated, so a
    caption cannot silently inherit authority it does not have.
    """
    lvl = normalize_source_provenance(level)
    src = (source or "").strip()
    if src.lower() in NOT_SUPPLIED:
        return ("Isolation source not supplied. Interpretation is genome-grounded and does not "
                "depend on it; do not infer a host or habitat for any figure or caption.")
    if source_is_traced(lvl):
        return (f"Isolation source '{src}' is {describe_source_provenance(lvl)}. "
                f"Provenance only — never read into a functional or bioactivity claim.")
    return (f"Isolation source '{src}' is {describe_source_provenance(lvl)}. Treat it as "
            f"UNVERIFIED provenance: do not present it as the strain's host in a figure, "
            f"caption or table without tracing it to the authoritative strain table or a "
            f"GenBank accession. Provenance only — never read into a functional claim.")
