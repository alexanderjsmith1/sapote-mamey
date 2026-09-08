# Volume VI — Deliverables & Outputs

*Edition: bundle v9.7.33 / engine Mamey 1.9.41 · re-grounded to bundle v9.7.91 / engine Mamey 1.9.91 on 2026-06-20 (strain_display_label(), the cap-40 figure_policy SSOT, the v9.7.45 4c AB/AF lead boards, the v9.7.46 Mode B deep-dive machinery — build_modeb_deepdive.py / deep_data.py with the CONFIRM/DOWNGRADE/DROP verdicts — and the v9.7.46/47 ingest_package.py merge with its mandatory schema gate all re-verified against the running engine) · 2026-06-15*
*Chapters VI.1–VI.10. Read Volumes I–III first (→ Master Index).*

> **Tag note for this volume.** Alongside <span class="tag t-engine">\[engine\]</span> (ships today) and <span class="tag t-concept">\[concept\]</span> (framing), this volume uses
> <span class="tag t-spec">\[spec\]</span> for a deliverable that is *defined and contracted* (in the deliverable spec) and being **encoded as a
> default output**, but is not yet auto-emitted by the package generator. The distinction is itself claim-safety:
> the volume never implies a deliverable is automatic when it is still hand-run.

------------------------------------------------------------------------

## §VI.1 · The deliverable contract

A run's worth to a reader is its deliverables — the artifacts a human opens to act on the strain. The deliverable
contract is the project's answer to a specific gap: the deterministic layer (Volume II) ships a complete,
honest, checksummed package, but that package historically stopped at *"extraction complete · judgment
pending."* The reader-facing judgment deliverables — the leads note, the DAPR ranking, the Mode B dossiers, the
layperson's guide, the fermentation card, the cross-comparative synthesis — were produced by hand. The contract's
goal is to make a **"Sapote Analysis" emit that full reader-ready set by default, in batches** (→ §VI.9), so the
package is act-on-able out of the box. <span class="tag t-concept">\[concept\]</span>

Two invariants govern every deliverable, automatic or spec'd:

1.  **The global claim-safety contract** (→ §I.3) applies to all of them, identically: capacity not production;
    KCB = similarity not identity; bioactivity extract-level (MRSA + *Candida*), never pinned per-BGC without
    fractionation; no strain called antibacterial/antifungal-negative; standing downgrades applied; **every BGC
    printed as `BGC_ID | contig | region | boundary`**; mobile-element-flagged BGCs excluded from ranked and
    comparative claims (→ §III.6).
2.  **Honest incompleteness.** A deliverable produced from a partial run says so; the package's `analysis_status`
    is `COMPLETE` or `PARTIAL(reason)`, and a partial run stamps the gap into the brief banner — nothing silently
    ships half-done (→ §VI.9). <span class="tag t-spec">\[spec\]</span>

The chapters that follow take each deliverable in turn: what triggers it, what it reads, its required shape, and
the claim-safety constraints specific to it.

## §VI.2 · The strain brief and the leads note

The **strain brief** is the deterministic front matter that ships with every run today — the headline figures
(raw and corrected counts, assembly tier with its interior-% band, → §II.5), the figure gallery, and the
**"DETERMINISTIC EXTRACTION COMPLETE · JUDGMENT LAYER PENDING"** banner that tells the reader exactly how far the
analysis has gone. The brief is honest by construction: it presents what the deterministic layer knows and
flags what it does not. <span class="tag t-engine">\[engine\]</span>

**The brief text page, top to bottom (`render_brief._text_page`, A4).** Every element is a deterministic fact or
an honesty marker; nothing here is a judgment-layer claim. <span class="tag t-engine">\[engine\]</span>

