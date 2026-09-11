# What It Does and Limitations

*Current to bundle v9.7.405 · engine Mamey 1.9.145. Authored by Codex (2026-08-27); admitted to
the bundle wiki at v9.7.405 by the Claude Code patch lane after a currency pass. Documentation
only — confers no scientific, release, or publication authority; class-level hypotheses,
judgment deferred.*

A candid internal assessment of Sapote-Mamey's demonstrated strengths and known limitations,
condensed from Codex's forty-strengths / forty-limitations review for the wiki. **Strength**
means a capability or design choice that has produced genuine scientific, interpretive,
reproducibility, or communication value. **Limitation** does not necessarily mean a bug — it
may be an unavoidable boundary of genome mining, an architectural debt, a data-coverage gap, or
a workflow that is scientifically correct but expensive to operate. Neither list establishes the
identity, production, activity, novelty, or ecological function of any metabolite; every channel
named below (BLASTp, MIBiG, BiG-SCAPE, ClusterBlast, Pfam, antiSMASH) provides class- or
similarity-level evidence whose authority depends on exact binding, coverage, comparator scope,
and experimental validation. See [Claim-Safety](Claim-Safety.md) for the language contract this
page itself follows.

---

## Strengths

### A. Scientific reasoning and claim calibration

- **Extraction and judgment are explicitly separated.** Mamey performs deterministic extraction
  while Sapote performs interpretation, so a successful parser or score can never silently become
  a biological conclusion.
- **Similarity is not treated as identity.** The distinction between a homologous sequence, an
  identical protein, an orthologous function, and a chemically equivalent pathway is preserved
  throughout — natural-product databases contain many remotely related enzymes whose shared
  family names conceal different substrates and reactions.
- **Capacity is not treated as production.** A coherent cluster supports biosynthetic capacity,
  not proof of expression or metabolite production; culture, expression, chemistry, and
  bioactivity stay outside the genomic claim unless measured evidence is supplied.
- **Missing evidence is represented as a workflow state.** Missing, blocked, unreturned, unbound,
  or CPU-terminated searches are never rewritten as biological no-hits.
- **Alternatives and resolving experiments are first-class outputs.** The strongest Mode B
  sections name competing interpretations and the specific experiment that would distinguish
  them, not just a favored model.

### B. Identity and evidence binding

- **The exact-locus display contract is exceptionally strong.** Every BGC is identified by
  strain, full node or contig, region, and secondary alias — evidence cannot drift between
  records that share a convenient alias but represent different physical intervals.
- **Protein sequence SHA-256 is the gene identity anchor**, more reliable than a mutable locus
  tag; it lets the workflow recognize renamed genes while refusing stale results attached only by
  label.
- **Physical interval and CDS-roster reconciliation is explicit** — node, region, coordinates,
  translated CDS roster, and neighboring genes are compared directly, which has already caught
  real loose-versus-canonical source conflicts.
- **Source-local aliases are display-only** and never control joins — a mature response to
  antiSMASH region renumbering and boundary-flavor changes.
- **Quarantine is a real evidence state, not a euphemism.** When a source cannot bind the exact
  physical object, the source and its exclusion reason are retained without contaminating current
  interpretation.

### C. Evidence breadth and channel separation

- **The per-gene BLASTp matrix is unusually informative** — named subjects, residue
  denominators, coverage, identity, positives, E-values, and channel state per protein, not a
  single cluster-level similarity label.
- **BLASTp channels remain distinct.** ClusteredNR representative-sequence similarity is never
  presented as full-nr identity, and curated Swiss-Prot evidence is never conflated with NCBI
  databases.
- **MIBiG evidence is decomposed to gene level** as family navigation, not automatic product-name
  transfer — per-gene agreement can reveal whether similarity concentrates in housekeeping
  proteins or genuinely diagnostic machinery.
- **ClusterBlast contributes physically-bound neighborhood evidence**, distinguishing a coherent
  pathway neighborhood from unrelated homologs scattered across genomes.
