# Mode B contract current50 v2 (§1–§50)

Machine copy: `mamey/data/mode_b/modeb_current50_v2_contract.json`. Emit with `python mamey_run.py emit-modeb-template --package <pkg> --bgc <BGC> --contract current50_v2`; verify the saved card with `python mamey_run.py verify-modeb <card.md> --package <pkg> --bgc <BGC> --contract current50_v2 --report-json <receipt.json>`.

A card declaring `FINISHED_FULL50_CURRENT50_V2` activates the independent per-gene roster and
channel matrix check in §50. Supply the exact-locus package and BGC so the verifier can bind its
canonical locus-tag roster; a card-only run cannot certify roster completeness. §4 remains a
role overview and cannot substitute for §50. Use the subsection heading
`#### Complete named-match, channel-separated table` in §50, with one row per canonical gene
and separate named-match and identity/positives/query-coverage cells for nr, ClusteredNR and
Swiss-Prot. Keep a channel's explicit missing or measured-no-hit state in both paired cells;
never replace missing values with zero. Pending cells are not finished terminal states.

A precise evidence limitation is permitted. For example:
`NOT_RUN: GECCO was not evaluated because its source file is unavailable; no prediction is inferred.`
The same sentence must name the typed state, a causal reason and the inference ceiling. The
verifier recognizes `NOT_RUN`, `UNAVAILABLE`, `NOT_APPLICABLE`, `OBSERVED_UNBOUND`, `UNRETURNED`
and `INGEST_GAP` for this narrow exception to generic non-evaluation wording. A token alone does
not exempt other sentences, TODOs, unfilled author prompts or promises of later work. Independent
review must still establish whether that state and reason are true and whether the selected
profile's readiness requirements are met.

The JSON receipt records `contract: current50_v2`, `contract_schema_version: modeb_current50_v2`
and the §1–§50 profile. Its `independent_roster_bound` reports the package roster binding; it is
not an independent content-QA verdict. Passing the shared evidence checks and v2 structure checks
does not validate every section's scientific content. The full48 semantic publication gates are
not applied to this profile's different section numbers. Source/protein provenance, geometry,
GECCO/rescue interpretation and final content acceptance still require independent review.

What changed from current50 v1:

- §21 merges the RiPP precursor ladder and the RiPP search (v1 §21 + §22).
- §22 is new: GECCO gene-level and cluster evidence.
- §23 merges heterologous expression and OSMAC into one production-strategy section (v1 §23 + §26).
- §26 is new: the contigs rescued into the BGC (reference-guided gap rescue, split-link rulings, assembled map).
- §8 and §26 name both reference genes when one found gene is the best hit of two.
- §40 uses the current BiG-SCAPE run with MIBiG and the reference genomes; §43 points to §26; §44 names the protein PCoA sets.
- §48 and §49 are the literature sections, with relevance. §50, the data evidence table, is the very last section and adds the GECCO probability and the gap-rescue match per gene.

Rows below use the same `| n | requirement |` shape as v1, so the four consumers that parse a 50-row table accept this file. Pin it by its own sha256; never edit it in place.

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
