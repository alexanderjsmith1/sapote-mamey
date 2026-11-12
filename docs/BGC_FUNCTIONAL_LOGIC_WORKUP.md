# BGC functional logic workup

`tools/bgc_functional_logic_workup.py` explains the [definitive ranking](DEFINITIVE_BGC_RANKER.md) at gene level. It keeps direct MIBiG and ClusterBlast matches. It adds a separate architecture-first channel for genes that do not align to the selected reference. The next tool in the chain is [strain-level BGC logic](STRAIN_LEVEL_BGC_LOGIC.md), which reads this tool's output. Terms such as KnownClusterBlast (KCB), MIBiG and BGC are in the [glossary](GLOSSARY.md).

A gene can support pathway logic without being a ClusterBlast match. Examples are a locally annotated precursor peptide, a maturation enzyme, a glycosyltransferase, a regulator, a transporter or a resistance candidate. Such a gene may be missing from the chosen MIBiG record, too divergent to count, or outside the reference's annotated genes.

## Usage

You need two inputs.

- Packages: sealed Mamey package folders. Each needs `manifest.json` and exactly one each of `*_cds_table.csv`, `*_3_mibig_per_gene.csv` and `*_2_inventory.csv`.
- The ranking: `ALL_BGC_DEFINITIVE_EVIDENCE_RANK.tsv`, made by `tools/definitive_bgc_ranker.py` from the same packages. See the [ranker guide](DEFINITIVE_BGC_RANKER.md).

```bash
python tools/bgc_functional_logic_workup.py \
  --package-list /path/to/exact_package_paths.txt \
  --definitive-rank /path/to/definitive-ranking/ALL_BGC_DEFINITIVE_EVIDENCE_RANK.tsv \
  --strain-aliases /path/to/STRAIN_ALIASES.csv \
  --out /path/to/functional_logic_workup
```

Name the packages in any of three ways, and combine them if you like:

- `--package PATH`, repeated once per package;
- `--package-list FILE`, a text file with one package folder per line (a line that starts with `#` is a comment; relative paths resolve from where you run the command);
- `--packages-root DIR`, which scans every folder under DIR for `*_cds_table.csv` next to a `manifest.json`.

Prefer `--package-list`. `--packages-root` also picks up old copies of a package. `--strain-aliases` is optional: a CSV with the columns `source_strain,display_strain`. Use a new `--out` folder.

When it works you should see the output files below in `--out`, including `RECEIPT.json` with `"status": "COMPLETE"`. A source strain that appears in two packages stops the run.

## Evidence channels

Each gene has three separate fields:

1. **Direct reference match:** whether the gene has any admitted MIBiG hit, and whether it maps to the dominant reference chosen by the ranker.
2. **Functional annotation logic:** antiSMASH `gene_functions`, `sec_met_domains`, product annotations, gene kind and gene order sort the gene into core, precursor, maturation, tailoring, transport, regulatory, resistance or other.
3. **Architecture-first inference:** a classifier (`mamey.architecture_first`) that does not look at KnownClusterBlast results reads the domain architecture. The output gives its pathway type, confidence, diagnostic markers, reasoning, agreement with the reference and a bounded final call.

Direct similarity and functional logic are not interchangeable. The workup never turns an annotation-only gene into a reference match. It never turns reference similarity into proof of a complete pathway or an exact product.

## Functional reference relationships

- `ARCHITECTURE_CORROBORATES_REFERENCE`: domain architecture, read without KCB results, agrees with the reference family.
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

## Limits

- The tool does not verify `manifest.json` or re-check a package seal. It hashes the manifest.
- The ranking is looked up by `complete_identity`. If two ranking rows share one identity, the last wins. Each BGC takes its contig and region from its first gene row. Check that identities are unique, and that no BGC mixes two loci, before you run.
- Role calls are annotation patterns. A regulator, transporter or resistance annotation is not measured regulation, transport or self-resistance. A table hit is not new alignment evidence. The workup checks the accession format and a non-placeholder subject gene when counting a match; it does not independently verify search completion, source hit provenance or the underlying alignment. A `NO` match flag can reflect missing or rejected input rows, not a verified biological absence. Bind the source search and its evidence separately. MIBiG accession versions are stripped for matching.
- Keep strain aliases unique. Two source strains that map to one display name are not rejected, and their per-strain folders can collide. Check every output identity and folder.
- The tool overwrites named outputs one at a time. A later error can leave partial output or stale files, so use a new folder and keep failed runs apart.
- `SOURCE_HASHES.tsv` hashes the four package input files, not the ranking or alias file. `RECEIPT.json` holds counts and relation labels, not every output hash. Record the SHA-256 of the ranking and alias files with the run.

`COMPLETE` means the tool finished. It is not scientific acceptance.
