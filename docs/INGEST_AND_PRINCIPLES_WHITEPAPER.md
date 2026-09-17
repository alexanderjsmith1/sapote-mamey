# From antiSMASH evidence to a durable BGC interpretation

Sapote–Mamey helps you move from an antiSMASH result to a reviewable account of what a biosynthetic gene cluster (BGC) might do. Mamey extracts and records source-derived facts. Sapote guides the interpretation of those facts in a Mode B card. The two steps answer different questions: **what is present in the input**, and **what the combined evidence supports**. A saved card becomes part of the project record only after its locus identity and structure are checked during ingest.

This paper explains that division of work and the claims it permits. For commands in run order, use the [maintained walkthrough](MASTER_WALKTHROUGH.md). For current card requirements, use the template emitted by your installed bundle and the [Mode B authoring guide](MODEB_FULL50_CONTRACT_USAGE.md).

## A gene can matter even when the region is incomplete

A short contig may cut through a pathway. That limits what you can say about the finished molecule, but it does not make every gene on the contig uninformative. A class-defining enzyme, a coherent group of tailoring genes, or a characteristic biosynthetic domain can make a fragment worth investigating. Conversely, a complete-looking region built mostly from common transporters and regulators may offer little support for a specific product assignment.

Keep two judgments separate:

| Question | Evidence that can help | What it does not prove |
|---|---|---|
| Is this locus worth follow-up? | Diagnostic genes or domains, coherent gene neighborhood, unusual tailoring capacity, and plausible links to other contigs | That the pathway is complete or expressed |
| How specific can the product claim be? | Verified core architecture, required tailoring steps, full boundaries, and convergence with a characterized reference | Compound identity from a single similar gene or a product name in a database |

Mamey records the region's boundary and architecture evidence. A reviewer should state which required steps are present, missing from the captured interval, or simply unresolved. An edge-truncated region may still be a strong *lead* while its product identity remains uncertain. Missing evidence is not proof of biological absence, especially when the assembly or annotation does not cover the relevant sequence.

## What each evidence channel contributes

The region GenBank files and Mamey's gene context identify the CDS features, locations, strands, translations, and antiSMASH domain calls available in the submitted result. These are the starting facts for a gene-by-gene pathway explanation. A domain may support a broad function such as condensation or ketosynthase activity; its presence alone rarely identifies a finished compound.

KnownClusterBlast and ClusterBlast compare the region with reference clusters and genomes. They help find similar neighborhoods, but similarity is not product identity. Check how many genes match, which genes they are, whether the biosynthetic core is among them, and whether the compared interval has the required architecture. A strong hit to one conserved enzyme can mislead when the rest of the pathway disagrees.

BLASTp adds protein-level context. Keep **nr, ClusteredNR, and Swiss-Prot** results in separate columns with their own source and date. A hit description is a functional clue, not a replacement for domain and neighborhood reasoning. A query file prepared for BLASTp is not a completed search, and an unbound or failed search is not a verified no-hit. When assemblies or BGC aliases change, bind a result to the exact query protein and its current locus before using it in a card.

Bioactivity belongs to the tested sample or fraction. A strain-level inhibition result can motivate BGC follow-up, but it does not identify which BGC made the active substance. Product and activity claims require the corresponding chemical and experimental linkage.

## Keep the locus identity attached to every claim

Write an individual BGC identity as **strain / full node or contig / antiSMASH region / current BGC alias**. The alias is a convenient local label; it can change between antiSMASH or Mamey runs. Two rows with the same alias may be different loci, and the same locus may receive a new alias. The package manifest and current gene table are the authority for the present run. Preserve the source assembly and input-ZIP hash when comparing an older card, BLASTp result, or reference package.

Mamey packages include a BGC-member protein FASTA and a CDS table. The optional protein-signature export records each protein's hash and full locus identity against its package manifest. It can help decide which assembly a saved BLASTp query came from. It does **not** by itself bind a BLASTp result to that query; retain the result-to-query or RID receipt for that step. See the [online BLASTp protocol](ONLINE_BLASTP_PROTOCOL.md).

## From package to a recorded Mode B card

1. **Inspect and run.** Inspect the antiSMASH ZIP, run Mamey with the intended strain, taxonomy, source, and depth, then validate the package. Check the manifest and gate report rather than inferring success from a ZIP filename or an exit code.
2. **Select the exact locus.** Use the current manifest, gene context, and full node/region identity. If an older card or database uses a different alias, reconcile it before transferring evidence.
3. **Build the pathway account.** Walk the actual CDS features. Separate the biosynthetic core, tailoring, transport, regulation, resistance candidates, and unrelated neighboring genes. Explain one plausible pathway and at least one alternative where the evidence leaves a real ambiguity. Mark boundary and split-pathway holds.
4. **Use the current template.** Emit the Mode B template from this bundle rather than copying a historical section list. Add interpretation and per-gene evidence; a filled template is a starting structure, not a completed scientific review.
5. **Verify, then ingest.** Run `verify-modeb` while drafting. When the card is ready, use `ingest-receipts` with `--card`, a receipt, or the documented auto-detect route. Ingest resolves the card against the package register and applies the structure gate before recording it. An unknown locus or a card with structure errors is held and reported; do not use `--force-structure` to turn an unresolved scientific problem into a recorded card.

For example, a card file can be checked and then submitted with commands shaped like these:

```bash
python mamey_run.py verify-modeb path/to/card.md --package runs/STRAIN/package
python mamey_run.py ingest-receipts --package runs/STRAIN/package --card path/to/card.md
```

Check the actual CLI help for your installed version before running a command. The [user manual](GUIDE/01_User_Manual.md) describes receipt-based ingest and optional master-workbook reconciliation.

## What a passed gate means

A validation or ingest result establishes that the required files and structural fields meet the relevant software contract. It does **not** establish that the pathway interpretation, compound assignment, or proposed experiment is scientifically correct. The author still has to check the genes and evidence, and the project owner still has to accept any manuscript or release claim.

This distinction is why the workflow retains both raw evidence and written judgment. A later reviewer should be able to trace a sentence in a card back to the exact gene, domain, hit, boundary, or experiment that supports it. If new evidence overturns a claim, update the interpretation and preserve a visible correction rather than allowing an older confident sentence to stand beside the new data.

## A useful reporting pattern

For each important locus, lead with the biology: the likely biosynthetic class, the core enzymes, the order of proposed transformations, and the most consequential uncertainty. Then show the per-gene evidence that supports or challenges that account. End with a discriminating next test—for example, checking a missing tailoring enzyme in a related assembly, comparing a core protein with characterized references, or connecting a fraction's mass spectrum to a proposed pathway. Report source and claim limits beside the conclusion, so a reader can see both the opportunity and the reason it remains a hypothesis.

Related current guides: [reading the package](READING_YOUR_RESULTS.md), [gene-level analysis](GENE_LEVEL_ANALYSIS_GUIDE.md), [Mode B authoring](MODEB_FULL50_CONTRACT_USAGE.md), and [troubleshooting](COMMON_MISTAKES.md).
