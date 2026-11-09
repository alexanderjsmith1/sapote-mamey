# BiG-SCAPE cohort reports and network views

This page turns one finished BiG-SCAPE run into cohort tables, interactive network views and gene-order figures. Run the [cohort walkthrough](BIGSCAPE_COHORT_WALKTHROUGH.md) first. It produces the database (`cohort.db` below) and shows how to find the run ID.

## Glossary

- **BiG-SCAPE:** the program that groups similar biosynthetic regions into families.
- **BGC:** biosynthetic gene cluster. Every BGC here is named `strain / full node-or-contig / region / BGC alias`.
- **GCF:** gene cluster family. One BiG-SCAPE run and cutoff create it. Family IDs mean nothing outside that run and cutoff.
- **Cutoff:** the BiG-SCAPE distance limit for joining two regions into a family. The report default is 0.3.
- **MIBiG:** the public database of characterized clusters. A comparator is one of its records used for bounded comparison.
- **Direct edge distance:** the BiG-SCAPE distance for a recorded pair. It is not sequence identity.
- **Class code:** a broad label for a family, such as `NRPS` or `T1PKS`. Other terms are in the [glossary](GLOSSARY.md).
- **Coherent component:** a dense local block of comparator-matched genes inside a larger region.
- **Whole-region fraction:** comparator-matched CDS divided by every CDS in the antiSMASH region.
- **Provenance binding:** a relative evidence locator plus the SHA-256 hash of the file that was read.
- **Claim ceiling:** the strongest interpretation the admitted evidence allows.

## Step 1. Build the cohort tables

`tools/bigscape_cohort_report.py` reads one run from the database. It opens the file read-only. It needs these inputs:

- `--db`: the BiG-SCAPE SQLite database.
- `--run-id`: a finished run in that database.
- `--cutoff`: optional, default 0.3.
- `--host-table`: a TSV with columns `strain`, `genus` and `host_as_deposited`. One row per strain. Example row: `DEMO-A`, `Streptomyces`, the host text as deposited.
- `--crosswalk`: a TSV with columns `strain`, `node_num`, `region` and `legacy_bgc`. One row per region. Example row: `DEMO-A`, `7`, `region001`, `BGC004`. The `*_2_inventory.csv` file in each package folder binds each region to its contig and alias; build the crosswalk from it.

```bash
python tools/bigscape_cohort_report.py \
  --db cohort.db --run-id 1 --cutoff 0.3 \
  --host-table strain_genus_host.tsv \
  --crosswalk node_region_bgc_crosswalk.tsv \
  --out cohort_report
```

Use a fresh, empty `--out` folder. The command prints nothing on success. Success is exit 0 and these files in `cohort_report/`:

- `BIGSCAPE_LOCUS_MEMBERSHIP.tsv`: one row per locus and family.
- `BIGSCAPE_GCF_SUMMARY.tsv`: one row per family.
- `BIGSCAPE_STRAIN_PAIRWISE_JACCARD.tsv`: shared families per strain pair.
- `BIGSCAPE_DIRECT_EDGES.tsv`: BiG-SCAPE distances between family members.
- `BIGSCAPE_COHORT_REPORT_RECEIPT.json`: the run, the source hashes and the counts.

Exit 2 means the tool refused and printed the reason on stderr. Pairwise Jaccard compares sets of exported family IDs. It is not a whole-genome or measured-chemistry comparison.

If the database has no `distance` or `edge_params` table, `BIGSCAPE_DIRECT_EDGES.tsv` is empty and the run still exits 0. An empty file means no distances were recorded, not no links.

### Checks before export

The tool refuses to export when the run cannot be trusted. It exits 2 with `RUN_SCOPE_GATE` in these cases:

| Message or state | Meaning | What to do |
|---|---|---|
| `RUN_SCOPE_GATE`, run ID absent | The run ID is not in the `run` table. | List runs with `sqlite3 cohort.db 'select id, end_time from run;'` and pick one. |
| `RUN_SCOPE_GATE`, blank `end_time` | The run did not finish. | Pick a finished run, or rerun BiG-SCAPE. |
| `RUN_SCOPE_GATE`, no families at this cutoff | The run has families at other cutoffs only. | Pass a cutoff the run used. |
| `run_scope_state = VALID_EMPTY_COMPLETED_RUN` | A finished run declared this cutoff and has no families. | Compare the admitted record count with your roster. An empty table is not a biological result. |
| Receipt status `RUN_COMPLETION_UNVERIFIED` | The database has no `run` table, or no `end_time` column, so completion cannot be proved. | Treat the output as unverified. |

The tool checks SQLite integrity. The receipt hashes the main database file, so copy a closed, checkpointed snapshot and keep it unchanged while the tool runs. The receipt covers the database, host table, crosswalk and overlay. It does not cover the reviewed-subtypes TSV, the vocabulary, the code or the outputs. Keep your own hashes of those.

