# Security Policy

## Scope
Sapote-Mamey is a research workflow that reads genome-mining output and emits interpretive,
claim-safe reports. The CODE archive ships small reference files and a few third-party Python components (packaging wheels and a vendored `ijson`). Local extraction runs offline. Online BLASTp, reference downloads and some companion tools contact outside services and can send them sequences or metadata.

## Reporting a vulnerability
Report privately through GitHub → Security → Report a vulnerability, if the repository has it turned on.
If it does not, ask the maintainer for a private route before sharing details.

Include bundle and engine versions, BUILD_STAMP, exact source/patch identity, affected path, the
operation and relevant flags, and a minimal synthetic or appropriately redacted reproduction.
Keep original source/input hashes and an observed-versus-expected result; do not upload a complete
private cohort, database, secrets or unrelated report set to demonstrate the issue.

We aim to acknowledge within a reasonable window and to coordinate a fix and disclosure timeline.
Because the tool is offline-by-default and processes the operator's own inputs, most risk relates
to parsing untrusted archive/JSON inputs; reports about archive traversal, resource exhaustion, or
unsafe deserialization are especially welcome.

## Supported versions
The supported version is the latest release the owner has published. A candidate archive is not a
release; [release record scopes](docs/RELEASE_RECORDS_GUIDE.md) explains how to tell them apart.
