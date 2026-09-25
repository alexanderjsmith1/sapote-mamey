# Manuscript Methods implementation template

**Template status:** prospective authoring aid; inclusion in the bundle does not assert that any study was run.  
**Version template:** Sapote-Mamey v9.7.442 / Mamey v1.9.169  
**Required substitutions:** replace every bracketed field and delete modules that were not used.

## Scope and reproducibility statement

This study used [archived release, DOI, or commit] with antiSMASH [version and strictness], [database/reference versions], and the input manifest [identifier and SHA-256]. Sapote-Mamey separates Mamey, the deterministic extraction and prioritization layer, from Sapote, the authored interpretation layer. Deterministic records were preserved when interpretation was added. Every locus-specific display used the complete identity `strain / full node-or-contig / region / BGC alias`.

## Execution and admission

The workflow was invoked from the bundle root with `python mamey_run.py`. Report the commands actually used, rather than copying this suggested sequence: `doctor`, `inspect`, `run --mode gold`, `validate`, and `explain`, followed only by the optional package-backed analyses used in the study. Inputs were admitted by archive contents, not filename. Record antiSMASH schema status, bounded-read overrides, archive SHA-256, warnings, and excluded or degraded inputs. Never convert unavailable evidence into an observed zero.

## BGC inventory and exact identity

Region GenBank records supplied BGC calls and CDS annotations; whole-record GenBank or FASTA members supplied contig lengths and assembly statistics when present. Describe coordinate recovery, edge classification, assembly-quality fields, and any heuristic corrected-count output. Display aliases such as `BGC001` are secondary identifiers and must not be used without strain, full node/contig, and region.

## Similarity evidence

KnownClusterBlast, MIBiG, and RiQ evidence was parsed with source precedence and provenance retained. State the evidence source, query and subject identifiers, admitted row counts, coverage/similarity fields, database version, and failure state. Compound names derived from similarity are class-level hypotheses; they are not product or activity confirmation. A zero admitted-row result is not a verified no-hit unless the query binding and search receipt support that conclusion.

## Fragmentation recovery

If used, report FLBR, EFLS, and RG-GMCI separately. RG-GMCI deterministically evaluates shared-reference pairs, subject-gene tiling, product compatibility, contig termini, and hub promiscuity. For this documented release, HIGH and MODERATE routes begin at scores 14 and 9; additional geometry limits are recorded in the technical appendix. These states nominate candidate split pathways and do not establish physical linkage or reassemble DNA. Report any hub demotion, low-complexity terminus, scan-cap, or insufficient-tiling state.

## Source-derived scans and scoring

For every scan used, report its registry/resource version, inputs, output unit, missingness, and applicable guards. CCTT, CGAD, UMED, resistance, bldA/TTA, TFBS, antibacterial, antifungal, and novelty outputs are deterministic screening or routing signals. Triage tiers and scores are expert-designed workflow policy, not probabilities, structures, products, or assay results. Preserve raw values and all downgrades or exclusions.

## Mode B and authored interpretation

Mode B evidence was inventoried by exact locus and channel before interpretation. Record the Mode B profile/contract, evidence hashes and binding states, model and prompt/controller where an LLM assisted, and the human disposition. Separate deterministic measurements from authored gene-role, pathway-architecture, ecological, or experimental interpretation. Missing components, phenotype links, and core/accessory divisions must remain hypotheses unless independently demonstrated.

## Cohort and phylogenetic analyses

For cohort results, define the biological unit, numerator, denominator, duplicate policy, exclusions, missingness, assembly state, scoring version, and metadata source. For phylogeny or ANI/AAI, report the admitted sequence roster and hashes, reference-selection rule, outgroup, marker set, tool versions, model, seed, aligned fraction, and failed/held samples. Placement is conditional on the sampled panel and does not automatically establish formal taxonomy.

## Figures and package integrity

Figures were generated from [sealed package or governed table identifiers] without rescoring. Report renderer/version, dimensions, DPI, source-data and caption/methods sidecars, hashes, mechanical checks, and human visual review. Package seals and checksums establish byte integrity and gate status, not biological correctness. State privacy/export profile and any non-public restrictions.

## Validation and claim ceiling

Describe hermetic software fixtures separately from public known-answer or biological controls. Include accessions, input hashes, expected-outcome source, software/database versions, exact commands, exclusions, and receipts. Do not generalize validation of one module to the complete workflow. Similarity supports relatedness, capacity supports potential, routing scores support prioritization, and strain-level phenotypes do not localize activity to a BGC without targeted evidence.

## Study-specific information still required

- [ ] Sample source, collection, culture, extraction, sequencing, assembly, and QC methods.
- [ ] antiSMASH version, strictness, database date, and all non-default parameters.
- [ ] Exact software bundle/engine/build or commit and input/reference SHA-256 values.
- [ ] Commands, environment, seeds, threads, resource limits, and failure handling.
- [ ] Statistical design, replicates, controls, exclusions, denominators, and missingness.
- [ ] Wet-lab, metabolomics, and validation methods supporting any biological claim.
- [ ] LLM disclosure, evidence binding, model/prompt record, and human review disposition.

