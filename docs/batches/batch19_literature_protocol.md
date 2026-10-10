# Literature Deep-Dive Protocol

## Current route and verification scope

Use the scoped [literature search protocol](../LITERATURE_SEARCH_PROTOCOL.md),
[review modes](../LITERATURE_REVIEW_MODES.md) and [Bert protocol](../BERT_MODE_PROTOCOL.md).
The original June 2026 body is preserved as history. Its §8 literature route is obsolete for current
full48 (comparator §8; literature relevance spans the selected content) and current50-v2 (literature
§48/§49, evidence §50). A work-order or model label does not authorize dispatch, fetching or another chat.

The reference bank's recorded verification date is historical metadata, not current-session lookup,
full-text consultation, correction checks or claim support. OPERATOR_SUPPLIED describes provenance,
not verified acceptance. Retain source receipts and distinguish bibliographic verification from inspected
passages/full text; do not require every source to have both a DOI and a PMID. A bounded no-hit search does
not prove no prior characterization or novelty. Verify each bank citation against its actual source before reuse.

The preserved punch-card command has wrong flags. Actual `tools/build_punchcard.py:267–278` takes
`--packages` (one or more existing packages) and an explicit `--out` file; it writes that destination,
not an automatic per-strain file under `--outdir`. Within an authorized task the current parser shape is:

```bash
python tools/build_punchcard.py --packages <existing-package> --out <candidate-punchcard.md>
```

Choose a new output file outside every selected input package and evidence directory, with its parent already present. The helper reads each package's `manifest.json`, prepares the whole Markdown text, then atomically replaces the single `--out` destination. It neither refuses an existing output nor protects input/output overlap: `--out` can overwrite a selected input manifest. Keep original packages immutable, confirm resolved destinations are separate and retain partial/previous files after failure. Success prints counts but provides no consumed-input/output hash receipt; independently retain the input roster, source hashes, options and current output hash. It does not run a literature search or write a returned answer back into packages.

The manifest must contain a `bgcs` array with the selected row fields. Missing `strain_id` falls back to the package basename, which may be a generic folder name rather than a strain identity. Identity checks require truthy strain, contig/node, region and BGC alias values, but do not validate that their spelling, types or linkage are authoritative; whitespace can pass. Admit the actual package roster and complete `strain / full node-or-contig / region / BGC alias` identity before using a question. Duplicate packages/rows are not refused. Shared anchors are grouped by accession plus a product name truncated to 48 characters; question counts describe grouped prompts, not unique validated loci or complete literature coverage.

Optional `--gbk-dirs` entries align with packages by position. Fewer entries silently leave later packages without a marker scan; extra entries are unused. The scanner selects files by the numeric `NODE_` token and text-matches annotations across each matching file, without verifying the region, full contig identity, source strain or gene linkage. The same contig-level match can be attached to more than one region. A row using only `node_id` can have a complete display identity while producing no scan selector, because this selector reads `contig`. Treat emitted marker questions as unbound hypotheses until independently reconciled with exact source/gene/region evidence; no marker output is not a verified absence.

Standard mode summarizes unresolved classes and displays at most ten identities per class, with a remaining count. `--directed` focuses on named anchors and marker questions and omits those unresolved-class questions even though the console still counts cryptic classes. Keyword buckets and built-in deprioritization labels are prompt-routing choices, not assay observations or current policy adjudication. Preserve the entire intended roster alongside either reading view. Questions emitted from package anchors are search prompts, not verified scientific findings. Reference existing evidence by path/SHA-256 without copying packages into a handoff or treating preparation as completed research. Source: `tools/build_punchcard.py:67–114,117–263,266–283`.

<!-- CP018 preserved original body follows. -->
**How to run literature reviews, close §8 deferrals, and use the punch-card**

**v9.7.149a** | Source: `docs/LITERATURE_REVIEW_MODES.md`, `docs/LITERATURE_SEARCH_PROTOCOL.md` | Last updated: 2026-06-29

---

## Overview

Every Sapote analysis defers §8 (Literature support) when network access is unavailable. This document tells you how to close that deferral and how to run literature reviews at two depth levels.

**Key rule:** Never emit a citation that has not been verified against a primary source this session (Bert Mode). A plausible-looking citation from memory is a fabrication, not a reference.

---

## Two modes: FLR and VLR

### FLR — Focused Literature Review

**Purpose:** Bounded, publication-ready contextual literature support for a defined strain, genus, compound class, or BGC interpretation.

**Typical scope:** 10–30 papers.

**Required fields:** key bibliographic verification, evidence type, key quantitative details (when available), one-sentence relevance note, citation-ready reference, explicit claim status.

**Use FLR for:** routine top-lead literature context, genus/source comparisons, compound-family searches, quick support for Mode B interpretations.

**Status label:** `FLR_COMPLETED` or `FLR_PRELIMINARY`

### VLR — Verified Literature Review

**Purpose:** Gold-standard citation verification and deeper extraction. Manuscript-grade.

