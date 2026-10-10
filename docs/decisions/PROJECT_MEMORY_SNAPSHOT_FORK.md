## Current reader/loader boundary — .447 documentation audit

This packaging decision record leaves the owner's choice intact. The normal writer produces the manifest alias stub, but readers have different failure contracts. `mamey/snapshot_alias.py:25–48` returns an unresolved stub when its target is missing or invalid; invalid initial snapshot JSON can raise. The generic resolver follows any truthy alias_of when source_scans is absent without schema, in-package path or target-hash validation. An unresolved stub is not a successfully read full manifest.

The standalone build_deep_data/build_bgc_markers/assembly_qc readers condition alias following on the snapshot filename and can raise on malformed target JSON. `mamey/deep_data.py:126–155` instead loads the package's literal manifest.json for a stub and can degrade to empty structures. Thus “all four readers follow alias_of” does not mean identical resolution or completeness. Presence validation does not prove an alias target, source binding or filled downstream records. Keep snapshot, manifest and integrity evidence together in place; preserve unresolved/empty states as reader holds rather than biological absence.

Historical size measurements and recommendations below are retained, not remeasured. No source package or decision was changed. The original record follows unchanged.

---

# Decision record — `Project_Memory_Snapshot.json`: keep-or-retire fork (opened 2026-06-25)

**Status: RESOLVED-BY-ALIAS at v9.7.400; residual choice below awaits the owner's ruling.**
Recorded v9.7.405 by the Claude Code patch lane. Not a scientific decision; packaging only.

## What the fork was
`RUNNING_PATCH_LIST_v3_open_items.md` (v9.7.128, 2026-06-25) item A1 asked whether the per-strain
`{strain}_Project_Memory_Snapshot.json` should be kept or retired, because it was a **verbatim
re-dump of `manifest.json`** — on a measured 96-BGC strain each carried a byte-identical
20,882,853-byte `source_scans` blob, ~40 % of the sealed package.

## What already happened (verified in this tree)
- `mamey/cli.py` (search "v9.7.400 de-bloat") now writes a **~300-byte alias stub**
  `{"schema": "project_memory_snapshot_alias_v1", "alias_of": "manifest.json", ...}`.
- `mamey/snapshot_alias.py::load_snapshot` resolves either generation (full pre-.400 file or stub).
- `mamey/validate.py::REQUIRED_SUFFIXES` still lists the file, so the presence gate and every
  `*Project_Memory_Snapshot.json` glob (`tools/build_deep_data.py`, `tools/build_bgc_markers.py`,
  `tools/assembly_qc_check.py`, `mamey/deep_data.py`) keep working unchanged.
So the cost that motivated "retire" (duplicate ~20 MB per strain) is already gone. Packages cut
before v9.7.400 (e.g. the `.381` atlas packages) still carry the full copies; that is history, not a
live defect.

## Residual choice
| Option | Effect | Risk |
|---|---|---|
| **A — keep the stub (recommended)** | zero change; old globs, external notebooks, and the validate gate stay valid | none measured |
| B — drop the file and the validate requirement | one fewer file per package | every external consumer that globs the name breaks silently; no in-bundle benefit |

**Recommendation: A.** The stub is the cheapest possible backward-compatibility shim; removing it
buys nothing measurable and breaks unknown external readers. Close the June-25 item as
RESOLVED (v9.7.400) rather than carrying it as "open".

What would change this: evidence that a downstream tool mis-reads the stub as a full snapshot
(none found — all four in-bundle readers follow `alias_of`).

For a new decision, record the maintainer or designated reviewer, the ruling and its evidence. The owner-ruling field below remains open.

Owner ruling: ____ (owner). Until ruled, nothing changes.
