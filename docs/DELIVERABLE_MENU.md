# The Sapote-Mamey Diner Menu

*Choose by label, name, or plain-language request. This document is generated from `mamey/data/deliverables_registry.json`; do not edit it by hand.*

**Bundle:** Sapote-Mamey v9.7.428  
**Engine:** Mamey 1.9.163  
**Required exact-locus display:** `strain / full node-or-contig / region / BGC alias`

> Similarity is not identity; capacity is not production; missing or unbound evidence is not biological absence. Gate success verifies encoded checks, not biological identity, activity, novelty, acceptance, or publication readiness.

## Availability language

- **DETERMINISTIC_BUILT_IN** — Produced by bundled deterministic code from admitted inputs.
- **OPTIONAL_LOCAL_ADAPTER** — Available only when the named local tool, database, or result is present and admitted.
- **POST_SEAL_JUDGMENT** — A Sapote judgment deliverable built after MAMEY_COMPLETE; it is not deterministic Mamey extraction.
- **OPTIONAL_EXTERNAL_WORKFLOW** — May require separately authorized external contact; staging alone does not authorize contact.
- **GOVERNANCE_AND_QA** — A validation, provenance, privacy, handoff, or release-control outcome.
- **HUMAN_REVIEW_PROTOCOL** — A structured human/LLM review protocol rather than an engine-generated scientific result.

Run `python mamey_run.py deliverables availability ...` for a local, read-only preflight. A listed external workflow is never authorization to contact it.

## The Counter - quick orientation

### #1 — Triage Board

*What biosynthetic capacity is in this strain?*

Ranked, source-derived BGC inventory with class calls, routing priors, evidence states, and complete physical locators.

- **Delivery class:** `DETERMINISTIC_BUILT_IN`
- **Commands:** `run`, `explore`, `explain`
- **Required inputs:** `antismash_zip`
- **Optional evidence/resources:** `admitted_companion_evidence`
- **Outputs:** `sealed_package`, `triage_board`
- **Gates:** `validate`
- **Ask for:** “Give me the triage board”; “What BGCs are in this strain?”
- **Claim ceiling:** Routing priority and biosynthetic-capacity hypothesis only.

### #2 — Lead Sheet

*Which loci deserve attention first?*

A short, evidence-weighted lead board that names why each exact locus was prioritized and what remains unresolved.

- **Delivery class:** `POST_SEAL_JUDGMENT`
- **Commands:** `lead-pages`, `good-guesses`
- **Required inputs:** `sealed_package`
- **Optional evidence/resources:** `admitted_blastp`, `admitted_bigscape`, `admitted_mibig`
- **Outputs:** `lead_pages`, `lead_board`
- **Gates:** `workflow`
- **Ask for:** “Give me the lead sheet”; “What are the top leads?”
- **Claim ceiling:** Prioritization, not product identity, production, or activity.

### #3 — Layered BGC Guide

*Explain a locus to both non-specialists and specialists.*

A layered lay-to-technical per-gene guide with structure, function, evidence-channel separation, and explicit holds.

- **Delivery class:** `POST_SEAL_JUDGMENT`
- **Commands:** `guide`, `verify-guide`
- **Required inputs:** `sealed_package`, `exact_locus_identity`
- **Optional evidence/resources:** `admitted_blastp`
- **Outputs:** `bgc_guide`
- **Gates:** `verify-guide`, `verify-citations`
- **Ask for:** “Write a layered guide for this exact locus”
- **Claim ceiling:** Gene-role interpretation remains evidence-weighted and conditional.

### #4 — Locus Map and Atlas

*Show the physical gene neighborhood.*

Gene-arrow or contig-level views with complete locus identity, visible label-denominator disclosure, and source-data sidecars.

