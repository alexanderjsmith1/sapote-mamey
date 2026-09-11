#!/usr/bin/env python3
"""remediate_phantom_locus.py — find and excise fabricated locus citations from authored Mode B cards.

v9.7.250. The v9.7.246 §4 template hardcoded a real per-gene BLASTp result belonging to
*Amycolatopsis* sp. NPDC004378 — including the locus `ctg12_71` — and emitted it verbatim into
every card of every strain. 74 cards across two strains carried it.

Those cards are NOT repaired by the v9.7.246 source fix. This tool finds them and removes the
fabrication, with the rule the changelog states:

    "Every §4 and §16 paragraph containing ctg12_71 should be DELETED, not reworded —
     there is no BLASTp result to reword."

Rewording produces a hedged fabrication, which is worse than an unhedged one because it reads as
careful.

Two modes of detection:
  * --package <pkg>  : authoritative. Loads the strain's own locus universe from
                       <pkg>/*_cds_table.csv, exactly as authored_verify does, and flags any
                       cited ctgN_M absent from it. This is the PHANTOM_LOCUS question.
  * (no --package)   : heuristic. Flags only the known v9.7.246 leak strings. Use when the sealed
                       package is unavailable; it cannot find *other* foreign loci.

Default is a dry run. --apply rewrites in place, keeping a .bak copy.

Usage
  python3 tools/remediate_phantom_locus.py --cards judgment/ --package runs/AS-XXX/package
  python3 tools/remediate_phantom_locus.py --cards judgment/ --apply
  python3 tools/remediate_phantom_locus.py --cards judgment/ --json
"""
from __future__ import annotations
import argparse
import csv
import json
import pathlib
import re
import shutil
import sys

_LOCUS = re.compile(r"\bctg\d+_\d+\b")
# `# Mode B — BGC036 (...)`. The BGC id is required: it is what separates a card from the
# exemplar README, whose title is `# Mode B exemplars — one good card per BGC class`.
_CARD_TITLE = re.compile(r"^#\s+Mode B\s*[\u2014\u2013-]\s*BGC\d+", re.IGNORECASE)

# The exact v9.7.246 leak. Used when no CDS table is available.
KNOWN_LEAK_LOCI = {"ctg12_71"}
KNOWN_LEAK_PHRASES = (
    "overturned two of ten on BGC006",
    "settled BGC006 ctg12_71",
    "the BGC006/colibrimycin fix",
)


def load_known_loci(pkg: pathlib.Path) -> set[str]:
    """Mirror authored_verify: glob *_cds_table.csv and cds_table.csv for locus_tag."""
    loci: set[str] = set()
    for p in list(pkg.glob("*_cds_table.csv")) + list(pkg.glob("cds_table.csv")):
        try:
            with open(p, newline="", encoding="utf-8") as fh:
                for row in csv.DictReader(fh):
                    lt = (row.get("locus_tag") or row.get("Locus_tag") or "").strip()
                    if lt:
                        loci.add(lt.lower())
        except OSError:
            continue
    return loci


def _paragraphs(text: str) -> list[str]:
    """Split on blank lines, RETAINING the separators so a rejoin is byte-identical.

    A 'paragraph' is the deletion unit the changelog names. Odd indices are the blank-line
    separators; dropping a paragraph must also drop exactly one adjacent separator, or the
    rewritten markdown loses its paragraph breaks.
    """
    return re.split(r"(\n[ \t]*\n)", text)


def scan_card(path: pathlib.Path, known: set[str] | None) -> dict:
    text = path.read_text(encoding="utf-8")
    cited = {m.group(0) for m in _LOCUS.finditer(text)}
    if known:
        phantom = sorted(c for c in cited if c.lower() not in known)
        basis = "cds_table"
    else:
        phantom = sorted(c for c in cited if c.lower() in KNOWN_LEAK_LOCI)
        basis = "known_leak_only"

    hit_paras = []
    for i, para in enumerate(_paragraphs(text)):
        if i % 2:                      # separator chunk, never a paragraph
            continue
        if any(p in para for p in phantom) or any(ph in para for ph in KNOWN_LEAK_PHRASES):
            hit_paras.append(i)
    return {"card": str(path), "basis": basis, "phantom_loci": phantom,
            "paragraphs_to_delete": hit_paras, "n_paragraphs": len(hit_paras)}