| Element | Content |
|----|----|
| Header | strain label (the `strain_display_label` form, → §VI.3); taxonomy · source · release; `Mamey <version> · <analysis_date>` |
| **Honesty banner** | the boxed "DETERMINISTIC EXTRACTION COMPLETE · JUDGMENT LAYER PENDING" — the single highest-value clarity item; a reader must never mistake a finished extraction for a finished analysis |
| Suppression line | "*N* pure-saccharide region(s) suppressed from priority figures · all *N* BGCs retained in data" — the figure omission stated in the body, not buried in a footnote |
| Corrected-count headline | `Corrected BGC count <c> (Interior + ½·Edge + ¼·Full-contig)`; raw · interior · edge · full-contig · assembly tier (band) |
| Assembly line | genome bp · contigs · N50 · GC% |
| Bioactivity line | targets (default-assumed MRSA + *Candida*, extract-level) · status · compound linkage (not established) |
| **Top leads** *(standard tier)* | top-5 auto-priority cards — "priority score, not activity" — each: `bgc_id · contig/region · boundary · products · tier · AB/AF · KCB · CCTT` (node/contig always shown) |
| Source scans *(standard)* | the scan roster (up to 8): `name: status — detail` |
| Self-resistance *(standard)* | genome-wide resistance-gene counts, labelled "not BGC-linked claims" |
| **Reading guards** (footer) | the score note, the KCB "(similarity, capacity-level, not 'produces')" note, the bioactivity-default/no-negative-call note, and the gap note |
| Judgment-slots line | names the pending Sapote judgment slots and states they are *not rendered here* |

Two structural facts. The brief is **tier-aware**: both tiers render the header/headline/banner + the landscape
figure; only `standard` adds the top-leads cards, the scan roster, the self-resistance line, and the composition
figure. And brief rendering is **non-blocking** — a render failure returns `SKIPPED` and never raises into the
build, because the brief is a convenience surface, not the sealed deliverable (→ §II.7); the package is valid with
or without it. <span class="tag t-engine">\[engine\]</span>

The **strain leads note** (deliverable spec A) is the judgment-layer front page that completes the picture: a
≤1.5-page note triggered on every run, reading the triage board (rank, AB/AF, boundary, architecture, CCTT
triggers, KCB top) and manifest. Its required shape: a header line (strain, accession, raw/corrected, tier);
the top three-to-five *genuine* leads — mobile-element-flagged regions excluded from the list and named instead
under caveats — each with its contig/region and a one-line capacity statement; a caveats block (truncation, KCB
conflicts, mobile elements); and an explicit "what's blocked" line (e.g. ecology, when the source habitat is
unknown). Lead lines are capacity-level; a region with a mobile-context HGT flag never appears in the lead list.
<span class="tag t-spec">\[spec\]</span>

## §VI.3 · The figure system and the data-only CSV discipline

Figures are deterministic and shipped today, and they follow one strict discipline: **every figure is a
data-only PNG with a companion `*_data.csv`** carrying the exact values it was drawn from. A reader (or a
reviewer, or a future re-plot) can reconstruct the figure from the CSV; the picture never carries data that the
table does not. The figure data CSV also records what was shown versus suppressed — for the BGC landscape, the
companion CSV holds **all** rows with `shown_in_figure` and `suppressed_saccharide_only` columns, so a
saccharide region omitted from the plot (per the standing downgrade, → §I.6) is still accounted for in the data,
never silently dropped. <span class="tag t-engine">\[engine\]</span>

**The two figures, field by field (`fig_landscape`, `fig_composition`).** <span class="tag t-engine">\[engine\]</span>

*Landscape (`_8a_fig_landscape.png`) — the priority figure.* One horizontal row per BGC (capped at **40**, with an
on-figure "+N more … (all in \_data.csv)" note rather than a silent trim). Each row draws **two bars on a 0–100
axis**: a **solid** bar = AB (antibacterial priority) and a **faded** bar = AF (antifungal); the **bar colour
encodes boundary** (Interior / Edge / Full-contig); a **tier swatch** (Exceptional / High / Medium / Inventory)
sits in a **right gutter** past the axis, with its own legend. Y-labels are `bgc_id · contig/region`; the title is
"BGC priority landscape — *\[strain label\]*"; the footer states "Data-only figure · … · capacity-level ·
pure-saccharide regions omitted (retained in \_data.csv)." Pure-saccharide rows are removed *via* `figure_policy`
(the single source of truth — the renderer never re-derives the policy), so the cap only ever trims genuine
surplus leads.

*Composition (`_8b_fig_composition.png`, standard tier) — the genome-shape figure.* Two panels: **left**, a
horizontal bar of the **top-8 antiSMASH product classes** by occurrence count; **right**, a stacked bar of the
**assembly boundary mix** (Interior / Edge / Full-contig counts). Footer: "Data-only · *N* BGCs · antiSMASH
product-label occurrences."

