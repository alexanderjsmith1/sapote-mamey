# Mode B gene-first and 48-section manual

*Current to bundle v9.7.405 · engine Mamey 1.9.145. Authored by Codex (Wiki Revision 03, 2026-08-31) against v9.7.395; admitted to the bundle wiki at v9.7.405 by the Claude Code patch lane after a currency pass. Documentation only — confers no scientific, release, or publication authority; class-level hypotheses, judgment deferred.*

This page does not replace the machine contract, create a Mode B card, or confer scientific, integration, release, or publication authority.

## What Mode B is

Mode B is the evidence-bound interpretation layer used after a Mamey package has been sealed. Mamey supplies deterministic evidence objects and routing priors. Mode B evaluates one exact locus, preserves competing explanations, and records what the evidence permits and forbids.

The complete identity for an individual locus is always:

`strain / full node-or-contig / region / BGC alias`

The four fields appear in that order in prose, headings, filenames, tables, ledgers, receipts, and figure metadata. The alias is secondary. A missing, shortened, ambiguous, or conflicting field causes a hold; it is never guessed.

Protein-level joins add a normalized amino-acid SHA-256. A matching label or length is not a positive identity key. A length mismatch can reject a join, while a length match alone cannot admit one.

## Gene-first comes before card authoring

Gene-first exploration is a bounded inspection step, not a smaller Mode B card. Use it when the locus needs focused review before prose is authored.

The safe order is:

1. Validate the sealed package and read its manifest and gate receipt.
2. Inventory evidence with `modeb-availability`; keep exact-locus, alias-bound, strain-only, unbound, and absent-in-scope observations distinct.
3. Freeze the canonical gene roster in genomic order, including exact-region and admitted boundary-context genes.
4. Stage protein and domain evidence offline with query, database, run, and output receipts.
5. Run `modeb-gene-first` for the one complete locus when focused exploration is needed.
6. Review its synthesis, important-gene inspection order, separate channel states, and single next-analysis route.
7. Only then author the current 48-section card. One locus must pass its structure and evidence gates before scaling.
8. Run the applicable structure, citation, claim-safety, and publication-candidate gates against the saved authored bytes.
9. Ingest an accepted judgment receipt additively. Do not modify deterministic package outputs.

`modeb-gene-first` composes already sealed or explicitly indexed evidence. It does not search a workspace, contact a service, perform biological inference, author card prose, render a figure, or establish a final ranking.

## Current Full Mode B contract

The current machine schema is `modeb_corrective_full48_v1`. An unqualified **Full Mode B** card uses `FINISHED_FULL48_CURRENT_EVIDENCE`: sections 1 through 48 appear exactly once and in order. A conditional or evidence-limited section remains present with a reasoned `NOT_APPLICABLE` or typed hold; it is not omitted.

The 1-8 form is legacy compact/core-spine language. The 1-30 form is a legacy candidate/calibration profile. Neither is unqualified Full Mode B.

