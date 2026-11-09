# Mode B contract current50 v2 (§1–§50)

This page lists what each of the 50 sections of a current50_v2 card covers, and which of them every card must have. For the step-by-step recipe, see the [Mode B walkthrough](MODE_B_USER_WALKTHROUGH.md). For terms such as KCB and RG-GMCI, see the [glossary](GLOSSARY.md).

The machine copy is `mamey/data/mode_b/modeb_current50_v2_contract.json`. The full authoring and audit requirements for each section, including identity, source-freeze and citation rules, are in [the 50-section authoring requirements](MODEB_50_SECTION_CONTRACT_CANDIDATE.md), a frozen page; read it with [its reading guide](MODEB_50_CONTRACT_READING_GUIDE.md). [MODEB_PUBLICATION_SECTION_REQUIREMENTS_v9_7_372.md](MODEB_PUBLICATION_SECTION_REQUIREMENTS_v9_7_372.md) holds the same requirements plus a note on which of them the verifier checks.

Emit a template with:

```bash
python mamey_run.py emit-modeb-template --package <pkg> --bgc <BGC> --contract current50_v2
```

Verify the saved card with:

```bash
python mamey_run.py verify-modeb <card.md> --package <pkg> --bgc <BGC> --contract current50_v2 --report-json <receipt.json>
```

## The §50 evidence table

A card that declares `FINISHED_FULL50_CURRENT50_V2` gets a check of §50: one row per gene, with each BLASTp channel kept apart. Give the verifier the package and BGC, so it can bind the package's locus-tag roster. A card-only run cannot show the roster is complete.

- §4 is a short role overview. It cannot stand in for §50.
- Use the subsection heading `#### Complete named-match, channel-separated table` in §50.
- Use one row per canonical gene, in canonical gene order, with the protein length in amino acids. Give each of nr, ClusteredNR and Swiss-Prot a named-match cell and an identity, positives and query-coverage cell.
- When a channel has a hit, the named-match cell holds the rank-1 accession, the full matched-protein description and the subject organism, as `accession — description [organism]`. A bare accession, a bare percentage, or an accession with only an organism fails verification (`BLASTP_MATRIX_SUBJECTS`). This is a check of the cell's shape. It does not compare the wording with the saved BLASTp result, so a person still checks each description against its source.
- When a channel has a hit, the paired metric cell holds percent identity, percent positives and query coverage. Percent positives is not percent identity.
- Give each channel's coverage denominator on its own. Do not add the denominators together.
- In both cells of a channel, write the explicit state: missing or measured no-hit. Never write zero for a missing value.
- Pending cells are not finished states.

## Required, conditional and optional sections

Each section in the table below is one of three kinds. The kind is the `required` field in the JSON copy.

- Required: §1–§20, §22, §23, §26, §28, §30 and §48–§50. Every card has these.
- Conditional: §21, §24, §25, §27, §29, §32–§36, §38 and §43. Write the section when its condition holds. Otherwise write a reasoned `NOT_APPLICABLE`. Conditions in the JSON include: §21 for RiPP- or NRPS-relevant loci, §32–§34 for a region with a measured assembly line, §35 for a region with more than one protocluster, §36 for a region at a contig edge or flagged as truncated or overmerged, §38 for a bound co-located resistance or efflux signal, and §43 for a region in an above-bar RG-GMCI pair. The JSON states the condition for each section.
- Optional: §31, §37, §39–§42 and §44–§47. A draft may leave these out. If you include one, it needs its exact number and title, the right order, and a body. A heading with an empty body fails with `EMPTY_OPTIONAL_SECTION`.

A finished card needs all fifty. A card that declares `FINISHED_FULL50_CURRENT50_V2` must contain every section, conditional and optional ones included. The emitted template declares this profile in its first line and contains all fifty headings. The rule is the `finished_profile_section_rule` entry in the JSON, and the verifier enforces it:

- an absent section fails with `MISSING_FINISHED_PROFILE_SECTION`;
- a section that applies does not need special wording;
- a section that does not apply carries `NOT_APPLICABLE` and a written reason, for example `NOT_APPLICABLE: no supervisor or university cohort was supplied for this strain.` A bare `NOT_APPLICABLE` with fewer than three words of reason fails with `NOT_APPLICABLE_WITHOUT_REASON`.

