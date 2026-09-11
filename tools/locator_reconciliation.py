#!/usr/bin/env python3
"""
locator_reconciliation.py — verify a Mode B card's header fields match the canonical
triage row for that BGC. Sprint-1 idea from the ChatGPT patch chat.

The AS-XXX failure mode: a card manually reconstructs its BGC label / locator / node /
products, and they drift from the authoritative triage row (a stale locator, a node
mismatch, a products string that doesn't match). Cards should render these directly from
the triage row; this tool catches the cases where they didn't.

Usage:
  from tools.locator_reconciliation import reconcile_card, extract_card_header_fields
  errors = reconcile_card(card_markdown, triage_row_dict)
"""
from __future__ import annotations

import json
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import re

# Canonical fields that must agree between a card header and its triage row.
_RECONCILED_FIELDS = ("BGC_ID", "Assembly_Locator", "Node_ID", "Products", "Boundary")

# Field-name aliases: triage CSVs and card headers don't always use identical labels.
_ALIASES = {
    "BGC_ID": ("bgc_id", "bgc", "id"),
    "Assembly_Locator": ("assembly_locator", "user_label", "locator"),
    "Node_ID": ("node_id", "node", "contig"),
    "Products": ("products", "product"),
    "Boundary": ("boundary", "edge_status", "edge"),
    "Misanchor_Flag": ("misanchor_flag", "misanchor"),  # v9.7.123: renamed column
}


def _norm(s) -> str:
    """Normalise a field value for comparison: lowercase, collapse whitespace, strip."""
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


def _get(row: dict, field: str) -> str:
    """Pull a field from a row by canonical name or any known alias."""
    if field in row:
        return row[field]
    for alias in _ALIASES.get(field, ()):
        for k in row:
            if k.lower() == alias:
                return row[k]
    return ""


def extract_card_header_fields(text: str, scan_lines: int = 40) -> dict:
    """Parse BGC_ID / locator / node / products / boundary from a Mode B card header.

    Handles two formats:
      1. Heading line — ``## BGC001 (AS-XXX · region1)`` — parsed via _RE_CARD_HEADER.
      2. Bold key-value lines — ``**Node/Contig:** NODE_xxx · Edge`` — parsed by splitting
         on the first ``:`` and stripping markdown emphasis from both sides.

    v9.7.123 (SM-P0-003): added heading-line parsing and ``node/contig`` key alias so
    the standard Mode B card format is fully reconcilable against the triage row.
    """
    fields: dict[str, str] = {}
    canonical = {f.lower(): f for f in _RECONCILED_FIELDS}
    # Extend aliases with card-specific key spellings
    card_aliases = {
        "node/contig": "Node_ID",   # "**Node/Contig:** NODE_xxx · Edge"
        "node_id": "Node_ID",
        "node": "Node_ID",
        "contig": "Node_ID",
        "products": "Products",
        "product": "Products",
        "boundary": "Boundary",
        "assembly_locator": "Assembly_Locator",
        "user_label": "Assembly_Locator",
        "locator": "Assembly_Locator",
        "bgc_id": "BGC_ID",
        "bgc": "BGC_ID",
    }
    all_aliases = {a: f for f, al in _ALIASES.items() for a in al}
    all_aliases.update(card_aliases)

    lines = text.splitlines()[:scan_lines]

    # 1. Extract BGC_ID and Assembly_Locator from the ## heading line via spec regex
    for line in lines:
        m = _RE_CARD_HEADER.search(line)
        if m:
            fields["BGC_ID"] = f"BGC{m.group(1)}"
            locator = m.group(2).strip()
            # Remove trailing · region fragment if present in the locator part
            locator = re.sub(r'\s*·\s*region\d+\s*$', '', locator, flags=re.I).strip()
            if locator:
                fields["Assembly_Locator"] = locator
            break  # only parse the first BGC heading

    # 2. Parse bold key-value lines ("**Key:** value" or "Key: value")
    for line in lines:
        if ":" not in line:
            continue
        key_raw, val_raw = line.split(":", 1)
        # Strip markdown: leading #, *, spaces; trailing *
        key_norm = re.sub(r'[*#\s]', '', key_raw).lower()
        canon = canonical.get(key_norm) or all_aliases.get(key_norm)
        if not canon:
            continue
        val = val_raw.strip().strip("*").strip()
        # For Node_ID: strip trailing " · Edge" / " · Interior" / " · Full-contig"
        # and capture the boundary token while we're there.
        if canon == "Node_ID":
            boundary_m = re.search(
                r'\s*·\s*(Edge|Interior|Full-contig|Full.contig)',
                val, flags=re.I
            )
            if boundary_m and "Boundary" not in fields:
                # Normalise "Full-contig" variants → "Full-contig"
                b = boundary_m.group(1)
                fields["Boundary"] = "Full-contig" if "contig" in b.lower() else b
            val = re.split(r'\s*·\s*(?:Edge|Interior|Full-contig|full.contig)', val,
                           maxsplit=1, flags=re.I)[0].strip()
        if val and canon not in fields:
            fields[canon] = val

    return fields