*The landscape companion `_8a_fig_landscape_data.csv` — all rows, evidence-conserving.* Fourteen columns, one per
**every** BGC (not just the 40 shown): `rank, bgc_id, contig, region, boundary, arch, ab_auto, af_auto, novelty_auto, lead_tier_auto, kcb_score, cctt_triggers, shown_in_figure, suppressed_saccharide_only`. The last two
are the conservation guarantee: a region absent from the plot is present in the CSV with `shown_in_figure=False`
and, if applicable, `suppressed_saccharide_only=True` — so the figure can hide a row but the data never loses it.
<span class="tag t-engine">\[engine\]</span>

The layout obeys the render_brief.py policy that the figures and tables share (→ §VI.4): a row-capped figure prints
an on-figure "+N more" note rather than truncating silently, the tier swatch sits in the right gutter clear of
the axes, and strain names render as *Genus species* strain `<ID>`. The principle is the same as the
deliverable contract's: a figure is a claim, and a claim must be reconstructible from stated data. <span class="tag t-engine">\[engine\]</span>

**Provenance and strain-name discipline (figures and their CSVs).** Two reader-facing rules harden the figure
system. First, **provenance**: a saved PNG should carry an edition footer (`bundle vX.Y.Z · engine A.B.C · `) and its companion CSV an edition header, so a re-plot or a reviewer can tell which engine
produced which numbers — scores do shift across engine versions, and an undated figure cannot be trusted. Second,
**the strain label**: every figure title and reader-facing strain mention renders the standing
*Genus species* strain `<ID>` form (italic genus, roman "strain", the ID), **never an accession fragment** — a
strain is never labeled by the first letters of its WGS accession (the engine's `strain_display_label()` helper
guarantees this on the brief side, falling back to the canonical id, then to the *whole* accession with a loud
"no strain name" warning, never a slice). The companion CSV keeps the internal `strain_id` column for machine
use; the rendered title is the organism name. <span class="tag t-engine">\[engine: brief/figure path; strain_display_label() helper\]</span>

## §VI.3b · Node-first locus label contract <span class="tag t-engine">\[engine\]</span>

All boss-facing outputs — figures, lead tables, DAPR boards, the layperson guide, and any
paper-facing deliverable — must use **node-first locus labels**:

    NODE_162 region001 (BGC008)

The node or contig name is the assembly locator: it is the string that lets a reader open the
antiSMASH output and find the region in their genome browser. The BGC ID (`BGC###`) is the
internal stable identifier used in the workbook, CSVs, and cross-strain comparisons. **A bare BGC
ID alone is never a sufficient boss-facing label** — it requires the reader to look up a separate
crosswalk table, and it cannot be found directly in an antiSMASH HTML.

Node-first labelling is enforced by the engine: the crosswalk sheet, the triage board, the
DAPR tables, and the figure labels all carry both the contig/region locator and the BGC ID in
the format above. Downstream CSV consumers must read by header name, not positional index, so
that adding or reordering columns in the triage board does not silently misalign the label.
<span class="tag t-engine">\[engine\]</span>

## §VI.3c · Figure label context rules <span class="tag t-engine">\[engine\]</span>

A well-formed lead-chart label answers three questions for the reader without requiring a
separate lookup:

1.  **Where is the locus?** — node/contig and region.
2.  **What kind of lead is it?** — product class or diagnostic trigger.
3.  **Why did the system surface it?** — top KCB/MIBiG context or CCTT trigger family.

Example of a correctly formed label:

    NODE_162 region001 (BGC008)
    nucleoside Antifungal lead; nikkomycin/polyoxin-like context

The product class and KCB context are **explanatory**, not identity claims. The caption must
state that KCB/MIBiG context is similarity evidence, not confirmed compound identity (→ §I.3).
Lead charts must spell out **Antibacterial** and **Antifungal** in full; the abbreviations AB/AF
may appear in CSV column names and internal fields only. <span class="tag t-engine">\[engine\]</span>

## §VI.4 · DAPR — the AB/AF priority table

**DAPR** (dual antibacterial/antifungal priority ranking, deliverable spec B) is the ranked triage a
bench scientist reads to choose targets. Triggered every run, it reads the triage board's AB/AF axes, boundary,
architecture, KCB, CCTT triggers, and location, plus the manifest's mobile-element flag, and emits: **Track A**
(antibacterial, ranked by AB), **Track B** (antifungal, ranked by AF), a **dual-threat** list (top-quartile on
both), an **excluded list** (mobile-element and standing-downgrade regions, each with its reason), and a
**mandatory footer** restating that bioactivity is extract-level and that absence of recorded activity is not
evidence of inactivity. <span class="tag t-spec">\[spec\]</span>

