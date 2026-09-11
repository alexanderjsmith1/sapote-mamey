"""modeb_structure_gate.py — structural validator for prose-first Mode B cards.

The motivating failure (v9.7.150, BGC033 case):
    A chat session authored a Mode B card against the historical §1–§10
    scaffold (Identity / Assembly / Forensic sweep / §11–20 enrichment)
    rather than the current §1–§48 contract. The wrong-scaffold card was
    structurally invalid but `record_mode_b()` accepted it silently because
    no code-level structure check existed — only "file is non-empty."

    The team had already documented this exact recurrence mode in
    `docs/ISSUES_EXPERIENCED_DURING_DEVELOPMENT.md:521` — "A chat that
    reads the contract but doesn't reach the §9 and §16 overrides in the
    619-line execution slice will conclude §1–§20 is the complete spec."

This module is the firebreak. It reads the canonical contract JSON,
validates a card's section headings against §1–§48 with conditional
predicates evaluated against a BGC context, and surfaces structured
findings. Wired into the three ingest paths so a misshapen card is
refused by default (with --force escape valve, like claim_safety_gate).

Public API:
    load_contract(path=None) -> dict
    extract_section_titles(card_md) -> list[(int, str)]
    lint_card(card_md, bgc_context=None) -> list[Finding]
    summarise(findings) -> str

A Finding is a dict:
    {"severity": "ERROR" | "WARN",
     "code": <stable string>,
     "section": <int|None>,
     "expected": <str|None>,
     "found": <str|None>,
     "message": <human one-liner>}

Severities:
    ERROR — gate refuses by default (override: --force)
    WARN  — gate proceeds, prints to stderr

W9 / structure-gate (v9.7.150+).
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path
if __package__:
    from .bigscape_namespace import NamespaceError, normalize_cutoff, normalize_run_id, parse_family_identity
else:  # compatibility for the historical direct-file import used by lint owners
    from mamey.bigscape_namespace import NamespaceError, normalize_cutoff, normalize_run_id, parse_family_identity
from typing import Any, Iterable, Optional

# Default contract path (relative to this module).
_CONTRACT_PATH = (Path(__file__).parent / "data" / "mode_b"
                  / "modeb_full30_corrective_contract.json")


# ---------------------------------------------------------------------------
# Contract loading
# ---------------------------------------------------------------------------

def load_contract(path: Optional[str | Path] = None) -> dict:
    """Load the canonical Mode B contract JSON. Defaults to the bundled
    `mamey/data/mode_b/modeb_full30_corrective_contract.json`.

    Raises FileNotFoundError if the contract is missing. Raises ValueError
    if the contract is malformed. (Callers — gates, emitters — should NOT
    silently degrade to a hard-coded fallback; a missing contract is a
    bundle-integrity failure that should surface.)
    """
    p = Path(path) if path else _CONTRACT_PATH
    if not p.exists():
        raise FileNotFoundError(
            f"Mode B contract not found at {p}. "
            "This is a bundle-integrity failure: the §1–§48 canonical "
            "contract JSON is missing or relocated."
        )
    try:
        contract = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"Contract JSON at {p} is malformed: {e}") from e
    if "sections" not in contract or not contract["sections"]:
        raise ValueError(f"Contract JSON at {p} has no sections list.")
    return contract


# ---------------------------------------------------------------------------
# Card parsing — extract section headings from markdown
# ---------------------------------------------------------------------------

# Tolerates these heading forms (the contract numbering is what matters,
# not the exact markdown level — `##`, `###`, `**§N**`, `## §N — Title`,
# `## N. Title`, `## Section N: Title` all parse):
#
#   "## §1 Identity and node/region"
#   "## §1 — Identity and node/region"
#   "### §1: Identity and node/region"
#   "## 1. Identity and node/region"
#   "## Section 1 — Identity and node/region"
#   "**§1 Identity and node/region**"
#
# The number is the canonical reference; the title is matched
# case-insensitively against the contract.
#
# v9.7.410: the last three forms above carry NO `§`/`Section ` marker, so on their own
# they are indistinguishable from prose (`§12 ecological context …`) or from a numbered
# subsection (`### 2. Committed-step core`). They are still accepted, but only when the
# title IS the canonical contract title for that number — see `_iter_headings`.
# v9.7.410 (MODEB-GATE-410): the prefix alternation is SPLIT into named groups so the
# admission rule in `_iter_headings` can tell a SELF-IDENTIFYING heading (`##` / `**`
# PLUS an explicit `§` / `Section ` marker — unambiguous, admitted on its number alone)
# from a MARKER-LESS one (`### 2. Committed-step core`, or a bare `§12 …` / `Section 5 …`
# line carrying no markdown level at all). See `_iter_headings` for why.
_HEADING_RE = re.compile(
    r"""^                                       # start of line
        (?:                                     # REQUIRED prefix (v9.7.152, Bug 2.1):
            (?P<md>\#{1,6}\s+|\*\*\s*)          #   markdown header level, or bold-only,
            (?P<md_marker>§|Section\s+|)        #     with an OPTIONAL § / Section marker
          | (?P<bare_marker>§|Section\s+)       #   bare § marker / bare "Section " word
        )                                       # at least one of the above must be present,
                                                #   so a plain "1. sentence" line no longer matches
        (?P<num>\d{1,2})                       # section number
        (?!\.\d)                               # v9.7.410: a number immediately followed by
                                               #   `.<digit>` is a NUMBERED SUBSECTION, not a
                                               #   section heading — `#### 4.1`, `### 4.2 ·`,
                                               #   `## §10.5` are body text belonging to the parent
        (?:\s*[\.\:\—\-–]\s*|\s+)              # separator: . : — - – or whitespace
        (?P<title>[^\n*]+?)                    # title up to newline or **
        (?:\s*\*\*|)                           # optional closing bold
        \s*$                                    # end of line
    """,
    re.VERBOSE | re.MULTILINE,
)



# --- v9.7.364: recognised section numbers are DERIVED FROM THE CONTRACT, never a literal ------------
# Codex/Rootstock review of the §31-§48 patch bundle (2026-08-11) found the defect this replaces: the
# contract gained §31-§48 while BOTH Markdown parsers stayed hard-capped at `1 <= num <= 30`, so a card
# with valid §31/§48 headings parsed to [] / {} and the new sections were SILENTLY DISCARDED. Verified
# first-hand on sealed .363 before fixing: extract_section_titles() returned only [(1, 'Intake')].
#
# The fix deliberately does NOT swap 30 for another literal 48 in two places. The bound comes from the
# canonical contract, so reserved §49/§50 work cannot recreate the same defect. If the contract cannot
# be read we fall back to the historical §1-§30 window rather than widening silently.
_RECOGNISED_FALLBACK_MAX = 30


# Numbers ABOVE the contract that must still be *seen* (so `lint_card` can warn UNKNOWN_SECTION_NUMBER)
# rather than silently dropped by the parser. Without this, tightening the parser to the contract would
# reintroduce the exact silent-discard class the .364 fix removes — one rung further up. §49/§50 are
# reserved in the roadmap, so they are the natural window.
_SURFACED_UNKNOWN_MAX = 50


def recognised_section_numbers(contract: Optional[dict] = None) -> set[int]:
    """Section numbers the parsers will admit. Derived from the contract; never hardcoded.

    Includes a small reserved window above the contract so out-of-contract numbers are SURFACED as
    UNKNOWN_SECTION_NUMBER warnings instead of vanishing.
    """
    # BC2-405: load_contract() is called OUTSIDE the try below on purpose. Its own docstring is
    # explicit that a missing/malformed bundled contract is a bundle-integrity failure that must
    # surface, never silently degrade to a hard-coded fallback -- but this function used to call
    # it INSIDE a bare `except Exception: pass`, catching exactly the FileNotFoundError/ValueError
    # load_contract() is designed to raise and silently returning a plausible-looking wrong
    # section-number set instead. lint_card() already calls load_contract() unguarded (raises
    # loudly), so this was a live gap only for a caller of the public extract_section_titles()
    # directly (contract=None) -- exactly the shape tests/test_modeb_reference_full48_exemplar_
    # v9_7_372.py and others use. Only a caller-SUPPLIED `contract` dict that turns out to be
    # malformed (a different, more benign, caller-controlled case) still falls back below.
    c = contract if contract is not None else load_contract()
    try:
        nums = {int(s["number"]) for s in c.get("sections", []) if str(s.get("number", "")).isdigit()}
        if nums:
            return nums | set(range(max(nums) + 1, _SURFACED_UNKNOWN_MAX + 1))
    except (AttributeError, TypeError, KeyError) as exc:
        # D4 (v9.7.406 candidate): a caller-SUPPLIED `contract` dict malformed enough to fail
        # `.get`/iteration/int() here is the "more benign, caller-controlled case" this
        # function's own docstring already calls out (load_contract()'s own malformed-bundle
        # failure is unguarded above and raises loudly, as it must). Named, not swallowed, so a
        # caller relying on the fallback range can see why it fired instead of a silently
        # plausible-looking wrong section-number set.
        sys.stderr.write(
            f"modeb_structure_gate: caller-supplied contract malformed "
            f"({type(exc).__name__}: {exc}); falling back to 1-{_RECOGNISED_FALLBACK_MAX}\n")
    return set(range(1, _RECOGNISED_FALLBACK_MAX + 1))


def _canonical_titles(contract: dict) -> dict[int, str]:
    """{section_number: _normalise(canonical title)} read from the contract.

    Used only by the v9.7.410 marker-less admission rule below. A malformed
    caller-supplied contract yields {} — which makes the rule maximally
    conservative (no marker-less heading is admitted), never more permissive.
    """
    out: dict[int, str] = {}
    try:
        for s in contract.get("sections", []) or []:
            n = s.get("number")
            if str(n).isdigit():
                out[int(n)] = _normalise(str(s.get("title", "")))
    except (AttributeError, TypeError, KeyError):
        return {}
    return out


def _iter_headings(card_md: str,
                   contract: Optional[dict] = None) -> list[tuple[Any, int, str]]:
    """Return [(match, number, stripped_title), ...] for every ADMITTED section
    heading, in document order. THE single section view — `extract_section_titles`
    and `extract_section_bodies` both read it, so a line can never be a heading for
    one and body text for the other.

    v9.7.410 (MODEB-GATE-410, round-6 re-audit Findings 1/2/5) — admission rule.
    `_HEADING_RE` alone over-matched and REFUSED valid hand-authored cards:

      * `#### 4.1 …` / `### 4.2 · …` parsed as a second §4 → DUPLICATE_SECTION,
        and `extract_section_bodies` truncated the real §4 body at the subsection
        (measured: 1359 → 78 chars) → THIN_SECTION. The project's own
        `wiki/User-Manual.md` writes subsections exactly this way.
      * `### 2. Committed-step core` inside §4 parsed as a top-level §2 → OUT_OF_ORDER.
      * An ordinary prose line opening `§12 ecological context …` or
        `Section 5 genes were absent …` parsed as a phantom heading →
        OUT_OF_ORDER + THIN_SECTION + DUPLICATE_SECTION. Mode B cards cross-reference
        sections by number constantly, so this fired routinely.

    Two guards close all three, and both fail toward "this is body text":

      1. `(?!\\.\\d)` in the regex: a number immediately followed by `.<digit>` is a
         numbered SUBSECTION. It is not a heading at all, so its prose stays inside
         the parent section's body and counts toward the parent's depth floor.
      2. Marker requirement (here): a heading is admitted on its NUMBER ALONE only
         when it is self-identifying — a markdown level (`#`…`######`) or bold `**`
         PLUS an explicit `§` / `Section ` marker. A MARKER-LESS heading (`## 20 —
         Next actions`, or a bare `§7 — …` / `Section 4 — …` line with no markdown at
         all) is admitted only when its title IS the canonical contract title for that
         number. Prose never accidentally states the canonical title, and the
         historical bare-heading tolerance (v9.7.152) is preserved for the real
         headings it was added for.

    Consequence worth stating plainly: a MARKER-LESS heading with a wrong title (e.g.
    `## 4. Gene by gene stuff`) is no longer read as §4, so it surfaces as
    MISSING_REQUIRED_SECTION rather than TITLE_MISMATCH. Both are ERROR — the card is
    still refused — and TITLE_MISMATCH is unchanged for every `§`/`Section `-marked
    heading, which is what the emitter and every template actually write.
    """
    hits: list[tuple[Any, int, str]] = []
    if not card_md:
        return hits
    c = contract if contract is not None else load_contract()
    _recognised = recognised_section_numbers(c)
    _canonical = _canonical_titles(c)
    for m in _HEADING_RE.finditer(card_md):
        try:
            num = int(m.group("num"))
        except (TypeError, ValueError):
            continue
        if num not in _recognised:
            # Not a Mode B section number — sub-heading like "## 4.1.2 ..."
            # or a list item that looks like a heading. Skip.
            continue
        title = m.group("title").strip()
        # Strip trailing punctuation/dashes that some authors append
        title = title.rstrip(" -–—:.")
        if not (m.group("md") and m.group("md_marker")):
            # Marker-less: must name the canonical title to be a heading.
            expected = _canonical.get(num)
            if not expected or _normalise(title) != expected:
                continue
        hits.append((m, num, title))
    return hits


def extract_section_titles(card_md: str, contract: Optional[dict] = None) -> list[tuple[int, str]]:
    """Return [(number, normalised_title), ...] for every section heading
    detected in the card. Sorted in detection order (so duplicates and
    out-of-order sections are both visible to the caller).
    """
    return [(num, title) for _m, num, title in _iter_headings(card_md, contract)]


# ---------------------------------------------------------------------------
# Section body extraction + depth floor (W9 depth-gate, v9.7.162)
# ---------------------------------------------------------------------------
#
# Motivating failure (v9.7.161, AS-XXX top-8 case): a chat authored a card
# whose §1–§30 HEADINGS were present (or collapsed) but whose bodies were
# one-to-two sentences each — ~44 lines for a large BGC against the ~500-line
# depth standard. The structure gate passed the headings it could see and had
# no notion of body length, so a thin card was not mechanically distinguished
# from a deep one. This block adds that notion: measure the prose body under
# each detected heading and flag sections/cards that fall below a floor.
#
# Severity policy (mirrors the conditional-section design):
#   - default: THIN_SECTION / THIN_CARD are WARN (gate proceeds, prints note)
#   - strict_depth=True: they are ERROR (gate refuses, --force to override)
# so depth enforcement is opt-in per caller and never silently blocks a
# legitimately short card for a trivial fragment unless the caller asked.

# Default body floors (characters). Large-BGC sections are held to a higher
# floor than small/fragment BGCs; §4 (gene-by-gene) and §16/§17 (capacity)
# carry the interpretive weight, so they get their own higher floors.
_DEPTH_DEFAULTS = {
    # v9.7.164: floors raised to match MEASURED good-card depth. The v9.7.162 floors
    # (400/900/9000) were set by estimate and let thin cards pass — a genuine full-depth
    # AS-XXX BGC006 card (Interior, 68 domains) measured ~800-1,500 chars/section, heavy
    # sections 1,100-2,800, and 31,676 total, yet tripped only 1 THIN under the old floors.
    # New floors demand roughly that measured depth, with headroom for legitimate N/A
    # sections (e.g. §21/§22 on a non-RiPP NRP), which should be marked considered-N/A prose
    # (>=~350 chars of reasoning), not left near-empty. Small-fragment floors scale down.
    # v9.7.227: floors LOWERED to catch genuinely empty/skeleton sections only, NOT to set
    # a length target. High floors rewarded length and drove ~22-40% padding (cross-refs,
    # restatement openers, elaborated hedges) as authors expanded to hit the count — the metric
    # became the target. A section carries its point in the evidence it cites, not its char
    # count. Density is enforced by the evidence-presence checks below, not by length.
    "section_min_chars_large": 250,    # "not empty", not a target (was 700)
    "section_min_chars_small": 150,    # (was 300)
    "heavy_section_min_chars_large": 450,    # §4/§16/§17 still need real prose (was 1400)
    "heavy_section_min_chars_small": 300,    # (was 500)
    "card_min_chars_large": 7000,      # backstop against a skeleton card (was 20000)
    "card_min_chars_small": 3000,      # (was 6000)
}
# Sections that carry the deep interpretive load and get the heavy floor.
_HEAVY_SECTIONS = {4, 16, 17}


def extract_section_bodies(card_md: str, contract: Optional[dict] = None) -> dict[int, str]:
    """Return {section_number: body_text} for each detected heading, where
    body_text is everything between that heading line and the next heading
    (or end of card). Only the FIRST occurrence of a section number is kept
    (duplicates are a separate DUPLICATE_SECTION finding). Body text excludes
    the heading line itself.

    v9.7.410: the heading set comes from `_iter_headings`, the SAME admitted view
    `extract_section_titles` uses, and a body now runs to the next ADMITTED heading
    rather than to the next raw `_HEADING_RE` hit. That is the point of the fix: a
    numbered subsection (`#### 4.1 …`) or a prose cross-reference (`§12 …`) no longer
    truncates the section it sits inside, so its prose counts toward the parent's
    depth floor and toward the whole-card total.
    """
    bodies: dict[int, str] = {}
    if not card_md:
        return bodies
    hits = _iter_headings(card_md, contract)
    for i, (m, num, _title) in enumerate(hits):
        if num in bodies:
            continue
        start = m.end()
        end = hits[i + 1][0].start() if i + 1 < len(hits) else len(card_md)
        bodies[num] = card_md[start:end].strip()
    return bodies


_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


def _strip_html_comments(text: str) -> str:
    """MODEB-GATE-P06 (v9.7.331): remove <!-- ... --> author-guidance comments from a section body
    before the novelty / padding PROSE scans run. The §24 template ships its own guidance comment
    that names a 'novel compound' placeholder; extract_section_bodies keeps it verbatim, so the
    novelty regex scanned the template's OWN text and every high-identity §24 card tripped
    NOVELTY_CONTRADICTION until the placeholder was filled. Stripping is LOCAL to these lints only —
    extract_section_bodies still returns comments verbatim, so the depth gate's char floors (which
    legitimately count comment text, per the cohort toolkit) are unchanged."""
    return _HTML_COMMENT_RE.sub("", text or "")


def _is_large_bgc(bgc_context: Optional[dict]) -> bool:
    """Large-BGC heuristic for choosing depth floors. A BGC earns the higher
    floor if its context marks it large by any of: boundary Interior, total
    domain count >= 40, or length >= 30 kb. Falsy/absent context defaults to
    the LARGE floor (fail toward demanding more depth, not less — the whole
    point of this gate is to stop thin cards slipping through)."""
    if not bgc_context:
        return False  # v9.7.227: default to the LOWER floor; demanding max depth by default
                      # was the padding incentive. Large floor applies only on positive evidence.
    if _context_count(bgc_context, "total_domains") >= 40:
        return True
    if _context_number(bgc_context, "length_kb") >= 30:
        return True
    if str(bgc_context.get("boundary", "")).strip().lower() == "interior":
        return True
    return False


def _depth_floors(contract: dict, bgc_context: Optional[dict]) -> dict:
    """Resolve effective depth floors: contract['depth'] overrides the code
    defaults if present (so a contract can tune floors without a code change),
    but a missing 'depth' key is fine — old contracts still work."""
    floors = dict(_DEPTH_DEFAULTS)
    floors.update(contract.get("depth", {}) or {})
    return floors


def _is_marked_not_applicable(body: str) -> bool:
    """True if a section body explicitly reasons that it is NOT APPLICABLE for this BGC
    (e.g. §21/§22 on a non-RiPP NRP). Conservative substring match on considered-N/A markers;
    a section still must clear the small floor, so this exempts reasoned N/A from the large/
    heavy floor but never lets a bare 'N/A' one-liner pass."""
    b = (body or "").lower()
    markers = (
        "not applicable", "n/a for", "considered-n/a", "considered n/a",
        "marked not-applicable", "not-applicable-for", "does not apply",
        "not the right tool", "not run", "n/a —", "n/a -",
    )
    return any(m in b for m in markers)


def _depth_findings(card_md: str,
                bgc_context: Optional[dict] = None,
                contract: Optional[dict] = None,
                strict_depth: bool = False) -> list[Finding]:
    """Measure per-section and whole-card body length against the depth floor
    and emit THIN_SECTION / THIN_CARD findings. Severity is WARN unless
    strict_depth is True, in which case it is ERROR (refuse-by-default).

    This is separate from lint_card's structural checks so it can be called
    independently, and is folded into lint_card via the check_depth=True arg.
    """
    findings: list[Finding] = []
    if not card_md or not card_md.strip():
        return findings  # EMPTY_CARD is lint_card's job
    if contract is None:
        contract = load_contract()
    floors = _depth_floors(contract, bgc_context)
    large = _is_large_bgc(bgc_context)
    sev = "ERROR" if strict_depth else "WARN"

    bodies = extract_section_bodies(card_md)
    total_body = sum(len(b) for b in bodies.values())

    for num, body in sorted(bodies.items()):
        # v9.7.164: a section explicitly reasoned as NOT APPLICABLE for this BGC class
        # (e.g. §21 precursor ladder / §22 RiPP search on a non-RiPP NRP) is held to the
        # SMALL floor, not the large one — a correctly-argued N/A should not be forced to
        # pad to full depth. But it must still carry real reasoning (>= small floor), so a
        # bare "N/A" one-liner still fails. Detection is conservative: the body must contain
        # an explicit not-applicable marker.
        _na = _is_marked_not_applicable(body)
        if num in _HEAVY_SECTIONS and not _na:
            floor = floors["heavy_section_min_chars_large" if large
                            else "heavy_section_min_chars_small"]
        elif _na:
            floor = floors["section_min_chars_small"]
        else:
            floor = floors["section_min_chars_large" if large
                           else "section_min_chars_small"]
        n = len(body)
        if n < floor:
            findings.append(_mk(
                sev, "THIN_SECTION", num, f">= {floor} chars", f"{n} chars",
                f"§{num} body is {n} chars; depth floor for a "
                f"{'large' if large else 'small'} BGC is {floor}. "
                f"{'This is a heavy interpretive section (gene-by-gene / capacity) '
                   'and needs substantive prose.' if num in _HEAVY_SECTIONS else 'Expand with evidence-grounded interpretation.'}"))

    card_floor = floors["card_min_chars_large" if large else "card_min_chars_small"]
    if total_body < card_floor:
        findings.append(_mk(
            sev, "THIN_CARD", None, f">= {card_floor} chars",
            f"{total_body} chars",
            f"Whole-card body is {total_body} chars across {len(bodies)} "
            f"sections; depth floor for a {'large' if large else 'small'} BGC "
            f"is {card_floor} (~2 pages of solid text for a large BGC). "
            f"The card is structurally present but interpretively thin."))
    return findings


# ---------------------------------------------------------------------------
# BGC context — predicates for conditional sections (§21–§27, §29)
# ---------------------------------------------------------------------------

# Class tokens that count as RiPP for §21/§22 purposes
_RIPP_CLASS_TOKENS = {
    "ripp", "ripp-like", "lassopeptide", "lasso", "lanthipeptide",
    "sactipeptide", "thiopeptide", "linaridin", "lanthidin",
    "ranthipeptide", "lipolanthine", "bottromycin", "microviridin",
    "lap", "head-to-tail",
}

# Class tokens that suggest "novel / no MIBiG hit" — used as a heuristic
# fallback when bgc_context doesn't carry an explicit MIBiG match flag.
_NOVEL_CLASS_TOKENS = {"other", "hybrid", "unknown"}

_NUMERIC_DEFICIT_STATES = {
    "", "-", "n/a", "na", "nan", "none", "null", "unknown", "unbound",
    "absent", "not_applicable", "not_measured", "not_produced",
    "source_unavailable", "source_present_row_missing", "identity_or_join_hold",
    "measured_none_found",
}


def _context_number(ctx: dict, *keys: str) -> float:
    """Return the first finite, non-negative numeric alias; deficits remain missing."""
    for key in keys:
        value = ctx.get(key)
        if value is None or str(value).strip().lower() in _NUMERIC_DEFICIT_STATES:
            continue
        if isinstance(value, bool):
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number) and number >= 0:
            return number
    return 0.0


def _context_count(ctx: dict, *keys: str) -> int:
    """Return the first finite non-negative integer alias; never truncate fractions."""
    for key in keys:
        value = ctx.get(key)
        if value is None or str(value).strip().lower() in _NUMERIC_DEFICIT_STATES:
            continue
        if isinstance(value, bool):
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number) and number >= 0 and number.is_integer():
            return int(number)
    return 0


def _numeric_context_findings(ctx: Optional[dict]) -> list[dict]:
    """Surface malformed present predicate inputs instead of converting them to zero."""
    if not ctx:
        return []
    fields = {
        "ab_score": "non-negative finite number",
        "AB_auto": "non-negative finite number",
        "af_score": "non-negative finite number",
        "AF_auto": "non-negative finite number",
        "length_kb": "non-negative finite number",
        "strain_high_priority_count": "non-negative integer",
        "n_genes": "non-negative integer",
        "module_count": "non-negative integer",
        "n_modules": "non-negative integer",
        "protocluster_count": "non-negative integer",
        "n_protoclusters": "non-negative integer",
        "n_cross_strain_comparisons": "non-negative integer",
        "n_4d_rows": "non-negative integer",
        "n_4a_rows": "non-negative integer",
        "total_domains": "non-negative integer",
    }
    findings = []
    for key, expected in fields.items():
        if key not in ctx:
            continue
        value = ctx.get(key)
        text = str(value).strip().lower() if value is not None else ""
        if value is None or text in _NUMERIC_DEFICIT_STATES:
            continue
        if isinstance(value, bool):
            valid = False
        else:
            try:
                number = float(value)
                valid = math.isfinite(number) and number >= 0
                if expected.endswith("integer"):
                    valid = valid and number.is_integer()
            except (TypeError, ValueError):
                valid = False
        if not valid:
            findings.append(_mk(
                "ERROR", "VERIFICATION_CONTEXT_NUMERIC_INVALID", None,
                f"{key}: {expected}", f"{key}: {value!r}",
                f"Present verification context field `{key}` is malformed; it cannot be "
                "treated as absent or zero. Repair the package context before verification."))
    return findings


def _build_predicates(ctx: Optional[dict]) -> dict[str, bool]:
    """Evaluate the contract's conditional predicates against a BGC context.

    `ctx` is a free-form dict — typically a row from the triage board
    augmented with strain-level rolled-up fields. Missing keys default to
    False so the validator never requires a section the caller can't prove
    is applicable. (This matches the "fail-closed for safety" pattern: if
    in doubt about whether a section applies, treat it as optional.)

    Recognised keys (all optional):
        products, class                — class tokens for RiPP detection
        umed_gap_flag, maturation_gap  — MATURATION_GAP signal
        kcb_top                        — MIBiG comparator: empty → novel
        novelty_auto                   — HIGH / MED / LOW
        lead_tier_auto                 — PRIORITY ISO / HIGH SEQ / MEDIUM ACT
        ab_score, af_score, antimicrobial — antimicrobial-candidate signals
        fermentation_selected          — bool, set by upstream
        strain_high_priority_count     — int (BGCs at HIGH+ lead-tier for the strain)
    """
    ctx = ctx or {}

    # is_ripp — token match in products or class
    class_blob = " ".join(str(ctx.get(k, "")) for k in
                          ("products", "class", "Class", "Products")).lower()
    is_ripp = any(tok in class_blob for tok in _RIPP_CLASS_TOKENS)

    # maturation_gap_or_novel_class
    # v9.7.251: the emitter writes `umed_gap_flag` (cli.py:2259) but the triage board column — the one
    # `chatgpt_commands` reads and writes, and the one a ctx built from a board row actually carries — is
    # `UMED_gap` (cli.py:2213). `_build_predicates` read only the first, so §23 was EMITTED on one BGC set
    # and ENFORCED on another. Reported diverging on 41 of 336 real BGCs, all `maturation_gap_or_novel_class`.
    # Accept every spelling the pipeline actually produces; this is the same class as the `query_gene`/
    # `locus_tag` overlay miss (.245) — a producer and a consumer naming one fact two ways.
    mat_gap = bool(ctx.get("umed_gap_flag") or ctx.get("UMED_gap") or ctx.get("maturation_gap"))
    novel_token = any(tok in class_blob for tok in _NOVEL_CLASS_TOKENS)
    maturation_gap_or_novel_class = mat_gap or novel_token

    # novel_or_no_mibig — empty kcb_top OR explicit novelty_auto=HIGH
    kcb_top = str(ctx.get("kcb_top") or ctx.get("KCB_top") or "").strip()
    novelty = str(ctx.get("novelty_auto") or ctx.get("Novelty_auto") or "").upper()
    novel_or_no_mibig = (not kcb_top) or novelty == "HIGH"

    # isolation_worthy — lead tier HIGH or PRIORITY ISO
    lead = str(ctx.get("lead_tier_auto") or ctx.get("Lead_tier_auto") or "").upper()
    isolation_worthy = lead in ("HIGH", "PRIORITY ISO", "PRIORITY_ISO",
                                "HIGH SEQ", "HIGH_SEQ")

    # fermentation_selected — explicit flag only. Don't auto-infer from lead
    # tier; fermentation selection is a separate human decision (the
    # corresponding ferm card / wet-lab matrix call).
    fermentation_selected = bool(ctx.get("fermentation_selected"))

    # antimicrobial_candidate — explicit flag, else inferred from non-empty
# AB or AF scores are routing priors; they do not imply a named assay, activity, or BGC linkage.
    # level, contrast by mechanism not phenotype).
    explicit_am = ctx.get("antimicrobial")
    if explicit_am is None:
        ab = _context_number(ctx, "ab_score", "AB_auto")
        af = _context_number(ctx, "af_score", "AF_auto")
        antimicrobial_candidate = ab > 0 or af > 0
    else:
        antimicrobial_candidate = bool(explicit_am)

    # strain_gt_3_high_priority
    n_hp = _context_count(ctx, "strain_high_priority_count")
    strain_gt_3_high_priority = n_hp > 3

    # ---- v9.7.364 §31–§48 predicates — TYPED, not Python truthiness --------------------------
    # Codex/Rootstock review (2026-08-11) rejected a generic `_any()` helper: it treats every
    # non-empty string as true, so "0", "false", "NONE", "NOT_PRODUCED", "NOT_MEASURED" and
    # "UNBOUND" all fired predicates. That would have enabled §32–§34 on `module_count="0"`,
    # §41/§43 on zero rows, §38 on `resistance_tier="NONE"`, and §45–§47 on a sentinel-valued
    # registry — i.e. sections asserted applicable on evidence that explicitly says otherwise.
    #
    # The evidence states are distinct and must stay distinct: PRESENT vs MEASURED_NONE_FOUND vs
    # NOT_PRODUCED vs NOT_MEASURED vs UNBOUND. Only PRESENT (or a positive count) makes a section
    # applicable. "Measured and none found" is a real result but does not make the section apply;
    # "not measured" is not evidence of absence.
    # Codex review #5 (2026-08-12): a negative blacklist cannot be complete. `_flag()` treated every
    # UNRECOGNISED non-empty string as True, so deficit states outside the blacklist —
    # SOURCE_UNAVAILABLE, NOT_APPLICABLE, IDENTITY_OR_JOIN_HOLD, SOURCE_PRESENT_ROW_MISSING — still
    # fired predicates. Inverted to an ALLOWLIST: a string makes a section applicable only if it is a
    # recognised POSITIVE state. Anything unrecognised is treated as NOT applicable, which is the
    # fail-safe direction: an unknown state must never assert that evidence exists.
    _POSITIVE = {"present", "bound", "true", "yes", "y", "1", "ok", "available",
                 "measured", "measured_present", "confirmed", "resolved"}
    # The authoring specification's full deficit vocabulary — kept explicit so the meaning of each
    # state stays visible even though the allowlist already excludes them.
    _DEFICIT = {"measured_none_found", "not_produced", "not_measured", "source_unavailable",
                "source_present_row_missing", "identity_or_join_hold", "not_applicable",
                "unbound", "none", "false", "no", "null", "nan", "n/a", "na", "absent",
                "unknown", "-", "0", "0.0", ""}

    def _flag(*keys) -> bool:
        """True only for a RECOGNISED positive state: real bool True, a positive number, or a
        string in `_POSITIVE`. An unrecognised string is NOT positive (fail-safe)."""
        for k in keys:
            v = ctx.get(k)
            if v is None:
                continue
            if isinstance(v, bool):
                if v:
                    return True
                continue
            if isinstance(v, (int, float)):
                if v > 0:
                    return True
                continue
            t = str(v).strip().lower()
            if t in _DEFICIT:
                # A recognised-negative value under THIS key must not short-circuit the whole
                # multi-key alias check — the same fact can be written under two different key
                # names by different producers (the umed_gap_flag/UMED_gap precedent documented
                # above), so a later key may still carry a genuine positive. Consistent with the
                # bool/int branches above, which also continue rather than return on a falsy value.
                continue
            if t in _POSITIVE:
                return True
            # An IDENTIFIER (accession, family id, run id, path) is a positive binding: it names a
            # specific thing. Only the explicit deficit vocabulary above is negative; an
            # unrecognised BARE WORD is still refused, so a novel sentinel cannot slip through.
            if any(ch.isdigit() for ch in t) and len(t) >= 2:
                return True
            # a bare positive integer as a string counts as a count-style positive
            try:
                if float(t) > 0:
                    return True
            except ValueError:
                continue
        return False

    has_gene_table = _flag("gene_table", "has_gene_table", "gene_by_gene", "gene_data") \
        or _context_count(ctx, "n_genes") > 0
    _al_tokens = ("pks", "nrps", "t1pks", "t2pks", "t3pks", "transat", "hgle-ks")
    has_assembly_line = (_context_count(ctx, "module_count", "n_modules") > 0
                         or _flag("has_assembly_line")
                         or any(t in class_blob for t in _al_tokens))
    # v9.7.369 W13 (fold amendment, INDIGO2 owner ruling 2026-08-18): a REQUIRED
    # section binding must ride MEASURED architecture only. The class-token branch
    # above fires on label alone — measured counterexamples AS-XXX BGC009 (hglE-KS)
    # / BGC030 + AS-XXX BGC016 (T3PKS): label-PKS with ZERO aSModule features, where
    # "module programming" is architecturally meaningless. §32–§34's condition_key
    # binds to THIS predicate; has_assembly_line stays for WARN-level applicability.
    # "Not measured is not evidence" — a label cannot make a section mandatory.
    has_measured_assembly_line = (_context_count(ctx, "module_count", "n_modules") > 0
                                  or _flag("has_assembly_line"))
    multi_protocluster = _context_count(ctx, "protocluster_count", "n_protoclusters") > 1 \
        or _flag("multi_protocluster")
    _boundary = str(ctx.get("boundary") or ctx.get("Boundary") or "").lower()
    boundary_or_overmerge_flag = (
        any(t in _boundary for t in ("edge", "truncat", "spans", "contig-edge"))
        or _flag("overmerge_flag", "overmerge", "split_candidate", "over_merge"))
    has_resistance_signal = _flag("resistance", "resistance_tier", "has_resistance",
                                  "efflux", "arts_hit")
    # §39 needs an ACTUAL bound cross-strain identity comparison — cohort_size >= 2 alone is a
    # roster fact, not a measurement (Codex item E).
    has_cohort_context = _flag("cross_strain_identity", "identity_comparison_bound") \
        or _context_count(ctx, "n_cross_strain_comparisons") > 0
    # §40 requires one parsed qualified identity. Separate legacy fields never suffice.
    has_gcf_assignment = False
    qualified = ctx.get("qualified_family_id") or ctx.get("bigscape_qualified_family")
    if qualified:
        try:
            identity = parse_family_identity(qualified)
            supplied_run = ctx.get("gcf_run") or ctx.get("bigscape_run") or ctx.get("run_id")
            supplied_cutoff = ctx.get("bigscape_cutoff") or ctx.get("normalized_cutoff")
            has_gcf_assignment = (
                (supplied_run is None or normalize_run_id(supplied_run) == identity.run_id)
                and (supplied_cutoff is None or normalize_cutoff(supplied_cutoff) == identity.normalized_cutoff)
            )
        except NamespaceError:
            has_gcf_assignment = False
    has_4d_rows = _context_count(ctx, "n_4d_rows") > 0 or _flag("has_4d_rows", "two_proof_rows_bound")
    has_4a_rows = _context_count(ctx, "n_4a_rows") > 0 or _flag("has_4a_rows", "rggmci_rows_bound")
    # §42 needs measured composition AND a declared baseline — GC presence alone is not HGT evidence.
    has_composition_stats = _flag("gc_content", "overall_gc", "genome_gc", "codon_usage") \
        and _flag("composition_baseline", "hgt_baseline_declared")
    has_wider_comparison_set = _flag("wider_comparison_set", "comparison_registry")
    has_reference_genomes = _flag("reference_genomes", "type_strain_set", "genus_references")
    has_host_matched_set = _flag("host_matched_set") and _flag("host_confirmed", "host_context")
    # §48 follows the sections that are ACTUALLY applicable (§39–§47), not a mere source pointer.
    always_when_extended = any((has_cohort_context, has_gcf_assignment, has_4d_rows, has_4a_rows,
                                has_composition_stats, has_wider_comparison_set,
                                has_reference_genomes, has_host_matched_set))

    return {
        "is_ripp": is_ripp,
        "maturation_gap_or_novel_class": maturation_gap_or_novel_class,
        "novel_or_no_mibig": novel_or_no_mibig,
        "isolation_worthy": isolation_worthy,
        "fermentation_selected": fermentation_selected,
        "antimicrobial_candidate": antimicrobial_candidate,
        "strain_gt_3_high_priority": strain_gt_3_high_priority,
        # v9.7.364 — §31–§48 (typed predicates; see the block above)
        "has_gene_table": has_gene_table,
        "has_assembly_line": has_assembly_line,
        "has_measured_assembly_line": has_measured_assembly_line,
        "multi_protocluster": multi_protocluster,
        "boundary_or_overmerge_flag": boundary_or_overmerge_flag,
        "has_resistance_signal": has_resistance_signal,
        "has_cohort_context": has_cohort_context,
        "has_gcf_assignment": has_gcf_assignment,
        "has_4d_rows": has_4d_rows,
        "has_4a_rows": has_4a_rows,
        "has_composition_stats": has_composition_stats,
        "has_wider_comparison_set": has_wider_comparison_set,
        "has_reference_genomes": has_reference_genomes,
        "has_host_matched_set": has_host_matched_set,
        "always_when_extended": always_when_extended,
    }


# ---------------------------------------------------------------------------
# Title matching
# ---------------------------------------------------------------------------

def _normalise(s: str) -> str:
    """Lower-case, strip punctuation/whitespace for forgiving title matching."""
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def _titles_match(found: str, expected: str, *, exact: bool = False) -> bool:
    """Codex review #3 (2026-08-12): `_normalise()` strips ALL punctuation, so for §31–§48 the
    selected titles were silently broadened — "Initiation release logic" passed for
    "Initiation & release logic", and "Cross cohort synthesis claim ceiling" for
    "Cross-cohort synthesis & claim ceiling". the Developer or User chose punctuation-bearing titles deliberately
    (`&`, `+`, `/`, hyphens, `(merged)`), so for the extension the comparison is LITERAL on the
    trimmed string. §1–§30 keep the historical tolerant match — tightening those would fail
    existing authored cards, which is a separate decision.
    """
    if exact:
        return found.strip() == expected.strip()
    return _normalise(found) == _normalise(expected)


# ---------------------------------------------------------------------------
# Linter
# ---------------------------------------------------------------------------

Finding = dict  # alias for clarity


def lint_card(card_md: str,
              bgc_context: Optional[dict] = None,
              contract: Optional[dict] = None,
              check_depth: bool = False,
              strict_depth: bool = False,
              check_class_content: bool = False,
              check_claim_safety: bool = False,
              check_citations: bool = False,
              check_evidence_presence: bool = False,
              check_publication_quality: bool = False,
              check_substantive_quality_v2: bool = False,
              check_semantic_sections_v3: bool = False,
              check_semantic_comparators_v4: bool = False,
              check_semantic_sections_v5: bool = False,
              check_semantic_decision_chains_v6: bool = False,
              check_semantic_claim_models_v7: bool = False,
              check_inventory_reconciliation_v8: bool = False,
              check_selection_process_v9: bool = False,
              check_figure_spec_v10: bool = False,
              check_reconciliation_specificity_v11: bool = False,
              canonical_loci: Optional[Iterable[str]] = None) -> list[Finding]:
    """Validate a Mode B card's structure against the canonical §1–§48 contract.

    Returns a list of Finding dicts. The list is empty for a card that
    passes. Severity ERROR = refuse; WARN = proceed with a printed note.

    `bgc_context`, if supplied, lets the linter evaluate conditional
    predicates (§21–§27, §29). Without context, conditional sections are
    treated as optional — missing them is a WARN, not an ERROR.

    `check_depth` (v9.7.162): also measure per-section and whole-card body
    length against the depth floor, emitting THIN_SECTION / THIN_CARD.
    These are WARN by default; `strict_depth=True` makes them ERROR so a
    thin-but-structurally-complete card is refused (the AS-XXX failure mode).
    Depth checks are additive and never suppress a structural finding.
    """
    findings: list[Finding] = _numeric_context_findings(bgc_context)
    if contract is None:
        contract = load_contract()

    sections = contract["sections"]
    by_num = {s["number"]: s for s in sections}

    if not card_md or not card_md.strip():
        findings.append(_mk("ERROR", "EMPTY_CARD", None, None, None,
                            "Card content is empty or whitespace-only."))
        return findings

    detected = extract_section_titles(card_md)
    if not detected:
        findings.append(_mk(
            "ERROR", "NO_HEADINGS_DETECTED", None, None, None,
            "No §1–§48 section headings detected in the card. "
            "Expected markdown headings of the form `## §1 Identity and node/region`."))
        return findings

    detected_nums = [n for n, _ in detected]
    detected_by_num: dict[int, str] = {}
    for num, title in detected:
        if num in detected_by_num:
            # Codex review #2 (2026-08-12): a duplicated §31–§48 section makes BODY OWNERSHIP
            # ambiguous — two blocks claim one registered slot, and `extract_section_bodies()`
            # keeps only the first, so the second is silently dropped. That is an ERROR for the
            # extension. §1–§30 keep WARN for back-compatibility with existing authored cards.
            _dup_sev = "ERROR" if num > 30 else "WARN"
            findings.append(_mk(
                _dup_sev, "DUPLICATE_SECTION", num,
                detected_by_num[num], title,
                f"Section §{num} appears more than once."
                + (" A duplicated extension section makes body ownership ambiguous; "
                   "only the first block is parsed." if num > 30 else "")))
        else:
            detected_by_num[num] = title

    # ----- legacy-scaffold detection (BGC033 case) -----
    # If the card has any of these legacy titles in a §1–§20 slot, that's
    # a strong signal someone authored against the old scaffold.
    legacy_titles = {
        "identity": [1],          # contract §1 is "Identity AND NODE/REGION"
        "assembly": [3],          # legacy §2 Assembly → contract §3
        "activation": [],         # legacy §9 — no current slot
        "forensic sweep": [],     # legacy §10 — no current slot
        "forensic": [],
    }
    for num, title in detected:
        tnorm = _normalise(title)
        for legacy, valid_slots in legacy_titles.items():
            if _normalise(legacy) == tnorm and num not in valid_slots:
                findings.append(_mk(
                    "ERROR", "LEGACY_SCAFFOLD_TITLE", num,
                    by_num.get(num, {}).get("title"), title,
                    f"§{num} title '{title}' matches the historical scaffold "
                    f"(pre-v9.7.144). The current canonical title is "
                    f"'{by_num.get(num, {}).get('title')}'. The legacy scaffold "
                    f"is superseded by the §1–§48 contract — see "
                    f"`docs/MODE_B_20_SECTION_CANONICAL_TITLES.md`."))

    # ----- always-required sections -----
    for s in sections:
        num = s["number"]
        # v9.7.364: 'optional' (§31-§48) is never required-when-absent. Present-section checks
        # (exact title, order, uniqueness, body/depth) run for ALL tiers further down, so an optional
        # section that IS present is still fully validated — recognised-but-not-required.
        if s.get("required") == "optional":
            # v9.7.364 §31-§48: absence is NEVER an error — but a PRESENT optional section is fully
            # validated (Codex acceptance cases 4/5). Recognised-but-not-required, not unchecked.
            if num in detected_by_num and not _titles_match(
                    detected_by_num[num], s["title"], exact=(num > 30)):
                findings.append(_mk(
                    "ERROR", "TITLE_MISMATCH", num,
                    s["title"], detected_by_num[num],
                    f"§{num} title is '{detected_by_num[num]}'; "
                    f"contract expects '{s['title']}'."))
            # Codex review #4 (2026-08-12): an EMPTY registered section must not pass the ordinary
            # structure gate. Body/depth floors only run under `check_depth=True`, but several real
            # callers (compilation_gate.py, receipt paths) lint without it — so an author could add
            # `## §31 Region CDS census` with no body and every ordinary gate would pass it. This
            # check is unconditional; richer depth floors stay behind check_depth.
            if num in detected_by_num:
                _bodies = extract_section_bodies(card_md)
                if not (_bodies.get(num) or "").strip():
                    findings.append(_mk(
                        "ERROR", "EMPTY_OPTIONAL_SECTION", num,
                        s["title"], detected_by_num[num],
                        f"§{num} '{s['title']}' is present but its body is empty. A registered "
                        f"section with no content asserts coverage it does not have — remove the "
                        f"heading or author the section."))
            continue
        if s["required"] != "always":
            continue
        if num not in detected_by_num:
            findings.append(_mk(
                "ERROR", "MISSING_REQUIRED_SECTION", num,
                s["title"], None,
                f"Section §{num} '{s['title']}' is required for every card "
                f"but is missing."))
            continue
        if not _titles_match(detected_by_num[num], s["title"], exact=(num > 30)):
            findings.append(_mk(
                "ERROR", "TITLE_MISMATCH", num,
                s["title"], detected_by_num[num],
                f"§{num} title is '{detected_by_num[num]}'; "
                f"contract expects '{s['title']}'."))

    # ----- ordering check -----
    # §1–§20 must appear in numeric order. §21–§30 may appear at the end
    # in any order (since some are conditional and may be absent).
    # v9.7.364: the §31-§48 extension block must also read in numeric order when present
    # (Codex acceptance case 7). §21-§30 keep their historical any-order allowance.
    ext_nums = [n for n in detected_nums if 31 <= n <= 48]
    if ext_nums and ext_nums != sorted(ext_nums):
        findings.append(_mk(
            "ERROR", "SECTION_ORDER", None, None, None,
            f"§31-§48 extension sections are out of numeric order: {ext_nums}."))
    main_nums = [n for n in detected_nums if 1 <= n <= 20]
    if main_nums and main_nums != sorted(main_nums):
        findings.append(_mk(
            "ERROR", "OUT_OF_ORDER", None, None, None,
            f"§1–§20 must appear in numeric order. Detected order: {main_nums}."))

    # ----- conditional sections -----
    # v9.7.151 bugfix: an empty dict ({}) is the documented signal from
    # _bgc_context_from_triage() for "no triage row found / context
    # unavailable" — its own docstring promises this degrades to WARN-only
    # (CONDITIONAL_SECTION_NOT_EVALUATED), matching None. But the original
    # `is not None` check let `{}` fall into the ERROR branch (predicates
    # built from an empty dict can still evaluate True — e.g. novel_or_no_
    # mibig fires on ANY missing kcb_top, which an empty context always has).
    # Treat any falsy context (None or {}) as "no context" uniformly.
    if bgc_context:
        predicates = _build_predicates(bgc_context)
        for s in sections:
            num = s["number"]
            if s["required"] != "conditional":
                continue
            key = s["condition_key"]
            applies = predicates.get(key, False)
            present = num in detected_by_num
            if applies and not present:
                findings.append(_mk(
                    "ERROR", "MISSING_CONDITIONAL_SECTION", num,
                    s["title"], None,
                    f"Section §{num} '{s['title']}' is required for this BGC "
                    f"because: {s['condition_human']} Add it or set the "
                    f"BGC context flag to False if the predicate is wrong."))
            elif present and not _titles_match(
                    detected_by_num[num], s["title"], exact=(num > 30)):
                findings.append(_mk(
                    "ERROR", "TITLE_MISMATCH", num,
                    s["title"], detected_by_num[num],
                    f"§{num} title is '{detected_by_num[num]}'; "
                    f"contract expects '{s['title']}'."))
    else:
        # No context — conditional sections become WARN-only
        for s in sections:
            num = s["number"]
            if s["required"] != "conditional":
                continue
            if num not in detected_by_num:
                findings.append(_mk(
                    "WARN", "CONDITIONAL_SECTION_NOT_EVALUATED", num,
                    s["title"], None,
                    f"Section §{num} '{s['title']}' is conditional; "
                    f"no BGC context was supplied so the predicate was not "
                    f"evaluated. Pass bgc_context to enforce."))
            elif not _titles_match(detected_by_num[num], s["title"],
                                   exact=(num > 30)):
                # v9.7.369 W13b (the patch lane fold repair, the review lane-routed): a PRESENT
                # section's title is checkable without any context — predicates gate
                # only whether a section is REQUIRED, never what a present heading
                # must say. Before this branch, flipping §32-§36/§38/§43 from
                # optional (which title-checked present sections) to conditional
                # silently dropped the title guard in degraded (no-ctx) mode — a
                # punctuation-stripped title drew no finding. test_5b pins this.
                findings.append(_mk(
                    "ERROR", "TITLE_MISMATCH", num,
                    s["title"], detected_by_num[num],
                    f"§{num} title is '{detected_by_num[num]}'; "
                    f"contract expects '{s['title']}'."))

    # ----- unknown sections (section numbers not in the §1–§48 contract) -----
    contract_nums = {s["number"] for s in sections}
    for num, title in detected:
        if num not in contract_nums:
            findings.append(_mk(
                "WARN", "UNKNOWN_SECTION_NUMBER", num,
                None, title,
                f"§{num} is not in the §1–§48 contract; treated as informational."))

    # ----- depth floor (v9.7.162, opt-in) -----
    if check_depth:
        findings.extend(
            _depth_findings(card_md, bgc_context, contract, strict_depth))

    # ----- class-specific content checklist (v9.7.164, opt-in) -----
    # A char floor stops one-liners but not padding; the class checklist stops a card that
    # is long yet never addresses its class-specific biology (a thioamide card silent on the
    # thioamidation cassette / O->S shift; a lasso card silent on leader/core + B/C enzymes).
    # products come from bgc_context['products'] (the antiSMASH label). Additive, WARN-level.
    if check_class_content:
        _products = (bgc_context or {}).get("products", "")
        if _products:
            try:
                from .modeb_class_checklist import check_class_content as _ccc
                findings.extend(_ccc(card_md, _products))
                # v9.7.355: PTM(tetramate)-vs-tetronate class-conflict adjudication. When a locus fires
                # BOTH a PTM/tetramate and a tetronate CCTT trigger, the card must adjudicate the two
                # grammars (FkbH+ACP => tetronate review, necessary-not-sufficient; PTM needs an
                # ornithine-selective A-domain). Triggers come from bgc_context or, failing that, the
                # card's own "CCTT triggers" line. Additive, WARN-level.
                from .modeb_class_checklist import check_class_conflict as _ccx
                _trigs = (bgc_context or {}).get("cctt_triggers", "")
                if not _trigs:
                    import re as _re
                    _m = _re.search(r"CCTT[ _]triggers?\s*[:|]\s*(.+)", card_md, _re.I)
                    _trigs = _m.group(1) if _m else ""
                findings.extend(_ccx(card_md, _trigs))
            except Exception as exc:
                # D4 (v9.7.406 candidate): kept broad on purpose, matching locus_map_v8.py's own
                # "non-blocking figure path" precedent -- the checklist is advisory (opt-in,
                # WARN-level) and must never break the structural gate, and its failure modes
                # span an optional-module ImportError through whatever check_class_content /
                # check_class_conflict themselves raise on malformed products/triggers text.
                # Named, not swallowed: a real internal error here (as opposed to "class has no
                # checklist yet") should be visible to whoever is triaging a card, not silent.
                sys.stderr.write(
                    f"modeb_structure_gate: class-content checklist skipped "
                    f"({type(exc).__name__}: {exc})\n")

    # claim-safety (#58) and citation/provenance (#59) lints — additive, WARN-level,
    # opt-in. Never suppress a structural finding; a "produces" slip or a bare BGC id
    # is advisory, not a structural refuse.
    if check_claim_safety:
        findings.extend(_claim_safety_findings(card_md))
    if check_citations:
        findings.extend(_citation_findings(card_md))
    # v9.7.229: evidence-presence — the real quality bar is evidence, not length. When the strain has a
    # BLASTp panel, §4 MUST carry the reconciled per-gene closest-match table (antiSMASH Pfam is a
    # hypothesis, not function). WARN-level; this is the form-level required-evidence assertion the
    # padding fix recommended, so the char-floor stops being the quality proxy.
    if check_evidence_presence:
        # EVIDENCE_GAP is panel-specific ("strain has a BLASTp panel but §4 omits the table").
        if (bgc_context or {}).get("has_blastp_panel"):
            findings.extend(_evidence_presence_findings(card_md))
        # item 4 (v9.7.323): the named-subject + §4 BLASTp-coverage checks are about the §4's OWN
        # content and self-skip when there is no core grid, so they don't need the panel gate — this
        # lets them fire at receipt (mode_b_receipt) and for core-BLASTp/region-GBK cards that have no
        # separate "panel" artifact, catching a non-compliant card even if the producer skipped verify.
        findings.extend(_section4_named_subject_findings(card_md))
        findings.extend(_section4_blastp_coverage_findings(card_md, bgc_context))
        findings.extend(_section4_complete_blastp_matrix_findings(card_md, bgc_context))
    if check_publication_quality:
        from .modeb_publication_gate import publication_quality_findings
        findings.extend(publication_quality_findings(
            card_md,
            canonical_loci=canonical_loci,
            check_substantive_quality_v2=check_substantive_quality_v2,
            check_semantic_sections_v3=check_semantic_sections_v3,
            check_semantic_comparators_v4=check_semantic_comparators_v4,
            check_semantic_sections_v5=check_semantic_sections_v5,
            check_semantic_decision_chains_v6=check_semantic_decision_chains_v6,
            check_semantic_claim_models_v7=check_semantic_claim_models_v7,
            check_inventory_reconciliation_v8=check_inventory_reconciliation_v8,
            check_selection_process_v9=check_selection_process_v9,
            check_figure_spec_v10=check_figure_spec_v10,
            check_reconciliation_specificity_v11=check_reconciliation_specificity_v11,
        ))
    # v9.7.227: padding lint — advisory, surfaces filler now that char-floors no longer force length.
    findings.extend(_padding_findings(card_md))
    # v9.7.232: KCB-name-as-identity lint — advisory, catches the selvamicin failure mode.
    findings.extend(_kcb_identity_findings(card_md, bgc_context))
    # v9.7.233 readiness lints — bind prose to the deterministic data + to itself
    findings.extend(_phantom_locus_findings(card_md, bgc_context))
    findings.extend(_locus_bgc_mismatch_findings(card_md, bgc_context))   # B1: wrong-BGC attribution
    findings.extend(_panel_absent_claim_findings(card_md, bgc_context))   # B1: result for unrun panel
    findings.extend(_novelty_conservation_findings(card_md, bgc_context))
    findings.extend(_internal_consistency_findings(card_md))
    findings.extend(_fact_binding_findings(card_md, bgc_context))

    return findings


# --- claim-safety lint (v9.7.209, item #58) ----------------------------------
# Enforces the convention documented in docs/MODE_B_CARD_CLAIM_SAFETY_AUDIT.md:
# product-identity language ("produces", "synthesizes", "the strain makes", etc.)
# is forbidden unless the line also carries claim-safe context. The regex + the
# claim-safe exclusion set are lifted from that audit doc, not invented here.
# v9.7.409 CANDIDATE (CLAUDE_409/F2): this authoring-time list stays high-precision (a per-line
# presence test cannot object-check, so bare "secretes/assembles/encodes" would false-positive on
# "secretes proteins" / "encodes a PKS"). Added additively and only where unambiguous: British
# `-ise` (`synthesises`) and `biosynthesi[sz]es`. The wider verb set is handled by the package linter
# (claim_safety_gate.lint_text), which object-checks. Copula identity ("the mature product is
# venezuelin") is handled by _COPULA_IDENTITY_LINE_RE below, which requires a compound-shaped object.
_FORBIDDEN_CLAIM_RE = re.compile(
    r"\bproduces\b|\bsynthesi[sz]es\b|\bbiosynthesi[sz]es\b|is an enediyne|confirmed enediyne|"
    r"identical to (the )?compound|the strain makes",
    re.IGNORECASE)
# v9.7.409 CANDIDATE (CLAUDE_409/F2): copula product-identity at authoring time. Deliberately narrow
# for a presence-style line check: the subject must be a product-noun / BGC id, and the object must
# be a lowercase compound-shaped token (>=5 chars) that is NOT a class/status word, so ordinary
# descriptive copulas ("the cluster is complete", "the region is a lanthipeptide") stay clean while
# "the mature product is venezuelin" is caught. The per-line _CLAIM_SAFE_CONTEXT_RE hedge still
# exempts a framed line ("the product is predicted to be ...").
_COPULA_IDENTITY_LINE_RE = re.compile(
    r"\b(?:BGC\d+|(?:the\s+)?(?:mature\s+|final\s+|end[- ]?)?(?:product|compound|metabolite|molecule))"
    r"\s+(?:is|are|was|were)\s+(?:the\s+|a\s+|an\s+)?([a-z][a-z0-9'\-]{4,})\b",
    re.IGNORECASE)
# Object tokens after the copula that are class/status words, never a specific-compound identity.
_COPULA_LINE_NON_NAME = {
    "predicted", "putative", "candidate", "possible", "likely", "unlikely", "plausible",
    "consistent", "compatible", "similar", "identical", "novel", "present", "absent", "unknown",
    "unresolved", "incomplete", "complete", "intact", "truncated", "partial", "responsible",
    "encoded", "located", "observed", "associated", "required", "expressed", "conserved",
    "distinct", "typical", "atypical", "class", "family", "type", "group", "backbone", "scaffold",
    "pathway", "polyketide", "peptide", "nonribosomal", "ribosomal", "terpene", "terpenoid",
    "siderophore", "lanthipeptide", "enediyne", "capacity", "similarity", "identity",
}
_COPULA_LINE_CLASS_SUFFIX = ("-like", "-type", "-class", "-family", "-forming", "-related")
# v9.7.409 (CLAUDE_409/F2, merged): the riskier production verbs at authoring time, under the SAME strict
# shape the package linter uses — a BARE lowercase, compound-morphology object directly after the verb.
# "secretes venezuelin" fires; "secretes proteins" / "encodes a PKS" / "assembles the scaffold" stay clean.
_STRICT_VERB_LINE_RE = re.compile(
    r"\b(?:secretes|assembles|elaborates|generates|affords|manufactures|encodes)\s+([a-z][a-z0-9'\-]{4,})\b")
# v9.7.409 CANDIDATE (CLAUDE_409/F2): natural-product name morphology — the copula object must read
# like a real compound name ("is venezuelin"/"is bottromycin"), not a status word ("is
# uncharacterised", "is the strongest lead"). Deliberately conservative; the seal-time tools linter
# and the "produces" path remain the primary nets for morphologically-unusual names.
_COPULA_LINE_NP_MORPHOLOGY_RE = re.compile(
    r"(?:mycin|micin|bactin|actin|statin|kacin|rubicin|cin|ycin|chelin|bactam|penem|mide|amide|"
    r"olide|actone|lactone|azole|in|ine|one|ol|ide|osin|toxin|zin|din|tin|pin|nin)$")
_CLAIM_SAFE_CONTEXT_RE = re.compile(
    r"candidate|predicted|putative|possible|does not|not a confirmed|"
    r"capacity consistent|consistent with|would|may |could |"
    r"cannot claim|cannot assert|no claim|not claim|never claim|"
    r"not evidence|no evidence that|whether |hypothes|if this|if the",
    re.IGNORECASE)
# v9.7.257 (B1 residual): a denial that introduces a LIST puts the denial cue on one line and the
# forbidden verb on a following list item — "The evidence does not support:\n(1) …produces X".
# A denial cue ending in a colon governs the items beneath it. Matched only against preceding lines,
# and only when the current line is itself a list item, so an unrelated earlier negation cannot mask
# a real, unhedged claim (the false-negative the NOVELTY_CONTRADICTION windowed guard warned about).
_DENIAL_LIST_INTRO_RE = re.compile(
    r"(?:does not|do not|did not|cannot|can't|no evidence|not support|not confirm|"
    r"are not|is not|none of)[^:]*:\s*$",
    re.IGNORECASE)
_LIST_ITEM_RE = re.compile(r"^\s*(?:[(\[]?\d+[)\].]|[-*•])\s")


def _padding_findings(card_md: str) -> list["Finding"]:
    """v9.7.227: flag padding — content added to occupy space, not to inform. WARN-level,
    advisory. High char-floors used to reward this; now that floors are lowered, this lint
    surfaces the residual filler so authors cut it. Two signals, both measured to correlate
    with expand-to-hit-floor edits: (a) cross-references to OTHER bgc ids that carry no
    evidence about the card in hand, (b) restatement openers that re-say the prior point.
    Reports the padding-sentence count and an approximate % of prose so density is visible."""
    import re as _re
    bodies = extract_section_bodies(card_md)
    # exclude the evidence ledger (§28) and pure-table gene section content
    # §28 (ledger) and §29 (cross-cluster interactions) legitimately reference other
    # BGCs; excluding them stops PAD_SIGNAL false-positives on their core content.
    # MODEB-GATE-P06 (v9.7.331): strip <!-- ... --> author-guidance comments before the padding scan
    # so template comment text is not counted as prose (cross-refs / restatement openers inside a
    # comment are not authored padding).
    # v9.7.380 (AUDIT-380-04): 4 joins 28/29 in the exclusion. The emitted .378b/.379
    # template puts a "Domain phylogeny (KS/AT two-proof - _4D)" partner table inside SS4, whose
    # rows legitimately name OTHER BGC ids. That is template-emitted evidence, not authored
    # padding, and it tripped PAD_SIGNAL on every card built from the real template.
    prose = "\n".join(_strip_html_comments(b) for n, b in bodies.items() if n not in (4, 28, 29))
    sents = [s.strip() for s in _re.split(r"(?<=[.!?])\s+", prose) if len(s.strip()) > 15]
    if not sents:
        return []
    self_ids = set(_re.findall(r"BGC\d+", bodies.get(1, "")))  # this card's own id(s)
    pad = 0
    for s in sents:
        sl = s.lower()
        others = [b for b in _re.findall(r"BGC\d+", s) if b not in self_ids]
        if others and "blast" not in sl and "kcb" not in sl and "cohort" not in sl \
                and not any(c in sl for c in ("unlike", "whereas", "in contrast", "rather than", "as opposed to")):
            pad += 1; continue
        if _re.match(r"(read together|in practice|practically|concretely|taken together|"
                     r"put another way|in other words|the practical (point|upshot|consequence))", sl):
            pad += 1
    if pad == 0:
        return []
    pct = round(100 * pad / len(sents))
    return [_mk("WARN", "PAD_SIGNAL", None, "0 padding sentences",
                f"{pad} sentences (~{pct}% of prose)",
                f"{pad} sentence(s) (~{pct}% of prose) read as padding — cross-references to "
                f"other BGCs that add no evidence here, or restatement openers that re-say the "
                f"prior point. Cut to the evidence; a dense short card beats a padded long one.")]




def _kcb_identity_findings(card_md: str, bgc_context: Optional[dict] = None) -> list["Finding"]:
    """v9.7.232: flag a KnownClusterBlast comparator name asserted as the product's
    identity. KCB is cluster-backbone similarity, not per-protein homology; asserting
    'is <kcb>' / '<kcb>-class' without a hedge, especially when the per-gene BLASTp genus
    differs from the KCB organism genus, is the error that mis-called BGC046 selvamicin.
    WARN-level, advisory. Needs bgc_context['kcb_top'] to know the comparator name."""
    import re as _re
    ctx = bgc_context or {}
    kcb_top = str(ctx.get("kcb_top") or ctx.get("KCB_top") or "")
    # extract the compound name from 'BGCxxxxxxx.n | <name> | ...'
    m = _re.search(r"\|\s*([A-Za-z][A-Za-z0-9 /\-]+?)\s*\|", kcb_top)
    if not m:
        return []
    name = m.group(1).strip()
    first = _re.split(r"[ /]", name)[0]
    if len(first) < 5:
        return []
    # NB (v9.7.233): '-class' is deliberately NOT a hedge here. In the *general* claim-safety
    # linter '<compound>-class' is safe capacity language, but in THIS lint the trigger token is
    # always a specific KCB comparator name (e.g. 'selvamicin'), and asserting '<comparator>-class'
    # is exactly the BGC046 overclaim this lint exists to catch — KCB is backbone similarity, so the
    # class attribution itself is unsupported when the per-gene BLASTp genus differs. '-adjacent',
    # 'family', 'neighbour', 'backbone', 'similarity', 'comparator' remain genuine hedges.
    # MODEB-GATE-P07 (v9.7.331): a KCB comparator name is claim-SAFE when the card hedges it
    # (comparator / class-or-family anchor / -like / similarity) OR explicitly REJECTS transferring
    # it (reject / overturn / not claimed / not transferred / downgrade). Recognise those as hedges
    # so a correctly-framed or rejected comparator name stops tripping KCB_IDENTITY_RISK (BGC017
    # loseolamycin "backbone similarity, not identity"; BGC018 "the aborycin name must not be
    # transferred"). NB '-like' is a genuine similarity hedge and is added here; '-class' remains
    # NOT a hedge (that is the BGC046 overclaim this lint exists to catch).
    hedges = ("not ", "similarity", "comparator", "backbone", "kcb", "-adjacent",
              "family", "neighbour", "not identity", "retract", "mis-fram",
              "-like", "anchor", "class anchor", "family anchor",
              "reject", "overturn", "not claimed", "not transferred", "downgrad")
    bodies = extract_section_bodies(card_md)
    flagged = []
    for num, body in bodies.items():
        for sent in _re.split(r"(?<=[.!?])\s+", body):
            sl = sent.lower()
            if first.lower() not in sl:
                continue
            # an identity assertion: 'is <name>' or 'a <name>' or '<name> cluster/producer'
            asserts = bool(_re.search(rf"\bis (a |an |the )?{_re.escape(first.lower())}\b", sl)
                           or _re.search(rf"\b{_re.escape(first.lower())} (cluster|producer|pathway)\b", sl))
            if asserts and not any(h in sl for h in hedges):
                flagged.append((num, sent.strip()[:80]))
    if not flagged:
        return []
    where = ", ".join(f"§{n}" for n, _ in flagged[:4])
    return [_mk("WARN", "KCB_IDENTITY_RISK", flagged[0][0],
                f"comparator '{name}' asserted as identity",
                f"{len(flagged)} place(s) ({where})",
                f"The KCB comparator '{name}' appears asserted as the product's identity "
                f"({where}) without a similarity/comparator hedge. KCB is backbone similarity, "
                f"not homology — confirm the per-gene BLASTp genus matches the comparator's "
                f"producer before naming it (the BGC046/selvamicin failure mode).")]

# ---------------------------------------------------------------------------
# v9.7.233 readiness lints — the correctness layer that binds card prose to the
# deterministic data (gene_context / manifest / source_scans) and to itself.
# The depth gate scores length; these score correctness. They target the real
# failures: the BGC043 novelty-over-claim (asserted "structural novelty / rare
# halogenase" at 100% identity) and the ctg66_8 "1 TTA in §28, 7 TTA in §15"
# contradiction. All WARN-level (advisory in lint_card); the readiness *state*
# (readiness_state) is what gates presentation on these codes.
# ---------------------------------------------------------------------------
_NOVELTY_ID_FLOOR = 90.0   # median per-gene %id at/above which novelty/rarity is contradicted
_NOVELTY_PATTERNS = [
    r"structural novelty", r"meaningful (?:structural )?novelt",
    r"novel (?:compound|scaffold|cluster|chemistr|natural product|metabolite|architecture)",
    r"genuinely novel", r"standout novelty", r"scaffold[- ]novel",
    r"rare (?:tailoring|feature|enzyme|halogenase|cluster|architecture)",
    r"isolate[- ]specific", r"bee[- ]specific",
    r"unique to (?:this|the) (?:strain|isolate)", r"horizontal(?:ly)? acqui",
]
_NOVELTY_ALLOW = [   # allowed even under high conservation: uncharacterised != novel machinery
    r"no mibig", r"uncharacteris", r"uncharacteriz", r"no characteris",
    r"not novel", r"no(?:t)? (?:a )?(?:bee[- ]specific|isolate[- ]specific)",
    r"no (?:characterised )?reference cluster",
]
_NEG_BEFORE = r"(?:not|no|isn'?t|aren'?t|never|un)\W+$"
# Sentence-level denial/contrast cues: a sentence that DENIES or CONTRASTS novelty is not an
# assertion of it. Fixes the false positives on disciplined cards ("not a novel scaffold",
# "not an isolate-specific ... one", "rather than a bee-specific locus", "no meaningful
# scaffold-novelty score") that the 12-char prefix guard missed because of an intervening
# article/adverb ("a", "an", "meaningful") or a "rather than" construction.
_NOVELTY_DENIAL = [
    r"\bnot\b", r"n'?t\b", r"\bno\b", r"rather than", r"instead of",
    r"\bconserved\b", r"genus[- ]conserved", r"shared (?:genus )?capacity",
    r"known (?:compound|metabolite|class)", r"not novel", r"no meaningful",
]


def _novelty_conservation_findings(card_md: str, bgc_context: Optional[dict] = None) -> list["Finding"]:
    """Flag novelty/rarity/isolate-specificity asserted while the per-gene conservation
    data say genus-conserved (median identity >= floor). Data-relative: a divergent
    cluster is NOT flagged, and 'no MIBiG / compound uncharacterised' is allowed. Reads
    bgc_context['conservation_median_id'] (nr overlay preferred, else ClusterBlast)."""
    import re as _re
    ctx = bgc_context or {}
    source_status = str(ctx.get("conservation_source_status") or "").strip().upper()
    if source_status == "INVALID":
        invalid_source = str(ctx.get("conservation_invalid_source") or "conservation source").strip()
        return [_mk(
            "WARN", "CONSERVATION_EVIDENCE_INVALID", 4,
            "admitted or explicitly unavailable per-locus conservation evidence",
            f"INVALID ({invalid_source})",
            f"Per-locus conservation evidence is INVALID in {invalid_source}; no median or "
            "conservation-relative novelty conclusion was derived. Repair or re-ingest the "
            "source before interpreting sequence conservation or divergence.",
        )]
    med = ctx.get("conservation_median_id")
    if med is None or float(med) < _NOVELTY_ID_FLOOR:
        return []
    bodies = extract_section_bodies(card_md)
    flagged = []
    for num, body in bodies.items():
        # MODEB-GATE-P06 (v9.7.331): the §24 template's own guidance comment names a 'novel compound'
        # placeholder; scan authored prose only, not the template's <!-- ... --> comment text.
        body = _strip_html_comments(body)
        for sent in _re.split(r"(?<=[.!?])\s+", body):
            sl = sent.lower()
            if any(_re.search(a, sl) for a in _NOVELTY_ALLOW):
                continue
            for pat in _NOVELTY_PATTERNS:
                m = _re.search(pat, sl)
                if not m:
                    continue
                if _re.search(_NEG_BEFORE, sl[max(0, m.start() - 12):m.start()]):
                    continue
                # Local-window denial/contrast guard: a denial cue that FRAMES this specific
                # claim (within ~40 chars before / ~20 after — covers "not a novel scaffold",
                # "rather than a bee-specific locus" style constructions the narrow 12-char
                # lookback above misses) means the card is denying novelty here, not asserting
                # it. Windowed rather than sentence-wide (2026-07-08 fix): a sentence-wide check
                # let an unrelated negation elsewhere in the same sentence ("This is not a
                # housekeeping gene, but the scaffold is a novel... architecture with no known
                # relatives") silently mask a real, unhedged claim later in that sentence —
                # confirmed false negative, now fixed. See test_novelty_unrelated_denial_does_not_mask_real_claim.
                window = sl[max(0, m.start() - 40):min(len(sl), m.end() + 20)]
                if any(_re.search(d, window) for d in _NOVELTY_DENIAL):
                    continue
                flagged.append((num, sent.strip()[:80]))
                break
    if not flagged:
        return []
    where = ", ".join(f"§{n}" for n, _ in flagged[:4])
    n_ms = ctx.get("multispecies_hits", 0)
    _bg = ctx.get("conservation_background_id")
    _sat = ctx.get("conservation_saturated")
    _bg_status = str(ctx.get("conservation_background_status") or "").strip().upper()
    _conservation_read = "genus-conserved"
    _reframe = "reframe to 'compound uncharacterised, machinery genus-common'."
    _bg_note = ""
    if _bg is not None:
        _delta = round(med - _bg, 1)
        _bg_note = (f" Genome background median is {_bg}% (n={ctx.get('conservation_background_n','?')}), "
                    f"so this BGC sits {_delta:+} vs its own genome.")
        if _sat:
            _bg_note += (" NOTE: the background itself clears the 90% floor — a near-relative is in the "
                         "reference DB, so rank-1 identity is saturated and this verdict carries little "
                         "novelty signal on its own. Judge distinctiveness by the delta, not the absolute.")
    elif _bg_status == "INVALID":
        _conservation_read = ("high closest-hit similarity; genome-relative conservation is not "
                              "interpretable")
        _reframe = ("reframe to 'compound uncharacterised; the target has high closest-hit "
                    "similarity, while genome-relative machinery conservation remains unresolved "
                    "pending an admitted background'.")
        _bg_note = (" Genome background status is INVALID because the background could not be read or "
                    "admitted. The valid target observation is retained, but it cannot support a "
                    "genome-relative conservation conclusion until the background is repaired.")
    elif _bg_status == "UNAVAILABLE":
        _conservation_read = ("high closest-hit similarity; genome-relative conservation is not "
                              "interpretable")
        _reframe = ("reframe to 'compound uncharacterised; the target has high closest-hit "
                    "similarity, while genome-relative machinery conservation remains unresolved "
                    "pending an admitted background'.")
        _bg_note = (" Genome background status is UNAVAILABLE because no admitted genome-wide nr "
                    "comparison was available. The valid target observation is retained, but it "
                    "cannot support a genome-relative conservation conclusion.")
    return [_mk("WARN", "NOVELTY_CONTRADICTION", flagged[0][0],
                "novelty consistent with conservation data",
                f"{len(flagged)} place(s) ({where}); median id {med}%",
                f"Novelty/rarity asserted ({where}) but per-gene identity median is {med}% "
                f"(n={ctx.get('conservation_n_genes', '?')} genes"
                f"{', MULTISPECIES hits present' if n_ms else ''}) — {_conservation_read}.{_bg_note} "
                f"'No MIBiG match' makes the COMPOUND uncharacterised, not the MACHINERY novel; "
                f"{_reframe} "
                f"(BGC043 novelty-over-claim failure mode.)")]


_CONTRAST_CUES = ("unlike", "whereas", "in contrast", "rather than", "as opposed to",
                  "compared to", "compared with", "comparator", "versus", " vs ", " vs.")
_MIBIG_REF = re.compile(r"BGC0\d{5,}")  # MIBiG accession = a comparator, not this BGC

def _self_numbers(card_md, pattern):
    """Numbers matching `pattern`, taken ONLY from sentences that are not contrastive/
    comparator references (which cite OTHER clusters, not this one).

    Markdown ATX headers and HTML author-comments are stripped BEFORE scanning: a
    canonical section title such as "## §35 Protocluster decomposition" (or its author
    guidance comment) otherwise matches r"(\\d+)\\s*protoclusters?" and injects a phantom
    "35" into the protocluster count on every compliant §1–§48 card. The section number
    is structure, not a self-stated fact, so it must not be counted."""
    import re as _re
    # Drop ATX headers (the "## §NN Title" lines carry the section number) and HTML
    # comments (author-guidance stubs echo the section title) so neither is scanned.
    _no_headers = _re.sub(r"(?m)^\s{0,3}#{1,6}[ \t].*$", "", card_md)
    _no_comments = _re.sub(r"<!--.*?-->", "", _no_headers, flags=_re.S)
    vals = set()
    for sent in _re.split(r"(?<=[.!?])\s+", _no_comments):
        sl = sent.lower()
        if any(c in sl for c in _CONTRAST_CUES) or _MIBIG_REF.search(sent):
            continue
        for x in _re.findall(pattern, sent, _re.I):
            vals.add(int(x))
    return vals


def _internal_consistency_findings(card_md: str) -> list["Finding"]:
    """Flag the same keyed fact stated two ways in one card (per-gene TTA, bldA tier,
    protocluster count). The ctg66_8 '1 TTA in §28, 7 TTA in §15' contradiction."""
    import re as _re
    out: list["Finding"] = []
    tta: dict[str, set] = {}
    for m in _re.finditer(r"(ctg\d+_\d+)[^.|\n]{0,60}?(\d+)\s*TTA", card_md, _re.I):
        tta.setdefault(m.group(1).lower(), set()).add(int(m.group(2)))
    for m in _re.finditer(r"(\d+)\s*TTA\s*codons?\s*in\s*(ctg\d+_\d+)", card_md, _re.I):
        tta.setdefault(m.group(2).lower(), set()).add(int(m.group(1)))
    for gene, vals in tta.items():
        if len(vals) > 1:
            out.append(_mk("WARN", "INTERNAL_CONTRADICTION", None, "one TTA count per gene",
                           f"{gene}: {sorted(vals)}",
                           f"{gene}: TTA count stated as {sorted(vals)} in different sections — reconcile."))
    tiers = {g for pair in _re.findall(r"bld[Aa]\s*tier\s*(T\d)|\btier\s*(T\d)\b", card_md) for g in pair if g}
    if len(tiers) > 1:
        out.append(_mk("WARN", "INTERNAL_CONTRADICTION", None, "one bldA tier",
                       f"{sorted(tiers)}", f"bldA tier stated as {sorted(tiers)} — a card must commit to one."))
    pcs = _self_numbers(card_md, r"(\d+)\s*protoclusters?")
    if len(pcs) > 1:
        out.append(_mk("WARN", "INTERNAL_CONTRADICTION", None, "one protocluster count",
                       f"{sorted(pcs)}", f"protocluster count stated as {sorted(pcs)} — reconcile."))
    return out


def _fact_binding_findings(card_md: str, bgc_context: Optional[dict] = None) -> list["Finding"]:
    """Flag a card fact that disagrees with its deterministic source: per-gene TTA vs
    gene_context, CDS count, protocluster count, edge status. Binds prose to the data."""
    import re as _re
    ctx = bgc_context or {}
    out: list["Finding"] = []
    tta_true = ctx.get("tta_by_gene") or {}
    claims: dict[str, set] = {}
    for m in _re.finditer(r"(ctg\d+_\d+)[^.|\n]{0,60}?(\d+)\s*TTA", card_md, _re.I):
        claims.setdefault(m.group(1).lower(), set()).add(int(m.group(2)))
    for m in _re.finditer(r"(\d+)\s*TTA\s*codons?\s*in\s*(ctg\d+_\d+)", card_md, _re.I):
        claims.setdefault(m.group(2).lower(), set()).add(int(m.group(1)))
    for gene, vals in claims.items():
        if gene in tta_true:
            wrong = [v for v in vals if v != tta_true[gene]]
            if wrong:
                out.append(_mk("WARN", "FACT_MISMATCH", 28, f"{gene}={tta_true[gene]} TTA",
                               f"{sorted(vals)}",
                               f"{gene}: card says {sorted(vals)} TTA, gene_context says {tta_true[gene]}."))
    cds_true = ctx.get("cds_count")
    cds_ment = _self_numbers(card_md, r"(\d+)\s*CDS\b")
    if cds_true and cds_ment and int(cds_true) not in cds_ment:
        out.append(_mk("WARN", "FACT_MISMATCH", 4, f"{cds_true} CDS", f"{sorted(cds_ment)}",
                       f"card states {sorted(cds_ment)} CDS; gene_context has {cds_true}."))
    pc_true = ctx.get("protocluster_count")
    pcs = _self_numbers(card_md, r"(\d+)\s*protoclusters?")
    if pc_true and pcs and int(pc_true) not in pcs:
        out.append(_mk("WARN", "FACT_MISMATCH", 5, f"{pc_true} protoclusters", f"{sorted(pcs)}",
                       f"card states {sorted(pcs)} protoclusters; manifest says {pc_true}."))
    edge_true = str(ctx.get("edge_status") or "").lower()
    if edge_true:
        m = _re.search(r"boundary[:\s\*]+(interior|edge|full-contig)", card_md.lower())
        if m and m.group(1) != edge_true:
            out.append(_mk("WARN", "FACT_MISMATCH", 3, f"boundary {edge_true}", m.group(1),
                           f"§3 boundary '{m.group(1)}' != manifest edge_status '{edge_true}'."))
    return out


_READINESS_BLOCKING = {"NOVELTY_CONTRADICTION", "INTERNAL_CONTRADICTION", "FACT_MISMATCH",
                       "PHANTOM_LOCUS"}


def readiness_state(findings, quality_tier: Optional[str] = None) -> str:
    """Return a mechanical validation state, never an owner/release state.

    Character/depth diagnostics and deterministic lints cannot confer scientific
    acceptance, integration, rendering approval, release approval, or publication approval.
    """
    findings = list(findings or [])
    if any(f.get("severity") == "ERROR" for f in findings):
        return "DRAFT"
    if quality_tier in (None, "STUB", "UNKNOWN"):
        return "DRAFT"
    if {f.get("code") for f in findings} & _READINESS_BLOCKING:
        return "STRUCTURE_VALIDATED_WITH_SCIENCE_HOLDS"
    return "EVIDENCE_MATRIX_VALIDATED"


def _claim_safety_findings(card_md: str) -> list["Finding"]:
    """Flag forbidden product-identity phrasing (item #58). WARN, not ERROR:
    a false positive on legitimate quoted text should not refuse a card, but
    the author must see it. Lines carrying claim-safe context are excluded."""
    out: list[Finding] = []
    lines = card_md.splitlines()
    for i, line in enumerate(lines, 1):
        # A per-line claim-safe hedge exempts the whole line for BOTH the verb and copula paths.
        if _CLAIM_SAFE_CONTEXT_RE.search(line):
            continue
        # v9.7.257: multi-line denial-list guard. If this line is a list item and a denial cue
        # ending in a colon governs it (within the two preceding non-blank lines), it's a correct
        # denial — "does not support: (1) …produces X" — not a claim. See _DENIAL_LIST_INTRO_RE.
        if _LIST_ITEM_RE.match(line):
            prev = [ln for ln in lines[max(0, i - 3):i - 1] if ln.strip()][-2:]
            if any(_DENIAL_LIST_INTRO_RE.search(ln) for ln in prev):
                continue
        m = _FORBIDDEN_CLAIM_RE.search(line)
        if m:
            out.append(_mk(
                "WARN", "CLAIM_SAFETY", None, "capacity-consistent phrasing",
                m.group(0),
                f"line {i}: '{m.group(0)}' is product-identity language. "
                f"Use 'capacity consistent with' / 'predicted' / 'candidate'. "
                f"See docs/MODE_B_CARD_CLAIM_SAFETY_AUDIT.md."))
            continue
        # v9.7.409 CANDIDATE (CLAUDE_409/F2): copula product-identity ("the mature product is
        # venezuelin"). Same per-line hedge + denial-list guard as the verb path above; only fires
        # when the copula object is a compound-shaped, non-class token.
        cm = _COPULA_IDENTITY_LINE_RE.search(line)
        if cm:
            name = cm.group(1).lower()
            if (name in _COPULA_LINE_NON_NAME or name.endswith(_COPULA_LINE_CLASS_SUFFIX)
                    or not _COPULA_LINE_NP_MORPHOLOGY_RE.search(name)):
                continue
            out.append(_mk(
                "WARN", "CLAIM_SAFETY", None, "capacity-consistent phrasing",
                cm.group(0),
                f"line {i}: '{cm.group(0)}' is copula product-identity language. "
                f"Use 'capacity consistent with' / 'predicted' / 'candidate'. "
                f"See docs/MODE_B_CARD_CLAIM_SAFETY_AUDIT.md."))
            continue
        # v9.7.409 (CLAUDE_409/F2, merged): strict-shape production verbs (see _STRICT_VERB_LINE_RE).
        sm = _STRICT_VERB_LINE_RE.search(line)
        if sm:
            name = sm.group(1).lower()
            if (name in _COPULA_LINE_NON_NAME or name.endswith(_COPULA_LINE_CLASS_SUFFIX)
                    or not _COPULA_LINE_NP_MORPHOLOGY_RE.search(name)):
                continue
            out.append(_mk(
                "WARN", "CLAIM_SAFETY", None, "capacity-consistent phrasing",
                sm.group(0),
                f"line {i}: '{sm.group(0)}' is product-identity language (named compound after a "
                f"production verb). Use 'capacity consistent with' / 'predicted' / 'candidate'. "
                f"See docs/MODE_B_CARD_CLAIM_SAFETY_AUDIT.md."))
    return out


# --- citation / provenance lint (v9.7.209, item #59) -------------------------
# A BGC mention should carry a node·region locator and a provenance tag. This is
# a heuristic: it flags bare "BGCddd" tokens that are NOT immediately followed by
# a node·region parenthetical, and cards that never tag provenance at all.
# bare BGC id = BGCddd NOT followed by a node·region parenthetical, and NOT part of a
# hyphenated compound word (e.g. "BGC039-specific" is prose, not a citation-requiring mention).
_BARE_BGC_RE = re.compile(r"\bBGC\d{3}(?![-\w])(?!\s*\((?:NODE|NODE_|ctg|[^)]*·))")
_PROVENANCE_RE = re.compile(
    r"store-backed|store backed|reconstructed|corpus|derived|"
    r"observed|inferred|computed|assumed",
    re.IGNORECASE)


_LOCATOR_BGC_RE = re.compile(r"\bBGC(\d{3})\s*\((?:NODE|NODE_|ctg|[^)]*·)", re.IGNORECASE)
_ANY_BGC_RE = re.compile(r"\bBGC(\d{3})\b", re.IGNORECASE)
# v9.7.395: both were case-sensitive, so a lowercase/mixed-case citation (e.g. "bgc039") never
# entered either set -- the MISSING_LOCATOR check (item #59, this file's own citation/provenance
# lint) silently never fired for it at all, the same case-insensitivity bypass already fixed in
# the sibling bgc_citation_gate.py / sapote_hooks/bgc_citation_node_guard.py gates. _norm_bgc()
# (used at the other two call sites of _ANY_BGC_RE) already strips to bare digits and lowercases
# its own output, so it was already case-agnostic on its input -- only these two patterns weren't.


# v9.7.338 (MB-01): the §4 evidence gate could still be satisfied by a bare integer that is really an
# aa-length / TTA count / coordinate, because _S4_PCTID_RE keeps a bare-number alternative. That
# alternative is load-bearing for REAL cards — they legitimately write identity as a bare number under
# a "%id" column header (see the shipped exemplars) — so it cannot simply be deleted. The fix splits the
# two jobs the one regex was doing:
#   - DETECTION ("is this a BLASTp table at all?") requires an unambiguous percent-SIGN value, OR a
#     bare number sitting in a column whose HEADER literally names identity/%id/BLASTp.
#   - COVERAGE ("does this core row carry a real %id?") accepts a bare number only when it is in an
#     identity-named column of the row's own table (never an aa/coord/TTA column).
# A prose mention of "BLASTp" is no longer enough to qualify a §4 as carrying evidence.
_S4_PCTID_PCT_RE = re.compile(r"(?<![\d.])\d{1,3}(?:\.\d+)?\s*%")           # explicit percent-sign form
_S4_IDENT_HDR_RE = re.compile(r"%\s*id\b|%id|percent\s*id|\bpident\b|\bident(?:ity)?\b", re.I)
_S4_HOMOLOGY_HDR_RE = re.compile(
    r"blastp|closest\s+match|top\s+hit|nr\s+hit|%\s*id\b|%id|percent\s*id|\bpident\b|\bident(?:ity)?\b",
    re.I)
_S4_CELL_NUM_RE = re.compile(r"\d")


def _split_pipe_cells(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def _is_md_sep_row(line: str) -> bool:
    """A markdown table separator row: every non-empty cell is dashes with optional colons."""
    if "-" not in line or "|" not in line:
        return False
    cells = [c for c in _split_pipe_cells(line) if c]
    return bool(cells) and all(re.fullmatch(r":?-{1,}:?", c) for c in cells)


def _s4_pipe_tables(text: str):
    """Yield (header_cells, [(raw_line, cells), ...]) for each markdown pipe table — a pipe row
    immediately followed by a |---| separator row. This anchors the header/identity checks to the
    actual TABLE header, so prose that merely mentions 'BLASTp' can no longer qualify a §4 (MB-01)."""
    lines = text.splitlines()
    i, n = 0, len(lines)
    while i < n:
        ln = lines[i]
        if "|" in ln and not _is_md_sep_row(ln) and i + 1 < n and _is_md_sep_row(lines[i + 1]):
            header = _split_pipe_cells(ln)
            rows = []
            j = i + 2
            while j < n and "|" in lines[j] and lines[j].strip() and not _is_md_sep_row(lines[j]):
                rows.append((lines[j], _split_pipe_cells(lines[j])))
                j += 1
            yield header, rows
            i = j
        else:
            i += 1


def _s4_identity_cols(header_cells: list[str]) -> list[int]:
    """Indices of table columns whose header literally names a percent-identity value."""
    return [i for i, c in enumerate(header_cells) if _S4_IDENT_HDR_RE.search(c)]


def _has_blastp_table(card_md: str) -> bool:
    """True if §4 carries a reconciled per-gene BLASTp table — the evidence artifact that makes a
    lead card trustworthy (antiSMASH Pfam is a hypothesis; BLASTp per-gene is the homology channel).
    Detects a markdown table in §4 whose header names a BLASTp/identity/closest-match column, or the
    explicit reconciled verdicts (CONFIRM/REFINE/OVERTURN) that only the per-gene reconciliation emits."""
    import re as _re
    s4 = extract_section_bodies(card_md).get(4, "")
    if not s4:
        return False
    # v9.7.335: the bare-verdict branch made this unfailable. "We could not confirm any homolog"
    # matched \bconfirm\b and passed a card with zero BLASTp; so did the pipeline's OWN unauthored
    # §4 skeleton, whose guidance text contains "CONFIRM / REFINE / OVERTURN" as plain body text.
    # v9.7.338 (MB-01): .335 stripped only the locus tag, but the bare-number alternative of
    # _S4_PCTID_RE was still satisfied by an aa length / coordinate / TTA count, and the header branch
    # accepted a bare "blastp" mentioned anywhere in the §4 PROSE. Both are closed below.
    s4_stripped = _strip_html_comments(s4)
    # (A) a locus-bearing row carrying an explicit percent-SIGN identity value — unambiguous. A bare
    #     integer is NOT accepted here (it is indistinguishable from aa/coord/TTA).
    for line in s4_stripped.splitlines():
        if "|" in line and _LOCUS_RE.search(line) and _S4_PCTID_PCT_RE.search(_s4_strip_locus(line)):
            return True
    # (B) a real homology TABLE: its actual HEADER ROW (not arbitrary prose) names a BLASTp/identity/
    #     %id column, and a data row carries an identity value — a percent-sign form anywhere, or a
    #     bare number in one of that table's identity-named columns.
    for header, rows in _s4_pipe_tables(s4_stripped):
        if not any(_S4_HOMOLOGY_HDR_RE.search(c) for c in header):
            continue
        ident_idxs = _s4_identity_cols(header)
        for raw, cells in rows:
            if _S4_PCTID_PCT_RE.search(_s4_strip_locus(raw)):
                return True
            if any(i < len(cells) and _S4_CELL_NUM_RE.search(cells[i]) for i in ident_idxs):
                return True
    return False


def _evidence_presence_findings(card_md: str) -> list["Finding"]:
    """v9.7.229: when the strain has a BLASTp panel, §4 must present the reconciled per-gene closest-match
    table. This is the evidence-presence bar the padding fix recommended — length is not a proxy for
    quality; evidence artifacts are. WARN-level (advisory), so it flags the omission without refusing."""
    if _has_blastp_table(card_md):
        return []
    return [_mk("WARN", "EVIDENCE_GAP", 4, "per-gene BLASTp table present",
                "§4 has no reconciled BLASTp table",
                "strain has a BLASTp panel but §4 omits the reconciled per-gene closest-match table "
                "(antiSMASH Pfam calls are a hypothesis, not function — run `mamey blastp-online` and "
                "author §4 from the reconciled CONFIRM/REFINE/OVERTURN calls). Evidence presence, not "
                "length, is the quality bar.")]

_GENUS_RE = re.compile(r"\b(Streptomyces|Amycolatopsis|Saccharopolyspora|Nocardia|Micromonospora|"
                       r"Kitasatospora|Actinomadura|Kribbella|Pseudonocardia|Streptosporangium|"
                       r"Salinispora|Nocardiopsis|Actinophytocola|Sciscionella|uncultured|Candidatus)\b")
_BRACKET_ORG_RE = re.compile(r"\[\*{0,2}[A-Z][a-z][a-z.]")


def _section4_named_subject_findings(card_md: str) -> list["Finding"]:
    """v9.7.322: §4 nr hits must name their subject organism — the tell that the author used the
    full package-tagged hittable WITH --xml, not a bare-accession/thin source. A §4 that carries
    CONFIRM/REFINE/OVERTURN verdicts but zero organism names came from a source without subject
    descriptions (no --xml) or the wrong thin store — the recurring Mode-B failure. WARN (advisory)."""
    s4 = extract_section_bodies(card_md).get(4, "")
    if not s4 or not _has_blastp_table(card_md):
        return []  # a missing §4 table is _evidence_presence_findings' job, not this one
    if _BRACKET_ORG_RE.search(s4) or _GENUS_RE.search(s4):
        return []
    return [_mk("WARN", "SUBJECTS_UNDESCRIBED", 4, "§4 nr hits name the subject organism",
                "§4 has verdicts but no named nr subjects",
                "§4 carries a reconciled table/verdicts but none of the BLASTp hits name their nr "
                "subject organism (e.g. 'type I PKS [Streptomyces sp.]'). That is the signature of a "
                "bare-accession source or a BLASTp run without --xml. Re-run `mamey blastp-online "
                "--xml` (or pull the full package-tagged wave-2 hittable + its BlastXML2 from the "
                "vault) and author §4 from named subjects — a bare accession is not an interpretable hit.")]


# v9.7.322 (§4_BLASTP_COVERAGE, reconciled with the other chat's Mode-B investigation): a §4 can
# carry a table + prose that still rests on antiSMASH-Pfam only ("pending BLASTp"), which the depth
# gate grades on length and lets pass. This gate demands the evidence: core rows must carry a real
# per-gene BLASTp signal (a %id value AND a CONFIRM/REFINE/OVERTURN reconciliation). WARN-first
# (calibration): all codes emit WARN; BLASTP_ABSENT is the promote-to-ERROR candidate after one pass
# over the exemplar set + current authored cards. The honest "I couldn't run it — here's the data I
# need" path (a DATA_REQUESTED token in the card) passes with an acknowledged WARN, never a hard fail.
_S4_RECON_RE = re.compile(r"\b(CONFIRM|REFINE|OVERTURN)\b")
# v9.7.335: the second alternative (a bare number) was satisfied by the digits inside the LOCUS
# TAG itself — a row is only tested when _LOCUS_RE (ctg\d+_\d+) matched, so "ctg13_108" supplied
# the "13". Verified over all 2438 real locus tags in three sealed packages: ZERO rows where the
# clause was not already satisfied by the tag alone, i.e. the coverage half of the gate could
# never fail. The regex itself is unchanged (real cards legitimately put the identity as a bare
# number under a "%id" column header); instead every caller strips the locus tag from the row
# first, via _s4_strip_locus, so the tag can no longer supply the digits.
_S4_PCTID_RE = re.compile(r"(?<![\d.])\d{1,3}(?:\.\d)?\s*%|(?<![\d.])\d{1,3}(?:\.\d)?(?![\d])")


def _s4_strip_locus(row: str) -> str:
    """Remove locus tags (ctg12_34) and node names from a §4 row before testing it for a percent
    identity, so a row cannot satisfy the %id requirement with its own identifier's digits."""
    out = _LOCUS_RE.sub(" ", row)
    return re.sub(r"NODE_\d+(?:_[A-Za-z]+_[\d.]+)*", " ", out)
_S4_CORE_MARK_RE = re.compile(r"\u25cf")
_S4_REQUEST_RE = re.compile(
    r"REQUEST:|BLASTp\s+pending|requested from the operator|blastp[-\s]pending|data\s+requested|"
    r"awaiting.*blastp|request(?:ed|ing)?\s+(?:the\s+)?(?:region\s+gbk|per-gene blastp|blastp)", re.I)
_S4_COVERAGE_FLOOR = 0.5
# MODEB-GATE-P08 (v9.7.331): cores explicitly flagged nr-pending are a KNOWN pending channel (the
# large NRPS/PKS "money" cores too big/divergent for Swiss-Prot), not an authoring gap. Tokens are
# the pre-annotation's own: "DATA REQUEST (nr)" and "no current-assembly Swiss-Prot hit".
_S4_NR_PENDING_RE = re.compile(
    r"DATA\s+REQUEST\s*\(\s*nr\s*\)|no\s+current-assembly\s+Swiss-?Prot\s+(?:hit|row)|"
    r"\bnr[-\s]pending\b|\breference[-\s]dark\b", re.I)


def _section4_blastp_coverage_findings(card_md: str, bgc_context: Optional[dict] = None) -> list["Finding"]:
    """WARN-first §4 per-gene-BLASTp coverage gate. Core rows must carry %id + a reconciliation token.
    Denominator = the package's rule-based core count when the context supplies one, else the card's
    own \u25cf-marked core rows (so the check is self-contained even without a package). Silent when no
    core grid is detectable (RiPP/siderophore §4s use a different evidence shape — cannot judge)."""
    import math as _math
    s4 = extract_section_bodies(card_md).get(4, "")
    if not s4:
        return []
    rows = [ln for ln in s4.splitlines() if ln.strip().startswith("|") and _LOCUS_RE.search(ln)]
    core_rows = [r for r in rows if _S4_CORE_MARK_RE.search(r)] or rows
    n_card_cores = len(core_rows)
    if n_card_cores == 0:
        return []  # no core locus-grid to judge (EVIDENCE_GAP covers "no table at all")
    # v9.7.335: strip the locus tag before the %id test — otherwise the tag's own digits satisfy it.
    # v9.7.338 (MB-01): a bare number counts as %id ONLY when it sits in an identity-named column of
    # the row's own table. An aa length / coordinate / TTA count no longer satisfies the clause, so a
    # Pfam-only §4 that sprinkles CONFIRM into its rows can no longer read as covered.
    _ident_by_row: dict[str, tuple[list[int], list[str]]] = {}
    for _hdr, _trows in _s4_pipe_tables(s4):
        _idxs = _s4_identity_cols(_hdr)
        for _raw, _cells in _trows:
            _ident_by_row[_raw] = (_idxs, _cells)

    def _row_has_real_pctid(r: str) -> bool:
        if _S4_PCTID_PCT_RE.search(_s4_strip_locus(r)):
            return True  # an explicit percent-sign value anywhere on the row
        entry = _ident_by_row.get(r)
        if entry:
            idxs, cells = entry
            return any(i < len(cells) and _S4_CELL_NUM_RE.search(cells[i]) for i in idxs)
        return False

    covered = sum(1 for r in core_rows
                  if _S4_RECON_RE.search(r) and _row_has_real_pctid(r))
    ctx = bgc_context or {}
    ctx_cores = ctx.get("n_core_genes") or ctx.get("core_gene_count") or 0
    n_cores = max(int(ctx_cores or 0), n_card_cores)
    # MODEB-GATE-P08 (v9.7.331): don't count nr-pending cores against the coverage floor. The big
    # NRPS/PKS cores marked "DATA REQUEST (nr)" / "no current-assembly Swiss-Prot hit" carry no %id
    # by data gap, not by authoring — counting them dragged BLASTP_THIN below floor cohort-wide with
    # no clearing path until the nr back-fill lands. Subtract them from the denominator (never below
    # the count actually covered, so the ratio stays sane).
    nr_pending = sum(1 for r in core_rows if _S4_NR_PENDING_RE.search(r))
    if nr_pending:
        n_cores = max(n_cores - nr_pending, covered)
    floor = _math.ceil(n_cores * _S4_COVERAGE_FLOOR)
    requested = bool(_S4_REQUEST_RE.search(card_md))
    if covered >= floor:
        return []
    if requested:
        return [_mk("WARN", "DATA_REQUESTED", 4, f">={floor} cores with per-gene BLASTp",
                    f"{covered}/{n_cores} cores carry BLASTp; data requested",
                    "\u00a74 does not yet rest on per-gene BLASTp for most cores, but the card plainly "
                    "REQUESTS the missing data (region GBKs / a BLASTp run of the named cores). Honest "
                    "gap \u2014 acknowledged, not a fail. Fold the results when they return.")]
    if covered == 0:
        return [_mk("WARN", "BLASTP_ABSENT", 4, f">={floor} cores with per-gene BLASTp",
                    f"0/{n_cores} cores carry a %id + reconciliation",
                    "\u00a74 has a core grid but NOT ONE core carries a real per-gene BLASTp signal "
                    "(a %id value + a CONFIRM/REFINE/OVERTURN reconciliation) \u2014 it reads as authored "
                    "from antiSMASH-Pfam alone. Run per-gene BLASTp of the rule-based cores (region-GBK "
                    "aa_seq \u2192 nr, --xml) and author \u00a74 from the reconciled calls, or add an explicit "
                    "data REQUEST. Pfam is a hypothesis, not the homology channel.")]
    return [_mk("WARN", "BLASTP_THIN", 4, f">={floor} cores with per-gene BLASTp",
                f"{covered}/{n_cores} cores carry a %id + reconciliation",
                f"\u00a74 rests on per-gene BLASTp for only {covered} of {n_cores} rule-based cores "
                f"(floor {floor}). A partial grid usually means a thin source (core_batches / few genes) "
                f"\u2014 pull the full package-tagged wave-2 hittable (+ --xml) and cover the remaining cores, "
                f"or REQUEST the data for those explicitly.")]


# v9.7.373 (BREAK-3, Codex title decision 2026-08-21): ONE shared §4 matrix-table locator used by
# BOTH this gate and modeb_publication_gate. The canonical emitter title is
# "Complete named-match, channel-separated table"; the legacy "Complete channel-separated BLASTp
# matrix" heading is accepted during migration but NOT sunset. Before this, the matrix gate accepted
# only the legacy heading, so it returned BLASTP_MATRIX_MISSING on every current native card.
# Observed heading variants across the v9.7.372-native corpus (23 cards, measured 2026-08-21):
#   "Complete named-match, channel-separated table"        (canonical, per Codex 2026-08-21)
#   "Complete named-match, channel-separated gene table"   (near-canonical drift, 15/23 cards)
#   "Complete channel-separated BLASTp matrix"             (legacy, accepted, not sunset)
# All three are accepted during migration; the emitter is asked to converge on the canonical.
_S4_MATRIX_TITLE_RE = re.compile(
    r"^####\s+Complete named-match,\s+channel-separated(?:\s+gene)?\s+table\s*$"
    r"|^####\s+Complete channel-separated\s+BLASTp\s+matrix\s*$", re.I | re.M)


def find_s4_matrix_block(s4_body: Optional[str]) -> Optional[str]:
    """Shared §4 matrix-table locator (v9.7.373). Given a §4 body, return the subsection BODY
    AFTER the matrix heading (canonical named-match title OR legacy title) — i.e. the text between
    that heading and the next `####` heading or end of §4 (the heading line itself is not included);
    None if no matrix heading is present. Scoped to §4; the caller validates that the located block
    is the complete gene×channel matrix (this only LOCATES it)."""
    if not s4_body:
        return None
    m = _S4_MATRIX_TITLE_RE.search(s4_body)
    if not m:
        return None
    tail = s4_body[m.end():]
    stop = re.search(r"^#{2,4}\s+", tail, re.M)
    return tail[:stop.start()] if stop else tail
_S4_MATRIX_MISSING_CELL_RE = re.compile(
    r"no bound hit|no current hit|not run|not available|unbound", re.I)
_S4_MATRIX_PENDING_CELL_RE = re.compile(r"\bpending\b", re.I)
_S4_MATRIX_OBSERVED_NO_HIT_RE = re.compile(
    r"(?:observed\s+no[- ](?:significant[- ]?)?hit|no\s+significant\s+.*?hit|"
    r"exact-sequence\s+local\s+search\s+completed)", re.I)
_S4_MATRIX_ID_RE = re.compile(r"\d+(?:\.\d+)?\s*%\s*(?:id|identity)\b", re.I)
_S4_MATRIX_SIM_RE = re.compile(r"\d+(?:\.\d+)?\s*%\s*(?:sim|positives?)\b", re.I)
_S4_MATRIX_QCOV_RE = re.compile(
    r"(?:qcov|query coverage)\s+(?:\d+(?:\.\d+)?\s*%|\d+\s*/\s*\d+|NR|not reported)", re.I)
_S4_MATRIX_SUBJECT_RE = re.compile(r"^\s*`?[A-Za-z0-9_.-]+`?\s*(?:—|-)\s*\S+")


def matrix_gene_tag(gene_cell: str) -> Optional[str]:
    """Return the gene identifier displayed in a section-4 matrix gene cell.

    Exact-locus rosters are not restricted to antiSMASH's common ``ctgN_N``
    grammar. RiPP precursor discovery can emit identifiers such as
    ``allorf_013118_013336`` and imported annotations can carry NCBI-style
    locus tags. The first code span is the author-controlled gene identifier;
    coordinates and protein SHA values occur only in later spans.
    """
    coded = re.search(r"`([A-Za-z][A-Za-z0-9_.:-]*)`", gene_cell)
    if coded:
        return coded.group(1)
    plain = re.match(r"\s*([A-Za-z][A-Za-z0-9_.:-]*)", gene_cell)
    return plain.group(1) if plain else None


def _section4_complete_blastp_matrix_findings(
        card_md: str, bgc_context: Optional[dict] = None) -> list["Finding"]:
    """Require a lossless per-gene/channel matrix for finished-current-evidence cards.

    The older §4 gate asks only whether >=50% of marked core rows carry a %id and a
    reconciliation token. That remains a useful authoring warning, but it cannot certify a
    finished card: it permits context genes to disappear and it does not require nr,
    ClusteredNR, Swiss-Prot, named subjects, identity, positives, and coverage to remain distinct.

    This gate is deliberately profile-scoped. Drafts and gap-aware authoring cards continue to
    use the older warning-first path. A card declaring FINISHED_CURRENT_EVIDENCE or
    PUBLICATION_REVIEW_CANDIDATE, or a caller setting ``require_complete_blastp_matrix``, must
    carry the complete matrix. Each channel needs a named-match column and a separate metric
    column. Missing results are valid only when both paired cells say so explicitly; missing is
    not converted to zero.
    """
    ctx = bgc_context or {}
    # v9.7.374 fix: the .373 status-vocabulary ratification names FINISHED_FULL48_CURRENT_EVIDENCE
    # as "the gate trigger" (docs/MODEB_STATUS_VOCABULARY_RATIFIED_v9_7_373.md) and
    # authored_verify.py's own _finished_profile check already recognizes it alongside the
    # grandfathered legacy FINISHED_CURRENT_EVIDENCE alias -- but this trigger was never updated to
    # match, so it only recognized the legacy token. FINISHED_CURRENT_EVIDENCE is NOT a substring of
    # FINISHED_FULL48_CURRENT_EVIDENCE (verified: False), so a card authored under the new canonical
    # strict profile silently skipped this entire per-gene/channel completeness matrix check.
    # Reproduced live: an identical card with a genuinely incomplete matrix (pending cells) trips
    # the gate under the legacy token but returns zero findings under the new canonical token.
    required = bool(ctx.get("require_complete_blastp_matrix")) \
        or "FINISHED_CURRENT_EVIDENCE" in card_md \
        or "FINISHED_FULL48_CURRENT_EVIDENCE" in card_md \
        or "PUBLICATION_REVIEW_CANDIDATE" in card_md
    if not required:
        return []

    expected = list(ctx.get("known_locus_tags") or ctx.get("canonical_locus_tags") or [])
    if not expected:
        return [_mk(
            "ERROR", "BLASTP_MATRIX_ROSTER_UNBOUND", 4,
            "authoritative canonical locus-tag roster supplied to verifier", "no bound roster",
            "A finished-current-evidence card cannot prove a complete per-gene BLASTp matrix "
            "without the authoritative canonical locus-tag roster. Pass known_locus_tags from "
            "the exact-locus package/GBK; do not infer completeness from the authored table.")]

    s4 = extract_section_bodies(card_md).get(4, "")
    block = find_s4_matrix_block(s4)
    if block is None:
        return [_mk(
            "ERROR", "BLASTP_MATRIX_MISSING", 4,
            "#### Complete named-match, channel-separated table", "subsection absent",
            "Finished-current-evidence cards must show one row per canonical gene with separate "
            "NCBI nr, NCBI ClusteredNR, and local Swiss-Prot named-match and metric cells. A channel summary or selected "
            "core rows is not a complete human-review table.")]

    pipe = [ln.strip() for ln in block.splitlines() if ln.strip().startswith("|")]
    if len(pipe) < 3:
        return [_mk("ERROR", "BLASTP_MATRIX_MISSING", 4,
                    "header plus one row per canonical gene", "no readable pipe table",
                    "The complete BLASTp subsection exists but does not contain a readable table.")]

    def cells(line: str) -> list[str]:
        return [x.strip() for x in line.strip().strip("|").split("|")]

    header = cells(pipe[0])
    lower = [h.lower() for h in header]
    # v9.7.385 (AUDIT-384-02): disambiguate among MULTIPLE header cells that merely
    # CONTAIN "gene"/"locus" as a substring (e.g. a descriptive "Gene context"/"Gene role"
    # category column ahead of the true "Locus" identity column) by cell SHAPE rather than by
    # which column comes first. See the matching fix + comment in modeb_publication_gate.py's
    # `_contiguous_homology_table_findings`, which this check must stay consistent with (the
    # .384 fix explicitly ties the two together). A real gene/locus tag always carries a digit
    # once matrix_gene_tag() strips it; a free-text descriptive value normally doesn't.
    _data_rows_for_gene_col = [cells(ln) for ln in pipe[2:]]
    _gene_candidates = [i for i, h in enumerate(lower) if "gene" in h or "locus" in h]

    def _column_is_digit_tagged(i: int) -> bool:
        vals = [r[i] for r in _data_rows_for_gene_col if i < len(r)]
        if not vals:
            return False
        return all(
            (tag := matrix_gene_tag(v)) and any(ch.isdigit() for ch in tag)
            for v in vals
        )

    idx_gene = next((i for i in _gene_candidates if _column_is_digit_tagged(i)), None)
    if idx_gene is None and _gene_candidates:
        idx_gene = _gene_candidates[0]
    match_words = ("accession", "matched", "protein", "subject")
    metric_words = (" id", "identity", "qcov", "coverage", "positives", "similarity", "sim")

    def pair(channel: str) -> tuple[Optional[int], Optional[int]]:
        def is_channel(h: str) -> bool:
            if channel == "nr":
                return "nr" in h and "cluster" not in h
            if channel == "clusterednr":
                return "cluster" in h and "nr" in h
            return "swiss" in h
        candidates = [(i, h) for i, h in enumerate(lower) if is_channel(h)]
        match_i = next((i for i, h in candidates if any(w in h for w in match_words)), None)
        metric_i = next((i for i, h in candidates if any(w in h for w in metric_words)), None)
        return match_i, metric_i

    nr_match, nr_metric = pair("nr")
    cluster_match, cluster_metric = pair("clusterednr")
    swiss_match, swiss_metric = pair("swiss")
    if None in (idx_gene, nr_match, nr_metric, cluster_match, cluster_metric,
                swiss_match, swiss_metric):
        return [_mk(
            "ERROR", "BLASTP_MATRIX_CHANNELS", 4,
            "Gene plus separate named-match and metric columns for NCBI nr, NCBI ClusteredNR, and local Swiss-Prot",
            f"headers={header}",
            "Finished-card BLASTp channels must remain separate and each channel must pair an "
            "accession/protein/organism column with an identity/positives/query-coverage column. "
            "An accession appended to a metric-only cell is not an interpretable named match.")]

    rows: dict[str, list[list[str]]] = {}
    for line in pipe[2:]:
        c = cells(line)
        if len(c) != len(header):
            continue
        gene = matrix_gene_tag(c[idx_gene])
        if gene:
            rows.setdefault(gene, []).append(c)

    exp = list(dict.fromkeys(str(x) for x in expected))
    missing = [x for x in exp if x not in rows]
    duplicate = [x for x in exp if len(rows.get(x, [])) > 1]
    extra = sorted(x for x in rows if x not in set(exp))
    if missing or duplicate or extra:
        found = (f"missing={missing[:8]}; duplicate={duplicate[:8]}; extra={extra[:8]}; "
                 f"rows={sum(len(v) for v in rows.values())}/{len(exp)}")
        return [_mk(
            "ERROR", "BLASTP_MATRIX_ROSTER", 4,
            f"exactly one matrix row for each of {len(exp)} canonical genes", found,
            "The BLASTp matrix must preserve the exact canonical roster. Boundary/context genes "
            "remain rows; their analytical inclusion can be stated separately.")]

    bad_pairing = []
    bad_subjects = []
    bad_metrics = []
    pending_cells = []
    channel_pairs = (
        ("nr", nr_match, nr_metric),
        ("ClusteredNR", cluster_match, cluster_metric),
        ("Swiss-Prot", swiss_match, swiss_metric),
    )
    for gene in exp:
        c = rows[gene][0]
        for label, match_i, metric_i in channel_pairs:
            match_value = c[match_i]
            metric_value = c[metric_i]
            if (_S4_MATRIX_PENDING_CELL_RE.search(match_value)
                    or _S4_MATRIX_PENDING_CELL_RE.search(metric_value)):
                pending_cells.append(f"{gene}:{label}")
                continue
            match_no_hit = bool(_S4_MATRIX_OBSERVED_NO_HIT_RE.search(match_value))
            metric_no_hit = bool(_S4_MATRIX_OBSERVED_NO_HIT_RE.search(metric_value))
            if match_no_hit or metric_no_hit:
                if match_no_hit != metric_no_hit:
                    bad_pairing.append(f"{gene}:{label}")
                # A completed exact-sequence search with no significant hit
                # has no accession or alignment percentages to fabricate.
                continue
            match_missing = bool(_S4_MATRIX_MISSING_CELL_RE.search(match_value))
            metric_missing = bool(_S4_MATRIX_MISSING_CELL_RE.search(metric_value))
            if match_missing != metric_missing:
                bad_pairing.append(f"{gene}:{label}")
                continue
            if match_missing:
                continue
            if not (_S4_MATRIX_SUBJECT_RE.search(match_value)
                    and (_BRACKET_ORG_RE.search(match_value) or _GENUS_RE.search(match_value))):
                bad_subjects.append(f"{gene}:{label}")
            complete_metrics = (bool(_S4_MATRIX_ID_RE.search(metric_value))
                                and bool(_S4_MATRIX_SIM_RE.search(metric_value))
                                and bool(_S4_MATRIX_QCOV_RE.search(metric_value)))
            if not complete_metrics:
                bad_metrics.append(f"{gene}:{label}")
    findings = []
    if pending_cells:
        findings.append(_mk(
            "ERROR", "BLASTP_MATRIX_PENDING_TERMINAL", 4,
            "no pending cells in a finished-current-evidence matrix",
            f"pending cells={pending_cells[:12]}",
            "Pending belongs in the work ledger, not the finished card. Integrate accessible, "
            "actively running, or practically attainable BLASTP before content-QA; otherwise "
            "retain a draft/blocked state with a typed readiness record."))
    if bad_pairing:
        findings.append(_mk(
            "ERROR", "BLASTP_MATRIX_PAIRING", 4,
            "each channel has either a named match plus alignment metrics, or explicit missing states in both paired cells",
            f"asymmetric cells={bad_pairing[:12]}",
            "A percentage without its named match, or a named match without its metrics, is not "
            "human-auditable evidence. Keep the pair together and never infer missing as zero."))
    if bad_subjects:
        findings.append(_mk(
            "ERROR", "BLASTP_MATRIX_SUBJECTS", 4,
            "every bound hit names accession, matched protein, and organism",
            f"invalid named-match cells={bad_subjects[:12]}",
            "A bare accession or percentage does not say what the gene matched. Preserve the "
            "rank-1 accession, protein description, and subject organism in the channel's match cell."))
    if bad_metrics:
        findings.append(_mk(
            "ERROR", "BLASTP_MATRIX_METRICS", 4,
            "every bound-hit metric cell has % identity + % positives/similarity + query coverage",
            f"invalid metric cells={bad_metrics[:12]}",
            "Do not leave blank cells, merge channels, infer missing values as zero, or substitute "
            "an accession for the required alignment metrics."))
    return findings


_LOCUS_RE = re.compile(r"\bctg\d+_\d+\b")

# B1 (v9.7.256) — membership gate helpers. PHANTOM_LOCUS asks "does this gene exist in this
# organism?"; that is necessary but not sufficient, because ctgN_M is a contig-index name that
# collides across BGCs within a strain (and across strains). The membership gate asks the sharper
# question the AS-XXX leak needed: "does this gene exist in the BGC the sentence attributes it to?"
_PANEL_RESULT_RE = re.compile(
    r"per-gene\s+BLASTp|BLASTp\s+(?:overturn|confirm|settl|reconcil)|"
    r"overturn(?:ed|s)?\s+\w+\s+of\s+\w+|settled\s+BGC|→\s*\w+.*\d{2,3}(?:\.\d)?\s*%",
    re.I)
_DENIAL_CONTRAST_RE = re.compile(
    r"\b(?:unlike|whereas|in contrast|contrast|rather than|as opposed to|compared (?:to|with)|"
    r"comparator|versus|vs\.?|does not|do not|did not|not|no\s+(?:BLASTp\s+)?panel|"
    r"never\s+run|not\s+support|was\s+not\s+run|absent|"
    # MODEB-GATE-P05 (v9.7.331): a §15/§30 split-pathway sentence co-citing THIS card's loci with a
    # partner BGC id (home BGC not named) is an explicit cross-cluster contrast, not a
    # misattribution. Treat split / partner / distinct-from as contrast cues so those sentences stop
    # throwing false LOCUS_BGC_MISMATCH ERRORs (AS-XXX/BGC031 partner BGC009; AS-XXX/BGC006).
    r"split|partner|distinct\s+from)\b", re.I)
# v9.7.264 follow-on: _PANEL_RESULT_RE matches a bare "per-gene BLASTp" topic mention, so a card that
# *defers*, *recommends*, or marks a panel N/A — legitimate for a no-panel or selected-but-not-run BGC —
# was flagged as a fabricated result. .264's selected-but-no-results branch widens that FP onto exactly
# the selected-not-run BGCs it targets. These tokens mark a non-result (plan / absence / deferral); scoped
# to the panel gate only. A stated RESULT ("overturned two of ten") still fires via the verb alternatives.
_PANEL_NONRESULT_RE = re.compile(
    r"\b(?:recommend(?:ed|s)?|defer(?:red|s)?|pending|planned|scheduled|suggest(?:ed|s)?|"
    r"to\s+be\s+run|not\s+(?:yet\s+)?run|not\s+applicable|n/?a|awaiting|would\s+(?:be\s+)?"
    r"(?:need|require)(?:ed|s)?|should\s+be\s+run)\b", re.I)


def _split_sentences(text: str) -> list[str]:
    return re.split(r"(?<=[.!?])\s+", text)


def _norm_bgc(x) -> str:
    """'BGC006' / '006' / '6' / 6 -> 'bgc006'. Zero-pads to 3 digits to match gene-table ids."""
    d = re.sub(r"\D", "", str(x))
    return f"bgc{int(d):03d}" if d else ""


def _is_contrastive_or_denial(sent: str) -> bool:
    return bool(_DENIAL_CONTRAST_RE.search(sent))


def _locus_bgc_mismatch_findings(card_md: str, bgc_context: Optional[dict] = None) -> list["Finding"]:
    """B1 — a ctgN_M cited under a BGC it is not a member of (misattribution, not non-existence).

    Existence (PHANTOM_LOCUS) is necessary but not sufficient. On AS-XXX a templated sentence
    read '…settled BGC006 ctg12_71' — ctg12_71 is a real gene in AS-XXX, so PHANTOM_LOCUS stayed
    silent, but its home is BGC010, not BGC006. The leak was *accidentally true of the wrong BGC in
    the right organism* — the most dangerous kind.

    Fires only when a locus is co-cited with a BGC in one sentence, its true home is known, and that
    home is NOT named in the sentence (so legitimate 'ctg12_71 in BGC010, unlike BGC006' passes).
    Requires bgc_context['locus_home'] (locus_tag -> home BGC id); silent without it.
    ERROR-level, release-blocking.
    """
    ctx = bgc_context or {}
    home_raw = ctx.get("locus_home")
    if not home_raw:
        return []
    # v9.7.373b (Codex one-to-many correction): a locus can have MORE THAN ONE declared home
    # (a boundary CDS shared by adjacent BGC regions). Normalise every value to a set of homes,
    # accepting both the new set form and the legacy single-string form for back-compat.
    def _home_set(v: object) -> set:
        if isinstance(v, (set, list, tuple)):
            return {_norm_bgc(x) for x in v}
        return {_norm_bgc(v)}
    home = {str(k).strip().lower(): _home_set(v) for k, v in home_raw.items()}
    out: list[Finding] = []
    seen: set = set()
    for sent in _split_sentences(card_md):
        loci = [m.group(0) for m in _LOCUS_RE.finditer(sent)]
        if not loci:
            continue
        bgcs = {_norm_bgc(b) for b in _ANY_BGC_RE.findall(sent)}
        if not bgcs:
            continue
        for lt in loci:
            hs = home.get(lt.lower())
            if not hs:
                continue  # unknown home -> that is PHANTOM_LOCUS's job, not this gate's
            if hs & bgcs:
                continue  # the locus IS attributed to (or alongside) ONE OF its true homes -> fine
            if _is_contrastive_or_denial(sent):
                continue  # belt-and-suspenders: skip explicit contrast/denial clauses
            attributed = sorted(bgcs)
            home_str = " / ".join(b.upper() for b in sorted(hs))
            key = (lt.lower(), tuple(sorted(hs)), tuple(attributed))
            if key in seen:
                continue
            seen.add(key)
            attr_str = ", ".join(b.upper() for b in attributed)
            out.append(_mk("ERROR", "LOCUS_BGC_MISMATCH", None,
                f"{lt} cited under its home {home_str}",
                f"{lt} co-cited with {attr_str} but is a member of {home_str}",
                f"Card attributes {lt} to {attr_str}, but {lt} belongs to {home_str} in this strain. "
                f"A locus cited under the wrong BGC is a misattributed observation, even when the gene "
                f"is real — check for templated boilerplate carried in from another BGC's session "
                f"(the AS-XXX BGC006/BGC010 leak class)."))
    return out


def _panel_absent_claim_findings(card_md: str, bgc_context: Optional[dict] = None) -> list["Finding"]:
    """B1 — a per-gene BLASTp *result* asserted for a BGC that has no panel.

    Independent of locus naming: AS-XXX BGC006 had no BLASTp panel, yet a card asserted
    'per-gene BLASTp overturned two of ten on BGC006'. A stated result for an unrun panel is a
    fabricated observation. Requires bgc_context['panels_present'] (set of BGC ids with a real
    panel); silent when the key is absent (cannot judge what it cannot see). ERROR-level.
    """
    ctx = bgc_context or {}
    panels_raw = ctx.get("panels_present")
    if panels_raw is None:
        return []
    panels = {_norm_bgc(b) for b in panels_raw}
    # v9.7.264: distinguish a panel *selection* from an actual results artifact. When the package
    # tracks results (a blastp_online/ dir with returned alignments exists), a per-gene result claimed
    # for a BGC that was selected but never run is unbacked. None => results not tracked => stay silent
    # on this stricter case (cannot tell "never run" from "results not shipped in this package").
    results_raw = ctx.get("blastp_results_present")
    results = {_norm_bgc(b) for b in results_raw} if results_raw is not None else None
    out: list[Finding] = []
    seen: set = set()
    for sent in _split_sentences(card_md):
        if not _PANEL_RESULT_RE.search(sent):
            continue
        if _is_contrastive_or_denial(sent):
            continue  # 'no BLASTp panel was run on BGC006' is a correct statement, not a claim
        if _PANEL_NONRESULT_RE.search(sent):
            continue  # deferred / recommended / N-A: a plan or absence, not an asserted result
        for b in {_norm_bgc(x) for x in _ANY_BGC_RE.findall(sent)}:
            if not b or b in seen:
                continue
            if b not in panels:
                seen.add(b)
                out.append(_mk("ERROR", "PANEL_ABSENT_CLAIM", None,
                    "per-gene BLASTp results only for BGCs that have a panel",
                    f"{b.upper()} has no BLASTp panel but the card states a per-gene BLASTp result for it",
                    f"Card states a per-gene BLASTp outcome for {b.upper()}, which has no BLASTp panel in this "
                    f"package. A BLASTp result for an unrun panel is a fabricated observation (AS-XXX BGC006 "
                    f"class). If the claim is a denial ('no panel was run'), rephrase so it does not read as a "
                    f"result."))
            elif results is not None and b not in results:
                seen.add(b)
                out.append(_mk("ERROR", "PANEL_ABSENT_CLAIM", None,
                    "per-gene BLASTp results require a returned-alignments artifact, not just a selection",
                    f"{b.upper()} has a panel selection but no results artifact — the panel was never run",
                    f"Card states a per-gene BLASTp outcome for {b.upper()}, which has a panel selection but no "
                    f"<BGC>_online_blastp.csv results artifact in this package that tracks BLASTp results — the "
                    f"panel was selected but never run, so the stated result is unbacked (the S_erythraea BGC017 "
                    f"residual-gap class the earlier PANEL_ABSENT_CLAIM missed). Run the panel or ingest its "
                    f"hit-table before authoring §4, or remove the result."))
    return out


def _family_skeleton(tag: str) -> tuple[Optional[str], bool]:
    """v9.7.410 — reduce a locus/gene identifier to its *family skeleton* regex source.

    Every maximal run of digits becomes ``\\d+``; every non-digit run is matched literally
    (``re.escape``). So ``KSE_RS00100`` -> ``KSE_RS\\d+``, ``allorf_013118_013336`` ->
    ``allorf_\\d+_\\d+``, ``ctg12_71`` -> ``ctg\\d+_\\d+``. Returns ``(skeleton, distinctive)``.

    ``distinctive`` gates which families are trustworthy enough to scan the free text with: a
    family is used only when it carries at least one digit run AND (an internal separator
    ``[._:-]`` OR an alpha prefix of length >= 3). This keeps the derived scan tightly scoped to
    the strain's *own* gene-id grammar — trivial shapes like ``A1`` never become a matcher — so a
    foreign subject accession of a different shape (``WP_012345678.1`` when the roster is
    ``KSE_RS#####``) is never in scope, while a fabricated member of the strain's own family
    (``KSE_RS99999``) is.
    """
    parts = re.split(r"(\d+)", tag)
    out: list[str] = []
    has_digit = False
    for p in parts:
        if not p:
            continue
        if p.isdigit():
            out.append(r"\d+")
            has_digit = True
        else:
            out.append(re.escape(p))
    if not has_digit:
        return None, False
    m = re.match(r"[A-Za-z]+", tag)
    prefix_len = len(m.group(0)) if m else 0
    has_sep = bool(re.search(r"[._:\-]", tag))
    distinctive = has_sep or prefix_len >= 3
    return "".join(out), distinctive


def _roster_family_matchers(known_raw: "set[str]") -> list["re.Pattern[str]"]:
    """v9.7.410 — compile one word-bounded matcher per *distinctive* id family in the roster.

    Deterministic: skeletons are de-duplicated and sorted before compilation. The strain's own
    roster is the authority on which identifier grammars are this strain's — a card token that
    matches one of these grammars but is not itself a roster member is a fabricated gene of the
    strain's own family (the generalization of the ctgN_M PHANTOM_LOCUS to any id format).
    """
    skeletons = set()
    for tag in known_raw:
        sk, distinctive = _family_skeleton(str(tag).strip())
        if sk and distinctive:
            skeletons.add(sk)
    return [re.compile(r"\b" + sk + r"\b") for sk in sorted(skeletons)]


def _phantom_locus_findings(card_md: str, bgc_context: Optional[dict] = None) -> list["Finding"]:
    """v9.7.246 — a locus_tag cited in a card that does not exist in that strain's own CDS table.

    Why this exists: the §4 authoring template hardcoded a real per-gene BLASTp result belonging to
    *Amycolatopsis* sp. NPDC004378 ("overturned two of ten on BGC006: beta-lactamase->esterase,
    phenol-hydroxylase->ferritin"; "settled BGC006 ctg12_71"). Templated, it was emitted verbatim into
    every card of every strain — asserting a specific BLASTp outcome for strains on which no BLASTp had
    been run, and citing a locus (ctg12_71) that exists on neither. 74 cards carried it.

    Every guard in the bundle passed those cards, because none of them ever asked the only question that
    matters for a cited locus: **does this gene exist in this organism?**

    v9.7.410 — the extractor was ctgN_M-only (``_LOCUS_RE``), so a fabricated gene id in any OTHER
    format that shares a real family in the roster (a RefSeq-style ``KSE_RS99999`` when the strain's
    genes are ``KSE_RS#####``, an ``allorf_…`` precursor id, an ``SCO####`` tag) slipped through even
    with ``--package``. The check now also derives the strain's own id-family grammars from the sealed
    roster and flags any card token matching a family but absent from it. The ctgN_M path is retained
    unchanged; determinism and the "silent without a roster" contract are preserved, and real roster
    genes (members, any format) still pass because membership is what clears a token.

    ERROR-level. A phantom locus is a fabricated observation, not a style problem. Requires
    bgc_context["known_loci"]; silent without it (cannot judge what it cannot see).
    """
    ctx = bgc_context or {}
    known = ctx.get("known_loci")
    if not known:
        return []
    known = {str(k).strip().lower() for k in known}
    # ctgN_M path (v9.7.246) — always on, catches a foreign ctg tag even when THIS strain's own
    # genes are not ctg-shaped (the foreign tag then matches no roster family but is still a phantom).
    cited = {m.group(0) for m in _LOCUS_RE.finditer(card_md)}
    # v9.7.410 generalization — scan for tokens shaped like ANY of this strain's own id families.
    for matcher in _roster_family_matchers(set(ctx.get("known_loci") or ())):
        cited.update(m.group(0) for m in matcher.finditer(card_md))
    phantom = sorted(c for c in cited if c.lower() not in known)
    if not phantom:
        return []
    shown = ", ".join(phantom[:6]) + ("…" if len(phantom) > 6 else "")
    return [_mk("ERROR", "PHANTOM_LOCUS", None,
                "every cited locus_tag exists in this strain's CDS table",
                f"{len(phantom)} locus tag(s) not in this strain: {shown}",
                f"Card cites {len(phantom)} locus_tag(s) that do not exist in this strain's CDS table "
                f"({shown}). A locus from another organism is a fabricated observation, however true it "
                f"is elsewhere. MOST COMMON CAUSE: the WRONG BLASTp SOURCE — region-relative tags (low "
                f"ctgN_M numbers) from a thin core_batches hittable instead of THIS strain's actual "
                f"package locus_tags. Don't reword the tags to pass; switch source: use the full "
                f"package-tagged wave-2 hittable (+ --xml for named subjects) or the region-GBK core "
                f"batch from the vault, then re-derive §4. Also check for boilerplate carried over from "
                f"another strain's session or a copy-paste from an example card.")]


def _citation_findings(card_md: str) -> list["Finding"]:
    """Flag BGCs that are NEVER given a node·region locator anywhere in the card
    (item #59), and a card with no provenance tagging at all. WARN-level heuristic.

    Refined (v9.7.209): running-prose cross-references like 'BGC039/BGC027's tier'
    are not citation errors as long as the BGC is cited with a locator *somewhere*
    in the card. So we flag per-BGC-id, only when NO locator form appears for it —
    this is the real failure (a BGC discussed but never located), not prose density.
    """
    out: list[Finding] = []
    located = set(_LOCATOR_BGC_RE.findall(card_md))       # e.g. {'039','027'}
    mentioned = set(_ANY_BGC_RE.findall(card_md))
    for bgc_num in sorted(mentioned - located):
        tok = f"BGC{bgc_num}"
        out.append(_mk(
            "WARN", "MISSING_LOCATOR", None, f"{tok} (NODE_… · r…)", tok,
            f"'{tok}' is mentioned but never cited with a node·region locator "
            f"anywhere in the card. Give it at least one '{tok} (NODE_x · rNNN)'."))
    if not _PROVENANCE_RE.search(card_md):
        out.append(_mk(
            "WARN", "NO_PROVENANCE_TAGS", None,
            "store-backed / observed / inferred / computed / assumed", None,
            "Card contains no provenance tags. Tag claims as store-backed vs. "
            "reconstructed vs. corpus, and observed/inferred/computed/assumed."))
    return out


def _mk(severity: str, code: str, section: Optional[int],
        expected: Optional[str], found: Optional[str],
        message: str) -> Finding:
    return {
        "severity": severity,
        "code": code,
        "section": section,
        "expected": expected,
        "found": found,
        "message": message,
    }


def summarise(findings: Iterable[Finding]) -> str:
    """One-screen human summary of a lint result. Use for stderr printing."""
    findings = list(findings)
    if not findings:
        return "Mode B structure: PASS (§1–§48 contract satisfied)."
    n_err = sum(1 for f in findings if f["severity"] == "ERROR")
    n_warn = sum(1 for f in findings if f["severity"] == "WARN")
    lines = [f"Mode B structure: {n_err} ERROR(S), {n_warn} WARN(S)"]
    for f in findings:
        sec = f"§{f['section']}" if f["section"] else "—"
        lines.append(f"  [{f['severity']}] [{f['code']}] {sec}: {f['message']}")
    return "\n".join(lines)
