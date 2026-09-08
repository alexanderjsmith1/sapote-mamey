# Volume I — Foundations & Concepts

*Edition: bundle v9.7.33 / engine Mamey 1.9.41 · re-grounded to bundle v9.7.91 / engine Mamey 1.9.91 on 2026-06-20 (assembly tiers, corrected-count weights, the ten-scan set, the \[E-signal\]/no-BSL-2 doctrine, and the public/private guard verified against the running engine) · rev. 2026-06-16 (poll-corrected: §I.6 \[E-signal\], §I.7 WW- public)*
*Chapters I.1–I.7. Read this volume before the technical ones (→ Master Index).*

------------------------------------------------------------------------

## §I.1 · What Sapote–Mamey is

Sapote–Mamey is a pipeline for **natural-product discovery from actinomycete genomes**. It takes the output of
antiSMASH — the standard tool that scans a bacterial genome and marks its **biosynthetic gene clusters (BGCs)**,
the contiguous stretches of DNA that encode the machinery for making secondary metabolites — and turns that raw
output into a disciplined, ranked, claim-safe account of what a strain *could* make and which of its clusters
are worth a closer look at the bench. <span class="tag t-concept">\[concept\]</span>

It exists because antiSMASH output, on its own, is a firehose. A single actinomycete genome routinely carries
twenty to seventy candidate BGCs; a cohort carries thousands. Most are fragments, duplicates, primary
metabolism, or well-trodden chemistry; a few are genuinely interesting. The bottleneck in discovery is not
detection — antiSMASH detects plenty — but **triage**: deciding, defensibly and at scale, which clusters earn
scarce experimental effort, and stating the case for each in language that does not outrun the evidence.

Sapote–Mamey is built around three commitments that recur in every later volume:

1.  **Determinism where it can be deterministic.** Anything that can be computed by a fixed rule from the
    antiSMASH output is computed that way, identically every time — counts, boundaries, scans, scores. (→ §I.2,
    the Mamey layer.)
2.  **Judgment where judgment is unavoidable**, but fenced. Interpreting what a cluster's signals *mean* needs
    reasoning that a fixed rule cannot supply; that reasoning is done by an LLM judgment layer held to an
    explicit contract. (→ §I.2, the Sapote layer; → §I.3.)
3.  **Claims that never exceed evidence.** A genome shows *capacity*; it does not show *product*. Every
    statement the pipeline emits is disciplined to that distinction. (→ §I.3.)

The name is a pair of fruits. **Mamey** is the deterministic extraction engine (a Python program, versioned
independently, e.g. engine 1.9.91). **Sapote** is the judgment layer that reads Mamey's extraction and applies
interpretation under contract. The two are versioned together as a **bundle** (e.g. v9.7.91) but are
conceptually distinct, and keeping them distinct is the single most important idea in the system (→ §I.2). The
target users are microbial-ecology and natural-product researchers; the methods paper targets venues such as
*NAR Genomics & Bioinformatics*.

## §I.2 · The two-layer contract

The architecture is two layers with a hard seam between them. The seam is not an implementation detail; it is
the load-bearing design decision, and most failure modes in genome-mining interpretation are failures to
respect it.

**Mamey — the deterministic layer. <span class="tag t-engine">\[engine\]</span>**
Mamey reads the antiSMASH archive and extracts everything that can be derived by fixed rule: the BGC inventory,
each cluster's product class, its **boundary status** and the **corrected count** (→ §I.5), the ten First-Pass
Scans (→ §IV), evidence channels, and a triage board. Mamey assigns no interpretive scores beyond what its
rules compute. Run the same input twice and you get byte-identical extraction. Mamey is the floor of fact on
which everything else stands; if Mamey is wrong, everything above it is wrong, so Mamey is conservative and
fully tested.

**Sapote — the judgment layer. <span class="tag t-concept">\[concept\]</span>**
Sapote reads Mamey's extraction and does the part that genuinely requires reasoning: weighing competing
signals, writing the per-BGC Mode B analysis (→ §III.2), adjudicating whether a trigger fired on a
class-compatible locus, ranking leads, and producing the reader-facing deliverables. This is LLM work, and LLM
work is not deterministic, so it is fenced by a contract — claim-safety rules, the hallucination-trap audit
(→ §III.6), evidence-conservation checks, and explicit corroboration requirements — that constrain what the
judgment is allowed to assert.