| § | Canonical title | Minimum role in the current profile |
|---:|---|---|
| 1 | Identity and node/region | Complete four-part identity and physical binding. |
| 2 | Why this BGC was selected | Evidence-based selection rationale; routing is not truth. |
| 3 | Boundary and assembly status | Geometry, exact/context denominators, truncation and overmerge limits. |
| 4 | Gene-by-gene interpretation | Complete canonical roster with channel-separated evidence and narrative interpretation. |
| 5 | Core biosynthetic logic | Committed steps, minimal gene set, alternatives, and on-contig completeness. |
| 6 | Tailoring and maturation logic | Direct candidates separated from broad context and missing functions. |
| 7 | Transport, resistance, and regulation | Three independent adjudications with coupling and mechanism holds. |
| 8 | Comparator/KCB interpretation | Comparator convergence and conflicts; similarity never identity. |
| 9 | Alternative hypotheses | Strong rival models and discriminating observations. |
| 10 | Fragmentation and co-capture risks | Edge distances, co-capture, overmerge, partner possibilities, and no-join ceiling. |
| 11 | Product-family interpretation | Class or family capacity model; exact compound held. |
| 12 | Bee/microbe ecological interpretation | Verified strain context; no unlinked locus attribution. |
| 13 | Antibacterial/antifungal relevance | Class-level relevance separated from measured strain or material phenotype. |
| 14 | What cannot be claimed | Explicit prohibited identity, production, activity, novelty, linkage, and expression claims. |
| 15 | Missing evidence | Typed gaps after available sources are accounted for. |
| 16 | BLASTP/HMMER next steps | Current evidence plus only unresolved bounded tests. |
| 17 | LC-MS / fermentation implications | Testable implications, not asserted detections. |
| 18 | Figure/locus-map notes | Lossless future-map payload; rendering remains a separate gate. |
| 19 | Final Mode B judgement | Supported capacity, strongest alternative, confidence, and exact ceiling. |
| 20 | Next actions | Prioritized actions with decision rules and owners. |
| 21 | Precursor mass ladder | RiPP/NRPS-relevant conditional ladder or reasoned not-applicable. |
| 22 | RiPP database search | Search scope and negative-result ceiling or reasoned not-applicable. |
| 23 | Heterologous expression | Construct, controls, limits, and decision rules or reasoned not-applicable. |
| 24 | Scaffold novelty score | Decomposed architecture, homology, prevalence, and comparator distance; no-hit is not novelty. |
| 25 | Genome neighbourhood | Exact conservation and core-versus-generic context. |
| 26 | OSMAC protocol | Regulation/chemistry-linked plan or reasoned not-applicable. |
| 27 | Self-resistance assessment | Mechanism-specific evidence and validation, not transporter-name inference. |
| 28 | Evidence provenance ledger | Claim-by-claim source tracing and all-stream disposition. |
| 29 | Cross-cluster interactions | Complete partner identities, evidence state, and physical-linkage ceiling. |
| 30 | Experimental decision tree | Question, experiment, positive/negative rule, and program consequence. |
| 31 | Region CDS census | Exact-region and boundary-context census with reconciled denominators. |
| 32 | Assembly-line inventory | Measured domains/modules; absent distinguished from unmeasured. |
| 33 | Module programming readout | Programming logic and uncertainty; no unsupported collinearity. |
| 34 | Initiation & release logic | Loading, release/cyclization candidates, alternatives, and gaps. |
| 35 | Protocluster decomposition | Per-system core/accessory assignment for mixed or overmerged regions. |
| 36 | Boundary status + overmerge/locus-splitting adjudication (merged) | Within-locus boundary and splitting decision from intervals, sequence, and CDS evidence. |
| 37 | Partner & accessory proteins | Direct, plausible, broad-context, or unbound classification. |
| 38 | Co-located resistance & efflux | Exact mechanism, direction, coupling, and phenotype ceiling. |
| 39 | Cross-strain sequence identity | Exact genes/loci, identity/coverage, denominators, and channels. |
| 40 | BiG-SCAPE family / cohort placement | Explicit run, cutoff, family namespace, membership, and scope. |
| 41 | Protein / domain phylogeny | Sequence-bound target, references, model limits, and clade-level ceiling. |
| 42 | Horizontal transfer evidence | Declared genomic baseline plus mobile/context alternatives. |
| 43 | Split-pathway / cross-contig (RG-GMCI) | Exact partner identity and component signals; candidate, not nucleotide join. |
| 44 | Within-cohort prevalence & tier | Exact numerator, denominator, definition, and exclusions. |
| 45 | Supervisor / university cohort comparison | Declared comparable cohort and source receipt. |
| 46 | Type / reference strain comparison | Profile-compatible exact loci and genes with divergence. |
| 47 | Host-matched unrelated reference | Verified host metadata, rationale, and transfer limits. |
| 48 | Cross-cohort synthesis & claim ceiling | Integrated support/conflict, final ceiling, and unresolved discriminating evidence. |

Mechanical checks may establish `STRUCTURE_VALIDATED`, `EVIDENCE_MATRIX_VALIDATED`, or a typed hold. They do not establish experimental adjudication, owner acceptance, figure approval, integration, release, or publication.

## Evidence channels never substitute for one another

Keep at least these evidence families separate throughout availability, gene-first exploration, §4, §16, §28, and receipts:

