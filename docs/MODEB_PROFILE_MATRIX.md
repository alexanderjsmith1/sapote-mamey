# Mode B profiles: which card is which

"Full Mode B" always means **the finished profile you selected**, never a section count on its own. Pick the profile
first, then use its producer and verifier. Machine definitions are the source of truth; this page routes to them.

| Profile | Sections | What it is | Producer | Verifier | Status it can claim |
|---|---|---|---|---|---|
| `MODEB_SCAFFOLD` | template headings | A mechanically populated evidence-routing artifact. Never a card. | `emit-modeb-template` | structure gate only | none |
| `MODEB_CANDIDATE_30` | conditional §1–§30 | Legacy candidate contract, kept for backward compatibility. | historical | `verify-modeb` (structure, depth) | candidate card |
| `FINISHED_FULL48_CURRENT_EVIDENCE` | §1–§48, exactly once, in order | **Default native finished profile.** Every section carries locus-specific interpretation or a reasoned not-applicable or hold statement. | `emit-modeb-template` (default `--contract full48`) | `verify-modeb` (publication gate triggers on the profile token) | engineering gate pass; current-evidence state requires source and independent review |
| current50 v1 | §1–§50 requirement rows | A reference contract for four consumers that need exactly 50 rows (`MODEB_FULL50_CONTRACT_USAGE.md`). Not a card profile. | none | consumer pins | none |
| `FINISHED_FULL50_CURRENT50_V2` | §1–§50 | Opt-in 50-section card: GECCO (§22), contigs rescued into the BGC (§26), literature with relevance (§48–§49), data evidence table last (§50). See `MODEB_CURRENT50_V2_CONTRACT.md`. | `emit-modeb-template --contract current50_v2` | `verify-modeb --contract current50_v2` | engineering gate pass; current-evidence state requires source and independent review |
| `EXPERIMENTALLY_ADJUDICATED` | any | A separate future state. A current-evidence card never implies it. | not automated | not automated | experimentally adjudicated |

**Machine definitions:**
- `mamey/data/mode_b/modeb_full30_corrective_contract.json` holds `modeb_corrective_full48_v1`, with 48 sections. Its `full30` filename is historical, and code depends on it.
- `mamey/data/mode_b/modeb_full50_contract.json` holds current50 v1.
- `mamey/data/mode_b/modeb_current50_v2_contract.json` holds current50 v2.

**Historical counts:** §1–§8, §1–§10, §1–§20 and conditional §1–§30 appear in older documents, including `MODE_B_FULL20_CONTRACT_RECONCILIATION.md` and `ACCEPTANCE_TESTS_MODE_B_FULL20_CONTRACT.md`. They are calibration history, not completion definitions.

**Draft, readiness, finished:** see `MODE_B_AUTHORING_PREFLIGHT.md` for which missing evidence still permits a draft, and which holds a claim or the finished status.

A structural pass is never scientific acceptance: judgment stays with the author and the independent reviewer.

[Exemplar reader guide](reference/modeb_exemplars/README.md): the supplied full48 reference demonstrates its historical format; the seven class cards are legacy sketches with incomplete section coverage. Their old FULL/OK statements are historical and do not certify a current50_v2 card. Reuse structure and register only; verify the new locus's identity, complete gene denominator, citations and independent evidence.

## Verification receipts and export are separate

Choose the intended contract explicitly and supply exact package/BGC context. A declaration token and section count do not create evidence. For full48, its finished token activates publication-quality checks; candidate cards use a different path. Opt-in semantic flags are not all automatic, and full48 semantic flags do not apply as content certification for current50's different section numbering. The current50 path has its own structural/depth/evidence checks; independent section-level content review remains required.

`verify-modeb` can return 0 with warnings. Its JSON records profile/contract, findings, roster/core-denominator flags and coverage status, but no card/package/source hashes, verifier source version, or complete override/options record. A receipt filename and `card_name` are insufficient to bind the exact validated bytes. Record those hashes and arguments separately, use a unique receipt path per attempt, and reverify after any card/source change. Existing receipt files are atomically replaced. Keep WARN/coverage-unverified holds visible; `independent_roster_bound` reflects context availability, not independent scientific review.

`--no-strict-depth` changes depth failures to warnings, and verifier `--force` changes the finished-profile claim-safety escalation behavior. A zero exit with such overrides is not equivalent to the unmodified work-order gate. The exporter applies only its limited claim-safety filter; [export guidance](MODEB_EXPORT_HOOK.md) covers per-format skips and output binding. The [judgment store](modules/MODE_B_WRITE.md) separately records legacy quality tiers and cannot manufacture a current-profile PASS.

Source owners: `mamey/authored_verify.py:68–109,591–680,804–879`; `mamey/cli.py:7241–7257`; `mamey/modeb_export.py:449–545`.
