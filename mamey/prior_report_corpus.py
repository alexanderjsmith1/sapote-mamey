"""Parse prior report corpora into source-bound, non-authoritative modules.

The adapters retain source-scoped BGC aliases. They do not promote an old
ordinal, rank, node label, interpretation, or compound name to current
evidence. Current-locus identity is governed separately.
"""

from __future__ import annotations

import re
from pathlib import Path


MODULE_STATES = {
    "PRELIMINARY_SOURCE_BOUND_NOT_VERIFIED",
    "VERIFIED_CURRENT",
    "SUPERSEDED_RETAINED_FOR_PROVENANCE",
    "HOLD_IDENTITY_REMAP",
}
MODULE_FORMATS = {
    "V7_RANKED_ATLAS_MARKDOWN",
    "PRELIMINARY_MODE_B_COMPILATION_MARKDOWN",
}

# A report is assembled quickly in stage 1, then individual modules are
# promoted (or held/superseded) in stage 2.  This catalog is deliberately
# data-like: report builders can expose the same lifecycle without embedding
# user paths or silently treating prior prose as current evidence.
REPORT_MODULE_CATALOG = (
    {
        "module_type": "EXACT_IDENTITY",
        "phase": "STAGE_1_PRELIMINARY_ASSEMBLY",
        "tool_or_input": "exact assembly/node/region/profile identity registry",
        "promotion_gate": "one exact current region occurrence",
    },
    {
        "module_type": "EXACT_GENE_DOMAIN_INVENTORY",
        "phase": "STAGE_1_PRELIMINARY_ASSEMBLY",
        "tool_or_input": "antiSMASH GBK parser plus exact sequence registry",
        "promotion_gate": "exact region identity and sequence hashes",
    },
    {
        "module_type": "EXACT_PROFILE_CALLS",
        "phase": "STAGE_1_PRELIMINARY_ASSEMBLY",
        "tool_or_input": "strict/relaxed/loose archive ledger",
        "promotion_gate": "same assembly and compatible antiSMASH version",
    },
    {
        "module_type": "OBSERVED_BLASTP_CHANNELS",
        "phase": "STAGE_1_PRELIMINARY_ASSEMBLY",
        "tool_or_input": "channel-separated BLASTP database or result tables",
        "promotion_gate": "submitted query bytes plus database/run receipt",
    },
    {
        "module_type": "V7_LITERATURE_ATLAS",
        "phase": "STAGE_1_PRELIMINARY_ASSEMBLY",
        "tool_or_input": "hash-bound V7 report corpus",
        "promotion_gate": "paragraph disposition against current locus evidence",
    },
    {
        "module_type": "PRELIMINARY_MODE_B",
        "phase": "STAGE_1_PRELIMINARY_ASSEMBLY",
        "tool_or_input": "hash-bound preliminary Mode B corpus",
        "promotion_gate": "current identity, channel coverage and claim review",
    },
    {
        "module_type": "MIBIG_KCB_COMPARATOR_CHILDREN",
        "phase": "STAGE_2_VERIFICATION_PROMOTION",
        "tool_or_input": "MiBIG per-gene plus KnownClusterBlast child rows",
        "promotion_gate": "one-to-many exact query and comparator provenance",
    },
    {
        "module_type": "CLUSTERBLAST_COMPARATOR_CHILDREN",
        "phase": "STAGE_2_VERIFICATION_PROMOTION",
        "tool_or_input": "ClusterBlast per-gene and ordered locus context",
        "promotion_gate": "subject/version binding and topology-preserving children",
    },
    {
        "module_type": "LOCUS_DOMAIN_MAP",
        "phase": "STAGE_2_VERIFICATION_PROMOTION",
        "tool_or_input": "Figure Studio editable locus/domain project",
        "promotion_gate": "exact coordinates, protein hashes and collision-safe render",
    },
    {
        "module_type": "PROFILE_DELTA",
        "phase": "STAGE_2_VERIFICATION_PROMOTION",
        "tool_or_input": "exact paired-profile comparison",
        "promotion_gate": "same assembly/version gate and correspondence classification",
    },
    {
        "module_type": "PARAGRAPH_DISPOSITION",
        "phase": "STAGE_2_VERIFICATION_PROMOTION",
        "tool_or_input": "V7/Mode B paragraph reconciliation",
        "promotion_gate": "retain/update/supersede/remap/hold decision per paragraph",
    },
    {
        "module_type": "CURRENT_MODE_B_VERIFICATION",
        "phase": "STAGE_2_VERIFICATION_PROMOTION",
        "tool_or_input": "Mode B verification engine and evidence coverage ledger",
        "promotion_gate": "all consumed assertions source-bound with claim ceilings",
    },
)