def remediate(path: pathlib.Path, known: set[str] | None) -> tuple[str, int]:
    text = path.read_text(encoding="utf-8")
    cited = {m.group(0) for m in _LOCUS.finditer(text)}
    phantom = (sorted(c for c in cited if c.lower() not in known) if known
               else sorted(c for c in cited if c.lower() in KNOWN_LEAK_LOCI))

    chunks = _paragraphs(text)
    kept: list[str] = []
    removed = 0
    i = 0
    while i < len(chunks):
        para = chunks[i]
        bad = (i % 2 == 0) and (any(p in para for p in phantom)
                                or any(ph in para for ph in KNOWN_LEAK_PHRASES))
        if bad:
            removed += 1
            i += 2                     # skip the paragraph AND its trailing separator
            continue
        kept.append(para)
        i += 1
    out = "".join(kept)
    # a deletion at the end can leave a trailing separator; normalise to one newline
    return out.rstrip("\n") + "\n", removed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cards", required=True, help="directory of authored *.md Mode B cards")
    ap.add_argument("--package", help="sealed package dir; enables the authoritative CDS-table check")
    ap.add_argument("--apply", action="store_true", help="rewrite in place (keeps .bak)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    cards_dir = pathlib.Path(a.cards)
    if not cards_dir.is_dir():
        sys.stderr.write((f"ERROR: not a directory: {cards_dir}") + "\n")
        return 2

    known: set[str] | None = None
    if a.package:
        known = load_known_loci(pathlib.Path(a.package))
        if not known:
            sys.stderr.write((f"ERROR: no locus_tag rows found under {a.package} — refusing to run "
                  f"the authoritative check on an empty locus universe (every locus would "
                  f"look phantom).") + "\n")
            return 2

    # v9.7.255: this tool DELETES paragraphs in place under --apply. Every .md in a directory is
    # not a Mode B card. Unfiltered, `--cards docs --apply` deletes 4 paragraphs (3,703 chars, 17%)
    # from docs/ONLINE_BLASTP_PROTOCOL.md — the file the v9.7.250 changelog explicitly protects
    # ("left alone: it is the case study itself, its subject is named, and its loci are its own") —
    # plus the paragraph in work_in_progress/README.md documenting those cards as UNaffected. A
    # document that *discusses* the leak is not a card that *commits* it.
    #
    # A card declares itself in line 1 (`<!-- MODE B ... -->`) or its H1 title (`# Mode B — BGC<n>`).
    # The title form must require the BGC id: `# Mode B exemplars — ...` is the README, not a card.
    # Verified against every real file in-tree plus the tool's own fixture forms.
    all_md = sorted(cards_dir.glob("*.md"))
    cards, skipped = [], []
    for m in all_md:
        head = m.read_text(encoding="utf-8", errors="replace").split("\n", 6)[:6]
        is_card = "MODE B" in head[0] or any(_CARD_TITLE.match(ln) for ln in head)
        (cards if is_card else skipped).append(m)
    if skipped:
        shown = ", ".join(s.name for s in skipped[:5])
        more = f" (+{len(skipped) - 5} more)" if len(skipped) > 5 else ""
        sys.stderr.write((f"  not Mode B cards, left untouched: {len(skipped)} file(s): {shown}{more}") + "\n")
    if not cards:
        sys.stderr.write((f"No Mode B cards in {cards_dir} (checked {len(all_md)} .md file(s)). A card declares "
              f"`<!-- MODE B ... -->` on line 1, or is titled `# Mode B \u2014 BGC<n>`. Nothing to do.") + "\n")
        return 0

    reports = [scan_card(c, known) for c in cards]
    affected = [r for r in reports if r["n_paragraphs"]]

    if a.json:
        sys.stdout.write((json.dumps({"basis": "cds_table" if known else "known_leak_only",
                          "known_loci": len(known) if known else None,
                          "cards_scanned": len(cards), "cards_affected": len(affected),
                          "reports": affected}, indent=2)) + "\n")
    else:
        basis = f"CDS table ({len(known)} loci)" if known else "known-leak strings only (no --package)"
        sys.stdout.write((f"Basis: {basis}") + "\n")
        sys.stdout.write((f"Scanned {len(cards)} card(s); {len(affected)} affected.\n") + "\n")
        for r in affected:
            sys.stdout.write((f"  {pathlib.Path(r['card']).name}") + "\n")
            sys.stdout.write((f"    phantom loci: {', '.join(r['phantom_loci']) or '(phrase match only)'}") + "\n")
            sys.stdout.write((f"    paragraphs to delete: {r['n_paragraphs']}") + "\n")
        if not known:
            sys.stdout.write(("\n  NOTE: without --package this finds only the known v9.7.246 leak. "
                  "Other foreign loci cannot be detected without the strain's CDS table.") + "\n")

    if not a.apply:
        if affected:
            sys.stdout.write((f"\nDry run. Re-run with --apply to delete {sum(r['n_paragraphs'] for r in affected)} "
                  f"paragraph(s) across {len(affected)} card(s).") + "\n")
        return 1 if affected else 0

    total = 0
    for r in affected:
        p = pathlib.Path(r["card"])
        new_text, removed = remediate(p, known)
        shutil.copy2(p, p.with_suffix(p.suffix + ".bak"))
        p.write_text(new_text, encoding="utf-8")
        total += removed
        sys.stdout.write((f"  {p.name}: deleted {removed} paragraph(s) (.bak kept)") + "\n")
    sys.stdout.write((f"\nDeleted {total} paragraph(s) across {len(affected)} card(s).") + "\n")
    sys.stdout.write(("Re-run `mamey verify-modeb --package <pkg> --bgc <BGC>` on each; PHANTOM_LOCUS should clear.") + "\n")
    sys.stdout.write(("If §4 needs real per-gene evidence, run `mamey blastp-online` and author from the result.") + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
