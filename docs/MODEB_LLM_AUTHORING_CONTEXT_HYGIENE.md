# What to put in a Mode B writing prompt

If you write a Mode B card with a language model, give it the evidence about the locus and nothing else. Release labels, file paths and task names pull the prose off the biology. This page lists what to include and what to leave out. It does not run anything.

For the card steps, see the [Mode B walkthrough](MODE_B_USER_WALKTHROUGH.md). For terms such as KCB and RG-GMCI, see the [glossary](GLOSSARY.md).

## Include

- The exact strain or reference label, the full node or contig, the antiSMASH region, its coordinates and the BGC alias.
- The exact CDS list, in order.
- The antiSMASH class, products, domains, modules, motifs and boundary evidence.
- Every other stream you have for this locus: the inventory, HMM and domain results, MIBiG, ClusterBlast, RG-GMCI and resistance.
- BLASTp results, each channel kept apart, only when they are bound to this exact locus.
- A typed state for each stream that is unavailable or does not apply.
- Prior-card and locus-map content, with a list of which parts you kept.
- Any validated source-specific receipts for cross-strain identity, family placement, composition or mobile-element context, and the full list of upstream results the card draws on.
- The claim limits: similarity is not identity, capacity is not production, and missing evidence is not biological absence.

## Leave out

- Public or private release labels, tier names and redaction instructions.
- PDF or image rendering status, unless the task is rendering.
- File paths, when a source name and hash say the same thing.
- Chat or task names and progress notes.
- Example genes, comparators, experiments or conclusions from some other locus.
- Private scoring weights, thresholds, phrase dictionaries, benchmark or holdout identities, repeated-phrase fingerprints and per-feature score deltas.
- Private material: owner authentication keys, private attempt ledgers, signatures and private calibration manifests.
- Placeholders for work still in progress, presented as results.

Keep the rules about who owns the data and where output may be written in the assistant's working instructions. Leaving release labels out of the prose does not lift them.

## A worked example

To see section order, how evidence is reconciled, how denominators stay separate and how a missing source is closed, read `docs/reference/modeb_exemplars/phosphonate_reference_full48_no_blastp_exemplar.md`. It is a historical full48 format example, not a `current50_v2` card, and its own header says it is not substantive calibration for §§20, 39, 40, 42 and 48. Take section numbers and readiness rules from your selected profile in [MODEB_PROFILE_MATRIX.md](MODEB_PROFILE_MATRIX.md). Do not copy its science into another card.

## Feedback boundary

A reviewer may give the writer one coarse route after a review:

- `PASS_TO_HUMAN_REVIEW`
- `HOLD_FOR_REWRITE`
- `UNSCORABLE_EVIDENCE_UNBOUND`

Do not expose exact threshold misses to the writer. Do not allow repeated probing of the same pass. No shipped command computes or sets a route. The finished-review-request check is a separate step: when a request carries a `blinded_score` record, it holds the request unless the supplied route is `PASS_TO_HUMAN_REVIEW` (`mamey/mode_b_receipt.py:2591-2594`). A route label does not show that any scoring ran.
