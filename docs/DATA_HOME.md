# Data home: where results live, how they get there, how to find them

Every result a paper or report relies on lives in one folder: the user's **User Strain Master**.
The bundle ships the commands that create it, fill it, check it and read it.
Any person or assistant follows the same route, so everyone finds the same file.

## The homes

| Home | What belongs there | Who writes |
|---|---|---|
| The bundle | Code, docs and shipped reference seeds. Never study data. Post-seal output never goes inside a sealed bundle. | Release owner, at a cut |
| User Strain Master | A byte copy of every record and result a paper uses, each with its SHA-256 and original path. | Only `strain-master apply`, after a different chat's `verify` |
| Record homes | The tables where records are edited (strain metadata, hosts, exclusions, rulings). The master holds copies of them. | An accepted record edit through the inbox, with a backup and a CHANGELOG line |
| Raw stores | Large raw inputs filed once and never edited: antiSMASH ZIPs of record, genome FASTA, sealed packages too large to copy. Named in the master's settings. | Intake, once |
| Asset registry | Machine-level tool assets: HMM sets, BLAST and MIBiG databases, conda environments. Not study data. | Whoever installs the asset |
| Working folders | Where work happens. Only the finished result moves on, through the inbox. | Anyone |

## Six principles

1. **One home per fact.** Each field has one authoritative table, its record. Every other table that shows it is built from the record by a script and never edited by hand.
2. **The master holds copies, never edits.** Records are edited at their home, then the copy is submitted again.
3. **A fixed layout.** The top level is `00 Inbox` and `01 Strains` to `07 Papers`. Each area allows only the subfolders in the master's `LAYOUT.md`. The check fails on anything else.
4. **One way in.** A result is submitted to `00 Inbox/`. A different chat verifies it against a fixed checklist. Only then is it applied, which writes its README line and a CHANGELOG line. Every step is booked in `00 Inbox/INBOX_LEDGER.tsv`.
5. **One way to look.** Read the area README, then `LAYOUT.md`, or run `strain-master where`. The bundle's resolver reads the same layout.
6. **Check every round.** Run `strain-master check` after every import and before anything is handed over, and report its RESULT line.

## The layout

`Source tables` holds copied records. `Built` holds tables a script makes from them. `*` means one folder per item. Every area may also hold `Superseded/`.

| Area | Subfolders |
|---|---|
| `00 Inbox` | `Done`, `Returned`, one folder per open submission, and `INBOX_LEDGER.tsv` |
| `01 Strains` | `Source tables`, `Figure rosters`, `Built` |
| `02 Bioassays` | `Raw plate reader`, `Plate maps`, `Readings`, `Figure data`, `Rulings`, `Scripts`, `Audit` |
| `03 Genomes` | `Source tables`, `16S rRNA`, `TYGS dDDH`, `ANI` |
| `04 Gene clusters` | `Source tables`, `antiSMASH`, `Mamey packages`, `Mode B cards`, `BLASTp evidence`, `Gap rescue`, `BiG-SLiCE`, `BiG-SCAPE`, `Conserved regions`, `Protein space` |
| `05 Trees` | `Source tables`, one folder per tree |
| `06 Figures` | one folder per figure family |
| `07 Papers` | `ToC`, `Fact sheets`, `Rulings`, `Glossary`, `Scripts`, one folder per paper |

Root files: `00 README.md`, `LAYOUT.md`, `CHANGELOG.md`, `strain_master.json`. A master may list more in its own `LAYOUT.md`.

## Where Mamey outputs land

