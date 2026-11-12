# Choosing a Sapote-Mamey example

Most entries are format templates and renderer test fixtures, not results. `judgment_18strain/` is different: it holds retained historical literature-verification records, with their identity and verification holds. Start with [the user task router](../docs/USER_TASK_ROUTER.md) and [the current documentation index](../CURRENT_DOCS_INDEX.md).

The table lists the main entries, not every file. The folder also holds `directed_pks/`, `figure_factory/`, `privacy/`, `test_data/` and several JSON and TSV templates.

| Path | Intended use | Limit |
|---|---|---|
| [Layperson guide](layperson_guide_exemplar.md) | Plain-language evidence and uncertainty structure | Fill only source-backed fields. |
| [Bench guide](bench_guide_exemplar.md) | Evidence-scope and material-lineage format | No preselected experimental conditions; requires admitted evidence. |
| [Citation library](citation_library_exemplar.md) | Citation-entry format | Historical worked citations are illustrative; verify actual sources and exact locus bindings before reuse. |
| `document_rendering/` | Document-layout fixtures used by renderer tests | Synthetic/incomplete cards; a rendering pass is not scientific or current-profile validation. |
| `token_light_documents/pilot_project/templates/` | Reusable document-factory bodies | Templates have placeholders and synthetic holds. Use the project builder, `examples/token_light_documents/build_pilot_inputs.py`; do not treat them as finished analysis. |
| [Tree tracks](tree_tracks/README.md) | Synthetic exact-tip track demonstration | Fabricated observations/topology and local receipt bindings. |
| `judgment_18strain/` | Historical redacted literature-verification records | Incomplete locus identities and historical VERIFIED labels; not currently admitted cohort evidence. |

For a current Mode B card, emit the selected current template and verify the actual authored file using [the Mode B walkthrough](../docs/MODE_B_USER_WALKTHROUGH.md). Do not choose a profile by counting sections in a renderer fixture. Preserve complete identity as `strain / full node-or-contig / region / BGC alias`.

Copy fixture inputs to a disposable authorized workspace before regenerating assets. Some fixtures reference adjacent assets or receipt hashes; moving only the Markdown file can break those bindings. Keep each example's relative directory structure. Never regenerate into the immutable shipped example tree or overwrite a research receipt.

For the pilot builder, select a fresh authorized workspace explicitly:

```bash
python examples/token_light_documents/build_pilot_inputs.py --out reviews/EXAMPLE-pilot-project
```

Substitute a fresh path and quote spaces. Without `--out`, the builder targets the shipped `pilot_project`; it uses `mkdir(exist_ok=True)` and does not independently enforce freshness. Inspect the chosen folder first and keep shipped fixtures unchanged.

## Examples versus test evidence

The named reader exemplars and synthetic rendering fixtures demonstrate format, identity discipline and rendering inputs; they are not current validation receipts. [The fixture index](../tests/fixtures/README.md) identifies intentionally positive/negative test payloads and optional missing source files. [Reference-panel guidance](../docs/CI_REFERENCE_FIXTURES_GUIDE.md) distinguishes stored-marker regression from independent biological validation. Preserve historical example payloads and unresolved identity/evidence rather than altering them to make a current claim.