def reconcile_card(card_text_or_fields, triage_row: dict) -> list[dict]:
    """Compare legacy/display card fields to the triage row.

    Accepts either raw card markdown (header is parsed) or a pre-parsed fields dict.
    A field absent from BOTH sides is not a mismatch; a field present on one side and
    differing on the other is.

    This is a legacy secondary-field comparator.  It is not an exact-locus identity
    authority.  Authoritative individual-BGC reconciliation is performed only by
    :func:`reconcile_heading_only` and :func:`reconcile_card_verdict`, both of which
    require one complete four-part identity.
    """
    if isinstance(card_text_or_fields, str):
        card_fields = extract_card_header_fields(card_text_or_fields)
    else:
        card_fields = dict(card_text_or_fields)

    errors = []
    for field in _RECONCILED_FIELDS:
        card_val = _norm(_get(card_fields, field))
        triage_val = _norm(_get(triage_row, field))
        if not card_val and not triage_val:
            continue  # neither side asserts it — nothing to reconcile
        if card_val != triage_val:
            errors.append({
                "field": field,
                "card": _get(card_fields, field),
                "triage": _get(triage_row, field),
            })
    return errors

import re

# ── Spec regex (SM-P0-003) ─────────────────────────────────────────────────────
# Parses a Mode B card heading: "BGC001 (AS-XXX · region1)" or "BGC001 (AS-XXX)"
_RE_CARD_HEADER = re.compile(
    r'BGC(\d+)\s*\(([^·()\n]+?)(?:\s*·\s*(region\d+))?\)', re.I
)

# v9.7.358 (the review lane, 2026-08-10): the current emitter writes the title as
#   `# Mode B — BGC007 (NODE_14_length_159225_cov_15) — AS-XXX`
# i.e. node-in-parens, strain after an em-dash, and NO region — so _RE_CARD_HEADER's
# group(3) is None on every current-engine card and the region was never recovered.
# The region IS present, in §1 (`**antiSMASH region:** region001`), measured at
# 1,962/1,962 mode_b_v9.7.339 cards. Fall back to it. Note §1 sits ~4.6 kB into the
# card, far beyond the old 500-char header window, so this scans the whole text.
_RE_S1_REGION = re.compile(r'\*\*antiSMASH region:\*\*\s*(region\d+)', re.I)

# CSV columns emitted by reconcile_batch
_CSV_COLUMNS = [
    "BGC_ID", "status", "exit_code", "mismatched_fields",
    "card_value", "triage_value", "refusal_reason", "identity_display",
    "secondary_fields", "Misanchor_Flag",
]


def _parse_header_region(card_text: str) -> str | None:
    """Extract the antiSMASH region string from a card header. None if absent."""
    m = _RE_CARD_HEADER.search(card_text[:500])  # only scan the header area
    if m and m.group(3):
        return m.group(3)
    # Fallback: the canonical §1 identity block (see _RE_S1_REGION note).
    s1 = _RE_S1_REGION.search(card_text)
    return s1.group(1) if s1 else None


