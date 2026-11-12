# BiG-SCAPE ingest: known limits

This page lists what the BiG-SCAPE helper tools do and do not check. Read it before you write BiG-SCAPE family (GCF, gene cluster family) context into Mode B cards. Mode B cards are the per-locus evidence write-ups. For the run steps, start with the [GCF workflow](BIGSCAPE_GCF_WORKFLOW.md) and the [companion tool protocol](LLM_COMPANION_TOOL_PROTOCOL.md).

> **Implementation scope:** this page describes the tools as they are. The workflow page is the guide for a new task. The limits below still need your own review. A tool label does not establish scientific acceptance.

## What to run

```bash
python tools/bigscape_ingest_to_mamey.py --db <bigscape.db> --run-id <N> \
  --package <package_dir> --cutoff 0.5 --dry-run
```

- `--db` is a finished BiG-SCAPE 2 database. `--run-id` is required with it and picks one run. Use `--from-tsv <AS_per_BGC_annotation.tsv>` plus `--strain` instead if you only have the portable table.
- `--package` finds the triage CSV and the `*_ModeB.md` cards. `--triage` and `--cards-dir` override it.
- `--dry-run` writes no card. With `--db` the database is opened read-only, and a path that does not exist is refused with `ERROR: not an existing BiG-SCAPE database` before any connection, so no empty database file is created. The "updated" count then means proposed changes. Check it, then run again without `--dry-run`.
- A real run edits the cards in place. It does not add GCF columns to the triage CSV.
- Never point it at sealed or canonical cards. Copy them first and review the copy.

## Run and family identity

The ingest tool takes region-level members of the run and cutoff you name, and it rejects conflicting family assignments. A family ID means something only together with its run and cutoff, so the tool joins all three. A family ID alone is not a key across runs. The tool does not check that the run finished or where its references came from.

The tool maps strain plus BGC alias to a normalized locator. Be aware of these behaviors:

- Duplicate entries in the triage file overwrite earlier ones.
- A locator with no strain is accepted as a fallback.
- Package discovery takes the first matching triage CSV and card folder.

Name the triage file and input folder yourself. Keep strain, full contig or node, region and alias for every locus. A matching normalized locator does not prove two records are the same biological locus.

## Nearest reference and status labels

Family membership comes from the run and cutoff you named. The nearest-MIBiG distance does not. The function that computes it reads the whole distance table without filtering by run or parameters. It can report a nearest reference from a different comparison. Hold that field until you have a distance record for the run you selected.

Status labels:

- `KNOWN` means a parsed MIBiG accession is in the same family.
- `NO_MIBIG_MEMBER` means no MIBiG member is in the family. It is not `NOVEL`.
- `UNKNOWN` means the TSV status was blank or not recognized.
- In `--from-tsv` mode an old `NOVEL` value is read as `NO_MIBIG_MEMBER`.

`NO_MIBIG_MEMBER` is limited to the reference panel that was loaded. It does not mean "no characterized analog." It does not prove the panel was complete. On cohort-only data, report within-panel membership and make no novelty claim. A missing or malformed MIBiG name index gives `?` for compound names.

`--from-tsv` mode has no list of co-members. In `--db` mode, an empty co-member list describes only the selected family. It does not show that the organism is rare or that related loci are absent elsewhere.

## Card writes

A real run replaces the existing fenced GCF block in a card. If there is none, it inserts the block after the first heading that begins `## 8` or `## §8`. If there is no such heading, it appends the block at the end. Section numbers in current Mode B profiles can mean something else, so check where the block landed.

The block can display a nearest-reference distance, but the lookup does not filter by the selected run or cutoff. Hold the value until you verify its source against the selected run as described above. Distance 0 does not show identical sequences or the same product.

- Each card is replaced atomically. The batch is not. A failure can leave some cards changed.
- There is no check of the original file hash and no record of input or output hashes.
- A card with no matching locator is skipped. Exit code 0 can mean every card was skipped. Read the updated, skipped and context counts.
- Repeating the run gives the same text. That does not prove the source or version is the same.

## Pipeline wrapper

`tools/bigscape_pipeline.py` runs BiG-SCAPE and can then ingest.

- It checks that the run you named exists, or that exactly one new run appeared.
- `--skip-cluster` and a shared or existing database both need `--run-id`.
- Prep needs `--strictness {loose,relaxed,strict}`, or `--allow-mixed` with `--mixed-justification`. `--assume-strictness` is passed through when given. A missing or conflicting choice stops the run before staging. `PREP_STRICTNESS_POLICY.json` records the choice.
- Loading MIBiG in batches (`--chunk-mibig`) is held. Do not use it without a review.
- `--ingest-package` writes cards with no approval step. Your run plan is the approval, not the flag.
- Without MIBiG, the table exporters still run. Their file names and status fields do not show chemical novelty.

## antiSMASH join

`tools/antismash_bigscape_join.py --gbk-dir <dir> --bigscape-tsv <tsv> --out <tsv>` joins GBK files to families. It checks the family namespaces. It matches GBK names on the first underscore-separated part of the strain name plus a file name locator.

- The optional `--kcb-dir` parser keys hits by strain and region only. It takes the first accession and percent it finds. Duplicate region keys across contigs can overwrite each other.
- Its agreement label compares "has a KCB hit" against a family status of `KNOWN`. It does not compare accessions or methods. A missing KCB value is unmeasured, not a disagreement.
- The output file is overwritten. It can hold only a header and still exit 0. It records no hashes.

## BiG-SLiCE

`tools/bigslice_query.py` follows the [BiG-SLiCE workflow](BIGSLICE_WORKFLOW.md). The adapter supports BiG-SLiCE 2.0.0 with database schema 1.0.1. Other versions and models are held.

- Use a fresh `--out`, a writable query working model, an exact run and clustering choice, reviewed runtime and model profiles, and four-part locus identities from the source.
- The query writes into the working model as well as the export folder.
- Native completion needs the report and database read back. A zero exit from the child process is not enough.
- The adapter tests are synthetic. They do not show your local model works.
- Results describe the model you selected. Do not carry reference or cohort counts from one model to another.