_V7 = re.compile(
    r"^## Rank (?P<rank>\d+): (?P<strain>[^ ]+) (?P<alias>BGC\d+)\s*-\s*(?P<title>.*)$",
    re.MULTILINE,
)
_MODE_B = re.compile(
    r"^## Mode B\s*[—-]\s*(?P<alias>BGC\d+)\s*\((?P<locator>[^)]+)\)\s*[—-]\s*(?P<strain>\S+)\s*$",
    re.MULTILINE,
)
_COMPILATION_CARD = re.compile(
    r"^###\s+\d+(?:\.\d+)+\s+(?P<alias>BGC\d+)\b.*$",
    re.MULTILINE,
)
_MODE_B_TEMPLATE = re.compile(
    r"<!--\s*MODE B TEMPLATE\s*\|\s*bgc:\s*(?P<alias>BGC\d+)\s*\|"
    r"\s*node:\s*(?P<locator>[^|]+?)\s*\|"
    r"\s*strain:\s*(?P<strain>[^|>\n]+?)\s*(?:\||-->)",
    re.IGNORECASE,
)


def _sections(text: str, pattern: re.Pattern[str]) -> list[tuple[re.Match[str], str]]:
    matches = list(pattern.finditer(text))
    return [
        (match, text[match.start(): matches[index + 1].start() if index + 1 < len(matches) else len(text)].strip())
        for index, match in enumerate(matches)
    ]


def _mode_b_sections(text: str) -> list[tuple[re.Match[str], str]]:
    """Split Mode B cards at every structural card boundary.

    The historical compilation interleaves full ``## Mode B`` cards with
    compact ``### 3.x BGC...`` cards.  Stopping only at the next full Mode B
    heading silently appended a compact card to nearly every extracted
    module.  The nearest of either boundary is therefore authoritative.
    """
    matches = list(_MODE_B.finditer(text))
    compact = list(_COMPILATION_CARD.finditer(text))
    sections: list[tuple[re.Match[str], str]] = []
    for index, match in enumerate(matches):
        candidates = [
            boundary.start()
            for boundary in compact
            if boundary.start() > match.start()
        ]
        if index + 1 < len(matches):
            candidates.append(matches[index + 1].start())
        end = min(candidates) if candidates else len(text)
        sections.append((match, text[match.start():end].strip()))
    return sections


def module_consistency_issues(
    content: str, *, expected_alias: str, expected_strain: str,
    expected_source_locator: str = "",
) -> list[str]:
    """Return structural cross-locus defects in one extracted prior module."""
    issues: list[str] = []
    headers = list(_MODE_B.finditer(content))
    if len(headers) != 1:
        issues.append(f"MODE_B_HEADER_COUNT_{len(headers)}")
    elif (
        headers[0].group("alias") != expected_alias
        or headers[0].group("strain") != expected_strain
    ):
        issues.append("MODE_B_HEADER_IDENTITY_MISMATCH")
    if _COMPILATION_CARD.search(content):
        issues.append("FOREIGN_COMPACT_BGC_CARD_PRESENT")
    for marker in _MODE_B_TEMPLATE.finditer(content):
        if marker.group("alias") != expected_alias:
            issues.append("FOREIGN_MODE_B_TEMPLATE_ALIAS")
        if marker.group("strain").strip() != expected_strain:
            issues.append("FOREIGN_MODE_B_TEMPLATE_STRAIN")
        if (
            expected_source_locator
            and marker.group("locator").strip() != expected_source_locator.strip()
        ):
            issues.append("MODE_B_TEMPLATE_LOCATOR_MISMATCH")
    return sorted(set(issues))


def parse_module_source(path: Path, source_format: str, expected_strain: str) -> dict[str, dict]:
    """Return one extracted module per source-scoped BGC alias."""
    if source_format not in MODULE_FORMATS:
        raise ValueError(f"Unsupported prior-report format: {source_format!r}")
    text = path.read_text(encoding="utf-8-sig")
    pattern = _V7 if source_format == "V7_RANKED_ATLAS_MARKDOWN" else _MODE_B
    parsed: dict[str, dict] = {}
    sections = (
        _mode_b_sections(text)
        if source_format == "PRELIMINARY_MODE_B_COMPILATION_MARKDOWN"
        else _sections(text, pattern)
    )
    for match, body in sections:
        values = match.groupdict()
        if values["strain"] != expected_strain:
            raise ValueError(
                f"Prior-report strain mismatch in {path.name}: expected {expected_strain}, "
                f"found {values['strain']}"
            )
        alias = values["alias"]
        if alias in parsed:
            raise ValueError(f"Duplicate {alias} module in {path.name}")
        if source_format == "PRELIMINARY_MODE_B_COMPILATION_MARKDOWN":
            issues = module_consistency_issues(
                body,
                expected_alias=alias,
                expected_strain=expected_strain,
                expected_source_locator=values.get("locator", ""),
            )
            if issues:
                raise ValueError(
                    f"Mode B consistency gate failed for {alias} in {path.name}: "
                    + ",".join(issues)
                )
        parsed[alias] = {
            "source_scoped_bgc_alias": alias,
            "source_format": source_format,
            "source_rank": values.get("rank", ""),
            "source_locator_text": values.get("locator", ""),
            "source_title": values.get("title", ""),
            "content_markdown": body + "\n",
        }
    if not parsed:
        raise ValueError(f"No BGC modules found in {path.name} for {source_format}")
    return parsed