**Required fields:** DOI/PMID/PMCID/journal-page verification (live lookup), full-text review when available, hard-number extraction, evidence typing, relevance notes, corrections/errata checks, publication-style citations.

**Use VLR for:** manuscript, grant, supplement, final bibliography workbook, producer-genome precedent, MIC/mechanism claims, high-confidence ecological/chemical assertions.

**Status label:** `VLR_COMPLETED` or `VLR_RECOMMENDED`

**Protocol:** `docs/BERT_MODE_PROTOCOL.md` — Bert Mode must be active for VLR.

### Which to use?

| Situation | Mode |
|-----------|------|
| Drafting a Mode B card | FLR |
| Supporting a claim in a paper | VLR |
| Ecological framing for a strain | FLR (or VLR if habitat-specific claim) |
| MIC data for a comparison table | VLR |
| Closing a §8 deferral for internal use | FLR |
| Final bibliography for submission | VLR |

---

## Why §8 is deferred by default

The Sapote interpretation layer runs without guaranteed network access. Protocol §4.8 and §10 require every citation to carry a verified PMID and DOI resolved against PubMed/DOI.org. Rather than fabricate unverifiable references, §8 is logged as `DEFERRED` with a completion path.

To close a §8 deferral:
1. Check the §8 deferral note in the Layer B report for the flagged BGC classes
2. Run the class-specific searches below
3. Verify each DOI at `https://doi.org/[DOI]`
4. Bring PMIDs back to Claude — §8 is written and closed in one pass

---

## The five-bucket search map

For each strain, the §8 deferral names specific BGC IDs and classes. Map those to the searches below.

### Bucket 1 — Top antibacterial lead

| BGC class | PubMed search strings |
|-----------|---------------------|
| NRPS + β-lactamase-fold self-resistance | `nonribosomal peptide synthetase self-resistance beta-lactamase Streptomyces` |
| T1PKS (hglE-KS) | `hglE KS heterocyst glycolipid polyketide synthase` |
| Betalactone / NRP-metallophore | `betalactone biosynthesis Streptomyces antibiotic` |
| T2PKS aromatic | `type II polyketide synthase aromatic Streptomyces self-resistance` |
| Hybrid NRPS/PKS | `hybrid NRPS PKS lipopeptide Streptomyces antibacterial biosynthesis` |
| Lanthipeptide class III | `class III lanthipeptide biosynthesis LanKC` |

### Bucket 2 — Resistance / self-protection framing (always include for any antibacterial lead)

Use these verified bank entries — no re-verification needed:
- **Ogawara2016** (PMID 27171072) — self-resistance to β-lactams in *Streptomyces*
- **Wencewicz2019** (PMID 31288031) — antibiotic biosynthesis / resistance crossroads
- **Yan2020** (PMID 31912842) — self-resistance-gene-directed discovery

### Bucket 3 — Top antifungal lead

| BGC class | PubMed search strings |
|-----------|---------------------|
| T1PKS polyene | `polyene macrolide polyketide Streptomyces antifungal biosynthesis` + compound name |
| Halogenated T1PKS | `halogenated polyketide Streptomyces biosynthesis` |
| Lanthipeptide | `lanthipeptide antifungal biosynthesis mining microorganism` — use **Hegemann2020** (PMID 34458752) from bank |
| NI-siderophore / NRP-metallophore | use **Kramer2020** (PMID 31748738) + **Cassat2013** (PMID 23684303) from bank |
| PTM tetramate (HSAF) | cite **Yu2007** (PMID 17074795) — general HSAF ref, note not bee-specific |

### Bucket 4 — Ecology / habitat framing

| Habitat | Anchor | Bank key |
|---------|--------|----------|
| Bee / insect-associated | Chevrette et al. 2019, *Nat. Commun.* | **Chevrette2019** (PMID 30705269) |
| Wasp / beewolf | Kaltenpoth et al. 2005, *Curr. Biol.* + Kroiss et al. 2010, *Nat. Chem. Biol.* | **Kaltenpoth2005** (PMID 15753044) + **Kroiss2010** (PMID 20190763) |
| Any *Streptomyces* | Seipke et al. 2012, *FEMS Microbiol. Rev.* | **Seipke2012** (PMID 22091965) |
| Strain-specific | `[Genus species] secondary metabolites` | Search fresh |

### Bucket 5 — Strain-specific prior literature

Always run this before §8:
- `[Genus species] secondary metabolites`
- `[Genus species] biosynthesis antibiotic`

If hits exist → first reference in §8.1 (discovery/prior context).
If no hits → note "no prior secondary metabolite characterization reported" — that is a positive novelty statement.

---

## Verified reference bank (no re-verification needed)

All 13 entries below were Bert-Mode-verified on 2026-06-29. Use as `OPERATOR_SUPPLIED` in work orders.

