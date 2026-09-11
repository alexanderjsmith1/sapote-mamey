# SOP-09 — C7 Public Workbook / Redaction Safety

> **STATUS: PLACEHOLDER / OUTLINE ONLY.** This file is included to reserve the SOP ID and section structure for multi-chat coordination. Do not treat it as completed operator instructions until this status line is removed.

## Status

Outline placeholder for v9.7.319 SOP library (structure reserved at v9.7.142). This file exists so another chat can pick it up without needing to invent the SOP map.

## Required sections

1. Purpose
2. Scope
3. Inputs
4. Required commands
5. Required outputs
6. Expected warnings
7. Failure recovery
8. Claim boundary
9. Bug-hunt checks
10. Tests required before release

## Open work

Draft this SOP, then convert every expectation into at least one bug-hunt check.

## v9.7.142 note

Public-safe BLASTP exports should use sanitized query headers such as `PUBLIC-FIXTURE-001`; raw private AS/SID labels in BLASTP query titles are allowed only in private-tier evidence stores and must not leak into public workbook/report artifacts.
