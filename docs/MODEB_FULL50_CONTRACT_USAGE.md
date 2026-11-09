# The 50-section reference files

Most users do not need this page. To write a Mode B card, use the [profile guide](MODEB_PROFILE_MATRIX.md) and the [walkthrough](MODE_B_USER_WALKTHROUGH.md). This page is for someone who points a cohort tool at the 50-section text.

## What is shipped

- `docs/MODEB_50_SECTION_CONTRACT_CANDIDATE.md` is the 50-section text, called current50 v1.
- `mamey/data/mode_b/modeb_full50_contract.json` is a frozen copy of its 50 rows. It records the text's SHA-256 under `source_document.sha256`.
- The newer opt-in card profile is current50_v2, described in the [v2 contract](MODEB_CURRENT50_V2_CONTRACT.md). It is a different file with its own hash.

Check the hash of the text before you pin it:

```bash
shasum -a 256 docs/MODEB_50_SECTION_CONTRACT_CANDIDATE.md
```

The value must equal `source_document.sha256` in the JSON.

## Which tools read it

Each tool reads the text in a different way. Point each at the input it reads.

| Tool | What it reads |
|---|---|
| `mamey/evidence_disagreements.py` | A Markdown path and SHA-256 in the `contract` entry of its selection configuration. |
| `mamey/cohort_enzyme_neighborhoods.py` | Pinned Markdown at `sources.current50_contract` in its configuration. |
| `tools/cohort_tailoring/build_atlas.py` | The contract text and hash held in its database profile. It then checks sections 1 to 50. |
| `mamey/structured_domain_motif_extension.py` | The section rows in its database. |

In the evidence-disagreements selection file, the pin is a JSON entry. The path is relative to the selection file:

```text
"contract": {"path": "MODEB_50_SECTION_CONTRACT_CANDIDATE.md", "sha256": "<value from the JSON>"}
```

If the file is missing or its hash differs, the tool stops with `CURRENT50_CONTRACT_PIN_HOLD`.

Do not point a Markdown tool at the JSON. Its row parser rejects it. A matching path and hash show that you chose those bytes. They do not show the content is complete or right.

## What this does not do

- It does not run `verify-modeb` or write a card. Passing a tool's hash check is not a card check.
- It does not change the default full48 profile, which lives in `mamey/data/mode_b/modeb_full30_corrective_contract.json` and has 48 sections.
- Changing the text means a new contract and new pins. Do not reuse a v1 pin for v2, and do not edit a pinned file in place.
