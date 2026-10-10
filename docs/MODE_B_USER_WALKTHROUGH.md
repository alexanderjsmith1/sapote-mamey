# From extraction to an authored Mode B card

Start with a validated Mamey package and one source-bound identity: **strain / full node-or-contig / region / BGC alias**. A complete extraction, ranked table or emitted template is not an authored scientific interpretation. This walkthrough is bound to .447 / engine 1.9.172; use the selected bundle's launcher from its root.

## Choose the profile before writing

Use the [profile matrix](MODEB_PROFILE_MATRIX.md). The native emitter and verifier accept two named command contracts in .447:

| Command contract | Card profile | Scope |
|---|---|---|
| `full48` | `FINISHED_FULL48_CURRENT_EVIDENCE` | Default 48-section current-evidence profile |
| `current50_v2` | `FINISHED_FULL50_CURRENT50_V2` | Opt-in 50-section profile, with GECCO in §22, rescued-contig evidence in §26, literature relevance in §48–§49 and the evidence matrix last at §50 |

Select the requested profile explicitly and carry the same contract through template emission and verification. The [current50 v2 guide](MODEB_CURRENT50_V2_CONTRACT.md) explains its independent roster checks and scientific limits. The machine definitions are `mamey/data/mode_b/modeb_full30_corrective_contract.json` (historical filename, current full48 schema) and `mamey/data/mode_b/modeb_current50_v2_contract.json`. Preserve their pinned bytes; the emitted titles and selected machine contract govern coverage.

The frozen [current50 v1 reference](MODEB_50_SECTION_CONTRACT_CANDIDATE.md) and its [four-consumer usage contract](MODEB_FULL50_CONTRACT_USAGE.md) remain separate reference objects. They are not the current50 v2 card profile. Older 20/30-section instructions and the former .429/.430 migration notes are history, not completion requirements for a new .447 card. Do not use a copied section map from another profile.

## Prepare a bounded review

Use a fresh external review folder. Replace paths and `<alias>` with the local selector copied from your bound package; keep all four identity components in the authored file. Inspect available evidence, missing channels and source provenance before selecting a locus.

```bash
python mamey_run.py mode-b --package '/path/to/working-package' --top-n 1 --outdir '/path/to/review/mode_b'
```

This prepares native top-lead output, not a finished card. Supply a working copy: the .447 CLI can refresh its package integrity files even with an external output folder. Keep the original sealed package and source hashes; see [post-seal boundaries](POSTSEAL_READERS.md#commands-that-still-author-package-data-in-447). `--top-n` is cumulative: 3 covers ranks 1–3. It does not select only the third lead. Review output files rather than inferring completion from the command name.

## Emit, author, then verify

The example selects current50 v2. Use `--contract full48` in both commands if that is the requested profile.

```bash
python mamey_run.py emit-modeb-template --package '/path/to/package' --bgc '<alias>' \
  --contract current50_v2 --out '/path/to/review/template.md'
```

Supply applicable cross-source inputs with `--cohort-dir`, `--reference-dir`, `--strain-metadata` and `--bigscape-regions-dir`; the strain metadata is read as supplied. The source-argument helper also serves `modeb-round`, `deliverable-queue` and `tools/emit_modeb_template_full50.py`. Missing source fields remain holds. A flag's existence does not establish that its input was available or admitted.

Author the saved template from admitted evidence. Preserve exact titles, channel separation, full identities, alternatives and per-claim sources. Do not fill missing evidence with plausible prose. Save the authored card separately from the template, then verify that actual file:

```bash
python mamey_run.py verify-modeb '/path/to/review/authored-card.md' \
  --package '/path/to/package' --bgc '<alias>' --contract current50_v2 \
  --summary-only --report-json '/path/to/review/card-verification.json'
```

The verifier requires the authored file as its first positional argument. Keep the JSON receipt and nonzero-exit findings. It does not perform online literature or protein searches. Do not force a finished pass or weaken depth simply to remove errors.

For an expanded-locus work order, follow [Expanded locus](MODEB_EXPANDED_LOCUS.md) and add `--require-expanded-locus` to the current50 v2 verification command. Supply repeated `--rescue-tsv` files only when the work order admits that context; [gap-rescue reader](MODEB_GAP_RESCUE_READER.md) explains that existence checks do not grant BGC membership.

## What a pass proves

Inspect the exact selected contract and gate receipt. A card-only current50 v2 check cannot certify the package's gene roster; supply the matching package and alias. A structural/depth pass does not verify every biological section, literature claim, physical linkage, compound identity or production. The current50 v2 route does not apply the full48 semantic publication gates to its different section numbers. Independent source/content review and owner scientific acceptance remain separate.

A useful request:

> Author one Mode B card for [full four-part identity] using [full48 or current50_v2], the validated package at [path] and admitted evidence at [paths]. Emit the selected template, author from the evidence, then verify the saved card with the same contract. Keep missing channels and alternatives explicit. Save the source mapping, verification receipt and unresolved scientific holds under [review folder].

## Recover and resume

Keep the template, authored card, source mapping, selected contract hash, input receipts, verification JSON and checkpoint together. Use [authoring preflight](MODE_B_AUTHORING_PREFLIGHT.md) to distinguish a permissible draft from a finished-profile hold. Reconcile a source or identity mismatch before continuing the affected claim. A failed check is not permission to edit sealed evidence or reduce requirements.

The [worked full48 reference card](reference/modeb_exemplars/phosphonate_reference_full48_no_blastp_exemplar.md) has [explicit scope limits](reference/modeb_exemplars/README.md); it is not a finished current50 v2 example. For updated evidence, retain the prior review and create a versioned update. A BGC alias alone cannot rebind a locus across runs.

For deeper writing guidance, use the [data availability contract](MODEB_DATA_AVAILABILITY_AND_WRITING_CONTRACT.md), [interpretive floor](MODEB_INTERPRETIVE_FLOOR_v97146.md) and [claim-safety audit](MODE_B_CARD_CLAIM_SAFETY_AUDIT.md) in the selected profile's scope. Their requirements are not evidence or release approval.
