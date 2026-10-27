# Choose a Mode B card profile

For a new card, choose **`full48`**, the native default, unless the work order requests **`current50_v2`**. Then follow the [walkthrough](MODE_B_USER_WALKTHROUGH.md) to prepare evidence, author, verify, save and review. “Full Mode B” means the selected finished profile, rather than a section count alone.

## The two native command contracts

| Command contract | Finished profile | Authoring layout | Emit and verify |
|---|---|---|---|
| `full48` (default) | `FINISHED_FULL48_CURRENT_EVIDENCE` | §1–§48 exactly once in order. Every section has locus-specific interpretation or a reasoned not-applicable/hold statement; named-match gene evidence is in §4. | `emit-modeb-template --contract full48`; `verify-modeb --contract full48` |
| `current50_v2` (opt-in) | `FINISHED_FULL50_CURRENT50_V2` | §1–§50 exactly once in order. GECCO §22; rescued-contig evidence §26; literature and relevance §48–§49; evidence table last at §50, with no appendices after it. | `emit-modeb-template --contract current50_v2`; `verify-modeb --contract current50_v2` |

Use the same contract on both commands and pass the saved authored file, matching package and alias to verification. The walkthrough supplies complete examples. The [authoring preflight](MODE_B_AUTHORING_PREFLIGHT.md) distinguishes a permissible draft from evidence gaps that hold finished status. Neither route's engineering pass establishes current-evidence sufficiency without source and independent review.

Machine definitions govern titles and requirements:

- `mamey/data/mode_b/modeb_full30_corrective_contract.json` contains schema `modeb_corrective_full48_v1`, with **48 sections**. Its filename is historical and code depends on it.
- `mamey/data/mode_b/modeb_current50_v2_contract.json` contains current50 v2. Read the [current50 v2 guide](MODEB_CURRENT50_V2_CONTRACT.md) for that profile's requirements.

## Recognize older names and intermediate outputs

| Name you may encounter | How to use it |
|---|---|
| `MODEB_SCAFFOLD` | Emitted headings and mechanically populated evidence routing, checked for structure. Author it before calling it a card. |
| `MODEB_CANDIDATE_30` | Legacy conditional §1–§30 candidate contract, retained for compatibility and historical producer workflows; its structure/depth path does not finish a new full48/current50 v2 card. |
| current50 v1 | A 50-row reference contract in `mamey/data/mode_b/modeb_full50_contract.json` for [four specific consumers](MODEB_FULL50_CONTRACT_USAGE.md), rather than a native card profile. |
| §1–§8, §1–§10, §1–§20 and older §1–§30 instructions | Calibration history, including `MODE_B_FULL20_CONTRACT_RECONCILIATION.md` and `ACCEPTANCE_TESTS_MODE_B_FULL20_CONTRACT.md`; these counts do not define current completion. |
| `EXPERIMENTALLY_ADJUDICATED` | A separate future state with no automated producer or verifier. A current-evidence card does not imply it. |

The [exemplar reader guide](reference/modeb_exemplars/README.md) describes the worked full48 reference and seven legacy class sketches. Their old FULL/OK labels do not certify a current50 v2 card. Reuse structure and writing register only after checking the new locus's complete identity, gene denominator, citations and independent evidence.

## Read the verification result

For full48, the finished-profile token activates publication-quality checks; candidate cards follow a different path. Later semantic flags remain opt-in. Current50 v2 has its own structural/depth/evidence checks; full48 semantic flags do not certify current50's different section numbers. Check the actual selected contract, arguments and findings.

`verify-modeb` can return 0 with warnings. Its JSON records profile/contract, findings, roster/core-denominator flags and coverage status. It does **not** record card/package/source hashes, verifier source version or a complete options/override record. Save those bindings separately, use a unique receipt path per attempt, and reverify after card/source changes. Existing receipt files are atomically replaced. `independent_roster_bound` means context was available, rather than an independent scientist reviewed it; keep WARN and coverage-unverified findings visible.

`--no-strict-depth` turns depth failures into warnings. Verifier `--force` changes finished-profile claim-safety escalation. A zero exit with either override is not equivalent to the unmodified work-order gate.

After verification, use [export guidance](MODEB_EXPORT_HOOK.md) for its limited claim-safety filter, per-format skips and output binding, or [the judgment store](modules/MODE_B_WRITE.md) for persistence. Export and legacy stored quality tiers do not manufacture a current-profile PASS. Independent source/content review and scientific acceptance remain separate.