# v9.7.374 (audit lane claim-safety/locator-gate audit): mamey/modeb_template_emitter.py's
# _header_block() emits the STARTING authoring scaffold's H1 title as
# `# Mode B — {strain} / {node} / {region} / {bgc}` (slash-separated) — its own docstring calls
# this "the top-of-card metadata banner the chat must preserve". _RE_CARD_HEADER only matches the
# paren-form convention (`BGCnnn (NODE_x · regionY)`) that filed cards use by established
# authoring convention (every shipped exemplar under docs/reference/modeb_exemplars/, and the
# citation convention documented in docs/ISSUES_EXPERIENCED_DURING_DEVELOPMENT.md, use the paren
# form) — but if a card is ever filed with the raw emitted scaffold header intact, the paren-form
# regex cannot match it at all, and reconcile_heading_only returned UNPARSEABLE (a BLOCKING FAIL
# in mamey/seal_package.py::_gate_locator) even when the node/region in that header are 100%
# correct — live-reproduced against a verbatim _header_block() output with a triage row that
# agreed on every field. Recognize the slash-form as a second, explicit heading shape so a
# well-formed heading in the OTHER format the codebase itself emits is not mis-declared
# UNPARSEABLE; a genuine node/region disagreement in that form still correctly flags.
_RE_EXACT_LOCUS_HEADER = re.compile(
    r'^#\s*Mode\s*B\s*[\u2014\-]\s*([^/\n]+?)\s*/\s*([^/\n]+?)\s*/\s*'
    r'([^/\n]+?)\s*/\s*([^/\n]+?)\s*$',
    re.M,
)

# Compatibility name retained for importers.  Unlike the former regex, every match now
# captures all four fields in their canonical order.  No consumer may treat a two-field
# node/region match as an authoritative individual-BGC identity.
_RE_CARD_HEADER_SLASH = _RE_EXACT_LOCUS_HEADER

_IDENTITY_COMPONENTS = (
    "strain", "full_node_or_contig", "region", "bgc_alias",
)
_PLACEHOLDERS = {"", "?", "-", "--", "---", "\u2014", "unknown", "unreported", "na", "n/a"}


def _clean(value) -> str:
    """Strip structural whitespace without case-folding, rounding, or fuzzy repair."""
    return str(value or "").strip()


def _is_placeholder(value: str) -> bool:
    return _clean(value).lower() in _PLACEHOLDERS


def _row_observations(row: dict, names: tuple[str, ...]) -> list[dict]:
    """Return exact, source-labelled values for a case-insensitive field-name set."""
    wanted = {name.lower() for name in names}
    out = []
    for key, raw in row.items():
        if str(key).lower() not in wanted:
            continue
        value = _clean(raw)
        if not _is_placeholder(value):
            out.append({"field": str(key), "value": value})
    return out


def _one_expected_value(row: dict, component: str, names: tuple[str, ...]):
    observations = _row_observations(row, names)
    values = []
    for item in observations:
        if item["value"] not in values:
            values.append(item["value"])
    if len(values) > 1:
        return None, observations, {
            "field": component,
            "card": "",
            "triage": "; ".join(values),
            "reason": "conflicting authoritative triage fields",
        }
    return (values[0] if values else None), observations, None


