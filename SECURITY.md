# Security Policy

## Scope
Sapote-Mamey is a research workflow that reads genome-mining output and emits interpretive,
claim-safe reports. It ships code and small governed reference data only — no third-party
databases, tools, or genomes. Its local extraction path is distinct from explicit online BLASTp, reference/download and companion-tool commands. Those operations can contact services and disclose selected sequence/metadata inputs; offline extraction does not establish that every CLI command is offline.

## Reporting a vulnerability
If private vulnerability reporting is enabled on the actual repository, use GitHub → Security →
Report a vulnerability. This bundle does not establish that the repository feature is enabled and
ships no independently verified private fallback contact. If it is unavailable, obtain the
maintainer’s authorized private reporting route before disclosing sensitive details. Preparing a
report does not authorize an assistant to send it.

Include bundle and engine versions, BUILD_STAMP, exact source/patch identity, affected path, the
operation and relevant flags, and a minimal synthetic or appropriately redacted reproduction.
Keep original source/input hashes and an observed-versus-expected result; do not upload a complete
private cohort, database, secrets or unrelated report set to demonstrate the issue.

We aim to acknowledge within a reasonable window and to coordinate a fix and disclosure timeline.
Because the tool is offline-by-default and processes the operator's own inputs, most risk relates
to parsing untrusted archive/JSON inputs; reports about archive traversal, resource exhaustion, or
unsafe deserialization are especially welcome.

## Supported versions
The latest owner-released bundle is the stated support target; a candidate filename or historical
PASS row does not establish that release. Check the archive-bound external receipt and owner
release decision separately. [Release record scopes](docs/RELEASE_RECORDS_GUIDE.md) distinguishes
change history, engine lineage, generated summaries and actual archive acceptance. Check the current repository security reporting policy for reporting routes and response expectations.
