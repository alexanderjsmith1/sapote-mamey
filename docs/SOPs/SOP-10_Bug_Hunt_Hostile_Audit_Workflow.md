# SOP-10 — Bug Hunt / Hostile Audit Workflow

## Purpose

Use this SOP to turn a pre-cut behavior review into supported findings and a cut recommendation.
Start with the selected SOP and trace its implementing command or code path before choosing a check.
For a codebase-wide pattern sweep, follow the [Bug Hunt protocol](../../debugging_modules/BUG_HUNT_PROTOCOL.md).
For a per-file Inspector/Defender review, use the [Bunny Hop protocol](../../debugging_modules/BUNNY_HOP_AUDIT_GAME.md).
Keep the reviewed scope and verification mode with each finding.

## Inputs

Bug Hunt can use:

- SOPs,
- patch packets,
- real antiSMASH ZIPs,
- BLASTP Hit Tables,
- XML2 files,
- sealed packages,
- public accession controls,
- prior known bugs.

## Method

For each SOP:

1. Identify required behavior.
2. Find the command or code path that should implement it.
3. Trace the source path first. Execute it only within the current authorized scope and resource limits; preserve private inputs and immutable originals. If execution is unavailable or unauthorized, record a source-only assessment or a separately labelled simulation.
4. Record the observed result and verification mode. An execution pass, source-supported finding, skipped check and untested hypothesis are different states. Do not label a simulated/source-only review as a passing runtime test.
5. If failed, classify severity.
6. Propose a test.
7. Decide whether the bug blocks the cut.

## Severity

| Severity | Meaning | Cut effect |
|---|---|---|
| BLOCKER | corrupts output, leaks private data, prevents run, or causes false sign-off | must fix |
| HIGH | common user path fails or overclaims evidence | must fix unless scoped out |
| MEDIUM | confusing or incomplete but recoverable | fix or document |
| LOW | polish, wording, non-critical warning | can defer |
| CHECK | skipped or unresolved evidence | explain before cut |

## Standing bug-hunt targets

1. BGC BLASTP FASTA export.
2. BLASTP result parser.
3. Headerless CSVs.
4. Comma-bearing query titles.
5. Giant NRPS/PKS follow-up labels.
6. Single-region accession inputs.
7. Selected [deliverable outputs](../DELIVERABLE_CONTRACT.md) and [strain privacy handling](../PORTABLE_STRAIN_PRIVACY_AND_EVIDENCE.md) — the historical C5/C7 categories.
8. Public/private redaction.
9. Claim boundary language.
10. Release packaging parity.

## Required Bug Hunt output

Use:

```text
BUG_ID:
SOP:
Baseline: exact source path, bundle/engine version and SHA-256
Reviewed scope and exclusions:
Path:
Expected:
Observed:
Severity:
Patch needed:
Test needed:
Verification mode: source-only | static check | executed | simulated | not checked
Evidence: exact source lines or command/output receipt
Skipped/held checks and reason:
Cut decision:
```

## Bug-hunt checks

1. Every bug has a test or a clear reason no test is practical.
2. Every skipped test has an explanation.
3. Every non-blocking issue is listed in release notes or known issues.
4. Candidate build cannot proceed with untriaged BLOCKER/HIGH bugs. Source review and test execution do not themselves authorize a release cut; use the current [owner cut protocol](../../CUT_PROTOCOL.md).