The reason check counts words. It does not judge whether the reason is true; a person still checks that.

## Stating a missing result

A card may state a precise evidence limit. Example:

`NOT_RUN: GECCO was not evaluated because its source file is unavailable; no prediction is inferred.`

The sentence must give the state, a cause and what you will not infer. The verifier accepts these six states:

| State | Use it when |
|---|---|
| `NOT_RUN` | The analysis was not run. |
| `UNAVAILABLE` | The input or source does not exist. |
| `NOT_APPLICABLE` | The analysis does not apply to this locus. |
| `OBSERVED_UNBOUND` | Output exists but cannot be tied to this exact locus. |
| `UNRETURNED` | A requested result has not come back. |
| `INGEST_GAP` | The result exists but has not been loaded into the package. |

The state alone does not excuse other wording. A bare TODO, an unfilled prompt or a promise of later work still fails. A person must still check that the state and reason are true.

## What a pass means

The JSON receipt records `contract: current50_v2`, `contract_schema_version: modeb_current50_v2` and the §1–§50 profile. `independent_roster_bound` says whether the package roster was bound. It is not a content verdict.

A pass means the structure and shared evidence checks hold. It does not validate any section's science. The full48 publication checks do not apply here, because the section numbers differ. A person must still review source and protein provenance, geometry, GECCO and rescue interpretation, and the final content.

Pin this file by its sha256. Do not edit it in place.

## Sections

