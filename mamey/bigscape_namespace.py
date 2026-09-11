"""Single owner for portable BiG-SCAPE GCF identity and admission.

Literal family identifiers are display data.  Portable grouping and joins use only a
validated identity containing the exact run, Decimal cutoff, and encoded literal.
"""
from __future__ import annotations

import contextlib
import csv
import os
import re
import tempfile
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable, Mapping, Sequence
from urllib.parse import quote, unquote_to_bytes


PREFIX = "bigscape-gcf:v1"
REQUIRED_COLUMNS = ("family_id", "run_id", "normalized_cutoff", "qualified_family_id")
NAMESPACE_COLUMNS = REQUIRED_COLUMNS + ("gcf_namespace",)
_QUALIFIED = re.compile(
    r"^bigscape-gcf:v1/run/(?P<run>[1-9][0-9]*)/cutoff/(?P<cutoff>[^/]+)/family/(?P<family>[^/]*)$"
)


class NamespaceError(ValueError):
    """Expected, public-safe namespace refusal with a stable code."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.public_message = message
        super().__init__(f"BIGSCAPE_NAMESPACE_ERROR[{code}]: {message}")


@dataclass(frozen=True, order=True)
class FamilyIdentity:
    run_id: int
    normalized_cutoff: str
    family_id: str
    qualified_family_id: str

    @property
    def gcf_namespace(self) -> str:
        return f"run_id={self.run_id};cutoff={self.normalized_cutoff}"


_STRAIN_ID = re.compile(r"^(AS-\d+|AJS-\d+|SID\d+)_", re.I)
# a trailing GenBank/RefSeq/assembly accession token: GCF_/GCA_<digits>, or an optional 1-3 letter
# database prefix + a 1-6 letter accession body + >=4 digits (+ optional version). Matched at the
# end of the accession-named stem so the ORGANISM name (which may contain spaces and a strain
# designator like "KAI-180") is preserved.
_ACCESSION_TAIL = re.compile(
    r"_(?:GC[AF]_\d+(?:\.\d+)?"
    r"|(?:[A-Za-z]{1,3}_)?[A-Za-z]{1,6}[0-9]{4,}(?:\.\d+)?)$", re.I)


def strain_from_gbk_name(name: str) -> str:
    """Strain id from a staged BiG-SCAPE region-GBK filename, for AS-cohort AND reference genomes.

    v9.7.412 (Amber): the per-tool `^(AS-\\d+|SID\\d+|[A-Za-z0-9-]+?)_` prefix could not cross a
    space or period, so every reference genome (`Genus species strain_ACCESSION.regionNNN.gbk`)
    collapsed to a single '?' bucket — verified: all 2,785 reference region GBKs in a real curated
    run mapped to '?', silently corrupting cross-strain counts and KNOWN/NOVEL calls on any mixed
    AS+reference run. This resolver keeps AS/SID/AJS ids exact (SPAdes `_NODE_` names) and, for
    reference names, strips only the trailing accession token, preserving the organism name.
    MIBiG (`BGC\\d+`) -> 'MIBiG'.
    """
    b = os.path.basename(name)
    if b[:3].upper() == "BGC":
        return "MIBiG"
    m = _STRAIN_ID.match(b)
    if m:
        return m.group(1)
    # Preserve portable strain prefixes across multiple SPAdes contigs.
    generic = re.match(r"^([A-Za-z0-9-]+)_NODE_", b, re.I)
    if generic:
        return generic.group(1)
    stem = re.sub(r"\.region\d+\.gbk$", "", b, flags=re.I)
    stem = _ACCESSION_TAIL.sub("", stem)
    return stem.strip() or "?"


def normalize_run_id(value: object) -> int:
    if isinstance(value, bool) or value is None:
        raise NamespaceError("RUN_ID_INVALID", "run_id must be a canonical positive integer")
    if isinstance(value, int):
        if value > 0:
            return value
        raise NamespaceError("RUN_ID_INVALID", "run_id must be a canonical positive integer")
    if not isinstance(value, str) or not re.fullmatch(r"[1-9][0-9]*", value):
        raise NamespaceError("RUN_ID_INVALID", "run_id must be a canonical positive integer")
    return int(value)


def normalize_cutoff(value: object) -> str:
    if isinstance(value, bool) or value is None:
        raise NamespaceError("CUTOFF_INVALID", "cutoff must be an exact Decimal in (0,1]")
    text = str(value)
    if not text or text != text.strip():
        raise NamespaceError("CUTOFF_INVALID", "cutoff must be an exact Decimal in (0,1]")
    try:
        number = Decimal(text)
    except (InvalidOperation, ValueError):
        raise NamespaceError("CUTOFF_INVALID", "cutoff must be an exact Decimal in (0,1]") from None
    if not number.is_finite() or number <= 0 or number > 1:
        raise NamespaceError("CUTOFF_INVALID", "cutoff must be an exact Decimal in (0,1]")
    canonical = format(number.normalize(), "f")
    return canonical


def normalize_family_literal(value: object) -> str:
    if isinstance(value, bool) or value is None or isinstance(value, float):
        raise NamespaceError("FAMILY_ID_INVALID", "family_id must be a safe non-empty literal")
    literal = str(value)
    if not literal or literal != literal.strip():
        raise NamespaceError("FAMILY_ID_INVALID", "family_id must be a safe non-empty literal")
    if any(unicodedata.category(char).startswith("C") for char in literal):
        raise NamespaceError("FAMILY_ID_INVALID", "family_id must not contain control characters")
    return literal


def build_family_identity(run_id: object, cutoff: object, family_id: object) -> FamilyIdentity:
    run = normalize_run_id(run_id)
    canonical_cutoff = normalize_cutoff(cutoff)
    literal = normalize_family_literal(family_id)
    qualified = f"{PREFIX}/run/{run}/cutoff/{canonical_cutoff}/family/{quote(literal, safe='')}"
    return FamilyIdentity(run, canonical_cutoff, literal, qualified)


def qualified_family_id(run_id: object, cutoff: object, family_id: object) -> str:
    return build_family_identity(run_id, cutoff, family_id).qualified_family_id


def parse_family_identity(value: object) -> FamilyIdentity:
    if not isinstance(value, str):
        raise NamespaceError("QUALIFIED_ID_INVALID", "qualified_family_id has invalid syntax")
    match = _QUALIFIED.fullmatch(value)
    if not match:
        raise NamespaceError("QUALIFIED_ID_INVALID", "qualified_family_id has invalid syntax")
    try:
        literal = unquote_to_bytes(match.group("family")).decode("utf-8", errors="strict")
    except (UnicodeDecodeError, ValueError):
        raise NamespaceError("QUALIFIED_ID_INVALID", "qualified_family_id has invalid encoding") from None
    identity = build_family_identity(match.group("run"), match.group("cutoff"), literal)
    if identity.qualified_family_id != value:
        raise NamespaceError("QUALIFIED_ID_INVALID", "qualified_family_id is not canonical")
    return identity


def validate_membership_row(
    row: Mapping[str, object], *, expected_run: object | None = None,
    expected_cutoff: object | None = None, allow_absent: bool = False,
) -> FamilyIdentity | None:
    present = {name: str(row.get(name) or "") != "" for name in NAMESPACE_COLUMNS}
    if not any(present.values()):
        if allow_absent:
            return None
        raise NamespaceError("LEGACY_LOCAL_ONLY_UNQUALIFIED", "portable membership requires a qualified identity")
    if not all(present[name] for name in REQUIRED_COLUMNS):
        raise NamespaceError("LEGACY_LOCAL_ONLY_UNQUALIFIED", "portable membership requires a qualified identity")
    identity = build_family_identity(row["run_id"], row["normalized_cutoff"], row["family_id"])
    parsed = parse_family_identity(row["qualified_family_id"])
    if identity != parsed:
        raise NamespaceError("QUALIFIED_COMPONENT_MISMATCH", "qualified identity components do not match")
    namespace = str(row.get("gcf_namespace") or "")
    if namespace and namespace != identity.gcf_namespace:
        raise NamespaceError("NAMESPACE_LABEL_MISMATCH", "gcf_namespace does not match qualified identity")
    if expected_run is not None and identity.run_id != normalize_run_id(expected_run):
        raise NamespaceError("RUN_ID_MISMATCH", "requested run does not match portable membership")
    if expected_cutoff is not None and identity.normalized_cutoff != normalize_cutoff(expected_cutoff):
        raise NamespaceError("CUTOFF_MISMATCH", "requested cutoff does not match portable membership")
    return identity


def validate_membership_rows(
    rows: Iterable[Mapping[str, object]], *, key_fields: Sequence[str],
    expected_run: object | None = None, expected_cutoff: object | None = None,
    allow_absent: bool = False,
) -> list[dict[str, str]]:
    accepted: dict[tuple[str, ...], dict[str, str]] = {}
    for source_row in rows:
        row = {str(k): str(v or "") for k, v in source_row.items()}
        identity = validate_membership_row(
            row, expected_run=expected_run, expected_cutoff=expected_cutoff, allow_absent=allow_absent
        )
        if identity is not None:
            row.update({
                "family_id": identity.family_id,
                "run_id": str(identity.run_id),
                "normalized_cutoff": identity.normalized_cutoff,
                "qualified_family_id": identity.qualified_family_id,
                "gcf_namespace": identity.gcf_namespace,
            })
        key = tuple(row.get(field, "") for field in key_fields)
        prior = accepted.get(key)
        if prior is None:
            accepted[key] = row
        elif prior != row:
            raise NamespaceError("DUPLICATE_CONFLICT", "conflicting duplicate portable membership rows")
    return [accepted[key] for key in sorted(accepted)]


def load_membership_tsv(
    source: str | os.PathLike[str], *, key_fields: Sequence[str],
    expected_run: object | None = None, expected_cutoff: object | None = None,
    allow_absent: bool = False,
) -> list[dict[str, str]]:
    with open(source, encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    return validate_membership_rows(
        rows, key_fields=key_fields, expected_run=expected_run,
        expected_cutoff=expected_cutoff, allow_absent=allow_absent,
    )


def atomic_write_text(target: str | os.PathLike[str], text: str) -> None:
    destination = Path(target)
    directory = destination.parent
    handle, temporary = tempfile.mkstemp(prefix=".bigscape-gcf-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="") as stream:
            stream.write(text)
        os.replace(temporary, destination)
    except BaseException:
        # v9.7.405 rebase: was `except OSError: pass` — an untyped swallow that trips the
        # repo_health ratchet (zero headroom at 154). contextlib.suppress is behaviour-identical
        # and is the conversion already used for the same temp-file cleanup shape elsewhere.
        with contextlib.suppress(OSError):
            os.unlink(temporary)
        raise


def public_error(error: NamespaceError) -> str:
    return str(error)
