# Fungal phylogenetics workflow — placing a fungal isolate (rDNA screen → genome MLSA)

Review the fungal phylogenetics workflow and its limits.  
This page is for researchers planning a fungal analysis.

**Purpose.** This is a companion to the
[current fungal guide](../docs/PHYLO_FUNGAL_WORKFLOW.md). It introduces an rDNA screen and
genome-ortholog study design using shared tree checks. Bacterial marker/reference presets
and the actinomycete registry cannot be reused unchanged for fungal inputs. The bundle
does not ship a one-command fungal runner.

## Current scope and input boundary

Read the
[current fungal guide](../docs/PHYLO_FUNGAL_WORKFLOW.md) and
[companion protocol](../docs/LLM_COMPANION_TOOL_PROTOCOL.md) before selecting inputs or compute.
Tool/platform behavior and biological interpretations require source-specific review.
Review only requires file access;
external programs, database downloads and phylogenetic compute have separate prerequisites.

## Tier 1 — rDNA screen

Extract the rDNA markers from the assembly and place each one independently:

| marker | resolves | honest limits |
|---|---|---|
| **18S (SSU)** | broad context | Often conserved; resolution and reference coverage depend on the sampled group. |
| **ITS** (ITS1–5.8S–ITS2) | finer-scale comparison | Review alignment and reference coverage within the chosen scope; do not concatenate divergent family-wide ITS as a default. A match alone is not a species determination. |
| **LSU (28S, D1/D2)** | additional rDNA context | Resolution and coverage depend on the sampled taxa and region. |
| **whole operon** (18S+ITS+28S) | linked rDNA evidence | Use only records with reviewed source correspondence and an appropriate alignment; report missing loci and sampling rather than silently substituting records. |

**Extraction.** ITSx (ITS) and Barrnap with an available model appropriate to the installed version (SSU/LSU; see [version guidance](../docs/BARRNAP.md)) are the dedicated tools. A
**blastn reference-probe** against the assembly (probe with a near-neighbor operon record, slice the
assembly by the hit coordinates, bounded by the real 18S-hit end / 28S-hit start) uses BLAST+.

**Reading discordance.** If markers disagree on the nearest genus, that discordance alone does not establish a novel lineage. Check source identity, alignment,
reference coverage and the stated analysis scope; retain unresolved placement as a hold. A separately
authorized genome comparison may resolve the question, but it is not automatically triggered.

## Tier 2 — genome ortholog comparison

The bundle’s GToTree presets do not establish a fungal workflow. One separate fungal route is
**single-copy-ortholog phylogenomics** using a reviewed BUSCO lineage dataset:

1. Plan **BUSCO** or **compleasm** for the query and reviewed reference genomes. The bundle lists `ascomycota_odb10` and `dothideomycetes_odb10` as examples, not universal fungal datasets. Review installed versions, lineage data, platform support and outputs; tool outputs are not assumed interchangeable. Reference selection and any retrieval require separate source and authorization review.
2. Review ortholog identity, duplication, missingness and taxon occupancy before selecting loci. Per-gene alignment (MUSCLE/MAFFT), trimming (trimAl), concatenation and partitioning require an explicit plan; a larger locus count alone does not establish a reliable tree.
3. Plan a partitioned **IQ-TREE** analysis with justified model, support settings and resource budget. Review the outgroup genome for the actual taxonomic scope; do not treat a previously used command or support setting as an approved preset.
4. **Gates**: inspect the outgroup-aware tree sanity result before rendering. Its CLI returns 0
   for a pass and 2 for a failure. `tools/signoff_check.py` is advisory and returns 0 even when
   it lists issues or cannot inspect a tree; read its per-tree report and complete the human checks.
   Exit 0 alone is not eight-item scientific sign-off.
5. Render with the shared ggtree tool (`GG_TITLE`/`GG_SUB` overrides so the caption never says "16S").

## Outgroup registry (fungal)

`mamey/data/fungal_outgroup_registry.tsv` mirrors the bacterial registry — root a family-scoped tree on a
**sister family, one rank out**, never a distant class. Seeded rows:

| scope | outgroup | accession | status |
|---|---|---|---|
| Trichomeriaceae | *Exophiala salmonis* (Herpotrichiellaceae) | NG_061119.1 | LOCKED |
| Herpotrichiellaceae | *Cyphellophora laciniata* | NG_064890.1 | CONFIRM |
| Chaetothyriales (order-level) | *Dothidea insculpta* (Dothideomycetes) | NG_027644.1 | CONFIRM |

The table above lists **marker accessions**, not genome assemblies. A genome tree must select an
appropriate `genome` row from the actual registry and bind its assembly accession, bytes and role;
do not supply an NG_ marker accession as a genome. The current registry also has explicit BANNED
rows. LOCKED/CONFIRM/BANNED are recorded project dispositions, not fresh sequence or taxonomy
verification for a new analysis. Report an unavailable/deferred reference rather than substituting
an unbound accession. Keep registry exclusion decisions and any sensitivity analysis visible.

The shared tree checker accepts explicit `--outgroup` identifiers. Its
`--locked-outgroup-group` / `--outgroup-registry` adapter reads bacterial `genus` rows;
it does not read this fungal registry’s `family` or `genome` rows. Fungal registry selection
and source binding remain a separately reviewed input decision.

## Known failure modes (learned the hard way — do not repeat)

- **Family-wide ITS concatenation**: a historical example produced a dominating internal branch despite different trim settings. Review ITS alignment and resolution for the specific taxa and question.
- **One bad reference record can sink a tree**: diagnose the accession, sequence, alignment and model before a justified, recorded exclusion. Do not automatically drop an inconvenient branch or weaken the gate.
- **A gate FAIL can be the finding**: a long-branch failure needs source/alignment/model diagnosis and does not establish novelty. Report the numbers and unresolved reason; do not loosen a gate merely to make artwork printable.
- **rDNA extraction without a dedicated tool is fine** *if* slice boundaries are anchored to real
  alignment ends of the flanking genes — document the coordinates.

## Tooling

ITSx 1.1.3 (Bengtsson-Palme 2013), barrnap (Seemann), BUSCO 5.x (Manni 2021), **compleasm**
(Huang & Li 2023, *Bioinformatics* 39:btad595), MUSCLE v5, trimAl, IQ-TREE, BLAST+, NCBI `datasets`.
See [External Tools & Databases](External-Tools-and-Databases.md).

## How to state the result (claim-safe)

> "On rDNA markers, isolate X is a member of family F (order O). The markers disagree on the nearest
> genus and the isolate is the most divergent taxon in a matched whole-operon matrix — placement remains unresolved under this reference/marker scope. Genus-level placement awaits the genome MLSA (single-copy-ortholog
> tree). rDNA identity is a neighborhood statement, not a species call; judgment deferred."

## Related pages

For placement on a fixed reference tree, see [Phylogenetic Placement](Phylogenetic-Placement.md). The fungal guide remains the source for fungal inputs.
