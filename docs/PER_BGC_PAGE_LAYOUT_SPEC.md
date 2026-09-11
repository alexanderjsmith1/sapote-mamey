# Per-BGC Page Layout Spec — locus map + class + Mode B co-location

**Status:** normative. Referenced by `docs/DELIVERABLE_CONTRACT.md` §A2.5 and `prompts/figure_prompts/deliverable_maps/map_gene_by_gene.md`. Applies to every compiled deliverable that pairs a BGC locus map with its analysis: the gene-by-gene deep-dive, the Technical Report's Mode B section, and the consolidated PDF.

## The rule, in one sentence

**Each BGC is a single page-unit: its locus map, its predicted-class line, and its §1–§20 Mode B card all render on the same page — never split a map from the analysis that interprets it.**

## Why this spec exists

The observed failure mode (ChatGPT-side compiler, v9.7.94 run): the master compilation placed **one locus map per page**, each map alone at the top with the lower ~55% of the page blank, and the Mode B prose for that BGC pushed onto the *next* page. Result: a 30-page deliverable is half white space, and the reader must flip back and forth between a map and the text describing it. There was no layout rule anywhere in the contract or the deliverable maps requiring co-location, so the compiler defaulted to one-figure-per-page.

## Page-unit layout (top → bottom)

```
┌────────────────────────────────────────────────────────────┐
│  LOCUS MAP  (gene-arrow panel for this BGC)         ~45%    │
│  ───────────────────────────────────────────────           │
│  ◄═exportase═╗ ╔═KS═╗ ╔═AT═╗ ╔═KR═╗  ◄═TE═╗  ╔═regulator═╗  │
│             (role-coloured arrows; legend once per section) │
├────────────────────────────────────────────────────────────┤
│  CLASS LINE  (one line, claim-safe)                         │
│  BGC024 (NODE_182 · region003) · predicted class: T1PKS ·   │
│  boundary: Interior · KCB: top hit 38% identity (similarity)│
├────────────────────────────────────────────────────────────┤
│  MODE B CARD  (§1–§8 for this BGC)                   ~55%    │
│  §1 Architecture …   §2 Domains …   §3 Boundary/contig …    │
│  §4 KCB & dereplication …   §5 Resistance axis …            │
│  §6 Bioactivity (typed strain-level context, if supplied) … │
│  §7 Novelty …   §8 Wet-lab next step …                      │
└────────────────────────────────────────────────────────────┘
                    one page  =  one BGC
```

### 1. Locus map — top ~45%
The gene-arrow panel for this BGC (role-coloured, from `mamey/locus_map.py` or the figure-prompt equivalent). Legend appears once per section, not per page. If the BGC has multiple loci (split pathway), stack the sub-panels within the 45% band.

### 2. Class line — one line, directly under the map
A single claim-safe line:

```
<BGC_ID> (<contig> · region<NNN>) · predicted class: <antiSMASH class> · boundary: <Interior|Edge|Full-contig> · KCB: <similarity note>
```

- `predicted class` is the antiSMASH region product class (capacity-level; never a compound identity).
- `KCB` is phrased as **similarity, not identity** ("top hit 38% identity" or "no significant hit").
- Carry the contig·region locator (Contract §4 Contig-ID Mandate).

### 3. Mode B card — remaining ~55%
The §1–§20 Mode B analysis for **this** BGC, filling the space below the class line. Section bodies are compact prose; tables wrap, never clip.

## Overflow rule (the only time a BGC spans two pages)

Spill to a second page **only** when a single BGC's Mode B card genuinely does not fit under its map. Then:
- Page 1: locus map + class line + §1–§4.
- Page 2: §5–§8, headed `BGC_ID (region<NNN>) — Mode B cont.`
Never spill merely because the template defaults to one figure per page.

## Worked example (one rendered page)

> **[locus map panel — NODE_182, six gene arrows: KS-AT-KR-DH spanning a module, a flanking oxidoreductase, a TetR-family regulator]**
>
> **`<SID>_BGC024 (NODE_182 · region003) · predicted class: T1PKS · boundary: Interior · KCB: top hit 38% identity (similarity, not identity)`**
>
> **§1 Architecture.** Single contiguous T1PKS region on NODE_182; one complete extension module (KS-AT-KR-DH) plus a loading didomain. Interior boundary — not truncated.
> **§2 Domains.** KS active-site His/Cys present; AT extender consensus = methylmalonyl (inferred); KR + DH indicate a reduced, possibly unsaturated polyketide backbone.
> **§3 Boundary / contig.** Interior; full module set on one node, so architecture is reliable (not a fragmentation artifact).
> **§4 KCB & dereplication.** Best KnownClusterBlast hit at 38% identity — similarity only, well below an identity call; treat as **novelty-leaning**, not "produces X."
> **§5 Resistance axis.** Co-localised TetR-family regulator (efflux/antibiotic-responsive repressor); no diagnostic self-resistance cassette — tier T3 (transporter-only routing).
> **§6 Bioactivity.** State the manifest metadata status exactly. Omitted metadata is `NOT_SUPPLIED`; strain-level observations are not assigned to this BGC without governed linkage.
> **§7 Novelty.** Reduced T1PKS with low KCB similarity = a structural-novelty candidate; capacity consistent with a reduced polyketide, identity unresolved.
> **§8 Wet-lab next step.** Prioritise for expression/fractionation; flag the methylmalonyl extender for backbone prediction. Claim ceiling: capacity-level.
>
> *(map + all eight sections on ONE page; the next BGC starts the next page-unit)*

## Implementation notes

- **ChatGPT-side compiler** (the common case): follow this layout when assembling the gene-by-gene PDF; the deliverable map points here. Build each BGC as a unit (map → class line → §1–§8), then page-break.
- **Engine-side** (`mamey/render_brief.py`, if it ever compiles the per-BGC Mode B set): it already interleaves text + figures per page via `PdfPages`; add a one-BGC-unit-per-page block — render the locus map into the top axes region, the class line beneath, then the Mode B text, before `pdf.savefig()`.

## Do / don't

- ✅ One page per BGC = map + class line + §1–§8 together.
- ✅ Two pages only when one BGC's Mode B overflows.
- ❌ One locus map per page with blank lower half and Mode B on the following page.
- ❌ A "figures section" of bare locus maps separated from a "text section" of Mode B cards.