### Aliases

The tool never guesses a BGC alias. The base crosswalk joins on the number in a contig named `NODE_<n>_...` plus the region number. A contig with any other name gets no alias from the base crosswalk, and public-accession contigs are the usual case. That locus is exported as `UNRESOLVED_BGC_ALIAS` with an identity hold. Two ways to handle it:

- `--require-complete-alias`: exit 2 and write nothing if any locus lacks an alias. Use it when every locus must be named.
- `--alias-overlay ALIAS_RECOVERY_CROSSWALK.tsv`: supply the missing aliases. Rows are keyed by `strain`, `full_node_or_contig` and `region`. Only rows with status `RESOLVED_EXACT_CURRENT_PACKAGE` whose recorded identity matches are admitted. A held overlay row stays held.

Strain names come from the host table, the crosswalk and the overlay. For each GBK filename the tool takes the longest exact `<strain>_` prefix and parses the rest as the full node-or-contig and `regionNNN`. A record whose name matches no admitted strain is left out and counted in the receipt. Two equal-length matches stop the run.

### Class codes

Every family row carries `class_code`, `class_nickname` and `reviewed_subtype_code`. Definitions come from `mamey/data/bigscape_class_vocabulary.json`. The tool derives a family's code from the antiSMASH labels of its members. Two or more different informative codes give `MIX`. All members unresolved gives `UNK`. A displayed code does not mean every member has the same class.

`reviewed_subtype_code` stays blank unless you pass `--reviewed-subtypes` with a TSV that has the columns `family_id`, `reviewed_subtype_code`, `full_name`, `plain_language_meaning`, `source_basis` and `claim_ceiling`. A reviewed subtype is your interpretation. The tool does not check it.

To write the class key as Markdown, run the command below. A copy ships as [the class key](BIGSCAPE_CLASS_GLOSSARY.md), so write to a new path.

```bash
python tools/bigscape_class_glossary.py --out my_class_key.md
```

## Step 2. Draw interactive network views

```bash
python deliverable_tools/bigscape_network_widget.py \
  --membership cohort_report/BIGSCAPE_LOCUS_MEMBERSHIP.tsv \
  --summary cohort_report/BIGSCAPE_GCF_SUMMARY.tsv \
  --pairwise cohort_report/BIGSCAPE_STRAIN_PAIRWISE_JACCARD.tsv \
  --direct-edges cohort_report/BIGSCAPE_DIRECT_EDGES.tsv \
  --out cohort_widgets --require-complete-alias
```

It writes two files to `cohort_widgets/`. Open `GCF_NETWORK_EXPLORER.html` in a browser to see the family networks. Open `STRAIN_SHARING_NETWORK.html` for the strain-to-strain view. Use a fresh `--out` folder, because the tool overwrites files with these names. Each family view shows the family ID, cutoff, direct edge distance, genus, host metadata, boundary state and claim ceiling. A contig-edge locus has a distinct outline. That is a boundary caution, not a completeness call.

Labels depend on how many loci a family view shows:

- One to three loci: compact `strain BGC-alias` labels on every node.
- Four to eight loci: strain-only labels in side columns with leader lines.
- Nine or more: only the focal strain is labeled.

Every node keeps its full `strain / full node-or-contig / region / BGC alias` identity in hover and click detail. The legend below each network lists the class codes present, with an expandable full key.

### Add a family section to an existing HTML report

The tool can insert a family section into a per-strain `REPORT.html` from `tools/strain_level_bgc_logic.py`. It reads the source report and writes the integrated copy to `--report-out`. `--report-out` and `--report-receipt-out` must be new files. The tool refuses, with `REPORT_INTEGRATION_GATE` and before it writes anything, an existing file at either path, the two paths naming the same file, or either one naming the source report, an input table, the MIBiG JSON folder or one of the two explorer pages. The insertion point is the report's `Claim ceiling` heading. The tool refuses a report without that heading and refuses a second integration block. Each selected family must contain the focal strain, and every selected locus needs a complete alias.

```bash
python deliverable_tools/bigscape_network_widget.py \
  --membership cohort_report/BIGSCAPE_LOCUS_MEMBERSHIP.tsv \
  --summary cohort_report/BIGSCAPE_GCF_SUMMARY.tsv \
  --pairwise cohort_report/BIGSCAPE_STRAIN_PAIRWISE_JACCARD.tsv \
  --direct-edges cohort_report/BIGSCAPE_DIRECT_EDGES.tsv \
  --out cohort_widgets --require-complete-alias \
  --report-html source_report.html --report-out integrated_report.html \
  --strain DEMO-A --family-id 12 --family-id 47
```

### Optional MIBiG comparator context

