# Expanded Mode B publication-candidate contract (§1–§50)

This contract governs scientific card authoring and audit. Mamey still performs deterministic
extraction; Sapote/Codex/Claude perform interpretation. Passing the deterministic scaffold means
only that the evidence is presented for scientific review. It does not establish product identity,
production, activity, novelty, owner acceptance, integration, rendering approval, release, or
publication approval.

## Gate timing and authoring route

The template emitter and publication gate serve different lifecycle stages. A fresh
`emit-modeb-template` result is an **unfilled authoring scaffold** and is expected to retain
publication findings. It must pass the structure gate, but it is not required—or permitted—to
claim publication completeness before an author reviews and fills the evidence-dependent cells.

Use this route:

1. emit the current §1–§50 scaffold;
2. freeze and bind the exact-locus evidence packet;
3. replace every prompt and placeholder, including the §50 channel matrix and all §28 disposition
   rows, using bare typed states from the closed vocabularies below;
4. save the authored candidate to disk; and
5. run the publication gate against those saved bytes and the independently bound gene roster.

Do not run the publication gate against a fresh template and interpret its expected placeholder
findings as an emitter failure. Conversely, do not call an authored card publication-gate-clean
until the actual saved candidate returns zero findings. See `MODEB_GATE_CLEAN_AUTHORING.md` for the
operational recipe.

## Identity and source rules

Every individual locus is displayed as:

`strain / full node-or-contig / region / BGC alias`

The filesystem-safe filename must contain all four fields. The alias is display metadata and is
never a join key. Bind on exact assembly plus full node/contig plus region interval/sequence and CDS
roster. Quarantine incomplete or conflicting identities.

For every gene-level join, the normalized amino-acid sequence SHA-256 is the positive identity key.
Protein length is rejection-only: a length mismatch rejects a join, while a length match never proves
one. If the same protein hash occurs more than once in the admitted comparison corpus, expand an
ordered neighborhood signature from adjacent protein hashes until the locus is unique, and preserve
the smallest sufficient radius plus the corpus receipt. A BLASTp result is admitted only when the
query protein hash, exact physical locus, channel/database, and result-job receipt all bind. Label-only,
alias-only, length-only, or result-without-query-receipt rows remain visible as `OBSERVED_UNBOUND` or
`QUARANTINED`; they are not silently discarded and their percentages are not quoted as exact-current
evidence.

Before writing, open the predecessor card, V7 evidence, historical locus map, exact antiSMASH GBK,
and current sealed Mamey package. A successor may refine or withdraw earlier content, but it may not
silently omit it. Every section has a reconciliation row with named evidence and one predecessor
disposition: `RETAIN`, `REFINE`, `WITHDRAW_WITH_REASON`, or `NOT_APPLICABLE`.

## Complete §50 table

Use one contiguous Markdown table: header, separator, then the first data row on the immediately
following physical line. Exactly one row is required for every exact-region and boundary-context
gene in the independently supplied displayed-gene roster. Preserve coordinates, strand, protein
length, antiSMASH function/domains, and separate named-match cells for nr, ClusteredNR, Swiss-Prot,
and MIBiG where available. Each hit states accession, full matched-protein name, organism, identity,
positives/similarity, and query coverage. The table or its exact machine-readable source also states
the protein SHA-256 or binding-register key, observed-result state, admission state, and typed hold.
`qcov NR` means not reported, never zero. ClusteredNR is not full nr. Missing/unbound evidence uses a
typed state and is not biological absence. Observed and admitted channel counts are reported
separately.

## Section-specific scientific requirements

| § | Minimum substantive content |
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

## Required supporting-stream disposition

Account separately for antiSMASH, sealed Mamey, MIBiG, BiG-SCAPE, ClusterBlast, RG-GMCI,
chitin, resistance, domain rarity, literature, prevalence, historical card, V7 evidence, and current
channel-separated BLASTp. Each uses exactly one state: `ADMITTED`, `CONTEXT_ONLY`, `UNBOUND`,
`ABSENT_IN_SCOPE`, or `SUPERSEDED`, plus a sentence saying how it changes—or does not change—the
interpretation.

## Readiness authority

Deterministic checks may report `STRUCTURE_VALIDATED`, `EVIDENCE_MATRIX_VALIDATED`, or a typed hold.
They may not assign owner acceptance, integration, rendered/visual-QA status, release approval, or
publication approval. Those remain distinct external gates.

## Citation relevance and migration

Each §48/§49 entry supplies an identifiable citation and direct DOI/PMID/publisher link, what the source supports, its relevance to the focal locus, and its transfer limits. State abstract-only versus full-text consultation. Prefer primary sources for mechanistic claims; label reviews as synthesis. No arbitrary citation quota, invented references, or generic relevance filler. A paper may appear in both sections only with distinct relevance. Broader taxa/topics are permitted when justified.

Migrate the former §48 synthesis into §19 without loss and the former §4 matrix into §50 without duplication. Update navigation, anchors, section reconciliation and layout consumers together. Legacy 48-section cards remain readable as legacy; do not silently reinterpret their §48. This document change alone does not migrate emitters, gates or parsers.