DAPR is where the claim-safety guards become visible to the reader: a mobile-element region (→ §III.6, the \#28
demotion) lands in the **excluded list**, never the ranked tracks, with its exclusion reason stated; the KCB
column is labeled "similarity." Tables cap at ten per track with a "+N more" pointer and the full set in the
companion CSV. DAPR ranks dual *threat by mechanism* — it never asserts a strain *is* antifungal-active; it
ranks which clusters carry the antifungal *capacity* worth testing first.

**Worked sketch (real v9.7.33 run — the Attine *Pseudonocardia*).** What a DAPR table makes of this strain:
<span class="tag t-engine">\[engine: real run; strain in the PRIVATE worked-examples key\]</span>

| DAPR element | Content for this strain |
|----|----|
| **Track A** (antibacterial) | the one T43-THA-corroborated RiPP lead (AB 59.9) at the top; the rest a long Inventory tail |
| **Track B** (antifungal) | no AF-diagnostic lead; the highest AF rows are Saccharides, which the footer's logic excludes from a capacity claim |
| **Dual-threat** | empty — nothing reaches the top quartile on both axes |
| **Excluded list** | the Saccharide-class regions (standing-rule downgrade) and the `hglE-KS` PREV-001 region, each with its reason; the five Promiscuous T43-HAL loci are simply low-ranked, not excluded |
| **Footer** | "Bioactivity is extract-level (MRSA + *Candida* default); absence of recorded activity is not inactivity; contrast strains by mechanism, not phenotype." |

The sketch shows DAPR doing its job on a low-yield strain: it surfaces the single defensible antibacterial lead,
declines to manufacture an antifungal ranking from Saccharide noise, and names the downgraded regions so the
reader sees *why* a region a raw score would rank is absent. A near-empty DAPR is an honest DAPR.

**Reading one Track-A row, field by field.** What a single ranked row actually carries, using the public flagship
of WAC 01438 (`NZ_CP029601.1`, BGC044): <span class="tag t-engine">\[engine: real run on a public genome\]</span>

| Column | Value (this row) | How to read it |
|----|----|----|
| **Rank** | 1 (Track A) | the engine's order on the AB axis after all guards; rank-1 means *read this first*, not *this is confirmed* |
| **Region** | `BGC044 \| contig_x \| region044` | always carried with contig and region: a bare `BGC044` would be unciteable |
| **Boundary** | Interior | the region sits ≥5 kb from both contig ends, so its size and module count are *trusted*, not floored |
| **AB / AF** | AB 65 (High) · AF lower | the headline axes; AB 65 lands High (≥70 would be Exceptional), AF below threshold means this is an antibacterial-track lead, not a dual-threat |
| **Architecture** | NRPS/PKS megacluster, ~187 kb, arch confidence HIGH | a large, well-resolved modular cluster: the structural call is trusted, distinct from the lead tier |
| **KCB** | glycopeptide / enduracidin-class **(similarity)** | the anchor, rendered as a *band with the "(similarity)" qualifier* — capacity consistent with a glycopeptide, **not** "produces enduracidin" |
| **CCTT** | corroborated class trigger present | the class call is corroborated by a gene signature, not a bare label, which is *why* it ranks above a keyword-only region |
| **Mobile flag** | (none) | not ICE-dominated, so the \#28 demotion does not touch it: contrast BGC032, below, which is excluded for exactly this |
| **WL** | high band | a large Interior cluster with a clean class call and a detection handle scores well on wet-lab readiness, so "rank 1" and "ready for the bench" agree here (they do not always, → §VIII.1 WL) |

The row teaches the read: every cell is a *qualified* statement (similarity not identity, capacity not production,
trusted-vs-floored boundary), and the rank is an ordering of *where to look first*, never a verdict. The contrast
row is BGC032 from the same strain: it does **not** appear in Track A at all (it is in the **excluded list** with
"mobile-dominant, non-class-typed" as its reason), which is the visible output of the label-vs-domain guards (→
§V.4). Reading DAPR well means reading the excluded list too: it is where the engine shows its work.