| Output | Folder | Rule |
|---|---|---|
| antiSMASH result ZIP | `04 Gene clusters/antiSMASH` (kind `antismash_zip`) | Named `<strain>.zip`. A genome's identity is the SHA-256 of this ZIP. Flavored results go in `strict/`, `relaxed/` or `loose/`. Too large to copy: leave it in a raw store. |
| Sealed package | `04 Gene clusters/Mamey packages` (kind `mamey_package`) | The Complete_Package ZIP exactly as sealed. Never extract or edit inside. |
| Mode B card | `04 Gene clusters/Mode B cards` (kind `modeb_card`) | The authored card and its `verify-modeb` result, both submitted. |
| BLASTp evidence | `04 Gene clusters/BLASTp evidence` (kind `blastp_evidence`) | Raw Hit Table CSV or XML2 as downloaded, before any summary. |
| Gap-rescue screen | `04 Gene clusters/Gap rescue` (kind `gap_rescue`) | One run of record per genome. A screen, not adjudicated. |
| Tree | `05 Trees/<tree name>` | Only a complete build: `.iqtree`, `.log` with "Total wall-clock time", `.contree`, `.treefile`. |
| Figure | `06 Figures/<figure family>` | Render, plotted data and caption, from a sealed route. |

A kind name can stand in for the folder in `--folder`. A master's settings may move any kind.

## Naming

- A file keeps its source name unless `--as` gives a clearer one. Put the strain ID first when the file is about one strain, so `where` finds it.
- A new folder under a `*` area gets a descriptive name: what it is, then the run or version when there are several (`Protein space/run 7`). No dates unless they tell runs apart. No chat, agent or session names.
- A new subfolder inside an area must be added to `LAYOUT.md` first. That change needs the owner's approval.

## The one way in

```bash
export SAPOTE_STRAIN_MASTER="<path to the master>"     # or pass --master every time
python mamey_run.py strain-master submit --chat <your id> --topic "ANI tables" --target "03 Genomes/ANI" \
  --summary "values behind the ANI figure" --check "26 genomes, 3 rows each" \
  --what "one line on what it is" --builder "<tool and version>" <file> [<file> ...]
python mamey_run.py strain-master verify --id <submission id> --chat <a different id> --accept \
  --checks "2 ok: <recount>; 3 ok: <identity source>; 4 ok: <records and rulings compared>; 6 ok: <claims and paths>"
python mamey_run.py strain-master apply --id <submission id> --chat <id>
python mamey_run.py strain-master check
```

Files bound for different folders go in one submission with `--manifest <tsv>` (columns `src` and `what`, and optional `folder`, `name`, `builder`, `member`, `intro`).
`status` prints the ledger.

The verifier's checklist:

1. The files match their sources by SHA-256. Run by `verify`.
2. The stated counts reproduce from the source files, by recount.
3. Every strain, contig, region and alias is copied from one source record.
4. No value contradicts a record or a ruling. A contradiction stops the submission until the owner rules.
5. The target folder is in `LAYOUT.md`, and the README line is drafted. Run by `verify`.
6. There is no claim beyond the evidence and no private path in a shareable file.

- `verify` refuses the submitter as verifier. To accept, `--checks` must number what was run for items 2, 3, 4 and 6, and items 1 and 5 must pass.
- `verify --return --checks "<what was run>" --notes "<why>"` sends a submission to `00 Inbox/Returned/`.
- A record edit is submitted with `--kind record-edit --changeset <tsv>` (columns `file`, `key_column`, `key`, `field`, `old`, `new`, `ruling`). Every file must sit in a record home named in the settings. `apply` changes a cell only if it still holds the old value and its key matches one row, keeps a `.bak_<time>_inbox` copy, and writes a CHANGELOG line. The re-copied record is then submitted as an import.
- `store` alone is the step `apply` uses. It is refused unless the settings set `"direct_store": true`, which a single-person master may choose.
- The ledger, `00 Inbox/INBOX_LEDGER.tsv`, has one row per submission: id, submitted, submitter, kind, topic, target, files, status (SUBMITTED, ACCEPTED, RETURNED, APPLIED), verifier, verified, checks, findings, applied, changelog.

## The record of each file

- The folder README gets one row: `| file | SHA-256 | copied from | what it is. Built by <builder>. |`.
- `CHANGELOG.md` gets one line: time, action, path, SHA-256, source, builder, what.
- A replaced copy moves to `Superseded/<date>_<name>` in the same folder, with a row under "`Superseded/` holds earlier copies".
- The original stays where it was. Its path is recorded relative to the folder that holds the master when it lies there.