**The contract between them.**
- Mamey states facts; Sapote states interpretations; **neither speaks in the other's voice.** A deterministic
count never carries a judgment, and a judgment never silently rewrites a count.
- **The deterministic package is honest about its own incompleteness.** A run that has completed extraction but
not the judgment layer says so, loudly — the brief carries an *"extraction complete · judgment pending"*
banner — so a reader never mistakes a half-analysis for a finished one. <span class="tag t-engine">\[engine\]</span>
- Where the two are produced by different tools or chats, they are reconciled, not concatenated: divergent
schemas are normalized first, evidence is conserved, and merged outputs are leak-audited and key-checked
(→ §VII). <span class="tag t-concept">\[concept\]</span>

The practical payoff: the parts that must be reproducible *are* reproducible, and the parts that require
judgment are visibly marked as judgment and constrained so the judgment cannot quietly manufacture certainty.

## §I.3 · The claim-safety doctrine

Claim-safety is the ethic of the whole system. A bacterial genome is evidence of **biosynthetic capacity** — of
what enzymes a strain could assemble — and nothing more. It is not evidence that the strain expresses that
pathway, makes the compound, makes it in culture, or makes enough to matter. The doctrine forces every emitted
claim back to what the genome can actually support. Three rules are load-bearing.

**1. Capacity, never production. <span class="tag t-concept">\[concept\]</span>**
The pipeline says "biosynthetic capacity consistent with class X," never "produces compound Y." Class-level,
capacity-level statements are permitted; compound-identity and production statements are not. This is not
hedging for its own sake — it is the literal truth of what a genome shows. A cluster can be present and silent,
truncated, mis-assembled, or mis-annotated; capacity language is the only honest register.

**2. KCB is similarity, not identity. <span class="tag t-concept">\[concept\]</span>**
KnownClusterBlast (KCB, → §IV.2) reports how similar a region is to a characterized reference cluster. A high
KCB hit is a **similarity signal**, not proof that the strain makes the reference's product, and KCB score is
not a measure of novelty. The pipeline treats every KCB hit as "consistent with the class of," never as an
identification. A named anchor that lacks its own class diagnostic is flagged as a **mis-anchor** and its
anchor-derived credit is suppressed (→ §V).

**3. Bioactivity is extract-level, and absence is not negative. <span class="tag t-concept">\[concept/science\]</span>**
Recorded bioassay activity (the project's default frame is MRSA + *Candida* inhibition at the crude-extract
level) belongs to the *extract*, not to any single BGC, and may not be pinned to a cluster without
fractionation data. Critically, **the absence of recorded activity means nothing** — bioassay data are
non-standardized and incomplete, so a strain is never called "antibacterial-negative" or "antifungal-negative."
When two strains are contrasted, the contrast is drawn by **biosynthetic mechanism** (e.g. the presence or
absence of a dedicated HSAF/PTM cluster), never by phenotype.

These rules are not advisory. They are enforced in the engine (the rationale renderer, the scoring guards, the
audit gates) and required of the judgment layer, and they are the reason the system can be trusted to scale: a
claim that cannot exceed the evidence cannot mislead at volume.

## §I.4 · The scientific domain

Sapote–Mamey is pointed at a specific corner of biology, and its design assumptions come from that corner.

**Actinomycetes** are a phylum of Gram-positive, often filamentous, high-GC bacteria — *Streptomyces*,
*Nocardia*, *Micromonospora*, *Pseudonocardia*, *Salinispora*, and relatives. They are the richest known source
of microbial natural products: a large fraction of clinically used antibiotics, antifungals, and other
bioactive small molecules trace to actinomycete biosynthesis. Their genomes are dense with BGCs, which is why
they are the substrate here. <span class="tag t-science">\[science\]</span>

