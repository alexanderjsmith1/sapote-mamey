# Mode B profiles: which card is which

"Full Mode B" always means **the finished profile you selected**, never a section count on its own. Pick the profile
first, then use its producer and verifier. Machine definitions are the source of truth; this page routes to them.

| Profile | Sections | What it is | Producer | Verifier | Status it can claim |
|---|---|---|---|---|---|
| `MODEB_SCAFFOLD` | template headings | A mechanically populated evidence-routing artifact. Never a card. | `emit-modeb-template` | structure gate only | none |
| `MODEB_CANDIDATE_30` | conditional §1–§30 | Legacy candidate contract, kept for backward compatibility. | historical | `verify-modeb` (structure, depth) | candidate card |
| `FINISHED_FULL48_CURRENT_EVIDENCE` | §1–§48, exactly once, in order | **Default native finished profile.** Every section carries locus-specific interpretation or a reasoned not-applicable or hold statement. | `emit-modeb-template` (default `--contract full48`) | `verify-modeb` (publication gate triggers on the profile token) | finished, current evidence |
| current50 v1 | §1–§50 requirement rows | A reference contract for four consumers that need exactly 50 rows (`MODEB_FULL50_CONTRACT_USAGE.md`). Not a card profile. | none | consumer pins | none |
| `FINISHED_FULL50_CURRENT50_V2` | §1–§50 | Opt-in 50-section card: GECCO (§22), contigs rescued into the BGC (§26), literature with relevance (§48–§49), data evidence table last (§50). See `MODEB_CURRENT50_V2_CONTRACT.md`. | `emit-modeb-template --contract current50_v2` | `verify-modeb --contract current50_v2` | finished, current evidence, once an independent review accepts it |
| `EXPERIMENTALLY_ADJUDICATED` | any | A separate future state. A current-evidence card never implies it. | not automated | not automated | experimentally adjudicated |

**Machine definitions:**
- `mamey/data/mode_b/modeb_full30_corrective_contract.json` holds `modeb_corrective_full48_v1`, with 48 sections. Its `full30` filename is historical, and code depends on it.
- `mamey/data/mode_b/modeb_full50_contract.json` holds current50 v1.
- `mamey/data/mode_b/modeb_current50_v2_contract.json` holds current50 v2.

**Historical counts:** §1–§8, §1–§10, §1–§20 and conditional §1–§30 appear in older documents, including `MODE_B_FULL20_CONTRACT_RECONCILIATION.md` and `ACCEPTANCE_TESTS_MODE_B_FULL20_CONTRACT.md`. They are calibration history, not completion definitions.

**Draft, readiness, finished:** see `MODE_B_AUTHORING_PREFLIGHT.md` for which missing evidence still permits a draft, and which holds a claim or the finished status.

A structural pass is never scientific acceptance: judgment stays with the author and the independent reviewer.
