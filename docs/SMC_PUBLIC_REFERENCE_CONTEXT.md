# Optional JGI public reference context: IMG-ABC and SMC

Use this guide when a selected public reference record could help explain a local result. Start with the accession versions already selected for your analysis, then use the manual crosswalk below. Sapote–Mamey has no identified JGI SMC API adapter, automatic import or SMC analysis runner in this bundle. Service details below may have changed; check the linked pages before retrieving anything.

JGI reports that IMG-ABC was retired following SMC’s official 2023 launch. Preserve IMG-ABC citations and identifiers when describing historical analyses; do not relabel them as SMC results. [JGI implementation report, page 14](https://archive.jgi.doe.gov/wp-content/uploads/sites/8/2024/03/Beyond-Basepairs-Implementation-Report-2024.pdf)

The [Secondary Metabolism Collaboratory](https://smc.jgi.doe.gov/) offers accession and identifier browsing, downloads and API documentation. Use a small selected public accession roster for reference context. Its presence in SMC does not establish type-strain status; retain independent type-strain evidence for paper examples.

## A bounded manual workflow

1. Start with the exact public assembly and contig accession versions already selected for the analysis. Search public accession metadata. Keep private strain names, sequences and annotations local.
2. Record the external record URL, SMC BGC/source/annotation IDs, retrieval date, source accession/version, assembly/contig association, coordinates with their original convention and strand, and supplied annotation tool/version/date. Record unknown values explicitly. If a file is separately retrieved, retain its original bytes and SHA-256 with its citation and reuse statement.
3. Make an explicit external-reference crosswalk before attaching a record to a local locus. Retain the local **strain / full contig / region / BGC alias** unchanged. Require accession-version and coordinate agreement; a shared taxon, display name or region number is insufficient. Preserve conflicting or ambiguous mappings as unresolved.
4. Keep external reference annotations separate from local antiSMASH, MIBiG, family assignments and reviewed interpretations. Label predicted, community-supplied and experimentally supported statements according to their actual source evidence. Reference agreement alone does not establish product identity, production or activity.
5. In a figure or report, cite the specific reference record and state what it contributes. Include a portable crosswalk and retrieval manifest if those reference annotations contribute to the deliverable. Use [Evidence to report](EVIDENCE_TO_REPORT.md) and [figure guidance](FIGURES_START_HERE.md) for the existing local workflow.

## Retrieval status and reproducibility

The [SMC Downloads page](https://smc.jgi.doe.gov/projects/) lists large dated exports. An offered snapshot is not evidence that it represents the current complete service. Prefer selected references over bulk acquisition for this workflow.

The [API help](https://smc.jgi.doe.gov/api-help) and [conduct policy](https://smc.jgi.doe.gov/code-of-conduct) require further endpoint/authentication-contract verification before automation. The policy’s broad availability wording does not establish a specific license for every underlying record. Preserve record-specific rights statements and source provenance. This guide has not tested any API endpoint, export or mapping.

For Methods: describe only the records and operations actually used, with retrieval date, accession versions, annotation provenance and mapping criteria. Merely consulting this guide does not mean SMC was used in an analysis.
