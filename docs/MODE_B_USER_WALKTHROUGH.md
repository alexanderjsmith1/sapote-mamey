# From extraction to a Mode B card

This guide connects the first-run walkthrough to authored interpretation. A complete extraction does not create a scientifically finished card. Begin with the whole validated package, the original input when needed, and an exact strain / full contig / region / BGC identity. Supply available evidence-channel files and their provenance; a manifest names files but does not contain all their evidence.

## Choose the actual profile

The always-required 1–20 core, older 30-section candidate/calibration profile, 48-section corrective profile and 50-section publication-candidate requirements are different objects. The intended 50-section deliverable must not be called complete because a shorter scaffold exists. Conversely, renaming a 48-section status does not implement 50-section verification.

The installed 48-section corrective profile still has consumers. The [50-section usage contract](MODEB_FULL50_CONTRACT_USAGE.md) lists the consumers that require exactly 50 sections and their Markdown/database bindings. The frozen source contract is [here](MODEB_50_SECTION_CONTRACT_CANDIDATE.md). Do not edit its hash-pinned text in place or feed the JSON reference to a Markdown reader. A full producer/consumer migration has not been performed in this cut.

## Runnable preparation and review

Use a separate review destination. Replace the sample paths with real locations and select a locus from the same package:

```bash
python mamey_run.py mode-b --package '/path/to/package' --top-n 1 --outdir '/path/to/review/mode_b'
python mamey_run.py verify-modeb '/path/to/review/authored-card.md' --package '/path/to/package' --bgc BGC001 --summary-only --report-json '/path/to/review/card-verification.json'
```

The first command prepares native Mode B output; it is not a universal 50-section author or a finished biological interpretation. Inspect the emitted files and named profile. The second checks an existing authored Markdown card under the installed verifier and selected gates; it does not perform online literature or protein searches. A JSON report retains findings; a nonzero exit requires review. Do not use force or weaker depth settings simply to make a finished card pass. Ask the operator to check the exact command help before adding prospective semantic gates, and record which gates actually ran.

A useful assistant request is: “Use this complete package and the selected four-part locus identity. Inventory the available evidence, identify the intended profile and its actual verifier, and draft a bounded interpretation. Preserve alternatives, missing evidence and per-claim sources. Do not submit anything online. Save the card, evidence mapping and verification report in this review folder. Tell me which publication requirements remain unverified.”

## Read and resume

Start with the [worked phosphonate reference card](reference/modeb_exemplars/phosphonate_reference_full48_no_blastp_exemplar.md) and [exemplar scope](reference/modeb_exemplars/README.md). This is an explicitly limited 48-section reference, not a finished 50-section card. The v9.7.429 cut is an internal review base. The requested migration—preserve the 48-section content, add two relevant literature sections, and place the evidence table last at §50—is queued as a v9.7.430 placeholder. It does not block this internal cut. A source-bound historical card will help test the later migration.

Keep the authored card, exact-source mapping, evidence receipts, selected contract hash, verification JSON and checkpoint together. Reopen them to resume; do not rebuild identity from a BGC alias alone. If a file or database binding is unavailable, record the required asset and decision it would resolve. Updating evidence requires a versioned review, not silently relabeling the previous card as current.

Use the [interpretive floor](MODEB_INTERPRETIVE_FLOOR_v97146.md), [data availability and writing contract](MODEB_DATA_AVAILABILITY_AND_WRITING_CONTRACT.md), [evidence escalation workflow](MODEB_EVIDENCE_ESCALATION_WORKFLOW_v97143a.md), and [claim-safety audit](MODE_B_CARD_CLAIM_SAFETY_AUDIT.md). Section requirements are not evidence and mechanical validation is not owner scientific acceptance.

## Complete 50-section requirement map

The rows below are copied from the installed frozen reference, not newly invented titles. Sections 48 and 49 cover citation/relevance requirements; section 50 is the complete gene-by-gene evidence-channel matrix. The profile's own conditions determine applicability; an unsupported section needs an explicit, justified state rather than invented detail.

