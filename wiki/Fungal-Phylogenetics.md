# Fungal phylogenetics workflow — placing a fungal isolate (rDNA screen → genome MLSA)

**Purpose.** The bundle's phylogenetic workflows are bacterial (16S placement, GToTree core-genome
backbones, an actinomycete outgroup registry). None of that applies to a fungus: different loci, different
alphabet, different reference bodies. This page is the fungal sibling — a two-tier method that goes from a
fast rDNA neighborhood screen to a genome-based multi-locus tree, with the same rooting rules and the same
sanity gates as the bacterial lane.

*Status: formalized in the bundle at **v9.7.399** (`docs/PHYLO_FUNGAL_WORKFLOW.md` +
`mamey/data/fungal_outgroup_registry.tsv`, P399 card). Developed on the workflow's founding
case — a Vespid-wasp-associated black yeast (Chaetothyriales), referred to below as "the founding
isolate" (internal cohort ID withheld from this page per release policy).*

## Current scope and input boundary

This page retains a historical worked-case workflow. Read the
[current fungal guide](../docs/PHYLO_FUNGAL_WORKFLOW.md) and
[companion protocol](../docs/LLM_COMPANION_TOOL_PROTOCOL.md) before selecting inputs or compute.
Recorded founding-case timings, marker identities, tool/platform behavior and biological
interpretations are not revalidated by the current bundle stamp. Review only requires file access;
external programs, database downloads and phylogenetic compute have separate prerequisites.

## Tier 1 — rDNA screen (hours, no genome pipeline needed)

Extract the rDNA markers from the assembly and place each one independently:

| marker | resolves | honest limits |
|---|---|---|
| **18S (SSU)** | family / broad neighborhood | highly conserved — 98%+ identity spans several genera |
| **ITS** (ITS1–5.8S–ITS2) | species **within** a genus | **unalignable across divergent genera** — never build a family-wide ITS tree, and never concatenate family-wide ITS into a supermatrix |
| **LSU (28S, D1/D2)** | genus-spanning family trees | the workhorse for a "many strains" family tree |
| **whole operon** (18S+ITS+28S, *matched* records only) | strongest rDNA statement | only for taxa with full-operon accessions — a matched matrix, never a gap-patched one |

**Extraction.** ITSx (ITS) and Barrnap with its installed version’s fungal model (SSU/LSU; see [version guidance](../docs/BARRNAP.md)) are the dedicated tools; a
**blastn reference-probe** against the assembly (probe with a near-neighbor operon record, slice the
assembly by the hit coordinates, bounded by the real 18S-hit end / 28S-hit start) works with nothing but
BLAST+ and is what the founding case actually used.

**Reading discordance.** If the markers disagree on the nearest genus (founding isolate: 18S→*Bradymyces* 98.6%,
ITS→*Knufia* ~87%, LSU→near *Trichomerium*, whole operon→longest branch in the matrix), marker discordance alone does not establish a novel lineage. Check source identity, alignment,
reference coverage and the stated analysis scope; retain unresolved placement as a hold. A separately
authorized genome comparison may resolve the question, but it is not automatically triggered.

## Tier 2 — genome MLSA (the fungal GToTree equivalent)

GToTree is bacterial. The fungal equivalent is **single-copy-ortholog phylogenomics** from BUSCO gene
sets:

1. Run **BUSCO** (lineage `ascomycota_odb10` / `dothideomycetes_odb10`) — or **compleasm**, the faster
   drop-in reimplementation (miniprot + hmmsearch; runs where BUSCO's metaeuk/augustus stack won't
   install, e.g. macOS-arm64) — on the query genome and on reference genomes for the family/order
   (fetched with NCBI `datasets`, one per genus where available, RefSeq-preferred).
2. Keep single-copy orthologs present in ~all taxa → per-gene align (MUSCLE/MAFFT) → trim (trimAl) →
   concatenate with a partition model. Hundreds of loci — far more signal than 3–4 hand-picked MLSA genes.
3. Partitioned **IQ-TREE** (`-m MFP -B 1000 -alrt 1000`), rooted on a sister-family outgroup genome.
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
verification for a new analysis. Report a unavailable/deferred reference rather than substituting
an unbound accession. Keep registry exclusion decisions and any sensitivity analysis visible.

## Known failure modes (learned the hard way — do not repeat)

- **Family-wide ITS concatenation**: produces a dominating internal branch that fails the sanity gate at
  every trim setting. ITS is a within-genus tool, full stop.
- **One bad reference record can sink a tree**: a single mis-deposited LSU accession (a 5.4-subs/site
  terminal branch) failed a 36-taxon tree; diagnose the accession, sequence, alignment and model before a justified, recorded exclusion; do not automatically drop a inconvenient branch or weaken the gate.
- **A gate FAIL can be the finding**: a long-branch failure needs source/alignment/model diagnosis and does not establish novelty. Report the numbers and unresolved reason; do not loosen a gate merely to make artwork printable.
- **rDNA extraction without a dedicated tool is fine** *if* slice boundaries are anchored to real
  alignment ends of the flanking genes — document the coordinates.

## Tooling

ITSx 1.1.3 (Bengtsson-Palme 2013), barrnap (Seemann), BUSCO 5.x (Manni 2021), **compleasm**
(Huang & Li 2023, *Bioinformatics* 39:btad595), MUSCLE v5, trimAl, IQ-TREE, BLAST+, NCBI `datasets`.
See [External Tools & Databases](External-Tools-and-Databases.md).

## How to state the result (claim-safe)

> "On rDNA markers, isolate X is a member of family F (order O); the markers disagree on the nearest
> genus and the isolate is the most divergent taxon in a matched whole-operon matrix — placement remains unresolved under this reference/marker scope. Genus-level placement awaits the genome MLSA (single-copy-ortholog
> tree). rDNA identity is a neighborhood statement, not a species call; judgment deferred."