- **Delivery class:** `OPTIONAL_LOCAL_ADAPTER`
- **Commands:** `figures diagram`, `figures atlas`, `render-figures`
- **Required inputs:** `sealed_package`, `figure_stack`
- **Optional evidence/resources:** `source_gbk`
- **Outputs:** `locus_map`, `figure_data_sidecar`
- **Gates:** `validate`
- **Ask for:** “Make a locus map for STRAIN-001 / NODE_12_length_48000_cov_30.1 / region001 / BGC007”
- **Claim ceiling:** Physical organization and annotation display; not proof of pathway operation.

## The Evidence Bar - bind before interpreting

### E1 — Mode B Evidence Availability

*Which evidence is physically present and exactly bound before prose?*

A pre-authoring manifest that separates available, admitted, unbound, absent-in-scope, and superseded evidence streams.

- **Delivery class:** `GOVERNANCE_AND_QA`
- **Commands:** `modeb-availability`
- **Required inputs:** `sealed_package`, `exact_locus_identity`
- **Optional evidence/resources:** `source_gbk`, `evidence_receipts`
- **Outputs:** `modeb_availability_manifest`
- **Gates:** `modeb-availability`
- **Ask for:** “Audit Mode B evidence availability before authoring”
- **Claim ceiling:** Availability and binding state only; missing evidence is not a biological negative.

### E2 — Targeted Protein Evidence

*What do the most informative proteins resemble?*

Target selection, FASTA staging, result import, and channel-separated availability for full nr, ClusteredNR, and pinned local Swiss-Prot.

- **Delivery class:** `OPTIONAL_LOCAL_ADAPTER`
- **Commands:** `bgc-blastp-panel`, `modeb-blastp`, `ingest-blastp`, `blastp-availability`
- **Required inputs:** `exact_locus_identity`, `exact_protein_sequences`
- **Optional evidence/resources:** `local_swissprot`, `imported_blastp_results`
- **Outputs:** `targeted_fasta`, `blastp_channel_matrix`, `blastp_availability`
- **Gates:** `blastp-availability`
- **Ask for:** “Build the targeted protein evidence panel”
- **Claim ceiling:** Named sequence similarity with explicit denominators; never identity or function by resemblance alone.

### E3 — Optional External BLASTP Workflow

*Prepare or run an explicitly authorized remote protein search.*

A separately governed remote-search workflow. FASTA preparation does not itself authorize submission, polling, or URL access.

- **Delivery class:** `OPTIONAL_EXTERNAL_WORKFLOW`
- **Commands:** `blastp-online`, `blastp-ebi`, `blastp-round`
- **Required inputs:** `exact_protein_sequences`, `external_contact_authorization`
- **Optional evidence/resources:** None
- **Outputs:** `remote_blastp_receipt`, `importable_results`
- **Gates:** `blastp-status`
- **Ask for:** “Run the authorized external BLASTP workflow”
- **Claim ceiling:** Remote similarity evidence only; authorization is per transaction.

### E4 — MIBiG, ClusterBlast, and BiG-SCAPE Context

*How does this exact locus compare with reference clusters and the cohort?*

Keeps source-local ClusterBlast, gene-level MIBiG anchors, whole-locus majority reads, and cutoff-specific BiG-SCAPE families distinct.

- **Delivery class:** `OPTIONAL_LOCAL_ADAPTER`
- **Commands:** `majority-read`, `bigscape`, `figures gcf-network`
- **Required inputs:** `sealed_package`
- **Optional evidence/resources:** `mibig_rows`, `clusterblast_rows`, `bigscape_local`
- **Outputs:** `reference_context`, `gcf_context`, `comparator_limits`
- **Gates:** `workflow`
- **Ask for:** “Reconcile MIBiG, ClusterBlast, and BiG-SCAPE evidence”
- **Claim ceiling:** Comparator navigation and family context; class discordance cannot support product identity or novelty.

### E5 — Phylogenomics Context

*What is the approved genome-scale comparator context?*

Approval-gated GToTree/IQ-TREE/ANI context with explicit outgroups, tip cleaning, and source receipts.

