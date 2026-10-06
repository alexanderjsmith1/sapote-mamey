"""Mode B contract current50 v2: fifty sections, with GECCO and the contigs rescued into the BGC.

`emit-modeb-template --contract current50_v2` emits the §1–§50 scaffold from
`data/mode_b/modeb_current50_v2_contract.json`. `verify-modeb --contract current50_v2` runs the structure,
depth, class-content, claim-safety and evidence-presence checks against the same contract, then the v2 checks here:

- §48 and §49 (literature) each cite a source by DOI, PMID or PMCID and say why it is relevant;
- §50 (Data evidence table) is the very last section and holds a Markdown table;
- no generic deferral text; typed limitations name a reason and their inference ceiling.

The finished-profile publication gates of the 48-section corrective profile are keyed to that profile's
section numbers and are not run on a v2 card. Passing these checks is structural. It establishes no product,
production, activity, novelty or release; judgment deferred.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Optional
from .modeb_markdown import active_markdown

CONTRACT_NAMES = ("full48", "current50_v2")
V2_PATH = Path(__file__).resolve().parent / "data" / "mode_b" / "modeb_current50_v2_contract.json"
V2_PROFILE = "FINISHED_FULL50_CURRENT50_V2"

CITATION = re.compile(r"\b(?:doi:\s*|https?://(?:dx\.)?doi\.org/)?10\.\d{4,9}/\S+|\bPMID:?\s*\d{5,9}\b|\bPMC\d{5,9}\b",
                      re.I)
RELEVANCE = re.compile(r"\brelevan(?:ce|t)\b", re.I)
TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$", re.M)
DEFERRAL = [
    (re.compile(r"\bnot (?:yet )?(?:recorded|evaluated|assessed|reviewed)\b", re.I), "says 'not recorded/evaluated'"),
    (re.compile(r"\bTODO\b|\bTBD\b|\bFIXME\b"), "has TODO/TBD"),
    (re.compile(r"<!--\s*Author", re.I), "still holds a template authoring prompt"),
    (re.compile(r"\bto be (?:added|completed|determined) later\b", re.I), "defers work to later"),
]


LIMITATION_STATE = re.compile(r"\b(?:NOT_RUN|UNAVAILABLE|NOT_APPLICABLE|OBSERVED_UNBOUND|UNRETURNED|INGEST_GAP):", re.I)
LIMITATION_REASON = re.compile(r"\b(?:because|due to|owing to)\s+\S+(?:\s+\S+){2,}", re.I)
LIMITATION_CEILING = re.compile(r"\b(?:no .{2,100}(?:inferred|claimed|established)|cannot (?:infer|claim|establish)|does not establish)\b", re.I)


# These abbreviations belong inside a sentence. Their final periods must not
# detach a typed limitation's reason from its inference ceiling.
LIMITATION_ABBREVIATION = re.compile(r"(?<!\w)(?:e\.g\.|i\.e\.|Dr\.|Prof\.)(?=\s|[,;)])", re.I)


def _limitation_sentences(body: str) -> list[str]:
    # Each Markdown cell is its own evidence statement. A reason or ceiling in
    # another cell cannot complete a limitation; escaped literal pipes remain.
    body = '\n'.join('\n'.join(re.split(r'(?<!\\)\|', row))
                     if TABLE_ROW.fullmatch(row) else row for row in body.split('\n'))
    protected_ends = {match.end() for match in LIMITATION_ABBREVIATION.finditer(body)}
    sentences, start = [], 0
    for separator in re.finditer(r"(?<=[.!?])\s+|\n", body):
        # Newlines retain the existing boundary even after an abbreviation.
        # Only abbreviation punctuation is exempted; subsequent prose remains
        # independently checked for deferrals and template prompts.
        if "\n" not in separator.group() and separator.start() in protected_ends:
            continue
        sentences.append(body[start:separator.start()])
        start = separator.end()
    sentences.append(body[start:])
    return sentences


def _reasoned_limitation(line: str) -> bool:
    # A typed token alone cannot exempt another sentence, table, or adjacent TODO.
    evaluations = list(DEFERRAL[0][0].finditer(line))
    if not evaluations:
        return False
    for i, match in enumerate(evaluations):
        start = evaluations[i-1].end() if i else 0
        end = evaluations[i+1].start() if i+1 < len(evaluations) else len(line)
        # A second evaluation statement needs its own typed state and its own
        # causal reason and ceiling, even when joined by a semicolon or 'and'.
        if not (LIMITATION_STATE.search(line[start:match.start()])
                and LIMITATION_REASON.search(line[match.end():end])
                and LIMITATION_CEILING.search(line[match.end():end])):
            return False
    return True


def load_contract(name: Optional[str]) -> Optional[dict]:
    """The contract dict for `name`; None for the default 48-section profile (callers then load their own)."""
    if not name or name == "full48":
        return None
    if name != "current50_v2":
        raise ValueError(f"unknown Mode B contract {name!r}; choose one of {', '.join(CONTRACT_NAMES)}")
    return json.loads(V2_PATH.read_text(encoding="utf-8"))


def contract_sha256() -> str:
    """sha256 of the shipped v2 contract file; a card header records it so a reader can bind the card to one contract."""
    return hashlib.sha256(V2_PATH.read_bytes()).hexdigest()


def header_line(strain: str, contig: str, region: str, bgc: str) -> str:
    """The first line of a v2 card: full four-part identity, contract name and sha, and the profile token."""
    return (f"<!-- MODE B | canonical_identity: {strain} / {contig} / {region} / {bgc} | contract: current50_v2 | "
            f"contract_sha256: {contract_sha256()} | profile: {V2_PROFILE} -->")


def blastp_table_findings(md: str) -> list[dict]:
    """A v2 card keeps the per-gene BLASTp table in §50, not §4. Same test as the 48-section EVIDENCE_GAP, read on §50."""
    from .modeb_structure_gate import _has_blastp_table
    tail = dict(_bodies(md)).get(50, "")
    if _has_blastp_table("## §4 Data evidence table\n" + tail):
        return []
    return [_f("WARN", "EVIDENCE_GAP", 50, "strain has a BLASTp panel but §50 holds no per-gene table with an identity "
               "column. Author §50 from the reconciled per-gene matches; evidence presence, not length, is the bar.")]


IDENTITY_STRAIN = re.compile(r"^#\s*Mode B\s*[\u2014-]\s*([^/\n]+?)\s*/", re.M)


def rescue_context_loci(md: str, tsv_paths) -> tuple[set, list[str]]:
    """Locus tags a v2 card may cite from the strain's gap-rescue tables, outside any antiSMASH region.

    §26 and §50 must name genes found elsewhere in the genome, including ones set aside by a partner check.
    Those genes are not in the package CDS table, which lists region CDS only, so PHANTOM_LOCUS would refuse
    them. A row's `best_locus` is admitted for existence only when its `best_region_identity` names the
    card's own strain. Membership in the BGC is not granted.
    """
    m = IDENTITY_STRAIN.search(md)
    strain = m.group(1) if m else None
    loci, notes = set(), []
    for path in tsv_paths or ():
        with open(path, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh, delimiter="\t"):
                lt = (row.get("best_locus") or "").strip()
                where = (row.get("best_region_identity") or "").strip()
                if not lt:
                    continue
                if strain and where.split(" / ")[0].strip() == strain:
                    loci.add(lt)
                else:
                    notes.append(f"{lt} not admitted: {where or 'no identity'} is not {strain or 'the card strain'}")
    return loci, notes


def is_v2(contract: Optional[dict]) -> bool:
    return bool(contract) and contract.get("schema_version") == "modeb_current50_v2"


def _bodies(md: str) -> list[tuple[int, str]]:
    """[(section number, body)] in card order, split on `## §N` headings."""
    md = active_markdown(md)
    heads = list(re.finditer(r"^#{1,6}\s*§(\d{1,2})\b[^\n]*$", md, re.M))
    out = []
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(md)
        out.append((int(h.group(1)), md[h.end():end]))
    return out


def _f(severity, code, section, message):
    return {"severity": severity, "code": code, "section": section, "message": message}


def v2_findings(md: str, *, require_expanded_locus: bool = False) -> list[dict]:
    """The checks a current50 v2 card adds on top of the shared structure gate."""
    found = []
    bodies = _bodies(md)
    # Hidden scaffolding is still unfinished authoring, while fenced examples of
    # placeholders remain examples. Comments never supply substantive evidence.
    prompts = active_markdown(md, preserve_comments=True)
    active_heads = list(re.finditer(r"^#{1,6}[ \t]*§(\d{1,2})\b[^\n]*$", active_markdown(md), re.M))
    for i, heading in enumerate(active_heads):
        end = active_heads[i+1].start() if i+1 < len(active_heads) else len(prompts)
        if DEFERRAL[2][0].search(prompts[heading.end():end]):
            found.append(_f("ERROR", "V2_DEFERRAL", int(heading.group(1)),
                            "Section still holds a template authoring prompt."))
    nums = [n for n, _ in bodies]
    by = {}
    for n, b in bodies:
        by.setdefault(n, b)
    for n in (48, 49):
        b = by.get(n, "")
        if n not in by:
            continue  # the structure gate reports the missing section
        if not CITATION.search(b):
            found.append(_f("ERROR", "V2_LITERATURE_NO_CITATION", n,
                            f"§{n} cites no source by DOI, PMID or PMCID."))
        if not RELEVANCE.search(b):
            found.append(_f("ERROR", "V2_LITERATURE_NO_RELEVANCE", n,
                            f"§{n} does not state the relevance of its citations to this locus."))
    if nums:
        if nums[-1] != 50:
            found.append(_f("ERROR", "V2_EVIDENCE_TABLE_NOT_LAST", nums[-1],
                            f"§50 (Data evidence table) must be the very last section; the card ends with §{nums[-1]}."))
        tail = by.get(50, "")
        if 50 in by and len(TABLE_ROW.findall(tail)) < 3:
            found.append(_f("ERROR", "V2_EVIDENCE_TABLE_MISSING", 50,
                            "§50 holds no Markdown table (a header, a rule and at least one gene row)."))
    for n, b in bodies:
        lines = _limitation_sentences(b)
        for rx, what in DEFERRAL:
            # Only the generic non-evaluation wording can be a precise limitation.
            # Explicit TODOs, author prompts and promises of later work remain failures.
            m = next((rx.search(line) for line in lines
                      if rx.search(line) and not (rx is DEFERRAL[0][0] and _reasoned_limitation(line))), None)
            if m:
                found.append(_f("ERROR", "V2_DEFERRAL", n, f"§{n} {what}: '{m.group(0)}'. Replace it with a "
                                "finding, a documented negative, a reasoned not-applicable decision or a precise "
                                "evidence limitation."))
    from .modeb_locus_scope import findings as locus_scope_findings
    found.extend(locus_scope_findings(md, require_expanded=require_expanded_locus))
    return found
