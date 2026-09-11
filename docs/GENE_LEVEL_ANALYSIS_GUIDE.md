# Gene-level BiG-SCAPE exploration — workflow guide (v9.7.294)

How to take a new batch of strains from antiSMASH GBKs through gene-level assembly-line analysis,
predicted chemistry, sequence-level novelty, and into Mode B cards — **following the floors strictly**.
Everything here is capacity-level: biosynthetic potential, never production or bioactivity.

## The one rule that governs everything: count per GENE, not per region
antiSMASH reports *regions*. On well-assembled contigs it MERGES neighbouring clusters into one region,
so a region-level domain sum adds modules across several assembly lines (inflates); on fragmented
contigs it splits one cluster across regions (deflates). Three specific traps, all handled by the tools:
1. `/aSDomain="Condensation"` appears in real `nrpspksdomains` features AND in redundant `PFAM_domain`
   (clusterhmmer) duplicates AND in detection-rule text. Count **only** `domain_id="nrpspksdomains_..."`.
2. Condensation domains are subtyped (`_LCL/_DCL/_Dual/_Starter`, `Heterocyclization`) — sum the family.
3. PKS carrier domains are `PKS_PP` as well as `ACP`/`PP-binding` — accept all three for completeness.
(These caused three real over/under-counts in development. The tools bake in the fixes.)

## Workflow for a new strain batch
1. **Scan into BiG-SCAPE** (see BiG-SCAPE_RUN_GUIDE): chunk CDS-dense genomes (Nocardia) to **1 strain
   per chunk** — 2 dense Nocardia together (~5.7k CDS) exceed the ~5k OOM ceiling on a 3.9 GB single core.
2. **Gene catalog:** `python gene_assembly_line.py --dir <region_gbks>/ --out gene_catalog.tsv`
   -> every assembly-line gene with reliable per-gene module counts, completeness, kind.
3. **Predicted chemistry:**
   - NRPS: `python nrps_substrate.py REGION.gbk` -> predicted backbone + siderophore/glycopeptide/
     lipopeptide signature (glyco/lipo auto-confirmed against P450/halogenase/GT or cyclizing TE).
   - PKS: `python pks_product_class.py REGION.gbk` -> polyene / aromatic / reduced-macrolide call from
     per-module reductive loops.
4. **MIBiG protein-homology context (BLASTp — run when the core is free, not during a scan):**
   `bigscape_blastp_novelty.py build --mibig-dir mibig_gbks/ --mibig-release RELEASE_ID --db mibig_db`
   `bigscape_blastp_novelty.py query --targets core_proteins.faa --db mibig_db --out mibig_protein_context.tsv`
   `bigscape_blastp_novelty.py modeb --results mibig_protein_context.tsv --out modeb_mibig_protein_context.md`
   BLAST `pident` is **percent amino-acid identity**. Interpret it with query and subject
   coverage, E-value, bitscore, exact query/subject sequence hashes, and the declared MIBiG
   database build. The build emits a hash-bound source-GBK manifest and versioned receipt
   with portable relative locators rather than personal absolute source paths;
   query refuses missing or drifted metadata, receipt, or source-manifest inputs. Both query
   and subject coverage must pass the declared thresholds before a whole-protein homolog state
   is emitted. A low-identity match is a sequence-divergence prior within that reference
   set, not proof of a novel scaffold. A high-identity match is not a self-hit unless exact
   source/strain provenance establishes that relationship. The historical filename is retained
   for compatibility; this tool does not run BiG-SCAPE and its output must not be described as a
   BiG-SCAPE family result.
5. **Mode B enrichment:** the preferred MIBiG route requires the result TSV and canonical
   protein roster plus their expected SHA-256 values and the complete identity in the order
   `strain / full node-or-contig / region / BGC alias`. The enrichment command refuses an
   unbound TSV, a query absent from the roster, hash/length drift, an unsupported evidence
   state, or a missing/drifted database receipt. The legacy `--blastp-pct` summary remains
   explicitly unbound and is insufficient for a finished card.

## Mode B routing for the MIBiG protein-context stream

The TSV and generated Markdown are evidence inputs, not standalone conclusions:

- **Admission:** bind the exact result TSV hash, exact roster hash, complete locus identity,
  database metadata hash, versioned build-receipt hash, and source-GBK-manifest hash. Display
  escaping never changes the exact source TSV values.

- **§4:** add the best admitted row for every queried gene, including protein SHA-256,
  MIBiG accession/subject, percent identity, query coverage, subject coverage, E-value,
  bitscore, and typed evidence state.
- **§8 and §11:** reconcile the gene-level homologs with KCB/MIBiG cluster-level evidence and
  the multi-gene biosynthetic logic chain. A single homolog cannot assign the product.
- **§15 and §16:** list missing queries, low-coverage hits, database/version gaps, and the
  next confirmatory comparison.
- **§24:** use distributed, coverage-qualified divergence only as a bounded novelty prior.
  Do not convert a fixed identity cutoff into chemical novelty.
- **§28:** bind the query FASTA, protein SHA-256, database metadata/build receipt, TSV, and
  command parameters.
- **§39-§41 and §46-§47:** use admitted homologs to select comparator proteins or loci for
  cross-strain identity, phylogeny, type/reference comparison, and host-matched controls.

This stream should normally be run for committed core, maturation/tailoring, export, and
mechanism-specific self-resistance candidates, not only the largest synthase. The card must
still end with the locus-level logic chain: committed core -> assembly/maturation -> tailoring
-> export/self-resistance -> missing or contradictory step.

## The floors (enforced by gene_modeb_enrichment, apply everywhere)
- **15 kb confidence floor:** very likely = best contig >=15 kb AND complete core (NRPS C+A+PCP; PKS
  KS+AT+carrier); likely = >=15 kb; fragment = <15 kb. Nothing <15 kb is "likely".
- **Capacity language:** "capacity consistent with", never "produces"/"makes".
- **BLASTp reports percent identity and percent positives; both are similarity evidence, not
  biological identity.** KCB is a separate cluster-level comparison. Never merge the channels.
- **Cite each BGC by `strain / full node-or-contig / region / BGC alias`.** The full
  four-part identity is primary; module counts remain per gene.
- **NAPAA excluded** from comparative claims. **Over-broad anchors** (platensimycin) flagged low-confidence.
- **No em-dashes in card stamps.**

## Doing Mode B in the same deliverable
The gene-level section is designed to slot into the existing Mode B card structure (it is one block,
not a parallel document). Author the strain's Mode B cards as usual, and for each modular BGC insert the
`gene_modeb_enrichment` output as the assembly-line subsection of the relevant card. Because the tool
enforces the floors and capacity language, the gene layer stays consistent with the rest of the card and
with the strict rules. Keep all four identity components in every filesystem-safe card filename.

## Findings this workflow already produced (51-strain cohort)
*(v9.7.372: the specific per-strain findings previously listed here are unpublished cohort results
and are withheld from the public code tier. A worked example regenerated from a public type strain
replaces them in a following cut — see the .372 disclosure-audit card. The workflow's capacity to
produce class-level novelty reads is unchanged.)*
