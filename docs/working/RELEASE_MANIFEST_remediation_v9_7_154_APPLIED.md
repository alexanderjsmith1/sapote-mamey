# RELEASE_MANIFEST.md remediation — APPLIED in v9.7.154

Responds to `RELEASE_MANIFEST_remediation_v9.7.154_spec.md`. Unlike the spec (which deliberately
stayed hands-off the v9.7.153 artifact), this cut **is** v9.7.154, so the remediation is applied
here, not just specified.

## Applied

1. **Stale `## Patches in v9.7.148b` → `## Patches in v9.7.149–v9.7.154`.** Rewritten with accurate
   v9.7.152/153 history (from CHANGELOG) and the v9.7.154 bug-fix list. **v9.7.149–151 flagged as an
   explicit GAP**, not guessed — the cutting chats for those revisions should backfill.
2. **"Known limits" pytest text corrected.** The prior claim that the 7 full-suite failures were a
   "pre-existing pandas 3.0.2 incompatibility in `mamey.mode_b.schema`" was **wrong**. They were the
   `sys.modules` leak in `test_bunny_hop_fixes.py` (PATCH-004), now fixed; full suite is clean. Text
   replaced accordingly, with a pointer to re-run the **full** suite (the bug never shows in isolation).
3. **Stale current-state version strings updated.** The derived-anchors build stamp
   (`20260630v97153a → 20260630v97154a`), the inner `sync_version --check` table row, and the two
   "all anchors at v9.7.153" lines now read v9.7.154. Historical references (e.g. "v9.7.153 artifact
   audit") were intentionally left.
4. **Footer tier token `PUBLIC_RELEASE` → `NOT_FOR_PUBLIC_RELEASE`** (see fork below), done in
   lockstep with the tooling trap:
   - `tools/sync_version.py` footer regex `\g<2>` literal updated `PUBLIC_RELEASE\*` →
     `NOT_FOR_PUBLIC_RELEASE\*`. Verified a full `sync_version.py` round-trip + `--check` PASS — the
     version still syncs and the token does not drift.
   - `tools/gen_release_manifest.py` footer rule captures only up to ` |` (token is outside its
     group), so it needed no token change; `--check` PASS confirmed.

## Fork — the tier token choice (surfaced, not silently picked)

`PUBLIC_RELEASE` was a **false claim** on a CODE-tier, non-signed artifact (contradicted by
`Release profile: CODE` and the redaction-blocked "public promotion is blocked" bullet). Leaving it
was not safe, so this cut replaced it with the unambiguously-safe `NOT_FOR_PUBLIC_RELEASE` — a token
that can only *over*-state restriction, never under-state it. If you prefer a neutral tier label over
a restriction label, override to one of:

1. **`NOT_FOR_PUBLIC_RELEASE`** (current choice) — safest; states the restriction explicitly.
2. **`CODE`** — matches `Release profile: CODE` line 9 and `TIER_NOTE_CODE.md`; neutral tier label.
3. **`CODE_TIER`** — same intent as (2), more explicit it's a tier classification.

Whatever is chosen, the literal must change in **both** `tools/sync_version.py` (the `\g<2>` backref)
and the `RELEASE_MANIFEST.md` footer in lockstep, or the next cut fails to sync. `gen_release_manifest.py`
is unaffected (token outside its capture).

## Not done (deliberately deferred — structural, separate change)

**Prevent-recurrence (spec item C):** bringing the two date fields and the tier token under
`gen_release_manifest.py`'s anchored set (so no field is tool-unowned) is the durable fix, but it's a
tooling change beyond this bug-fix cut's scope. Recommended as a v9.7.155 follow-up. Until then, the
tier token is owned by `sync_version.py`'s footer rule (as of this cut) but the **dates** are still
tool-unowned and must be manually verified at cut time — add an explicit line to `CUT_PROTOCOL.md`'s
handback step if anchoring is deferred again.