**Where the AB/AF leads actually live, and the v9.7.45 dedicated board files.** Until v9.7.45 the per-axis
ranking was implicit: the triage board (`<strain>_4_triage_board.csv`) carried the antibacterial and antifungal
scores in the `AB_auto` and `AF_auto` columns, but the rows were ordered by a single general `Rank`/`corrected_rank`,
so a reader wanting "the antibacterial board" had to re-sort the triage CSV by `AB_auto` themselves — and the
distinction between the **raw** score order and the **corrected** order (after the standing-rule and primary-metabolism
demotions are applied) was easy to miss. v9.7.45 (B-8) makes the two axis boards first-class deliverables:
`<strain>_4c_AB_lead_board.csv` and `<strain>_4c_AF_lead_board.csv`. Each is **pre-sorted** — clean leads first, by
descending axis score — with standing-rule and primary-metabolism rows **marked in a `Downgrade` column and sunk to
the bottom rather than dropped** (absence is never evidence, so an excluded row is still shown, just demoted). The
boards are auto-tracked into the package manifest, and `START_HERE.md` points at them. The practical effect is that
the antibacterial board now leads with the genuine clean lead — on a real strain whose raw `AB_auto` \#1 was a
saccharide region, the dedicated board surfaces the clean NRPS/halogenase cluster at the top and sinks the saccharide,
which is the standing rules doing visible work at the board level rather than only inside the rationale. <span class="tag t-engine">\[engine: v9.7.45\]</span>

## §VI.5 · Mode B — the tiered compendium and the §1–§8 deep report

Mode B is the gene-by-gene per-BGC analysis (its §1–§8 anatomy is Volume III, → §III.2). As a deliverable it
comes in two coupled forms. The **tiered Mode B compendium** (deliverable spec C, every run) is the
strain-wide map: a four-line tier legend and tier census, then every BGC grouped by tier in BGC-ID order, each
carrying its `contig | region | boundary`. Ledger and one-line entries are single rows; Full entries link to the
deep report. <span class="tag t-spec">\[spec\]</span>

The **Mode B per-BGC deep report** (deliverable spec D) is the full §1–§48 dossier, emitted for every
**High-tier / Full** lead (and on request for any BGC). It reads the pass-1 gene inventory (locus tags, domains,
categories), the region GBK domains, the triage row, the KCB line, and the boundary, and fills the fixed
skeleton — §1 boundary, §3 the gene-by-gene domain table with role assignment, §5 the mechanism hypothesis with
an explicit KCB-vs-content reconciliation where they conflict, the **§34 trap card** (truncation / keyword-only /
cross-genus / mobile-element checks, → §III.7), and §8 the safe claim plus wet-lab next step. Its claim-safety
constraints are exact: the §8 claim is capacity-level; an A-domain substrate prediction is never elevated to a
residue or sequence; a size or module count on an Edge/Full-contig region is tagged "floor." <span class="tag t-spec">\[spec\]</span>

**A Mode B card walked end to end (the instructive case: WAC 01438 BGC032).** The most teaching-rich card is not a
clean flagship but the one where the guards do visible work, because it shows the reader what each section is *for*.
BGC032 is the ICE that masqueraded as a lanthipeptide lead (→ §V.4); here is how its Mode B dossier reads section
by section. <span class="tag t-engine">\[engine: real run on public `NZ_CP029601.1`; structure per the §1–§8 spec\]</span>

