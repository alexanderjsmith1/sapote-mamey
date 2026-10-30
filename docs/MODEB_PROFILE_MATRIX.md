# Choose a Mode B card profile

Choose the format for a new card, then use the [authoring walkthrough](MODE_B_USER_WALKTHROUGH.md).
You need a selected package, one complete locus identity and the evidence for that card.
The default is `full48`; choose `current50_v2` when the requested work calls for it.

## The two native command contracts

- **full48:** `FINISHED_FULL48_CURRENT_EVIDENCE`, with sections 1–48 once each in
  order. Named-match gene evidence belongs in section 4.
- **current50_v2:** `FINISHED_FULL50_CURRENT50_V2`, with sections 1–50 once each in
  order. GECCO is in section 22, rescued-contig evidence in 26, literature and
  relevance in 48–49, and the evidence table last in 50.

Use the same contract to emit and verify. Both commands default to full48; add
`--contract current50_v2` to choose the other profile. Each required section needs
locus-specific interpretation or a reasoned explanation of a gap. [Preflight](MODE_B_AUTHORING_PREFLIGHT.md)
explains when gaps allow a draft and when they hold a finished card.

The machine definitions are `mamey/data/mode_b/modeb_full30_corrective_contract.json`
(schema `modeb_corrective_full48_v1`) and
`mamey/data/mode_b/modeb_current50_v2_contract.json`. The first filename is historical;
it defines 48 sections. See the [current50 guide](MODEB_CURRENT50_V2_CONTRACT.md) for its details.

## Recognize older names and intermediate outputs

`MODEB_SCAFFOLD` is a template to author. `MODEB_CANDIDATE_30` is a legacy conditional
format. Older 8-, 10-, 20- and 30-section instructions describe earlier work, not the
current finished profiles. Current50 v1 is a reference contract used by
[four other consumers](MODEB_FULL50_CONTRACT_USAGE.md).

Use the [exemplar guide](reference/modeb_exemplars/README.md) for writing examples,
then check your own locus, gene denominator and citations. `EXPERIMENTALLY_ADJUDICATED`
is a separate future state without an automated producer or verifier.

## Read the verification result

Read the selected profile, arguments, findings and coverage status. Full48's
finished-profile token activates its publication-quality checks; later semantic
flags are opt-in. Current50 v2 uses its own checks.

Verification can return zero with warnings. Save card, package and source hashes,
verifier version and arguments beside the JSON report; that report omits those
bindings. Choose a new report filename for each attempt, because an existing file
is replaced, and reverify after editing the card or its sources.

`independent_roster_bound` means a roster context was available. `--no-strict-depth` reduces depth failures
to warnings; `--force` changes finished-profile escalation. Keep those overrides
visible when reviewing a zero exit.

After verification, follow [export](MODEB_EXPORT_HOOK.md) or
[save the authored card](modules/MODE_B_WRITE.md). Read and review the actual text
and evidence before accepting the interpretation.
