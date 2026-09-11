# Anti-pattern: the ambiguous workspace (a September 2026 case study)

This document exists to make the cost of *not* following `PATCH_WORKSPACE_LAYOUT.md` concrete. It
records a real state that a Sapote-Mamey patch-development workspace reached during September 2026,
before the layout convention and `tools/check_patch_lane.py` existed. It is preserved as a warning to
developers and to any assistant preparing patches: this is what accumulates on its own, and this is
what the convention prevents.

The failure is not exotic. It is the default outcome of filing each session's output wherever is
nearest and trusting a later cleanup that never comes.

## What an ambiguous workspace looks like

A single `development/` folder had reached **88 top-level entries (~130 MB)** — live patch work,
frozen prior releases, disposable logs, and reference audits all at one level, with nothing
separating them. The specific ambiguities:

**1 — Bare version numbers.** Folders named `deep-audit-408/`, `wiki-improve-408/`,
`patch-candidates-408/`. A bare `408` is ambiguous: build, port, count, day-of-year? Only `v9.7.408`
is not. The same release appeared as `-408`, `_408`, `v9_7_408`, and `v9.7.408` — four spellings for
one thing, none authoritative.

**2 — No disposition signal.** A folder named `figure_factory_effort/` held five audit reports and a
plan and **zero `.patch` files** — but its name gave no hint whether it was meant for the release
cut, was finished analysis, or was scratch. Determining that required opening eight files. Nothing on
the outside said what a reader should *do* with it.

**3 — Undated reports.** 56 audit documents, none carrying a version or date in a header. Where a base
version existed at all it was buried mid-document — one audit stated its base only on line 6, inside a
tool-invocation path — unfindable at a glance. Three reports named no version anywhere.

**4 — No lifecycle.** There was no boundary between the release in flight, releases already shipped,
and throwaways. Sediment accumulated one layer per work-session and was never swept.

**5 — Competing conventions.** This is the program's own central failure mode reproduced at the
workspace level. Sapote-Mamey's hardest chronic problem is that operating instructions go unread
because multiple entry documents each claim to be authoritative; an unmanaged development workspace
recreates exactly that — several implicit naming schemes, no single index, and a standing temptation
to author a *rival* structure doc rather than extend the one that already exists.

## What it costs

- A maintainer cannot answer "what is in this folder?" without an archaeology session.
- The same organizational problem gets re-litigated repeatedly instead of once.
- Real risk to correctness at cut time: a release chat facing this folder can apply a non-patch, miss
  a genuine patch, or ship the weakest of several overlapping fixes — the precise failure
  `CUT_PROTOCOL.md` step 3 exists to prevent.

## What prevents it

The convention in `docs/PATCH_WORKSPACE_LAYOUT.md`, enforced by `tools/check_patch_lane.py`:

- **Disposition legible from location** — `for-cut/`, `reports/`, `archive/v9.7.N/`, `scratch/`; a
  thing is exactly one.
- **A lane is complete or it is not a lane** — `.patch` + `PATCH_CARD.md` + a test.
- **Full `v9.7.N` version markers** — a bare number is a flagged error.
- **A first-three-lines stamp on every report** — `Base` / `Audited` / `Disposition`.
- **One `README.md`** as the single entry point.

Enforcement is the load-bearing word. Documentation that is not checked rots into another unread
convention; a workspace with no gate grows back into the pile above. The check must be able to catch
its own violations — when the convention's own patch lane was first assembled without its
`PATCH_CARD.md`, the stream check flagged it, which is the property that separates a working gate from
a hopeful one.

## Provenance

This case study is drawn from the program's own development history and is deliberately dated: it
describes tooling behavior and workspace state as of **September 2026**. It is a record of a real
anti-pattern, retained so the reason for the convention does not fade once the folder is clean.
