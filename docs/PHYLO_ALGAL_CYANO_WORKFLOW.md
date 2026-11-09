# Compare green-algal and cyanobacterial records

Use this page to plan a tree comparison for the green algae *Trebouxia*, *Chlorella* and
*Coccomyxa*, or for cyanobacteria. The bundle has no one-command workflow and no outgroup
registry for these groups. It has one check that you can run on your plan, described below.

A passing check is a technical result. It does not establish organism identity, marker
orthology, correct rooting or scientific acceptance. A label or record name is only a lead.

Terms used here are in the [glossary](GLOSSARY.md). A **hold** is a decision you still owe.
An **evidence channel** is one kind of data, such as a nuclear marker or a plastid marker.
A **compartment** is where the sequence lives in the cell: nuclear, plastid or mitochondrial.
The **ingroup** is the set of taxa you are studying. The **outgroup** is the taxon used to root the tree.

## Steps

1. Write the question and the taxonomic scale you are asking about.
2. List every input you plan to use: sequences, alignments, trees and reports. For each one, note its
   path, SHA-256 and, for a public record, the exact accession and version.
3. Copy `examples/phylo_crossgroup_intake.example.json` to a working folder. Replace every `REPLACE`
   value with absolute paths, hashes and your own labels. Set the top-level `group` and `data_kind`
   (see [the manifest](#fill-the-manifest)); the example ships `"group": "algae"`, which is not a
   `REPLACE` value. [Declare each record](#fill-the-manifest).
4. Run the intake check:

   ```bash
   python tools/phylo_crossgroup_intake.py /absolute/manifest.json --allow-root /absolute/authorized/root
   ```

   Repeat `--allow-root` for each folder that holds the manifest, the input files or the registry.
   Add `--estimate-only` to stat the declared files and estimate scan size without opening them.
   An estimate is not the check. It reads only the schema, the record paths and file sizes, and the
   registry path when `group` is `fungi`. It does not check `group`, `data_kind`, the other record
   fields or any hash. It prints `"status": "ESTIMATE_ONLY"` and exits 0 even when the full check
   would fail. Always run the command without `--estimate-only` before you trust the manifest.
5. Read the JSON the full check prints. A good result has `"status": "HOLD"` and an empty `errors` list.
   `HOLD` is the best status this tool gives. Every entry in `holds` is a decision you still owe.
   For the full check, exit code 0 means `errors` is empty. Exit code 2 means `"status": "ERROR"`;
   fix each line in `errors` and run again. With `--estimate-only`, exit 2 means a path, the schema
   or a size could not be read, and exit 0 says nothing about the rest of the manifest.
6. Settle the holds, then follow the [companion protocol](LLM_COMPANION_TOOL_PROTOCOL.md) before any external
   tool runs. The [phylogenetics workflow](PHYLOGENETICS_WORKFLOW.md) covers the tree itself.

The check reads files and compares hashes. It does not verify organism identity or sequence
content, choose a reference, or authorize computation.

## Fill the manifest

Two top-level fields decide which checks run:

| Field | Allowed values | Notes |
|---|---|---|
| `group` | `fungi`, `algae`, `cyanobacteria` | Anything else is an error. Set it to `cyanobacteria` for a cyanobacterial roster; the example's `algae` raises a hold for a `bacterial` compartment and skips the cyanobacteria review hold. |
| `data_kind` | `marker`, `genome` | Every record's `kind` must equal it. A `marker` manifest also needs a `marker` name. |

Each record needs these fields. Use the example file for the rest. An assembly accession (`GCA_` or
`GCF_`) cannot be declared with `kind` `marker`; use `data_kind` `genome` for it.

| Field | Allowed values | Notes |
|---|---|---|
| `role` | `query`, `ingroup`, `outgroup` | The check flags identical bytes used in opposing roles. |
| `file_scope` | `single_record`, `multi_record`, `archive`, `unknown` | Use `multi_record` for a multi-record FASTA and `archive` for a ZIP. A `multi_record` or `archive` record needs a `record_locator`. |
| `source_format` | `fasta`, `fasta_gzip`, `zip` | `fasta` with `multi_record` counts the header token. `fasta_gzip` needs `multi_record`. `zip` goes with `archive`. |
| `record_locator` | exact header token or ZIP member path | The token must occur once. |
| `member_sha256` | lowercase hex | Required for a ZIP member. |
| `member_format`, `member_record_locator` | `fasta`, header token | Optional, for a multi-record FASTA inside a ZIP member. |
| `sequence_extent` | `single_marker`, `chromosome`, `single_contig`, `whole_assembly`, `unknown` | Your own statement of what the record covers. A chromosome does not mean a complete multi-replicon assembly. A marker manifest with any extent other than `single_marker` raises a hold. |
| `compartment` | `nuclear`, `plastid`, `mitochondrial`, `bacterial`, `mixed`, `unknown` | `unknown` and `mixed` each raise a hold. |

Limits to know:

- Gzip FASTA and ZIP members are read up to 64 MiB. FASTA headers over 64 KiB are refused.
- The tool hashes the whole file, so large files take time. It rechecks the hash after reading.
- Other archive and multi-record formats are not opened.
- It matches versioned GCA, GCF and NG accessions case-insensitively. It does not treat different versions as the same record.
- Two archive members can repeat one accession in their headers and still differ in content. Bind the member path and its hash, not the basename or accession.

## What to settle before you build a tree

**Source.** An antiSMASH results ZIP is not automatically a complete genome or marker. Find the member
you want and its provenance. A missing source is **unavailable**. It is not evidence that the organism
is absent. Keep quarantine and exclusion decisions. Do not swap in a different record.

**Compartment.** Treat nuclear, plastid and mitochondrial trees as separate evidence channels. Their
histories and sampled taxa can differ. Mixed source material can hold more than one symbiont, so a claim
that a record belongs to the photobiont needs independent source review.

**Lineage.** *Trebouxia*, *Chlorella* and *Coccomyxa* each need their own reference roster and scope.
Published studies are examples, not defaults:
[*Trebouxia* photobionts](https://pmc.ncbi.nlm.nih.gov/articles/PMC4204673/),
[*Chlorella*](https://pubmed.ncbi.nlm.nih.gov/20522192/),
[*Coccomyxa* species concepts](https://pubmed.ncbi.nlm.nih.gov/27028195/) and
[green-algal plastids](https://pmc.ncbi.nlm.nih.gov/articles/PMC4189289/).
[Xiong et al. 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12366059/) compare 18S and
single-copy orthologues across Trebouxiophyceae. Their reference set answers their question, not yours.
[Darienko et al. 2015](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0127838) found that
V9 alone did not separate *C. subellipsoidea* from *C. simplex* in their strains. A single marker or a
generic identity threshold does not establish a species.

**Cyanobacteria are bacteria.** Keep their source and reference decisions apart from algae and fungi.
The bundle's 16S workflows and actinomycete taxon maps and presets do not automatically fit them. Do not
apply bacterial species thresholds or outgroups from an unrelated preset. A
[classification study](https://pubmed.ncbi.nlm.nih.gov/36443823/) used phylogenomic and 16S evidence and noted
that 16S is limited at some broader ranks. Similarity to a plastid record does not show that a query is
a cyanobacterial isolate.

**Outgroup.** Record the outgroup and the reason for it. If no suitable reference or outgroup is
supported, record a hold. Do not reuse the fungal registry or the bacterial registry adapter for algae.
Differences between evidence channels are findings to investigate, not proof of a new lineage.

## Examples of records that need reconciling

These show what to check. They do not select an input or an outgroup.

- *Trebouxia* assembly `GCA_000818905.1`: a [Zenodo record](https://zenodo.org/records/23749643) and
  [BioProject PRJNA263654](https://www.ncbi.nlm.nih.gov/bioproject/263654) list it, but the
  [BioSample](https://www.ncbi.nlm.nih.gov/biosample/SAMN03104849) says the sample came from a mycobiont,
  while the [Trebouxia Research Portal](https://trebouxia.net/index.php/genomes) says lichen thallus.
  These descriptions disagree, so purity and contig membership are open.
- *Nostoc* sp. ATCC 53789, assembly `GCA_009873495.1` ([BioProject PRJNA588357](https://www.ncbi.nlm.nih.gov/bioproject/588357)):
  the [genome paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC7118181/) names `CP046703` as the chromosome and
  `CP046704` to `CP046715` as other replicons. A chromosome record alone is not the full assembly.
  [Another project](https://www.ncbi.nlm.nih.gov/bioproject/319598) lists a different assembly under the same strain name.

## Stage checklist

Use this as a review aid for your own data. It is not an automatic pipeline or a marker panel.

| Stage | Green-algal review | Cyanobacterial review | Keep |
|---|---|---|---|
| Question and roster | Which genus is in scope; sample origin; mixed symbionts. | The actual bacterial lineage and source context. | Paths, hashes, accessions, versions, roles, exclusions, unresolved identity. |
| Source and evidence | Nuclear, plastid and mitochondrial identity apart; marker or orthologue question. | Marker, chromosome or multi-replicon assembly. | Member bindings, extent, compartment, tool and reference versions. |
| Comparison design | Marker or orthologue suitability and reference coverage. | Marker or genome route and reference coverage. | Reference rule, ingroup and outgroup reasons, missing data, holds. |
| Alignment and inference | Keep each marker and compartment traceable; review discordance. | Keep loci or genome evidence traceable. | Input and trimmed alignment hashes, parameters, model and support settings, logs, tree. |
| Display | Compare the display roster with the analysis roster and state differences. | Same, without importing algal or fungal decisions. | Gate reports, display binding or an explicit unavailable state, figure review. |

An absent source or an unavailable display tree is a hold, not a zero difference.

## Check an existing tree

Keep the analysis tree, the source alignment (or an explicit unavailable state), the exact tip roster,
the display tree, the exclusions, the metadata and their hashes. Two tools check a tree:

- `python tools/tree_sanity_check.py <tree.treefile> --outgroup <TIP_TOKEN>` checks branch lengths.
  Name the outgroup tip with `--outgroup` (repeat it, or comma-separate, for several tips). A tip
  already labelled `OUTGROUP` is found without it. Each `--outgroup` value gets an `[outgroup-term]`
  line naming the tips it matched; a value that matches no tip fails with `OUTGROUP_UNMATCHED`, even
  when another tip is labelled `OUTGROUP`. For a tree with no outgroup by design, such as a
  midpoint-rooted one, pass `--allow-no-outgroup` instead. With neither, the check fails with
  `NO_OUTGROUP` and skips the branch-length checks. Outgroup branches are exempt from the
  branch-length checks; the `[outgroup-exempt]` line gives the longest one and its share of tree
  depth. A pass does not show that the root is where you intended, so review it. It exits 0 on pass
  and 2 on fail.
- `python tools/tree_trust_audit.py --manifest <manifest.json> --output <out> --gate tools/tree_sanity_check.py`
  audits tree, metadata and render bindings. Run `--help` for the manifest layout.

Add `--snapshot-gate` for an experimental tree-only comparison against declared outgroup tips. Matching
results stay `UNVERIFIED`; a mismatch or a gate failure fails that check. It reads the displayed-tree
snapshot up to 8 MiB and is stricter than the native gate: one tree, parsers that agree, finite non-negative
branch lengths. It can refuse inputs that other workflows accept. It does not protect against a file changing
after the first read.

Render only through the bundle's figure route; see [Figure house rules](FIGURE_HOUSE_RULES.md).
Fungal inputs follow the [fungal guide](PHYLO_FUNGAL_WORKFLOW.md).

## rRNA extraction

For rRNA extraction, see [Barrnap](BARRNAP.md). Run `barrnap --help` to see the models your install
lists. No Barrnap model is a validated algal marker extractor. Keep partial and ambiguous predictions under review.