**Biosynthetic gene clusters (BGCs)** are the encoded assembly lines — polyketide synthases (PKS),
non-ribosomal peptide synthetases (NRPS), terpene synthases, RiPP machinery, and many hybrids — that build
secondary metabolites. antiSMASH detects and classes them; Mamey extracts them; Sapote interprets them. The
megasynthase families (PKS/NRPS) are large and modular, which makes them both the most interesting and the most
fragmentation-prone to assemble (→ §I.5, → §IV on the FLBR census). <span class="tag t-science">\[science\]</span>

**The ecological lens.** The project's center of gravity is **bee and other Hymenoptera microbial ecology** —
the actinomycete symbionts of pollinators and the **defensive symbiosis** chemistry behind those relationships,
in which a host insect carries bacteria whose small molecules defend the host or its food stores. Pollinator-
and wasp-associated strains are compared against **bryophyte-associated** and **attine-ant-associated** strains
for ecological context. Two reference relationships recur as touchstones: the fungus-cultivating **Attini**,
which carry vertically transmitted actinomycete mutualists, and **Philanthus** wasps with their *Streptomyces*
symbionts. The working hypothesis of the field is that distinct ecological niches select for distinct
biosynthetic repertoires — a hypothesis the pipeline is built to interrogate carefully, never to assume. <span class="tag t-science">\[science\]</span>

**The biomedical lens.** The ecological framing is not the only reason this work matters; insect-associated
actinomycete chemistry sits at the **confluence** of antibiotic/antifungal discovery and microbial ecology, and
the two lenses reinforce each other. The clearest example is **selvamicin**, an atypical antifungal polyene
characterized from an **attine-ant-associated *Pseudonocardia*** symbiont — a compound that arose directly from
the defensive-symbiosis system and stands as a meaningful contribution to antifungal and candidiasis research.
That pattern — an ecologically discovered symbiont yielding a biomedically relevant scaffold — is the reason the
pipeline holds capacity claims to a high standard (→ §I.3) while still surfacing antifungal leads (the AF axis
and DAPR, → §V) for follow-up: the clinical payoff of getting the chemistry right is real. The microbial ecology
also carries **applied weight beyond the clinic** — for agriculture and for bee culture and health, spanning both
managed/beekeeper-associated and native-bee systems, where the microbial communities that defend pollinators and
their stores bear on pollinator health and, through it, on food systems. <span class="tag t-science">\[science\]</span>

**Three habitats, three defensive-symbiosis logics.** The pipeline's comparative core is a contrast between three
host systems, each a different way of using bacterial chemistry for defense, and reading them side by side is what
gives an isolate's repertoire ecological meaning. <span class="tag t-cand">\[science: candidate — Pass-2 pending\]</span>

1.  **Bee / Hymenoptera (the focal system).** Social and solitary bees and their relatives carry actinomycete associates whose small molecules are hypothesised to defend the host, its brood, or its stored food (pollen provisions, larval food) against fungal and bacterial spoilage. The defensive logic here is *provision protection* as much as direct host protection: a bee's stored food is a rich, static substrate under constant microbial pressure, so antimicrobial capacity in an associate is ecologically coherent. This is the system the pipeline is pointed at, and the one whose strains are treated as the unpublished discovery cohort.
2.  **Attine ants (the characterised reference).** Fungus-cultivating ants maintain a vertically transmitted *Pseudonocardia* mutualist whose antifungals defend the colony's fungal cultivar against the specialised parasite *Escovopsis*. This is the best-understood insect defensive symbiosis, and it is the reference precisely because its chemistry is *known*: selvamicin (an atypical antifungal polyene) and other antifungals from attine *Pseudonocardia* are the proof-of-concept that an ecologically defined symbiont yields a real antifungal scaffold. An attine comparison strain therefore functions as a calibration point: a repertoire whose defensive output has a named, validated endpoint.
3.  **Bryophytes / moss (the environmental contrast).** Moss-associated actinomycetes are not a brood-defense symbiosis at all; they are an environmental association in a damp, competitive, surface niche. They enter the comparison as the *non-insect* control: a strain set under different selective pressure (surface competition and desiccation rather than provision protection), so a biosynthetic feature shared across bee, attine, and bryophyte strains is more likely habitat-non-specific (a candidate standing exclusion, → §I.6) than a feature concentrated in one system.

