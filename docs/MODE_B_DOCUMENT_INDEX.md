# Find the Mode B guide you need

Use this index to write, check or save a Mode B card from an existing package.
Start with one selected locus and its full identity:
**strain / full node-or-contig / region / BGC alias**.

## Write one card

1. [Choose the profile](MODEB_PROFILE_MATRIX.md): full48 is the default;
   current50_v2 is the optional 50-section profile.
2. Follow [the authoring walkthrough](MODE_B_USER_WALKTHROUGH.md) to prepare
   evidence, emit a template, write it and verify the saved file.
3. Use [preflight](MODE_B_AUTHORING_PREFLIGHT.md) to distinguish a draft with
   recorded gaps from a finished card. [Evidence availability](MODEB_DATA_AVAILABILITY_AND_WRITING_CONTRACT.md)
   explains what each stage needs.
4. Record the authored card in the package with `ingest-receipts --card`, as in step 6 of the [walkthrough](MODE_B_USER_WALKTHROUGH.md#6-save-and-review). `ingest-receipts` takes the card only; it has no option for the `verify-modeb` report, so keep that report and the command you ran beside the card yourself. Scripts can use the [Python helper](modules/MODE_B_WRITE.md).

For examples, use the [exemplar reader guide](reference/modeb_exemplars/README.md).
Copy a useful writing structure, then use your own locus, gene roster and citations.
The [full48 format example](reference/modeb_exemplars/phosphonate_reference_full48_no_blastp_exemplar.md)
has documented limits for sections 20, 39, 40, 42 and 48. They are stated in its "Calibration boundary" paragraph; read it before reusing the example.

## Resolve a specific problem

- **Large proteins, repeated comparator hits or conflicting evidence:** use
  [evidence escalation](MODEB_EVIDENCE_ESCALATION_WORKFLOW_v97143a.md).
- **Domain architecture:** use [domain-level review](modules/DOMAIN_LEVEL_MODE_B.md).
- **A fragmented or composite locus:** use [expanded-locus review](MODEB_EXPANDED_LOCUS.md)
  and keep competing explanations visible.
- **A batch of cards:** use [batch execution](modules/MODE_B_BATCH_RUN.md) (`emit-modeb-template --batch --scope pending`, then `ingest-receipts --auto-detect`), checking
  the requested roster and coverage rather than treating a top-N list as the full inventory.
- **Supporting gene evidence:** use [support cards](MODE_B_SUPPORT_CARD_CONTRACT.md).
- **Report layout:** use [the region page layout](PER_BGC_PAGE_LAYOUT_SPEC.md) and
  [delivery requirements](DELIVERABLE_CONTRACT.md).

## Older instructions

Older 8-, 10-, 20- and 30-section documents describe earlier formats. Use the
profile you chose in the [profile guide](MODEB_PROFILE_MATRIX.md) for what a finished
card needs.

## For maintainers and assistants

- [AGENTS.md](../AGENTS.md): the contract every coding assistant follows.
- [Maintenance inventory](MAINTENANCE_INVENTORY.generated.md): a generated list of maintained files and their owners.
- [Context preparation](MODEB_LLM_AUTHORING_CONTEXT_HYGIENE.md): what to give an assistant that drafts a card.
- [Writer and reviewer protocol](MODEB_DUAL_WRITER_AUDITOR_PROTOCOL.md): independent checking of a card.
- [Documentation index](../CURRENT_DOCS_INDEX.md): the wider reference material.