- **Delivery class:** `OPTIONAL_LOCAL_ADAPTER`
- **Commands:** `phylo-run`, `clade-deepdive`
- **Required inputs:** `phylogenomics_local`, `approved_compute_plan`
- **Optional evidence/resources:** `ani_inputs`, `bigscape_local`
- **Outputs:** `phylogeny_context`, `ani_context`, `signoff_receipt`
- **Gates:** `signoff`
- **Ask for:** “Build the approved phylogenomics context”
- **Claim ceiling:** Comparator placement and nucleotide/protein similarity; taxonomy and novelty require their own admitted evidence.

## Full Meals - integrated analysis

### #5 — Mode B 48-Section Deep Dive

*What does all admitted evidence support for one exact locus?*

A complete 48-section, gene-oriented evidence reconciliation with alternatives, discriminating tests, typed holds, and loss audit.

- **Delivery class:** `POST_SEAL_JUDGMENT`
- **Commands:** `modeb-availability`, `mode-b`, `modeb-compile`, `verify-modeb`, `verify-citations`
- **Required inputs:** `sealed_package`, `exact_locus_identity`, `canonical_protein_roster`, `authored_judgment`
- **Optional evidence/resources:** `admitted_blastp`, `admitted_bigscape`, `admitted_mibig`, `phylogenomics_context`
- **Outputs:** `modeb_48_card`, `source_loss_audit`, `future_map_payload`
- **Gates:** `verify-modeb`, `verify-citations`, `claim-safety`
- **Ask for:** “Write full Mode B for STRAIN-001 / NODE_12_length_48000_cov_30.1 / region001 / BGC007”
- **Claim ceiling:** Candidate interpretation only unless separately accepted; capacity is not production.

### #6 — Full Strain Analysis

*Integrate extraction, lead interpretation, figures, and next actions for one strain.*

A governed compilation of the sealed package and independently gated post-seal deliverables; unavailable components remain typed rather than silently omitted.

- **Delivery class:** `POST_SEAL_JUDGMENT`
- **Commands:** `compile-report`, `workflow`, `report-card`
- **Required inputs:** `sealed_package`, `authored_judgment`
- **Optional evidence/resources:** `figure_stack`, `admitted_companion_evidence`
- **Outputs:** `compiled_report`, `workflow_ledger`
- **Gates:** `workflow`, `validate`
- **Ask for:** “Build the full strain analysis”
- **Claim ceiling:** Compilation does not raise the authority of its component evidence.

### #7 — Split-Pathway and Assembly-Line Reconstruction

*Could measured biosynthetic capacity span boundaries or multiple regions?*

RG-GMCI, protocluster, over-merge, and domain-architecture views with explicit physical-linkage limits and alternative assignments.

- **Delivery class:** `POST_SEAL_JUDGMENT`
- **Commands:** `rggmci-widget`, `assembly-line-widget`, `split-overmerge-cards`, `overmerge-widgets`
- **Required inputs:** `sealed_package`, `exact_locus_identity`
- **Optional evidence/resources:** `source_gbk`, `admitted_blastp`
- **Outputs:** `linkage_assessment`, `assembly_line_context`
- **Gates:** `workflow`
- **Ask for:** “Reconstruct the measured split pathway”
- **Claim ceiling:** Co-occurrence or linkage score is not proof of one biosynthetic product.

### #8 — Cohort and GCF Atlas

*What biosynthetic capacity is shared or strain-private across a governed cohort?*

Cross-strain synthesis, source-derived cohort tables, and cutoff-specific GCF context with denominator and comparator-composition limits.

- **Delivery class:** `OPTIONAL_LOCAL_ADAPTER`
- **Commands:** `cohort-precompute`, `cohort`, `cohort-figures`, `bigscape`
- **Required inputs:** `multiple_sealed_packages`
- **Optional evidence/resources:** `master_workbook`, `bigscape_local`, `figure_stack`
- **Outputs:** `cohort_tables`, `cohort_synthesis`, `gcf_atlas`
- **Gates:** `workflow`
- **Ask for:** “Build the cohort comparison”; “Build the cross-strain GCF atlas”
- **Claim ceiling:** Measured cohort prevalence and clustering only; sampling and cutoff choices bound interpretation.