| § | Requirement |
|---|---|
| 1 | Identity and node/region: Exact four-part identity; assembly/profile; region interval and sequence/CDS binding; protein-hash/neighborhood identity policy; canonical versus source-local alias distinction. |
| 2 | Why this BGC was selected: Evidence-based selection rationale; current triage context; why this exact locus merits attention; no score-as-truth shortcut. |
| 3 | Boundary and assembly status: Exact boundary geometry; truncation/overmerge assessment; displayed exact/context denominators; what assembly state permits and prevents. |
| 4 | Gene-by-gene interpretation: Short gene-role overview and pointer to §50. Preserve exact/context membership and the core, tailoring, transport, regulator and context distinctions without duplicating the full table. |
| 5 | Core biosynthetic logic: Exact committed-step genes; reaction-level roles; conditional ordered pathway; minimal-gene-set/on-contig audit; strongest false-positive alternative; evidence for/against; positive and negative claim ceilings. |
| 6 | Tailoring and maturation logic: Direct tailoring candidates separated from broad metabolic context; conditional order; non-diagnostic families; comparator conflicts; coupling evidence; discriminating tests. |
| 7 | Transport, resistance, and regulation: Independent transport, resistance, and regulation adjudications; direction/substrate/mechanism/operon holds; no proximity-to-function leap; no exact-bound evidence distinguished from biological absence. |
| 8 | Comparator/KCB interpretation: KCB, MIBiG, ClusterBlast, and named comparator convergence/conflict; gene coverage and core-versus-generic-flank distinction; similarity never identity. Integrate reference-guided rescue comparisons. If one found gene matches two reference genes, report the reciprocal-best assignment and name the competing match with its evidence; an absent reciprocal result remains explicit. |
| 9 | Alternative hypotheses: At least two locus-specific alternatives when evidence permits; strongest rival model; observations that discriminate each model. |
| 10 | Fragmentation and co-capture risks: Fragment/co-capture/overmerge risks; exact edge distances; partner-locus possibilities; RG-GMCI claim ceiling; no physical join without nucleotide proof. |
| 11 | Product-family interpretation: Product-family capacity model from core grammar; exact compound held unless independently established; comparator conflicts retained. |
| 12 | Host/microbe ecological interpretation: Host/microbe context from verified strain metadata and prevalence across all AS strains, including bee/wasp, attine and moss cohorts; chitin/ecology signals treated as strain context unless exact-locus coupled. |
| 13 | Antibacterial/antifungal relevance: Class-level antibacterial/antifungal relevance; extract phenotype separated from locus attribution; literature claim and organism scope explicit. |
| 14 | What cannot be claimed: Explicit forbidden claims: exact product, production, activity attribution, novelty, ecological function, physical linkage, and expression as applicable. |
| 15 | Missing evidence: Typed remaining gaps only after accessible sources are searched; distinguish unavailable, unbound, not run, running, ingest gap, measured-none, and not applicable. |
| 16 | BLASTP/HMMER next steps: Current BLASTp/HMM/domain evidence plus only unresolved next tests; later nr/ClusteredNR additions are versioned, additive updates rather than a card-wide blocker. |
| 17 | LC-MS / fermentation implications: Testable LC-MS/fermentation implications derived from the conditional product-family model; no predicted mass asserted as detected. |
| 18 | Figure/locus-map notes: Lossless future-map payload requirements: every displayed gene, label, coordinates, strand, domains, selected genes, named matches and holds; V7 comparator preserved. Rendering remains a separate gate. |
| 19 | Final Mode B judgement: One integrated judgment and cross-cohort synthesis, preserving support, contradictions, strongest alternative, confidence, final claim ceiling and unresolved discriminating evidence. No publication-ready claim from mechanical checks. |
| 20 | Next actions: Prioritized bounded actions with decision rules and owners; accessible evidence is obtained/reconciled rather than labeled pending. |
| 21 | RiPP / NRPS precursor ladder and RiPP search: Merged v1 §§21–22: For RiPP/NRPS-relevant loci, conditional precursor/monomer ladder with assumptions. For RiPP-relevant loci, document search scope, databases, precursor/maturation evidence and negative-result ceiling. Preserve NRPS applicability; justify component-level non-applicability separately. |
| 22 | GECCO gene-level and cluster evidence: GECCO evidence across the exact core region and candidate rescued contigs: complete per-gene probability table, cluster probabilities, run/version and sequence binding; agreement or disagreement with antiSMASH boundaries; GECCO-only genes and clusters. Bind GECCO ClusteredNR evidence and available nr results separately to exact proteins; distinguish returned hits, measured no-hit results and unperformed or unreturned searches. Prediction is not product or activity proof. |
| 23 | Production strategy: heterologous expression and OSMAC: Merged v1 §§23 and 26: Integrated production-strategy assessment covering heterologous-expression rationale, minimum-construct assessment, pathway completeness, host limitations, controls and interpretation, plus OSMAC rationale tied to plausible regulation/product-family chemistry and measurable outcomes. Preserve distinct questions and evidence for each component; justify non-applicability separately. No inference of production from genomic capacity. |
| 24 | Scaffold novelty score: Novelty evidence decomposed into architecture, homology, cohort prevalence and comparator distance; “no hit” is not novelty. |
| 25 | Genome neighbourhood: Exact genomic-neighborhood conservation from ClusterBlast/current comparisons; core versus generic conserved context distinguished. |
| 26 | Contigs rescued into the BGC: Reference-guided gap rescue and the whole-BGC view: preserve the core identity as strain / full contig / region / BGC; identify every partner contig and its exact gene identities. Tabulate reference genes found within the core region, found elsewhere and set aside by partner checks, with denominators and reference identity. Bind every gene-level split-link ruling and adjudication, RG-GMCI component evidence, assembly evidence and assembled/candidate locus map. Settled similarity or partner rulings do not establish a nucleotide join. Display unresolved partners as candidates; state competing explanations and the precise evidence needed to discriminate them. |
| 27 | Self-resistance assessment: Mechanism-specific self-resistance evidence, exact gene coupling, alternatives and required validation; broad transporter/family names are insufficient. |
| 28 | Evidence provenance ledger: Claim-by-claim provenance; 14-stream disposition table; historical source-loss table; 50-row section reconciliation matrix. |
| 29 | Cross-cluster interactions: Cross-cluster hypotheses with exact four-part partner identities, evidence state and physical-linkage ceiling; otherwise reasoned not-applicable. |
| 30 | Experimental decision tree: Branching experimental decision tree: question, experiment, positive/negative decision rule, and program consequence. |
| 31 | Region CDS census: Exact region CDS census plus boundary-context census; independently reconciled denominators; no denominator-difference identity failure. |
| 32 | Assembly-line inventory: Assembly-line enzyme/domain inventory from measured architecture; absent modules distinguished from unmeasured modules. |
| 33 | Module programming readout: Module programming, substrate/extension/reduction logic and uncertainty; no collinearity assumption without support. |
| 34 | Initiation & release logic: Initiation/loading and release/cyclization logic, candidate genes, alternatives and missing functions. |
| 35 | Protocluster decomposition: Per-protocluster decomposition for mixed/overmerged regions; each core and accessory set assigned or held separately. |
| 36 | Boundary status + overmerge/locus-splitting adjudication (merged): Boundary, overmerge and locus-splitting adjudication integrated with exact intervals and sequence/CDS evidence. |
| 37 | Partner & accessory proteins: Partner/accessory proteins classified as direct, plausible, broad context, or unbound; mechanism and coupling evidence stated. |
| 38 | Co-located resistance & efflux: Resistance/efflux signals with exact locus, mechanism specificity, direction, coupling and phenotype ceiling. |
| 39 | Cross-strain sequence identity: Cross-strain identity/coverage on exact orthologous genes/loci with denominators and channels; no alias-only comparison. |
| 40 | BiG-SCAPE family / cohort placement: BiG-SCAPE family, cutoff, run receipt, cohort/reference membership and private/shared scope; new run may update additively. Bind the current BiG-SCAPE run including MIBiG and reference-genome membership, per the companion-tool protocol, with its run receipt, parameters and compatible sequence/profile scope. If the required run is absent, state the actual evidence limitation rather than infer its results. |
| 41 | Protein / domain phylogeny: Protein/domain phylogeny target, sequence binding, reference set, model limits and supported clade-level inference. |
| 42 | Horizontal transfer evidence: HGT/composition evidence relative to a declared genomic baseline; mobile/context alternatives; GC deviation alone is insufficient. |
| 43 | Split-pathway / cross-contig (RG-GMCI): RG-GMCI/cross-contig candidates with exact partner identity, component signals and explicit “candidate, not nucleotide join” ceiling. Cross-reference §26 for rescue tables and gene-level rulings; retain independent RG-GMCI component assessment without duplicating those tables. |
| 44 | Within-cohort prevalence & tier: Within-cohort prevalence with exact numerator/denominator, profile/class definition and governed exclusions. Also enumerate protein PCoA set membership for the exact BGC proteins and candidate partners, with input sequence identities, set/run receipts, embedding parameters and membership denominators. Separate set membership and visual proximity from supported functional or phylogenetic inference. Show the protein PCoA figure for the BGC: the compact two-set view, or the full PCoA where its proteins fall in more than two sets. |
| 45 | Supervisor / university cohort comparison: Supervisor/university cohort comparison with declared cohort, comparable denominator and source receipt; otherwise reasoned not-applicable. |
| 46 | Type / reference strain comparison: Type/reference-strain comparison on exact comparable loci and genes, including Mamey/antiSMASH profile compatibility and divergence. |
| 47 | Host-matched unrelated reference: Host-matched unrelated reference comparison with verified host metadata, comparator rationale and transfer limits. |
| 48 | Biosynthetic gene, domain and machinery literature: Biosynthetic gene, domain and machinery citations with explicit relevance to named genes, domain logic, alternatives or experiments; source scope and limits of transfer stated. Evaluate primary literature claim by claim, identifying the named gene/domain or inference supported, comparator organism and experimental scope, contradictory findings and transfer limits. |
| 49 | Genus and biological-context literature: Genus secondary-metabolite and broader biological-context citations with explicit relevance; justify broader taxa/topics and distinguish reference phenotype from focal-strain evidence. Evaluate primary literature relevance to verified strain/genus and host context, retaining contradictory evidence and separating reference-organism activity from focal-locus attribution. |
| 50 | Data evidence table: Complete contiguous named-match table formerly in §4, with unchanged full gene roster, geometry, protein binding, channel separation, result/admission states and typed holds. This data evidence table is the final numbered section. Include every core-region CDS and separately identified partner/context genes with full identities, coordinates, strand, sequence binding, named matches, identity/coverage, independent evidence channels, domains, GECCO probabilities, comparator/rescue assignments and split-link rulings as applicable. Resolve competing reference matches by reciprocal-best evidence where available and name the alternative. Tables may be split into linked parts for readability without dropping rows or provenance. |
