# Bounded native workspaces

Some native programs re-expand relative data paths against their working directory.
Relative filenames therefore do not make a working directory with spaces safe. The
shared `mamey.native_workspace` owner supplies a fresh disposable directory under an
existing caller-selected root. Its native cwd and data paths contain only ASCII
letters, digits, `_`, `-`, `.`, and `/`. Spaces, tabs, other whitespace, Unicode and
shell metacharacters are refused. Explicit symlink roots and ancestor aliases are
refused; the default system temporary root is resolved first, including the ordinary
macOS `/var` alias. A refused explicit root is never silently replaced.

Executable locators retain argv-list semantics, including directories with spaces.
The MLSA CLI separately binds the selected executable locator, resolved regular-file
target and target SHA-256 before and after execution. A hash is software identity;
it is not a version banner, scientific validation or installation approval.

## DIAMOND clustering

Protein PCoA keeps its existing `--cluster-work-root` option and whole-worker
monitor. Without the option, clustering scratch goes under the attempt's own
`RESOURCE_ATTEMPT` folder, beside the receipts that own it, so a run writes nothing
outside its output kit. If that folder's path is not shell-safe (for example it
contains a space), the resolved system temporary root is used instead. The receipt's
`cluster_workspace.root_source` records which (`EXPLICIT`, `ATTEMPT_RECEIPT_DEFAULT`,
`SYSTEM_TEMP_FALLBACK_ATTEMPT_PATH_NOT_SHELL_SAFE`). The free-disk watch on the
scratch filesystem is unchanged. Only DIAMOND's clustering cwd and file arguments use the shared disposable
workspace. Scientific arguments, thresholds, feature construction, similarity and
ordination are unchanged. Bounded streamed copies bind original and consumed bytes.
The original attempt retains its cluster diagnostics, copied table and source hashes.
No global `chdir`, shell invocation or detached child session is introduced.

## MLSA

The public `tools/build_mlsa.py` CLI watches the complete existing computation,
including Python processing, Prodigal, BLAST, MUSCLE and IQ-TREE. Only the BLAST
filesystem block is redirected into the safe native workspace. BLAST databases and
staged inputs return to the original output namespace after bounded byte checks.
The scientific tool argument lists, locus set, best-hit rule, gap trimming,
concatenation, model selection and bootstrap options are unchanged.

```bash
python tools/build_mlsa.py /path/to/genomes "/path/to/output with spaces" \
  --bin-dir "/path/to/binary directory" --seeds-dir "/path/to/seed inputs" \
  --native-work-root /private/tmp --threads 4 \
  --rss-limit-bytes 3800000000 --min-free-disk-bytes 2000000000 \
  --timeout-seconds 900 --native-copy-limit-bytes 536870912
```

Select an existing explicit root appropriate to the operating system; `/private/tmp`
is a macOS example. Output must be new or empty and have an existing parent. Input,
source and output ancestors may not overlap. Preflight refuses unsafe paths, invalid
budgets, missing tools, excessive input bytes, estimated RSS above an 80% margin, or
insufficient free disk on either the output or scratch filesystem before launching
a child. There is no automatically created diagnostic sibling outside the requested
output. Positive finite larger budgets are supported as explicit user configuration;
thread count and the OS CPU-count observation are recorded, without claiming that
`os.cpu_count()` is an allocated CPU entitlement.

Defaults are 3.8 GB RSS, 2 GB free disk, 900 seconds, 4 requested threads and a
536,870,912-byte per-input/copy ceiling. Resource estimates are conservative engineering
allowances, not universal peak bounds, scientific filters or authority to run. The
existing watcher periodically observes the whole worker and its descendants and
both filesystem floors; it is not a kernel-enforced memory limit. Actual generated
BLAST database copies and output closure have finite byte/count ceilings as well.
The six one-thread library environment controls are pinned for the worker, while
explicit existing native thread arguments are preserved.

`RESOURCE_ATTEMPT/<fresh-id>/` contains the frozen request, child log, resource
receipt, worker completion and terminal `SUCCEEDED.json` or `FAILED.json`. Resource
evidence is frozen before terminal success; hashes have no circular dependency.
Only validated outputs are copied into exclusive final names, retaining the worker
bytes and rechecking the output disk floor. Mechanical `run_status.json` becomes visible
last. A late terminal failure invalidates this owner's promoted COMPLETE status.
Failed partial products remain inside their attempt; bounded historical diagnostic
surfaces may also appear at the requested output. No failed attempt is reused.
Terminal success requires a zero child exit, no resource stop or cleanup error,
unchanged code/input/tool bytes and exact completion/output closure.

The native scratch directory is allocated by the coordinator. Children inherit the
watched worker's process group; there is no nested watcher. Cleanup removes only the
owned fresh directory after watcher return. If descendant cleanup is unconfirmed,
scratch is retained with an explicit failure for diagnosis. Identity checks refuse a
replaced directory or symlink. This is protection against ordinary ownership mistakes,
not a general hostile concurrent filesystem sandbox.

Receipts retain local operator paths and byte provenance. They are local diagnostics,
not public distribution authority or a portable public artifact. The terminal receipt
records historical worker and promoted output roots so relocated output hashes can be
resolved without rewriting the original native-copy evidence. Mechanical completion
never establishes orthology, type status, a species boundary or scientific sign-off.
