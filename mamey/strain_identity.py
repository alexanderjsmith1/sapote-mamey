"""strain_identity.py — a strain ID must be an identity, not an accession.

Motivation
----------
``run --strain`` accepts any string, and when omitted the ID is derived from the ZIP stem. A student
who downloads ``CP108695.1.zip`` from NCBI therefore gets a package whose entire identity is
``CP108695_1``: every output filename, the manifest ``strain_id``, the sealed package name, and every
downstream Mode-B card and figure label. An accession is a database pointer, not a strain identity —
nobody reading ``CP108695_1`` in a figure knows it is *Nocardia* sp. NBC_01009.

This happened at scale on 2026-08-20: a reference-strain run produced packages named ``CP025018_1``,
``CP029711_1``, ``CP108695_1``, ``CP109162_1``, ``CP120997_1`` and ``CP192113_1`` before it was caught
by eye, and had to be stopped and re-run.

The engine already knows what an accession looks like — ``cli._ACCESSION_RE`` matches RefSeq, WGS and
assembly accessions. It simply never applied that knowledge to the strain ID. This module owns that
regex (``cli._label_is_accession`` delegates here, so there is one definition, not two) and adds the
resolution the guard needs to be *helpful* rather than merely obstructive.

Policy
------
* An accession-shaped strain ID is **refused only when a better name is available** from the archive.
  The error names the organism and the exact id to use, so the fix is one edit.
* When nothing better can be resolved, the run **proceeds with a loud warning**. Blocking a user while
  offering no alternative is not a guard, it is an obstacle.
* ``--strain auto`` resolves the id from the archive.
* ``--allow-accession-strain-id`` exists for the operator who genuinely wants the accession as identity.

Claim-safety: a resolved organism name is a record label taken from the genome's own metadata. It is
not a taxonomic assertion, and it is not evidence about the strain's biology.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Optional

__all__ = [
    "ACCESSION_RE",
    "looks_like_accession",
    "looks_like_accession_prefixed",
    "StrainIdentity",
    "resolve_strain_id",
]

#: RefSeq chromosome / WGS / assembly accessions. Mirrors the historical ``cli._ACCESSION_RE``;
#: ``cli._label_is_accession`` now delegates here so the two cannot drift apart.
# v9.7.374 fix (two more gaps found by audit, same shape as the two closed 2026-08-20):
#  3. neither pattern was compiled with re.IGNORECASE, so a lowercase/mixed-case accession (e.g.
#     a filename or --strain value typed as "cp108695.1") matched NEITHER regex and sailed through
#     this guard with no warning at all -- reproducing the exact 2026-08-20 incident by casing
#     alone, since resolve_strain_id()'s explicit-value refuse/suggest branch is entirely gated on
#     looks_like_accession() returning True.
#  4. RefSeq routinely prefixes an ordinary 2-letter INSDC accession with NZ_ for complete/
#     chromosome-level bacterial assemblies (e.g. NZ_CP009110.1, extremely common for actinomycete
#     genomes) -- neither the RefSeq alternative (requires digits immediately after NZ_) nor the
#     WGS alternative (requires 4-6 letters after the optional NZ_) matches this shape, so
#     NZ_CP009110.1 was not recognized as an accession even though CP009110.1 (the same accession
#     minus "NZ_") already was.
ACCESSION_RE = re.compile(
    r"^(?:NC_|NZ_|NW_|NT_|NG_)\d{6,}(?:\.\d+)?$"       # RefSeq chromosome, e.g. NC_003888.3
    r"|^(?:NZ_)?[A-Z]{4,6}\d{6,}(?:\.\d+)?$"           # WGS, e.g. NZ_QHHY00000000.1
    r"|^GC[AF]_\d{9}(?:\.\d+)?$"                       # assembly, e.g. GCA_009862675.1
    , re.IGNORECASE
)

#: Two gaps in the historical pattern, both of which let real damage through on 2026-08-20:
#:  1. it requires 4-6 letters, so the 2-letter INSDC prefixes (``CP025018.1``, ``AP...``) never
#:     matched — which is precisely why the six bad IDs were not caught;
#:  2. it only sees the dotted form, but once a filename is sanitised the label is ``CP025018_1``.
#: Letter/digit counts are kept TIGHT on purpose: ``SID10815`` (3 letters + 5 digits) is a governed
#: cohort strain, and flagging it would block real work. 2-letter prefixes therefore demand >=6
#: digits, and 4-6 letter prefixes demand >=6 digits.
_EXTRA_ACCESSION_RE = re.compile(
    r"^(?:NZ_)?[A-Z]{2}\d{6,}(?:[._]\d+)?$"           # INSDC 2-letter, e.g. CP025018.1 / CP025018_1 / NZ_CP009110.1
    r"|^(?:NC_|NZ_|NW_|NT_|NG_)\d{6,}(?:[._]\d+)?$"    # RefSeq, sanitised form
    r"|^(?:NZ_)?[A-Z]{4,6}\d{6,}(?:[._]\d+)?$"         # WGS, sanitised form
    r"|^GC[AF]_\d{9}(?:[._]\d+)?$"                     # assembly, sanitised form
    , re.IGNORECASE
)


def looks_like_accession(strain_id: str) -> bool:
    """True when the label is a database accession rather than a strain identity."""
    text = (strain_id or "").strip()
    if not text:
        return False
    return bool(ACCESSION_RE.match(text) or _EXTRA_ACCESSION_RE.match(text))


# v97395 tick 17 fix: ``looks_like_accession`` is a full-string match, so it never fires on the
# extremely common NCBI assembly-report download shape ``GCA_009862675.1_ASM986267v1_genomic`` —
# a real accession used as a *prefix*, followed by an assembly name and "_genomic". Sanitised
# (underscore-joined, as the zip-stem fallback below does), that becomes
# ``GCA_009862675_1_ASM986267v1_genomic``: no exact-match regex catches it, so the fallback strain
# id silently ships as this accession-derived, non-identity label with zero warning -- one
# filename shape away from the exact 2026-08-20 incident (CP025018_1, CP108695_1, ...) this
# module exists to catch. Reuses the same letter/digit-count discipline as ``_EXTRA_ACCESSION_RE``
# (2-letter prefixes still demand >=6 digits, protecting real cohort ids like ``SID10815``) but
# only requires the accession-shaped token to be followed by an underscore or end-of-string,
# rather than requiring it to be the entire label.
_ACCESSION_PREFIX_RE = re.compile(
    r"^(?:NC_|NZ_|NW_|NT_|NG_)\d{6,}(?:_\d+)?(?=_|$)"
    r"|^(?:NZ_)?[A-Z]{2,6}\d{6,}(?:_\d+)?(?=_|$)"
    r"|^GC[AF]_\d{9}(?:_\d+)?(?=_|$)"
    , re.IGNORECASE
)


def looks_like_accession_prefixed(sanitised_stem: str) -> bool:
    """True when *sanitised_stem* begins with a database accession followed by more filename
    content -- e.g. an underscore-sanitised NCBI assembly-report stem. ``sanitised_stem`` is
    expected to already be underscore-joined (as ``resolve_strain_id``'s zip-stem fallback
    produces); this is not a general-purpose check on arbitrary raw strings."""
    text = (sanitised_stem or "").strip()
    if not text:
        return False
    return bool(_ACCESSION_PREFIX_RE.match(text))


@dataclass
class StrainIdentity:
    """Outcome of resolving a strain ID, with the reasoning attached."""

    strain_id: Optional[str]
    source: str = ""            # supplied | archive | zip_stem
    refused: bool = False
    message: str = ""
    suggestion: Optional[str] = None
    organism: Optional[str] = None

    def __bool__(self) -> bool:  # truthy when usable
        return bool(self.strain_id) and not self.refused


def _from_archive(input_zip: str) -> tuple[Optional[str], Optional[str]]:
    """Return ``(suggested_strain_id, organism)`` using the antiSMASH input reader when present."""
    try:
        from .antismash_input import identify
    except Exception:
        return None, None
    try:
        info = identify(input_zip)
    except Exception:
        return None, None
    return info.suggested_strain_id, info.organism


# v9.7.409 (BC hostile audit H2): a strain id becomes a directory name, a file prefix and a zip name.
# `--strain '../escaped'` created a directory OUTSIDE the caller's --outdir on the sealed .408 engine, and
# `--strain 'AS-1; echo X; $(id)'` was accepted verbatim (no shell ran, but every downstream shell tool
# — BLAST, bash helpers — would break or worse). Path separators, traversal, whitespace and shell
# metacharacters are refused before anything is written.
SAFE_STRAIN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class UnsafeStrainId(ValueError):
    """Raised for a strain id that cannot safely become a path component."""


def validate_strain_id(strain_id: str) -> str:
    """Return ``strain_id`` unchanged if it is a safe path component; raise :class:`UnsafeStrainId` otherwise."""
    s = str(strain_id or "")
    if not SAFE_STRAIN_ID_RE.match(s) or ".." in s:
        raise UnsafeStrainId(
            f"strain id {s!r} is not a safe path component: letters, digits, '.', '_' and '-' only "
            f"(1–64 chars, must start with a letter or digit; no '/', '\\', '..', spaces or shell characters)")
    return s


def resolve_strain_id(supplied: Optional[str], input_zip: str,
                      allow_accession: bool = False) -> StrainIdentity:
    """Decide the strain ID for a run.

    ``supplied`` may be ``None``/``"auto"`` (resolve from the archive) or an explicit label. An
    accession-shaped label is refused **only** when the archive offers a real organism name.
    """
    suggestion, organism = _from_archive(input_zip)
    stem = os.path.splitext(os.path.basename(input_zip or ""))[0]

    wanted = (supplied or "").strip()
    if wanted.lower() in ("", "auto"):
        if suggestion:
            return StrainIdentity(strain_id=suggestion, source="archive", organism=organism,
                                  message=f"strain id resolved from the archive: {organism}")
        fallback = re.sub(r"[^A-Za-z0-9]+", "_", stem).strip("_") or None
        ident = StrainIdentity(strain_id=fallback, source="zip_stem", organism=organism)
        if fallback and not allow_accession:
            if looks_like_accession(fallback):
                ident.message = (
                    f"strain id '{fallback}' is a database accession and no organism could be read "
                    f"from the archive. The run will proceed, but this label will appear in every "
                    f"output file, figure and card. Pass --strain <Genus_species_strain> to give it "
                    f"an identity."
                )
            elif looks_like_accession_prefixed(fallback):
                ident.message = (
                    f"strain id '{fallback}' begins with a database accession (from a filename like "
                    f"an NCBI assembly-report download) and no organism could be read from the "
                    f"archive. The run will proceed, but this label will appear in every output "
                    f"file, figure and card. Pass --strain <Genus_species_strain> to give it an "
                    f"identity."
                )
        return ident

    if looks_like_accession(wanted) and not allow_accession:
        if suggestion:
            return StrainIdentity(
                strain_id=None, source="supplied", refused=True, suggestion=suggestion,
                organism=organism,
                message=(
                    f"--strain '{wanted}' is a database accession, not a strain identity. It would "
                    f"become the name of every output file, the manifest strain_id, the sealed "
                    f"package and every downstream card and figure label.\n"
                    f"  This archive is: {organism}\n"
                    f"  Use:  --strain {suggestion}\n"
                    f"  Or:   --strain auto            (resolve it automatically)\n"
                    f"  Or:   --allow-accession-strain-id   (keep the accession deliberately)"
                ))
        return StrainIdentity(
            strain_id=wanted, source="supplied", organism=organism,
            message=(f"strain id '{wanted}' looks like a database accession and no organism could be "
                     f"read from the archive to suggest a better one; proceeding as given."))

    return StrainIdentity(strain_id=wanted, source="supplied", organism=organism)
