# Versioning — three streams, one sync tool, and the freeze scars

Sapote-Mamey tracks **three versions independently** and reconciles them at cut time. Mixing them
up is the single most common citation error, so learn the trio:

| stream | where it lives | example | what it means |
|---|---|---|---|
| **Engine version** | `mamey/__init__.py::__version__` + `pyproject.toml [project].version` | `1.9.143` | the deterministic extraction code; gate/checkpoint rules tie to it |
| **Bundle version** | `BUNDLE_VERSION` in `__init__.py`, mirrored in `pyproject.toml [tool.sapote]` | `9.7.398` | the public Sapote-Mamey release line users cite |
| **Build stamp** | `BUILD_STAMP.txt` / `TAG` | `build=20260901v97398a` | the physical cut + patch notes |

The engine bumps only when deterministic behavior changes; most cuts are bundle-only (docs, data,
protocols, tools). Output package names embed both:
`{strain}_SapoteMamey_v{BUNDLE}_engine{ENGINE}_Complete_Package.zip` — so a package is
self-identifying even when found loose.

## Keeping them aligned

`tools/sync_version.py` writes the versions everywhere they appear;
`tests/test_version_sync.py`, `test_no_stale_version_literals_*`, and
`test_docs_version_drift.py` fail the build on drift. **When you bump a version, run sync_version
and re-run the version tests** — that is the whole ritual.

## Why the paranoia — the documented freeze history

`CURRENT_DOCS_INDEX.md` (the authority for which docs are current) records its own failures, and
they justify the machinery:

- Its header **froze at v9.7.136** while cuts advanced (caught at v9.7.335 — and three of the four
  filenames it pointed to did not exist).
- It froze **again at v9.7.337 for 29 cuts** (caught 2026-08-15).
- A fix was *described* at .366 but not implemented — and the index froze a **third** time at
  v9.7.367, caught inside the sealed .370 bundle.
- v9.7.371 landed the real ratchet: `sync_version.py` owns the header, `--check` fails on drift,
  and `test_docs_version_drift.py` covers it.

The lesson generalizes: a version stamp that is not machine-owned WILL drift, and drift survives
sealing. Never hand-edit a version literal; let the sync tool own every copy.

## Practical rules

- **Citing a run**: quote bundle + engine together (they are both in the package ZIP name and
  `manifest.json`). A Mode-B card or deliverable on disk may be from an older engine — verify
  against the current engine before asserting a defect or building on its content.
- **Reading docs**: `CURRENT_DOCS_INDEX.md` in the current bundle decides which docs are current;
  historical root notes are shipped but superseded.
- **Cut procedure**: version bump → `sync_version.py` → version tests → seal. Only the project
  owner seals a cut.