| Channel | Scope | Required caution |
|---|---|---|
| NCBI nr | Broad protein homology | Not ClusteredNR or local Swiss-Prot. |
| ClusteredNR | Clustered protein homology | Not a proxy for full nr. |
| Local Swiss-Prot | Curated local snapshot | Snapshot identity and database hash required. |
| MIBiG / KnownClusterBlast | Characterized-cluster similarity | Similarity is not product identity. |
| ClusterBlast | Neighborhood similarity | Conserved context is not pathway equivalence. |
| BiG-SCAPE | Family placement under an explicit run/cutoff | No newest-run or directory-order inference. |
| RG-GMCI | Cross-contig candidate linkage | Candidate linkage is not a physical join. |
| Cohort comparison | Prevalence or sequence context under a governed denominator | No silent cohort or engine mixing. |
| Domain / HMM | Profile or architecture evidence | A profile call is capacity evidence, not expression or activity. |
| Literature | Published class/component context | Citation scope does not localize a phenotype to the locus. |

Historical cards use a separate `historical_card` channel and `LEAD_ONLY`. They can direct review but cannot contribute evidence support, ranking, currentness, or acceptance.

Missing, unbound, unavailable, not-run, and measured-zero are different states. A gap in one channel is never filled from another. Coverage denominators are reported per channel and are not summed.

## Offline protein and domain staging

The composer does not generate missing BLASTp or HMM evidence. Stage it before card authoring under an explicit local project root.

For every protein or domain result, retain:

- complete four-part locus identity;
- canonical locus tag and canonical roster membership;
- normalized amino-acid SHA-256 and length;
- channel and database/profile identity;
- database or profile snapshot SHA-256;
- tool name/version and material parameters or cutoffs;
- query-batch or run receipt;
- portable logical locator, output SHA-256, byte count, and admission state; and
- typed reason for `UNBOUND`, `MISSING`, or `NOT_RUN`.

Use local Swiss-Prot and local profile/HMM collections only when their exact snapshots are recorded. Offline nr or ClusteredNR output is admissible only when the query, database snapshot, and result receipt bind. A copied percentage, filename match, bare accession, or historical table is not enough.

For a finished current-evidence §4 matrix, each canonical gene has separate named-match and metric cells for nr, ClusteredNR, and local Swiss-Prot. Bound hits retain accession, complete matched-protein description, organism, percent identity, percent positives/similarity, and query coverage. `not reported` is not zero.

## `modeb-gene-first` contract

Use the bundle-local launcher and an existing additive output root:

```bash
python mamey_run.py modeb-gene-first \
  --package project/runs/SYNTH-001/package \
  --strain SYNTH-001 \
  --node NODE_7_length_120000_cov_42.5 \
  --region region002 \
  --bgc BGC007 \
  --evidence-index project/evidence/gene_first_index.tsv \
  --out project/explorations
```

The exact example identity is `SYNTH-001 / NODE_7_length_120000_cov_42.5 / region002 / BGC007`. It is synthetic.

The command validates the package identity, canonical gene table, evidence-index schema, channel states, locators, hashes, and collision state before creating output. It writes one complete-identity child directory containing:

- a concise exploration synthesis;
- a deterministic important-gene inspection table;
- a channel-separated availability table; and
- a content-addressed receipt.

The inspection order is role category, then count of bound gene channels, then coordinates and locus tag. It is not a biological-importance score. The output selects exactly one next analysis from a fixed information-gain route; that route is workflow triage, not scientific priority.

## Boundary, overmerge, and contig-rescue effects

These are three related but distinct questions.

| Question | Card location | What changes | What must not be inferred |
|---|---|---|---|
| Boundary/truncation | §§3, 10, 31, 36 | Completeness confidence, exact/context denominators, edge-distance reporting, and interpretation limits. | Edge status alone does not identify the missing pathway arm or prove that a partner exists. |
| Within-locus overmerge | §§10, 35, 36 | Decompose protoclusters, assign core/accessory genes per system, and interpret region-level KCB/length/counts cautiously. | One antiSMASH region is not automatically one coherent pathway or one product. |
| Cross-contig rescue | §§29, 43 | Record complete partner identities, RG-GMCI geometry/tiling, and a candidate-linkage ceiling. | Do not concatenate sequences, assert nucleotide adjacency, or call one physical pathway without nucleotide proof. |

Within-locus overmerge in §36 and cross-contig rescue in §43 remain separate adjudication paths. A large or mixed region can inflate region-level comparator signals. An RG-GMCI pair can be a useful navigation candidate while remaining unjoined. Figures and captions must preserve the same distinction.

## Stop boundary

Gene-first completion means the exact-locus review surface and its receipt were created. A 48-section structural pass means the saved card met the named mechanical gates. Neither state establishes that the biological model is correct, the card is owner-accepted, the figure is visually approved, or any artifact is integrated, released, or published.
