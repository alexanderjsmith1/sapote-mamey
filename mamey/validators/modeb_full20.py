"""Canonical prose-first Full Mode B §1–§20 validator.

The current contract is intentionally stricter than the older §1–§8 and
§1–§10+enrichment language. Full Mode B now means the exact §1–§20 titles
from the corrective protocol. LLMs/renderers must not invent, rename, reorder,
or substitute section headings. Evidence tables support the card; they do not
replace the prose-first scientific interpretation.

Source of truth (N10 / W9-C, v9.7.150e+):
    `mamey/data/mode_b/modeb_full30_corrective_contract.json` is the **single**
    canonical contract. This module derives its §1–§20 subset from that file
    via `mamey.modeb_structure_gate.load_contract()` rather than carrying its
    own copy. The standalone `modeb_full20_corrective_contract.json` has been
    retired; the hard-coded fallback list previously embedded in this module
    has been replaced with a derivation from `modeb_structure_gate`'s small
    safety-net fallback so the schema lives in exactly one place.

    Why a separate module still exists: `directed_pks_study.py` and the
    artifact-drift / obsolete-heading diagnostics here are §1–§20-specific
    and not duplicated in `modeb_structure_gate.lint_card()`. Keep this as
    the §1–§20 facade; `modeb_structure_gate` is the §1–§48 enforcer.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


def _load_contract() -> dict[str, Any]:
    """Return a §1–§20 view of the canonical §1–§48 contract.

    Reads from `mamey.modeb_structure_gate.load_contract()` (the single
    source of truth) and slices to the §1–§20 always-required sections.
    Falls back to an empty-failsafe schema only if the structure gate
    itself fails to load — in which case the import-time guard below
    will raise, surfacing the bundle-integrity issue immediately.
    """
    try:
        from ..modeb_structure_gate import load_contract as _load_full30
        full30 = _load_full30()
        slim = [
            {"number": s["number"], "title": s["title"]}
            for s in full30.get("sections", [])
            if s.get("number") and 1 <= int(s["number"]) <= 20
        ]
        slim.sort(key=lambda s: s["number"])
        return {"sections": slim, "derived_from": full30.get("schema_version")}
    except Exception:
        # The import-time guard below will catch this and raise — we don't
        # want a silent fallback that drifts from the canonical contract.
        return {"sections": []}


MODEB_FULL20_CONTRACT = _load_contract()
REQUIRED_MODEB_FULL20_SECTIONS = [str(s["title"]) for s in MODEB_FULL20_CONTRACT.get("sections", [])]

if len(REQUIRED_MODEB_FULL20_SECTIONS) != 20:  # pragma: no cover - import-time release guard
    raise RuntimeError(
        f"Mode B contract must define exactly 20 §1–§20 sections; found "
        f"{len(REQUIRED_MODEB_FULL20_SECTIONS)}. This typically means "
        f"`mamey/data/mode_b/modeb_full30_corrective_contract.json` is "
        f"missing, malformed, or has lost a required §1–§20 entry. The "
        f"§1–§20 subset is derived from that file by "
        f"`mamey.modeb_structure_gate.load_contract()`.")

# Older headings are intentionally *not* aliases. They are rejection examples.
# This list is used only to produce more helpful diagnostics.
OBSOLETE_OR_INVENTED_SECTION_TITLES = {
    "Stable identity and node-first locator",
    "BGC class and antiSMASH call",
    "Assembly / boundary status",
    "Gene-by-gene architecture",
    "Core domain architecture",
    "Comparator / KCB / MIBiG evidence",
    "Manual BLASTP evidence, if present",
    "Functional grouping context",
    "Biosynthetic logic and predicted chemical space",
    "Antifungal relevance",
    "Bee-microbe ecological relevance",
    "Fragmentation risks and non-merge warnings",
    "Exclusion / background-control logic, if applicable",
    "Citation status ledger",
    "Wet-lab LC-HRMS/DAD expectations",
    "Genetic validation options",
    "Dereplication risks",
    "Figure-ready locus map notes",
    "Final interpretation_scope statement",
    "Next evidence needed",
}


@dataclass(frozen=True)
class Full20Validation:
    ok: bool
    missing: list[str]
    present_numbers: list[int]
    message: str
    artifact_drift: list[str]
    invented_or_obsolete_sections: list[str]


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _heading_lines(markdown_text: str) -> list[str]:
    lines: list[str] = []
    for raw in (markdown_text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#") or line.startswith("§") or re.match(r"^(?:\*\*)?\s*(?:§\s*)?\d{1,2}\s*[.)—:-]", line):
            lines.append(line.strip("* "))
    return lines


def _extract_section_heading(markdown_text: str, index: int) -> str | None:
    # Accept Markdown heading markers, bold heading markers, or bare numbered section lines.
    pat = re.compile(
        rf"(?im)^\s*(?:#+\s*)?(?:\*\*)?\s*(?:§\s*)?{index}\s*[.)—:\-]\s*(.+?)\s*(?:\*\*)?\s*$"
    )
    match = pat.search(markdown_text or "")
    if match:
        return match.group(1).strip().strip("#* ")
    return None


def _section_present(markdown_text: str, index: int, title: str) -> bool:
    heading = _extract_section_heading(markdown_text, index)
    return bool(heading and _norm(heading) == _norm(title))


def _section_body(markdown_text: str, index: int) -> str:
    text = markdown_text or ""
    start_pat = re.compile(rf"(?im)^\s*(?:#+\s*)?(?:\*\*)?\s*(?:§\s*)?{index}\s*[.)—:\-].*$")
    end_pat = re.compile(rf"(?im)^\s*(?:#+\s*)?(?:\*\*)?\s*(?:§\s*)?{index + 1}\s*[.)—:\-].*$")
    start = start_pat.search(text)
    if not start:
        return ""
    end = end_pat.search(text, start.end())
    return text[start.end(): end.start() if end else len(text)]


def present_section_numbers(markdown_text: str) -> set[int]:
    return {i for i, title in enumerate(REQUIRED_MODEB_FULL20_SECTIONS, start=1) if _section_present(markdown_text, i, title)}


def missing_modeb_sections(markdown_text: str) -> list[str]:
    present = present_section_numbers(markdown_text)
    return [f"§{i} — {title}" for i, title in enumerate(REQUIRED_MODEB_FULL20_SECTIONS, start=1) if i not in present]


def invented_or_obsolete_sections(markdown_text: str) -> list[str]:
    found: list[str] = []
    allowed = {_norm(s) for s in REQUIRED_MODEB_FULL20_SECTIONS}
    obsolete = {_norm(s): s for s in OBSOLETE_OR_INVENTED_SECTION_TITLES}
    for index in range(1, 21):
        heading = _extract_section_heading(markdown_text or "", index)
        if not heading:
            continue
        hnorm = _norm(heading)
        if hnorm not in allowed:
            label = obsolete.get(hnorm, heading)
            found.append(f"§{index} — {label}")
    # Do not scan arbitrary prose for old titles: phrases such as "Antifungal
    # relevance" can be substrings of current headings. Obsolete detection is
    # intentionally heading-based so current section titles are not penalized.
    return sorted(set(found))


def _non_table_word_count(body: str) -> int:
    words: list[str] = []
    for line in (body or "").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("|") or re.match(r"^[-:| ]+$", stripped):
            continue
        words.extend(re.findall(r"[A-Za-z][A-Za-z0-9_/-]*", stripped))
    return len(words)


def artifact_drift_issues(markdown_text: str) -> list[str]:
    """Return blocking issues for compliance-looking but non-card artifacts.

    These are intentionally conservative heuristics. They catch the failure mode
    where an LLM ships tables/PDF/progress accounting while calling it a Mode B
    card. They do not attempt to judge scientific correctness.
    """
    issues: list[str] = []
    text = markdown_text or ""

    body4 = _section_body(text, 4)
    if _section_present(text, 4, REQUIRED_MODEB_FULL20_SECTIONS[3]):
        table_lines = sum(1 for line in body4.splitlines() if line.strip().startswith("|"))
        prose_words = _non_table_word_count(body4)
        if table_lines >= 3 and prose_words < 35:
            issues.append("SECTION_4_TABLE_ONLY: §4 must contain prose gene-by-gene interpretation; evidence tables are appendices/supporting material.")

    # Progress-accounting tables are allowed in a report package, but not as the
    # body of a card. If the whole document is dominated by Before/After/Delta
    # accounting and lacks section prose, call it out.
    accounting_terms = sum(text.lower().count(term) for term in ("before chars", "after chars", "delta", "character count"))
    if accounting_terms >= 3 and len(present_section_numbers(text)) < 20:
        issues.append("PROGRESS_ACCOUNTING_ONLY: character counts/progress tables are not Mode B acceptance evidence.")

    # BLASTP/HMMER is allowed at §16. If the heading of §7 contains BLASTP/HMMER,
    # the card is following the old/invented schema.
    heading7 = _extract_section_heading(text, 7) or ""
    if re.search(r"\bblastp\b|\bhmmer\b", heading7, re.I):
        issues.append("BLASTP_SECTION_DRIFT: BLASTP/HMMER belongs in §16, not §7.")

    return issues


def validate_modeb_card(markdown_text: str) -> bool:
    return validate_full20(markdown_text).ok


def validate_full20(markdown_text: str) -> Full20Validation:
    missing = missing_modeb_sections(markdown_text)
    present = sorted(present_section_numbers(markdown_text))
    drift = artifact_drift_issues(markdown_text)
    invented = invented_or_obsolete_sections(markdown_text)
    ok = not missing and not drift and not invented
    if ok:
        msg = "FULL20 PASS"
    else:
        parts = []
        if missing:
            parts.append(f"missing {len(missing)} section(s)")
        if invented:
            parts.append(f"obsolete/invented section heading(s): {len(invented)}")
        if drift:
            parts.append(f"artifact-drift issue(s): {len(drift)}")
        msg = "FULL20 FAIL: " + "; ".join(parts)
    return Full20Validation(
        ok=ok,
        missing=missing,
        present_numbers=present,
        message=msg,
        artifact_drift=drift,
        invented_or_obsolete_sections=invented,
    )