def _expected_identity(triage_row: dict) -> tuple[dict | None, list[dict], list[dict], str | None]:
    """Extract one exact expected identity while keeping display aliases secondary."""
    identity = {}
    sources = []
    errors = []

    specs = (
        ("strain", ("Strain", "strain_id")),
        ("region", ("antiSMASH_Region", "Region", "region")),
        ("bgc_alias", ("BGC_ID", "bgc_alias")),
    )
    for component, names in specs:
        value, observations, conflict = _one_expected_value(triage_row, component, names)
        sources.extend({"component": component, **item} for item in observations)
        if conflict:
            errors.append(conflict)
        elif value is not None:
            identity[component] = value

    # A declared full contig is authoritative.  Node_ID is an exact source only when a
    # full-node/contig field is absent; when both exist, Node_ID remains a typed display alias.
    full_value, full_obs, full_conflict = _one_expected_value(
        triage_row, "full_node_or_contig",
        ("Full_Node_or_Contig", "full_node_or_contig", "Contig"),
    )
    node_value, node_obs, node_conflict = _one_expected_value(
        triage_row, "node_id_secondary", ("Node_ID",),
    )
    sources.extend({"component": "full_node_or_contig", **item} for item in full_obs)
    if full_conflict:
        errors.append(full_conflict)
    elif full_value is not None:
        identity["full_node_or_contig"] = full_value
    elif node_conflict:
        errors.append(node_conflict)
    elif node_value is not None:
        identity["full_node_or_contig"] = node_value

    secondary = []
    if full_value is not None:
        secondary.extend(
            {"kind": "DISPLAY_NODE_ALIAS", **item} for item in node_obs
        )
    for names, kind in (
        (("Assembly_Locator",), "LEGACY_ASSEMBLY_LOCATOR"),
        (("User_Label", "user_label"), "DISPLAY_USER_LABEL"),
        (("bgc", "id"), "LEGACY_BGC_ALIAS"),
    ):
        secondary.extend({"kind": kind, **item} for item in _row_observations(triage_row, names))

    if errors:
        return None, secondary, errors, "EXPECTED_IDENTITY_CONFLICT"
    missing = [name for name in _IDENTITY_COMPONENTS if _is_placeholder(identity.get(name, ""))]
    if missing:
        return None, secondary, [{
            "field": name, "card": "", "triage": "", "reason": "missing expected identity field"
        } for name in missing], "EXPECTED_IDENTITY_INCOMPLETE"
    if not re.fullmatch(r"region\d+", identity["region"]):
        return None, secondary, [{
            "field": "region", "card": "", "triage": identity["region"],
            "reason": "expected region is not an exact region token",
        }], "EXPECTED_IDENTITY_INVALID"
    if not re.fullmatch(r"BGC\d+", identity["bgc_alias"]):
        return None, secondary, [{
            "field": "bgc_alias", "card": "", "triage": identity["bgc_alias"],
            "reason": "expected BGC alias is not an exact BGC token",
        }], "EXPECTED_IDENTITY_INVALID"
    return identity, secondary, [], None


def _legacy_secondary_fields(card_text: str) -> list[dict]:
    fields = extract_card_header_fields(card_text)
    return [
        {"kind": "LEGACY_CARD_FIELD", "field": key, "value": value}
        for key, value in sorted(fields.items()) if not _is_placeholder(value)
    ]


def _identity_display(identity: dict | None) -> str:
    if not identity:
        return ""
    return " / ".join(identity[name] for name in _IDENTITY_COMPONENTS)


def _reconcile_exact_identity(card_text: str, triage_row: dict) -> dict:
    """Require exactly one complete exact-locus header and compare all four fields."""
    secondary = {
        "card": _legacy_secondary_fields(card_text),
        "triage": [],
    }
    expected, triage_secondary, expected_errors, expected_refusal = _expected_identity(triage_row)
    secondary["triage"] = triage_secondary
    if expected_refusal:
        return {
            "status": "MISMATCH" if expected_refusal.endswith("CONFLICT") else "UNPARSEABLE",
            "errors": expected_errors,
            "refusal_reason": expected_refusal,
            "identity_display": "",
            "secondary_fields": secondary,
        }

    matches = list(_RE_EXACT_LOCUS_HEADER.finditer(card_text))
    if not matches:
        return {
            "status": "UNPARSEABLE",
            "errors": [{
                "field": "identity", "card": "", "triage": _identity_display(expected),
                "reason": "zero exact four-part identity headers",
            }],
            "refusal_reason": "ZERO_EXACT_IDENTITIES",
            "identity_display": "",
            "secondary_fields": secondary,
        }
    if len(matches) != 1:
        return {
            "status": "MISMATCH",
            "errors": [{
                "field": "identity", "card": str(len(matches)),
                "triage": _identity_display(expected),
                "reason": "multiple exact four-part identity headers",
            }],
            "refusal_reason": "MULTIPLE_EXACT_IDENTITIES",
            "identity_display": "",
            "secondary_fields": secondary,
        }

    values = [_clean(value) for value in matches[0].groups()]
    card_identity = dict(zip(_IDENTITY_COMPONENTS, values))
    missing = [name for name, value in card_identity.items() if _is_placeholder(value)]
    invalid = []
    if not re.fullmatch(r"region\d+", card_identity["region"]):
        invalid.append("region")
    if not re.fullmatch(r"BGC\d+", card_identity["bgc_alias"]):
        invalid.append("bgc_alias")
    if missing or invalid:
        fields = list(dict.fromkeys(missing + invalid))
        return {
            "status": "UNPARSEABLE",
            "errors": [{
                "field": name, "card": card_identity.get(name, ""),
                "triage": expected.get(name, ""),
                "reason": "missing or invalid exact identity field",
            } for name in fields],
            "refusal_reason": "INCOMPLETE_EXACT_IDENTITY",
            "identity_display": _identity_display(card_identity),
            "secondary_fields": secondary,
        }

    errors = []
    for component in _IDENTITY_COMPONENTS:
        if card_identity[component] != expected[component]:
            errors.append({
                "field": component,
                "card": card_identity[component],
                "triage": expected[component],
                "reason": "exact four-part identity conflict",
            })
    if errors:
        return {
            "status": "MISMATCH",
            "errors": errors,
            "refusal_reason": "IDENTITY_CONFLICT",
            "identity_display": _identity_display(card_identity),
            "secondary_fields": secondary,
        }
    return {
        "status": "PASS",
        "errors": [],
        "refusal_reason": "",
        "identity_display": _identity_display(card_identity),
        "secondary_fields": secondary,
    }


