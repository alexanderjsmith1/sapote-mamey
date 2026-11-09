# Mode B data-availability inventory

`modeb-availability` lists which evidence you have for each biosynthetic gene cluster (BGC) before you write a Mode B card. It writes tables. It does not write prose or judge the biology.

This step is optional. Use it when you gather evidence from several folders and want to know which cards are ready to write. For the step-by-step card recipe, see the [Mode B walkthrough](MODE_B_USER_WALKTHROUGH.md). Terms such as KnownClusterBlast (KCB), RG-GMCI and GCF are in the [glossary](GLOSSARY.md).

Run every command from the bundle root.

## 1. Run it

```bash
python mamey_run.py modeb-availability \
  --inventory project/per_bgc_inventory.tsv \
  --source-root package=project/runs \
  --source-root blastp=project/evidence/blastp \
  --evidence-index project/curated_evidence.tsv \
  --out project/modeb_availability
```

- `--inventory` is required. See section 2.
- `--source-root LABEL=PATH` scans a folder recursively for evidence files. Repeat it for more folders.
- `--evidence-index PATH` reads a table you wrote that names each evidence file. Repeat it for more tables.
- `--out` is the output folder.

You can use either evidence option, or both. With neither, the command still runs. Every stream shows as absent except the inventory's own identity row.

You should see a JSON manifest on screen with `"status": "PASS"`, your strain and BGC counts, and the output files. Exit code 0 means the files were written. It does not mean the cards are ready. A bad inventory raises an error that names the row, and nothing is written.

## 2. The inventory file

The inventory is a CSV or TSV with a header row and one row per BGC. The package already has one: `<strain>_2_inventory.csv`. Use it as is, or any table with these columns:

```text
Strain    BGC_ID    Contig                          antiSMASH_Region
EXAMPLE   BGC001    NODE_7_length_120000_cov_42.5   region001
EXAMPLE   BGC002    NODE_9_length_90000_cov_30.1    region002
```

The tool also accepts common header spellings such as `strain_id`, `bgc`, `contig`, `node_id` and `region`. An optional `products` column carries through to the output.

A BGC is identified by strain, full contig and region. The `BGC###` alias is secondary. A row without a contig or region cannot be matched exactly, and its card stays on hold. Each strain and alias pair, and each exact locus, must appear once.

Identity rules, in short:

- A bare `NODE_7` is partial. It is not a complete identity.
- Accessions keep their version. `CP103060.1` and `CP103060.2` are different contigs.
- If two fields in one row disagree, the row is an error or stays unbound. The tool never picks one.
- The tool upper-cases SPAdes `NODE_` contig names in its outputs. Compare against the inventory by eye if you search them.

## 3. How evidence is matched

Each evidence file gets one of five states:

| State | Meaning |
|---|---|
| `EXACT_LOCUS` | Strain, full contig and region all match the inventory. |
| `ALIAS_BOUND` | Strain and BGC alias match. The file does not establish the contig. |
| `STRAIN_ONLY` | It describes the strain or cohort. Do not attach it to one BGC. |
| `UNBOUND` | It cannot be attached to the inventory without a crosswalk. |
| `ABSENT` | No matching file was found in the folders you gave. |

`UNBOUND` and `ABSENT` describe your files. They say nothing about the biology.

An evidence index is a TSV or CSV with a header. Required columns are `channel` and `source_path`. `channel` is a stream name such as `blastp_per_gene`, `domains_hmm` or `kcb_mibig`; the full list is in `mamey/data/mode_b/modeb_evidence_stream_contract.json`. Add the identity columns (`strain`, `bgc`, `contig`, `region`) so the row can bind exactly. Optional columns are `freshness_state`, `record_count` and `notes`. A relative `source_path` is read from the index's folder, and a missing file is an error. Mark a BLASTp file `CURRENT` in `freshness_state` only after you checked it belongs to this package.

A folder scan reads file and folder names, and the header of large tables, to guess identity. It does not guess a contig from an arbitrary folder name. Where the guess is weak, use an index.

## 4. Outputs

The command writes six fixed filenames under `--out`:

- `MODEB_AVAILABILITY_SUMMARY.md`: counts of ready and not-ready BGCs, and how many BGCs each stream reaches. Open this first.
- `modeb_bgc_availability.tsv`: one row per BGC, with `work_state`, `writing_gate`, `promotion_gate` and three columns for each stream. Open this second.
  - `<stream>_state` is the strongest binding state found for that stream.
  - `<stream>_records` counts only the records at that state. Records at weaker states are not added to it.
  - `<stream>_records_by_state` lists the records at every state, strongest first, for example `EXACT_LOCUS=1;UNBOUND=9`. It is blank when no file was found.
  Before you read coverage from these counts, open `modeb_evidence_observations.tsv` for the records behind them.
