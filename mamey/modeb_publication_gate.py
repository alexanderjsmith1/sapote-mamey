"""Fail-closed publication-candidate checks for expanded Mode B cards.

The gate validates evidence presentation and reconciliation scaffolds. It does
not adjudicate scientific correctness and cannot confer owner acceptance,
integration, rendering, release, or publication approval.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Iterable, Optional

from .modeb_structure_gate import (
    extract_section_bodies,
    find_s4_matrix_block,
    matrix_gene_tag,
)
from .modeb_evidence_state import EVIDENCE_STATES


STREAM_STATES = EVIDENCE_STATES
# v9.7.412 (card surface audit, motivated by the .411 nine-card batch): the two-state
# vocabulary below cannot express a section that WAS reviewed but whose evidence is
# genuinely incomplete or unbound -- an author facing that state had to pick either
# SUBSTANTIVE (overclaiming bound evidence that is not there) or REASONED_NOT_APPLICABLE
# (misrepresenting reviewed-but-thin as inapplicable). REVIEWED_SCOPE_LIMIT is a third,
# distinct disposition: the section was authored and reviewed, and the reviewer's own
# finding is that the bound evidence does not reach a full claim -- not "not applicable",
# not "fully substantive". Deliberately disjoint from EVIDENCE_STATES (mamey/modeb_
# evidence_state.py: UNBOUND, CONTEXT_ONLY, ADMITTED, ABSENT_IN_SCOPE, SUPERSEDED) and
# from HISTORY_DISPOSITIONS below, since a single §28 row's cells are checked against
# all three vocabularies by membership, not by column position -- a name shared with
# either would create a false-positive match unrelated to section disposition.
# This adds the state to the accepted vocabulary only. It does NOT re-derive which of
# the .411 nine-card batch's existing SUBSTANTIVE rows should become REVIEWED_SCOPE_LIMIT
# -- that is a content judgement over each section's actual evidence, left to the card
# author/reviewer, not something a mechanical patch should decide.
SECTION_STATES = {"SUBSTANTIVE", "REASONED_NOT_APPLICABLE", "REVIEWED_SCOPE_LIMIT"}
HISTORY_DISPOSITIONS = {
    "RETAIN", "REFINE", "WITHDRAW_WITH_REASON", "NOT_APPLICABLE",
}
PUBLICATION_EVIDENCE_STREAMS = (
    "antiSMASH", "sealed Mamey", "MIBiG", "BiG-SCAPE", "ClusterBlast",
    "RG-GMCI", "chitin", "resistance", "domain rarity", "literature",
    "prevalence", "historical card", "V7 evidence",
    "current channel-separated BLASTp",
)
HISTORICAL_SOURCES = ("historical card", "V7 evidence", "historical locus map")

_HOMOLOGY_HEADER = re.compile(
    r"blastp|clustered\s*nr|swiss[- ]?prot|top\s+hit|matched\s+protein|%\s*id|identity",
    re.I,
)
_LOCUS = re.compile(
    r"\b(?:ctg\d+_\d+|[A-Za-z]{2,8}\d*_\d{4,6}|"
    r"[A-Za-z]{2,12}_[A-Za-z]{1,4}\d{3,8})\b"
)
_COMPLETE_AS_LOCUS = re.compile(
    r"\bAS-\d+\s*/\s*NODE_[^/\n|]+\s*/\s*region\d+\s*/\s*BGC\d{3}\b",
    re.I,
)
_COMPLETE_SELECTION_LOCUS = re.compile(
    r"\b[A-Za-z][A-Za-z0-9._-]+\s*/\s*NODE_[^/\n|]+\s*/\s*region\d+\s*/\s*BGC\d{3}\b",
    re.I,
)
_COMPLETE_LOCUS = re.compile(
    r"^[^/\n|]+\s*/\s*[^/\n|]+\s*/\s*region\d+\s*/\s*BGC\d{3}$",
    re.I,
)
_GENE_CLAIM_SECTIONS = frozenset((set(range(5, 40)) - {28}) | {41, 45, 46})
_GENE_CLAIM_LANGUAGE = re.compile(
    r"\b(?:gene|protein|enzyme|domain|synthase|synthetase|transferase|oxidoreductase|"
    r"transporter|efflux|resistance|regulator|repressor|activator|carrier|core|tailoring|"
    r"maturase|protease|hydrolase|kinase|phosphatase|ABC|MFS|APH|lactamase)\b",
    re.I,
)
_TYPED_ZERO_RE = re.compile(
    r"ZERO_EXACT_BOUND_CANDIDATES\s*;\s*denominator\s*=\s*(\d+)\s+"
    r"exact displayed proteins?\s*;\s*sources\s*=\s*([^;\n]+)",
    re.I,
)
_TYPED_COHORT_NONE_RE = re.compile(
    r"COHORT_COMPARISON_NOT_AVAILABLE_TYPED\s*;\s*denominator\s*=\s*([^;\n]+)\s*;\s*"
    r"sources\s*=\s*([^;\n]+)\s*;\s*reason\s*=\s*([^;\n]+)",
    re.I,
)

_S27_COLUMNS = (
    "gene", "physical membership", "candidate role", "evidence source",
    "class concordance", "allowed inference",
)
_S27_MEMBERSHIP_STATES = {
    "EXACT_REGION", "BOUNDARY_CONTEXT", "OUTSIDE_EXACT_REGION_QUARANTINED",
}
_S27_CONCORDANCE_STATES = {
    "CONCORDANT", "DISCORDANT", "UNRESOLVED", "NOT_APPLICABLE",
}
_S45_COLUMNS = (
    "comparator exact locus", "query genes", "comparator genes",
    "sequence / synteny evidence", "agreement and mismatch", "allowed inference",
)
_S26_COLUMNS = (
    "condition", "perturbation", "pathway rationale", "measured readout", "decision rule",
)
_S9_COLUMNS = (
    "hypothesis", "evidence for", "evidence against", "discriminating test",
    "current disposition",
)
_S3_BOUNDARY_COLUMNS = (
    "source", "observed boundary", "limitation", "effect on interpretation",
)
_S36_COLUMNS = (
    "model", "genes or interval", "evidence for", "evidence against", "decision consequence",
)
_S20_COLUMNS = (
    "action", "evidence gap resolved", "measured or computed result", "decision change",
    "claim ceiling",
)
_S46_COLUMNS = (
    "comparator exact locus", "query genes", "comparator genes",
    "profile compatibility", "divergence", "allowed inference",
)
_S47_COLUMNS = (
    "comparator exact locus", "verified host metadata", "query genes", "comparator genes",
    "comparator rationale", "sequence / synteny evidence", "transfer limits", "allowed inference",
)
_S10_COLUMNS = (
    "observed geometry", "competing boundary or co-capture model", "evidence for",
    "evidence against", "interpretation consequence", "discriminating closure test",
)
_S12_COLUMNS = (
    "ecological hypothesis", "locus-specific evidence", "evidence against",
    "competing explanation", "causality ceiling", "matched discriminating test",
)
_S17_COLUMNS = (
    "exact in-roster target", "condition rationale", "perturbation", "control",
    "measured readout", "decision rule", "claim ceiling",
)
_S24_COLUMNS = (
    "reference space", "source receipt sha-256", "denominator", "measured result",
    "counterevidence or limitation", "allowed inference", "resolving next action",
)
_S6_V4_COLUMNS = (
    "exact in-roster gene", "candidate reaction", "evidence for", "evidence against",
    "pathway-order or coupling evidence", "distinct alternative role", "allowed inference",
    "discriminating test",
)
_S15_V5_COLUMNS = (
    "missing evidence object", "source / state receipt sha-256", "typed state",
    "why missing", "affected inference", "resolving acquisition", "decision rule",
)
_S19_V5_COLUMNS = (
    "final disposition", "strongest supporting evidence",
    "strongest conflict or alternative", "boundary / completeness state",
    "claim ceiling", "linked highest-information action",
)
_S29_V5_COLUMNS = (
    "partner exact locus", "interaction mechanism", "evidence for",
    "evidence against", "physical-link state", "allowed inference",
    "discriminating test",
)
_S31_V5_COLUMNS = (
    "canonical roster sha-256", "exact-region genes", "boundary-context genes",
    "displayed genes", "missing from displayed roster",
    "extra beyond canonical roster", "reconciliation state",
)
_S43_ACCOUNTING_V5_COLUMNS = (
    "rg-gmci run receipt sha-256", "pair denominator", "high count",
    "moderate count", "low count", "two-proof rescue rows",
)
_S43_ADJUDICATION_V5_COLUMNS = (
    "partner exact locus or measured-zero state", "functional-coupling evidence",
    "physical-link evidence", "distinct alternative", "allowed inference",
    "resolving action",
)
_V6_DECISION_CHAIN_COLUMNS = (
    "typed state", "exact target or measured object", "evidence or terminal basis",
    "alternative or limitation", "allowed inference",
    "resolving action and measured result", "decision consequence",
)
_V6_PROFILES = {
    14: ({"LIMIT_DEFINED", "EVIDENCE_UNAVAILABLE_TYPED"},
         r"claim|inference|product|activity|expression|ecolog|pathway"),
    16: ({"RESULT_MEASURED", "ANALYSIS_NOT_RUN_TYPED"},
         r"BLASTP|HMMER|homolog|protein|domain|profile"),
    21: ({"MASS_MEASURED", "PRECURSOR_NOT_ASSIGNABLE_TYPED"},
         r"precursor|mass|m/z|adduct|processing"),
    22: ({"SEARCH_MEASURED", "SEARCH_NOT_RUN_TYPED"},
         r"RiPP|database|search|precursor|maturation"),
    23: ({"DESIGN_READY", "EXPRESSION_NOT_READY_TYPED"},
         r"heterolog|expression|transferred interval|construct|host"),
    25: ({"NEIGHBOURHOOD_MEASURED", "BOUNDARY_UNRESOLVED_TYPED"},
         r"neighbou?rhood|boundary|interval|synteny|flanking"),
    30: ({"DECISION_BRANCH_DEFINED", "EXPERIMENT_NOT_READY_TYPED"},
         r"hypothesis|model|evidence gap|experiment|branch"),
    41: ({"PHYLOGENY_MEASURED", "PHYLOGENY_NOT_RUN_TYPED"},
         r"phylogen|tree|topology|branch|comparator|support"),
}
_V7_CLAIM_MODEL_COLUMNS = (
    "typed state", "exact target or measured object", "evidence for or terminal basis",
    "evidence against or limitation", "evidence receipt", "narrowest allowed claim",
    "resolving comparison or assay", "result-dependent claim consequence",
)
_V7_PROFILES = {
    8: ({"COMPARATOR_MEASURED", "COMPARATOR_UNAVAILABLE_TYPED"}, r"comparator|KCB|MIBiG|synteny|similarity|cluster"),
    11: ({"FAMILY_MODEL_DEFINED", "FAMILY_UNRESOLVED_TYPED"}, r"product|family|class|scaffold|biosynthetic"),
    13: ({"ACTIVITY_HYPOTHESIS_DEFINED", "ACTIVITY_EVIDENCE_UNAVAILABLE_TYPED"}, r"antibacterial|antifungal|activity|bioactivity|assay"),
    44: ({"PREVALENCE_MEASURED", "COHORT_UNAVAILABLE_TYPED"}, r"prevalence|cohort|denominator|numerator|tier"),
}
_V8_INVENTORY_COLUMNS = (
    "typed state", "exact member or typed zero", "section-specific role",
    "evidence receipt", "declared denominator", "evidence state",
    "limitation", "reconciliation state",
)
_V8_INVENTORY_PROFILES = {
    32: ({"ASSEMBLY_INVENTORY_MEASURED", "NO_ASSEMBLY_COMPONENTS_OBSERVED_TYPED"},
         r"core|carrier|tailoring|transport|regulat|accessory|component"),
    33: ({"MODULE_PROGRAM_MEASURED", "NO_MODULES_ASSIGNABLE_TYPED"},
         r"module|domain|substrate|extension|program"),
    34: ({"INITIATION_RELEASE_MEASURED", "NO_INITIATION_RELEASE_ASSIGNABLE_TYPED"},
         r"initiat|starter|load|release|terminat"),
    35: ({"PROTOCLUSTER_DECOMPOSITION_MEASURED", "NO_PROTOCLUSTERS_ASSIGNABLE_TYPED"},
         r"protocluster|component|boundary|interval|member"),
    37: ({"PARTNER_INVENTORY_MEASURED", "NO_PARTNERS_OBSERVED_TYPED"},
         r"partner|accessory|carrier|chaperone|transport|regulat|enzyme"),
    38: ({"RESISTANCE_EFFLUX_INVENTORY_MEASURED", "NO_RESISTANCE_EFFLUX_OBSERVED_TYPED"},
         r"resistance|efflux|transport|immunity|candidate"),
}
_V9_SELECTION_COLUMNS = (
    "selection state", "selected exact identity",
    "comparator exact identity or terminal state", "candidate-set denominator",
    "candidate-set receipt", "selected observed metrics",
    "comparator metrics or terminal basis", "predeclared selection rule",
    "rule evaluation", "bounded information-gain reason",
    "discriminating next action",
)
_V9_SELECTION_STATES = {
    "COMPARATIVE_SELECTION_MEASURED", "SINGLE_CANDIDATE_SET_TYPED",
}
_V10_FIGURE_COLUMNS = (
    "figure state", "exact plotted identity", "plotted interval",
    "locus-map v8 receipt", "rendered formats", "evidence-state encoding",
    "uncertainty labels", "provenance footer", "lossless sidecar",
    "visual-review receipt", "visual-review state",
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$", re.I)
_GENERIC_SEMANTIC_CELL = {
    "present", "reported", "available", "evidence", "supported", "yes", "no",
    "same", "different", "unknown", "pending", "n/a", "not applicable",
}
_S6_TYPED_TERMINAL_RE = re.compile(
    r"TAILORING_NOT_ASSIGNABLE_TYPED\s*;\s*denominator\s*=\s*([^;\n]+)\s*;\s*"
    r"sources\s*=\s*([^;\n]+)\s*;\s*reason\s*=\s*([^;\n]+)\s*;\s*"
    r"resolving_test\s*=\s*([^;\n]+)", re.I,
)
_S29_TYPED_TERMINAL_RE = re.compile(
    r"CROSS_CLUSTER_INTERACTION_NOT_EVALUABLE_TYPED\s*;\s*"
    r"denominator\s*=\s*([^;\n]+)\s*;\s*sources\s*=\s*([^;\n]+)\s*;\s*"
    r"reason\s*=\s*([^;\n]+)\s*;\s*resolving_test\s*=\s*([^;\n]+)",
    re.I,
)
_S15_STATES = {
    "NOT_RUN", "UNBOUND", "MISSING_ARTIFACT", "QC_HOLD", "MEASURED_ZERO",
    "UNAVAILABLE",
}
_S19_DISPOSITIONS = {
    "RETAIN_CANDIDATE", "HOLD_EVIDENCE", "INVENTORY_ONLY", "DEPRIORITIZE",
}
_S29_PHYSICAL_STATES = {
    "NO_PHYSICAL_LINK", "PHYSICAL_LINK_OBSERVED", "UNRESOLVED",
}
_TYPED_SECTION_UNAVAILABLE = {
    26: re.compile(
        r"OSMAC_NOT_APPLICABLE_TYPED\s*;\s*reason\s*=\s*([^;\n]+)\s*;\s*"
        r"sources\s*=\s*([^;\n]+)", re.I),
    46: re.compile(
        r"TYPE_REFERENCE_COMPARISON_NOT_AVAILABLE_TYPED\s*;\s*denominator\s*=\s*([^;\n]+)\s*;\s*"
        r"sources\s*=\s*([^;\n]+)\s*;\s*reason\s*=\s*([^;\n]+)", re.I),
    47: re.compile(
        r"HOST_MATCHED_COMPARISON_NOT_AVAILABLE_TYPED\s*;\s*denominator\s*=\s*([^;\n]+)\s*;\s*"
        r"sources\s*=\s*([^;\n]+)\s*;\s*reason\s*=\s*([^;\n]+)", re.I),
}


def _finding(code: str, section: Optional[int], message: str, *, found: str = "") -> dict:
    return {
        "severity": "ERROR", "code": code, "section": section,
        "expected": "expanded publication-candidate contract",
        "found": found or None, "message": message,
    }


# ── v9.7.412 (SURFACE-412): surface-integrity checks for authored §1–§50 cards ──
# The .411 §1–§50 publication contract is a doc-only pilot, so authored cards are hand/tool
# written and no runtime check reads their SURFACE. FOUR defect classes were measured across the
# nine tool-major cards in the .411 batch -- 4 tagged _CANDIDATE_ and 5 tagged _PROVISIONAL_SEAL_,
# not nine provisional-seal (provenance corrected by Codex, 2026-09-07). None of the four is
# currently detectable by any gate.
#
# These are SURFACE lint checks. They are not completeness or scientific validation, and a clean
# result here says nothing about whether a card's evidence or judgement is sound.

_GOVERNED_TERM_TYPOS = {"RG-GCMI": "RG-GMCI"}

# Tokens that legitimately end in a digit. Anything here is NOT a missing-space defect.
_WORDNUM_IDENTIFIERS = frozenset({
    "BGC", "PKS", "NRPS", "RiPP", "ctg", "NODE", "WP", "MBS", "PMC", "XWD", "MFC", "SMCOG",
    "NPDC", "TIGR", "PF", "COG", "KSC", "FLBR", "ADH", "Rml", "SDR", "CAL", "MIBiG", "EFLS",
    "UMED", "TTA", "SHA", "ANI", "AAI", "GfsA", "GfsB", "GfsC", "GfsD", "GfsE", "Pfam", "cov",
    "region", "run", "Run", "SID", "AS", "KS", "AT", "KR", "DH", "ER", "ACP", "TE", "TD", "PP",
    "CDS", "HSP", "nr", "v", "V", "Vol", "Fig", "Table", "PubMed", "doi", "DOI", "ISBN",
})

def _prose_only(card_md: str) -> str:
    """Drop fenced code, inline code, link destinations and bare paths.

    Accession numbers, SHA-256 digests and URLs legitimately glue letters to digits, so they
    must be removed before a missing-space rule can be applied without false positives.
    """
    text = re.sub(r"```.*?```", " ", card_md, flags=re.S)
    text = re.sub(r"`[^`\n]*`", " ", text)
    text = re.sub(r"\]\([^)]*\)", "] ", text)
    text = re.sub(r"<[^>\s]+>", " ", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"/[A-Za-z0-9_./ -]{8,}", " ", text)
    return text

def _word_number_spacing_findings(card_md: str) -> list[dict]:
    """A prose word glued to a following number ('engine1.9.149', 'supplied50-section')."""
    hits: list[str] = []
    for match in re.finditer(r"\b([A-Za-z]{3,})(?=\d)", _prose_only(card_md)):
        word = match.group(1)
        if word in _WORDNUM_IDENTIFIERS or word.isupper():
            continue
        hits.append(match.group(0) + "…")
    if not hits:
        return []
    uniq = sorted(set(hits))
    return [_finding(
        "CARD_WORD_NUMBER_SPACING", None,
        f"{len(hits)} place(s) glue a prose word to a following number; a reader cannot tell a "
        "value from a token. Identifiers, code spans, links and paths are excluded.",
        found=", ".join(uniq[:8]) + (f" (+{len(uniq) - 8} more)" if len(uniq) > 8 else ""))]

def _governed_term_findings(card_md: str) -> list[dict]:
    """A governed term spelled wrongly is not a typo; it breaks corpus-wide search."""
    out: list[dict] = []
    for wrong, right in _GOVERNED_TERM_TYPOS.items():
        n = len(re.findall(re.escape(wrong), card_md))
        if n:
            out.append(_finding(
                "CARD_GOVERNED_TERM_MISSPELLED", None,
                f"{n} use(s) of {wrong!r}; the governed term is {right!r}.", found=wrong))
    return out

def _surface_table_cells(line: str) -> list[str]:
    """Split unescaped pipes; keep the historical evidence parser unchanged."""
    text = line.strip()
    cells = []
    start = 0
    backslashes = 0
    for i, char in enumerate(text):
        if char == "|" and backslashes % 2 == 0:
            cells.append(text[start:i].strip())
            start = i + 1
        backslashes = backslashes + 1 if char == "\\" else 0
    cells.append(text[start:].strip())
    if text.startswith("|"):
        cells.pop(0)
    if cells and start == len(text) and text.endswith("|"):
        cells.pop()
    return cells


def _table_separator_findings(card_md: str) -> list[dict]:
    """Check top-level pipe-table widths, excluding fenced code examples.

    This is bounded surface lint, not a complete Markdown parser or a scientific
    gate. Nested blockquote/list tables and indented code are outside this scope.
    Body width findings catch silent renderer padding/truncation.
    """
    lines = []
    fence_char = None
    fence_length = 0
    for line in card_md.splitlines():
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if fence_char is not None:
            if (marker and marker[1][0] == fence_char
                    and len(marker[1]) >= fence_length and not marker[2].strip()):
                fence_char = None
            lines.append("")
        elif marker:
            fence_char, fence_length = marker[1][0], len(marker[1])
            lines.append("")
        else:
            lines.append(line if not line.startswith(("    ", "\t")) else "")
    bad_separator = []
    bad_body = []
    for i in range(1, len(lines)):
        line = lines[i]
        header = lines[i - 1]
        if "|" not in line or "|" not in header:
            continue
        separator = _surface_table_cells(line)
        if not separator or not all(re.fullmatch(r":?-{3,}:?", c) for c in separator):
            continue
        width = len(_surface_table_cells(header))
        if width != len(separator):
            bad_separator.append(
                f"line {i + 1}: header {width} cells vs separator {len(separator)}")
            continue
        for j in range(i + 1, len(lines)):
            if not lines[j].strip() or "|" not in lines[j]:
                break
            count = len(_surface_table_cells(lines[j]))
            if count != width:
                bad_body.append(f"line {j + 1}: header {width} cells vs body {count}")
    findings = []
    if bad_separator:
        findings.append(_finding(
            "CARD_TABLE_SEPARATOR_MISMATCH", None,
            f"{len(bad_separator)} table separator(s) disagree with header width.",
            found="; ".join(bad_separator[:4])))
    if bad_body:
        findings.append(_finding(
            "CARD_TABLE_BODY_MISMATCH", None,
            f"{len(bad_body)} body row(s) disagree with header width; rendering may "
            "silently pad or truncate cells.",
            found="; ".join(bad_body[:4])))
    return findings

def _section_disposition_uniform_findings(card_md: str) -> list[dict]:
    """Advisory repetition tripwire, not proof that a judgment is wrong.

    Legitimate assessments may share states and scope. Neither variation nor
    uniformity establishes scientific completeness; inspect the underlying evidence.
    """
    rows = re.findall(
        r"^\|\s*(\d{1,3})\s*\|\s*([A-Z_]+)\s*\|([^|]*)\|([^|]*)\|([^|]*)\|\s*$",
        card_md, re.M)
    if len(rows) < 20:
        return []
    states = {r[1] for r in rows}
    bases = {r[2].strip() for r in rows}
    scopes = {r[4].strip() for r in rows}
    if len(states) == 1 and len(scopes) == 1:
        finding = _finding(
            "SECTION_DISPOSITION_TABLE_UNIFORM", 28,
            f"All {len(rows)} sampled rows share state {sorted(states)[0]} and scope. "
            "Review their evidence bases for unsupported reuse. Uniformity alone does not "
            "establish an error; varying states does not establish completeness. Do not "
            "change a justified state merely to silence this advisory.",
            found=f"{len(rows)} rows, {len(bases)} distinct evidence bases")
        finding["severity"] = "WARN"
        finding["expected"] = "evidence-backed section assessments; no required state diversity"
        return [finding]
    return []


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _separator(line: str) -> bool:
    cells = _cells(line)
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", c or "") for c in cells)


def _table_rows(text: str) -> list[list[str]]:
    return [_cells(line) for line in text.splitlines()
            if line.strip().startswith("|") and not _separator(line)]


def _normal_header(cell: str) -> str:
    return re.sub(r"\s+", " ", cell.strip().casefold())


def _named_contract_table(text: str, title: str) -> tuple[list[str], list[list[str]]]:
    """Return one named contract table as ``(header, rows)``.

    A contract table is deliberately scoped to its heading. A table elsewhere
    in the section cannot rescue a missing reader-orientation table.
    """
    rows = _table_rows(_named_heading_block(text, title))
    if not rows:
        return [], []
    return rows[0], rows[1:]


def _named_heading_block(text: str, title: str) -> str:
    """Return one named Markdown heading's body, bounded by the next peer/parent heading.

    Scoping the contract tables prevents a detailed narrative table elsewhere in the card from
    being miscounted as a duplicate standardized disposition row.
    """
    pattern = re.compile(
        rf"^(?P<marks>#{{2,6}})\s+(?:Publication-contract\s+)?{re.escape(title)}\s*$",
        re.I | re.M,
    )
    match = pattern.search(text)
    if not match:
        return ""
    level = len(match.group("marks"))
    next_heading = re.search(rf"^#{{2,{level}}}\s+", text[match.end():], re.M)
    end = match.end() + next_heading.start() if next_heading else len(text)
    return text[match.end():end]


def _contiguous_homology_table_findings(section4: str,
                                         canonical_loci: Optional[Iterable[str]]) -> list[dict]:
    """Require one renderable named-match table; later rows cannot rescue a break.

    v9.7.373 (BREAK-3): scope the scan to the shared §4 matrix block (canonical named-match heading
    or the accepted legacy heading), so both this gate and the structure-gate matrix check locate the
    table the same way and an unrelated §4 pipe table can never be mistaken for the matrix."""
    block = find_s4_matrix_block(section4)
    if block is None:
        return [_finding("PUBLICATION_GENE_TABLE_MISSING", 4,
                         "Section 4 must contain one contiguous named-match gene table under the "
                         "'Complete named-match, channel-separated table' heading (the legacy "
                         "'Complete channel-separated BLASTp matrix' heading is also accepted).")]
    lines = block.splitlines()
    tables: list[tuple[list[str], list[list[str]]]] = []
    broken = False
    for i in range(len(lines) - 1):
        if "|" not in lines[i] or not _separator(lines[i + 1]):
            continue
        header = _cells(lines[i])
        if not any(_HOMOLOGY_HEADER.search(cell) for cell in header):
            continue
        rows: list[list[str]] = []
        j = i + 2
        if j >= len(lines) or not lines[j].strip().startswith("|"):
            if any(
                ln.strip().startswith("|")
                and (lambda cells: bool(cells and matrix_gene_tag(cells[0])))(_cells(ln))
                for ln in lines[j:]
            ):
                broken = True
            continue
        while j < len(lines) and lines[j].strip().startswith("|"):
            if _separator(lines[j]):
                break
            rows.append(_cells(lines[j]))
            j += 1
        tables.append((header, rows))

    if broken:
        return [_finding(
            "BROKEN_MARKDOWN_TABLE", 4,
            "A recognized homology-table separator is not followed immediately by its first data "
            "row. Blank lines or prose breaks make later pipe rows a separate Markdown block.",
        )]
    if not tables:
        return [_finding("PUBLICATION_GENE_TABLE_MISSING", 4,
                         "Section 4 must contain one contiguous named-match gene table.")]
    if len(tables) != 1:
        return [_finding("PUBLICATION_GENE_TABLE_MULTIPLE", 4,
                         f"Expected one authoritative named-match table; found {len(tables)}.")]

    header, rows = tables[0]
    findings: list[dict] = []
    if not rows:
        return [_finding("PUBLICATION_GENE_TABLE_EMPTY", 4,
                         "The named-match table has no data rows.")]
    widths = {len(header), *(len(row) for row in rows)}
    if len(widths) != 1:
        findings.append(_finding("PUBLICATION_GENE_TABLE_WIDTH", 4,
                                 f"Header/data column counts differ: {sorted(widths)}."))
    # v9.7.384 (AUDIT-384-01): resolve the gene column by header name, exactly as the
    # sibling check in modeb_structure_gate does, instead of hardcoding column 0.
    # v9.7.383 replaced a whole-row `_LOCUS.search()` with `matrix_gene_tag(row[0])`. That
    # broadened which tag SHAPES are admitted (its stated intent) but silently narrowed WHERE the
    # tag may sit. Any matrix whose first column is not the gene -- for example one leading with
    # the mandated `strain / full node-or-contig / region / BGC alias` identity columns -- then
    # yields the same column-0 value on every row and fails PUBLICATION_GENE_TABLE_DUPLICATE.
    # Falls back to column 0 when no gene/locus header is present, preserving legacy behaviour.
    #
    # v9.7.385 (AUDIT-384-02): a header can contain MORE THAN ONE column whose name
    # merely CONTAINS "gene"/"locus" as a substring -- e.g. a descriptive "Gene context" or
    # "Gene role" categorical column (values like "core biosynthetic gene", "resistance gene")
    # placed ahead of the true identity column ("Locus"). The .384 fix picked the FIRST
    # substring match by column order, not the actual identity column, which reintroduces the
    # exact bug class .384 was written to close, just triggered by a different header shape:
    #   - false positive: many rows legitimately share the same descriptive category value
    #     ("core biosynthetic gene"), so distinct genes trip PUBLICATION_GENE_TABLE_DUPLICATE.
    #   - false negative (worse): a genuine duplicate locus tag is silently MASKED because the
    #     descriptive column's values differ row to row while the real locus column repeats.
    # Disambiguate among substring-matching candidates by cell SHAPE, not header wording: a real
    # gene/locus tag (ctgN_N, allorf_..., NCBI-style WP_/SCO-style tags, etc.) always carries at
    # least one digit once matrix_gene_tag() strips it to the leading identifier; free-text
    # category values normally don't. Prefer the first candidate whose column is digit-tagged in
    # every row; fall back to the first substring match (old .384 behaviour) if none qualify, and
    # to column 0 if there is no substring match at all (legacy tables unaffected either way).
    _lower = [h.lower() for h in header]
    _gene_candidates = [i for i, h in enumerate(_lower) if "gene" in h or "locus" in h]

    def _column_is_digit_tagged(i: int) -> bool:
        cells = [row[i] for row in rows if i < len(row)]
        if not cells:
            return False
        return all(
            (tag := matrix_gene_tag(cell)) and any(ch.isdigit() for ch in tag)
            for cell in cells
        )

    _idx_gene = next((i for i in _gene_candidates if _column_is_digit_tagged(i)), None)
    if _idx_gene is None:
        _idx_gene = _gene_candidates[0] if _gene_candidates else 0
    loci = [tag for row in rows if row
            for tag in [matrix_gene_tag(row[_idx_gene] if _idx_gene < len(row) else row[0])] if tag]
    duplicate = sorted(tag for tag, count in Counter(loci).items() if count > 1)
    if duplicate:
        findings.append(_finding("PUBLICATION_GENE_TABLE_DUPLICATE", 4,
                                 "Each displayed gene must occur exactly once.",
                                 found=", ".join(duplicate)))
    if canonical_loci is not None:
        expected = {str(x).strip() for x in canonical_loci if str(x).strip()}
        observed = set(loci)
        if observed != expected:
            findings.append(_finding(
                "PUBLICATION_GENE_TABLE_ROSTER", 4,
                "The table roster differs from the independently supplied displayed-gene roster.",
                found=f"missing={sorted(expected-observed)} extra={sorted(observed-expected)}",
            ))
    return findings


_SECTION_ANCHORS = {
    5: (
        "Committed-step genes", "Reaction-level sequence", "Minimal-gene-set audit",
        "Strongest alternative", "Evidence for the alternative",
        "Evidence against the alternative", "Claim ceiling",
    ),
    6: (
        "Direct tailoring candidates", "Broad metabolic context",
        "Conditional pathway order", "Non-diagnostic enzyme families",
        "Comparator conflicts", "Coupling evidence", "Discriminating tests",
    ),
    7: (
        "Transport adjudication", "Resistance adjudication", "Regulation adjudication",
        "No exact-bound evidence versus biological absence",
    ),
}


def _scientific_scaffold_findings(bodies: dict[int, str]) -> list[dict]:
    findings: list[dict] = []
    for section, anchors in _SECTION_ANCHORS.items():
        body = bodies.get(section, "")
        missing = [anchor for anchor in anchors if anchor.lower() not in body.lower()]
        if missing:
            findings.append(_finding(
                f"SECTION_{section}_SCIENTIFIC_SCAFFOLD", section,
                "Missing required evidence/reasoning anchors: " + "; ".join(missing),
            ))
    return findings


def _typed_zero_state(body: str, canonical_loci: Optional[Iterable[str]]) -> tuple[bool, str]:
    """Validate the only accepted no-candidate substitute for exact gene IDs."""
    match = _TYPED_ZERO_RE.search(body or "")
    if not match:
        return False, "missing ZERO_EXACT_BOUND_CANDIDATES state with denominator and sources"
    denominator = int(match.group(1))
    sources = match.group(2).strip()
    if not sources or sources.casefold() in {"none", "unknown", "pending", "n/a"}:
        return False, "typed zero-candidate state has no usable source list"
    if canonical_loci is not None:
        expected = len({str(item).strip() for item in canonical_loci if str(item).strip()})
        if denominator != expected:
            return False, f"typed zero-candidate denominator={denominator}, expected={expected}"
    return True, ""


def _gene_orientation_findings(bodies: dict[int, str],
                               canonical_loci: Optional[Iterable[str]]) -> list[dict]:
    """Require reader orientation where a section makes gene-level claims.

    This is an evidence-density contract, not a word-count floor. A concise
    section passes when it names exact genes. If the searched evidence contains
    zero exact-bound candidates, the section passes only with a typed state that
    records the displayed-protein denominator and searched sources.
    """
    findings: list[dict] = []
    for section in sorted(_GENE_CLAIM_SECTIONS):
        body = bodies.get(section, "")
        if not body or not _GENE_CLAIM_LANGUAGE.search(body):
            continue
        genes = set(_LOCUS.findall(body))
        typed_ok, typed_reason = _typed_zero_state(body, canonical_loci)
        if not genes and not typed_ok:
            findings.append(_finding(
                "SECTION_GENE_ORIENTATION_MISSING", section,
                "A section that discusses genes, proteins, domains, transporters, resistance, "
                "regulators or enzymes must name exact gene IDs on first use or record "
                "ZERO_EXACT_BOUND_CANDIDATES with the displayed-protein denominator and sources.",
                found=typed_reason,
            ))
    return findings


def _section27_findings(body: str,
                        canonical_loci: Optional[Iterable[str]]) -> list[dict]:
    """Validate the self-resistance reader-orientation contract.

    Positive candidates require a per-gene table. A typed zero-candidate state
    is accepted only when its denominator and source list validate. Long prose,
    family names and a generic 'not assigned' sentence cannot satisfy the gate.
    """
    findings: list[dict] = []
    genes = set(_LOCUS.findall(body or ""))
    typed_ok, typed_reason = _typed_zero_state(body, canonical_loci)
    if not genes:
        if not typed_ok:
            findings.append(_finding(
                "SECTION_27_GENE_ORIENTATION_MISSING", 27,
                "Section 27 must name exact resistance/self-protection candidate genes or use "
                "the validated ZERO_EXACT_BOUND_CANDIDATES state.",
                found=typed_reason,
            ))
        if not re.search(r"(?im)^#### Claim ceiling\s*$", body or ""):
            findings.append(_finding(
                "SECTION_27_CLAIM_CEILING_MISSING", 27,
                "Section 27 requires a 'Claim ceiling' subsection even when no candidate is found.",
            ))
        return findings

    header, rows = _named_contract_table(body, "Candidate gene orientation")
    if not header:
        findings.append(_finding(
            "SECTION_27_GENE_TABLE_MISSING", 27,
            "Positive Section 27 candidates require one table under 'Candidate gene orientation' "
            "with exact genes, physical membership, candidate role, evidence source, class "
            "concordance and allowed inference.",
        ))
    else:
        normalized = tuple(_normal_header(cell) for cell in header)
        if normalized != _S27_COLUMNS:
            findings.append(_finding(
                "SECTION_27_GENE_TABLE_COLUMNS", 27,
                "The Section 27 table columns must be exactly: " + "; ".join(_S27_COLUMNS),
                found="; ".join(normalized),
            ))
        elif not rows:
            findings.append(_finding(
                "SECTION_27_GENE_TABLE_EMPTY", 27,
                "The Section 27 candidate table has no data rows.",
            ))
        else:
            table_genes: set[str] = set()
            for index, row in enumerate(rows, 1):
                if len(row) != len(header):
                    findings.append(_finding(
                        "SECTION_27_GENE_TABLE_WIDTH", 27,
                        f"Candidate row {index} has {len(row)} cells; expected {len(header)}.",
                    ))
                    continue
                gene_match = _LOCUS.search(row[0])
                if not gene_match:
                    findings.append(_finding(
                        "SECTION_27_GENE_ROW_UNBOUND", 27,
                        f"Candidate row {index} does not begin with an exact gene ID.",
                    ))
                    continue
                gene = gene_match.group(0)
                table_genes.add(gene)
                if row[1].strip().upper() not in _S27_MEMBERSHIP_STATES:
                    findings.append(_finding(
                        "SECTION_27_MEMBERSHIP_STATE", 27,
                        f"{gene} needs one of {sorted(_S27_MEMBERSHIP_STATES)}.", found=row[1],
                    ))
                if not row[2].strip() or not row[3].strip():
                    findings.append(_finding(
                        "SECTION_27_ROLE_OR_SOURCE_MISSING", 27,
                        f"{gene} needs a candidate role and evidence source.",
                    ))
                if row[4].strip().upper() not in _S27_CONCORDANCE_STATES:
                    findings.append(_finding(
                        "SECTION_27_CONCORDANCE_STATE", 27,
                        f"{gene} needs one of {sorted(_S27_CONCORDANCE_STATES)}.", found=row[4],
                    ))
                if not row[5].strip():
                    findings.append(_finding(
                        "SECTION_27_ALLOWED_INFERENCE_MISSING", 27,
                        f"{gene} needs an allowed-inference statement.",
                    ))
            if genes - table_genes:
                findings.append(_finding(
                    "SECTION_27_GENE_TABLE_INCOMPLETE", 27,
                    "Every exact gene mentioned in Section 27 must occur in its orientation table.",
                    found=", ".join(sorted(genes - table_genes)),
                ))
            if canonical_loci is not None:
                expected = {str(item).strip() for item in canonical_loci if str(item).strip()}
                foreign = table_genes - expected
                if foreign:
                    findings.append(_finding(
                        "SECTION_27_GENE_OUTSIDE_DISPLAYED_ROSTER", 27,
                        "Candidate genes must belong to the independently supplied displayed roster; "
                        "outside genes require an explicitly quarantined boundary record.",
                        found=", ".join(sorted(foreign)),
                    ))
    if not re.search(r"(?im)^#### Claim ceiling\s*$", body or ""):
        findings.append(_finding(
            "SECTION_27_CLAIM_CEILING_MISSING", 27,
            "Section 27 requires a 'Claim ceiling' subsection after the per-gene decision table.",
        ))
    return findings


def _section45_findings(body: str,
                        canonical_loci: Optional[Iterable[str]]) -> list[dict]:
    """Require a real cohort comparison, not predecessor bookkeeping."""
    findings: list[dict] = []
    typed = _TYPED_COHORT_NONE_RE.search(body or "")
    has_denominator_heading = bool(re.search(
        r"(?im)^#### (?:Cohort comparison denominator|Cohort denominator)\s*$", body or ""))
    has_conclusion = bool(re.search(
        r"(?im)^#### Cohort-comparison conclusion\s*$", body or ""))
    if typed:
        denominator, sources, reason = (item.strip() for item in typed.groups())
        if not has_denominator_heading or not has_conclusion or any(
            value.casefold() in {"", "none", "unknown", "pending", "n/a"}
            for value in (denominator, sources, reason)
        ):
            findings.append(_finding(
                "SECTION_45_TYPED_UNAVAILABLE_INCOMPLETE", 45,
                "A typed unavailable cohort comparison needs denominator and conclusion headings "
                "plus nonempty denominator, sources and reason fields.",
            ))
        return findings

    header, rows = _named_contract_table(body, "Cohort gene comparison")
    if not has_denominator_heading:
        findings.append(_finding(
            "SECTION_45_COHORT_DENOMINATOR_MISSING", 45,
            "Section 45 must identify the compared cohort and its strain/locus denominator.",
        ))
    if not header:
        findings.append(_finding(
            "SECTION_45_COMPARATOR_TABLE_MISSING", 45,
            "Section 45 needs a 'Cohort gene comparison' table; predecessor history alone is not "
            "a cohort comparison.",
        ))
    else:
        normalized = tuple(_normal_header(cell) for cell in header)
        if normalized != _S45_COLUMNS:
            findings.append(_finding(
                "SECTION_45_COMPARATOR_TABLE_COLUMNS", 45,
                "The Section 45 table columns must be exactly: " + "; ".join(_S45_COLUMNS),
                found="; ".join(normalized),
            ))
        elif not rows:
            findings.append(_finding(
                "SECTION_45_COMPARATOR_TABLE_EMPTY", 45,
                "The Section 45 comparator table has no data rows.",
            ))
        else:
            expected = ({str(item).strip() for item in canonical_loci if str(item).strip()}
                        if canonical_loci is not None else None)
            for index, row in enumerate(rows, 1):
                if len(row) != len(header):
                    findings.append(_finding(
                        "SECTION_45_COMPARATOR_TABLE_WIDTH", 45,
                        f"Comparator row {index} has {len(row)} cells; expected {len(header)}.",
                    ))
                    continue
                if not _COMPLETE_AS_LOCUS.fullmatch(row[0].strip()):
                    findings.append(_finding(
                        "SECTION_45_COMPARATOR_IDENTITY_INCOMPLETE", 45,
                        "Every comparator must display strain / full node-or-contig / region / BGC alias.",
                        found=row[0],
                    ))
                query_genes = set(_LOCUS.findall(row[1]))
                comparator_genes = set(_LOCUS.findall(row[2]))
                if not query_genes or not comparator_genes:
                    findings.append(_finding(
                        "SECTION_45_COMPARATOR_GENES_MISSING", 45,
                        f"Comparator row {index} must name exact query and comparator genes.",
                    ))
                if expected is not None and query_genes - expected:
                    findings.append(_finding(
                        "SECTION_45_QUERY_GENE_OUTSIDE_DISPLAYED_ROSTER", 45,
                        "Section 45 query genes must belong to the independently supplied displayed roster.",
                        found=", ".join(sorted(query_genes - expected)),
                    ))
                if not all(cell.strip() for cell in row[3:]):
                    findings.append(_finding(
                        "SECTION_45_COMPARATOR_INTERPRETATION_MISSING", 45,
                        f"Comparator row {index} needs sequence/synteny evidence, mismatch analysis "
                        "and an allowed inference.",
                    ))
    if not has_conclusion:
        findings.append(_finding(
            "SECTION_45_CONCLUSION_MISSING", 45,
            "Section 45 requires a 'Cohort-comparison conclusion' subsection.",
        ))
    return findings


def _typed_section_unavailable(body: str, section: int) -> tuple[bool, str]:
    """Validate the section-specific, source-bearing unavailable state.

    Finished cards may use a reasoned not-applicable path, but a bare ``N/A`` or
    generic hold is not evidence that the condition was actually considered.
    """
    match = _TYPED_SECTION_UNAVAILABLE[section].search(body or "")
    if not match:
        return False, "missing section-specific typed unavailable state"
    values = [value.strip() for value in match.groups()]
    unusable = {"", "none", "unknown", "pending", "n/a", "not available"}
    if any(value.casefold() in unusable for value in values):
        return False, "typed unavailable state has an empty or unresolved field"
    return True, ""


def _required_table_findings(body: str, *, section: int, heading: str,
                             columns: tuple[str, ...], minimum_rows: int) -> list[dict]:
    """Require a named, decision-bearing table with complete cells."""
    findings: list[dict] = []
    code_stem = re.sub(r"[^A-Z0-9]+", "_", heading.upper()).strip("_")
    header, rows = _named_contract_table(body, heading)
    if not header:
        return [_finding(
            f"SECTION_{section}_{code_stem}_MISSING",
            section,
            f"Section {section} needs a '{heading}' table; prose or keywords alone are insufficient.",
        )]
    normalized = tuple(_normal_header(cell) for cell in header)
    if normalized != columns:
        findings.append(_finding(
            f"SECTION_{section}_{code_stem}_COLUMNS",
            section,
            "The required columns are exactly: " + "; ".join(columns),
            found="; ".join(normalized),
        ))
        return findings
    if len(rows) < minimum_rows:
        findings.append(_finding(
            f"SECTION_{section}_{code_stem}_THIN",
            section,
            f"The '{heading}' table needs at least {minimum_rows} complete data row(s).",
        ))
    for index, row in enumerate(rows, 1):
        if len(row) != len(header) or not all(cell.strip() for cell in row):
            findings.append(_finding(
                f"SECTION_{section}_{code_stem}_ROW_INCOMPLETE",
                section,
                f"Row {index} of '{heading}' must fill every required cell.",
            ))
    return findings


def _alternatives_boundary_next_action_findings(bodies: dict[int, str]) -> list[dict]:
    """Prospective gates for alternatives, boundaries, and the resolving next action."""
    findings = _required_table_findings(
        bodies.get(9, ""), section=9, heading="Competing hypotheses",
        columns=_S9_COLUMNS, minimum_rows=2,
    )
    findings.extend(_required_table_findings(
        bodies.get(3, ""), section=3, heading="Boundary and completeness audit",
        columns=_S3_BOUNDARY_COLUMNS, minimum_rows=1,
    ))
    findings.extend(_required_table_findings(
        bodies.get(36, ""), section=36, heading="Overmerge / locus-splitting adjudication",
        columns=_S36_COLUMNS, minimum_rows=2,
    ))
    findings.extend(_required_table_findings(
        bodies.get(20, ""), section=20, heading="Highest-information next action",
        columns=_S20_COLUMNS, minimum_rows=1,
    ))
    return findings


def _section26_findings(body: str) -> list[dict]:
    """Require a decision-bearing OSMAC plan or a source-bound N/A state."""
    typed_ok, typed_reason = _typed_section_unavailable(body, 26)
    if typed_ok:
        return []
    findings: list[dict] = []
    rationale = bool(re.search(r"(?im)^#### Pathway-grounded rationale\s*$", body or ""))
    controls = bool(re.search(r"(?im)^#### Controls and claim ceiling\s*$", body or ""))
    header, rows = _named_contract_table(body, "Condition matrix")
    if not rationale:
        findings.append(_finding(
            "SECTION_26_PATHWAY_RATIONALE_MISSING", 26,
            "Section 26 needs a 'Pathway-grounded rationale' subsection tying condition choices "
            "to the locus model, or a validated OSMAC_NOT_APPLICABLE_TYPED state.",
            found=typed_reason,
        ))
    if not header:
        findings.append(_finding(
            "SECTION_26_CONDITION_MATRIX_MISSING", 26,
            "Section 26 needs a 'Condition matrix' with perturbations, pathway rationale, measured "
            "readouts and decision rules; generic OSMAC prose is insufficient.",
        ))
    else:
        normalized = tuple(_normal_header(cell) for cell in header)
        if normalized != _S26_COLUMNS:
            findings.append(_finding(
                "SECTION_26_CONDITION_MATRIX_COLUMNS", 26,
                "The Section 26 condition matrix columns must be exactly: " + "; ".join(_S26_COLUMNS),
                found="; ".join(normalized),
            ))
        elif len(rows) < 2:
            findings.append(_finding(
                "SECTION_26_CONDITION_MATRIX_THIN", 26,
                "The Section 26 condition matrix needs at least two independently interpretable conditions.",
            ))
        else:
            for index, row in enumerate(rows, 1):
                if len(row) != len(header) or not all(cell.strip() for cell in row):
                    findings.append(_finding(
                        "SECTION_26_CONDITION_ROW_INCOMPLETE", 26,
                        f"Condition row {index} must fill every required cell.",
                    ))
    if not controls:
        findings.append(_finding(
            "SECTION_26_CONTROLS_CEILING_MISSING", 26,
            "Section 26 requires a 'Controls and claim ceiling' subsection so an induced feature "
            "is not treated as locus attribution without genotype and batch controls.",
        ))
    return findings


def _section10_findings(body: str) -> list[dict]:
    """Require boundary/co-capture adjudication that can change a decision."""
    findings = _required_table_findings(
        body, section=10, heading="Boundary and co-capture adjudication",
        columns=_S10_COLUMNS, minimum_rows=1,
    )
    header, rows = _named_contract_table(body, "Boundary and co-capture adjudication")
    if tuple(_normal_header(cell) for cell in header) != _S10_COLUMNS:
        return findings
    for index, row in enumerate(rows, 1):
        if len(row) != len(header):
            continue
        if not re.search(r"\b(?:interior|edge|full[- ]contig|truncat|unbound|closed)\b", row[0], re.I):
            findings.append(_finding(
                "SECTION_10_OBSERVED_GEOMETRY_UNTYPED", 10,
                f"Boundary row {index} must state an observed geometry such as INTERIOR, EDGE, FULL_CONTIG, TRUNCATED, CLOSED or UNBOUND.",
                found=row[0],
            ))
        if not re.search(r"\b(?:overmerge|co[- ]capture|split|extension|truncat|adjacent|omission|single locus|multiple loci)\b", row[1], re.I):
            findings.append(_finding(
                "SECTION_10_COMPETING_MODEL_UNTYPED", 10,
                f"Boundary row {index} must name a competing boundary/co-capture model.", found=row[1],
            ))
        if _normal_header(row[2]) == _normal_header(row[3]):
            findings.append(_finding(
                "SECTION_10_EVIDENCE_SIDES_COLLAPSED", 10,
                f"Boundary row {index} must distinguish evidence for from evidence against.",
            ))
        if not re.search(r"\b(?:long[- ]read|read[- ]pair|pcr|closure|transcript|operon|metabolom|knockout|deletion)\b", row[5], re.I):
            findings.append(_finding(
                "SECTION_10_CLOSURE_TEST_UNSPECIFIC", 10,
                f"Boundary row {index} must name a discriminating physical or functional closure test.", found=row[5],
            ))
    return findings


def _section12_findings(body: str) -> list[dict]:
    """Require at least two ecological models, including evidence against and a matched test."""
    findings = _required_table_findings(
        body, section=12, heading="Ecological hypothesis matrix",
        columns=_S12_COLUMNS, minimum_rows=2,
    )
    header, rows = _named_contract_table(body, "Ecological hypothesis matrix")
    if tuple(_normal_header(cell) for cell in header) != _S12_COLUMNS:
        return findings
    hypotheses = {_normal_header(row[0]) for row in rows if len(row) == len(header)}
    if len(rows) >= 2 and len(hypotheses) < 2:
        findings.append(_finding(
            "SECTION_12_HYPOTHESES_NOT_DISTINCT", 12,
            "The ecological matrix needs at least two distinct hypotheses, not duplicated labels.",
        ))
    # v9.7.410 hostile audit (semantic-gate hollow-card probe): "two distinct hypotheses" was
    # satisfied by CLONING a row and swapping the hypothesis / competing-explanation labels — same
    # locus evidence, same evidence against, same ceiling, same "discriminating" test. Two models
    # that share every evidence cell are one model with two names; the matrix has to argue them
    # apart. Rows are clones when everything except columns 1 and 4 (the two labels) is identical.
    bodies = [tuple(_normal_header(cell) for k, cell in enumerate(row) if k not in (0, 3))
              for row in rows if len(row) == len(header)]
    if len(bodies) >= 2 and len(set(bodies)) < len(bodies):
        findings.append(_finding(
            "SECTION_12_HYPOTHESIS_ROWS_CLONED", 12,
            "Two ecological hypotheses share identical evidence, evidence-against, ceiling and "
            "matched-test cells — a cloned row with the labels swapped is not a second model.",
        ))
    for index, row in enumerate(rows, 1):
        if len(row) != len(header):
            continue
        if not (_LOCUS.search(row[1]) or re.search(r"\b(?:receipt|manifest|measured|exact[- ]region)\b", row[1], re.I)):
            findings.append(_finding(
                "SECTION_12_LOCUS_EVIDENCE_UNBOUND", 12,
                f"Ecology row {index} must name an exact locus gene or a bound measurement/receipt.", found=row[1],
            ))
        if _normal_header(row[0]) == _normal_header(row[3]):
            findings.append(_finding(
                "SECTION_12_COMPETING_EXPLANATION_COLLAPSED", 12,
                f"Ecology row {index} must distinguish its competing explanation from its focal hypothesis.",
            ))
        if not re.search(r"\b(?:not|only|unknown|hypothesis|cannot|unresolved|context)\b", row[4], re.I):
            findings.append(_finding(
                "SECTION_12_CAUSALITY_CEILING_MISSING", 12,
                f"Ecology row {index} needs an explicit causality ceiling.", found=row[4],
            ))
        test = row[5]
        if not (re.search(r"\b(?:knockout|deletion|mutant|perturb|complement)\w*\b", test, re.I)
                and re.search(r"\b(?:matched|control|wild type|complement)\w*\b", test, re.I)):
            findings.append(_finding(
                "SECTION_12_MATCHED_TEST_UNSPECIFIC", 12,
                f"Ecology row {index} needs a genotype-dependent test with a matched control or complement.", found=test,
            ))
    return findings


def _section17_findings(body: str,
                        canonical_loci: Optional[Iterable[str]]) -> list[dict]:
    """Require an exact-target analytical decision row rather than generic LC-MS prose."""
    findings = _required_table_findings(
        body, section=17, heading="LC-MS / fermentation decision matrix",
        columns=_S17_COLUMNS, minimum_rows=1,
    )
    header, rows = _named_contract_table(body, "LC-MS / fermentation decision matrix")
    if tuple(_normal_header(cell) for cell in header) != _S17_COLUMNS:
        return findings
    expected = ({str(item).strip() for item in canonical_loci if str(item).strip()}
                if canonical_loci is not None else None)
    for index, row in enumerate(rows, 1):
        if len(row) != len(header):
            continue
        targets = set(_LOCUS.findall(row[0]))
        if not targets:
            findings.append(_finding(
                "SECTION_17_EXACT_TARGET_MISSING", 17,
                f"Decision row {index} must name at least one exact in-roster target gene.",
            ))
        elif expected is not None and targets - expected:
            findings.append(_finding(
                "SECTION_17_TARGET_OUTSIDE_DISPLAYED_ROSTER", 17,
                "Section 17 perturbation targets must belong to the independently supplied displayed roster.",
                found=", ".join(sorted(targets - expected)),
            ))
        perturbation_genes = set(_LOCUS.findall(row[2]))
        if targets and not (targets & perturbation_genes):
            findings.append(_finding(
                "SECTION_17_PERTURBATION_TARGET_MISMATCH", 17,
                f"Decision row {index} must bind its perturbation to the exact target gene.", found=row[2],
            ))
        control_kinds = sum(bool(re.search(pattern, row[3], re.I)) for pattern in (
            r"\bwild type\b", r"\bcomplement\w*\b", r"\bbatch blank\w*\b", r"\bvehicle\b",
        ))
        if control_kinds < 2:
            findings.append(_finding(
                "SECTION_17_CONTROLS_INSUFFICIENT", 17,
                f"Decision row {index} must name at least two control classes, including genotype and analytical/batch controls where applicable.", found=row[3],
            ))
        if not re.search(r"\b(?:LC[-– ]?MS|MS2|feature|metabolom|retention time|isotope|titre|titer)\b", row[4], re.I):
            findings.append(_finding(
                "SECTION_17_READOUT_UNMEASURED", 17,
                f"Decision row {index} must name a measured analytical readout.", found=row[4],
            ))
        if not re.search(r"\b(?:if|only|advance|reject|support|require)\w*\b", row[5], re.I):
            findings.append(_finding(
                "SECTION_17_DECISION_RULE_MISSING", 17,
                f"Decision row {index} must state how the readout changes the decision.", found=row[5],
            ))
        if not re.search(r"\b(?:not|only|unknown|cannot|unresolved|feature)\b", row[6], re.I):
            findings.append(_finding(
                "SECTION_17_CLAIM_CEILING_MISSING", 17,
                f"Decision row {index} must limit what a positive result establishes.", found=row[6],
            ))
    return findings


def _section24_findings(body: str) -> list[dict]:
    """Require receipt-bound reference-space measurements and bounded novelty inference."""
    findings = _required_table_findings(
        body, section=24, heading="Novelty evidence ledger",
        columns=_S24_COLUMNS, minimum_rows=1,
    )
    header, rows = _named_contract_table(body, "Novelty evidence ledger")
    if tuple(_normal_header(cell) for cell in header) != _S24_COLUMNS:
        return findings
    for index, row in enumerate(rows, 1):
        if len(row) != len(header):
            continue
        if not _SHA256_RE.fullmatch(row[1].strip()):
            findings.append(_finding(
                "SECTION_24_SOURCE_RECEIPT_INVALID", 24,
                f"Novelty row {index} must bind its reference-space result to a 64-hex SHA-256 receipt.",
                found=row[1],
            ))
        if not re.search(r"\d", row[2]):
            findings.append(_finding(
                "SECTION_24_DENOMINATOR_UNMEASURED", 24,
                f"Novelty row {index} must state a numeric searched/reference denominator.",
                found=row[2],
            ))
        if not re.search(r"\b(?:not|only|candidate|unknown|cannot|unresolved|distinctiveness|class[- ]level)\b", row[5], re.I):
            findings.append(_finding(
                "SECTION_24_ALLOWED_INFERENCE_UNBOUNDED", 24,
                f"Novelty row {index} must state a bounded allowed inference.", found=row[5],
            ))
        if not re.search(r"\b(?:isolate|structure|NMR|LC[-– ]?MS|compare|sequence|phylogen|test|close)\w*\b", row[6], re.I):
            findings.append(_finding(
                "SECTION_24_NEXT_ACTION_UNSPECIFIC", 24,
                f"Novelty row {index} must name one resolving analysis or experiment.", found=row[6],
            ))
    return findings


def _semantic_cell(value: str, *, minimum_words: int = 3) -> bool:
    """Reject nonempty-but-vacuous cells without rewarding raw length."""
    normalized = " ".join((value or "").strip().casefold().split())
    return bool(
        normalized
        and normalized not in _GENERIC_SEMANTIC_CELL
        and len(re.findall(r"[A-Za-z0-9_%-]+", normalized)) >= minimum_words
    )


def _measured_comparison_cell(value: str) -> bool:
    text = value or ""
    return _semantic_cell(text, minimum_words=4) and bool(
        re.search(r"\d", text)
        and re.search(
            r"\b(?:identity|coverage|align(?:ed|ment)?|residue|aa|bp|gene|protein|domain|"
            r"profile|order|synteny|distance|member|hit|match)\w*\b|%|\d+\s*/\s*\d+",
            text, re.I,
        )
    )


def _bounded_inference_cell(value: str) -> bool:
    text = value or ""
    return _semantic_cell(text, minimum_words=5) and bool(re.search(
        r"\b(?:not|only|cannot|unknown|unresolved|candidate|hypothesis|navigation|"
        r"does not|insufficient)\b", text, re.I,
    ))


def _discriminating_action_cell(value: str) -> bool:
    text = value or ""
    return _semantic_cell(text, minimum_words=8) and bool(
        re.search(
            r"\b(?:align|compare|sequence|synteny|phylogen|delete|knockout|mutant|"
            r"complement|perturb|assay|LC[-– ]?MS|MS/MS|culture|profile)\w*\b",
            text, re.I,
        )
        and re.search(
            r"\b(?:measure|readout|identity|coverage|order|ortholog|feature|result|"
            r"distinguish|support|reject|retain|decision)\w*\b",
            text, re.I,
        )
    )


def _section6_semantic_v4_findings(
        body: str, canonical_loci: Optional[Iterable[str]]) -> list[dict]:
    """Require evidence-opposed tailoring adjudication or a typed terminal state."""
    terminal = _S6_TYPED_TERMINAL_RE.search(body or "")
    if terminal:
        denominator, sources, reason, resolving_test = (item.strip() for item in terminal.groups())
        findings: list[dict] = []
        if not re.search(r"\d", denominator):
            findings.append(_finding(
                "SECTION_6_TYPED_TERMINAL_DENOMINATOR", 6,
                "The tailoring terminal state needs a numeric searched-roster denominator.",
                found=denominator,
            ))
        if not _semantic_cell(sources) or not _semantic_cell(reason, minimum_words=5):
            findings.append(_finding(
                "SECTION_6_TYPED_TERMINAL_BASIS", 6,
                "The tailoring terminal state needs substantive sources and a reason.",
            ))
        if not _discriminating_action_cell(resolving_test):
            findings.append(_finding(
                "SECTION_6_TYPED_TERMINAL_TEST", 6,
                "The tailoring terminal state needs a discriminating resolving test.",
                found=resolving_test,
            ))
        return findings

    findings = _required_table_findings(
        body, section=6, heading="Tailoring and maturation adjudication",
        columns=_S6_V4_COLUMNS, minimum_rows=1,
    )
    header, rows = _named_contract_table(body, "Tailoring and maturation adjudication")
    if tuple(_normal_header(cell) for cell in header) != _S6_V4_COLUMNS:
        return findings
    expected = ({str(item).strip() for item in canonical_loci if str(item).strip()}
                if canonical_loci is not None else None)
    for index, row in enumerate(rows, 1):
        if len(row) != len(header):
            continue
        targets = set(_LOCUS.findall(row[0]))
        if not targets:
            findings.append(_finding(
                "SECTION_6_EXACT_TARGET_MISSING", 6,
                f"Tailoring row {index} must name at least one exact in-roster gene.",
            ))
        elif expected is not None and targets - expected:
            findings.append(_finding(
                "SECTION_6_TARGET_OUTSIDE_DISPLAYED_ROSTER", 6,
                "Tailoring targets must belong to the independently supplied displayed roster.",
                found=", ".join(sorted(targets - expected)),
            ))
        if not (_semantic_cell(row[1]) and re.search(
            r"\b(?:methyl|hydroxyl|oxid|reduc|glycosyl|acyl|cycl|cleav|dehydrat|"
            r"tailor|modify|isomer|epimer|crosslink)\w*\b", row[1], re.I,
        )):
            findings.append(_finding(
                "SECTION_6_CANDIDATE_REACTION_UNTYPED", 6,
                f"Tailoring row {index} must name a candidate chemical or maturation reaction.",
                found=row[1],
            ))
        for column, code in ((2, "EVIDENCE_FOR_UNTYPED"), (3, "EVIDENCE_AGAINST_UNTYPED")):
            if not (_semantic_cell(row[column], minimum_words=5) and re.search(
                r"\b(?:antiSMASH|BLAST|Pfam|domain|motif|residue|identity|coverage|"
                r"synteny|boundary|receipt|gene|protein|homolog|architecture)\w*\b",
                row[column], re.I,
            )):
                findings.append(_finding(
                    f"SECTION_6_{code}", 6,
                    f"Tailoring row {index} needs locus- or source-specific {code.lower().replace('_', ' ')}.",
                    found=row[column],
                ))
        if _normal_header(row[2]) == _normal_header(row[3]):
            findings.append(_finding(
                "SECTION_6_EVIDENCE_SIDES_COLLAPSED", 6,
                f"Tailoring row {index} must distinguish evidence for from evidence against.",
            ))
        if not (_semantic_cell(row[4], minimum_words=5) and re.search(
            r"\b(?:order|adjacent|distance|bp|synteny|co[- ]?locat|coupl|boundary|interval)\w*\b",
            row[4], re.I,
        )):
            findings.append(_finding(
                "SECTION_6_COUPLING_EVIDENCE_UNTYPED", 6,
                f"Tailoring row {index} needs physical order or coupling evidence.", found=row[4],
            ))
        if not _semantic_cell(row[5], minimum_words=4) or _normal_header(row[1]) == _normal_header(row[5]):
            findings.append(_finding(
                "SECTION_6_ALTERNATIVE_ROLE_COLLAPSED", 6,
                f"Tailoring row {index} needs a distinct alternative role.", found=row[5],
            ))
        if not _bounded_inference_cell(row[6]):
            findings.append(_finding(
                "SECTION_6_ALLOWED_INFERENCE_UNBOUNDED", 6,
                f"Tailoring row {index} needs an explicit claim ceiling.", found=row[6],
            ))
        if not _discriminating_action_cell(row[7]):
            findings.append(_finding(
                "SECTION_6_DISCRIMINATING_TEST_UNSPECIFIC", 6,
                f"Tailoring row {index} needs a test whose readout distinguishes the candidate reaction from the alternative.",
                found=row[7],
            ))
    return findings


def _comparison_conclusion_and_action_findings(body: str, section: int,
                                                conclusion_heading: str) -> list[dict]:
    findings: list[dict] = []
    conclusion = _named_heading_block(body, conclusion_heading)
    if not _bounded_inference_cell(conclusion):
        findings.append(_finding(
            f"SECTION_{section}_SEMANTIC_CONCLUSION_UNBOUNDED", section,
            f"Section {section} needs a substantive bounded conclusion under '{conclusion_heading}'.",
            found=conclusion.strip()[:160],
        ))
    action = _named_heading_block(body, "Discriminating next comparison")
    if not _discriminating_action_cell(action):
        findings.append(_finding(
            f"SECTION_{section}_DISCRIMINATING_NEXT_COMPARISON_MISSING", section,
            f"Section {section} needs a specific 'Discriminating next comparison' and decision-bearing readout.",
            found=action.strip()[:160],
        ))
    return findings


def _section45_semantic_v4_findings(body: str) -> list[dict]:
    findings = _comparison_conclusion_and_action_findings(
        body, 45, "Cohort-comparison conclusion")
    if _TYPED_COHORT_NONE_RE.search(body or ""):
        return findings
    header, rows = _named_contract_table(body, "Cohort gene comparison")
    if tuple(_normal_header(cell) for cell in header) != _S45_COLUMNS:
        return findings
    for index, row in enumerate(rows, 1):
        if len(row) != len(header):
            continue
        if not _measured_comparison_cell(row[3]):
            findings.append(_finding(
                "SECTION_45_SEQUENCE_SYNTENY_UNMEASURED", 45,
                f"Cohort row {index} needs a measured sequence or gene-order comparison.", found=row[3],
            ))
        agreement = bool(re.search(r"\b(?:agree|shared|concord|match|retained|same)\w*\b", row[4], re.I))
        mismatch = bool(re.search(r"\b(?:mismatch|differ|diverg|absent|missing|not|but)\w*\b", row[4], re.I))
        if not (_semantic_cell(row[4], minimum_words=6) and agreement and mismatch):
            findings.append(_finding(
                "SECTION_45_AGREEMENT_MISMATCH_NOT_OPPOSED", 45,
                f"Cohort row {index} must state both an agreement and a mismatch.", found=row[4],
            ))
        if not _bounded_inference_cell(row[5]):
            findings.append(_finding(
                "SECTION_45_ALLOWED_INFERENCE_UNBOUNDED", 45,
                f"Cohort row {index} needs a bounded allowed inference.", found=row[5],
            ))
    return findings


def _section46_semantic_v4_findings(body: str) -> list[dict]:
    findings = _comparison_conclusion_and_action_findings(
        body, 46, "Type/reference comparison conclusion")
    typed_ok, _reason = _typed_section_unavailable(body, 46)
    if typed_ok:
        return findings
    header, rows = _named_contract_table(body, "Type/reference gene comparison")
    if tuple(_normal_header(cell) for cell in header) != _S46_COLUMNS:
        return findings
    for index, row in enumerate(rows, 1):
        if len(row) != len(header):
            continue
        if not _measured_comparison_cell(row[3]):
            findings.append(_finding(
                "SECTION_46_PROFILE_COMPATIBILITY_UNMEASURED", 46,
                f"Type/reference row {index} needs measured profile compatibility.", found=row[3],
            ))
        if not (_semantic_cell(row[4], minimum_words=5) and re.search(
            r"\b(?:differ|diverg|absent|missing|extra|mismatch|not shared|distinct)\w*\b",
            row[4], re.I,
        )):
            findings.append(_finding(
                "SECTION_46_DIVERGENCE_UNTYPED", 46,
                f"Type/reference row {index} needs concrete divergence or counterevidence.", found=row[4],
            ))
        if not _bounded_inference_cell(row[5]):
            findings.append(_finding(
                "SECTION_46_ALLOWED_INFERENCE_UNBOUNDED", 46,
                f"Type/reference row {index} needs a bounded allowed inference.", found=row[5],
            ))
    return findings


def _section47_semantic_v4_findings(body: str) -> list[dict]:
    findings = _comparison_conclusion_and_action_findings(
        body, 47, "Host-matched comparison conclusion")
    typed_ok, _reason = _typed_section_unavailable(body, 47)
    if typed_ok:
        return findings
    header, rows = _named_contract_table(body, "Host-matched gene comparison")
    if tuple(_normal_header(cell) for cell in header) != _S47_COLUMNS:
        return findings
    for index, row in enumerate(rows, 1):
        if len(row) != len(header):
            continue
        if not re.search(r"\b[0-9a-f]{64}\b", row[1], re.I):
            findings.append(_finding(
                "SECTION_47_HOST_METADATA_RECEIPT_INVALID", 47,
                f"Host-matched row {index} must bind metadata to a 64-hex SHA-256 receipt.", found=row[1],
            ))
        if not (_semantic_cell(row[4], minimum_words=5) and re.search(
            r"\b(?:host|niche|lineage|taxonom|ecolog|source)\w*\b", row[4], re.I,
        )):
            findings.append(_finding(
                "SECTION_47_COMPARATOR_RATIONALE_UNTYPED", 47,
                f"Host-matched row {index} needs a specific host/lineage comparator rationale.", found=row[4],
            ))
        if not _measured_comparison_cell(row[5]):
            findings.append(_finding(
                "SECTION_47_SEQUENCE_SYNTENY_UNMEASURED", 47,
                f"Host-matched row {index} needs a measured sequence or gene-order comparison.", found=row[5],
            ))
        if not _bounded_inference_cell(row[6]):
            findings.append(_finding(
                "SECTION_47_TRANSFER_LIMITS_UNBOUNDED", 47,
                f"Host-matched row {index} needs explicit transfer limits.", found=row[6],
            ))
        if not _bounded_inference_cell(row[7]):
            findings.append(_finding(
                "SECTION_47_ALLOWED_INFERENCE_UNBOUNDED", 47,
                f"Host-matched row {index} needs a bounded allowed inference.", found=row[7],
            ))
    return findings


def _comparison_table_findings(body: str, *, section: int, heading: str,
                               columns: tuple[str, ...], canonical_loci: Optional[Iterable[str]],
                               denominator_heading: str, conclusion_heading: str) -> list[dict]:
    """Shared exact-locus/gene checks for Sections 46 and 47."""
    typed_ok, typed_reason = _typed_section_unavailable(body, section)
    if typed_ok:
        return []
    findings: list[dict] = []
    if not re.search(rf"(?im)^#### {re.escape(denominator_heading)}\s*$", body or ""):
        findings.append(_finding(
            f"SECTION_{section}_DENOMINATOR_MISSING", section,
            f"Section {section} needs a '{denominator_heading}' subsection or a validated typed "
            "unavailable state.", found=typed_reason,
        ))
    header, rows = _named_contract_table(body, heading)
    if not header:
        findings.append(_finding(
            f"SECTION_{section}_COMPARATOR_TABLE_MISSING", section,
            f"Section {section} needs a '{heading}' table with complete comparator identity, exact "
            "genes, evidence, disagreements and an allowed inference.",
        ))
    else:
        normalized = tuple(_normal_header(cell) for cell in header)
        if normalized != columns:
            findings.append(_finding(
                f"SECTION_{section}_COMPARATOR_TABLE_COLUMNS", section,
                f"The Section {section} comparator columns must be exactly: " + "; ".join(columns),
                found="; ".join(normalized),
            ))
        elif not rows:
            findings.append(_finding(
                f"SECTION_{section}_COMPARATOR_TABLE_EMPTY", section,
                f"The Section {section} comparator table has no data rows.",
            ))
        else:
            expected = ({str(item).strip() for item in canonical_loci if str(item).strip()}
                        if canonical_loci is not None else None)
            for index, row in enumerate(rows, 1):
                if len(row) != len(header) or not all(cell.strip() for cell in row):
                    findings.append(_finding(
                        f"SECTION_{section}_COMPARATOR_ROW_INCOMPLETE", section,
                        f"Comparator row {index} must fill every required cell.",
                    ))
                    continue
                if not _COMPLETE_LOCUS.fullmatch(row[0].strip()):
                    findings.append(_finding(
                        f"SECTION_{section}_COMPARATOR_IDENTITY_INCOMPLETE", section,
                        "Every comparator must display strain / full node-or-contig / region / BGC alias.",
                        found=row[0],
                    ))
                query_col = 2 if section == 47 else 1
                comparator_col = 3 if section == 47 else 2
                query_genes = set(_LOCUS.findall(row[query_col]))
                comparator_genes = set(_LOCUS.findall(row[comparator_col]))
                if not query_genes or not comparator_genes:
                    findings.append(_finding(
                        f"SECTION_{section}_COMPARATOR_GENES_MISSING", section,
                        f"Comparator row {index} must name exact query and comparator genes.",
                    ))
                if expected is not None and query_genes - expected:
                    findings.append(_finding(
                        f"SECTION_{section}_QUERY_GENE_OUTSIDE_DISPLAYED_ROSTER", section,
                        f"Section {section} query genes must belong to the independently supplied displayed roster.",
                        found=", ".join(sorted(query_genes - expected)),
                    ))
                if section == 47 and not re.search(
                    r"\b(?:verified|receipt|accession|source|metadata|manifest)\b", row[1], re.I
                ):
                    findings.append(_finding(
                        "SECTION_47_HOST_METADATA_UNVERIFIED", 47,
                        "The host-metadata cell must identify its verification source or receipt.",
                        found=row[1],
                    ))
    if not re.search(rf"(?im)^#### {re.escape(conclusion_heading)}\s*$", body or ""):
        findings.append(_finding(
            f"SECTION_{section}_CONCLUSION_MISSING", section,
            f"Section {section} requires a '{conclusion_heading}' subsection that preserves "
            "comparison limits and the claim ceiling.",
        ))
    return findings


def _section46_findings(body: str,
                        canonical_loci: Optional[Iterable[str]]) -> list[dict]:
    return _comparison_table_findings(
        body, section=46, heading="Type/reference gene comparison", columns=_S46_COLUMNS,
        canonical_loci=canonical_loci, denominator_heading="Type/reference comparison denominator",
        conclusion_heading="Type/reference comparison conclusion",
    )


def _section47_findings(body: str,
                        canonical_loci: Optional[Iterable[str]]) -> list[dict]:
    return _comparison_table_findings(
        body, section=47, heading="Host-matched gene comparison", columns=_S47_COLUMNS,
        canonical_loci=canonical_loci, denominator_heading="Host-matched comparison denominator",
        conclusion_heading="Host-matched comparison conclusion",
    )


def _repeated_generic_sentence_findings(bodies: dict[int, str]) -> list[dict]:
    """Reject repeated evidence-free prose without rewarding longer cards."""
    sentence_sections: dict[str, set[int]] = {}
    sentence_example: dict[str, str] = {}
    evidence = re.compile(
        r"\b(?:ctg\d+_\d+|WP_\d+|BGC\d{7}|antiSMASH|Mamey|MIBiG|BiG-SCAPE|"
        r"ClusterBlast|RG-GMCI|BLAST|protein SHA|flanks?|contig edge|boundary|interval|"
        r"\d+\s*bp|\d+\s+CDS|\d+\s*/\s*\d+)\b|https?://",
        re.I,
    )
    for section, body in bodies.items():
        if section == 28:
            continue
        prose = "\n".join(line for line in body.splitlines()
                           if not line.lstrip().startswith(("|", "#", "<!--")))
        for sentence in re.split(r"(?<=[.!?])\s+", prose):
            sentence = sentence.strip()
            if len(sentence) < 35 or evidence.search(sentence):
                continue
            normalized = _COMPLETE_AS_LOCUS.sub("<LOCUS>", sentence)
            normalized = _LOCUS.sub("<GENE>", normalized)
            normalized = re.sub(r"\b\d+(?:\.\d+)?\b", "<N>", normalized)
            normalized = re.sub(r"\s+", " ", normalized).strip().casefold()
            sentence_sections.setdefault(normalized, set()).add(section)
            sentence_example.setdefault(normalized, sentence)
    repeated = [(key, sections) for key, sections in sentence_sections.items() if len(sections) >= 3]
    if not repeated:
        return []
    examples = "; ".join(
        f"§{','.join(map(str, sorted(sections)))}: {sentence_example[key][:120]}"
        for key, sections in repeated[:5]
    )
    return [_finding(
        "REPEATED_GENERIC_SENTENCE", None,
        "The same evidence-free sentence appears in three or more sections. Remove it or replace "
        "it with section-specific evidence. Card length is not a quality target.", found=examples,
    )]


def _stream_findings(rows: list[list[str]]) -> list[dict]:
    findings: list[dict] = []
    for stream in PUBLICATION_EVIDENCE_STREAMS:
        matches = [row for row in rows
                   if row and row[0].casefold() == stream.casefold()
                   and ({cell.upper() for cell in row} & STREAM_STATES)]
        if len(matches) != 1:
            findings.append(_finding("EVIDENCE_STREAM_DISPOSITION", 28,
                                     f"Expected exactly one row for {stream!r}; found {len(matches)}."))
            continue
        states = {cell.upper() for cell in matches[0]} & STREAM_STATES
        if len(states) != 1:
            findings.append(_finding("EVIDENCE_STREAM_STATE", 28,
                                     f"{stream!r} needs one typed state from {sorted(STREAM_STATES)}."))
        if len(matches[0]) < 3 or not matches[0][-1]:
            findings.append(_finding("EVIDENCE_STREAM_INTERPRETATION", 28,
                                     f"{stream!r} needs an interpretation-effect sentence."))
    return findings


def _history_findings(rows: list[list[str]]) -> list[dict]:
    findings: list[dict] = []
    for source in HISTORICAL_SOURCES:
        matches = [row for row in rows
                   if row and row[0].casefold() == source.casefold()
                   and ({cell.upper() for cell in row} & HISTORY_DISPOSITIONS)]
        if len(matches) != 1:
            findings.append(_finding("HISTORICAL_SOURCE_LOSS", 28,
                                     f"Expected exactly one reconciliation row for {source!r}."))
            continue
        states = {cell.upper() for cell in matches[0]} & HISTORY_DISPOSITIONS
        if len(states) != 1:
            findings.append(_finding("HISTORICAL_DISPOSITION", 28,
                                     f"{source!r} needs one disposition from {sorted(HISTORY_DISPOSITIONS)}."))
        if len(matches[0]) < 3 or not matches[0][-1]:
            findings.append(_finding("HISTORICAL_REASON_MISSING", 28,
                                     f"{source!r} needs a content-retention decision and reason."))
    return findings


def _section_matrix_findings(rows: list[list[str]]) -> list[dict]:
    """Require an accountable reconciliation row for every one of §1–§48."""
    findings: list[dict] = []
    for number in range(1, 49):
        labels = {f"§{number}", f"SECTION {number}"}
        matches = [row for row in rows if row and row[0].strip().upper() in labels]
        if len(matches) != 1:
            findings.append(_finding("SECTION_RECONCILIATION_ROW", number,
                                     f"Expected exactly one section-matrix row for §{number}."))
            continue
        row = matches[0]
        # The contract fixes columns: section, state, evidence, predecessor, note.
        # Tokens in prose cells must not validate an unrelated control field.
        state = row[1].strip().upper() if len(row) > 1 else ""
        predecessor = row[3].strip().upper() if len(row) > 3 else ""
        if state not in SECTION_STATES:
            findings.append(_finding("SECTION_RECONCILIATION_STATE", number,
                                     f"§{number} needs SUBSTANTIVE, REASONED_NOT_APPLICABLE, or REVIEWED_SCOPE_LIMIT."))
        if predecessor not in HISTORY_DISPOSITIONS:
            findings.append(_finding("SECTION_PREDECESSOR_DISPOSITION", number,
                                     f"§{number} needs a predecessor-content disposition."))
        if len(row) < 5 or not row[2] or not row[-1]:
            findings.append(_finding("SECTION_RECONCILIATION_DETAIL", number,
                                     f"§{number} needs named evidence and a reconciliation note."))
    return findings


def _normalise_reconciliation_cell_v11(cell: str) -> str:
    """Normalise superficial variation in a §28 evidence/note cell.

    Section labels are deliberately removed so adding ``section 1``,
    ``section 2``, ... to one copied sentence does not manufacture apparent
    specificity.  Scientific identifiers and source names remain visible.
    """
    value = re.sub(r"§\s*\d+|\bsection\s+\d+\b", " ", cell, flags=re.I)
    value = re.sub(r"[^a-z0-9]+", " ", value.casefold())
    return " ".join(value.split())


def _section_matrix_specificity_v11_findings(
        rows: list[list[str]], *, reuse_floor: int = 8) -> list[dict]:
    """Reject one evidence/note pair reused across many §28 section rows.

    This narrow prospective check does not score card prose or fixed
    claim-safety language.  It only tests the two cells that are supposed to
    explain why each section is substantively supported and how predecessor
    content was reconciled.
    """
    pairs: Counter[tuple[str, str]] = Counter()
    for row in rows:
        if len(row) < 5 or not re.fullmatch(r"(?:§\s*|SECTION\s+)\d+", row[0].strip(), re.I):
            continue
        evidence = _normalise_reconciliation_cell_v11(row[2])
        note = _normalise_reconciliation_cell_v11(row[-1])
        if evidence and note:
            pairs[(evidence, note)] += 1
    repeated = sorted(
        ((count, evidence, note) for (evidence, note), count in pairs.items()
         if count >= reuse_floor),
        reverse=True,
    )
    if not repeated:
        return []
    count, evidence, note = repeated[0]
    return [_finding(
        "SECTION_RECONCILIATION_V11_TEMPLATE_REUSE", 28,
        (f"The same normalized evidence/note pair occurs in {count} section rows; "
         f"the prospective v11 floor permits at most {reuse_floor - 1}. "
         "Name section-specific evidence and the actual reconciliation decision."),
        found=f"evidence={evidence!r}; note={note!r}",
    )]


def _section15_semantic_v5_findings(body: str) -> list[dict]:
    """Require a receipt-bound missing-object to decision-resolution chain."""
    findings = _required_table_findings(
        body, section=15, heading="Missing-evidence ledger",
        columns=_S15_V5_COLUMNS, minimum_rows=1,
    )
    header, rows = _named_contract_table(body, "Missing-evidence ledger")
    if tuple(_normal_header(cell) for cell in header) != _S15_V5_COLUMNS:
        return findings
    for index, row in enumerate(rows, 1):
        if len(row) != len(header):
            continue
        if not _semantic_cell(row[0], minimum_words=3):
            findings.append(_finding(
                "SECTION_15_MISSING_OBJECT_UNTYPED", 15,
                f"Missing-evidence row {index} must name the exact missing object.",
                found=row[0],
            ))
        if not _SHA256_RE.fullmatch(row[1].strip()):
            findings.append(_finding(
                "SECTION_15_SOURCE_STATE_RECEIPT_INVALID", 15,
                f"Missing-evidence row {index} must bind its source/state to a 64-hex SHA-256 receipt.",
                found=row[1],
            ))
        if row[2].strip().upper() not in _S15_STATES:
            findings.append(_finding(
                "SECTION_15_STATE_UNTYPED", 15,
                f"Missing-evidence row {index} needs one of {sorted(_S15_STATES)}.",
                found=row[2],
            ))
        if not _semantic_cell(row[3], minimum_words=5):
            findings.append(_finding(
                "SECTION_15_REASON_UNSUBSTANTIVE", 15,
                f"Missing-evidence row {index} must explain why the object is missing.",
                found=row[3],
            ))
        if not _bounded_inference_cell(row[4]):
            findings.append(_finding(
                "SECTION_15_AFFECTED_INFERENCE_UNBOUNDED", 15,
                f"Missing-evidence row {index} must state the inference that remains limited.",
                found=row[4],
            ))
        if not _discriminating_action_cell(row[5]):
            findings.append(_finding(
                "SECTION_15_RESOLVING_ACQUISITION_UNSPECIFIC", 15,
                f"Missing-evidence row {index} needs a specific acquisition or analysis with a measurable result.",
                found=row[5],
            ))
        if not (_semantic_cell(row[6], minimum_words=6) and re.search(
            r"\b(?:if|only|advance|retain|reject|hold|support|require)\w*\b",
            row[6], re.I,
        )):
            findings.append(_finding(
                "SECTION_15_DECISION_RULE_MISSING", 15,
                f"Missing-evidence row {index} must state how the acquired result changes the decision.",
                found=row[6],
            ))
    return findings


def _section19_semantic_v5_findings(body: str, section20: str) -> list[dict]:
    """Require a final decision whose support, conflict, ceiling and action remain opposed."""
    findings = _required_table_findings(
        body, section=19, heading="Final decision record",
        columns=_S19_V5_COLUMNS, minimum_rows=1,
    )
    header, rows = _named_contract_table(body, "Final decision record")
    if tuple(_normal_header(cell) for cell in header) != _S19_V5_COLUMNS:
        return findings
    action_header, action_rows = _named_contract_table(
        section20, "Highest-information next action")
    actions = {
        _normal_header(row[0]) for row in action_rows
        if tuple(_normal_header(cell) for cell in action_header) == _S20_COLUMNS
        and len(row) == len(action_header)
    }
    for index, row in enumerate(rows, 1):
        if len(row) != len(header):
            continue
        if row[0].strip().upper() not in _S19_DISPOSITIONS:
            findings.append(_finding(
                "SECTION_19_DISPOSITION_UNTYPED", 19,
                f"Final-decision row {index} needs one of {sorted(_S19_DISPOSITIONS)}.",
                found=row[0],
            ))
        for column, code in ((1, "SUPPORT_UNSUBSTANTIVE"), (2, "CONFLICT_UNSUBSTANTIVE")):
            if not (_semantic_cell(row[column], minimum_words=6) and re.search(
                r"\b(?:antiSMASH|BLAST|Pfam|domain|motif|identity|coverage|synteny|"
                r"boundary|receipt|manifest|gene|protein|roster|measured|missing|absent)\w*\b",
                row[column], re.I,
            )):
                findings.append(_finding(
                    f"SECTION_19_{code}", 19,
                    f"Final-decision row {index} needs source- or locus-specific {code.lower().replace('_', ' ')}.",
                    found=row[column],
                ))
        if _normal_header(row[1]) == _normal_header(row[2]):
            findings.append(_finding(
                "SECTION_19_SUPPORT_CONFLICT_COLLAPSED", 19,
                f"Final-decision row {index} must distinguish supporting evidence from conflict or alternative.",
            ))
        if not (_semantic_cell(row[3], minimum_words=4) and re.search(
            r"\b(?:interior|edge|complete|incomplete|truncat|overmerge|split|"
            r"unbound|closed|boundary|context)\w*\b",
            row[3], re.I,
        )):
            findings.append(_finding(
                "SECTION_19_BOUNDARY_STATE_UNTYPED", 19,
                f"Final-decision row {index} needs an explicit boundary/completeness state.",
                found=row[3],
            ))
        if not _bounded_inference_cell(row[4]):
            findings.append(_finding(
                "SECTION_19_CLAIM_CEILING_UNBOUNDED", 19,
                f"Final-decision row {index} needs an explicit claim ceiling.",
                found=row[4],
            ))
        if _normal_header(row[5]) not in actions:
            findings.append(_finding(
                "SECTION_19_ACTION_NOT_LINKED_TO_SECTION_20", 19,
                "The final decision must repeat exactly one action from the Section 20 highest-information table.",
                found=row[5],
            ))
    return findings


def _section29_semantic_v5_findings(body: str) -> list[dict]:
    """Require physical-versus-functional adjudication or a typed terminal state."""
    terminal = _S29_TYPED_TERMINAL_RE.search(body or "")
    if terminal:
        denominator, sources, reason, resolving_test = (
            value.strip() for value in terminal.groups())
        findings: list[dict] = []
        if not re.search(r"\d", denominator):
            findings.append(_finding(
                "SECTION_29_TYPED_TERMINAL_DENOMINATOR", 29,
                "The terminal state needs a numeric searched-partner denominator.",
                found=denominator,
            ))
        if not (_semantic_cell(sources, minimum_words=4)
                and _semantic_cell(reason, minimum_words=6)):
            findings.append(_finding(
                "SECTION_29_TYPED_TERMINAL_BASIS", 29,
                "The terminal state needs substantive sources and a reason.",
            ))
        if not _discriminating_action_cell(resolving_test):
            findings.append(_finding(
                "SECTION_29_TYPED_TERMINAL_TEST", 29,
                "The terminal state needs a specific resolving test.",
                found=resolving_test,
            ))
        return findings
    findings = _required_table_findings(
        body, section=29, heading="Cross-cluster interaction adjudication",
        columns=_S29_V5_COLUMNS, minimum_rows=1,
    )
    header, rows = _named_contract_table(body, "Cross-cluster interaction adjudication")
    if tuple(_normal_header(cell) for cell in header) != _S29_V5_COLUMNS:
        return findings
    for index, row in enumerate(rows, 1):
        if len(row) != len(header):
            continue
        if not _COMPLETE_AS_LOCUS.fullmatch(row[0].strip()):
            findings.append(_finding(
                "SECTION_29_PARTNER_IDENTITY_INCOMPLETE", 29,
                "Every proposed partner must display strain / full node-or-contig / region / BGC alias.",
                found=row[0],
            ))
        if not (_semantic_cell(row[1], minimum_words=4) and re.search(
            r"\b(?:trans[- ]acting|precursor|substrate|regulat|transport|resistance|"
            r"maturation|complement|shared intermediate|functional coupling)\w*\b",
            row[1], re.I,
        )):
            findings.append(_finding(
                "SECTION_29_INTERACTION_MECHANISM_UNTYPED", 29,
                f"Cross-cluster row {index} must name a plausible interaction mechanism.",
                found=row[1],
            ))
        if not (_semantic_cell(row[2], minimum_words=6)
                and _semantic_cell(row[3], minimum_words=6)):
            findings.append(_finding(
                "SECTION_29_EVIDENCE_SIDES_UNSUBSTANTIVE", 29,
                f"Cross-cluster row {index} needs substantive evidence for and against.",
            ))
        if _normal_header(row[2]) == _normal_header(row[3]):
            findings.append(_finding(
                "SECTION_29_EVIDENCE_SIDES_COLLAPSED", 29,
                f"Cross-cluster row {index} must distinguish evidence for from evidence against.",
            ))
        if row[4].strip().upper() not in _S29_PHYSICAL_STATES:
            findings.append(_finding(
                "SECTION_29_PHYSICAL_LINK_STATE_UNTYPED", 29,
                f"Cross-cluster row {index} needs one of {sorted(_S29_PHYSICAL_STATES)}.",
                found=row[4],
            ))
        if not _bounded_inference_cell(row[5]):
            findings.append(_finding(
                "SECTION_29_ALLOWED_INFERENCE_UNBOUNDED", 29,
                f"Cross-cluster row {index} needs a bounded allowed inference.",
                found=row[5],
            ))
        if not _discriminating_action_cell(row[6]):
            findings.append(_finding(
                "SECTION_29_DISCRIMINATING_TEST_UNSPECIFIC", 29,
                f"Cross-cluster row {index} needs a test whose readout distinguishes coupling from independence.",
                found=row[6],
            ))
    return findings


def _section31_semantic_v5_findings(
        body: str, canonical_loci: Optional[Iterable[str]]) -> list[dict]:
    """Require exact displayed-roster reconciliation, not merely plausible prose."""
    findings = _required_table_findings(
        body, section=31, heading="Region CDS census reconciliation",
        columns=_S31_V5_COLUMNS, minimum_rows=1,
    )
    header, rows = _named_contract_table(body, "Region CDS census reconciliation")
    if tuple(_normal_header(cell) for cell in header) != _S31_V5_COLUMNS:
        return findings
    expected = ({str(item).strip() for item in canonical_loci if str(item).strip()}
                if canonical_loci is not None else None)
    if expected is None:
        findings.append(_finding(
            "SECTION_31_CANONICAL_ROSTER_UNBOUND", 31,
            "Section 31 cannot be certified without an independently supplied canonical roster.",
        ))
    for index, row in enumerate(rows, 1):
        if len(row) != len(header):
            continue
        if not _SHA256_RE.fullmatch(row[0].strip()):
            findings.append(_finding(
                "SECTION_31_ROSTER_RECEIPT_INVALID", 31,
                f"Census row {index} must bind the canonical roster to a 64-hex SHA-256 receipt.",
                found=row[0],
            ))
        exact = set(_LOCUS.findall(row[1]))
        context = set() if row[2].strip().upper() == "NONE" else set(_LOCUS.findall(row[2]))
        displayed = set(_LOCUS.findall(row[3]))
        if not exact or not displayed:
            findings.append(_finding(
                "SECTION_31_GENE_SETS_MISSING", 31,
                f"Census row {index} must enumerate exact-region and displayed genes.",
            ))
        if (exact & context) or ((exact | context) != displayed):
            findings.append(_finding(
                "SECTION_31_INTERNAL_CENSUS_MISMATCH", 31,
                "Exact-region and boundary-context sets must be disjoint and union to the displayed set.",
                found=", ".join(sorted(displayed)),
            ))
        if row[4].strip().upper() != "NONE" or row[5].strip().upper() != "NONE":
            findings.append(_finding(
                "SECTION_31_NONZERO_RECONCILIATION", 31,
                "A finished-profile census must state NONE for both missing and extra genes.",
                found=f"missing={row[4]}; extra={row[5]}",
            ))
        if row[6].strip().upper() != "EXACT_MATCH":
            findings.append(_finding(
                "SECTION_31_RECONCILIATION_STATE", 31,
                "The finished-profile census reconciliation state must be EXACT_MATCH.",
                found=row[6],
            ))
        if expected is not None and displayed != expected:
            findings.append(_finding(
                "SECTION_31_DISPLAYED_ROSTER_MISMATCH", 31,
                "Section 31 displayed genes must equal the independently supplied canonical roster.",
                found=", ".join(sorted(displayed)),
            ))
    return findings


def _section43_semantic_v5_findings(body: str) -> list[dict]:
    """Require arithmetic RG-GMCI accounting and opposed split-pathway adjudication."""
    findings = _required_table_findings(
        body, section=43, heading="RG-GMCI accounting",
        columns=_S43_ACCOUNTING_V5_COLUMNS, minimum_rows=1,
    )
    account_header, account_rows = _named_contract_table(body, "RG-GMCI accounting")
    total_pairs: Optional[int] = None
    if tuple(_normal_header(cell) for cell in account_header) == _S43_ACCOUNTING_V5_COLUMNS:
        if len(account_rows) != 1:
            findings.append(_finding(
                "SECTION_43_ACCOUNTING_ROW_COUNT", 43,
                "RG-GMCI accounting requires exactly one denominator row.",
                found=str(len(account_rows)),
            ))
        for row in account_rows:
            if len(row) != len(account_header):
                continue
            if not _SHA256_RE.fullmatch(row[0].strip()):
                findings.append(_finding(
                    "SECTION_43_RUN_RECEIPT_INVALID", 43,
                    "RG-GMCI accounting must bind the run to a 64-hex SHA-256 receipt.",
                    found=row[0],
                ))
            try:
                values = [int(cell.strip()) for cell in row[1:]]
            except ValueError:
                findings.append(_finding(
                    "SECTION_43_ACCOUNTING_NONNUMERIC", 43,
                    "Pair denominator, confidence counts and rescue rows must be nonnegative integers.",
                ))
                continue
            if any(value < 0 for value in values):
                findings.append(_finding(
                    "SECTION_43_ACCOUNTING_NEGATIVE", 43,
                    "RG-GMCI counts cannot be negative.",
                ))
                continue
            total_pairs, high, moderate, low, rescue = values
            if high + moderate + low != total_pairs:
                findings.append(_finding(
                    "SECTION_43_CONFIDENCE_COUNTS_MISMATCH", 43,
                    "HIGH + MODERATE + LOW counts must equal the pair denominator.",
                    found=f"{high}+{moderate}+{low}!={total_pairs}",
                ))
            if rescue > total_pairs:
                findings.append(_finding(
                    "SECTION_43_RESCUE_COUNT_EXCEEDS_PAIRS", 43,
                    "Two-proof rescue rows cannot exceed the pair denominator.",
                    found=str(rescue),
                ))
    findings.extend(_required_table_findings(
        body, section=43, heading="Split-pathway adjudication",
        columns=_S43_ADJUDICATION_V5_COLUMNS, minimum_rows=1,
    ))
    adj_header, adj_rows = _named_contract_table(body, "Split-pathway adjudication")
    if tuple(_normal_header(cell) for cell in adj_header) != _S43_ADJUDICATION_V5_COLUMNS:
        return findings
    for index, row in enumerate(adj_rows, 1):
        if len(row) != len(adj_header):
            continue
        partner = row[0].strip()
        if total_pairs == 0:
            if partner.upper() != "MEASURED_ZERO_PARTNERS":
                findings.append(_finding(
                    "SECTION_43_ZERO_PARTNER_STATE_MISSING", 43,
                    "A zero pair denominator requires MEASURED_ZERO_PARTNERS.",
                    found=partner,
                ))
        elif total_pairs is not None and not _COMPLETE_AS_LOCUS.fullmatch(partner):
            findings.append(_finding(
                "SECTION_43_PARTNER_IDENTITY_INCOMPLETE", 43,
                "A nonzero RG-GMCI result requires strain / full node-or-contig / region / BGC alias.",
                found=partner,
            ))
        if not (_semantic_cell(row[1], minimum_words=6)
                and _semantic_cell(row[2], minimum_words=6)):
            findings.append(_finding(
                "SECTION_43_LINK_EVIDENCE_UNSUBSTANTIVE", 43,
                f"Split-pathway row {index} needs substantive functional and physical-link evidence.",
            ))
        if not _semantic_cell(row[3], minimum_words=5):
            findings.append(_finding(
                "SECTION_43_ALTERNATIVE_UNSUBSTANTIVE", 43,
                f"Split-pathway row {index} needs a distinct alternative.",
                found=row[3],
            ))
        if _normal_header(row[1]) == _normal_header(row[3]):
            findings.append(_finding(
                "SECTION_43_MODEL_ALTERNATIVE_COLLAPSED", 43,
                f"Split-pathway row {index} must distinguish the coupling model from its alternative.",
            ))
        if not _bounded_inference_cell(row[4]):
            findings.append(_finding(
                "SECTION_43_ALLOWED_INFERENCE_UNBOUNDED", 43,
                f"Split-pathway row {index} needs a bounded allowed inference.",
                found=row[4],
            ))
        if not _discriminating_action_cell(row[5]):
            findings.append(_finding(
                "SECTION_43_RESOLVING_ACTION_UNSPECIFIC", 43,
                f"Split-pathway row {index} needs a specific action and decision-bearing readout.",
                found=row[5],
            ))
    return findings


def semantic_sections_v5_receipt_hashes(card_md: str) -> dict[str, list[str]]:
    """Return normalized receipt cells from the three v5 provenance tables.

    This deliberately extracts table cells without deciding whether they are
    trustworthy.  A request validator that owns the external artifacts can
    compare them with independently verified hashes.
    """
    bodies = extract_section_bodies(card_md)
    specs = (
        ("section15_missing_evidence_state", 15, "Missing-evidence ledger", _S15_V5_COLUMNS, 1),
        ("section31_canonical_roster", 31, "Region CDS census reconciliation", _S31_V5_COLUMNS, 0),
        ("section43_rggmci_run", 43, "RG-GMCI accounting", _S43_ACCOUNTING_V5_COLUMNS, 0),
    )
    result: dict[str, list[str]] = {}
    for key, section, heading, columns, column_index in specs:
        header, rows = _named_contract_table(bodies.get(section, ""), heading)
        if tuple(_normal_header(cell) for cell in header) != columns:
            result[key] = []
            continue
        result[key] = [
            row[column_index].strip().lower()
            for row in rows if len(row) == len(header)
        ]
    return result


def semantic_decision_chain_v6_bindings(
        card_md: str) -> dict[str, list[dict[str, object]]]:
    """Extract typed states and evidence hashes from the eight v6 tables.

    The publication gate owns the Markdown table grammar.  A request validator
    that owns external artifacts can use this deliberately non-authenticating
    projection to compare card literals with independently verified receipts.
    """
    bodies = extract_section_bodies(card_md)
    result: dict[str, list[dict[str, object]]] = {}
    for section in _V6_PROFILES:
        header, rows = _named_contract_table(
            bodies.get(section, ""), "Semantic decision chain")
        key = f"section{section}"
        if tuple(_normal_header(cell) for cell in header) != _V6_DECISION_CHAIN_COLUMNS:
            result[key] = []
            continue
        result[key] = [
            {
                "typed_state": row[0].strip().upper(),
                "evidence_hashes": [
                    value.lower() for value in
                    re.findall(r"\b[0-9a-f]{64}\b", row[2], re.I)
                ],
            }
            for row in rows if len(row) == len(header)
        ]
    return result


def semantic_claim_model_v7_bindings(card_md: str) -> dict[str, list[dict[str, object]]]:
    """Project v7 literals for validation by the owner of external artifacts."""
    bodies = extract_section_bodies(card_md)
    result: dict[str, list[dict[str, object]]] = {}
    for section in _V7_PROFILES:
        header, rows = _named_contract_table(bodies.get(section, ""), "Semantic claim model")
        key = f"section{section}"
        if tuple(_normal_header(cell) for cell in header) != _V7_CLAIM_MODEL_COLUMNS:
            result[key] = []
            continue
        result[key] = [{"typed_state": row[0].strip().upper(),
                        "evidence_hashes": re.findall(r"\b[0-9a-f]{64}\b", row[4].lower())}
                       for row in rows if len(row) == len(header)]
    return result


def inventory_reconciliation_v8_bindings(card_md: str) -> dict[str, list[dict[str, object]]]:
    """Project v8 inventory row literals for external artifact validation."""
    bodies = extract_section_bodies(card_md)
    result: dict[str, list[dict[str, object]]] = {}
    for section in _V8_INVENTORY_PROFILES:
        header, rows = _named_contract_table(
            bodies.get(section, ""), "Inventory reconciliation")
        key = f"section{section}"
        if tuple(_normal_header(cell) for cell in header) != _V8_INVENTORY_COLUMNS:
            result[key] = []
            continue
        result[key] = [{
            "typed_state": row[0].strip().upper(),
            "exact_member_or_typed_zero": row[1].strip().strip("`"),
            "section_specific_role": row[2].strip(),
            "evidence_hashes": re.findall(r"\b[0-9a-f]{64}\b", row[3].lower()),
            "declared_denominator": row[4].strip(),
            "evidence_state": row[5].strip().upper(),
        } for row in rows if len(row) == len(header)]
    return result


def selection_process_v9_bindings(card_md: str) -> list[dict[str, object]]:
    """Project section-2 selection literals for external artifact validation."""
    body = extract_section_bodies(card_md).get(2, "")
    header, rows = _named_contract_table(body, "Selection process")
    if tuple(_normal_header(cell) for cell in header) != _V9_SELECTION_COLUMNS:
        return []
    return [{
        "selection_state": row[0].strip().upper(),
        "selected_exact_identity": row[1].strip(),
        "comparator_exact_identity_or_terminal_state": row[2].strip(),
        "candidate_set_denominator": row[3].strip(),
        "candidate_set_hashes": re.findall(r"\b[0-9a-f]{64}\b", row[4].lower()),
        "selected_observed_metrics": row[5].strip(),
        "comparator_metrics_or_terminal_basis": row[6].strip(),
        "predeclared_selection_rule": row[7].strip(),
        "rule_evaluation": row[8].strip().upper(),
    } for row in rows if len(row) == len(header)]


def figure_spec_v10_bindings(card_md: str) -> list[dict[str, object]]:
    """Project section-18 literals for the canonical locus-map-v8 bridge."""
    body = extract_section_bodies(card_md).get(18, "")
    header, rows = _named_contract_table(body, "Figure specification")
    if tuple(_normal_header(cell) for cell in header) != _V10_FIGURE_COLUMNS:
        return []
    return [{
        "figure_state": row[0].strip().upper(),
        "exact_plotted_identity": row[1].strip(),
        "plotted_interval": row[2].strip(),
        "locus_map_hashes": re.findall(r"\b[0-9a-f]{64}\b", row[3].lower()),
        "rendered_formats": row[4].strip().upper(),
        "evidence_state_encoding": row[5].strip().upper(),
        "provenance_footer": row[7].strip().upper(),
        "lossless_sidecar": row[8].strip().upper(),
        "visual_review_hashes": re.findall(r"\b[0-9a-f]{64}\b", row[9].lower()),
        "visual_review_state": row[10].strip().upper(),
    } for row in rows if len(row) == len(header)]


def _section18_figure_spec_v10_findings(body: str) -> list[dict]:
    findings = _required_table_findings(
        body, section=18, heading="Figure specification",
        columns=_V10_FIGURE_COLUMNS, minimum_rows=1)
    for finding in findings:
        if str(finding.get("code") or "").startswith("SECTION_18_"):
            finding["code"] = "SECTION_18_V10_" + finding["code"][len("SECTION_18_"):]
    header, rows = _named_contract_table(body, "Figure specification")
    if tuple(_normal_header(cell) for cell in header) != _V10_FIGURE_COLUMNS:
        return findings
    if len(rows) != 1:
        findings.append(_finding(
            "SECTION_18_V10_ROW_COUNT", 18,
            "Figure specification requires exactly one canonical rendered-map row.",
            found=str(len(rows))))
    for row in rows:
        if len(row) != len(header):
            continue
        if row[0].strip().upper() != "FIGURE_RENDERED_REVIEWED":
            findings.append(_finding(
                "SECTION_18_V10_FIGURE_STATE_INVALID", 18,
                "Finished review requires FIGURE_RENDERED_REVIEWED.", found=row[0]))
        if not _COMPLETE_SELECTION_LOCUS.fullmatch(row[1].strip()):
            findings.append(_finding(
                "SECTION_18_V10_IDENTITY_INCOMPLETE", 18,
                "Plotted identity requires strain / full node-or-contig / region / BGC alias.",
                found=row[1]))
        interval = re.fullmatch(r"(\d+)\s*-\s*(\d+)\s+bp", row[2].strip(), re.I)
        if not interval or int(interval.group(1)) >= int(interval.group(2)):
            findings.append(_finding(
                "SECTION_18_V10_INTERVAL_INVALID", 18,
                "Plotted interval must be an ordered start-end bp range.", found=row[2]))
        if not _SHA256_RE.fullmatch(row[3].strip().lower()):
            findings.append(_finding(
                "SECTION_18_V10_LOCUS_MAP_RECEIPT_INVALID", 18,
                "Locus-map v8 receipt must be exactly one 64-hex SHA-256.", found=row[3]))
        if row[4].strip().upper() != "PNG+SVG+CSV":
            findings.append(_finding(
                "SECTION_18_V10_FORMAT_SET_INCOMPLETE", 18,
                "Rendered formats must be the exact PNG+SVG+CSV triple.", found=row[4]))
        if row[5].strip().upper() != "ENCODED_WITH_EXPLICIT_MISSING":
            findings.append(_finding(
                "SECTION_18_V10_EVIDENCE_ENCODING_INVALID", 18,
                "Evidence-state encoding must explicitly represent unavailable layers.",
                found=row[5]))
        if not (_semantic_cell(row[6], minimum_words=6)
                and re.search(r"\b(?:boundary|missing|unbound|coverage|similarity|claim|uncertain)\w*\b", row[6], re.I)):
            findings.append(_finding(
                "SECTION_18_V10_UNCERTAINTY_LABELS_MISSING", 18,
                "Name the uncertainty labels shown on the rendered figure.", found=row[6]))
        if row[7].strip().upper() != "PRESENT_PACKAGE_RELATIVE_SOURCES":
            findings.append(_finding(
                "SECTION_18_V10_PROVENANCE_FOOTER_INVALID", 18,
                "Provenance footer must declare package-relative sources.", found=row[7]))
        if row[8].strip().upper() != "VERIFIED_ALL_GENES":
            findings.append(_finding(
                "SECTION_18_V10_SIDECAR_UNVERIFIED", 18,
                "Lossless sidecar must be VERIFIED_ALL_GENES.", found=row[8]))
        if not _SHA256_RE.fullmatch(row[9].strip().lower()):
            findings.append(_finding(
                "SECTION_18_V10_VISUAL_REVIEW_RECEIPT_INVALID", 18,
                "Visual-review receipt must be exactly one 64-hex SHA-256.", found=row[9]))
        if row[10].strip().upper() != "PASS_OWNER_REVIEWED":
            findings.append(_finding(
                "SECTION_18_V10_VISUAL_REVIEW_STATE_INVALID", 18,
                "Finished review requires PASS_OWNER_REVIEWED.", found=row[10]))
    return findings


def _section2_selection_process_v9_findings(body: str) -> list[dict]:
    findings = _required_table_findings(
        body, section=2, heading="Selection process",
        columns=_V9_SELECTION_COLUMNS, minimum_rows=1)
    for finding in findings:
        if str(finding.get("code") or "").startswith("SECTION_2_"):
            finding["code"] = "SECTION_2_V9_" + finding["code"][len("SECTION_2_"):]
    header, rows = _named_contract_table(body, "Selection process")
    if tuple(_normal_header(cell) for cell in header) != _V9_SELECTION_COLUMNS:
        return findings
    if len(rows) != 1:
        findings.append(_finding(
            "SECTION_2_V9_ROW_COUNT", 2,
            "Selection process requires exactly one frozen decision row.",
            found=str(len(rows))))
    for row in rows:
        if len(row) != len(header):
            continue
        state = row[0].strip().upper()
        if state not in _V9_SELECTION_STATES:
            findings.append(_finding(
                "SECTION_2_V9_STATE_UNTYPED", 2,
                f"Selection state must be one of {sorted(_V9_SELECTION_STATES)}.",
                found=row[0]))
        selected = row[1].strip()
        if not _COMPLETE_SELECTION_LOCUS.fullmatch(selected):
            findings.append(_finding(
                "SECTION_2_V9_SELECTED_IDENTITY_INCOMPLETE", 2,
                "Selected candidate requires strain / full node-or-contig / region / BGC alias.",
                found=selected))
        try:
            denominator = int(row[3].strip())
            if denominator < 1:
                raise ValueError
        except ValueError:
            denominator = -1
            findings.append(_finding(
                "SECTION_2_V9_DENOMINATOR_INVALID", 2,
                "Frozen candidate-set denominator must be a positive integer.",
                found=row[3]))
        terminal = state == "SINGLE_CANDIDATE_SET_TYPED"
        comparator = row[2].strip()
        if terminal:
            if comparator != "NO_COMPARATOR_SINGLE_CANDIDATE_SET" or denominator != 1:
                findings.append(_finding(
                    "SECTION_2_V9_SINGLE_CANDIDATE_STATE_INVALID", 2,
                    "Single-candidate state requires its exact terminal literal and denominator 1.",
                    found=f"{comparator}; {row[3]}"))
        else:
            if not _COMPLETE_SELECTION_LOCUS.fullmatch(comparator):
                findings.append(_finding(
                    "SECTION_2_V9_COMPARATOR_IDENTITY_INCOMPLETE", 2,
                    "Comparative selection requires a complete comparator identity.",
                    found=comparator))
            elif comparator.lower() == selected.lower():
                findings.append(_finding(
                    "SECTION_2_V9_COMPARATOR_EQUALS_SELECTED", 2,
                    "Comparator must differ from the selected candidate."))
            if denominator != -1 and denominator < 2:
                findings.append(_finding(
                    "SECTION_2_V9_COMPARATIVE_DENOMINATOR_TOO_SMALL", 2,
                    "Comparative selection requires a frozen denominator of at least 2.",
                    found=row[3]))
        if not _SHA256_RE.fullmatch(row[4].strip().lower()):
            findings.append(_finding(
                "SECTION_2_V9_CANDIDATE_SET_RECEIPT_INVALID", 2,
                "Candidate-set receipt must be exactly one 64-hex SHA-256.",
                found=row[4]))
        metric_pattern = r"\b(?:score|rank|tier|coverage|identity|novelty|priority|count|value|metric)\w*\b"
        if not (_semantic_cell(row[5], minimum_words=6)
                and re.search(metric_pattern, row[5], re.I)
                and re.search(r"\d", row[5])):
            findings.append(_finding(
                "SECTION_2_V9_SELECTED_METRICS_UNMEASURED", 2,
                "Selected candidate needs named, observed and numeric ranking metrics.",
                found=row[5]))
        if terminal:
            comparator_basis_ok = (
                _semantic_cell(row[6], minimum_words=7)
                and re.search(r"\b(?:only|single)\b", row[6], re.I)
                and re.search(r"\b(?:frozen|candidate set|receipt|denominator)\b", row[6], re.I)
            )
        else:
            comparator_basis_ok = (
                _semantic_cell(row[6], minimum_words=6)
                and re.search(metric_pattern, row[6], re.I)
                and re.search(r"\d", row[6])
            )
        if not comparator_basis_ok:
            findings.append(_finding(
                "SECTION_2_V9_COMPARATOR_METRICS_OR_TERMINAL_BASIS_MISSING", 2,
                "Provide measured comparator metrics or a reasoned frozen-set terminal basis.",
                found=row[6]))
        if not (_semantic_cell(row[7], minimum_words=7)
                and re.search(r"\b(?:before|predeclared|select|priority|threshold|rank|rule)\w*\b", row[7], re.I)
                and re.search(r"\b(?:greater|higher|lower|at least|top|exceed|tie)\w*\b|[<>=]", row[7], re.I)):
            findings.append(_finding(
                "SECTION_2_V9_SELECTION_RULE_UNSPECIFIC", 2,
                "Selection rule must be predeclared and evaluable against the metrics.",
                found=row[7]))
        if row[8].strip().upper() not in {"RULE_MET", "RULE_NOT_MET_HELD", "SINGLE_CANDIDATE_TERMINAL"}:
            findings.append(_finding(
                "SECTION_2_V9_RULE_EVALUATION_INVALID", 2,
                "Rule evaluation must use the controlled decision state.", found=row[8]))
        if terminal and row[8].strip().upper() != "SINGLE_CANDIDATE_TERMINAL":
            findings.append(_finding(
                "SECTION_2_V9_TERMINAL_EVALUATION_MISMATCH", 2,
                "Single-candidate selection requires SINGLE_CANDIDATE_TERMINAL."))
        if not (_semantic_cell(row[9], minimum_words=8)
                and re.search(r"\binformation\b", row[9], re.I)
                and re.search(r"\b(?:only|bounded|candidate|does not|uncertain|hypothesis)\b", row[9], re.I)):
            findings.append(_finding(
                "SECTION_2_V9_INFORMATION_GAIN_UNBOUNDED", 2,
                "State a bounded information-gain reason without converting priority into merit.",
                found=row[9]))
        if not _discriminating_action_cell(row[10]):
            findings.append(_finding(
                "SECTION_2_V9_NEXT_ACTION_UNSPECIFIC", 2,
                "Next action must name a discriminating analysis or experiment and readout.",
                found=row[10]))
    return findings


def _section_inventory_reconciliation_v8_findings(
        section: int, body: str,
        canonical_loci: Optional[Iterable[str]]) -> list[dict]:
    states, role_pattern = _V8_INVENTORY_PROFILES[section]
    findings = _required_table_findings(
        body, section=section, heading="Inventory reconciliation",
        columns=_V8_INVENTORY_COLUMNS, minimum_rows=1)
    for finding in findings:
        prefix = f"SECTION_{section}_"
        if str(finding.get("code") or "").startswith(prefix):
            finding["code"] = prefix + "V8_" + finding["code"][len(prefix):]
    header, rows = _named_contract_table(body, "Inventory reconciliation")
    if tuple(_normal_header(cell) for cell in header) != _V8_INVENTORY_COLUMNS:
        return findings
    expected = ({str(item).strip() for item in canonical_loci if str(item).strip()}
                if canonical_loci is not None else None)
    if expected is None:
        findings.append(_finding(
            f"SECTION_{section}_V8_CANONICAL_ROSTER_UNBOUND", section,
            "Inventory reconciliation requires an independently supplied canonical roster."))
    measured_rows: list[list[str]] = []
    zero_rows: list[list[str]] = []
    denominators: list[int] = []
    members: list[str] = []
    for index, row in enumerate(rows, 1):
        if len(row) != len(header):
            continue
        state = row[0].strip().upper()
        if state not in states:
            findings.append(_finding(
                f"SECTION_{section}_V8_STATE_UNTYPED", section,
                f"Inventory row {index} needs one of {sorted(states)}.", found=row[0]))
        terminal = state.endswith("_TYPED")
        member = row[1].strip().strip("`")
        if terminal:
            zero_rows.append(row)
            if member != "TYPED_ZERO":
                findings.append(_finding(
                    f"SECTION_{section}_V8_TYPED_ZERO_INVALID", section,
                    "A typed-zero state requires the exact TYPED_ZERO member literal.", found=row[1]))
        else:
            measured_rows.append(row)
            if not _LOCUS.fullmatch(member):
                findings.append(_finding(
                    f"SECTION_{section}_V8_MEMBER_IDENTITY_INVALID", section,
                    "Each measured inventory row requires exactly one locus tag.", found=row[1]))
            else:
                members.append(member)
                if expected is not None and member not in expected:
                    findings.append(_finding(
                        f"SECTION_{section}_V8_MEMBER_OUTSIDE_ROSTER", section,
                        "Every inventory member must occur in the canonical roster.", found=member))
        if not (_semantic_cell(row[2], minimum_words=2)
                and re.search(role_pattern, row[2], re.I)):
            findings.append(_finding(
                f"SECTION_{section}_V8_ROLE_UNTYPED", section,
                "The role must use section-specific observational vocabulary.", found=row[2]))
        if not _SHA256_RE.fullmatch(row[3].strip().lower()):
            findings.append(_finding(
                f"SECTION_{section}_V8_RECEIPT_INVALID", section,
                "Evidence receipt must be exactly one 64-hex SHA-256.", found=row[3]))
        try:
            denominator = int(row[4].strip())
            if denominator < 0:
                raise ValueError
            denominators.append(denominator)
        except ValueError:
            findings.append(_finding(
                f"SECTION_{section}_V8_DENOMINATOR_INVALID", section,
                "The declared denominator must be a nonnegative integer.", found=row[4]))
        if row[5].strip().upper() not in {
            "OBSERVED_SOURCE_BOUND", "INFERRED_SOURCE_BOUND",
            "UNRESOLVED_SOURCE_BOUND", "MEASURED_ZERO_SOURCE_BOUND",
        }:
            findings.append(_finding(
                f"SECTION_{section}_V8_EVIDENCE_STATE_INVALID", section,
                "Evidence state must distinguish observed, inferred, unresolved, or measured zero.", found=row[5]))
        if terminal and row[5].strip().upper() != "MEASURED_ZERO_SOURCE_BOUND":
            findings.append(_finding(
                f"SECTION_{section}_V8_ZERO_EVIDENCE_STATE_MISMATCH", section,
                "Typed zero requires MEASURED_ZERO_SOURCE_BOUND.", found=row[5]))
        if not (_semantic_cell(row[6], minimum_words=6)
                and re.search(r"\b(?:limitation|incomplete|uncertain|missing|bias|cannot|unresolved|alternative)\w*\b", row[6], re.I)):
            findings.append(_finding(
                f"SECTION_{section}_V8_LIMITATION_MISSING", section,
                "Every inventory row needs a substantive limitation.", found=row[6]))
        if row[7].strip().upper() != "EXACT_MATCH":
            findings.append(_finding(
                f"SECTION_{section}_V8_RECONCILIATION_NOT_EXACT", section,
                "Inventory reconciliation state must be EXACT_MATCH.", found=row[7]))
    if measured_rows and zero_rows:
        findings.append(_finding(
            f"SECTION_{section}_V8_ZERO_MEMBER_MIXED", section,
            "Typed-zero and measured-member rows are mutually exclusive."))
    if len(zero_rows) > 1:
        findings.append(_finding(
            f"SECTION_{section}_V8_ZERO_ROW_COUNT", section,
            "A typed-zero inventory must contain exactly one row.", found=str(len(zero_rows))))
    if len(members) != len(set(members)):
        findings.append(_finding(
            f"SECTION_{section}_V8_MEMBER_DUPLICATE", section,
            "Measured inventory members must be unique."))
    if denominators and len(set(denominators)) != 1:
        findings.append(_finding(
            f"SECTION_{section}_V8_DENOMINATOR_CONFLICT", section,
            "Every row must carry one common inventory denominator."))
    if denominators:
        expected_count = 0 if zero_rows and not measured_rows else len(set(members))
        if denominators[0] != expected_count:
            findings.append(_finding(
                f"SECTION_{section}_V8_DENOMINATOR_MISMATCH", section,
                "The denominator must equal the displayed unique-member count.",
                found=f"{denominators[0]} != {expected_count}"))
    return findings


def _section_claim_model_v7_findings(section: int, body: str,
                                      canonical_loci: Optional[Iterable[str]]) -> list[dict]:
    states, object_pattern = _V7_PROFILES[section]
    findings = _required_table_findings(body, section=section, heading="Semantic claim model",
                                        columns=_V7_CLAIM_MODEL_COLUMNS, minimum_rows=1)
    for finding in findings:
        prefix = f"SECTION_{section}_"
        if str(finding.get("code") or "").startswith(prefix):
            finding["code"] = prefix + "V7_" + finding["code"][len(prefix):]
    header, rows = _named_contract_table(body, "Semantic claim model")
    if tuple(_normal_header(cell) for cell in header) != _V7_CLAIM_MODEL_COLUMNS:
        return findings
    expected = ({str(item).strip() for item in canonical_loci if str(item).strip()}
                if canonical_loci is not None else None)
    if expected is None:
        findings.append(_finding(f"SECTION_{section}_V7_CANONICAL_ROSTER_UNBOUND", section,
                                 "The claim model requires an independently supplied canonical roster."))
    for index, row in enumerate(rows, 1):
        if len(row) != len(header):
            continue
        state = row[0].strip().upper()
        if state not in states:
            findings.append(_finding(f"SECTION_{section}_V7_STATE_UNTYPED", section,
                                     f"Claim-model row {index} needs one of {sorted(states)}.", found=row[0]))
        targets = set(_LOCUS.findall(row[1]))
        if not (_semantic_cell(row[1], minimum_words=4) and targets and re.search(object_pattern, row[1], re.I)):
            findings.append(_finding(f"SECTION_{section}_V7_OBJECT_UNTYPED", section,
                                     "The scientific object must name an exact in-roster gene and a section-specific object.", found=row[1]))
        if expected is not None and not targets.issubset(expected):
            findings.append(_finding(f"SECTION_{section}_V7_TARGET_OUTSIDE_ROSTER", section,
                                     "Every claim-model locus must occur in the canonical roster.", found=", ".join(sorted(targets - expected))))
        terminal = state.endswith("_TYPED")
        basis = row[2]
        basis_ok = _semantic_cell(basis, minimum_words=8)
        if terminal:
            basis_ok = bool(basis_ok and re.search(r"\b(?:unavailable|missing|not run|unbound|insufficient)\b", basis, re.I)
                            and re.search(r"\b(?:source|receipt|package|denominator|reason)\w*\b", basis, re.I))
        else:
            basis_ok = bool(basis_ok and re.search(r"\b(?:measur|observ|result|identity|coverage|synteny|assay|cohort|numerator|denominator)\w*\b", basis, re.I)
                            and re.search(r"\d", basis))
        if section == 44 and state == "PREVALENCE_MEASURED":
            basis_ok = bool(basis_ok and (re.search(r"\d+\s*/\s*\d+|\d+\s+of\s+\d+", basis, re.I)
                                          or (re.search(r"numerator", basis, re.I) and re.search(r"denominator", basis, re.I))))
        if not basis_ok:
            findings.append(_finding(f"SECTION_{section}_V7_EVIDENCE_OR_TERMINAL_BASIS_MISSING", section,
                                     "The claim model needs a measured result or source-bearing terminal basis.", found=basis))
        if not (_semantic_cell(row[3], minimum_words=6) and re.search(r"\b(?:against|limitation|conflict|failure|incomplete|background|artifact|artefact|bias|uncertain|alternative)\w*\b", row[3], re.I)):
            findings.append(_finding(f"SECTION_{section}_V7_EVIDENCE_AGAINST_MISSING", section,
                                     "Evidence against or limitation must be substantive.", found=row[3]))
        if _normal_header(row[2]) == _normal_header(row[3]):
            findings.append(_finding(f"SECTION_{section}_V7_EVIDENCE_COLLAPSED", section,
                                     "Evidence for and against must be distinct."))
        if not _SHA256_RE.fullmatch(row[4].strip().lower()):
            findings.append(_finding(f"SECTION_{section}_V7_RECEIPT_INVALID", section,
                                     "Evidence receipt must be exactly one 64-hex SHA-256.", found=row[4]))
        if not (_semantic_cell(row[5], minimum_words=6) and re.search(r"\b(?:only|cannot|not establish|unresolved|candidate|hypothesis)\b", row[5], re.I) and re.search(object_pattern, row[5], re.I)):
            findings.append(_finding(f"SECTION_{section}_V7_CLAIM_UNBOUNDED", section,
                                     "The narrowest claim must be bounded and section-specific.", found=row[5]))
        if not (_semantic_cell(row[6], minimum_words=8) and re.search(r"\b(?:compare|search|align|measure|sequence|culture|assay|profile|quantif|test)\w*\b", row[6], re.I) and re.search(r"\b(?:result|readout|identity|coverage|feature|hit|support|ratio|count|inhibition)\w*\b", row[6], re.I)):
            findings.append(_finding(f"SECTION_{section}_V7_RESOLVING_ACTION_UNSPECIFIC", section,
                                     "The resolving comparison or assay needs an action and measured readout.", found=row[6]))
        if not (_semantic_cell(row[7], minimum_words=7) and re.search(r"\b(?:if|when|result|outcome)\b", row[7], re.I) and re.search(r"\b(?:retain|reject|hold|revise|narrow|remove|deprioriti[sz]e)\w*\b", row[7], re.I)):
            findings.append(_finding(f"SECTION_{section}_V7_CLAIM_CONSEQUENCE_MISSING", section,
                                     "The result must explicitly retain, reject, hold, or revise the claim.", found=row[7]))
    return findings


def _section_decision_chain_v6_findings(
        section: int, body: str,
        canonical_loci: Optional[Iterable[str]]) -> list[dict]:
    """Apply one shared decision-chain schema with section-specific object profiles."""
    states, object_pattern = _V6_PROFILES[section]
    findings = _required_table_findings(
        body, section=section, heading="Semantic decision chain",
        columns=_V6_DECISION_CHAIN_COLUMNS, minimum_rows=1,
    )
    for finding in findings:
        prefix = f"SECTION_{section}_"
        if str(finding.get("code") or "").startswith(prefix):
            finding["code"] = prefix + "V6_" + finding["code"][len(prefix):]
    header, rows = _named_contract_table(body, "Semantic decision chain")
    if tuple(_normal_header(cell) for cell in header) != _V6_DECISION_CHAIN_COLUMNS:
        return findings
    expected = ({str(item).strip() for item in canonical_loci if str(item).strip()}
                if canonical_loci is not None else None)
    if expected is None:
        findings.append(_finding(
            f"SECTION_{section}_V6_CANONICAL_ROSTER_UNBOUND", section,
            "The decision chain cannot be certified without an independently supplied canonical roster.",
        ))
    for index, row in enumerate(rows, 1):
        if len(row) != len(header):
            continue
        state = row[0].strip().upper()
        if state not in states:
            findings.append(_finding(
                f"SECTION_{section}_V6_STATE_UNTYPED", section,
                f"Decision-chain row {index} needs one of {sorted(states)}.", found=row[0],
            ))
        targets = set(_LOCUS.findall(row[1]))
        if not (_semantic_cell(row[1], minimum_words=4)
                and targets and re.search(object_pattern, row[1], re.I)):
            findings.append(_finding(
                f"SECTION_{section}_V6_OBJECT_UNTYPED", section,
                "The exact target/measured object must name an in-roster gene and this section's scientific object.",
                found=row[1],
            ))
        if expected is not None and not targets.issubset(expected):
            findings.append(_finding(
                f"SECTION_{section}_V6_TARGET_OUTSIDE_ROSTER", section,
                "Every locus tag in the decision object must occur in the independently supplied canonical roster.",
                found=", ".join(sorted(targets - expected)),
            ))
        terminal = state.endswith("_TYPED")
        if terminal:
            valid_basis = (
                _semantic_cell(row[2], minimum_words=8)
                and re.search(r"\b(?:not run|unavailable|missing|unbound|absent|no exact|insufficient)\b", row[2], re.I)
                and re.search(r"\b(?:source|receipt|package|roster|reason|because|denominator)\w*\b", row[2], re.I)
            )
        else:
            valid_basis = (
                _semantic_cell(row[2], minimum_words=8)
                and re.search(r"\b(?:measur|observ|result|identity|coverage|mass|m/z|hit|support|synteny|boundary|construct)\w*\b", row[2], re.I)
                and bool(re.search(r"\d|sha[- ]?256|receipt", row[2], re.I))
            )
        if not valid_basis:
            findings.append(_finding(
                f"SECTION_{section}_V6_EVIDENCE_OR_TERMINAL_BASIS_MISSING", section,
                "The row needs a measured result or a reasoned, source-bearing terminal basis.",
                found=row[2],
            ))
        if not (_semantic_cell(row[3], minimum_words=6)
                and re.search(r"\b(?:alternative|limitation|conflict|failure|incomplete|background|artefact|artifact|bias|uncertain|different)\w*\b", row[3], re.I)):
            findings.append(_finding(
                f"SECTION_{section}_V6_ALTERNATIVE_OR_LIMITATION_MISSING", section,
                "The row must name a substantive alternative, limitation, or failure mode.",
                found=row[3],
            ))
        if _normal_header(row[2]) == _normal_header(row[3]):
            findings.append(_finding(
                f"SECTION_{section}_V6_EVIDENCE_ALTERNATIVE_COLLAPSED", section,
                "Evidence/terminal basis and alternative/limitation must be distinct.",
            ))
        if not _bounded_inference_cell(row[4]):
            findings.append(_finding(
                f"SECTION_{section}_V6_ALLOWED_INFERENCE_UNBOUNDED", section,
                "The decision chain needs an explicit bounded inference.", found=row[4],
            ))
        if not (
            _semantic_cell(row[5], minimum_words=9)
            and re.search(r"\b(?:align|compare|search|sequence|profile|clone|express|culture|assay|LC[-– ]?MS|MS/MS|phylogen|delete|perturb|map)\w*\b", row[5], re.I)
            and re.search(r"\b(?:measure|result|readout|identity|coverage|mass|feature|hit|support|topology|boundary|synteny)\w*\b", row[5], re.I)
        ):
            findings.append(_finding(
                f"SECTION_{section}_V6_RESOLVING_ACTION_UNSPECIFIC", section,
                "The resolving action must name an analysis/experiment and its measurable or computed result.",
                found=row[5],
            ))
        if not (
            _semantic_cell(row[6], minimum_words=7)
            and re.search(r"\b(?:if|when|only if|result|outcome)\b", row[6], re.I)
            and re.search(r"\b(?:retain|reject|hold|advance|revise|remove|deprioriti[sz]e)\w*\b", row[6], re.I)
        ):
            findings.append(_finding(
                f"SECTION_{section}_V6_DECISION_CONSEQUENCE_MISSING", section,
                "The row must state how the measured result retains, rejects, holds, or revises a model.",
                found=row[6],
            ))
    return findings


def publication_quality_findings(
        card_md: str,
        canonical_loci: Optional[Iterable[str]] = None,
        *,
        check_substantive_quality_v2: bool = False,
        check_semantic_sections_v3: bool = False,
        check_semantic_comparators_v4: bool = False,
        check_semantic_sections_v5: bool = False,
        check_semantic_decision_chains_v6: bool = False,
        check_semantic_claim_models_v7: bool = False,
        check_inventory_reconciliation_v8: bool = False,
        check_selection_process_v9: bool = False,
        check_figure_spec_v10: bool = False,
        check_reconciliation_specificity_v11: bool = False) -> list[dict]:
    """Return ERROR findings for an expanded owner-review candidate.

    ``check_substantive_quality_v2`` enables the prospective structured
    requirements for §26 (pathway-grounded OSMAC), §46 (type/reference
    comparison), and §47 (host-matched comparison). It is deliberately
    opt-in: the pre-v2 finished-card population predates these exact tables,
    so silently enabling them would turn a quality improvement into a
    retroactive migration event. The verifier exposes the opt-in explicitly.

    ``check_semantic_sections_v3`` separately enables structured §10, §12,
    §17 and §24 checks. It is a distinct opt-in so the published v2 switch
    does not silently acquire a broader migration meaning.

    ``check_semantic_comparators_v4`` separately rejects nonempty-but-vacuous
    §6/§45/§46/§47 anchor and comparison cells. It remains opt-in so neither
    v2 nor v3 silently changes meaning.

    ``check_semantic_sections_v5`` separately requires typed, cross-checkable
    decision objects in §15/§19/§29/§31/§43. It remains opt-in because the
    existing finished-card population predates these exact schemas.

    ``check_semantic_decision_chains_v6`` applies one shared evidence-to-decision
    schema to the eight high-consequence sections with a demonstrated bypass.
    It remains opt-in and does not broaden to inventory/presentation sections.
    """
    bodies = extract_section_bodies(card_md)
    findings: list[dict] = []
    missing_sections = [n for n in range(1, 49) if n not in bodies]
    if missing_sections:
        findings.append(_finding(
            "PUBLICATION_SECTIONS_INCOMPLETE", None,
            "Expanded Mode B requires §1–§48 in exact order; use reasoned NOT_APPLICABLE, not omission.",
            found=", ".join(map(str, missing_sections)),
        ))
    findings.extend(_contiguous_homology_table_findings(bodies.get(4, ""), canonical_loci))
    findings.extend(_scientific_scaffold_findings(bodies))
    findings.extend(_gene_orientation_findings(bodies, canonical_loci))
    if check_substantive_quality_v2:
        findings.extend(_alternatives_boundary_next_action_findings(bodies))
        findings.extend(_section26_findings(bodies.get(26, "")))
    findings.extend(_section27_findings(bodies.get(27, ""), canonical_loci))
    findings.extend(_section45_findings(bodies.get(45, ""), canonical_loci))
    if check_substantive_quality_v2:
        findings.extend(_section46_findings(bodies.get(46, ""), canonical_loci))
        findings.extend(_section47_findings(bodies.get(47, ""), canonical_loci))
    if check_semantic_sections_v3:
        findings.extend(_section10_findings(bodies.get(10, "")))
        findings.extend(_section12_findings(bodies.get(12, "")))
        findings.extend(_section17_findings(bodies.get(17, ""), canonical_loci))
        findings.extend(_section24_findings(bodies.get(24, "")))
    if check_semantic_comparators_v4:
        findings.extend(_section6_semantic_v4_findings(bodies.get(6, ""), canonical_loci))
        findings.extend(_section45_semantic_v4_findings(bodies.get(45, "")))
        findings.extend(_section46_semantic_v4_findings(bodies.get(46, "")))
        findings.extend(_section47_semantic_v4_findings(bodies.get(47, "")))
    if check_semantic_sections_v5:
        findings.extend(_section15_semantic_v5_findings(bodies.get(15, "")))
        findings.extend(_section19_semantic_v5_findings(
            bodies.get(19, ""), bodies.get(20, "")))
        findings.extend(_section29_semantic_v5_findings(bodies.get(29, "")))
        findings.extend(_section31_semantic_v5_findings(
            bodies.get(31, ""), canonical_loci))
        findings.extend(_section43_semantic_v5_findings(bodies.get(43, "")))
    if check_semantic_decision_chains_v6:
        for section in _V6_PROFILES:
            findings.extend(_section_decision_chain_v6_findings(
                section, bodies.get(section, ""), canonical_loci))
    if check_semantic_claim_models_v7:
        for section in _V7_PROFILES:
            findings.extend(_section_claim_model_v7_findings(
                section, bodies.get(section, ""), canonical_loci))
    if check_inventory_reconciliation_v8:
        for section in _V8_INVENTORY_PROFILES:
            findings.extend(_section_inventory_reconciliation_v8_findings(
                section, bodies.get(section, ""), canonical_loci))
    if check_selection_process_v9:
        findings.extend(_section2_selection_process_v9_findings(bodies.get(2, "")))
    if check_figure_spec_v10:
        findings.extend(_section18_figure_spec_v10_findings(bodies.get(18, "")))
    findings.extend(_repeated_generic_sentence_findings(bodies))
    stream_rows = _table_rows(_named_heading_block(card_md, "Evidence-stream disposition"))
    history_rows = _table_rows(_named_heading_block(card_md, "Historical source-loss reconciliation"))
    section_rows = _table_rows(_named_heading_block(
        card_md, "Section-by-section completeness and predecessor reconciliation"))
    findings.extend(_stream_findings(stream_rows))
    findings.extend(_history_findings(history_rows))
    findings.extend(_section_matrix_findings(section_rows))
    if check_reconciliation_specificity_v11:
        findings.extend(_section_matrix_specificity_v11_findings(section_rows))
    # v9.7.412 (SURFACE-412): surface integrity of the authored card.
    findings.extend(_word_number_spacing_findings(card_md))
    findings.extend(_governed_term_findings(card_md))
    findings.extend(_table_separator_findings(card_md))
    findings.extend(_section_disposition_uniform_findings(card_md))
    return findings
