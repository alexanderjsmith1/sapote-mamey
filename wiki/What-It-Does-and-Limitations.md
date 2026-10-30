# What It Does and Limitations

Review the software capabilities and their limits.  
This page is for readers deciding whether a workflow fits their task.

*Current to bundle v9.7.461 · engine Mamey 1.9.177.*

What Sapote-Mamey does well, and where its limits are recorded. The retained strengths describe design requirements and selected demonstrated routes, not universal enforcement across every command. Current implementation gaps and source-specific holds remain controlling; this page is not a fresh benchmark or audit receipt. **Strength**
means a capability or design choice that has produced genuine scientific, interpretive,
reproducibility, or communication value. The strengths below do not establish the
identity, production, activity, novelty, or ecological function of any metabolite. Every channel
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
  throughout. Natural-product databases contain many remotely related enzymes whose shared
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

- **The exact-locus display contract requires four fields:** strain, full node or contig,
  region, and secondary alias. Verify each consumer's binding: records can share an alias while
  representing different physical intervals, and a stated contract does not guarantee every join.
- **Protein sequence SHA-256 binds sequence content**, including when a gene label changes.
  Identical sequences can occur at different loci, so the digest does not identify a physical gene
  by itself; retain the complete locus, coordinates and roster binding as well.
- **Physical interval and CDS-roster reconciliation is explicit** — node, region, coordinates,
  translated CDS roster, and neighboring genes are compared directly, which has already caught
  real loose-versus-canonical source conflicts.
- **Source-local aliases are secondary in the identity contract.** Some consumers still resolve records by alias, and the biosynthetic-tree preparer retains products by `bgc_id` without emitting full contig/region identity. Reconcile the complete bound locus tuple before using those outputs; an alias lookup is not an accepted physical-identity join.
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
- **RG-GMCI offers a split-pathway hypothesis layer** — homology-guided candidate linkage stays
  separate from physical nucleotide joining. Computational categories do not prove a physical join.
- **Chitin metabolism is assessed as a strain-level system**, not forced into a BGC-local pathway
  narrative.
- **Resistance evidence is routed into gene-oriented review**, naming genes and retaining
  substrate, direction, and mechanism as unresolved unless supported.
- **Domain rarity provides a complementary lens** — a prioritization signal, not proof of
  novelty.
- **Historical cards and V7 evidence are preserved, not discarded**, via an additive successor
  model that corrects stale boundaries/aliases/overclaims explicitly rather than erasing them.

### D. Mode B as a scientific product

- **Named Mode B profiles structure multidimensional review**: `full48` is the default and
  `current50_v2` is opt-in. Mechanical checks do not establish scientific review; see
  [Mode B](Mode-B.md) for the selected contract and evidence limits.
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
- **Release metadata defaults to PRIVATE.** Named profiles use exact strain assignments and nonpublic default tiers; identifier spelling supplies no public authority. The legacy operator route has selected private-pattern/registry guards, while an exact profile follows its own tier policy. Review the actual selected export projection and receipts: a release label or helper rule does not establish whole-bundle disclosure safety.
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

The earlier limitations list is kept as a [historical record](../docs/history/retired_458/What-It-Does-limitations.md); for the limits that apply to a current run, read [Claim-Safety](Claim-Safety.md) and [Common Mistakes](Common-Mistakes.md).

---

## Methods note

This assessment was derived from the Sapote-Mamey code and documentation line, Mode B authoring
and audits, BLASTp completion receipts, sealed packages, BiG-SCAPE/clinker outputs, Figure
Factory work, public-release audits, and repeated exact-locus reconciliation exercises. It is a
design and workflow assessment, not a benchmark against an external gold-standard BGC annotation
corpus. The strengths describe demonstrated capabilities or repeated useful behaviors. The
limitations list, now kept as a historical record, described observed failure modes, known data
constraints, and foreseeable risks.
