# BLASTp → BGC-novelty workflow (four unmixed channels)

## Scope and grading contract

This page proposes an advisory interpretation rubric. Reading it changes no files; actual ingestion can write a workbook and package overlays. See [ONLINE_BLASTP_PROTOCOL.md](ONLINE_BLASTP_PROTOCOL.md). Suggested classifications below are not guaranteed output files from one command.

The proposed family-anchor thresholds below are not the parser's tier contract. `mamey/kcb_frontpage.py` labels `STRONG` at similarity ≥40 and matching genes ≥8, `MODERATE` at ≥25/≥5, with separate WEAK/COINCIDENTAL/LARGE_GENERIC/LOW states. Carry the grading source, channel, reference identity and denominator with every label. Ordinary ClusterBlast is a general cluster-similarity channel; it does not certify a characterized reference. Reviewed SwissProt and unreviewed UniProt records likewise need distinct provenance.

Low nr identity is a divergence observation within the searched database and query/result scope. It cannot establish taxonomic or chemical novelty. Remote concurrency numbers below are historical project guidance, not a current service guarantee or a globally enforced RID cap. The per-service rolling daily-submit ledger (`mamey/blast_ledger.py`) is a separate control. Remote runs require the current project authorization.

*Post-seal interpretation guide. It sets how the four BLASTp channels are run, kept separate, and combined into a
**novelty prior** that feeds the phylogeny overlay (`PHYLOGENETICS_WORKFLOW.md`) and Mode B evidence
(`MODEB_EVIDENCE_ESCALATION_WORKFLOW_v97143a.md`)*.

## Claim ceiling (read first)
Everything below produces **class-level capacity hypotheses**, never product/structure/activity claims.
- **similarity ≠ identity** — a BLASTp %id is homology, not the same molecule.
- **a per-gene reference hit ≠ product identity** — a few genes resembling a characterized cluster is a
  *class-level anchor*, not that compound.
- **high nr %id ≠ known/characterized** — nr is dominated by taxonomy genomes never assayed for natural
  products; closeness in nr means a close *sequence* exists, not that the product is known.
- **nr distance = a novelty prior, not activity** — divergence flags "worth looking at," nothing more.
- Judgment is deferred to the Sapote tiers. This layer ranks where to look; it does not conclude.

## Report-wrapper completion boundary

`tools/mamey_pipeline.py` collects package hashes, validation output, explanation
output and optional figure-stage text into a report. The current wrapper returns 1
if validation or explanation fails, a requested figure directory is unavailable,
or the requested figure renderer returns nonzero; otherwise it returns 0 after
report creation. It can still write a report containing failed stages. Optional
literature-helper failure is recorded but does not independently fail the wrapper.
Inspect each stage's output and actual artifacts: a child's zero exit or soft skip
is not independent artifact validation. Comparator and BLASTp steps in the diagram
require separate authorized commands and their own receipts.

The package manifest records files found before validation and explanation. The
wrapper does not check that package bytes remain unchanged through those stages,
or bind engine files and figure inputs in that manifest. Keep the selected source
snapshot and producer identity separate from the current run; verify stability
and retain the stage receipts and output hashes before admitting its results.

Choose a fresh report destination. Report, manifest and diagnostic filenames are
replaced directly on rerun. When `--figures` is supplied, the wrapper invokes
`tools/lab_office_render.py` without its `--out` option: render outputs go to
`<figure-directory>/_rendered`, independently of the wrapper's report directory.
Select an authorized writable figure directory outside immutable evidence and
verify the actual renderer outputs and failures. A previous figure file left by
a failed attempt is not evidence of current completion.

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
| **nr** | NCBI `nr` (remote) | paced RID crawl | **Sequence-divergence prior** — how similar is each gene to its best returned sequence in the selected database/search? This is bounded by database version, query/result coverage and search settings, rather than every deposited sequence or a taxonomic-novelty determination. |
| **MIBiG / KnownClusterBlast** | antiSMASH KnownClusterBlast (local, in the package) | at parse time | **Anchor capacity** — does the locus resemble a *characterized reference FAMILY* by real multi-gene support? Graded, not binary. |
| **Swiss-Prot / other UniProt inputs** | exact selected local database, with release and review-status provenance | local search under its own resource budget | **Per-gene function hypothesis** — keep reviewed Swiss-Prot and unreviewed records distinct. A named subject annotation does not verify the query's function; preserve unavailable and no-hit evidence separately. |
| **ClusteredNR** | NCBI `nr_cluster_seq` (remote) | paced RID crawl (own ledger) | **Deep representative channel** — clustered nr surfaces a representative per cluster; complements nr where nr is saturated or a gene is promiscuous. |