1.  **§1 Identity & boundary**: `BGC032 | contig | region032`, Interior, antiSMASH label `lanthipeptide-class-v`. The boundary is trusted (Interior), so a reader cannot dismiss what follows as a truncation artifact: the problem is not that the region is fragmentary, it is that the label is wrong.
2.  **§3 Gene-by-gene domain table**: this is where the card earns its keep. The in-region CDS resolve to a **T3SS effector HopA1** and a **phosphotransferase (APH/AAC family)**, plus ICE machinery (integrase, recombinase, transposase, conjugation, replication-initiator). **There is no LanC/LanM cyclase in the region**: the nearest genuine lanthionine synthetase sits \>1.7 Mb away on the contig. The gene table is the evidence that the class label has no enzymatic basis here.
3.  **§5 Mechanism hypothesis with KCB-vs-content reconciliation**: the section where a conflict must be named, not smoothed. The KCB anchor leans siderophore-ish, the label says lanthipeptide, and the gene content says *mobile element carrying a resistance gene*. The reconciliation states plainly that the content does not support the lanthipeptide call and that the APH/AAC is not class-concordant with any biosynthetic product in the region.
4.  **§34 trap card**: every check fires. *Keyword-only?* yes (the class is label-derived, no defining enzyme). *Mobile-element?* yes (five mobility families, mobile-dominant). *Cross-genus / mis-anchor?* the resistance is non-concordant cargo. The trap card is the single place a reader can see, at a glance, that this region tripped the guards.
5.  **§8 Safe claim + wet-lab next step**: the only defensible statement is that BGC032 is an **integrative/conjugative element carrying horizontally-acquired resistance cargo, with no corroborated biosynthetic class capacity** — capacity-level, claim-safe, and explicitly *not* a discovery lead. The wet-lab next step is "none as a lead": the card's honest output is to send the reader elsewhere.

The walked card is the whole claim-safety doctrine in one page: §3 supplies parsed-domain evidence, §5 refuses to
reconcile a conflict by picking the convenient reading, §34 makes the guards legible, and §8 holds the claim to
what the genes support. Read against the clean flagship (BGC044, whose §3 shows a real NRPS/PKS module census and
whose §8 carries a genuine glycopeptide-capacity claim with a fractionation next step), the two cards teach the
reader the same lesson from opposite ends: *the card's job is to make the evidence trail visible enough that a
wrong call cannot hide.*

**The gene-by-gene verdict layer as a wired run step (v9.7.46).** The Mode B deep report above is built by
`tools/build_modeb_deepdive.py`, which reads three banked gene-level inputs: `deep_data.json` (per-BGC domain
profile, active-site calls, class predictions), `gene_data.json` (the ordered domain architecture, substrate
consensus, RiPP cores), and `modeb_verdicts.csv` (the per-BGC status). Before v9.7.46 the standard run never emitted
these, so the deep-dive **degraded to verdict-less placeholder cards** — every `§2` architecture line came out as
`?` because the domain counts were never banked. v9.7.46 (B-9) makes a **gold-mode** run emit all three from the
package's own snapshot and evidence parse (the SSOT extractors live in `mamey/deep_data.py`, which the cohort-bank
tool now imports rather than duplicating). The deep-dive then runs directly from the package. <span class="tag t-engine">\[engine: v9.7.46\]</span>

The verdict column carries one of three statuses, and the semantics matter because they are the framework's own
read of whether the gene content supports the anchor: **CONFIRM** = the gene logic supports the anchor's class;
**DOWNGRADE** = a real locus, but reclassified out of the lead set (a standing-rule class exclusion — saccharide /
NAPAA / hglE — or a **mis-anchor**, where the KCB anchor lacks its class diagnostic gene); **DROP** = the anchor's
biosynthetic class is not supported at the locus at all (primary-metabolism / housekeeping core — the framework
saying no). The emitted `modeb_verdicts.csv` is a **deterministic first-pass scaffold** keyed on those flags; it is
explicitly the floor that the Sapote judgment layer refines, not the final gene-by-gene call. Its measurable value
over the standing-rule board is the **mis-anchor demotion**: on a 64-BGC strain the scaffold moved 3 of the top-12
antibacterial leads off CONFIRM, two of them saccharide exclusions the board already sinks and **one a mis-anchor the
deterministic board kept** — the new signal the gene-by-gene layer contributes. The flagship leads (the nikkomycin
antifungal lead, the split indolocarbazole pair) all returned CONFIRM and held their board positions. <span class="tag t-engine">\[engine: v9.7.46 verified\]</span>

## §VI.6 · The layperson's plain-language guide

The **layperson's guide** (deliverable spec E) makes a run legible to a non-specialist — a collaborator, a
student, a grant reviewer. Triggered on every GOOD/MODERATE assembly (skipped for FAILED), it reads the manifest
counts and tier, the leads note (§VI.2), and DAPR (§VI.4), and renders in a fixed annotation style: a
**statement followed by a *Plain note* gloss**, every acronym expanded on first use, every metric explained
number-by-number, and each claim tagged **observed / computed / inferred / assumed** — the project's epistemic
vocabulary made explicit for a reader who needs to know how much to trust each line. It ships as MD + PDF +
DOCX, uses capacity language throughout, and draws only on PUBLIC examples — no unpublished identifier appears in
a guide meant to be shared. <span class="tag t-spec">\[spec\]</span>

