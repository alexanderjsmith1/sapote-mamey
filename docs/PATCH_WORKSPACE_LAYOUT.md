# Patch workspace layout — disposition is legible from location

Companion to `docs/PATCH_PACKET_POLICY.md`. That policy says what a packet may **contain** (no
assemblies, no caches, size caps) and is enforced by `tools/patch_packet_preflight.py`. This document
says how a patch workspace is **arranged** — so a reader (a person or the next chat) can tell any
artifact's fate without opening it — and is enforced by `tools/check_patch_lane.py`.

The failure this prevents: a flat pile where an audit report, a half-finished patch, a frozen prior
cut, and a disposable log all sit at the same level, and nobody can tell which the Patch Chat should
apply. A folder named `figure_factory_effort/` that carries five audit reports and zero `.patch`
files is the symptom — its name gives no signal, so someone has to ask.
`docs/ANTIPATTERN_WORKSPACE_AMBIGUITY.md` is a dated, real case study of exactly this state and what
it cost — read it for the *why*; this document is the *rule*.

## The rule: four dispositions, and an artifact is exactly one

Disposition is declared by **location**, never by reading the file:

| Directory | Disposition | The Patch Chat… |
|---|---|---|
| `for-cut/` | patch lanes ready to apply | **applies these** |
| `reports/` | audits, plans, findings | reads for context; never applies |
| `archive/v9.7.N/` | frozen prior cuts | ignores |
| `scratch/` | logs, transcripts, throwaways | ignores; safe to delete |

One `README.md` at the workspace root is the single entry point: it names these four and points at
the live cut. It is the first file a new chat reads.

## What a report is (the front-matter rule)

A **report** must state, in its **first three lines**, what it concerns — so a reader knows in ten
seconds, not by digging a version out of a harness path halfway down. The opening is:

```
# <title>

> **Base:** v9.7.408 · **Audited:** 2026-09-05 · **Disposition:** report
```

The base is the **full `v9.7.N`** (never a bare `408`) of the bundle the report actually concerns —
taken from the report's own content, not the folder it happens to sit in. A report whose base is
genuinely unknown says `**Base:** (unstated in source)` rather than guessing. This is the reports-side
analogue of the lane's completeness rule, and `check_patch_lane.py --reports <dir>` enforces it.

## What a lane is (the hard rule)

A **lane** is *one issue = one folder* under `for-cut/`, containing exactly:

- **one `*.patch`** — a unified diff that applies `patch -p1 --fuzz=0` to the named pristine baseline;
- **`PATCH_CARD.md`** — premise (verified before patching), fix, fail-before/pass-after evidence,
  co-apply notes, and the baseline it targets;
- **at least one test** — `test_*.py` (or, for a figure/asset lane, a parity/contract test), also
  carried inside the `.patch` as `tests/…` so it travels with the fix.

A folder under `for-cut/` missing any of the three **is not a lane** and is not cut-selectable. It is
either unfinished (finish it) or not a patch at all (move it to `reports/` or `scratch/`).

This is the completeness check `patch_packet_preflight.py` does not do: preflight rejects a packet
that contains junk; `check_patch_lane.py` rejects a lane that is *missing* its card, its test, or its
diff — or a stream folder that has loose material with no disposition.

## Naming

**Every versioned name uses the full `v9.7.N` form — never a bare number, and there is NO exemption
for lane slugs.** `408`/`410` is ambiguous (a build? a port? a count? a *strain*? — this project has a
strain named 410); `v9.7.410` is thousands of times less likely to collide. A folder called
`deep-audit-408/` fails this rule, and so does a lane folder `CLAUDE_410_<slug>` — a lane is a unit
that gets copied and shared on its own, so the bare number travels with it wherever it goes. An earlier draft of this convention exempted lane slugs on the theory that the author prefix
disambiguates — that was wrong (the prefix says *who*, not *which version*) and is corrected here.

- Lane folder: `<AUTHOR>_v9.7.<N>_<slug>` — e.g. `CLAUDE_v9.7.410_modeb_heading_regex`. When the slug
  itself references another release, that reference is also full form
  (`CLAUDE_v9.7.410_blastp_bgc_recovery_v9.7.409`). No dates smeared into filenames (the version *is*
  the anchor).
- Archive: `archive/v9.7.408/`, `archive/v9.7.409/` — full version at the boundary, frozen, never
  edited. Bare `archive/408/` is forbidden.
- Stream folder: `Patches for Sapote Mamey Claude (v9.7.410)/` — full version, the disposition marker
  for the whole stream.

**One deliberate boundary:** test *files inside a patch* keep their `test_410_*.py` name. They live
inside a bundle whose own directory and `BUILD_STAMP` carry `v9.7.410`, so the version context always
travels with them, and renaming them would break the shipped test contract and the co-apply with
other patch streams. The rule targets names that circulate *standalone* — folders, stream wrappers,
archive dirs, report files.

## Usage

```bash
# One lane — is it complete and cut-ready?
python tools/check_patch_lane.py --lane for-cut/CLAUDE_410_modeb_heading_regex

# A whole stream — every lane complete, nothing mis-filed?
python tools/check_patch_lane.py --stream "for-cut/Patches for Sapote Mamey Claude (v9.7.410)"
```

Exit 0 = every lane is complete and correctly disposed. Exit 1 = at least one lane is incomplete or a
non-lane artifact is filed as cut-bound; the report names each.

Passing this check does not accept, integrate, seal, or scientifically validate anything — like the
preflight, it is a mechanical gate. See `CUT_PROTOCOL.md` for the confirm-before-cut handshake.
