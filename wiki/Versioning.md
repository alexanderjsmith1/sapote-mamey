# Versioning — three streams, one sync tool, and the freeze scars

Understand the bundle version, engine version and build stamp.  
This page is for maintainers and readers citing a build.

Sapote-Mamey tracks **three versions independently** and reconciles them at cut time. Mixing them
up is the single most common citation error, so learn the trio:

| stream | where it lives | example | what it means |
|---|---|---|---|
| **Engine version** | `mamey/__init__.py::__version__` + `pyproject.toml [project].version` | `1.9.NNN` | the deterministic extraction code; gate/checkpoint rules tie to it |
| **Bundle version** | `BUNDLE_VERSION` in `__init__.py`, mirrored in `pyproject.toml [tool.sapote]` | `9.7.NNN` | the public Sapote-Mamey release line users cite |
| **Build stamp** | `BUILD_STAMP.txt` / `TAG` | `build=YYYYMMDDv97NNNa` | the physical cut + patch notes |

The engine bumps only when deterministic behavior changes; most cuts are bundle-only (docs, data,
protocols, tools). Current output package names embed both versions and the antiSMASH detection profile:
`{strain}_SapoteMamey_v{BUNDLE}_engine{ENGINE}_{profile}_Complete_Package.zip`, where
`profile` is `strict`, `relaxed`, `loose` or `unknown`. Use the actual emitted filename and
producing manifest rather than reconstructing it; an older package retains its original name.

## Keeping them aligned

`tools/sync_version.py` writes its declared anchored version surfaces; historical versions and unowned prose may intentionally remain unchanged. It does not discover and certify every version-like value automatically;
`tests/test_version_sync.py`, `test_no_stale_version_literals_*`, and
`test_docs_version_drift.py` fail the build on drift. For a separately authorized version bump, run the synchronizer and required checks in the
candidate tree. `python tools/sync_version.py --check` checks without writing; invoking it without
`--check` writes anchored files and delegates bootstrap regeneration. Do not run its write mode
on an immutable source while merely reviewing documentation. Version checks do not replace
release identity, tier/archive integrity, governance or owner acceptance gates.

## Why the paranoia — the documented freeze history

`CURRENT_DOCS_INDEX.md` (the authority for which docs are current) records its own failures, and
they justify the machinery:

- Its header **froze at v9.7.136** while cuts advanced (caught at v9.7.335 — and three of the four
  filenames it pointed to did not exist).
- It froze **again at v9.7.337 for 29 cuts**.
- A fix was *described* at .366 but not implemented — and the index froze a **third** time at
  v9.7.367, caught inside the sealed .370 bundle.
- v9.7.371 landed the real ratchet: `sync_version.py` owns the header, `--check` fails on drift,
  and `test_docs_version_drift.py` covers it.

Version stamps can drift even after sealing. Check the synchronizer's declared rules and the
relevant tests; preserve historical version statements and handle any unowned current literal through
the authorized cut process.

## Practical rules

- **Citing a run**: quote bundle + engine together (they are both in the package ZIP name and
  `manifest.json`). A Mode-B card or deliverable on disk may be from an older engine — verify
  against the current engine before asserting a defect or building on its content.
- **Reading docs**: `CURRENT_DOCS_INDEX.md` in the current bundle decides which docs are current;
  historical root notes are shipped but superseded.
- **Cut procedure**: use the current `CUT_PROTOCOL.md` and release manifest. Synchronization and version tests are bounded steps; a passing check does not authorize sealing, promotion or publication.
