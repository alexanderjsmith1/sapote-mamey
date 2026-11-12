# RiPPER byte admission and bounded lifecycle

For maintainers of the optional RiPPER adapter. Skip this page unless you run RiPPER on a named strain. Core runs never need it.

The `lifecycle` subcommand checks a set of files, then optionally runs one supervised process. It has two modes:
- `synthetic_stub`: runs a tiny script you wrote, to test the supervisor. No RiPPER runs.
- `adapted_local05`: the native discovery route. Setup and review are in [RIPPER_NATIVE_DISCOVERY.md](RIPPER_NATIVE_DISCOVERY.md). Commands are in [RIPPER_CLI_METHODS.md](RIPPER_CLI_METHODS.md).

By default `lifecycle` launches nothing. It hashes files, checks limits and writes `PREFLIGHT.json` and `TERMINAL.json` in the run root. Only `--execute-stub` or `--execute-native` launches a process. Neither shows biological success, a license grant or BGC membership. Membership stays `UNVERIFIED`.

## Bind an adapted source

The adapted source is a locally patched copy of the archived RiPPER script. The archived script is pinned to revision `e90b3e6e74ddee99685183ca421323737012a991`.

```sh
python tools/ripper_adapter.py adapted-profile \
  --owner-receipt FILE --base-source FILE --source-patch FILE \
  --adapted-source FILE --out FRESH_DIRECTORY
```

The four inputs:
- owner receipt: a saved JSON file from whoever made the adaptation. It names the patch hash and the adapted-source hash. The adapter binds its bytes. It does not authenticate the author.
- base source: the original archived script. Its hash must match the pin.
- source patch: a single-file unified patch.
- adapted source: the patched script. It must declare the run-root and temp-root interface.

The command rebuilds the adapted source from base plus patch in memory and compares it with yours. No Perl is run. It writes `ADAPTED_SOURCE_PROFILE.json`, which records the four hashes separately.

To use the profile with `bind-run`, `local-plan`, `import` or `lifecycle`, pass `--adapted-profile FILE` and supply the roles `archived_base`, `source_patch`, `upstream_source` and `adaptation_receipt`. Without the profile, adapted bytes fail the original pin.

## Hash large files without copying them

Two sets of roles are hashed in 1 MiB chunks. The files are not copied.

| Roles | Budget key (per file) | Timeout key | Maximum | Default timeout |
|---|---|---|---|---|
| `pfam_model`, `ripp_model`, `pfam_index_h3f`, `_h3i`, `_h3m`, `_h3p`, and the same four for `ripp_index_` | `model_byte_budget` | `hash_timeout_seconds` | 16 GiB | 30 s (max 600 s) |
| `python_runtime`, `perl_runtime`, `makeblastdb`, `blastp`, `blastn`, `prodigal_short`, `hmmsearch` | `executable_byte_budget` | `executable_hash_timeout_seconds` | 512 MiB | 30 s (max 300 s) |

Set them in the spec. Config, queries, receipts and other inputs keep a 5 MiB limit. Without an executable budget, executables keep a 16 MiB, 30 s limit. A timeout without a byte budget is refused. Large BLAST+ binaries exceed 16 MiB, so set a budget, for example 32 MiB. A spec may bind at most 32 files. Symlinks are refused. Nothing is found or downloaded on its own.

## Lifecycle spec and invocation

```sh
python tools/ripper_adapter.py lifecycle --spec SPEC.json \
  --file ROLE=PATH [--file ROLE=PATH ...] --run-root ABSOLUTE_FRESH_PATH
```

The run root must not exist; an existing root is refused. The one exception is a reviewed native run with `--resume-preflight`: it reuses the run root that its own earlier preflight reserved, and only when that folder is pristine and its source, files, profile, root and review request still match (see [native discovery](RIPPER_NATIVE_DISCOVERY.md)). No other existing folder is accepted. The spec is JSON. This one runs the stub mode:

```json
{
  "schema_version": "ripper-lifecycle-spec/1",
  "mode": "synthetic_stub",
  "profile_id": "archived-e90b3e6-mergeRidePfam",
  "source_revision": "e90b3e6e74ddee99685183ca421323737012a991",
  "files": {
    "python_runtime": "<sha256 of the Python executable>",
    "stub_script": "<sha256 of your script>",
    "config": "<sha256 of the config file>"
  },
  "limits": {
    "wall_seconds": 60,
    "rss_bytes": 268435456,
    "disk_bytes": 1048576,
    "poll_seconds": 0.1
  }
}
```