If the source report already has one MIBiG Comparator Identity Summary, add `--mibig-json-dir` and `--report-receipt-out`. The folder must hold accession-named MIBiG JSON files such as `BGC0000001.json`. Only `biosynthesis.classes` is read. A missing class stays visibly unavailable.

```bash
python deliverable_tools/bigscape_network_widget.py \
  --membership cohort_report/BIGSCAPE_LOCUS_MEMBERSHIP.tsv \
  --summary cohort_report/BIGSCAPE_GCF_SUMMARY.tsv \
  --pairwise cohort_report/BIGSCAPE_STRAIN_PAIRWISE_JACCARD.tsv \
  --direct-edges cohort_report/BIGSCAPE_DIRECT_EDGES.tsv \
  --out cohort_widgets --require-complete-alias \
  --report-html source_report.html --report-out integrated_report.html \
  --report-receipt-out integration_receipt.json \
  --strain DEMO-A --family-id 12 \
  --mibig-json-dir mibig_json
```

Every enhanced table says: `Characterized comparator context. These MIBiG fields describe the characterized comparator only and do not predict activity or mechanism for the focal locus.` Activity, mechanism, evidence status and literature fields read `not verified in current evidence` unless you add a curated table with `--curated-comparator-context`.

The curated TSV has one row per exact MIBiG accession. It carries the class, the activity and mechanism fields, a verification status for each, an evidence status, the PMID, PMCID and DOI, the article title and URL, an abstract-level locator, hold reasons, source hashes, the curator and the review date. Each status is `VERIFIED_PRIMARY_LITERATURE` or `NOT_VERIFIED_CURRENT_EVIDENCE`. An unverified field holds the literal text `not verified in current evidence`. A row with an unresolved field needs a hold reason. The class must match the bound MIBiG JSON, and every hash must be a valid SHA-256.

### How to read comparator badges and citations

A comparator is a characterized reference cluster. Its literature describes that reference, not the focal locus.

- **Activity + mechanism verified:** both fields were found in bound primary literature for the comparator.
- **Activity verified; mechanism unresolved:** the reported activity was found, but no mechanism or target was established.
- **Comparator context unresolved:** a comparator accession exists, but the curated table does not verify the requested field.
- **No admitted comparator:** the row has no comparator accession. This is not evidence that no related cluster exists.
- **A dash:** a compact unresolved marker. Its hover title keeps the exact machine status.

Each citation link comes with a PMID and a local evidence locator. The locator is relative to the curated table, and its SHA-256 must match the actual file. A hash for a missing file is rejected.

Example: `BGC0000001` has a paper that reports antibacterial activity but no target. The activity cell may be verified and linked while the mechanism cell stays a dash. That does not make `DEMO-A / NODE_7_length_47000_cov_20.0 / region001 / BGC004` antibacterial.

### Whole-region and coherent-component metrics

An antiSMASH region can merge more than one biological neighborhood. Keep the whole-region fraction. Add a local component view only when gene order supports a coherent block of comparator matches.

Example: 25 of 47 CDS match, so `25 / 47` is the whole-region result. If 24 matches fill genes 1 to 26 and one match is an outlier, the component view is `24 / 26 (92.3%)`, genes 1 to 26, plus one outlier. The higher local percentage does not replace `25 / 47`. It gives pathway-family context while a hold such as `OVERMERGED_REGION_COMPONENT_BOUNDARIES_REQUIRE_REVIEW` stays open. The component tool writes that hold in the `segmentation_hold` column when the block is smaller than the region or a match lies outside it. Otherwise it writes `NO_SEGMENTATION_HOLD`. Report core markers elsewhere in the region separately. The `core_completeness_status` column checks type II PKS markers only (KS, CLF, ACP). Ignore it for other classes. Their presence does not prove the product or a complete pathway.

Build a component row from a per-gene evidence table. `functional_evidence.tsv` below is `ALL_GENE_FUNCTIONAL_EVIDENCE.tsv` from the functional workup ([BGC_FUNCTIONAL_LOGIC_WORKUP.md](BGC_FUNCTIONAL_LOGIC_WORKUP.md)). The tool needs its columns `complete_identity`, `gene_order`, `dominant_reference_gene_match` and `dominant_mibig_accession`. It writes the one-locus extract to `--evidence-extract` and the result row to `--out`. Both must be new files, different from each other and from `--evidence-tsv`. The tool checks the identity, gene order and comparator match before it writes, so a refused run leaves neither file. `evidence_sha256` is the hash of the extract as written.

```bash
python deliverable_tools/mibig_component_context.py \
  --evidence-tsv functional_evidence.tsv \
  --identity "DEMO-A / NODE_7_length_47000_cov_20.0 / region001 / BGC004" \
  --mibig-accession BGC0000001 \
  --evidence-extract evidence/sources/DEMO-A_NODE_7_length_47000_cov_20.0_region001_BGC004.tsv \
  --evidence-locator sources/DEMO-A_NODE_7_length_47000_cov_20.0_region001_BGC004.tsv \
  --out evidence/comparator_component_context.tsv
```