The worked contrast is what makes a single isolate legible. A halogenated-RiPP capacity in a bee associate reads
one way against an attine reference that carries the same capacity (likely a shared actinomycete baseline) and
another way against a bryophyte set that lacks it (a candidate bee-enriched feature worth following). The pipeline
never asserts the enrichment from one strain: it surfaces the contrast and holds the claim at *candidate* until a
cohort supports it (→ §VI.8, the cross-comparative synthesis). The discipline mirrors §I.3: a habitat difference is
a hypothesis the comparison *generates*, not a conclusion it assumes, and the two genuine standing exclusions that
came out of this exact reasoning (hglE-KS-PREV-001 and NAPAA, both confirmed habitat-non-specific across genera and
habitats) are the cautionary evidence that an exciting cross-habitat signal is often a baseline, not a discovery.

This domain framing explains several design choices downstream: the bioactivity default (→ §I.3), the
habitat-comparison machinery (→ §VI on cross-comparative synthesis), and the standing exclusions for domains
that have proven *non*-discriminating across habitats (→ §I.6).

**Defensive-symbiosis reference facts.** Claim-safe and habitat-aware; the strength of evidence differs sharply
by system. <span class="tag t-cand">\[science: candidate — Pass-2 pending\]</span>

| Fact | Status |
|----|----|
| Fungus-cultivating Attini carry vertically transmitted actinomycete (*Pseudonocardia*) mutualists | Established |
| *Philanthus* (beewolf) wasps carry *Streptomyces* symbionts that protect the brood | Established |
| Selvamicin (antifungal polyene) arose from an attine-associated *Pseudonocardia* | Established (named compound; capacity-not-production still applies to genome reads) |
| A defined defensive mutualism in honeybees / other bees | **Hedged** — pollen/hive Actinobacteria are documented, but a settled defensive mutualism is far less established than in Attini/beewolves; bee claims are stated cautiously |
| Distinct niches select distinct biosynthetic repertoires | **Working hypothesis** — interrogated, never assumed |

