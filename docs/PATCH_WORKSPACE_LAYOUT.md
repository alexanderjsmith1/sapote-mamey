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
| `for-cut/` | patch lanes ready to apply | reviews/selects them under the current authorized task |
| `reports/` | audits, plans, findings | reads for context; never applies |
| `archive/v9.7.N/` | frozen prior cuts | ignores |
| `scratch/` | logs, transcripts, throwaways | ignores for cut selection; retention/deletion requires a separate explicit disposition |

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
python tools/check_patch_lane.py --lane for-cut/CLAUDE_v9.7.410_modeb_heading_regex

# A whole stream — every lane complete, nothing mis-filed?
python tools/check_patch_lane.py --stream "for-cut/Patches for Sapote Mamey Claude (v9.7.410)"
```

Exit 0 means the selected mode recorded no implemented structural findings; it does not establish the complete lane policy below. Exit 1 reports recorded findings. A nonexistent or non-directory target is refused with exit 2; argument errors also exit 2. Unexpected traversal errors can raise instead of producing a normal checker report.

Passing this check does not accept, integrate, seal, or scientifically validate anything — like the
preflight, it is a mechanical gate. See `CUT_PROTOCOL.md` for the confirm-before-cut handshake.

## Mechanical checks are narrower than the policy

`tools/check_patch_lane.py:89–126` recursively looks for patch files, a card and matching test filenames. It does not enforce exactly one diff, validate card/test content, apply `patch -p1 --fuzz=0`, or execute tests. Its tests/ diff check is a text-marker check; despite the message saying “soft”, that finding participates in a nonzero result. Verify baseline hash, applyability and meaningful validation separately before selection.

Naming policy above uses complete versions. The implemented bare-number regex only recognizes 400–419, and naming checks run on stream child names rather than standalone `--lane` names (`:39–57,160–199`). A clean exit therefore does not certify all names obey policy. Report checks require Base/Disposition tokens and some full version or explicit unstated marker in the first three lines; they do not parse or require a valid Audited date (`:129–155`). Empty report directories can also pass without an audited report.

The checker inspects selected structures and diff-header paths; it is not a filesystem containment or archive safety certificate. Neither a for-cut location nor a zero exit authorizes applying, publishing, deleting or moving evidence. Keep evidence at its source path with SHA-256 locators, use one staged candidate for modified files, and maintain the authoritative workspace index. Logs/transcripts may be unique evidence even under scratch; preserve them until their actual retention disposition is authorized.

Check the actual input roles before selecting a lane. Recursive card/test name matches can be directories rather than readable regular files, and patch text containing the `+++ b/tests/` marker can pass without valid unified-diff hunks. A directory named `*.patch` instead produces a read finding. Independently verify the intended file roster, regular/readable payloads, meaningful card/test content and valid diff syntax (`tools/check_patch_lane.py:65–119`).

Diff-path screening tokenizes `---`/`+++` headers by non-whitespace text and checks a leading slash or a `..` component. Quoted absolute/parent paths and drive-qualified paths are not fully parsed or refused by that test. Have the selected patch tool and a separate reviewed target/containment check resolve every actual touched path before application; a clean structural result is not permission to apply a diff (`:73–85,110–118`).

For `--reports`, every recursively discovered Markdown file named `README.md` or `INDEX.md` is skipped, including nested files. Other reports are read in full, but only the first three lines are examined; a full version elsewhere in those lines can satisfy the test even when the Base field itself is invalid. For `--stream`, dot-prefixed children, `__pycache__` and underscore-prefixed directories are omitted, while top-level `.md`, `.tsv`, `.json` and `.txt` files receive no content/disposition check. Reconcile intended, inspected and skipped material independently (`:122–181`).

Results go to the terminal; there is no saved input roster, content/hash receipt or report-output option. Preserve the selected mode/path, actual exit status, full diagnostics and source hashes in a fresh disjoint receipt. If a read/traversal failure interrupts the check, preserve its diagnostics and rerun only after the input issue is resolved; neither a leftover log nor its absence establishes a completed check (`:184–211`).

See [packet-content scope](PATCH_PACKET_POLICY.md). Record checker execution and any authorized application, move or deletion separately.

## Optional composition-screen scope

```bash
python tools/patch_queue_composition_audit.py '<selected-queue>' --base '<reviewed-base>' --json
```

This read-only advisory screen compares selected file drops and asks whether individual diffs apply to the pristine base. It does not apply the queue, resolve dependency order, run tests or certify the final composed tree. Preserve the authoritative base, selected card roster, expected apply order and required independent validation.

Discovery walks only immediate queue subdirectories; loose root-level patches are omitted. A card with a root/one-level bundle-marker filename is skipped as an audit working tree. More than 200 recursively discovered entries also triggers this skip, counting directories as well as files. Non-diff scaffolding is excluded, but `.patch`/`.diff` recognition runs before the scaffold check, so scaffold diffs are still selected. Recognized binary suffixes are not line-compared; debris has its own warning. Keep a complete intended/selected/skipped inventory rather than treating report rows as all queue material (`tools/patch_queue_composition_audit.py:118–140,209–247`).

Mirrored payload paths map at the first recognized bundle-root component. A bare card-root filename uses the first matching root in the fixed root list; multiple basename matches are not refused. Cross-card collision checks concern file drops with the same mapped target and differing digests, not overlapping diff changes or diff/drop interactions. Multiple drops for one target within a card collapse to that card's last digest and can conceal a conflict. Review exact target mapping and every payload identity independently before composition (`:70–87,250–264`).

Text drops use ordered line comparison, including repeats and line endings. A removal warning can represent a deliberate rewrite; retain its reviewed intent as a diff or explicit resolution. Unreadable UTF-8 also produces a removal warning with zero counted removed lines, which does not mean zero change. Do not use the count as a complete impact estimate (`:90–113`).

Diff checks run native `git apply --check` and strict forward `patch -p1 --dry-run --fuzz=0`, sometimes a reverse dry-run, each with a 60-second timeout. Missing tools or initial command exceptions/timeouts return `DIFF`/`OK` with an apply-check-skipped note. The ordinary text display hides `DIFF` entries, including that note; `--json` retains it. Review skipped checks explicitly and retain tool versions, full diagnostics and input hashes. A reverse-check failure after forward rejection can instead be informational. A pristine-base failure does not establish that a patch is valid after another patch, and disagreement between apply tools requires a reviewed choice or regenerated patch (`:143–206`).

Exit 0 is advisory even with WARN findings; only a non-directory queue/base is explicitly refused with exit 2. Unexpected traversal/read errors can raise. JSON goes to stdout and has no source hashes, tool-status receipt or saved report transaction; shell redirection can itself overwrite evidence, so use a fresh disjoint report path. Text totals count finding entries, including synthetic collision/working-tree rows; its file-drop count also includes several non-drop codes. Use exact per-entry codes and the independent roster rather than these totals as a denominator (`:267–308`).

