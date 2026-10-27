# What It Does and Limitations: the limitations list

> Retired in v9.7.458 and kept as a record. Settings and commands may be out of date. Current guide: [What It Does and Limitations](../../../wiki/What-It-Does-and-Limitations.md).

This is the Limitations section of the wiki page What It Does and Limitations, as it stood in v9.7.457. A limitation does not necessarily mean a bug. It may be an unavoidable boundary of genome mining, an architectural debt, a data-coverage gap, or a workflow that is scientifically correct but expensive to operate. The list does not establish the identity, production, activity, novelty, or ecological function of any metabolite. See [Claim-Safety](../../../wiki/Claim-Safety.md) for the language contract.

## Limitations

### A. Complexity and scale

- **The workspace has become operationally sprawling** — many dated roots, cuts, and patch queues
  increase discovery time and invite a writer to select a convenient but stale source.
  *Improvement:* one generated source catalog and one canonical front door; old trees preserved as
  indexed archives, not active-looking peers.
- **The evidence architecture is richer than the user interface** — understanding a locus's state
  can require navigating many folders and TSVs. *Improvement:* a local project dashboard showing
  exact locus, admitted streams, holds, and card/map/widget status.
- **The corpus is too large for uniformly deep manual review.** Thousands of loci cannot all
  receive repeated expert passes. *Improvement:* a two-tier corpus — substantive breadth drafts
  for every locus, deeply audited publication candidates for a prioritized set.
- **Mode B cards can become longer than their evidence warrants** when 48 required sections
  encourage generic prose on a fragmentary locus. *Improvement:* explicit compact sections, with
  padding and unevidenced sentences penalized.
- **Review and promotion remain bottlenecks** — candidate writers can outpace a single expert
  auditor. *Improvement:* risk-stratified audits and an earned quality streak, reserving manual
  deep review for scientific claims and source conflicts.

### B. Source identity and representation hazards

- **Loose, relaxed, canonical, and historical antiSMASH representations can disagree** on
  boundaries, region numbers, or product classes for the same node. *Improvement:* a single
  exact-locus binding service returning admitted equivalences and quarantines before any
  downstream writer runs.
- **BGC aliases remain cognitively seductive** — humans and LLMs naturally reach for short labels
  and may transfer evidence between similarly numbered records even when software treats aliases
  as display-only. *Improvement:* make complete identity mandatory everywhere an alias could
  otherwise stand alone.
- **Locus tags are not globally stable** across reannotation and different antiSMASH exports.
  *Improvement:* protein SHA-256 plus an ordered neighborhood fingerprint as the canonical join
  key everywhere, not only in selected workflows.
- **Exact sequence identity can still be non-unique** between related strains or duplicated
  proteins. *Improvement:* a minimal neighborhood fingerprint extending outward until identity is
  unique, with the resolving scope recorded.
- **Source/header rows can masquerade as biological rows** — a real, already-caught defect class
  where state rows were miscounted as MIBiG or RG-GMCI results despite passing structural gates.
  *Improvement:* schema-aware row typing with an explicit `row_kind` field; no writer infers
  biological counts from raw line counts.

### C. Database coverage and external-computation limits

- **BLASTp completeness is uneven and temporally unstable** — some proteins have full nr,
  ClusteredNR, and Swiss-Prot results while others remain unreturned or CPU-limited.
  *Improvement:* a per-locus completeness ledger keyed by exact protein SHA; no "no hit" wording
  without a terminal exact-query record.
- **NCBI online BLASTp is operationally fragile** (rate limits, DNS failures, RID expiration).
  *Improvement:* prefer local databases where licensing allows, and treat online completion as an
  asynchronous enhancement, not a card-writing prerequisite.
- **ClusteredNR identities are easy to overinterpret** as if interchangeable with full nr or a
  curated biochemical reference. *Improvement:* label every percentage by channel with a short
  database-definition tooltip.
- **A missing Swiss-Prot cell has an unresolved cause until its source state is checked.** Local availability does not establish that the exact query was searched, returned, admitted or imported. Preserve `NOT_RUN`, `UNBOUND`, unavailable and verified no-hit states separately. *Improvement:* inspect the bound local snapshot, query/job receipt and import state for each selected locus before choosing recovery.
- **Comparator corpora are incomplete by construction** — an apparently private family can become
  shared as more type, cohort, or taxonomically close genomes are added. *Improvement:* record
  comparator-corpus version and nearest-reference density beside every prevalence/novelty
  statement.

### D. Biological and assembly limitations

- **Fragmented assemblies inflate apparent BGC counts.** Many short contigs and edge-reaching
  records can inflate the number of antiSMASH regions and split one pathway into several
  candidates. This is an already-observed pattern in this project's own fragmented-assembly cases, not
  only a theoretical risk. *Improvement:* assembly-quality weighting, fragment-family
  consolidation, and an explicit "region count is not pathway count" figure annotation.
- **antiSMASH boundaries are analytical windows, not biological operon boundaries** — relevant
  genes can lie just outside a region while unrelated genes are captured inside it.
  *Improvement:* preserve ordered boundary-context genes and report sensitivity to reasonable
  boundary expansion.
- **Product-class labels can be wrong or overly broad**, as seen in halogenase-versus-reductase
  and saccharide-versus-terpene conflicts. *Improvement:* require gene-level catalytic and
  neighborhood reconciliation before a class label becomes prose authority.
