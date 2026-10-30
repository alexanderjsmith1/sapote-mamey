# Choose an output

Find the result you need below. Each entry lists its inputs and whether it needs extra tools, an external service or a written interpretation.

For the complete requirements and command names of the first entry, run from the bundle directory:

```bash
python mamey_run.py deliverables explain '#1'
```

Replace the example path with your antiSMASH ZIP, then check it for that entry:

```bash
python mamey_run.py deliverables availability '#1' --input-zip ~/Downloads/EXAMPLE.zip
```

Availability checks local files and tools; each output still needs its own input checks. Use another entry's label to inspect its requirements.

For a single locus, supply its complete identity: `strain / full node-or-contig / region / BGC alias`.

## Explore a strain

### #1 — Triage Board

A ranked BGC inventory with predicted classes and the location of each region.

- **You need:** antismash zip.
- **You get:** sealed package, triage board.
- **Work involved:** Built-in output.

### #2 — Lead Sheet

A short list of loci to investigate, with reasons for the ranking and open questions.

- **You need:** sealed package.
- **You get:** lead pages, lead board.
- **Work involved:** Requires interpretation and writing.

### #3 — Layered BGC Guide

A gene-by-gene explanation for general and specialist readers.

- **You need:** sealed package, exact locus identity.
- **You get:** bgc guide.
- **Work involved:** Requires interpretation and writing.

### #4 — Locus Map and Atlas

Gene-arrow maps and contig views, with source tables and complete locus labels.

- **You need:** sealed package, figure stack.
- **You get:** locus map, figure data sidecar.
- **Work involved:** Needs optional local tools or data.

## Inspect evidence

### E1 — Mode B Evidence Availability

A list of the evidence available for a locus and the files that still need checking.

- **You need:** sealed package, exact locus identity.
- **You get:** modeb availability manifest.
- **Work involved:** Checks and records.

### E2 — Targeted Protein Evidence

Protein selection, FASTA export and result import for nr, ClusteredNR and local Swiss-Prot searches.

- **You need:** exact locus identity, exact protein sequences.
- **You get:** targeted fasta, blastp channel matrix, blastp availability.
- **Work involved:** Needs optional local tools or data.

### E3 — Optional External BLASTP Workflow

A remote protein search. Review the sequence-upload plan and approve submission before contacting the service.

- **You need:** exact protein sequences, external contact authorization.
- **You get:** remote blastp receipt, importable results.
- **Work involved:** Uses an external service.

### E4 — MIBiG, ClusterBlast, and BiG-SCAPE Context

Reference comparisons from ClusterBlast, MIBiG and BiG-SCAPE, identified by method and scope.

- **You need:** sealed package.
- **You get:** reference context, gcf context, comparator limits.
- **Work involved:** Needs optional local tools or data.

### E5 — Phylogenomics Context

Genome trees and ANI comparisons using GToTree and IQ-TREE, with selected references and outgroups.

- **You need:** phylogenomics local, approved compute plan.
- **You get:** phylogeny context, ani context, signoff receipt.
- **Work involved:** Needs optional local tools or data.

### E6 — GECCO Class Cross-check

Compare antiSMASH regions with a separately installed GECCO 0.11 run. See [companion class evidence](COMPANION_CLASS_EVIDENCE.md).

- **You need:** sealed package, gecco local, biopython, source archive binding, gecco version 0 11 and tables.
- **You get:** gecco crosscheck sidecars, gecco only candidates, source and output receipt.
- **Work involved:** Needs optional local tools or data.

### E7 — Class-level Metabolomics Review Export

Export domain-based class hypotheses and a template for reviewing MS observations. See [companion class evidence](COMPANION_CLASS_EVIDENCE.md).

- **You need:** sealed package, biopython, source archive binding.
- **You get:** class hypotheses, source bound region gbk pointers, independent ms review template, source and output receipt.
- **Work involved:** Built-in output.

### E8 — Explicit Non-KS Second-proof Reader

Review candidate split loci using class-specific evidence and relative gene positions. See [companion class evidence](COMPANION_CLASS_EVIDENCE.md).

- **You need:** sealed package, admitted pair evidence.
- **You get:** policy recorded 4D advisory, two proof policy receipt.
- **Work involved:** Requires interpretation and writing.