| Section | Requirement |
|---:|---|
| 1 | Exact four-part identity; assembly/profile; region interval and sequence/CDS binding; protein-hash/neighborhood identity policy; canonical versus source-local alias distinction. |
| 2 | Evidence-based selection rationale; current triage context; why this exact locus merits attention; no score-as-truth shortcut. |
| 3 | Exact boundary geometry; truncation/overmerge assessment; displayed exact/context denominators; what assembly state permits and prevents. |
| 4 | Short gene-role overview and pointer to §50. Preserve exact/context membership and the core, tailoring, transport, regulator and context distinctions without duplicating the full table. |
| 5 | Exact committed-step genes; reaction-level roles; conditional ordered pathway; minimal-gene-set/on-contig audit; strongest false-positive alternative; evidence for/against; positive and negative claim ceilings. |
| 6 | Direct tailoring candidates separated from broad metabolic context; conditional order; non-diagnostic families; comparator conflicts; coupling evidence; discriminating tests. |
| 7 | Independent transport, resistance, and regulation adjudications; direction/substrate/mechanism/operon holds; no proximity-to-function leap; no exact-bound evidence distinguished from biological absence. |
| 8 | KCB, MIBiG, ClusterBlast, and named comparator convergence/conflict; gene coverage and core-versus-generic-flank distinction; similarity never identity. |
| 9 | At least two locus-specific alternatives when evidence permits; strongest rival model; observations that discriminate each model. |
| 10 | Fragment/co-capture/overmerge risks; exact edge distances; partner-locus possibilities; RG-GMCI claim ceiling; no physical join without nucleotide proof. |
| 11 | Product-family capacity model from core grammar; exact compound held unless independently established; comparator conflicts retained. |
| 12 | Bee/microbe context from verified strain metadata and prevalence; chitin/ecology signals treated as strain context unless exact-locus coupled. |
| 13 | Class-level antibacterial/antifungal relevance; extract phenotype separated from locus attribution; literature claim and organism scope explicit. |
| 14 | Explicit forbidden claims: exact product, production, activity attribution, novelty, ecological function, physical linkage, and expression as applicable. |
| 15 | Typed remaining gaps only after accessible sources are searched; distinguish unavailable, unbound, not run, running, ingest gap, measured-none, and not applicable. |
| 16 | Current BLASTp/HMM/domain evidence plus only unresolved next tests; later nr/ClusteredNR additions are versioned, additive updates rather than a card-wide blocker. |
| 17 | Testable LC-MS/fermentation implications derived from the conditional product-family model; no predicted mass asserted as detected. |
| 18 | Lossless future-map payload requirements: every displayed gene, label, coordinates, strand, domains, selected genes, named matches and holds; V7 comparator preserved. Rendering remains a separate gate. |
| 19 | One integrated judgment and cross-cohort synthesis, preserving support, contradictions, strongest alternative, confidence, final claim ceiling and unresolved discriminating evidence. No publication-ready claim from mechanical checks. |
| 20 | Prioritized bounded actions with decision rules and owners; accessible evidence is obtained/reconciled rather than labeled pending. |
| 21 | For RiPP/NRPS-relevant loci, conditional precursor/monomer ladder with assumptions; otherwise reasoned not-applicable. |
| 22 | RiPP search scope, databases, precursor/maturation evidence and negative-result ceiling; otherwise reasoned not-applicable. |
| 23 | Heterologous-expression rationale, minimum construct and controls, host limitations, and result interpretation; otherwise reasoned not-applicable. |
| 24 | Novelty evidence decomposed into architecture, homology, cohort prevalence and comparator distance; “no hit” is not novelty. |
| 25 | Exact genomic-neighborhood conservation from ClusterBlast/current comparisons; core versus generic conserved context distinguished. |
| 26 | OSMAC plan tied to plausible pathway regulation/product chemistry and measurable outcomes; otherwise reasoned not-applicable. |
| 27 | Mechanism-specific self-resistance evidence, exact gene coupling, alternatives and required validation; broad transporter/family names are insufficient. |
| 28 | Claim-by-claim provenance; 14-stream disposition table; historical source-loss table; 50-row section reconciliation matrix. |
| 29 | Cross-cluster hypotheses with exact four-part partner identities, evidence state and physical-linkage ceiling; otherwise reasoned not-applicable. |
| 30 | Branching experimental decision tree: question, experiment, positive/negative decision rule, and program consequence. |
| 31 | Exact region CDS census plus boundary-context census; independently reconciled denominators; no denominator-difference identity failure. |
| 32 | Assembly-line enzyme/domain inventory from measured architecture; absent modules distinguished from unmeasured modules. |
| 33 | Module programming, substrate/extension/reduction logic and uncertainty; no collinearity assumption without support. |
| 34 | Initiation/loading and release/cyclization logic, candidate genes, alternatives and missing functions. |
| 35 | Per-protocluster decomposition for mixed/overmerged regions; each core and accessory set assigned or held separately. |
| 36 | Boundary, overmerge and locus-splitting adjudication integrated with exact intervals and sequence/CDS evidence. |
| 37 | Partner/accessory proteins classified as direct, plausible, broad context, or unbound; mechanism and coupling evidence stated. |
| 38 | Resistance/efflux signals with exact locus, mechanism specificity, direction, coupling and phenotype ceiling. |
| 39 | Cross-strain identity/coverage on exact orthologous genes/loci with denominators and channels; no alias-only comparison. |
| 40 | BiG-SCAPE family, cutoff, run receipt, cohort/reference membership and private/shared scope; new run may update additively. |
| 41 | Protein/domain phylogeny target, sequence binding, reference set, model limits and supported clade-level inference. |
| 42 | HGT/composition evidence relative to a declared genomic baseline; mobile/context alternatives; GC deviation alone is insufficient. |
| 43 | RG-GMCI/cross-contig candidates with exact partner identity, component signals and explicit “candidate, not nucleotide join” ceiling. |
| 44 | Within-cohort prevalence with exact numerator/denominator, profile/class definition and governed exclusions. |
| 45 | Supervisor/university cohort comparison with declared cohort, comparable denominator and source receipt; otherwise reasoned not-applicable. |
| 46 | Type/reference-strain comparison on exact comparable loci and genes, including Mamey/antiSMASH profile compatibility and divergence. |
| 47 | Host-matched unrelated reference comparison with verified host metadata, comparator rationale and transfer limits. |
| 48 | Biosynthetic gene, domain and machinery citations with explicit relevance to named genes, domain logic, alternatives or experiments; source scope and limits of transfer stated. |
| 49 | Genus secondary-metabolite and broader biological-context citations with explicit relevance; justify broader taxa/topics and distinguish reference phenotype from focal-strain evidence. |
| 50 | Complete contiguous named-match table formerly in §4, with unchanged full gene roster, geometry, protein binding, channel separation, result/admission states and typed holds. |