## Sides - focused additions

### S1 — Domain and Tailoring Review

*Which measured domains and tailoring families change the pathway alternatives?*

Post-seal domain grammar, P450 context, and assembly-line enrichment kept separate from inferred reaction assignment.

- **Delivery class:** `OPTIONAL_LOCAL_ADAPTER`
- **Commands:** `domain-level`, `hmm-adjudicate`, `p450-tailoring`, `assembly-line`
- **Required inputs:** `sealed_package`
- **Optional evidence/resources:** `source_gbk`, `local_hmm_database`
- **Outputs:** `domain_evidence`, `tailoring_context`
- **Gates:** `workflow`
- **Ask for:** “Add the domain and tailoring review”
- **Claim ceiling:** Domain capacity and architecture; reaction assignment remains conditional.

### S2 — Reference-Dark and Novelty Shortlist

*Which genes or loci remain poorly anchored to admitted references?*

Reference-dark and novelty-routing views that preserve missing-channel and comparator-coverage limitations.

- **Delivery class:** `POST_SEAL_JUDGMENT`
- **Commands:** `reference-dark`, `novelty-shortlist`, `comparator-coverage`
- **Required inputs:** `sealed_package`
- **Optional evidence/resources:** `admitted_blastp`, `admitted_mibig`, `bigscape_local`
- **Outputs:** `reference_dark_report`, `novelty_shortlist`
- **Gates:** `claim-safety`
- **Ask for:** “Show the reference-dark genes and novelty shortlist”
- **Claim ceiling:** Reference darkness is not novelty; missing evidence is not biological absence.

### S3 — Figure Set and Comparative Clinker

*Create source-backed visuals without changing the scientific verdict.*

Data-sidecar-backed figures, BGC diagrams, GCF networks, and comparative Clinker views generated after the package seal.

- **Delivery class:** `OPTIONAL_LOCAL_ADAPTER`
- **Commands:** `render-figures`, `cohort-figures`, `figures clinker`, `figures gcf-network`
- **Required inputs:** `figure_stack`
- **Optional evidence/resources:** `sealed_package`, `bigscape_local`, `source_gbk`
- **Outputs:** `figures`, `figure_data_sidecars`, `clinker_html`
- **Gates:** `validate`
- **Ask for:** “Build the source-backed figure set”
- **Claim ceiling:** Visualization of admitted measurements; figures do not upgrade inference.

### S4 — Local Literature Context

*What does the pinned local literature corpus say about the named families?*

Offline lookup and search over the bundled corpus, followed by claim-level citation adjudication in Sapote judgment.

- **Delivery class:** `OPTIONAL_LOCAL_ADAPTER`
- **Commands:** `literature lookup`, `literature search`
- **Required inputs:** `local_literature_corpus`
- **Optional evidence/resources:** `authored_judgment`
- **Outputs:** `literature_context`
- **Gates:** `claim-safety`
- **Ask for:** “Search the local literature corpus for this enzyme family”
- **Claim ceiling:** Literature supplies family or comparator context unless exact experimental identity is independently established.

### S5 — Bench Planning Matrix

*What experiments would discriminate the leading pathway alternatives?*

A judgment-layer fermentation, detection, metabolomics, and wet-lab decision matrix tied to explicit hypotheses and uncertainties.

- **Delivery class:** `POST_SEAL_JUDGMENT`
- **Commands:** None
- **Required inputs:** `authored_judgment`, `exact_locus_identity`
- **Optional evidence/resources:** `measured_activity`, `metabolomics`
- **Outputs:** `bench_planning_matrix`
- **Gates:** `claim-safety`
- **Ask for:** “Build a hypothesis-linked bench planning matrix”
- **Claim ceiling:** Experimental planning, not evidence that a compound is produced or active.

