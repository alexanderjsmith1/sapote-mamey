# Bert Mode — Citation Verification Protocol

**Sapote–Mamey Bundle v9.7.307 | Literature deliverable standard**
**Status:** `PROMPT_BACKED` — a discipline the assistant applies; not executable code.
**Supersedes:** the v9.4 "three-bucket" standard (Verified / Partially verified /
Unverified leads), which is retired. The status vocabulary and output structure
below are the current ones and match the standalone `literature-digest` skill
(see *Canonical source & drift-check* at the end).

Bert Mode is the citation-verification discipline for every literature
deliverable in the project — the literature-support track, the Path A citation
library, glossary addenda, bench-guide key-reference blocks, and PNAS-style
reference lists. Its single rule: **accuracy over quantity. Never emit a citation
that has not been verified against a primary source this session.**

The full-fidelity form of this discipline (Mode A itemized-in-chat + Mode B
Eden Summary Table workbook, with reference-level detail) lives in the
`literature-digest` skill. This document is the in-bundle, self-contained
statement of the same contract so the bundle stands alone when that skill isn't
loaded.

---

## When Bert Mode is active

- Any time a deliverable will carry citations (literature section, bench-guide
  key-references block, citation library, glossary addendum, manuscript
  reference list).
- When the user says "Bert Mode", "Eden Summary Table", "verify citations",
  "citation library", or "deep literature dive".
- Default-on for the literature deliverable whenever PubMed / DOI access exists.

---

## Two output modes over one verified source set

Both modes draw from the **same** verified entries. They're complementary, not
either/or — Mode A is the quick pasteable draft, Mode B is the durable checked
record. If asked for "both", produce Mode A inline first, then build Mode B from
the same cleared entries so the two can't drift apart. Never let Mode B carry a
citation or number that Mode A's verification didn't clear.

### Mode A — Itemized-in-Chat

One entry per paper (or per finding): a terse declarative claim carrying the key
numbers, followed by its PNAS-style parenthetical and its tags. Dense note-fodder,
rendered inline — do not create a file for Mode A.

```
<Terse claim with the key numbers> (Author et al. Year, Journal Vol:Pages; doi:...).
[evidence: <type> · relevance: <one clause> · <tier>]
```

### Mode B — Eden Summary Table (Excel workbook)

Build with the **xlsx** skill; do not hand-roll openpyxl formatting. Three sheets,
in this order:

