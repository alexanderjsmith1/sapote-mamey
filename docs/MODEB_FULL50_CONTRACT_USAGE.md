# Using the 50-section Mode B contract

The bundle includes `docs/MODEB_50_SECTION_CONTRACT_CANDIDATE.md` and a frozen machine-readable copy of its 50 requirement rows in `mamey/data/mode_b/modeb_full50_contract.json`.

The JSON records the Markdown SHA-256 and the consumers that require a 50-section shape. It is a reference artifact, not a new input format for those consumers.

## Bind the input the consumer actually reads

- `mamey/evidence_disagreements.py` reads a Markdown path and SHA-256 from the selection configuration's `contract` entry.
- `mamey/cohort_enzyme_neighborhoods.py` reads pinned Markdown from `sources.current50_contract`.
- `tools/cohort_tailoring/build_atlas.py` checks the selected contract text and hash against its bound database profile, then checks sections 1 through 50.
- `mamey/structured_domain_motif_extension.py` checks section rows in its bound database.

For Markdown consumers, select the bundled Markdown and verify its bytes against `source_document.sha256` in the JSON. Do not point a Markdown consumer at the JSON: its row parser will reject that format. Database consumers still need their existing database bindings and profile checks.

A supplied path and matching hash prove the selected bytes, not independent authority or scientific completeness. This addition does not change consumer resolution, evidence admission, or completion gates.

## Preserve existing profiles

Keep the source Markdown unchanged while existing configurations pin its hash. A future revision needs an explicit new contract identity and updated bindings.

The separate `mamey/data/mode_b/modeb_full30_corrective_contract.json` contains the 48-section corrective profile. Its filename is historical. The 50-section reference does not supersede it.

Section requirements describe scope. Their presence does not supply evidence or establish biological conclusions. Judgment deferred.
