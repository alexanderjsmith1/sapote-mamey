# Recorded public-genome walkthroughs

This page is a fixed record of nine past runs on public type-strain genomes. It is not a recipe
and not a pass test. Your own run can give different numbers. To run your own genome, use
[Your first run](../reader/01_FIRST_RUN.md).

The strain names are public culture-collection strains (JCM, NBRC, DSM, NRRL, ATCC). Terms used
below:

- A **BGC** is a biosynthetic gene cluster. A **region** is one antiSMASH call that holds one or more BGCs. See the [glossary](../GLOSSARY.md#1-bgc--biosynthetic-gene-cluster).
- **RG-GMCI** is the check that finds pairs of regions that may be two pieces of one cluster. See the [glossary](../GLOSSARY.md#7-rg-gmci-and-the-rescue-layer).
- A **sealed** package is one that passed the package integrity checks. See the [glossary](../GLOSSARY.md).
- **Judgment** is the written interpretation of BGCs (Mode B cards). `JUDGMENT_PENDING` means the validator did not find a qualifying Mode B card for every locked item (`mamey/validate.py:944-946,975-977`). The required judgment is incomplete or unverified. The validator cannot show that no partial or separately stored interpretation exists, so inspect the actual register and any retained writing separately.
- **Interior**, **edge** and **full-contig** describe where a region sits on its contig. See the [glossary](../GLOSSARY.md#3-corrected-bgc-count).

Exit status 0 from a command and no `FAIL` from `validate` mean only that the checks the software encodes did not fail. They do not show visual quality, or that checks it does not run were met. The Presentation note near the end of this page records a brief with visible defects that validation did not catch. Review the issue log, the outputs and the figures yourself.
[Your first run](../reader/01_FIRST_RUN.md) explains the exit codes.

The nine inputs are public type-strain genomes from seven genera, plus two more
*Streptomyces*. Each identity was checked against the archived headers, with no independent
online taxonomy check. The software bundle does not include the input ZIPs or the run receipts. Every figure, status and command result on this page is therefore a reported historical result that cannot be re-checked from the bundle. That does not show the runs did not happen.

## What ran

Each input went through `inspect`, `run`, `validate`, `explain` and an inventory listing. All
45 commands (five per input) were reported to return zero. Settings were bounded JSON evidence (`--json-evidence bounded`), the standard
brief, locus maps on and private output. That differs from the capped recipe in
[Your first run](../reader/01_FIRST_RUN.md). These runs did not use online searches, trees, family
clustering or full Mode B writing.

## Timing and memory

Mean run time was **40.93 s**, median **39.18 s**, range **33.88 to 49.56 s**. Peak memory per
child process was **1.90 to 2.41 GB** (1 GB = 1,000,000,000 bytes). Run seconds and peak memory come from the
process receipt.

The host was one macOS arm64 machine with Python 3.12.14 and ten logical CPUs. Each input ran
once, in sequence. Caches and background activity were not controlled, and no thread-count
test was done.

## Results by input

Regions are antiSMASH regions. They split by position on the contig into interior, edge and
full-contig. The weighted count is interior x 1.0 plus edge x 0.5 plus full-contig x 0.25; see
the [glossary](../GLOSSARY.md#3-corrected-bgc-count).

| Input | Regions (interior / edge / full-contig) | Weighted count | Contigs | N50 (bp) | Run s | Peak GB | Package files | Package MB | Sealed ZIP MB |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| *Actinomadura citrea* JCM 3295 | 68 (48 / 12 / 8) | 56.0 | 74 | 326159 | 36.65 | 2.33 | 686 | 128.5 | 39.4 |
| *Nocardia thailandica* NBRC 100428 | 51 (10 / 26 / 15) | 26.75 | 312 | 47211 | 41.65 | 2.18 | 554 | 117.4 | 31.9 |
| *Pseudonocardia* sp. DSM 110487 | 52 (52 / 0 / 0) | 52.0 | 1 | 10132709 | 45.46 | 1.90 | 569 | 113.5 | 34.6 |
| *Saccharopolyspora erythraea* NRRL 2338 | 57 (57 / 0 / 0) | 57.0 | 1 | 8212805 | 36.20 | 2.15 | 614 | 133.5 | 37.2 |
| *Saccharothrix espanaensis* DSM 44229 | 58 (58 / 0 / 0) | 58.0 | 1 | 9360653 | 39.07 | 2.12 | 617 | 152.2 | 40.8 |
| *Streptomyces clavuligerus* ATCC 27064 | 60 (58 / 2 / 0) | 59.0 | 2 | 6748591 | 39.18 | 2.41 | 633 | 139.4 | 40.7 |
| *Streptomyces fradiae* ATCC 10745 | 52 (50 / 2 / 0) | 51.0 | 1 | 6725579 | 33.88 | 2.10 | 575 | 128.7 | 32.8 |
| *Streptomyces spectabilis* ATCC 27465 | 67 (67 / 0 / 0) | 67.0 | 1 | 9807160 | 46.70 | 2.37 | 685 | 175.0 | 47.8 |
| *Streptosporangium pseudovulgare* JCM 3115 | 56 (45 / 10 / 1) | 50.25 | 73 | 329744 | 49.56 | 2.21 | 606 | 124.0 | 38.9 |

Every run ended with pipeline status `MAMEY_COMPLETE_WITH_ISSUES`, validator status
`MAMEY_COMPLETE` and interpretation status `JUDGMENT_PENDING`. Every run carried the evidence
advisory `MAIN_JSON_WALKER_TRUNCATED`. The links on each package's entry page and ZIP integrity checked
successfully for all nine.

## First triage row per input

Each row is the first row of that run's triage table. It was cross-checked against the
inventory and a source region GBK in the input ZIP. Each identity is
`contig / region / BGC alias`. AB and AF are prioritization scores for antibacterial and
antifungal follow-up. They are not percentages or assay results. See
[reading your results](../READING_YOUR_RESULTS.md) for boundary, architecture grade and class
confidence.

| Input | Contig / region / alias | Products | Boundary | Architecture | Class confidence | AB | AF |
|---|---|---|---|---|---|---:|---:|
| *Actinomadura citrea* | BMRD01000003.1 / region002 / BGC014 | RiPP; lanthipeptide-class-ii | Interior | A | LOW | 74.0 | 24.0 |
| *Nocardia thailandica* | NZ_BAGK01000184.1 / region001 / BGC026 | NRPS; PKS; T1PKS; saccharide | Edge | C | MODERATE | 59.0 | 42.0 |
| *Pseudonocardia* sp. | CP080521.1 / region029 / BGC029 | RiPP; lassopeptide | Interior | A | LOW | 68.0 | 20.0 |
| *Saccharopolyspora erythraea* | AM420293.1 / region035 / BGC035 | RiPP; lanthipeptide-class-iii | Interior | A | LOW | 74.0 | 24.0 |
| *Saccharothrix espanaensis* | HE804045.1 / region023 / BGC023 | HR-T2PKS; NRPS; PKS; fatty_acid; halogenated; other; thioamide-NRP | Interior | A | HIGH | 100 | 32.0 |
| *Streptomyces clavuligerus* | CP027858.1 / region002 / BGC002 | NRPS; NRPS-like; PKS; T1PKS; saccharide; terpene | Interior | A | MODERATE | 59.0 | 74.0 |
| *Streptomyces fradiae* | CP023696.1 / region010 / BGC010 | RiPP; lanthipeptide-class-i | Interior | A | LOW | 74.0 | 24.0 |
| *Streptomyces spectabilis* | CP023690.1 / region004 / BGC004 | NRPS; PKS; RiPP; lassopeptide; transAT-PKS | Interior | A | MODERATE | 98.0 | 44.0 |
| *Streptosporangium pseudovulgare* | NZ_BMQJ01000002.1 / region002 / BGC009 | RiPP; lanthipeptide-class-iii | Interior | A | LOW | 74.0 | 24.0 |

## Issues each run recorded

The issue log of each run listed some of the following. The counts are per input.

| Issue | What it means | What to do |
|---|---|---|
| `MULTIBATCH` | More than 25 raw BGCs. Judgment needs several batches of about 20 BGCs. | Plan the batches before you write cards. |
| `RG-GMCI HIGH pairs` | Pairs of regions that look like pieces of one cluster. | Include split-cluster review in each batch. |
| `OVER_MERGE_CANDIDATES` | Regions that hold two or more protoclusters, which is antiSMASH's own signal that a region may be more than one BGC. | Check these regions in the run's predicted-polymers table (`*_predicted_polymers.csv`). |
| `VERY_POOR` assembly | Under 20 percent of BGCs are interior. Most leads are edge or full-contig fragments. | Use RG-GMCI before ranking leads. |
| `MAIN_JSON_WALKER_TRUNCATED` | Bounded mode stopped reading the main antiSMASH JSON early. | Do not call the extraction exhaustive. |

| Input | Judgment batches (MULTIBATCH) | RG-GMCI HIGH pairs | OVER_MERGE_CANDIDATES regions | VERY_POOR |
|---|---:|---:|---:|---|
| *Actinomadura citrea* | about 4 | 16 | 7 | no |
| *Nocardia thailandica* | about 3 | 10 | 6 | yes (19.6% interior) |
| *Pseudonocardia* sp. | about 3 | 1 | 2 | no |
| *Saccharopolyspora erythraea* | about 3 | 13 | 14 | no |
| *Saccharothrix espanaensis* | about 3 | 7 | 9 | no |
| *Streptomyces clavuligerus* | about 3 | 13 | 16 | no |
| *Streptomyces fradiae* | about 3 | 5 | 7 | no |
| *Streptomyces spectabilis* | about 4 | 5 | 21 | no |
| *Streptosporangium pseudovulgare* | about 3 | 9 | 7 | no |

For recovery steps, see [Recovery and limits](../reader/04_RECOVERY_AND_LIMITS.md).

## Where the runs needed judgment

- Metadata: use the full archived description, or record the identity as unresolved.
- Evidence: bounded mode can finish with a truncated main JSON walker. Full mode can instead hold an over-cap file.
- Presentation: the brief for the *Nocardia* run had first-page overflow, overlapping text and shortened identifiers. Package validation did not catch these visual defects.
- Storage: figures and locus maps generate hundreds of files per package. Use the run inventory to choose what to keep.