`files` maps each role to the SHA-256 of the file you pass with `--file ROLE=PATH`. A hash that does not match the file is refused. `profile_id` and `source_revision` must match the `id` and `revision` in `tools/ripper_source_profile.json`. A mismatch is refused. The three hashes in `files` are placeholders for your own.

All four `limits` fields are required:

| Field | Rule |
|---|---|
| `wall_seconds` | positive, at most 3600 |
| `rss_bytes` | positive integer, at most 1 GiB (stub) or 2 GiB (`adapted_local05`) |
| `disk_bytes` | positive integer, at most 256 MiB |
| `poll_seconds` | 0.01 through 0.25 |

For the native mode, use `"mode": "adapted_local05"`, add `--adapted-profile` and bind the roles listed in [RIPPER_NATIVE_DISCOVERY.md](RIPPER_NATIVE_DISCOVERY.md#source-runtime-and-input-admission). It also accepts `bind_observed_runtime_closure` and the budget keys above.

Success for a preflight is exit 0 and a `PREFLIGHT.json` that lists the roster. A `HOLD` or `UNAVAILABLE` status still exits 0 on preflight. Read the status in the file.

## Stub mode

Roles: `python_runtime`, `stub_script`, `config`. Add `--execute-stub` to launch. The supervisor runs your script with the bound Python as `python -I -S -B SCRIPT <run-root>/result.tsv`. The script is executable code. Write it yourself. The word "synthetic" is a label, not a sandbox.

`psutil` must be installed before any launch. If it is not, the status is `UNAVAILABLE`, and nothing is installed for you.

A strict 11-column, header-only output gives `NO_HIT`. Retained rows give `SUCCESS_UNBOUND`. Both report `upstream_execution=NOT_EXECUTED`, `biological_absence_inferred=false` and membership `UNVERIFIED`. A stub result is never an importable RiPPER completion.

## What the supervisor does

It writes `STARTED`, then `LAUNCHED` (with process ID, process group, stdout log and stderr log), then the terminal. It samples wall time, the memory of the process tree and disk use of the run root. A limit hit, Ctrl-C or the cancel file stops the process group with SIGKILL and reaps the child.

`--cancel-file ABSOLUTE_PATH` is checked before launch and at every sample. The adapter only checks that it exists. It never creates it. To cancel, create that file yourself.

Limits are checks at poll time. They can overshoot, and they are not operating-system quotas or a network or file sandbox. Detached child processes are not covered. If the supervisor is killed with SIGKILL or the machine dies, a run can end with `STARTED` or `LAUNCHED` and no terminal. The outcome is unverified; inspect the surviving artifacts.

If permission denial prevents supervision, stub mode reports `UNAVAILABLE` and native mode reports `HOLD`; neither is a clean cancel. Unclear cleanup blocks any `NO_HIT` or row admission.

## Result and exit codes

The terminal and receipts bind the input hashes, supervisor version, logs and output files. Inputs are rehashed after a stub run. Artifacts stay on failure.

| Result | Meaning |
|---|---|
| `FAILED` | missing, empty or bad output, or nonzero exit |
| `INTERRUPTED` | cancel or resource limit |
| `NO_HIT` / `SUCCESS_UNBOUND` | see the status table in [RIPPER_NATIVE_DISCOVERY.md](RIPPER_NATIVE_DISCOVERY.md#statuses) |

| Exit code | When |
|---|---|
| `0` | preflight finished, or the run finished without failure |
| `2` | refusal, `FAILED`, `AMBIGUOUS`, or `HOLD` or `UNAVAILABLE` on an execute run |
| `130` | interrupted |

## Recovery

The terminal is written to `<name>.staging` first, then published as `TERMINAL.json` or `EXECUTION_TERMINAL.json` by an exclusive hard link. A staging file alone is not a result. If there is no canonical terminal, the outcome is unverified. Keep all files and investigate. Do not overwrite or delete them.

A first Ctrl-C while the terminal is being written records `INTERRUPTED` through a recovery staging file and keeps the partial bytes. A second interrupt, a write failure, SIGKILL or machine loss can leave no terminal. Output hashes describe the checked bytes at that moment. They do not lock the storage afterward.

Maintainer notes on finalization and cleanup are in the [development record](history/RIPPER_DEVELOPMENT_RECORD.md).
