# What's new — v9.7.368 → v9.7.370 (user-facing surface)

*Companion to `CURRENT_DOCS_INDEX.md`; one section per user-visible capability added since the GUIDE
docs' last content refresh. Every item is class-level tooling; judgment stays deferred.*

## Breaking / behavior changes you must know
- **`tools/bigscape_prep.py` now REQUIRES `--strictness {loose|relaxed|strict}`** (v9.7.370, Amber).
  It detects each input's antiSMASH strictness and refuses silent flavor mixing; JSON-less inputs
  need `--assume-strictness <flavor>` to force; every staging writes a `STRICTNESS_MANIFEST.tsv`
  provenance record into the output dir. Old flagless invocations FAIL by design (exit 2).
- **Engine 1.9.122 (v9.7.369):** Mode-B §31–§48 depth is enforceable (full48 gate binding; §32–§34
  bind to the measured-assembly-line predicate — a product LABEL never makes them required).
- **Engine 1.9.123 (v9.7.370):** `verify-modeb` and the ingest/record door now share ONE context
  (W7) — on degraded/historical cards verify can newly ERROR where a predicate previously could not
  be evaluated; that is the fix working. Re-lint authored cards under 1.9.123 (the sealed corpus
  re-lint receipt: 1,559/1,559 OK).

## New pre-authoring / QC steps
- **`python mamey_run.py modeb-availability`** (v9.7.370, Codex): formal pre-authoring
  data-availability inventory — evidence streams bound to canonical loci, STRAIN_ONLY/UNBOUND/ABSENT
  states, §1–§30 channel map, manifest-backed work order. Run it BEFORE authoring a Mode-B card.
- **`tools/modeb_card_guard.py`** (v9.7.370, the review lane): identity QC — diffs a card's §1/§12 stated
  genus + ecology against the strain's authoritative `STRAIN_CARD.md`. Run on every authored card.

## Asset & compute discipline (the full loop now ships)
- **`tools/find_asset.py`** — find before compute (`--check` exits 3 on a redundant fetch).
- **`hooks/check_local_assets_before_download.sh`** — gates redundant downloads AND redundant heavy
  recompute (bigscape/gtotree/antismash/clinker signatures).
- **`tools/register_compute_output.py`** (since .369) — register after compute.

## BLASTp operations
- **`tools/blastp_coverage_wave.py`** (v9.7.370, VGP): measure coverage gaps off `blastp.sqlite`,
  stage isolated-ledger submission waves with receipts, plot coverage.
- **`tools/ingest_swissprot_local.py`** (v9.7.370, VGP): idempotent local-SwissProt channel loader
  (`local_swissprot`, 22-col schema, `--dry-run` default).

## Guardrails that now travel with the bundle
- **`sapote_hooks/sapote_hooks.py`** (v9.7.370, VGP): `capture` / `list` / `verify` / `install` over
  the 32-hook registry (`HOOKS_MANIFEST.tsv`). On a new workspace: `install --apply --bundle hooks/`
  wires the whole guard set portably (`$SAPOTE_WORKSPACE_ROOT`/`$CLAUDE_PROJECT_DIR`). `verify
  --gate` is CI-usable; the seal-path wiring (`hooks/SEAL_GATE_snippet.sh`) ships as a documented
  drop-in, deliberately not auto-wired at .370.
- **`hooks/verify_before_assert_contract.py`** (the phylogenomics lane) and **`hooks/block_out_of_bounds_writes.py`**
  now ship in-bundle.

## v9.7.368 in one line
MULTI_CHANNEL_HOLD wave — engine-neutral evidence-channel HOLD accounting in non-whitelisted `_4D`
artifacts (see `CHANGELOG.md` for the full entry).
