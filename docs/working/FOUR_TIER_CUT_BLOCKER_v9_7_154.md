# Four-tier cut — why it can't run from this CODE artifact (read before cutting v9.7.154)

**Short version:** the v9.7.154 changes are ready as a **patch**, but the four-tier cut
(`tools/make_public_tier.sh code|clean|sid|merged`) **cannot** be run from the uploaded
`sapote-mamey-v9_7_153-CODE-…` bundle. It must run from the **private superset source tree** (the
merge-chat bundle that still contains `private/`, `cohort/`, and real AS IDs). Apply this patch to
that tree, then cut.

## Why (verified against the uploaded bundle)

`make_public_tier.sh` produces tiers by stripping + redacting **down** from a private superset:

- `code`   → removes `private/ cohort/ merged_cohort/ data/ …`, scrubs AS IDs → `AS-XXX`.
- `clean`  → code, plus removes worked analyses/figures and anonymizes SID IDs.
- `sid`    → removes `private/` but **keeps `cohort/` SID banks** (the SID data tier).
- `merged` → keeps **everything**, including `private/` and **real AS IDs** (the private scaffold).

The uploaded CODE bundle is the *output* of that process, not a valid *input*:

| Required input dir | Present in CODE bundle? |
|---|---|
| `private/` | **absent** |
| `cohort/` (SID banks) | **absent** |
| `merged_cohort/` | **absent** |
| `data/` | **absent** |
| `tools/release_denylist.txt` | **absent** |

Consequences:
- `merged` tier is impossible — there is no `private/` or real-AS-ID data to keep.
- `sid` tier would ship **without** the SID `cohort/` banks it is defined to contain.
- `code`/`clean` would "work" but only because the tree is already redaction-shaped; they would not
  be a real derivation from the private source, so the tier-derivation parity gate
  (`verify_tier_derivation.py`, which asserts `public == redact(private)`) has no private source to
  compare against.

The leak audit confirms the tree's state: `redact_public_tier.py --check-only --as-only` reports
**29 strain IDs** present (e.g. AS-XXX, AS-XXX, AS-XXX, AS-XXX, AS-XXX) — expected in a *private
source* (the redactor would scrub them in write-mode first), but this bundle is not that source.
These IDs predate the v9.7.154 patch (they are in the v9.7.153 CHANGELOG/docs/code history).

## Environment prerequisites also unmet here

Per `CUT_PROTOCOL.md` step 0, the cut needs `pytest` (+ `pluggy`, `iniconfig`) for the in-tier
pytest gate, the post-cut unpublished-ID invariant, and step-5 artifact verification. This sandbox
has no pytest and no network to install it. `SKIP_INTIER_PYTEST=1` can bypass only the in-tier
suite (and only after out-of-band verification); the leak audit, version-sync, redaction, and
tier-derivation parity gates are **un-skippable**.

## The correct path to a v9.7.154 four-tier cut

1. Go to the chat / location that holds the **private superset** source tree (the one imported last
   time — has `private/` + `cohort/` + real AS IDs + `release_denylist.txt`).
2. Apply `sapote-mamey-v9_7_154_candidate.patch` there (`patch -p1`). It touches only the files in
   the patch (engine fixes, tests, docs, version anchors) — none of which are private data — so it
   applies cleanly on the superset too. **Re-confirm** the patch applies (the superset may carry
   private-only files the patch doesn't reference; that's fine — `patch` ignores them).
3. Upload `pytest`/`pluggy`/`iniconfig` wheels (CUT_PROTOCOL step 0).
4. Run the full suite once on the assembled superset source (CUT_PROTOCOL step 4) — expect 0 failed
   after PATCH-004; the flake only shows at full-suite scope.
5. Cut all four tiers from the superset:
   ```
   tools/make_public_tier.sh code   <superset> <out>
   tools/make_public_tier.sh clean  <superset> <out>
   tools/make_public_tier.sh sid    <superset> <out>
   tools/make_public_tier.sh merged <superset> <out>
   ```
6. Step-5 artifact verification: extract each public zip to scratch and re-run `pytest tests/`;
   compare counts to step 4.
7. Per the multi-tier disclosure rule, confirm the `tests/` changes (PATCH-001/004/005 regression
   tests) land **identically** across CODE / CODE-analysis-free / SID-public / MERGED; flag any tier
   whose `tests/` diverges.

## One fix folded in for the cut's sake

My new regression tests originally reused the existing `AS-XXX|BGC002|…` fixture header. `AS-XXX` is
a **real cohort strain**, not on `tools/test_synthetic_ids.txt`, so the tests/-leak-audit in
`make_public_tier.sh` would fail the cut on it. The two lines I added now use the allowlisted
synthetic `AS-XXX`. **Pre-existing** `AS-XXX` occurrences in `test_blastp_followup_v97142.py`
(lines ~9–63, authored before this session) were left untouched — they are a separate, pre-existing
finding: either scrub them to a synthetic or confirm the tests/-leak-audit already accounts for them
before relying on a green cut. Flagging rather than silently rewriting tests I didn't author.
