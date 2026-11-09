# Check that a bundle matches its checksum and identity files

This page is for a maintainer or reviewer who has a bundle folder and wants to know
whether its identity files describe the files actually in it. It is not needed to run an analysis.

The task: confirm that the governed files match the bundle's own checksum and identity
files. One command does it. It does not check every byte under the bundle folder; see
"What the check does not cover" below.

## The files it checks

| File | What it holds |
|---|---|
| `BUILD_STAMP.txt` | The build name (`build=...`) |
| `TAG` and `pyproject.toml` | The bundle and engine versions |
| `SOURCE_CHECKSUMS_SHA256.txt` | The expected SHA-256 of every tracked source file |
| `TIER_MANIFEST.txt` | The build stamp (`stamp=...`) and the list of files the bundle should contain |
| `MODULE_MANIFEST.txt` | One line per `mamey` module, taken from its docstring. It is a reading aid, not a command list |
| `RELEASE_MANIFEST.md` | The checks recorded for the release |

These files describe the bundle. They do not show who built it, that tests ran, or that
the science was accepted. If you need proof of origin, compare the bundle's own SHA-256
against a hash you got from a separate source.

## Run the check

From the bundle root:

```bash
python tools/check_release_manifest.py --root "/absolute/path/to/bundle"
```

`--quiet` hides the summary line and the PASS line. Problems still print.

The check recomputes every checksum, confirms every listed file exists, confirms no tracked
file is missing from the list, and confirms `TIER_MANIFEST.txt` and `BUILD_STAMP.txt` name
the same build.

Success prints two lines and exits 0:

```
release manifest: <N> verified | 0 mismatched | 0 missing | stamp <build> vs build <build>
check_release_manifest: PASS (artifacts describe the tree)
```

If the bundle root holds release artifacts, a third line comes between them:

```
not checked here: <K> root release artifact(s) outside the tracked-file policy; check them against their own SHA-256 receipt: <names>
```

## What the check does not cover

The check covers governed files only. `tools/tracked_file_policy.py` decides which files
are governed. It leaves out build cruft (`__pycache__/`, `*.pyc` and similar), the two
manifest files themselves, and root-level release artifacts: the tier ZIP, `SHA256SUMS*.txt`
and `cut_*_log.txt`. A changed root ZIP still gives PASS. The `not checked here` line
names those root files. Check each one against a hash from its own receipt.

The checksum file sits inside the bundle it describes. Anyone who can change a file can also
change its checksum line. A PASS shows that the files and the manifest agree. It does not
show that either came from the release. For that, compare the archive's SHA-256 with a hash
you got from a separate source.

Failure exits 1. The same summary line comes first, then `check_release_manifest: FAIL`,
then one `  - ` line per problem. Read the problem lines, not just the last line.

A work tree that has been edited since its last cut will fail. That is expected there.
Only a bundle you were handed as finished should pass.

## Module inventory

`python tools/check_module_accretion.py` checks that every module in the sealed checksum
list is accounted for and that new modules are justified in the newest changelog block.
It reports removed modules without failing on them. `--json` prints the report as JSON.
`--write` rewrites `MODULE_MANIFEST.txt`. Use `--write` only as a cut step.
To find commands and capabilities, use [the catalog guide](CATALOG_MAINTENANCE.md)
and [task routes](USER_TASK_ROUTER.md).

## Cut-time tools

Regenerating the checksum list, the stamps and the seal plan belongs to the cut process.
Follow the [cut protocol](../CUT_PROTOCOL.md). `python tools/make_seal_script.py --help`
lists the seal-plan generator's inputs. It is a standalone tool, not a `mamey_run.py`
command. It writes a plan and a wrapper script for the owner to review, and it does not
run the seal. `--verify-plan PLAN --plan-sha256 EXPECTED` rechecks a plan without running it.

For the older tier layouts, see [tier differences](TIER_DIFFERENCES.md).
