# RiPPER native discovery contract

For maintainers of the optional RiPPER adapter. Skip this page unless you run RiPPER on a named strain. Core runs never need it, and `mamey_run.py` has no RiPPER command.

Native discovery runs a locally adapted copy of the RiPPER Perl source under a supervisor. It finds short peptide candidates near one selected enzyme. It is opt-in: nothing launches without `--execute-native`, a matching review and an admission file. Commands are in [RIPPER_CLI_METHODS.md](RIPPER_CLI_METHODS.md). The spec, limits and supervisor are in [RIPPER_OPERATIONAL_LIFECYCLE.md](RIPPER_OPERATIONAL_LIFECYCLE.md).

What a run gives you: raw candidate rows. It gives no HMM annotation, no verified genome coordinates, and no proof that a candidate belongs to a BGC. Raw discovery never enters canonical scores.

Only one platform has been tested: macOS on arm64, with system Perl and a private Prodigal build. Other platforms are unverified. The adapter installs nothing and downloads nothing.

## Prepare an explicit local runtime before native preflight

Prepare these separately, then bind the actual files. Each row says how to check it.

| # | Item | Check | Expect |
|---|---|---|---|
| 1 | Python 3.12 or newer, with full Biopython and `psutil`; `sqlite3` must support `deserialize` | `"$PYTHON" -c "import Bio, psutil, sqlite3; print(Bio.__version__, psutil.__version__, hasattr(sqlite3.Connection, 'deserialize'))"` | two versions and `True` |
| 2 | Perl with BioPerl, DBI, DBD::SQLite, Digest::SHA, XML::Simple, LWP::Simple, JSON::PP | `perl -MBio::SeqIO -MBio::SearchIO -MBio::Seq -MBio::SeqFeature::Generic -MBio::Species -MDBI -MDBD::SQLite -MDigest::SHA -MXML::Simple -MLWP::Simple -MJSON::PP -e 'print "ok\n"'` | `ok` |
| 3 | BLAST+ `makeblastdb`, `blastp`, `blastn` | `blastp -version` (and the other two) | a version line |
| 4 | Prodigal-short, a modified Prodigal for short ORFs, built privately | run the binary with `-v` | `Prodigal V2.6.3` |
| 5 | A runtime receipt (schema `ripper-native-runtime/1`) | see below | all probe exit codes are `0` |
| 6 | Adapted source files and a config | see below | the profile step passes |

