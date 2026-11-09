# Keep results in a Strain Master

A **Strain Master** is a folder that holds approved copies of your results. Each copy is logged with its source path and SHA-256 value. By default, files enter it only through an inbox: you submit, a second person verifies, then the file is applied. A one-person master can opt in to direct store instead, which skips the second reviewer (see [Working alone](#working-alone)).

You need the installed program and a finished run (see [first run](reader/01_FIRST_RUN.md)). To copy a result to another computer instead, see [Files, storage and handoff](FILES_STORAGE_AND_HANDOFF.md). For an index that leaves all files in place, see [Project file index](PROJECT_DATA_HOME.md).

Every command below runs from the program folder. Each `strain-master` command takes `--master <folder>`. Except `init` and `adopt`, you can leave it out after running `export SAPOTE_STRAIN_MASTER=../EXAMPLE-master` in your shell. `init` and `adopt` always need `--master`.

## Create the master

```bash
python mamey_run.py strain-master init --master ../EXAMPLE-master --name 'EXAMPLE master'
```

The folder must not exist or must be empty. Success prints the files it created, including `00 README.md`, `LAYOUT.md`, `CHANGELOG.md`, `strain_master.json` and `00 Inbox/INBOX_LEDGER.tsv`. Keep working analyses outside the master.

## The one way in

### 1. Submit

This files the sealed package of a run (the `_Complete_Package.zip` a finished run writes; see the [glossary](GLOSSARY.md)). The name ends in `_Complete_Package.zip`. Run `ls runs/EXAMPLE`, then put the real name into `PACKAGE` in place of the text in angle brackets. Keep the quotes: unquoted `<` and `>` are shell redirections, so a literal paste could read or overwrite a file instead of passing an argument.

```bash
PACKAGE='runs/EXAMPLE/<the real _Complete_Package.zip name>'
python mamey_run.py strain-master submit --master ../EXAMPLE-master \
  --chat AB --topic 'EXAMPLE package' --target mamey_package \
  --summary 'Sealed package for EXAMPLE' --check 'Archive opens' \
  "$PACKAGE"
```

- `--chat` is the name you sign with. Use 2 to 64 letters, digits, `.`, `_` or `-` (for example `ab-1`). A shorter or other id prints `REFUSED BAD_ID`. The reviewer must use a different one.
- `--target` is a folder in the master, such as `'03 Genomes/ANI'`, or an output kind such as `mamey_package`. A kind stands in for its folder (see [Where Mamey outputs land](#where-mamey-outputs-land)).
- `--summary` says what the file is. Each `--check` names a count or claim the reviewer must reproduce.
- The source file stays where it is. A copy is staged in `00 Inbox`.

On success it prints JSON with an `id` and `"status": "SUBMITTED"`. Save the `id`; every later step uses it. Put it in a shell variable, replacing the text in angle brackets and keeping the quotes:

```bash
SUBMISSION_ID='<the id printed by submit>'
```

### 2. Status

```bash
python mamey_run.py strain-master status --master ../EXAMPLE-master
python mamey_run.py strain-master check --master ../EXAMPLE-master
```

`status` prints the inbox ledger as tab-separated rows. The row for your `id` reads `SUBMITTED`. `check` reads the master and prints a `[PASS]`, `[WARN]` or `[FAIL]` line per check, with detail lines under any that need attention. The last line is `RESULT: PASS`, `RESULT: PASS with warnings` or `RESULT: FAIL`. It exits 1 on FAIL. A refused command of any kind prints `REFUSED <CODE>: <reason>` and exits 2. Common codes:
`BAD_ID` (a `--chat` id that is not 2 to 64 letters, digits, `.`, `_` or `-`),
`OCCUPIED` (`init` into a folder that is not empty), `NEED_CHECKS` (`verify` without
`--checks`, or without a numbered item for each checklist line), and `CANNOT_ACCEPT`
(`verify` found a problem; the reason follows the code).

A staged file is not yet part of the master.

### 3. Verify

A different person runs this. The checklist is in the [storage reference](reference/STRAIN_MASTER_STORAGE_REFERENCE.md#the-one-way-in): recount the stated counts (item 2), confirm each locus identity comes from one source record (item 3), compare against records and rulings (item 4), and look for claims beyond the evidence or private paths (item 6).

```bash
python mamey_run.py strain-master verify --master ../EXAMPLE-master \
  --id "$SUBMISSION_ID" --chat CD --accept \
  --checks '2 ok: <recount>; 3 ok: <identity source>; 4 ok: <records compared>; 6 ok: <claims and paths>'
```

On success the status is `ACCEPTED`. Using your own `--chat` prints `REFUSED SELF_VERIFY`. To send a submission back, use `--return` with `--checks` and `--notes '<why>'`; it moves to `00 Inbox/Returned/`.

### 4. Apply

```bash
python mamey_run.py strain-master apply --master ../EXAMPLE-master \
  --id "$SUBMISSION_ID" --chat CD
```

The file is copied to its folder with a README row and a `CHANGELOG.md` line, and the status becomes `APPLIED`. Run `check` again and expect `RESULT: PASS`.

### Working alone

A one-person master has no second reviewer. Set `"direct_store": true` in `strain_master.json` at the master root, then store files directly:

```bash
python mamey_run.py strain-master store --master ../EXAMPLE-master \
  --target mamey_package --what 'Sealed package for EXAMPLE' \
  --builder 'mamey_run.py run' \
  "$PACKAGE"
```

Set `PACKAGE` first, as in [Submit](#1-submit). Add `--dry-run` to see what would happen without writing. Both forms need the setting; without it, `store` prints `REFUSED INBOX_REQUIRED`. Direct store skips the second-person check, so run `check` after every store.

## Where Mamey outputs land

Use these kinds with `--target`.

| Output | Kind | Folder |
|---|---|---|
| antiSMASH result ZIP | `antismash_zip` | `04 Gene clusters/antiSMASH` |
| Sealed package (`*_Complete_Package.zip`) | `mamey_package` | `04 Gene clusters/Mamey packages` |
| Mode B card (a written locus review) | `modeb_card` | `04 Gene clusters/Mode B cards` |
| BLASTp evidence (raw homology hit tables) | `blastp_evidence` | `04 Gene clusters/BLASTp evidence` |
| Gap-rescue screen (a rescan for genes missed in the assembly) | `gap_rescue` | `04 Gene clusters/Gap rescue` |

Do not file a table you built from a run under `Source tables`. That folder holds copied cohort registries and other records. File the package instead; the table stays inside it. The [storage reference](reference/STRAIN_MASTER_STORAGE_REFERENCE.md#where-mamey-outputs-land) lists all kinds and the full layout.

## Find existing files

```bash
python mamey_run.py strain-master where --master ../EXAMPLE-master \
  --type mamey_package --strain EXAMPLE
```

`--type` is a folder name, area path or output kind. Without `--strain`, the result lists the folder's README rows under `records`. With `--strain`, read these keys instead:

- `strain_records`: registered files whose name or description carries the strain ID.
- `files_mentioning`: registered text tables with lines that mention it.
- `unregistered`: files in the folder with the ID that the README does not list.

The result is JSON with a `status`:

- `FOUND`: the folder matched, and with `--strain` at least one record or table matched.
- `NOT_IN_MASTER`: the folder matched but nothing is recorded for the strain. This means "not recorded here", not "does not exist". The result adds `raw_stores`, what each configured raw store holds for the strain. Those files are not chosen for analysis; bind the one you use explicitly. A raw store is set with `init --raw-store <path>`.
- `NO_SUCH_TYPE`: the type is not in the layout. The result lists `known_types`.
- `AMBIGUOUS`: the type matches several folders. Use the full path.
- `NOT_CONFIGURED`: no `--master` and `SAPOTE_STRAIN_MASTER` is not set.
- `MASTER_NOT_FOUND`: the master path is not a folder.
- `CONFIG_INVALID`: `strain_master.json` cannot be read. The `reason` says why.

The [storage reference](reference/STRAIN_MASTER_STORAGE_REFERENCE.md) covers record edits, folder imports, hard links, replacement backups, layouts and settings.
