# BLASTp → BGC-novelty workflow (four unmixed channels)

*Post-seal analysis doctrine. Non-scoring, advisory: nothing here changes the Tier-1 engine, a package,
or a gate decision. It formalizes how the four BLASTp channels are run, kept separate, and combined into a
**novelty prior** that feeds the phylogeny overlay (`PHYLOGENETICS_WORKFLOW.md`) and Mode B evidence
(`MODEB_EVIDENCE_ESCALATION_WORKFLOW.md`).*

## Claim ceiling (read first)
Everything below produces **class-level capacity hypotheses**, never product/structure/activity claims.
- **similarity ≠ identity** — a BLASTp %id is homology, not the same molecule.
- **a per-gene reference hit ≠ product identity** — a few genes resembling a characterized cluster is a
  *class-level anchor*, not that compound.
- **high nr %id ≠ known/characterized** — nr is dominated by taxonomy genomes never assayed for natural
  products; closeness in nr means a close *sequence* exists, not that the product is known.
- **nr distance = a novelty prior, not activity** — divergence flags "worth looking at," nothing more.
- Judgment is deferred to the Sapote tiers. This layer ranks where to look; it does not conclude.

## Where this sits in the program
```
seal package ──▶ mamey_pipeline (validate + explain + figures + REPORT)
                        │
                        ├─▶ comparator_discovery ──▶ (download) ──▶ ANI / genome tree   [PHYLOGENETICS_WORKFLOW]
                        │
                        └─▶ FOUR-CHANNEL BLASTp ──▶ anchor × nr-distance rank ──┐
                                                                                 ├─▶ tree × BGC overlay
                                                                                 └─▶ Mode B admission (U=0)
```

## The four channels — each answers ONE question. NEVER mix them.
Every channel keeps its **own store, own output folder, own `subject_db` tag**, and reports
`pct_identity` and `pct_positives` as **separate columns** (never averaged or conflated).

| Channel | DB / locus | Runs | The question it answers |
|---|---|---|---|
| **nr** | NCBI `nr` (remote) | paced RID crawl | **Taxonomic novelty prior** — how far is each gene from the nearest sequence *deposited anywhere*? Low %id to distant/uncultured taxa = novel. |
| **MIBiG / ClusterBlast** | antiSMASH KnownClusterBlast (local, in the package) | at parse time | **Anchor capacity** — does the locus resemble a *characterized reference FAMILY* by real multi-gene support? Graded, not binary. |
| **SwissProt / UniProt** | local curated BLAST DB | local, no rate limit | **Curated per-gene sanity / function hypothesis** — a reviewed, named homolog per gene. Sparse for actinomycete BGC genes; a corroborating channel, not a primary one. |
| **ClusteredNR** | NCBI `nr_cluster_seq` (remote) | paced RID crawl (own ledger) | **Deep representative channel** — clustered nr surfaces a representative per cluster; complements nr where nr is saturated or a gene is promiscuous. |

**Unmixed rule (hard):** a hit from one channel is never merged into, averaged with, or relabelled as another.
The stores stay physically separate so a later reader can always tell which DB produced a number.

## Grading the MIBiG/ClusterBlast anchor (capacity, not identity)
A per-gene hit is graded into a **family anchor** by *real support*, never by a single best gene:
- **STRONG** — ≥4 genes hit one reference family, covering ≥25% of the BGC's true gene count, at ≥55% median id.
- **PARTIAL** — ≥2 anchor genes but below the STRONG bar.
- **promiscuous-only** — the only hits are to genes that recur across many unrelated clusters (scaffold/tailoring);
  gated OUT of "anchored," because a promiscuous gene is capacity noise, not a family call.
- **NO_MIBiG** — no family anchor; the locus is reference-dark by this channel.
Print the honest form `Ng @ X% → <family>`. Never print `= <compound>`.

## Combining: the anchor × nr-distance rank (the lead signal)
The highest-value lead is **real machinery in a novel background**: a STRONG family anchor **and** nr-distant.
- **nr-distance = 100 − nr median %id** across the BGC's genes.
- Rank STRONG-anchored BGCs by ascending nr %id (most divergent first).
- **Denominator honesty (mandatory):** always carry the **number of genes** behind the nr median. A "62% nr"
  computed over 2 genes is not comparable to one over 40; treat nr-distance from <~5 genes as *soft* and say so.
- **Over-merge caveat:** a fused antiSMASH region (COMPOSITE_SEPARABLE) confounds *both* axes — the anchor span
  and the nr median span two biosynthetic units. Flag it and verify the split before trusting either number.

Reads produced: a per-strain **anchored / neighbourhood / divergent+dark** classification, and a cohort
shortlist of anchored BGCs ranked by nr-distance.

**Merging split pathways — by gene evidence, NOT by RG-GMCI score.** When two BGC fragments are RG-GMCI-linked,
collapse them into ONE lead pathway ONLY when it is a **gene-confirmed true split**: `functional_rescue_class
= COMPLEMENTARY_SPLIT` (or a terminus-truncation split) AND both fragments contribute core biosynthesis
(reasonable core fractions). A **HIGH** RG-GMCI score with `functional_rescue_class = ACCESSORY_ONLY` (shared
housekeeping tailoring — MbtH, MFS transporter, AKR, PPTase) and low core fractions (~0.2) is NOT one pathway;
each fragment keeps its own core. Never collapse by score alone (gene-confirmed example: a true biosynthetic
split shares the pathway core, whereas high-score links between fragments carrying only accessory/tailoring
genes are ACCESSORY_ONLY — not one cluster).

## Concurrency discipline for the remote channels (nr + ClusteredNR)
Both remote channels draw on the **same NCBI concurrent-search budget**.
- Submit **serially** (one panel per sleep interval), never a burst.
- Keep **total open RIDs across nr + ClusteredNR ≤ ~10–15**. Holding ~40 open searches trips NCBI's
  concurrent-search limit and earns an **IP-level submit cooldown** (new submits fail even at in-flight 0,
  while status GETs still return 200 — the tell-tale signature).
- When running both channels at once, **split the budget** (e.g. nr in-flight 6 + ClusteredNR in-flight 5),
  don't run each at the full cap.
- Never attach an email or personal identifier to an outbound NCBI/API request.

## Feeds downstream
- **Phylogeny overlay** — the per-strain novelty load (anchored-vs-novel counts, top nr-distances) becomes a
  column painted onto tree tips, keyed to the tree's exact leaf labels. Governed by the sign-off gate in
  `PHYLOGENETICS_WORKFLOW.md` (outgroup sanity, ANI-boundary honesty, comparator provenance, label integrity).
- **Mode B admission** — an anchored lead may only be *promoted* in a Mode B card once its per-gene channel is
  fresh (U = 0 uncovered anchor genes) and the card carries OBSERVATION / INFERENCE / ALTERNATIVE / FALSIFIER
  structure (`modeb_evidence_gate.py`). Novelty from weak/thin evidence is a HOLD, not a lead.

## Exclusions (carry through every channel)
Respect the engine's exclusion accessors (`mamey/exclusions.py`) — never hardcode: contaminated strains are
hard-excluded everywhere; chimeric/void assemblies are excluded from raw per-gene/BLASTp readers (their branch
lengths and per-gene distances are untrustworthy) even where they remain in governed conclusions.
