# Gene-level BiG-SCAPE exploration — workflow guide (v9.7.294)

How to take a new batch of strains from antiSMASH GBKs through gene-level assembly-line analysis,
predicted chemistry, sequence-level novelty, and into Mode B cards — **following the floors strictly**.
Everything here is capacity-level: biosynthetic potential, never production or bioactivity.

## The one rule that governs everything: count per GENE, not per region
antiSMASH reports *regions*. On well-assembled contigs it MERGES neighbouring clusters into one region,
so a region-level domain sum adds modules across several assembly lines (inflates); on fragmented
contigs it splits one cluster across regions (deflates). Three annotation-counting traps handled within the parser's supported ID format:
1. `/aSDomain="Condensation"` appears in real `nrpspksdomains` features AND in redundant `PFAM_domain`
   (clusterhmmer) duplicates AND in detection-rule text. Count **only** `domain_id="nrpspksdomains_..."`.
2. Condensation domains are subtyped (`_LCL/_DCL/_Dual/_Starter`, `Heterocyclization`) — sum the family.
3. PKS carrier domains are `PKS_PP` as well as `ACP`/`PP-binding` — accept all three for completeness.
(These caused three real over/under-counts in development. The tools bake in the fixes.)

## Workflow for a new strain batch
1. **Scan into BiG-SCAPE** (see BiG-SCAPE_RUN_GUIDE): the old one-strain Nocardia chunk recommendation was a measurement on a particular 3.9 GB/single-core environment, not a universal CDS/OOM limit. Bind the intended run configuration and resource receipt; this guide does not authorize a scan.
2. **Gene catalog:** `python gene_assembly_line.py --dir <region_gbks>/ --out gene_catalog.tsv`
   -> every assembly-line gene with reliable per-gene module counts, completeness, kind.
3. **Predicted chemistry:**
   - NRPS: `python nrps_substrate.py REGION.gbk` -> predicted backbone + siderophore/glycopeptide/
     lipopeptide signature (glyco/lipo annotation-based candidates; keyword co-occurrence is not confirmation).
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

## Local legacy helper labels (not a universal acceptance floor)
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
`gene_modeb_enrichment` output as the assembly-line subsection of the relevant card. The generated block remains evidence input: local helper labels and capacity wording do not verify the whole card, its current profile, exact identity or scientific claims. Keep all four identity components in every filesystem-safe card filename.

## Findings this workflow already produced (51-strain cohort)
*(v9.7.372: the specific per-strain findings previously listed here are unpublished cohort results
and are withheld from the public code tier. A worked example regenerated from a public type strain
replaces them in a following cut — see the .372 disclosure-audit card. The workflow's capacity to
produce class-level novelty reads is unchanged.)*

## Current parser, identity and profile limits

Use `tools/` paths from the bundle root; this older guide's bare script names are not root entry points. `gene_assembly_line.py:35–78` regex-matches `nrpspksdomains_ctg<digits>_<digits>_<domain>.<digits>` only, not arbitrary valid gene IDs. The catalog ignores genes without C/KS, counts modules as `max(C,KS)` and chooses NRPS on a tie. Its “complete” means presence of a C+A+any accepted carrier or KS+AT+carrier on that gene, not whole-pathway completeness. Empty catalog output can be a schema/ID mismatch rather than biological absence.

Catalog identity comes from filenames: strain is the first underscore-delimited token, node matching drops a NODE coverage suffix, and no BGC alias is emitted. Output TSV is directly overwritten and has no input/code/output receipt (`:62–107`). Bind the actual GBK hash and a verified four-part locus map separately; do not adopt truncated `node_region` as the full locus identity.

`gene_modeb_enrichment.py:54–65,209–228` gets “contig length” from a `length_<digits>` token in the display identity/filename, not the GBK sequence. The 15 kb label is a local heuristic using the **largest-module gene's** core flag; it is not measured confidence, boundary completeness, a universal genome/locus floor or current50 approval. Missing length defaults to zero/fragment. `--complete-identity` is optional for legacy unbound paths. A no-assembly-line branch returns before validating the MIBiG stream. Require exact identity and data binding before treating any emitted block as admitted evidence.

NRPS substrate consensus is concatenated across all matched genes in the region and corroborated by whole-file annotation keywords; this can combine adjacent candidates. PKS class labels are simple domain-order heuristics, including literal activity-like wording in the classifier. Neither defines a verified scaffold, activity or precise product. Enrichment only prints the first PKS gene's class, not all PKS genes (`nrps_substrate.py:35–69`; `pks_product_class.py:33–65`; `gene_modeb_enrichment.py:229–243`). “Auto-confirmed” in the older recipe is corrected above.

The protein-context hash/roster path described earlier remains the preferred bound channel. It does not repair catalog identity truncation or validate the whole report. The numbered section suggestions are legacy full-card mapping; bind the actual current profile and verifier before insertion. Finished current50 cards require the applicable [current50 contract](MODEB_CURRENT50_V2_CONTRACT.md), not the legacy floors or a successful helper stdout result. The generated NAPAA/anchor warning is prose, not a general filter over every comparative output. Record biological/search/model execution and card adoption as separate evidence states.

## Saved RiPP views are separate readers

For precursor/core motif rows, start with [saved RiPP evidence and source mapping](ANTISMASH_INPUTS_CONSUMED.md#saved-ripp-motif-evidence). The normalized motif CSV/workbook sheet and `gene_data.json` → `ripp` are different projections. The latter retains strain/contig/family/locus/motif-index/core fields from saved evidence; it is not the normalized table's full BGC mapping or raw-detail export. Reconcile the complete four-part locus and source motif before reuse. Empty `gene_data.ripp` is not an independently validated RiPP-negative result.

`mamey.deep_data.build_deep_data_files` is a package-authoring helper, not a read-only repair command. It selects saved snapshot/evidence JSON (with wildcard fallback), silently treats missing/unreadable JSON as empty input, and directly replaces `deep_data.json` then `gene_data.json` through separate temporary files. Calling it can replace existing richer views with empties and can leave only one refreshed file after failure. Read accepted views in place; any separately authorized rebuild requires a preserved working copy, explicit input/hash bindings and inspection of both final files. Returned counts do not establish source completeness or scientific acceptance.

## Package gene records and completeness

For existing sealed results, read [current gene-context export scope](reference/06_CURRENT_SOURCE_SCOPE.md#plumbing-part-4-gene-exports-and-package-integrity) before reusing the JSONL, CDS/domain tables or protein FASTA. These exports are BGC-scoped; header CDS observations and summed per-BGC rows have different denominators. Available protein translations are retained, not a guaranteed complete proteome. The loader can return a partial prefix after warning, and four sequentially published outputs can be incomplete after a failure.

Before a gene-level claim, bind the expected file set, producer status, source hashes and complete strain / full node-or-contig / region / BGC alias. Check same-tag collisions across contigs and overlapping-region membership: some joins use locus_tag alone and one BGC assignment. An empty or partial exported view is not biological absence. Preserve failed attempts and reconcile identity or completeness before scaling a downstream analysis.