1. **Verified Bibliography** — one row per source. Columns: `#`, `Citation (PNAS)`,
   `DOI`, `PMID`, `PMCID`, `Summary` (rich, **with the hard numbers**, in the
   user's register), `Evidence type`, `Relevance` (one clause), `Status`, `Topic`.
2. **Zotero Cleanup** — one row per library issue surfaced during verification.
   Columns: `#`, `Citation`, `Issue`, `Correct value`, `Action`. If nothing was
   found, keep headers + a single "no cleanup items found" row (an empty sheet
   reads as "not checked").
3. **Summary Stats** — the roll-up. Columns: `Metric`, `Value`, `Note`. Counts:
   total sources, count per Status tier, per Evidence type, per Topic, # with DOI,
   # with PMCID, # Partial.

Color-code **by topic** (not by Status — Status is its own column; overloading
color with two meanings makes the sheet unreadable). Legend the topic palette on
Summary Stats. Filename carries the strain/project ID per the user's convention,
e.g. `AS-XXX_LitDigest_BertMode.xlsx`.

---

## Status tiers (current vocabulary)

Assign exactly one tier per entry.

| Tier | Meaning |
|---|---|
| **Verified** | Metadata resolved to a stable identifier **and** the summarized numbers were read from the paper's own full text this session. |
| **Partial** | The record resolves but a wanted number or field couldn't be confirmed from available text. State exactly what's missing. |
| **Policy** | A guideline, standard, or agency page rather than a primary study. Note the "as of" date — these change. |
| **GenBank** | A sequence/assembly record rather than a paper. Cite the accession. |

A deliverable that cannot reach **Verified** for an entry says so explicitly and
places it at the correct lower tier rather than emitting an unverified citation.

---

## The verification standard

Resolve every citation against at least one of PubMed, DOI.org, or the publisher
page. Promote to **Verified** only when all of the following are confirmed
against the primary source *this session*:

- Full author list captured (the abbreviated "et al." is only for the rendered
  PNAS form, never the verified record).
- Journal, year, volume(issue):pages.
- DOI as a resolvable URL (`https://doi.org/...`).
- PMID, and PMCID where one exists.
- Evidence type stated: Experimental / Review / Bioinformatic / Clinical (or the
  finer Mode-B evidence types: in vitro assay, in vivo model, genome mining,
  taxonomy description, guideline, sequence record).

**Resolve each citation to a real record — do not copy it from the citing
paper's reference list.** Reference lists are where wrong-year / transposed-code
/ wrong-volume errors propagate; a digest pasted into a manuscript inherits them.
Cross-check the resolved title against what was cited — a title mismatch means
the identifier is wrong, not the title.

---

## Anti-fabrication rules (hard)

- Never invent a PMID, DOI, PMCID, author list, or page range. A plausible-looking
  identifier that wasn't confirmed is a fabrication, not a citation.
- Never construct an identifier by pattern-guessing. It's either looked up or absent.
- Never reconstruct a citation from memory and present it as verified.
- **Hard numbers come from full text.** Any quantitative claim the user will
  reuse (case counts, MICs, metabolite counts, assembly stats, percentages) is
  pulled from PMC full text or the PDF's Results/tables — abstracts routinely omit
  or round the figure that matters. If full text isn't reachable, the number is
  **Partial**, not "close enough".
- If access is unavailable this session, Bert Mode cannot reach Verified — say so,
  mark the entry Partial, and record the exact search needed to close it.
- If two sources disagree on a field, note the conflict rather than silently
  picking one.
- Don't pad a reference list to a count. Three verified citations beat ten
  unconfirmed ones.

---

## House rules when digesting the project's own genome / BGC work

Bert Mode inherits the pipeline's claim-safety floor. When a summary touches the
project's own strains or BGCs:

- **Capacity, never production** — "capacity consistent with", never "produces".
- **BLASTp / KnownClusterBlast are similarity, not identity.**
- **Bioactivity is extract-level**, never a per-BGC phenotype claim.
- **Cite BGCs by node·region** and tag provenance; reconcile ID collisions first.

These are claim safety, not prose padding — keep them even when trimming for voice.

---

## PNAS citation format

- **Mode A parenthetical:** `(Author et al. Year, Journal Vol:Pages; doi:...)` —
  first author + "et al." for three or more; both names for two.
- **Mode B bibliography:** full reference —
  `Author AB, Author CD, Author EF (Year) Article title. Journal Vol:Pages.` then
  the DOI. Journal names abbreviated per standard usage.
- Paraphrase source claims — never reproduce copyrighted text; preserve the
  source's claim strength (don't upgrade "associated with" to "causes").

---

## Compliance note

Every Bert Mode deliverable ends with a note stating exactly what was verified
this session versus only transcribed, e.g.:

> Bert Mode compliance note. The primary source ([first author] [year]) was
> verified directly against PubMed and the publisher page this session.
> Parenthetical supporting references are Partial: transcribed faithfully from
> the source's reference list but not individually re-confirmed. Any entry
> promoted to a full citation-library entry undergoes its own Bert Mode
> verification at build time.

---

## Integration points (bundle-internal)

- The monolith literature module (BERT MODE v2.0 → verified bibliography +
  anchored summaries) invokes this protocol.
- `examples/citation_library_exemplar.md` is the worked reference output.
- Bench-guide "Key references" blocks cite only **Verified**-tier entries.
- The front-door skill routes here: `skills/sapote-mamey/SKILL.md` →
  "Verify literature citations → `docs/BERT_MODE_PROTOCOL.md`".

---

## What "done" means

Report receipts, not adjectives: row count, count per Status tier, and how many
Zotero cleanup items were found — not "the workbook is complete". For Mode B, all
three sheets present in order with the columns above; every Verified row has a
resolved identifier; every Partial row names its gap; topic color legend present.

---

## Canonical source & drift-check

The upstream, full-fidelity form of this discipline is the standalone
`literature-digest` skill (`SKILL.md` + `references/bert-mode.md` +
`references/citations.md`). That skill is **not shipped in this bundle** — it's
installed into the assistant environment — so this document is the in-bundle
mirror that keeps the bundle self-contained.

To prevent the two from drifting: changes flow **skill → this doc**, not the
reverse. At cut time, diff this file's Status-tier vocabulary and three-sheet
contract against the skill's `references/bert-mode.md`; if they've diverged,
re-sync this doc. The v9.4 → v9.7.307 drift (a stale three-bucket taxonomy that
outlived the Eden Summary Table workflow) is exactly the failure this check
exists to catch.