Pass that table to the widget or batch tool with `--comparator-component-context`. The renderer checks the identity, the arithmetic, the relative locator, the file and its hash before it shows the row.

## Batch enrichment without changing source reports

`deliverable_tools/batch_mibig_comparator_context.py` finds every file named `REPORT.html` under `--report-root`, such as the per-strain reports from `tools/strain_level_bgc_logic.py`. It prepares all enhanced copies in memory, then writes them to `--out-root`. Each source report needs one compatible MIBiG summary block. An already enriched or malformed report stops the whole batch before anything is written.

```bash
python deliverable_tools/batch_mibig_comparator_context.py \
  --report-root authoritative_reports \
  --out-root enriched_report_copies \
  --mibig-json-dir mibig_json \
  --curated-comparator-context evidence/comparator_context.tsv \
  --comparator-component-context evidence/comparator_component_context.tsv \
  --receipt-out enriched_report_copies/BATCH_RECEIPT.json
```

Use an empty `--out-root` outside the report root and every evidence folder. Put the receipt inside it under a name no report or input uses, because the receipt path is not protected against overwriting a source file. The tool finds reports by filename, so compare the list it found with your intended roster. Success prints JSON with `status` and `report_count` and exits 0. If a later write fails, the output folder can hold a partial copy. Keep it, fix the input and rerun into a new folder. Read `BATCH_RECEIPT.json` for what was written, not the folder listing.

The receipt records report locators, hashes and row counts. Its source hashes are taken after each write. Record your own hashes of the inputs before the run.

## Static gene-order and GCF figure

`deliverable_tools/bigscape_gene_domain_context.py` draws one family. Bind every member to its exact region GBK first. It aligns gene direction on a shared anchor, summarizes antiSMASH domains, shows direct BiG-SCAPE distances and computes protein 5-mer similarities. These are comparison aids, not BLAST identities.

```bash
python deliverable_tools/bigscape_gene_domain_context.py \
  --membership cohort_report/BIGSCAPE_LOCUS_MEMBERSHIP.tsv \
  --direct-edges cohort_report/BIGSCAPE_DIRECT_EDGES.tsv \
  --family-id 12 --focal-strain DEMO-A \
  --gbk-dir exact_region_gbks --out-dir gcf_context \
  --figure-png gcf_context/GCF_0012_CONTEXT.png \
  --figure-pdf gcf_context/GCF_0012_CONTEXT.pdf
```

The figure has three linked views: gene order with domains, the family network, and domain counts. Every locus carries its full identity. Open the PNG and every PDF page before you use them.

### Stacked locus maps

`deliverable_tools/stacked_locus_map.py` draws a query-and-comparator locus panel from a JSON spec. The spec holds track-relative base-pair coordinates, gene roles and optional protein-identity links. Reverse a comparator in the spec when its homologous segment runs the other way.

```bash
python deliverable_tools/stacked_locus_map.py \
  --spec exact_locus_map.json \
  --out-prefix figures/exact_locus_map \
  --receipt figures/exact_locus_map_receipt.json
```

It writes SVG, PNG and PDF files. The query identity sits outside the gene track. If the labels cannot be placed without collisions, the tool exits without claiming success. The roles and links in the spec are your evidence-bound input. The map is comparative context only.

## Using a browser assistant

Open a generated HTML copy in a current browser, or in a browser assistant that can read local files. Use it to check navigation and layout, not as evidence.

1. Confirm the page has one comparator-context block and one GCF integration block.
2. At laptop width, confirm the wide comparator table scrolls sideways.
3. Tab through the citation links. Every dash and badge needs an accessible status label.
4. Hover or click each network node. The full locus identity should appear.
5. Compare the displayed counts with the JSON receipt. If they differ, hold delivery and regenerate.

Do not paste private paths, credentials or unpublished identifiers into an assistant prompt.

## Common mistakes

- Treating comparator activity as focal-locus activity.
- Replacing a whole-region denominator with a favorable component denominator.
- Calling a region complete because minimal core markers are present.
- Reading a small BiG-SCAPE distance as percentage identity.
- Guessing a BGC alias, or accepting a displayed identity that disagrees with its component fields.
- Trusting a recorded hash without confirming the evidence file exists.
- Writing enriched HTML back into the source report folder.
- Using a figure or PDF that was rendered but not opened.

## Interpretation

Family membership and direct edge distance are region-similarity context for one run and cutoff. They can point to genes worth comparing. They do not establish pathway completeness, a shared product, expression, production, activity, novelty, enrichment, host adaptation or physical linkage across contigs. Host comparisons need genus-aware sampling. A complete alias is a required join, not scientific approval.