## §VI.7 · The fermentation / bench card

The **fermentation / bench card** (deliverable spec F) is the one deliverable in this volume **not yet built** —
it is contracted and specified, awaiting implementation. It is scoped to the top-two AB and top-two AF DAPR
leads, reading those leads, their Mode B §8 wet-lab lines, the manifest's bldA tier and regulators where present
(→ §II.3), and the KCB detection handle. Its required content per lead: the target; induction/expression notes;
a **detection handle** (a UV/MS signature to track the molecule); an isolation priority; and a long-read-sequencing
flag when the cluster is on an Edge/Full-contig boundary. Its claim-safety constraints are strict precisely
because it is the most action-oriented deliverable: capacity-level only, **no yield or titre claims**, activity
kept extract-level. Until it is built, the package does not emit it, and this volume says so rather than implying
otherwise. <span class="tag t-spec">\[spec\]</span>

## §VI.8 · The cross-comparative synthesis

The **cross-comparative synthesis** (deliverable spec G) is the cohort-level deliverable, triggered when a run
covers two or more strains. It reads the per-strain inventories and leads and emits a shared-versus-unique
capacity comparison drawn **by biosynthetic mechanism, never by phenotype** (the presence or absence of a
dedicated cluster, not a claim that one strain "is" more active than another, → §I.3), with mobile-element
regions excluded and one comparative figure plus its companion CSV. <span class="tag t-spec">\[spec\]</span>

One rule here is a hard methodological guard carried from Volume VII: **cohort-local layers are recomputed, not
concatenated.** A product-class matrix or a gene-cluster-family grouping is computed *within* a specific cohort;
when the cohort changes — a strain added, a merge performed — those layers must be recomputed from the new
membership, never stitched together from the old. Concatenating a cohort-local layer across a merge silently
produces a matrix that describes no real cohort. The synthesis is honest only when its comparative layers
describe exactly the strains in front of it. <span class="tag t-spec">\[spec/concept\]</span>

**The cross-strain merge, exercised end to end (v9.7.46/47).** The merge that builds the cohort behind a synthesis
is not a concatenation; it is a gated ingest with a verification contract. Each per-strain package is banked through
`tools/ingest_package.py --merge`, which applies a **mandatory schema gate**: the first source establishes the
cohort's schema version and every subsequent source must match it or the bank refuses it — this is the engine
enforcing *normalize-before-append*, so divergent-schema sources can never be silently stitched together. The merge
then verifies, fail-closed: **`bgc_uid` (= `sid:BGC_ID`) global uniqueness** (a collision blocks the merge), a
**per-source row-count reconciliation**, and **release tagging** — a merged set containing any unpublished `AS-`/`AJS`
strain is auto-tagged **PRIVATE**. The **export-safe PUBLIC cut** is then produced by filtering to the public strains
and **audited for leaks** (a scan for any `AS-###` / `AJS-###` token must come back clean) before it can be shared. A
worked instance: an 11-strain actinomycete cohort (7 public + 4 AS) banked to **678 BGCs, `bgc_uid` 678/678 unique,
0 collisions**, reconciling to 172 AS + 506 public; the PUBLIC cut was 7 strains / 506 BGCs with **zero AS tokens**.
The cohort-local product-class layer was then **recomputed from the 678 merged rows**, per the rule above, never
carried over from the per-strain matrices. One consistency note from that exercise (fixed in v9.7.74): the bank's
cohort classifier must consult the same accession→SID resolver the run uses (→ Vol I taxonomy), or WGS-deposited SID
strains bank as REF while the run calls them SID. <span class="tag t-engine">\[engine: v9.7.46/47 verified\]</span>

## §VI.9 · Batching a full Sapote Analysis

A full Sapote Analysis on a large strain (100+ BGCs) is too big for one pass, so the deliverable set is produced
in **batches** by a runner. The batch model (from the deliverable batching plan): strain-level deliverables are
one bounded pass each over the triage board; the only unbounded part — the per-BGC Mode B §1–§8 layer — is
**windowed at 15 BGCs**, which matches the run profile's batch rule and stays within a reliable generation
budget (≈ 6–10k tokens of output per batch). A 100-BGC strain with ~20 High-tier leads is roughly seven batches.
<span class="tag t-spec">\[spec\]</span>

