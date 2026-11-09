# Reading the frozen fifty-section contract

[Original hash-bound contract](MODEB_50_SECTION_CONTRACT_CANDIDATE.md).

Choose the profile in [MODEB_PROFILE_MATRIX.md](MODEB_PROFILE_MATRIX.md); the scope rules for every
profile are in [MODEB_CONTRACT_HISTORY_AND_GATE_SCOPE.md](MODEB_CONTRACT_HISTORY_AND_GATE_SCOPE.md).

This is the proposed expanded publication-candidate contract, retained without changing its normative
section mapping. It is not the implemented `current50_v2` section map: this proposal's §22/§26 discuss
RiPP search/OSMAC, whereas `mamey/data/mode_b/modeb_current50_v2_contract.json` selects GECCO evidence /
contigs rescued into the BGC. The proposal also describes migrating former §48 synthesis into §19;
that policy is not proof that an emitter, gate, parser or author migrated any saved card.

The runnable selection is `--contract current50_v2` on the actual emitter/verifier, with §50 evidence
and §48/§49 literature. Its checker is `v2_findings` in `mamey/modeb_current50_v2.py`. `verify-modeb` routes a
`current50_v2` card to it from `mamey/authored_verify.py` (the `_v2_contract` branch); legacy full48
publication/semantic gates are not applied to this route.
Retain this proposed checklist for a specifically selected review, but report requirements not implemented
or not tested as holds. Do not use the full48 `publication_quality_findings` call in
[MODEB_GATE_CLEAN_AUTHORING.md](MODEB_GATE_CLEAN_AUTHORING.md) to certify these fifty sections.

## Read the frozen page with these corrections

The frozen page is bound by SHA-256 in `mamey/data/mode_b/modeb_full50_contract.json`, so its text is
not edited. Read it with these notes:

- `current50_v2` is opt-in. The default profile is `full48`. Pass `--contract current50_v2` to both
  commands, or you get 48 sections.
- "Emit the current §1–§50 scaffold" means:
  `python mamey_run.py emit-modeb-template --package runs/EXAMPLE/package --bgc BGC001 --contract current50_v2 --out reviews/EXAMPLE-mode-b.md`.
  `--out` must be a new file.
- "Run the publication gate" means verifying the saved card against the package, so the gene roster
  is bound:
  `python mamey_run.py verify-modeb reviews/EXAMPLE-mode-b.md --package runs/EXAMPLE/package --bgc BGC001 --contract current50_v2 --report-json reviews/EXAMPLE-verify-1.json`.
  It does not run the full48 publication gate in `mamey/modeb_publication_gate.py`.
- "This document change alone does not migrate emitters, gates or parsers" is out of date: both
  commands accept `--contract current50_v2` and read the 50-section JSON, with §48–§50 as the frozen
  page describes. §22 and §26 differ, as noted above.
- "V7 evidence" is an earlier evidence workup of the locus. The gate treats it as one of three
  historical sources, with the historical card and the historical locus map (`HISTORICAL_SOURCES` in
  `mamey/modeb_publication_gate.py`). Record `NOT_APPLICABLE` when your locus has none.
- Where the frozen page says "Sapote/Codex/Claude perform interpretation", read: Sapote, or the person
  authoring the card, interprets.

