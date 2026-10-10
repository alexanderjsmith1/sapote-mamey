# Manuscript Methods implementation template

**Template status:** prospective authoring aid; inclusion in the bundle does not assert that any study was run.  
**Version template:** Sapote-Mamey v9.7.449 / Mamey v1.9.174  
**Required substitutions:** replace every bracketed field and delete modules that were not used. Rewrite each retrospective sentence below to match actual execution; this template is not an execution receipt.

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

Build the reported channel inventory from the final bound outputs, then reconcile it with the actual phase receipts. The current `source_scans` phase can end before RG-GMCI and per-gene/structured enrichments are filled. Its `END` row records BGC, preliminary EFLS-pair and TFBS-hit counts, not successful completion of every channel. Later enrichment can retain `ERROR_*` in its own output while the broader RG-GMCI phase still records `END`; its functional-profile status also defaults to `OK` when no explicit status field exists. Preserve the actual channel state and inspected row/identity scope instead of translating these aggregate/default labels into verified results (`mamey/cli.py:1577–1588, 1797–1902`).

For degradation reporting, retain the `degradation_events` receipt's total `n` separately from its `events` list, which stores only the first 50 collected details. Draining clears the process-local collector before the summary receipt is written; the collector is not an independent persistent event ledger. Its recording/draining and receipt writing are best-effort, so an absent event or receipt must remain an evidence gap rather than a demonstrated clean channel. Disclose any incomplete detail coverage and bind the saved receipts to the extraction being described (`mamey/cli.py:341–384, 1089–1098`; `mamey/degradation.py:18–38`).

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


## Authoring checks before adoption

Verify numerical statements against the installed source and [technical appendix](../reference/METHODS_TECHNICAL_APPENDIX.md), including units, warning versus refusal behavior, and export budgets that retain HIGH rows beyond a display cap. Pin the exact configuration used in this study rather than inferring it from a release label. The [source-map gate](../development/METHODS_IMPLEMENTATION_SOURCE_MAP.md) checks paths, not whether all modules ran or their results were correct.

Distinguish fixed analytical records from mutable judgment/timing receipts and supplementary rendering. Report the specific artifacts compared when claiming reproducibility. Passing ingest, structure, publication, or seal checks does not replace evidence review or the project owner's adoption decision. Use the contract/profile selected for the actual run; a historical section count in a CLI diagnostic is not the current profile authority.