## The Check - provenance, QA, and handoff

### G1 — Workflow and Evidence Receipt

*Which required stages passed, remain pending, or are blocked?*

A machine-readable Sapote workflow ledger and additive evidence-receipt ingestion without mutating the sealed extraction package.

- **Delivery class:** `GOVERNANCE_AND_QA`
- **Commands:** `workflow`, `ingest-receipts`
- **Required inputs:** `sealed_package`
- **Optional evidence/resources:** `evidence_receipts`, `authored_deliverables`
- **Outputs:** `workflow_ledger`, `receipt_registry`
- **Gates:** `workflow`, `validate`
- **Ask for:** “Show the workflow and evidence receipt status”
- **Claim ceiling:** Process state and provenance only.

### G2 — Claim and Citation Audit

*Does the authored interpretation stay within its evidence and identity contract?*

Post-hoc claim-safety, complete-locus citation, and authored-content gates over finished files.

- **Delivery class:** `GOVERNANCE_AND_QA`
- **Commands:** `claim-safety`, `verify-citations`, `verify-modeb`, `verify-guide`
- **Required inputs:** `authored_deliverables`
- **Optional evidence/resources:** `sealed_package`
- **Outputs:** `gate_findings`
- **Gates:** `claim-safety`, `verify-citations`
- **Ask for:** “Audit the claims and exact-locus citations”
- **Claim ceiling:** Mechanical and encoded semantic checks; not scientific acceptance.

### G3 — Reproducible Handoff

*Can another operator identify the exact inputs, outputs, and resume point?*

Fingerprints, manifests, durable state, and a portable handoff that preserves source identity and unresolved holds.

- **Delivery class:** `GOVERNANCE_AND_QA`
- **Commands:** `fingerprint`, `handoff`, `resume`
- **Required inputs:** `sealed_package`
- **Optional evidence/resources:** `authored_deliverables`
- **Outputs:** `fingerprint`, `handoff_bundle`, `resume_state`
- **Gates:** `validate`
- **Ask for:** “Build the reproducible handoff”
- **Claim ceiling:** Reproducibility and custody only; no acceptance or release implication.

### G4 — Release QA and Privacy Review

*Is a candidate mechanically ready for an authorized release decision?*

Release checks, privacy-tier controls, and sign-off receipts. Passing does not grant release authority.

- **Delivery class:** `GOVERNANCE_AND_QA`
- **Commands:** `release-qa`, `signoff`
- **Required inputs:** `candidate_bundle`
- **Optional evidence/resources:** `privacy_policy`, `review_receipts`
- **Outputs:** `release_qa_receipt`, `signoff_receipt`
- **Gates:** `release-qa`, `signoff`
- **Ask for:** “Run candidate release QA”
- **Claim ceiling:** Mechanical candidate readiness only; owner approval remains separate.

### G5 — Adversarial Patch Review

*What breaks, conflicts, or remains unproven in a proposed change?*

A bounded source-first review protocol for patch applicability, conflicts, tests, provenance, and claim ceilings.

- **Delivery class:** `HUMAN_REVIEW_PROTOCOL`
- **Commands:** None
- **Required inputs:** `immutable_baseline`, `patch_payload`
- **Optional evidence/resources:** `prior_review_receipts`
- **Outputs:** `patch_card`, `independent_findings`, `application_receipt`
- **Gates:** `zero_fuzz_apply`, `named_tests`
- **Ask for:** “Run an adversarial patch review”; “Can we Bunny Hop?”
- **Claim ceiling:** Review recommendation only; no integration, acceptance, or release authority.

## How to order safely

For a single locus, always provide the complete identity in this order:

`strain / full node-or-contig / region / BGC alias`

If an input or adapter is unavailable, the correct result is a typed workflow state—not an invented biological negative and not a silent omission.

---

*Generated from the shipped registry. Gate success is not owner acceptance, release approval, or publication readiness.*
