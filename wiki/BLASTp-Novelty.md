# BLASTp → novelty workflow — four unmixed channels and one honest rank

*Source of truth: `docs/BLASTP_NOVELTY_WORKFLOW.md` (v9.7.401). Post-seal, advisory doctrine:
nothing here changes the Tier-1 engine, a package, or a gate decision. It ranks where to look.*

## The claim ceiling (read before quoting any number)

Everything this workflow produces is a **class-level capacity hypothesis**: similarity ≠ identity;
a per-gene reference hit ≠ product identity; **high nr %id ≠ "known"** (nr is dominated by
taxonomy genomes never assayed for natural products — closeness means a close *sequence* exists,
not that the product is characterized); nr distance is a novelty *prior*, not activity.

## Four channels, four questions — NEVER mixed

| channel | database | the ONE question it answers |
|---|---|---|
| **nr** | NCBI nr (remote, paced RID crawl) | taxonomic novelty prior — how far is each gene from anything deposited anywhere? |
| **MIBiG / ClusterBlast** | antiSMASH KnownClusterBlast (local, in the package) | anchor capacity — does the locus resemble a characterized reference *family* with real multi-gene support? |
| **Swiss-Prot** | local curated BLAST DB | curated per-gene function sanity — a reviewed, named homolog (corroborating channel, sparse for BGC genes) |
| **ClusteredNR** | NCBI nr_cluster_seq (remote, own ledger) | deep representative channel where nr is saturated — **ClusteredNR is NOT nr**; its numbers are never merged with nr's |

Hard rule: each channel keeps its own store, folder, and `subject_db` tag; `pct_identity` and
`pct_positives` stay separate columns; a hit is never relabelled across channels.

## Grading the family anchor (capacity, not identity)

- **STRONG** — ≥4 genes hit one reference family, ≥25% of the BGC's true gene count, ≥55% median id.
- **PARTIAL** — ≥2 anchor genes, below the STRONG bar.
- **promiscuous-only** — hits only to genes recurring across unrelated clusters (scaffold/tailoring):
  gated OUT of "anchored" — promiscuous genes are capacity noise, not a family call.
- **NO_MIBiG** — reference-dark by this channel.

Print the honest form `Ng @ X% → <family>`. Never print `= <compound>`.

## The lead signal: anchor × nr-distance

The highest-value lead is **real machinery in a novel background** — a STRONG anchor that is also
nr-distant (nr-distance = 100 − median nr %id across the BGC's genes; rank STRONG-anchored BGCs
most-divergent-first). Two mandatory honesty rules:

1. **Denominator honesty** — always carry the gene count behind the median; an nr median over <~5
   genes is *soft* and must say so.
2. **Over-merge caveat** — a fused antiSMASH region (COMPOSITE_SEPARABLE) confounds both axes;
   verify the split before trusting either number.

**Merging split fragments is by gene evidence, not by RG-GMCI score:** collapse two RG-GMCI-linked
fragments into one lead only for a gene-confirmed COMPLEMENTARY_SPLIT where both fragments carry
core biosynthesis. A HIGH score whose shared genes are ACCESSORY_ONLY (MbtH, MFS transporter,
PPTase…) is NOT one pathway.

## Remote-channel discipline (nr + ClusteredNR share one NCBI budget)

Submit serially; keep total open RIDs ≤ ~10–15 across both channels (split the budget when running
both); ~40 open searches trips the concurrent-search limit and earns an IP-level submit cooldown
whose signature is *new submits fail while status GETs still return 200*. Never attach an email or
personal identifier to an outbound request.

## Where it feeds

- **Phylogeny overlay** — per-strain novelty load painted onto tree tips (keyed to exact leaf
  labels, under the tree sign-off gate).
- **Mode B admission** — an anchored lead is only promoted once its per-gene channel is fresh
  (U = 0 uncovered anchor genes) and the card carries OBSERVATION / INFERENCE / ALTERNATIVE /
  FALSIFIER structure. Thin evidence is a HOLD, not a lead.
- **Exclusions carry through** — contaminated strains hard-excluded; chimeric/void assemblies
  excluded from per-gene readers (their distances are untrustworthy).