Use the Python from item 1 for `pip`: `"$PYTHON" -m pip install ...` from your approved package source. Installing into another Python does not fix this one. For a machine with no internet, see [offline installation](INSTALL.md#offline-installation).

Notes on each item:

- Perl. Install new modules into a runtime folder you own. You do not need to change system Perl. The dispatcher replaces `@INC` with the library roots in your runtime receipt, so `PERL5LIB` and shell activation do not reach the run. A `.pm` file that exists may still fail to load. Check native extensions against the Perl you chose.
- BLAST+. The controlled `PATH` of the run must resolve to the exact bound files.
- Prodigal-short. Stock Prodigal prints the same banner, so the banner proves nothing. Keep the source revision, the recipe, the toolchain, the binary hash and the behavior evidence next to the receipt. Use the source owner's reviewed recipe and a compiler for your platform.
- Runtime receipt. Record tool and module versions, probe exit codes, hashes, module paths and library roots. These are declarations bound to file bytes. They are not proof of authorship or of complete library loading. You can set `bind_observed_runtime_closure` in the spec to also recheck the loaded library files under the Perl roots. Without it, do your own before and after checks.
- Executable budgets. Hashing has a byte limit and a time limit per executable. Set `executable_byte_budget` and `executable_hash_timeout_seconds` in the spec large enough for your files (maximums are in the lifecycle page). Large BLAST+ binaries exceed the default 16 MiB.
- Config. Keys allowed: `prodigalshortbin`, `prepeptab`, `sqlite3fn`, `blastdbdir`, and seven numeric controls (`minPPlen`, `maxPPlen`, `flankLen`, `maxDistFromTE`, `fastaOutputLimit`, `prodigalScoreThresh`, `sameStrandReward`). Each line is a key and one value. Values cannot hold whitespace, so the Prodigal path cannot either. `prodigalshortbin` must equal the bound binary's absolute path.
- Run root. Pick a new absolute folder outside the source and input folders, with ordinary non-symlink parents. Leave `upstream_run` and the runtime temp folder for the run to create.

When all rows pass, go to the preflight step in [RIPPER_CLI_METHODS.md](RIPPER_CLI_METHODS.md#prepare-and-run-a-new-native-discovery).

Discovery does not need HMMER or Pfam models. HMM annotation is a separate stage with its own admission, and it is not run here.

## Source, runtime and input admission

Use mode `adapted_local05` and the matching adapted-source profile. The original base plus the cumulative patch must rebuild the adapted source in memory. Adapted bytes are never accepted under the original source pin.

Every role is given as `--file ROLE=PATH` and hashed:

- source: `archived_base`, `source_patch`, `upstream_source`, `adaptation_receipt`, `source_closure`, and `source_discovery_contract` for the supported source interface;
- inputs: `config`, `genbank`, `query_fasta`, `queries`;
- tools: `perl_runtime`, `makeblastdb`, `blastp`, `blastn`, `prodigal_short`;
- runtime: `runtime_receipt`, `prodigal_recipe`, `perl_dispatcher`;
- eleven Perl modules, one role each.

A module role is `perl_module_` plus the lowercase module name with `::` changed to `_`. The roles are `perl_module_bio_seqio`, `perl_module_bio_searchio`, `perl_module_bio_seq`, `perl_module_bio_seqfeature_generic`, `perl_module_bio_species`, `perl_module_dbi`, `perl_module_dbd_sqlite`, `perl_module_digest_sha`, `perl_module_xml_simple`, `perl_module_lwp_simple`, `perl_module_json_pp`. Bind the actual `.pm` file. Its path must sit under a Perl library root in the receipt.

If a role is missing, preflight returns `HOLD` with the exact list. Preflight does not search, install, compile, download or probe.

The runtime receipt must carry these fields: `tool_sha256`, `tool_versions`, `module_sha256`, `module_paths`, `module_versions`, `perl5lib`, `tool_probe_exit_codes`, `module_probe_exit_codes`, `probed_interpreter_sha256`. Every probe exit code must be integer `0`. It also records `state` set to `PROBED_NATIVE_RUNTIME_CONTENT_UNATTESTED`; without that exact value preflight returns `HOLD_NATIVE_RUNTIME_RECEIPT`. And it records four reviewed decisions:
- `prodigal_short_validation=SHORT_ORF_BEHAVIOR_REVIEWED`;
- `blast_database_format_validation=REVIEWED_FOR_SELECTED_SOURCE`;
- `blast_pairwise_parser_validation=REVIEWED_FOR_SELECTED_BIOPERL`;
- `prodigal_recipe_sha256` equal to the hash of the recipe file.

The spec may bind at most 32 files.

The input record must pass strict Biopython checks: one record, one query, unique CDS IDs, complete contiguous ATG coding sequences, translation tables 1 or 11. The first scope needs an exact unique match between the query and the selected CDS. Anything else is refused or held. Without full Biopython the result is `HOLD_DEPENDENCY_UNAVAILABLE`. The enzyme's location is never the peptide's location.

## Review and admission

Preflight writes `NATIVE_REVIEW_REQUEST.json` once the inputs are complete. It binds the spec, every file hash, the adapted profile, the code hashes, the exact command line and the environment. Its decision reads `PENDING_PARENT_REVIEW`. Read the exact command line and environment there. The command line differs between supported source interfaces, so do not copy one from a doc.

The command line has no shell. `PERL5LIB`, `PERL5OPT` and loader overrides are dropped. `TMPDIR` is a fresh folder in the run root.

To approve, copy the request to a new file and change two fields:
- `decision` to `APPROVED_NATIVE_LOCAL_EXECUTION`;
- `local_use_decision` to `REVIEWED_LOCAL_EXECUTION_ONLY_NO_DISTRIBUTION_CLEARANCE`.

Leave every other field as the request has it, including `schema_version` (`ripper-native-admission/1`), `reviewer` (`parent`) and `evidence_kind` (`operator_supplied`). Any other change, or any change to the spec, files or source, makes the admission invalid. The file is a label, not a signature. It does not show that the native run will work or that RiPPER may be distributed.

Pass it as `--native-admission FILE` together with `--execute-native`. An admission is good for one run.

## Resume a reserved preflight

A preflight reserves the run root. To run on it, add `--resume-preflight`. Only a pristine folder can resume, and it holds only `PREFLIGHT.json`, `TERMINAL.json`, `TERMINAL.json.staging` and `NATIVE_REVIEW_REQUEST.json`. Older three-file preflights also resume. The staging file must be the same file as the canonical terminal. Do not delete evidence to make a folder look pristine. The source, files, profile, root and request must match, and the earlier terminal must show no execution.

You can also run directly on a new run root, with no reserved preflight, if the request was reviewed first. That route writes `PREFLIGHT.json` and `TERMINAL.json`. A resumed preflight instead writes `EXECUTION_PREFLIGHT.json` and `EXECUTION_TERMINAL.json` beside the reserved files. A second attempt on the same root is refused.

## Raw output

After a zero exit, the supervisor reads the SQLite result from a bounded in-memory copy. It refuses leftover sidecar files, wrong columns, a missing unique accession and peptide serial, and more than 10,000 rows. It checks serial and FASTA IDs, the sequence alphabet and length, strand, finite scores and non-negative distance. Original IDs are not changed.

It also checks that the stage start and end records, schema, command line and output hashes agree. SQLite sequences must match the exported FASTA. A missing export, incomplete stages or a different BLAST subject gives `AMBIGUOUS`, with a null candidate count and the raw rows kept. `NO_HIT` needs the exact three-stage BLAST no-hit path. A full five-stage run with zero rows is `NO_RETAINED_CANDIDATES`. A zero exit with an empty summary is never a no-hit.

Raw discovery goes to `RAW_DISCOVERY.json`. Coordinates read `ABSENT_PRODUCER_MAPPING`. The window coordinates of the GenBank export and the enzyme query do not place the peptide. The score file's header is the first non-blank, non-comment line, with 13 tab-separated columns (`Beg`, `End`, `Std`, `Total`, `CodPot`, `StrtSc`, `Codon`, `RBSMot`, `Spacer`, `RBSScr`, `UpsScr`, `TypeScr`, `GCCont`). One such header is accepted. A repeated or misplaced one is a bad row.

## Statuses

| Status | Meaning | Next step |
|---|---|---|
| `PENDING_PARENT_REVIEW` | Request written, not approved | Review it and write the admission |
| `READY_NATIVE_REVIEWED_NOT_EXECUTED` | Preflight passed with an admission | Add `--execute-native` |
| `HOLD` | A role, review or dependency is missing; in this native mode also when `psutil` is missing (listed as `optional_psutil`) or supervision is denied (`reason` `SUPERVISION_UNAVAILABLE`) | Read the listed holds, `missing` and `reason` |
| `UNAVAILABLE` | Synthetic stub mode only: a role is missing, `psutil` is missing or supervision was denied | Read `missing` and `reason`; fix the environment |
| `NOT_EXECUTED` | Nothing was launched | None |
| `EXECUTED_NATIVE_LOCAL_ADAPTER_OBSERVED` | The native process launched, even if it then failed | Read the terminal for the outcome |
| `SUCCESS_UNBOUND` | Raw candidates kept in the declared scope | Separate annotation or coordinate evidence |
| `NO_HIT` | No enzyme hit for the bound query | Keep as a scoped result |
| `NO_RETAINED_CANDIDATES` | Enzyme hit, no kept candidates | Keep apart from `NO_HIT` |
| `AMBIGUOUS` | Stages or exports disagree | Count is null; inspect the stage files |
| `FAILED` | Nonzero exit, failed stage, bad output or changed hash | Find the cause; keep the evidence |
| `INTERRUPTED` | Cancel file, Ctrl-C or a resource limit | Same |

No status says anything about biological absence. A missing terminal is never evidence of completion, but its absence alone does not show what happened: the run may have stopped, or the file may be missing or unreadable for another reason. Keep every surviving file and establish the outcome from them before you conclude anything.

## Native dispatcher and temp folder

The `perl_dispatcher` role is bound to one reviewed dispatcher by SHA-256. Unknown dispatcher bytes stay held. See the [development record](history/RIPPER_DEVELOPMENT_RECORD.md#native-dispatcher-binding).

Preflight does not create the runtime temp folder or the inner source folders. A reviewed execution creates the runtime temp folder, then launches. A failed attempt keeps it and refuses a second pristine resume. This controls names. It is not a sandbox.

## Observed runtime files

Set `bind_observed_runtime_closure: true` in the spec to bind the loaded library files listed in the runtime receipt. The list holds 1 to 512 unique regular files under the Perl library roots, at most 5 MiB each and 64 MiB in total. Network locators and `..` paths are refused. The files join the roster and are rechecked before launch and at the end. This does not show that no library loaded later.

The native RSS cap can be up to 2 GiB. Stubs stay at 1 GiB. Sampling can overshoot and is not an operating-system quota.
