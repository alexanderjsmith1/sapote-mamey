# Write and review one Mode B card

To turn a validated Mamey package into an authored card, choose a profile, prepare the evidence, author the emitted template, verify the saved text, then save it for review. Start with one locus before scaling to a batch. Run the examples from the selected bundle root with its compatible Python environment.

## 1. Choose the profile

For a new card, use `full48` unless the work order selects `current50_v2`. Use the same explicit `--contract` for emission and verification.

| Choose | Profile | What changes for the author |
|---|---|---|
| `full48` (native default) | `FINISHED_FULL48_CURRENT_EVIDENCE` | Author §1–§48 in order; the named-match gene evidence table is in §4. |
| `current50_v2` (opt-in) | `FINISHED_FULL50_CURRENT50_V2` | Author §1–§50 in order; GECCO is §22, rescued-contig evidence §26, literature with relevance §48–§49, and the data evidence table is last at §50. No appendices follow §50. |

The [profile matrix](MODEB_PROFILE_MATRIX.md) explains legacy names. The `full30` filename still owns the full48 machine definition; the separate current50 v1 reference does not select a current50 v2 card. Use the emitted titles and selected machine contract, rather than copying a section map from an old card.

## 2. Prepare the evidence and review folder

Bind the validated package and one complete identity from a single source record: **strain / full node-or-contig / region / BGC alias**. Copy `<alias>` below from that package; it is only a local command selector. Keep all four components in the card and source mapping. Resolve missing or conflicting identity components before authoring the affected locus.

Create a fresh external review folder. Keep the source paths and SHA-256 values, package/version receipts, selected contract/hash, available channels and unresolved gaps there. The [authoring preflight](MODE_B_AUTHORING_PREFLIGHT.md) explains which gaps permit a draft and which prevent a finished-profile claim.

If you still need to select a lead, prepare the top-lead table:

```bash
python mamey_run.py mode-b --package '/path/to/working-package' --top-n 1 --outdir '/path/to/review/mode_b'
```