- **BiG-SCAPE is interpreted as run-relative family placement**, retained by cutoff and comparator
  corpus rather than promoted to biological identity.
- **RG-GMCI offers a disciplined split-pathway hypothesis layer** — homology-guided linkage stays
  separate from physical nucleotide joining, gated by a two-proof admission requirement.
- **Chitin metabolism is assessed as a strain-level system**, not forced into a BGC-local pathway
  narrative.
- **Resistance evidence is routed into gene-oriented review**, naming genes and retaining
  substrate, direction, and mechanism as unresolved unless supported.
- **Domain rarity provides a complementary lens** — a prioritization signal, not proof of
  novelty.
- **Historical cards and V7 evidence are preserved, not discarded**, via an additive successor
  model that corrects stale boundaries/aliases/overclaims explicitly rather than erasing them.

### D. Mode B as a scientific product

- **The 48-section format forces multidimensional review**, making it difficult for one
  attractive annotation to dominate the interpretation unnoticed.
- **The complete named-match gene table is a major advance** — a reader sees the actual protein,
  its length, identity, domains, channel-specific matches, and proposed role.
- **Sections 5–7 can reconstruct biosynthetic logic rather than repeat labels**, at their best
  reasoning closer to expert natural-products analysis than an antiSMASH product string.
- **Gene-oriented self-resistance and comparator sections improve usefulness** by naming the
  actual transporter, regulator, or resistance-like protein — and expose when a section has no
  real evidence.
- **Future locus-map parity is built into the card**, so a polished figure is less likely to
  silently use a different denominator from the scientific narrative.

### E. Reproducibility, governance, and software quality

- **Packages carry manifests, checksums, and provenance**, distinguishing byte preservation from
  semantic equivalence and from biological acceptance.
- **Durable state files support long-running work** — checkpoints, decision/hold ledgers, and
  save-state front doors reduce dependence on conversational memory alone.
- **Governed exclusions are explicit**, with rationale and retained historical evidence kept
  separate from the operational cohort.
- **Release tiers fail safe.** Private strain identifiers are protected by prefix- and
  policy-aware release logic; a public override is refused for governed private identifiers.
- **Post-seal analyses are non-blocking** — figures, cohort comparisons, and Mode B writing run
  after deterministic package completion, so a visualization failure cannot invalidate the core
  package.
- **The test suite is broad and guard-oriented**, targeting claim safety, source transfer,
  scoring guards, release hygiene, and structural contracts.
- **Patch and cut discipline encourages traceability** — bounded patches, reviewed and tested
  against clean trees before a new cut.
- **Offline and portable operation is a real design goal** — vendored parsers, optional-dependency
  fallbacks, and sealed ZIP packages reduce dependence on any one cloud environment.
- **The system is extensible without forcing every module into the core run** — clinker, Figure
  Factory, phylogenomics, and report builders evolve as optional or post-seal capabilities.
- **Version streams are explicitly tracked** — engine, bundle, and build versions as separate but
  synchronized concepts (see [Versioning](Versioning.md)).

### F. Communication and research integration

- **Figure Factory converts governed data into publication-oriented views**, with captions and
  methods living beside each figure.
- **Interactive widgets expose gene-level evidence efficiently**, letting a reader inspect
  BLASTp coverage without opening several databases.
- **Clinker adds a powerful neighborhood-comparison layer** — pairwise and family-wide gene maps
  reveal conserved core cassettes, rearrangements, and accessory blocks; phylogeny-ordered clinker
  separates BGC-family relatedness from species phylogeny.
- **The system supports thesis, manuscript, supervisor, and collaborator outputs** from the same
  evidence, reducing the risk of a scientifically inconsistent retelling per audience.
- **The project creates a durable reasoning record** — why a candidate was prioritized, what was
  rejected, and which experiment would resolve the uncertainty, independent of whether the
  compound is ever validated.