**Three worked examples (real v9.7.33 runs — a habitat contrast across the project's three reference niches).**
<span class="tag t-engine">\[engine: real runs; strain identifiers in the PRIVATE worked-examples key\]</span>

| Worked example | Source | Raw BGCs | Interior / Edge / Full-contig | Corrected | Interior % → tier | Notable |
|----|----|----|----|----|----|----|
| Bumblebee *Streptomyces* | Bee | 68 | 17 / 31 / 20 | 37.5 | 25.0% → POOR | RiPP lanthipeptide leads (novelty 44.4 / 42.8 / 27.8) |
| Attine *Pseudonocardia* | Attine fungal garden | 50 | 12 / 22 / 16 | 27.0 | 24.0% → POOR | 49 Inventory / 1 Medium; CCTT T43-HAL ×5 (Promiscuous), T43-THA ×1; top scorers are Saccharides (downgraded) |
| Bryophyte *Pseudonocardia* | Bryophyte (moss) | 41 | 22 / 12 / 7 | 29.8 | 53.7% → MODERATE | 39 Inventory / 2 Medium; best-assembled of the three; top scorers again Saccharides (downgraded) |

Two lessons are meant to land. First, **niche differences must be read through assembly quality, not around it**:
the bee and attine strains both tier POOR for the same reason (fragmented draft assembly), while the bryophyte
strain is better assembled (53.7% Interior → MODERATE), so a naive raw-count comparison across the three would
confound habitat with assembly. Second, **the same claim-safe machinery governs all three**: the corrected count
discounts fragmentation identically, and on every strain the standing-rule guard keeps Saccharide regions out of
the lead rank even when they top the raw score (→ §I.6), while a Promiscuous T43-HAL count is held to extra
corroboration (→ §IV.2). The habitat comparison is only trustworthy once all strains are read through that shared
discipline (→ §VI on cross-comparative synthesis).

## §I.5 · The unit of work and the corrected count

**The unit of work is one strain. <span class="tag t-engine">\[engine\]</span>**
A run takes one strain's antiSMASH archive and produces one sealed package. Cohorts are built by running
strains individually and consolidating the per-strain packages, never by analyzing a merged blob; this keeps
provenance per-strain and keeps cohort-local computations honest (→ §VII on why cohort-local layers are
recomputed after a merge, not concatenated).

**The corrected count exists because raw BGC counts lie. <span class="tag t-engine">\[engine/concept\]</span>**
A raw antiSMASH count treats every detected region as a whole cluster. But assembly is imperfect, and many
"clusters" are fragments — a cluster running off the end of a contig is probably truncated, and a region
spanning an entire short contig is very likely a piece of something larger. Counting these at full weight
inflates a strain's apparent biosynthetic richness. The pipeline corrects by weighting each region by its
**boundary status**:

> **corrected count = Interior × 1 + Edge × ½ + Full-contig × ¼**

- **Interior** — bounded on both sides within its contig; counted whole.
- **Edge** — runs off one end; likely truncated; half-weighted.
- **Full-contig** — spans the contig end to end, the strongest fragment signature; quarter-weighted.

This is a **calibrated heuristic, not a validated metric** — the direction and the weights are reasonable and
honest about fragmentation, but they have not been independently validated, and the encyclopedia states that
plainly wherever the count appears. <span class="tag t-concept">\[concept\]</span>

> **Worked example (real v9.7.33 run — a bumblebee-associated *Streptomyces* sp., POOR assembly).** Genome
> 9.09 Mbp across 2,294 contigs; **68 raw BGCs** partition into **17 Interior / 31 Edge / 20 Full-contig**.
> The corrected count is `17 × 1 + 31 × ½ + 20 × ¼ = 17 + 15.5 + 5 =`**`37.5`** — the 68 raw regions collapse by
> ~45% once fragmentation is discounted. Interior fraction `17 / 68 =`**`25.0%`** → assembly tier **POOR**
> (20–45% band). The example shows why the raw count alone misleads: a third of the regions are Edge fragments
> and another third span their whole contig, so "68 clusters" overstates what the assembly actually resolves.
> <span class="tag t-engine">\[engine: real run; strain identifier in the PRIVATE worked-examples key\]</span>
>
> **Proposed refinement (out of current scope).** The flat **¼** weight on full-contig regions is a placeholder.
> A length-aware successor would weight the full-contig contribution by *information recovered* rather than by a
> fixed fraction: take the combined length of a strain's full-contig fragments and divide by the average BGC
> length of a fully-assembled strain of that species (≈ **30 kb** as a fair first estimate), so a long
> full-contig fragment that plausibly represents most of a real cluster counts for more than a short one. The
> estimate can later be sharpened to a **genus-level average BGC length**, and possibly refined by excluding
> certain BGC types from the average. This is recorded as a future direction; the weights above remain the
> shipped definition until then. <span class="tag t-concept">\[concept\]</span>

**Assembly tiers** summarize the same concern at the genome level: a strain is graded **GOOD / MODERATE / POOR
/ VERY_POOR** by the fraction of its BGCs that are Interior. A VERY_POOR assembly is not a verdict on the
strain's biology — it is a warning that the fragmentation is severe enough that counts and boundaries should be
read with caution, and the deliverables carry that caveat forward rather than burying it. <span class="tag t-engine">\[engine\]</span>

## §I.6 · Standing downgrades and permanent exclusions

Some signals recur so widely, or have proven so non-discriminating, that the project has fixed standing rules
about them. These are **permanent, project-level decisions** — not per-run judgments — and they exist to stop
known false leads from re-surfacing every cohort. A standing downgrade removes a region from comparative and
lead-ranking claims; it does **not** necessarily erase a separate structural-novelty observation. <span class="tag t-concept">\[concept\]</span>

- **Pure saccharide** regions are downgraded — sugar biosynthesis is ubiquitous and not, on its own, a
  discovery lead.
- **NAPAA** (an ε-poly-L-lysine-class signal) is excluded from all comparative and ecological claims. An older
  Nosema/glucocerebrosidase antifungal hypothesis attached to it has been **retired** and is not repeated.
- **hglE-KS-PREV-001** (the prevalent hglE-type glycolipid ketosynthase domain, associated with a
  hexacosalactone-class signal) is **habitat-non-specific** — observed broadly across many strains, genera, and
  habitats — so it carries **no** habitat-specific or ecological claim. Its structural novelty observation (a
  zero-KCB signal) stands on its own; only the ecological inference is barred.
- **Primary-metabolism calls are dropped** — housekeeping and pigment cores are not bioactivity leads, and
  scoring suppresses their AB/AF credit (→ §V).
- An **enediyne** KCB signal is handled by a claim-safety reframe (the v9.7.28 R-B change): the spurious-anchor
  case is downgraded, and a genuine enediyne carries a neutral **`[E-signal]` claim-safety note** routing it to
  cytotoxicity/self-protection review — <span class="tag t-engine">\[engine\]</span>. The engine emits **no per-cluster BSL-2 lab-safety flag**:
  a selective flag would falsely imply the *unflagged* clusters are safe, and chemical handling is governed by
  standard lab SOPs, not a per-cluster gate — <span class="tag t-concept">\[concept\]</span>. (Verified at v9.7.91: a grep of `mamey/`
  for `bsl`/`biosafety` returns only no-flag affirmations — `rules.py` and `scoring.py` state
  explicitly that no lab-safety/BSL-2 warning is emitted; the engine has no selective biosafety flag. The
  `[E-signal]` / non-selective-handling reframe is settled doctrine and per-BGC BSL-2 flagging is retired. A
  few `docs/` surfaces still describe the doctrine in BSL-2 terms, but none emit a selective flag.)

The discipline behind these: a standing rule is the institutional memory of a lesson already learned, encoded
so it does not have to be relearned per cohort. The full registry of standing rules lives in Volume VIII; the
scoring-side enforcement lives in Volume V.

## §I.7 · Public/private and the embargo

The project works with two kinds of strain, and the boundary between them is a **hard guard**, not a preference.

- **Unpublished strains** — identifiers in the lab's internal series (the **AS-####, AJS-####, PENDING-**
  *families) — are under embargo pending the PI's clearance. They are* *PRIVATE.* *<span class="tag t-engine">\[engine\]</span>*\* (the hard-guarded
  patterns in `dedup_and_guard.py`).