def reconcile_heading_only(card_text: str, triage_row: dict) -> dict:
    """Card-write reconciliation requiring one complete four-part identity.

    Legacy paren headings and body fields are retained in ``secondary_fields`` for
    diagnostics only.  They never fill, normalize, or override a required identity field.
    """
    return _reconcile_exact_identity(card_text, triage_row)


def reconcile_card_verdict(card_text: str, triage_row: dict) -> dict:
    """Full exact-locus verdict for one card versus one authoritative triage row."""
    verdict = _reconcile_exact_identity(card_text, triage_row)
    return {**verdict, "exit_code": 0 if verdict["status"] == "PASS" else 1}


def reconcile_batch(entries: list[dict]) -> list[dict]:
    """Reconcile a list of {"card_text": ..., "triage_row": ...} entries.

    Returns rows suitable for writing to header_locator_reconciliation.csv.
    Each row includes all _CSV_COLUMNS.
    """
    rows = []
    for entry in entries:
        card_text = entry.get("card_text", "")
        triage_row = entry.get("triage_row", {})
        verdict = reconcile_card_verdict(card_text, triage_row)

        # Flatten mismatched fields for CSV
        mismatched = "; ".join(e["field"] for e in verdict["errors"])
        card_val = "; ".join(str(e.get("card", "")) for e in verdict["errors"])
        triage_val = "; ".join(str(e.get("triage", "")) for e in verdict["errors"])
        bgc_id = _get(triage_row, "BGC_ID") or ""

        rows.append({
            "BGC_ID": bgc_id,
            "status": verdict["status"],
            "exit_code": verdict["exit_code"],
            "mismatched_fields": mismatched,
            "card_value": card_val,
            "triage_value": triage_val,
            "refusal_reason": verdict.get("refusal_reason", ""),
            "identity_display": verdict.get("identity_display", ""),
            "secondary_fields": json.dumps(
                verdict.get("secondary_fields", {}), sort_keys=True, separators=(",", ":")
            ),
            "Misanchor_Flag": _get(triage_row, "Misanchor_Flag"),
        })
    return rows


def write_reconciliation_csv(rows: list[dict], out_path) -> None:
    """Write reconciliation rows to a CSV file."""
    import csv
    from pathlib import Path
    out = Path(out_path)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = _SafeDictWriter(f, fieldnames=_CSV_COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":  # v9.7.410: library module — no CLI. The guard exists so the
    # module-level csv_safety import fallback above is not 'work at import' for the tools
    # import-safety ratchet (test_tools_import_safe_v97250) while still carrying the sys.path
    # guard every mamey-importing tool must have (test_tool_front_doors).
    raise SystemExit("locator_reconciliation.py is a library: "
                     "`from tools.locator_reconciliation import reconcile_card` from the bundle root")