## Build an interpretation

### #5 — Mode B 48-Section / Current50 v2 Deep Dive

Write a locus-specific interpretation after generating a template. Choose the default full48 or optional current50_v2 [profile](MODEB_PROFILE_MATRIX.md). The [50-section contract](MODEB_CURRENT50_V2_CONTRACT.md) and [expanded-locus guide](MODEB_EXPANDED_LOCUS.md) explain the additional requirements.

- **You need:** sealed package, exact locus identity, canonical protein roster, authored judgment.
- **You get:** modeb 48 card, modeb current50 v2 card, source loss audit, future map payload.
- **Work involved:** Requires interpretation and writing.

### #6 — Full Strain Analysis

Combine the package and completed interpretations into a strain report, listing any unfinished parts.

- **You need:** sealed package, authored judgment.
- **You get:** compiled report, workflow ledger.
- **Work involved:** Requires interpretation and writing.

### #7 — Split-Pathway and Assembly-Line Evidence Review

Compare candidate split pathways, merged regions and domain arrangements, including alternative explanations.

- **You need:** sealed package, exact locus identity.
- **You get:** linkage assessment, assembly line context.
- **Work involved:** Requires interpretation and writing.

### #8 — Cohort and GCF Atlas

Compare strains and gene-cluster families using the selected cohort and clustering cutoff.

- **You need:** multiple sealed packages.
- **You get:** cohort tables, cohort synthesis, gcf atlas.
- **Work involved:** Needs optional local tools or data.

## Add focused comparisons

### S1 — Domain and Tailoring Review

Review domain arrangements, tailoring enzymes and assembly-line organization.

- **You need:** sealed package.
- **You get:** domain evidence, tailoring context.
- **Work involved:** Needs optional local tools or data.

### S2 — Reference-Dark and Novelty Shortlist

Find loci with sparse reference matches for further investigation. Sparse matches alone do not establish novelty.

- **You need:** sealed package.
- **You get:** reference dark report, novelty shortlist.
- **Work involved:** Requires interpretation and writing.

### S3 — Figure Set and Comparative Clinker

Create BGC diagrams, family networks and comparative Clinker views with their source tables.

- **You need:** figure stack.
- **You get:** figures, figure data sidecars, clinker html.
- **Work involved:** Needs optional local tools or data.

### S4 — Local Literature Context

Search the bundled literature, then check the cited passages against the interpretation.

- **You need:** local literature corpus.
- **You get:** literature context.
- **Work involved:** Needs optional local tools or data.

### S5 — Bench Planning Matrix

Write a plan for observations that could distinguish competing pathway hypotheses.

- **You need:** authored judgment, exact locus identity.
- **You get:** bench planning matrix.
- **Work involved:** Requires interpretation and writing.

## Check and share work

### G1 — Workflow and Evidence Receipt

Check progress and import evidence records. By default, `workflow` writes a Markdown record inside the package; `ingest-receipts` writes Mode B cards into `judgment/` and updates the package's judgment register.

- **You need:** sealed package.
- **You get:** workflow ledger, receipt registry.
- **Work involved:** Checks and records.

### G2 — Claim and Citation Audit

Check completed interpretations for unsupported claims, missing citations and incomplete locus identities.

- **You need:** authored deliverables.
- **You get:** gate findings.
- **Work involved:** Checks and records.

### G3 — Portable package

Prepare a portable package with input/output identities and the point at which work can resume.

- **You need:** sealed package.
- **You get:** fingerprint, transfer ZIP, resume state.
- **Work involved:** Checks and records.

### G4 — Release QA and Privacy Review

Check a release candidate, privacy settings and review records. Release approval is a separate decision.

- **You need:** candidate bundle.
- **You get:** release qa receipt, signoff receipt.
- **Work involved:** Checks and records.

### G5 — Adversarial Patch Review

Review a proposed patch for conflicts, missing tests and unsupported conclusions.

- **You need:** immutable baseline, patch payload.
- **You get:** patch card, independent findings, application receipt.
- **Work involved:** Requires a reviewer.

---

Sapote-Mamey v9.7.461; engine 1.9.177. Generated from `mamey/data/deliverables_registry.json` by `tools/generate_deliverables_menu.py`.