- **Public strains** — named reference genomes, NCBI accessions, and the **SID-public** series — are **PUBLIC**.
  Note that a public SID strain's GenBank WGS contigs carry a **WW-** accession prefix (SID-XXX→WWKG…, SID-XXX→WWHM…);
  **WW- is therefore a *public* contig prefix, not an embargo class** — earlier drafts listed it as PRIVATE, which
  would have flagged every public SID strain's own contig IDs. The engine has no WW- guard pattern, and correctly so.

The rules that follow are absolute and recur throughout Volume VII:

1.  **An unpublished identifier never enters a public-facing artifact.** Any dataset, cut, report, figure CSV,
    or handoff that contains even one unpublished strain is PRIVATE in its entirety.
2.  **A public cut is made by filtering, then auditing.** To produce something shareable from mixed material,
    filter to PUBLIC strains first, then re-scan every file — manifests, reports, figure data, package names —
    to confirm no embargoed identifier survived. The audit is run, not assumed.
3.  **The embargo is not operator-overridable.** The engine accepts an explicit release directive, and it will
    honor a PUBLIC declaration on a genuinely public genome shape — but it **refuses** to widen disclosure on an
    AS/AJS/PENDING identifier. An operator can open a public genome; no one can open an embargoed one by flag.
    <span class="tag t-engine">\[engine\]</span>
4.  **When in doubt, PRIVATE.** Ambiguity resolves toward the safe reading, and the fork is surfaced rather than
    silently decided.

This is why the build system carries four release tiers and a per-tier leak audit (→ §VII.3–§VII.4), and why
even this encyclopedia admits unpublished strains only as anonymized examples (→ Master Index, conventions). The
cost of a leak is a researcher's unpublished work; the guard is sized to that cost.

------------------------------------------------------------------------

*End of Volume I. Next: Volume II — The Mamey Engine (ingest, the ten scans, evidence channels, boundary and
assembly tiers, the FLBR census, the package). Each subsequent volume is grounded in the running engine of its
edition before it ships.*

</div>

<div id="vol2" class="section vol">
