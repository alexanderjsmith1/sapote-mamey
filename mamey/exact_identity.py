"""Fail-closed helpers for the permanent exact-locus display contract.

An individual BGC is displayed as::

    strain / full node-or-contig / region / BGC alias

The alias is deliberately last and secondary.  These helpers are presentation
and validation utilities; they do not infer or repair missing biological
identity.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass


class ExactLocusIdentityError(ValueError):
    """Raised when a complete exact-locus identity cannot be formed."""


_MISSING = {"", "?", "-", "na", "n/a", "nan", "none", "null", "unknown"}
_SHORT_NODE = re.compile(r"^NODE_\d+$", re.IGNORECASE)
_REGION = re.compile(r"^region\d{3,}$", re.IGNORECASE)


@dataclass(frozen=True)
class NativeManifestBGCIdentity:
    """Validated current-producer identity with display and join roles kept distinct."""

    strain: str
    full_contig: str
    normalized_node_id: str
    region: str
    bgc_alias: str
    exact_locus: str


@dataclass(frozen=True)
class NativeLegacyEvidenceAnchorBinding:
    """A same-package normalized evidence key bound to an admitted board row.

    This is deliberately not a second physical-locus identity.  Legacy v9.7.409
    profile/convergence anchors carry a normalized producer token but not the
    full physical contig used for display.
    """

    status: str
    board_identity: NativeManifestBGCIdentity


def _required(value: object, label: str) -> str:
    text = "" if value is None else str(value).strip()
    if text.lower() in _MISSING:
        raise ExactLocusIdentityError(f"missing {label}; exact-locus identity is fail-closed")
    if any(ch in text for ch in ("\n", "\r", "|")):
        raise ExactLocusIdentityError(f"unsafe {label}; exact-locus identity is fail-closed")
    return text


def exact_locus_display(
    strain: object,
    full_node_or_contig: object,
    region: object,
    bgc_alias: object,
) -> str:
    """Return the complete human display identity, or raise without guessing."""
    strain_text = _required(strain, "strain")
    node_text = _required(full_node_or_contig, "full node-or-contig")
    region_text = _required(region, "region")
    alias_text = _required(bgc_alias, "BGC alias")
    if _SHORT_NODE.fullmatch(node_text):
        raise ExactLocusIdentityError(
            f"short node token {node_text!r} is not a full node-or-contig identifier"
        )
    if not _REGION.fullmatch(region_text):
        raise ExactLocusIdentityError(
            f"region {region_text!r} is not the required regionNNN identity"
        )
    return f"{strain_text} / {node_text} / {region_text} / {alias_text}"


def exact_locus_from_mapping(strain: object, row: Mapping[str, object]) -> str:
    """Form a complete identity from a package inventory/triage row.

    Only known field aliases are considered. Missing fields remain errors, and
    multiple supplied aliases for one identity component must agree. This
    accepts current package producer spellings such as lower-case contig; it
    never derives identity from a filename or repairs a shortened node.
    """
    def consistent(label: str, *keys: str) -> object:
        supplied: list[str] = []
        for key in keys:
            value = row.get(key)
            if value is not None and str(value).strip().lower() not in _MISSING:
                supplied.append(_required(value, label))
        unique = set(supplied)
        if len(unique) > 1:
            raise ExactLocusIdentityError(
                f"conflicting {label} values across supplied identity synonyms"
            )
        return supplied[0] if supplied else None

    package_strain = _required(strain, "strain")
    row_strain = consistent("strain", "strain", "strain_id", "Strain", "Strain_ID")
    if row_strain is not None and row_strain != package_strain:
        raise ExactLocusIdentityError("conflicting strain values across package and row identity")

    return exact_locus_display(
        package_strain,
        consistent("full node-or-contig", "Full_Node_ID", "full_node_or_contig", "full_node",
                   "Node_ID", "node_id", "node", "Contig", "contig"),
        consistent("region", "antiSMASH_Region", "antismash_region", "region", "Region"),
        consistent("BGC alias", "BGC_ID", "bgc_id", "bgc_alias", "BGC_alias"),
    )


def exact_locus_from_native_manifest_bgc(
    strain: object,
    row: Mapping[str, object],
) -> NativeManifestBGCIdentity:
    """Validate one current native manifest BGC without conflating typed fields.

    Native Mamey manifests carry the authoritative physical ``contig`` alongside
    a producer-normalized ``node_id`` used by existing database joins.  The
    relationship is validated from the full contig alone: source paths are never
    consulted.  Every other supplied synonym remains visible to the generic
    conflict checker.
    """
    package_strain = _required(strain, "strain")
    full_contig = _required(row.get("contig"), "native manifest contig")
    normalized_node_id = _required(row.get("node_id"), "native manifest node_id")
    region = _required(row.get("antismash_region"), "native manifest antismash_region")
    bgc_alias = _required(row.get("bgc_id"), "native manifest bgc_id")

    # Local import keeps the generic identity helpers independent of the model-heavy
    # crosswalk module unless the explicitly typed native-producer path is selected.
    from .crosswalk import infer_node_id

    expected_node_id = infer_node_id(full_contig, "")
    if normalized_node_id != expected_node_id:
        raise ExactLocusIdentityError(
            "native manifest node_id does not match the producer normalization of contig"
        )

    # Remove only the already-validated native lower-case join field.  Upper-case
    # Node_ID and every other supplied synonym remain, so a real conflict cannot be
    # hidden by rebuilding a four-field mapping.
    display_row = dict(row)
    display_row.pop("node_id", None)
    exact_locus = exact_locus_from_mapping(package_strain, display_row)
    return NativeManifestBGCIdentity(
        strain=package_strain,
        full_contig=full_contig,
        normalized_node_id=normalized_node_id,
        region=region,
        bgc_alias=bgc_alias,
        exact_locus=exact_locus,
    )


def exact_locus_from_native_inventory_row(
    strain: object,
    row: Mapping[str, object],
) -> NativeManifestBGCIdentity:
    """Validate current inventory/triage CSV roles through the native owner.

    ``Contig`` owns the full physical locator; ``Node_ID`` is the normalized
    producer key. The optional legacy ``Region`` is a numeric ordinal that
    must agree with ``antiSMASH_Region``. Other supplied spellings remain
    visible to the existing conflict checks. This adapter never changes the source row or consults a
    source filename.
    """
    roles = {
        "contig": "Contig",
        "node_id": "Node_ID",
        "antismash_region": "antiSMASH_Region",
        "bgc_id": "BGC_ID",
    }
    supplied = {
        native: _required(row.get(column), f"native inventory {column}")
        for native, column in roles.items()
    }
    if "node_id" in row:
        lower_node = _required(row["node_id"], "native inventory node_id")
        if lower_node != supplied["node_id"]:
            raise ExactLocusIdentityError(
                "conflicting normalized node keys across native inventory roles"
            )
    native_row = dict(row)
    # Inventory's legacy Region is a numeric ordinal, unlike its canonical
    # antiSMASH_Region label. Validate their relationship before removing only
    # this known producer role from generic textual-synonym validation.
    if "Region" in row:
        ordinal = _required(row["Region"], "native inventory numeric Region")
        label = supplied["antismash_region"]
        if (not re.fullmatch(r"[0-9]+", ordinal) or not _REGION.fullmatch(label)
                or ordinal.lstrip("0") != label[6:].lstrip("0")):
            raise ExactLocusIdentityError(
                "native inventory numeric Region disagrees with antiSMASH_Region"
            )
        native_row.pop("Region")
    for native, value in supplied.items():
        native_row.setdefault(native, value)
    # The native owner validates this normalized key against the full contig.
    # Keep every other original field for its generic synonym consistency check.
    native_row.pop("Node_ID")
    return exact_locus_from_native_manifest_bgc(strain, native_row)


def validate_native_legacy_evidence_anchor(
    package_strain: object,
    row: Mapping[str, object],
    board_identity: NativeManifestBGCIdentity,
) -> NativeLegacyEvidenceAnchorBinding:
    """Bind one old normalized profile/convergence anchor to an admitted board row.

    This accepts only the lower-case v9.7.409 evidence-anchor roles.  It never
    constructs a full-contig identity from the evidence row.  A row offering a
    richer identity spelling must be routed through the appropriate strict
    full/native validator instead of being silently treated as legacy.
    """
    expected_strain = _required(package_strain, "package strain")
    if expected_strain != board_identity.strain:
        raise ExactLocusIdentityError("legacy evidence package strain conflicts with admitted board")

    required = ("strain", "contig", "region", "bgc_id")
    values = {key: _required(row.get(key), f"legacy evidence {key}") for key in required}
    richer_identity_keys = {
        "strain_id", "Strain", "Strain_ID",
        "Full_Node_ID", "full_node_or_contig", "full_node",
        "Node_ID", "node_id", "node", "Contig",
        "antiSMASH_Region", "antismash_region", "Region",
        "BGC_ID", "bgc_alias", "BGC_alias",
    }
    supplied_richer = sorted(key for key in richer_identity_keys if key in row)
    if supplied_richer:
        raise ExactLocusIdentityError(
            "legacy evidence anchor carries richer identity fields: " + ", ".join(supplied_richer)
        )
    if values["strain"] != board_identity.strain:
        raise ExactLocusIdentityError("legacy evidence strain conflicts with admitted board")
    if values["contig"] != board_identity.normalized_node_id:
        raise ExactLocusIdentityError("legacy evidence normalized contig conflicts with admitted board")
    if values["region"] != board_identity.region:
        raise ExactLocusIdentityError("legacy evidence region conflicts with admitted board")
    if values["bgc_id"] != board_identity.bgc_alias:
        raise ExactLocusIdentityError("legacy evidence BGC alias conflicts with admitted board")
    return NativeLegacyEvidenceAnchorBinding(
        status="NORMALIZED_ANCHOR_BOUND_TO_BOARD",
        board_identity=board_identity,
    )