| Key | Authors | Year | Journal | PMID | DOI |
|-----|---------|------|---------|------|-----|
| Chevrette2019 | Chevrette MG et al. | 2019 | Nat. Commun. 10(1):516 | 30705269 | 10.1038/s41467-019-08438-0 |
| Seipke2012 | Seipke RF, Kaltenpoth M, Hutchings MI | 2012 | FEMS Microbiol. Rev. 36(4):862–876 | 22091965 | 10.1111/j.1574-6976.2011.00313.x |
| Yan2020 | Yan Y, Liu N, Tang Y | 2020 | Nat. Prod. Rep. 37(7):879–892 | 31912842 | 10.1039/c9np00050j |
| Ogawara2016 | Ogawara H | 2016 | Molecules 21(5):605 | 27171072 | 10.3390/molecules21050605 |
| Wencewicz2019 | Wencewicz TA | 2019 | J. Mol. Biol. 431(18):3370–3399 | 31288031 | 10.1016/j.jmb.2019.06.033 |
| Blin2023 | Blin K et al. | 2023 | Nucleic Acids Res. 51(W1):W46–W50 | 37140036 | 10.1093/nar/gkad344 |
| Wang2022 | Wang L et al. | 2022 | Sci. Data 9(1):760 | 36494363 | 10.1038/s41597-022-01866-6 |
| Sun2019 | Sun X et al. | 2019 | Biotechnol. Biofuels 12:136 | 31171937 | 10.1186/s13068-019-1472-1 |
| Li2023 | Li F et al. | 2023 | Int. J. Mol. Sci. 24(1):275 | 36613716 | 10.3390/ijms24010275 |
| Takano2003 | Takano E et al. | 2003 | Mol. Microbiol. 50(2):475–486 | 14617172 | 10.1046/j.1365-2958.2003.03728.x |
| Kaltenpoth2005 | Kaltenpoth M et al. | 2005 | Curr. Biol. 15(5):475–479 | 15753044 | 10.1016/j.cub.2004.12.084 |
| Kroiss2010 | Kroiss J et al. | 2010 | Nat. Chem. Biol. 6(4):261–263 | 20190763 | 10.1038/nchembio.331 |
| Yu2007 | Yu F et al. | 2007 | Antimicrob. Agents Chemother. 51(1):64–72 | 17074795 | 10.1128/AAC.00931-06 |

⚠ **Yu2007 scope note:** *Lysobacter enzymogenes* HSAF reference only. Not bee/pollinator-specific. Do not cite as evidence that HSAF functions in bee microbiome defense.

---

## The punch-card

`build_punchcard.py` generates a deterministic literature punch-card immediately after a Mamey run — before any Mode B work. It extracts KCB anchors and gene markers from the package and produces a structured list of "cite-required questions":

```bash
python tools/build_punchcard.py \
  --package runs/[strain]/package \
  --outdir punch_cards/
```

**Output:** `punch_cards/[strain]_punchcard.md` — a numbered table of searches the user can hand to ChatGPT to run in parallel while Mode B is being written. Format per row:

```
BGC locator | compound family | search query | purpose
```

Every row is a search to run, not a verified fact. Nothing from the punch-card may enter a deliverable until citation-verified with a confirmed PMID/DOI.

---

## Dispatching to ChatGPT (for verification)

See `chatgpt_lit_work_order_INSTRUCTIONS.md` for the full dispatch protocol. The short version:

1. Generate the work order (use blank template: `chatgpt_lit_work_order_BLANK_TEMPLATE.md`)
2. Open ChatGPT with web browsing enabled
3. Paste the preamble first (sets Bert Mode)
4. Paste the task blocks
5. ChatGPT returns verified entries — bring them back to Claude to close §8

---

## Literature-Search Handoff list (A2.3)

Instead of writing the literature review inline (which serialises work behind the deep-dive), Sapote emits a structured search list the user can hand to ChatGPT to run in parallel. Format per row:

```
Lead (BGC locator) | search query | purpose | citation purpose
```

ChatGPT returns per row: PMID/DOI, title, one-line finding, and Verified/Partial/Not-found tag. Unmatched rows return Not-found — no fabrication. Nothing from the handoff list may enter a manuscript until citation-verified.

---

## Claim-status labels

Every literature section must declare one of these at the top:

| Label | Meaning |
|-------|---------|
| `FLR_COMPLETED` | Focused review done; fields verified; not manuscript-grade |
| `FLR_PRELIMINARY` | Some citations not yet verified; draft only |
| `VLR_COMPLETED` | Full Bert Mode verification; manuscript-grade |
| `VLR_RECOMMENDED` | VLR not yet run but required for this claim level |
| `LITERATURE_NOT_RUN` | §8 deferred; no literature review performed |

Reports must not imply VLR-grade verification when only FLR/preliminary was performed.

---

## See also

- **Mode protocol:** `docs/LITERATURE_REVIEW_MODES.md`
- **Per-class search map:** `docs/LITERATURE_SEARCH_PROTOCOL.md`
- **Bert Mode rules:** `docs/BERT_MODE_PROTOCOL.md`
- **Punch-card tool:** `tools/build_punchcard.py`
- **Work order system:** `chatgpt_lit_work_order_INSTRUCTIONS.md`
- **Verified bank (full):** `verified_reference_bank_2026-06-29.md`