- `modeb_strain_availability.tsv`: the same counts per strain.
- `modeb_evidence_observations.tsv`: one row per evidence file or table group.
- `modeb_section_plan.tsv`: a planning table over the 30 legacy sections. It is not the card outline. Use the sections your profile emits.

`modeb_section_plan.tsv` has one row per BGC per planning section (sections 1 to 30). Its `section_state` column takes one of three values:

- `EVIDENCE_AVAILABLE_REQUIRES_INTERPRETATION`: at least one stream that supports the section is bound at `EXACT_LOCUS` or `ALIAS_BOUND`. The evidence exists. You still write the interpretation.
- `CONTEXT_ONLY_DO_NOT_LOCALIZE`: the only support is `STRAIN_ONLY`. Use it as strain context. Do not attach it to this BGC.
- `WRITE_EXPLICIT_GAP_OR_HOLD`: no supporting stream is bound. State the gap in the card or hold the card.

The columns `available_streams` and `context_only_streams` name the streams behind each state. The tool never writes the interpretation. The planning numbers are not your profile's section numbers, so match them to the emitted template yourself.
- `modeb_availability_manifest.json`: hashes, byte counts and counts.

Existing files with these names are overwritten one by one. Use a new `--out` folder for each run.

The outputs hold absolute paths to your local files. Remove them before you share the folder.

## 5. Writing and promotion gates

Each BGC row carries two gates.

`writing_gate` decides whether you can start a draft:

- `PASS_FOR_GAP_AWARE_AUTHORING`: the row has a full contig and region, and a gene-level source bound at `EXACT_LOCUS` or `ALIAS_BOUND`. You can draft, with every gap stated.
- `HOLD_IDENTITY_UNRESOLVED`: the contig or region is missing. Fix the inventory.
- `HOLD_MISSING_GENE_LEVEL_SOURCE`: no gene-level source is bound. Add one.

`promotion_gate` decides whether the card can move toward review:

- `ELIGIBLE_FOR_SEPARATE_INTERPRETIVE_REVIEW`: per-gene BLASTp is bound and marked `CURRENT`.
- `HOLD_BLASTP_UNAVAILABLE_OR_UNBOUND`: no per-gene BLASTp is bound.
- `HOLD_BLASTP_FRESHNESS_UNVERIFIED`: BLASTp is bound but not marked `CURRENT`.

A passing gate checks the inventory and the file bindings only. It does not compare assembly hashes, confirm the source package, or show the biology is right. Run `verify-modeb` with your chosen profile before you call a card finished.

A `HOLD` row means do not write that card as finished yet. A draft with the gap stated is allowed when `writing_gate` passes.

`work_state` summarizes the row: `EVIDENCE_RICH_REVIEW_CANDIDATE` (BLASTp, domains and locus map all bound), `GAP_AWARE_REVIEW_CANDIDATE`, or `NEEDS_EVIDENCE_ASSEMBLY`.

## 6. Readiness classes

The tool does not output these. You assign them by hand to each evidence stream before the content check of a card:

- `READY_BOUND`: use it now.
- `AVAILABLE_UNINGESTED`: the file exists. Ingest it before you write.
- `NEAR_READY_ACTIVE_RUN`: a run is still going. Wait, ingest, and hold the card.
- `PRACTICALLY_ATTAINABLE`: you can get it. Get it before the content check.
- `STRUCTURALLY_UNAVAILABLE`: it cannot exist for this locus. State the reason in the card.
- `NOT_APPLICABLE`: it does not apply. Say why and close it.

Only the first, fifth and sixth may stand in a finished card. `Pending` is not an acceptable final cell. A missing result in a finished card is a typed statement of the state, such as `not run` or `unbound`, with the reason. It is never a zero.

The finished-card BLASTp table, with one named-match row per gene and nr, ClusteredNR and Swiss-Prot kept apart, is defined once, in the [current50 contract](MODEB_CURRENT50_V2_CONTRACT.md). The default full48 profile puts that table in section 4; current50_v2 puts it in section 50.

## 7. What this does not show

Strain phenotype, ecology, thesis or literature context may support the context sections of a card. None of it may be attributed to a BGC without a separate exact-locus link and experimental evidence. Availability and provenance do not establish identity, production, activity, novelty or cause. Similarity is not identity. Capacity is not production. Missing or unbound evidence is not biological absence.