**Unmixed rule (hard):** a hit from one channel is never merged into, averaged with, or relabeled as another.
The stores stay physically separate so a later reader can always tell which DB produced a number.

## Grading the MIBiG/ClusterBlast anchor (capacity, not identity)
A per-gene hit is graded into a **family anchor** by *real support*, never by a single best gene.
- **STRONG** — ≥4 genes hit one reference family, covering ≥25% of the BGC's true gene count, at ≥55% median id.
- **PARTIAL** — ≥2 anchor genes but below the STRONG bar.
- **promiscuous-only** — the only hits are to genes that recur across many unrelated clusters (scaffold/tailoring);
  gated OUT of "anchored," because a promiscuous gene is capacity noise, not a family call.
- **NO_MIBiG** — no family anchor observed in the completed, declared channel scope. Unrun, unavailable, unreadable, partial or unbound evidence remains a separate hold; it cannot supply this negative classification.
Print the honest form `Ng @ X% → <family>`. Never print `= <compound>`.

## Combining: the anchor × nr-distance rank (the lead signal)
The highest-value lead is **real machinery in a novel background**: a STRONG family anchor **and** nr-distant.
- **nr-distance = 100 − nr median %id** across the BGC's genes.
- Rank STRONG-anchored BGCs by ascending nr %id (most divergent first).
- **Denominator honesty (mandatory):** always carry the **number of genes** behind the nr median. A "62% nr"
  computed over 2 genes is not comparable to one over 40; treat nr-distance from <~5 genes as *soft* and say so.
- **Over-merge caveat:** a fused antiSMASH region (COMPOSITE_SEPARABLE) confounds *both* axes — the anchor span
  and the nr median span two biosynthetic units. Flag it and verify the split before trusting either number.

Reads produced: a per-strain **anchored / neighborhood / divergent+dark** classification, and a cohort
shortlist of anchored BGCs ranked by nr-distance.

**Candidate split interpretation — retain both loci and the evidence limits.**
`COMPLEMENTARY_SPLIT` and `TERMINUS_TRUNCATION_SPLIT` are values of
`subject_tiling_verdict`, not `functional_rescue_class`. The latter reports
`COMPLEMENTARY`, `BOTH_CORE`, `ACCESSORY_ONLY`, `AMBIGUOUS` or `UNKNOWN_NO_PROFILE`
from the inspected gene-role profiles. Read these fields separately with the exact
reference/channel support, geometry, contradictory evidence and each endpoint
(`strain / full physical contig / region / BGC alias`).

These computational categories can prioritize a candidate fragmented-locus
interpretation; they do not prove physical adjacency, a complete single pathway,
product identity or exclusion of paralogy. A HIGH score or a complementary category
does not authorize collapsing loci or subtracting a rescue from a biological BGC
count. Keep both source records visible, preserve unresolved/unavailable evidence,
and require independent sequence/assembly and compatible synteny evidence plus
scientific review before adopting a physical join or revised pathway count.
Sources: `mamey/clusterblast_genes.py`, `mamey/rggmci.py`.

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
  fresh for the complete declared current-gene roster (U = 0 under the selected card contract). Its query/result evidence must be independently bound. The card must also carry OBSERVATION / INFERENCE / ALTERNATIVE / FALSIFIER
  structure. `tools/modeb_evidence_gate.py` is a text lint with an optional supplied freshness boolean; it does not verify the gene roster, query hashes or job receipts. Novelty from weak/thin evidence is a HOLD, not a lead.

## Exclusions (carry through every channel)
Respect the engine's exclusion accessors (`mamey/exclusions.py`); never hardcode them. Contaminated strains are
hard-excluded everywhere. Chimeric/void assemblies are excluded from raw per-gene/BLASTp readers (their branch
lengths and per-gene distances are untrustworthy) even where they remain in governed conclusions.