## Looking for data before making any

1. The area README, then `LAYOUT.md`.
2. `python mamey_run.py strain-master where --type <folder or kind> --strain <ID>`: the folder, its README rows, the rows naming the strain, the registered tables that mention it, and unregistered files with its ID.
3. When the master holds nothing for the strain, `where` reports what each raw store holds. `mamey/strain_data_home.py` looks in the master first and then the legacy homes. For antiSMASH it prefers a raw result, then the flavored canonical home, and only then a package, and it says which (`antismash_source_kind`). Two different flavors give no answer until a flavor is named.
4. The asset registry, before any download.
5. Only then create or fetch something new, and submit the result.

## The self-check

`python mamey_run.py strain-master check` reads only. It checks:

1. no junk files (FAIL);
2. the top level and area subfolders against `LAYOUT.md` (FAIL). `LAYOUT.md` may be a table of entries (as `init` writes it, which also checks root files) or a list of allowed folders;
3. every file and folder is named in a README (WARN);
4. every README with a `| File | SHA-256 |` table lists exactly the files on disk, with matching SHA-256 (FAIL);
5. each CHANGELOG entry still matches its file, so a copy changed by hand is caught (FAIL);
6. inbox bookkeeping: every submission has a ledger row, no one verified their own, nothing ACCEPTED waits a day or more, each row's folder is where its status says (FAIL);
7. every path in backticks in a README exists (WARN).

It prints one line per check and `RESULT: PASS`, `PASS with warnings` or `FAIL`. It exits 1 on FAIL.
`--layout <file>` and `--config <file>` preview a proposed layout or settings without writing them.
Study-specific checks (paper numbers against the data, figure renders) stay in the master's own script, which can run this check first.

## Settings

`strain_master.json` at the master root:

| Key | Meaning |
|---|---|
| `schema` | `sapote.strain-master.v1` |
| `name` | Display name |
| `raw_stores` | Raw-data homes searched when the master holds nothing for a strain; relative to the master or absolute |
| `folders` | Output kind to folder; overrides the table above |
| `checksum_readmes` | Which READMEs the checksum check reads (glob patterns; default all) |
| `coverage_exempt` | Regular expressions for generated folders the README-coverage check skips |
| `direct_store` | `true` lets `store` write without the inbox; default `false` |
| `record_homes` | Folders where an accepted record edit may change a cell; relative to the master or absolute |
| `package_homes` | Folders holding sealed packages; the resolver searches them when `SAPOTE_STRAIN_MASTER` names this master |

The root comes from `--master` or `SAPOTE_STRAIN_MASTER`. The bundle source names no path, so a public release carries none.

## Starting a master

- New: `python mamey_run.py strain-master init --master <empty folder> --name "<name>" [--raw-store <path>]`. It writes the layout, a README in every folder, `LAYOUT.md`, `CHANGELOG.md`, the inbox ledger and the settings.
- Existing: `python mamey_run.py strain-master adopt --master <folder>` writes only `strain_master.json`. Preview first with `check --layout <draft LAYOUT.md> --config <draft settings>`, then write the master's own `LAYOUT.md`.

## Which records belong in the master

| Kind of record | Home |
|---|---|
| Strain metadata, hosts, isolation source as deposited, exclusions, rulings, cohort rosters and denominators | Master, `01 Strains/Source tables` (copies); edited at the record home until the owner moves editing to the master |
| Genome inventory, reference strain and pool registries, 16S provenance, GenBank correction logs, assembly tiers | Master, `03 Genomes/Source tables` |
| Cohort denominators for gene clusters, BLASTp evidence density | Master, `04 Gene clusters/Source tables` |
| Tree strain and tip metadata, outgroup registry | Master, `05 Trees/Source tables` |
| Asset registry, genome indexes, MIBiG references, protein catalogs, HMM sets, caches | Asset level, outside the master |
| Procedures, intake protocols, templates | Where they are; they describe the route, not the data |
| Backups (`.bak`) | Never copied |