---

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
- **Swiss-Prot coverage gaps should usually be avoidable** since the curated database can be
  searched locally — a missing cell often signals ingestion failure, not an unavoidable gap.
  *Improvement:* routine offline Swiss-Prot preflight for every selected locus.
- **Comparator corpora are incomplete by construction** — an apparently private family can become
  shared as more type, cohort, or taxonomically close genomes are added. *Improvement:* record
  comparator-corpus version and nearest-reference density beside every prevalence/novelty
  statement.

### D. Biological and assembly limitations

- **Fragmented assemblies inflate apparent BGC counts.** Many short contigs and edge-reaching
  records can inflate the number of antiSMASH regions and split one pathway into several
  candidates — an already-observed pattern in this project's own fragmented-assembly cases, not
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
  [Phylogenetic Placement](Phylogenetic-Placement.md).
- **Public-release genericization can conflict with private research workflows** — stripping
  private cohorts and personal paths for public release can break the same software used
  internally. *Improvement:* one core codebase with explicit private-project adapters and a
  tested public-derivative build, rather than forking scientific logic.
- **Sapote-Mamey is not a substitute for expert or experimental validation.** It can make review
  more disciplined, but cannot guarantee every gene annotation, pathway reconstruction, or
  priority is correct. Its highest-value outputs are transparent reasoning and efficient
  experimental choices.

---

## Planned: clinker expansion (short version)

The current clinker implementation already supports interactive gene arrows and homology
ribbons, coloring by shared dominant Pfam orthogroup, several row-ordering modes (including an
optional BiG-SCAPE family tree), reversible track orientation, cohort/type/MIBiG-associated
family membership, and an explicit warning that a BGC-family tree is not a species tree. A
phylogeny-ordered actinomycete case study already shows this working end to end: a large
conserved type-II-PKS-associated neighborhood, aligned across biosynthetic, regulatory,
transport, and resistance-like components — a comparison target, not a metabolite-identity
assignment.

Planned next, per Codex's expansion note:

1. **A standard per-locus clinker folder** (`<strain>__<node>__<region>__<alias>/clinker/`)
   holding a pairwise-best-comparator page, a cohort/type-family page, and a MIBiG/characterized-
   reference page, each with its own binding TSV and caption/methods file — the folder name and
   every row preserving the full exact-locus identity, never a bare alias.
2. **A restrained broader-family view** — the query locus plus a small, representative set of
   nearest cohort loci and genus-matched type/reference loci, rather than every family record, to
   avoid unreadable ribbon tangles on large families.
3. **A fixed interpretation checklist per clinker folder** — which named genes/domains define the
   shared biosynthetic core; which shared proteins are only generic transport/regulatory/
   housekeeping; whether core genes share order and orientation; which tailoring or
   resistance-like genes distinguish the query; whether the comparison is full-, partial-, or
   single-gene; whether assembly fragmentation truncates either locus; and what remains
   unresolved.
4. **A literature-grounded diagnostic note for type-II PKS comparisons** — explicitly warning
   that common ABC-transporter/membrane-component domains are not by themselves type-II-PKS
   identifiers, and that diagnostic weight belongs on minimal PKS machinery, cyclases/aromatases,
   ketoreductases, tailoring enzymes, and conserved neighborhood structure instead.

None of this is implemented by this page. It is a specification note only — the same
non-overlap discipline as [Figure-Factory-Preflight-and-Methods-Manual](Figure-Factory-Preflight-and-Methods-Manual.md).

---

## Methods note

This assessment was derived from the Sapote-Mamey code and documentation line, Mode B authoring
and audits, BLASTp completion receipts, sealed packages, BiG-SCAPE/clinker outputs, Figure
Factory work, public-release audits, and repeated exact-locus reconciliation exercises. It is a
design and workflow assessment, not a benchmark against an external gold-standard BGC annotation
corpus. The strengths describe demonstrated capabilities or repeated useful behaviors; the
limitations describe observed failure modes, known data constraints, and foreseeable risks.
