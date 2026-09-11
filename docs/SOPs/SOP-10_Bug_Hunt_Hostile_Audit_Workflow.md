# SOP-10 — Bug Hunt / Hostile Audit Workflow

## Purpose

This SOP defines the pre-cut Bug Hunt process.

Bug Hunt is not a vague review. It is an adversarial pass that tries to break the system before a release candidate is cut.

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
3. Run or simulate the path.
4. Record pass/fail.
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

## Standing Bug Hunt targets (categories, established v9.7.142)

1. BGC BLASTP FASTA export.
2. BLASTP result parser.
3. Headerless CSVs.
4. Comma-bearing query titles.
5. Giant NRPS/PKS follow-up labels.
6. Single-region accession inputs.
7. C5/C7 optional deliverables.
8. Public/private redaction.
9. Claim boundary language.
10. Release packaging parity.

## Required Bug Hunt output

Use:

```text
BUG_ID:
SOP:
Path:
Expected:
Observed:
Severity:
Patch needed:
Test needed:
Cut decision:
```

## Bug-hunt checks

1. Every bug has a test or a clear reason no test is practical.
2. Every skipped test has an explanation.
3. Every non-blocking issue is listed in release notes or known issues.
4. Candidate build cannot proceed with untriaged BLOCKER/HIGH bugs.
