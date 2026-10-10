# Functional logic workup — operational boundaries for v9.7.447

Read the guide below with these source-backed limits:

- Inputs require a `manifest.json` plus exactly one each of `*_cds_table.csv`, `*_3_mibig_per_gene.csv` and `*_2_inventory.csv` per package. The manifest is required and hashed; this tool does not verify its contents or revalidate a package seal. Package-list relative paths resolve against the process working directory; only lines starting directly with `#` are comments.
- Rank lookup uses `complete_identity`; duplicate rank identities collapse to the last row in a dictionary. BGC grouping is by `bgc_id` within a package and takes the first gene row's contig/region identity. Independently check identity uniqueness and mixed-locus rows before running. The final count equality is not proof that those source identities or annotations are correct.
- Alias CSV columns are `source_strain,display_strain`; duplicate source aliases use the last value. Duplicate source strains across packages fail, but distinct source strains mapping to one display name are not separately rejected. Sanitized per-strain folder names can collide. Keep aliases unique and verify every output identity and per-strain folder.
- Dominant MIBiG accession versions are stripped for matching. Role calls are annotation-pattern classification; an admitted table hit is not newly computed alignment evidence. A regulator, transporter or resistance annotation is not measured regulation, transport or self-resistance.
- `--out` is created early and existing named TSV/JSON outputs are overwritten sequentially. There is no transactional rollback or empty-directory refusal; a later error can leave partial output or stale prior files. Use a new output directory and keep failed runs separate.
- `SOURCE_HASHES.tsv` hashes the four package input files, not the definitive-rank or alias table. `RECEIPT.json` records counts and relation labels; it does not itself bind every output hash or scientific inference. Record the rank/alias paths and SHA-256 alongside the run and verify output completeness independently. Retain the original research-result hashes and bind any new calculation separately.

`COMPLETE` is a tool completion status. Preserve all claim ceilings in the guide below; scientific acceptance stays with the user.

---

# BGC functional logic workup

`tools/bgc_functional_logic_workup.py` explains the definitive ranking at gene resolution. It preserves direct MIBiG and ClusterBlast evidence while adding a separate architecture-first channel for genes that do not align to the selected reference.

This distinction matters because a gene can support pathway logic without being reported as a ClusterBlast match. Examples include a locally annotated precursor peptide, maturation enzyme, glycosyltransferase, regulator, transporter, or resistance candidate that is absent from the chosen MIBiG record, too divergent for the admitted match, or outside the reference's annotated gene set.

## Evidence channels

Each gene is represented in three independent fields:

1. **Direct reference match:** whether the gene has any admitted MIBiG hit and whether it maps specifically to the dominant reference used by Definitive BGC Ranker.
2. **Functional annotation logic:** antiSMASH `gene_functions`, `sec_met_domains`, product annotations, gene kind, and gene order are classified into core, precursor, maturation, tailoring, transport, regulatory, resistance, or other roles.
3. **Architecture-first inference:** the existing KCB-blind `mamey.architecture_first` classifier assesses domain architecture without reading the reference match. Its pathway type, confidence, diagnostic markers, reasoning, reference concordance, and final bounded assignment are reported.

Direct similarity and functional logic are not interchangeable. The workup never converts an annotation-only gene into a reference match, and it never converts reference similarity into proof of a complete pathway or exact product.

## Usage

Supply the exact package set, rather than a broad historical root, whenever multiple package versions may exist.

```bash
python tools/bgc_functional_logic_workup.py \
  --package-list /path/to/exact_package_paths.txt \
  --definitive-rank /path/to/ALL_BGC_DEFINITIVE_EVIDENCE_RANK.tsv \
  --strain-aliases /path/to/STRAIN_ALIASES.csv \
  --out /path/to/functional_logic_workup
```

The package list contains one package directory per line. Duplicate source strains fail closed.

## Functional reference relationships

- `ARCHITECTURE_CORROBORATES_REFERENCE`: KCB-blind architecture and the reference family agree.
- `ARCHITECTURE_REFERENCE_DISCORDANT`: domain architecture and reference assignment disagree; inspect the genes driving each channel.
- `ARCHITECTURE_UNRESOLVED_REFERENCE_DOMINANT`: architecture cannot resolve the class and the reference provides the principal provisional signal.
- `ARCHITECTURE_EXTENDS_WEAK_REFERENCE`: independent architecture is present and unmatched functional genes extend a weak reference comparison.
- `ARCHITECTURE_SUPPORT_PRESENT`: independent architecture is present beside the reference channel.
- `ARCHITECTURE_ONLY_NO_REFERENCE_MATCH`: a class-relevant architecture is detected without an admitted dominant reference.
- `REFERENCE_MATCH_ARCHITECTURE_UNRESOLVED`: a reference match exists but the local domain architecture remains unresolved.
- `BOTH_CHANNELS_UNRESOLVED`: neither channel supports a bounded family interpretation.

These labels are explanations, not a replacement probability or a new product score.

## Outputs

- `ALL_BGC_FUNCTIONAL_LOGIC_WORKUP.tsv` gives one detailed record for every ranked BGC.
- `ALL_GENE_FUNCTIONAL_EVIDENCE.tsv` gives the gene-by-gene evidence ledger.
- `NO_MIBIG_MATCH_FUNCTIONAL_GENES.tsv` isolates genes with functional logic and no admitted MIBiG gene match at all.
- `NONDOMINANT_REFERENCE_FUNCTIONAL_GENES.tsv` isolates the broader set with functional logic but no match to the selected dominant reference; some of these genes may match a different MIBiG entry.
- `FUNCTIONAL_REFERENCE_RELATION_SUMMARY.tsv` summarizes the relationship labels.
- `PER_STRAIN/<strain>/` contains the same BGC, gene, no-MIBiG-match, and non-dominant-reference views for each strain.
- `SOURCE_HASHES.tsv` and `RECEIPT.json` bind the run.

Every BGC uses `strain / full node-or-contig / region / BGC alias`. The workup supports pathway-family interpretation and experimental prioritization only. It does not prove an exact product, pathway completeness, expression, production, activity, novelty, physical linkage, or scientific acceptance.