The runner walks a **strict order**, because later deliverables read earlier ones: metadata → tiering → leads
note → DAPR → compendium skeleton → Mode B §1–§8 (BGC-ID order, High-tier first, 15 per window) → fermentation
card → layperson's guide → cross-comparative (cohort, after all strains). **Recombination** stitches in that
reading order; Mode B windows are keyed by `BGC_ID` (last-write-wins on a duplicate), and the union is asserted
to cover every BGC exactly once — **fail-closed against the antiSMASH region count**, reusing the completeness
gate (→ §III.7). A **final consistency pass** confirms every BGC carries `contig | region | boundary`, that no
mobile-element region leaked into a ranked or comparative claim, that the phrasing is claim-safe (no "produces,"
no bare compound identity), and that any KCB-vs-content conflict flagged in Mode B is reconciled back into the
leads note. <span class="tag t-spec">\[spec\]</span>

**Resumption** is explicit: each batch writes a `BATCH_STATE.json` (`{deliverable, window, status, bgc_ids_done}`),
and a resumed run continues from the first `PENDING`. The package manifest carries `analysis_status = COMPLETE | PARTIAL(reason)`; a partial run **must** stamp `PARTIAL` and list the missing windows in the brief
banner — the same honest-incompleteness rule the deterministic brief already follows (→ §VI.2), now extended
across the whole judgment layer. An over-budget window **splits** (15 → 8 + 7) rather than truncating silently;
a missing input emits an explicit "input unavailable — not assessed" line rather than a guess. The net: kick off
"Sapote Analysis," and the runner walks the steps, windows the Mode B layer, records its state, runs the
consistency pass, and emits one reader-ready package marked `COMPLETE` — or `PARTIAL` with the exact gap named. <span class="tag t-spec">\[spec\]</span>

------------------------------------------------------------------------

## §VI.10 · Special review buckets <span class="tag t-engine">\[engine\]</span>

Some BGC rows must be surfaced for human review even when they are not top-ranked by the
composite AB/AF score. The engine maintains four **special review buckets** that operate as
deterministic surfacing rules — they do not claim product identity, they ensure
high-value evidence is not buried by generic rank cut-offs.

- **Nucleoside priority.** Nucleoside and peptidyl-nucleoside loci (nikkomycin/polyoxin-family
  architecture, aminonucleoside logic, polar compound caveats) are always surfaced for antifungal
  review regardless of composite rank. Use polar/ion-exchange-aware extraction notes. This is a
  mechanism hypothesis, not a product claim.
- **Polyene/PTM/HSAF flags.** Large modular PKS-KS regions consistent with polyene, post-translational
  modification, or heat-stable antifungal factor architecture are flagged for antifungal review.
  **Arylpolyene alone is not sufficient** to claim antifungal polyene macrolide capacity — large
  modular PKS-KS context is required before that inference is drawn.
- **Other-token rows.** antiSMASH `other` is a generic fall-through product token. It is not a
  final class assignment and it is not junk. Every `other`-labelled row requires gene-level
  review; the class may be determinable from domain content even when antiSMASH has not assigned
  it. These rows appear in a dedicated special-review section of every report, even when the count
  is zero (zero is reported explicitly rather than omitted).
- **RG-GMCI HIGH pairs.** Reference-guided gapped multi-contig integration pairs scored HIGH are
  possible split-pathway reconstructions (→ §IV.4). They are hypotheses about biosynthetic
  co-localisation on fragmented assemblies, not confirmed physical contig joins. Each HIGH pair
  is reported with its evidence trail and the interpretation guard.

Special review bucket rows are populated deterministically by the engine and written to the
triage board, the DAPR tables, and the per-strain workbook. They travel with the package;
they do not depend on Sapote judgment. <span class="tag t-engine">\[engine\]</span>

------------------------------------------------------------------------

*End of Volume VI. The deliverable spec and batching plan that ground this volume are archived at `feedback/1WAC_output_spec.md` and `feedback/1WAC_batching.md`; the encoding of these as default outputs is a tracked workstream in the backlog. (Re-grounding pass: Volumes I–VII done; remaining — Volume VIII — Reference & Apparatus, and the back matter X–XIII.)*

</div>

<div id="vol7" class="section vol">