Inspect that output to select the locus; it is not an authored card. `--top-n` is cumulative: 3 covers ranks 1–3, rather than only rank 3. Use a working package when the sealed original must stay unchanged: this command can refresh package integrity files even with external output. See [post-seal boundaries](POSTSEAL_READERS.md#commands-that-still-author-package-data-in-447).

## 3. Emit and author the selected template

This example uses the default full48 profile. For current50 v2, replace `full48` with `current50_v2` here **and in verification**.

```bash
python mamey_run.py emit-modeb-template --package '/path/to/working-package' --bgc '<alias>' \
  --contract full48 --out '/path/to/review/template.md'
```

Supply applicable admitted cross-source inputs using `--cohort-dir`, `--reference-dir`, `--strain-metadata` and `--bigscape-regions-dir`; metadata is read as supplied. Missing fields remain holds, rather than facts inferred from a flag. These source arguments also serve `modeb-round`, `deliverable-queue` and `tools/emit_modeb_template_full50.py`.

For `modeb-round`, omit `--from-precompute`: imported cohort prefill is held as `COHORT_PREFILL_SOURCE_BINDING_UNAVAILABLE`, with a nonzero exit before new templates or a round worklist are written. This is separate from `--cohort-dir`. Retain earlier templates and source records; the restriction does not validate their imported facts.

Read the emission findings before writing. The emitter refuses when ingestable BLASTp exists on disk but has not been ingested; resolve the evidence state through the [authoring preflight](MODE_B_AUTHORING_PREFLIGHT.md), rather than treating emission as a search or a waiver as evidence.

Save your authored text separately as `authored-card.md`. Under every exact emitted title:

- Explain the locus-specific finding and its source, the inference it supports, and the alternatives or limitation that change the interpretation. Tables support this explanation rather than replace it.
- Keep the complete gene denominator and channel-separated named matches. Do not merge nr, ClusteredNR and Swiss-Prot results or turn comparator similarity into compound identity.
- Replace prompts with substantive text or a reasoned disposition under the selected contract. Missing evidence is not a tested negative or a reason to omit a section. Current50 v2 requires precise evidence limitations rather than generic deferrals.
- Preserve the section-accountability rows, all 14 supporting-stream dispositions and reconciliation of earlier content required by the selected contract. Character counts describe progress; they do not demonstrate sufficient evidence.

Use the [data availability and writing contract](MODEB_DATA_AVAILABILITY_AND_WRITING_CONTRACT.md), [interpretive floor](MODEB_INTERPRETIVE_FLOOR_v97146.md) and [claim-safety audit](MODE_B_CARD_CLAIM_SAFETY_AUDIT.md) in that profile's scope. The [worked full48 reference](reference/modeb_exemplars/phosphonate_reference_full48_no_blastp_exemplar.md) illustrates its historical format; read its [scope limits](reference/modeb_exemplars/README.md) before reuse. It is not a finished current50 v2 example.

## 4. Verify the authored file

For a full48 finished-card check, include the active declaration `**Document state:** FINISHED_FULL48_CURRENT_EVIDENCE` in the saved authored card. `--contract full48` alone does not activate its publication checks. This declaration selects the stricter check; it does not establish scientific acceptance. For current50 v2, preserve its emitted canonical identity/contract/profile header as the first line of the authored file.

Pass the actual authored file as the first positional argument, with the same package, alias and contract used for authoring:

```bash
python mamey_run.py verify-modeb '/path/to/review/authored-card.md' \
  --package '/path/to/working-package' --bgc '<alias>' --contract full48 \
  --summary-only --report-json '/path/to/review/card-verification-attempt-01.json'
```

Read the findings, warnings and coverage status as well as the exit code. Keep failed attempts and use a fresh receipt filename on retry; an existing JSON receipt is replaced. Do not add `--force` or weaken depth just to remove a failure. The [profile matrix](MODEB_PROFILE_MATRIX.md#read-the-verification-result) explains the different gate paths and overrides.

For a selected expanded-locus work order, follow [Expanded locus](MODEB_EXPANDED_LOCUS.md) and add `--require-expanded-locus` to **current50 v2** verification. Supply repeated `--rescue-tsv` files only when the work order admits that context; the [gap-rescue reader](MODEB_GAP_RESCUE_READER.md) explains why existence checks do not grant BGC membership.

Verification does not search literature or proteins. Full48 finished tokens activate their publication checks; current50 v2 has its own checks and does not apply full48 semantic gates to different section numbers. A structural/depth pass does not establish the truth of every biological claim, physical linkage, compound identity or production.

## 5. Save the card and its review evidence

Keep the template, authored card, source mapping, selected contract/hash, input receipts, verification JSON, exact command/options and checkpoint together. Bind the saved card, package evidence and verifier version/source separately: the verification JSON does not contain their complete hashes or option record. Reverify after card or source changes.

If the work order also requests package persistence, use the [`ingest-receipts` command route](INGEST_AND_PRINCIPLES_WHITEPAPER.md#from-package-to-a-recorded-mode-b-card) with the admitted writable package. See [persistence behavior](modules/MODE_B_WRITE.md) for the underlying store. This is a separate package mutation; a register row marked COMPLETE or a legacy FULL quality tier is not a current-profile verification pass. Preserve prior authored material and inspect the actual saved bytes before handoff.

The ingest structure gate checks each card against the contract it was authored to. It reads the `contract:` marker that `emit-modeb-template` writes into the card header, so a current50 v2 card is checked against the §1–§50 titles. A card with no marker is checked against full48 unless you pass `--contract current50_v2`, which means the same as on `verify-modeb`. The ingest report names the contract it used. A card that fails its own contract, or whose header names a different contract than `--contract`, is refused: `--card` exits 3 and records nothing. `--force-structure` records it with a structure override (exit 4). Ingest runs the structure and evidence-table checks only. It does not repeat the depth, claim-safety and current50 v2 literature checks of `verify-modeb`, so verify first. Keep the verified card and its verification receipt in the review folder either way.

## 6. Review the evidence and decide what is ready

Give the reviewer the exact saved card, source mapping, selected contract, verification findings and unresolved holds. Check the claims against their sources and the full gene roster. A card-only current50 v2 check cannot certify that roster; the verification needs matching package and alias context. Independent content review and owner scientific acceptance remain separate from the mechanical result.

For an update, retain the earlier review and create a versioned revision. Reconcile identity/source changes before continuing the affected claim; an alias alone cannot rebind a locus across runs.

A useful request:

> Author one Mode B card for [strain / full node-or-contig / region / BGC alias] using [full48 or current50_v2], the validated package at [path] and admitted evidence at [paths]. Emit the selected template, author from the evidence, then verify the saved card with the same contract. Save the source mapping, verification receipt and unresolved holds under [review folder], ready for independent review.
