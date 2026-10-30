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
4. [Save the authored card](modules/MODE_B_WRITE.md) and its verification record.

For examples, use the [exemplar reader guide](reference/modeb_exemplars/README.md).
Copy a useful writing structure, then use your own locus, gene roster and citations.
The [full48 format example](reference/modeb_exemplars/phosphonate_reference_full48_no_blastp_exemplar.md)
has documented limits for sections 20, 39, 40, 42 and 48; read those before reusing them.

## Resolve a specific problem

- **Large proteins, repeated comparator hits or conflicting evidence:** use
  [evidence escalation](MODEB_EVIDENCE_ESCALATION_WORKFLOW_v97143a.md).
- **Domain architecture:** use [domain-level review](modules/DOMAIN_LEVEL_MODE_B.md).
- **A fragmented or composite locus:** use [expanded-locus review](MODEB_EXPANDED_LOCUS.md)
  and keep competing explanations visible.
- **A batch of cards:** use [batch execution](modules/MODE_B_BATCH_RUN.md), checking
  the requested roster and coverage rather than treating a top-N list as the full inventory.
- **Supporting gene evidence:** use [support cards](MODE_B_SUPPORT_CARD_CONTRACT.md).
- **Preparing an assistant's context:** use [context preparation](MODEB_LLM_AUTHORING_CONTEXT_HYGIENE.md).
- **Independent checking:** use [the writer/reviewer protocol](MODEB_DUAL_WRITER_AUDITOR_PROTOCOL.md).
- **Report layout:** use [the region page layout](PER_BGC_PAGE_LAYOUT_SPEC.md) and
  [delivery requirements](DELIVERABLE_CONTRACT.md).

## Understand older instructions

Older 8-, 10-, 20- and 30-section documents describe earlier formats or additive
checks. Use the selected profile's current machine contract for finished-card
requirements. The full48 contract lives in a file with `full30` in its name;
that filename does not limit the card to 30 sections.

Ordinary full48 structure lint permits optional or conditional extensions in
sections 31–48. A basic structure pass therefore differs from finishing the
48-section card. Read the declared state and enabled checks with the result.

The outline at `SOPs/SOP-06_Mode_B_BGC_Card_Production.md` is marked as a placeholder.
Use the authoring walkthrough above for executable steps.

## For maintainers

Read the [bundle instructions](../AGENTS.md) before changing implementation.
The profile JSON files own section definitions. `mamey/modeb_structure_gate.py`
and `mamey/mode_b_receipt.py` implement the selected checks and saving path;
`mamey/validators/modeb_full20.py` is a legacy subset facade.

Use `mamey/gene_by_gene.py` and `mamey/mode_b/schema.py` for gene-table fields,
`mamey/mode_b/guards.py` for protein-length checks, and
`mamey/mode_b/comparator_workflow.py` for comparator prompts.
The workflow, coverage, quality-gate and receipt tests cover different behaviors;
read the relevant implementation and test together.

When the guide, code and tests disagree, record the discrepancy before changing
a card's completion status. The [current documentation index](../CURRENT_DOCS_INDEX.md)
locates the wider reference material.

<!-- Previous index section anchors -->
<a id="0-mandatory-first-read-bootstrap"></a>
<a id="1-current-mode-b-workflow-documents"></a>
<a id="2-mode-b-implementation-files"></a>
<a id="3-mode-b-tests-and-acceptance-gates"></a>
<a id="4-resolved-mode-b-contract-hierarchy"></a>
<a id="5-placeholder--caution-files"></a>
<a id="6-practical-reading-order-for-a-new-assistant-session"></a>
<a id="7-search-commands-to-rediscover-this-index-manually"></a>
<a id="8-minimal-mode-b-preflight-checklist"></a>
<a id="9-one-line-rule"></a>