- **The "Other" class can make figures scientifically unhelpful** by hiding distinct chemistries
  in one heterogeneous bin. *Improvement:* replace it with an interpretable hierarchy
  (unknown-core, mixed/hybrid, primary-metabolism-like, fragmentary, unclassified RiPP,
  genuinely miscellaneous).
- **Genomic capacity cannot resolve expression, product, or activity** even with a perfect
  assembly and annotation. *Improvement:* connect prioritized loci to OSMAC, transcript,
  metabolomics, and gene-perturbation plans; never let computational polish obscure this boundary.

### E. Interpretive false-positive risks

- **MIBiG compound names can anchor the reader too strongly**, even with disclaimers, and may
  dominate a weaker gene-level comparison. *Improvement:* lead with matched machinery and
  discordant genes; place compound names after the gene evidence as "reference navigation."
- **BiG-SCAPE families can be mistaken for novelty units** — membership depends on cutoff, class
  binning, and corpus composition. *Improvement:* show membership at several cutoffs; never treat
  singleton status alone as a novelty claim.
- **RG-GMCI can be mistaken for physical pathway completion** — homology-guided linkage cannot
  join contigs. *Improvement:* a separate visual lane for remote hypotheses, two independent
  evidence types required, no inclusion in the canonical denominator without assembly evidence.
- **Generic transporters can be mistaken for producer immunity** — ABC/MFS proteins are common
  and substrate/direction are usually unknown. *Improvement:* require mechanism/class
  concordance, exact co-location, and compound-dependent functional tests before a resistance
  interpretation.
- **Resistance-like folds are not necessarily resistance genes** — beta-lactamase-like, kinase,
  and acetyltransferase folds have many ordinary cellular roles. *Improvement:* name the physical
  gene, homolog coverage, neighborhood, predicted substrate class, and alternative housekeeping
  function.

### F. Software evolution and documentation debt

- **Rapid bundle cuts create version churn** — small engine improvements can tempt unnecessary
  card rewrites while larger legacy gaps remain. *Improvement:* version evidence schemas
  independently and modernize old cards deliberately rather than on every nonmaterial bump.
- **Documentation can lag the executable CLI** — retired modes and renamed flags have appeared in
  user docs. *Improvement:* generate command references from the live parser and execute every
  worked example in clean-bundle tests.
- **The template and its publication gates have diverged at times** — an emitter can produce text
  its own downstream gate rejects, or a gate can miss a substantive defect while accepting
  structure. *Improvement:* test emitter-to-gate round trips; keep structure, evidence, and
  scientific-reasoning audits separate.
- **Optional capability discovery is weak** — users may not know which reports, figures, or
  comparison modules exist. *Improvement:* a generated capability catalog with
  installed/available/unconfigured states.
- **Third-party tool setup and licensing are complex** (antiSMASH, BLAST databases, Pfam,
  BiG-SCAPE, clinker, GToTree, aligners). *Improvement:* ship no unauthorized third-party data;
  provide versioned fetch/install instructions, license links, checksums, and `doctor` checks.

### G. Performance and resource use

- **Deep card authoring is expensive in time and model usage** — true gene reconciliation,
  comparator scans, and 48-section synthesis can take tens of minutes per locus.
  *Improvement:* precompute shared cohort/reference protein comparisons across many loci and
  reserve prose generation for the final bound packet.
- **Rendering can consume disproportionate resources** relative to the underlying text revision.
  *Improvement:* keep nonvisual scientific completion separate; render only review-selected
  batches.
- **Large databases and networks strain portability** — full nr, Pfam, and BiG-SCAPE data can
  reach gigabytes. *Improvement:* define a portable core, an optional local science stack, and
  external evidence roots with content-addressed manifests.
- **Repeated scans can duplicate work** across concurrent lanes. *Improvement:* a central
  exact-locus work-claim ledger and a SHA-keyed cache of completed analyses.
- **LLM breadth behavior can produce skeletons** — some writers fill headings with templates
  rather than evidence. *Improvement:* source-binding headers, named genes in evidence-dependent
  sections, and anti-padding checks before promotion.

### H. Product and publication maturity

- **Passing gates can create false confidence.** Structural and precision gates cannot judge
  every scientific sentence — a card can be machine-clean yet substantively wrong.
  *Improvement:* content-derived invariants alongside independent scientific audits as a separate
  authority layer.
- **Citation coverage is not yet uniform** — some strong biosynthetic explanations lack immediate
  literature context. *Improvement:* a domain-to-citation registry with gene-specific primary
  references, without turning every card into a review article.
- **Phylogenomics is not yet fully integrated with BGC evidence** — species trees, BGC-family
  trees, and locus comparisons exist but interpretation remains scattered. *Improvement:*
  standardize tip identity, tree provenance, and family-tree-versus-species-tree labeling. See
  [Phylogenetic Placement](../../../wiki/Phylogenetic-Placement.md).
- **Public-release genericization can conflict with private research workflows** — stripping
  private cohorts and personal paths for public release can break the same software used
  internally. *Improvement:* one core codebase with explicit private-project adapters and a
  tested public-derivative build, rather than forking scientific logic.
- **Sapote-Mamey is not a substitute for expert or experimental validation.** It can make review
  more disciplined, but cannot guarantee every gene annotation, pathway reconstruction, or
  priority is correct. Its highest-value outputs are transparent reasoning and efficient
  experimental choices.
